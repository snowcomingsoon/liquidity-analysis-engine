import { useEffect, useState } from "react";
import * as api from "../lib/api";
import type { Gem } from "../lib/types";
import type { SectorsView } from "../lib/sectors";
import { Logo } from "../components/Logo";
import { age, changeText, usdShort } from "../lib/format";
import { gemId } from "../components/TokenRow";

const WATCH_KEY = "watchlist-v1";   // the token page's star (TokenPage.tsx)

export function watchedIds(): string[] {
  try { return (JSON.parse(localStorage.getItem(WATCH_KEY) || "[]") as string[]).map((id) => id.replace(/^gem:/, ""))
    .filter((id) => !id.startsWith("meme:")); } catch { return []; }   // no memes: serious projects only
}

/** Watch (direction A, screen 5): the starred tokens, each with the line of what changed. */
export function Watch({ data, gems, onOpen }: { data: SectorsView | null; gems: Gem[]; onOpen: (e: Gem) => void }) {
  const ids = watchedIds();
  const byId = new Map<string, { e: Gem; sector?: string }>();
  for (const e of gems) byId.set(gemId(e), { e });
  for (const s of data?.sectors ?? []) for (const e of s.entries) if (e.in !== false || !byId.get(gemId(e))?.sector) byId.set(gemId(e), { e, sector: s.label });
  const news = new Map((data?.today.items ?? []).map((i) => [gemId(i.gem), i] as const));
  const [tab, setTab] = useState<"follow" | "alerts">("follow");
  const [alerts, setAlerts] = useState<api.AlertItem[] | null>(null);
  // Tokens outside the ranking: their real name from the token page, never the address (Lorenzo 22/10).
  const [named, setNamed] = useState<Record<string, Gem | null>>({});
  useEffect(() => {
    for (const id of ids) {
      if (byId.has(id) || news.has(id) || id in named) continue;
      const cut = id.indexOf(":");
      api.getToken(id.slice(0, cut), id.slice(cut + 1))
        .then((d) => setNamed((m) => ({ ...m, [id]: (d.entry as Gem | null) ?? null })))
        .catch(() => setNamed((m) => ({ ...m, [id]: null })));
    }
  }, [ids.join(","), data, gems.length]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    Promise.all([api.getAlerts("meme").catch(() => ({ items: [] })), api.getAlerts("gem").catch(() => ({ items: [] }))])
      .then(([m, g]) => setAlerts([...(m.items ?? []), ...(g.items ?? [])].sort((x, y) => y.at - x.at).slice(0, 25)));
  }, []);
  const seg = ([["follow", `Following ${ids.length}`], ["alerts", `Alerts${alerts ? ` ${alerts.length}` : ""}`]] as const);
  return (
    <>
      <div className="flex rounded-full bg-pill p-1">
        {seg.map(([k, l]) => (
          <button key={k} type="button" aria-pressed={tab === k} onClick={() => setTab(k)}
            className={`h-9 flex-1 rounded-full text-[14px] font-medium ${tab === k ? "bg-card text-text shadow-[0_1px_2px_rgb(0_0_0/.06)]" : "text-text-2"}`}>{l}</button>
        ))}
      </div>
      {tab === "alerts" && (alerts && !alerts.length ? <p className="mt-4 rounded-[16px] bg-card p-4 text-[14px] text-text-2">No alert yet: the ones sent on Telegram show up here.</p> : (
        <ol className="mt-3 rounded-[16px] bg-card p-1.5">
          {(alerts ?? []).map((a) => {
            const cap = a.gone ? null : a.cap0 && a.now != null ? a.cap0 * (1 + a.now) : a.cap0;
            const [chg, sign] = changeText(a.now == null ? null : a.now * 100);
            return (
              <li key={`${a.chain}:${a.token_address}:${a.at}`}>
                <button type="button" onClick={() => onOpen({ chain: a.chain, token_address: a.token_address, symbol: a.symbol, name: a.name, image: a.image, market_cap: cap ?? undefined })}
                  className="flex w-full items-center gap-3 rounded-[12px] px-2 py-2 text-left active:bg-pill">
                  <Logo size={36} symbol={a.symbol} image={a.image} chain={a.chain} token={a.token_address} />
                  <span className="min-w-0 flex-1">
                    <b className="block truncate text-[15px] font-semibold leading-tight">{a.symbol}</b>
                    <small className="block truncate text-[12.5px] text-text-3">alerted {age(a.at)[0]} ago{a.gone ? " · pool gone" : ""}</small>
                  </span>
                  <span className="flex flex-col items-end">
                    <b className="num text-[14px] font-semibold">{usdShort(cap)}</b>
                    <em className={`num text-[12px] not-italic ${sign === "up" ? "text-up" : sign === "down" ? "text-down" : "text-text-3"}`}>{chg} since</em>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      ))}
      {tab === "follow" && !ids.length && <p className="mt-4 rounded-[16px] bg-card p-4 text-[14px] text-text-2">Tap ☆ on a token to follow it here, with what changed since the last research run.</p>}
      {tab === "follow" && ids.length > 0 && (() => {
        // Ranked first with real data; the rest folded away, and a token with no real name is not shown (Lorenzo 22/10).
        const rows = ids.flatMap((id) => {
          const hit = byId.get(id), n = news.get(id);
          const e = hit?.e ?? n?.gem ?? named[id] ?? undefined;
          return e && (e.name || e.symbol) && !/^0x[0-9a-f]{4}$/i.test(e.symbol ?? "") ? [{ id, e, hit, n }] : [];
        });
        const ranked = rows.filter((r) => r.hit), off = rows.filter((r) => !r.hit);
        const row = ({ id, e, hit, n }: (typeof rows)[number]) => {
          const [chg, sign] = changeText(e.change_24h);
          const line = n ? n.text : hit?.sector ? `${hit.sector}${e.arena_rank ? ` · #${e.arena_rank}` : ""}${e.score != null ? ` · score ${Math.round(e.score)}` : ""}` : "";
          return (
            <li key={id}>
              <button type="button" onClick={() => onOpen(e)} className="flex w-full items-center gap-3 rounded-[12px] px-2 py-2 text-left active:bg-pill">
                <Logo size={36} symbol={e.symbol} image={e.image} chain={e.chain} token={e.token_address} />
                <span className="min-w-0 flex-1">
                  <b className="block truncate text-[15px] font-semibold leading-tight">{e.symbol || e.name}{e.name && e.symbol && e.name !== e.symbol && <span className="font-normal text-text-3"> · {e.name}</span>}</b>
                  {line && <small className="block truncate text-[12.5px] text-text-3">{line}</small>}
                </span>
                {e.market_cap != null && (
                  <span className="flex flex-col items-end">
                    <b className="num text-[14px] font-semibold">{usdShort(e.market_cap)}</b>
                    {e.change_24h != null && <em className={`num text-[12px] not-italic ${sign === "up" ? "text-up" : sign === "down" ? "text-down" : "text-text-3"}`}>{chg}</em>}
                  </span>
                )}
              </button>
            </li>
          );
        };
        return (
          <>
            {ranked.length > 0 ? <ol className="mt-3 rounded-[16px] bg-card p-1.5">{ranked.map(row)}</ol>
              : <p className="mt-4 rounded-[16px] bg-card p-4 text-[14px] text-text-2">None of the tokens you follow is in the ranking now.</p>}
            {off.length > 0 && (
              <details className="mt-3 rounded-[16px] bg-card p-1.5">
                <summary className="cursor-pointer px-2 py-2 text-[14px] font-medium text-text-2">Not in the ranking now · {off.length}</summary>
                <ol>{off.map(row)}</ol>
              </details>
            )}
          </>
        );
      })()}
    </>
  );
}
