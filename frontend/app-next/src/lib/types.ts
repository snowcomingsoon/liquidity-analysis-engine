export type Usage = { vol_7d_avg?: number; vol_24h?: number; holders?: number };

export type Gem = {
  chain: string;
  token_address: string;
  pair_address?: string;
  pair_url?: string;
  symbol: string;
  name?: string;
  image?: string;
  score?: number;
  market_cap?: number;
  fdv?: number;
  liquidity_usd?: number;
  change_24h?: number;
  launched_at?: number;
  usage?: Usage;
  early?: boolean;
  hidden?: boolean;
  in?: boolean;
  arena_rank?: number;
  arena_label?: string;
};

export type Arena = { key: string; label: string; heat: number; size: number; median: number; entries: Gem[] };

export type Top = { entries: Gem[]; early: Gem[]; arenas: Arena[] };

export type Project = {
  chain: string; token: string; symbol?: string; name?: string; image?: string; status: string;
  score?: number; mcap?: number; liq?: number; website?: string; github?: string; why?: string;
  overall?: { layer?: string };
};

export type ProjectStats = {
  total: number; in_band: number; band?: [number, number]; band_waiting?: number;
  by_status?: Record<string, number>; band_by_status?: Record<string, number>;
  by_chain?: Record<string, number>; by_layer?: Record<string, number>;
  top_rejections?: { why: string }[];
};

export type Projects = { items: Project[]; total: number; stats?: ProjectStats };

export type Narrative = { key: string; label?: string; projects?: number };

export type Candle = { time: number; open: number; high: number; low: number; close: number };

/* The dossier is wide and grows on the server: the fields the page reads are
   typed, the facts behind the pillars stay loose (leaderboard.js reads them as is). */
type Loose = Record<string, any>;
export type Point = string | { text?: string; evidence?: string; note?: string };
export type Pillar = { score?: number; facts?: Loose; flags?: string[] };
export type Judge = { score?: number; verdict?: string; strengths?: string[]; problems?: string[]; admit_reason?: string | null;
  x?: Loose; tg?: Loose; tg_events?: Loose[]; dc?: Loose; drift?: Loose };
export type Entry = Gem & {
  on_board?: boolean; top_rank?: number | null; rank?: number; why?: string; summary?: string; stage?: string; honor?: string;
  pillars?: Record<string, Pillar>; traction?: { traction?: number; value?: number; facts?: Loose; reasons?: string[] } | null;
  judge?: Judge | null; review?: { keep?: boolean; reason?: string } | null;
  code?: { complexity?: number; innovation?: number; fork_of?: string | null; summary?: string; strengths?: string[]; concerns?: string[] } | null;
  similarity?: { score?: number; traits?: { label: string; got: number }[] }; benchmark?: boolean; closed_source?: boolean;
  scan_url?: string; description?: string; website?: string; github?: string; socials?: { type: string; url: string }[];
};
export type Deep = { verdict?: string; score?: number; keep?: boolean; unsupported?: boolean; reason?: string; strengths?: Point[]; problems?: Point[];
  claims?: { status: string; text?: string; evidence?: string; note?: string }[]; cleared?: number; unverified?: number; confirmed?: number; at?: number; auto?: boolean };
export type RecheckProgress = { running?: boolean; started?: number; steps?: { label: string; detail?: string }[];
  log?: { n: number; src: string; text: string; code?: number | null }[] };
export type TokenDossier = { entry: Entry | null; deep?: Deep | null; deep_wait_s?: number | null; deep_progress?: RecheckProgress | null };
export type Job = { state: string; result?: { deep?: Deep }; detail?: { wait_s?: number }; error?: string };
