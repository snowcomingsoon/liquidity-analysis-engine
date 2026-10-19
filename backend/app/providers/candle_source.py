"""Where a pool's candles come from: GeckoTerminal, or the candles squid
for the Ethereum Uniswap V3 pools it indexes (ISTRUZIONI_CLAUDE_SQUID.md,
phase 5; services/candles-squid).

settings.squid_mode:
- "off" (default): GeckoTerminal only, as before. The squid is not called.
- "compare": every answer still comes from GeckoTerminal; for the requests
  the squid could have served, its candles are fetched too and compared
  (counters in metrics(), file data/candle_source.json). Nothing decides on
  the squid's data.
- "on": the squid serves a request only when it covers it entirely (see
  `fetch`); anything else goes to GeckoTerminal, whole.

A request is served by one source end to end: a window the squid covers only
in part is never stitched to GeckoTerminal's candles. The rows returned keep
GeckoTerminal's contract: [timestamp_s, open, high, low, close, volume],
newest first, prices and volume in USD, the price of the requested token's
side.

Statuses (Result.status), kept apart on purpose:
- "unsupported": not a pool, side, timeframe or chain the squid indexes;
- "lagging": the squid's last indexed block is older than squid_max_lag_s;
- "incomplete": the window reaches before the squid's start for that pool,
  or after its last indexed block, or holds a bucket it could not price;
- "no_trades": covered, indexed, and no swap in the window;
- "error": the squid did not answer;
- "ok": covered and answered.
Only "ok" is ever used in "on" mode; "no_trades" too goes to GeckoTerminal,
so an empty answer keeps meaning what it meant for its callers.
"""
from __future__ import annotations

import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path


from app import http_client
from app.config import settings

logger = logging.getLogger(__name__)

PROVIDER_GECKO = "geckoterminal"
PROVIDER_SQUID = "squid:candles-squid@1"
# GeckoTerminal (timeframe, aggregate) -> squid timeframe in seconds
TF_SECONDS = {("minute", 5): 300, ("minute", 15): 900, ("hour", 1): 3600, ("day", 1): 86400}
SQUID_NET = "eth"
MAX_ROWS = 5000
STATUS_TTL_S = 15.0

_status_cache: dict = {"at": 0.0, "value": None}
_pools_cache: dict = {"at": 0.0, "value": None}
_stats: dict = {"requests": {}, "compared": 0, "close_diff": [], "volume_diff": [], "only_gecko": 0, "only_squid": 0}
_saved = {"at": 0.0}


@dataclass
class Result:
    status: str
    rows: list = field(default_factory=list)
    detail: str = ""


def mode() -> str:
    m = (settings.squid_mode or "off").strip().lower()
    return m if m in ("off", "compare", "on") else "off"


def allowlist() -> set[str]:
    return {p.strip().lower() for p in (settings.squid_pools or "").split(",") if p.strip()}


def reset_for_tests() -> None:
    _status_cache.update(at=0.0, value=None)
    _pools_cache.update(at=0.0, value=None)
    _stats.update(requests={}, compared=0, close_diff=[], volume_diff=[], only_gecko=0, only_squid=0)
    _saved["at"] = 0.0


async def _gql(query: str, variables: dict | None = None) -> dict:
    async with http_client.pooled(timeout=10.0) as client:
        r = await client.post(settings.squid_url, json={"query": query, "variables": variables or {}})
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise RuntimeError(str(body["errors"])[:200])
    return body["data"]


async def _status() -> dict | None:
    now = time.monotonic()
    if _status_cache["value"] is not None and now - _status_cache["at"] < STATUS_TTL_S:
        return _status_cache["value"]
    rows = (await _gql("{ syncStatuses { block timestamp finalizedBlock } }"))["syncStatuses"]
    value = rows[0] if rows else None
    _status_cache.update(at=now, value=value)
    return value


async def _pools() -> dict[str, dict]:
    now = time.monotonic()
    if _pools_cache["value"] is not None and now - _pools_cache["at"] < 300:
        return _pools_cache["value"]
    rows = (await _gql("{ pools { id token0 token1 fromBlock fromTimestamp } }"))["pools"]
    value = {r["id"].lower(): r for r in rows}
    _pools_cache.update(at=now, value=value)
    return value


async def fetch(net: str, pool: str, timeframe: str, aggregate: int, token: str,
                start: float, end: float) -> Result:
    """The squid's candles of buckets starting in [start, end), as
    GeckoTerminal rows, or why not."""
    tf = TF_SECONDS.get((timeframe, int(aggregate)))
    pool, token = (pool or "").lower(), (token or "").lower()
    if net != SQUID_NET or tf is None or not token or pool not in allowlist():
        return Result("unsupported")
    try:
        st = await _status()
        info = (await _pools()).get(pool)
    except Exception as exc:  # noqa: BLE001 - a down squid is a fallback, never an error for the caller
        return Result("error", detail=type(exc).__name__)
    if st is None or info is None or token not in (info["token0"].lower(), info["token1"].lower()):
        return Result("unsupported", detail="pool or side not indexed")
    if time.time() - st["timestamp"] > settings.squid_max_lag_s:
        return Result("lagging", detail=f"indexed to {st['timestamp']}")
    first = int(start // tf * tf)
    if first < (info.get("fromTimestamp") or 0):
        return Result("incomplete", detail="before the squid's start for this pool")
    if end > st["timestamp"] + tf:
        return Result("incomplete", detail="after the last indexed block")
    q = """query($pool:String!,$token:String!,$tf:Int!,$from:Int!,$to:Int!,$n:Int!){
      candles(where:{pool_eq:$pool, token_eq:$token, timeframe_eq:$tf, start_gte:$from, start_lt:$to},
              orderBy: start_DESC, limit:$n){ start openUsd highUsd lowUsd closeUsd volumeUsd swaps pricedSwaps } }"""
    try:
        rows = (await _gql(q, {"pool": pool, "token": token, "tf": tf, "from": first, "to": int(end),
                               "n": MAX_ROWS}))["candles"]
    except Exception as exc:  # noqa: BLE001
        return Result("error", detail=type(exc).__name__)
    if not rows:
        return Result("no_trades")
    if any(r["pricedSwaps"] < r["swaps"] or r["closeUsd"] is None for r in rows):
        return Result("incomplete", detail="a bucket without a USD price")
    return Result("ok", [[r["start"], float(r["openUsd"]), float(r["highUsd"]), float(r["lowUsd"]),
                          float(r["closeUsd"]), float(r["volumeUsd"])] for r in rows])


def _count(status: str) -> None:
    _stats["requests"][status] = _stats["requests"].get(status, 0) + 1


def compare(gecko_rows: list, squid_rows: list, tf: int, indexed_ts: float | None = None) -> None:
    """Closed buckets present on both sides: relative difference of close
    and volume. Kept as counters, never used to decide."""
    end = time.time() if indexed_ts is None else min(time.time(), indexed_ts)
    g = {int(r[0]): r for r in gecko_rows if int(r[0]) + tf <= end}
    s = {int(r[0]): r for r in squid_rows if int(r[0]) + tf <= end}
    for t in g.keys() & s.keys():
        gc, sc = float(g[t][4]), float(s[t][4])
        gv, sv = float(g[t][5]), float(s[t][5])
        if gc:
            _stats["close_diff"].append(abs(sc - gc) / abs(gc))
        if gv:
            _stats["volume_diff"].append(abs(sv - gv) / abs(gv))
        _stats["compared"] += 1
    _stats["only_gecko"] += len(g.keys() - s.keys())
    _stats["only_squid"] += len(s.keys() - g.keys())
    for k in ("close_diff", "volume_diff"):
        del _stats[k][:-5000]


async def _compare_later(gecko_rows: list, net, pool, timeframe, aggregate, token, start, end) -> None:
    res = await fetch(net, pool, timeframe, aggregate, token, start, end)
    _count(res.status)
    if res.status == "ok":
        compare(gecko_rows, res.rows, TF_SECONDS[(timeframe, int(aggregate))],
                (_status_cache["value"] or {}).get("timestamp"))


async def route(net: str, pool: str, timeframe: str, aggregate: int, token: str, start: float, end: float,
                gecko) -> tuple[list | None, str]:
    """Rows for buckets in [start, end) and the provider that gave them.
    `gecko` is a no-argument coroutine function returning the caller's own
    GeckoTerminal rows (or None / [] with their usual meaning)."""
    m = mode()
    if m == "on":
        res = await fetch(net, pool, timeframe, aggregate, token, start, end)
        _count(res.status)
        if res.status == "ok":
            return res.rows, PROVIDER_SQUID
        return await gecko(), PROVIDER_GECKO
    rows = await gecko()
    if m == "compare" and rows and (timeframe, int(aggregate)) in TF_SECONDS and net == SQUID_NET \
            and (pool or "").lower() in allowlist():
        task = asyncio.create_task(_compare_later(list(rows), net, pool, timeframe, aggregate, token, start, end))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    return rows, PROVIDER_GECKO


_tasks: set = set()


def metrics() -> dict:
    def q(v):
        if not v:
            return None
        s = sorted(v)
        return {"n": len(s), "median": round(statistics.median(s), 6), "p95": round(s[int(0.95 * (len(s) - 1))], 6),
                "max": round(s[-1], 6)}
    return {"mode": mode(), "pools": sorted(allowlist()), "requests_by_status": dict(_stats["requests"]),
            "compared_buckets": _stats["compared"], "only_gecko": _stats["only_gecko"],
            "only_squid": _stats["only_squid"], "close_diff": q(_stats["close_diff"]),
            "volume_diff": q(_stats["volume_diff"]), "squid_status": _status_cache["value"]}


def save(path: Path, now: float | None = None) -> bool:
    """Counters on file every 5 minutes when the squid is in use."""
    now = now or time.time()
    if mode() == "off" or now - _saved["at"] < 300:
        return False
    _saved["at"] = now
    try:
        path.write_text(json.dumps({**metrics(), "saved_at": now}), encoding="utf-8")
        return True
    except OSError:
        logger.exception("candle source metrics not saved")
        return False


