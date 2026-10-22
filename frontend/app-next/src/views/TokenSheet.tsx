import { useEffect, useState } from "react";
import * as api from "../lib/api";
import type { Entry } from "../lib/types";
import { Sheet } from "../components/Sheet";
import { Logo } from "../components/Logo";
import { changeText, usdShort } from "../lib/format";
import { toggleWatch, watchId, watched, type Opened } from "./TokenPage";
import { t, locale } from "../lib/i18n";

/** Direction A, screen 3: a tap on a row opens this preview over the list; "Full dossier" opens the token page. */
export function TokenSheet({ open, onClose, onFull }: { open: Opened | null; onClose: () => void; onFull: (o: Opened) => void }) {
  const [entry, setEntry] = useState<Entry | null>(null);
  const [watch, setWatch] = useState(false);
  const e = open?.e;
  useEffect(() => {
    setEntry(null);
    if (!e) return;
    setWatch(watched().has(watchId(e)));
    api.getToken(e.chain, e.token_address).then((r) => setEntry(r.entry)).catch(() => {});
  }, [e]);

  const g = { ...e, ...entry } as Entry;
  const [chg, sign] = changeText(g.change_24h);
  const score = g.score == null ? null : Math.round(g.score);
  const good = entry?.judge?.strengths?.[0] ?? entry?.summary ?? entry?.why;
  const weak = entry?.judge?.problems?.[0];
  const u = g.usage ?? {};
  const kpis: [string, string][] = [
    [t("Volume 7d"), u.vol_7d_avg != null ? t("{v}/d", { v: usdShort(u.vol_7d_avg) }) : "—"],
    [t("Holders"), u.holders != null ? u.holders.toLocaleString(locale()) : "—"],
    [t("Volume 24h"), usdShort(u.vol_24h)],
    [t("Liquidity"), usdShort(g.liquidity_usd)],
  ];
  return (
    <Sheet open={!!open} onClose={onClose} title={undefined}>
      {e && (
        <div className="grid gap-2.5">
          <div className="flex items-center gap-3">
            <Logo size={42} symbol={g.symbol} image={g.image} chain={g.chain} token={g.token_address} />
            <span className="min-w-0 flex-1">
              <b className="block truncate text-[17px] font-semibold leading-tight">{g.name || g.symbol}</b>
              <small className="block truncate text-[12.5px] text-text-3">{[g.symbol, open?.context?.split(` · ${t("score")} `)[0], g.chain].filter(Boolean).join(" · ")}</small>
            </span>
            <span className="flex flex-col items-end">
              <b className="num text-[16px] font-semibold">{usdShort(g.market_cap)}</b>
              <em className={`num text-[12.5px] not-italic ${sign === "up" ? "text-up" : sign === "down" ? "text-down" : "text-text-3"}`}>{chg}</em>
            </span>
          </div>
          <div className="flex items-center gap-3 rounded-[16px] bg-sage p-3 text-on-sage">
            <svg viewBox="0 0 44 44" className="h-12 w-12 flex-none" aria-hidden="true">
              <circle cx="22" cy="22" r="18" fill="none" stroke="var(--c-card)" strokeWidth="5" />
              <circle cx="22" cy="22" r="18" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" strokeDasharray={`${((score ?? 0) / 100) * 113} 113`} transform="rotate(-90 22 22)" />
              <text x="22" y="26.5" textAnchor="middle" fontSize="13" fontWeight="700" fill="currentColor">{score ?? "—"}</text>
            </svg>
            <span className="min-w-0 flex-1">
              <b className="line-clamp-2 text-[14.5px] font-semibold leading-snug">{good ?? (entry ? t("No review yet") : t("Loading the review…"))}</b>
              {weak && <small className="mt-0.5 line-clamp-2 block text-[12.5px] opacity-80">{t("Weak point: {w}", { w: weak })}</small>}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {kpis.map(([l, v]) => (
              <div key={l} className="rounded-[12px] bg-bg px-3 py-2">
                <div className="text-[10.5px] font-medium uppercase tracking-[0.07em] text-text-3">{l}</div>
                <div className="num text-[17px] font-semibold">{v}</div>
              </div>
            ))}
          </div>
          <div className="mt-1 flex gap-2">
            <button type="button" aria-pressed={watch} onClick={() => setWatch(toggleWatch(watchId(e)))}
              className="h-12 flex-1 rounded-full bg-pill text-[15px] font-semibold">{watch ? t("★ Watching") : t("☆ Watch")}</button>
            <button type="button" onClick={() => open && onFull(open)} className="h-12 flex-1 rounded-full bg-ink text-[15px] font-semibold text-on-ink">{t("Full dossier")}</button>
          </div>
        </div>
      )}
    </Sheet>
  );
}
