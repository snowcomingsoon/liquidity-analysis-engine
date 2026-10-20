/**
 * Arenas: the best quality low caps, each ranked against its own narrative.
 *
 * Lorenzo, 27/09, replaced Picks with a Top 15/25/50 ("voglio semmai
 * sniperare progetti di qualita' con capitalizzazioni basse"); 07/10: "la
 * top50 come concetto e' limitante, serve un sistema meritocratico [...]
 * data la complessita' dei progetti e le diverse narrative". Now the list is
 * arenas.py: one arena per narrative (and one for layer chains), no fixed
 * size, the projects at or above the arena's median "in" and the rest on its
 * bench. The podium is pound for pound: the projects that lead their own
 * arena by the most. Refreshed every POLL_MS; a tap opens the token page.
 */
import * as api from "@onchain/api.js";
import { register } from "@onchain/detail.js";
import { isHidden, onHiddenChange, withEntrance } from "@onchain/hidden.js";
import { escapeHtml, tile, tokenRow, usdShort } from "@onchain/format.js";
import { renderPodium } from "@onchain/podium.js";
import { shownSummary } from "@onchain/lab-shown.js";
import * as narr from "@onchain/narrative_pick.js";
import { disintegrate } from "@onchain/particles.js";
import "@onchain/motion.js";

const POLL_MS = 30_000;
// Trading off (Lorenzo, 07/10): rows show the market, not a backtest.
const TRADING = document.documentElement.dataset.trading === "on";

let root = null;
let arenas = [];
let p4p = [];
let labStatus = null;
let filtered = false;   // the last load was narrowed by narrative
let labels = {};        // narrative key -> label, from the coverage
// One arena on its own, bench open (Lorenzo, 07/10: "la top aggiornata per
// ogni categoria"); null shows them all. Remembered per device.
let only = null;   // the single-arena list; the mosaic opens arenas in place now (10/10)
function setOnly(k) { only = k; try { k ? localStorage.setItem("lae:arena", k) : localStorage.removeItem("lae:arena"); } catch { /* private mode */ } }

// Each arena's champion on the last visit (Lorenzo, 28/09: "se rientro dopo
// un po' e c'e' stato un capovolgimento [...] fai una bella animazione"):
// arena key -> {id, symbol}.
const SEEN_KEY = "lae:arena-crowns";
function readSeen() { try { return JSON.parse(localStorage.getItem(SEEN_KEY)) || null; } catch { return null; } }
function writeSeen(map) { try { localStorage.setItem(SEEN_KEY, JSON.stringify(map)); } catch { /* private mode */ } }
let seen = readSeen();
let shown = false;
let stale = false;          // new data arrived while the arenas were off screen
const idOf = (e) => `gem:${e.chain}:${e.token_address}`;
// The arenas sit in a tab: painted while another tab is open, the "since your
// last visit" animation would play unseen (Lorenzo, 29/09). It waits until it shows.
const onScreen = () => document.visibilityState === "visible" && root.getClientRects().length > 0;

let playing = false;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

/** Each dethroned champion turns to dust over the row of the one that took
 *  its place, one arena after the other. Leaving the tab stops it and keeps
 *  the crowns unseen, so it plays again next time. */
async function sequence(changes, crowns) {
  playing = true;
  let aborted = false;
  for (const { li, was } of changes) {
    if (!onScreen()) { aborted = true; break; }
    const ghost = li.cloneNode(true);
    ghost.classList.remove("rank-new", "rank-wait");
    ghost.setAttribute("aria-hidden", "true");
    const r = li.getBoundingClientRect();
    Object.assign(ghost.style, { position: "fixed", visibility: "hidden", top: `${r.top}px`, left: `${r.left}px`,
      width: `${r.width}px`, margin: "0", animation: "none" });
    const name = ghost.querySelector(".trow-main b");
    if (name) name.textContent = `1. ${was.symbol ?? ""}`;
    ghost.querySelectorAll(".trow-main small, .trow-num b, img, svg").forEach((x) => x.remove());
    document.body.append(ghost);
    await disintegrate(ghost, 900);
    ghost.remove();
    li.classList.remove("rank-wait");
    li.classList.add("rank-new");
    await wait(300);
  }
  root.querySelectorAll("[data-top-arenas] li.rank-wait").forEach((li) => li.classList.remove("rank-wait"));
  playing = false;
  if (aborted) { stale = true; return; }
  seen = crowns;
  writeSeen(seen);
}

const heatBar = (h) => `<span class="ar-heat" aria-label="Narrative heat ${h} of 3">${"█".repeat(h)}${"░".repeat(Math.max(0, 3 - h))}</span>`;
// What the tile counts is what the list shows: tokens hidden by the user left out.
const unhidden = (a) => a.entries.filter((e) => !isHidden(e.chain, e.token_address));
const shownCount = (a) => unhidden(a).length;
// The mosaic: the biggest arenas take the biggest tiles, privacy first;
// the colour is how the arena's projects moved in 24 hours (their median).
const SPANS = [[4, 3], [2, 3], [3, 2], [3, 2], [2, 2], [2, 2], [2, 2]];
const MOSAIC_MAX = 13;     // tiles before "+ N more"
let mosaicAll = false;
function move(a) {
  const xs = unhidden(a).map((e) => e.change_24h).filter((v) => v != null).sort((x, y) => x - y);
  if (!xs.length) return null;
  const m = xs.length >> 1;
  return xs.length % 2 ? xs[m] : (xs[m - 1] + xs[m]) / 2;
}
const SHORT = {
  "Perps & Derivatives": "Perps", "Chains L0/L1/L2": "Chains", "Stablecoin Payments": "Payments",
  "Wallets & Account Abstraction": "Wallets", "NFT & Collectibles": "NFT", "Lending & Credit": "Lending",
  "Music & Media": "Music", "Dev Tools & RPC": "Dev tools", "Yield & Vaults": "Yield",
  "Robotics / Physical AI": "Robotics", "Identity / Personhood": "Identity", "AI Data / Oracles": "AI Data",
  "Prediction Markets": "Predictions", "Chain Abstraction": "Chain Abstr.", "AI-Managed Money": "AI Money",
};
function mosaicHtml(width = 360) {
  if (!arenas.length) return "";
  // Privacy is one arena among the others (Lorenzo, 10/10): biggest first, no pin.
  const list = [...arenas].sort((a, b) => shownCount(b) - shownCount(a));
  const openA = hive ? arenas.find((a) => a.key === hive) : null;
  const cut = mosaicAll || list.length <= MOSAIC_MAX ? list.length : MOSAIC_MAX - 1;
  const tiles = list.slice(0, cut).map((a, i) => {
    const [c, r] = SPANS[i] ?? [2, 1];
    const n = shownCount(a);
    const ch = move(a);
    const tone = ch == null ? "" : ch >= 3 ? "g1" : ch >= 0.5 ? "g2" : ch <= -3 ? "r1" : ch <= -0.5 ? "r2" : "";
    const top = unhidden(a)[0];
    const lead = top ? `♛ ${escapeHtml(top.symbol ?? "")}` : "searching";
    const pct = ch == null ? "" : ` <span class="${ch >= 0 ? "up" : "down"}">${ch >= 0 ? "+" : "−"}${Math.abs(ch).toFixed(Math.abs(ch) < 10 ? 1 : 0)}%</span>`;
    const open = a.key === hive;
    return `<button type="button" class="mz ${tone}${open ? " mz-open" : ""}" data-arena-pick="${escapeHtml(a.key)}" aria-expanded="${open}"
      style="grid-column: span ${c}; grid-row: span ${r}" aria-label="${escapeHtml(a.label)}: ${n} projects">
      <b>${escapeHtml(SHORT[a.label] || a.label)}</b>${r > 1 ? `<span class="mz-n">${n}<em> projects</em></span><small>${lead}${pct}</small>` : `<small>${n} · ${lead}</small>`}</button>`;
  });
  if (cut < list.length) tiles.push(`<button type="button" class="mz mz-more" data-mosaic-more style="grid-column: span 2">
    <b>+ ${list.length - cut} more</b><small>smaller arenas</small></button>`);
  return `<p class="mz-intro">Each tile is a narrative: its projects compete only with each other. Tap one for its ranking.</p>
    <div class="mosaic" role="group" aria-label="Arenas">${tiles.join("")}</div>
    <p class="mz-legend"><span>♛ leader · size = projects</span><span><i class="up">■</i> up 24h <i class="down">■</i> down 24h</span></p>
    ${openA ? `<div class="ar-open">${arenaHtml(openA, true)}</div>` : ""}`;
}
// A tile opens its ranking right under the mosaic, same screen, no sub-menu
// (Lorenzo, 10/10: the honeycomb was "orribile, ripristina un elenco").
let hive = null;            // arena key whose ranking is open

function row(e, a) {
  const id = idOf(e);
  const rank = e.arena_rank;
  register(id, { kind: "gem", symbol: e.symbol, name: e.name, chain: e.chain, token: e.token_address, pair: e.pair_address,
    pairUrl: e.pair_url, image: e.image, cap: e.market_cap, change: e.change_24h != null ? e.change_24h / 100 : null,
    ageTs: e.launched_at, rank, context: `${a.label} · #${rank} of ${a.size} · score ${Math.round(e.score ?? 0)}` });
  const html = tokenRow({ id, symbol: e.symbol, name: `${rank}. ${e.name || e.symbol}`, chain: e.chain, token: e.token_address,
    image: e.image, cap: e.market_cap, change: e.change_24h != null ? e.change_24h / 100 : null, ageTs: e.launched_at,
    score: e.score, badge: e.early ? "early" : e.hidden ? "hidden" : null, sub: TRADING ? btSub(e.backtests) : marketSub(e) });
  return html.replace('<li class="trow"', `<li class="trow${rank === 1 ? " ar-champ" : ""}" style="--v:${Math.max(0, Math.min(100, Math.round(e.score ?? 0)))}%"`);
}

function arenaHtml(a, open = false) {
  const rows = a.entries.filter((e) => !isHidden(e.chain, e.token_address));
  if (!rows.length) {
    return open && !a.entries.length ? `<section class="arena" data-arena="${escapeHtml(a.key)}"><header class="ar-head"><h4>${escapeHtml(a.label)}</h4></header>
      <p class="muted pad">No ${escapeHtml(a.label)} project has passed the checks yet: they appear here as the research finds them.</p></section>` : "";
  }
  const inn = open ? rows : rows.filter((e) => e.in);
  const bench = open ? [] : rows.filter((e) => !e.in);
  return `<section class="arena" data-arena="${escapeHtml(a.key)}">
    <header class="ar-head"><h4>${escapeHtml(a.label)}</h4>${a.heat ? heatBar(a.heat) : ""}<span class="ar-count">${open ? `${rows.length} projects` : `${inn.length} in`} · median ${Math.round(a.median)}</span></header>
    <ol class="memes-list" data-top-rows>${inn.map((e) => row(e, a)).join("")}</ol>
    ${bench.length ? `<details class="ar-bench"><summary>${bench.length} below the arena median</summary>
      <ol class="memes-list" data-top-rows>${bench.map((e) => row(e, a)).join("")}</ol></details>` : ""}
  </section>`;
}

function paint() {
  if (!root || playing) return;
  delete root.dataset.loading;
  const firstPaint = !shown;
  // The podium is pound for pound: the projects leading their own arena by the most.
  let podium = root.querySelector("[data-top-podium]");
  if (!podium) {
    podium = document.createElement("div");
    podium.className = "top-hero";
    podium.dataset.topPodium = "";
    root.insertBefore(podium, root.firstChild);
  }
  podium.classList.remove("top-wait");
  podium.removeAttribute("role");
  const top3 = p4p.filter((e) => !isHidden(e.chain, e.token_address)).slice(0, 3).map((e) => {
    register(idOf(e), { kind: "gem", symbol: e.symbol, name: e.name, chain: e.chain, token: e.token_address,
      pair: e.pair_address, pairUrl: e.pair_url, image: e.image, cap: e.market_cap,
      change: e.change_24h != null ? e.change_24h / 100 : null, ageTs: e.launched_at,
      context: `Top 25 · score ${Math.round(e.score ?? 0)}` });
    return { id: idOf(e), symbol: e.symbol, value: `score ${Math.round(e.score ?? 0)}`,
      logoHtml: tile(e.symbol, e.image, e.chain, e.token_address) };
  });
  const sig = top3.map((x) => x.id).join("|");
  if (top3.length) renderPodium(podium, top3, { still: podium.dataset.sig === sig });
  else podium.innerHTML = "";
  podium.dataset.sig = sig;

  const box = root.querySelector("[data-top-arenas]");
  if (only && !arenas.some((a) => a.key === only)) setOnly(null);
  // No arena picked: the mosaic of every arena (Lorenzo, 10/10, "Mosaico");
  // one picked: its whole list under a way back.
  const picked = only ? arenas.find((a) => a.key === only) : null;
  if (hive && !arenas.some((a) => a.key === hive)) hive = null;
  withEntrance(box, () => {
    const html = picked
      ? `<button type="button" class="ar-back" data-arena-pick="">← All arenas</button>${arenaHtml(picked, true)}`
      : mosaicHtml(box?.clientWidth || 360);
    box.innerHTML = html || `<p class="muted pad">The arenas are filling up: projects appear as they pass the checks.</p>`;
  });

  // A narrowed view is not what the last visit saw: no comparison.
  const visible = onScreen();
  if (!visible) stale = true;
  const prev = !filtered && seen && visible ? seen : null;
  const crowns = Object.fromEntries(arenas.filter((a) => a.entries.length)
    .map((a) => [a.key, { id: idOf(a.entries[0]), symbol: a.entries[0].symbol }]));
  const changes = [];
  const lead = [];
  if (prev) {
    for (const a of arenas) {
      const was = prev[a.key];
      const now = crowns[a.key];
      if (!was || !now || was.id === now.id) continue;
      const li = box.querySelector(`[data-arena="${CSS.escape(a.key)}"] li.ar-champ`);
      if (li) { li.classList.add("rank-wait"); changes.push({ li, was }); }
      lead.push(`${now.symbol} took ${a.label} from ${was.symbol}`);
    }
  }
  if (arenas.length && !filtered && visible) {
    shown = true;
    stale = false;
    if (changes.length) sequence(changes, crowns);
    else { seen = crowns; writeSeen(seen); }
  }
  // A project shows in each of its narratives (also: true) but counts once.
  const total = new Set(arenas.flatMap((a) => a.entries.map(idOf))).size;
  const narrLine = filtered
    ? `<button type="button" class="top-narr-clear" data-top-narr-clear>${escapeHtml(narr.get().map((k) => labels[k] ?? k).join(", "))} ✕</button> `
    : "";
  const head = lead.length ? `${firstPaint ? "Since your last visit: " : ""}${lead.slice(0, 3).join(", ")}. ` : "";
  const bt = labStatus;
  root.querySelector("[data-top-note]").innerHTML = narrLine + escapeHtml(head
    + (total ? `${arenas.length} arenas · ${total} projects` : "")
    + (TRADING && bt?.total ? ` · backtests ${bt.ready}/${bt.total} ready` : ""))
    + (TRADING ? ' <button type="button" class="top-narr-clear" data-top-wallet>$10k wallet on these trades →</button>' : "");
}

// Without trading: measured usage (usage.py), what put the project here.
const compact = (n) => new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(n);

function marketSub(e) {
  const u = e.usage ?? {};
  const vol = u.vol_7d_avg ?? u.vol_24h;
  // Short enough for a phone row: "$812k/day · 15.2k holders".
  const parts = [vol != null ? `${usdShort(vol)}/day` : null,
    u.holders != null ? `${compact(u.holders)} holders` : null];
  const line = parts.filter(Boolean).join(" · ");
  return line || (e.liquidity_usd != null ? `Liquidity ${usdShort(e.liquidity_usd)}` : "");
}

// Its own view in the dock (Lorenzo, 07/10: "la sezione EARLY non la trovo").
function paintEarly(list) {
  const box = document.querySelector("[data-early-view]");
  if (!box) return;
  box.querySelector("[data-early-empty]").hidden = list.length > 0;
  box.querySelector("[data-early-rows]").innerHTML = list.map((e) => {
    const id = `gem:${e.chain}:${e.token_address}`;
    register(id, { kind: "gem", symbol: e.symbol, name: e.name, chain: e.chain, token: e.token_address, pair: e.pair_address,
      pairUrl: e.pair_url, image: e.image, cap: e.market_cap, change: e.change_24h != null ? e.change_24h / 100 : null,
      ageTs: e.launched_at, context: `Early · score ${Math.round(e.score ?? 0)}` });
    return tokenRow({ id, symbol: e.symbol, name: e.name || e.symbol, chain: e.chain, token: e.token_address,
      image: e.image, cap: e.market_cap, change: e.change_24h != null ? e.change_24h / 100 : null, ageTs: e.launched_at,
      score: e.score, badge: "early", sub: marketSub(e) });
  }).join("");
}

// The H24 lab's best backtest (strategy_lab.py), in the row: what the
// Strategies tab is for (Lorenzo, 28/09).
function btSub(b) {
  if (!b) return '<span class="bt-live" role="img" aria-label="Backtest on its way"><i></i><i></i><i></i></span>';
  const pct = (v) => { const r = Math.round(v ?? 0); return `${r > 0 ? "+" : ""}${r}%`; };
  const s = shownSummary(b);
  if (!s) return "bt: no entry";
  const win = s.win_rate != null ? ` · ${Math.round(s.win_rate)}% win` : "";
  return `${s.interval} ${pct(s.return_pct)} · ${s.trades} trades${win}${s.in_position ? " · long" : ""}`;
}

async function load() {
  try {
    const keys = narr.get();
    const top = await api.getTop(50, keys);
    filtered = keys.length > 0;
    // A page served before the arenas: one arena holding the old list.
    arenas = top?.arenas ?? [{ key: "all", label: "All projects", heat: 0, size: (top?.entries ?? []).length, median: 0,
      entries: (top?.entries ?? []).map((e, i) => ({ ...e, arena_rank: i + 1, in: true })) }];
    // The podium is the Top's first three by score (Lorenzo, 20/10: "i primi
    // tre della top 25 [...] chi ha il miglior valore e' primo").
    p4p = [...(top?.entries ?? [])].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
    labStatus = top?.backtests ?? null;
    paint();
    paintEarly(top?.early ?? []);   // the board's own early list, never narrowed by narrative
  } catch {
    // Keep the last view; with none yet, the cube says the next poll retries.
    const w = root.querySelector(".top-wait");
    if (!w) return;
    w.querySelector("engn-motion").setAttribute("state", "reconnect");
    w.querySelector("p").textContent = "Reconnecting…";
  }
}

/** Until the first arenas land, the podium's place holds the ENGN cube
 * working (the motion kit's loading state), not an empty gap. */
function waiting() {
  if (root.querySelector("[data-top-podium]")) return;
  const el = document.createElement("div");
  el.className = "top-hero top-wait";
  el.dataset.topPodium = "";
  el.setAttribute("role", "status");
  el.innerHTML = '<engn-motion state="loading" decorative></engn-motion><p>Loading the arenas…</p>';
  root.insertBefore(el, root.firstChild);
}

export function mountTop() {
  root = document.getElementById("top-picks");
  if (!root) return;
  waiting();
  root.addEventListener("click", (event) => {
    if (event.target.closest("[data-top-narr-clear]")) { narr.set([]); return; }
    const tileHit = event.target.closest(".mz[data-arena-pick]");
    if (tileHit) {
      const key = tileHit.dataset.arenaPick;
      hive = hive === key ? null : key;        // the same tile again closes it
      paint();
      const again = root.querySelector(`.mz[data-arena-pick="${CSS.escape(key)}"]`);
      again?.focus({ preventScroll: true });
      if (hive) root.querySelector(".ar-open")?.scrollIntoView({ block: "start", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
      return;
    }
    const pick = event.target.closest("[data-arena-pick]");
    if (pick) {
      hive = null;
      const back = only;
      setOnly(pick.dataset.arenaPick || null);
      paint();
      root.querySelector(only ? ".ar-back" : `[data-arena-pick="${CSS.escape(back ?? "")}"]`)?.focus({ preventScroll: true });
      if (only) root.querySelector("[data-top-arenas]")?.scrollIntoView({ block: "start" });
      return;
    }
    if (event.target.closest("[data-mosaic-more]")) { mosaicAll = true; paint(); root.querySelectorAll("[data-top-arenas] .mz")[MOSAIC_MAX - 1]?.focus({ preventScroll: true }); return; }
    if (event.target.closest("[data-top-wallet]")) { import("@onchain/sim-backtest.js").then((m) => m.openSimBacktest()); }
  });
  onHiddenChange(paint);
  // First time the arenas are on screen in this visit: now the comparison can play.
  new IntersectionObserver((seenNow) => {
    if (seenNow.some((x) => x.isIntersecting) && (!shown || stale) && arenas.length) paint();
  }).observe(root);
  document.addEventListener("visibilitychange", () => { if ((!shown || stale) && arenas.length && onScreen()) paint(); });
  narr.onChange(() => load());
  narr.coverage().then((list) => {
    labels = Object.fromEntries(list.map((n) => [n.key, n.label ?? n.key]));
    if (filtered) paint();
  });
  load();
  setInterval(() => document.visibilityState === "visible" && load(), POLL_MS);
}
