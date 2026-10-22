import { useEffect, useRef, useState } from "react";
import * as api from "../lib/api";
import type { Project } from "../lib/types";
import type { SectorsView } from "../lib/sectors";
import { Logo } from "../components/Logo";
import { usdShort } from "../lib/format";
import type { Gem } from "../lib/types";
import { Scan } from "../components/Scan";
import { ClusterCheck } from "../components/ClusterCheck";
import { t } from "../lib/i18n";

const ADDRESS = /^(0x[0-9a-fA-F]{40}|[1-9A-HJ-NP-Za-km-z]{32,48})$/;

const RECENT_KEY = "search-recent-v1";
const RECENT_MAX = 8;
const HITS = 8;

function recent(): string[] { try { return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]"); } catch { return []; } }
function remember(s: string) {
  const list = [s, ...recent().filter((x) => x !== s)].slice(0, RECENT_MAX);
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(list)); } catch { /* private mode */ }
}

/** The one search (direction A, screen 6): projects in the database, sectors, and recent searches. */
export function Search({ sectors, onProject, onSector, onToken }: { sectors: SectorsView | null; onProject: (p: Project) => void; onSector: (key: string) => void; onToken: (e: Gem) => void }) {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Project[] | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const s = q.trim();

  useEffect(() => {
    if (!s) { setHits(null); return; }
    const t = setTimeout(() => api.getProjects({ q: s, sort: "score", limit: HITS }).then((d) => setHits(d.items ?? [])).catch(() => setHits([])), 250);
    return () => clearTimeout(t);
  }, [s]);

  const low = s.toLowerCase();
  const secHits = !s ? [] : (sectors?.sectors ?? []).filter((x) => x.label.toLowerCase().includes(low) || x.key.toLowerCase().includes(low));
  const open = (p: Project) => { remember(p.symbol || s); onProject(p); };
  const last = recent();

  return (
    <>
      <label className="flex h-12 items-center gap-2 rounded-full bg-card px-4 shadow-[inset_0_0_0_1.5px_var(--c-ink)]">
        <svg viewBox="0 0 24 24" className="h-5 w-5 flex-none text-text-3" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" aria-hidden="true"><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4.5 4.5" /></svg>
        <input ref={input} autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("Project, ticker, sector or address")} autoComplete="off" spellCheck={false}
          aria-label={t("Search")} className="min-w-0 flex-1 bg-transparent text-[16px] outline-none placeholder:text-text-3" />
        {q && <button type="button" aria-label={t("Clear")} onClick={() => { setQ(""); input.current?.focus(); }} className="rounded-md bg-pill px-2 py-0.5 font-mono text-[12px] text-text-2">✕</button>}
      </label>

      {s && (
        <>
          <Label>{t("Projects")}</Label>
          {hits == null ? <div className="h-16 animate-pulse rounded-[16px] bg-card" />
            : hits.length ? (
              <ol className="rounded-[16px] bg-card p-1.5">
                {hits.map((p) => (
                  <li key={`${p.chain}:${p.token}`}>
                    <button type="button" onClick={() => open(p)} className="flex w-full items-center gap-3 rounded-[12px] px-2 py-2 text-left active:bg-pill">
                      <Logo size={36} symbol={p.symbol} image={p.image} chain={p.chain} token={p.token} />
                      <span className="min-w-0 flex-1">
                        <b className="block truncate text-[15px] font-semibold leading-tight">{p.name || p.symbol}</b>
                        <small className="block truncate text-[12.5px] text-text-3">{p.symbol} · {p.chain} · {p.score == null ? p.status : t("score {n}", { n: Math.round(p.score) })}</small>
                      </span>
                      <span className="num text-[13px] text-text-3">{usdShort(p.mcap)}</span>
                    </button>
                  </li>
                ))}
              </ol>
            ) : <p className="rounded-[16px] bg-card p-4 text-[14px] text-text-2">{t("No project called “{s}” in the database.", { s })}</p>}
          {secHits.length > 0 && (
            <>
              <Label>{t("Sectors")}</Label>
              <div className="grid gap-1.5">
                {secHits.map((x) => (
                  <button key={x.key} type="button" onClick={() => onSector(x.key)} className="flex items-center rounded-[16px] bg-card px-4 py-3 text-left active:bg-pill">
                    <b className="flex-1 text-[15px] font-semibold">{x.label} · {t("{n} projects", { n: x.size })}</b>
                    <span className="text-[13px] text-text-3">{t("open ›")}</span>
                  </button>
                ))}
              </div>
            </>
          )}
          {ADDRESS.test(s) && <><Label>{t("Wallet clusters")}</Label><ClusterCheck address={s} onOpen={(e) => { remember(s); onToken(e); }} /></>}
          <Label>{hits?.length ? t("Something else?") : t("Not in the database yet")}</Label>
          <Scan key={s} query={s} onOpen={(e) => { remember(e.symbol || s); onToken(e); }} />
        </>
      )}

      {last.length > 0 && (
        <>
          <Label>{t("Recent")}</Label>
          <div className="flex flex-wrap gap-1.5">
            {last.map((x) => <button key={x} type="button" onClick={() => setQ(x)} className="rounded-full bg-pill px-3 py-1.5 text-[13px] text-text-2">{x}</button>)}
          </div>
        </>
      )}
    </>
  );
}

const Label = ({ children }: { children: React.ReactNode }) =>
  <h2 className="mb-2 mt-5 text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">{children}</h2>;
