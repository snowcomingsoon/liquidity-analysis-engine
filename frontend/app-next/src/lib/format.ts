import { t } from "./i18n";
// The same formats as static/onchain/format.js, so both apps read alike.
export const usdShort = (v?: number | null) => (v == null || !Number.isFinite(Number(v)) ? "—"
  : v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(v >= 1e8 ? 0 : 1)}M`
    : v >= 1e3 ? `$${(v / 1e3).toFixed(v >= 1e5 ? 0 : 1)}k` : `$${Math.round(v)}`);

export function age(ts?: number): [string, boolean] {
  if (!ts) return ["—", false];
  const s = Date.now() / 1000 - ts;
  if (s < 3600) return [`${Math.max(1, Math.round(s / 60))}m`, s < 1800];
  if (s < 86400) return [`${Math.round(s / 3600)}h`, false];
  return [t("{n}d", { n: Math.round(s / 86400) }), false];
}

export const compact = (n: number) => new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(n);
export const num = (n?: number) => (n ?? 0).toLocaleString("en-US");

/** "↑ 42%" from a percentage (the API's change_24h). */
export function changeText(pct?: number | null): [string, "up" | "down" | ""] {
  if (pct == null || !Number.isFinite(Number(pct))) return ["—", ""];
  const p = Math.abs(pct);
  const t = p >= 1000 ? Math.round(p).toLocaleString("en-US") : p >= 10 ? String(Math.round(p)) : p.toFixed(1);
  return [`${pct >= 0 ? "↑" : "↓"} ${t}%`, pct >= 0 ? "up" : "down"];
}

/** The row's grey line without trading: FDV, volume a day, holders (top.js marketSub). */
export function marketSub(e: { fdv?: number; usage?: { vol_7d_avg?: number; vol_24h?: number; holders?: number }; liquidity_usd?: number }) {
  const u = e.usage ?? {};
  const vol = u.vol_7d_avg ?? u.vol_24h;
  const parts = [e.fdv ? `FDV ${usdShort(e.fdv)}` : null, vol != null ? t("{v}/day", { v: usdShort(vol) }) : null,
    u.holders != null ? t("{n} holders", { n: compact(u.holders) }) : null];
  const line = parts.filter(Boolean).join(" · ");
  return line || (e.liquidity_usd != null ? t("Liquidity {v}", { v: usdShort(e.liquidity_usd) }) : "");
}
