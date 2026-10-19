"""The Gem Finder's memory of every project it has ever met: a database.

Request: "il gem hunter deve trovare progetti di qualita', ma vedi sempre i
soliti... ma fatti un database no?". Why the board kept showing the same
names: the finder had no memory of the market, only of its board.

- A project was examined only when a source handed it over at the right
  moment (a CoinGecko category page, a DexScreener profile, a README), and
  CoinGecko was read only through the "solana-ecosystem" category, which
  lists a fraction of the Solana coins CoinGecko knows.
- The working set held 400 projects; older ones were dropped and forgotten.
- One rejection was final for 30 days, whatever changed after.

Here every project from every source is written once and kept: identity,
links, which sources saw it, the market (cap, liquidity, volume), and the
last analysis (pillars, score, verdict and why). The board's working set is
fed from here by priority, a rejected project is looked at again after
RECHECK_S (a repository gets commits, a site gets docs), and the whole
database can be searched from the app: nothing examined is lost.

SQLite on the volume, like the order ledger: one process, one writer,
atomic upserts, and a file that survives deploys.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

from app.trading.onchain.storage import data_file

_DB_FILE = data_file("onchain_projects.db")
_lock = threading.Lock()
_conn: sqlite3.Connection | None = None
_conn_path: Path | None = None

CAP_MIN = 10_000                 # early gems (leaderboard.EARLY_CAP_USD) start here
CAP_MAX = 10_000_000             # leaderboard.BOARD_CAP_MAX_USD: was $3M until 07/10, so rows
                                 # between $3M and $10M were never fed to the board
LIQ_MIN = 5_000
MARKET_TTL_S = 6 * 3600          # cap and liquidity older than this get refreshed
RECHECK_S = 14 * 86400           # a rejected project is looked at again after two weeks
RECHECK_DATA_S = 2 * 86400       # ...sooner when it failed for missing data
DETAIL_TTL_S = 14 * 86400        # CoinGecko page (website, GitHub) re-read
STATUSES = ("new", "analyzing", "studied", "ranked", "rejected")
_JSON = ("sources", "categories", "socials", "pillars", "overall", "similarity", "narratives", "traction")
NO_LINKS = "no website or GitHub to read"
_DATA_WORDS = ("not responding", "unreachable", "not available", "pending", "incomplete")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    key TEXT PRIMARY KEY,
    chain TEXT NOT NULL,
    token TEXT NOT NULL,
    symbol TEXT, name TEXT, website TEXT, github TEXT, image TEXT, description TEXT,
    cg_id TEXT,
    cg_mcap REAL,
    categories TEXT, socials TEXT, sources TEXT,
    first_seen REAL NOT NULL, last_seen REAL NOT NULL,
    mcap REAL, liq REAL, vol24 REAL, price REAL, launched_at REAL, market_at REAL,
    detail_at REAL,
    status TEXT NOT NULL DEFAULT 'new', why TEXT,
    analyzed_at REAL, next_check REAL NOT NULL DEFAULT 0,
    score REAL, pillars TEXT, overall TEXT, similarity TEXT, narratives TEXT, traction TEXT,
    rank INTEGER,
    narr_at REAL
);
CREATE INDEX IF NOT EXISTS projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS projects_market ON projects(market_at);
CREATE INDEX IF NOT EXISTS projects_score ON projects(score);
"""


def _db() -> sqlite3.Connection:
    global _conn, _conn_path
    if _conn is None or _conn_path != _DB_FILE:
        _conn = sqlite3.connect(_DB_FILE, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(_SCHEMA)
        cols = {r[1] for r in _conn.execute("PRAGMA table_info(projects)")}
        if "cg_mcap" not in cols:
            _conn.execute("ALTER TABLE projects ADD COLUMN cg_mcap REAL")
        if "narr_at" not in cols:  # when DeepSeek mapped the row's narratives (narrative_map.py)
            _conn.execute("ALTER TABLE projects ADD COLUMN narr_at REAL")
        _merge_spellings(_conn)
        _conn_path = _DB_FILE
    return _conn


def reset_for_tests() -> None:
    with _lock:
        _db().execute("DELETE FROM projects")
        _db().commit()


def norm_token(token: str) -> str:
    """One spelling per contract. EVM addresses ignore case, and PRIORS entered
    twice, once checksummed and once lowercase (Lorenzo, 19/10: "deve far fede
    l'indirizzo di contratto"). Solana, Tron and TON addresses are case-sensitive
    and never start with 0x (base58 has no 0)."""
    t = (token or "").strip()
    return t.lower() if t[:2].lower() == "0x" else t


_STATUS_RANK = {"ranked": 4, "studied": 3, "analyzing": 2, "new": 1, "rejected": 0}


def _merge_spellings(conn: sqlite3.Connection) -> None:
    """Rows saved under a mixed-case EVM address: renamed to the lowercase one,
    and when both exist only the more advanced row stays."""
    rows = conn.execute("SELECT key, chain, token, status, score, first_seen FROM projects"
                        " WHERE token LIKE '0x%' AND token != lower(token)").fetchall()
    for r in rows:
        low = norm_token(r["token"])
        lk = f"{r['chain']}:{low}"
        other = conn.execute("SELECT key, status, score, first_seen FROM projects WHERE key = ?", (lk,)).fetchone()
        if other is not None:
            rank = lambda x: (_STATUS_RANK.get(x["status"], 0), x["score"] or 0, -(x["first_seen"] or 0))  # noqa: E731
            if rank(other) >= rank(r):
                conn.execute("DELETE FROM projects WHERE key = ?", (r["key"],))
                continue
            conn.execute("DELETE FROM projects WHERE key = ?", (lk,))
        conn.execute("UPDATE projects SET key = ?, token = ? WHERE key = ?", (lk, low, r["key"]))
    if rows:
        conn.commit()


def key(chain: str, token: str) -> str:
    return f"{chain}:{norm_token(token)}"


def _row(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for f in _JSON:
        if d.get(f):
            try:
                d[f] = json.loads(d[f])
            except ValueError:
                d[f] = None
    return d


def get(chain: str, token: str) -> dict | None:
    with _lock:
        return _row(_db().execute("SELECT * FROM projects WHERE key = ?", (key(chain, token),)).fetchone())


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


# ------------------------------------------------------------------ writing

def upsert(item: dict, source: str, now: float | None = None) -> bool:
    """Write what a source knows about a project. True if it was new.
    Known fields are never erased by a source that does not have them."""
    with _lock:
        new = _upsert(_db(), item, source, now)
        _db().commit()
    return new


def upsert_many(items: list[dict], source: str, now: float | None = None) -> int:
    """Thousands of rows (CoinGecko's full list) in one transaction."""
    with _lock:
        n = sum(_upsert(_db(), i, source, now) for i in items)
        _db().commit()
    return n


def _upsert(db: sqlite3.Connection, item: dict, source: str, now: float | None) -> bool:
    chain, token = item.get("chain"), norm_token(item.get("token_address") or "")
    if not chain or not token:
        return False
    now = now or time.time()
    k = key(chain, token)
    fields = {
        "symbol": item.get("symbol") if (item.get("symbol") or "?") != "?" else None,
        "name": item.get("name") or None, "website": item.get("website") or None,
        "github": item.get("github") or None, "image": item.get("image") or None,
        "description": (item.get("description") or "")[:600] or None, "cg_id": item.get("cg_id") or None,
        "categories": json.dumps(item["categories"][:8]) if item.get("categories") else None,
        "socials": json.dumps(item["socials"][:6]) if item.get("socials") else None,
        "mcap": _num(item.get("market_cap")), "liq": _num(item.get("liquidity_usd")),
        "launched_at": _num(item.get("launched_at") or item.get("created_at")),
    }
    old = db.execute("SELECT sources FROM projects WHERE key = ?", (k,)).fetchone()
    if old is None:
        cols = {k2: v for k2, v in fields.items() if v is not None}
        cols.update(key=k, chain=chain, token=token, first_seen=now, last_seen=now, sources=json.dumps([source]))
        if cols.get("mcap") is not None:
            cols["market_at"] = now
        db.execute(f"INSERT INTO projects ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                   tuple(cols.values()))
        return True
    sources = json.loads(old["sources"] or "[]")
    if source not in sources:
        sources.append(source)
    sets = {k2: v for k2, v in fields.items() if v is not None}
    sets.update(sources=json.dumps(sources), last_seen=now)
    db.execute(f"UPDATE projects SET {','.join(f'{c} = ?' for c in sets)} WHERE key = ?", (*sets.values(), k))
    return False


def set_market(chain: str, token: str, *, mcap=None, liq=None, vol24=None, price=None, launched_at=None,
               now: float | None = None) -> None:
    now = now or time.time()
    with _lock:
        _db().execute(
            "UPDATE projects SET mcap = COALESCE(?, mcap), liq = COALESCE(?, liq), vol24 = COALESCE(?, vol24),"
            " price = COALESCE(?, price), launched_at = COALESCE(launched_at, ?), market_at = ? WHERE key = ?",
            (_num(mcap), _num(liq), _num(vol24), _num(price), _num(launched_at), now, key(chain, token)))
        _db().commit()


def _set_links(chain: str, token: str, info: dict) -> None:
    """The website and GitHub DexScreener lists for the pair, for rows that
    have none: a coin from the CoinGecko list waits hours for its own page
    (5 requests a minute) and AUREON never got analysed meanwhile (29/09)."""
    site = next((w["url"] for w in info.get("websites") or [] if w.get("url")), None)
    git = next((x["url"] for x in info.get("socials") or [] if "github.com" in (x.get("url") or "")), None)
    if not (site or git):
        return
    with _lock:
        _db().execute("UPDATE projects SET website = COALESCE(website, ?), github = COALESCE(github, ?),"
                      " next_check = CASE WHEN status = 'rejected' AND why = ? THEN 0 ELSE next_check END"
                      " WHERE key = ?", (site, git, NO_LINKS, key(chain, token)))
        _db().commit()


def reset_linkless_market() -> int:
    """Rows with a cap but no website or GitHub: ask DexScreener again for its links."""
    with _lock:
        cur = _db().execute("UPDATE projects SET market_at = NULL WHERE mcap IS NOT NULL AND website IS NULL"
                            " AND github IS NULL AND market_at IS NOT NULL")
        _db().commit()
        return cur.rowcount


def apply_pairs(chain: str, tokens: list[str], pairs: list[dict], now: float | None = None) -> int:
    """DexScreener /tokens answer for a batch: the deepest pool per token.
    Tokens without any pool are stamped too, so they wait MARKET_TTL_S."""
    now = now or time.time()
    best: dict[str, dict] = {}
    # DexScreener answers EVM addresses in checksum case, the CoinGecko list
    # stores them in lower case: matched exactly, every such row was stamped
    # "no pool" and never got a cap (AUREON, 29/09).
    for p in pairs or []:
        t = ((p.get("baseToken") or {}).get("address") or "").lower()
        liq = float((p.get("liquidity") or {}).get("usd") or 0)
        if t not in best or liq > float((best[t].get("liquidity") or {}).get("usd") or 0):
            best[t] = p
    for t in tokens:
        p = best.get(t.lower())
        if p is None:
            set_market(chain, t, now=now)
            continue
        set_market(chain, t, mcap=p.get("marketCap") or p.get("fdv"), liq=(p.get("liquidity") or {}).get("usd"),
                   vol24=(p.get("volume") or {}).get("h24"), price=p.get("priceUsd"),
                   launched_at=(p.get("pairCreatedAt") or 0) / 1000 or None, now=now)
        _set_links(chain, t, p.get("info") or {})
    return len(best)


def record(e: dict, status: str, why: str = "", score: float | None = None, traction: dict | None = None,
           now: float | None = None) -> None:
    """The verdict of an analysis, from a board entry."""
    if status not in STATUSES:
        raise ValueError(status)
    now = now or time.time()
    if status == "rejected":
        soon = any(w in (why or "").lower() for w in _DATA_WORDS)
        next_check = now + (RECHECK_DATA_S if soon else RECHECK_S)
    elif status in ("studied", "ranked"):
        next_check = now + RECHECK_S
    else:
        next_check = 0
    dump = lambda v: json.dumps(v) if v is not None else None  # noqa: E731
    narr = list(e.get("narratives") or [])
    with _lock:
        # A new analysis must not wipe the keys DeepSeek mapped (narrative_map.py): once
        # a row is mapped it is never mapped again, so the two lists are merged.
        mapped = _db().execute("SELECT narratives FROM projects WHERE key = ? AND narr_at IS NOT NULL",
                               (key(e["chain"], e["token_address"]),)).fetchone()
        if mapped and mapped[0]:
            try:
                have = [n.get("key") if isinstance(n, dict) else n for n in json.loads(mapped[0]) or []]
            except ValueError:
                have = []
            narr = list(dict.fromkeys([*narr, *(k for k in have if isinstance(k, str) and k)]))
        _db().execute(
            "UPDATE projects SET status = ?, why = ?, analyzed_at = ?, next_check = ?, score = COALESCE(?, score),"
            " pillars = COALESCE(?, pillars), overall = COALESCE(?, overall), similarity = COALESCE(?, similarity),"
            " narratives = COALESCE(?, narratives), traction = COALESCE(?, traction), rank = ?,"
            " github = COALESCE(github, ?) WHERE key = ?",
            (status, why or None, now, next_check, score, dump(e.get("pillars") or None), dump(e.get("overall")),
             dump(e.get("similarity")), dump(narr or None), dump(traction), e.get("rank"),
             e.get("github"), key(e["chain"], e["token_address"])))
        _db().commit()
    from app.trading.onchain import history
    history.append(key(e["chain"], e["token_address"]), "projects_db.verdict",
                   {"analyzed_at": now, "status": status, "why": why or None, "score": score, "rank": e.get("rank"),
                    "overall": e.get("overall")}, now)


def demote_ranked(keep: set[str]) -> int:
    """Rows still marked "ranked" that are no longer on the board become
    "studied": a stale flag hid them from the Top (Lorenzo, 28/09)."""
    with _lock:
        rows = [r[0] for r in _db().execute("SELECT key FROM projects WHERE status = 'ranked'").fetchall()]
        stale = [k for k in rows if k not in keep]
        for k in stale:
            _db().execute("UPDATE projects SET status = 'studied', rank = NULL WHERE key = ?", (k,))
        if stale:
            _db().commit()
    return len(stale)


def drop_layer_alias(symbol: str, keep_token: str) -> int:
    """Remove the CoinGecko-era row of a layer once its CoinPaprika row exists:
    rows written before 07/10 carry a cg_id, and the same chain showed twice
    (FLOW as "flow" and "flow-flow")."""
    with _lock:
        cur = _db().execute("DELETE FROM projects WHERE chain = 'layer' AND cg_id IS NOT NULL"
                            " AND UPPER(symbol) = ? AND token != ?", ((symbol or "").upper(), keep_token))
        if cur.rowcount:
            _db().commit()
    return cur.rowcount


def set_standing(chain: str, token: str, status: str, score: float | None, rank: int | None, why: str = "") -> None:
    """Score and place after a later change (DeepSeek's report, review or
    code reading): the database follows the board without a new analysis."""
    if status not in ("studied", "ranked"):
        raise ValueError(status)
    with _lock:
        _db().execute("UPDATE projects SET status = ?, score = ?, rank = ?, why = ? WHERE key = ?"
                      " AND status IN ('studied', 'ranked')",
                      (status, score, rank, why or None, key(chain, token)))
        _db().commit()
    from app.trading.onchain import history
    history.append(key(chain, token), "projects_db.standing", {"status": status, "score": score, "rank": rank, "why": why or None})


def lift_rejected(chain: str, token: str) -> bool:
    """A row rejected under an old check whose working-set entry has since
    passed: back to "studied", so set_standing (studied/ranked only) can move it."""
    with _lock:
        cur = _db().execute("UPDATE projects SET status = 'studied' WHERE key = ? AND status = 'rejected'",
                            (key(chain, token),))
        _db().commit()
        return cur.rowcount > 0


def sync_top(keys: list[str]) -> int:
    """The Top is the ranking (Lorenzo, 29/09: HATCHER "Studied" and first on
    the podium). Every analysed row in `keys` becomes "ranked" at its place,
    with no exclusion text left beside it; a "ranked" row out of the Top goes
    back to "studied". Returns how many rows changed."""
    place = {k: i for i, k in enumerate(keys, 1)}
    changed = 0
    with _lock:
        rows = _db().execute("SELECT key, status, rank, why FROM projects WHERE status = 'ranked'"
                             f" OR key IN ({','.join('?' for _ in place) or 'NULL'})", tuple(place)).fetchall()
        for r in rows:
            k = r["key"]
            if k in place:
                if r["status"] in ("studied", "ranked") and (r["status"], r["rank"], r["why"]) != ("ranked", place[k], None):
                    _db().execute("UPDATE projects SET status = 'ranked', rank = ?, why = NULL WHERE key = ?",
                                  (place[k], k))
                    changed += 1
            else:
                _db().execute("UPDATE projects SET status = 'studied', rank = NULL WHERE key = ?", (k,))
                changed += 1
        if changed:
            _db().commit()
    return changed


def recheck(chain: str, token: str) -> bool:
    """Back in the analysis queue at once (the consistency audit's "recheck")."""
    with _lock:
        cur = _db().execute("UPDATE projects SET next_check = 0 WHERE key = ? AND status != 'analyzing'",
                            (key(chain, token),))
        _db().commit()
        return cur.rowcount > 0


# ------------------------------------------------------------------ reading

def reset_empty_market() -> int:
    """EVM rows stamped "no pool" by the case bug in apply_pairs: ask again."""
    with _lock:
        cur = _db().execute("UPDATE projects SET market_at = NULL WHERE mcap IS NULL AND token LIKE '0x%'"
                            " AND market_at IS NOT NULL")
        _db().commit()
        return cur.rowcount


def stale_market(limit: int, now: float | None = None) -> dict[str, list[str]]:
    """Tokens whose market is unknown or old, oldest first, by chain."""
    now = now or time.time()
    with _lock:
        rows = _db().execute(
            "SELECT chain, token FROM projects WHERE chain != 'layer'"
            " AND (market_at IS NULL OR market_at < ?)"
            " ORDER BY COALESCE(market_at, 0) LIMIT ?", (now - MARKET_TTL_S, limit)).fetchall()
    out: dict[str, list[str]] = {}
    for r in rows:
        out.setdefault(r["chain"], []).append(r["token"])
    return out


def _band_sql() -> str:
    return (f"mcap BETWEEN {CAP_MIN} AND {CAP_MAX} AND COALESCE(liq, 0) >= {LIQ_MIN}"
            f" AND COALESCE(cg_mcap, 0) <= {CAP_MAX} AND chain != 'layer'")


def need_detail(limit: int, now: float | None = None) -> list[dict]:
    """In the band, known to CoinGecko, never (or long ago) read in detail:
    CoinGecko's own page gives the website and the GitHub."""
    now = now or time.time()
    with _lock:
        rows = _db().execute(
            f"SELECT chain, cg_id, symbol, name, mcap, image FROM projects WHERE cg_id IS NOT NULL AND {_band_sql()}"
            " AND (detail_at IS NULL OR detail_at < ? OR cg_mcap IS NULL) ORDER BY liq DESC LIMIT ?",
            (now - DETAIL_TTL_S, limit)).fetchall()
    return [{"id": r["cg_id"], "chain": r["chain"], "symbol": (r["symbol"] or "").upper(), "name": r["name"] or "",
             "market_cap": r["mcap"], "image": r["image"]} for r in rows]


def mark_detail(chain: str, cg_id: str, now: float | None = None, cg_mcap: float | None = None) -> None:
    with _lock:
        _db().execute("UPDATE projects SET detail_at = ?, cg_mcap = ? WHERE chain = ? AND cg_id = ?",
                      (now or time.time(), float(cg_mcap) if cg_mcap else 0, chain, cg_id))
        _db().commit()


def reject_cg(chain: str, cg_id: str, why: str, now: float | None = None) -> None:
    """A coin CoinGecko itself says is big: out of the band, looked at again
    in two weeks (the cap can fall)."""
    now = now or time.time()
    with _lock:
        _db().execute("UPDATE projects SET status = 'rejected', why = ?, analyzed_at = ?, next_check = ?,"
                      " rank = NULL WHERE chain = ? AND cg_id = ?",
                      (why, now, now + RECHECK_S, chain, cg_id))
        _db().commit()


def due_for_analysis(limit: int, exclude: set[str] | None = None, now: float | None = None) -> list[dict]:
    """What the board should look at next: in the band, with a website or
    a GitHub to read, never analysed or due for a second look. Projects
    with code first, then the deepest pools."""
    now = now or time.time()
    exclude = exclude or set()
    with _lock:
        rows = _db().execute(
            f"SELECT * FROM projects WHERE {_band_sql()} AND (website IS NOT NULL OR github IS NOT NULL)"
            " AND status != 'analyzing' AND next_check <= ?"
            " ORDER BY (github IS NOT NULL) DESC, (analyzed_at IS NULL) DESC, liq DESC LIMIT ?",
            (now, limit + len(exclude))).fetchall()
    out = [_row(r) for r in rows if r["key"] not in exclude]
    return out[:limit]


def reject_linkless(now: float | None = None) -> int:
    """Rows in the band with nothing to read get a verdict instead of
    sitting "new" for ever: `due_for_analysis` skips them, and the funnel
    counted them as neither studied nor rejected (Lorenzo, 07/10: "ce ne
    mancano tanti"). DexScreener links put them back in the queue
    (`_set_links`)."""
    now = now or time.time()
    with _lock:
        cur = _db().execute(
            f"UPDATE projects SET status = 'rejected', why = ?, analyzed_at = ?, next_check = ?"
            f" WHERE {_band_sql()} AND website IS NULL AND github IS NULL AND status = 'new'",
            (NO_LINKS, now, now + RECHECK_DATA_S))
        if cur.rowcount:
            _db().commit()
        return cur.rowcount


def as_item(p: dict) -> dict:
    """A database row in the shape the board's `add` takes."""
    return {"chain": p["chain"], "token_address": p["token"], "symbol": p.get("symbol") or "?",
            "name": p.get("name") or "", "website": p.get("website"), "github": p.get("github"),
            "image": p.get("image"), "description": p.get("description"), "categories": p.get("categories") or [],
            "socials": p.get("socials") or [], "market_cap": p.get("mcap"), "liquidity_usd": p.get("liq"),
            "launched_at": p.get("launched_at")}


LAYERS = ("L0", "L1", "L2")  # layers.py writes the type in overall.layer
_LIST_COLUMNS = ("key, chain, token, symbol, name, website, github, image, mcap, liq, vol24, launched_at,"
                 " first_seen, analyzed_at, status, why, score, rank, sources, narratives, traction, overall,"
                 " description, categories")
SORTS = {"score": "COALESCE(score, -1) DESC", "cap": "COALESCE(mcap, 0) ASC", "liq": "COALESCE(liq, 0) DESC",
         "recent": "first_seen DESC", "checked": "COALESCE(analyzed_at, 0) DESC"}


def search(q: str = "", status: str = "", sort: str = "score", limit: int = 50, offset: int = 0,
           in_band: bool = False, narrative: str = "", chain: str = "", layer: str = "",
           full: bool = False) -> dict:
    """`full` returns whole rows, as get() does: what final_score reads
    (pillars, cg_mcap...). The lighter default is for lists that only show
    the row (Lorenzo, 17/10: the arenas scored without pillars, the token
    page with them)."""
    where, args = [], []
    if layer in LAYERS:
        where.append("chain = 'layer' AND json_extract(overall, '$.layer') = ?")
        args.append(layer)
    elif chain.isalnum():
        where.append("chain = ?")
        args.append(chain)
    keys = [k for k in (x.strip() for x in (narrative or "").split(",")) if k.replace("_", "").isalnum()]
    if keys:
        # '"key"' matches both a list of keys and a list of {"key": ...} dicts
        where.append("(" + " OR ".join("narratives LIKE ? ESCAPE '\\'" for _ in keys) + ")")
        args += ['%"' + k.replace("_", "\\_") + '"%' for k in keys]
    if q:
        where.append("(symbol LIKE ? OR name LIKE ? OR token = ? OR website LIKE ?)")
        like = f"%{q.strip()}%"
        args += [like, like, q.strip(), like]
    if status in STATUSES:
        where.append("status = ?")
        args.append(status)
    if in_band:
        where.append(_band_sql())
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    order = SORTS.get(sort, SORTS["score"])
    limit = max(1, min(int(limit), 200))
    with _lock:
        total = _db().execute(f"SELECT COUNT(*) FROM projects {clause}", args).fetchone()[0]
        rows = _db().execute(
            f"SELECT {'*' if full else _LIST_COLUMNS} FROM projects {clause} ORDER BY {order} LIMIT ? OFFSET ?",
            (*args, limit, max(0, int(offset)))
        ).fetchall()
    return {"total": total, "items": [_row(r) for r in rows]}


def recheck_studied(patterns: tuple[str, ...], statuses: tuple[str, ...] = ("studied",)) -> int:
    """Projects held back only by an old limit: put them back in the queue.
    Lorenzo, 28/09: the $3M / one-year limits were raised to $25M / three
    years (#259), so rows rejected with "over $3M" or "over N days" deserve
    a fresh look. `statuses` widens it to other rows (29/09: rules dropped
    outright). Returns how many rows were changed."""
    statuses = tuple(x for x in statuses if x in STATUSES and x != "analyzing")
    if not patterns or not statuses:
        return 0
    where = " OR ".join("why LIKE ?" for _ in patterns)
    marks = ", ".join("?" for _ in statuses)
    with _lock:
        cur = _db().execute(f"UPDATE projects SET next_check = 0 WHERE status IN ({marks}) AND ({where})",
                            (*statuses, *(f"%{p}%" for p in patterns)))
        _db().commit()
        return cur.rowcount


def scored_rows() -> list[dict]:
    """Every studied or ranked row: what a rescore walks over."""
    with _lock:
        rows = _db().execute("SELECT * FROM projects WHERE status IN ('studied', 'ranked')").fetchall()
    return [_row(r) for r in rows]


def rescore_many(rows: list[tuple[str, float | None, str]]) -> int:
    """(key, score, why) for many rows in one transaction, no new analysis:
    the score formula changed, the readings did not."""
    if not rows:
        return 0
    with _lock:
        cur = _db().executemany("UPDATE projects SET score = ?, why = ? WHERE key = ? AND status IN ('studied', 'ranked')",
                                [(s, w or None, k) for k, s, w in rows])
        _db().commit()
        return cur.rowcount


def requeue(statuses: tuple[str, ...] = ("studied", "ranked"), why_like: tuple[str, ...] = ()) -> int:
    """Back in the analysis queue: rows of `statuses`, or only those whose
    reason matches `why_like`. The nightly run takes them a few at a tick."""
    statuses = tuple(x for x in statuses if x in STATUSES and x != "analyzing")
    if not statuses:
        return 0
    marks = ", ".join("?" for _ in statuses)
    where = (" AND (" + " OR ".join("why LIKE ?" for _ in why_like) + ")") if why_like else ""
    with _lock:
        cur = _db().execute(f"UPDATE projects SET next_check = 0 WHERE status IN ({marks}){where}",
                            (*statuses, *(f"{p}%" for p in why_like)))
        _db().commit()
        return cur.rowcount


_NARR_ORDER = ("CASE status WHEN 'ranked' THEN 0 WHEN 'studied' THEN 1 WHEN 'new' THEN 2"
               " WHEN 'analyzing' THEN 3 WHEN 'rejected' THEN 4 ELSE 5 END")


def need_narratives(limit: int, before: float = 0.0) -> list[dict]:
    """Rows DeepSeek has not mapped to narratives yet, or mapped before
    `before` (an older catalogue), best first."""
    with _lock:
        rows = _db().execute(
            "SELECT chain, token, symbol, name, website, description, categories, narratives FROM projects"
            f" WHERE narr_at IS NULL OR narr_at < ? ORDER BY {_NARR_ORDER}, COALESCE(score, -1) DESC LIMIT ?",
            (float(before), max(1, int(limit)))).fetchall()
    return [_row(r) for r in rows]


def set_narratives(chain: str, token: str, keys: list[str], now: float | None = None) -> None:
    with _lock:
        _db().execute("UPDATE projects SET narratives = ?, narr_at = ? WHERE key = ?",
                      (json.dumps(list(keys)), now or time.time(), key(chain, token)))
        _db().commit()


def narrative_progress() -> dict:
    with _lock:
        mapped, total = _db().execute("SELECT COUNT(narr_at), COUNT(*) FROM projects").fetchone()
    return {"mapped": mapped, "total": total}


def narrative_counts() -> dict[str, int]:
    """How many projects each narrative key has, from the rows' JSON column."""
    out: dict[str, int] = {}
    with _lock:
        rows = _db().execute("SELECT narratives FROM projects WHERE narratives IS NOT NULL").fetchall()
    for (raw,) in rows:
        try:
            keys = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            continue
        for k in keys or []:
            out[k] = out.get(k, 0) + 1
    return out


def stats() -> dict:
    with _lock:
        db = _db()
        total = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        by = dict(db.execute("SELECT status, COUNT(*) FROM projects GROUP BY status").fetchall())
        band = db.execute(f"SELECT COUNT(*) FROM projects WHERE {_band_sql()}").fetchone()[0]
        band_by = dict(db.execute(f"SELECT status, COUNT(*) FROM projects WHERE {_band_sql()} GROUP BY status").fetchall())
        chains = dict(db.execute("SELECT chain, COUNT(*) FROM projects GROUP BY chain").fetchall())
        layers = dict(db.execute("SELECT json_extract(overall, '$.layer') t, COUNT(*) FROM projects"
                                 " WHERE chain = 'layer' GROUP BY t").fetchall())
        reasons = db.execute(
            "SELECT why, COUNT(*) n FROM projects WHERE status = 'rejected' AND why IS NOT NULL"
            " GROUP BY why ORDER BY n DESC LIMIT 8").fetchall()
    # by_status counts every row (layers and rows outside the band included),
    # so it never added up to in_band: band_by_status is the same funnel inside it.
    return {"total": total, "in_band": band, "band": [CAP_MIN, CAP_MAX], "band_by_status": band_by,
            "band_waiting": band_by.get("new", 0) + band_by.get("analyzing", 0), "by_status": by, "by_chain": chains,
            "by_layer": {k: v for k, v in layers.items() if k in LAYERS},
            "top_rejections": [{"why": r[0], "n": r[1]} for r in reasons]}
