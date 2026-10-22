import { useEffect, useState } from "react";
import * as api from "../lib/api";
import type { Gem } from "../lib/types";
import { ClusterCheck } from "../components/ClusterCheck";
import { CheckProgress, useClusterCheck } from "../components/CheckProgress";
import { SellsMap } from "../components/SellsMap";
import { AnimatePresence, motion } from "motion/react";

const short = (a: string) => `${a.slice(0, 4)}…${a.slice(-4)}`;
const ago = (ts?: number | null) => {
  if (!ts) return "—";
  const h = (Date.now() / 1000 - ts) / 3600;
  return h < 1 ? "<1h ago" : h < 48 ? `${Math.round(h)}h ago` : `${Math.round(h / 24)}d ago`;
};
const pct = (x?: number | null) => (x == null ? "—" : `${(x * 100).toFixed(x < 0.1 ? 1 : 0)}%`);
// The real clusters' share of supply (the "top" group is holders with no link found).
const held = (r: api.SellsReport) => r.clusters.filter((c) => c.id !== "top").reduce((s, c) => s + (c.share ?? 0), 0);

/** The Clusters tab (Lorenzo, 22/10: "voglio una tab a parte, oltre ad averlo
 *  sui progetti"): every checked token, riskiest first, and a check by
 *  address. A row opens the token page with its bubble map and waves. */
export function Clusters({ onToken }: { onToken: (e: Gem) => void }) {
  const [q, setQ] = useState("");
  const [list, setList] = useState<api.SellsReport[] | null>(null);
  const [chain, setChain] = useState("all");
  const [asked, setAsked] = useState<{ chain: string; token: string; at: number } | null>(null);
  const [screen, setScreen] = useState(false);
  const s = q.trim();

  useEffect(() => {
    api.getCoordinatedSells().then((d) => setList(d.sample ? [] : d.reports ?? [])).catch(() => setList([]));
  }, []);

  const open = (c: string, token: string, symbol?: string) => onToken({ chain: c, token_address: token, symbol: symbol || short(token) } as Gem);
  const chains = [...new Set((list ?? []).map((r) => r.chain))];
  const rows = (list ?? []).filter((r) => chain === "all" || r.chain === chain)
    .sort((a, b) => (b.risk?.score ?? -1) - (a.risk?.score ?? -1));

  return (
    <>
      <label className="flex h-12 items-center gap-2 rounded-full bg-card px-4 shadow-[inset_0_0_0_1.5px_var(--c-ink)]">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Paste a token address to check" autoComplete="off" spellCheck={false}
          aria-label="Token address" className="min-w-0 flex-1 bg-transparent text-[16px] outline-none placeholder:text-text-3" />
        {q && <button type="button" aria-label="Clear" onClick={() => setQ("")} className="rounded-md bg-pill px-2 py-0.5 font-mono text-[12px] text-text-2">✕</button>}
      </label>
      <div className="mt-3"><ClusterCheck address={s} onStart={(c) => { setAsked({ chain: c, token: s, at: Date.now() }); setScreen(true); }} onOpen={() => setQ("")} onFail={() => { setAsked(null); setScreen(false); }} /></div>
      {asked && <Asked key={asked.at} chain={asked.chain} token={asked.token} onOpen={() => setScreen(true)}
        onReady={() => api.getCoordinatedSells().then((d) => setList(d.sample ? [] : d.reports ?? [])).catch(() => {})} />}
      <AnimatePresence>
        {asked && screen && <LiveCheck key={asked.at} chain={asked.chain} token={asked.token} onClose={() => setScreen(false)}
          onOpen={() => { setScreen(false); open(asked.chain, asked.token); }} />}
      </AnimatePresence>

      <div className="mb-2 mt-5 flex items-center gap-2">
        <h2 className="flex-1 text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">Riskiest first</h2>
        {chains.length > 1 && ["all", ...chains].map((c) => (
          <button key={c} type="button" onClick={() => setChain(c)} aria-pressed={chain === c}
            className={`rounded-full px-2.5 py-1 text-[12px] capitalize ${chain === c ? "bg-ink font-semibold text-on-ink" : "bg-pill text-text-2"}`}>{c}</button>
        ))}
      </div>
      {list == null ? <div className="h-16 animate-pulse rounded-[16px] bg-card" />
        : rows.length ? (
          <ol className="rounded-[16px] bg-card p-1.5">
            {rows.map((r) => {
              const risk = r.risk?.score;
              const last = r.events[0];
              return (
                <li key={`${r.chain}:${r.token}`}>
                  <button type="button" onClick={() => open(r.chain, r.token, r.symbol)} className="flex w-full items-center gap-3 rounded-[12px] px-2 py-2.5 text-left active:bg-pill">
                    <span className="min-w-0 flex-1">
                      <b className="block truncate text-[15px] font-semibold leading-tight">{r.symbol || short(r.token)} <span className="text-[12.5px] font-normal text-text-3">· {r.chain}</span></b>
                      <small className="block truncate text-[12.5px] text-text-3">
                        clusters hold {pct(held(r))} · {last ? `last wave ${ago(last.ts)}, ${pct(last.share_sold)} sold` : "no wave yet"}
                      </small>
                    </span>
                    {risk != null && <span className={`num flex-none rounded-full px-2.5 py-1 text-[13px] font-semibold ${risk >= 60 ? "bg-down/15 text-down" : "bg-pill text-text-2"}`}>{Math.round(risk)}</span>}
                  </button>
                </li>
              );
            })}
          </ol>
        ) : <p className="rounded-[16px] bg-card p-4 text-[14px] text-text-2">No token checked yet. Paste an address above.</p>}
    </>
  );
}

/** The check just asked, live from the tap: steps and bar until its report lands. */
function Asked({ chain, token, onOpen, onReady }: { chain: string; token: string; onOpen: () => void; onReady: () => void }) {
  const { rep, check } = useClusterCheck(chain, token, true);
  useEffect(() => { if (rep) onReady(); }, [rep]);
  return (
    <button type="button" onClick={onOpen} className="mt-3 block w-full text-left">
      {rep ? <span className="flex items-center rounded-[16px] bg-card p-4 text-[14px]"><b className="flex-1 font-semibold">{short(token)} · {chain}: ready</b><span className="text-[13px] text-text-3">open ›</span></span>
        : <CheckProgress check={check} title={`${short(token)} · ${chain}`} />}
    </button>
  );
}

/** The check's own screen (Lorenzo, 22/10: "la schermata che si apre sulla
 *  tab dedicata con il grafico dei cluster che si compila"): steps, counters,
 *  and the bubble map filling in as holders, links and sells are read. */
function LiveCheck({ chain, token, onClose, onOpen }: { chain: string; token: string; onClose: () => void; onOpen: () => void }) {
  return (
    <motion.div role="dialog" aria-modal="true" aria-label="Cluster check" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }}
      transition={{ duration: 0.2 }} className="fixed inset-0 z-40 overflow-y-auto bg-bg">
      <div className="mx-auto max-w-[540px] px-4 pb-28 pt-[calc(12px+env(safe-area-inset-top))]">
        <header className="mb-4 flex items-center gap-2">
          <button type="button" onClick={onClose} aria-label="Back" className="grid h-10 w-10 place-items-center rounded-full bg-pill text-[18px]">‹</button>
          <span className="min-w-0 flex-1">
            <b className="block text-[18px] font-semibold leading-tight">Cluster check</b>
            <small className="block truncate font-mono text-[12px] text-text-3">{chain} · {short(token)}</small>
          </span>
          <button type="button" onClick={onOpen} className="rounded-full bg-ink px-3.5 py-2 text-[13px] font-semibold text-on-ink">Token page</button>
        </header>
        <SellsMap chain={chain} token={token} starting bare />
      </div>
    </motion.div>
  );
}
