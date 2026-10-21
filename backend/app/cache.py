import asyncio

from cachetools import TTLCache

_INTRADAY_TTL = 90
_DAILY_TTL = 600

# 2d/3d/5d are folded from daily candles: they move as slowly as "1d".
_DAILY_PLUS_INTERVALS = {"1d", "2d", "3d", "5d", "1w", "1M"}

_intraday_cache: TTLCache = TTLCache(maxsize=256, ttl=_INTRADAY_TTL)
_daily_cache: TTLCache = TTLCache(maxsize=256, ttl=_DAILY_TTL)
_lock = asyncio.Lock()

# Singleflight: one in-flight Future per cache key — followers await the same
# Future instead of spawning duplicate fetches for the same (symbol, interval).
_in_flight: dict[tuple, asyncio.Future] = {}

# Last good answer per key, kept past the TTL for the chart only (see
# get_or_fetch_stale). Small: a 3000-candle frame is ~150 KB.
_STALE_INTRADAY_S = 15 * 60
_STALE_DAILY_S = 6 * 3600
_stale_intraday: TTLCache = TTLCache(maxsize=48, ttl=_STALE_INTRADAY_S)
_stale_daily: TTLCache = TTLCache(maxsize=48, ttl=_STALE_DAILY_S)
_refreshing: set[asyncio.Task] = set()


def _cache_for(interval: str) -> TTLCache:
    return _daily_cache if interval in _DAILY_PLUS_INTERVALS else _intraday_cache


async def get_or_fetch(key: tuple, fetch_fn):
    cache = _cache_for(key[1])
    async with _lock:
        if key in cache:
            return cache[key]
        if key in _in_flight:
            fut: asyncio.Future = _in_flight[key]
            leader = False
        else:
            fut = asyncio.get_event_loop().create_future()
            _in_flight[key] = fut
            leader = True

    if not leader:
        # Wait for whoever started the fetch to finish; propagates exceptions.
        return await asyncio.shield(fut)

    try:
        result = await fetch_fn()
        async with _lock:
            cache[key] = result
            (_stale_daily if cache is _daily_cache else _stale_intraday)[key] = result
        fut.set_result(result)
        return result
    except Exception as exc:
        fut.set_exception(exc)
        raise
    finally:
        async with _lock:
            _in_flight.pop(key, None)


async def get_or_fetch_stale(key: tuple, fetch_fn) -> tuple[object, bool]:
    """Like get_or_fetch, but past the TTL it answers at once with the last
    good frame (up to 15 min intraday, 6 h daily and up) and refreshes it in
    the background. Returns (value, stale). Only for the chart: opening it
    waited 2-3 s on the exchange every time the 90 s / 10 min cache had
    expired, and the page fetches a fresh copy right after a stale answer."""
    cache = _cache_for(key[1])
    async with _lock:
        if key in cache:
            return cache[key], False
        old = (_stale_daily if cache is _daily_cache else _stale_intraday).get(key)
    if old is None:
        return await get_or_fetch(key, fetch_fn), False

    async def _refresh():
        try:
            await get_or_fetch(key, fetch_fn)
        except Exception:  # noqa: BLE001 — the next request retries in the foreground
            pass

    task = asyncio.get_running_loop().create_task(_refresh())
    _refreshing.add(task)
    task.add_done_callback(_refreshing.discard)
    return old, True
