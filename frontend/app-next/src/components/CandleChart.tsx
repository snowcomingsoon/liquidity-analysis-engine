import { useEffect, useRef } from "react";
import type { Candle } from "../lib/types";
import { usdShort } from "../lib/format";

// The main site's engine (detail.js drawChart): TradingView Lightweight Charts,
// the same build the original app loads, candles in market-cap terms.
const LIB = "/static/lightweight-charts.standalone.production.js";
const MIN_BAR_PX = 7;   // narrowest candle the chart opens with

declare global { interface Window { LightweightCharts?: any } }
let loading: Promise<any> | null = null;
function lib(): Promise<any> {
  if (window.LightweightCharts) return Promise.resolve(window.LightweightCharts);
  loading ??= new Promise((resolve, reject) => {
    const s = Object.assign(document.createElement("script"), { src: LIB, async: true });
    s.onload = () => resolve(window.LightweightCharts);
    s.onerror = () => { loading = null; reject(new Error("chart library failed")); };
    document.head.append(s);
  });
  return loading;
}

// The canvas cannot read CSS: the colours come from the app's tokens (chart-theme.js).
function theme() {
  const s = getComputedStyle(document.documentElement);
  const v = (n: string, f: string) => s.getPropertyValue(n).trim() || f;
  return { up: v("--c-up", "#2f7a4a"), down: v("--c-down", "#b4472f"), faint: v("--c-text-3", "#687264"), line: v("--c-line", "#e0d9cb"),
    raised: v("--c-pill", "#e4dfd3"), font: getComputedStyle(document.body).fontFamily };
}
const chartOptions = (t = theme()) => ({
  layout: { background: { color: "transparent" }, textColor: t.faint, fontSize: 11, fontFamily: t.font, attributionLogo: false },
  grid: { vertLines: { visible: false }, horzLines: { color: t.line, style: 2 } },
  crosshair: { vertLine: { color: t.faint, style: 2, labelBackgroundColor: t.raised }, horzLine: { color: t.faint, style: 2, labelBackgroundColor: t.raised } },
});
const seriesOptions = (t = theme()) => ({ upColor: t.up, downColor: t.down, borderVisible: false, wickUpColor: t.up, wickDownColor: t.down });

/** Candles scaled by `k` (supply): prices read as market cap. `onFail` when the library cannot load. */
export function CandleChart({ candles, k, onFail }: { candles: Candle[]; k: number; onFail: () => void }) {
  const box = useRef<HTMLDivElement>(null);
  const lw = useRef<{ chart: any; series: any; k: number } | null>(null);
  const first = useRef(true);

  useEffect(() => {
    let dead = false;
    lib().then((LC) => {
      if (dead || !box.current) return;
      const t = theme();
      const chart = LC.createChart(box.current, {
        ...chartOptions(t), autoSize: true,
        rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.08 } },
        timeScale: { timeVisible: true, secondsVisible: false, borderVisible: false, rightOffset: 8 },
        handleScale: { axisPressedMouseMove: false },
      });
      const series = chart.addCandlestickSeries({
        ...seriesOptions(t),
        // Market cap when the cap is known, else the raw price; never below zero.
        priceFormat: { type: "custom", minMove: 1e-10,
          formatter: (v: number) => (v < 0 ? "" : lw.current?.k === 1 && Math.abs(v) < 1 ? `$${Number(v.toPrecision(3))}` : usdShort(v)) },
        autoscaleInfoProvider: (original: () => any) => {
          const r = original();
          if (r?.priceRange) r.priceRange.minValue = Math.max(0, r.priceRange.minValue);
          return r;
        },
      });
      lw.current = { chart, series, k };
      first.current = true;
      draw();
    }, onFail);
    // A new theme (dark mode): repaint on the next frame, once the tokens apply.
    const repaint = () => requestAnimationFrame(() => {
      const t = theme();
      lw.current?.chart.applyOptions(chartOptions(t));
      lw.current?.series.applyOptions(seriesOptions(t));
    });
    const mo = new MutationObserver(repaint);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => { dead = true; mo.disconnect(); try { lw.current?.chart.remove(); } catch { /* gone */ } lw.current = null; };
  }, []);

  function draw() {
    const c = lw.current;
    if (!c || candles.length < 2) return;
    c.k = k;
    const bars = candles.map((x) => {
      const close = x.close * k;
      const open = (Number.isFinite(x.open) ? x.open : x.close) * k;
      return { time: x.time, open, close,
        high: Math.max(open, close, (Number.isFinite(x.high) ? x.high : x.close) * k),
        low: Math.min(open, close, (Number.isFinite(x.low) ? x.low : x.close) * k) };
    });
    c.series.setData(bars);
    // A year of daily bars on a phone is a row of dots (07/10): open on the
    // latest bars at a readable width, older ones a swipe away.
    if (first.current) {
      first.current = false;
      const ts = c.chart.timeScale();
      const fit = Math.floor((box.current?.clientWidth || 360) / MIN_BAR_PX);
      if (bars.length <= fit) ts.fitContent();
      else ts.setVisibleLogicalRange({ from: bars.length - fit, to: bars.length - 1 + 8 });
    }
  }

  // New candles or a new scale: same chart, new data; a new interval opens on its latest bars.
  const span = candles.length > 1 ? candles[1].time - candles[0].time : 0;
  useEffect(() => { first.current = true; }, [span]);
  useEffect(draw);

  return <div ref={box} className="h-full w-full" />;
}
