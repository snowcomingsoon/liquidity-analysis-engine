/**
 * Bubble map of a token's wallet clusters (Lorenzo, 22/10: "inserisci
 * rappresentazione grafica molto fluida per identificare questi cluster";
 * then "potevi fare meglio la grafica"). One bubble per wallet, its area the
 * share of supply it holds. Linked clusters sit in colour around the centre,
 * each named with its share; holders with no link found stay grey in the
 * middle, only the largest TOP_N, the rest folded into one "+N others"
 * bubble. Bubble sizes are scaled to fill the frame without overlapping. A
 * legend under the canvas names every group.
 *
 * Canvas, so 60 fps: frames run only while the layout settles or a
 * highlight fades, then the loop stops. With reduced motion the layout is
 * computed at once and drawn a single time.
 * Also loaded by the React app (frontend/app-next, SellsMap.tsx) from
 * /static/onchain/: one map for both apps.
 */

const PALETTE = ["--c-down", "--k-amber,--c-amber", "#3b82f6", "#a855f7", "#14b8a6", "#ec4899"];
const FALLBACK = ["#ef4444", "#eab308"];
const NEUTRAL = "--c-text-3,--c-text";   // holders with no link found
const TOP_N = 24;                         // grey holders drawn one by one
const FILL = 0.34;                        // share of the frame the bubbles cover
const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const pct = (x) => `${(x * 100).toFixed(x < 0.01 ? 2 : 1)}%`;

function colour(el, token, i) {
  if (!token.startsWith("--")) return token;
  // "--a,--b": the first one the page defines (the classic app and /app name some differently).
  const css = getComputedStyle(el);
  for (const t of token.split(",")) { const v = css.getPropertyValue(t).trim(); if (v) return v; }
  return FALLBACK[i] || "#888";
}

const WORDS = { cluster: "Cluster", wallets: "wallets", nolink: "No link found", none: "No linked wallets among the top holders." };

export function clusterMap(host, report, { onPick, words } = {}) {
  const w = { ...WORDS, ...words };
  const canvas = document.createElement("canvas");
  canvas.className = "cs-map-canvas";
  canvas.setAttribute("role", "img");
  const legend = document.createElement("ul");
  legend.className = "cs-map-legend";
  legend.style.cssText = "display:flex;flex-wrap:wrap;gap:6px 14px;margin:0;padding:10px 14px 12px;list-style:none;font-size:12px;line-height:1.3;opacity:.85";
  host.replaceChildren(canvas, legend);
  const ctx = canvas.getContext("2d");

  let real = [], top = null, list = [], edges = [], groups = [];
  const nodes = new Map();
  const sync = (rep) => {
    real = rep.clusters.filter((c) => c.id !== "top" && c.wallets.length);
    top = rep.clusters.find((c) => c.id === "top") || null;
    const seen = new Set();
    const put = (id, share, cluster, extra) => {
      seen.add(id);
      const n = nodes.get(id);
      // A wallet already drawn keeps its place and drifts to its (new) cluster.
      if (n) Object.assign(n, { share, cluster }, extra);
      else nodes.set(id, { id, share, cluster, x: NaN, y: 0, vx: 0, vy: 0, a: 1, ta: 1, grow: 0, ...extra });
    };
    real.forEach((c) => c.wallets.forEach((w) => { if (!seen.has(w.address)) put(w.address, w.share ?? 0, c); }));
    const loose = (top?.wallets ?? []).filter((w) => !seen.has(w.address)).sort((a, b) => (b.share ?? 0) - (a.share ?? 0));
    loose.slice(0, TOP_N).forEach((w) => put(w.address, w.share ?? 0, top));
    const rest = loose.slice(TOP_N);
    if (rest.length) put("others", rest.reduce((s, w) => s + (w.share ?? 0), 0), top, { others: rest.length, members: rest.map((w) => w.address) });
    for (const k of [...nodes.keys()]) if (!seen.has(k)) nodes.delete(k);
    list = [...nodes.values()];
    edges = [];
    real.forEach((c) => (c.edges ?? []).forEach(([a, b]) => {
      if (nodes.has(a) && nodes.has(b)) edges.push([nodes.get(a), nodes.get(b)]);
    }));
    groups = [...real, ...(top && loose.length ? [top] : [])];
    canvas.setAttribute("aria-label", `${real.length} linked cluster(s) among ${list.length} holder bubbles`);
  };
  sync(report);

  let W = 0, H = 0, unit = 1, raf = 0, ticks = 0;
  const anchors = new Map();
  const colours = new Map();
  const shareOf = (c) => c.share ?? c.wallets.reduce((s, w) => s + (w.share ?? 0), 0);

  function measure() {
    const dpr = Math.min(2, devicePixelRatio || 1);
    W = host.clientWidth || 320;
    H = Math.round(Math.min(360, Math.max(240, W * 0.7)));
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.height = `${H}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    // Areas add up to FILL of the frame, and no bubble wider than 30% of the short side.
    const total = list.reduce((s, n) => s + n.share, 0) || 1e-6;
    const biggest = Math.max(1e-6, ...list.map((n) => n.share));
    unit = Math.min(Math.sqrt(FILL * W * H / (Math.PI * total)), Math.min(W, H) * 0.15 / Math.sqrt(biggest));
    // Grey holders in the middle, each linked cluster on a ring around them.
    const packR = (ns) => Math.sqrt(ns.reduce((s, n) => s + radius(n) ** 2, 0)) * 1.25;
    const greyR = top ? packR(list.filter((n) => n.cluster === top)) : 0;
    const side = Math.min(W, H);
    real.forEach((c, i) => {
      const r = packR(list.filter((n) => n.cluster === c));
      const ring = Math.min(Math.max(greyR + r + 14, side * 0.22), side / 2 - r - 10);
      // Left and right first: the frame is wider than tall.
      const t = real.length === 1 ? 0 : Math.PI + (i / real.length) * Math.PI * 2;
      anchors.set(c, { x: W / 2 + Math.cos(t) * ring * Math.min(1.5, W / H), y: H / 2 + Math.sin(t) * ring });
      colours.set(c, colour(canvas, PALETTE[i % PALETTE.length], i));
    });
    if (top) { anchors.set(top, { x: W / 2, y: H / 2 }); colours.set(top, colour(canvas, NEUTRAL, -1)); }
    drawLegend();
  }
  const radius = (n) => Math.max(n.cluster === top ? 2.5 : 5, Math.sqrt(n.share) * unit);

  function drawLegend() {
    const item = (c, label) => `<li style="display:flex;align-items:center;gap:6px"><i style="inline-size:10px;block-size:10px;border-radius:50%;background:${colours.get(c)};opacity:${c === top ? .45 : .85}"></i>${label}</li>`;
    legend.innerHTML = real.map((c, i) => item(c, `<b>${w.cluster} ${i + 1}</b>&nbsp;${c.wallets.length} ${w.wallets} · ${pct(shareOf(c))}`)).join("")
      + (top && groups.includes(top) ? item(top, w.nolink) : "")
      + (real.length ? "" : `<li>${w.none}</li>`);
  }

  function seed() {
    list.forEach((n, i) => {
      if (!Number.isNaN(n.x)) return;
      const a = anchors.get(n.cluster);
      const t = i * 2.399963;           // golden angle: an even spiral, no random
      const r = 4 * Math.sqrt(i + 1);
      n.x = a.x + Math.cos(t) * r; n.y = a.y + Math.sin(t) * r;
    });
  }

  function step() {
    for (const n of list) {
      const a = anchors.get(n.cluster);
      const k = n.cluster === top ? 0.02 : 0.03;
      n.vx += (a.x - n.x) * k; n.vy += (a.y - n.y) * k;
    }
    for (const [p, q] of edges) {
      const dx = q.x - p.x, dy = q.y - p.y, d = Math.hypot(dx, dy) || 1;
      const f = (d - (radius(p) + radius(q) + 6)) * 0.01;
      p.vx += dx / d * f; p.vy += dy / d * f; q.vx -= dx / d * f; q.vy -= dy / d * f;
    }
    let energy = 0;
    for (const n of list) {
      n.vx *= 0.8; n.vy *= 0.8;
      n.x += n.vx; n.y += n.vy;
      energy += n.vx * n.vx + n.vy * n.vy;
    }
    // Overlaps are solved last, on positions: forces never push bubbles into each other.
    for (let pass = 0; pass < 4; pass++) for (let i = 0; i < list.length; i++) {
      const p = list[i], rp = radius(p);
      for (let j = i + 1; j < list.length; j++) {
        // Different groups keep a wider gap, so each cluster reads as one.
        const q = list[j], gap = p.cluster === q.cluster ? 1.5 : 6;
        const dx = q.x - p.x, dy = q.y - p.y, min = rp + radius(q) + gap;
        const d2 = dx * dx + dy * dy;
        if (d2 >= min * min) continue;
        const d = Math.sqrt(d2) || 0.01, push = (min - d) / d * 0.5;
        p.x -= dx * push; p.y -= dy * push; q.x += dx * push; q.y += dy * push;
      }
    }
    for (const n of list) {
      const r = radius(n);
      n.x = Math.min(W - r - 2, Math.max(r + 2, n.x)); n.y = Math.min(H - r - 2, Math.max(r + 16, n.y));
    }
    return energy;
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    ctx.lineWidth = 1.5;
    for (const [p, q] of edges) {
      ctx.globalAlpha = 0.6 * Math.min(p.a, q.a) * Math.min(p.grow, q.grow);
      ctx.strokeStyle = colours.get(p.cluster);
      ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
    }
    for (const n of list) {
      const r = radius(n) * n.grow, c = colours.get(n.cluster);
      if (r <= 0) continue;
      const grey = n.cluster === top;
      ctx.globalAlpha = (grey ? 0.16 : 0.62) * n.a;
      ctx.fillStyle = c;
      ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2); ctx.fill();
      ctx.globalAlpha = (grey ? 0.35 : 0.95) * n.a;
      ctx.strokeStyle = c;
      ctx.lineWidth = n.ring ? 2.5 : 1;
      if (n.others) ctx.setLineDash([3, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
      if (n.others && r > 12) {
        ctx.globalAlpha = 0.8 * n.a;
        ctx.fillStyle = c;
        ctx.font = "600 11px system-ui, sans-serif";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(`+${n.others}`, n.x, n.y);
      }
    }
    // Each linked cluster's name and share, over its bubbles.
    ctx.font = "600 11.5px system-ui, sans-serif";
    ctx.textAlign = "center"; ctx.textBaseline = "bottom";
    real.forEach((c, i) => {
      const ns = list.filter((n) => n.cluster === c && n.grow > 0.5);
      if (!ns.length) return;
      const x = ns.reduce((s, n) => s + n.x, 0) / ns.length;
      const y = Math.min(...ns.map((n) => n.y - radius(n)));
      ctx.globalAlpha = Math.max(...ns.map((n) => n.a));
      ctx.fillStyle = colours.get(c);
      ctx.fillText(`${w.cluster} ${i + 1} · ${pct(shareOf(c))}`, Math.min(W - 50, Math.max(50, x)), Math.max(13, y - 4));
    });
    ctx.globalAlpha = 1;
  }

  function frame() {
    const energy = ticks < 500 ? step() : 0;
    ticks++;
    let moving = false;
    for (const n of list) {
      if (n.grow < 1) { n.grow = Math.min(1, n.grow + 0.06); moving = true; }
      if (Math.abs(n.ta - n.a) > 0.01) { n.a += (n.ta - n.a) * 0.18; moving = true; } else n.a = n.ta;
    }
    draw();
    raf = (moving || (energy > 0.01 && ticks < 500)) ? requestAnimationFrame(frame) : 0;
  }
  const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };

  function settleNow() {
    for (ticks = 0; ticks < 400; ticks++) step();
    list.forEach((n) => { n.grow = 1; n.a = n.ta; });
    draw();
  }

  measure(); seed();
  if (still()) settleNow(); else kick();

  const ro = new ResizeObserver(() => {
    const w = host.clientWidth;
    if (!w || w === W) return;
    measure(); ticks = 0;
    if (still()) settleNow(); else kick();
  });
  ro.observe(host);

  canvas.addEventListener("click", (event) => {
    const box = canvas.getBoundingClientRect();
    const x = event.clientX - box.left, y = event.clientY - box.top;
    const hit = list.find((n) => Math.hypot(n.x - x, n.y - y) <= Math.max(8, radius(n)));
    list.forEach((n) => { n.ring = n === hit; });
    onPick?.(hit ? { address: hit.id, share: hit.share, cluster: hit.cluster,
      others: hit.others ?? 0, label: hit.others ? `${hit.others} smaller holders, no link found` : null } : null);
    if (still()) draw(); else kick();
  });

  return {
    /** Light up these wallets (a Set of addresses), or every one with null. */
    highlight(addresses) {
      list.forEach((n) => { n.ta = !addresses || addresses.has(n.id) || n.members?.some((m) => addresses.has(m)) ? 1 : 0.12; });
      if (still()) { list.forEach((n) => { n.a = n.ta; }); draw(); } else kick();
    },
    colourOf: (cluster) => colours.get(cluster),
    /** A newer report of the same token (a check filling live): new wallets
     *  grow in, known ones keep their place and drift to their cluster. */
    update(next) {
      sync(next); measure(); seed(); ticks = 0;
      if (still()) settleNow(); else kick();
    },
    destroy() { cancelAnimationFrame(raf); ro.disconnect(); },
  };
}
