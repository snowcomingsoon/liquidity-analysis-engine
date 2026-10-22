import { motion } from "motion/react";
import { t } from "../lib/i18n";

export type View = "today" | "sectors" | "watch" | "search" | "gems" | "pearl" | "top" | "rank" | "quality" | "agent" | "clusters" | "profile";

const ICONS: Partial<Record<View, React.ReactNode>> = {
  today: <path d="M4 13h3l2.5-6 4 11 2.5-5H20" />,
  sectors: <><rect x="3.5" y="3.5" width="9" height="9" rx="2" /><rect x="14.5" y="3.5" width="6" height="6" rx="1.5" /><rect x="14.5" y="11.5" width="6" height="9" rx="1.5" /><rect x="3.5" y="14.5" width="9" height="6" rx="2" /></>,
  watch: <path d="m12 4 2.4 4.9 5.4.8-3.9 3.8.9 5.4L12 16.4l-4.8 2.5.9-5.4-3.9-3.8 5.4-.8Z" />,
  clusters: <><circle cx="7" cy="8" r="3" /><circle cx="17" cy="7" r="2.2" /><circle cx="14" cy="17" r="3.5" /><path d="m9.6 9.6 2.3 4.4M9.9 7.7l4.9-.5M16.6 9.2l-1.6 4.3" /></>,
  search: <><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
};
export const LABEL: Record<View, string> = {
  today: "Today", sectors: "Sectors", watch: "Watch", search: "Search", gems: "Gems", pearl: "Pearl", top: "Early", rank: "Top", quality: "Quality", agent: "Scout", clusters: "Clusters", profile: "Profile",
};
export const DOCK: View[] = ["today", "sectors", "clusters", "watch", "search"];

/** Direction A's bar (Lorenzo 22/10, "come in questo pdf"): five places on an ink pill (Clusters added, Lorenzo 22/10: "voglio una tab a parte"), the chosen one on sage. */
export function Dock({ view, onView }: { view: View; onView: (v: View) => void }) {
  return (
    <nav aria-label={t("Sections")}
      className="fixed inset-x-3.5 bottom-[calc(14px+env(safe-area-inset-bottom))] z-30 mx-auto flex max-w-[540px] justify-around rounded-full bg-ink px-2 py-2 shadow-float">
      {DOCK.map((v) => {
        const on = v === view;
        return (
          <button key={v} type="button" onClick={() => onView(v)} aria-label={t(LABEL[v])} aria-current={on || undefined}
            className={`relative flex h-[52px] min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-full transition-colors duration-200 ${on ? "font-semibold text-ink" : "font-medium text-[#aeb7a9]"}`}>
            {on && <motion.span layoutId="dock-pill" className="absolute inset-0 rounded-full bg-sage" transition={{ type: "spring", stiffness: 520, damping: 42 }} />}
            <svg viewBox="0 0 24 24" className="relative h-5 w-5" fill="none" stroke="currentColor" strokeWidth={on ? 2.1 : 1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{ICONS[v]}</svg>
            <span className="relative text-[11.5px] leading-none">{t(LABEL[v])}</span>
          </button>
        );
      })}
    </nav>
  );
}
