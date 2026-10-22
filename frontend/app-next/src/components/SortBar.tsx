import { pickSort, useSort, type SortBy } from "../lib/store";

const SORTS: [SortBy["by"], string][] = [["score", "Score"], ["cap", "Cap"], ["new", "Newest"]];

/** One order for every gem list; tapping the chosen one again reverses it (top.js). */
export function SortBar() {
  const s = useSort();
  return (
    <nav className="my-3 flex gap-1.5" aria-label="Sort the gems">
      {SORTS.map(([k, l]) => (
        <button key={k} type="button" onClick={() => pickSort(k)} aria-pressed={s.by === k}
          className={`h-[30px] rounded-full border px-3 text-[12.5px] font-medium transition-colors duration-200 ${s.by === k ? "border-ink bg-ink text-on-ink" : "border-line bg-transparent text-text-2"}`}>
          {l}{s.by === k ? ` ${s.desc ? "↓" : "↑"}` : ""}
        </button>
      ))}
    </nav>
  );
}
