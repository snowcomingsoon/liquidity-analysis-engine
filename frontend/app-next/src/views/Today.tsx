import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { Gem } from "../lib/types";
import { type SectorsView, type TodayKind, sinceText } from "../lib/sectors";
import { Logo } from "../components/Logo";
import { changeText, usdShort } from "../lib/format";
import { gemId } from "../components/TokenRow";
import { watchedIds } from "./Watch";

const FILTERS: [TodayKind | "all", string][] = [["all", "All"], ["champion", "Champions"], ["entered", "New"], ["dropped", "Dropped"]];
const MARK: Record<TodayKind, string> = { champion: "text-up", entered: "text-up", dropped: "text-down", moved: "text-text-3" };
const PREVIEW = 4;
const WATCH_ROWS = 5;

/** Today (direction A, Lorenzo 10/10 and 22/10): what changed since about a
 *  day ago, then a glance at the strongest sectors. */
export function Today({ data, onOpen, onSectors, onWatch, early, onEarly }: { data: SectorsView | null; onOpen: (e: Gem) => void; onSectors: () => void; onWatch: () => void; early: number | null; onEarly: () => void }) {
  const [filter, setFilter] = useState<TodayKind | "all">("all");
  if (!data) return <div className="mt-2 space-y-2">{Array.from({ length: 5 }, (_, i) => <div key={i} className="h-16 animate-pulse rounded-[20px] bg-card" />)}</div>;
  const t = data.today;
  const items = t.items.filter((i) => filter === "all" || i.kind === filter);
  const ranked = new Set(data.sectors.flatMap((s) => s.entries.filter((e) => e.in !== false).map(gemId))).size;
  // The starred tokens, with their sector and the line of what changed (direction A: the watchlist on Today).
  const byId = new Map<string, { e: Gem; sector: string }>();
  for (const s of data.sectors) for (const e of s.entries) if (!byId.has(gemId(e)) || e.in !== false) byId.set(gemId(e), { e, sector: s.label });
  const news = new Map(t.items.map((i) => [gemId(i.gem), i] as const));
  // Only the followed tokens that are ranked now, with real data; the rest live in Watch (Lorenzo 22/10).
  const watchAll = watchedIds().flatMap((id) => { const hit = byId.get(id); return hit ? [{ id, hit, news: news.get(id) }] : []; });
  const watch = watchAll.slice(0, WATCH_ROWS);
  return (
    <>
      <p className="text-[13px] text-text-2">
        {t.since ? `${ranked} projects ranked · ${t.items.length} changes ${sinceText(t.since)}` : `${ranked} projects ranked`}
      </p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Stat label="New champions" v={t.counts.champion} />
        <Stat label="Dropped" v={t.counts.dropped} />
      </div>
      {/* Early stays one tap away (Lorenzo 22/10: "sparita la sezione early"). */}
      <button type="button" onClick={onEarly} className="mt-2 flex w-full items-center rounded-[20px] bg-card px-4 py-3 text-left active:bg-pill">
        <span className="flex-1"><b className="block text-[15px] font-semibold">Early</b><small className="text-[12.5px] text-text-3">under $300k cap, every other bar passed</small></span>
        <b className="num text-[20px] font-semibold">{early ?? "…"}</b><span className="ml-2 text-text-3">›</span>
      </button>
      {watch.length > 0 && (
        <>
          <div className="mt-4 flex items-baseline justify-between">
            <h2 className="text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">Your watchlist</h2>
            <button type="button" onClick={onWatch} className="text-[13px] font-medium text-text-2">Show all ›</button>
          </div>
          <ol className="mt-2 rounded-[20px] bg-card p-1.5">
            {watch.map(({ id, hit, news: n }) => {
              const e = hit.e;
              const [chg, sign] = changeText(e.change_24h);
              return (
                <li key={id}>
                  <button type="button" onClick={() => onOpen(e)} className="flex w-full items-center gap-3 rounded-[16px] px-2 py-2 text-left active:bg-pill">
                    <Logo size={34} symbol={e.symbol} image={e.image} chain={e.chain} token={e.token_address} />
                    <span className="min-w-0 flex-1">
                      <b className="block truncate text-[15px] font-medium leading-tight">{e.symbol}</b>
                      <small className="block truncate text-[12.5px] text-text-2">{n ? n.text : `${hit.sector}${e.arena_rank ? ` · #${e.arena_rank}` : ""}${e.score != null ? ` · score ${Math.round(e.score)}` : ""}`}</small>
                    </span>
                    <span className="flex flex-col items-end">
                      <b className="num text-[14px] font-semibold">{usdShort(e.market_cap)}</b>
                      <em className={`num text-[12px] not-italic ${sign === "up" ? "text-up" : sign === "down" ? "text-down" : "text-text-3"}`}>{chg}</em>
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        </>
      )}
      {t.since ? (
        <>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {FILTERS.map(([k, label]) => {
              const n = k === "all" ? t.items.length : t.counts[k];
              return (
                <button key={k} type="button" aria-pressed={filter === k} onClick={() => setFilter(k)} disabled={!n && k !== "all"}
                  className={`h-8 rounded-full px-3 text-[13px] font-medium disabled:opacity-40 ${filter === k ? "bg-ink text-on-ink" : "bg-pill text-text-2"}`}>
                  {label}{k !== "all" && n ? ` ${n}` : ""}
                </button>
              );
            })}
          </div>
          <ol className="mt-3 rounded-[20px] bg-card p-1.5">
            <AnimatePresence initial={false}>
              {items.map((i, n) => (
                <motion.li key={`${i.kind}:${gemId(i.gem)}`} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  transition={{ duration: 0.2, delay: Math.min(n, 8) * 0.02 }}>
                  <button type="button" onClick={() => i.kind !== "dropped" && onOpen(i.gem)} disabled={i.kind === "dropped"}
                    className="flex w-full items-center gap-3 rounded-[16px] px-2 py-2 text-left active:bg-pill disabled:active:bg-transparent">
                    <Logo size={38} symbol={i.gem.symbol} image={i.gem.image} chain={i.gem.chain} token={i.gem.token_address} />
                    <span className="min-w-0 flex-1">
                      <b className="block truncate text-[15px] font-medium leading-tight">{i.text}</b>
                      <small className="num block truncate text-[12.5px] text-text-2">{i.detail}</small>
                    </span>
                    <span className={`text-[11px] font-semibold uppercase tracking-wide ${MARK[i.kind]}`}>{i.kind === "entered" ? "new" : i.kind === "champion" ? "♛" : i.kind}</span>
                  </button>
                </motion.li>
              ))}
            </AnimatePresence>
            {!items.length && <li className="px-2 py-4 text-[14px] text-text-2">Nothing changed {sinceText(t.since)}.</li>}
          </ol>
        </>
      ) : (
        <p className="mt-3 rounded-[20px] bg-card p-4 text-[14px] text-text-2">
          Today compares the ranking with about a day ago. The first reading is saved now: changes show up after the next research run.
        </p>
      )}
      <div className="mt-5 flex items-baseline">
        <h2 className="flex-1 text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">Strongest sectors</h2>
        <button type="button" onClick={onSectors} className="text-[13px] font-medium text-text-2">All sectors ›</button>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2">
        {data.sectors.slice(0, PREVIEW).map((s) => (
          <button key={s.key} type="button" onClick={() => onOpen(s.top[0])} className="flex min-w-0 flex-col gap-1.5 rounded-[18px] bg-card p-3 text-left">
            <span className="truncate text-[11px] font-medium uppercase tracking-[0.07em] text-text-3">{s.label}</span>
            <span className="flex min-w-0 items-center gap-2">
              <Logo size={30} symbol={s.top[0].symbol} image={s.top[0].image} chain={s.top[0].chain} token={s.top[0].token_address} />
              <b className="min-w-0 flex-1 truncate text-[14px] font-semibold">{s.top[0].symbol}</b>
              <span className="num rounded-full bg-sage px-1.5 text-[11.5px] font-semibold text-on-sage">{Math.round(s.top[0].score ?? 0)}</span>
            </span>
          </button>
        ))}
      </div>
    </>
  );
}

function Stat({ label, v }: { label: string; v: number }) {
  return (
    <div className="rounded-[18px] bg-card px-3.5 py-2.5">
      <div className="text-[11px] font-medium uppercase tracking-[0.07em] text-text-3">{label}</div>
      <div className="num text-[24px] font-semibold leading-tight">{v}</div>
    </div>
  );
}
