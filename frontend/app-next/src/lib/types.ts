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
