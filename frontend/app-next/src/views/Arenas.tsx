import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { Arena, Gem } from "../lib/types";
import { isHiddenIn, setNarratives, sortRows, useHidden, useNarratives, useSort } from "../lib/store";
import { TokenRow, gemId } from "../components/TokenRow";
import { SortBar } from "../components/SortBar";

const FOLD = 3;   // the first three of each arena in view, the rest behind "Show all" (Lorenzo, 17/10)
const SEEN_KEY = "lae:arena-crowns";

function readSeen(): Record<string, { id: string; symbol: string }> | null {
  try { return JSON.parse(localStorage.getItem(SEEN_KEY) ?? "null"); } catch { return null; }
}

/** Every arena open, biggest first, each ranked against its own narrative (top.js). */
export function Arenas({ arenas, filtered, labels, onOpen }: {
  arenas: Arena[]; filtered: boolean; labels: Record<string, string>; onOpen: (e: Gem) => void;
}) {
  const hidden = useHidden();
  const sort = useSort();
  const narr = useNarratives();
  const shown = (a: Arena) => a.entries.filter((e) => !isHiddenIn(hidden, e.chain, e.token_address));
  const list = arenas.filter((a) => shown(a).length).sort((a, b) => shown(b).length - shown(a).length);
  const total = new Set(arenas.flatMap((a) => a.entries.map(gemId))).size;

  // "Since your last visit": the arenas whose champion changed (Lorenzo, 28/09).
  const [changed] = useState(() => new Map<string, string>());
  const lead = useMemo(() => {
    const prev = !filtered ? readSeen() : null;
    const out: string[] = [];
    if (prev) for (const a of arenas) {
      const was = prev[a.key], now = a.entries[0];
      if (was && now && was.id !== gemId(now)) { out.push(`${now.symbol} took ${a.label} from ${was.symbol}`); changed.set(a.key, gemId(now)); }
    }
    return out;
  }, [arenas, filtered, changed]);
  useEffect(() => {
    if (filtered || !arenas.length) return;
    const crowns = Object.fromEntries(arenas.filter((a) => a.entries.length).map((a) => [a.key, { id: gemId(a.entries[0]), symbol: a.entries[0].symbol }]));
    try { localStorage.setItem(SEEN_KEY, JSON.stringify(crowns)); } catch { /* private mode */ }
  }, [arenas, filtered]);

  return (
    <>
      <p className="mt-3 text-[13px] text-text-2">
        {filtered && (
          <button type="button" onClick={() => setNarratives([])} className="mr-1.5 rounded-full bg-pill px-2.5 py-0.5 text-[12px]">
            {narr.map((k) => labels[k] ?? k).join(", ")} ✕
          </button>
        )}
        {lead.length > 0 && `Since your last visit: ${lead.slice(0, 3).join(", ")}. `}
        {total > 0 && `${list.length} arenas · ${total} projects`}
      </p>
      <SortBar />
      {list.length
        ? <div className="grid grid-cols-[minmax(0,1fr)] gap-[18px]">{list.map((a) => <ArenaBox key={a.key} a={a} rows={sortRows(shown(a), sort)} champ={changed.get(a.key)} onOpen={onOpen} />)}</div>
        : <p className="py-6 text-[14px] text-text-2">The arenas are filling up: projects appear as they pass the checks.</p>}
    </>
  );
}

function ArenaBox({ a, rows, champ, onOpen }: { a: Arena; rows: Gem[]; champ?: string; onOpen: (e: Gem) => void }) {
  const [all, setAll] = useState(false);
  const vis = all ? rows : rows.slice(0, FOLD);
  return (
    <section className="min-w-0 rounded-xl border border-line p-3">
      <header className="mb-2.5 flex items-center gap-2">
        <h4 className="text-[15px] font-semibold leading-snug">{a.label}</h4>
        {a.heat > 0 && <span className="text-[11px] tracking-[-1px] text-amber" aria-label={`Narrative heat ${a.heat} of 3`}>{"█".repeat(a.heat)}<span className="opacity-30">{"█".repeat(Math.max(0, 3 - a.heat))}</span></span>}
        <span className="num ml-auto text-[12px] text-text-3">{rows.length} projects · median {Math.round(a.median)}</span>
      </header>
      <ol>
        <AnimatePresence initial={false}>
          {vis.map((e, i) => (
            <motion.div key={gemId(e)} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}
              className={champ === gemId(e) && e.arena_rank === 1 ? "rounded-[20px] ring-2 ring-sage" : ""}>
              <TokenRow e={e} name={`${e.arena_rank ?? i + 1}. ${e.name || e.symbol}`} badge={e.early ? "early" : e.hidden ? "hidden" : null} onOpen={onOpen} i={i} />
            </motion.div>
          ))}
        </AnimatePresence>
      </ol>
      {rows.length > FOLD && (
        <button type="button" onClick={() => setAll(!all)} aria-expanded={all}
          className="mt-1 h-10 w-full rounded-xl border border-line text-[14px] text-text transition-colors active:bg-pill">
          {all ? "Show less" : `Show all ${rows.length}`}
        </button>
      )}
    </section>
  );
}
