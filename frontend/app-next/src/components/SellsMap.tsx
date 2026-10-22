import { useEffect, useRef, useState } from "react";
import * as api from "../lib/api";
import type { ClusterCheck, SellsReport } from "../lib/api";

// The bubble map lives once, in the classic app's static files: the same
// module draws it here (canvas, 60 fps, still with reduced motion).
const MAP_URL = "/static/onchain/cluster-map.js";
type MapApi = { highlight(a: Set<string> | null): void; destroy(): void };
type Pick = { address: string; share: number; cluster: { id: string } } | null;

const pct = (x?: number | null) => (x == null ? "—" : `${(x * 100).toFixed(x < 0.01 ? 2 : 1)}%`);
const short = (a: string) => `${a.slice(0, 6)}…${a.slice(-4)}`;
const when = (ts: number) => {
  const s = Date.now() / 1000 - ts;
  return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m ago` : s < 86400 ? `${Math.round(s / 3600)}h ago`
    : new Date(ts * 1000).toLocaleDateString("en-US", { month: "short", day: "numeric" });
};
const tone = (s?: number | null) => (s == null ? "text-text-3" : s >= 70 ? "text-down" : s >= 40 ? "text-amber" : "text-up");

// Without a report the section still shows, with where its check stands
// (Lorenzo, 22/10: "mica c'è ancora"): opening the page queues the check.
const WAIT: Record<ClusterCheck["state"], string> = {
  running: "Cluster check running now. The map appears here when it ends.",
  queued: "Cluster check queued. The map appears here when it runs.",
  none: "Cluster check not run yet for this token.",
  failed: "Cluster check failed on this token's data. It retries later.",
  built: "Cluster check done: no wallet cluster found among the top holders.",
  unsupported: "Cluster check is not available on this chain.",
};

/** Coordinated sells of one token: its wallet clusters as bubbles and the
 *  waves they sold in; without a report, where its check stands. */
export function SellsMap({ chain, token }: { chain: string; token: string }) {
  const [rep, setRep] = useState<SellsReport | null>(null);
  const [check, setCheck] = useState<ClusterCheck | null>(null);
  const [pick, setPick] = useState<Pick>(null);
  const [lit, setLit] = useState<number | null>(null);
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<MapApi | null>(null);

  useEffect(() => {
    let live = true;
    setRep(null); setCheck(null);
    const n = token.startsWith("0x") ? token.toLowerCase() : token;
    api.getCoordinatedSells().then((d) => {
      if (!live) return;
      const found = d.sample ? null : (d.reports ?? []).find((r) => r.chain === chain && r.token === n) ?? null;
      if (found) setRep(found);
      else api.getClusterCheck(chain, token).then((c) => { if (live) setCheck(c); }).catch(() => {});
    }).catch(() => {});
    return () => { live = false; };
  }, [chain, token]);

  useEffect(() => {
    if (!rep || !host.current) return;
    let gone = false;
    import(/* @vite-ignore */ MAP_URL).then((m) => {
      if (gone || !host.current) return;
      map.current = m.clusterMap(host.current, rep, { onPick: setPick });
    }).catch(() => {});
    return () => { gone = true; map.current?.destroy(); map.current = null; };
  }, [rep]);

  if (!rep) {
    if (!check) return null;
    return (
      <section className="mt-5">
        <h3 className="mb-2 text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">Coordinated sells</h3>
        <p className="flex items-center gap-2.5 rounded-[16px] bg-card px-4 py-3.5 text-[13.5px] text-text-2">
          {(check.state === "running" || check.state === "queued") && <i className="h-2 w-2 flex-none animate-pulse rounded-full bg-amber" aria-hidden="true" />}
          <span>{check.state === "built" && check.clusters ? "Clusters found. Their sells are being read: the map appears here in a few minutes." : WAIT[check.state]}{check.state === "queued" && check.place ? ` Place in line: ${check.place}.` : ""}</span>
        </p>
      </section>
    );
  }
  const real = rep.clusters.filter((c) => c.id !== "top");
  const name = (id: string) => (id === "top" ? "Top holders" : `Cluster ${real.findIndex((c) => c.id === id) + 1}`);
  const waves = rep.events.slice(0, 6);
  const light = (i: number) => {
    const next = lit === i ? null : i;
    setLit(next);
    const e = next == null ? null : waves[next];
    const c = e && rep.clusters.find((x) => x.id === e.cluster);
    map.current?.highlight(e ? new Set(e.sellers?.length ? e.sellers : (c?.wallets ?? []).map((w) => w.address)) : null);
  };

  return (
    <section className="mt-5">
      <h3 className="mb-2 flex items-baseline justify-between text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">
        Coordinated sells<b className={`num text-[13px] font-semibold normal-case tracking-normal ${tone(rep.risk?.score)}`}>risk {rep.risk?.score == null ? "—" : Math.round(rep.risk.score)}</b>
      </h3>
      <div ref={host} className="overflow-hidden rounded-[16px] bg-card" aria-label="Wallet bubble map" />
      <p className="mt-1 min-h-[1.4em] text-[12.5px] text-text-3">
        {pick ? `${short(pick.address)} · ${pct(pick.share)} of supply · ${pick.cluster.id === "top" ? "top holder, no link found" : name(pick.cluster.id)}`
          : "Bubble size = share of supply. Tap a bubble or a sell."}
      </p>
      {waves.length > 0 && (
        <ol className="mt-1">
          {waves.map((e, i) => (
            <li key={e.id}>
              <button type="button" onClick={() => light(i)} aria-pressed={lit === i}
                className={`flex w-full items-baseline gap-3 py-2 text-left transition-opacity ${lit != null && lit !== i ? "opacity-45" : ""}`}>
                <span className="min-w-0 flex-1">
                  <b className="block text-[14px] font-medium">{name(e.cluster)} sold {pct(e.share_sold)}</b>
                  <small className="text-[12.5px] text-text-3">{e.sellers?.length || e.wallets} wallets{e.window_s ? ` in ${e.window_s >= 60 ? `${Math.round(e.window_s / 60)} min` : `${Math.round(e.window_s)} s`}` : ""}</small>
                </span>
                <time className="text-[12.5px] text-text-3">{when(e.ts)}</time>
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
