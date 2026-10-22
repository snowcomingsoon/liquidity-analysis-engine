import type { ReactNode } from "react";
import type { Deep, Entry, Judge, Pillar, Point } from "../lib/types";
import { t as tr } from "../lib/i18n";

// The Why and Info tabs of the token page, as leaderboard.js gemWhy() and
// details() write them, with the deep re-check of detail.js deepBlock().

const PILLARS = [["github", "GitHub"], ["site", "Research"], ["tokenomics", "Tokenomics"]] as const;
const CHAINS: Record<string, string> = { solana: "Solana", robinhood: "Robinhood", base: "Base", bsc: "BSC", ethereum: "Ethereum", arc: "Arc" };

const usd = (v?: number | null) => (v == null ? "—" : v >= 1e6 ? `$${(v / 1e6).toFixed(v >= 1e7 ? 0 : 1)}M` : v >= 1e3 ? `$${Math.round(v / 1e3)}k` : `$${Math.round(v)}`);
const compactNum = (v: unknown) => { const n = Number(v) || 0; return n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}k` : `${n}`; };
const score = (v?: number | null) => (v == null ? "—" : Math.round(v));
const yes = (v: unknown) => (v ? tr("yes") : tr("no"));
export function ago(at?: number) {
  if (!at) return "";
  const s = Math.max(0, Math.floor(Date.now() / 1000 - at));
  return s < 60 ? tr("just now") : s < 3600 ? tr("{n}m ago", { n: Math.floor(s / 60) }) : s < 86400 ? tr("{n}h ago", { n: Math.floor(s / 3600) }) : tr("{n}d ago", { n: Math.floor(s / 86400) });
}

type Tone = "good" | "bad" | "warn" | "";
const MARK: Record<Tone, ReactNode> = {
  good: <svg viewBox="0 0 16 16" className="absolute left-0.5 top-[6px] h-4 w-4 text-up" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m3.5 8.5 3 3 6-7" /></svg>,
  bad: <i className="absolute left-1.5 top-[11px] h-[6px] w-[6px] rounded-full bg-down" aria-hidden="true" />,
  warn: <i className="absolute left-1.5 top-[11px] h-[6px] w-[6px] rounded-full bg-amber" aria-hidden="true" />,
  "": null,
};
function Li({ tone = "", children }: { tone?: Tone; children: ReactNode }) {
  return <li className="relative py-1 pl-6 text-[14px] leading-[1.35]">{MARK[tone]}{children}</li>;
}
function Head({ title, right }: { title: string; right?: ReactNode }) {
  return <h5 className="mb-0.5 mt-3.5 flex items-baseline justify-between text-[13px] font-semibold text-text-2">{tr(title)}{right && <b className="num font-bold text-text">{right}</b>}</h5>;
}

function socialLines(j?: Judge | null): ReactNode[] {
  const out: ReactNode[] = [];
  const x = j?.x;
  if (x) out.push(<Li key="x">X: {tr("{p} posts/7d · {a} authors · median {f} followers", { p: Number(x.posts_7d) || 0, a: Number(x.authors) || 0, f: compactNum(x.median_followers ?? 0) })}</Li>);
  const tg = j?.tg;
  if (tg) {
    const at = `@${tg.handle ?? ""}`;
    let body: string;
    let tone: Tone = "";
    if (tg.kind === "missing") body = `${at} ${tr("not found")}`;
    else if (tg.kind === "group") body = `${at} · ${tr("group")} · ${tr("{n} members", { n: compactNum(tg.subs ?? 0) })}${tg.online != null ? ` · ${tr("{n} online", { n: compactNum(tg.online) })}` : ""}`;
    else if (tg.kind === "no_preview") body = `${at} · ${tr("{n} subscribers · posts not public", { n: compactNum(tg.subs ?? 0) })}`;
    else {
      const parts = [tr("{n} members", { n: compactNum(tg.subs ?? 0) }), tr("{n} posts/7d", { n: Number(tg.posts_7d) || 0 })];
      if (tg.last_post_days != null) parts.push(tr("last {n}d ago", { n: Math.round(Number(tg.last_post_days)) }));
      if (tg.median_views != null) parts.push(tr("{n} views", { n: compactNum(tg.median_views) }));
      body = `${at} · ${parts.join(" · ")}`;
      if (tg.last_post_days != null && Number(tg.last_post_days) > 180) { tone = "bad"; body += ` · ${tr("silent {n} months", { n: Math.floor(Number(tg.last_post_days) / 30) })}`; }
    }
    out.push(<Li key="tg" tone={tone}>Telegram: {body}</Li>);
    (Array.isArray(j?.tg_events) ? j!.tg_events! : []).forEach((ev, i) => out.push(<Li key={`ev${i}`}>{ev?.date ?? ""} · {ev?.type ?? ""} · {ev?.text ?? ""}</Li>));
  }
  const dc = j?.dc;
  if (dc) {
    const name = dc.name ?? dc.code ?? "";
    if (dc.kind === "missing") out.push(<Li key="dc">Discord: {name} {tr("invite expired")}</Li>);
    else {
      const members = Number(dc.members) || 0;
      out.push(<Li key="dc">Discord: {name} · {tr("{n} members", { n: compactNum(members) })} · {tr("{n} online", { n: compactNum(dc.online ?? 0) })}{members > 0 ? ` · ${tr("{n} online", { n: `${((Number(dc.online) || 0) / members * 100).toFixed(1)}%` })}` : ""}</Li>);
    }
  }
  return out;
}

/** The Scout's report: its verdict, the editor's call, the code reading, the socials. */
function Report({ e }: { e: Entry }) {
  const j = e.judge, r = e.review, c = e.code;
  if (!j && !r && !c) return null;
  return (
    <div>
      <Head title="Scout" right={j ? `${j.verdict ?? ""} · ${j.score ?? "—"}/100` : undefined} />
      <ul className="rounded-[20px] bg-card px-3 py-1">
        {r && <Li tone={r.keep ? "good" : "bad"}>{r.keep ? tr("Kept on review:") : tr("Dropped on review:")} {r.reason ?? ""}</Li>}
        {j?.admit_reason && <Li tone="good">{j.admit_reason}</Li>}
        {c && <Li>{tr("Code: complexity {c} · innovation {i}", { c: c.complexity ?? "—", i: c.innovation ?? "—" })}{c.fork_of ? ` · ${tr("fork of {f}", { f: c.fork_of })}` : ""}</Li>}
        {c?.summary && <Li>{c.summary}</Li>}
        {(c?.strengths ?? []).map((x, i) => <Li key={`cs${i}`} tone="good">{x}</Li>)}
        {(c?.concerns ?? []).map((x, i) => <Li key={`cc${i}`} tone="bad">{x}</Li>)}
        {(j?.strengths ?? []).map((x, i) => <Li key={`js${i}`} tone="good">{x}</Li>)}
        {(j?.problems ?? []).map((x, i) => <Li key={`jp${i}`} tone="bad">{x}</Li>)}
        {socialLines(j)}
      </ul>
    </div>
  );
}

const fill = (v: number) => ({ background: `linear-gradient(90deg, var(--c-text) ${v}%, var(--c-press) 0)` });

export function GemWhy({ e }: { e: Entry }) {
  const s = Math.round(e.score ?? 0);
  const flags = Object.values(e.pillars ?? {}).flatMap((p) => p?.flags ?? []);
  const title = e.top_rank ? `Top #${e.top_rank}` : e.early ? tr("Early gem") : e.top_rank === null ? tr("Not in the Top right now") : tr("Rank #{n}", { n: e.rank ?? "—" });
  return (
    <>
      <div className="flex items-center gap-3.5 rounded-[24px] bg-card p-3.5">
        <span className="relative grid h-16 w-16 flex-none place-items-center rounded-full" style={{ background: `conic-gradient(var(--c-text) ${s}%, var(--c-press) 0)` }}>
          <i className="absolute inset-[4px] rounded-full bg-card" />
          <b className="num relative text-[22px] font-semibold">{s}</b>
        </span>
        <p className="min-w-0">
          <b className="block text-[16px] font-semibold">{title}</b>
          <small className="mt-0.5 block text-[14px] leading-snug text-text-2">{e.early ? tr("Under $300k and past every other bar of the Top: smaller and riskier.") : tr("Usage, holders, code, research and tokenomics, scored every day.")}</small>
        </p>
      </div>
      {e.summary && <p className="mt-3 text-[14px] leading-[1.45]">{e.summary}</p>}
      <Report e={e} />
      {(e.traction?.reasons ?? []).length > 0 && <ul className="mt-2">{e.traction!.reasons!.map((r, i) => <Li key={i} tone="good">{r}</Li>)}</ul>}
      {flags.length > 0 && <ul>{flags.map((f, i) => <Li key={i} tone="bad">{f}</Li>)}</ul>}
      <p className="mt-3 text-[14px] text-text-2">{tr("Research, not advice.")}</p>
    </>
  );
}

/** detail.js whyOf(): a newer deep re-check replaces the board review's lines. */
export function WhyOf({ e, deep }: { e: Entry; deep?: Deep | null }) {
  if (deep) return <GemWhy e={{ ...e, review: null, judge: e.judge ? { ...e.judge, strengths: [], problems: [], admit_reason: null } : e.judge }} />;
  return (
    <>
      <GemWhy e={e} />
      {!e.on_board && <p className="mt-2 text-[14px] text-text-2">{tr("Not on the board")}{e.why ? `: ${e.why}` : ""}.</p>}
    </>
  );
}

function Fact({ label, value }: { label: string; value: ReactNode }) {
  if (value == null || value === "") return null;
  return <div className="flex justify-between gap-4 py-px text-[13px] leading-[1.45]"><dt className="text-text-2">{tr(label)}</dt><dd className="num text-right">{value}</dd></div>;
}
const Link = ({ href, children }: { href: string; children: ReactNode }) =>
  <a href={href} target="_blank" rel="noopener" className="underline decoration-text-3 underline-offset-[3px]">{children}</a>;
const host = (u: string) => { try { return new URL(u).hostname; } catch { return u; } };

function PillarBlock({ p = {}, k, label }: { p?: Pillar; k: string; label: string }) {
  const f = p.facts ?? {};
  let rows: ReactNode;
  if (k === "github") rows = <>
    <Fact label="Repository" value={f.url ? <Link href={f.url}>{f.repo}</Link> : null} />
    <Fact label="Commits, 90 days" value={f.commits_90d} /><Fact label="Active weeks (of 12)" value={f.active_weeks_12} />
    <Fact label="Authors" value={Math.max(f.authors ?? 0, f.contributors ?? 0)} />
    <Fact label="Last commit" value={f.last_commit_days == null ? null : tr("{n} d ago", { n: f.last_commit_days })} />
    <Fact label="Code" value={f.code_kb == null ? null : `${f.code_kb} KB · ${(f.languages ?? []).join(", ")}`} />
    <Fact label="Test · CI" value={`${yes(f.tests)} · ${yes(f.ci)}`} /><Fact label="Trivial commits" value={f.trivial_pct == null ? null : `${f.trivial_pct}%`} />
    <Fact label="Stars" value={f.stars} />
  </>;
  else if (k === "site") rows = <>
    <Fact label={f.reader ? "Reading" : "Claude's read"} value={f.ai_substance == null ? null : `${f.ai_substance}/10 · ${f.verdict ?? ""}`} />
    <Fact label="Description" value={f.description_score == null ? null : `${f.description_score}/100 · ${tr("{n} words", { n: f.description?.words ?? 0 })}`} />
    <Fact label="Sites read" value={f.sites_read} /><Fact label="Holders" value={f.holders} />
    <Fact label="Website" value={f.url ? <Link href={f.url}>{host(f.url)}</Link> : null} />
    <Fact label="Words" value={f.words} /><Fact label="Internal pages" value={f.internal_pages == null ? null : `${f.internal_pages} · ${tr("{n} load with content", { n: f.pages_ok ?? 0 })}`} />
    <Fact label="Docs" value={f.docs == null ? null : f.docs_ok ? tr("yes, reachable") : f.docs ? tr("linked, empty") : tr("no")} />
    <Fact label="App" value={f.app == null ? null : f.app_ok ? tr("yes, responds") : f.app ? tr("linked, not responding") : tr("no")} />
    <Fact label="Sections" value={(f.sections ?? []).join(", ") || null} />
    <Fact label="Domain" value={f.domain_days == null ? null : tr("registered {n} d ago", { n: f.domain_days })} />
  </>;
  // The split behind the 40% limit (19/10): every holder's top 10, what sits in contracts, the wallets the limit counts.
  else rows = <>
    <Fact label="Top wallet" value={f.top1_pct == null ? null : `${f.top1_pct}%`} />
    <Fact label="Top 10, all holders" value={f.top10_all_pct == null ? null : `${f.top10_all_pct}%`} />
    <Fact label="In contracts / programs" value={f.contracts_pct == null ? null : `${f.contracts_pct}%`} />
    <Fact label={f.top10_all_pct == null ? "Top 10" : "Top 10 wallets"} value={f.top10_pct == null ? null : `${f.top10_pct}%`} />
    <Fact label="Creator" value={f.creator_pct == null ? null : `${f.creator_pct}%`} /><Fact label="Holder" value={f.holders} />
    <Fact label="Locked liquidity" value={f.lp_locked_pct == null ? null : `${f.lp_locked_pct}%`} />
    <Fact label="Mint · freeze" value={f.mint == null ? null : `${f.mint ? tr("active") : f.mint_by ? tr("by {who}", { who: f.mint_by }) : tr("revoked")} · ${f.freeze ? tr("active") : tr("revoked")}`} />
    <Fact label="Tax" value={f.tax_pct == null ? null : `${f.tax_pct}%`} />
  </>;
  const flags = [...(p.flags ?? []), ...(f.red_flags ?? [])];
  return (
    <Section label={label} v={p.score}>
      <dl>{rows}</dl>
      {k === "site" && f.why?.length > 0 && <p className="mt-1 text-[13px] text-text-2">{f.why.join(" · ")}</p>}
      {flags.length > 0 && <ul className="mt-1">{flags.map((x: string, i: number) => <li key={i} className="text-[13px] text-amber"><b>! </b>{x}</li>)}</ul>}
    </Section>
  );
}

function Section({ label, v, children }: { label: string; v?: number | null; children: ReactNode }) {
  return (
    <section className="mt-4">
      <h5 className="flex justify-between text-[13px] font-medium">{tr(label)}<b className="num font-medium">{score(v)}</b></h5>
      <i className="mb-2 mt-1.5 block h-0.5" style={fill(v ?? 0)} />
      {children}
    </section>
  );
}

function Traction({ e }: { e: Entry }) {
  const t = e.traction;
  if (!t) return null;
  const f = t.facts ?? {};
  return (
    <Section label="Traction" v={t.traction}>
      <dl>
        <Fact label="TVL" value={f.tvl == null ? null : usd(f.tvl)} /><Fact label="Fees, 30 days" value={f.fees_30d == null ? null : usd(f.fees_30d)} />
        <Fact label="TVL, 7 days" value={f.tvl_change_7d == null ? null : `${f.tvl_change_7d > 0 ? "+" : ""}${Math.round(f.tvl_change_7d)}%`} />
        <Fact label="Cap ÷ yearly fees" value={f.mcap_to_fees == null ? null : `${f.mcap_to_fees}×`} />
        <Fact label="Cap ÷ TVL" value={f.mcap_to_tvl == null ? null : `${f.mcap_to_tvl}×`} />
        <Fact label="Value" value={t.value == null ? null : `${Math.round(t.value)}/100`} />
      </dl>
      {t.reasons?.length ? <p className="mt-1 text-[13px] text-text-2">{t.reasons.join(" · ")}</p> : null}
    </Section>
  );
}

function Traits({ e }: { e: Entry }) {
  const t = e.similarity?.traits ?? [];
  if (!t.length) return null;
  return (
    <>
      <p className="mb-1.5 mt-4 text-[13px] font-semibold text-amber">{e.benchmark ? tr("The benchmark") : `${tr("Technical similarity to DREGG")} · ${e.similarity?.score}%`}</p>
      <ul className="flex flex-wrap gap-1.5">{t.map((x, i) => (
        <li key={i} className={`rounded-full px-2.5 py-0.5 text-[12px] ${x.got >= 1 ? "bg-sage text-on-sage" : x.got > 0 ? "bg-pill text-text" : "bg-pill text-text-3 line-through"}`}>{x.label}</li>
      ))}</ul>
    </>
  );
}

/** The Info tab (details() + descriptionBlock()). Its header line is hidden on the phone, as in the original. */
export function Details({ e }: { e: Entry }) {
  const links = [[tr("Website"), e.website], ["GitHub", e.github], ...(e.socials ?? []).map((s) => [s.type, s.url])].filter(([, u]) => u) as [string, string][];
  return (
    <>
      {e.honor && <p className="mb-3 text-[13px] font-semibold text-amber">{e.honor}</p>}
      {e.summary && <p className="text-[14px] leading-[1.45]">{e.summary}{e.stage && e.stage !== "unclear" && <em> {e.stage}</em>}</p>}
      <Report e={e} />
      <Traits e={e} />
      <div className="mt-2">{PILLARS.map(([k, label]) => <PillarBlock key={k} p={e.pillars?.[k]} k={k} label={label} />)}<Traction e={e} /></div>
      {e.description && <p className="mt-5 text-[14px] leading-[1.45]">{e.description}</p>}
      {links.length > 0 && <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[15px]">{links.map(([l, u]) => <Link key={u} href={u}>{l}</Link>)}</p>}
    </>
  );
}

export function InfoFallback({ chain, token, pairUrl }: { chain: string; token: string; pairUrl?: string }) {
  return (
    <dl>
      <Fact label="Chain" value={CHAINS[chain] ?? chain} />
      <Fact label="Contract" value={<span className="break-all font-mono text-[12px]">{token || "—"}</span>} />
      {pairUrl && <Fact label="Chart" value={<Link href={pairUrl}>DexScreener</Link>} />}
    </dl>
  );
}

/** The deep re-check's verdict, every point with the quote that backs it (#464). */
export function DeepResult({ d }: { d: Deep }) {
  const why = (x: Point) => (typeof x === "string" ? { text: x } : x ?? {});
  const row = (key: string, tone: Tone, label: string, x: Point) => {
    const w = why(x);
    const q = w.evidence || w.note;
    return <Li key={key} tone={tone}>{label}{w.text ?? ""}{q && <small className="mt-1 block text-[13px] text-text-2">“{q}”</small>}</Li>;
  };
  const claims = d.claims ?? [];
  const TONE: Record<string, [Tone, string]> = { refuted: ["good", tr("Cleared: ")], confirmed: ["bad", ""], unverified: ["warn", tr("Unverified: ")] };
  const count = (k: "refuted" | "unverified" | "confirmed") => (claims.length ? claims.filter((c) => c.status === k).length : d[k === "refuted" ? "cleared" : k] ?? 0);
  return (
    <>
      <ul>
        {d.unsupported ? row("h", "warn", tr("Unverified: "), { text: d.reason }) : row("h", d.keep ? "good" : "bad", d.keep ? tr("Kept: ") : tr("Dropped: "), { text: d.reason })}
        {(d.strengths ?? []).map((x, i) => row(`s${i}`, "good", "", x))}
        {(d.problems ?? []).map((x, i) => row(`p${i}`, "bad", "", x))}
        {claims.map((c, i) => row(`c${i}`, TONE[c.status]?.[0] ?? "warn", TONE[c.status]?.[1] ?? "", { text: c.text, evidence: c.evidence || c.note }))}
      </ul>
      <p className="mt-2 text-[14px] text-text-2">{tr("{a} cleared · {b} unverified · {c} confirmed", { a: count("refuted"), b: count("unverified"), c: count("confirmed") })} · {d.auto ? `${tr("weekly re-check")} ` : ""}{ago(d.at)}</p>
    </>
  );
}

export { Head as DossierHead };
