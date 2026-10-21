/**
 * Quality (Lorenzo, 21/10): the projects of quality 80 or more that are not
 * in his Top 25, whatever their score or usage, for him to accept into the
 * gems or discard. An accepted one skips only the score's bars: every other
 * gem rule still holds, and it leaves when it fails one ("Se Dregg domani
 * dovesse avere un crollo [...] esce"). His account only: the server answers
 * 404 to the others, and the dock button stays hidden.
 */
import * as api from "@onchain/api.js";
import { register } from "@onchain/detail.js";
import { escapeHtml, tokenRow } from "@onchain/format.js";

const POLL_MS = 60_000;
const WHERE = { top: "In the Top 25", arena: "In the arenas", early: "In Early", out: "Out" };
const PILLARS = { github: "GitHub", site: "Site", tokenomics: "Holders" };

let box = null;
let data = null;
let busy = false;

function line(e) {
  const p = e.pillars ?? {};
  const parts = [`Quality ${Math.round(e.quality ?? 0)}`,
    ...Object.entries(PILLARS).filter(([k]) => p[k] != null).map(([k, label]) => `${label} ${Math.round(p[k])}`)];
  return escapeHtml(parts.join(" · "));
}

function row(e, actions, note = "") {
  const id = `gem:${e.chain}:${e.token_address}`;
  const change = e.change_24h != null ? e.change_24h / 100 : null;
  register(id, { kind: "gem", symbol: e.symbol, name: e.name, chain: e.chain, token: e.token_address, pair: e.pair_address,
    fdv: e.fdv, pairUrl: e.pair_url, image: e.image, cap: e.market_cap, change, ageTs: e.launched_at,
    context: `Quality ${Math.round(e.quality ?? 0)} · score ${Math.round(e.score ?? 0)}` });
  const li = tokenRow({ id, symbol: e.symbol, name: e.name || e.symbol, chain: e.chain, token: e.token_address,
    image: e.image, cap: e.market_cap, change, ageTs: e.launched_at, score: e.score, capTag: true });
  const key = `data-chain="${escapeHtml(e.chain)}" data-token="${escapeHtml(e.token_address)}"`;
  const buttons = actions.map(([act, label]) =>
    `<button type="button" class="q-btn" data-q-act="${act}" ${key}>${label}</button>`).join("");
  // The pillars under the row, whole: in the row's subline a phone cut them.
  const text = [line(e), note].filter(Boolean).join("<br>");
  return li.replace(/<\/li>$/, `<div class="q-act"><span class="q-note">${text}</span>${buttons}</div></li>`);
}

function paint() {
  if (!box || !data) return;
  const waiting = data.waiting ?? [];
  const accepted = data.accepted ?? [];
  const discarded = data.discarded ?? [];
  box.querySelector("[data-quality-rows]").innerHTML = waiting.map((e) => row(e, [["accept", "Accept"], ["discard", "Discard"]],
    e.where === "arena" ? "Already in the arenas" : e.where === "early" ? "Already in Early" : "")).join("");
  box.querySelector("[data-quality-empty]").hidden = waiting.length > 0;
  box.querySelector("[data-quality-accepted]").innerHTML = accepted.map((e) => row(e, [["reset", "Undo"]],
    escapeHtml(e.where === "out" ? `Out: ${e.why ?? ""}` : WHERE[e.where] ?? ""))).join("");
  box.querySelector("[data-quality-accepted-head]").hidden = accepted.length === 0;
  const fold = box.querySelector("[data-quality-discarded-fold]");
  fold.hidden = discarded.length === 0;
  fold.querySelector("summary small").textContent = String(discarded.length);
  fold.querySelector("[data-quality-discarded]").innerHTML = discarded.map((e) => row(e, [["reset", "Restore"]])).join("");
}

async function load() {
  try {
    data = await api.getQuality();
  } catch (error) {
    if (error?.status === 404) document.querySelector('#dock [data-go="quality"]')?.setAttribute("hidden", "");
    return;
  }
  document.querySelector('#dock [data-go="quality"]')?.removeAttribute("hidden");
  paint();
}

const shown = () => document.getElementById("app-shell")?.dataset.view === "quality" && document.visibilityState === "visible";

export function mountQuality() {
  box = document.querySelector("[data-quality-view]");
  if (!box) return;
  box.addEventListener("click", async (event) => {
    const b = event.target.closest("[data-q-act]");
    if (!b || busy) return;
    event.stopPropagation();
    busy = true;
    b.disabled = true;
    try {
      await api.decideQuality(b.dataset.chain, b.dataset.token, b.dataset.qAct);
      await load();
    } catch {
      b.disabled = false;
    } finally {
      busy = false;
    }
  });
  const shell = document.getElementById("app-shell");
  if (shell) new MutationObserver(() => { if (shown()) load(); }).observe(shell, { attributes: true, attributeFilter: ["data-view"] });
  load();
  setInterval(() => { if (shown()) load(); }, POLL_MS);
}
