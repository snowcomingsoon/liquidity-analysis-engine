"""Archivio delle candele della Top 50, su ogni sorgente della scala.

Lorenzo, 30/09: "visto che GeckoTerminal fornisce lentamente queste candele,
mettiamo un motore che le scarica costantemente per quelle che sono la top
50 e le archiviamo, cosi' poi quando ci servono ce l'abbiamo".

Ogni (pool, lato del token, timeframe GeckoTerminal) e' una serie in SQLite
sul volume. `candles()` risponde dall'archivio se e' fresco, altrimenti
chiede a GeckoTerminal solo il pezzo che manca e lo aggiunge: la serie
cresce oltre le 1000 barre di una chiamata (i 5 minuti non si fermano piu' a
tre giorni e mezzo). `archive_loop` tiene calde tutte le sorgenti dei token
della Top quando GeckoTerminal ha margine, cosi' il laboratorio (e ogni
prova di una regola nuova) legge da disco invece di aspettare.
"""
from __future__ import annotations

import asyncio
import contextvars
import logging
import sqlite3
import threading
import time
from typing import Callable

import httpx

from app import http_client

from app.trading.onchain import alert_track, priority
from app.trading.onchain.storage import data_file

logger = logging.getLogger(__name__)

_DB_FILE = data_file("candle_archive.sqlite")
# Set by the daily ladder check (ladder_watch): answer from disk only, no
# GeckoTerminal call and no write, without touching the lab running beside it.
offline: contextvars.ContextVar[bool] = contextvars.ContextVar("candle_archive_offline", default=False)
_lock = threading.Lock()
_conn: sqlite3.Connection | None = None
_conn_path = None

# Every GeckoTerminal series the ladder builds its rungs from.
SOURCES = [("day", 1), ("hour", 12), ("hour", 4), ("hour", 1), ("minute", 15), ("minute", 5)]
UNIT_S = {"day": 86400, "hour": 3600, "minute": 60}
FRESH_MAX_S = 3600          # the lab reruns a token every hour: no series older than that
MAX_BARS = 5000             # per series; the oldest go first
LIMIT = 1000                # one GeckoTerminal call
# One call every TICK_S, through the shared background limiter (14 a
# minute): it waits its turn instead of skipping. The first version only
# ran below 10 calls a minute, and the other background jobs keep the load
# at the cap, so after 4 hours (30/09) the 12h, 1h and 15m series of the
# Top 50 were still empty.
TICK_S = 20
WARM_S = 3 * 3600           # the loop keeps every series at most this old; the lab tops up the rest

_SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
    k TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, PRIMARY KEY (k, t)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS fetched (k TEXT PRIMARY KEY, at REAL, n INTEGER);
CREATE TABLE IF NOT EXISTS series (k TEXT PRIMARY KEY, provider TEXT NOT NULL, version TEXT);
"""
# Provenance (19/10, candles squid): one provider per series, never mixed.
# The archive is filled from GeckoTerminal only (or the exchange, net "cex");
# series written before this table are GeckoTerminal's, the "cex" ones the
# exchange's, by the only paths that ever wrote them.
PROVIDER_GECKO = "geckoterminal"
PROVIDER_CEX = "cex"


def _db() -> sqlite3.Connection:
    global _conn, _conn_path
    if _conn is None or _conn_path != _DB_FILE:
        _conn = sqlite3.connect(_DB_FILE, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(_SCHEMA)
        _conn.execute("INSERT OR IGNORE INTO series (k, provider, version) SELECT k, CASE WHEN k LIKE 'cex:%' "
                      "THEN ? ELSE ? END, 'legacy' FROM fetched", (PROVIDER_CEX, PROVIDER_GECKO))
        _conn.commit()
        _conn_path = _DB_FILE
    return _conn


def key(net: str, pair: str, tf: str, agg: int, token: str = "") -> str:
    return f"{net}:{pair}:{(token or '').lower()}:{tf}{agg}"


def step_of(tf: str, agg: int) -> int:
    return UNIT_S[tf] * agg


def fresh_s(tf: str, agg: int) -> int:
    return min(step_of(tf, agg), FRESH_MAX_S)


def get(k: str) -> list[list]:
    with _lock:
        rows = _db().execute("SELECT t, o, h, l, c, v FROM candles WHERE k = ? ORDER BY t", (k,)).fetchall()
    return [list(r) for r in rows]


def fetched_at(k: str) -> float | None:
    with _lock:
        row = _db().execute("SELECT at FROM fetched WHERE k = ?", (k,)).fetchone()
    return row[0] if row else None


def put(k: str, rows: list[list], now: float) -> None:
    good = [(k, int(r[0]), *(float(x) for x in r[1:6])) for r in rows
            if len(r) >= 6 and all(isinstance(x, (int, float)) for x in r[:6])]
    with _lock:
        db = _db()
        db.executemany("INSERT OR REPLACE INTO candles VALUES (?, ?, ?, ?, ?, ?, ?)", good)
        n = db.execute("SELECT COUNT(*) FROM candles WHERE k = ?", (k,)).fetchone()[0]
        if n > MAX_BARS:
            db.execute("DELETE FROM candles WHERE k = ? AND t IN (SELECT t FROM candles WHERE k = ? ORDER BY t LIMIT ?)",
                       (k, k, n - MAX_BARS))
            n = MAX_BARS
        db.execute("INSERT OR REPLACE INTO fetched VALUES (?, ?, ?)", (k, now, n))
        db.execute("INSERT OR IGNORE INTO series (k, provider, version) VALUES (?, ?, ?)",
                   (k, provider_of(k), None))
        db.commit()


def provider_of(k: str) -> str:
    return PROVIDER_CEX if k.startswith("cex:") else PROVIDER_GECKO


def series_provider(k: str) -> str | None:
    with _lock:
        row = _db().execute("SELECT provider FROM series WHERE k = ?", (k,)).fetchone()
    return row[0] if row else None


async def candles(client: httpx.AsyncClient, net: str, pair: str, tf: str, agg: int, now: float,
                  token: str = "") -> list | None:
    """The whole archived series, topped up from GeckoTerminal when older
    than fresh_s. [] = the pool is unknown there; None = no answer and
    nothing archived (try again later)."""
    k = key(net, pair, tf, agg, token)
    if offline.get():
        return await asyncio.to_thread(get, k)
    at = await asyncio.to_thread(fetched_at, k)
    if at is not None and now - at < fresh_s(tf, agg):
        return await asyncio.to_thread(get, k)
    # Only the missing stretch (plus a little overlap: the last candle was
    # still forming), or a full call the first time.
    limit = LIMIT if at is None else max(10, min(LIMIT, int((now - at) // step_of(tf, agg)) + 3))
    raw = await alert_track._candles(client, net, pair, tf, agg, now, limit, token, source="gecko")
    if raw is None:
        have = await asyncio.to_thread(get, k)
        return have or None
    await asyncio.to_thread(put, k, raw, now)
    return await asyncio.to_thread(get, k)


def status(pairs: list[tuple[str, str, str]], now: float | None = None) -> dict:
    """How much of the Top's candles is on disk and fresh."""
    now = now or time.time()
    total = fresh = bars = 0
    with _lock:
        db = _db()
        for net, pair, token in pairs:
            for tf, agg in SOURCES:
                total += 1
                row = db.execute("SELECT at, n FROM fetched WHERE k = ?", (key(net, pair, tf, agg, token),)).fetchone()
                if row:
                    bars += row[1] or 0
                    fresh += now - row[0] < fresh_s(tf, agg)
    return {"series": total, "fresh": fresh, "bars": bars}


def next_due(pairs: list[tuple[str, str, str]], now: float) -> tuple[str, str, str, str, int] | None:
    """The stalest series among the Top's older than WARM_S: never fetched first."""
    best, best_age = None, -1.0
    with _lock:
        db = _db()
        for net, pair, token in pairs:
            for tf, agg in SOURCES:
                row = db.execute("SELECT at FROM fetched WHERE k = ?", (key(net, pair, tf, agg, token),)).fetchone()
                age = float("inf") if row is None else now - row[0]
                if age >= WARM_S and age > best_age:
                    best, best_age = (net, pair, token, tf, agg), age
    return best


def _pairs(entries: list[dict]) -> list[tuple[str, str, str]]:
    """(network, pool, token) of the Top's tokens whose pool the lab knows."""
    from app.sniper.scanner import GECKO_NETWORKS
    from app.trading.onchain import strategy_lab
    out = []
    for e in entries:
        net = GECKO_NETWORKS.get(e.get("chain") or "")
        k = strategy_lab.key_of(e.get("chain") or "", e.get("token_address") or "")
        pair = (strategy_lab._results.get(k) or {}).get("pair") or e.get("pair")
        if net and pair:
            out.append((net, pair, e.get("token_address") or ""))
    return out


async def tick(entries: list[dict], now: float | None = None) -> bool:
    """One series refreshed, the stalest of the Top's. True = fetched. The
    queue is the `fetched` table on disk: a restart resumes where it was."""
    now = now or time.time()
    if priority.backtests_first():
        return False
    due = await asyncio.to_thread(next_due, _pairs(entries), now)
    if due is None:
        return False
    net, pair, token, tf, agg = due
    async with http_client.pooled(timeout=15.0) as client:
        got = await candles(client, net, pair, tf, agg, now, token)
    return got is not None


async def archive_loop(entries: Callable[[], list[dict]]) -> None:
    await asyncio.sleep(TICK_S * 3)
    while True:
        try:
            await tick(entries())
        except Exception:
            logger.exception("candle archive: giro fallito")
        await asyncio.sleep(TICK_S)
