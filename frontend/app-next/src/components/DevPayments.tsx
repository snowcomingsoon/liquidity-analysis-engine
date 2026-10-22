import { useEffect, useState } from "react";
import * as api from "../lib/api";
import type { DevEvent, DevReport } from "../lib/api";

// What the developer is paid (pump.fun creator fees) and whether they sell
// (Lorenzo, 22/10, DREGG). The server reads the chain every 30 min.
const SOL_ADDR = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
const short = (a: string) => `${a.slice(0, 4)}…${a.slice(-4)}`;
const sol = (x?: number | null) => (x == null ? "—" : `${x >= 100 ? x.toFixed(0) : x >= 10 ? x.toFixed(1) : x.toFixed(2)} SOL`);
const qty = (x?: number | null) => (x == null ? "—" : x >= 1e6 ? `${(x / 1e6).toFixed(2)}M` : x >= 1e3 ? `${(x / 1e3).toFixed(0)}k` : x.toFixed(0));
const when = (ts: number) => {
  const s = Date.now() / 1000 - ts;
  return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m ago` : s < 86400 ? `${Math.round(s / 3600)}h ago`
    : new Date(ts * 1000).toLocaleDateString("en-US", { month: "short", day: "numeric" });
};
const LABEL: Record<DevEvent["kind"], string> = {
  fee: "Fees in", claim: "Claimed", sell: "Sold", limit_sell: "Sell order", buy: "Bought", transfer_out: "Sent out", transfer_in: "Received",
};
const TONE: Partial<Record<DevEvent["kind"], string>> = { sell: "text-down", limit_sell: "text-amber", transfer_out: "text-amber", buy: "text-up" };

function Stat({ k, v, tone = "" }: { k: string; v: string; tone?: string }) {
  return (
    <div className="rounded-[14px] bg-card px-3 py-2.5">
      <small className="block text-[12px] text-text-3">{k}</small>
      <b className={`num block text-[15px] font-semibold ${tone}`}>{v}</b>
    </div>
  );
}

function Bars({ daily }: { daily: DevReport["fees"]["daily"] }) {
  const days = daily.slice(-30);
  const max = Math.max(...days.map((d) => d.sol), 0.000001);
  if (!days.length) return null;
  return (
    <div className="mt-2 flex h-[56px] items-end gap-[3px] rounded-[14px] bg-card px-3 pb-2 pt-3" aria-label="Fees per day, last 30 days">
      {days.map((d) => (
        <span key={d.day} title={`${d.day} · ${sol(d.sol)}`} className="flex-1 rounded-[2px] bg-up/70" style={{ height: `${Math.max(4, (d.sol / max) * 100)}%` }} />
      ))}
    </div>
  );
}

function Setup({ token, symbol, onDone }: { token: string; symbol: string; onDone: () => void }) {
  const [v, setV] = useState("");
  const [err, setErr] = useState("");
  const ok = SOL_ADDR.test(v.trim());
  return (
    <form className="mt-2 flex gap-2" onSubmit={(ev) => {
      ev.preventDefault();
      if (!ok) return;
      api.watchDevPayments(token, symbol, v.trim()).then(onDone, (e) => setErr(e.message));
    }}>
      <input value={v} onChange={(ev) => { setV(ev.target.value); setErr(""); }} placeholder="Creator fee account"
        className="h-10 min-w-0 flex-1 rounded-full bg-card px-4 text-[14px] outline-none" aria-label="Creator fee account" />
      <button type="submit" disabled={!ok} className="h-10 rounded-full bg-ink px-4 text-[14px] font-medium text-on-ink disabled:opacity-40">Watch</button>
      {err && <p className="text-[12.5px] text-down">{err}</p>}
    </form>
  );
}

/** The developer's payments and sells of one token; nothing if unwatched
 *  (except the one-time setup on the benchmark). */
export function DevPayments({ token, symbol, setup = false }: { token: string; symbol: string; setup?: boolean }) {
  const [d, setD] = useState<Awaited<ReturnType<typeof api.getDevPayments>> | null>(null);
  const [n, setN] = useState(0);
  useEffect(() => {
    let gone = false;
    api.getDevPayments(token).then((r) => { if (!gone) setD(r); }, () => {});
    return () => { gone = true; };
  }, [token, n]);
  // While the first read runs, look again every 20 s.
  useEffect(() => {
    if (!d?.watched || d.report?.complete) return;
    const t = setTimeout(() => setN((x) => x + 1), 20000);
    return () => clearTimeout(t);
  }, [d]);
  if (!d || (!d.watched && !(setup && d.can_edit))) return null;
  const r = d.report;
  const moves = (r?.events ?? []).filter((e) => e.kind !== "fee" && e.kind !== "claim").slice(0, 8);
  return (
    <section className="mt-5">
      <h3 className="mb-2 flex items-baseline justify-between text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">
        Developer payments
        {r && <span className="text-[12px] normal-case tracking-normal">{r.complete ? `updated ${when(r.updated_at)}` : "reading history…"}</span>}
      </h3>
      {!d.watched && <><p className="text-[13px] text-text-3">Paste the pump.fun account the creator fees go to.</p><Setup token={token} symbol={symbol} onDone={() => setN((x) => x + 1)} /></>}
      {d.watched && !r && <p className="rounded-[14px] bg-card px-3 py-3 text-[13px] text-text-3">Reading the fee account…</p>}
      {r && (
        <>
          <div className="grid grid-cols-3 gap-2">
            <Stat k="Last 24h" v={sol(r.fees.d1)} />
            <Stat k="Last 7 days" v={sol(r.fees.d7)} />
            <Stat k={r.first_ts ? `Since ${new Date(r.first_ts * 1000).toLocaleDateString("en-US", { month: "short", day: "numeric" })}` : "Total"} v={sol(r.fees.total)} />
          </div>
          <Bars daily={r.fees.daily} />
          {r.claimers.map((c) => (
            <div key={c.address} className="mt-3">
              <p className="mb-1.5 text-[13px] text-text-2">
                Claimed by <a className="underline decoration-text-3/40 underline-offset-2" href={`https://solscan.io/account/${c.address}`} target="_blank" rel="noreferrer">{short(c.address)}</a> · {sol(c.claimed_sol)}
              </p>
              <div className="grid grid-cols-3 gap-2">
                <Stat k={`${symbol} held`} v={qty(c.holding)} />
                <Stat k="Bought" v={qty(c.bought)} tone="text-up" />
                <Stat k="Sold" v={qty(c.sold)} tone={c.sold ? "text-down" : ""} />
                <Stat k="Sold for" v={sol(c.sold_sol)} />
                <Stat k="In sell orders" v={qty(c.in_orders)} tone={c.in_orders ? "text-amber" : ""} />
                <Stat k="Sent to others" v={qty(c.sent_out)} tone={c.sent_out ? "text-amber" : ""} />
              </div>
            </div>
          ))}
          {moves.length > 0 && (
            <ol className="mt-2">
              {moves.map((e) => (
                <li key={e.id}>
                  <a href={`https://solscan.io/tx/${e.tx ?? e.id}`} target="_blank" rel="noreferrer" className="flex items-baseline gap-3 py-2">
                    <span className="min-w-0 flex-1">
                      <b className={`block text-[14px] font-medium ${TONE[e.kind] ?? ""}`}>{LABEL[e.kind]} {qty(e.amount)} {symbol}</b>
                      <small className="text-[12.5px] text-text-3">{e.kind === "sell" || e.kind === "buy" ? sol(Math.abs(e.sol ?? 0)) : e.other && e.kind !== "limit_sell" ? `to ${short(e.other)}` : ""}</small>
                    </span>
                    <time className="text-[12.5px] text-text-3">{when(e.ts)}</time>
                  </a>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  );
}
