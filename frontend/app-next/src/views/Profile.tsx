import { useEffect, useRef, useState } from "react";
import * as api from "../lib/api";
import type { Gem } from "../lib/types";
import { Sheet } from "../components/Sheet";
import { Logo } from "../components/Logo";
import { age } from "../lib/format";
import { t, locale } from "../lib/i18n";

// Profile (profile.js with trading off): picture, name, handle and bio, the
// theme, and the track record of the picks (track.js).
const THEMES = [["light", "Light"], ["dark", "Dark"], ["auto", "Auto"]] as const;
const KEY = "lae:theme";
const DAYS = [1, 3, 7, 30, 90];
const pct = (f?: number | null) => (f == null ? "—" : `${f > 0 ? "+" : ""}${Math.round(f * 100)}%`);
const share = (f?: number | null) => (f == null ? "—" : `${Math.round(f * 100)}%`);
const tone = (f?: number | null) => (f == null ? "" : f >= 0 ? "text-up" : "text-down");

function themePref(): string { try { return localStorage.getItem(KEY) || "light"; } catch { return "light"; } }
function applyTheme(pref: string) {
  try { localStorage.setItem(KEY, pref); } catch { /* private mode */ }
  const dark = pref === "dark" || (pref === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}
const readFile = (f: File) => new Promise<string>((ok, ko) => { const r = new FileReader(); r.onload = () => ok(String(r.result)); r.onerror = ko; r.readAsDataURL(f); });

export function Profile({ onOpen, onMe }: { onOpen: (e: Gem, context: string) => void; onMe?: (p: api.Profile) => void }) {
  const [p, setP] = useState<api.Profile | null>(null);
  const [theme, setTheme] = useState(themePref);
  const [edit, setEdit] = useState(false);
  const [err, setErr] = useState("");
  const [track, setTrack] = useState<api.Track | null>(null);
  const [days, setDays] = useState<number | null>(null);
  const form = useRef<HTMLFormElement>(null);

  const me = (x: api.Profile) => { setP(x); onMe?.(x); };
  useEffect(() => { api.getProfile().then((d) => me(d.profile)).catch(() => {}); api.getTrack().then(setTrack).catch(() => {}); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  async function save(ev: React.FormEvent) {
    ev.preventDefault();
    const f = new FormData(form.current!);
    try { me((await api.updateProfile({ display_name: String(f.get("display_name")), handle: String(f.get("handle")), bio: String(f.get("bio") ?? "") })).profile); setEdit(false); }
    catch (e) { setErr((e as Error).message); }
  }

  const hz = track?.stats?.horizons ?? [];
  const ready = DAYS.filter((d) => hz.find((x) => x.days === d)?.all?.n);
  const h = days && ready.includes(days) ? days : ready[ready.length - 1];
  const H = hz.find((x) => x.days === h);
  const row = (c: api.TrackPick, sub: string) => {
    const ret = c.now ?? c.checkpoint?.ret;
    const ctx = t("{what} {t} ago", { what: c.decision === "ranked" ? (c.rank ? t("Picked at #{n}", { n: c.rank }) : t("Picked it")) : c.decision === "rejected" ? t("Turned it down") : t("Studied, not picked"), t: age(c.at)[0] });
    return (
      <li key={`${c.chain}:${c.token_address}:${c.at}`}>
        <button type="button" onClick={() => onOpen({ chain: c.chain, token_address: c.token_address, symbol: c.symbol, score: c.score }, ctx)}
          className="flex w-full items-center gap-3 rounded-[12px] px-2 py-2 text-left active:bg-pill">
          <Logo size={36} symbol={c.symbol} chain={c.chain} token={c.token_address} />
          <span className="min-w-0 flex-1"><b className="block truncate text-[15px] font-semibold">{c.symbol}</b><small className="block truncate text-[12.5px] text-text-3">{sub}</small></span>
          <b className={`num text-[14px] font-semibold ${tone(ret)}`}>{pct(ret)}</b>
        </button>
      </li>
    );
  };

  return (
    <>
      {p && (
        <section className="flex items-center gap-3 rounded-[16px] bg-card p-3">
          <label className="relative h-16 w-16 flex-none cursor-pointer overflow-hidden rounded-full bg-ink text-on-ink" title={t("Change picture")}>
            {p.avatar_url ? <img src={p.avatar_url} alt="" className="h-full w-full object-cover" /> : <i className="grid h-full w-full place-items-center text-[24px] font-semibold not-italic">{p.display_name.trim().charAt(0).toUpperCase()}</i>}
            <input type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={async (e) => { const f = e.target.files?.[0]; if (f) try { me((await api.uploadAvatar(await readFile(f))).profile); } catch { /* keep */ } }} />
          </label>
          <span className="min-w-0 flex-1">
            <b className="block truncate text-[18px] font-semibold">{p.display_name}</b>
            <small className="block text-[13px] text-text-3">@{p.handle}{p.joined ? ` · ${t("joined")} ${new Date(p.joined * 1000).toLocaleDateString(locale(), { month: "short", year: "numeric" })}` : ""}</small>
            {p.bio ? <p className="mt-1 text-[13.5px] text-text-2">{p.bio}</p> : <button type="button" onClick={() => setEdit(true)} className="mt-1 text-[13px] text-text-2 underline">{t("+ Add a bio")}</button>}
          </span>
          <button type="button" onClick={() => { setErr(""); setEdit(true); }} className="h-9 rounded-full bg-pill px-3 text-[13px] font-semibold">{t("Edit")}</button>
        </section>
      )}

      <h2 className="mb-2 mt-5 text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">{t("Appearance")}</h2>
      <div className="flex rounded-full bg-pill p-1">
        {THEMES.map(([k, l]) => (
          <button key={k} type="button" aria-pressed={theme === k} onClick={() => { setTheme(k); applyTheme(k); }}
            className={`h-9 flex-1 rounded-full text-[14px] font-medium ${theme === k ? "bg-card text-text shadow-[0_1px_2px_rgb(0_0_0/.06)]" : "text-text-2"}`}>{t(l)}</button>
        ))}
      </div>

      <h2 className="mb-2 mt-5 text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">{t("Track record")}</h2>
      <p className="text-[13px] text-text-2">{t("Every pick is frozen with its receipt and checked against the market. Research, not advice.")}</p>
      <div className="mt-2 flex gap-1">
        {DAYS.map((d) => (
          <button key={d} type="button" disabled={!ready.includes(d)} aria-pressed={d === h} onClick={() => setDays(d)}
            className={`h-8 flex-1 rounded-full text-[13px] font-medium disabled:opacity-40 ${d === h ? "bg-ink text-on-ink" : "bg-pill text-text-2"}`}>{t("{n}d", { n: d })}</button>
        ))}
      </div>
      {track && !H && <p className="mt-2 rounded-[16px] bg-card p-4 text-[14px] text-text-2">{t("The first picks reach their 1-day check soon: results land here as each window closes.")}</p>}
      {H && (
        <>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {([[t("Median pick"), pct(H.all?.median), tone(H.all?.median), t("{n} picks · {d}d", { n: H.all?.n ?? 0, d: h })], [t("vs market"), pct(H.excess?.median), tone(H.excess?.median), t("over the chain's coin")],
              [t("Went up"), share(H.all?.positive), "", t("doubled {p}", { p: share(H.all?.doubled) })]] as const).map(([l, v, tn, s]) => (
              <div key={l} className="rounded-[12px] bg-card px-3 py-2">
                <div className="text-[10.5px] font-medium uppercase tracking-[0.07em] text-text-3">{l}</div>
                <div className={`num text-[17px] font-semibold ${tn}`}>{v}</div>
                <small className="block text-[11px] text-text-3">{s}</small>
              </div>
            ))}
          </div>
          <table className="mt-2 w-full rounded-[16px] bg-card text-[13.5px]">
            <thead><tr className="text-text-3"><th /><th className="py-1.5 text-right font-medium">{t("Median")}</th><th className="text-right font-medium">{t("Up")}</th><th className="pr-3 text-right font-medium">n</th></tr></thead>
            <tbody>{([["Top 10", H.top], [t("Picked"), H.all], [t("Studied"), H.studied], [t("Turned down"), H.rejected]] as const).map(([k, s]) => (
              <tr key={k}><th className="py-1 pl-3 text-left font-medium">{k}</th><td className={`num text-right ${tone(s?.median)}`}>{pct(s?.median)}</td><td className="num text-right">{share(s?.positive)}</td><td className="num pr-3 text-right">{s?.n ?? 0}</td></tr>
            ))}</tbody>
          </table>
        </>
      )}
      {(track?.picks ?? []).length > 0 && (
        <>
          <h2 className="mb-2 mt-5 text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">{t("Latest picks")}</h2>
          <ol className="rounded-[16px] bg-card p-1.5">{track!.picks!.map((c) => row(c, c.checkpoint?.days
            ? `${t("{n}d", { n: c.checkpoint.days })} ${pct(c.checkpoint.ret)}${c.checkpoint.excess != null ? ` · ${t("vs market")} ${pct(c.checkpoint.excess)}` : ""}` : `${t("picked")}${c.rank ? ` #${c.rank}` : ""} · ${t("first check pending")}`))}</ol>
        </>
      )}
      {(track?.missed ?? []).length > 0 && (
        <>
          <h2 className="mb-2 mt-5 text-[11.5px] font-medium uppercase tracking-[0.07em] text-text-3">{t("Missed")}</h2>
          <ol className="rounded-[16px] bg-card p-1.5">{track!.missed!.map((c) => row(c, `${c.decision === "rejected" ? t("turned down") : t("not picked")} · ${t("peak")} ${pct(c.hi)}${c.why ? ` · ${c.why}` : ""}`))}</ol>
        </>
      )}

      <Sheet open={edit} title={t("Edit profile")} onClose={() => setEdit(false)}>
        {p && (
          <form ref={form} onSubmit={save} className="grid gap-3 text-[14px]">
            <label className="grid gap-1">{t("Name")}<input name="display_name" maxLength={40} defaultValue={p.display_name} required className="h-11 rounded-[12px] border border-line bg-bg px-3 text-[16px]" /></label>
            <label className="grid gap-1">{t("Handle")}<input name="handle" maxLength={20} pattern="[A-Za-z0-9_]{3,20}" defaultValue={p.handle} required className="h-11 rounded-[12px] border border-line bg-bg px-3 text-[16px]" /></label>
            <label className="grid gap-1">Bio<textarea name="bio" maxLength={160} rows={3} defaultValue={p.bio ?? ""} className="rounded-[12px] border border-line bg-bg p-3 text-[16px]" /></label>
            {err && <p className="text-down">{err}</p>}
            <div className="flex gap-2"><button type="button" onClick={() => setEdit(false)} className="h-11 flex-1 rounded-full bg-pill font-semibold">{t("Cancel")}</button>
              <button type="submit" className="h-11 flex-1 rounded-full bg-ink font-semibold text-on-ink">{t("Save")}</button></div>
          </form>
        )}
      </Sheet>
    </>
  );
}
