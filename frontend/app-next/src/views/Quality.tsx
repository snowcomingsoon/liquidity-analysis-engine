import { useCallback, useEffect, useState } from "react";
import * as api from "../lib/api";
import type { Gem, QualityLists, QualityRow } from "../lib/types";
import { TokenRow, gemId } from "../components/TokenRow";
import { ListHead } from "../components/ListHead";
import { t } from "../lib/i18n";

// Quality (quality.js, Lorenzo 21/10): projects of quality 80 or more outside
// his Top 25, to accept into the gems or discard. One account's: the server
// answers 404 to the others and the dock button stays hidden.

const POLL_MS = 60_000;
const WHERE: Record<string, string> = { top: "In the Top 25", arena: "In the arenas", early: "In Early", out: "Out" };
const PILLARS: [string, string][] = [["github", "GitHub"], ["site", "Site"], ["tokenomics", "Holders"]];
type Act = "accept" | "discard" | "reset";

const line = (e: QualityRow) => [t("Quality {n}", { n: Math.round(e.quality ?? 0) }),
  ...PILLARS.filter(([k]) => e.pillars?.[k] != null).map(([k, label]) => `${t(label)} ${Math.round(e.pillars![k])}`)].join(" · ");

export const qualityContext = (e: Gem & { quality?: number }) => `${t("Quality {n}", { n: Math.round(e.quality ?? 0) })} · ${t("score {n}", { n: Math.round(e.score ?? 0) })}`;

export function Quality({ onOpen }: { onOpen: (e: Gem) => void }) {
  const [data, setData] = useState<QualityLists | null>(null);
  const [busy, setBusy] = useState("");
  const [fold, setFold] = useState(false);

  const load = useCallback(() => api.getQuality().then(setData).catch(() => {}), []);
  useEffect(() => {
    load();
    const t = setInterval(() => document.visibilityState === "visible" && load(), POLL_MS);
    return () => clearInterval(t);
  }, [load]);

  async function decide(e: QualityRow, act: Act) {
    if (busy) return;
    setBusy(`${gemId(e)}:${act}`);
    try { await api.decideQuality(e.chain, e.token_address, act); await load(); }
    catch { /* the button comes back */ }
    finally { setBusy(""); }
  }

  const row = (e: QualityRow, i: number, actions: [Act, string][], note = "") => (
    // The row as quality.js draws it: cap, change, score and age, no market line (the pillars are below).
    <TokenRow key={gemId(e)} e={{ ...e, fdv: undefined, usage: undefined, liquidity_usd: undefined }} i={i} onOpen={() => onOpen(e)} footer={
      // The pillars under the row, whole: in the row's subline a phone cut them.
      <div className="flex flex-wrap items-center justify-end gap-2 px-2.5 pb-2.5">
        <span className="basis-full text-[11.5px] leading-[1.45] text-text-2">{line(e)}{note && <><br />{note}</>}</span>
        {actions.map(([act, label]) => (
          <button key={act} type="button" disabled={!!busy} onClick={() => decide(e, act)}
            className={`rounded-full px-3.5 py-1.5 text-[13px] font-medium disabled:opacity-50 ${act === "accept" ? "bg-text text-bg" : "border border-line"}`}>
            {busy === `${gemId(e)}:${act}` ? "…" : t(label)}
          </button>
        ))}
      </div>
    } />
  );

  const waiting = data?.waiting ?? [], accepted = data?.accepted ?? [], discarded = data?.discarded ?? [];
  return (
    <>
      <ListHead title={t("Quality")} rule={t("quality 80 or more, outside the Top 25")}
        lead={t("Projects whose code, site and holders score 80 or more, whatever their score or usage. Accept one and it joins the gems past the score bar: every other rule still applies, and it leaves when it fails one (a crash first). Research, not advice.")} />
      <ol className="mt-3">{waiting.map((e, i) => row(e, i, [["accept", "Accept"], ["discard", "Discard"]],
        e.where === "arena" ? t("Already in the arenas") : e.where === "early" ? t("Already in Early") : ""))}</ol>
      {data && !waiting.length && <p className="py-4 text-[14px] text-text-2">{t("No project of quality 80 or more waits for a decision.")}</p>}
      {accepted.length > 0 && (
        <>
          <header className="mt-5 flex items-baseline gap-2"><h3 className="text-[20px] font-semibold">{t("Accepted")}</h3><span className="text-[12.5px] text-text-3">{t("where each one is now")}</span></header>
          <ol className="mt-2">{accepted.map((e, i) => row(e, i, [["reset", "Undo"]], e.where === "out" ? t("Out: {why}", { why: e.why ?? "" }) : t(WHERE[e.where ?? ""] ?? "")))}</ol>
        </>
      )}
      {discarded.length > 0 && (
        <section className="mt-4">
          <button type="button" aria-expanded={fold} onClick={() => setFold(!fold)} className="flex items-center gap-2 py-2 text-[15px] font-medium text-text-2">
            {t("Discarded")} <small className="rounded-full bg-pill px-2 text-[12px]">{discarded.length}</small>
            <svg viewBox="0 0 24 24" className={`h-4 w-4 transition-transform ${fold ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
          </button>
          {fold && <ol>{discarded.map((e, i) => row(e, i, [["reset", "Restore"]]))}</ol>}
        </section>
      )}
    </>
  );
}
