import * as api from "./api";
import type { Candle } from "./types";

// The token page's candles, as detail.js fetches them. Three sources race and
// the first with a line wins: the server's copy (peek: never calls anyone),
// GeckoTerminal straight from the browser on the viewer's own quota, and the
// server fetching it only if both came back empty. No pool known: DexScreener
// says which is the token's main pool, then GeckoTerminal.

export const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "8h", "1d", "1w"] as const;
export type Interval = (typeof INTERVALS)[number];
// 8h and 1w are built from 4h and 1d candles: [base, step, offset].
const DERIVED: Partial<Record<Interval, [Interval, number, number]>> = { "8h": ["4h", 28800, 0], "1w": ["1d", 604800, 4 * 86400] };
export const STEP: Record<Interval, number> = { "1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "8h": 28800, "1d": 86400, "1w": 604800 };
const GECKO = "https://api.geckoterminal.com/api/v2";
const GECKO_NET: Record<string, string> = { solana: "solana", robinhood: "robinhood", base: "base", bsc: "bsc", ethereum: "eth", arc: "arc" };
const GECKO_TF: Record<string, [string, number]> = { "1m": ["minute", 1], "5m": ["minute", 5], "15m": ["minute", 15], "1h": ["hour", 1], "4h": ["hour", 4], "1d": ["day", 1] };
export const DS_EMBED = new Set(["solana", "base", "bsc", "ethereum", "arc"]);   // chains DexScreener charts
const FRESH_MS = 30_000;

export type Market = { chain: string; token: string; symbol: string; pair?: string };

const charts = new Map<string, { at: number; promise: Promise<Candle[]>; candles?: Candle[] }>();
const pools = new Map<string, string>();

async function fetchJson<T>(url: string, ms: number): Promise<T> {
  const r = await fetch(url, { signal: AbortSignal.timeout(ms), headers: { Accept: "application/json" }, referrerPolicy: "no-referrer" });
  if (!r.ok) throw new Error(String(r.status));
  return r.json() as Promise<T>;
}

type DsPair = { pairAddress?: string; liquidity?: { usd?: number }; marketCap?: number; fdv?: number; priceUsd?: string; priceChange?: { h24?: number } };
const deepest = (rows: unknown) => (Array.isArray(rows) ? (rows as DsPair[]) : []).sort((x, y) => (y.liquidity?.usd ?? 0) - (x.liquidity?.usd ?? 0))[0];

export async function poolOf(m: Market): Promise<string> {
  if (m.pair) return m.pair;
  const k = `${m.chain}:${m.token}`;
  if (pools.has(k)) return pools.get(k)!;
  let pair = "";
  try { pair = deepest(await fetchJson(`https://api.dexscreener.com/tokens/v1/${m.chain}/${m.token}`, 4000))?.pairAddress ?? ""; } catch { /* GeckoTerminal below */ }
  const net = GECKO_NET[m.chain];
  if (!pair && net) {
    try {
      const d = await fetchJson<{ data?: { attributes?: { address?: string } }[] }>(`${GECKO}/networks/${net}/tokens/${m.token}/pools?page=1`, 4000);
      pair = d?.data?.[0]?.attributes?.address ?? "";
    } catch { /* no pool: the page says so */ }
  }
  if (pair) pools.set(k, pair);
  return pair;
}

async function geckoDirect(m: Market, pair: string, iv: Interval): Promise<Candle[]> {
  const net = GECKO_NET[m.chain];
  const [tf, agg] = GECKO_TF[iv] ?? GECKO_TF["5m"];
  if (!net) throw new Error("chain");
  const q = new URLSearchParams({ aggregate: String(agg), limit: "1000", currency: "usd", ...(m.token ? { token: m.token } : {}) });
  const d = await fetchJson<{ data?: { attributes?: { ohlcv_list?: number[][] } } }>(`${GECKO}/networks/${net}/pools/${pair}/ohlcv/${tf}?${q}`, 6000);
  return (d?.data?.attributes?.ohlcv_list ?? []).map((r) => ({ time: r[0], open: Number(r[1]), high: Number(r[2]), low: Number(r[3]), close: Number(r[4]) }))
    .filter((c) => Number.isFinite(c.close)).sort((a, b) => a.time - b.time);
}

const clean = (d: { candles?: Candle[] }) => (d?.candles ?? []).filter((c) => Number.isFinite(c.close));
const enough = (c: Candle[]) => { if (c.length < 2) throw new Error("empty"); return c; };

export function aggregate(candles: Candle[], step: number, offset: number): Candle[] {
  const out: Candle[] = [];
  for (const c of candles) {
    const t = Math.floor((c.time - offset) / step) * step + offset;
    const cur = out[out.length - 1];
    if (cur && cur.time === t) { cur.high = Math.max(cur.high, c.high); cur.low = Math.min(cur.low, c.low); cur.close = c.close; }
    else out.push({ ...c, time: t });
  }
  return out;
}

export function chartFor(m: Market, iv: Interval): Promise<Candle[]> {
  const d = DERIVED[iv];
  if (d) return chartFor(m, d[0]).then((c) => aggregate(c, d[1], d[2]));
  const k = `${m.chain}:${m.pair || m.token}:${iv}`;
  const hit = charts.get(k);
  if (hit && Date.now() - hit.at < FRESH_MS) return hit.promise;
  const promise = (async () => {
    const pair = await poolOf(m);
    if (!pair) return [];
    const peek = api.getTokenChart(m.chain, pair, m.symbol, iv, true).then(clean).then(enough);
    const direct = geckoDirect(m, pair, iv).then(enough);
    try { return await Promise.any([peek, direct]); }
    catch { return clean(await api.getTokenChart(m.chain, pair, m.symbol, iv)); }
  })().then((candles) => { charts.set(k, { at: Date.now(), promise: Promise.resolve(candles), candles }); return candles; },
    (err) => { if (charts.get(k)?.promise === promise) charts.delete(k); throw err; });
  charts.set(k, { at: Date.now(), promise, candles: hit?.candles });
  if (charts.size > 60) charts.delete(charts.keys().next().value!);
  return promise;
}

/** The candles already in hand for an interval (drawn while the fresh ones load). */
export function cached(m: Market, iv: Interval): Candle[] | undefined {
  const d = DERIVED[iv];
  const c = charts.get(`${m.chain}:${m.pair || m.token}:${d ? d[0] : iv}`)?.candles;
  return c && d ? aggregate(c, d[1], d[2]) : c;
}

/** Drop an interval's candles, so the next read fetches them again (the live refresh). */
export function forget(m: Market, iv: Interval) {
  const d = DERIVED[iv];
  charts.delete(`${m.chain}:${m.pair || m.token}:${d ? d[0] : iv}`);
}

/** Cap, supply and 24h change from DexScreener's deepest pool (Lorenzo, 16/10). */
export async function liveQuote(m: Market): Promise<{ cap: number; supply?: number; change?: number; pair?: string } | null> {
  if (!m.token || !DS_EMBED.has(m.chain)) return null;
  const best = deepest(await fetchJson(`https://api.dexscreener.com/tokens/v1/${m.chain}/${m.token}`, 5000).catch(() => null));
  const cap = Number(best?.marketCap || best?.fdv);
  const price = Number(best?.priceUsd);
  if (!(cap > 0)) return null;
  return { cap, supply: price > 0 ? cap / price : undefined, change: best?.priceChange?.h24, pair: best?.pairAddress };
}

export function embedUrl(chain: string, pair: string, iv: Interval) {
  const i = ({ "1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240" } as Record<string, string>)[iv] ?? "5";
  return `https://dexscreener.com/${chain}/${pair}?embed=1&loadChartSettings=0&trades=0&tabs=0&info=0&chartLeftToolbar=0&chartTheme=dark&theme=dark&chartStyle=2&chartType=marketCap&interval=${i}`;
}
