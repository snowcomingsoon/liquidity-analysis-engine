import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import * as api from "../lib/api";
import { NODE_LABEL, SOURCE, SPEEDS, autoSpeed, replaySchedule, verifyChain, type Journey as J, type JourneyAnswer } from "../lib/scout";
import { t, locale } from "../lib/i18n";

// One token's recorded evaluation path, replayed at the real pace between
// steps and checked hash by hash in the browser (agent-journey.js).

const CAP_MS = 3000;
const short = (h: string) => `${h.slice(0, 8)}…${h.slice(-4)}`;
const when = (ts: number) => new Date(ts * 1000).toLocaleString(locale());
const fmt = (s: number) => (s < 60 ? `${Math.round(s)}s` : s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : t("{n}d", { n: Math.round(s / 86400) }));
const label = (n: string) => t(NODE_LABEL[n] || "Other activity");

export type JourneyHandle = { trace: (args: { q?: string; chain?: string; token?: string }) => void };

export const Journey = forwardRef<JourneyHandle>(function Journey(_, ref) {
  const still = useReducedMotion();
  const root = useRef<HTMLElement>(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState(() => t("Type any ticker to replay how the engine evaluated it."));
  const [matches, setMatches] = useState<JourneyAnswer["matches"]>([]);
  const [j, setJ] = useState<J | null>(null);
  const [verify, setVerify] = useState<{ ok: boolean; brokenAt: number | null } | null>(null);
  const [shown, setShown] = useState(0);
  const [speed, setSpeed] = useState(60);
  const [clock, setClock] = useState("");
  const [following, setFollowing] = useState(true);
  const timers = useRef(new Set<number>());
  const run = useRef(0);
  const followRef = useRef(true);
  followRef.current = following;
  const rail = useRef<HTMLOListElement>(null);

  const clear = () => { timers.current.forEach(clearTimeout); timers.current.clear(); };
  useEffect(() => () => clear(), []);
  // A finger or wheel on the page: stop following the replay until asked.
  useEffect(() => {
    const un = () => { if (timers.current.size && followRef.current) setFollowing(false); };
    addEventListener("wheel", un, { passive: true });
    addEventListener("touchmove", un, { passive: true });
    return () => { removeEventListener("wheel", un); removeEventListener("touchmove", un); };
  }, []);

  function play(journey: J, from: number, sp: number) {
    clear();
    const mine = run.current;
    const n = journey.steps.length;
    const plan = replaySchedule(journey.steps, sp, CAP_MS);
    const base = plan[from]?.at ?? 0, t0 = performance.now();
    for (let i = from; i < n; i++) {
      const id = window.setTimeout(() => {
        timers.current.delete(id);
        if (mine !== run.current) return;
        setShown(i + 1);
        // The step just revealed stays in view while following.
        if (followRef.current) requestAnimationFrame(() => rail.current?.children[i]?.scrollIntoView({ behavior: "smooth", block: "center" }));
        if (i + 1 === n) setClock(`${t("Replay done")} · ${when(journey.steps[n - 1].t)}`);
      }, plan[i].at - base);
      timers.current.add(id);
    }
    let last = from;
    const tick = () => {
      if (mine !== run.current || !timers.current.size) return;
      const ms = performance.now() - t0 + base;
      while (last < n && plan[last].at <= ms) last++;
      const i = Math.max(0, last - 1), next = plan[last];
      let real = journey.steps[i].t;
      if (next && !next.capped && last > 0) real += Math.min(next.gapS, ((ms - plan[i].at) / 1000) * sp);
      setClock(next?.capped && last > 0 ? t("Skipping a pause of {gap} · next step {at}", { gap: fmt(next.gapS), at: when(journey.steps[last].t) })
        : `${when(real)} · ${t(SPEEDS.find((x) => x[0] === sp)?.[1] ?? "")}`);
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  async function show(journey: J) {
    clear();
    const mine = ++run.current;
    setJ(journey); setVerify(null); setShown(0); setClock(""); setFollowing(true);
    const n = journey.steps.length;
    setStatus(n ? `${journey.symbol || journey.token.slice(0, 8)} · ${journey.chain} · ${t("{n} recorded steps", { n })}` : t("No stored record for {s}.", { s: journey.symbol || journey.token }));
    if (!n) return;
    const v = await verifyChain(journey).catch(() => ({ ok: false, brokenAt: 0 }));
    if (mine !== run.current) return;
    setVerify(v);
    if (still) { setShown(n); return; }
    const sp = autoSpeed(journey.steps);
    setSpeed(sp);
    play(journey, 0, sp);
  }

  async function trace(args: { q?: string; chain?: string; token?: string }) {
    clear(); run.current++;
    setMatches([]); setJ(null); setVerify(null); setShown(0); setClock("");
    setStatus(t("Loading recorded steps…"));
    let data: JourneyAnswer;
    try { data = await api.getAgentJourney(args); } catch { setStatus(t("Trace unavailable. Try again.")); return; }
    root.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    if (data?.journey) { setQ(data.journey.symbol || q); return show(data.journey); }
    const m = data?.matches ?? [];
    if (!m.length) { setStatus(t("No stored project matches “{q}”.", { q: args.q ?? "" })); return; }
    setStatus(t("{n} tokens share this ticker. Pick one:", { n: m.length }));
    setMatches(m);
  }
  useImperativeHandle(ref, () => ({ trace }));


  const steps = j?.steps.slice(0, shown) ?? [];
  const n = j?.steps.length ?? 0;
  const counts = new Map<string, number>();
  for (const s of j?.steps ?? []) if (!counts.has(s.node)) counts.set(s.node, 0);
  for (const s of steps) counts.set(s.node, (counts.get(s.node) ?? 0) + 1);
  const playing = !!j && shown < n && !still;
  const plan = j ? replaySchedule(j.steps, speed, CAP_MS) : [];

  return (
    <section ref={root} aria-label={t("Token journey")} className="mt-4 scroll-mt-4">
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (q.trim()) trace({ q: q.trim() }); }}>
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("Ticker or token address")} autoComplete="off" aria-label={t("Ticker or token address")}
          className="h-[52px] min-w-0 flex-1 rounded-full border border-line bg-bg px-5 text-[16px] outline-none placeholder:text-text-3" />
        <button type="submit" className="h-[52px] rounded-full bg-ink px-5 text-[16px] font-medium text-on-ink">{t("Trace")}</button>
      </form>
      <p className="mt-3 text-[13px] text-text-2">{status}</p>
      {!!matches?.length && (
        <div className="mt-2 flex flex-wrap gap-2">{matches.map((m) => (
          <button key={`${m.chain}:${m.token}`} type="button" onClick={() => trace({ chain: m.chain, token: m.token })} className="rounded-full border border-up px-3.5 py-2 text-[14px]">
            {m.symbol || "?"} · {m.chain} · {m.token.slice(0, 4)}…{m.token.slice(-4)}{m.status ? ` · ${m.status}` : ""}
          </button>
        ))}</div>
      )}
      {j && n > 0 && (
        <>
          <p className={`mt-3 text-[13px] ${verify == null ? "text-text-2" : verify.ok ? "text-up" : "text-amber"}`}>
            {verify == null ? t("Verifying hash chain…") : verify.ok ? t("Chain verified in your browser · {n} records · head {h}", { n, h: short(j.head) })
              : t("Chain does not match at step {n}: do not trust this trace", { n: (verify.brokenAt ?? 0) + 1 })}
          </p>
          <p className="mt-2 text-[13px] text-text-2">{j.limits} {t("The replay keeps the real time between steps at the chosen speed; a pause longer than {n} s on screen is shortened and marked.", { n: CAP_MS / 1000 })}</p>
          <div aria-live="polite" className="my-2.5 flex flex-wrap gap-1.5">
            {[...counts].map(([node, c]) => (
              <motion.span key={`${node}:${c}`} initial={still || !c ? false : { scale: 1.15 }} animate={{ scale: 1 }} transition={{ duration: 0.26 }}
                className="rounded-full px-2 py-0.5 text-[12px] text-up">{label(node)} {c}</motion.span>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <select aria-label={t("Replay speed")} value={speed} onChange={(e) => { const sp = Number(e.target.value); setSpeed(sp); if (playing) play(j, shown, sp); }}
              className="h-12 w-full rounded-full border border-line bg-bg px-5 text-[15px]">
              {SPEEDS.map(([v, name]) => <option key={v} value={v}>{t(name)}</option>)}
            </select>
            {playing && <Btn onClick={() => { clear(); setShown(n); setClock(""); }}>{t("Show all")}</Btn>}
            {playing && !following && <Btn onClick={() => { setFollowing(true); rail.current?.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "center" }); }}>{t("Follow")}</Btn>}
            {!playing && <Btn onClick={() => show(j)}>{t("Replay")}</Btn>}
          </div>
          <ol ref={rail} className="relative my-3 pl-[22px] before:absolute before:bottom-1.5 before:left-1.5 before:top-1.5 before:w-0.5 before:bg-line">
            {steps.map((s, i) => {
              const now = playing && i === shown - 1;
              const gap = i ? s.t - steps[i - 1].t : 0;
              let record = s.record;
              try { record = JSON.stringify(JSON.parse(s.record), null, 2); } catch { /* as stored */ }
              return (
                <motion.li key={s.id + i} initial={still ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: [0.2, 0.8, 0.2, 1] }}
                  className={`relative mb-3 rounded-[12px] border bg-card px-3 py-2.5 ${now ? "border-up" : "border-line"}`}>
                  <i className={`absolute -left-[21px] top-4 h-2.5 w-2.5 rounded-full ${now ? "animate-pulse bg-up" : "bg-text-3"}`} />
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="rounded-full px-2 py-0.5 text-[12px] text-up">{label(s.node)}</span>
                    <time className="text-[12px] text-text-2">{i ? `${when(s.t)} · ${gap < 60 ? `+${Math.round(gap)}s` : gap < 3600 ? `+${Math.round(gap / 60)}m` : gap < 86400 ? `+${Math.round(gap / 3600)}h` : `+${Math.round(gap / 86400)}d`}` : when(s.t)}</time>
                  </div>
                  <p className="mt-1.5 text-[12px] text-text-2">{i + 1}. {SOURCE[s.source] ? t(SOURCE[s.source]) : s.source}{plan[i]?.capped && !still ? ` · ${t("pause of {gap} shortened", { gap: fmt(gap) })}` : ""}</p>
                  <p className="my-1 text-[14px]">{s.text || t("No description recorded")}</p>
                  <details>
                    <summary className="cursor-pointer font-mono text-[12px] text-text-2">{t("record")} {short(s.id)} · {t("link")} {short(s.link)}</summary>
                    <pre className="mt-1.5 max-h-[220px] overflow-auto whitespace-pre-wrap break-all rounded-lg bg-bg p-2 text-[11px]">{record}</pre>
                  </details>
                </motion.li>
              );
            })}
          </ol>
        </>
      )}
      {clock && <p className="fixed bottom-[calc(112px+env(safe-area-inset-bottom))] left-1/2 z-30 max-w-[calc(100vw-32px)] -translate-x-1/2 rounded-full border border-up bg-card px-3.5 py-2 text-[13px] shadow-float">{clock}</p>}
    </section>
  );
});

const Btn = ({ onClick, children }: { onClick: () => void; children: React.ReactNode }) =>
  <button type="button" onClick={onClick} className="h-11 rounded-[12px] border border-up px-4 text-[15px]">{children}</button>;
