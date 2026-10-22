import { useState } from "react";
import * as api from "../lib/api";
import { askPush } from "../lib/push";
import type { Entry, Gem } from "../lib/types";
import { Logo } from "./Logo";
import { changeText, usdShort, age } from "../lib/format";
import { GemWhy } from "../views/Dossier";

// The scanner (sheets.js openScan), inside Search: the checks live, then the verdict.
const LABEL: Record<string, string> = {
  pool: "Finding the pool on DexScreener", name: "Reading the name", security: "Security scan", contract: "Contract permissions",
  socials: "Social accounts", site: "Reading the project website", github: "Checking GitHub", ai: "AI reads the listing",
  holders: "Counting holders", memory: "Comparing with past rugs", risk: "AI rates the rug risk", gem: "Looking up the Gem Finder",
  pillars: "Scoring research, GitHub and tokenomics", report: "Scout writes the report", code: "AI reads the code", recheck: "Final review of the red flags",
};
type Step = { k: string; state: string; detail?: string };
/* eslint-disable @typescript-eslint/no-explicit-any */
type Result = any;

function gemStatus(g: any): [string, string] {
  if (g.added) return ["up", `Gem Finder: added · score ${g.score} · the board studies it now`];
  if (g.status === "ranked") return ["up", `Gem Finder: ranked #${g.rank} · score ${g.score}`];
  if (g.status === "unknown") return g.score == null ? ["amber", "Gem Finder: not studied yet"]
    : g.why ? ["amber", `Scout: would not rank yet · ${g.why}`] : ["up", `Scout: would qualify · score ${g.score}`];
  if (g.status === "new" || g.status === "analyzing") return ["amber", "Gem Finder: queued for a full study"];
  if (g.status === "rejected") return ["down", `Gem Finder: rejected · ${g.why || "rules"}`];
  return g.why ? ["amber", `Gem Finder: studied, not ranked · ${g.why}`] : ["up", `Gem Finder: qualifies · score ${g.score}`];
}

export function Scan({ query, onOpen }: { query: string; onOpen: (e: Gem) => void }) {
  const [steps, setSteps] = useState<Step[]>([]);
  const [run, setRun] = useState<"idle" | "busy" | "done">("idle");
  const [err, setErr] = useState("");
  const [d, setD] = useState<Result>(null);
  const [added, setAdded] = useState("");

  async function go() {
    askPush();
    setRun("busy"); setErr(""); setD(null); setSteps([]); setAdded("");
    try {
      const r = await api.streamScan(query, (ev) => {
        if (ev.reconnecting) setSteps((s) => [...s, { k: "_re", state: "wait", detail: "Connection dropped. Scout is still working, collecting the result…" }]);
        else if (ev.plan) setSteps(ev.plan.map((k) => ({ k, state: "wait" })));
        else if (ev.step) setSteps((s) => s.map((x) => (x.k === ev.step ? { ...x, state: ev.state ?? x.state, detail: ev.detail ?? x.detail } : x)));
      });
      if ((r as Result).error) setErr(String((r as Result).error)); else setD(r);
    } catch (e) { setErr((e as Error).message); }
    setRun("done");
  }

  if (run === "idle") return (
    <button type="button" onClick={go} className="flex w-full items-center gap-3 rounded-[16px] bg-card px-4 py-3 text-left active:bg-pill">
      <span className="flex-1 text-[14px]">Scan “{query}” as a ticker or address</span>
      <span className="rounded-full bg-ink px-3 py-1 text-[13px] font-semibold text-on-ink">Scan</span>
    </button>
  );

  const t = d?.token, g = d?.gem, ab = d?.about ?? {};
  const [chg, sign] = changeText(t?.change_24h);
  const status: [string, string] | null = !d ? null : g ? gemStatus(added === "yes" ? { ...g, status: "new" } : g)
    : ({ ok: ["up", "Would pass the listing filter"], fail: ["down", `Would be rejected: ${d.pipeline?.reason}`], wait: ["amber", `Waiting: ${d.pipeline?.reason}`] } as Record<string, [string, string]>)[d.pipeline?.status] ?? ["amber", d.pipeline?.reason ?? ""];
  const tone = (s: string) => (s === "up" ? "text-up" : s === "down" ? "text-down" : "text-amber");
  return (
    <div className="rounded-[16px] bg-card p-3">
      {!d && (
        <ol className="grid gap-1.5 text-[13.5px]">
          {run === "busy" && !steps.length && <li className="text-text-2">Scout is examining {query}…</li>}
          {steps.map((s) => (
            <li key={s.k} className="flex items-start gap-2">
              <i className={`mt-1.5 h-2 w-2 flex-none rounded-full ${s.state === "ok" || s.state === "done" ? "bg-up" : s.state === "fail" ? "bg-down" : s.state === "run" ? "animate-pulse bg-amber" : s.state === "skip" ? "bg-text-4" : "bg-line"}`} />
              <span className="min-w-0 flex-1">{LABEL[s.k] ?? s.detail ?? s.k}{s.detail && LABEL[s.k] && <small className="block text-[12px] text-text-3">{s.detail}</small>}</span>
            </li>
          ))}
        </ol>
      )}
      {err && <p className="mt-2 text-[14px] text-down">{err} <button type="button" onClick={go} className="underline">Try again</button></p>}
      {d && t && (
        <>
          <div className="flex items-center gap-3">
            <Logo size={42} symbol={t.symbol} image={t.image} chain={t.chain} token={t.token_address} />
            <span className="min-w-0 flex-1">
              <b className="block truncate text-[16px] font-semibold">{t.name || t.symbol}</b>
              <small className="line-clamp-2 block text-[12.5px] text-text-3">{ab.summary || `${t.symbol} · ${t.chain}`}</small>
            </span>
          </div>
          <dl className="mt-3 grid grid-cols-3 gap-1.5">
            {([["Cap", usdShort(t.market_cap)], ["Liquidity", usdShort(t.liquidity_usd)], ["Volume 24h", usdShort(t.volume_24h)], ["24h", chg],
              ["Age", t.created_at ? age(t.created_at)[0] : "—"], ["Holders", ab.holders != null ? Number(ab.holders).toLocaleString("en-US") : "—"]] as [string, string][]).map(([l, v]) => (
              <div key={l} className="rounded-[12px] bg-bg px-2.5 py-1.5">
                <dt className="text-[10.5px] font-medium uppercase tracking-[0.07em] text-text-3">{l}</dt>
                <dd className={`num text-[14px] font-semibold ${l === "24h" ? (sign === "up" ? "text-up" : sign === "down" ? "text-down" : "") : ""}`}>{v}</dd>
              </div>
            ))}
          </dl>
          {status && <p className={`mt-3 text-[14px] font-medium ${tone(status[0])}`}>{status[1]}</p>}
          {d.ai ? (
            <p className="mt-2 flex items-center gap-2 text-[13px]">
              <b className={`num rounded-md px-1.5 font-mono ${d.ai.risk >= 60 ? "bg-down text-on-ink" : d.ai.risk >= 30 ? "bg-amber text-on-ink" : "bg-sage text-on-sage"}`}>{d.ai.risk}</b>
              <span>Scout rug risk · {[d.ai.theme, ...(d.ai.flags ?? [])].filter(Boolean).join(" · ") || "no red flags"}</span>
            </p>
          ) : <p className="mt-2 text-[13px] text-text-3">Scout's AI assessment is unavailable right now.</p>}
          {d.scout && <div className="mt-3"><GemWhy e={d.scout as Entry} /></div>}
          {d.memory?.summary && <p className="mt-2 text-[13px] text-text-2"><b>Memory:</b> {d.memory.summary}</p>}
          {(d.checks ?? []).length > 0 && (
            <ul className="mt-2 grid gap-1 text-[13px]">
              {d.checks.map((c: any, i: number) => (
                <li key={i} className="flex gap-2"><span className={c.ok === true ? "text-up" : c.ok === false ? "text-down" : "text-text-3"}>{c.ok === true ? "✓" : c.ok === false ? "✕" : "?"}</span>
                  <span>{c.label}{c.detail && <small className="block text-text-3">{c.detail}</small>}</span></li>
              ))}
            </ul>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            {g && !g.added && ["unknown", "rejected", "studied"].includes(g.status) && (
              <button type="button" disabled={!!added} onClick={async () => { setAdded("…"); try { const r = await api.addScanned(t.chain, t.token_address); setAdded(r.error ? r.error : "yes"); } catch (e) { setAdded((e as Error).message); } }}
                className="h-10 rounded-full bg-pill px-4 text-[14px] font-semibold disabled:opacity-70">
                {added === "yes" ? "Registered" : added || (g.status === "unknown" ? "Add to database" : "Study again")}
              </button>
            )}
            <button type="button" onClick={() => onOpen({ chain: t.chain, token_address: t.token_address, symbol: t.symbol, name: t.name, image: t.image, pair_address: t.pair_address,
              pair_url: t.pair_url, market_cap: t.market_cap, change_24h: t.change_24h, liquidity_usd: t.liquidity_usd })}
              className="h-10 rounded-full bg-ink px-4 text-[14px] font-semibold text-on-ink">Full token page</button>
            <button type="button" onClick={go} className="h-10 rounded-full px-3 text-[14px] text-text-2">Scan again</button>
          </div>
        </>
      )}
    </div>
  );
}
