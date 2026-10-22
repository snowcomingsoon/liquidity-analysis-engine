import type { Gem } from "../lib/types";
import { isHiddenIn, sortRows, useHidden, useSort } from "../lib/store";
import { TokenRow, gemId } from "../components/TokenRow";
import { SortBar } from "../components/SortBar";
import { ListHead } from "../components/ListHead";

/** Pearl, Early and Top: a head, the sort bar, the rows (top.js paintPearl / paintEarly / paintRank). */
export function GemList({ title, rule, lead, empty, rows, ranked = false, badge, onOpen }: {
  title: string; rule: string; lead: string; empty: string; rows: Gem[]; ranked?: boolean;
  badge?: "early"; onOpen: (e: Gem) => void;
}) {
  const hidden = useHidden();
  const sort = useSort();
  let list = rows.filter((e) => !isHiddenIn(hidden, e.chain, e.token_address));
  // A ranking keeps each gem's place by score whatever the order shown.
  const place = new Map(ranked ? [...list].sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).map((e, i) => [gemId(e), i + 1]) : []);
  if (ranked) list = list.filter((e) => (place.get(gemId(e)) ?? 99) <= 25);
  list = sortRows(list, sort);
  return (
    <>
      <ListHead title={title} rule={rule} lead={lead} />
      <SortBar />
      {list.length
        ? <ol>{list.map((e, i) => (
            <TokenRow key={gemId(e)} e={e} i={i} onOpen={onOpen}
              name={ranked ? `${place.get(gemId(e))}. ${e.name || e.symbol}` : undefined}
              badge={badge ?? (e.early ? "early" : e.hidden ? "hidden" : null)} />
          ))}</ol>
        : <p className="py-4 text-[14px] text-text-2">{empty}</p>}
    </>
  );
}
