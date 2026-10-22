import { motion } from "motion/react";

export type View = "gems" | "pearl" | "top" | "rank" | "quality" | "agent" | "profile";

const ICONS: Record<Exclude<View, "profile">, React.ReactNode> = {
  gems: <><circle cx="9.5" cy="10" r="6" /><path d="M15.2 8.4a6 6 0 1 1-6.8 8.3" /></>,
  pearl: <><circle cx="12" cy="13" r="6.5" /><path d="M9.5 11a3 3 0 0 1 3-2" /><path d="M5 5.5 7 7.5M19 5.5 17 7.5M12 3v2" /></>,
  top: <><path d="M12 20v-8" /><path d="M12 12c0-3.5-2.5-6-6.5-6 0 3.5 2.5 6 6.5 6Z" /><path d="M12 13.5c0-3 2.2-5.5 6.5-5.5 0 3-2.2 5.5-6.5 5.5Z" /></>,
  rank: <><path d="M5 20V12M12 20V5M19 20v-5" /><path d="M3 20h18" /></>,
  quality: <path d="m12 3.5 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9Z" />,
  agent: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3.5" /><circle cx="12" cy="12" r="1" fill="currentColor" /></>,
};
export const LABEL: Record<View, string> = { gems: "Gems", pearl: "Pearl", top: "Early", rank: "Top", quality: "Quality", agent: "Scout", profile: "Profile" };

/** The floating deep green bar and the round search button (classic.css #dock); the sage pill slides to the chosen view. */
export function Dock({ view, views, onView, onSearch, initial }: {
  view: View; views: View[]; onView: (v: View) => void; onSearch: () => void; initial: string;
}) {
  return (
    <>
      <nav aria-label="Sections"
        className="fixed bottom-[calc(14px+env(safe-area-inset-bottom))] left-4 z-30 flex h-16 w-[calc(100vw-32px-70px)] max-w-[560px] gap-0.5 rounded-full border border-float-line bg-float p-1 shadow-float">
        {views.map((v) => {
          const on = v === view;
          return (
            <button key={v} type="button" onClick={() => onView(v)} aria-label={LABEL[v]} aria-current={on || undefined}
              className={`relative flex h-14 min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-full transition-colors duration-200 ${on ? "text-on-sage" : "text-sage/80"}`}>
              {on && <motion.span layoutId="dock-pill" className="absolute inset-0 rounded-full bg-sage" transition={{ type: "spring", stiffness: 520, damping: 42 }} />}
              <span className="relative h-5 w-5">
                {v === "profile"
                  ? <i className={`grid h-full w-full place-items-center rounded-full text-[10px] not-italic ${on ? "bg-ink text-on-ink" : "bg-sage/20 text-on-ink"}`}>{initial}</i>
                  : <svg viewBox="0 0 24 24" className="h-full w-full" fill="none" stroke="currentColor" strokeWidth={on ? 2.1 : 1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{ICONS[v]}</svg>}
              </span>
              <span className="relative max-w-full truncate text-[9.5px] font-medium leading-none">{LABEL[v]}</span>
            </button>
          );
        })}
      </nav>
      <button type="button" onClick={onSearch} aria-label="Search a token"
        className="fixed bottom-[calc(14px+env(safe-area-inset-bottom))] right-4 z-30 grid h-16 w-16 place-items-center rounded-full border border-float-line bg-float text-on-ink shadow-float">
        <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" aria-hidden="true"><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4.5 4.5" /></svg>
      </button>
    </>
  );
}
