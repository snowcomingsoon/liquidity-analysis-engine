import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import * as api from "../lib/api";
import type { Narrative, Project, ProjectStats } from "../lib/types";
import { coverage, isHiddenIn, setNarratives, useHidden, useNarratives } from "../lib/store";
import { num } from "../lib/format";
import { Sheet } from "../components/Sheet";
import { t } from "../lib/i18n";

// The project database (projects.js): everything the Gem Finder has seen, its verdict and why.
const PAGE = 30;
const CHAINS: Record<string, string> = { solana: "Solana", robinhood: "Robinhood", base: "Base", bsc: "BSC", ethereum: "Ethereum", arc: "Arc", layer: "Layer" };
const LABEL: Record<string, string> = { ranked: "Ranked", studied: "Studied", rejected: "Rejected", new: "Waiting", analyzing: "Analyzing" };
const LAYERS: Record<string, string> = { L0: "Layer 0", L1: "Layer 1", L2: "Layer 2" };
const VERDICTS = ["ranked", "studied", "rejected", "new"];
const KINDS = ["L0", "L1", "L2", "solana", "bsc", "ethereum", "base", "robinhood", "arc"];
const kindLabel = (k: string) => LAYERS[k] ?? CHAINS[k] ?? k;
const usd = (v?: number) => (v == null ? "—" : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${Math.round(v / 1e3)}k` : `$${Math.round(v)}`);

type Q = { q: string; status: string; kind: string };

export function Database({ onOpen, scan }: { onOpen: (p: Project) => void; scan: React.ReactNode }) {
  const [query, setQuery] = useState<Q>({ q: "", status: "", kind: "" });
  const [items, setItems] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState(false);
  const [narratives, setNarrList] = useState<Narrative[]>([]);
  const narr = useNarratives();
  const hidden = useHidden();
  const typing = useRef<number>(0);
  const [text, setText] = useState("");

  useEffect(() => { coverage().then((l) => setNarrList([...l].sort((a, b) => (b.projects ?? 0) - (a.projects ?? 0)))); }, []);

  async function load(offset = 0) {
    const params: Record<string, string | number> = { q: query.q, status: query.status, sort: "score", limit: PAGE, offset };
    if (query.kind) params[LAYERS[query.kind] ? "layer" : "chain"] = query.kind;
    if (narr.length) params.narrative = narr.join(",");
    try {
      const d = await api.getProjects(params);
      setItems((cur) => (offset ? [...cur, ...(d.items ?? [])] : d.items ?? []));
      setTotal(d.total ?? 0);
      if (d.stats) setStats(d.stats);
    } catch { /* keep what is shown */ }
    setLoading(false);
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(0); }, [query, narr.join(",")]);

  const labels = Object.fromEntries(narratives.map((n) => [n.key, n.label ?? n.key]));
  const chips: [string, string][] = [
    ...(query.status ? [["status", t(LABEL[query.status])] as [string, string]] : []),
    ...(query.kind ? [["kind", kindLabel(query.kind)] as [string, string]] : []),
    ...narr.map((k) => [`narr:${k}`, labels[k] ?? k] as [string, string]),
  ];
  const clear = (k: string) => {
    if (k === "all") { setQuery({ ...query, status: "", kind: "" }); setNarratives([]); return; }
    if (k === "status" || k === "kind") { setQuery({ ...query, [k]: "" }); return; }
    setNarratives(narr.filter((x) => `narr:${x}` !== k));
  };
  const shown = items.filter((p) => !isHiddenIn(hidden, p.chain, p.token));
  const band = stats?.band_by_status ?? stats?.by_status ?? {};
  const bc = stats?.by_chain ?? {};

  return (
    <section>
      {scan}
      <header className="mt-5 flex items-baseline justify-between gap-2">
        <h3 className="text-[20px] font-semibold">{t("Project database")}</h3>
      </header>
      {stats && (
        <>
          <p className="mt-1 text-[12px] text-text-3">
            {num(bc.solana)} Solana · {num(bc.robinhood)} Robinhood · {num(bc.base)} Base · {num(bc.ethereum)} Ethereum{bc.arc ? ` · ${num(bc.arc)} Arc` : ""}{bc.layer ? ` · ${num(bc.layer)} Layer` : ""}
          </p>
          <p className="mt-1.5 text-[13px] leading-snug text-text-2">
            <b>{num(stats.total)}</b> {t("projects known")} · <b>{num(stats.in_band)}</b> {t("in the {a}–{b} band", { a: usd(stats.band?.[0] ?? 10000), b: usd(stats.band?.[1] ?? 10000000) })} · <b>{num((band.studied ?? 0) + (band.ranked ?? 0))}</b> {t("studied")} · <b>{num(band.rejected ?? 0)}</b> {t("rejected")} · <b>{num(stats.band_waiting ?? 0)}</b> {t("waiting")}{stats.top_rejections?.[0] ? ` ${t("(most often: {why})", { why: stats.top_rejections[0].why })}` : ""}
          </p>
        </>
      )}
      <div className="mt-3 flex gap-2">
        <input type="search" value={text} placeholder={t("Search name, ticker, address or site")} aria-label={t("Search the project database")} autoComplete="off"
          onChange={(ev) => { setText(ev.target.value); clearTimeout(typing.current); const v = ev.target.value.trim(); typing.current = window.setTimeout(() => setQuery((q) => ({ ...q, q: v })), 250); }}
          className="h-12 min-w-0 flex-1 rounded-full border border-line bg-transparent px-5 text-[16px] outline-none placeholder:text-text-3 focus:border-text-3" />
        <button type="button" onClick={() => setFilters(true)} aria-haspopup="dialog"
          className={`flex h-12 flex-none items-center gap-1.5 rounded-full px-4 text-[15px] font-medium ${chips.length ? "bg-ink text-on-ink" : "bg-pill text-text"}`}>
          <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" aria-hidden="true"><path d="M2 4h12M4.5 8h7M7 12h2" /></svg>
          {t("Filters")}{chips.length > 0 && <span className="num rounded-full bg-sage px-1.5 text-[12px] text-on-sage">{chips.length}</span>}
        </button>
      </div>
      {chips.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {chips.map(([k, l]) => <button key={k} type="button" onClick={() => clear(k)} className="rounded-full bg-sage px-3 py-1 text-[13px] text-on-sage">{l} <span aria-hidden="true">✕</span></button>)}
          {chips.length > 1 && <button type="button" onClick={() => clear("all")} className="rounded-full px-3 py-1 text-[13px] text-text-2 underline">{t("Clear all")}</button>}
        </div>
      )}
      <ol className="mt-3">
        {shown.length ? shown.map((p, i) => <ProjectRow key={`${p.chain}:${p.token}`} p={p} i={i} onOpen={onOpen} />)
          : !loading && <li className="py-4 text-[14px] text-text-2">{narr.length ? t("No project in these narratives yet.") : query.q || query.status || query.kind ? t("Nothing matches.") : t("The database is filling up: sources are being read.")}</li>}
      </ol>
      {items.length < total && (
        <button type="button" onClick={() => load(items.length)} className="mt-1 h-11 w-full rounded-full bg-pill text-[15px] font-medium">{t("Show more")}</button>
      )}
      <Sheet open={filters} title={t("Filters")} sub={t("Pick what the database shows.")} onClose={() => setFilters(false)}>
        <FilterBody stats={stats} total={total} query={query} narratives={narratives} narr={narr}
          setStatus={(s) => setQuery({ ...query, status: s })} setKind={(k) => setQuery({ ...query, kind: k })}
          onReset={() => clear("all")} onDone={() => setFilters(false)} />
      </Sheet>
    </section>
  );
}

function ProjectRow({ p, i, onOpen }: { p: Project; i: number; onOpen: (p: Project) => void }) {
  const score = p.score == null ? "—" : Math.round(p.score);
  const out = p.status !== "ranked" && p.score != null;
  let site = "";
  try { site = p.website ? new URL(p.website).hostname.replace(/^www\./, "") : ""; } catch { /* not a URL */ }
  const layer = p.chain === "layer" && p.overall?.layer && LAYERS[p.overall.layer] ? p.overall.layer : "";
  return (
    <motion.li initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.26, delay: Math.min(i, 8) * 0.02 }} className="mb-2">
      <button type="button" onClick={() => onOpen(p)} className="flex w-full items-start gap-3 rounded-[20px] bg-card px-3.5 py-3 text-left active:bg-pill">
        <span className={`num w-7 flex-none pt-0.5 text-[15px] font-semibold ${out ? "line-through decoration-1 opacity-45" : ""}`}
          title={out ? t("Score, not on the board") : t("Score")}>{score}</span>
        <span className="min-w-0 flex-1">
          <b className="block text-[15px] font-semibold">{p.symbol ?? "?"}{layer && <i className="ml-1 rounded bg-pill px-1 text-[10px] not-italic">{layer}</i>}</b>
          <span className="block truncate text-[14px] text-text-2">{p.name}</span>
          <small className="mt-0.5 block truncate text-[12.5px] text-text-3">
            {layer ? LAYERS[layer] : CHAINS[p.chain] ?? p.chain} · cap {usd(p.mcap)} · liq {usd(p.liq)}{site ? ` · ${site}` : ""}{p.github ? ` · ${t("code")}` : ""}
          </small>
          {p.why && <small className="mt-0.5 block text-[12.5px] leading-snug text-text-2">{p.why}</small>}
        </span>
        <em className={`flex-none rounded-full bg-pill px-2 py-0.5 text-[11px] not-italic ${p.status === "rejected" ? "text-down" : "text-text-2"}`}>{LABEL[p.status] ? t(LABEL[p.status]) : p.status}</em>
      </button>
    </motion.li>
  );
}

function Opt({ on, label, count, onClick }: { on: boolean; label: string; count?: number; onClick: () => void }) {
  return (
    <button type="button" aria-pressed={on} onClick={onClick}
      className={`rounded-full px-3.5 py-2 text-[14px] transition-colors ${on ? "bg-sage text-on-sage" : "bg-pill text-text"}`}>
      {label}{count != null && <small className="num ml-1 opacity-70">{num(count)}</small>}
    </button>
  );
}

function FilterBody({ stats, total, query, narratives, narr, setStatus, setKind, onReset, onDone }: {
  stats: ProjectStats | null; total: number; query: Q; narratives: Narrative[]; narr: string[];
  setStatus: (s: string) => void; setKind: (k: string) => void; onReset: () => void; onDone: () => void;
}) {
  const by = stats?.by_status ?? {};
  const kindN = (k: string) => (LAYERS[k] ? stats?.by_layer?.[k] : stats?.by_chain?.[k]) ?? 0;
  const sel = new Set(narr);
  const toggle = (k: string) => setNarratives(!k ? [] : sel.has(k) ? narr.filter((x) => x !== k) : [...narr, k]);
  const H = ({ children }: { children: React.ReactNode }) => <h4 className="mb-2 mt-4 text-[13px] font-semibold uppercase tracking-wide text-text-3">{children}</h4>;
  return (
    <div>
      <H>{t("Verdict")}</H>
      <div className="flex flex-wrap gap-1.5">
        <Opt on={!query.status} label={t("All")} count={stats?.total} onClick={() => setStatus("")} />
        {VERDICTS.map((v) => <Opt key={v} on={query.status === v} label={t(LABEL[v])} count={by[v] ?? 0} onClick={() => setStatus(v)} />)}
      </div>
      <H>{t("Type")}</H>
      <div className="flex flex-wrap gap-1.5">
        <Opt on={!query.kind} label={t("All")} onClick={() => setKind("")} />
        {KINDS.map((k) => <Opt key={k} on={query.kind === k} label={LAYERS[k] ? k : kindLabel(k)} count={kindN(k)} onClick={() => setKind(k)} />)}
      </div>
      {narratives.length > 0 && (
        <>
          <H>{t("Narratives")} <small className="normal-case tracking-normal">{t("any of")}</small></H>
          <div className="flex flex-wrap gap-1.5">
            <Opt on={!sel.size} label={t("All")} onClick={() => toggle("")} />
            {narratives.map((n) => <Opt key={n.key} on={sel.has(n.key)} label={n.label ?? n.key} count={n.projects} onClick={() => toggle(n.key)} />)}
          </div>
        </>
      )}
      <footer className="sticky bottom-0 mt-5 grid grid-cols-2 gap-2 bg-card pt-2">
        <button type="button" onClick={onReset} className="h-12 rounded-full bg-pill text-[15px] font-medium">{t("Reset")}</button>
        <button type="button" onClick={onDone} className="h-12 rounded-full bg-ink text-[15px] font-medium text-on-ink">{t("Show {n}", { n: num(total) })}</button>
      </footer>
    </div>
  );
}
