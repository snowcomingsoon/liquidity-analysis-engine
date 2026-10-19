/**
 * La classifica: i progetti migliori fra quelli visti dal radar.
 *
 * Richiesta: "una specie di leaderboard [...] cose estetiche che facciano
 * capire primo posto, secondo posto, terzo posto [...] dinamica [...]
 * aggiornata in tempo reale [...] segnalare anche da quanto e' che sono
 * usciti".
 *
 * Il podio per i primi tre, poi una riga a testa. Tre barrette per riga:
 * GitHub, sito, tokenomics (vedi app/trading/onchain/depth.py). Un tocco
 * apre i numeri che giustificano il voto. Quando l'ordine cambia le righe
 * scivolano al posto nuovo, con la freccia di quanto sono salite o scese.
 */
import * as api from "@onchain/api.js";
import { escapeHtml, tile, tokenRow } from "@onchain/format.js";
import { register } from "@onchain/detail.js";
import { renderPodium } from "@onchain/podium.js";

const ROOT = document.getElementById("onchain-embed") ?? document;
const POLL_MS = 10_000;
const MOVE_SHOWN_S = 15 * 60;
const PILLARS = [["github", "GitHub", "G"], ["site", "Research", "R"], ["tokenomics", "Tokenomics", "T"]];
const CHAINS = { solana: "Solana", robinhood: "Robinhood", base: "Base", bsc: "BSC", ethereum: "Ethereum", arc: "Arc" };
const PLACES = ["First", "Second", "Third"];

let root = null;
let data = null;
let version = -1;
let open = null;
let timer = null;

const key = (e) => `${e.chain}:${e.token_address}`;
const usd = (v) => (v == null ? "—" : v >= 1e6 ? `$${(v / 1e6).toFixed(v >= 1e7 ? 0 : 1)}M`
  : v >= 1e3 ? `$${Math.round(v / 1e3)}k` : `$${Math.round(v)}`);
const since = (ts) => {
  if (!ts) return "—";
  const s = Math.max(0, Date.now() / 1000 - ts);
  return s < 3600 ? `${Math.max(1, Math.round(s / 60))} min` : s < 172_800 ? `${Math.round(s / 3600)} h`
    : s < 86_400 * 60 ? `${Math.round(s / 86_400)} d` : `${Math.round(s / (86_400 * 30))} mo`;
};
const score = (v) => (v == null ? "—" : Math.round(v));
const yes = (v) => (v ? "yes" : "no");

export function mountLeaderboard() {
  root = ROOT.querySelector("#board");
  if (!root) return;
  if (matchMedia("(pointer: fine)").matches) {
    root.addEventListener("pointermove", tilt);
    root.addEventListener("pointerout", untilt);
  }
  root.addEventListener("click", (event) => {
    const row = event.target.closest("[data-board]");
    if (!row || event.target.closest("a")) return;
    open = open === row.dataset.board ? null : row.dataset.board;
    paint(false);
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") refresh();
  });
  setInterval(() => data && paintAges(), 30_000);
  refresh();
}

async function refresh() {
  clearTimeout(timer);
  try {
    const next = await api.getLeaderboard();
    if (next.version !== version) {
      data = next;
      version = next.version;
      paint(true);
    }
  } catch {
    // Keep what is on screen; with nothing yet, say so instead of an endless skeleton.
    if (!data) {
      delete root.dataset.loading;
      root.querySelector("[data-board-podium]").innerHTML = "";
      const empty = root.querySelector("[data-board-empty]");
      empty.textContent = "Leaderboard unavailable right now. Retrying…";
      empty.hidden = false;
      root.querySelector("[data-board-podium]").hidden = true;
    }
  }
  if (document.visibilityState === "visible") timer = setTimeout(refresh, POLL_MS);
}

// ------------------------------------------------------------------ disegno

function paint(animate) {
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const painted = root.querySelector("[data-board-podium]").childElementCount > 0;
  // Rank changes morph with the View Transitions API; FLIP where it is missing.
  // A view transition snapshots the whole page: only when the board is on
  // screen and no sheet is open, or every 10s poll flashed whatever view
  // was showing, sheets included (Lorenzo, 27/09: "ogni tanto flasha la
  // schermata e appaiono sovrapposizioni").
  const onScreen = root.offsetParent !== null && !document.querySelector("dialog[open]");
  if (animate && painted && onScreen && document.startViewTransition && !reduced && document.visibilityState === "visible") {
    document.startViewTransition(() => render(false));
    return;
  }
  render(animate);
}

function render(animate) {
  // First paint only: the entrance (pedestals rise, cards drop in 3-2-1).
  if (!root.dataset.seen) {
    root.dataset.seen = "1";
    root.dataset.enter = "";
    setTimeout(() => delete root.dataset.enter, 2000);
  }
  root.querySelector("[data-board-podium]").hidden = false;
  root.hidden = false;
  delete root.dataset.loading;
  const before = animate ? positions() : null;
  const entries = data.entries ?? [];
  const podium = root.querySelector("[data-board-podium]");
  const list = root.querySelector("[data-board-list]");
  // The podium lives here (Lorenzo, 27/09: "il podio ha senso soltanto per
  // le gemme"): the top three on it, every project below as a row.
  const top3 = entries.slice(0, 3).map((e) => ({ id: `gem:${e.chain}:${e.token_address}`, symbol: e.symbol,
    value: `${Math.round(e.score ?? 0)} pts`, logoHtml: tile(e.symbol, e.image, e.chain, e.token_address) }));
  const sig = top3.map((x) => x.id).join("|");
  if (top3.length) renderPodium(podium, top3, { still: podium.dataset.sig === sig });
  else podium.innerHTML = "";
  podium.dataset.sig = sig;
  podium.dataset.count = String(top3.length);
  list.innerHTML = entries.map(gemRow).join("");
  const detail = root.querySelector("[data-board-detail]");
  const chosen = entries.find((e) => key(e) === open);
  detail.hidden = !chosen;
  detail.innerHTML = chosen ? details(chosen) : "";
  if (chosen && chosen.rank > 3) {
    list.querySelector(`[data-board="${CSS.escape(open)}"]`)?.after(detail);
  } else {
    podium.after(detail);
  }
  root.querySelector("[data-board-empty]").hidden = entries.length > 0;
  root.querySelector("[data-board-empty]").textContent = emptyText();
  paintClose();
  paintMeta();
  paintTrack();
  paintEarly(entries);
  countUp();
  if (before) slide(before);
}

function positions() {
  const out = new Map();
  root.querySelectorAll("[data-board]").forEach((el) => out.set(el.dataset.board, el.getBoundingClientRect()));
  return out;
}

/** FLIP: ogni riga parte da dove stava e scivola al posto nuovo. */
function slide(before) {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  root.querySelectorAll("[data-board]").forEach((el) => {
    const was = before.get(el.dataset.board);
    if (!was) { el.classList.add("is-new"); return; }
    const now = el.getBoundingClientRect();
    const dx = was.left - now.left;
    const dy = was.top - now.top;
    if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return;
    el.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }],
      { duration: 620, easing: "cubic-bezier(.2,.8,.2,1)" });
  });
}

function move(e) {
  if (!e.moved_at || Date.now() / 1000 - e.moved_at > MOVE_SHOWN_S) return "";
  if (e.rank_before == null) return `<i class="bd-move" data-dir="new">new</i>`;
  const d = e.rank_before - e.rank;
  if (!d) return "";
  return `<i class="bd-move" data-dir="${d > 0 ? "up" : "down"}">${d > 0 ? "▲" : "▼"}${Math.abs(d)}</i>`;
}

function badges(e) {
  const out = [];
  if (e.benchmark) out.push(`<em data-tone="gold">benchmark</em>`);
  else if (e.similarity?.score >= 25) out.push(`<em class="bd-sim">≈ DREGG ${e.similarity.score}%</em>`);
  if (e.early) out.push(`<em data-tone="early" title="Under $300k and past every other bar of the Top: smaller and riskier. Research, not advice.">early</em>`);
  if (e.exception) out.push(`<em data-tone="gold">exception</em>`);
  if (e.bonding) out.push(`<em>pump.fun</em>`);
  if (e.closed_source) out.push(`<em>closed source</em>`);
  if (e.text_moved) out.push(`<em title="Score rose ${Math.round(e.text_moved.to - e.text_moved.from)} points on new site text alone: no new code, tokenomics or market">text-driven</em>`);
  if (e.judge?.drift) out.push(`<em title="The AI judge changed its mind on the same facts (${e.judge.drift.from_score} → ${e.judge.drift.to_score})">judge unsure</em>`);
  // Real use, from DefiLlama: the strongest signal a microcap can show.
  const tr = e.traction;
  if (tr?.facts?.mcap_to_fees != null && tr.facts.mcap_to_fees <= 20) out.push(`<em data-tone="use">${Math.round(tr.facts.mcap_to_fees)}× fees</em>`);
  else if (tr?.facts?.tvl) out.push(`<em data-tone="use">TVL ${usd(tr.facts.tvl)}</em>`);
  // hottest narrative first, at most two so the card stays clean
  for (const n of (e.narratives ?? []).slice().sort((a, b) => b.heat - a.heat).slice(0, 2)) {
    out.push(`<em class="bd-nar"${n.heat >= 3 ? ' data-tone="hot"' : ""}>${escapeHtml(n.label)}</em>`);
  }
  return out.join("");
}

// Stable, CSS-safe name per project for the View Transitions API: a rank
// change morphs each card from its old place to the new one.
const vtName = (k) => `gb-${[...k].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7).toString(36)}`;

/** Three rings, one per pillar: the arc is the score, drawn in on arrival. */
function rings(e) {
  return `<span class="gb-rings">${PILLARS.map(([k, label, letter]) => {
    const closed = k === "github" && e.closed_source;
    const v = closed ? 0 : Math.round(e.pillars?.[k]?.score ?? 0);
    return `<i style="--v:${v}" title="${label} ${closed ? "no public code" : v}"${closed ? ' data-off="1"' : ""}><b>${letter}</b></i>`;
  }).join("")}</span>`;
}

function podiumCard(e, i) {
  const k = key(e);
  const total = Math.round(e.score ?? 0);
  return `<li data-place="${i + 1}"${open === k ? ' aria-expanded="true"' : ""} style="view-transition-name:${vtName(k)};--i:${i}">
    <button type="button" data-board="${escapeHtml(k)}" aria-label="${PLACES[i]} place, ${escapeHtml(e.symbol)}, score ${total}">
      <span class="gb-glow" aria-hidden="true"></span>
      <span class="bd-medal" aria-hidden="true">${i + 1}</span>
      <span class="bd-sym"><b>${escapeHtml(e.symbol)}</b>${move(e)}</span>
      <span class="gb-score" style="--v:${total}"><b data-num="${total}">${total}</b></span>
      ${rings(e)}
      <small><span data-age="${e.launched_at ?? ""}">${since(e.launched_at)}</span> · ${usd(e.market_cap)}</small>
      <span class="bd-tags">${badges(e)}</span>
      ${e.benchmark ? `<p class="bd-honor">Honorable mention</p>` : ""}
    </button>
    <span class="gb-step" aria-hidden="true"></span>
  </li>`;
}

function row(e) {
  const k = key(e);
  const total = Math.round(e.score ?? 0);
  return `<li${open === k ? ' aria-expanded="true"' : ""}${e.early ? ' data-early="1"' : ""} style="view-transition-name:${vtName(k)}">
    <button type="button" data-board="${escapeHtml(k)}">
      <span class="gb-glow" aria-hidden="true"></span>
      <span class="bd-rank">${e.rank}</span>
      <span class="tk-name"><b>${escapeHtml(e.symbol)} ${move(e)}</b>
        <small>launched <span data-age="${e.launched_at ?? ""}">${since(e.launched_at)}</span> ago · ${usd(e.market_cap)} · ${CHAINS[e.chain] ?? e.chain} ${badges(e)}</small></span>
      ${rings(e)}
      <span class="gb-total" style="--v:${total}"><b data-num="${total}">${total}</b><i aria-hidden="true"></i></span>
    </button>
  </li>`;
}

const compactNum = (v) => { const n = Number(v) || 0; return n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}k` : `${n}`; };

// The social numbers the judge read: X search, the project's own Telegram and Discord.
function socialLines(j) {
  const out = [];
  const x = j?.x;
  if (x) out.push(`<li>X: ${Number(x.posts_7d) || 0} posts/7d · ${Number(x.authors) || 0} authors · median ${compactNum(x.median_followers ?? 0)} followers</li>`);
  const tg = j?.tg;
  if (tg) {
    const at = `@${escapeHtml(tg.handle ?? "")}`;
    let body;
    let tone = "";
    if (tg.kind === "missing") body = `${at} not found`;
    else if (tg.kind === "group") {
      body = `${at} · group · ${compactNum(tg.subs ?? 0)} members`;
      if (tg.online != null) body += ` · ${compactNum(tg.online)} online`;
    } else if (tg.kind === "no_preview") body = `${at} · ${compactNum(tg.subs ?? 0)} subscribers · posts not public`;
    else {
      const parts = [`${compactNum(tg.subs ?? 0)} members`, `${Number(tg.posts_7d) || 0} posts/7d`];
      if (tg.last_post_days != null) parts.push(`last ${Math.round(Number(tg.last_post_days))}d ago`);
      if (tg.median_views != null) parts.push(`${compactNum(tg.median_views)} views`);
      body = `${at} · ${parts.join(" · ")}`;
      if (tg.last_post_days != null && Number(tg.last_post_days) > 180) {
        tone = ' data-tone="bad"';
        body += ` · silent ${Math.floor(Number(tg.last_post_days) / 30)} months`;
      }
    }
    out.push(`<li${tone}>Telegram: ${body}</li>`);
    const events = Array.isArray(j?.tg_events) ? j.tg_events : [];
    for (const ev of events) {
      out.push(`<li>${escapeHtml(ev?.date ?? "")} · ${escapeHtml(ev?.type ?? "")} · ${escapeHtml(ev?.text ?? "")}</li>`);
    }
  }
  const dc = j?.dc;
  if (dc) {
    const name = escapeHtml(dc.name ?? dc.code ?? "");
    if (dc.kind === "missing") {
      out.push(`<li>Discord: ${name} invite expired</li>`);
    } else {
      const members = Number(dc.members) || 0;
      let body = `${name} · ${compactNum(members)} members · ${compactNum(dc.online ?? 0)} online`;
      if (members > 0) body += ` · ${((Number(dc.online) || 0) / members * 100).toFixed(1)}% online`;
      out.push(`<li>Discord: ${body}</li>`);
    }
  }
  return out.join("");
}

// DeepSeek's report on the project: its own verdict and, when it read the
// whole board, the editor's call.
function deepseekBlock(e) {
  const j = e.judge, r = e.review, c = e.code;
  if (!j && !r && !c) return "";
  const head = j ? `${escapeHtml(j.verdict ?? "")} · ${j.score ?? "—"}/100` : "";
  const edit = r ? `<li data-tone="${r.keep ? "good" : "bad"}">${r.keep ? "Kept" : "Dropped"} on review: ${escapeHtml(r.reason ?? "")}</li>` : "";
  const code = c ? `<li>Code: complexity ${c.complexity} · innovation ${c.innovation}${c.fork_of ? ` · fork of ${escapeHtml(c.fork_of)}` : ""}</li>` : "";
  const codeSummary = c?.summary ? `<li>${escapeHtml(c.summary)}</li>` : "";
  const codeGood = (c?.strengths ?? []).map((x) => `<li data-tone="good">${escapeHtml(x)}</li>`).join("");
  const codeBad = (c?.concerns ?? []).map((x) => `<li data-tone="bad">${escapeHtml(x)}</li>`).join("");
  const good = (j?.strengths ?? []).map((x) => `<li data-tone="good">${escapeHtml(x)}</li>`).join("");
  const bad = (j?.problems ?? []).map((x) => `<li data-tone="bad">${escapeHtml(x)}</li>`).join("");
  const admit = j?.admit_reason ? `<li data-tone="good">${escapeHtml(j.admit_reason)}</li>` : "";
  return `<div class="ds-report"><h5>Scout${head ? ` <b>${head}</b>` : ""}</h5>
    <ul class="why-list">${edit}${admit}${code}${codeSummary}${codeGood}${codeBad}${good}${bad}${socialLines(j)}</ul></div>`;
}

export function gemWhy(e) {
  const blocks = [...PILLARS, ["traction", "Traction"]].map(([k, label]) => {
    const v = k === "traction" ? e.traction?.traction : e.pillars?.[k]?.score;
    if (v == null) return "";
    return `<li><span>${label}</span><i style="--v:${Math.round(v)}"></i><b>${Math.round(v)}</b></li>`;
  }).join("");
  const flags = Object.values(e.pillars ?? {}).flatMap((p) => p?.flags ?? []);
  return `<div class="why-score"><span class="ring" style="--v:${Math.round(e.score ?? 0)}"><b>${Math.round(e.score ?? 0)}</b></span>
      <p><b>${e.top_rank ? `Top #${e.top_rank}` : e.early ? "Early gem" : e.top_rank === null ? "Not in the Top right now" : `Rank #${e.rank ?? "—"}`}</b><small>${e.early ? "Under $300k and past every other bar of the Top: smaller and riskier." : "Usage, holders, code, research and tokenomics, scored every day."}</small></p></div>
    <ul class="bars">${blocks}</ul>
    ${e.summary ? `<p class="dt-summary">${escapeHtml(e.summary)}</p>` : ""}
    ${deepseekBlock(e)}
    ${(e.traction?.reasons ?? []).length ? `<ul class="why-list">${e.traction.reasons.map((r) => `<li data-tone="good">${escapeHtml(r)}</li>`).join("")}</ul>` : ""}
    ${flags.length ? `<ul class="why-list">${flags.map((f) => `<li data-tone="bad">${escapeHtml(f)}</li>`).join("")}</ul>` : ""}
    <p class="muted">Research, not advice.</p>`;
}

function gemRow(e) {
  const id = `gem:${e.chain}:${e.token_address}`;
  register(id, {
    kind: "gem", symbol: e.symbol, name: e.name, chain: e.chain, token: e.token_address, pair: e.pair_address,
    pairUrl: e.pair_url, image: e.image, cap: e.market_cap, change: e.change_24h != null ? e.change_24h / 100 : null,
    ageTs: e.launched_at, context: `Rank #${e.rank ?? "—"} · score ${Math.round(e.score ?? 0)} · liquidity ${usd(e.liquidity_usd)}`,
    why: gemWhy(e), info: details(e),
  });
  const nar = (e.narratives ?? []).slice().sort((a, b) => b.heat - a.heat)[0];
  return tokenRow({ id, symbol: e.symbol, name: e.name, chain: e.chain, token: e.token_address, image: e.image,
    cap: e.market_cap, ageTs: e.launched_at, badge: e.early ? "early" : null, sign: "",
    sub: nar ? `<span class="bd-nar">${escapeHtml(nar.label)}</span>` : "",
    pill: `<em class="chg score">${Math.round(e.score ?? 0)}</em>` });
}

/** Scores count up from where they were (or from 0) instead of jumping. */
const shown = new Map();
function countUp() {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  root.querySelectorAll("[data-num]").forEach((el) => {
    const id = el.closest("[data-board]")?.dataset.board ?? "";
    const to = Number(el.dataset.num);
    const from = shown.get(id) ?? 0;
    shown.set(id, to);
    if (from === to) return;
    const t0 = performance.now();
    const step = (t) => {
      const p = Math.min(1, (t - t0) / 900);
      el.textContent = String(Math.round(from + (to - from) * (1 - (1 - p) ** 3)));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
}

/** Pointer-driven tilt and light, only where there is a real pointer. */
function tilt(event) {
  const card = event.target.closest?.(".board-podium button, .board-list button");
  if (!card) return;
  const r = card.getBoundingClientRect();
  const x = (event.clientX - r.left) / r.width;
  const y = (event.clientY - r.top) / r.height;
  card.style.setProperty("--mx", `${x * 100}%`);
  card.style.setProperty("--my", `${y * 100}%`);
  if (card.closest(".board-podium")) {
    card.style.setProperty("--ry", `${(x - 0.5) * 10}deg`);
    card.style.setProperty("--rx", `${(0.5 - y) * 8}deg`);
  }
}
function untilt(event) {
  const card = event.target.closest?.(".board-podium button, .board-list button");
  if (card && !card.contains(event.relatedTarget)) ["--rx", "--ry"].forEach((v) => card.style.removeProperty(v));
}

function fact(label, value) {
  return value == null || value === "" ? "" : `<div><dt>${label}</dt><dd>${value}</dd></div>`;
}

function pillarBlock(e, k, label) {
  const p = e.pillars?.[k] ?? {};
  const f = p.facts ?? {};
  let rows = "";
  if (k === "github") {
    rows = fact("Repository", f.url ? `<a href="${escapeHtml(f.url)}" target="_blank" rel="noopener">${escapeHtml(f.repo)}</a>` : null)
      + fact("Commits, 90 days", f.commits_90d) + fact("Active weeks (of 12)", f.active_weeks_12)
      + fact("Authors", Math.max(f.authors ?? 0, f.contributors ?? 0)) + fact("Last commit", f.last_commit_days == null ? null : `${f.last_commit_days} d ago`)
      + fact("Code", f.code_kb == null ? null : `${f.code_kb} KB · ${(f.languages ?? []).join(", ")}`)
      + fact("Test · CI", `${yes(f.tests)} · ${yes(f.ci)}`) + fact("Trivial commits", f.trivial_pct == null ? null : `${f.trivial_pct}%`)
      + fact("Stars", f.stars);
  } else if (k === "site") {
    rows = fact(f.reader ? "Reading" : "Claude's read", f.ai_substance == null ? null : `${f.ai_substance}/10 · ${escapeHtml(f.verdict ?? "")}`)
      + fact("Description", f.description_score == null ? null : `${f.description_score}/100 · ${f.description?.words ?? 0} words`)
      + fact("Sites read", f.sites_read) + fact("Holders", f.holders)
      + fact("Website", f.url ? `<a href="${escapeHtml(f.url)}" target="_blank" rel="noopener">${escapeHtml(new URL(f.url).hostname)}</a>` : null)
      + fact("Words", f.words) + fact("Internal pages", f.internal_pages == null ? null : `${f.internal_pages} · ${f.pages_ok ?? 0} load with content`)
      + fact("Docs", f.docs == null ? null : f.docs_ok ? "yes, reachable" : f.docs ? "linked, empty" : "no")
      + fact("App", f.app == null ? null : f.app_ok ? "yes, responds" : f.app ? "linked, not responding" : "no")
      + fact("Sections", (f.sections ?? []).join(", ") || null)
      + fact("Domain", f.domain_days == null ? null : `registered ${f.domain_days} d ago`);
  } else {
    // The split behind the 40% limit (Lorenzo, 19/10): the top 10 of every
    // holder, then what is held by contracts / program accounts (left out of
    // the limit), then the wallets the limit is measured on.
    rows = fact("Top wallet", f.top1_pct == null ? null : `${f.top1_pct}%`)
      + fact("Top 10, all holders", f.top10_all_pct == null ? null : `${f.top10_all_pct}%`)
      + fact("In contracts / programs", f.contracts_pct == null ? null : `${f.contracts_pct}%`)
      + fact(f.top10_all_pct == null ? "Top 10" : "Top 10 wallets", f.top10_pct == null ? null : `${f.top10_pct}%`)
      + fact("Creator", f.creator_pct == null ? null : `${f.creator_pct}%`) + fact("Holder", f.holders)
      + fact("Locked liquidity", f.lp_locked_pct == null ? null : `${f.lp_locked_pct}%`)
      + fact("Mint · freeze", f.mint == null ? null : `${f.mint ? "active" : f.mint_by ? `by ${escapeHtml(f.mint_by)}` : "revoked"} · ${f.freeze ? "active" : "revoked"}`)
      + fact("Tax", f.tax_pct == null ? null : `${f.tax_pct}%`);
  }
  const flags = [...(p.flags ?? []), ...(f.red_flags ?? [])].map((x) => `<li>${escapeHtml(x)}</li>`).join("");
  const why = k === "site" && f.why?.length ? `<p class="bd-why">${escapeHtml(f.why.join(" · "))}</p>` : "";
  return `<section style="--v:${p.score ?? 0}"><h5>${label}<b>${score(p.score)}</b></h5><dl>${rows}</dl>${why}
    ${flags ? `<ul class="bd-flags">${flags}</ul>` : ""}</section>`;
}

export function details(e) {
  const chart = e.pair_url ? `<a href="${escapeHtml(e.pair_url)}" target="_blank" rel="noopener">Chart</a>` : "";
  const scan = e.scan_url ? `<a href="${escapeHtml(e.scan_url)}" target="_blank" rel="noopener">Security report</a>` : "";
  return `<header><b>${escapeHtml(e.name ?? e.symbol)}</b>
      <small>${CHAINS[e.chain] ?? e.chain} · launched ${since(e.launched_at)} ago · liquidity ${usd(e.liquidity_usd)}${e.change_24h != null ? ` · 24h ${e.change_24h > 0 ? "+" : ""}${e.change_24h}%` : ""}</small>
      <span>${chart}${scan}</span></header>
    ${e.honor ? `<p class="bd-honor" style="text-align:start;margin:0 0 12px">${escapeHtml(e.honor)}</p>` : ""}
    ${e.summary ? `<p class="bd-summary">${escapeHtml(e.summary)}${e.stage && e.stage !== "unclear" ? ` <em>${escapeHtml(e.stage)}</em>` : ""}</p>` : ""}
    ${deepseekBlock(e)}
    ${traits(e)}
    <div class="bd-pillars">${PILLARS.map(([k, label]) => pillarBlock(e, k, label)).join("")}${tractionBlock(e)}</div>`;
}

/** Use and price, from DefiLlama. Absent for most microcaps: no block, no verdict. */
function tractionBlock(e) {
  const t = e.traction;
  if (!t) return "";
  const f = t.facts ?? {};
  const rows = fact("TVL", f.tvl == null ? null : usd(f.tvl)) + fact("Fees, 30 days", f.fees_30d == null ? null : usd(f.fees_30d))
    + fact("TVL, 7 days", f.tvl_change_7d == null ? null : `${f.tvl_change_7d > 0 ? "+" : ""}${Math.round(f.tvl_change_7d)}%`)
    + fact("Cap ÷ yearly fees", f.mcap_to_fees == null ? null : `${f.mcap_to_fees}×`)
    + fact("Cap ÷ TVL", f.mcap_to_tvl == null ? null : `${f.mcap_to_tvl}×`)
    + fact("Value", t.value == null ? null : `${Math.round(t.value)}/100`);
  return `<section class="bd-use" style="--v:${t.traction ?? 0}"><h5>Traction<b>${score(t.traction)}</b></h5><dl>${rows}</dl>
    ${t.reasons?.length ? `<p class="bd-why">${escapeHtml(t.reasons.join(" · "))}</p>` : ""}</section>`;
}

/** Early gems first: under $300k with every other bar of the board. */
function paintEarly(entries) {
  const box = root.querySelector("[data-board-early]");
  if (!box) return;
  const early = entries.filter((e) => e.early);
  box.hidden = !early.length;
  box.innerHTML = early.length ? `<b>Early gems · ${early.length}</b> Under $300k and past every other bar of the Top: smaller and riskier, sized to lose.
    <span>${early.map((e) => `<button type="button" data-board="${escapeHtml(key(e))}">${escapeHtml(e.symbol)} · ${usd(e.market_cap)}</button>`).join("")}</span>` : "";
}

const signed = (f) => (f == null ? "—" : `${f > 0 ? "+" : ""}${Math.round(f * 100)}%`);

/** What happened to what the board ranked: 7, 30, 90 days after entry. */
function paintTrack() {
  const box = root.querySelector("[data-board-track]");
  if (!box) return;
  const h = (data?.track?.horizons ?? []).filter((x) => x.all?.n);
  box.hidden = false;
  if (!h.length) {
    box.innerHTML = `<p class="track-note">Track record starts now: every project that enters the board is followed for 7, 30 and 90 days, top ten against the rest.</p>`;
    return;
  }
  box.innerHTML = `<dl class="track-grid">${h.map((x) => `<div class="track-stat"><dt>After ${x.days} days</dt>
      <dd><b data-sign="${(x.top.median ?? 0) >= 0 ? "up" : "down"}">${signed(x.top.median)}</b><small>top 10 median · ${x.top.n}</small></dd>
      <p>rest ${signed(x.rest.median)} · ${Math.round((x.all.doubled ?? 0) * 100)}% doubled · ${x.all.n} tracked</p></div>`).join("")}</dl>
    <p class="track-note">Price change since each project first entered the board. Research, not a promise.</p>`;
}

function traits(e) {
  const t = e.similarity?.traits ?? [];
  if (!t.length) return "";
  const head = e.benchmark ? "The benchmark" : `Technical similarity to DREGG · ${e.similarity.score}%`;
  return `<p class="bd-honor" style="text-align:start;margin:0 0 6px">${head}</p><ul class="bd-traits">${t.map((x) =>
    `<li data-got="${x.got >= 1 ? "1" : x.got > 0 ? "half" : "0"}">${escapeHtml(x.label)}</li>`).join("")}</ul>`;
}

function paintAges() {
  root.querySelectorAll("[data-age]").forEach((el) => {
    const ts = Number(el.dataset.age);
    if (ts) el.textContent = since(ts);
  });
  paintMeta();
}

function paintMeta() {
  const meta = root.querySelector("[data-board-meta]");
  const d = data ?? {};
  const gh = d.github_rate?.core;
  const starved = !gh ? "" : !d.github_rate.token || gh.limit <= 60 ? " · GitHub limited: no token"
    : gh.remaining === 0 ? " · GitHub paused" : "";
  meta.textContent = `${d.examined ?? 0} examined${d.past_floor ? ` · ${d.past_floor} under study` : ""}${d.analyzing ? ` · ${d.analyzing} under analysis` : ""}${starved}`;
}

// What the researcher is looking at right now and why each is not in yet:
// an empty board should still show the work.
function paintClose() {
  const box = root.querySelector("[data-board-close]");
  if (!box) return;           // a cached page from before this block existed
  const rows = (data?.close ?? []).filter((c) => c.research != null);
  box.hidden = !rows.length;
  box.querySelector("ul").innerHTML = rows.map((c) => `<li><b>${escapeHtml(c.symbol ?? "?")}</b>
    <span>${c.research}${c.verdict ? ` · ${escapeHtml(c.verdict)}` : ""}${c.market_cap ? ` · ${usd(c.market_cap)}` : ""}</span>
    <small>${escapeHtml(c.why)}</small></li>`).join("");
}

function emptyText() {
  const d = data ?? {};
  return d.waiting
    ? `No project has passed the full analysis yet. ${d.waiting} waiting on data (GitHub, RugCheck or website).`
    : "No project has passed the GitHub, website and tokenomics checks yet.";
}
