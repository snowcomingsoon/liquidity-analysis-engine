/**
 * Coordinated sells (Lorenzo, 22/10): the wallet clusters of a token, how
 * much of the supply they hold, when they sold together, and the token's
 * risk. The engine writes the reports (coordinated_sells.py has the format);
 * until it does, the server answers with a sample, marked as such.
 * Whitekobra's only: the server answers 404 to the others. Reached from
 * a pill at the top of Scout, #sells, and the Telegram alert.
 */
import * as api from "@onchain/api.js";
import { clusterMap } from "@onchain/cluster-map.js";
import { escapeHtml } from "@onchain/format.js";

const POLL_MS = 60_000;
const LINKS = { same_funder: "Same funder", same_block_sells: "Same-block sells", same_amounts: "Same amounts" };

let box = null;
let maps = [];
let shownSig = "";

const pct = (x) => (x == null ? "—" : `${(x * 100).toFixed(x < 0.01 ? 2 : 1)}%`);
const short = (a) => (a.length > 12 ? `${a.slice(0, 6)}…${a.slice(-4)}` : a);
const level = (s) => (s == null ? "" : s >= 70 ? "high" : s >= 40 ? "mid" : "low");
const usd = (v) => (v == null ? "" : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${Math.round(v / 1e3)}k` : `$${Math.round(v)}`);

function ago(ts) {
  const s = Date.now() / 1000 - ts;
  if (s < 3600) return `${Math.max(1, Math.round(s / 60))}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return new Date(ts * 1000).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// Colour slot of a cluster, the same on the map, the dots and the bar:
// real clusters in order, the top-holders group grey.
const slot = (r, c) => (c?.id === "top" ? "top" : String(r.clusters.filter((x) => x.id !== "top").indexOf(c) % 6));

function report(r, idx) {
  const real = r.clusters.filter((c) => c.id !== "top");
  const name = (c) => (c?.id === "top" ? "Top holders" : `Cluster ${real.indexOf(c) + 1}`);
  const byId = Object.fromEntries(r.clusters.map((c) => [c.id, c]));
  // A wallet can sit in a cluster and in the top holders: count it once.
  const shares = new Map(r.clusters.flatMap((c) => c.wallets.map((w) => [w.address, w.share ?? 0])));
  const held = [...shares.values()].reduce((t, v) => t + v, 0);
  const owner = new Map();          // each wallet in the bar once, in its first cluster
  [...real, ...r.clusters.filter((c) => c.id === "top")].forEach((c) => c.wallets.forEach((w) => { if (!owner.has(w.address)) owner.set(w.address, c); }));
  const part = (c) => [...owner].reduce((t, [a, o]) => t + (o === c ? shares.get(a) : 0), 0);
  const score = r.risk?.score;
  const bar = r.clusters.map((c, i) =>
    `<i class="cs-seg" data-i="${slot(r, c)}" style="--w:${(part(c) * 100).toFixed(2)}%"></i>`).join("");
  const clusters = r.clusters.map((c) => `
    <details class="cs-cluster">
      <summary><i class="cs-dot" data-i="${slot(r, c)}"></i><b>${name(c)}</b>
        <span>${c.wallets.length} wallets · ${pct(c.share)}</span>
        <em data-level="${level(c.risk)}">${c.risk == null ? "" : Math.round(c.risk)}</em></summary>
      <p class="cs-links">${c.links.map((l) => `<span>${escapeHtml(LINKS[l] ?? l.replace(/_/g, " "))}</span>`).join("")}</p>
      <ol class="cs-wallets">${c.wallets.map((w) =>
        `<li><code title="${escapeHtml(w.address)}">${escapeHtml(short(w.address))}</code><span>${pct(w.share)}</span></li>`).join("")}</ol>
    </details>`).join("");
  const events = r.events.map((e, i) => {
    const c = byId[e.cluster];
    const win = e.window_s == null ? "" : e.window_s >= 60 ? ` in ${Math.round(e.window_s / 60)} min` : ` in ${Math.round(e.window_s)} s`;
    return `<li data-ev="${i}" tabindex="0"><i class="cs-dot" data-i="${slot(r, c)}"></i>
      <p><b>${name(c)} sold ${pct(e.share_sold)}</b><small>${e.wallets} wallets${win}${e.usd ? ` · ${usd(e.usd)}` : ""}</small></p>
      <time>${ago(e.ts)}</time></li>`;
  }).join("");
  const title = r.symbol ? escapeHtml(r.symbol) : `<code>${escapeHtml(short(r.token))}</code>`;
  return `<article class="cs-card" data-card="${idx}">
    <header class="cs-head">
      <p><b>${title}</b><small>${escapeHtml(r.chain.charAt(0).toUpperCase() + r.chain.slice(1))}${r.updated_at ? ` · updated ${ago(r.updated_at)}` : ""}</small></p>
      <p class="cs-risk" data-level="${level(score)}" style="--r:${(score ?? 0) / 100}"><b>${score == null ? "—" : Math.round(score)}</b><small>risk</small><i></i></p>
    </header>
    <div class="cs-map" data-map="${idx}" aria-label="Wallet bubble map"></div>
    <p class="cs-pick" data-pick>Bubble size = share of supply held. Tap a bubble or a sell.</p>
    ${r.risk?.reasons?.length ? `<ul class="cs-why">${r.risk.reasons.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul>` : ""}
    <h4>Supply held by clusters <span>${pct(held)}</span></h4>
    <div class="cs-bar" aria-hidden="true">${bar}</div>
    ${clusters}
    <h4>Sells together <span>${r.events.length}</span></h4>
    ${events ? `<ol class="cs-time">${events}</ol>` : `<p class="early-empty">No coordinated sell yet.</p>`}
  </article>`;
}

async function load() {
  let data;
  try {
    data = await api.getCoordinatedSells();
  } catch (error) {
    if (error?.status === 404) document.getElementById("sells-entry")?.setAttribute("hidden", "");
    return;
  }
  const entry = document.getElementById("sells-entry");
  if (entry) {
    const top = Math.max(-1, ...(data.reports ?? []).map((r) => r.risk?.score ?? -1));
    entry.hidden = false;
    entry.dataset.level = level(top < 0 ? null : top);
    entry.querySelector("[data-sells-entry-risk]").textContent = top < 0 ? "" : `risk ${Math.round(top)}`;
  }
  box.querySelector("[data-sells-sample]").hidden = !data.sample;
  box.querySelector("[data-sells-empty]").hidden = (data.reports ?? []).length > 0;
  const reports = data.reports ?? [];
  // Same reports as on screen: leave the map alone, no new entrance.
  const sig = JSON.stringify(reports.map((r) => [r.token, r.updated_at]));
  if (sig === shownSig) return;
  shownSig = sig;
  const open = new Set([...box.querySelectorAll(".cs-cluster[open] b")].map((b) => b.textContent));
  maps.forEach((m) => m.destroy());
  box.querySelector("[data-sells-rows]").innerHTML = reports.map(report).join("");
  box.querySelectorAll(".cs-cluster b").forEach((b) => { if (open.has(b.textContent)) b.closest("details").open = true; });
  maps = reports.map((r, i) => mountMap(r, box.querySelector(`[data-card="${i}"]`)));
}

function mountMap(r, card) {
  const pick = card.querySelector("[data-pick]");
  const hint = pick.textContent;
  const real = r.clusters.filter((c) => c.id !== "top");
  const map = clusterMap(card.querySelector("[data-map]"), r, {
    onPick(hit) {
      pick.textContent = hit
        ? hit.label ? `${hit.label} · ${pct(hit.share)} of supply together` : `${short(hit.address)} · ${pct(hit.share)} of supply · ${hit.cluster.id === "top" ? "top holder, no link found" : `Cluster ${real.indexOf(hit.cluster) + 1}`}`
        : hint;
    },
  });
  let lit = null;
  const light = (li) => {
    card.querySelectorAll(".cs-time li[aria-current]").forEach((x) => x.removeAttribute("aria-current"));
    const e = li && li !== lit ? r.events[Number(li.dataset.ev)] : null;
    lit = e ? li : null;
    if (!e) { map.highlight(null); pick.textContent = hint; return; }
    li.setAttribute("aria-current", "true");
    const c = r.clusters.find((x) => x.id === e.cluster);
    const who = e.sellers?.length ? e.sellers : (c?.wallets ?? []).map((w) => w.address);
    map.highlight(new Set(who));
    pick.textContent = `${e.sellers?.length ? `${e.sellers.length} wallets sold` : "Its cluster"} ${pct(e.share_sold)} · ${ago(e.ts)}`;
  };
  card.querySelector(".cs-time")?.addEventListener("click", (ev) => light(ev.target.closest("[data-ev]")));
  card.querySelector(".cs-time")?.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); light(ev.target.closest("[data-ev]")); }
  });
  return map;
}

const shown = () => ["sells", "agent"].includes(document.getElementById("app-shell")?.dataset.view) && document.visibilityState === "visible";

async function upload(input) {
  const msg = box.querySelector("[data-sells-upload-msg]");
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  msg.textContent = "Uploading…";
  try {
    const r = await api.uploadCluster(JSON.parse(await file.text()));
    msg.textContent = `Saved: ${r.wallets ?? "?"} wallets. The first read takes a few minutes.`;
  } catch (error) {
    msg.textContent = error instanceof SyntaxError ? "Not a JSON file." : `Not saved: ${error?.message ?? "error"}`;
  }
}

export function mountSells() {
  box = document.querySelector("[data-sells-view]");
  if (!box) return;
  box.querySelector("[data-sells-upload]")?.addEventListener("change", (event) => upload(event.target));
  const shell = document.getElementById("app-shell");
  if (shell) new MutationObserver(() => { if (shown()) load(); }).observe(shell, { attributes: true, attributeFilter: ["data-view"] });
  load();
  setInterval(() => { if (shown()) load(); }, POLL_MS);
}
