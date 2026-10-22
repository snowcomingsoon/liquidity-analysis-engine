import { motion } from "motion/react";
import type { Gem } from "../lib/types";
import { age, changeText, marketSub, usdShort } from "../lib/format";
import { Logo } from "./Logo";

const BADGE = { early: "EARLY", hidden: "HIDDEN GEM" } as const;

export const gemId = (e: { chain: string; token_address: string }) => `${e.chain}:${e.token_address}`;

/** One gem as a soft card: logo, name, score, ticker, age, market line; cap and 24h on the right (format.js tokenRow). */
export function TokenRow({ e, name, badge, onOpen, i = 0, dim = false, footer }: {
  e: Gem; name?: string; badge?: keyof typeof BADGE | null; onOpen: (e: Gem) => void; i?: number; dim?: boolean;
  footer?: React.ReactNode;   // under the row, on the same card (quality.js actions)
}) {
  const [a, fresh] = age(e.launched_at);
  const [chg, sign] = changeText(e.change_24h);
  const sub = marketSub(e);
  return (
    <motion.li layout="position" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.26, ease: [0.25, 0.1, 0.25, 1], delay: Math.min(i, 8) * 0.025 }} className={`mb-2 ${footer ? "rounded-[20px] bg-card" : ""}`}>
      <button type="button" onClick={() => onOpen(e)}
        className={`flex w-full items-center gap-3.5 rounded-[20px] ${footer ? "" : "bg-card"} px-3.5 py-2.5 text-left transition-colors duration-150 active:bg-pill`}>
        <Logo symbol={e.symbol} image={e.image} chain={e.chain} token={e.token_address} />
        <span className="min-w-0 flex-1">
          <b className={`block truncate text-[16px] font-medium leading-tight ${dim ? "text-text-2" : ""}`}>
            {name ?? e.name ?? e.symbol}
            {badge && <em className="ml-1.5 rounded-full border border-amber px-1.5 align-[2px] text-[10px] font-semibold not-italic tracking-wide text-amber">{BADGE[badge]}</em>}
          </b>
          <small className="mt-1 flex min-w-0 items-center gap-2 whitespace-nowrap text-[13.5px] text-text-2">
            {e.score != null && <span className="num rounded-full bg-sage px-2 text-[12px] font-semibold leading-normal text-on-sage">{Math.round(e.score)}</span>}
            <span>{e.symbol}</span>
            {e.launched_at && (
              <span className={`flex items-center gap-0.5 ${fresh ? "text-up" : "text-text-3"}`}>
                <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={1.4} strokeLinecap="round" aria-hidden="true"><path d="M8 14V7M8 9c0-3 2-4.5 5-4.5 0 3-2 4.5-5 4.5ZM8 8C8 5.5 6.3 4 3.5 4c0 2.6 1.7 4 4.5 4Z" /></svg>{a}
              </span>
            )}
            {sub && <span className="min-w-0 truncate">{sub}</span>}
          </small>
        </span>
        <span className="flex flex-none flex-col items-end gap-1">
          <b className="num text-[16px] font-semibold leading-none"><i className="mr-1 align-[2px] text-[9px] font-medium not-italic tracking-wide text-text-3">MC</i>{usdShort(e.market_cap)}</b>
          <em className={`num text-[13px] font-medium not-italic ${sign === "up" ? "text-up" : sign === "down" ? "text-down" : "text-text-3"}`}>{chg}</em>
        </span>
      </button>
      {footer}
    </motion.li>
  );
}
