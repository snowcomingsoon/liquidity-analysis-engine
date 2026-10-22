import { useSyncExternalStore } from "react";
import * as api from "./api";

// Small shared stores, the React side of hidden.js, narrative_pick.js and
// the gem sort in top.js. Same localStorage keys, so a choice made in one
// app holds in the other.
function store<T>(initial: T) {
  let value = initial;
  const subs = new Set<() => void>();
  return {
    get: () => value,
    set(next: T) { value = next; subs.forEach((f) => f()); },
    subscribe(f: () => void) { subs.add(f); return () => { subs.delete(f); }; },
  };
}
const use = <T,>(s: ReturnType<typeof store<T>>) => useSyncExternalStore(s.subscribe, s.get);

function readJson<T>(key: string, fallback: T): T {
  try { const v = JSON.parse(localStorage.getItem(key) ?? "null"); return v ?? fallback; } catch { return fallback; }
}
function writeJson(key: string, v: unknown) {
  try { localStorage.setItem(key, JSON.stringify(v)); } catch { /* private mode */ }
}

// --- hidden tokens (per account, on the server) -------------------------
const hidden = store<Set<string>>(new Set());
export const useHidden = () => use(hidden);
export const isHiddenIn = (set: Set<string>, chain: string, token: string) => set.has(`${chain}:${token}`);
export function loadHidden() {
  api.getHidden().then((r) => hidden.set(new Set(r?.hidden ?? []))).catch(() => { /* signed out: nothing hidden */ });
}
export async function setTokenHidden(chain: string, token: string, hide: boolean) {
  const r = await api.setHidden({ chain, token, hide });
  hidden.set(new Set(r?.hidden ?? []));
}

// --- gem sort, shared by every gem list (top.js) -------------------------
export type SortBy = { by: "score" | "cap" | "new"; desc: boolean };
const SORT_KEY = "lae:gem-sort";
const sort = store<SortBy>({ by: "score", desc: true, ...readJson<Partial<SortBy>>(SORT_KEY, {}) });
export const useSort = () => use(sort);
const DEFAULT_DESC = { score: true, cap: false, new: true };   // best, smallest, newest first
export function pickSort(by: SortBy["by"]) {
  const cur = sort.get();
  const next = by === cur.by ? { by, desc: !cur.desc } : { by, desc: DEFAULT_DESC[by] };
  writeJson(SORT_KEY, next);
  sort.set(next);
}
export function sortRows<T extends { score?: number; market_cap?: number; launched_at?: number }>(list: T[], s: SortBy): T[] {
  const val = (e: T) => (s.by === "cap" ? e.market_cap : s.by === "new" ? e.launched_at : e.score);
  const sign = s.desc ? -1 : 1;
  return [...list].sort((a, b) => {
    const x = val(a), y = val(b);
    if (x == null || y == null) return Number(x == null) - Number(y == null);   // no value: last either way
    return sign * (x - y);
  });
}

// --- narratives picked as a filter (narrative_pick.js) -------------------
const NARR_KEY = "lae:narr";
const narr = store<string[]>(readJson<string[]>(NARR_KEY, []).filter((k) => typeof k === "string" && k));
export const useNarratives = () => use(narr);
export function setNarratives(keys: string[]) {
  const list = [...new Set(keys)];
  writeJson(NARR_KEY, list);
  narr.set(list);
}
let coverageP: Promise<{ key: string; label?: string; projects?: number }[]> | null = null;
export function coverage() {
  coverageP ??= api.getNarrativeCoverage().then((d) => d?.items ?? []).catch(() => { coverageP = null; return []; });
  return coverageP;
}
