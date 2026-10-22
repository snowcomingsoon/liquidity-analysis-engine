import { useEffect, useState } from "react";
import * as api from "../lib/api";
import type { Gem } from "../lib/types";
import { ClusterCheck } from "../components/ClusterCheck";
import { WAIT } from "../components/SellsMap";

const ADDRESS = /^(0x[0-9a-fA-F]{40}|[1-9A-HJ-NP-Za-km-z]{32,48})$/;
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
  const [asked, setAsked] = useState<{ chain: string; token: string; check?: api.ClusterCheck } | null>(null);
  const s = q.trim();

  useEffect(() => {
    api.getCoordinatedSells().then((d) => setList(d.sample ? [] : d.reports ?? [])).catch(() => setList([]));
  }, []);

  // The asked check: where it stands, again every 15 s while it waits or runs.
  useEffect(() => {
    if (!asked) return;
    let t = 0, live = true;
    const load = () => api.getClusterCheck(asked.chain, asked.token).then((c) => {
      if (!live) return;
      setAsked((a) => a && { ...a, check: c });
      if (c.state === "queued" || c.state === "running") t = window.setTimeout(load, 15000);
      else if (c.state === "built") api.getCoordinatedSells().then((d) => live && setList(d.sample ? [] : d.reports ?? [])).catch(() => {});
    }).catch(() => { if (live) t = window.setTimeout(load, 30000); });
    load();
    return () => { live = false; clearTimeout(t); };
  }, [asked?.chain, asked?.token]);

  const open = (c: string, token: string, symbol?: string) => onToken({ chain: c, token_address: token, symbol: symbol || short(token) } as Gem);
  const chains = [...new Set((list ?? []).map((r) => r.chain))];
  const rows = (list ?? []).filter((r) => chain === "all" || r.chain === chain)
    .sort((a, b) => (b.risk?.score ?? -1) - (a.risk?.score ?? -1));
  const st = asked?.check;

  return (
    <>
      <label className="flex h-12 items-center gap-2 rounded-full bg-card px-4 shadow-[inset_0_0_0_1.5px_var(--c-ink)]">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Paste a token address to check" autoComplete="off" spellCheck={false}
          aria-label="Token address" className="min-w-0 flex-1 bg-transparent text-[16px] outline-none placeholder:text-text-3" />
        {q && <button type="button" aria-label="Clear" onClick={() => setQ("")} className="rounded-md bg-pill px-2 py-0.5 font-mono text-[12px] text-text-2">✕</button>}
      </label>
      {s && (ADDRESS.test(s)
        ? <div className="mt-3"><ClusterCheck address={s} onOpen={(e) => { setAsked({ chain: e.chain, token: s }); setQ(""); }} /></div>
        : <p className="mt-3 text-[13px] text-text-3">Not an address yet: 0x… (40 characters) or a Solana mint.</p>)}
      {asked && (
        <button type="button" onClick={() => open(asked.chain, asked.token)} className="mt-3 flex w-full items-center gap-2.5 rounded-[16px] bg-card p-4 text-left active:bg-pill">
          {(!st || st.state === "running" || st.state === "queued") && <i className="h-2 w-2 flex-none animate-pulse rounded-full bg-amber" aria-hidden="true" />}
          <span className="min-w-0 flex-1">
            <b className="block text-[14px] font-semibold">{short(asked.token)} · {asked.chain}</b>
            <small className={`block text-[13px] ${st?.state === "failed" || st?.state === "unsupported" ? "text-down" : "text-text-2"}`}>
              {!st ? "Asking…" : st.state === "built" && st.clusters ? `${st.clusters} cluster(s) found. Their sells are being read.` : WAIT[st.state].replace(" The map appears here when it", " Open it when it")}
              {st?.state === "queued" && st.place ? ` Place in line: ${st.place}.` : ""}
            </small>
          </span>
          <span className="text-[13px] text-text-3">open ›</span>
        </button>
      )}

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
