/**
 * Bubble map of a token's wallet clusters (Lorenzo, 22/10: "inserisci
 * rappresentazione grafica molto fluida per identificare questi cluster").
 * One bubble per wallet, its area the share of supply it holds, its colour
 * its cluster; lines join wallets the engine linked (cluster.edges, when
 * the report has them). A wave of the timeline lights up the wallets that
 * sold in it (event.sellers), or its whole cluster.
 *
 * Canvas, so 60 fps with hundreds of bubbles: frames run only while the
 * layout settles or a highlight fades, then the loop stops. With reduced
 * motion the layout is computed at once and drawn a single time.
 * Also loaded by the React app (frontend/app-next, SellsMap.tsx) from
 * /static/onchain/: one map for both apps.
 */

const PALETTE = ["--c-down", "--k-amber,--c-amber", "#60a5fa", "#c084fc", "#2dd4bf", "#f472b6"];
const FALLBACK = ["#ef4444", "#facc15"];
const NEUTRAL = "--c-text";          // the top-holders group: no link found
const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

function colour(el, token, i) {
  if (!token.startsWith("--")) return token;
  // "--a,--b": the first one the page defines (the classic app and /app name some differently).
  const css = getComputedStyle(el);
  for (const t of token.split(",")) { const v = css.getPropertyValue(t).trim(); if (v) return v; }
  return FALLBACK[i] || "#888";
}

export function clusterMap(host, report, { onPick } = {}) {
  const canvas = document.createElement("canvas");
  canvas.className = "cs-map-canvas";
  canvas.setAttribute("role", "img");
  host.replaceChildren(canvas);
  const ctx = canvas.getContext("2d");

  // Real clusters first; the top-holders group only colours who is in no other.
  let real = [], order = [], list = [], edges = [];
  const nodes = new Map();
  const sync = (rep) => {
    real = rep.clusters.filter((c) => c.id !== "top");
    order = [...real, ...rep.clusters.filter((c) => c.id === "top")];
    const seen = new Set();
    order.forEach((c) => c.wallets.forEach((w) => {
      if (seen.has(w.address)) return;
      seen.add(w.address);
      const n = nodes.get(w.address);
      // A wallet already drawn keeps its place and drifts to its (new) cluster.
      if (n) { n.cluster = c; n.share = w.share ?? n.share; } else nodes.set(w.address, { id: w.address, share: w.share ?? 0, cluster: c, x: NaN, y: 0, vx: 0, vy: 0, a: 1, ta: 1, grow: 0 });
    }));
    for (const k of [...nodes.keys()]) if (!seen.has(k)) nodes.delete(k);
    list = [...nodes.values()];
    edges = [];
    rep.clusters.forEach((c) => (c.edges ?? []).forEach(([a, b]) => {
      if (nodes.has(a) && nodes.has(b)) edges.push([nodes.get(a), nodes.get(b)]);
    }));
    canvas.setAttribute("aria-label", `${list.length} wallets in ${real.length || 1} group(s)`);
  };
  sync(report);

  let W = 0, H = 0, unit = 1, raf = 0, ticks = 0;
  const anchors = new Map();
  const colours = new Map();

  function measure() {
    const dpr = Math.min(2, devicePixelRatio || 1);
    W = host.clientWidth || 320;
    H = Math.round(Math.min(380, Math.max(240, W * 0.72)));
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.height = `${H}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    // Bubble area ~ share: the largest holder gets ~11% of the shorter side.
    const top = Math.max(1e-6, ...list.map((n) => n.share));
    unit = Math.min(W, H) * 0.11 / Math.sqrt(top);
    const ring = order.length > 1 ? Math.min(W, H) * 0.28 : 0;
    order.forEach((c, i) => {
      const t = (i / order.length) * Math.PI * 2 - Math.PI / 2;
      anchors.set(c, { x: W / 2 + Math.cos(t) * ring * (W / Math.min(W, H)) * 0.8, y: H / 2 + Math.sin(t) * ring });
      colours.set(c, c.id === "top" ? colour(canvas, NEUTRAL, -1) : colour(canvas, PALETTE[real.indexOf(c) % PALETTE.length], real.indexOf(c)));
    });
  }
  const radius = (n) => Math.max(2.5, Math.sqrt(n.share) * unit);

  function seed() {
    list.forEach((n, i) => {
      if (!Number.isNaN(n.x)) return;
      const a = anchors.get(n.cluster);
      const t = i * 2.399963;           // golden angle: an even spiral, no random
      const r = 6 * Math.sqrt(i + 1);
      n.x = a.x + Math.cos(t) * r; n.y = a.y + Math.sin(t) * r;
    });
  }

  function step() {
    for (const n of list) {
      const a = anchors.get(n.cluster);
      n.vx += (a.x - n.x) * 0.012; n.vy += (a.y - n.y) * 0.012;
    }
    for (const [p, q] of edges) {
      const dx = q.x - p.x, dy = q.y - p.y, d = Math.hypot(dx, dy) || 1;
      const f = (d - (radius(p) + radius(q) + 10)) * 0.004;
      p.vx += dx / d * f; p.vy += dy / d * f; q.vx -= dx / d * f; q.vy -= dy / d * f;
    }
    for (let pass = 0; pass < 2; pass++) for (let i = 0; i < list.length; i++) {
      const p = list[i], rp = radius(p);
      for (let j = i + 1; j < list.length; j++) {
        const q = list[j], dx = q.x - p.x, dy = q.y - p.y, min = rp + radius(q) + 1.5;
        const d2 = dx * dx + dy * dy;
        if (d2 >= min * min) continue;
        const d = Math.sqrt(d2) || 0.01, push = (min - d) / d * 0.5;
        p.x -= dx * push; p.y -= dy * push; q.x += dx * push; q.y += dy * push;
      }
    }
    let energy = 0;
    for (const n of list) {
      n.vx *= 0.82; n.vy *= 0.82;
      n.x += n.vx; n.y += n.vy;
      const r = radius(n);
      n.x = Math.min(W - r - 2, Math.max(r + 2, n.x)); n.y = Math.min(H - r - 2, Math.max(r + 2, n.y));
      energy += n.vx * n.vx + n.vy * n.vy;
    }
    return energy;
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    ctx.lineWidth = 1;
    for (const [p, q] of edges) {
      ctx.globalAlpha = 0.35 * Math.min(p.a, q.a) * Math.min(p.grow, q.grow);
      ctx.strokeStyle = colours.get(p.cluster);
      ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
    }
    for (const n of list) {
      const r = radius(n) * n.grow, c = colours.get(n.cluster);
      if (r <= 0) continue;
      ctx.globalAlpha = (n.cluster.id === "top" ? 0.28 : 0.55) * n.a;
      ctx.fillStyle = c;
      ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2); ctx.fill();
      ctx.globalAlpha = 0.9 * n.a;
      ctx.strokeStyle = c;
      ctx.lineWidth = n.ring ? 2 : 1;
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  function frame() {
    const energy = ticks < 400 ? step() : 0;
    ticks++;
    let moving = false;
    for (const n of list) {
      if (n.grow < 1) { n.grow = Math.min(1, n.grow + 0.06); moving = true; }
      if (Math.abs(n.ta - n.a) > 0.01) { n.a += (n.ta - n.a) * 0.18; moving = true; } else n.a = n.ta;
    }
    draw();
    raf = (moving || (energy > 0.02 && ticks < 400)) ? requestAnimationFrame(frame) : 0;
  }
  const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };

  function settleNow() {
    for (ticks = 0; ticks < 300; ticks++) step();
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
    onPick?.(hit ? { address: hit.id, share: hit.share, cluster: hit.cluster } : null);
    if (still()) draw(); else kick();
  });

  return {
    /** Light up these wallets (a Set of addresses), or every one with null. */
    highlight(addresses) {
      list.forEach((n) => { n.ta = !addresses || addresses.has(n.id) ? 1 : 0.12; });
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
