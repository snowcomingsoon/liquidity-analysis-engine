/**
 * Punto d'ingresso della schermata wallet.
 *
 * Tiene insieme la sessione, il disegno della schermata per la chain
 * scelta, e il collegamento fra i pannelli sempre visibili (grafico,
 * ordine, posizioni/ordini/storico/strategie) e i pochi dialog rimasti
 * (Ricevi, Limiti, Simula, Rivela chiave). Tutto il resto sta nei moduli
 * accanto — questo file monta e smonta, non disegna i form.
 */
import "@onchain/nozoom.js";
import "@onchain/theme.js";
import "@onchain/ui.js";
import * as api from "@onchain/api.js";
import { ApiError } from "@onchain/api.js";
import { freshness, formatToken, formatUsd, shortAddress, usdParts } from "@onchain/format.js";
import { startReveal } from "@onchain/reveal.js";
import * as sheets from "@onchain/sheets.js";
import { drawSparkline } from "@onchain/sparkline.js";
import { appendHistory, chainInfo, readCache, readHistory, state, writeCache } from "@onchain/store.js";
import { mountSwap } from "@onchain/swap.js";
import { mountLimitOrder, mountOpenOrders, mountHistory } from "@onchain/limitOrders.js";
import { mountChart, onTokenChanged, resetForChainSwitch, setToken as setChartToken } from "@onchain/chart.js";
import { refreshHoldings } from "@onchain/holdings.js";
import { mountLeaderboard } from "@onchain/leaderboard.js";
import { mountProjects } from "@onchain/projects.js";
import { mountAlerts, openInbox } from "@onchain/alerts.js";
import { flash, liveDelta, liveKey, roll, watch } from "@onchain/live.js";
import { mountProfile, phantomAnswer, refreshProfile } from "@onchain/profile.js";
import * as phantom from "@onchain/phantomlink.js";
import { loadLinked } from "@onchain/userswap.js";
import { mountMemes } from "@onchain/memes.js";
import { mountAgent, mountAgentView } from "@onchain/agent.js";
import { mountAsk } from "@onchain/ask.js";
import * as bg from "@onchain/bg.js";
import { mountTop } from "@onchain/top.js";
import { mountQuality } from "@onchain/quality.js";
import { mountTrack } from "@onchain/track.js";
import { deskView, openFirst, openFromHash } from "@onchain/detail.js";

// Sulla pagina a se' (onchain-app.html) la radice e' il documento intero.
// Fusa dentro la tab Trading, invece, questo modulo viene importato dentro
// un contenitore con id "onchain-embed": restringere qui la ricerca evita
// che un id del wallet (nessuno oggi collide, ma un domani sì) catturi un
// elemento omonimo del resto del sito invece del suo.
const ROOT = document.getElementById("onchain-embed") ?? document;
const $ = (selector) => ROOT.querySelector(selector);
const $$ = (selector) => ROOT.querySelectorAll(selector);
// Trading and automatic strategies: off unless <html data-trading="on"> (see VIEWS).
const TRADING = document.documentElement.dataset.trading === "on";
// Trading-only modules are imported on demand, so with trading off the
// browser never downloads them (main.py leaves them out of modulepreload).

const view = {
  login: $("#login-screen"),
  shell: $("#app-shell"),
  balance: $("#balance"),
  address: $("#address"),
  chainLabel: $("#chain-label"),
  chainIcon: $("#chain-ic"),
  chainFlip: $("#chain-flip"),
  fresh: $("#fresh"),
  liveDot: $("#live-dot"),
  spark: $("#spark"),
  status: $("#status"),
  statusText: $("#status-text"),
  marketOrderRow: $("#market-order-row"),
  marketPanel: $("#market-panel"),
  orderPanelBody: $("#order-panel-body"),
  bottomPanel: $("#bottom-panel"),
  bottomPanelBody: $("#bottom-panel-body"),
  topbarAddress: $("#topbar-address-text"),
  statusSub: $("#status-sub"),
  actions: $("#actions"),
  reveal: $("#reveal-row"),
  more: $("#more-btn"),
  moreSheet: $("#more"),
  empty: $("#onchain-empty-state"),
  dock: $("#dock"),
  holdings: $("#holdings"),
  walletView: $("#wallet-view"),
  toast: $("#toast"),
};

/* ------------------------------------------------------------------ chain */

const CHAIN_ICON = { solana: "◎", robinhood: "◆", base: "■", bsc: "◈", ethereum: "Ξ", arc: "◠" };

function paintChainStatic() {
  const { label, unit, suffix } = chainInfo();
  const cached = readCache(state.chain);
  const wallet = state.wallets[state.chain];
  const hasWallet = Boolean(wallet || cached);

  view.chainLabel.textContent = view.chainFlip ? label : `${label}${suffix}`;
  if (view.chainFlip) view.chainFlip.title = `${label}${suffix} · tap to switch network`;
  if (view.chainIcon) view.chainIcon.textContent = CHAIN_ICON[state.chain] ?? "";
  for (const node of [view.actions, view.reveal, view.more, view.walletView]) {
    if (node) node.hidden = !hasWallet;
  }
  for (const node of [view.status, view.marketOrderRow, view.bottomPanel]) {
    if (node) node.hidden = !hasWallet || !TRADING;
  }
  view.empty.hidden = hasWallet || !TRADING;   // no wallet to create for research only
  view.balance.hidden = !hasWallet;
  view.address.hidden = !hasWallet;

  if (!hasWallet) {
    view.empty.querySelector("[data-chain-name]").textContent = label;
    view.spark.hidden = true;
    if (view.holdings) view.holdings.hidden = true;
    if (!(TRADING ? ["gems", "meme"] : ["gems", "pearl", "top", "rank", "quality", "agent", "profile"]).includes(view.shell.dataset.view)) setView("gems");
    return;
  }

  const address = wallet?.address ?? cached?.address ?? "";
  view.address.textContent = shortAddress(address);
  if (view.topbarAddress) {
    view.topbarAddress.textContent = shortAddress(address);
    view.topbarAddress.closest("button").dataset.full = address;
  }
  view.address.dataset.full = address;
  view.fresh.textContent = cached ? freshness(cached.at) : "waiting for first balance";
  paintBalance(cached, unit);
  drawSparkline(view.spark, readHistory(state.chain), sparkFormatter());
}

function sparkFormatter() {
  const usdMode = readCache(state.chain)?.native_usd_value != null;
  return (value) => (usdMode ? formatUsd(value) : formatToken(value));
}

// Un tocco sulla cifra cambia unita': nativa (SOL/ETH), dollari, BTC, e
// si ricomincia. Richiesta: "se clicco su ETH mi switchi la visualizzazione
// in dollari, in Bitcoin e basta". Le viste senza prezzo si saltano, mai
// un valore inventato; la scelta resta fra una visita e l'altra.
const BALANCE_MODES = ["native", "usd", "btc"];
const BALANCE_MODE_KEY = "onchain.balanceMode";
let balanceMode = "usd";
try { balanceMode = localStorage.getItem(BALANCE_MODE_KEY) || "usd"; } catch { /* resta "usd" */ }
let lastPainted = null;

function balanceModes(reading) {
  const usdValue = reading.native_usd_value;
  return BALANCE_MODES.filter((mode) =>
    mode === "native" || (usdValue != null && (mode === "usd" || reading.btc_price_usd > 0)));
}

function paintBalance(reading, unit) {
  lastPainted = reading ? { reading, unit } : null;
  if (!reading) { view.balance.textContent = "—"; return; }
  const modes = balanceModes(reading);
  const mode = modes.includes(balanceMode) ? balanceMode : modes.includes("usd") ? "usd" : "native";
  view.balance.dataset.mode = mode;
  view.balance.title = modes.length > 1 ? "Tap to switch unit" : "";
  if (mode === "usd") {
    const { currency, integer, fraction } = usdParts(reading.native_usd_value);
    view.balance.innerHTML =
      `<span class="unit-mark">${currency}</span>${integer}<span class="cents">${fraction}</span>`;
    return;
  }
  if (mode === "btc") {
    const btc = reading.native_usd_value / reading.btc_price_usd;
    view.balance.innerHTML = `${formatToken(btc)}<span class="cents"> BTC</span>`;
    return;
  }
  view.balance.innerHTML = `${formatToken(reading.native_balance)}<span class="cents"> ${unit}</span>`;
}

function cycleBalanceMode() {
  if (!lastPainted) return;
  const modes = balanceModes(lastPainted.reading);
  if (modes.length < 2) return;
  const current = modes.indexOf(view.balance.dataset.mode);
  balanceMode = modes[(current + 1) % modes.length];
  try { localStorage.setItem(BALANCE_MODE_KEY, balanceMode); } catch { /* solo per questa visita */ }
  paintBalance(lastPainted.reading, lastPainted.unit);
}

view.balance.setAttribute("role", "button");
view.balance.tabIndex = 0;
view.balance.addEventListener("click", cycleBalanceMode);
view.balance.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  cycleBalanceMode();
});

async function selectChain(next) {
  if (next === state.chain) return;
  state.chain = next;
  state.balance = null;
  // Il saldo e l'indirizzo hanno un view-transition-name: il browser li
  // interpola da una chain all'altra invece di farli sparire e riapparire.
  const swap = () => paintChainStatic();
  if (document.startViewTransition) await document.startViewTransition(swap).updateCallbackDone;
  else swap();
  resetForChainSwitch(); // il token in vista non appartiene piu' alla chain nuova
  presetToken = null;
  loadChainData();
}

/* ------------------------------------------------------------------- dati */

function loadChainData() {
  // Trading off (07/10): no balance, holdings or chart to read — the reads
  // failed for accounts with no wallet and retried every 5 s for ever.
  if (!TRADING) return;
  if (view.empty.hidden === false) return;  // nessun wallet: niente da chiedere
  refreshBalance();
  refreshStatus();
  if (TRADING) {
    mountChart(view.marketPanel);
    mountOrderTab(currentOrderTab);
    mountBottomTab(currentBottomTab);
  }
  paintHoldings(true);
}

function paintHoldings(force = false) {
  if (!TRADING) return;   // no holdings to read with trading off (16/10 review)
  refreshHoldings(view.holdings, {
    force,
    // Il tocco su una moneta apre lo scambio con quella in vendita.
    onPick: TRADING ? (holding) => {
      setView("manual");
      if (currentOrderTab !== "swap") $('[data-order-tab="swap"]')?.click();
      window.dispatchEvent(new CustomEvent("onchain:swap-from", { detail: holding }));
    } : undefined,
  });
}

let balanceRetry = null;
let balanceTries = 0;

async function refreshBalance() {
  clearTimeout(balanceRetry);
  const chain = state.chain;
  try {
    const reading = await api.getBalance(chain);
    if (chain !== state.chain) return;  // l'utente ha cambiato chain nel frattempo
    state.balance = reading;
    balanceTries = 0;
    writeCache(chain, reading);
    paintBalance(reading, chainInfo().unit);
    view.liveDot.classList.add("is-live");
    view.fresh.textContent = "updated just now";
    drawSparkline(view.spark, appendHistory(chain, reading.native_usd_value ?? reading.native_balance), sparkFormatter());
  } catch (error) {
    if (chain !== state.chain) return;
    view.fresh.textContent = `${error.message} — retrying`;
    // Not every 5 s for ever: a missing wallet (404) never comes back by itself.
    balanceTries += 1;
    if (balanceTries < 6) balanceRetry = setTimeout(refreshBalance, 5000 * 2 ** (balanceTries - 1));
  }
}

// Una riga sola, e dice la cosa che puo' cambiare: se l'esecuzione reale e'
// armata. E' lo stesso interruttore che il backend legge prima di inviare
// qualunque transazione, non un'etichetta decorativa.
async function refreshStatus() {
  const chain = state.chain;
  try {
    const risk = await api.getRiskStatus(chain);
    if (chain !== state.chain) return;
    view.status.dataset.armed = String(Boolean(risk.execution_enabled));
    if (view.statusSub) {
      view.statusText.textContent = risk.execution_enabled ? "Live execution on" : "Live execution off";
      view.statusSub.textContent = risk.execution_enabled
        ? `Up to ${formatUsd(risk.per_trade_cap_usd)} per order · ${formatUsd(risk.daily_cap_usd)} per day`
        : "Quotes only · no auto-signing";
    } else {
      view.statusText.textContent = risk.execution_enabled
        ? `Live execution on — up to ${formatUsd(risk.per_trade_cap_usd)} per order, ${formatUsd(risk.daily_cap_usd)} per day.`
        : "Read-only — nothing gets signed from this page.";
    }
  } catch { /* resta la riga di default, che e' quella prudente */ }
}

/* --------------------------------------------------------- pannello ordine */
// Swap e Limite condividono lo stesso spazio, sempre visibile — due tab,
// non due bottoni che aprono due sheet diverse.

let currentOrderTab = "swap";

// Un token si sceglie una volta sola: quello scelto sul grafico diventa
// l'altra gamba di swap e limite, e quello scelto nel pannello ordine
// sposta il grafico. Prima erano due scelte separate, e da telefono il
// pannello ordine sta due schermate sotto il grafico — Richiesta: "se
// seleziono un token si aprono troppe schermate".
let presetToken = null;
let presetSeq = 0;
const tokenInfoCache = new Map();

async function resolvePreset(token) {
  const key = `${state.chain}:${token.address.toLowerCase()}`;
  if (!tokenInfoCache.has(key)) {
    const info = await api.getTokenInfo(state.chain, token.address);
    tokenInfoCache.set(key, {
      address: token.address,
      decimals: info.decimals,
      symbol: info.symbol || token.symbolHint || shortAddress(token.address),
      priceUsd: info.price_usd ?? null,
    });
  }
  return tokenInfoCache.get(key);
}

onTokenChanged(async (token) => {
  const seq = ++presetSeq;
  presetToken = null;
  if (token && !sheets.isNativeAddress(state.chain, token.address)) {
    try {
      presetToken = await resolvePreset(token);
    } catch (error) {
      toast("Token unverified", error.message);
    }
  }
  if (seq !== presetSeq) return;
  mountOrderTab(currentOrderTab);
});

const followInChart = (token) => {
  presetToken = token;
  setChartToken({ address: token.address, symbolHint: token.symbol });
};

function mountOrderTab(tab) {
  currentOrderTab = tab;
  $$("#order-tabs .mo-side-tab").forEach((t) => {
    const active = t.dataset.orderTab === tab;
    t.classList.toggle("mo-tab-active", active);
    t.setAttribute("aria-selected", String(active));
  });
  if (tab === "swap") {
    mountSwap(view.orderPanelBody, {
      presetToken,
      onTokenPicked: followInChart,
      onExecuted: () => { refreshBalance(); mountBottomTab(currentBottomTab); toast("Swap sent", "check the signature in history"); },
    });
  } else {
    mountLimitOrder(view.orderPanelBody, {
      presetToken,
      onTokenPicked: followInChart,
      onPlaced: () => { mountBottomTab(currentBottomTab); toast("Limit order placed", "it's waiting in history"); },
    });
  }
}

$$("#order-tabs .mo-side-tab").forEach((tab) => {
  tab.addEventListener("click", () => mountOrderTab(tab.dataset.orderTab));
});

/* -------------------------------------------------- pannello inferiore */
// Posizioni / Ordini aperti / Storico / Strategie: "cosa ho, cosa ho
// ordinato, cosa e' successo" in un colpo d'occhio, non tre pannelli
// separati da riaprire ogni volta.

let currentBottomTab = "positions";

function mountBottomTab(tab) {
  currentBottomTab = tab;
  $$("#bottom-tabs .mo-side-tab").forEach((t) => {
    const active = t.dataset.bottomTab === tab;
    t.classList.toggle("mo-tab-active", active);
    t.setAttribute("aria-selected", String(active));
  });
  if (!TRADING) return;
  const mounters = {
    positions: () => import("@onchain/portfolio.js").then((m) => m.mountPortfolio),
    orders: async () => mountOpenOrders,
    history: async () => mountHistory,
    strategies: () => import("@onchain/strategies.js").then((m) => m.mountStrategies),
  };
  mounters[tab]?.().then((mount) => { if (currentBottomTab === tab) mount(view.bottomPanelBody); });
}

$$("#bottom-tabs .mo-side-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const name = tab.dataset.bottomTab;
    mountBottomTab(name);
  });
});

/* ------------------------------------------------------------------ toast */

let toastTimer = null;

function toast(title, detail) {
  clearTimeout(toastTimer);
  view.toast.querySelector(".toast-title").textContent = title;
  view.toast.querySelector(".toast-detail").textContent = detail;
  view.toast.hidden = false;
  toastTimer = setTimeout(() => { view.toast.hidden = true; }, 6000);
}

/* ---------------------------------------------------------------- comandi */

$$("[data-chain]").forEach((tab) => {
  tab.addEventListener("click", () => {
    $$("[data-chain]").forEach((other) =>
      other.setAttribute("aria-selected", String(other === tab)));
    $("#chain-switch").dataset.selected = tab.dataset.chain;
    selectChain(tab.dataset.chain);
  });
});

view.address.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  await navigator.clipboard?.writeText(button.dataset.full ?? "");
  toast("Address copied", shortAddress(button.dataset.full ?? ""));
});

const SHEETS = {
  receive: () => sheets.openReceive(),
  send: () => import("@onchain/send.js").then(({ openSend }) => openSend({
    onSent: () => { refreshBalance(); paintHoldings(true); mountBottomTab(currentBottomTab); toast("Sent", "check the signature in history"); },
  })),
  risk: () => sheets.openRisk(() => { refreshStatus(); mountBottomTab(currentBottomTab); }),
  simulate: () => sheets.openSimulate({
    onAccepted: () => { mountBottomTab(currentBottomTab); refreshStatus(); toast("Simulation accepted", "logged to the ledger"); },
  }),
};
$$("[data-sheet]").forEach((button) =>
  button.addEventListener("click", () => SHEETS[button.dataset.sheet]?.()));
// Buttons drawn later (the profile's "+") ask for a sheet by event.
document.addEventListener("lae:sheet", (event) => SHEETS[event.detail]?.());

view.reveal.addEventListener("click", () => sheets.openKey({ onStart: startReveal }));

// Menu "⋯" (solo sulla pagina a se': la copia nella tab Trading non ce
// l'ha, da qui i ?.): si chiude da solo sul tocco di una voce (la voce apre il suo
// foglio) o fuori dal pannello.
// Your picture in the header opens your profile; the wallet menu is its "…".
view.more?.addEventListener("click", () => setView("profile"));
document.addEventListener("lae:wallet-menu", () => {
  if (view.moreSheet?.querySelector("#actions")?.hidden) return;   // no wallet: nothing to show
  view.moreSheet?.showModal();
});

// Two sections chosen at the door, each with its own purpose: Progetti
// (a round-the-clock scan of serious low/micro caps, ranked) and Meme
// (the sniper radar plus its autopilot). Then Scambia and Portafoglio.
// The home page picks the section (#gems or #meme); that is the first view.
// Lorenzo, 07/10: "non voglio piu' vedere strategie automatiche [...] questa
// parte di trading deve sparire". Signals, the pilot, swaps and
// limit orders leave the app; <html data-trading="on"> brings them back,
// together with onchain_trading_enabled on the server.
// Lorenzo, 16/10: Pearl right after Gems, Top (the 25 best by score) before Scout.
// Lorenzo, 21/10: Quality after Top, whitekobra's only (quality.js shows its button).
const VIEWS = TRADING ? ["meme", "gems", "pearl", "top", "rank", "quality", "agent", "profile", "wallet", "manual"] : ["gems", "pearl", "top", "rank", "quality", "agent", "profile", "wallet"];
const DOCK = TRADING ? ["meme", "gems", "pearl", "top", "rank", "quality", "agent", "profile"] : ["gems", "pearl", "top", "rank", "quality", "agent", "profile"];   // the wallet lives in the profile

// Resolves once the new view is painted (after the transition's update).
// `instant` skips the transition: a field focused right after must be on
// screen within the tap, or phones don't open the keyboard.
function setView(name, { instant = false } = {}) {
  if (!VIEWS.includes(name)) return Promise.resolve();
  let painted = Promise.resolve();
  const from = view.shell.dataset.view;
  const paint = () => {
    view.shell.dataset.view = name;
    if (name === "gems" || name === "meme") view.shell.dataset.section = document.documentElement.dataset.section = name;
    view.dock?.querySelectorAll("[data-go]").forEach((b) => {
      if (b.dataset.go === name) b.setAttribute("aria-current", "page");
      else b.removeAttribute("aria-current");
    });
    if (view.dock) view.dock.dataset.at = String(DOCK.indexOf(name));
    document.querySelectorAll(".tabs[data-tabs]").forEach((nav) => { nav.hidden = nav.dataset.tabs !== name; });
    window.scrollTo({ top: 0 });
  };
  if (!instant && from !== name && document.startViewTransition && !document.querySelector("dialog[open]")
      && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    view.shell.dataset.dir = VIEWS.indexOf(name) > VIEWS.indexOf(from) ? "fwd" : "back";
    painted = document.startViewTransition(paint).updateCallbackDone.catch(() => {});
  } else paint();
  if (name === "profile") refreshProfile();
  if (name === "wallet" && !view.bottomPanel.hidden) mountBottomTab(currentBottomTab);
  paintHoldings();
  deskView(name);
  return painted;
}
// One app: a floating bar at the bottom on every screen, the search button
// beside it, the balance in the header next to your avatar.
const dockSearch = document.getElementById("dock-search");
function placeDock() {
  if (!view.dock) return;
  document.body.append(view.dock);
  if (dockSearch) document.body.append(dockSearch);
}
placeDock();
// The header shows everything, every chain, every token (Lorenzo: "il
// wallet deve essere multi-chain e devo visualizzare il saldo a
// prescindere da quale token e in quale chain ho"). The per-chain native
// balance stays in the wallet view, where the chain switch is.
const totalEl = document.createElement("button");
totalEl.type = "button";
totalEl.className = "amount total-bal";
totalEl.setAttribute("aria-label", "Total balance, all chains");
totalEl.textContent = "—";
document.querySelector("[data-balance-slot]")?.prepend(totalEl);
totalEl.addEventListener("click", () => setView("profile"));
// The live price moves it between readings (live.js), as in the profile.
let shownTotal = null;
let totalNow = null;
function paintTotal(t) {
  totalNow = t;
  if (t.total == null) { totalEl.textContent = t.wallet === "sim" ? "SIM —" : "$0.00"; shownTotal = null; return; }
  // a chain that did not answer is not an empty one: no false $0
  if (!t.complete && t.missing?.length && !t.total) { totalEl.textContent = "$—"; shownTotal = null; }
  else {
    const total = t.total + liveDelta(t.live);
    const [i, d] = total.toFixed(2).split(".");
    if (!totalEl.querySelector("[data-tw]")) {
      totalEl.innerHTML = `<span data-tw></span><span class="cents" data-tc></span><span class="cents" data-tp></span>`;
    }
    roll(totalEl.querySelector("[data-tw]"), `$${Number(i).toLocaleString("en-US")}`);
    roll(totalEl.querySelector("[data-tc]"), `.${d}`);
    totalEl.querySelector("[data-tp]").textContent = t.complete === false ? "*" : "";
    if (shownTotal != null && Math.abs(total - shownTotal) >= 0.005) flash(totalEl, total > shownTotal ? "up" : "down");
    shownTotal = total;
  }
  totalEl.title = Object.entries(t.by_chain ?? {}).map(([c, v]) => `${c}: $${v.toFixed(2)}`).join(" · ")
    + (t.missing?.length ? ` · not read: ${t.missing.join(", ")}` : "");
}

// Same guard as the profile: an answer that arrives after a newer switch is
// dropped, and the last total of each mode is shown at once on the switch.
const totalByMode = { real: null, sim: null };
let totalSeq = 0;
async function refreshTotal() {
  if (!TRADING) return;   // no wallet total on top with trading off (16/10 review)
  const mode = api.walletMode();
  const seq = ++totalSeq;
  try {
    const t = await api.getWalletsTotal();
    if (seq !== totalSeq || mode !== api.walletMode()) return;
    totalByMode[mode] = t;
    totalEl.dataset.wallet = t.wallet === "sim" ? "sim" : "real";
    paintTotal(t);
  } catch { /* keep the last number */ }
}
refreshTotal();
watch({
  keys: () => (totalNow?.live ?? []).filter((p) => !p.hidden).map(liveKey).filter(Boolean),
  active: () => Boolean(totalNow?.live?.length),
  onPrices: () => { if (totalNow) paintTotal(totalNow); },
});
document.addEventListener("lae:wallet-mode", () => {
  shownTotal = null;
  const t = totalByMode[api.walletMode()];
  if (t) { totalEl.dataset.wallet = t.wallet === "sim" ? "sim" : "real"; paintTotal(t); }
  refreshTotal();
});
setInterval(() => { if (document.visibilityState === "visible") refreshTotal(); }, 60_000);

/** Tabs inside a view: panels carry data-pane="<view>:<tab>". */
function setTab(viewName, tab) {
  const nav = document.querySelector(`.tabs[data-tabs="${viewName}"]`);
  if (!nav) return;
  nav.querySelectorAll("[data-tab]").forEach((b) => {
    if (b.dataset.tab === tab) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  document.querySelectorAll(`[data-pane^="${viewName}:"]`).forEach((pane) => {
    pane.classList.toggle("pane-off", pane.dataset.pane !== `${viewName}:${tab}`);
  });
}
document.querySelectorAll(".tabs[data-tabs]").forEach((nav) => {
  setTab(nav.dataset.tabs, nav.querySelector("[aria-current]")?.dataset.tab ?? nav.querySelector("[data-tab]").dataset.tab);
  nav.addEventListener("click", (event) => {
    const b = event.target.closest("[data-tab]");
    if (b) { setTab(nav.dataset.tabs, b.dataset.tab); window.scrollTo({ top: 0 }); }
  });
});
{
  const hash = location.hash.slice(1).split("&")[0];
  const first = VIEWS.includes(hash) ? hash
    : !TRADING || (document.documentElement.dataset.section === "gems" && /gem/i.test(hash)) ? "gems" : "meme";
  view.shell.dataset.view = first;  // same view on both sides: no transition on load
  setView(first);
}
// Search: straight to the swap with the token picker open.
dockSearch?.addEventListener("click", () => {
  // Without trading the lens is the scanner: a ticker or an address.
  if (!TRADING) {
    const input = document.querySelector("#gem-scan input");
    input?.removeAttribute("readonly");
    setView("gems", { instant: true });
    input?.focus();
    return;
  }
  setView("manual");
  requestAnimationFrame(() => document.getElementById("swap-pick-out")?.click());
});
document.getElementById("inbox-btn")?.addEventListener("click", () => openInbox());
// Buy from a token page: the swap opens with that token as the one you get.
document.addEventListener("lae:buy", (event) => {
  const { address, symbol } = event.detail ?? {};
  if (!address || !TRADING) return;
  setView("manual");
  setChartToken({ address, symbolHint: symbol });
});

for (const el of [view.dock, view.shell]) {
  el?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-go]");
    if (button) setView(button.dataset.go);
  });
}

document.addEventListener("lae:go", (event) => setView(event.detail));

// Lorenzo, 01/10: the scan box opened the phone keyboard as the app started.
// It stays readonly (no keyboard) until a real tap or keystroke on it, and
// goes back to readonly when it loses focus.
const SCAN_INPUT = "[data-scan-form] input";
const unlockScan = (event) => event.target.closest?.(SCAN_INPUT)?.removeAttribute("readonly");
document.addEventListener("pointerdown", unlockScan, true);
document.addEventListener("keydown", (event) => { if (event.key !== "Tab") unlockScan(event); }, true);
document.addEventListener("focusout", (event) => event.target.closest?.(SCAN_INPUT)?.setAttribute("readonly", ""), true);

mountAgentView();
mountLeaderboard();
mountProjects();
if (TRADING) {
  mountAlerts();
}
mountProfile({ go: (v) => setView(v) });
loadLinked();
// Back from Phantom (phantomlink.js): its answer is in this page's URL.
phantom.takeAnswer().then(async (ans) => {
  if (!ans || await phantomAnswer(ans)) return;
  if (ans.error) { toast("Phantom", ans.error); return; }
  if (ans.op === "connect") { toast("Phantom connected", "tap Buy or Sell again to sign"); return; }
  if (ans.op === "signAndSendTransaction") {
    toast(`${ans.pending?.symbol || "Swap"} sent`, `signature ${ans.data.signature.slice(0, 8)}… on Solscan`);
    refreshProfile();
  }
});
// Picks (memes.js) retired: Lorenzo wants no meme coins promoted; Top replaces it.
mountAgent();
mountAsk();
mountTop();
mountQuality();
// Lorenzo, 30/09: the meme screens and the backtest hall of fame are gone.
// The "meme" view now holds Signals, the "top" view the Early list (07/10;
// the Track record folds under the profile). The view names stay: the home
// page links, the splash and the desk use them.
if (TRADING) import("@onchain/signals.js").then((m) => m.mountSignals());
mountTrack();   // the picks' track record (gem_track), not a backtest
// The scanner, in Gems now that Signals is gone (it lived there).
document.getElementById("gem-scan")?.addEventListener("submit", (event) => {
  event.preventDefault();
  const q = event.target.q.value.trim();
  if (q) sheets.openScan(q);
});
// Desktop: the start view opens its first token once the lists are in.
setTimeout(openFirst, 2500);

// La rete si cambia dal suo nome, accanto al saldo: un tocco, niente menu.
view.chainFlip?.addEventListener("click", () => {
  view.chainFlip.classList.remove("is-flipping");
  void view.chainFlip.offsetWidth;
  view.chainFlip.classList.add("is-flipping");
  $('#chain-switch button[aria-selected="false"]')?.click();
});
view.moreSheet?.addEventListener("click", (event) => {
  const go = event.target.closest("[data-go]");
  if (go) setView(go.dataset.go);
  if (event.target === view.moreSheet || event.target.closest("button")) view.moreSheet.close();
});

view.empty.querySelector("[data-create]").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  try {
    const wallet = await api.createWallet(state.chain);
    state.wallets[state.chain] = wallet;
    paintChainStatic();
    loadChainData();
    toast("Wallet created", shortAddress(wallet.address));
  } catch (error) {
    toast("Not created", error.message);
  } finally {
    button.disabled = false;
  }
});

view.toast.querySelector(".toast-close").addEventListener("click", () => { view.toast.hidden = true; });

/* ---------------------------------------------------------------- sessione */

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const message = $("#login-error");
  const button = form.querySelector("button");
  button.disabled = true;
  message.hidden = true;
  try {
    const fields = new FormData(form);
    await api.login(String(fields.get("email")).trim(), String(fields.get("password")));
    // The server picks the app version by account (onchain_v1_emails):
    // reload so the page served is the one for who just signed in.
    location.reload();
  } catch (error) {
    message.textContent = error.message;
    message.hidden = false;
    button.disabled = false;
  }
});

// Sessione e wallet che il server ha gia' messo nell'HTML (onchain-app.html):
// due richieste in fila risparmiate. Si usa una volta sola — dopo un login
// o dentro index.html, che non lo porta, si torna a chiederli.
function takeBootData() {
  const node = document.getElementById("onchain-boot");
  if (!node) return null;
  node.remove();
  try { return JSON.parse(node.textContent); } catch { return null; }
}

async function boot() {
  const preloaded = takeBootData();
  let signedIn = false;
  if (preloaded) signedIn = Boolean(preloaded.user);
  else try { signedIn = Boolean((await api.getSession())?.user); } catch { /* offline: si tratta come non loggato */ }

  view.login.hidden = signedIn;
  view.shell.hidden = !signedIn;
  if (view.dock) view.dock.hidden = !signedIn;
  if (dockSearch) dockSearch.hidden = !signedIn;
  if (!signedIn) return;

  try {
    const wallets = preloaded?.wallets ?? await api.listWallets();
    for (const wallet of wallets) state.wallets[wallet.chain] = wallet;
  } catch { /* al primo carico senza rete resta la cache locale, se c'e' */ }

  paintChainStatic();
  loadChainData();
  // A finished task's notification (bg.js) puts you back where it started;
  // otherwise a shared or Telegram link to a token opens it once signed in,
  // so the destination survives the login screen.
  if (!(await bg.boot())) openFromHash();
}

boot();

// A tab left open on a phone keeps the version it was opened with: Lorenzo
// sent a screenshot of the old app hours after the new one was live. When
// the app comes back to the screen (and every 5 minutes) it asks the server
// which version it serves; if it changed, one reload, once per version.
const MY_VERSION = new URL(import.meta.url).searchParams.get("v") ?? "";
async function checkVersion() {
  if (!MY_VERSION) return;
  try {
    const r = await fetch("/api/version", { cache: "no-store" });
    if (!r.ok) return;
    const { asset_version: live } = await r.json();
    if (!live || live === MY_VERSION) return;
    const key = `lae.reloaded.${live}`;
    try { if (sessionStorage.getItem(key)) return; sessionStorage.setItem(key, "1"); } catch { /* reload anyway */ }
    location.reload();
  } catch { /* offline: the page we have beats no page */ }
}
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") checkVersion(); });
window.addEventListener("pageshow", (event) => { if (event.persisted) checkVersion(); });
setInterval(() => { if (document.visibilityState === "visible") checkVersion(); }, 5 * 60_000);
