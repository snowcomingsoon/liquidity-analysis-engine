import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import * as api from "../lib/api";
import { askPush } from "../lib/push";
import type { Candle, Deep, Entry, Gem, RecheckProgress } from "../lib/types";
import { age, changeText, usdShort } from "../lib/format";
import { setTokenHidden } from "../lib/store";
import { DS_EMBED, INTERVALS, cached, chartFor, embedUrl, forget, liveQuote, type Interval, type Market } from "../lib/chart";
import { Glance } from "../components/Glance";
import { Logo } from "../components/Logo";
import { CandleChart } from "../components/CandleChart";
import { SellsMap } from "../components/SellsMap";
import { DeepResult, DossierHead, Details, InfoFallback, WhyOf } from "./Dossier";

// The token page (detail.js): a full screen with the identity, the market-cap
// candles, the Why and Info tabs from the dossier, the deep re-check and the
// way out to DexScreener. No Signal tab: trading is off (07/10).

import { WATCH_KEY } from "../lib/watchKey";
const LIVE_MS = 60_000;
const LOG_LINES = 4;

export type Opened = { e: Gem; context?: string };

export const watchId = (e: Gem) => `gem:${e.chain}:${e.token_address}`;
export function watched(): Set<string> { try { return new Set(JSON.parse(localStorage.getItem(WATCH_KEY) || "[]")); } catch { return new Set(); } }
export function toggleWatch(id: string) {
  const w = watched();
  if (w.has(id)) w.delete(id); else w.add(id);
  try { localStorage.setItem(WATCH_KEY, JSON.stringify([...w])); } catch { /* private mode */ }
  return w.has(id);
}
// The same link the Telegram alerts use: whoever opens it signed in lands on this token.
export const tokenLink = (e: Gem) => `${location.origin}/onchain-app.html#gems&token=${encodeURIComponent(e.chain)}:${encodeURIComponent(e.token_address)}`;

async function copy(text: string) {
  try { await navigator.clipboard.writeText(text); return true; } catch {
    // In-app browsers (Telegram) without the clipboard API: a hidden textarea.
    const ta = Object.assign(document.createElement("textarea"), { value: text, readOnly: true });
    ta.style.cssText = "position:fixed;opacity:0";
    document.body.append(ta);
    ta.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch { ok = false; }
    ta.remove();
    return ok;
  }
}

const Icon = ({ d, className = "h-5 w-5" }: { d: string; className?: string }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>
);
const OUT = "M14 4h6v6M20 4l-9 9M18 14v6H4V6h6";

type Chart = { state: "loading" } | { state: "candles"; candles: Candle[]; shown: Interval } | { state: "embed"; pair: string } | { state: "none"; text: string };
type Recheck = { busy: boolean; own: boolean; failed: boolean; steps: RecheckProgress["steps"]; log: RecheckProgress["log"]; started?: number };

export function TokenPage({ open, onClose }: { open: Opened; onClose: () => void }) {
  const e = open.e;
  const m: Market = { chain: e.chain, token: e.token_address, symbol: e.symbol, pair: e.pair_address };
  const [tab, setTab] = useState<"why" | "info">("why");
  const tabs = useRef<HTMLElement>(null);
  const [entry, setEntry] = useState<Entry | null>(null);
  const [loading, setLoading] = useState(true);
  const [deep, setDeep] = useState<Deep | null>(null);
  const [wait, setWait] = useState(0);
  const [rc, setRc] = useState<Recheck>({ busy: false, own: false, failed: false, steps: [], log: [] });
  const rcRef = useRef(rc);
  rcRef.current = rc;
  const [live, setLive] = useState<{ cap?: number; change?: number; supply?: number; pair?: string }>({});
  const [interval, setIv] = useState<Interval>("1d");
  const [chart, setChart] = useState<Chart>({ state: "loading" });
  const [libFailed, setLibFailed] = useState(false);
  const [watch, setWatch] = useState(() => watched().has(watchId(e)));
  const [copied, setCopied] = useState<"" | "yes" | "no">("");
  const alive = useRef(true);
  const want = useRef("");

  useEffect(() => () => { alive.current = false; }, []);

  // Back on the phone closes the page, as the original's dialog.
  useEffect(() => {
    history.pushState({ detail: 1 }, "");
    const pop = () => onClose();
    addEventListener("popstate", pop);
    return () => removeEventListener("popstate", pop);
  }, [onClose]);
  const close = () => { if (history.state?.detail) history.back(); else onClose(); };

  // The dossier: Why and Info complete whichever list opened the page.
  useEffect(() => {
    api.getToken(e.chain, e.token_address).then((r) => {
      if (!alive.current) return;
      setEntry(r.entry);
      if (r.deep) setDeep(r.deep);
      if (r.deep_wait_s != null) setWait(r.deep_wait_s);
      // A re-check still running (the weekly round, or one started before the page closed): follow it.
      if (r.deep_progress?.running) {
        rcRef.current = { ...rcRef.current, busy: true, ...take(r.deep_progress) };
        setRc(rcRef.current);
        follow();
      }
    }).catch(() => {}).finally(() => alive.current && setLoading(false));
  }, [e.chain, e.token_address]);

  const paint = useCallback(async (iv: Interval) => {
    const key = `${iv}:${Date.now()}`;
    want.current = key;
    const stale = cached(m, iv);
    if (stale && stale.length >= 2) setChart({ state: "candles", candles: stale, shown: iv });
    let candles: Candle[] = [];
    let shown = iv;
    // No candles on this interval (1m on a quiet pool): step up instead of the embed (28/09).
    for (const x of INTERVALS.slice(INTERVALS.indexOf(iv))) {
      try { candles = await chartFor(m, x); } catch { candles = []; }
      if (want.current !== key || !alive.current) return;
      if (candles.length >= 2) { shown = x; break; }
    }
    if (candles.length >= 2) { setChart({ state: "candles", candles, shown }); return; }
    if (stale) return;
    const pair = m.pair || live.pair;
    setChart(pair && DS_EMBED.has(m.chain) ? { state: "embed", pair } : { state: "none", text: "No trades to chart yet." });
  }, [e.chain, e.token_address, live.pair]);

  useEffect(() => { paint(interval); }, [interval, paint]);

  // Live market: on opening and every minute, cap and change from DexScreener, candles fetched again.
  useEffect(() => {
    let first = true;
    const tick = async () => {
      if (document.visibilityState !== "visible") return;
      const q = await liveQuote(m).catch(() => null);
      if (!alive.current) return;
      if (q) setLive({ cap: q.cap, change: q.change, supply: q.supply, pair: q.pair });
      if (!first) { forget(m, interval); paint(interval); }
      first = false;
    };
    tick();
    const t = setInterval(tick, LIVE_MS);
    return () => clearInterval(t);
  }, [e.chain, e.token_address, interval]);

  function take(p?: RecheckProgress | null): Partial<Recheck> {
    return { ...(p?.steps ? { steps: p.steps } : {}), ...(p?.log ? { log: p.log } : {}), ...(p?.started ? { started: p.started } : {}) };
  }

  // Polls the server's steps while the re-check runs; without our own request
  // in flight (page reopened, weekly round) it also fetches the result.
  const following = useRef(false);
  async function follow() {
    if (following.current) return;
    following.current = true;
    try {
      while (alive.current && rcRef.current.busy) {
        try {
          const p = (await api.recheckProgress(e.chain, e.token_address)).progress;
          if (p?.steps && alive.current) setRc((x) => ({ ...x, ...take(p) }));
          if (p && !p.running && !rcRef.current.own) {
            const r = await api.getToken(e.chain, e.token_address);
            if (r.deep) setDeep(r.deep);
            if (r.deep_wait_s != null) setWait(r.deep_wait_s);
            setRc((x) => ({ ...x, busy: false }));
            break;
          }
        } catch { /* the next poll tries again */ }
        await new Promise((res) => setTimeout(res, 700));
      }
    } finally { following.current = false; }
  }

  // The re-check is a job on the server (bg.js): it goes on with the app closed.
  async function recheck() {
    askPush();
    if (!entry || rc.busy || wait > 0) return;
    const busy: Recheck = { busy: true, own: true, failed: false, steps: [], log: [], started: Date.now() / 1000 };
    rcRef.current = busy;
    setRc(busy);
    follow();
    const view = `gems&token=${encodeURIComponent(e.chain)}:${encodeURIComponent(e.token_address)}&tab=why`;
    let job: { state: string; result?: { deep?: Deep }; detail?: { wait_s?: number } };
    try {
      const r = await api.recheckJob(e.chain, e.token_address, { view, label: (e.symbol ?? "").slice(0, 40) });
      job = r.job ? await pollJob(r.job) : { state: "finito", result: r };
    } catch (err) { job = { state: "fallito", detail: (err as api.ApiError).detail as { wait_s?: number } }; }
    if (!alive.current) return;
    if (job.state === "finito" && job.result?.deep) { setDeep(job.result.deep); setWait(0); }
    else if (job.detail?.wait_s) setWait(job.detail.wait_s);
    else {
      setRc((x) => ({ ...x, busy: false, own: false, failed: true }));
      setTimeout(() => alive.current && setRc((x) => ({ ...x, failed: false })), 4000);
      return;
    }
    // Let the last step land on screen before the verdict replaces the list.
    await new Promise((res) => setTimeout(res, 600));
    setRc((x) => ({ ...x, busy: false, own: false }));
  }
  async function pollJob(id: string) {
    for (;;) {
      try {
        const j = await api.getJob(id);
        if (j.state !== "in corso") return j;
      } catch (err) {
        if ((err as api.ApiError).status === 404) return { state: "fallito", error: "the task was lost, run it again" };
      }
      if (!alive.current) return { state: "fallito" };
      await new Promise((res) => setTimeout(res, 2000));
    }
  }

  const sym = e.symbol || entry?.symbol || e.token_address.slice(0, 6);
  const name = e.name || entry?.name || sym;
  const cap = live.cap ?? e.market_cap ?? entry?.market_cap;
  const [chg, sign] = changeText(live.change ?? e.change_24h ?? entry?.change_24h);
  const pairUrl = e.pair_url || entry?.pair_url;
  const dex = pairUrl || `https://dexscreener.com/${e.chain}/${e.token_address}`;
  const [a] = age(e.launched_at ?? entry?.launched_at);
  const born = e.launched_at ?? entry?.launched_at;
  const last = chart.state === "candles" ? chart.candles[chart.candles.length - 1].close : 0;
  const k = live.supply || (cap && last ? cap / last : 1);
  const note = chart.state === "candles" && chart.shown !== interval ? `No ${interval} candles for this token: showing ${chart.shown}.` : "";

  async function share() {
    const url = tokenLink(e);
    if (navigator.share) {
      try { await navigator.share({ title: sym, text: `${sym} on DEGEN`, url }); return; }
      catch (err) { if ((err as Error).name === "AbortError") return; }
    }
    flash(await copy(url));
  }
  function flash(ok: boolean) { setCopied(ok ? "yes" : "no"); setTimeout(() => alive.current && setCopied(""), 1600); }

  return (
    <motion.div role="dialog" aria-label="Token" aria-modal="true" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }}
      transition={{ duration: 0.18 }} className="fixed inset-0 z-40 flex flex-col bg-bg">
      <header className="flex h-14 flex-none items-center gap-2 px-4 pt-[env(safe-area-inset-top)]">
        <button type="button" onClick={close} aria-label="Back" className="-ml-2 grid h-10 w-10 place-items-center"><Icon d="m15 5-7 7 7 7" className="h-6 w-6" /></button>
        <span className="flex min-w-0 flex-1 items-center gap-2.5 text-[16px] font-medium text-text-2">
          <b className="truncate font-medium">{open.context?.split(" · score")[0] || sym}</b>
          {born && <><i className="h-4 w-px bg-line" /><span className="flex items-center gap-0.5 text-text-3">
            <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={1.4} strokeLinecap="round" aria-hidden="true"><path d="M8 14V7M8 9c0-3 2-4.5 5-4.5 0 3-2 4.5-5 4.5ZM8 8C8 5.5 6.3 4 3.5 4c0 2.6 1.7 4 4.5 4Z" /></svg>{a}</span></>}
        </span>
        <span className="flex gap-2">
          <Round label="Hide from my lists" onClick={() => { setTokenHidden(e.chain, e.token_address, true); close(); }}
            d="M3 3l18 18M10.6 6.1A9.8 9.8 0 0 1 12 6c5 0 8.5 4 9.5 6-.5 1-1.6 2.6-3.3 3.9M6.2 7.6C4.3 8.9 3 10.8 2.5 12c1 2 4.5 6 9.5 6 1.5 0 2.9-.4 4.1-1M9.9 9.9a3 3 0 0 0 4.2 4.2" />
          <Round label="Watch" pressed={watch} onClick={() => setWatch(toggleWatch(watchId(e)))} d="m12 3.5 2.6 5.4 5.9.8-4.3 4.1 1 5.8L12 16.8 6.8 19.6l1-5.8L3.5 9.7l5.9-.8z" />
          <Round label={copied === "yes" ? "Link copied" : "Share"} onClick={share} d="M12 15V3.5M8 7.5l4-4 4 4M6 11H5v9.5h14V11h-1" />
        </span>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-28">
        <section className="mt-5 flex items-center gap-3">
          <span className="w-[44px]"><Logo size={44} symbol={sym} image={e.image ?? entry?.image} chain={e.chain} token={e.token_address} /></span>
          <span className="min-w-0 flex-1">
            <b className="block truncate text-[18px] font-semibold">{name}</b>
            <small className="mt-1 flex items-center gap-2 text-[14px] text-text-2">
              <button type="button" onClick={async () => flash(await copy(e.token_address))} title="Copy address">{sym}</button>
              <button type="button" onClick={async () => flash(await copy(e.token_address))} aria-label={copied === "yes" ? "Address copied" : copied === "no" ? "Copy failed" : "Copy address"}
                title={e.token_address} className="flex items-center gap-1 rounded-full bg-pill px-2 py-0.5 text-[13px] font-medium">
                {copied === "yes" ? <Icon d="m5 12.5 4.5 4.5L19 7.5" className="h-3.5 w-3.5 text-up" /> : <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden="true"><rect x="8" y="8" width="11" height="11" rx="2" /><path d="M16 8V5H5v11h3" /></svg>}
                <span>{copied === "yes" ? "Copied" : `${e.token_address.slice(0, 4)}…${e.token_address.slice(-4)}`}</span>
              </button>
              {pairUrl && <a href={pairUrl} target="_blank" rel="noopener" aria-label="Open chart"><Icon d={OUT} className="h-4 w-4" /></a>}
            </small>
          </span>
          <span className="flex flex-none flex-col items-end">
            <small className="text-[12px] text-text-3">MC</small>
            <b className="num text-[18px] font-semibold">{usdShort(cap)}</b>
            <em className={`num text-[13px] font-medium not-italic ${sign === "up" ? "text-up" : sign === "down" ? "text-down" : "text-text-3"}`}>{chg}</em>
          </span>
        </section>
        {entry && <Glance e={entry} />}
        <div className="mb-2 mt-4 flex items-center justify-between">
          <h3 className="text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">Price</h3>
          <div className="flex gap-1">
            {INTERVALS.map((iv) => (
              <button key={iv} type="button" aria-pressed={iv === interval} onClick={() => setIv(iv)}
                className={`h-7 rounded-full px-2.5 text-[12.5px] font-medium transition-colors ${iv === interval ? "bg-ink text-on-ink" : "bg-pill text-text-2"}`}>{iv}</button>
            ))}
          </div>
        </div>
        <div className="h-[240px] overflow-hidden rounded-[16px] bg-card">
          {chart.state === "candles" && !libFailed && <CandleChart candles={chart.candles} k={k} onFail={() => setLibFailed(true)} />}
          {chart.state === "candles" && libFailed && <Line candles={chart.candles} k={k} />}
          {chart.state === "embed" && <iframe className="h-full w-full rounded-[20px] border-0" src={embedUrl(e.chain, chart.pair, interval)} title={`${sym} chart on DexScreener`} loading="lazy" referrerPolicy="no-referrer" />}
          {(chart.state === "loading" || chart.state === "none") && (
            <div className="grid h-full place-items-center text-[14px] text-text-3">{chart.state === "none" ? chart.text : "Loading chart…"}</div>
          )}
        </div>
        {note && <p className="mt-1 text-[13px] text-text-3">{note}</p>}
        <SellsMap chain={e.chain} token={e.token_address} />
        <nav ref={tabs} className="mt-[18px] flex scroll-mt-4 gap-1 rounded-full bg-pill p-1">
          {(["why", "info"] as const).map((t) => (
            <button key={t} type="button" aria-current={tab === t ? "true" : undefined} onClick={() => setTab(t)}
              className={`relative h-9 flex-1 rounded-full text-[14px] font-medium ${tab === t ? "text-text" : "text-text-2"}`}>
              {tab === t && <motion.span layoutId="dt-tab" className="absolute inset-0 rounded-full bg-card shadow-[0_1px_2px_rgb(0_0_0/.06)]" transition={{ type: "spring", stiffness: 520, damping: 42 }} />}
              <span className="relative">{t === "why" ? "Why" : "Info"}</span>
            </button>
          ))}
        </nav>

        <div className="pt-2">
          {tab === "why" ? (
            <>
              {entry ? <WhyOf e={entry} deep={deep} /> : <p className="text-[14px] text-text-2">{loading ? "Loading…" : "Nothing to add yet."}</p>}
              {entry && (
                <div>
                  <DossierHead title="Deep re-check" right={deep ? `${deep.verdict ?? ""} · ${deep.score ?? "—"}/100` : undefined} />
                  {deep && <DeepResult d={deep} />}
                  <RecheckButton rc={rc} wait={wait} onClick={recheck} />
                </div>
              )}
            </>
          ) : entry ? <Details e={entry} /> : <InfoFallback chain={e.chain} token={e.token_address} pairUrl={pairUrl} />}
        </div>
      </div>

      <div className="pointer-events-none absolute inset-x-0 bottom-0 px-4 pb-[calc(env(safe-area-inset-bottom)+12px)] pt-5" style={{ background: "linear-gradient(transparent, var(--c-bg) 18px)" }}>
        <div className="pointer-events-auto flex gap-2">
          <button type="button" onClick={() => tabs.current?.scrollIntoView({ behavior: "smooth", block: "start" })} className="h-12 flex-1 rounded-full bg-pill text-[15px] font-semibold">Why · Info</button>
          <a href={dex} target="_blank" rel="noopener" className="flex h-12 flex-1 items-center justify-center rounded-full bg-ink text-[15px] font-semibold text-on-ink">DexScreener ↗</a>
        </div>
      </div>
    </motion.div>
  );
}

function Round({ label, d, onClick, pressed }: { label: string; d: string; onClick: () => void; pressed?: boolean }) {
  return (
    <button type="button" aria-label={label} aria-pressed={pressed} onClick={onClick}
      className={`grid h-10 w-10 place-items-center rounded-full ${pressed ? "bg-ink text-on-ink" : "bg-pill text-text"}`}>
      <Icon d={d} />
    </button>
  );
}

// The re-check's live log on the button itself (08/10: "voglio vedere cosa fa, cosa sta navigando").
function RecheckButton({ rc, wait, onClick }: { rc: Recheck; wait: number; onClick: () => void }) {
  const [, tick] = useState(0);
  useEffect(() => { if (!rc.busy) return; const t = setInterval(() => tick((x) => x + 1), 1000); return () => clearInterval(t); }, [rc.busy]);
  const base = "mt-4 block min-h-12 w-full rounded-full px-5 text-[15px] font-medium";
  if (rc.busy) {
    const steps = rc.steps ?? [];
    const lastStep = steps[steps.length - 1];
    const secs = rc.started ? Math.max(0, Math.round(Date.now() / 1000 - rc.started)) : 0;
    return (
      <button type="button" disabled data-busy className={`${base} rounded-[24px] bg-ink py-3 text-left text-[12px] font-normal leading-[1.35] text-on-ink`}>
        <span aria-live="polite" className="block">
          <span className="flex justify-between gap-3"><b className="truncate font-mono">&gt; {lastStep ? `${lastStep.label}${lastStep.detail ? ` · ${lastStep.detail}` : ""}` : "Starting"}</b>
            <em className="flex-none not-italic opacity-70">{steps.length ? `step ${steps.length} · ` : ""}{secs}s</em></span>
          {(rc.log ?? []).slice(-LOG_LINES).map((x) => (
            <motion.span key={x.n} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="mt-1 flex gap-2 font-mono">
              <i className="flex-none not-italic opacity-60">{x.src}</i><span className="min-w-0 flex-1 truncate">{x.text}</span>
              <em className={`flex-none not-italic ${x.code == null ? "opacity-60" : x.code < 400 ? "text-sage" : "text-down"}`}>{x.code == null ? "…" : x.code}</em>
            </motion.span>
          ))}
        </span>
      </button>
    );
  }
  const label = rc.failed ? "Re-check failed" : wait > 0 ? (wait >= 3600 ? `Re-check in ${Math.round(wait / 3600)}h` : `Re-check in ${Math.max(1, Math.round(wait / 60))}m`) : "Deep re-check";
  return <button type="button" disabled={rc.failed || wait > 0} onClick={onClick} className={`${base} bg-pill text-text disabled:text-text-3`}>{label}</button>;
}

/** The fallback line when the chart library cannot load (detail.js svgChart). */
function Line({ candles, k }: { candles: Candle[]; k: number }) {
  const W = 360, H = 260, R = 58, T = 14, B = 18;
  const ys = candles.map((c) => c.close * k);
  let lo = Math.min(...ys), hi = Math.max(...ys);
  if (hi === lo) { hi *= 1.05; lo *= 0.95; }
  const pad = (hi - lo) * 0.08;
  lo -= pad; hi += pad;
  const t0 = candles[0].time, t1 = candles[candles.length - 1].time;
  const x = (t: number) => ((t - t0) / Math.max(1, t1 - t0)) * (W - R);
  const y = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const d = candles.map((c, i) => `${i ? "L" : "M"}${x(c.time).toFixed(1)},${y(ys[i]).toFixed(1)}`).join("");
  const up = ys[ys.length - 1] >= ys[0];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" role="img" aria-label="Market cap chart">
      {[0, 1, 2, 3, 4].map((i) => { const v = lo + ((hi - lo) * i) / 4; return <text key={i} x={W - 4} y={y(v) + 4} textAnchor="end" className="fill-text-3 text-[10px]">{usdShort(v)}</text>; })}
      <path d={d} fill="none" strokeWidth={1.6} className={up ? "stroke-up" : "stroke-down"} />
    </svg>
  );
}
