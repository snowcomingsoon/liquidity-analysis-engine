import type { Candle, Deep, Job, Narrative, Projects, QualityLists, RecheckProgress, Top, TokenDossier } from "./types";
import type { AgentInfo, AgentItem, JourneyAnswer } from "./scout";

// The same contract as static/onchain/api.js: X-Device on every call,
// identical GETs in flight shared, errors carry the server's detail.
export class ApiError extends Error {
  status?: number;
  detail?: unknown;
  constructor(message: string, status?: number, detail?: unknown) { super(message); this.status = status; this.detail = detail; }
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
  if (!r.ok) throw new ApiError(typeof payload?.detail === "string" ? payload.detail : `error ${r.status}`, r.status, payload?.detail);
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

const tq = (chain: string, token: string) => `chain=${encodeURIComponent(chain)}&token=${encodeURIComponent(token)}`;
// The token page's dossier (main.py onchain_token): board entry or database row, and the deep re-check.
export const getToken = (chain: string, token: string) => get<TokenDossier>(`/api/onchain/token?${tq(chain, token)}`);
export const recheckProgress = (chain: string, token: string) =>
  get<{ progress?: RecheckProgress | null }>(`/api/onchain/token/recheck/progress?${tq(chain, token)}`);
// The re-check as a job (bg.js): {job} at once, the result by poll.
export const recheckJob = (chain: string, token: string, body: { view: string; label: string }) =>
  send<{ job?: string; deep?: Deep }>(`/api/onchain/token/recheck?${tq(chain, token)}`, "POST", body, 20000);
export const getJob = (id: string) => send<Job>(`/api/jobs/${encodeURIComponent(id)}?visible=1`, "GET", undefined, 10000);
export const getTokenChart = (chain: string, pool: string, symbol: string, interval: string, peek = false) =>
  get<{ candles?: Candle[] }>(`/api/onchain/chart?${new URLSearchParams({ chain, pool, symbol, interval, ...(peek ? { peek: "1" } : {}) })}`, 20000);

// Quality (quality.js): one account's list; 404 for the others.
export const getQuality = () => get<QualityLists>("/api/onchain/quality", 20000);
export const decideQuality = (chain: string, token: string, action: "accept" | "discard" | "reset") =>
  post<{ state?: string }>("/api/onchain/quality", { chain, token, action });

// Scout (agent.js, agent-journey.js).
export const getAgent = () => get<AgentInfo>("/api/agent");
export const getAgentLog = (before?: number) => get<{ items?: AgentItem[] }>(`/api/agent/log?limit=60${before ? `&before=${before}` : ""}`);
export const getAgentJourney = ({ q = "", chain = "", token = "" }: { q?: string; chain?: string; token?: string }) =>
  get<JourneyAnswer>(`/api/agent/journey?q=${encodeURIComponent(q)}&chain=${encodeURIComponent(chain)}&token=${encodeURIComponent(token)}`, 20000);
// Coordinated sells (sells.js): whitekobra and the /app accounts; 404 for the others.
export type SellsReport = {
  chain: string; token: string; symbol?: string; updated_at?: number | null;
  risk?: { score?: number | null; reasons?: string[] };
  clusters: { id: string; wallets: { address: string; share?: number | null }[]; share?: number | null; links?: string[]; risk?: number | null; edges?: [string, string][] }[];
  events: { id: string; cluster: string; ts: number; window_s?: number | null; wallets: number; share_sold?: number | null; sellers?: string[] }[];
};
export type ClusterCheck = { state: "unsupported" | "running" | "queued" | "failed" | "built" | "none"; place?: number; clusters?: number };
type CheckRaw = { position?: number | null; busy?: boolean; built_at?: number | null; clusters?: number; error?: string | null };
// GET /check (wallet_clusters): its fields read as one state for the token page.
export const getClusterCheck = (chain: string, token: string): Promise<ClusterCheck> =>
  get<CheckRaw>(`/api/onchain/coordinated-sells/check?chain=${encodeURIComponent(chain)}&token=${encodeURIComponent(token)}`, 15000).then((r) =>
    r.busy && r.position === 0 ? { state: "running" }
      : r.position != null ? { state: "queued", place: r.position }
      : r.built_at ? { state: "built", clusters: r.clusters ?? 0 }
      : r.error ? { state: "failed" } : { state: "none" },
  (e: { status?: number }) => { if (e?.status === 400) return { state: "unsupported" } as ClusterCheck; throw e; });
// A cluster check on demand for a pasted address (wallet_clusters, first in line).
export const askClusterCheck = (chain: string, token: string) =>
  post<{ queued?: boolean; position?: number | null; error?: string | null; manual_left?: number }>("/api/onchain/coordinated-sells/check", { chain, token });
export const getCoordinatedSells = () => get<{ sample?: boolean; reports?: SellsReport[] }>("/api/onchain/coordinated-sells", 20000);

// The scanner (sheets.js openScan): a server job streamed as NDJSON; if the
// phone drops the stream the job goes on and its result is collected by id.
export type ScanEvent = { plan?: string[]; step?: string; state?: string; detail?: string; reconnecting?: boolean };
export async function streamScan(query: string, onEvent: (ev: ScanEvent) => void): Promise<Record<string, unknown>> {
  let r: Response;
  try {
    r = await fetch("/api/onchain/scan/stream", {
      method: "POST", headers: { "Content-Type": "application/json", ...(device ? { "X-Device": device } : {}) },
      body: JSON.stringify({ query, view: `${location.pathname}#search` }), signal: AbortSignal.timeout(300000),
    });
  } catch (e) { throw new ApiError((e as Error).name === "TimeoutError" ? "network is slow" : "network unreachable"); }
  if (!r.ok || !r.body) throw new ApiError(`scan failed (${r.status})`);
  const reader = r.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = "", result: Record<string, unknown> | null = null, id: string | null = null;
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += value;
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim();
        buf = buf.slice(i + 1);
        if (!line) continue;
        const ev = JSON.parse(line);
        if ("result" in ev) result = ev.result;
        else if ("id" in ev) id = ev.id;
        else if (!("ping" in ev)) onEvent(ev);
      }
    }
  } catch { if (!id) throw new ApiError("connection lost, run the scan again"); }
  if (result) return result;
  if (!id) throw new ApiError("scan interrupted");
  onEvent({ reconnecting: true });
  for (let k = 0; k < 90; k++) {
    await new Promise((res) => setTimeout(res, 2000));
    let d: { done?: boolean; result?: Record<string, unknown> };
    try { d = await send(`/api/onchain/scan/result/${encodeURIComponent(id)}`, "GET", undefined, 10000); }
    catch (e) { if (String((e as Error).message).startsWith("scan not found")) throw new ApiError("the server restarted during the scan, run it again"); continue; }
    if (d.done && d.result) return d.result;
  }
  throw new ApiError("scan is taking too long, try again");
}
export const addScanned = (chain: string, token: string) => post<{ error?: string }>("/api/onchain/scan/add", { chain, token });

// Profile (profile.js) and the picks' track record (track.js).
export type Profile = { display_name: string; handle: string; bio?: string; avatar_url?: string; joined?: number };
export const getProfile = () => get<{ profile: Profile }>("/api/profile", 25000);
export const updateProfile = (body: { display_name: string; handle: string; bio: string }) => send<{ profile: Profile }>("/api/profile", "PATCH", body);
export const uploadAvatar = (data_url: string) => send<{ profile: Profile }>("/api/profile/avatar", "POST", { data_url }, 30000);
export type TrackStat = { n?: number; median?: number | null; positive?: number | null; doubled?: number | null };
export type TrackPick = { chain: string; token_address: string; symbol: string; score?: number; at: number; rank?: number; decision?: string;
  now?: number | null; hi?: number | null; why?: string; checkpoint?: { days?: number; ret?: number; excess?: number | null } };
export type Track = { stats?: { horizons?: { days: number; all?: TrackStat; top?: TrackStat; studied?: TrackStat; rejected?: TrackStat; excess?: TrackStat }[] };
  picks?: TrackPick[]; missed?: TrackPick[] };
export const getTrack = () => get<Track>("/api/onchain/track");

// The Telegram alerts (alert_track.py), the bell of alerts.js.
export type AlertItem = { symbol: string; name?: string; chain: string; token_address: string; image?: string; at: number; cap0?: number; now?: number | null; gone?: boolean };
export const getAlerts = (kind: "meme" | "gem") => get<{ items?: AlertItem[] }>(`/api/onchain/alerts/${kind}`);
export const getPushKey = () => get<{ key: string }>("/api/push/key");
export const pushSubscribe = (subscription: PushSubscriptionJSON) => post<unknown>("/api/push/subscribe", { subscription });
