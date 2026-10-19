"""La classifica dei progetti migliori: il Gem Finder.

Dal 25/09 non legge piu' il radar (Lorenzo: "il cacciatore di gemme non
deve scansionare il mercato degli ultimi 15 minuti [...] la ricerca al
minuto delle cose che escono deve stare sullo sniper, non qui"). Le fonti
sono solo di ricerca (`discovery.py`: CoinGecko, GitHub, profili) piu' i
riferimenti che Lorenzo ha indicato; il pilastro "site" e' la ricerca di
`research.py`. Il testo sotto racconta la prima versione.

Lorenzo: "una specie di leaderboard [...] primo posto, secondo posto, terzo
posto [...] una classifica dinamica, non fissa, aggiornata in tempo reale
[...] rigoroso [...] da quanto e' che sono usciti [...] e ampliamo anche la
chain per i token lanciati su Pump Fun".

Da dove arrivano i progetti:
- i listing verificati (`listings.recent()`) e le proposte e i token provati
  dal radar (`radar.snapshot()`): hanno gia' passato `legit.assess`;
- pump.fun e i progetti fuori dai limiti del radar (tipo DREGG) li porta il
  radar stesso: qui si legge solo quello che ha salvato, una fonte sola.

Ogni progetto passa da `depth.analyze` (GitHub, sito, tokenomics). Chi viene
bocciato su un pilastro esce e non rientra; chi ha un dato in attesa resta
fuori finche' non arriva. Il punteggio si rifa' da solo: tokenomics ogni
20 minuti (i portafogli cambiano), GitHub ogni 2 ore, sito ogni 12. Cap e
liquidita' ogni minuto da DexScreener. Le regole della gemma sono in
`qualifies` (dal 29/09 ne' eta' ne' eccezioni del radar: vedi li').

Il riferimento (Lorenzo, 24/09: "mi devi mettere drag al primo posto in
assoluto con menzione d'onore"): DREGG sta sempre primo, e gli altri si
ordinano per qualita' (i tre pilastri) e somiglianza tecnica a DREGG
(`benchmark.py`), 70/30.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import time

import httpx

from app import http_client
from app.config import settings

from app.sniper.quality import _looks_like_meme
from app.trading.onchain import (benchmark, big_coins, code_review, consistency, depth, discovery, gem_learn, gem_track, judge, legit, narrative_map,
                                  narratives, priority, projects_db, research, storage, traction, usage)
from app.atomic_write import write_text_atomic

logger = logging.getLogger(__name__)

_STORE_FILE = storage.data_file("onchain_leaderboard.json")

TICK_S = 10
MARKET_POLL_S = 60
DEX_TOKENS = "https://api.dexscreener.com/tokens/v1/{chain}/{addresses}"

STALE_S = {"tokenomics": 20 * 60, "github": 2 * 3600, "site": 12 * 3600}
PENDING_RETRY_S = 3 * 60
PENDING_GIVE_UP_S = 6 * 3600       # un dato che non arriva in 6 ore non arrivera'
MAX_ENTRIES = 400
KEEP_EXCLUDED = 60
ANALYZE_CONCURRENCY = 5   # was 3: "la scansione complessiva e' lenta" (27/09)
# The project database (projects_db): how much of it the board takes in and
# refreshes per step.
DB_FEED_PER_TICK = 6
DB_FEED_MAX_WAITING = 20            # unanalysed entries in the working set before feeding more
DB_MARKET_S = 60
DB_MARKET_BATCH = 150               # 5 DexScreener requests a minute
BOARD_SIZE = 50
MIN_PILLAR = 35                    # sotto, un pilastro e' troppo debole per stare in classifica
# One floor per pillar, the same with or without public code (29/09). Before,
# public code needed GitHub 70 and every pillar 60, no code needed site 70:
# a project that showed weak code fared worse than one that hid it, and the
# site bar left out STEALF (60) and GRID (52), read as "promising". Lorenzo:
# "se non passano le nostre regole sono da rivedere [...] risultano troppo
# severi". Code quality still weighs in the score and the rank.
PILLAR_FLOOR = {"github": MIN_PILLAR, "site": 50, "tokenomics": 60}
# GEM_STRICT_CAP_USD was the band above which a gem needed a high final
# score (28/09-07/10; replaced by the usage bars). The band was $100k until 29/09 (Lorenzo: "alziamo semmai il tetto della
# market cap sopra i 100k, perche' tanto le gemme possono arrivare anche a
# 1 o 2 milioni [...] sono comunque capitalizzazioni basse"). DeepSeek's
# judge can admit what the rules exclude, or veto what passes.
GEM_STRICT_CAP_USD = 2_000_000
# Research sources (discovery). Since 29/09 every source follows the same
# rules; the tuple only names them.
SERIOUS_SOURCES = ("coingecko", "dexscreener", "github", "reference", "jupiter", "defillama")
RADAR_SOURCES = ("radar", "listing")   # before 25/09: fresh launches, now the Meme Sniper's
# Projects Lorenzo found himself: always examined, never pinned.
REFERENCES = (
    {"chain": "solana", "token_address": "6SjVTj1VGwFSXn7wEjwFm77LvACeTqB7sQUebYKX8Ds5", "symbol": "ROUTER",
     "name": "Solrouter", "website": "https://solrouter.com", "websites": ["https://docs.solrouter.com"],
     "narratives_hint": ["privacy", "fhe_mpc_tee"]},
    # Lorenzo, 08/10: "fagli fare un giro dentro al nostro sistema" (a list of
    # Robinhood-ecosystem projects). Same rules as every other source.
    {"chain": "robinhood", "token_address": "0xD0cA71118ca21D674f9018A53026a38A0AB54DbF", "symbol": "DUCAT", "name": "Ducat"},
    {"chain": "robinhood", "token_address": "0xE0fB5d77C627BA9c7950Fc0D62d1D96603e7B7C6", "symbol": "Rialto", "name": "Rialto"},
    {"chain": "robinhood", "token_address": "0x56910D4409F3a0C78C64DD8D0545FF0705389870", "symbol": "Index", "name": "The Index"},
    {"chain": "robinhood", "token_address": "0x0C020Bef365D7001611EF1cEcd6084cdD6b73683", "symbol": "L4VA", "name": "L4VA"},
    {"chain": "robinhood", "token_address": "0x39dBED3a2bd333467115dE45665cC57F813C4571", "symbol": "PONS", "name": "Pons"},
    {"chain": "robinhood", "token_address": "0xf2AD0505968862195Ee3bFd3E8A2C430578C1aAd", "symbol": "HOPPR", "name": "Hoppr"},
    {"chain": "robinhood", "token_address": "0x791229E3EbD6CFdC3D8157f48722684173C29aD9", "symbol": "SLVR", "name": "Slvr"},
    {"chain": "robinhood", "token_address": "0xDc45b71d7203c2e8baafC43A19BcA0Eb993bB54E", "symbol": "DARK", "name": "Darkwoods"},
    {"chain": "base", "token_address": "0x5aB3D4c385B400F3aBB49e80DE2fAF6a88A7B691", "symbol": "FLOCK", "name": "FLock.io"},
    {"chain": "robinhood", "token_address": "0xc32Ab2e562adE6fBa6D3d1E3960d49b0957Ef645", "symbol": "LIEGE", "name": "Liege Agents"},
    {"chain": "robinhood", "token_address": "0xeDBf91223639800BCd5756815CAf908Df3b890bE", "symbol": "PRIORS", "name": "Priors Agents"},
    {"chain": "robinhood", "token_address": "0xF8BC08092C06dB6148114DCf82AF881F1085f92b", "symbol": "WOOD", "name": "Sherwood Protocol"},
    {"chain": "robinhood", "token_address": "0xdc453b1405CfE25e2afBA8E7F4272b0a00437777", "symbol": "TasQ", "name": "TasQ Network"},
    {"chain": "robinhood", "token_address": "0xC34cBBE7D2a71f5dfa4d3a5285AC21B6852E2c4f", "symbol": "CFPX", "name": "CrossFund Protocol"},
    {"chain": "robinhood", "token_address": "0xA3b6AEe90017b72c0812dC1e013De70eB2917ba3", "symbol": "EARN", "name": "EARNONHOOD"},
    {"chain": "robinhood", "token_address": "0x459476869aF797Eb9061B41fA04dE46A60FBeDBD", "symbol": "BV7X", "name": "BV7X"},
    {"chain": "robinhood", "token_address": "0x4A72B9702f991b790788f8AFA9e7112541f4E8f8", "symbol": "ROUTE", "name": "Route"},
    {"chain": "robinhood", "token_address": "0xc4f730335Fb9e439ca5552f7b52B8E638c4245B0", "symbol": "NOTE", "name": "Note Systems"},
    {"chain": "robinhood", "token_address": "0x47569d49471bDBaBFaf5531c0F74d9f2dE82A11A", "symbol": "PROPHET", "name": "PROPHET"},
)
# A researcher's floor: a pool someone can trade. No age floor since 29/09
# (Lorenzo: "il limite di data non ha granche' senso"): a project new on a
# chain can be old elsewhere (BV7X, 8 months on Base, 12 days on Robinhood).
MIN_LIQUIDITY_USD = 10_000
# Early gems. Request: "quando la market cap e' sotto i 50k e fondamentali
# ci sono, voglio che il sistema lo evidenzi che potrebbe valere la pena di
# comprare un po'". Below EARLY_CAP_USD a pool is thinner, so the floor is
# lower; the fundamentals are not: public code and every pillar solid.
EARLY_CAP_USD = 50_000
EARLY_MIN_LIQUIDITY_USD = 5_000
ALERTS_PER_TICK = 5
# A "new gem" is a project entering the Top's gated pool (main.ARENA_POOL),
# the list the nightly summary reads "Entrati nelle arene" from (Lorenzo,
# 17/10: three entered overnight, no Telegram). It used to be a project
# entering the board's own ranking, announced only if it was in the Top 50
# at that moment: database rows never, board entries almost never, and the
# skipped ones were marked as sent for good.
TOP_ALERT_POOL = 500
# Pearl (whitekobra's app, 16/10): the early list's gems scoring 70 or more,
# rounded as the app shows them. Lorenzo, 17/10: "aggiungi l'alert nella
# chat delle gemme anche per quelle che eventualmente entrano nella sezione Pearl".
PEARL_MIN = 70
# Lorenzo (28/09): "per gemme solitamente si intende roba di capitalizzazione
# bassa [...] massimo 10 milioni". A hard ceiling for every entry, checked on
# the token's global cap too: AAVE's Solana copy showed $585k while AAVE
# is worth $2.2B, and a local pool cap cannot tell the two apart.
BOARD_CAP_MAX_USD = 10_000_000
# Real usage before any score (Lorenzo, 07/10, scheda approvata: "progetti
# che hanno un prodotto molto funzionante, che ci siano volumi, che ci sia
# partecipazione"; Clawville World sat 3rd with $492 of volume a day and 245
# holders). Measured once a day by usage.py on DexScreener and GeckoTerminal.
# Under TOP_CAP_MIN_USD a project passing every other bar is "early": a list
# apart, never on the podium.
# Same day, later (Lorenzo): "dare troppa importanza [a] volume [...] esclude
# delle gemme che sono nascoste [...] il nostro obiettivo e' trovare delle
# gemme [...] sono cose importanti, ma non devono direzionare troppo il
# tutto". So the hard bars only drop what nobody trades at all (Clawville:
# $712 a day, 2 buyers) or what is shrinking or held by a few wallets; how
# much a token is used weighs in the score, and a strong product with little
# market (a hidden gem, hidden_gem) is flagged, not dropped.
TOP_CAP_MIN_USD = 300_000
USAGE_DEAD_VOL_USD = 2_000           # 7-day average a day: below it AND few buyers = nobody trades it
USAGE_DEAD_BUYERS = 10               # distinct buyers in 24 hours
USAGE_HOLDERS_MIN = 100
USAGE_SHRINK_MAX = 0.10              # holders down more than 10% in 30 days
USAGE_TOP10_MAX_PCT = 40.0           # wallets only: pools, contracts and program accounts are not whales
USAGE_STALE_S = 3 * 86400           # an older snapshot is no measure
# Where the usage score starts counting (not bars): $25k a day, 30 buyers,
# 100 trades, 500 holders.
USAGE_VOL_LO_USD = 25_000
USAGE_BUYERS_LO = 30
USAGE_TX_LO = 100
USAGE_HOLDERS_LO = 500
HIDDEN_PRODUCT_MIN = 65              # product block at least this...
HIDDEN_USAGE_MAX = 35                # ...with usage at most this: a hidden gem
USAGE_PER_TICK = 10                  # tokens measured per tick, each at most once a day
USAGE_WARM_MAX = 200                 # at start-up: ~3 GeckoTerminal calls each, 14 a minute
# The final score (07/10): measured parts first, DeepSeek last and light.
# Product = research (site, docs), GitHub and DeepSeek's code reading; token
# = tokenomics; DeepSeek = its report and its board review. A part with no
# reading is left out and the others share its weight.
# Product and DeepSeek's reading (which now sees the usage numbers too)
# lead with 55; measured market 30 (Lorenzo: balanced, the old Top "non era
# male"); tokenomics 15.
SCORE_WEIGHTS = {"usage": 0.20, "participation": 0.10, "product": 0.30, "token": 0.15, "deepseek": 0.25}
CG_CONTRACT = "https://api.coingecko.com/api/v3/coins/{platform}/contract/{address}"
CG_PLATFORM = {"solana": "solana", "robinhood": "robinhood", "arc": "arc"}
GLOBAL_CAP_EVERY_S = 15            # one CoinGecko lookup per gap, shared with discovery
GLOBAL_CAP_TTL_S = 24 * 3600
# DeepSeek re-reads the whole board (judge.review_board): every two hours,
# or ten minutes after the board changes. Its score is the DeepSeek block of
# final_score; a drop keeps the project off for judge.REVIEW_TTL_S.
REVIEW_EVERY_S = 2 * 3600
REVIEW_MIN_GAP_S = 10 * 60
# DeepSeek reads the code of each project (code_review.py): complexity and
# innovation are part of the product block, one project at a time.
CODE_EVERY_S = 60
# Scan less, complete more (Lorenzo, 28/09: "quando raggiungiamo un bel bacino
# fermiamo la scansione e concentriamoci su completare le informazioni").
# Past POOL_TARGET projects that passed the filters, discovery of new ones
# pauses while more than BACKLOG_LOW of them still miss a piece (analysis,
# DeepSeek's report, the code reading); once nearly complete, one slow
# discovery round every DISCOVERY_SLOW_S keeps the pool fresh. Since 18/10
# this holds only discovery.BULK_STEPS (CoinGecko): the fast sources run
# always, or a 4,000-project pool kept them off for good.
POOL_TARGET = 300
BACKLOG_LOW = 10
DISCOVERY_SLOW_S = 6 * 3600
CODE_RETRY_S = 6 * 3600        # a failed reading waits: GitHub allows few calls an hour
# Without public code a project ranks below an equal one that shows it.
NO_GITHUB_PENALTY = 10.0
# Whitekobra's weights (Lorenzo, 17/10, only his account): no participation
# block, its holder growth moved into usage, product up, DeepSeek down, and
# half the closed-code penalty. main._top_entries(full=True) scores with them.
KOBRA_SCORE_WEIGHTS = {"usage": 0.25, "product": 0.35, "token": 0.20, "deepseek": 0.20}
KOBRA_NO_GITHUB_PENALTY = 5.0
KOBRA_GROWTH_WEIGHT = 20              # inside usage, next to volume/cap 45, volume 30, buyers 25
RULES_VERSION = 16             # 2: "no GitHub" stopped being a ban; 3: radar launches out;
                               # 4: research read by reader.py, older bans and readings dropped;
                               # 5: reader recognises research-stage code and stated limits
                               # 6: no age limits, strict band from $100k to $2M, one rule chain
                               # 7: private linked repos are missing code, GeckoTerminal tokenomics
                               # 8: every cached fatal pillar is recomputed under today's checks
                               # 9: tokenomics redone: missing data is not a pass, big contracts
                               #    are whales (audit 29/09, M01/M02)
                               # 10: EVM rows stamped "no pool" by an address-case bug ask DexScreener again
                               # 11: DexScreener's own links fill website/GitHub of rows without them
                               # 12: rows rejected for "a single wallet" are looked at again (contracts left out)
                               # 13: Solana program accounts leave the wallet limits like EVM contracts
                               # 14: minting by a contract/program, busy or code-drop repos, script-built sites
                               # 15: unreadable site + empty description rejects; linked wallets >= 50% reject
                               # 16: rules 15 applied from the stored facts at load (no re-read)

_entries: dict[str, dict] = {}     # chain:token
_excluded: list[dict] = []
_gone: dict[str, float] = {}       # chain:token bocciati: non si riesaminano
_busy: set[str] = set()
_tasks: set[asyncio.Task] = set()
_slots = asyncio.Semaphore(ANALYZE_CONCURRENCY)
_state = {"version": 0, "examined": 0, "last_tick": 0.0, "last_market": 0.0,
          "sources": {}, "board": []}
_counts = {"analysed": 0}          # analyses finished since start: the nightly run's summary
_recorded: set[str] = set()         # working-set keys whose verdict was written to the database since start
_alerted: set[str] = set()          # "new:<key>" / "early:<key>": alerts already sent
_outbox: list[tuple[str, str]] = []
_alert_hooks: list = []
_flush_hooks: list = []              # awaited once a flush_alerts has sent everything (main.py)
_priming = False
_top_primed = False                 # the Top already seen once: what is in it at first sight is not news
_pearl_primed = False               # the same for Pearl
_dirty = False
_reset_market = False     # set by _load when the stored rules predate version 10
_requeue_fatals = False   # set by _load when the stored rules predate version 8
_recheck_programs = False  # set by _load when the stored rules predate version 13
_recheck_misreads = False  # set by _load when the stored rules predate version 14
MISREAD_FATALS = ("new tokens can be minted", "all commits on a single day", "almost no code", "empty page")


def _key(chain: str, token: str) -> str:
    return f"{chain}:{token}"


# ------------------------------------------------------------------ memoria

def apply_rules_15(pillars: dict) -> None:
    """Rules 15 (Spidey Show, 19/10) on pillars scored before them, from
    their own facts: no call, the same verdicts research.judge_research and
    depth._judge_tokenomics give now."""
    from app.trading.onchain import research
    site = pillars.get("site") or {}
    f = site.get("facts") or {}
    if f.get("unreadable") and not site.get("fatal") and f.get("verdict") == "thin" \
            and (f.get("ai_substance") or 0) <= research.UNREAD_THIN_MAX:
        site.update(score=0, fatal="research: site not readable and the description shows nothing built")
    tok = pillars.get("tokenomics") or {}
    linked = (tok.get("facts") or {}).get("linked_pct")
    if linked is not None and linked >= depth.LINKED_REJECT_PCT and not tok.get("fatal"):
        tok.update(score=0, fatal=f"linked wallets hold {linked:.0f}% of supply")


def _load() -> None:
    try:
        raw = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(raw, dict):
        _entries.update({k: v for k, v in (raw.get("entries") or {}).items()
                         if isinstance(v, dict) and v.get("source") not in RADAR_SOURCES})
        rules = int(raw.get("rules") or 1)
        if rules < 5:
            # Research pillars scored before the reader existed: read them again now.
            for e in _entries.values():
                (e.get("pillars") or {}).pop("site", None)
                (e.get("checked_at") or {}).pop("site", None)
        global _requeue_fatals, _reset_market, _recheck_programs, _recheck_misreads
        if rules < 12:
            _reset_market = True
        if rules < 16:
            # Unreadable sites were a neutral 50 whatever the description said,
            # and a linked majority only a flag. Both verdicts are already in
            # the stored facts: applied here, at once (the sentinel never
            # re-reads an old entry, the night would have been hours away).
            for e in _entries.values():
                apply_rules_15(e.get("pillars") or {})
        if rules < 14:
            # Fatal verdicts that misread who can mint, a busy repository, an
            # account's profile repo or a script-built site: read again.
            _recheck_misreads = True
            for e in _entries.values():
                p = e.get("pillars") or {}
                for name in [n for n, x in p.items()
                             if any(m in ((x or {}).get("fatal") or "") for m in MISREAD_FATALS)]:
                    p.pop(name, None)
                    (e.get("checked_at") or {}).pop(name, None)
        if rules < 13:
            # Solana holders read with program accounts counted as wallets: read again.
            _recheck_programs = True
            for e in _entries.values():
                if e.get("chain") == "solana":
                    (e.get("pillars") or {}).pop("tokenomics", None)
                    (e.get("checked_at") or {}).pop("tokenomics", None)
        if rules < 8:
            # Fatal pillars scored by checks fixed since (contracts counted as
            # one wallet, JS sites read as empty: BV7X, PFWA) are redone once.
            _requeue_fatals = True
            for e in _entries.values():
                p = e.get("pillars") or {}
                for name in [n for n, x in p.items() if (x or {}).get("fatal")]:
                    p.pop(name, None)
                    (e.get("checked_at") or {}).pop(name, None)
        if rules < 9:
            # Tokenomics scored when a missing answer counted as a pass and
            # any contract was left out of the limits: read again.
            for e in _entries.values():
                (e.get("pillars") or {}).pop("tokenomics", None)
                (e.get("checked_at") or {}).pop("tokenomics", None)
        if rules < 7:
            # "GitHub link without a repository" was private repos (BV7X), and a
            # tokenomics pending on GoPlus now falls back to GeckoTerminal.
            for e in _entries.values():
                p = e.get("pillars") or {}
                for name, stale in (("github", (p.get("github") or {}).get("fatal") == "GitHub link without a repository"),
                                    ("tokenomics", bool((p.get("tokenomics") or {}).get("pending")))):
                    if stale:
                        p.pop(name, None)
                        (e.get("checked_at") or {}).pop(name, None)
        # Bans under older rules (no GitHub, the old site score) are lifted.
        if rules >= RULES_VERSION:
            _excluded.extend(x for x in raw.get("excluded") or [] if isinstance(x, dict))
            _gone.update(raw.get("gone") or {})
        _state["examined"] = int(raw.get("examined") or 0)
        _state["rescored_rules"] = raw.get("rescored_rules")
        _alerted.update(raw.get("alerted") or [])
        # First start with alerts: what is already on the board is not news.
        global _priming, _top_primed, _pearl_primed
        _priming = "alerted" not in raw
        # "top_seen", not the old "top_primed": the Top's own tags start empty
        # (see queue_top_news), so the first look must take note again.
        _top_primed = bool(raw.get("top_seen"))
        _pearl_primed = bool(raw.get("pearl_primed"))
        _rank()
        _priming = False


def _save() -> None:
    global _dirty
    _dirty = False
    try:
        write_text_atomic(_STORE_FILE, json.dumps({"entries": _entries, "excluded": _excluded, "gone": _gone,
                                           "examined": _state["examined"], "rules": RULES_VERSION,
                                           "rescored_rules": _state.get("rescored_rules"),
                                           "alerted": sorted(_alerted), "top_seen": _top_primed,
                                           "pearl_primed": _pearl_primed},
                                          ensure_ascii=False),
                               encoding="utf-8")
    except OSError:
        pass
    gem_track.save()


def reset_for_tests() -> None:
    global _top_primed, _pearl_primed
    _top_primed = _pearl_primed = False
    _alerted.clear()
    _recorded.clear()
    _outbox.clear()
    _alert_hooks.clear()
    _flush_hooks.clear()
    gem_track.reset_for_tests()
    big_coins.reset_for_tests()
    traction.reset_for_tests()
    _entries.clear()
    _excluded.clear()
    _gone.clear()
    _busy.clear()
    _state.update(version=0, examined=0, last_tick=0.0, last_market=0.0, sources={}, board=[],
                  reviewed_at=0.0, reviewed_board=[], reviewing=False, code_reading=False, code_at=0.0, db_board=[],
                  narr_mapping=False, top_filling=False, top_fill_at=0.0, top_synced_at=0.0, auditing=False)
    _top_tried.clear()
    _top_rank.clear()
    set_top_source(None)


# ------------------------------------------------------------------- fonti

def merge_narratives(hint: list[str] | None, site: list[str] | None, more: list[str] | None) -> list[str]:
    """Hint keys first (the category the coin was found in), then the rest."""
    return list(dict.fromkeys([*(hint or []), *(site or []), *(more or [])]))


def add(item: dict, source: str, now: float | None = None) -> bool:
    """Un progetto da esaminare. False se c'e' gia' o e' gia' stato bocciato."""
    chain, token = item.get("chain"), item.get("token_address")
    if not chain or not token:
        return False
    k = _key(chain, token)
    now = now or time.time()
    try:
        projects_db.upsert(item, source, now)
    except Exception:
        logger.exception("classifica: database non scritto per %s", k)
    # The database decides when a rejected project deserves a second look.
    if benchmark.is_benchmark(chain, token) or source in ("reference", "database"):
        _gone.pop(k, None)
    if k in _gone:
        return False
    fresh = {f: item[f] for f in ("market_cap", "liquidity_usd", "website", "github", "socials", "pair_url",
                                  "report", "scan_url", "checks", "exception", "github_verified", "description",
                                  "categories", "websites", "narratives_hint") if item.get(f)}
    if "narratives_hint" in item:       # an empty hint clears one a shared category gave before
        fresh["narratives_hint"] = list(item["narratives_hint"] or [])
    if k in _entries:
        _entries[k].update(fresh)
        return False
    launched = item.get("launched_at") or item.get("created_at")
    if not launched and item.get("age_hours") is not None:
        launched = now - float(item["age_hours"]) * 3600
    _entries[k] = {
        "chain": chain, "token_address": token, "pair_address": item.get("pair_address") or "",
        "symbol": item.get("symbol") or "?", "name": item.get("name") or item.get("symbol") or "?",
        "source": source, "found_at": now, "launched_at": launched,
        "image": item.get("image"), "bonding": bool(item.get("bonding")),
        "bonding_curve": item.get("bonding_curve"), "associated_bonding_curve": item.get("associated_bonding_curve"),
        "pillars": {}, "checked_at": {}, "rank": None, **fresh,
    }
    _state["examined"] += 1
    _mark()
    return True


def collect_saved() -> int:
    """The benchmark and the references Lorenzo named. Nothing from the
    radar: fresh launches are the Meme Sniper's."""
    n = add(benchmark.seed_item(), "riferimento")
    for item in REFERENCES:
        n += add(dict(item), "reference")
    return n


def is_big(item: dict, now: float | None = None) -> bool:
    """Above GEM_STRICT_CAP_USD: a label for the discovery pool, no longer a bar."""
    return float(item.get("market_cap") or 0) > GEM_STRICT_CAP_USD


def apply_market(pairs: list[dict]) -> None:
    """Cap, liquidita', variazione e data del pool piu' liquido di ogni token."""
    best: dict[str, dict] = {}
    # EVM keys may be stored in lower case while DexScreener answers in checksum case.
    index = {k.lower(): k for k in _entries}
    for p in pairs:
        token = (p.get("baseToken") or {}).get("address")
        k = index.get(_key(p.get("chainId") or "", token or "").lower())
        if k is None:
            continue
        liq = float((p.get("liquidity") or {}).get("usd") or 0)
        if k not in best or liq > float((best[k].get("liquidity") or {}).get("usd") or 0):
            best[k] = p
        created = (p.get("pairCreatedAt") or 0) / 1000
        e = _entries[k]
        if created and (not e.get("launched_at") or created < e["launched_at"]):
            e["launched_at"] = created
    for k, p in best.items():
        e = _entries[k]
        cap = p.get("marketCap") or p.get("fdv")
        e.update(market_cap=float(cap) if cap else e.get("market_cap"), price_usd=p.get("priceUsd"),
                 liquidity_usd=float((p.get("liquidity") or {}).get("usd") or 0),
                 change_24h=(p.get("priceChange") or {}).get("h24"), pair_url=p.get("url") or e.get("pair_url"),
                 dex=p.get("dexId"), bonding=(p.get("dexId") == "pumpfun"))
        if not e.get("pair_address") or e.get("bonding"):
            e["pair_address"] = p.get("pairAddress") or e.get("pair_address")
        base = p.get("baseToken") or {}
        if no_name(e.get("symbol")) and not no_name(base.get("symbol")):
            e.update(symbol=base["symbol"], name=base.get("name") or base["symbol"])
        sites = legit.links_from_dexscreener(p)["websites"]
        if sites:
            e["websites"] = list(dict.fromkeys([*(e.get("websites") or []), *sites]))[:6]
        gem_track.sample(e["chain"], e["token_address"], p.get("priceUsd"))
        projects_db.set_market(e["chain"], e["token_address"], mcap=cap, liq=e["liquidity_usd"],
                               vol24=(p.get("volume") or {}).get("h24"), price=p.get("priceUsd"))
    _mark()


async def _poll_market(client: httpx.AsyncClient) -> None:
    by_chain: dict[str, list[str]] = {}
    for e in _entries.values():
        by_chain.setdefault(e["chain"], []).append(e["token_address"])
    for chain, tokens in by_chain.items():
        for i in range(0, len(tokens), 30):
            r = await client.get(DEX_TOKENS.format(chain=chain, addresses=",".join(tokens[i:i + 30])),
                                 timeout=10.0)
            if r.status_code == 200 and isinstance(r.json(), list):
                apply_market(r.json())


# ---------------------------------------------------------------- analisi

def due(e: dict, now: float) -> set[str]:
    """I pilastri da rifare adesso."""
    out = set()
    for k, every in STALE_S.items():
        p = e["pillars"].get(k)
        at = e["checked_at"].get(k, 0)
        retry = p is not None and (p.get("pending") or (p.get("facts") or {}).get("unreadable"))
        if p is None or (retry and now - at >= PENDING_RETRY_S) or now - at >= every:
            out.add(k)
    return out


def apply_analysis(k: str, result: dict, now: float | None = None) -> None:
    now = now or time.time()
    e = _entries.get(k)
    if e is None:
        return
    ready = bool(e.get("overall")) and not e["overall"].get("pending")
    before = final_score(e) if ready else None
    old_pillars = {n: (e["pillars"].get(n) or {}).get("score") for n in depth.WEIGHTS}
    from app.trading.onchain import history
    for name, pillar in result.items():
        e["pillars"][name] = pillar
        e["checked_at"][name] = now
        if isinstance(pillar, dict):
            history.append(k, "leaderboard.pillar", {"pillar": name, "checked_at": now, **{
                f: pillar[f] for f in ("score", "flags", "fatal") if pillar.get(f) is not None}}, now)
        if name == "github" and (pillar.get("facts") or {}).get("url"):
            e["github"] = pillar["facts"]["url"]
    e["overall"] = depth.overall(e["pillars"])
    e["similarity"] = benchmark.similarity(benchmark.signals(
        (e["pillars"].get("github") or {}).get("facts"),
        (e["pillars"].get("site") or {}).get("facts", {}).get("tech_terms")))
    gh = (e["pillars"].get("github") or {}).get("facts") or {}
    site_keys = (e["pillars"].get("site") or {}).get("facts", {}).get("narratives") or []
    more = narratives.match(e.get("description"), e.get("categories"), gh.get("topics"), gh.get("description"))
    e["narratives"] = merge_narratives(e.get("narratives_hint"), site_keys, [*more, *(e.get("narr_ds") or [])])
    _text_moved(e, before, old_pillars, now)
    if e["overall"]["fatal"] and not benchmark.is_benchmark(e["chain"], e["token_address"]) \
            and e.get("source") != "reference":     # Lorenzo's references stay, with their reason
        _exclude(k, e["overall"]["fatal"], now)
        _remember(e, "rejected", e["overall"]["fatal"], now)
        _mark()
        return
    _mark()
    if not (e["overall"] or {}).get("pending"):
        why = qualifies(e, now)
        _remember(e, "ranked" if e.get("rank") else "studied", why, now)


# Lorenzo, 30/09 ("applica tutto"): the cheapest way to climb the board is
# to rewrite a website. A score that rose only because the site pillar did,
# with code and tokenomics unchanged, is flagged (not changed): the flag goes
# on the card, in the receipt and in the trace, and clears as soon as another
# pillar moves.
TEXT_MOVE = 8


def _text_moved(e: dict, before: float | None, old_pillars: dict, now: float) -> None:
    moved = [n for n in depth.WEIGHTS if (e["pillars"].get(n) or {}).get("score") != old_pillars.get(n)]
    if any(n != "site" for n in moved):
        e.pop("text_moved", None)
        return
    if before is None or moved != ["site"] or (e.get("overall") or {}).get("pending"):
        return
    after = final_score(e)
    if after - before >= TEXT_MOVE:
        e["text_moved"] = {"at": now, "from": before, "to": after, "site_from": old_pillars.get("site"),
                           "site_to": (e["pillars"].get("site") or {}).get("score")}


def _remember(e: dict, status: str, why: str, now: float) -> None:
    """The verdict goes to the database, so it outlives the working set.
    "ranked" or "studied" is the Top's word, not the board's (see sync_top)."""
    rank = e.get("rank")
    if status in ("ranked", "studied"):
        status, rank = _place(_key(e["chain"], e["token_address"]), rank)
        if status == "ranked":
            why = ""
    try:
        projects_db.record({**e, "rank": rank}, status, why, final_score(e) if status != "rejected" else None,
                           traction_of(e), now)
    except Exception:
        logger.exception("classifica: verdetto non salvato per %s", e.get("symbol"))
    if status in ("studied", "rejected") and not benchmark.is_benchmark(e["chain"], e["token_address"]):
        try:
            gem_track.decide(e, status, why, final_score(e), score_parts(e, now), rules_version(), now)
        except Exception:
            logger.exception("classifica: ricevuta non salvata per %s", e.get("symbol"))


def _exclude(k: str, reason: str, now: float) -> None:
    e = _entries.pop(k, None)
    _gone[k] = now
    if e is None:
        return
    _excluded.insert(0, {"chain": e["chain"], "token_address": e["token_address"], "symbol": e["symbol"],
                         "name": e["name"], "source": e["source"], "reason": reason, "at": now,
                         "was_rank": e.get("rank")})
    del _excluded[KEEP_EXCLUDED:]


async def _analyze(k: str, skip: set[str], client: httpx.AsyncClient) -> None:
    try:
        async with _slots:
            e = _entries.get(k)
            if e is None:
                return
            item = {**e, "links": [s.get("url") for s in e.get("socials") or [] if s.get("url")],
                    # only projects past the researcher's floor are worth Claude's reading
                    "finalist": not research_floor(e),
                    # the Top 50 gets the on-chain check of linked wallets (DREGG, 30/09)
                    "top": k in _top_rank or bool(e.get("rank"))}
            result = await depth.analyze(item, client, skip=skip)
        apply_analysis(k, result)
        if result:
            _counts["analysed"] += 1
        e = _entries.get(k)
        if e is not None and result:
            _note_study(e, sorted(result))
        if e is not None:
            o = e.get("overall") or {}
            if not o.get("pending") and not o.get("fatal"):
                # The Top has its own allowance: after a prompt change the whole set is
                # re-read and must not starve the projects people are looking at.
                j = await judge.judge(e, qualifies(e), priority=k in _top_rank)
                if j:
                    e["judge"] = j
                    _remember(e, "ranked" if e.get("rank") else "studied", qualifies(e), time.time())
                    _mark()
    except Exception:
        logger.exception("classifica: analisi fallita su %s", k)
    finally:
        _busy.discard(k)


_PILLAR_NAMES = {"github": "GitHub", "site": "site", "tokenomics": "tokenomics"}


def _note_study(e: dict, pillars: list[str]) -> None:
    """Ogni studio di un progetto nel registro dell'agente (Lorenzo, 28/09:
    "voglio avere la sensazione che stia lavorando costantemente [...]
    andando nel database a approfondire"). Solo lavoro vero, niente LLM."""
    from app.notify import deepseek_desk
    names = [_PILLAR_NAMES.get(p, p) for p in pillars]
    steps = []
    for p in pillars:
        pil = (e.get("pillars") or {}).get(p) or {}
        if pil.get("score") is not None:
            steps.append(f"{_PILLAR_NAMES.get(p, p)}: {round(pil['score'])}")
        elif pil.get("detail"):
            steps.append(f"{_PILLAR_NAMES.get(p, p)}: {str(pil['detail'])[:80]}")
    o = e.get("overall") or {}
    outcome = ("rejected: " + str(o.get("fatal"))[:80] if o.get("fatal")
               else f"score {round(o['score'])}" if o.get("score") is not None else "")
    deepseek_desk.note("study", f"Studied {e.get('symbol') or e.get('name')}: {', '.join(names)}",
                       steps=steps, outcome=outcome, chain=e.get("chain"), token=e.get("token_address"))


def _prune(now: float) -> None:
    for k, e in list(_entries.items()):
        pending_since = e.get("found_at", now)
        if benchmark.is_benchmark(e["chain"], e["token_address"]):
            continue
        # No age limit (29/09): only data that never arrives leaves the set.
        if (e.get("overall") or {}).get("pending") and now - pending_since > PENDING_GIVE_UP_S:
            # A slow service (GitHub out of requests) is not the project's
            # fault: drop it from the queue, but let it come back.
            _entries.pop(k)
    if len(_entries) > MAX_ENTRIES:
        for k in sorted(_entries, key=lambda k: _entries[k].get("found_at", 0))[:len(_entries) - MAX_ENTRIES]:
            _entries.pop(k)
    for k, at in list(_gone.items()):
        if now - at > 30 * 86400:
            del _gone[k]


# -------------------------------------------------------------- classifica

def true_cap(e: dict) -> float:
    """The larger of the pool's cap, the contract's global cap (CoinGecko) and
    the cap of the top coin this token is a copy of (bridged AAVE)."""
    return max(float(e.get("market_cap") or 0), float(e.get("global_cap") or 0), big_coins.cap_of(e))


def too_big(e: dict) -> str:
    """Why a token is not a small cap at all: a port from another chain or
    a cap over the ceiling (pool, CoinGecko, or the top coin it copies)."""
    if big_coins.bridged(e):
        return "bridged copy of a coin from another chain"
    if true_cap(e) > BOARD_CAP_MAX_USD:
        return f"over ${BOARD_CAP_MAX_USD / 1e6:.0f}M (${true_cap(e) / 1e6:,.0f}M)"
    return ""


# The gem rule chain (29/09, Lorenzo: "stai facendo un po' di casino delle
# scelte"): one chain for every source, no age anywhere. Hard safety first:
# a bridged copy or a cap over BOARD_CAP_MAX_USD ($10M, pool, CoinGecko or
# the top coin copied) is not a small cap; a DeepSeek board review that
# dropped the project holds for its TTL; the researcher's floor wants a name
# and a tradeable pool. Then the analysis: a fatal pillar (rug, fork, empty
# site) is out, a missing pillar waits. DeepSeek's judge vetoes an
# avoid/scam verdict it is sure of, and admits a gem/watch verdict with a
# high score past the quality bars below. The quality bar: every pillar at
# its PILLAR_FLOOR, the same with or without public code (no code costs
# NO_GITHUB_PENALTY in the score instead). Since 07/10 the usage bars
# (usage_gate) come first and the $2M score band is gone: a token under
# TOP_CAP_MIN_USD that passes everything else goes to the early list. Holders that are contracts (pools, vesting) are not "a single
# wallet" in the tokenomics pillar (depth.judge_tokenomics_evm).
def _ramp(x: float, lo: float, hi: float) -> float:
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def wallet_top10(e: dict) -> float | None:
    """The top 10 wallets' share (EVM contracts and Solana program accounts
    left out, depth.py), or None:
    GeckoTerminal's split counts pools and contracts and cannot judge this."""
    f = ((e.get("pillars") or {}).get("tokenomics") or {}).get("facts") or {}
    return f.get("top10_pct") if f.get("source") != "geckoterminal" else None


def usage_gate(e: dict, cap_floor: bool = True) -> str:
    """"" unless the token is plainly unused, shrinking or held by a few
    wallets. Low volume alone is not a reason (hidden gems): it weighs in
    the score. Not measured yet passes: unknown is not zero."""
    cap = true_cap(e)
    if cap_floor and cap and cap < TOP_CAP_MIN_USD:
        return f"under ${TOP_CAP_MIN_USD / 1e3:.0f}k (early list)"
    m = usage.latest(e.get("chain"), e.get("token_address"))
    if m and time.time() - (m.get("at") or 0) <= USAGE_STALE_S:
        vol = m.get("vol_7d_avg") if m.get("vol_7d_avg") is not None else m.get("vol_24h")
        buyers = m.get("buyers_24h")
        if vol is not None and vol < USAGE_DEAD_VOL_USD and buyers is not None and buyers < USAGE_DEAD_BUYERS:
            return f"nobody trades it: ${vol:,.0f} a day, {buyers} buyers"
        if m.get("holders") is not None and m["holders"] < USAGE_HOLDERS_MIN:
            return f"{m['holders']} holders (needs {USAGE_HOLDERS_MIN})"
    growth = usage.holders_growth(e.get("chain"), e.get("token_address"), 30)
    if growth is not None and growth < -USAGE_SHRINK_MAX:
        return f"holders {growth:+.0%} in 30 days"
    top10 = wallet_top10(e)
    if top10 is not None and top10 >= USAGE_TOP10_MAX_PCT:
        return f"top 10 wallets hold {top10:.0f}% (max {USAGE_TOP10_MAX_PCT:.0f}%)"
    return ""


def qualifies(e: dict, now: float | None = None, cap_floor: bool = True) -> str:
    """"" se entra in classifica, altrimenti perche' no. cap_floor=False
    asks whether it would enter but for the $300k floor (the early list)."""
    if benchmark.is_benchmark(e.get("chain"), e.get("token_address")):
        # The yardstick skips caps and quality bars, never a fatal finding
        # (rug, honeypot, mint...): audit 29/09, M03.
        return (e.get("overall") or {}).get("fatal") or ""
    big = too_big(e)
    if big:
        return big
    r = e.get("review") or {}
    if r.get("keep") is False and (now or time.time()) - (r.get("at") or 0) < judge.REVIEW_TTL_S:
        return f"DeepSeek review: {r.get('reason') or 'dropped'}"
    floor = research_floor(e, now)
    if floor:
        return floor
    # Usage first: no report, review or narrative admits a token nobody trades.
    used = usage_gate(e, cap_floor)
    if used:
        return used
    o = e.get("overall") or {}
    pillars = e.get("pillars") or {}
    if not o or o.get("fatal"):
        return o.get("fatal") or "to be examined"
    if o.get("pending"):
        return o["pending"]
    closed = no_github(e)
    need = [k for k in depth.WEIGHTS if not (closed and k == "github")]
    if any((pillars.get(k) or {}).get("score") is None for k in need):
        return "incomplete analysis"
    j = e.get("judge") or {}
    if j.get("verdict") in ("avoid", "scam") and (j.get("confidence") or 0) >= judge.VETO_MIN_CONF:
        return f"DeepSeek: {(j.get('problems') or [j['verdict']])[0]}"
    # Admitting past the quality bars needs the same certainty as a veto
    # (audit 29/09, M05); fatal and pending were already checked above.
    if j.get("verdict") in ("gem", "watch") and (j.get("score") or 0) >= judge.ADMIT_MIN \
            and (j.get("confidence") or 0) >= judge.VETO_MIN_CONF and _fresh(j, judge.TTL_S, now):
        return ""
    # A site we could not read (JS shell, down) is unknown, not weak: no floor.
    weak = [k for k in need if pillars[k]["score"] < PILLAR_FLOOR[k]
            and not (pillars[k].get("facts") or {}).get("unreadable")]
    if weak:
        return f"{weak[0]} too weak ({pillars[weak[0]]['score']})"
    return ""


def no_name(symbol) -> bool:
    """A symbol nobody can read: missing, "?", or a JSON null that became
    the string "null" upstream (Lorenzo, 28/09: "ci sono ticker tra le top
    che si chiamano null")."""
    return str(symbol or "").strip().lower() in ("", "?", "null", "none", "undefined", "nan")


# Lorenzo, 18/10 ("come possiamo fare per intercettare progetti come Veil
# prima che spicchino il volo?"): a project launched less than YOUNG_DAYS ago
# goes first in the analysis queue and in the usage measure.
YOUNG_DAYS = 14


def young(e: dict, now: float | None = None) -> bool:
    born = e.get("launched_at")
    return bool(born) and (now or time.time()) - float(born) < YOUNG_DAYS * 86400


def research_floor(e: dict, now: float | None = None) -> str:
    """What a researcher would not even open: no name, a pool nobody can
    trade. Age is not a reason (29/09)."""
    if no_name(e.get("symbol")):
        return "no name"
    liq = e.get("liquidity_usd")
    small = float(e.get("market_cap") or 0) and float(e.get("market_cap") or 0) < EARLY_CAP_USD
    floor = EARLY_MIN_LIQUIDITY_USD if small else MIN_LIQUIDITY_USD
    if liq is not None and float(liq) < floor:
        return f"liquidity under ${floor // 1000}k"
    return ""


def is_early(e: dict, now: float | None = None) -> bool:
    """Under TOP_CAP_MIN_USD and passing every other bar, usage included
    (07/10: a list apart, never on the podium)."""
    cap = true_cap(e)
    if not cap or cap >= TOP_CAP_MIN_USD or benchmark.is_benchmark(e["chain"], e["token_address"]):
        return False
    return not qualifies(e, now, cap_floor=False)


def no_github(e: dict) -> bool:
    return bool(((e.get("pillars") or {}).get("github") or {}).get("facts", {}).get("missing"))


def _fresh(d: dict, ttl: float, now: float | None = None) -> bool:
    """An AI reading counts while it's recent (twice its cache TTL, so a
    late refresh doesn't make scores jump): audit 29/09, M04."""
    at = d.get("at")
    return bool(at) and (now or time.time()) - at < 2 * ttl


def usage_score(e: dict, growth: bool = False) -> float | None:
    """0-100: how much the token is traded and used. Volume against the cap,
    volume in dollars, distinct buyers; DefiLlama's TVL and fees when listed.
    `growth` (whitekobra) adds the holders' 30-day growth, when measurable."""
    m = usage.latest(e.get("chain"), e.get("token_address")) or {}
    use = traction_of(e)
    parts: list[tuple[float, float]] = []          # (weight, 0-1), only what was read
    vol = m.get("vol_7d_avg") if m.get("vol_7d_avg") is not None else m.get("vol_24h")
    cap = true_cap(e)
    if vol is not None:
        if cap:
            parts.append((45, _ramp(math.log10(max(vol / cap, 1e-6)), -2.3, -1)))      # 0.5% -> 0, 10% -> full
        parts.append((30, _ramp(math.log10(max(vol, 1)), math.log10(USAGE_VOL_LO_USD), 6)))   # $25k -> $1M
    if m.get("buyers_24h") is not None:
        parts.append((25, _ramp(math.log10(max(m["buyers_24h"], 1)), math.log10(USAGE_BUYERS_LO), 3)))  # 30 -> 1,000
    elif m.get("tx_24h") is not None:
        parts.append((25, _ramp(math.log10(max(m["tx_24h"], 1)), math.log10(USAGE_TX_LO), 3.5)))
    if growth:
        g = usage.holders_growth(e.get("chain"), e.get("token_address"), 30)
        if g is not None:
            parts.append((KOBRA_GROWTH_WEIGHT, _ramp(g, -0.05, 0.30)))      # -5% -> 0, +30% -> full
    if not parts and not use:
        return None
    pts = 100 * sum(w * x for w, x in parts) / sum(w for w, _ in parts) if parts else 0.0
    return round(max(pts, use["traction"] if use else 0.0), 1)


def participation_score(e: dict) -> float | None:
    """0-100: how many hold it and whether that grows."""
    m = usage.latest(e.get("chain"), e.get("token_address"))
    if not m or m.get("holders") is None:
        return None
    pts = 60 * _ramp(math.log10(max(m["holders"], 1)), math.log10(USAGE_HOLDERS_LO), 4.5)   # 500 -> 30k
    growth = usage.holders_growth(e.get("chain"), e.get("token_address"), 30)
    pts += 40 * (0.5 if growth is None else _ramp(growth, -0.05, 0.30))
    return round(pts, 1)


def product_score(e: dict) -> float | None:
    """0-100: research (site, docs, app), public code and DeepSeek's code reading."""
    pillars = e.get("pillars") or {}
    parts = [pillars[k]["score"] for k in ("site", "github")
             if (pillars.get(k) or {}).get("score") is not None and not (k == "github" and no_github(e))]
    c = e.get("code") or {}
    if c.get("complexity") is not None and c.get("innovation") is not None and _fresh(c, code_review.TTL_S):
        parts.append((c["complexity"] + c["innovation"]) / 2)
    return round(sum(parts) / len(parts), 1) if parts else None


def deepseek_score(e: dict) -> float | None:
    """0-100: DeepSeek's report and its board review, when fresh."""
    parts = []
    j = e.get("judge") or {}
    if j.get("score") is not None and _fresh(j, judge.TTL_S):
        parts.append(j["score"])
    r = e.get("review") or {}
    if r.get("keep") and r.get("score") is not None and _fresh(r, judge.REVIEW_TTL_S):
        parts.append(r["score"])
    return sum(parts) / len(parts) if parts else None


def hidden_gem(e: dict) -> bool:
    """A strong product the market has not found yet: what the Gem Finder is
    for (Lorenzo, 07/10). A label on the row, never a reason to drop it; only
    on a measured market (unmeasured is unknown, not hidden)."""
    b = score_blocks(e)
    return (b["product"] or 0) >= HIDDEN_PRODUCT_MIN and b["usage"] is not None and b["usage"] <= HIDDEN_USAGE_MAX


def score_blocks(e: dict, kobra: bool = False) -> dict:
    tok = ((e.get("pillars") or {}).get("tokenomics") or {}).get("score")
    if kobra:
        return {"usage": usage_score(e, growth=True), "product": product_score(e), "token": tok,
                "deepseek": deepseek_score(e)}
    return {"usage": usage_score(e), "participation": participation_score(e), "product": product_score(e),
            "token": tok, "deepseek": deepseek_score(e)}


def final_score(e: dict, kobra: bool = False) -> float:
    """The weights of SCORE_WEIGHTS (or KOBRA_SCORE_WEIGHTS) over the blocks
    that could be measured. Closed code costs NO_GITHUB_PENALTY (or
    KOBRA_NO_GITHUB_PENALTY); DREGG's likeness and the narrative are labels,
    no longer points."""
    weights = KOBRA_SCORE_WEIGHTS if kobra else SCORE_WEIGHTS
    blocks = score_blocks(e, kobra)
    have = {k: v for k, v in blocks.items() if v is not None and k in weights}
    if not have:
        return 0.0
    w = sum(weights[k] for k in have)
    base = sum(weights[k] * v for k, v in have.items()) / w
    if no_github(e):
        base -= KOBRA_NO_GITHUB_PENALTY if kobra else NO_GITHUB_PENALTY
    rules = round(max(0.0, min(100.0, base)), 1)
    if gem_learn.approved():
        p = gem_learn.chance(score_parts(e, early=False))
        if p is not None:
            rules = round((1 - gem_learn.LEARNED_WEIGHT) * rules + gem_learn.LEARNED_WEIGHT * 100 * p, 1)
    return rules


def score_parts(e: dict, now: float | None = None, early: bool = True) -> dict:
    """Every input of final_score as it stands, for the decision receipt
    (gem_track) and for measuring which of them predicts (gem_learn)."""
    now = now or time.time()
    pillars = e.get("pillars") or {}
    use = traction_of(e) or {}
    j = e.get("judge") or {}
    j = j if j.get("score") is not None and _fresh(j, judge.TTL_S, now) else {}
    c = e.get("code") or {}
    c = c if c.get("complexity") is not None and _fresh(c, code_review.TTL_S, now) else {}
    r = e.get("review") or {}
    r = r if r.get("keep") and r.get("score") is not None and _fresh(r, judge.REVIEW_TTL_S, now) else {}
    m = usage.latest(e.get("chain"), e.get("token_address")) or {}
    blocks = score_blocks(e)
    launched = e.get("launched_at")
    return {"quality": (e.get("overall") or {}).get("score"),
            **{f"pillar_{n}": (pillars.get(n) or {}).get("score") for n in ("github", "site", "tokenomics")},
            **{f"block_{k}": v for k, v in blocks.items()},
            "vol_7d_avg": m.get("vol_7d_avg"), "tx_24h": m.get("tx_24h"), "buyers_24h": m.get("buyers_24h"),
            "holders": m.get("holders"),
            "similarity": (e.get("similarity") or {}).get("score"), "closed_source": int(no_github(e)),
            "traction": use.get("traction"), "value": use.get("value"),
            "narrative_bonus": narratives.bonus(e.get("narratives") or []),
            "judge": j.get("score"), "judge_confidence": j.get("confidence"),
            "code": (c["complexity"] + c["innovation"]) / 2 if c.get("innovation") is not None else None,
            "review": r.get("score"),
            "mcap": true_cap(e) or e.get("market_cap"), "liq": e.get("liquidity_usd"),
            "age_d": round((now - launched) / 86400, 2) if launched else None,
            "change_24h": e.get("change_24h"), "text_moved": int(bool(e.get("text_moved"))), "early": int(is_early(e, now)) if early else None,
            "chain": e.get("chain")}


def rules_version() -> str:
    """The hand weights in force, as a short hash: a receipt says which rules chose."""
    rules = {"blocks": SCORE_WEIGHTS, "no_github": NO_GITHUB_PENALTY, "floor": PILLAR_FLOOR,
             "usage_gates": [TOP_CAP_MIN_USD, USAGE_DEAD_VOL_USD, USAGE_DEAD_BUYERS, USAGE_HOLDERS_MIN,
                             USAGE_SHRINK_MAX, USAGE_TOP10_MAX_PCT],
             "learned": gem_learn.approved_hash()}
    return gem_track.receipt_of({"parts": rules})[:16]


def traction_of(e: dict) -> dict | None:
    if not e.get("chain") or not e.get("token_address"):
        return None
    return traction.judge(traction.lookup(e["chain"], e["token_address"]), e.get("market_cap"))


def _rank() -> None:
    from app.trading.onchain import history
    # By score only (Lorenzo, 27/09: "nel podio compaiono token con punteggi
    # piu' bassi rispetto a quelli presenti in database"): the benchmark keeps
    # its honorable mention, no longer the first place by decree.
    ranked = sorted((e for e in _entries.values() if not qualifies(e)),
                    key=lambda e: (-final_score(e), -(e.get("launched_at") or 0)))[:BOARD_SIZE]
    order = [_key(e["chain"], e["token_address"]) for e in ranked]
    now = time.time()
    for i, e in enumerate(ranked, 1):
        gem_track.enter(e, final_score(e), i, now, score_parts(e, now), rules_version())
        k = _key(e["chain"], e["token_address"])
        # "new" is the Top's (queue_top_news); the board flags early ones only.
        tag = f"early:{k}"
        if is_early(e, now) and tag not in _alerted:
            _alerted.add(tag)
            if not _priming and not benchmark.is_benchmark(e["chain"], e["token_address"]):
                _outbox.append(("early", k))
        if e.get("rank") != i:
            e["rank_before"], e["rank"], e["moved_at"] = e.get("rank"), i, now
            history.append(k, "leaderboard.rank", {"moved_at": now, "rank": i, "rank_before": e["rank_before"]}, now)
    for k, e in _entries.items():
        if k not in order and e.get("rank") is not None:
            e["rank_before"], e["rank"], e["moved_at"] = e["rank"], None, now
            history.append(k, "leaderboard.rank", {"moved_at": now, "rank": None, "rank_before": e["rank_before"]}, now)
    if order != _state["board"]:
        _state["board"] = order
    _sync_database(order)


def _sync_database(order: list[str]) -> None:
    """Keep the database's score and "Ranked" in step with the board: DeepSeek's
    report, review and code reading move the score after the analysis was saved
    (Lorenzo, 28/09: three at 93 in the database, off the podium)."""
    board = set(order)
    # Once the Top has been synced (sync_top), "ranked" means "in the Top":
    # the board only moves scores, it no longer demotes what the Top holds.
    if not _state.get("top_synced_at") and board != set(_state.get("db_board") or []):
        try:
            projects_db.demote_ranked(board)
            _state["db_board"] = sorted(board)
        except Exception:
            logger.exception("classifica: stato ranked non riallineato")
    for k, e in _entries.items():
        o = e.get("overall") or {}
        if not o or o.get("fatal") or o.get("pending"):
            continue
        status, rank = _place(k, e.get("rank"))
        score = final_score(e)
        if k not in _recorded:
            # Once per start: a row still "rejected" under an old check (BV7X, "single
            # wallet 41%") is not moved by set_standing, which only touches studied
            # and ranked rows. A working-set entry with no fatal pillar is studied.
            _recorded.add(k)
            try:
                projects_db.lift_rejected(e["chain"], e["token_address"])
            except Exception:
                logger.exception("classifica: riga rifiutata non riaperta per %s", e.get("symbol"))
        seen = (status, score, rank)
        if e.get("_db") == list(seen):
            continue
        try:
            projects_db.set_standing(e["chain"], e["token_address"], status, score, rank,
                                     "" if status == "ranked" else qualifies(e))
        except Exception:
            logger.exception("classifica: posizione non salvata per %s", e.get("symbol"))
            continue
        e["_db"] = list(seen)


def _mark() -> None:
    global _dirty
    _dirty = True
    _state["version"] += 1
    _rank()


def _public(e: dict) -> dict:
    keep = ("chain", "token_address", "pair_address", "symbol", "name", "source", "launched_at", "found_at",
            "market_cap", "liquidity_usd", "change_24h", "website", "github", "socials", "pair_url", "scan_url",
            "image", "bonding", "rank", "rank_before", "moved_at", "overall", "pillars", "checked_at")
    top = benchmark.is_benchmark(e["chain"], e["token_address"])
    return {**{k: e.get(k) for k in keep}, "market_cap": true_cap(e) or e.get("market_cap"),
            "exception": is_big(e) and not top, "score": final_score(e),
            "similarity": e.get("similarity"), "benchmark": top, "early": is_early(e), "price_usd": e.get("price_usd"),
            "narratives": narratives.labels(e.get("narratives") or []), "closed_source": no_github(e),
            "text_moved": e.get("text_moved"), "usage": usage.latest(e.get("chain"), e.get("token_address")),
            "hidden": hidden_gem(e),
            "blocks": score_blocks(e),
            **_research_public(e), "honor": benchmark.HONOR if top else None, "traction": traction_of(e),
            "review": {k: (e.get("review") or {}).get(k) for k in ("keep", "score", "reason")} if e.get("review") else None,
            "judge": {k: (e.get("judge") or {}).get(k)
                      for k in ("score", "verdict", "problems", "strengths", "admit_reason", "x", "tg", "drift")} if e.get("judge") else None,
            "code": {k: (e.get("code") or {}).get(k)
                     for k in ("complexity", "innovation", "fork_of", "summary", "strengths", "concerns")}
            if e.get("code") else None}


def _research_public(e: dict) -> dict:
    f = ((e.get("pillars") or {}).get("site") or {}).get("facts") or {}
    return {"summary": f.get("summary") or None, "stage": f.get("stage"), "verdict": f.get("verdict")}


CLOSE_SIZE = 6


def close_calls(now: float | None = None) -> list[dict]:
    """The projects nearest the board and what keeps each out: past the
    researcher's floor, ranked by their research score."""
    out = []
    for k, e in _entries.items():
        if k in _state["board"] or research_floor(e, now):
            continue
        site = (e.get("pillars") or {}).get("site") or {}
        out.append({"symbol": e.get("symbol"), "name": e.get("name"), "chain": e.get("chain"),
                    "token_address": e.get("token_address"), "market_cap": e.get("market_cap"),
                    "research": site.get("score"), "verdict": (site.get("facts") or {}).get("verdict"),
                    "why": qualifies(e, now) or "ranking"})
    out.sort(key=lambda x: -(x["research"] if x["research"] is not None else -1))
    return out[:CLOSE_SIZE]


EARLY_SIZE = 15


def early_list() -> list[dict]:
    """Under $300k and past every other bar, best first: never on the podium."""
    early = [e for e in _entries.values() if not no_name(e.get("symbol")) and is_early(e)]
    early.sort(key=lambda e: -final_score(e))
    return [_public(e) for e in early[:EARLY_SIZE]]


def board() -> dict:
    entries = [_entries[k] for k in _state["board"] if k in _entries and not no_name(_entries[k].get("symbol"))]
    waiting = sum(1 for k, e in _entries.items() if k not in _state["board"])
    return {
        "version": _state["version"], "updated_at": _state["last_tick"] or None,
        "entries": [_public(e) for e in entries],
        "early": early_list(),
        "examined": _state["examined"], "analyzing": len(_busy), "waiting": waiting,
        "excluded": _excluded[:20], "excluded_total": len(_gone),
        "sources": _state["sources"], "discovery": discovery.status(),
        "github_rate": legit.github_rate or None,
        "research_ai": research.ai_status(), "close": close_calls(),
        "track": gem_track.stats(), "learning": gem_learn.status(), "defillama": traction.status(), "database": projects_db.stats(),
        "past_floor": sum(1 for e in _entries.values() if not research_floor(e)),
        "nightly": _nightly_status(),
        "rules": {"score_weights": SCORE_WEIGHTS, "top_cap_min_usd": TOP_CAP_MIN_USD,
                  "usage_dead_vol_usd": USAGE_DEAD_VOL_USD, "usage_dead_buyers": USAGE_DEAD_BUYERS,
                  "usage_shrink_max": USAGE_SHRINK_MAX,
                  "usage_holders_min": USAGE_HOLDERS_MIN, "usage_top10_max_pct": USAGE_TOP10_MAX_PCT,
                  "benchmark": benchmark.NAME, "min_pillar": MIN_PILLAR,
                  "board_cap_max_usd": BOARD_CAP_MAX_USD, "pillar_floor": PILLAR_FLOOR},
    }


def _nightly_status() -> dict | None:
    try:
        from app.trading.onchain import nightly
        return nightly.status()
    except Exception:
        logger.exception("classifica: stato del giro serale illeggibile")
        return None


# -------------------------------------------------------------------- giro

async def _step(name: str, fn, *args) -> None:
    try:
        await fn(*args)
        _state["sources"][name] = {"ok": True, "at": time.time()}
    except Exception as exc:
        _state["sources"][name] = {"ok": False, "at": time.time(), "error": type(exc).__name__}
        logger.info("classifica: %s non riuscito: %s", name, exc)


def on_alert(fn) -> None:
    """fn(kind, public_entry) is awaited for a project new on the board
    ("new") or flagged early ("early"). Telegram lives in main.py."""
    _alert_hooks.append(fn)


def on_flush(fn) -> None:
    """fn() is awaited at the end of flush_alerts: what the alert hooks held
    back (main.py: the gems over the hourly cap) goes out there."""
    _flush_hooks.append(fn)


def queue_top_news(top: list[dict]) -> int:
    """Queues a "new" alert for each project in `top` (the Top's gated pool,
    best first) never announced before. The first look only takes note: a
    deploy must not announce the whole Top. Returns the alerts queued."""
    global _top_primed, _dirty
    queued = 0
    for t in top:
        k = _key(t["chain"], t["token_address"])
        # Its own tag, not "new:": until 17/10 _rank() marked "new:" every
        # project that entered the board's internal ranking (1225 on the
        # server), so almost every gem entering the Top was skipped as
        # already announced (Lorenzo, 17/10: 8 entered at 18:00, no message).
        if f"top:{k}" in _alerted:
            continue
        _alerted.add(f"top:{k}")
        _dirty = True
        if _top_primed and not benchmark.is_benchmark(t["chain"], t["token_address"]):
            _outbox.append(("new", k))
            queued += 1
    if not _top_primed:
        _top_primed, _dirty = True, True
    return queued


def is_pearl(e: dict) -> bool:
    return is_early(e) and round(final_score(e)) >= PEARL_MIN


def queue_pearl_news() -> int:
    """Queues a "pearl" alert for each gem new to Pearl (the early list at
    PEARL_MIN and up, what top.js paintPearl shows). First look: note only."""
    global _pearl_primed, _dirty
    queued = 0
    for t in early_list():
        if round(t.get("score") or 0) < PEARL_MIN:
            continue
        k = _key(t["chain"], t["token_address"])
        if f"pearl:{k}" in _alerted:
            continue
        _alerted.add(f"pearl:{k}")
        _dirty = True
        if _pearl_primed:
            _outbox.append(("pearl", k))
            queued += 1
    if not _pearl_primed:
        _pearl_primed, _dirty = True, True
    return queued


# The rankings a gem can appear in, by the tag its alert leaves: the arenas
# and the Top ("top:"), Early ("early:"), Pearl ("pearl:", inside Early).
_RANKING_TAGS = {"new": "top", "early": "early", "pearl": "pearl"}


def first_in_any_ranking(kind: str, k: str) -> bool:
    """True when the gem had never been in another ranking: a project moving
    from Early to the Top, or into Pearl, is not new (Lorenzo, 17/10: "Solo
    quando una gemma non presente nelle classifiche, qualsiasi sia, allora
    scatta la notifica")."""
    return not any(f"{tag}:{k}" in _alerted for other, tag in _RANKING_TAGS.items() if other != kind)


async def drain_alerts() -> int:
    sent = 0
    # The place announced is the Top's, the list the app shows: the board's
    # own rank ignores the database rows mixed into the Top (Lorenzo, 29/09:
    # "PFWA posto 4" on Telegram, Covenant 4th in the app).
    top = _top_source(TOP_ALERT_POOL) if _top_source and any(kind == "new" for kind, _ in _outbox) else []
    places = {_key(t["chain"], t["token_address"]): (i, t) for i, t in enumerate(top, 1)}
    while _outbox and sent < ALERTS_PER_TICK:
        kind, k = _outbox.pop(0)
        e = _entries.get(k)
        if kind in ("early", "pearl"):
            # Under the Top's floor by definition: never in the Top (07/10).
            if e is None or not (is_pearl(e) if kind == "pearl" else is_early(e)):
                continue
            item = _public(e)
        else:
            if k not in places:
                continue            # left the Top before its turn
            place, row = places[k]
            item = _public(e) if e is not None else dict(row)
            item["rank"] = place
        item["first_seen"] = first_in_any_ranking(kind, k)
        for fn in list(_alert_hooks):
            try:
                await fn(kind, item)
            except Exception:
                logger.exception("classifica: avviso %s fallito", k)
        sent += 1
    return sent


async def flush_alerts(now: float | None = None) -> int:
    """Everything new in the Top or in Pearl, queued and sent now, not five a
    tick. The nightly run's ticks stop before the run does: what the last
    readings, the settle and the deep re-check put in the Top was announced
    at the next run at best (Lorenzo, 17/10: the 18:00 run listed new gems
    in its summary, the gems chat heard nothing)."""
    if _top_source is not None:
        await _sync_top(now or time.time())
    sent = 0
    while _outbox:              # every drain pops at least one: this ends
        sent += await drain_alerts()
    for fn in list(_flush_hooks):
        try:
            await fn()
        except Exception:
            logger.exception("classifica: chiusura degli avvisi fallita")
    if _dirty:
        _save()
    return sent


async def _db_market(client: httpx.AsyncClient, now: float) -> None:
    """Cap and liquidity for the database, oldest first: this is what puts a
    project known only by name into the band, or out of it."""
    for chain, tokens in projects_db.stale_market(DB_MARKET_BATCH, now).items():
        for i in range(0, len(tokens), 30):
            batch = tokens[i:i + 30]
            r = await client.get(DEX_TOKENS.format(chain=chain, addresses=",".join(batch)), timeout=10.0)
            if r.status_code == 200 and isinstance(r.json(), list):
                projects_db.apply_pairs(chain, batch, r.json(), now)
            await asyncio.sleep(0.3)


def _make_room(n: int, now: float) -> int:
    """Send the n weakest analysed entries outside the Top back to the database."""
    idle = [k for k, e in _entries.items()
            if e.get("pillars") and not (e.get("overall") or {}).get("pending") and k not in _busy
            and k not in _top_rank and not e.get("rank")
            and not benchmark.is_benchmark(e["chain"], e["token_address"])]
    idle.sort(key=lambda k: (final_score(_entries[k]), max((_entries[k].get("checked_at") or {}).values(), default=0)))
    for k in idle[:n]:
        e = _entries.pop(k)
        _remember(e, "studied", qualifies(e, now), now)
    return min(n, len(idle))


def feed_from_database(now: float | None = None) -> int:
    """Move the next projects from the database into the working set, while
    the analysis queue has room: never analysed first, then second looks."""
    now = now or time.time()
    projects_db.reject_linkless(now)
    waiting = sum(1 for e in _entries.values() if not e["pillars"])
    if waiting >= DB_FEED_MAX_WAITING:
        return 0
    due = projects_db.due_for_analysis(DB_FEED_PER_TICK * 3, set(_entries), now)
    if due and len(_entries) >= MAX_ENTRIES:
        # A full set used to stop the feed for good: the 400 places went to
        # whoever came first and AUREON, PFWA, GRID never got one (29/09).
        # Analysed projects outside the Top step back into the database.
        _make_room(min(len(due), DB_FEED_PER_TICK), now)
    if len(_entries) >= MAX_ENTRIES:
        return 0
    fed = 0
    for p in due:
        item = projects_db.as_item(p)
        if _looks_like_meme(item["symbol"], item["name"]):
            projects_db.record(item, "rejected", "meme name", now=now)
            continue
        if add(item, "database", now):
            fed += 1
        if fed >= DB_FEED_PER_TICK:
            break
    return fed


async def _from_database(client: httpx.AsyncClient, now: float) -> None:
    if now - _state.get("db_market_at", 0.0) >= DB_MARKET_S:
        _state["db_market_at"] = now
        await _db_market(client, now)
    feed_from_database(now)


async def tick(client: httpx.AsyncClient, now: float | None = None, light: bool = False) -> None:
    """`light` is the sentinel's tick (nightly.sentinel_loop): the fast
    sources, the analysis of new and young projects, their usage, the Top
    and its alerts; the database feed, DeepSeek's readings, the audits and
    the CoinGecko sweep wait for the research runs."""
    now = now or time.time()
    _state["last_tick"] = now
    try:
        collect_saved()
    except Exception:
        logger.exception("classifica: lettura del radar fallita")
    # The fast sources always run (18/10: the pause had stopped them since
    # the pool passed POOL_TARGET); the pause holds the CoinGecko sweep only.
    await _step("progetti", discovery.tick, client, add, now, not light and discovery_open(now))
    if now - _state["last_market"] >= MARKET_POLL_S and _entries:
        _state["last_market"] = now
        await _step("dexscreener", _poll_market, client)
    await _step("storico", gem_track.poll, client, set(_entries), now)
    if not light:
        await _step("pagella", asyncio.to_thread, gem_learn.refresh, now)
        await _step("database", _from_database, client, now)
        await _step("grandi monete", _refresh_big_coins, client, now)
    await _step("cap globale", _check_global_cap, client, now)
    if light:
        await _step("uso", _measure_usage, client, USAGE_PER_TICK, [e for e in usage_candidates() if young(e, now)])
    else:
        await _step("uso", _measure_usage, client)
    if not light and not _state.get("reviewing") and not priority.backtests_first():
        task = asyncio.create_task(_step("revisione", _review_board, now))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    if not light and not _state.get("code_reading"):
        task = asyncio.create_task(_step("codice", _read_code, client, now))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    if not _state.get("top_filling") and _top_source is not None \
            and now - _state.get("top_fill_at", 0.0) >= TOP_FILL_EVERY_S:
        task = asyncio.create_task(_step("top", top_fill, client, now))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    if _top_source is not None and now - _state.get("top_synced_at", 0.0) >= TOP_SYNC_EVERY_S:
        await _step("top sync", _sync_top, now)
    if not light and not _state.get("auditing") and consistency.due(now):
        task = asyncio.create_task(_step("coerenza", _audit, now))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    if not light and not _state.get("narr_mapping"):
        task = asyncio.create_task(_step("narrative", _map_narratives, now))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    await drain_alerts()
    _prune(now)
    # I nuovi prima (nessun pilastro), fra questi i progetti giovani, poi i
    # piu' vecchi da rinfrescare.
    todo = sorted(((k, due(e, now)) for k, e in _entries.items() if k not in _busy),
                  key=lambda kv: (bool(_entries[kv[0]]["pillars"]), not young(_entries[kv[0]], now),
                                  -_entries[kv[0]].get("found_at", 0)))
    for k, need in todo:
        if not need or len(_busy) >= ANALYZE_CONCURRENCY * 2:
            continue
        if light and _entries[k]["pillars"] and not young(_entries[k], now):
            continue            # refreshing the old ones is the research runs' job
        _busy.add(k)
        task = asyncio.create_task(_analyze(k, set(STALE_S) - need, client))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    if _dirty:
        _save()


USAGE_DB_ROWS = 200                  # studied database rows measured too (the Top's other half)


def usage_candidates() -> list[dict]:
    """What usage.py measures once a day: the projects past the researcher's
    floor and under the ceiling, board first, then the studied database
    rows the Top reads (straight from the database: the Top itself drops
    the unmeasured ones, so it cannot be the source). Only chains with a
    DEX pool to measure (no layers)."""
    items = [e for k, e in _entries.items() if not research_floor(e) and not too_big(e)]
    now = time.time()
    items.sort(key=lambda e: (not young(e, now), _key(e["chain"], e["token_address"]) not in _state["board"],
                              -final_score(e)))
    seen = {_key(e["chain"], e["token_address"]) for e in items}
    cutoff = time.time() - 30 * 86400
    try:
        rows = [r for st in ("studied", "ranked")
                for r in projects_db.search(status=st, sort="score", limit=USAGE_DB_ROWS)["items"]]
    except Exception:
        logger.exception("usage: database rows not read")
        rows = []
    for r in sorted(rows, key=lambda r: -(r.get("score") or 0)):
        if (r.get("analyzed_at") or 0) < cutoff or _key(r["chain"], r["token"]) in seen:
            continue
        seen.add(_key(r["chain"], r["token"]))
        items.append({"chain": r["chain"], "token_address": r["token"], "pair_address": r.get("pair")})
    return [e for e in items if e["chain"] in research.GECKO_NET][:USAGE_WARM_MAX + USAGE_DB_ROWS]


async def _measure_usage(client: httpx.AsyncClient, limit: int | None = USAGE_PER_TICK,
                         items: list[dict] | None = None) -> int:
    """Volume, trades and holders once a day (usage.py); the board is
    re-ranked when anything new came in."""
    items = usage_candidates() if items is None else items
    n = await usage.refresh(client, items, limit) if items else 0
    if n:
        _mark()
    return n


async def warm_usage(limit: int = USAGE_WARM_MAX) -> int:
    """At start-up, the candidates with no usable snapshot at all (none, or
    older than USAGE_STALE_S): usage_gate keeps them off the Top, so the
    first deploy would leave it empty until the night's run. Tokens measured
    on an earlier day wait for the night, as planned."""
    now = time.time()
    todo = [e for e in usage_candidates()
            if now - ((usage.latest(e["chain"], e["token_address"]) or {}).get("at") or 0) > USAGE_STALE_S]
    async with http_client.pooled(timeout=20) as client:
        return await _measure_usage(client, limit, todo)


async def _refresh_big_coins(client: httpx.AsyncClient, now: float) -> None:
    if await big_coins.refresh(client, now):
        _mark()     # re-rank at once: a copy of a top coin leaves the board now


async def _check_global_cap(client: httpx.AsyncClient, now: float) -> None:
    """One CoinGecko lookup: the board first, then the rest past the floor."""
    if now < _state.get("cap_next_at", 0):
        return
    _state["cap_next_at"] = now + GLOBAL_CAP_EVERY_S
    board = set(_state["board"])
    todo = [k for k, e in _entries.items()
            if now - (e.get("global_cap_at") or 0) > GLOBAL_CAP_TTL_S and not research_floor(e, now)
            and CG_PLATFORM.get(e.get("chain")) and not benchmark.is_benchmark(e["chain"], e["token_address"])]
    if not todo:
        return
    k = min(todo, key=lambda k: (k not in board, -(float(_entries[k].get("market_cap") or 0))))
    e = _entries[k]
    r = await client.get(CG_CONTRACT.format(platform=CG_PLATFORM[e["chain"]], address=e["token_address"]),
                         timeout=15.0, headers={"Accept": "application/json"})
    if r.status_code == 429:
        _state["cap_next_at"] = now + 120
        return
    md = (r.json().get("market_data") or {}) if r.status_code == 200 else {}
    e["global_cap"] = max(float((md.get("market_cap") or {}).get("usd") or 0),
                          float((md.get("fully_diluted_valuation") or {}).get("usd") or 0)) or None
    e["global_cap_at"] = now
    _mark()


async def _review_board(now: float) -> None:
    """DeepSeek challenges the board as a whole (Lorenzo, 28/09)."""
    keys = [k for k in _state["board"] if k in _entries
            and not benchmark.is_benchmark(_entries[k]["chain"], _entries[k]["token_address"])]
    last = _state.get("reviewed_at", 0)
    changed = set(keys) != set(_state.get("reviewed_board") or [])
    if not keys or _state.get("reviewing") or now - last < (REVIEW_MIN_GAP_S if changed else REVIEW_EVERY_S):
        return
    _state["reviewing"] = True
    try:
        res = await judge.review_board([_entries[k] for k in keys], now)
    finally:
        _state["reviewing"] = False
    _state["reviewed_at"], _state["reviewed_board"] = now, keys
    for k, v in res.items():
        if k in _entries:
            _entries[k]["review"] = v
    if res:
        _mark()


def pool_status(now: float | None = None) -> dict:
    """The pool (projects past the filters, in the database) and what is
    still missing on the ones in the working set."""
    now = now or time.time()
    try:
        by = projects_db.stats().get("by_status") or {}
    except Exception:
        by = {}
    pool = int(by.get("studied", 0)) + int(by.get("ranked", 0))
    waiting = reports = code = done = 0
    for e in _entries.values():
        o = e.get("overall") or {}
        if not e.get("pillars") or o.get("pending"):
            waiting += 1
            continue
        if o.get("fatal") or research_floor(e, now):
            continue
        # With the research's DeepSeek off (settings.research_ai_enabled) no
        # report is coming: waiting for one paused discovery for good (18/10).
        miss_report = settings.research_ai_enabled and not e.get("judge")
        has_repo = bool((((e.get("pillars") or {}).get("github") or {}).get("facts") or {}).get("repo"))
        miss_code = has_repo and not e.get("code")
        reports += miss_report
        code += miss_code
        done += not (miss_report or miss_code)
    backlog = waiting + reports + code
    return {"pool": pool, "target": POOL_TARGET, "waiting": waiting, "reports": reports, "code": code,
            "complete": done, "backlog": backlog,
            "paused": pool >= POOL_TARGET and backlog > BACKLOG_LOW}


def discovery_open(now: float) -> bool:
    """Scan for new projects only while the pool is small, or slowly once
    what we have is nearly complete."""
    st = pool_status(now)
    _state["pool"] = st
    if st["pool"] < POOL_TARGET:
        return True
    if st["paused"]:
        return False
    if now - _state.get("slow_scan_at", 0.0) < DISCOVERY_SLOW_S:
        return False
    _state["slow_scan_at"] = now
    return True


async def _read_code(client: httpx.AsyncClient, now: float) -> None:
    """DeepSeek legge il codice di un progetto per volta (Lorenzo, 28/09)."""
    if _state.get("code_reading") or now - _state.get("code_at", 0.0) < CODE_EVERY_S:
        return
    _state["code_at"] = now
    board = set(_state["board"])
    todo = []
    for k, e in _entries.items():
        gh = (e.get("pillars") or {}).get("github") or {}
        if not (gh.get("facts") or {}).get("repo"):
            continue
        c = e.get("code") or {}
        if c and now - (c.get("at") or 0) < code_review.TTL_S:
            continue
        if now - (e.get("code_tried_at") or 0) < CODE_RETRY_S:
            continue
        if k in board or not research_floor(e, now) or benchmark.is_benchmark(e["chain"], e["token_address"]):
            todo.append(k)
    if not todo:
        return
    k = min(todo, key=lambda k: (k not in board, -(float(_entries[k].get("market_cap") or 0))))
    e = _entries[k]
    e["code_tried_at"] = now
    _state["code_reading"] = True
    try:
        result = await code_review.review(e, client, now)
    finally:
        _state["code_reading"] = False
    if result:
        e["code"] = result
        _mark()


async def _map_narratives(now: float) -> None:
    """DeepSeek maps the database to narratives, a batch per turn
    (narrative_map.py); keys it finds for a board entry join its own."""
    _state["narr_mapping"] = True
    try:
        written = await narrative_map.step(now)
    finally:
        _state["narr_mapping"] = False
    changed = False
    for k, keys in written.items():
        e = _entries.get(k)
        if e is None:
            continue
        e["narr_ds"] = keys          # survives the next analysis, which rebuilds "narratives"
        have = list(e.get("narratives") or [])
        new = [x for x in keys if x not in have]
        if new:
            e["narratives"] = have + new
            changed = True
    if changed:
        _mark()


# ------------------------------------------------------------ the Top first

# Lorenzo, 29/09: "tutti i token che entrano in top dovranno avere l'indagine
# di deepseek nella tab why e info, come fatto per dregg". The Top (main.py
# _top_entries) mixes board entries with database rows the board never
# judged, and a board entry may still wait for the daily cap: every minute a
# few of them are read first, on their own allowance (priority=True).
TOP_FILL_EVERY_S = 60
TOP_FILL_PER_TURN = 3
TOP_RETRY_S = 6 * 3600         # a reading that failed waits before the next try
_top_source = None             # callable(n) -> the Top's entries (main._top_entries)
_top_tried: dict[str, float] = {}
TOP_SYNC_EVERY_S = 60
_top_rank: dict[str, int] = {}  # "chain:token" -> place in the unfiltered Top, after sync_top


def _place(k: str, board_rank: int | None) -> tuple[str, int | None]:
    """("ranked", place) when the project is in the Top, else ("studied", None).
    Before the first sync the board's own order stands in for the Top."""
    if _state.get("top_synced_at"):
        return ("ranked", _top_rank[k]) if k in _top_rank else ("studied", None)
    return ("ranked", board_rank) if board_rank else ("studied", None)


def sync_top(now: float | None = None) -> int:
    """The database's "ranked" follows the Top (Lorenzo, 29/09: HATCHER
    "Studied" in the Database and first on the podium). Only the unfiltered
    Top counts: a narrative filter is a view, not the ranking."""
    if _top_source is None:
        return 0
    keys = [_key(t["chain"], t["token_address"]) for t in _top_source(50)]
    changed = projects_db.sync_top(keys)
    _top_rank.clear()
    _top_rank.update({k: i for i, k in enumerate(keys, 1)})
    _state["top_synced_at"] = now or time.time()
    for e in _entries.values():
        e.pop("_db", None)      # the next _sync_database rewrites with the Top's places
    return changed


async def _sync_top(now: float) -> None:
    sync_top(now)
    _sync_database(_state["board"])
    queue_top_news(_top_source(TOP_ALERT_POOL))
    queue_pearl_news()


async def _audit(now: float) -> None:
    """DeepSeek looks for contradictions between the Top and the database."""
    _state["auditing"] = True
    try:
        await consistency.step(_top_source(50) if _top_source else [], now, requeue=requeue)
    finally:
        _state["auditing"] = False


def requeue(chain: str, token: str) -> bool:
    """A fresh analysis: a board entry's pillars go stale at once, a
    database row goes back in the queue."""
    e = _entries.get(_key(chain, token))
    if e is not None:
        e["checked_at"] = {}
        e.pop("_db", None)
        return True
    return projects_db.recheck(chain, token)


def set_top_source(fn) -> None:
    global _top_source
    _top_source = fn


def db_entry(p: dict) -> dict:
    """A database row in board shape: what the token page and the judge read.
    Layer rows (layers.py) keep their pillars as a list: keyed here like the
    board's, or every reader's .get() fails (07/10: 500 on the token page)."""
    pillars = p.get("pillars") or {}
    if isinstance(pillars, list):
        pillars = {x["key"]: x for x in pillars if isinstance(x, dict) and x.get("key")}
    return {**projects_db.as_item(p), "score": p.get("score"), "pillars": pillars,
            "overall": p.get("overall"), "narratives": p.get("narratives") or [],
            "traction": p.get("traction"), "rank": p.get("rank"), "status": p.get("status"),
            "why": p.get("why"), "on_board": False}


async def top_fill(client: httpx.AsyncClient, now: float | None = None) -> int:
    """DeepSeek's report and code reading for the Top's entries that lack
    them, up to TOP_FILL_PER_TURN readings a turn. Returns the readings tried."""
    now = now or time.time()
    if _top_source is None or _state.get("top_filling"):
        return 0
    _state["top_fill_at"] = now
    _state["top_filling"] = True
    tried = 0
    changed = False
    try:
        for t in _top_source(50):
            if tried >= TOP_FILL_PER_TURN:
                break
            k = _key(t["chain"], t["token_address"])
            e = _entries.get(k)
            board = e is not None
            if e is None:
                p = projects_db.get(t["chain"], t["token_address"])
                if p is None:
                    continue
                e = db_entry(p)
            o = e.get("overall") or {}
            rules_why = qualifies(e, now) if board else (e.get("why") or "")
            # A reading from an older prompt is re-read too: the Top is where
            # people look (STEALF 38, GRID 34 stayed as they were, 29/09).
            needs_judge = judge.wants_reading(e, rules_why, now)
            if needs_judge and not o.get("pending") and not o.get("fatal") \
                    and now - _top_tried.get("judge:" + k, 0) >= TOP_RETRY_S:
                _top_tried["judge:" + k] = now
                tried += 1
                j = await judge.judge(e, rules_why, now, priority=True)
                if j and board and k in _entries:
                    _entries[k]["judge"] = j
                    _remember(e, "ranked" if e.get("rank") else "studied", qualifies(e), now)
                    changed = True
            repo = code_review.repo_of(e)
            has_code = e.get("code") if board else code_review.get(repo)
            if repo and not has_code and tried < TOP_FILL_PER_TURN \
                    and now - _top_tried.get("code:" + k, 0) >= TOP_RETRY_S:
                _top_tried["code:" + k] = now
                tried += 1
                c = await code_review.review(e, client, now, priority=True)
                if c and board and k in _entries:
                    _entries[k]["code"] = c
                    changed = True
    finally:
        _state["top_filling"] = False
    if changed:
        _mark()
    return tried


START_DELAY_S = 20
# Verdicts of rules that no longer exist: rows judged by them are looked at again.
DROPPED_RULES = ("above $100k", "younger than", "over % days", "beyond the%limits", "radar exception",
                 "without an exceptional GitHub", "GitHub link without a repository", "GoPlus does not have")


def backlog(now: float | None = None) -> dict:
    """What the research still owes tonight (nightly.py): analyses running or
    spawned, entries never analysed, database rows due for a look, and the
    discovery queue while the pool still wants projects. Late data (pending
    pillars, retried for hours) does not count: it would keep the run open
    for nothing."""
    now = now or time.time()
    try:
        db_due = len(projects_db.due_for_analysis(100, set(_entries), now))
    except Exception:
        db_due = 0
    queue = discovery.status().get("queue") or 0
    if queue and pool_status(now)["pool"] >= POOL_TARGET:
        queue = 0                   # discovery is paused or slow: its queue waits
    unmeasured = sum(1 for e in usage_candidates() if not usage.tried_today(e["chain"], e["token_address"]))
    return {"running": len(_busy) + len(_tasks), "unanalysed": sum(1 for e in _entries.values() if not e["pillars"]),
            "database": db_due, "discovery": queue, "unmeasured": unmeasured}


def drained(now: float | None = None) -> bool:
    return not any(backlog(now).values())


def analyze_now(chain: str, token: str) -> bool:
    """One project analysed at once, outside the tick: with the nightly run a
    project added by hand would otherwise wait for 22:00. False when it is
    not in the working set or already being analysed."""
    k = _key(chain, token)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:            # called outside the server (tests, scripts)
        return False
    if k not in _entries or k in _busy:
        return False
    _busy.add(k)

    async def _go() -> None:
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "Mozilla/5.0 (LiquidityEngine)"}) as client:
            try:                    # usage too, or usage_gate keeps it out until the night
                await usage.refresh(client, [_entries[k]], 1)
            except Exception:
                logger.exception("usage: %s not measured", k)
            await _analyze(k, set(), client)     # its finally frees the slot
        if _dirty:
            _save()
    task = loop.create_task(_go())
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return True


def rescore_database() -> int:
    """Every studied database row scored again with today's formula and
    rules (07/10, Lorenzo: "aggiornami tutti i voti di quelle presenti nel
    database [...] con le nuove logiche"). No API call: the readings stay,
    the weights and bars change. Board entries are left to the board, layer
    rows to their own scorer."""
    out = []
    for row in projects_db.scored_rows():
        if row["chain"] == "layer" or _key(row["chain"], row["token"]) in _entries:
            continue
        e = {**db_entry(row), "global_cap": row.get("cg_mcap"), "judge": judge.get(row["chain"], row["token"])}
        try:
            out.append((projects_db.key(row["chain"], row["token"]), final_score(e),
                        "" if row["status"] == "ranked" else qualifies(e)))
        except Exception:
            logger.exception("rescore: %s skipped", row.get("symbol"))
    return projects_db.rescore_many(out)


def rescore_once() -> None:
    """When the rules change (rules_version): rescore the database now, and
    queue every studied row, plus the ones DeepSeek dropped, for a fresh
    analysis with the new judge prompt. The nightly run works through it."""
    rules = f"{rules_version()}:{judge.PROMPT_VERSION}"
    if _state.get("rescored_rules") == rules:
        return
    try:
        n = rescore_database()
        q = projects_db.requeue(("studied", "ranked")) + projects_db.requeue(("rejected",), ("DeepSeek",))
        logger.info("classifica: %d voti del database ricalcolati, %d progetti rimessi in coda", n, q)
        _state["rescored_rules"] = rules
        _mark()
        _save()
    except Exception:
        logger.exception("classifica: ricalcolo del database fallito")


def startup_requeue() -> None:
    """Once per start: rows judged by limits that no longer exist go back in the queue."""
    rescore_once()
    try:
        n = projects_db.recheck_studied(("over $%", "over % days%"))
        # Rules dropped on 29/09 (age limits, radar exceptions, the $100k band).
        n += projects_db.recheck_studied(DROPPED_RULES, ("studied", "rejected"))
        if _reset_market:
            logger.info("classifica: %d righe EVM senza mercato rimesse in coda",
                        projects_db.reset_empty_market() + projects_db.reset_linkless_market())
        if _reset_market:
            # Wallet limits now leave contracts out (BV7X: 41% in a contract): look again.
            n += projects_db.recheck_studied(("a single wallet holds", "single wallet"), ("rejected",))
        if _recheck_misreads:
            n += projects_db.recheck_studied(MISREAD_FATALS, ("rejected", "studied"))
        if _recheck_programs:
            # Wallet limits now leave Solana program accounts out (19/10: MNDE, SONIC, NATIX).
            n += projects_db.recheck_studied(("a single wallet holds", "top 10 hold", "top 10 wallets hold"),
                                             ("rejected", "studied"))
        if _requeue_fatals:
            n += projects_db.recheck_studied(("github:", "site:", "tokenomics:"), ("rejected",))
        if n:
            logger.info("classifica: %d progetti rimessi in coda (limiti vecchi)", n)
    except Exception:
        logger.exception("classifica: recheck_studied fallito")


async def leaderboard_loop() -> None:
    await asyncio.sleep(START_DELAY_S)
    startup_requeue()
    async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "Mozilla/5.0 (LiquidityEngine)"}) as client:
        while True:
            try:
                await tick(client)
            except Exception:
                logger.exception("classifica: giro fallito")
            await asyncio.sleep(TICK_S)


_load()


# ── Live market of the Top (Lorenzo, 16/10: "i grafici sempre aggiornati
# con i dati dex, cosi' come la MarketCap") ───────────────────────────────
# Since the research runs only at night (nightly.py) the board's own market
# poll (tick -> _poll_market) ran only then too, and the database rows of the
# Top kept the cap of their last analysis. This loop runs around the clock,
# research or not: once a minute every token of the Top (board and database
# rows) is read from DexScreener; board entries get it through apply_market,
# everything is kept in _live for _top_entries. Display only: the gates still
# judge the stored figures, so a minute's move never reshuffles the arenas.
LIVE_MARKET_S = 60
LIVE_TOP_N = 500
_live: dict[str, dict] = {}


def live(chain: str, token: str, max_age_s: float = 15 * 60) -> dict | None:
    """The token's DexScreener market of the last minutes, or None."""
    x = _live.get(_key(chain, token).lower())
    return x if x and time.time() - x["at"] <= max_age_s else None


def apply_live(pairs: list[dict], now: float | None = None) -> int:
    """The deepest pool of each token in a DexScreener /tokens answer."""
    now = now or time.time()
    best: dict[str, dict] = {}
    for p in pairs or []:
        k = _key(p.get("chainId") or "", (p.get("baseToken") or {}).get("address") or "").lower()
        if k not in best or float((p.get("liquidity") or {}).get("usd") or 0) > \
                float((best[k].get("liquidity") or {}).get("usd") or 0):
            best[k] = p
    for k, p in best.items():
        cap = p.get("marketCap") or p.get("fdv")
        _live[k] = {"market_cap": float(cap) if cap else None, "price_usd": p.get("priceUsd"),
                    "liquidity_usd": float((p.get("liquidity") or {}).get("usd") or 0),
                    "change_24h": (p.get("priceChange") or {}).get("h24"), "pair_url": p.get("url"),
                    "pair_address": p.get("pairAddress"),
                    # Every token that will exist, at today's price: whitekobra's view
                    # weighs it against the cap (main._gem_view, 18/10).
                    "fdv": float(p["fdv"]) if p.get("fdv") else None, "at": now}
    return len(best)


async def poll_live(client: httpx.AsyncClient, now: float | None = None) -> int:
    from app.trading.onchain import layers
    keys = {(e["chain"], e["token_address"]) for e in _entries.values()}
    if _top_source is not None:
        keys |= {(t["chain"], t["token_address"]) for t in _top_source(LIVE_TOP_N)}
    by_chain: dict[str, list[str]] = {}
    for chain, token in keys:
        if chain and token and chain != layers.CHAIN:
            by_chain.setdefault(chain, []).append(token)
    n = 0
    for chain, tokens in by_chain.items():
        for i in range(0, len(tokens), 30):
            r = await client.get(DEX_TOKENS.format(chain=chain, addresses=",".join(tokens[i:i + 30])), timeout=10.0)
            if r.status_code == 200 and isinstance(r.json(), list):
                apply_market(r.json())
                n += apply_live(r.json(), now)
            await asyncio.sleep(0.25)
    return n


async def live_market_loop() -> None:
    await asyncio.sleep(START_DELAY_S)
    async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "Mozilla/5.0 (LiquidityEngine)"}) as client:
        while True:
            try:
                await poll_live(client)
            except Exception:
                logger.exception("classifica: mercato in tempo reale non letto")
            try:
                from app.trading.onchain import listing_dates
                await listing_dates.fill(client)
            except Exception:
                logger.exception("classifica: date di listing non lette")
            from app.providers import gecko_client
            gecko_client.save(storage.data_file("gecko_metrics.json"))
            await asyncio.sleep(LIVE_MARKET_S)
