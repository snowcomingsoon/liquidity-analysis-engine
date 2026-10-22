import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import * as api from "../lib/api";
import { liveProject, recentProjects, type AgentInfo, type AgentItem } from "../lib/scout";
import { Journey, type JourneyHandle } from "../components/Journey";

// Scout (agent.js): what the engine is doing, with every line something the
// server really did; Inside Engine replays one token's recorded path.

const POLL_MS = 10_000;
const LIVE_S = 180;
const PLURAL: Record<string, string> = { backtest: "backtests", study: "projects studied", research: "deep reads", scanner: "token checks",
  judge: "board reviews", chat: "chats", scan: "scans" };
const compact = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}k` : String(n));
const ago = (t: number) => { const s = Math.max(0, Date.now() / 1000 - t); return s < 60 ? "now" : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };
const agoLong = (s: number) => (s < 60 ? `${s}s ago` : s < 3600 ? `${Math.round(s / 60)}m ago` : `${Math.round(s / 3600)}h ago`);
const hm = (t: number) => new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

export const ScoutCube = ({ state, className = "" }: { state: "idle" | "working" | "off"; className?: string }) => (
  <span className={`scout-cube block ${className}`} data-state={state} aria-hidden="true">
    <svg className="sc-svg" viewBox="-30 -23 200 200" focusable="false">
      <circle className="sc-ring" cx="70" cy="77" r="94" pathLength="100" />
      <circle className="sc-core" cx="70" cy="64" r="17" />
      <g className="sc-left"><path className="sc-face" d="M0 38 70 76 70 153 0 115Z" /><path className="sc-band" d="M3 81 70 117" /></g>
      <g className="sc-right"><path className="sc-face" d="M70 76 140 38 140 115 70 153Z" /><path className="sc-band" d="M70 117 137 81" /></g>
      <g className="sc-top"><path className="sc-face" d="M70 0 140 38 70 76 0 38Z" /></g>
    </svg>
  </span>
);

/** Two things never merged: AI calls (tokens spent) and work done; with the research AI off, how the research runs. */
function todayLine(d: AgentInfo | null) {
  const calls = Object.values(d?.today ?? {}).reduce((a, n) => a + n, 0);
  const cap = d?.cap_usd ? ` · $${(d.spent_usd ?? 0).toFixed(2)} of $${d.cap_usd.toFixed(2)}` : "";
  const r = d?.research;
  const ai = r && !r.ai
    ? [r.running ? "Research running now, no AI" : "Research without AI",
       r.last_run ? `last run ${hm(r.last_run)}${r.examined != null ? `: ${r.examined} examined, ${r.entered ?? 0} new on the board` : ""}` : "",
       r.next_run && !r.running ? `next ${hm(r.next_run)}` : ""].filter(Boolean).join(" · ")
    : calls ? `AI: ${calls} calls · ${compact(d?.tokens ?? 0)} tokens${cap}` : "";
  const distinct = d?.distinct ?? {};
  const work = Object.entries(d?.done ?? {}).map(([k, n]) => [k, distinct[k] ?? n] as const).filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1]).map(([k, n]) => `${compact(n)} ${PLURAL[k] ?? k}`).join(" · ");
  return [ai, work].filter(Boolean).join(" — ") || "Nothing yet today";
}

export function Scout({ sells }: { sells?: { risk: number | null } | null }) {
  const [info, setInfo] = useState<AgentInfo | null>(null);
  const [items, setItems] = useState<AgentItem[]>([]);
  const [fresh, setFresh] = useState<Set<number>>(new Set());
  const [error, setError] = useState("");
  const [at, setAt] = useState(0);
  const first = useRef(true);
  const journey = useRef<JourneyHandle>(null);
  const [, tick] = useState(0);

  useEffect(() => {
    let busy = false;
    const load = async () => {
      if (busy || document.visibilityState !== "visible") return;
      busy = true;
      try {
        const [i, log] = await Promise.all([api.getAgent(), api.getAgentLog()]);
        setInfo(i);
        setAt(Date.now());
        const got = log.items ?? [];
        setItems((old) => {
          if (first.current) return got;
          const add = got.filter((a) => !old.some((b) => b.t === a.t));
          if (add.length) setFresh(new Set(add.map((a) => a.t)));
          return add.length ? [...add, ...old] : old;
        });
        first.current = false;
        setError("");
      } catch {
        setError(first.current ? "Activity could not be loaded. Scout will retry automatically."
          : "Updates interrupted. Showing the last received activity; retrying automatically.");
      } finally { busy = false; }
    };
    load();
    const t = setInterval(load, POLL_MS);
    // Local freshness clock only: never polls.
    const c = setInterval(() => tick((x) => x + 1), 15_000);
    return () => { clearInterval(t); clearInterval(c); };
  }, []);

  async function earlier() {
    if (!items.length) return;
    try {
      const log = await api.getAgentLog(items[items.length - 1].t);
      const older = (log.items ?? []).filter((a) => !items.some((b) => b.t === a.t));
      if (older.length) setItems([...items, ...older]);
    } catch { /* keep what is on screen */ }
  }

  const state = !info ? "off" : info.working ? "working" : info.active ? "idle" : "off";
  const now = liveProject(items);
  const stale = !!error || !at || Date.now() - at > 45000;
  const on = !!now && now.ageS < 120 && !stale;
  const recent = recentProjects(items);
  const latest = items[0];
  const live = latest && Date.now() / 1000 - latest.t <= LIVE_S ? latest : null;

  return (
    <>
      {sells && (
        <a href="/onchain-app.html?classic=1#sells" className="flex h-11 items-center gap-2 rounded-full bg-card px-4 text-[14px] font-medium">
          <span className="flex-1">Coordinated sells</span>
          {sells.risk != null && <b className={`text-[13px] ${sells.risk >= 70 ? "text-down" : sells.risk >= 40 ? "text-amber" : "text-text-2"}`}>risk {Math.round(sells.risk)}</b>}
          <i className="not-italic text-text-3" aria-hidden="true">›</i>
        </a>
      )}

      <div className="grid justify-items-center gap-1.5 pb-[18px] pt-6 text-center">
        <ScoutCube state={state} className="mb-1.5 h-24 w-24" />
        <h2 className="text-[22px] font-bold leading-tight tracking-tight">Scout</h2>
        <p className={`text-[14px] font-semibold ${state === "off" ? "text-text-3" : "text-up"}`}>
          {error && !info ? "Connection unavailable" : !info ? "Connecting" : info.working ? "Working now" : info.active ? "Watching" : "Off"}
        </p>
        <p className="px-2 text-[12.5px] leading-snug text-text-3">{info ? todayLine(info) : error ? "Today's activity is not available yet." : "Loading activity…"}</p>
      </div>

      <section aria-label="Inside Engine" className="my-6 rounded-[24px] bg-card p-3.5">
        <h3 className="text-[20px] font-semibold">Inside Engine</h3>
        <p className="mt-1 text-[13px] text-text-2">Every recorded step the engine took on a token, replayed in order and checked in your browser.</p>
        <button type="button" disabled={!now} onClick={() => now && journey.current?.trace({ chain: now.chain, token: now.token })}
          className="mt-3 flex w-full items-center gap-2.5 rounded-[16px] bg-bg px-3 py-2.5 text-left text-[13px] text-text-2">
          <span className={`h-2.5 w-2.5 flex-none rounded-full ${on ? "bg-up shadow-[0_0_0_5px_color-mix(in_srgb,var(--c-up)_18%,transparent)]" : "bg-text-3"}`} aria-hidden="true" />
          <span>{now ? `${on ? "Now analysing" : "Last analysed"} ${now.symbol} · ${now.chain} · ${agoLong(now.ageS)} · tap to trace`
            : error ? "Activity unavailable. Retrying." : "Waiting for activity…"}</span>
        </button>
        <div aria-label="Recently analysed projects" className="mt-3 flex flex-wrap gap-2">
          {recent.map((p) => (
            <button key={p.key} type="button" onClick={() => journey.current?.trace({ chain: p.chain, token: p.token })}
              className="h-10 rounded-full bg-pill px-4 text-[15px]">{p.symbol}</button>
          ))}
        </div>
        <Journey ref={journey} />
      </section>

      {!!info?.progress?.length && (
        <div className="my-3.5 grid gap-3">
          {info.progress.map((row) => {
            const total = row.total ?? 0, done = row.done ?? 0;
            const r = total > 0 ? Math.min(1, Math.max(0, done / total)) : 0;
            return (
              <div key={row.key}>
                <div className="flex items-baseline justify-between gap-2 text-[13px] text-text-2"><span>{row.label}</span>
                  <b className="num font-semibold text-text">{row.key === "scan" ? `${total} left` : `${done}/${total}`}</b></div>
                {row.key !== "scan" && (
                  <div className="mt-1 h-1 overflow-hidden rounded-full bg-pill">
                    <motion.i className="block h-full origin-left rounded-full bg-text" initial={{ scaleX: 0 }} animate={{ scaleX: r }} transition={{ duration: 0.6, ease: "easeOut" }} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <AnimatePresence>
        {live && (
          <motion.div key={live.t} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="mb-3 flex items-center gap-2.5 rounded-[16px] border border-sage bg-card px-3.5 py-2.5">
            <span className="h-2 w-2 flex-none animate-pulse rounded-full bg-up" aria-hidden="true" />
            <Kind kind={live.kind} />
            <p className="min-w-0 flex-1 truncate text-[14px]">{live.text}</p>
          </motion.div>
        )}
      </AnimatePresence>

      <h3 className="mb-2 mt-4 text-[20px] font-semibold">Activity</h3>
      {error && <p role="status" className="mb-2 text-[13px] text-amber">{error}</p>}
      <ul aria-label="Scout activity" className="grid gap-2">
        {items.length ? items.map((a) => (
          <motion.li key={`${a.t}:${a.kind}`} initial={fresh.has(a.t) ? { opacity: 0, y: -8 } : false} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}
            className="grid gap-1.5 rounded-[20px] bg-card px-3.5 py-3">
            <header className="flex items-center justify-between gap-2"><Kind kind={a.kind} /><small className="text-[12px] text-text-3">{ago(a.t)}</small></header>
            <p className="text-[14px] leading-[1.4]">{a.text}{a.outcome && <> <b className="block font-semibold">{a.outcome}</b></>}</p>
            {!!a.steps?.length && (
              <details className="group">
                <summary className="cursor-pointer list-none text-[12.5px] font-semibold text-text-2 [&::-webkit-details-marker]:hidden">Reasoning <span className="text-text-3 group-open:hidden">▾</span><span className="hidden text-text-3 group-open:inline">▴</span></summary>
                <ol className="mt-2 grid gap-1 text-[13px]">{a.steps.map((s, i) => (
                  <motion.li key={i} initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.09, duration: 0.3 }}
                    className={s.startsWith("✗") ? "text-down" : s.startsWith("✓") ? "text-up" : ""}>{s}</motion.li>
                ))}</ol>
              </details>
            )}
          </motion.li>
        )) : <li className="py-3 text-[14px] text-text-2">No activity recorded yet today.</li>}
      </ul>
      {items.length >= 60 && <button type="button" onClick={earlier} className="mx-auto mt-3 block h-10 rounded-full bg-pill px-4 text-[14px]">Load earlier</button>}
    </>
  );
}

const Kind = ({ kind }: { kind: string }) => <span className="rounded-full bg-pill px-2 text-[12px] font-medium leading-normal text-text-2">{kind}</span>;
