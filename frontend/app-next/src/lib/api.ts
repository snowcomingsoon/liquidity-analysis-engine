import type { Narrative, Projects, Top } from "./types";

// The same contract as static/onchain/api.js: X-Device on every call,
// identical GETs in flight shared, errors carry the server's detail.
export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) { super(message); this.status = status; }
}

export const device = (() => {
  try {
    let d = localStorage.getItem("lae.device");
    if (!d) { d = crypto.randomUUID().replace(/-/g, ""); localStorage.setItem("lae.device", d); }
    return d;
  } catch { return ""; }
})();

const inFlight = new Map<string, Promise<unknown>>();

async function send<T>(path: string, method = "GET", body?: unknown, timeoutMs = 8000): Promise<T> {
  let r: Response;
  try {
    r = await fetch(path, {
      method,
      headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...(device ? { "X-Device": device } : {}) },
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (e) {
    throw new ApiError((e as Error).name === "TimeoutError" ? "network is slow" : "network unreachable");
  }
  let payload: { detail?: unknown } | null = null;
  try { payload = await r.json(); } catch { /* 204 or not JSON */ }
  if (r.status === 401) location.href = "/onchain-app.html";
  if (!r.ok) throw new ApiError(typeof payload?.detail === "string" ? payload.detail : `error ${r.status}`, r.status);
  return payload as T;
}

function get<T>(path: string, timeoutMs?: number): Promise<T> {
  let p = inFlight.get(path) as Promise<T> | undefined;
  if (!p) {
    p = send<T>(path, "GET", undefined, timeoutMs).finally(() => inFlight.delete(path));
    inFlight.set(path, p);
  }
  return p;
}

function post<T>(path: string, body: unknown): Promise<T> {
  inFlight.clear();
  return send<T>(path, "POST", body);
}

export const getTop = (n: number, keys: string[] = []) =>
  get<Top & { p4p?: unknown }>(`/api/onchain/top?n=${n}${keys.length ? `&narrative=${encodeURIComponent(keys.join(","))}` : ""}`);
export const getProjects = (params: Record<string, string | number>) =>
  get<Projects>(`/api/onchain/projects?${new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]))}`);
export const getNarrativeCoverage = () => get<{ items: Narrative[] }>("/api/onchain/narratives/coverage");
export const getHidden = () => get<{ hidden: string[] }>("/api/profile/hidden");
export const setHidden = (body: { chain: string; token: string; hide: boolean }) => post<{ hidden: string[] }>("/api/profile/hidden", body);
