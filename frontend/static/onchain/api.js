/**
 * L'unico posto che parla col backend. Ogni chiamata passa da `request`,
 * quindi il timeout e la forma dell'errore sono uguali ovunque: il resto
 * dell'app vede o un oggetto, o un ApiError con un messaggio in italiano
 * gia' pronto da mostrare.
 */

export class ApiError extends Error {}

const DEFAULT_TIMEOUT_MS = 8000;

// This browser, for the push of a finished job (bg.js, backend jobs.py): a
// random id kept here, sent on every call as X-Device.
export const device = (() => {
  try {
    let d = localStorage.getItem("lae.device");
    if (!d) { d = crypto.randomUUID().replace(/-/g, ""); localStorage.setItem("lae.device", d); }
    return d;
  } catch { return ""; }
})();
const headersFor = (body) => ({ ...(body ? { "Content-Type": "application/json" } : {}), ...(device ? { "X-Device": device } : {}) });

// GET identici in volo insieme diventano una richiesta sola: all'avvio
// saldo e stato di rischio li chiedevano due pannelli ciascuno, e ogni
// saldo e' una chiamata RPC vera lato server. Chi arriva dopo riceve la
// stessa risposta (o lo stesso errore) di chi e' partito per primo.
const inFlight = new Map();

function request(path, options = {}) {
  if ((options.method ?? "GET") !== "GET") {
    inFlight.clear();  // una scrittura rende vecchia qualunque lettura partita prima
    return send(path, options);
  }
  let pending = inFlight.get(path);
  if (!pending) {
    pending = send(path, options).finally(() => inFlight.delete(path));
    inFlight.set(path, pending);
  }
  return pending;
}

async function send(path, { method = "GET", body, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: headersFor(body),
      body: body ? JSON.stringify(body) : undefined,
      // AbortSignal.timeout al posto di una Promise.race con setTimeout:
      // qui la richiesta viene davvero interrotta, non solo ignorata.
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (cause) {
    throw new ApiError(cause.name === "TimeoutError" ? "network is slow" : "network unreachable", { cause });
  }

  let payload = null;
  try { payload = await response.json(); } catch { /* 204, o una risposta non-JSON */ }

  if (!response.ok) {
    const d = payload?.detail;
    throw Object.assign(new ApiError(typeof d === "string" ? d : `error ${response.status}`), { status: response.status, detail: d });
  }
  return payload;
}

export const getSession = () => request("/api/auth/me");
export const login = (email, password) => request("/api/auth/login", { method: "POST", body: { email, password } });

export const listWallets = () => request("/api/onchain/wallets");
export const createWallet = (chain) => request("/api/onchain/wallets", { method: "POST", body: { chain } });
export const setWalletEnabled = (chain, enabled) =>
  request(`/api/onchain/wallets/${chain}`, { method: "PATCH", body: { enabled } });

export const getBalance = (chain) => request(`/api/onchain/wallets/${chain}/balance`);
export const getTransactions = (chain) => request(`/api/onchain/wallets/${chain}/transactions`, { timeoutMs: 15000 });
export const getPositions = (chain) => request(`/api/onchain/positions/${chain}`);
export const getRiskStatus = (chain) => request(`/api/onchain/risk/status/${chain}`);
export const resetCircuitBreaker = (chain) =>
  request(`/api/onchain/risk/circuit-breaker/${chain}/reset`, { method: "POST" });

export const simulateOrder = (order) => request("/api/onchain/simulate", { method: "POST", body: order });

// Lo swap in due tempi, sempre: prima il preventivo (nessuna chiave, nessun
// impegno), poi — solo se l'utente conferma e solo se il server ha
// l'esecuzione accesa — l'ordine vero. Il backend rifa' comunque il quote da
// se' prima di firmare: quello qui sotto serve a far vedere il prezzo, non e'
// il numero su cui si firma.
export const quoteSolana = (body) => request("/api/onchain/quote/solana", { method: "POST", body, timeoutMs: 15000 });
export const getTokenInfo = (chain, address) => request(`/api/onchain/token/${chain}/${address}`, { timeoutMs: 12000 });
export const searchTokens = (chain, query) =>
  request(`/api/onchain/tokens/search?chain=${chain}&query=${encodeURIComponent(query)}`, { timeoutMs: 10000 });
export const quoteRobinhood = (body) => request("/api/onchain/quote/robinhood", { method: "POST", body, timeoutMs: 15000 });

// One id per click: a retry of the same request can't trade twice.
const withOrderId = (body) => ({ client_order_id: crypto.randomUUID(), ...body });
export const executeSolana = (body) =>
  request("/api/onchain/execute/solana", { method: "POST", body: withOrderId(body), timeoutMs: 45000 });
export const executeRobinhood = (body) =>
  request("/api/onchain/execute/robinhood", { method: "POST", body: withOrderId(body), timeoutMs: 45000 });

export const sendToken = (body) =>
  request("/api/onchain/send", { method: "POST", body: withOrderId(body), timeoutMs: 45000 });

export const requestReveal = (chain) =>
  request(`/api/onchain/wallets/${chain}/reveal/request`, { method: "POST" });
export const consumeReveal = (chain, token) =>
  request(`/api/onchain/wallets/${chain}/reveal`, { method: "POST", body: { token } });

// Ordini limite (piano DEX): non un book on-chain vero, size+prezzo+
// direzione persistiti ed eseguiti dal server quando il prezzo tocca il
// target — vedi limit_order_loop in main.py.
export const createLimitOrder = (body) => request("/api/onchain/limit-orders", { method: "POST", body });
export const listLimitOrders = (chain) => request(`/api/onchain/limit-orders/${chain}`);
export const cancelLimitOrder = (id) => request(`/api/onchain/limit-orders/${id}`, { method: "DELETE" });
export const getHistory = (chain) => request(`/api/onchain/history/${chain}`, { timeoutMs: 15000 });

// Ecosistema DEX (piano 2026-09-23): portafoglio reale, grafico ereditato
// dal motore del sito principale, e le stesse strategie dell'archivio
// (Watchlist) attivabili da qui invece che da un'altra tab.
export const getPortfolio = (chain) => request(`/api/onchain/portfolio/${chain}`, { timeoutMs: 15000 });
export const getChart = (chain, address, interval = "15m") =>
  request(`/api/onchain/chart/${chain}/${address}?interval=${interval}`, { timeoutMs: 15000 });
export const getLivePrice = (chain, address) => request(`/api/onchain/price/${chain}/${address}`, { timeoutMs: 8000 });

// Ponte sniper -> trend EMA (2026-09-23): il server aggiunge da solo alla
// watchlist, con la strategia trend EMA attiva, i token scoperti dallo
// sniper su questa chain — qui solo l'interruttore per utente/chain.
export const getRadar = () => request("/api/onchain/radar");
export const getRadarFeed = () => request("/api/onchain/radar/feed", { timeoutMs: 15000 });
export const getLeaderboard = () => request("/api/onchain/leaderboard");
export const getAlerts = (kind) => request(`/api/onchain/alerts/${kind}`);
export const getScanFeed = () => request("/api/onchain/scan-feed");
export const getLivePrices = (keys) => request(`/api/onchain/live-prices?ids=${encodeURIComponent(keys.join(","))}`, { timeoutMs: 5000 });
export const getTrack = () => request("/api/onchain/track");
export const getTopBacktest = () => request("/api/onchain/top/backtest", { timeoutMs: 20000 });
export const getAgentLog = (before) => request(`/api/agent/log?limit=60${before ? `&before=${before}` : ""}`);
export const getAgentJourney = ({ q = "", chain = "", token = "" } = {}) =>
  request(`/api/agent/journey?q=${encodeURIComponent(q)}&chain=${encodeURIComponent(chain)}&token=${encodeURIComponent(token)}`);
/* Which wallet the profile and the header show: the real ones or the
 * autotrader's simulated one. A per-device choice. */
// The simulated wallet traded the strategies: with trading off there is only the real one.
export const walletMode = () => {
  if (document.documentElement.dataset.trading !== "on") return "real";
  try { return localStorage.getItem("lae:wallet") === "sim" ? "sim" : "real"; } catch { return "real"; }
};
export const setWalletMode = (m) => {
  try { localStorage.setItem("lae:wallet", m); } catch { /* private mode: this page only */ }
  document.dispatchEvent(new CustomEvent("lae:wallet-mode", { detail: m }));
};
const walletQ = () => (walletMode() === "sim" ? "?wallet=sim" : "");
export const getProfile = () => request(`/api/profile${walletQ()}`, { timeoutMs: 25000 });
export const getHidden = () => request("/api/profile/hidden");
export const setHidden = (body) => request("/api/profile/hidden", { method: "POST", body });
export const updateProfile = (body) => request("/api/profile", { method: "PATCH", body });
export const uploadAvatar = (body) => request("/api/profile/avatar", { method: "POST", body, timeoutMs: 30000 });
export const walletChallenge = (body) => request("/api/wallets/link/challenge", { method: "POST", body });
export const walletLink = (body) => request("/api/wallets/link", { method: "POST", body });
export const getLinkedWallets = () => request("/api/wallets/linked");
export const scanToken = (query) => request("/api/onchain/scan", { method: "POST", body: { query }, timeoutMs: 60000 });
// The scan step by step (manual_scan.Steps): one JSON line per event, the
// last one carries the result.
export async function streamScan(query, onEvent, { view = "", onId } = {}) {
  let response;
  try {
    response = await fetch("/api/onchain/scan/stream", {
      method: "POST", headers: headersFor(true), body: JSON.stringify({ query, view }),
      signal: AbortSignal.timeout(300000),
    });
  } catch (cause) {
    throw new ApiError(cause.name === "TimeoutError" ? "network is slow" : "network unreachable", { cause });
  }
  if (!response.ok || !response.body) throw new ApiError(`scan failed (${response.status})`);
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = "", result = null, id = null;
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += value;
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim();
        buf = buf.slice(i + 1);
        if (!line) continue;
        const ev = JSON.parse(line);
        if ("result" in ev) result = ev.result;
        else if ("id" in ev) { id = ev.id; onId?.(id); }
        else if (!("ping" in ev)) onEvent(ev);
      }
    }
  } catch (cause) {
    // Safari says "Load failed" when a phone drops the stream: the scan goes on
    // on the server, so collect its result instead of showing an error.
    if (!id) throw new ApiError("connection lost, run the scan again", { cause });
  }
  if (result) return result;
  if (!id) throw new ApiError("scan interrupted");
  onEvent({ reconnecting: true });
  for (let k = 0; k < 90; k++) {
    await new Promise((r) => setTimeout(r, 2000));
    let d;
    try { d = await send(`/api/onchain/scan/result/${encodeURIComponent(id)}`, { timeoutMs: 10000 }); }
    catch (err) { if (String(err.message).startsWith("scan not found")) throw new ApiError("the server restarted during the scan, run it again"); continue; }
    if (d.done) return d.result;
  }
  throw new ApiError("scan is taking too long, try again");
}
export const addScanned = (chain, token) => request("/api/onchain/scan/add", { method: "POST", body: { chain, token } });
export const getTop = (n, keys = []) =>
  request(`/api/onchain/top?n=${n}${keys?.length ? `&narrative=${encodeURIComponent(keys.join(","))}` : ""}`);
// Whitekobra's Quality list (quality.js): 404 for the other accounts.
export const getQuality = () => request("/api/onchain/quality", { timeoutMs: 20000 });
export const decideQuality = (chain, token, action) =>
  request("/api/onchain/quality", { method: "POST", body: { chain, token, action } });
export const getNarrativeCoverage = () => request("/api/onchain/narratives/coverage");
export const getToken = (chain, token) => request(`/api/onchain/token?chain=${encodeURIComponent(chain)}&token=${encodeURIComponent(token)}`);
export const recheckToken = (chain, token) =>
  request(`/api/onchain/token/recheck?chain=${encodeURIComponent(chain)}&token=${encodeURIComponent(token)}`,
          { method: "POST", timeoutMs: 120000 });
export const recheckProgress = (chain, token) =>
  request(`/api/onchain/token/recheck/progress?chain=${encodeURIComponent(chain)}&token=${encodeURIComponent(token)}`,
          { timeoutMs: 8000 });
// The same re-check as a job (bg.js): {job} at once, the result by poll or push.
export const recheckJob = (chain, token, bg) =>
  request(`/api/onchain/token/recheck?chain=${encodeURIComponent(chain)}&token=${encodeURIComponent(token)}`,
          { method: "POST", body: bg, timeoutMs: 20000 });
export const getJob = (id, visible = false) => send(`/api/jobs/${encodeURIComponent(id)}${visible ? "?visible=1" : ""}`, { timeoutMs: 10000 });
export const getPushKey = () => request("/api/push/key");
export const pushSubscribe = (subscription) => request("/api/push/subscribe", { method: "POST", body: { subscription } });
export const getSlippage = (chain, token) => request(`/api/onchain/slippage?chain=${encodeURIComponent(chain)}&token=${encodeURIComponent(token)}`, { timeoutMs: 12000 });
export const getAgent = () => request("/api/agent");
export const getDeposit = () => request("/api/wallets/deposit");
export const getWalletsTotal = () => request(`/api/wallets/total${walletQ()}`, { timeoutMs: 30000 });
export const buildUserSwap = (body) => request("/api/wallets/swap/build", { method: "POST", body, timeoutMs: 30000 });
export const walletUnlink = (kind, address) => request(`/api/wallets/link/${kind}/${address}`, { method: "DELETE" });
export const getAiReview = () => request("/api/onchain/ai-review");
export const getProjects = (params) => request(`/api/onchain/projects?${new URLSearchParams(params)}`);
export const getRadarLessons = () => request("/api/onchain/radar/lessons");
export const getRadarMemes = () => request("/api/onchain/radar/memes");
export const getTokenChart = (chain, pool, symbol, interval, peek = false) =>
  request(`/api/onchain/chart?${new URLSearchParams({ chain, pool, symbol, interval, ...(peek ? { peek: "1" } : {}) })}`);
export const getRadarChart = (chain, pool, symbol, interval) =>
  request(`/api/onchain/radar/chart?${new URLSearchParams({ chain, pool, symbol, interval })}`);
export const followRadar = (body) => request("/api/onchain/radar/follow", { method: "POST", body });

export const getStrategies = () => request("/api/strategies");
export const getWatchlist = () => request("/api/watchlist");
export const addWatchlistEntry = (body) => request("/api/watchlist", { method: "POST", body });
export const setWatchlistStrategy = (id, strategyName, enabled) =>
  request(`/api/watchlist/${id}/strategy`, { method: "PATCH", body: { strategy_name: strategyName, enabled } });
export const setWatchlistAutoTrade = (id, strategyName, enabled) =>
  request(`/api/watchlist/${id}/auto_trade`, { method: "PATCH", body: { strategy_name: strategyName, enabled } });

export const getQuant = () => request("/api/agent/quant");
export const getQuantProject = (chain, token) => request(`/api/agent/quant/project?chain=${encodeURIComponent(chain)}&token=${encodeURIComponent(token)}`);
export const getQuantReport = (id) => request(`/api/agent/quant/reports/${encodeURIComponent(id)}`);
// The mic button (ask.js): DeepSeek may read the database a few times before answering.
export const askAgent = (text, voice = false, talk = false) =>
  request("/api/agent/ask", { method: "POST", body: { text, voice, talk }, timeoutMs: 120000 });
// The agent's answer as speech (WAV from the server's Piper voice). Not
// through `request`: the body is audio, not JSON.
export async function speakAgent(text, lang = "it") {
  const response = await fetch("/api/agent/speak", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, lang }), signal: AbortSignal.timeout(12000),
  });
  if (!response.ok) throw Object.assign(new ApiError(`error ${response.status}`), { status: response.status });
  return response.blob();
}
export const askJob = (text, voice, view) =>
  request("/api/agent/ask", { method: "POST", body: { text, voice, view, background: true }, timeoutMs: 20000 });
