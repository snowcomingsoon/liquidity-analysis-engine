"""Arenas: the Top by narrative instead of one Top 15/25/50.

Lorenzo, 07/10: "la top50 come concetto e' limitante, serve un sistema
meritocratico [...] data la complessita' dei progetti e le diverse
narrative", then "procedi come consigliato". An AI-agent token, an L1 chain
and an RWA project no longer sit in one row: each competes only with its
peers, in the arena of one of its narratives (layer chains have their own).

- No fixed size: an arena holds every project that passed the gates, and
  the ones at or above the arena's median are "in"; the rest sit on its
  bench. A strong arena can have twelve, a weak one two.
- A project with several narratives competes where it beats its peers by
  the most (score minus the arena's median).
- Pound for pound: the projects that lead their own arena by the most, in
  spreads from its median; one per arena. A small project that dominates
  its niche beats a big one in the middle of its own.
- The ladder (record_night): each night every project duels up to
  DUELS_PER_NIGHT peers of its arena, block by block (usage, participation,
  product, token, DeepSeek), and an Elo rating keeps the result. Recorded
  from the first night, shown once it has settled (LADDER_READY_NIGHTS):
  a lucky night is worth a few points, not the top place.
- Tenure: a project that made it "in" stays in for TENURE_S from its
  entry, even when others push it below the median (Lorenzo, 08/10: "se
  una crypto e' comparsa tra le migliori, anche se poi viene surclassata;
  deve rimanerci per almeno 2-3 gg"). Leaving the pool (a gate, a measured
  rejection, a rug) still takes it out at once.
"""
from __future__ import annotations

import json
import logging
import statistics
import time

from app.atomic_write import write_text_atomic
from app.trading.onchain import narratives, storage

logger = logging.getLogger(__name__)

CHAINS = "chains"                  # layer chains (layers.CHAIN), whatever their narrative
OTHER = "other"                    # projects with no narrative of their own
LABELS = {CHAINS: "Chains L0/L1/L2", OTHER: "Other builders"}
HEAT = {CHAINS: 2, OTHER: 0}
# Privacy is one arena with its tools (Lorenzo, 07/10: "a me interessa molto
# la privacy, progetti come Solrouter [...] DREGG"): zero knowledge and
# FHE/MPC/TEE compete there, not in arenas of their own.
GROUP = {"zero_knowledge": "privacy", "fhe_mpc_tee": "privacy"}
FIRST = ("privacy",)               # shown first, whatever the heat
# Narratives that keep their projects, in this order: a privacy or compute
# project competes there, not where it would lead by more (Lorenzo 07-08/10).
CLAIM = ("privacy", "decentralized_compute")
LAYER_CHAIN = "layer"
MIN_SIZE = 2                       # an arena of one has no peers: its project goes elsewhere
SPREAD_MIN = 3                     # a spread needs at least three projects
SPREAD_FLOOR = 5.0                 # points: five near-equal scores are not "+4 sigma"
P4P_SIZE = 3                       # shown; P4P_SEND go out, so a hidden one leaves room
P4P_SEND = 10

BLOCKS = ("usage", "participation", "product", "token", "deepseek")
RATING_START = 1500.0
ELO_K = 24.0
DUELS_PER_NIGHT = 5
HISTORY = 7                        # nights shown beside the name
NIGHT_GAP_S = 20 * 3600            # one ladder night per evening, even across a resume
LADDER_READY_NIGHTS = 21
TENURE_S = 3 * 86400               # minimum stay "in" after entering, whatever the median does

_FILE = storage.data_file("onchain_arena_ladder.json")
_TENURE_FILE = storage.data_file("onchain_arena_tenure.json")


def entry_id(e: dict) -> str:
    return f"{e.get('chain')}:{e.get('token_address')}"


def _catalog() -> dict[str, dict]:
    return {n["key"]: n for n in narratives.catalog()}


def candidates(e: dict, cat: dict[str, dict] | None = None, prefer: set[str] | None = None) -> list[str]:
    """The arenas a project may compete in: its narratives (memes left out,
    GROUP folded), the chains arena for a layer, else OTHER. `prefer` (the
    narratives the user filtered on) keeps a project in the arena asked for."""
    if e.get("chain") == LAYER_CHAIN:
        return [CHAINS]
    cat = _catalog() if cat is None else cat
    keys = []
    for n in e.get("narratives") or []:
        k = n.get("key") if isinstance(n, dict) else n
        if k in cat and cat[k].get("kind") != "meme":
            k = GROUP.get(k, k)
            if k not in keys:
                keys.append(k)
    if prefer:
        wanted = [k for k in keys if k in {GROUP.get(p, p) for p in prefer}]
        keys = wanted or keys
    else:
        keys = next(([k] for k in CLAIM if k in keys), keys)
    return keys or [OTHER]


def also_in(e: dict, cat: dict[str, dict], home: str) -> list[str]:
    """Every other narrative arena of a project, besides the one it competes
    for (Lorenzo, 10/10: "non voglio vederle vuote"): a DEX that leads the AI
    arena still shows in DEX & AMM, ranked among DEXes, without a second
    podium place or tenure."""
    out = []
    for n in e.get("narratives") or []:
        k = n.get("key") if isinstance(n, dict) else n
        if k in cat and cat[k].get("kind") != "meme":
            k = GROUP.get(k, k)
            if k != home and k not in out:
                out.append(k)
    return out


def _score(e: dict) -> float:
    return float(e.get("score") or 0.0)


def _heat(key: str, cat: dict[str, dict]) -> int:
    return HEAT[key] if key in HEAT else int((cat.get(key) or {}).get("heat") or 0)


def assign(entries: list[dict], cat: dict[str, dict] | None = None, prefer: set[str] | None = None) -> dict[str, str]:
    """entry id -> arena key. Each project goes where it leads its peers by
    the most; an arena left with fewer than MIN_SIZE projects is dropped and
    its projects try their next arena, OTHER as the last resort."""
    cat = _catalog() if cat is None else cat
    cands = {entry_id(e): candidates(e, cat, prefer) for e in entries}
    by_id = {entry_id(e): e for e in entries}
    dropped: set[str] = set()
    asked = {GROUP.get(p, p) for p in prefer or ()}
    for _ in range(len(entries) + 1):
        open_ = {i: [k for k in c if k not in dropped] or [OTHER] for i, c in cands.items()}
        pool: dict[str, list[float]] = {}
        for i, ks in open_.items():
            for k in ks:
                pool.setdefault(k, []).append(_score(by_id[i]))
        med = {k: statistics.median(v) for k, v in pool.items()}
        out = {i: max(ks, key=lambda k: (_score(by_id[i]) - med[k], _heat(k, cat), k)) for i, ks in open_.items()}
        size: dict[str, int] = {}
        for k in out.values():
            size[k] = size.get(k, 0) + 1
        # The arena the user filtered on stays, even with one project.
        small = {k for k, n in size.items() if n < MIN_SIZE and k not in (OTHER, *CLAIM) and k not in asked}
        if not small:
            return out
        dropped |= small
    return out


def build(entries: list[dict], ladder: dict | None = None, prefer: set[str] | None = None,
          tenure: dict | None = None, now: float | None = None) -> dict:
    """The arenas and the pound-for-pound podium for the Top's entries
    (already gated and scored by _top_entries). `tenure` (entry id -> time
    it went "in") keeps a project in for TENURE_S; only the unfiltered view
    records it, since a narrative filter reshapes the arenas."""
    cat = _catalog()
    now = time.time() if now is None else now
    persist = tenure is None and not prefer
    tenure = load_tenure() if tenure is None else tenure
    before = dict(tenure)
    record = not prefer
    where = assign(entries, cat, prefer)
    ladder = load() if ladder is None else ladder
    ratings = ladder.get("ratings") or {}
    groups: dict[str, list[dict]] = {}
    for e in entries:
        groups.setdefault(where[entry_id(e)], []).append(e)
    if not prefer:
        for e in entries:
            for k in also_in(e, cat, where[entry_id(e)]):
                groups.setdefault(k, []).append({**e, "also": True})
    arenas, p4p = [], []
    for key, members in groups.items():
        members = sorted(members, key=lambda e: -_score(e))
        scores = [_score(e) for e in members]
        med = statistics.median(scores)
        spread = max(statistics.pstdev(scores), SPREAD_FLOOR) if len(scores) >= SPREAD_MIN else None
        rows = []
        for pos, e in enumerate(members):
            eid = entry_id(e)
            r = ratings.get(eid) or {}
            merit = _score(e) >= med
            since = tenure.get(eid)
            held = not merit and since is not None and 0 <= now - since < TENURE_S
            if record and not e.get("also"):
                if merit and since is None:
                    tenure[eid] = now
                elif not merit and not held:
                    tenure.pop(eid, None)
            rows.append({**e, "arena_rank": pos + 1, "in": merit or held, "held": held,
                         "z": round((_score(e) - med) / spread, 2) if spread else None,
                         "rating": round(r["r"]) if r.get("r") is not None else None,
                         "nights": r.get("nights") or []})
        label = LABELS.get(key) or (cat.get(key) or {}).get("label") or key
        arenas.append({"key": key, "label": label, "heat": _heat(key, cat), "size": len(rows),
                       "median": round(med, 1), "entries": rows})
        # The arena's own leader: a copy from another narrative competes there.
        lead = next((r for r in rows if not r.get("also")), None)
        if lead is not None and key != OTHER:
            p4p.append({**lead, "arena": key, "arena_label": label})
    if record:
        # Out of the pool (a gate, a rejection, a rug): out now, and a return starts afresh.
        for eid in set(tenure) - {entry_id(e) for e in entries}:
            tenure.pop(eid)
    if persist and tenure != before:
        _save_tenure(tenure)
    # The arenas Lorenzo follows are always there to pick, even before a project qualifies.
    for key in CLAIM:
        if key not in groups and key in cat and not prefer:
            arenas.append({"key": key, "label": cat[key].get("label") or key, "heat": _heat(key, cat),
                           "size": 0, "median": 0.0, "entries": []})
    arenas.sort(key=lambda a: (not a["entries"], a["key"] not in FIRST, a["key"] == OTHER, -a["heat"],
                               -_score(a["entries"][0]) if a["entries"] else 0.0))
    # Leaders by how far they lead (z) first; then, so the podium never stands
    # with two steps (Lorenzo, 19/10), the leaders of the arenas too small
    # for a spread or led by a hair, by score.
    p4p.sort(key=lambda e: (not (e["z"] or 0) > 0, -(e["z"] or 0), -_score(e)))
    return {"arenas": arenas, "p4p": p4p[:P4P_SEND],
            "ladder": {"nights": ladder.get("nights") or 0, "ready": (ladder.get("nights") or 0) >= LADDER_READY_NIGHTS}}


# The ladder ---------------------------------------------------------------

def load() -> dict:
    try:
        return json.loads(_FILE.read_text())
    except FileNotFoundError:
        return {}
    except Exception:
        logger.exception("arenas: ladder not readable")
        return {}


def _save(state: dict) -> None:
    write_text_atomic(_FILE, json.dumps(state, separators=(",", ":")))


def load_tenure() -> dict:
    try:
        return {k: float(v) for k, v in json.loads(_TENURE_FILE.read_text()).items()}
    except FileNotFoundError:
        return {}
    except Exception:
        logger.exception("arenas: tenure not readable")
        return {}


def _save_tenure(tenure: dict) -> None:
    write_text_atomic(_TENURE_FILE, json.dumps(tenure, separators=(",", ":")))


def duel(a: dict, b: dict) -> float | None:
    """1 if `a` beats `b` on more blocks, 0 if it loses, 0.5 if even; None
    when they share no measured block."""
    ba, bb = a.get("blocks") or {}, b.get("blocks") or {}
    wins = losses = 0
    shared = 0
    for k in BLOCKS:
        x, y = ba.get(k), bb.get(k)
        if x is None or y is None:
            continue
        shared += 1
        wins += x > y
        losses += x < y
    if not shared:
        return None
    return 1.0 if wins > losses else 0.0 if wins < losses else 0.5


def _expected(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))


def record_night(entries: list[dict], now: float | None = None, state: dict | None = None) -> int:
    """Plays one night of duels inside each arena and saves the ratings.
    Each project meets up to DUELS_PER_NIGHT peers nearest to it in rating;
    a pair meets once. Returns the duels played (0 if tonight already ran)."""
    now = time.time() if now is None else now
    persist = state is None
    state = load() if state is None else state
    if now - (state.get("last") or 0) < NIGHT_GAP_S:
        return 0
    ratings: dict = state.setdefault("ratings", {})
    where = assign(entries)
    groups: dict[str, list[dict]] = {}
    for e in entries:
        groups.setdefault(where[entry_id(e)], []).append(e)
    rate = lambda e: (ratings.get(entry_id(e)) or {}).get("r", RATING_START)  # noqa: E731
    delta: dict[str, float] = {}
    tally: dict[str, float] = {}
    played = 0
    for members in groups.values():
        met: set[frozenset] = set()
        for e in members:
            peers = sorted((p for p in members if p is not e), key=lambda p: (abs(rate(p) - rate(e)), entry_id(p)))
            for p in peers[:DUELS_PER_NIGHT]:
                pair = frozenset((entry_id(e), entry_id(p)))
                if pair in met:
                    continue
                met.add(pair)
                res = duel(e, p)
                if res is None:
                    continue
                played += 1
                exp = _expected(rate(e), rate(p))
                for who, s, x in ((e, res, exp), (p, 1 - res, 1 - exp)):
                    i = entry_id(who)
                    delta[i] = delta.get(i, 0.0) + ELO_K * (s - x)
                    tally[i] = tally.get(i, 0.0) + (s - 0.5)
    for e in entries:
        i = entry_id(e)
        if i not in tally:
            continue
        r = ratings.setdefault(i, {"r": RATING_START, "nights": []})
        r["r"] = round(r.get("r", RATING_START) + delta.get(i, 0.0), 1)
        r["last_delta"] = round(delta.get(i, 0.0), 1)
        r["symbol"] = e.get("symbol")
        r["nights"] = ((r.get("nights") or []) + ["w" if tally[i] > 0 else "l" if tally[i] < 0 else "d"])[-HISTORY:]
    state["last"] = now
    state["nights"] = (state.get("nights") or 0) + 1
    if persist:
        _save(state)
    return played
