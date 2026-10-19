"""Scan H24 dei progetti seri, separato dal radar.

Lorenzo (24/09): "per quanto riguarda i progetti seri voglio che anche li'
ci sia uno scan H24 che poi finisce nella leaderboard [...] vedo che hai
trovato soltanto drag perche' te l'ho detto io [...] devi trovarli, ce ne
sono tanti su Robinhood Chain e su Solana [...] low cap e micro cap".

Perche' prima non usciva niente: la classifica leggeva solo cio' che il
radar aveva salvato, e il radar guarda pool nuovi e di tendenza, cioe'
quasi solo meme coin. Un progetto con codice vero raramente e' nato ieri o
e' fra i piu' scambiati dell'ora.

Qui due fonti diverse, pensate per i progetti e non per i pool:

- CoinGecko, categorie "solana-ecosystem", "robinhood-ecosystem", "base-ecosystem" e "ethereum-ecosystem", la
  fascia di capitalizzazione fra CAP_MIN e CAP_MAX. Per ogni moneta la
  scheda dice indirizzo del contratto, sito, categorie e soprattutto il
  repository GitHub: senza GitHub non si va avanti. Le categorie "Meme" si
  scartano subito.
- DexScreener, profili token appena compilati: chi paga per pubblicare
  sito e social su DexScreener. Si tengono quelli con un sito proprio e un
  nome non da meme; il GitHub lo cerca poi l'analisi nell'HTML del sito.

Quello che passa entra in classifica (`leaderboard.add`) e da li' fa la
stessa analisi profonda di tutti. CoinGecko gratuito regge poche richieste
al minuto: una ogni CG_GAP_S secondi, schede ricontrollate ogni settimana.
"""
from __future__ import annotations

import asyncio
import calendar
import json
import logging
import re
import time
from datetime import datetime
from typing import Callable

import httpx

from app.sniper.quality import _looks_like_meme
from app.trading.onchain import legit, narratives, projects_db, storage, traction
from app.atomic_write import write_text_atomic

logger = logging.getLogger(__name__)

_STORE_FILE = storage.data_file("onchain_discovery.json")

COINGECKO = "https://api.coingecko.com/api/v3"
DEX_PROFILES = "https://api.dexscreener.com/token-profiles/latest/v1"
# categoria CoinGecko e pagine da 250 (ordinate per cap decrescente) che
# coprono la fascia CAP_MIN-CAP_MAX
CG_CATEGORIES = {"solana": ("solana-ecosystem", range(3, 9)), "robinhood": ("robinhood-ecosystem", range(1, 5)),
                 "base": ("base-ecosystem", range(1, 7)), "ethereum": ("ethereum-ecosystem", range(1, 9)),
                 "arc": ("arc-ecosystem", range(1, 2))}
CG_PLATFORMS = {"solana": ("solana",), "robinhood": ("robinhood",), "base": ("base",), "ethereum": ("ethereum",),
                "arc": ("arc",)}
# Lorenzo (28/09): "magari dobbiamo alzare un po' i limiti di market cap [...]
# anche i progetti un po' piu' datati ha senso metterceli"
CAP_MIN = 10_000             # early gems start under $50k (leaderboard.EARLY_CAP_USD)
NARRATIVE_PAGES = 12
CAP_MAX = 10_000_000             # Lorenzo 28/09: gems are small caps, $10M at most
# azioni tokenizzate, stablecoin, token avvolti: non sono progetti
_NOT_PROJECT = ("meme", "stock", "stablecoin", "wrapped", "bridged", "etf")
CG_GAP_S = 12                # 5 richieste al minuto: sotto il limite gratuito
CG_SWEEP_S = 6 * 3600        # un giro completo delle categorie
CG_DETAIL_TTL_S = 7 * 86400
CG_DB_DETAILS = 20           # CoinGecko pages taken from the database per empty queue
PROFILES_POLL_S = 120
PROFILES_PER_POLL = 12

_state = {"cg_queue": [], "cg_last_sweep": 0.0, "cg_next_at": 0.0, "profiles_at": 0.0, "jup_at": 0.0, "jup_last": 0,
          "gh_queue": [], "gh_query": 0, "gh_search_at": 0.0, "gh_repo_at": 0.0,
          "found": 0, "skipped": 0, "running": False}
_chain_ids: dict[str, set[str]] = {}   # CoinGecko ids with a contract on our chains
_seen: dict[str, dict] = {}   # "cg:<chain>:<id>" o "dx:<chain>:<token>" -> {at, ok, why}


def _load() -> None:
    try:
        raw = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    # rules 2: projects without public GitHub are no longer banned; look again
    if isinstance(raw, dict) and int(raw.get("rules") or 1) >= 2:
        _seen.update({k: v for k, v in (raw.get("seen") or {}).items() if isinstance(v, dict)})
        _state["cg_last_sweep"] = float(raw.get("cg_last_sweep") or 0)


def _save() -> None:
    try:
        write_text_atomic(_STORE_FILE, json.dumps({"seen": _seen, "cg_last_sweep": _state["cg_last_sweep"], "rules": 2},
                                          ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def reset_for_tests() -> None:
    _seen.clear()
    _chain_ids.clear()
    _state.update(cg_queue=[], cg_last_sweep=0.0, cg_next_at=0.0, profiles_at=0.0, gh_queue=[], gh_query=0,
                  gh_search_at=0.0, gh_repo_at=0.0, gt_at=0.0, gt_turn=-1, found=0, skipped=0, running=False)


def status() -> dict:
    return {"queue": len(_state["cg_queue"]) + len(_state["gh_queue"]), "found": _state["found"], "skipped": _state["skipped"],
            "last_sweep": _state["cg_last_sweep"] or None, "seen": len(_seen), "jupiter": _state["jup_last"]}


def _note(key: str, ok: bool, why: str, now: float) -> None:
    _seen[key] = {"at": now, "ok": ok, "why": why}
    _state["found" if ok else "skipped"] += 1


# ------------------------------------------------------------- CoinGecko

def chain_index(rows: list[dict]) -> dict[str, set[str]]:
    """From /coins/list?include_platform=true: which ids live on which chain."""
    out: dict[str, set[str]] = {c: set() for c in CG_PLATFORMS}
    for r in rows or []:
        plats = r.get("platforms") or {}
        for chain, keys in CG_PLATFORMS.items():
            if any(plats.get(k) for k in keys):
                out[chain].add(r.get("id"))
    return out


def universe(rows: list[dict]) -> list[dict]:
    """From /coins/list?include_platform=true: every coin with a contract on
    one of our chains, as database rows (no market yet)."""
    out = []
    for r in rows or []:
        plats = r.get("platforms") or {}
        for chain, keys in CG_PLATFORMS.items():
            token = next((plats[k] for k in keys if plats.get(k)), None)
            if token and r.get("id"):
                out.append({"chain": chain, "token_address": token, "cg_id": r["id"],
                            "symbol": (r.get("symbol") or "").upper(), "name": r.get("name") or ""})
    return out


def market_candidates(chain: str, rows: list[dict]) -> list[dict]:
    """Dalla lista /coins/markets: le monete nella fascia di cap, nome non da meme."""
    out = []
    for r in rows or []:
        cap = float(r.get("market_cap") or 0)
        if not (CAP_MIN <= cap <= CAP_MAX):
            continue
        if _looks_like_meme(r.get("symbol") or "", r.get("name") or ""):
            continue
        out.append({"id": r.get("id"), "chain": chain, "symbol": (r.get("symbol") or "").upper(),
                    "name": r.get("name") or "", "market_cap": cap, "image": r.get("image")})
    return [x for x in out if x["id"]]


def from_coin_detail(chain: str, coin: dict, base: dict | None = None) -> tuple[dict | None, str]:
    """(voce per la classifica, perche' no). Serve: contratto sulla chain,
    niente categoria meme, sito proprio. Il GitHub, se CoinGecko non lo ha,
    lo cerca l'analisi del sito."""
    platforms = coin.get("platforms") or {}
    token = next((platforms[p] for p in CG_PLATFORMS[chain] if platforms.get(p)), None)
    if not token:
        return None, "no contract on this chain"
    cap = global_cap(coin)
    if cap and cap > CAP_MAX:
        return None, (f"global market cap ${cap:,.0f}: a large coin, not a gem"
                      " (this chain holds a bridged copy)")
    cats = [c for c in coin.get("categories") or [] if c]
    bad = next((c for c in cats if any(w in c.lower() for w in _NOT_PROJECT)), None)
    if bad:
        return None, f"category {bad}"
    links = coin.get("links") or {}
    website = legit.pick_website(links.get("homepage") or [])
    if not website:
        return None, "no own website"
    repos = [u for u in (links.get("repos_url") or {}).get("github") or [] if legit.github_targets([u])]
    socials = []
    if links.get("twitter_screen_name"):
        socials.append({"type": "twitter", "url": f"https://x.com/{links['twitter_screen_name']}"})
    if links.get("telegram_channel_identifier"):
        socials.append({"type": "telegram", "url": f"https://t.me/{links['telegram_channel_identifier']}"})
    b = base or {}
    return {
        "chain": chain, "token_address": token, "symbol": b.get("symbol") or (coin.get("symbol") or "").upper(),
        "name": b.get("name") or coin.get("name") or "", "website": website, "github": repos[0] if repos else None,
        "socials": socials, "market_cap": cap or b.get("market_cap"), "image": b.get("image"),
        "categories": cats[:6], "description": ((coin.get("description") or {}).get("en") or "")[:400],
        "launched_at": _genesis(coin.get("genesis_date")),
    }, ""


def global_cap(coin: dict) -> float | None:
    """CoinGecko's market cap for the coin as a whole, not for the one
    contract on our chain: a bridged copy holds a fraction of the supply."""
    cap = ((coin.get("market_data") or {}).get("market_cap") or {}).get("usd")
    try:
        cap = float(cap)
    except (TypeError, ValueError):
        return None
    return cap if cap > 0 else None


def _genesis(date: str | None) -> float | None:
    try:
        return time.mktime(time.strptime(date, "%Y-%m-%d")) if date else None
    except ValueError:
        return None


async def _cg_get(client: httpx.AsyncClient, path: str, params: dict | None = None):
    r = await client.get(f"{COINGECKO}{path}", params=params, timeout=15.0,
                         headers={"Accept": "application/json"})
    if r.status_code == 429:
        raise RuntimeError("CoinGecko: troppe richieste")
    r.raise_for_status()
    return r.json()


async def _cg_step(client: httpx.AsyncClient, add: Callable[[dict, str], bool], now: float) -> None:
    """Una richiesta a CoinGecko: una pagina della categoria o una scheda."""
    if now < _state["cg_next_at"]:
        return
    _state["cg_next_at"] = now + CG_GAP_S
    q = _state["cg_queue"]
    if not q:
        # Between sweeps: CoinGecko pages of coins the database has put in the
        # band (any coin on our chains, not just the "ecosystem" categories).
        q.extend(("coin", b["chain"], b) for b in projects_db.need_detail(CG_DB_DETAILS, now))
        if q:
            return
        if now - _state["cg_last_sweep"] < CG_SWEEP_S:
            return
        _state["cg_last_sweep"] = now
        # Narratives first (hotter, smaller lists), then the chain ecosystems.
        from app import profiles
        q.append(("index",))
        # Thin narratives first: a category whose narrative has fewer than 10
        # projects in the database is swept before the crowded ones.
        # Order: narratives users chose, then thin ones, then the rest.
        counts = projects_db.narrative_counts()
        wanted = profiles.wanted_narratives()
        cats = narratives.coingecko_categories(first=wanted)
        chosen = {c for c in cats if set(narratives.keys_for_category(c)) & set(wanted)}
        thin = {c for c in cats if any(n < 10 for n in
                                       (counts.get(k, 0) for k in narratives.keys_for_category(c)))}
        cats.sort(key=lambda c: 0 if c in chosen else 1 if c in thin else 2)
        q.extend(("npage", cat, 1) for cat in cats)
        q.extend(("page", chain, cat, p) for chain, (cat, pages) in CG_CATEGORIES.items() for p in pages)
        return
    job = q.pop(0)
    if job[0] == "index":
        rows = await _cg_get(client, "/coins/list", {"include_platform": "true"})
        _chain_ids.clear()
        _chain_ids.update(chain_index(rows if isinstance(rows, list) else []))
        # Every coin CoinGecko knows on our chains goes into the database: the
        # market refresh then tells which ones sit in the band.
        projects_db.upsert_many(universe(rows if isinstance(rows, list) else []), "coingecko-list", now)
        return
    if job[0] == "npage":
        _, cat, page = job
        rows = await _cg_get(client, "/coins/markets", {"vs_currency": "usd", "category": cat,
                                                       "order": "market_cap_desc", "per_page": 250,
                                                       "page": page})
        rows = rows if isinstance(rows, list) else []
        hint = narratives.keys_for_category(cat, exclusive=True)
        fresh = []
        for chain in CG_CATEGORIES:
            ids = _chain_ids.get(chain) or set()
            fresh += [("coin", chain, {**c, "narratives_hint": hint})
                      for c in market_candidates(chain, [r for r in rows if r.get("id") in ids])
                      if now - (_seen.get(f"cg:{chain}:{c['id']}") or {}).get("at", 0) >= CG_DETAIL_TTL_S]
        q[0:0] = fresh
        # sorted by cap: another page only while the band is not yet below CAP_MIN
        if len(rows) == 250 and float(rows[-1].get("market_cap") or 0) >= CAP_MIN and page < NARRATIVE_PAGES:
            q.insert(len(fresh), ("npage", cat, page + 1))
        return
    if job[0] == "page":
        _, chain, cat, page = job
        rows = await _cg_get(client, "/coins/markets", {"vs_currency": "usd", "category": cat,
                                                       "order": "market_cap_desc", "per_page": 250,
                                                       "page": page})
        fresh = [("coin", chain, c) for c in market_candidates(chain, rows if isinstance(rows, list) else [])
                 if now - (_seen.get(f"cg:{chain}:{c['id']}") or {}).get("at", 0) >= CG_DETAIL_TTL_S]
        q[0:0] = fresh          # le schede di questa pagina prima delle pagine successive
        return
    _, chain, base = job
    coin = await _cg_get(client, f"/coins/{base['id']}", {"localization": "false", "tickers": "false",
                                                         "market_data": "true", "community_data": "false",
                                                         "developer_data": "false"})
    item, why = from_coin_detail(chain, coin, base)
    projects_db.mark_detail(chain, base["id"], now, global_cap(coin))
    if item is None and why.startswith("global market cap"):
        projects_db.reject_cg(chain, base["id"], why, now)
    _note(f"cg:{chain}:{base['id']}", item is not None, why, now)
    if item:
        if "narratives_hint" in base:   # found through a narrative category (possibly a shared one: [])
            item["narratives_hint"] = list(base["narratives_hint"] or [])
        add(item, "coingecko")
    _save()


# ----------------------------------------------------------- DexScreener

def profile_candidates(profiles: list[dict]) -> list[dict]:
    out = []
    for p in profiles or []:
        chain = p.get("chainId")
        if chain not in CG_CATEGORIES or not p.get("tokenAddress"):
            continue
        links = p.get("links") or []
        website = legit.pick_website([x.get("url") or "" for x in links
                                      if (x.get("label") or x.get("type") or "").lower() in ("website", "")])
        if not website:
            continue
        desc = p.get("description") or ""
        if _looks_like_meme("", desc[:80]) or "meme" in desc.lower():
            continue
        github = next((x["url"] for x in links if "github.com" in (x.get("url") or "")), None)
        socials = [{"type": (x.get("type") or "").lower(), "url": x["url"]} for x in links
                   if x.get("type") and x.get("url")]
        out.append({"chain": chain, "token_address": p["tokenAddress"], "website": website, "github": github,
                    "socials": socials, "description": desc[:400], "image": p.get("icon")})
    return out


async def _poll_profiles(client: httpx.AsyncClient, add: Callable[[dict, str], bool], now: float) -> None:
    if now - _state["profiles_at"] < PROFILES_POLL_S:
        return
    _state["profiles_at"] = now
    r = await client.get(DEX_PROFILES, timeout=10.0)
    r.raise_for_status()
    n = 0
    for c in profile_candidates(r.json()):
        k = f"dx:{c['chain']}:{c['token_address']}"
        if k in _seen or n >= PROFILES_PER_POLL:
            continue
        n += 1
        _note(k, True, "", now)
        add(c, "dexscreener")


# ---------------------------------------------------------------- GitHub
#
# Reversed channel: start from the code. Serious small projects put their
# contract address in the README; the address both finds the token and
# proves the repository is theirs. Only the search costs GitHub API quota
# (one call every GH_SEARCH_S); READMEs come from raw.githubusercontent.

GH_QUERIES = (
    '"pump.fun" in:readme',
    '"dexscreener.com/solana" in:readme',
    '"dexscreener.com/robinhood" in:readme',
    '"robinhood chain" token in:readme',
    '"contract address" solana in:readme',
    '"CA:" solana in:readme',
    '"token" "solana" "mint address" in:readme',
    '"birdeye.so/token" in:readme',
    '"robinhood chain" in:readme,description',
) + (
    # Named primitives (study 002 §5): projects building on checkable
    # standards. A repository still becomes a candidate only if its README
    # carries a token address, so these widen the net without lowering it.
    'x402 agent', '"ERC-8004"', '"MCP server" onchain', 'A2A agent protocol',
    'EAS attestation', 'Turnkey wallet privacy', 'Umbra stealth',
    'LayerZero prediction market', 'Polymarket vault', '"Lean 4" zkVM',
    'STARK proof capability', 'treasury rebalancing agent',
)
GH_SEARCH_S = 60
GH_REPO_S = 6
GH_FRESH_DAYS = 120
GH_QUEUE_MAX = 300
DEX_TOKENS = "https://api.dexscreener.com/tokens/v1/{chain}/{addresses}"
_SOL_ADDR = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{32,44}(?![1-9A-HJ-NP-Za-km-z])")
_EVM_ADDR = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
# Program ids and famous mints: in many READMEs, never a project's own token.
_KNOWN = {
    "So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb", "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
    "11111111111111111111111111111111", "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
    "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s", "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
    "0x0000000000000000000000000000000000000000",
}


def readme_addresses(text: str) -> dict[str, list[str]]:
    """Contract addresses in a README, by chain family, in order of appearance."""
    sol, evm = [], []
    for m in _SOL_ADDR.findall(_EVM_ADDR.sub(" ", text or "")):
        # a base58 word with no digit and no mixed case is a word, not a key
        if m not in _KNOWN and m not in sol and any(c.isdigit() for c in m) and not m.islower():
            sol.append(m)
    for m in _EVM_ADDR.findall(text or ""):
        if m not in _KNOWN and m.lower() not in {x.lower() for x in evm}:
            evm.append(m)
    # EVM addresses look the same everywhere: DexScreener says which chain has the pool.
    return {"solana": sol[:10], "robinhood": evm[:10], "base": evm[:10], "ethereum": evm[:10], "arc": evm[:10]}


def search_candidates(items: list[dict], now: float) -> list[dict]:
    """Repositories worth reading: own code, pushed recently, not forks."""
    out = []
    for r in items or []:
        full = r.get("full_name")
        if not full or r.get("fork") or r.get("archived") or not r.get("size"):
            continue
        pushed = _iso(r.get("pushed_at"))
        if pushed and now - pushed > GH_FRESH_DAYS * 86400:
            continue
        if f"gh:{full}" in _seen:
            continue
        out.append({"full_name": full, "html_url": r.get("html_url") or f"https://github.com/{full}",
                    "homepage": r.get("homepage") or "", "default_branch": r.get("default_branch") or "HEAD"})
    return out


def _iso(s: str | None) -> float | None:
    try:
        return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) if s else None
    except ValueError:
        return None


def token_from_pairs(chain: str, pairs: list[dict], repo: dict) -> tuple[dict | None, str]:
    """The README's token, from DexScreener: the most liquid pool, cap in band."""
    best = None
    for p in pairs or []:
        if p.get("chainId") != chain:
            continue
        liq = float((p.get("liquidity") or {}).get("usd") or 0)
        if best is None or liq > float((best.get("liquidity") or {}).get("usd") or 0):
            best = p
    if best is None:
        return None, "no pool"
    base = best.get("baseToken") or {}
    cap = float(best.get("marketCap") or best.get("fdv") or 0)
    if not (CAP_MIN <= cap <= CAP_MAX):
        return None, f"cap ${cap / 1e6:.2f}M"
    if _looks_like_meme(base.get("symbol") or "", base.get("name") or ""):
        return None, "meme name"
    links = legit.links_from_dexscreener(best)
    website = legit.pick_website(links["websites"] + [repo.get("homepage") or ""])
    return {
        "chain": chain, "token_address": base.get("address"), "pair_address": best.get("pairAddress") or "",
        "symbol": base.get("symbol") or "?", "name": base.get("name") or "", "website": website,
        "github": repo["html_url"], "github_verified": True, "socials": links["socials"],
        "market_cap": cap, "liquidity_usd": float((best.get("liquidity") or {}).get("usd") or 0),
        "launched_at": (best.get("pairCreatedAt") or 0) / 1000 or None, "image": (best.get("info") or {}).get("imageUrl"),
        "pair_url": best.get("url"),
    }, ""


async def _gh_search(client: httpx.AsyncClient, now: float) -> None:
    if now - _state["gh_search_at"] < GH_SEARCH_S or len(_state["gh_queue"]) >= GH_QUEUE_MAX:
        return
    _state["gh_search_at"] = now
    for k in [k for k, v in _seen.items() if now - v.get("at", now) > 30 * 86400]:
        del _seen[k]
    from app import profiles
    queries = GH_QUERIES + tuple(narratives.github_queries(first=profiles.wanted_narratives()))
    q = queries[_state["gh_query"] % len(queries)]
    _state["gh_query"] += 1
    since = time.strftime("%Y-%m-%d", time.gmtime(now - GH_FRESH_DAYS * 86400))
    r = await legit.gh_get(client, f"{legit.GITHUB_API}/search/repositories",
                         params={"q": f"{q} fork:false pushed:>{since}", "sort": "updated", "per_page": 50},
                         headers=legit._gh_headers(), timeout=10.0)
    if r.status_code != 200:
        raise RuntimeError(f"GitHub search {r.status_code}")
    queued = {j["full_name"] for j in _state["gh_queue"]}
    _state["gh_queue"].extend(c for c in search_candidates(r.json().get("items") or [], now)
                              if c["full_name"] not in queued)


async def _gh_repo(client: httpx.AsyncClient, add: Callable[[dict, str], bool], now: float) -> None:
    if not _state["gh_queue"] or now - _state["gh_repo_at"] < GH_REPO_S:
        return
    _state["gh_repo_at"] = now
    repo = _state["gh_queue"].pop(0)
    text = ""
    for name in ("README.md", "readme.md", "README.MD", "README"):
        r = await client.get(f"https://raw.githubusercontent.com/{repo['full_name']}/{repo['default_branch']}/{name}",
                             timeout=10.0)
        if r.status_code == 200:
            text = r.text[:200_000]
            break
    found, why = None, "no contract address"
    for chain, addrs in readme_addresses(text).items():
        if not addrs:
            continue
        r = await client.get(DEX_TOKENS.format(chain=chain, addresses=",".join(addrs)), timeout=10.0)
        pairs = r.json() if r.status_code == 200 else []
        # the first address in the README with a pool is the project's token
        for a in addrs:
            own = [p for p in pairs if ((p.get("baseToken") or {}).get("address") or "").lower() == a.lower()]
            if own:
                found, why = token_from_pairs(chain, own, repo)
                break
        if found or why != "no contract address":
            break
    _note(f"gh:{repo['full_name']}", found is not None, why, now)
    if found:
        add(found, "github")
    _save()


# -------------------------------------------------------------------- giro

# ------------------------------------------------------------- Jupiter

# Jupiter's verified list: ~3,700 Solana tokens a team has vouched for, with
# cap, liquidity, age, website and mint authority in one response. The widest
# net for existing projects: on 25/09 it held 213 in band against the ~370
# the other sources had found in a day.
JUP_VERIFIED = "https://lite-api.jup.ag/tokens/v2/tag?query=verified"
JUP_POLL_S = 6 * 3600
JUP_SKIP_TAGS = {"meme", "stocks", "prestocks", "rwa", "lst", "original-lst", "duplicate"}
JUP_MIN_LIQUIDITY = 5_000


def _iso_ts(v) -> float | None:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def jupiter_candidates(rows: list[dict], now: float) -> list[dict]:
    """In band, tradeable, with a website, no meme/stock tag. No age floor
    since 29/09 (Lorenzo: "il limite di data non ha granche' senso"). An
    active mint authority no longer drops a token here (19/10): Jupiter
    does not say who holds it, and the tokenomics pillar does (a program's
    costs points, a wallet's rejects); bridged copies of big coins, the
    reason for the old filter, are stopped by leaderboard's bridged check."""
    out = []
    for t in rows or []:
        cap = float(t.get("mcap") or 0)
        born = _iso_ts((t.get("firstPool") or {}).get("createdAt")) if t.get("firstPool") else None
        if not (CAP_MIN <= cap <= CAP_MAX) or float(t.get("liquidity") or 0) < JUP_MIN_LIQUIDITY:
            continue
        if not t.get("website") or JUP_SKIP_TAGS & set(t.get("tags") or []):
            continue
        if _looks_like_meme(t.get("symbol") or "", t.get("name") or ""):
            continue
        out.append({"chain": "solana", "token_address": t.get("id"), "symbol": t.get("symbol") or "?",
                    "name": t.get("name") or "", "website": t.get("website"), "market_cap": cap,
                    "liquidity_usd": float(t.get("liquidity") or 0), "launched_at": born, "image": t.get("icon"),
                    "socials": [{"type": k, "url": t[k]} for k in ("twitter", "telegram", "discord") if t.get(k)]})
    return out


async def _poll_jupiter(client: httpx.AsyncClient, add: Callable[[dict, str], bool], now: float) -> None:
    if now - _state["jup_at"] < JUP_POLL_S:
        return
    _state["jup_at"] = now
    r = await client.get(JUP_VERIFIED, timeout=30.0)
    if r.status_code != 200:
        raise RuntimeError(f"Jupiter {r.status_code}")
    rows = r.json() if isinstance(r.json(), list) else []
    # The whole verified list into the database, in band or not: the market
    # moves, and the database will look again.
    projects_db.upsert_many([{"chain": "solana", "token_address": t.get("id"), "symbol": t.get("symbol"),
                              "name": t.get("name"), "website": t.get("website"), "image": t.get("icon"),
                              "market_cap": t.get("mcap"), "liquidity_usd": t.get("liquidity")}
                             for t in rows if t.get("id")], "jupiter", now)
    found = jupiter_candidates(rows, now)
    _state["jup_last"] = len(found)
    for item in found:
        key = f"jup:{item['token_address']}"
        if key in _seen:
            continue
        _note(key, add(item, "jupiter"), "verified list", now)


# --------------------------------------------------------- GeckoTerminal
#
# New tokens on Ethereum and Base (Lorenzo, 17/10: "aggiungi la fonte di
# token nuovi per Ethereum e Base"). Jupiter brings Solana's young projects;
# the other two chains only had CoinGecko's full list, mostly old coins, and
# scored far lower (8 and 4 studied projects at 60 or more, against 46 on
# Robinhood). GeckoTerminal's newest pools, in the cap band, then the token's
# own page for its website: no website, no analysis.

GT_NEW_POOLS = "https://api.geckoterminal.com/api/v2/networks/{net}/new_pools"
GT_TOKEN_INFO = "https://api.geckoterminal.com/api/v2/networks/{net}/tokens/{token}/info"
GT_CHAINS = {"ethereum": "eth", "base": "base"}
GT_POLL_S = 600
GT_PAGES = 2                     # 20 pools a page
GT_INFO_PER_CHAIN = 3            # token pages read per chain per poll: one chain cannot starve the other
GT_MIN_LIQUIDITY = 5_000
# Launchpads (Lorenzo, 18/10: "pump.fun (Veil ad esempio e' stato lanciato da
# li'), Meteora, Pons"). On Solana a new_pools page holds a minute of
# pump.fun's bonding curves, so the launchpads are read by DEX instead:
# the pools with the most trades in 24 hours (GeckoTerminal has no newest-
# first order per DEX), i.e. the launches people are actually buying.
# pumpswap = pump.fun's graduates, meteora-dbc / -damm-v2 = Meteora's curve
# and its graduates (Believe, Jupiter Studio...), the others their own pads.
GT_DEX_POOLS = "https://api.geckoterminal.com/api/v2/networks/{net}/dexes/{dex}/pools"
GT_LAUNCHPADS = {
    "solana": ("solana", ("pumpswap", "pump-fun", "meteora-dbc", "meteora-damm-v2", "raydium-launchlab",
                          "bags-fm", "letsbonk-fun")),
    "robinhood": ("robinhood", ("pons-dot-family", "pons-v2", "pons-v2-dex")),
}
GT_INFO_PER_LAUNCHPAD_CHAIN = 6  # token pages per poll on a launchpad chain: more lists, more candidates
# The quote side of a pool is never the project.
GT_QUOTES = {"WETH", "ETH", "USDC", "USDT", "DAI", "CBBTC", "WBTC", "USDBC", "EURC", "USDE", "USDS"}


def new_pool_candidates(chain: str, payload: dict | None) -> list[dict]:
    """The base tokens of GeckoTerminal's new pools in the band, not memes."""
    payload = payload or {}
    tokens = {t.get("id"): (t.get("attributes") or {}) for t in payload.get("included") or [] if isinstance(t, dict)}
    out, seen = [], set()
    for pool in payload.get("data") or []:
        a = pool.get("attributes") or {}
        rel = ((pool.get("relationships") or {}).get("base_token") or {}).get("data") or {}
        t = tokens.get(rel.get("id")) or {}
        address, symbol = t.get("address"), (t.get("symbol") or "")
        if not address or address.lower() in seen or symbol.upper() in GT_QUOTES:
            continue
        cap = next((float(v) for v in (a.get("market_cap_usd"), a.get("fdv_usd")) if v and float(v) > 0), 0.0)
        liq = float(a.get("reserve_in_usd") or 0)
        if not (CAP_MIN <= cap <= CAP_MAX) or liq < GT_MIN_LIQUIDITY:
            continue
        if _looks_like_meme(symbol, t.get("name") or ""):
            continue
        seen.add(address.lower())
        out.append({"chain": chain, "token_address": address, "symbol": symbol or "?", "name": t.get("name") or "",
                    "market_cap": cap, "liquidity_usd": liq, "launched_at": _iso_ts(a.get("pool_created_at")),
                    "image": t.get("image_url") if t.get("image_url") not in (None, "missing.png") else None})
    return out


def token_info_fields(payload: dict | None) -> dict:
    """Website, socials and description from GeckoTerminal's token page."""
    a = ((payload or {}).get("data") or {}).get("attributes") or {}
    website = legit.pick_website(a.get("websites") or [])
    handle = lambda h: str(h).rstrip("/").rsplit("/", 1)[-1].lstrip("@")     # noqa: E731 - "@x", "x" or a full link
    socials = [{"type": k, "url": u} for k, u in (
        ("twitter", f"https://x.com/{handle(a['twitter_handle'])}" if a.get("twitter_handle") else None),
        ("telegram", f"https://t.me/{handle(a['telegram_handle'])}" if a.get("telegram_handle") else None),
        ("discord", a.get("discord_url"))) if u]
    desc = (a.get("description") or "")[:400]
    if "meme" in desc.lower():
        return {}
    return {"website": website, "socials": socials, "description": desc} if website else {}


async def _poll_new_pools(client: httpx.AsyncClient, add: Callable[[dict, str], bool], now: float) -> None:
    if now - _state.get("gt_at", 0.0) < GT_POLL_S:
        return
    _state["gt_at"] = now
    from app.trading.onchain.usage import _gecko      # the shared GeckoTerminal gate
    lists: dict[str, list[tuple]] = {}
    for chain, net in GT_CHAINS.items():
        lists.setdefault(chain, []).extend(
            (net, GT_NEW_POOLS.format(net=net), {"page": page, "include": "base_token"}, "geckoterminal")
            for page in range(1, GT_PAGES + 1))
    # Each poll starts from the next launchpad: the first ones in the list
    # cannot use up the budget every time (review on #591).
    turn = _state["gt_turn"] = _state.get("gt_turn", -1) + 1
    for chain, (net, dexes) in GT_LAUNCHPADS.items():
        start = turn % len(dexes)
        lists.setdefault(chain, []).extend(
            (net, GT_DEX_POOLS.format(net=net, dex=dex), {"page": 1, "include": "base_token",
                                                          "sort": "h24_tx_count_desc"}, "launchpad")
            for dex in dexes[start:] + dexes[:start])
    try:
        for chain, reqs in lists.items():
            budget = GT_INFO_PER_LAUNCHPAD_CHAIN if chain in GT_LAUNCHPADS else GT_INFO_PER_CHAIN
            reads = 0
            for net, url, params, source in reqs:
                if reads >= budget:
                    break
                data = await _gecko(client, url, params, caller="discovery")
                if not data:
                    continue
                for c in new_pool_candidates(chain, data):
                    k = f"gt:{chain}:{c['token_address'].lower()}"
                    if k in _seen or reads >= budget:
                        continue
                    reads += 1
                    extra = token_info_fields(await _gecko(client, GT_TOKEN_INFO.format(net=net, token=c["token_address"]),
                                                           caller="discovery"))
                    if not extra:
                        _note(k, False, "no website, or a meme description", now)
                        continue
                    _note(k, add({**c, **extra}, source), "new pool", now)
    finally:
        _save()


# The bulk sweep: CoinGecko's lists find projects weeks after their launch
# (18/10: median 71 days for those only CoinGecko found, 10 for the rest), so
# it alone waits while the pool is busy; the fast sources never stop.
BULK_STEPS = ("coingecko",)


async def tick(client: httpx.AsyncClient, add: Callable[[dict, str], bool], now: float | None = None,
               bulk: bool = True) -> None:
    """Chiamato dal giro della classifica. Non solleva. `bulk` False skips
    BULK_STEPS (leaderboard.discovery_open)."""
    now = now or time.time()
    if _state["running"]:
        return
    _state["running"] = True
    try:
        steps = (("jupiter", _poll_jupiter), ("geckoterminal", _poll_new_pools), ("defillama", traction.poll),
                 ("coingecko", _cg_step), ("profili", _poll_profiles),
                 ("github", lambda c, a, n: _gh_search(c, n)), ("readme", _gh_repo))
        for name, step in steps:
            if not bulk and name in BULK_STEPS:
                continue
            try:
                await step(client, add, now)
            except (httpx.HTTPError, ValueError, RuntimeError) as exc:
                logger.info("scan progetti: %s non riuscito: %s", name, exc)
                if name == "coingecko":
                    _state["cg_next_at"] = now + 60
    finally:
        _state["running"] = False
    await asyncio.sleep(0)


_load()
