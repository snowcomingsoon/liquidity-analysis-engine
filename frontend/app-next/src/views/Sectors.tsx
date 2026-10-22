import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { Gem } from "../lib/types";
import { type Sector, type SectorsView, newChampions } from "../lib/sectors";
import { changeText, usdShort } from "../lib/format";
import { TokenRow, gemId } from "../components/TokenRow";
import { Logo, Tile } from "../components/Logo";
import { t } from "../lib/i18n";

type Mode = "champions" | "map";
// Lorenzo, 22/10: "avevo scelto M2" — Champions first, with the Map one tap away.
const MODES: [Mode, string][] = [["champions", "Champions"], ["map", "Map"]];

/** The sectors as a mosaic (Lorenzo, 22/10 "SECTORS!"): champions and who chases
 *  them, a market map of every project, or which sectors are improving. */
export function Sectors({ data, onOpen }: { data: SectorsView | null; onOpen: (e: Gem) => void }) {
  const [mode, setMode] = useState<Mode>("champions");
  if (!data) return <div className="mt-4 grid grid-cols-2 gap-2">{Array.from({ length: 6 }, (_, i) => <div key={i} className={`h-28 animate-pulse rounded-[20px] bg-card ${i ? "" : "col-span-2"}`} />)}</div>;
  const list = data.sectors;
  const projects = new Set(list.flatMap((s) => s.entries.map(gemId))).size;
  return (
    <>
      <div className="flex gap-1 rounded-full bg-pill p-1" role="tablist" aria-label={t("Mosaic")}>
        {MODES.map(([m, label]) => (
          <button key={m} type="button" role="tab" aria-selected={mode === m} onClick={() => setMode(m)}
            className={`relative h-9 flex-1 rounded-full text-[14px] font-medium transition-colors ${mode === m ? "text-text" : "text-text-2"}`}>
            {mode === m && <motion.span layoutId="sectors-mode" className="absolute inset-0 rounded-full bg-card shadow-sm" transition={{ type: "spring", stiffness: 520, damping: 42 }} />}
            <span className="relative">{t(label)}</span>
          </button>
        ))}
      </div>
      <p className="mt-3 text-[13px] text-text-2">
        {t("{n} sectors · {m} projects", { n: list.length, m: projects })} · {mode === "champions" ? t("strongest first: how far the top 3 sit above the median") : t("size = market cap")}
      </p>
      {!list.length && <p className="py-6 text-[14px] text-text-2">{t("The sectors are filling up: projects appear as they pass the checks.")}</p>}
      <AnimatePresence mode="wait">
        <motion.div key={mode} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.16 }} className="mt-3">
          {mode === "champions" && <Champions list={list} fresh={newChampions(data.today)} onOpen={onOpen} />}
          {mode === "map" && <MarketMap list={list} onOpen={onOpen} />}
        </motion.div>
      </AnimatePresence>
    </>
  );
}

// M2 ------------------------------------------------------------------

function Champions({ list, fresh, onOpen }: { list: Sector[]; fresh: Set<string>; onOpen: (e: Gem) => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const max = Math.max(...list.map((s) => s.strength), 0.01);
  return (
    <div className="grid grid-flow-row-dense grid-cols-2 gap-2">
      {list.map((s, i) => {
        const champ = s.top[0], isNew = fresh.has(s.label), isOpen = open === s.key, wide = i === 0 || isOpen || isNew;
        return (
          <motion.section key={s.key} layout="position" className={`min-w-0 rounded-[20px] bg-card p-3 ${i === 0 || isOpen || isNew ? "col-span-2" : ""} ${isNew ? "ring-[1.5px] ring-up" : ""}`}>
            <button type="button" onClick={() => setOpen(isOpen ? null : s.key)} aria-expanded={isOpen} className="flex w-full items-center gap-2 text-left">
              <span className="min-w-0 flex-1 truncate text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">{s.label}</span>
              {isNew && <span className="text-[10px] font-bold tracking-wide text-up">{t("NEW CHAMPION")}</span>}
              <span className="num text-[12px] text-text-3">{s.size} ›</span>
            </button>
            <button type="button" onClick={() => onOpen(champ)} className="mt-2 flex w-full min-w-0 items-center gap-2.5 text-left">
              <Logo size={40} symbol={champ.symbol} image={champ.image} chain={champ.chain} token={champ.token_address} />
              <span className="min-w-0 flex-1">
                <b className="block truncate text-[15px] font-semibold leading-tight">{wide ? champ.name || champ.symbol : champ.symbol}</b>
                <small className="num block truncate text-[12px] text-text-2">
                  {champ.z != null ? `+${Math.max(0, champ.z).toFixed(1)}σ · ` : ""}{usdShort(champ.market_cap)}
                </small>
              </span>
              {champ.score != null && <span className="num rounded-full bg-sage px-2 text-[12px] font-semibold text-on-sage">{Math.round(champ.score)}</span>}
            </button>
            <div className="mt-2 flex min-w-0 items-center gap-1.5">
              {s.top.slice(1).map((e) => (
                <button key={gemId(e)} type="button" onClick={() => onOpen(e)} className="flex min-w-0 items-center gap-1 rounded-full bg-pill py-0.5 pl-0.5 pr-2">
                  <span className="h-5 w-5 flex-none [&_.tile]:rounded-full"><Tile symbol={e.symbol} image={e.image} chain={e.chain} token={e.token_address} /></span>
                  <span className="num truncate text-[11.5px] text-text-2">{e.symbol}{wide ? ` ${Math.round(e.score ?? 0)}` : ""}</span>
                </button>
              ))}
            </div>
            <div className="mt-2.5 h-1 overflow-hidden rounded-full bg-pill" aria-label={t("Strength {n}", { n: s.strength })}>
              <div className="h-full rounded-full bg-up" style={{ width: `${Math.max(4, (s.strength / max) * 100)}%` }} />
            </div>
            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.ol initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="mt-3 overflow-hidden">
                  {s.entries.map((e, j) => <TokenRow key={gemId(e)} e={e} name={`${e.arena_rank ?? j + 1}. ${e.name || e.symbol}`} dim={e.in === false} onOpen={onOpen} i={j} />)}
                </motion.ol>
              )}
            </AnimatePresence>
          </motion.section>
        );
      })}
    </div>
  );
}

// M1 ------------------------------------------------------------------

type Paint = "24h" | "score";

function tone(e: Gem, paint: Paint) {
  if (paint === "score") {
    const s = e.score ?? 0;
    return s >= 80 ? "bg-up text-white" : s >= 70 ? "bg-up/75 text-white" : s >= 60 ? "bg-up/45 text-text" : s >= 50 ? "bg-press text-text" : "bg-down/40 text-text";
  }
  const c = e.change_24h;
  if (c == null) return "bg-press text-text";
  return c >= 5 ? "bg-up text-white" : c >= 1.5 ? "bg-up/70 text-white" : c > 0.3 ? "bg-up/35 text-text"
    : c > -0.3 ? "bg-press text-text" : c > -1.5 ? "bg-down/35 text-text" : c > -5 ? "bg-down/70 text-white" : "bg-down text-white";
}

function MarketMap({ list, onOpen }: { list: Sector[]; onOpen: (e: Gem) => void }) {
  const [paint, setPaint] = useState<Paint>("24h");
  const weight = (cap: number) => Math.sqrt(Math.max(cap, 1));
  const sorted = [...list].sort((a, b) => b.cap - a.cap);
  const total = sorted.reduce((t, s) => t + weight(s.cap), 0) || 1;
  return (
    <>
      <div className="mb-2 flex items-center gap-1.5">
        {(["24h", "score"] as Paint[]).map((p) => (
          <button key={p} type="button" aria-pressed={paint === p} onClick={() => setPaint(p)}
            className={`h-7 rounded-full px-3 text-[12px] font-medium ${paint === p ? "bg-ink text-on-ink" : "bg-pill text-text-2"}`}>{p === "24h" ? t("Colour: 24h") : t("Colour: score")}</button>
        ))}
      </div>
      <div className="flex flex-wrap gap-1">
        {sorted.map((s) => {
          const share = weight(s.cap) / total;
          const basis = Math.min(100, Math.max(31, share * 260));
          const cells = [...s.entries].filter((e) => e.in !== false).sort((a, b) => (b.market_cap ?? 0) - (a.market_cap ?? 0));
          const inner = cells.reduce((t, e) => t + weight(e.market_cap ?? 0), 0) || 1;
          return (
            <section key={s.key} className="flex min-w-0 flex-col rounded-[14px] bg-pill p-1" style={{ flex: `1 1 calc(${basis}% - 4px)`, minHeight: basis > 60 ? 132 : 92 }}>
              <h4 className="truncate px-1 pb-0.5 text-[10px] font-medium uppercase tracking-[0.07em] text-text-3">{s.label}</h4>
              <div className="flex flex-1 flex-wrap gap-[3px]">
                {cells.map((e) => {
                  const w = weight(e.market_cap ?? 0) / inner;
                  return (
                    <button key={gemId(e)} type="button" onClick={() => onOpen(e)}
                      className={`grid min-h-[34px] min-w-0 place-items-center overflow-hidden rounded-[8px] px-1 text-center leading-tight ${tone(e, paint)}`}
                      style={{ flex: `${Math.max(w, 0.05)} 1 calc(${Math.min(100, Math.max(30, w * 100))}% - 3px)` }}>
                      <span className="truncate text-[11px] font-semibold">{e.symbol}</span>
                      {w > 0.18 && <span className="num text-[10px] opacity-90">{paint === "24h" ? changeText(e.change_24h)[0] : Math.round(e.score ?? 0)}</span>}
                    </button>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
      <p className="mt-2 flex items-center gap-1.5 text-[11px] text-text-3">
        {paint === "24h"
          ? <><i className="h-2 w-4 rounded-sm bg-down" />−5% <i className="h-2 w-4 rounded-sm bg-press" />0 <i className="h-2 w-4 rounded-sm bg-up" />+5%</>
          : <><i className="h-2 w-4 rounded-sm bg-down/40" />{t("under 50")} <i className="h-2 w-4 rounded-sm bg-up/45" />60 <i className="h-2 w-4 rounded-sm bg-up" />80+</>}
        <span className="ml-auto">{t("tap a square to open it")}</span>
      </p>
    </>
  );
}
