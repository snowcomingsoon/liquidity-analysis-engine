import { useEffect, useRef, useState } from "react";
import * as api from "../lib/api";
import type { QueueItem, QueueLog } from "../lib/api";
import { STEPS } from "./CheckProgress";

const short = (a: string) => `${a.slice(0, 4)}…${a.slice(-4)}`;
const name = (x: { symbol?: string; token?: string }) => x.symbol || (x.token ? short(x.token) : "—");
const clock = (ts: number) => new Date(ts * 1000).toLocaleTimeString("en-GB", { hour12: false });
const TONE: Record<string, string> = { done: "text-up", failed: "text-down", start: "text-amber", phase: "text-[#aeb7a9]", queued: "text-[#7f8a7a]", pruned: "text-[#7f8a7a]" };
const KEEP = 200;

/** What the cluster engine does right now (Lorenzo, 22/10: "voglio vedere la
 *  coda [...] in real time con console in real time"): the checks running,
 *  the line, and a console of the engine's events, read every 2 s. */
export function ClusterQueue({ onOpen }: { onOpen: (chain: string, token: string, symbol?: string) => void }) {
  const [view, setView] = useState<api.ClusterQueue | null>(null);
  const [log, setLog] = useState<QueueLog[]>([]);
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLOListElement>(null);

  useEffect(() => {
    let live = true, t = 0, since = 0;
    const tick = () => api.getClusterQueue(since).then((v) => {
      if (!live) return;
      since = v.now;
      setView(v);
      if (v.log.length) setLog((l) => [...l, ...v.log].slice(-KEEP));
    }).catch(() => {}).finally(() => { if (live) t = window.setTimeout(tick, document.hidden ? 10000 : 2000); });
    tick();
    return () => { live = false; clearTimeout(t); };
  }, []);

  // The console follows the newest line unless the reader scrolled up.
  useEffect(() => {
    const el = box.current;
    if (el && el.scrollHeight - el.scrollTop - el.clientHeight < 60) el.scrollTop = el.scrollHeight;
  }, [log]);

  if (!view) return <div className="h-24 animate-pulse rounded-[16px] bg-card" />;
  const row = (x: QueueItem, i: number, now?: boolean) => {
    const step = STEPS.findIndex(([k]) => k === x.phase);
    return (
      <li key={`${x.chain}:${x.token}`}>
        <button type="button" onClick={() => onOpen(x.chain, x.token, x.symbol)} className="flex w-full items-center gap-2.5 rounded-[12px] px-2 py-2 text-left active:bg-pill">
          {now ? <i className="cp-spin h-3.5 w-3.5 flex-none rounded-full border-2 border-amber border-t-transparent" aria-hidden="true" />
            : <span className="num w-5 flex-none text-right text-[12px] text-text-3">{i + 1}</span>}
          <span className="min-w-0 flex-1">
            <b className="block truncate text-[14px] font-semibold">{name(x)} <span className="text-[12px] font-normal text-text-3">· {x.chain}</span></b>
            {now && <small className="block text-[12px] text-text-2">{x.phase === "waiting" ? "waiting for a slot" : step >= 0 ? `${STEPS[step][1]}${x.progress != null ? ` ${Math.round(x.progress * 100)}%` : "…"}` : "starting…"}</small>}
          </span>
          {x.manual && <span className="rounded-full bg-ink px-2 py-0.5 text-[11px] font-semibold text-on-ink">manual</span>}
          {x.section && <span className="rounded-full bg-pill px-2 py-0.5 text-[11px] capitalize text-text-2">{x.section}</span>}
          {now && step >= 0 && (
            <span className="relative h-1 w-12 flex-none overflow-hidden rounded-full bg-pill" aria-hidden="true">
              <i className="absolute inset-0 origin-left rounded-full bg-ink transition-transform duration-500" style={{ transform: `scaleX(${(step + (x.progress ?? 0.5)) / STEPS.length})` }} />
            </span>
          )}
        </button>
      </li>
    );
  };

  return (
    <section className="rounded-[16px] bg-card p-1.5">
      <div className="flex items-baseline gap-2 px-2 pb-1 pt-2">
        <b className="flex-1 text-[14px] font-semibold">Engine now</b>
        <small className="num text-[12px] text-text-3">{view.queued} in line · {view.built_today}/{view.max_per_day} today</small>
      </div>
      <ol>{view.running.length ? view.running.map((x, i) => row(x, i, true))
        : <li className="px-2 py-2 text-[13px] text-text-3">Nothing running right now.</li>}</ol>
      {view.queue.length > 0 && (
        <>
          <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-center px-2 py-2 text-left text-[12.5px] text-text-2">
            <span className="flex-1">Next in line: {view.queue.slice(0, 3).map(name).join(", ")}{view.queued > 3 ? ` and ${view.queued - 3} more` : ""}</span>
            <span className="text-text-3">{open ? "hide" : "show all"}</span>
          </button>
          {open && <ol className="max-h-[320px] overflow-y-auto">{view.queue.map((x, i) => row(x, i))}</ol>}
        </>
      )}
      <ol ref={box} aria-label="Engine console" aria-live="polite"
        className="mt-1 h-[180px] overflow-y-auto rounded-[12px] bg-ink px-3 py-2 font-mono text-[11.5px] leading-[1.55] text-[#d9e0d4]">
        {log.length ? log.map((e, i) => (
          <li key={`${e.ts}-${i}`} className="cq-line whitespace-pre-wrap break-words">
            <span className="text-[#7f8a7a]">{clock(e.ts)} </span>
            <span className={TONE[e.kind] ?? ""}>{e.kind.padEnd(6)}</span> {name(e)}{e.chain ? ` ${e.chain}` : ""}{e.msg ? ` · ${e.msg}` : ""}
          </li>
        )) : <li className="text-[#7f8a7a]">Waiting for the engine… new events show here as they happen.</li>}
      </ol>
    </section>
  );
}
