/**
 * I pannelli che salgono dal basso, su <dialog> nativo.
 *
 * Il browser porta gia' quello che una sheet fatta a mano deve reimplementare
 * male: top-layer (niente z-index da rincorrere), ::backdrop, trappola del
 * focus, chiusura con Escape, e il resto della pagina reso inerte. L'entrata
 * e l'uscita sono CSS (@starting-style + transition-behavior: allow-discrete),
 * non timer JS.
 *
 * Il contenuto si carica all'apertura, mai prima: tetti, transazioni e
 * posizioni cambiano, e una sheet riempita al caricamento della pagina
 * mostrerebbe lo stato di quando la pagina e' stata aperta.
 */
import * as api from "@onchain/api.js";
import { age, escapeHtml, formatToken, formatUsd, shortAddress, tile } from "@onchain/format.js";
import { chainInfo, state } from "@onchain/store.js";
import { scoutCube } from "@onchain/scout-cube.js";
import * as bg from "@onchain/bg.js";

// Stesso indirizzo nativo duplicato in swap.js/limitOrders.js: qui serve
// solo per proporre il nativo come "token che hai" nel picker, non per
// firmare niente.
const NATIVE_ADDRESS = {
  solana: "So11111111111111111111111111111111111111112",
  robinhood: "0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73",
};

const dialog = document.querySelector("#sheet");
const titleEl = dialog.querySelector(".sheet-title");
const descEl = dialog.querySelector(".sheet-desc");
const bodyEl = dialog.querySelector(".sheet-body");

// Sul backdrop di un <dialog> il click ha come target il dialog stesso:
// e' il modo standard di distinguerlo da un click sul contenuto.
dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
dialog.querySelector(".sheet-close").addEventListener("click", () => dialog.close());

export function openSheet(title, description) {
  titleEl.textContent = title;
  descEl.textContent = description;
  bodyEl.replaceChildren();
  dialog.classList.remove("dep-has-back");
  if (!dialog.open) dialog.showModal();
}
const open = openSheet;

export const closeSheet = () => dialog.close();
export const sheetBody = () => bodyEl;

const html = (markup) => {
  const template = document.createElement("template");
  template.innerHTML = markup.trim();
  return template.content;
};

export const setBody = (markup) => bodyEl.replaceChildren(html(markup));
export const setMessage = (text, tone = "") =>
  setBody(`<p class="sheet-note ${tone}">${escapeHtml(text)}</p>`);

/* ----------------------------------------------------------- Manual scan */

// Lorenzo, 27/09: a ticker or an address through the whole process, by
// hand: DexScreener, the checks, the rug memory, DeepSeek (manual_scan.py).
const pctS = (f) => (f == null ? "—" : `${f > 0 ? "+" : ""}${Math.round(f * 100)}%`);
const usdS = (n) => (n == null ? "—" : n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${Math.round(n / 1e3)}k` : `$${Math.round(n)}`);

function scanning(query) {
  open(`Scanning ${query}`, "Scout checks market data, security, the project site and previous risk signals.");
  setBody(`<div class="scan-live"><div class="scan-live-head"><span class="agent-orb scout-cube" aria-hidden="true">${scoutCube}</span>
    <p>Scout is examining <b>${escapeHtml(query)}</b></p></div><ol class="scan-steps"></ol></div>`);
  return bodyEl.querySelector(".scan-steps");
}

// The scan is a job on the server (bg.js): it goes on if the app is closed,
// and its push reopens this sheet with the result (Lorenzo, 01/10).
export async function openScan(query) {
  bg.askPush();
  const list = scanning(query);
  const t0 = performance.now();
  const view = bg.here("&scan=1");
  let d, id = null;
  try {
    d = await api.streamScan(query, (ev) => scanStep(list, ev),
      { view, onId: (x) => { id = x; bg.follow(x, "scan", { view, label: query }); } });
  } catch (err) {
    if (id) bg.settle(id);
    setMessage(err.message ?? "Scan failed.", "is-warn");
    return;
  }
  if (id) bg.settle(id);
  await showScan(d, list, ((performance.now() - t0) / 1000).toFixed(1));
}

bg.handle("scan", {
  show(job, meta) {
    const list = scanning(meta.label || job.title || "token");
    for (const ev of job.result?.steps ?? []) scanStep(list, ev);
    if (job.state !== "finito") { setMessage(job.error || "Scan failed.", "is-warn"); return; }
    showScan(job.result, list, job.elapsed_s != null ? String(job.elapsed_s) : "");
  },
  pending(meta) {
    const list = scanning(meta.label || "token");
    scanStep(list, { reconnecting: true });
  },
});

async function showScan(d, list, took) {
  const ran = list.querySelectorAll('li:not([data-state="skip"]):not([data-state="wait"])').length;
  const [{ gemWhy }] = await Promise.all([import("@onchain/leaderboard.js"), new Promise((r) => setTimeout(r, 450))]);
  if (d.error) { setMessage(d.error, "is-warn"); return; }
  const t = d.token;
  titleEl.textContent = `${t.symbol} · ${t.chain}`;
  // A project is judged by the Gem Finder, a meme by the listing filter
  // (Lorenzo, 29/09: the scanner had not followed the updates).
  const g = d.gem, ab = d.about ?? {};
  const stepsDone = list.innerHTML;
  const status = g ? gemStatus(g) : { ok: ["pass", "Would pass the listing filter"], fail: ["fail", `Would be rejected: ${d.pipeline.reason}`],
    wait: ["wait", `Waiting: ${d.pipeline.reason}`] }[d.pipeline.status] ?? ["wait", d.pipeline.reason];
  const ai = d.ai;
  const hist = (d.memory.history ?? []).map((h) => `${escapeHtml(h.decision ?? "seen")}${h.outcome ? ` → ${escapeHtml(h.outcome)}` : ""}`).join(", ");
  setBody(`
    <div class="scan-head">${tile(t.symbol, t.image, t.chain, t.token_address)}
      <div><b>${escapeHtml(t.name || t.symbol)}</b><small>${escapeHtml(ab.summary || `${t.dex || ""} pool`)}</small></div></div>
    <dl class="scan-facts">
      <div><dt>Cap</dt><dd>${usdS(t.market_cap)}</dd></div>
      <div><dt>Liquidity</dt><dd>${usdS(t.liquidity_usd)}</dd></div>
      <div><dt>Volume 24h</dt><dd>${usdS(t.volume_24h)}</dd></div>
      <div><dt>24h</dt><dd data-s="${(t.change_24h ?? 0) >= 0 ? "up" : "down"}">${t.change_24h == null ? "—" : `${t.change_24h > 0 ? "+" : ""}${t.change_24h}%`}</dd></div>
      <div><dt>Age</dt><dd>${t.created_at ? age(t.created_at)[0] : "—"}</dd></div>
      <div><dt>Holders</dt><dd>${ab.holders != null ? Number(ab.holders).toLocaleString("en-US") : "—"}${ab.top10_pct != null ? ` <small>top 10 ${Math.round(ab.top10_pct)}%</small>` : ""}</dd></div>
    </dl>
    ${ab.socials?.length || /^https:\/\//.test(t.website ?? "") ? `<p class="scan-socials">${/^https:\/\//.test(t.website ?? "") ? `<a href="${escapeHtml(t.website)}" target="_blank" rel="noopener">Website</a>` : ""}${(ab.socials ?? []).map((x) => `<a href="${escapeHtml(x.url)}" target="_blank" rel="noopener">${escapeHtml(x.type || "link")}</a>`).join("")}</p>` : ""}
    <p class="scan-status" data-s="${status[0]}">${escapeHtml(status[1])}</p>
    ${ai ? `<div class="scan-ai" data-risk="${ai.risk >= 60 ? "high" : ai.risk >= 30 ? "mid" : "low"}"><b>${ai.risk}</b>
      <span><b>Scout rug risk</b><small>${escapeHtml([ai.theme, ...(ai.flags ?? [])].filter(Boolean).join(" · ") || "no red flags")}</small></span></div>`
      : `<p class="sheet-note">Scout's AI assessment is unavailable right now.</p>`}
    ${d.scout ? `<div class="scan-scout">${gemWhy(d.scout)}${unlockBlock(d.scout.unlocks)}${recheckBlock(d.scout.recheck)}</div>` : g ? gemCard(g) : ""}
    ${btCard(d.backtest)}
    <p class="sheet-note"><b>Memory:</b> ${escapeHtml(d.memory.summary)}${hist ? ` · this token before: ${hist}` : ""}</p>
    ${d.alert ? `<p class="sheet-note">Alerted ${new Date(d.alert.at * 1000).toLocaleDateString("en-US", { month: "short", day: "numeric" })}, now ${pctS(d.alert.now)}.</p>` : ""}
    <ul class="scan-checks">${(d.checks ?? []).map((c) => `<li data-ok="${c.ok === true ? "yes" : c.ok === false ? "no" : "unknown"}">
      <span>${escapeHtml(c.label)}</span><small>${escapeHtml(c.detail ?? "")}</small></li>`).join("")}</ul>
    <details class="scan-trail"><summary>Scout ran ${ran} checks${took ? ` in ${took}s` : ""}</summary><ol class="scan-steps is-done">${stepsDone}</ol></details>
    <div class="scan-links">${g && !g.added && (g.status === "unknown" || g.status === "rejected" || g.status === "studied") ? `<button type="button" class="btn-quiet scan-add" data-add><svg viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/></svg><span>${g.status === "unknown" ? "Add to database" : "Study again"}</span></button>` : ""}
    <button type="button" class="btn-quiet" data-full>Full token page</button>
    ${t.pair_url ? `<a class="btn-quiet" href="${escapeHtml(t.pair_url)}" target="_blank" rel="noopener">DexScreener</a>` : ""}</div>`);
  bodyEl.animate?.([{ opacity: 0, transform: "translateY(8px)" }, { opacity: 1, transform: "none" }],
    { duration: 380, easing: "cubic-bezier(.2, .8, .2, 1)" });
  bodyEl.querySelector("[data-add]")?.addEventListener("click", async (ev) => {
    const btn = ev.currentTarget, label = btn.querySelector("span");
    btn.disabled = true;
    try {
      const [r] = await Promise.all([api.addScanned(t.chain, t.token_address),
        import("@onchain/particles.js").then((m) => m.absorb(bodyEl.querySelector(".scan-head"), btn))]);
      label.textContent = r.error ?? "Registered";
      btn.dataset.done = r.error ? "no" : "yes";
      if (!r.error) bodyEl.querySelector(".scan-status").replaceWith(Object.assign(document.createElement("p"),
        { className: "scan-status", textContent: "Gem Finder: queued for a full study", dataset: { s: "wait" } }));
    } catch (err) {
      label.textContent = err.message ?? "Couldn't add it";
      btn.disabled = false;
    }
  });
  bodyEl.querySelector("[data-full]")?.addEventListener("click", async () => {
    dialog.close();
    location.hash = `${location.hash.split("&")[0].slice(1) || (g ? "gems" : "meme")}&token=${encodeURIComponent(t.chain)}:${encodeURIComponent(t.token_address)}`;
    // The page gets what the scan read (name, pool, cap): without it a token
    // no list shows opened as "0xAA57" on a dead side pool (HYDX, 30/09).
    const detail = await import("@onchain/detail.js");
    detail.register(`${g ? "gem" : "alert:meme"}:${t.chain}:${t.token_address}`, {
      kind: g ? "gem" : "meme", chain: t.chain, token: t.token_address, symbol: t.symbol, name: t.name,
      pair: t.pair_address, pairUrl: t.pair_url, image: t.image, cap: t.market_cap,
      change: t.change_24h != null ? t.change_24h / 100 : null, ageTs: t.created_at,
    });
    detail.openFromHash();
  });
}

// Every step the scan really takes (manual_scan.STEPS), in the scout's words.
const STEP_LABEL = {
  pool: "Finding the pool on DexScreener", name: "Reading the name", security: "Security scan",
  contract: "Contract permissions", socials: "Social accounts", site: "Reading the project website",
  github: "Checking GitHub", ai: "DeepSeek reads the listing", holders: "Counting holders on GeckoTerminal",
  memory: "Comparing with past rugs", risk: "DeepSeek rates the rug risk", gem: "Looking up the Gem Finder",
  pillars: "Scoring research, GitHub and tokenomics", report: "Scout writes the report", code: "DeepSeek reads the code",
  recheck: "Final review of the red flags",
  backtest: "Backtesting the trend follower",
};

function scanStep(list, ev) {
  if (ev.reconnecting) {
    const note = document.createElement("li"); note.dataset.state = "wait";
    note.textContent = "Connection dropped. Scout is still working, collecting the result…";
    list.append(note); return;
  }
  if (ev.plan) {
    list.innerHTML = ev.plan.map((k, i) => `<li data-k="${k}" data-state="wait" style="--i:${i}">
      <i class="step-dot" aria-hidden="true"><b></b><s></s></i><span>${STEP_LABEL[k] ?? escapeHtml(k)}</span><small></small></li>`).join("");
    return;
  }
  const li = list.querySelector(`[data-k="${ev.step}"]`);
  if (!li) return;
  li.dataset.state = ev.state;
  if (ev.detail) li.querySelector("small").textContent = ev.detail;
  if (ev.state === "run") li.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
}

const VERDICT = { gem: "gem", watch: "watch", avoid: "avoid", scam: "scam" };
const pctN = (n) => (n == null ? "—" : `${n > 0 ? "+" : ""}${Math.round(n)}%`);

// The red points the second look could not confirm (scout_recheck.py):
// cleared ones and what it found, then the ones still unverified.
// Contracts holding the supply, read on chain (unlocks.py): lockers,
// vesting and their unlock dates.
function unlockBlock(u) {
  if (!u?.length) return "";
  const when = (x) => { const at = x.unlock_at ?? x.end; return at ? ` · ${new Date(at * 1000).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}` : ""; };
  return `<div class="ds-report"><h5>Supply in contracts</h5><ul class="why-list">
    ${u.map((x) => `<li data-tone="${x.kind === "contract" || x.kind === "unknown" ? "warn" : "good"}">${Number(x.pct).toFixed(1)}% ${escapeHtml(x.kind)}${when(x)}<small>${escapeHtml(x.note ?? "")}</small></li>`).join("")}</ul></div>`;
}

function recheckBlock(r) {
  if (!r || !(r.refuted?.length || r.unverified?.length || r.found?.length)) return "";
  const li = (tone, head, x) => `<li data-tone="${tone}">${head}${escapeHtml(x.text)}${x.note ? `<small>${escapeHtml(x.note)}</small>` : ""}</li>`;
  return `<div class="ds-report"><h5>Checked again</h5><ul class="why-list">
    ${(r.found ?? []).map((f) => `<li data-tone="good">${escapeHtml(f)}</li>`).join("")}
    ${(r.refuted ?? []).map((x) => li("good", "Cleared: ", x)).join("")}
    ${(r.unverified ?? []).map((x) => li("warn", "Not verified: ", x)).join("")}</ul></div>`;
}

function gemStatus(g) {
  if (g.added) return ["pass", `Gem Finder: added · score ${g.score} · the board studies it now`];
  if (g.status === "ranked") return ["pass", `Gem Finder: ranked #${g.rank} · score ${g.score}`];
  if (g.status === "unknown") return g.score == null ? ["wait", "Gem Finder: not studied yet"]
    : g.why ? ["wait", `Scout: would not rank yet · ${g.why}`] : ["pass", `Scout: would qualify · score ${g.score}`];
  if (g.status === "new" || g.status === "analyzing") return ["wait", "Gem Finder: queued for a full study"];
  if (g.status === "rejected") return ["fail", `Gem Finder: rejected · ${g.why || "rules"}`];
  return g.why ? ["wait", `Gem Finder: studied, not ranked · ${g.why}`] : ["pass", `Gem Finder: qualifies · score ${g.score}`];
}

function gemCard(g) {
  const pil = Object.entries(g.pillars ?? {}).filter(([, v]) => v != null);
  const j = g.judge, c = g.code;
  if (!pil.length && !j && !c) return "";
  return `<div class="scan-card">
    ${g.score != null ? `<b class="scan-big">${g.score}</b>` : ""}
    <div>${pil.map(([k, v]) => `<span class="scan-bar"><i style="--v:${v}%"></i><small>${escapeHtml(k)} ${v}</small></span>`).join("")}
    ${j ? `<small>DeepSeek: <b data-v="${VERDICT[j.verdict] ?? ""}">${escapeHtml(j.verdict)}</b> ${j.score ?? ""}${j.problems?.length ? ` · ${escapeHtml(j.problems[0])}` : j.strengths?.length ? ` · ${escapeHtml(j.strengths[0])}` : ""}</small>` : ""}
    ${c ? `<small>Code: complexity ${c.complexity} · innovation ${c.innovation}</small>` : ""}</div></div>`;
}

function btCard(b) {
  if (!b) return "";
  if (!b.fast && !b.daily) return `<p class="sheet-note">Backtest: ${escapeHtml(b.error || "no trade yet")}.</p>`;
  const row = (r, what) => `<li><span>${what}</span><b data-s="${(r.return_pct ?? 0) >= 0 ? "up" : "down"}">${pctN(r.return_pct)}</b>
    <small>${r.trades} trades${r.win_rate != null ? ` · ${Math.round(r.win_rate)}% win` : ""} · hold ${pctN(r.hold_pct)}</small></li>`;
  return `<ul class="scan-bt">${b.daily ? row(b.daily, `Trend follower · ${b.daily.interval === "1d" ? "daily" : b.daily.interval}`) : ""}
    ${b.fast ? row(b.fast, `${escapeHtml(b.fast.label)} · 5m`) : ""}</ul>`;
}

/* --------------------------------------------------------------- Deposit */

// Lorenzo, 27/09: "aggiungiamo queste possibilita' per i depositi" (a
// "Deposit with" sheet: Crypto / Debit / Exchanges and apps). One sheet,
// three steps, a back arrow between them; the data comes from
// /api/wallets/deposit (deposit.py) when it opens.
const CHAIN_ICON = (id) => `https://dd.dexscreener.com/ds-data/chains/${id === "bsc" ? "bsc" : id}.png`;
const BRAND = {
  coinbase: `<svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#0052ff"/><path d="M16 23.5a7.5 7.5 0 1 1 7.4-8.7h-4a3.7 3.7 0 1 0 0 2.4h4A7.5 7.5 0 0 1 16 23.5z" fill="#fff"/></svg>`,
  binance: `<svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#1e2026"/><path d="M16 7l2.6 2.6L16 12.2l-2.6-2.6zm-5.4 5.4l2.6 2.6-2.6 2.6L8 15zm10.8 0L24 15l-2.6 2.6-2.6-2.6zM16 12.4l2.6 2.6-2.6 2.6-2.6-2.6zm0 5.4l2.6 2.6L16 23l-2.6-2.6z" fill="#f0b90b"/></svg>`,
};
const ICONS = {
  qr: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h2v2h-2zM18 14h2v2h-2zM14 18h2v2h-2zM18 18h2v2h-2z"/></svg>`,
  card: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="6" width="18" height="12" rx="2.5"/><path d="M3 10h18M7 15h4"/></svg>`,
};
let deposit = null;

const depRow = (attrs, title, sub, icon) => `
  <button type="button" class="dep-row" ${attrs}>
    <span><b>${title}</b>${sub ? `<small>${sub}</small>` : ""}</span>
    <i class="dep-ico">${icon}</i>
  </button>`;

function depStep(title, desc, back, markup) {
  open(title, desc);
  setBody(`${back ? `<button type="button" class="dep-back" aria-label="Back">‹</button>` : ""}<div class="dep-list">${markup}</div>`);
  dialog.classList.toggle("dep-has-back", !!back);
  bodyEl.querySelector(".dep-back")?.addEventListener("click", back);
}

export async function openReceive() {
  open("Deposit with", "");
  setMessage("Loading…");
  try {
    deposit = await api.getDeposit();
  } catch (err) {
    setMessage(err.message ?? "Couldn't load deposit options.", "is-warn");
    return;
  }
  depositHome();
}

function depositHome() {
  const ex = deposit.exchanges;
  depStep("Deposit with", "", null,
    depRow("data-d=crypto", "Crypto", "Receive USDC from a crypto wallet", ICONS.qr)
    + depRow("data-d=debit", "Debit", "Deposit cash with a debit card", ICONS.card)
    + depRow("data-d=apps", "Exchanges and apps", ex.map((e) => e.label).join(", "),
      `<span class="dep-brands">${ex.map((e) => BRAND[e.id] ?? "").join("")}</span>`));
  bodyEl.querySelector("[data-d=crypto]").addEventListener("click", () => depositNetworks(null, depositHome));
  bodyEl.querySelector("[data-d=debit]").addEventListener("click", depositDebit);
  bodyEl.querySelector("[data-d=apps]").addEventListener("click", depositApps);
}

function depositNetworks(only, back, from = "") {
  const nets = only ? only.map((id) => deposit.networks.find((n) => n.id === id)).filter(Boolean) : deposit.networks;
  depStep(from ? `Deposit from ${from}` : "Deposit crypto",
    from ? `Withdraw USDC from ${from} on one of these networks.` : "Choose a network to deposit from.", back,
    nets.map((n, i) => depRow(`data-net="${n.id}"`, escapeHtml(n.label),
      from && i === 0 ? "cheapest" : "",
      `<img src="${CHAIN_ICON(n.id)}" alt="" width="26" height="26" onerror="this.replaceWith(Object.assign(document.createElement('b'),{textContent:'${escapeHtml(n.label[0])}'}))">`)).join(""));
  bodyEl.querySelectorAll("[data-net]").forEach((b) => b.addEventListener("click", () =>
    depositAddress(deposit.networks.find((n) => n.id === b.dataset.net), () => depositNetworks(only, back, from))));
}

function depositAddress(n, back) {
  if (!n.address) {
    depStep(`Deposit on ${n.label}`, "", back,
      `<p class="sheet-note is-warn">No ${n.kind === "solana" ? "Solana" : "EVM"} wallet on this account yet. Create one in Wallet, or connect yours from the profile.</p>`);
    return;
  }
  const use = n.use === "trades" ? "Counts in your balance and can be traded here."
    : "Counts in your balance; trading here runs on Solana and Robinhood Chain.";
  depStep(`Deposit on ${n.label}`, `Send USDC on ${n.label} only: anything sent from another network is gone.`, back, `
    <div class="dep-qr"><img src="${n.qr}" alt="QR code of the address" width="180" height="180"></div>
    <p class="address-block">${escapeHtml(n.address)}</p>
    <dl class="kv">
      <div><dt>Network</dt><dd>${escapeHtml(n.label)}</dd></div>
      <div><dt>Token</dt><dd>USDC${n.usdc ? ` <small>${escapeHtml(shortAddress(n.usdc))}</small>` : ""}</dd></div>
      <div><dt>Wallet</dt><dd>${n.source === "site" ? "this site's" : "your connected wallet"}</dd></div>
    </dl>
    <p class="sheet-note">${use}${n.id === "robinhood" && !n.usdc ? " USDC on Robinhood Chain isn't confirmed yet: send USDG or ETH." : ""}</p>
    <button type="button" class="btn-quiet" data-copy>Copy address</button>`);
  bodyEl.querySelector("[data-copy]").addEventListener("click", async (event) => {
    await navigator.clipboard?.writeText(n.address);
    event.currentTarget.textContent = "Copied";
  });
}

function depositApps() {
  depStep("Deposit", "Choose an exchange or app to deposit from.", depositHome,
    deposit.exchanges.map((e) => depRow(`data-ex="${e.id}"`, escapeHtml(e.label), "", BRAND[e.id] ?? "")).join(""));
  bodyEl.querySelectorAll("[data-ex]").forEach((b) => b.addEventListener("click", () => {
    const e = deposit.exchanges.find((x) => x.id === b.dataset.ex);
    depositNetworks(e.networks, depositApps, e.label);
    bodyEl.querySelector(".dep-list").insertAdjacentHTML("beforeend",
      `<a class="btn-quiet dep-open" href="${escapeHtml(e.url)}" target="_blank" rel="noopener">Open ${escapeHtml(e.label)}</a>`);
  }));
}

function depositDebit() {
  if (deposit.onramp) {
    window.open(deposit.onramp, "_blank", "noopener");
    return;
  }
  depStep("Debit card", "", depositHome,
    `<p class="sheet-note">Card deposits aren't switched on yet: they need an on-ramp account (MoonPay, Transak…) set up by the site. Meanwhile, buy USDC on an exchange and send it here.</p>`
    + depRow("data-d=apps", "Exchanges and apps", deposit.exchanges.map((e) => e.label).join(", "), ""));
  bodyEl.querySelector("[data-d=apps]").addEventListener("click", depositApps);
}

/* ---------------------------------------------------------------- Limiti */

export async function openRisk(onChange) {
  open("Limits & safety", "Caps apply to every order, simulated or live. The circuit breaker only re-arms manually.");
  setMessage("Loading status…");
  await renderRisk(onChange);
}

async function renderRisk(onChange) {
  try {
    const data = await api.getRiskStatus(state.chain);
    const breaker = data.circuit_breaker;
    const spentRatio = data.daily_cap_usd ? Math.min(1, data.daily_spent_usd / data.daily_cap_usd) : 0;

    setBody(`
      <dl class="kv">
        <div><dt>Per order</dt><dd>${formatUsd(data.per_trade_cap_usd)}</dd></div>
        <div><dt>Max concentration</dt><dd>${data.concentration_cap_pct}%</dd></div>
        <div><dt>Live execution</dt><dd>${data.execution_enabled ? "on" : "off"}</dd></div>
      </dl>

      <div class="meter" style="--fill:${(spentRatio * 100).toFixed(1)}%">
        <div class="meter-head"><span>Spent today</span>
          <b>${formatUsd(data.daily_spent_usd)} of ${formatUsd(data.daily_cap_usd)}</b></div>
        <div class="meter-track"><div class="meter-bar"></div></div>
      </div>

      <p class="breaker" data-tripped="${breaker.tripped}">
        <span class="breaker-dot"></span>
        ${breaker.tripped
          ? `Circuit breaker tripped — ${breaker.consecutive_losses} losses in a row`
          : "Circuit breaker idle"}
      </p>
      ${breaker.tripped ? '<button type="button" class="btn-quiet" data-reset>Re-arm manually</button>' : ""}

      <div class="switch-row">
        <span><b>Wallet active</b><small>when off it stays visible, but nothing touches it</small></span>
        <button type="button" class="switch" role="switch" data-toggle></button>
      </div>
    `);

    bodyEl.querySelector("[data-reset]")?.addEventListener("click", async () => {
      try {
        await api.resetCircuitBreaker(state.chain);
        await renderRisk(onChange);
        onChange?.();
      } catch (error) { setMessage(error.message, "is-error"); }
    });
    wireWalletSwitch(bodyEl.querySelector("[data-toggle]"));
  } catch (error) {
    setMessage(error.message, "is-error");
  }
}

// L'interruttore del wallet sta qui, fra i limiti, non in una schermata
// "impostazioni" a se': spegnerlo e' una misura di sicurezza, non una
// preferenza.
function wireWalletSwitch(button) {
  const wallet = state.wallets[state.chain];
  if (!button || !wallet) { button?.closest(".switch-row")?.remove(); return; }

  const paint = (enabled) => button.setAttribute("aria-checked", String(enabled));
  paint(wallet.enabled !== false);

  button.addEventListener("click", async () => {
    const next = button.getAttribute("aria-checked") !== "true";
    button.disabled = true;
    try {
      const updated = await api.setWalletEnabled(state.chain, next);
      state.wallets[state.chain] = { ...wallet, enabled: updated.enabled };
      paint(updated.enabled);
    } catch (error) {
      setMessage(error.message, "is-error");
    } finally {
      button.disabled = false;
    }
  });
}

/* ------------------------------------------------------------- Simulazione */

export function openSimulate({ onAccepted } = {}) {
  open("Simulation", "Same guardrails as a live order, no key and no transaction: just checks whether it would pass.");
  setBody(`
    <form class="form" id="simulate-form">
      <label for="sim-token">Token</label>
      <input id="sim-token" name="token" type="text" placeholder="symbol or address" required autocomplete="off" />

      <label for="sim-side">Side</label>
      <select id="sim-side" name="side">
        <option value="buy">Buy</option>
        <option value="sell">Sell</option>
      </select>

      <div class="form-pair">
        <span><label for="sim-notional">Size (USD)</label>
          <input id="sim-notional" name="notional" type="number" min="0" step="0.01" value="10" required /></span>
        <span><label for="sim-price">Price (USD)</label>
          <input id="sim-price" name="price" type="number" min="0" step="0.000001" value="1" required /></span>
      </div>

      <label for="sim-impact">Estimated price impact (%)</label>
      <input id="sim-impact" name="impact" type="number" min="0" step="0.01" value="0.5" required />

      <button type="submit" class="btn-primary">Simulate</button>
    </form>
    <output class="outcome" id="simulate-outcome" hidden></output>
  `);

  const form = bodyEl.querySelector("#simulate-form");
  const outcome = bodyEl.querySelector("#simulate-outcome");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = new FormData(form);
    const button = form.querySelector("button");
    button.disabled = true;
    outcome.hidden = false;
    outcome.dataset.tone = "";
    outcome.textContent = "Simulating…";
    try {
      const result = await api.simulateOrder({
        chain: state.chain,
        token: String(fields.get("token")).trim(),
        strategy_name: "manuale",
        side: fields.get("side"),
        notional_usd: Number(fields.get("notional")),
        price_impact_pct: Number(fields.get("impact")),
        price_usd: Number(fields.get("price")),
      });
      outcome.dataset.tone = result.accepted ? "ok" : "no";
      outcome.textContent = result.accepted ? "Passes every guardrail." : result.reason;
      if (result.accepted) onAccepted?.();
    } catch (error) {
      outcome.dataset.tone = "no";
      outcome.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

/* ------------------------------------------------------------ Chiave privata */

export function openKey({ onStart }) {
  open("Reveal private key", "Needs verification on your phone — Face ID, Touch ID or password. A browser session alone isn't enough.");
  setBody(`
    <dl class="kv">
      <div><dt>Verification</dt><dd>QR + WebAuthn or password</dd></div>
      <div><dt>QR valid for</dt><dd>2 minutes</dd></div>
    </dl>
    <button type="button" class="btn-danger" data-start>Reveal now</button>
  `);
  bodyEl.querySelector("[data-start]").addEventListener("click", () => { dialog.close(); onStart(); });
}

/* ------------------------------------------------------- Righe delle posizioni */

export function positionRow(position) {
  return `
    <li class="asset">
      <span class="asset-mark is-token tk-logo">${tile(position.token, null, state.chain, position.token)}</span>
      <span class="asset-name"><b>${escapeHtml(position.token)}</b>
        <small>${formatToken(position.quantity)} ${escapeHtml(position.token)}</small></span>
      <span class="asset-value"><b>${formatUsd(position.cost_usd)}</b><small>cost</small></span>
    </li>`;
}

/* --------------------------------------------------------- Ricerca token */
// Sostituisce il prompt() del browser: mai un dialog nativo dentro l'app
// (richiesta: "sta cosa va fatta all'interno della web app"). Cerca per
// ticker sulla stessa fonte del resto del sito — DexScreener, gia' usata
// per i grafici — non un indirizzo digitato a mano come unica via.
const pickerDialog = document.querySelector("#picker");
const pickerBody = pickerDialog.querySelector(".sheet-body");
pickerDialog.addEventListener("click", (event) => { if (event.target === pickerDialog) pickerDialog.close(); });
pickerDialog.querySelector(".sheet-close").addEventListener("click", () => pickerDialog.close());
pickerBody.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target.matches?.("li[data-address]")) event.target.click();
});

let pickerDebounce = null;

export const isNativeAddress = (chain, address) =>
  Boolean(address) && address.toLowerCase() === NATIVE_ADDRESS[chain]?.toLowerCase();

// Una schermata sola per scegliere un token, a tutto schermo da telefono:
// campo in alto con "Annulla" accanto, sotto i token che hai; scrivere
// sostituisce la lista invece di allungarla. Richiesta: "quando scelgo un
// token appare sto casino, serve una schermata immersiva e semplice" e
// "immersivo, pulito e ben fatto".
//
// Il campo e' type=search con name "search": Safari su iOS non propone
// l'autocompilazione dei contatti (casa/ufficio sopra la tastiera) sui
// campi di ricerca, mentre autocomplete="off" da solo lo ignora.
const iconCache = new Map(); // indirizzo -> url, dalle ricerche gia' fatte

const hueOf = (text) => [...text].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) % 360, 7);

// The token's own picture: the search's icon, else DexScreener's image for
// the address (the same source as every other list in the app).
const DS = { solana: "solana", robinhood: "robinhood" };
function avatar(token) {
  const a = token.address.startsWith("0x") ? token.address.toLowerCase() : token.address;
  const icon = token.icon || iconCache.get(token.address.toLowerCase())
    || (DS[state.chain] ? `https://dd.dexscreener.com/ds-data/tokens/${DS[state.chain]}/${a}.png` : "");
  const letter = escapeHtml((token.symbol || "?").replace(/^\$/, "").slice(0, 1).toUpperCase());
  return `<span class="tok-av" style="--h:${hueOf(token.address)}" aria-hidden="true">${
    icon ? `<img src="${escapeHtml(icon)}" alt="" loading="lazy" referrerpolicy="no-referrer" />` : ""}<span>${letter}</span></span>`;
}

const VERIFIED_MARK = `<svg class="tok-check" viewBox="0 0 16 16" aria-label="verified"><path d="M8 1.5l1.7 1.2 2.1-.1.7 2 1.7 1.2-.6 2 .6 2-1.7 1.2-.7 2-2.1-.1L8 14.5l-1.7-1.2-2.1.1-.7-2L1.8 10.2l.6-2-.6-2 1.7-1.2.7-2 2.1.1z"/><path class="tick" d="M5.4 8.2l1.8 1.8 3.4-3.6"/></svg>`;

function tokenRow(token, side) {
  return `
    <li class="tok-row" data-address="${escapeHtml(token.address)}" data-symbol="${escapeHtml(token.symbol || "")}" role="button" tabindex="0">
      ${avatar(token)}
      <span class="tok-main">
        <span class="tok-sym">${escapeHtml(token.symbol || shortAddress(token.address))}${token.verified ? VERIFIED_MARK : ""}</span>
        <small>${escapeHtml(token.name || "")}</small>
      </span>
      <span class="tok-side">${side}</span>
    </li>`;
}

const skeleton = (n) => Array.from({ length: n }, () =>
  `<li class="tok-row is-skeleton" aria-hidden="true"><span class="tok-av"></span><span class="tok-main"><span></span><small></small></span></li>`).join("");

const note = (text) => `<li class="tok-note">${escapeHtml(text)}</li>`;

// Un'immagine che non carica lascia la lettera sotto, non un riquadro rotto.
function wireAvatars(list) {
  list.querySelectorAll(".tok-av img").forEach((img) => {
    img.addEventListener("error", () => img.remove(), { once: true });
  });
}

export function openTokenPicker(chain, { onPick, title = "Pick token" } = {}) {
  pickerDialog.querySelector(".sheet-title").textContent = title;
  pickerDialog.setAttribute("aria-label", title);
  pickerBody.innerHTML = `
    <div class="picker-top">
      <p class="picker-title">${escapeHtml(title)}</p>
      <div class="picker-search">
        <label class="picker-field">
          <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="6"/><path d="M13.5 13.5L17 17"/></svg>
          <input type="search" id="picker-query" name="search" placeholder="Search name or ticker"
            aria-label="Search tokens" autocomplete="off" autocorrect="off" autocapitalize="off"
            spellcheck="false" enterkeyhint="search" data-1p-ignore data-lpignore="true" data-form-type="other" />
        </label>
        <button type="button" class="picker-cancel">Cancel</button>
      </div>
    </div>
    <div class="picker-scroll">
      <p class="picker-label" id="picker-label">Your tokens</p>
      <ul id="picker-held" class="picker-list">${skeleton(2)}</ul>
      <ul id="picker-results" class="picker-list" hidden></ul>
      <p class="picker-hint">Can't find it? Paste the token contract in the field up top.</p>
    </div>
  `;
  // Da telefono la tastiera della ricerca sposta la pagina sotto il foglio,
  // e chiuso il foglio ci si ritrovava piu' in basso (richiesta: "la
  // schermata mi va in basso e mi tocca tornare su"). Si torna dov'eri.
  if (!pickerDialog.open) {
    const scrollTop = window.scrollY;
    pickerDialog.addEventListener("close", () => {
      const back = () => window.scrollTo({ top: scrollTop, behavior: "instant" });
      requestAnimationFrame(back);
      setTimeout(back, 350);  // dopo che la tastiera di iOS ha finito di chiudersi
    }, { once: true });
    pickerDialog.showModal();
  }

  const input = pickerBody.querySelector("#picker-query");
  const results = pickerBody.querySelector("#picker-results");
  const held = pickerBody.querySelector("#picker-held");
  const label = pickerBody.querySelector("#picker-label");
  pickerBody.querySelector(".picker-cancel").addEventListener("click", () => pickerDialog.close());
  // Schermata di ricerca: si scrive subito. I tuoi token restano sopra la
  // tastiera, perche' la lista parte appena sotto il campo.
  input.focus();

  const pick = (token) => { pickerDialog.close(); onPick?.(token); };
  const wirePicks = (list) => {
    wireAvatars(list);
    list.querySelectorAll("[data-address]").forEach((li) => {
      li.addEventListener("click", () => pick({ address: li.dataset.address, symbolHint: li.dataset.symbol || null }));
    });
  };

  // I token che il wallet ha DAVVERO (saldo nativo + portafoglio reale via
  // RPC), non solo la ricerca per ticker — Richiesta: "quando seleziono cosa
  // vendere mi devi far selezionare dalle crypto disponibili nel wallet,
  // qualunque esse siano".
  (async () => {
    try {
      const { unit } = chainInfo();
      const [balance, portfolio] = await Promise.all([
        api.getBalance(chain).catch(() => null),
        api.getPortfolio(chain).catch(() => ({ holdings: [] })),
      ]);
      const rows = [];
      if (balance) {
        rows.push({ address: NATIVE_ADDRESS[chain], symbol: unit, name: "Native · pays gas", amount: balance.native_balance, verified: true });
      }
      for (const h of portfolio.holdings) {
        if (h.amount > 0) rows.push({ address: h.address, symbol: h.symbol, name: h.name || "", amount: h.amount });
      }
      held.innerHTML = rows.length
        ? rows.map((r) => tokenRow(r, `<b>${formatToken(r.amount)}</b>`)).join("")
        : note("No tokens with a balance in this wallet.");
      wirePicks(held);
    } catch (error) {
      held.innerHTML = note(error.message);
    }
  })();

  const showHeld = (yes) => {
    held.hidden = !yes;
    results.hidden = yes;
    label.textContent = yes ? "Your tokens" : "Results";
  };

  input.addEventListener("input", () => {
    clearTimeout(pickerDebounce);
    const q = input.value.trim();
    if (q.length < 2) { showHeld(true); return; }
    showHeld(false);
    // Un indirizzo incollato si usa cosi' com'e': niente ricerca per
    // ticker, niente secondo campo nascosto in un "non lo trovi?".
    if (looksLikeAddress(q)) {
      results.innerHTML = tokenRow({ address: q, symbol: "Pasted contract", name: shortAddress(q) }, "Use ›");
      wirePicks(results);
      return;
    }
    results.innerHTML = skeleton(3);
    pickerDebounce = setTimeout(async () => {
      try {
        const found = await api.searchTokens(chain, q);
        if (input.value.trim() !== q) return;
        if (!found.length) { results.innerHTML = note("No token by that name on this network."); return; }
        for (const t of found) if (t.icon) iconCache.set(t.address.toLowerCase(), t.icon);
        results.innerHTML = found.map((t) => tokenRow(t, `${
          t.liquidity_usd ? `<span>liq. ${compactUsd.format(t.liquidity_usd)}</span>` : ""}${
          t.verified ? "" : "<i>unverified</i>"}`)).join("");
        wirePicks(results);
      } catch (error) {
        results.innerHTML = note(error.message);
      }
    }, 300);
  });

  input.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    results.querySelector("[data-address]")?.click();
  });
}

const compactUsd = new Intl.NumberFormat("en-US", {
  style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1,
});

// Mint Solana (base58, 32-44 caratteri) o contratto EVM (0x + 40 hex).
const looksLikeAddress = (text) =>
  /^0x[0-9a-fA-F]{40}$/.test(text) || /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(text);

export { shortAddress };
