import { useSyncExternalStore } from "react";
import { IT } from "./it";

// The app's language (Lorenzo 22/10: "traduci tutta l'app in italiano",
// then "metti poi tastino per selezionare EN o IT"). The English text is
// the key; lib/it.ts holds the Italian. A missing key shows the English.
export type Lang = "it" | "en";
const KEY = "lae:lang";

function read(): Lang {
  try { return localStorage.getItem(KEY) === "en" ? "en" : "it"; } catch { return "it"; }
}
let lang: Lang = read();
const subs = new Set<() => void>();
document.documentElement.lang = lang;

export const getLang = () => lang;
export const useLang = () => useSyncExternalStore((f) => { subs.add(f); return () => { subs.delete(f); }; }, getLang);
export function setLang(next: Lang) {
  lang = next;
  document.documentElement.lang = next;
  try { localStorage.setItem(KEY, next); } catch { /* private mode */ }
  subs.forEach((f) => f());
}

/** `t("{n} projects", { n: 4 })`: the text in the chosen language, with its values. */
export function t(en: string, v?: Record<string, string | number>): string {
  const s = lang === "it" ? IT[en] ?? en : en;
  return v ? s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? String(v[k]) : m)) : s;
}

/** Numbers in the reader's language: 1,234 or 1.234. */
export const locale = () => (lang === "it" ? "it-IT" : "en-GB");
