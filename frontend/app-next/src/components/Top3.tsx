import { motion } from "motion/react";
import type { Gem } from "../lib/types";
import { Tile } from "./Logo";
import { t } from "../lib/i18n";

const ORDER = [1, 0, 2];   // second, first, third: the winner in the middle

/** The Top's best three by score, fixed under the title on every view (top.js paintTop3). */
export function Top3({ list, onOpen }: { list: Gem[]; onOpen: (e: Gem) => void }) {
  if (!list.length) return null;
  return (
    <nav className="mb-3 flex gap-1.5" aria-label={t("Top three gems")}>
      {ORDER.filter((p) => list[p]).map((p) => {
        const e = list[p];
        return (
          <motion.button key={`${e.chain}:${e.token_address}`} type="button" onClick={() => onOpen(e)} layout
            title={`${e.name || e.symbol} · ${t("score {n}", { n: Math.round(e.score ?? 0) })}`}
            className={`flex min-w-0 flex-1 items-center gap-1.5 rounded-[10px] border py-1 pl-1 pr-1.5 text-left ${p === 0 ? "border-sage bg-card" : "border-line"}`}>
            <i className="num text-[11px] font-semibold not-italic text-up">{p + 1}</i>
            <span className="h-[22px] w-[22px] flex-none [&_.tile]:rounded-[7px]"><Tile symbol={e.symbol} image={e.image} chain={e.chain} token={e.token_address} /></span>
            <span className="grid min-w-0 leading-tight">
              <b className="truncate text-[12px] font-semibold">{e.symbol}</b>
              <small className="truncate text-[9px] opacity-70">{t("score {n}", { n: Math.round(e.score ?? 0) })}</small>
            </span>
          </motion.button>
        );
      })}
    </nav>
  );
}
