import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, MotionConfig, motion } from "motion/react";
import * as api from "./lib/api";
import type { Arena, Gem, Project } from "./lib/types";
import { coverage, loadHidden, useNarratives } from "./lib/store";
import { Dock, LABEL, type View } from "./components/Dock";
import { Top3 } from "./components/Top3";
import { Sheet } from "./components/Sheet";
import { TokenRow, gemId } from "./components/TokenRow";
import { Arenas } from "./views/Arenas";
import { Database } from "./views/Database";
import { GemList } from "./views/GemList";
import { TokenPage, type Opened } from "./views/TokenPage";

const POLL_MS = 30_000;
const PEARL_MIN = 70;          // a "70" on screen is always a pearl
const PEARL_MAX_AGE_DAYS = 30;
const ALL: View[] = ["gems", "pearl", "top", "rank", "quality", "agent", "profile"];

// Read before the view's own hash replaces it.
const LINK = location.hash.match(/&token=([^:&]+):([^&]+)/);

type Data = { entries: Gem[]; early: Gem[]; arenas: Arena[] };

function boot(): { initial: string } {
  try {
    const b = JSON.parse(document.getElementById("onchain-boot")?.textContent ?? "{}");
    const u = b.user ?? {};
    return { initial: String(u.display_name || u.username || u.email || "?").charAt(0).toUpperCase() };
  } catch { return { initial: "?" }; }
}

export function App() {
  const [view, setView] = useState<View>(() => { const h = location.hash.slice(1).split("&")[0] as View; return ALL.includes(h) ? h : "gems"; });
  const [sub, setSub] = useState<"arenas" | "database">("arenas");
  const [data, setData] = useState<Data | null>(null);
  const [err, setErr] = useState("");
  const [open, setOpenRaw] = useState<Opened | null>(null);
  const [search, setSearch] = useState(false);
  const closePage = useCallback(() => setOpenRaw(null), []);
  const [quality, setQuality] = useState(false);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const narr = useNarratives();
  const [{ initial }] = useState(boot);

  const load = useCallback(async () => {
    try {
      const top = await api.getTop(50, narr);
      // A page served before the arenas: one arena holding the whole list.
      const arenas = top.arenas ?? [{ key: "all", label: "All projects", heat: 0, size: top.entries.length, median: 0,
        entries: top.entries.map((e, i) => ({ ...e, arena_rank: i + 1, in: true })) }];
      setData({ entries: top.entries ?? [], early: top.early ?? [], arenas });
      setErr("");
    } catch (e) { setErr((e as Error).message); }
  }, [narr]);

  useEffect(() => { load(); const t = setInterval(() => document.visibilityState === "visible" && load(), POLL_MS); return () => clearInterval(t); }, [load]);
  useEffect(() => { loadHidden(); coverage().then((l) => setLabels(Object.fromEntries(l.map((n) => [n.key, n.label ?? n.key])))); }, []);
  // Quality is one account's (quality.js): its button shows only when the list answers.
  useEffect(() => { fetch("/api/onchain/quality").then((r) => setQuality(r.ok)).catch(() => {}); }, []);
  useEffect(() => { history.replaceState(null, "", `${location.pathname}${location.search}#${view}`); scrollTo(0, 0); }, [view]);

  const views = ALL.filter((v) => v !== "quality" || quality);
  const podium = data ? [...data.entries].sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).slice(0, 3) : [];
  const born = Date.now() / 1000 - PEARL_MAX_AGE_DAYS * 86400;
  const sc = (e: { score?: number }) => Math.round(e.score ?? 0);
  // Each list says where the token was seen, on the page's context line (top.js, projects.js register()).
  const openWith = (context: (e: Gem) => string) => (e: Gem) => setOpen({ e, context: context(e) });
  const setOpen = (o: Opened | null) => setOpenRaw(o);
  const byScore = data ? [...data.entries].sort((a, b) => (b.score ?? 0) - (a.score ?? 0)) : [];
  const openArena = openWith((e) => {
    const a = data?.arenas.find((x) => x.entries.some((y) => gemId(y) === gemId(e)));
    return a ? `${a.label} · #${e.arena_rank} of ${a.size} · score ${sc(e)}` : `score ${sc(e)}`;
  });
  const openRanked = openWith((e) => `Top 25 · #${byScore.findIndex((x) => gemId(x) === gemId(e)) + 1} · score ${sc(e)}`);
  const openProject = (p: Project) => setOpen({
    e: { chain: p.chain, token_address: p.token, symbol: p.symbol ?? "?", name: p.name, image: p.image, score: p.score, market_cap: p.mcap, liquidity_usd: p.liq },
    context: `Database · score ${p.score == null ? "—" : Math.round(p.score)} · ${p.status}${p.why ? ` · ${p.why}` : ""}` });

  // A shared link or an alert: #<view>&token=<chain>:<address>[&tab=why] opens that token.
  useEffect(() => {
    const m = LINK;
    if (!m) return;
    const chain = decodeURIComponent(m[1]), token = decodeURIComponent(m[2]);
    api.getToken(chain, token).then((r) => {
      const p = r.entry;
      setOpen({ e: { chain, token_address: token, symbol: p?.symbol ?? token.slice(0, 6), name: p?.name, image: p?.image, pair_address: p?.pair_address,
        pair_url: p?.pair_url, market_cap: p?.market_cap, change_24h: p?.change_24h, launched_at: p?.launched_at } });
    }).catch(() => {});
  }, []);

  return (
    <MotionConfig reducedMotion="user">
      <main className="mx-auto max-w-xl px-4 pb-[calc(104px+env(safe-area-inset-bottom))] pt-[calc(env(safe-area-inset-top)+18px)]">
        <h1 className="mb-3 text-[40px] font-bold leading-none tracking-tight">{LABEL[view]}</h1>
        <Top3 list={podium} onOpen={openWith((e) => `Top 25 · score ${sc(e)}`)} />
        {err && !data && <p className="rounded-2xl bg-card p-4 text-[14px] text-down">Could not load the gems: {err}</p>}
        <AnimatePresence mode="wait">
          <motion.div key={view} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.16 }}>
            {view === "gems" && (
              <>
                <div className="flex gap-2">
                  {([["arenas", "Arenas"], ["database", "Database"]] as const).map(([s, label]) => (
                    <button key={s} type="button" onClick={() => setSub(s)} aria-pressed={sub === s}
                      className={`relative h-10 rounded-full px-[18px] text-[15px] font-medium transition-colors duration-200 ${sub === s ? "text-on-ink" : "bg-pill text-text-2"}`}>
                      {sub === s && <motion.span layoutId="gems-sub" className="absolute inset-0 rounded-full bg-ink" transition={{ type: "spring", stiffness: 520, damping: 42 }} />}
                      <span className="relative">{label}</span>
                    </button>
                  ))}
                </div>
                {sub === "arenas" ? (
                  <>
                    <ScanButton onClick={() => setSearch(true)} />
                    {data ? <Arenas arenas={data.arenas} filtered={narr.length > 0} labels={labels} onOpen={openArena} /> : <Skeleton />}
                  </>
                ) : <Database onOpen={openProject} scan={<ScanButton onClick={() => setSearch(true)} />} />}
              </>
            )}
            {view === "pearl" && data && (
              <GemList title="Pearl" rule="Early gems scoring 70 or more, at most 30 days old" badge="early" onOpen={openWith((e) => `Pearl · score ${sc(e)}`)}
                lead="The best of Early: under $300k cap, every bar of the Top passed, and a score of at least 70. Small and risky. Research, not advice."
                empty="No Early gem of the last 30 days scores 70 or more right now. The list is refreshed by the nightly scan."
                rows={data.early.filter((e) => Math.round(e.score ?? 0) >= PEARL_MIN && (e.launched_at ?? 0) >= born)} />
            )}
            {view === "top" && data && (
              <GemList title="Early" rule="under $300k cap" badge="early" onOpen={openWith((e) => `Early · score ${sc(e)}`)} rows={data.early}
                lead="Small projects that pass every other bar of the Top: real usage, holders, code and research. Smaller and riskier. Research, not advice."
                empty="No project under $300k passes the bars right now. The list is refreshed by the nightly scan." />
            )}
            {view === "rank" && data && (
              <GemList title={narr.length ? `Top 25 · ${narr.map((k) => labels[k] ?? k).join(", ")}` : "Top 25"} rule="the best gems by score" ranked onOpen={openRanked} rows={data.entries}
                lead="The 25 highest scores among the gems that passed the checks: usage, holders, code, research and tokenomics. Market cap and 24h change live from DexScreener. Research, not advice."
                empty="The ranking is filling up: gems appear as they pass the checks." />
            )}
            {(view === "quality" || view === "agent" || view === "profile") && (
              <p className="py-8 text-center text-[14px] text-text-2">
                {LABEL[view]} moves here in a next step. Until then it is in the <a className="underline" href={`/onchain-app.html#${view}`}>current app</a>.
              </p>
            )}
          </motion.div>
        </AnimatePresence>
      </main>
      <Dock view={view} views={views} onView={setView} onSearch={() => setSearch(true)} initial={initial} />
      <SearchSheet open={search} data={data} onClose={() => setSearch(false)} onOpen={(e) => { setSearch(false); setOpen({ e }); }} />
      <AnimatePresence>{open && <TokenPage key={gemId(open.e)} open={open} onClose={closePage} />}</AnimatePresence>
    </MotionConfig>
  );
}

function ScanButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="relative mt-3 flex h-12 w-full items-center rounded-full border border-line pl-5 text-left text-[16px] text-text-3">
      Scan a token: ticker or address
      <span className="absolute right-1 top-1 grid h-10 w-10 place-items-center rounded-full bg-ink text-on-ink">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden="true"><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4 4" /></svg>
      </span>
    </button>
  );
}

// Until the scanner moves here (step 5): a search among the gems already loaded.
function SearchSheet({ open, data, onClose, onOpen }: { open: boolean; data: Data | null; onClose: () => void; onOpen: (e: Gem) => void }) {
  const [q, setQ] = useState("");
  const s = q.trim().toLowerCase();
  const seen = new Set<string>();
  const hits = !s || !data ? [] : [...data.entries, ...data.early, ...data.arenas.flatMap((a) => a.entries)].filter((e) => {
    const id = gemId(e);
    if (seen.has(id)) return false;
    seen.add(id);
    return e.symbol.toLowerCase().includes(s) || (e.name ?? "").toLowerCase().includes(s) || e.token_address.toLowerCase() === s;
  });
  return (
    <Sheet open={open} title="Search" sub="Ticker, name or address among the gems." onClose={onClose}>
      <input autoFocus value={q} onChange={(ev) => setQ(ev.target.value)} placeholder="Ticker or address" autoComplete="off" spellCheck={false}
        className="h-12 w-full rounded-full border border-line bg-transparent px-5 text-[16px] outline-none placeholder:text-text-3 focus:border-text-3" />
      <ol className="mt-3">{hits.map((e, i) => <TokenRow key={gemId(e)} e={e} i={i} onOpen={onOpen} />)}</ol>
      {s && !hits.length && <p className="py-3 text-[14px] text-text-2">Nothing called "{q}" among the gems.</p>}
    </Sheet>
  );
}

function Skeleton() {
  return <div className="mt-4 space-y-2">{Array.from({ length: 6 }, (_, i) => <div key={i} className="h-[72px] animate-pulse rounded-[20px] bg-card" />)}</div>;
}
