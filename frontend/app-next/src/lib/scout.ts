// The Scout's read-only projection of the activity feed and the journey's
// hash chain (static/onchain/agent-map-model.js), the parts the phone uses.

export type AgentItem = { t: number; kind: string; text: string; outcome?: string; steps?: string[]; chain?: string; token?: string; symbol?: string };
export type AgentInfo = {
  active?: boolean; working?: boolean; items?: AgentItem[]; watching?: number; today?: Record<string, number>; tokens?: number;
  spent_usd?: number; cap_usd?: number; done?: Record<string, number>; distinct?: Record<string, number>;
  progress?: { key: string; label: string; done?: number; total?: number }[];
  research?: { ai?: boolean; running?: boolean; last_run?: number; next_run?: number; examined?: number; entered?: number };
};
export type JourneyStep = { node: string; t: number; source: string; text?: string; record: string; id: string; link: string };
export type Journey = { symbol?: string; chain: string; token: string; genesis: string; head: string; steps: JourneyStep[]; limits?: string };
export type JourneyAnswer = { journey?: Journey | null; matches?: { chain: string; token: string; symbol?: string; status?: string }[] };

export const NODE_LABEL: Record<string, string> = {
  scan: "Discovery", study: "Project study", research: "Research / judge", code: "Code review", narratives: "Narratives",
  consistency: "Consistency", memory: "Evidence / reuse", decision: "Decision", backtest: "Backtests", outcomes: "Observed outcomes",
  agent: "Agent objectives", other: "Other activity",
};
export const SOURCE: Record<string, string> = {
  "projects_db.first_seen": "Project database", "projects_db.verdict": "Project database", "projects_db.standing": "Project database",
  agent_activity: "Agent activity", deepseek_call: "DeepSeek call journal", strategy_lab: "Strategy lab",
  discovery: "Discovery log", "leaderboard.found": "Research queue", "leaderboard.pillar": "Pillar check",
  "leaderboard.rank": "Ranking", judge: "Judge cache", "research.dossier": "Research cache", "research.reading": "Research cache",
  code_review: "Code review cache", "gem_track.entry": "Top tracker", "gem_track.return": "Top tracker",
  "outcomes.journal": "Outcome journal", "outcomes.archive": "Outcome archive", alert_track: "Alert tracker",
};

type Event = AgentItem & { key: string | null };
const projectKey = (e: AgentItem) => (e.chain && e.token ? JSON.stringify([e.chain, e.token]) : null);
function events(items?: AgentItem[]): Event[] {
  if (!Array.isArray(items)) return [];
  return items.filter((e) => e && Number.isFinite(e.t) && e.t >= 0).map((e) => ({ ...e, key: projectKey(e) }))
    .sort((a, b) => b.t - a.t).slice(0, 300);
}

/** Most recent event that names a project: what the engine is looking at now. */
export function liveProject(items?: AgentItem[], now = Date.now()) {
  const e = events(items).find((x) => x.key);
  if (!e) return null;
  return { key: e.key!, chain: e.chain!, token: e.token!, symbol: e.symbol || e.token!.slice(0, 12), ageS: Math.max(0, Math.round(now / 1000 - e.t)) };
}

/** Up to `limit` most recently active projects. */
export function recentProjects(items?: AgentItem[], limit = 8) {
  const out = new Map<string, { key: string; chain: string; token: string; symbol: string }>();
  for (const e of events(items)) {
    if (!e.key || out.has(e.key)) continue;
    out.set(e.key, { key: e.key, chain: e.chain!, token: e.token!, symbol: e.symbol || e.token!.slice(0, 6) });
    if (out.size >= limit) break;
  }
  return [...out.values()];
}

export async function sha256Hex(text: string) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Recompute the chain: id = sha256(record), link = sha256(prev + id). The first broken step, if any. */
export async function verifyChain(j: Journey): Promise<{ ok: boolean; brokenAt: number | null }> {
  let link = j?.genesis;
  const steps = Array.isArray(j?.steps) ? j.steps : [];
  if (typeof link !== "string") return { ok: false, brokenAt: 0 };
  for (let i = 0; i < steps.length; i++) {
    const s = steps[i];
    if (typeof s?.record !== "string" || await sha256Hex(s.record) !== s.id) return { ok: false, brokenAt: i };
    link = await sha256Hex(link + s.id);
    if (link !== s.link) return { ok: false, brokenAt: i };
  }
  return { ok: link === j.head, brokenAt: link === j.head ? null : steps.length };
}

export const SPEEDS: [number, string][] = [[1, "Real time"], [60, "1 s = 1 min"], [600, "1 s = 10 min"], [3600, "1 s = 1 h"], [86400, "1 s = 1 day"]];

/** Replay times proportional to the real gaps: `speed` real seconds per screen second; long pauses capped and marked. */
export function replaySchedule(steps: { t: number }[], speed: number, capMs = 3000, minMs = 80) {
  let at = 0;
  return steps.map((s, i) => {
    const gapS = i ? Math.max(0, s.t - steps[i - 1].t) : 0;
    const want = i ? (gapS / speed) * 1000 : 0;
    const capped = want > capMs;
    at += i ? Math.max(minMs, capped ? capMs : want) : 0;
    return { at, gapS, capped };
  });
}

/** Slowest speed whose replay fits the budget with at most a quarter of the pauses shortened. */
export function autoSpeed(steps: { t: number }[], budgetMs = 60000) {
  const gaps = Math.max(0, steps.length - 1);
  for (const [speed] of SPEEDS) {
    const plan = replaySchedule(steps, speed);
    if (!plan.length || (plan[plan.length - 1].at <= budgetMs && plan.filter((p) => p.capped).length <= Math.ceil(gaps / 4))) return speed;
  }
  return SPEEDS[SPEEDS.length - 1][0];
}
