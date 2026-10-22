import { useEffect, useMemo, useRef, useState } from "react";
import type { ClusterLive, SellsReport } from "../lib/api";
import { CheckProgress, useClusterCheck } from "./CheckProgress";
import { t, locale } from "../lib/i18n";

// The bubble map lives once, in the classic app's static files: the same
// module draws it here (canvas, 60 fps, still with reduced motion).
const MAP_URL = "/static/onchain/cluster-map.js";
type MapApi = { highlight(a: Set<string> | null): void; update(r: SellsReport): void; destroy(): void };
type Pick = { address: string; share: number; cluster: { id: string }; label?: string | null; others?: number } | null;

const pct = (x?: number | null) => (x == null ? "—" : `${(x * 100).toFixed(x < 0.01 ? 2 : 1)}%`);
const short = (a: string) => `${a.slice(0, 6)}…${a.slice(-4)}`;
const when = (ts: number) => {
  const s = Date.now() / 1000 - ts;
  return s < 3600 ? t("{n}m ago", { n: Math.max(1, Math.round(s / 60)) }) : s < 86400 ? t("{n}h ago", { n: Math.round(s / 3600) })
    : new Date(ts * 1000).toLocaleDateString(locale(), { month: "short", day: "numeric" });
};
const liveSig = (l: ClusterLive) => `${l.holders?.length ?? 0}.${l.clusters?.length ?? 0}.${(l.clusters ?? []).reduce((s, c) => s + (c.edges?.length ?? 0) + c.wallets.length, 0)}.${l.events?.length ?? 0}`;
/** What a running check has read so far, as a report: its clusters, then
 *  every other holder in the grey top group. */
function fromLive(chain: string, token: string, l: ClusterLive): SellsReport {
  const share = new Map((l.holders ?? []).map((h) => [h.address, h.share ?? 0]));
  const inside = new Set((l.clusters ?? []).flatMap((c) => c.wallets));
  const clusters = (l.clusters ?? []).map((c) => ({ id: c.id, edges: c.edges, links: c.links, wallets: c.wallets.map((a) => ({ address: a, share: share.get(a) ?? 0 })),
    share: c.wallets.reduce((s, a) => s + (share.get(a) ?? 0), 0) }));
  const top = (l.holders ?? []).filter((h) => !inside.has(h.address));
  return { chain, token, clusters: top.length ? [...clusters, { id: "top", wallets: top }] : clusters, events: [...(l.events ?? [])].sort((a, b) => b.ts - a.ts) };
}
const tone = (s?: number | null) => (s == null ? "text-text-3" : s >= 70 ? "text-down" : s >= 40 ? "text-amber" : "text-up");


/** Coordinated sells of one token: its wallet clusters as bubbles and the
 *  waves they sold in; without a report, where its check stands. */
export function SellsMap({ chain, token, starting = false, bare = false }: { chain: string; token: string; starting?: boolean; bare?: boolean }) {
  const { rep: done, check } = useClusterCheck(chain, token, starting);
  // While the check runs, what it has read so far is drawn and fills in.
  const sig = check?.live ? liveSig(check.live) : "";
  // The last live picture stays until the report replaces it (live goes when the run ends).
  const last = useRef<SellsReport | null>(null);
  const rep = useMemo(() => done ?? (last.current = check?.live ? fromLive(chain, token, check.live) : last.current), [done, sig]);
  const [pick, setPick] = useState<Pick>(null);
  const [lit, setLit] = useState<number | null>(null);
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<MapApi | null>(null);
  const has = !!rep && rep.clusters.some((c) => c.wallets.length);

  useEffect(() => {
    if (!has || !host.current) return;
    if (map.current) { map.current.update(rep!); return; }
    let gone = false;
    import(/* @vite-ignore */ MAP_URL).then((m) => {
      if (gone || !host.current) return;
      map.current = m.clusterMap(host.current, rep, { onPick: setPick, words: { cluster: t("Cluster"), wallets: t("wallets"), nolink: t("No link found"), none: t("No linked wallets among the top holders.") } });
    }).catch(() => {});
    return () => { gone = true; };
  }, [rep, has]);
  useEffect(() => () => { map.current?.destroy(); map.current = null; }, []);

  if (!rep || !has) {
    if (!check && !starting) return null;
    return (
      <section className={bare ? "" : "mt-5"}>
        {!bare && <h3 className="mb-2 text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">{t("Coordinated sells")}</h3>}
        <CheckProgress check={check} />
        {bare && <div className="cp-empty mt-3 grid h-[280px] place-items-center rounded-[16px] bg-card text-[13px] text-text-3">{t("The map fills in as holders are read")}</div>}
      </section>
    );
  }
  const real = rep.clusters.filter((c) => c.id !== "top");
  const name = (id: string) => (id === "top" ? t("Top holders") : `Cluster ${real.findIndex((c) => c.id === id) + 1}`);
  const waves = rep.events.slice(0, 6);
  const light = (i: number) => {
    const next = lit === i ? null : i;
    setLit(next);
    const e = next == null ? null : waves[next];
    const c = e && rep.clusters.find((x) => x.id === e.cluster);
    map.current?.highlight(e ? new Set(e.sellers?.length ? e.sellers : (c?.wallets ?? []).map((w) => w.address)) : null);
  };

  return (
    <section className={bare ? "" : "mt-5"}>
      <h3 className="mb-2 flex items-baseline justify-between text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">
        {t("Coordinated sells")}<b className={`num text-[13px] font-semibold normal-case tracking-normal ${tone(rep.risk?.score)}`}>{done ? (rep.risk?.score == null ? t("risk {n}", { n: "—" }) : t("risk {n}/100 · {level}", { n: Math.round(rep.risk.score), level: t(rep.risk.score >= 60 ? "high" : rep.risk.score >= 30 ? "medium" : "low") })) : t("live")}</b>
      </h3>
      {!done && <div className="mb-3"><CheckProgress check={check} /></div>}
      <div ref={host} className="overflow-hidden rounded-[16px] bg-card" aria-label={t("Wallet bubble map")} />
      <p className="mt-1 min-h-[1.4em] text-[12.5px] text-text-3">
        {pick ? (pick.label ? `${t("{n} smaller holders, no link found", { n: pick.others ?? 0 })} · ${t("{p} of supply", { p: pct(pick.share) })}` : `${short(pick.address)} · ${t("{p} of supply", { p: pct(pick.share) })} · ${pick.cluster.id === "top" ? t("top holder, no link found") : name(pick.cluster.id)}`)
          : t("Bubble size = share of supply. Tap a bubble or a sell.")}
      </p>
      {waves.length > 0 && (
        <ol className="mt-1">
          {waves.map((e, i) => (
            <li key={e.id}>
              <button type="button" onClick={() => light(i)} aria-pressed={lit === i}
                className={`flex w-full items-baseline gap-3 py-2 text-left transition-opacity ${lit != null && lit !== i ? "opacity-45" : ""}`}>
                <span className="min-w-0 flex-1">
                  <b className="block text-[14px] font-medium">{t("{who} sold {p}", { who: name(e.cluster), p: pct(e.share_sold) })}</b>
                  <small className="text-[12.5px] text-text-3">{t("{n} wallets", { n: e.sellers?.length || e.wallets })}{e.window_s ? ` ${t("in")} ${e.window_s >= 60 ? `${Math.round(e.window_s / 60)} min` : `${Math.round(e.window_s)} s`}` : ""}</small>
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
