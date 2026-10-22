import { useEffect, useState } from "react";
import type { Entry } from "../lib/types";
import { t } from "../lib/i18n";

// Direction A, screen 4: what changed since this phone last opened the token, then the score's blocks.
const BLOCKS: [string, string][] = [["github", "Code"], ["site", "Research"], ["tokenomics", "Token"], ["traction", "Usage"]];
type Seen = { t: number; score?: number; b: Record<string, number> };

const blocks = (e: Entry) => Object.fromEntries(BLOCKS.map(([k]) => [k, k === "traction" ? e.traction?.traction : e.pillars?.[k]?.score])
  .filter(([, v]) => v != null).map(([k, v]) => [k, Math.round(v as number)])) as Record<string, number>;
const key = (e: Entry) => `seen-v1:${e.chain}:${e.token_address}`;
const ago = (at: number) => { const h = (Date.now() - at) / 36e5; return h < 1 ? t("within the hour") : h < 24 ? t("{n}h ago", { n: Math.round(h) }) : t("{n}d ago", { n: Math.round(h / 24) }); };

export function Glance({ e }: { e: Entry }) {
  const [before, setBefore] = useState<Seen | null | undefined>(undefined);
  const now: Seen = { t: Date.now(), score: e.score == null ? undefined : Math.round(e.score), b: blocks(e) };
  useEffect(() => {
    let prev: Seen | null = null;
    try { prev = JSON.parse(localStorage.getItem(key(e)) || "null"); } catch { /* none */ }
    setBefore(prev);
    try { localStorage.setItem(key(e), JSON.stringify(now)); } catch { /* private mode */ }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [e.chain, e.token_address]);

  const changes: [string, number, number][] = [];
  if (before) {
    if (before.score != null && now.score != null && before.score !== now.score) changes.push([t("Score"), before.score, now.score]);
    for (const [k, label] of BLOCKS) if (before.b[k] != null && now.b[k] != null && before.b[k] !== now.b[k]) changes.push([t(label), before.b[k], now.b[k]]);
  }
  const bars = BLOCKS.filter(([k]) => now.b[k] != null);
  return (
    <>
      <h3 className="mb-2 mt-4 text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">{t("Since you last looked")}</h3>
      <ul className="rounded-[16px] bg-card px-4 py-2.5 text-[14px]">
        {before === null && <li className="py-0.5 text-text-2">{t("First look from this phone: changes show here next time.")}</li>}
        {before && !changes.length && <li className="flex py-0.5"><span className="flex-1 text-text-2">{t("No change")}</span><span className="font-mono text-[12px] text-text-3">{ago(before.t)}</span></li>}
        {changes.map(([l, a, b]) => (
          <li key={l} className="flex py-0.5"><span className="flex-1">{l} {a} → {b}</span><span className={`num font-medium ${b > a ? "text-up" : "text-down"}`}>{b > a ? "+" : ""}{b - a}</span></li>
        ))}
      </ul>
      {bars.length > 0 && (
        <ul className="mt-2 rounded-[16px] bg-card px-4 py-2.5 text-[14px]">
          {bars.map(([k, label]) => (
            <li key={k} className="flex items-center gap-3 py-1">
              <span className="flex-1">{t(label)}</span>
              <i className="h-[5px] w-[120px] overflow-hidden rounded-full bg-pill"><i className="block h-full rounded-full bg-ink" style={{ width: `${now.b[k]}%` }} /></i>
              <b className="num w-7 text-right font-semibold">{now.b[k]}</b>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
