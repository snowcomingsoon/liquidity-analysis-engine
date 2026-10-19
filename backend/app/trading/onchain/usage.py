"""Real usage of a token: volume, trades, distinct traders, holders.

Measurement only, from free public APIs: DexScreener (volume, trades,
liquidity, market cap; batched 30 addresses a call) and GeckoTerminal
(buyers/sellers, daily volumes, holders). GeckoTerminal calls go through the
shared rate gate in app.providers.dexscreener. A daily store keeps one
snapshot per token per UTC day, 60 days, so holder growth can be measured.
A value no source returned stays None, never 0.
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
from datetime import datetime, timezone

import httpx

from app.atomic_write import write_text_atomic
from app.trading.onchain import storage
from app.trading.onchain.research import GECKO_NET

DEX_TOKENS = "https://api.dexscreener.com/tokens/v1/{chain}/{addresses}"
GECKO = "https://api.geckoterminal.com/api/v2/networks/{net}"
DEX_BATCH = 30
KEEP_DAYS = 60
FILE_NAME = "usage_history.json"

_lock = threading.Lock()
_cache: dict | None = None


def _num(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x else None       # NaN is not a number here


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def _key(chain: str, token: str) -> str:
    # Solana addresses are case-sensitive, EVM ones are not
    return f"{chain}:{token if chain == 'solana' else token.lower()}"


# --- sources --------------------------------------------------------------

async def _dex_pairs(client: httpx.AsyncClient, chain: str, tokens: list[str]) -> list[dict] | None:
    """All pairs for up to 30 tokens in one call; None = no answer."""
    try:
        r = await client.get(DEX_TOKENS.format(chain=chain, addresses=",".join(tokens)), timeout=15.0)
        if r.status_code != 200:
            return None
        data = r.json()
    except (httpx.HTTPError, ValueError):
        return None
    return [p for p in data if isinstance(p, dict)] if isinstance(data, list) else None


def _pick_pair(pairs: list[dict], chain: str, token: str, pool: str | None) -> dict | None:
    """The given pool, else the token's most liquid pair."""
    k = _key(chain, token)
    mine = [p for p in pairs if _key(chain, ((p.get("baseToken") or {}).get("address") or "")) == k
            and (p.get("chainId") or chain) == chain]
    if pool:
        hit = [p for p in mine if _key(chain, p.get("pairAddress") or "") == _key(chain, pool)]
        if hit:
            return hit[0]
    if not mine:
        return None
    return max(mine, key=lambda p: _num((p.get("liquidity") or {}).get("usd")) or 0.0)


def _from_pair(p: dict) -> dict:
    tx = (p.get("txns") or {}).get("h24") or {}
    buys, sells = _num(tx.get("buys")), _num(tx.get("sells"))
    mcap = _num(p.get("marketCap"))
    return {"vol_24h": _num((p.get("volume") or {}).get("h24")),
            "tx_24h": int(buys + sells) if buys is not None and sells is not None else None,
            "liq": _num((p.get("liquidity") or {}).get("usd")),
            "mcap": mcap if mcap is not None else _num(p.get("fdv")),
            "pool": p.get("pairAddress")}


async def _gecko(client: httpx.AsyncClient, url: str, params: dict | None = None,
                 caller: str = "usage") -> dict | None:
    """One GeckoTerminal call through the shared gate; one retry on 429
    (the gate makes the retry wait out the 429's Retry-After)."""
    from app.providers import gecko_client
    for _ in range(2):
        try:
            r = await gecko_client.request(client, url, params=params, timeout=15.0,
                                           headers={"Accept": "application/json"}, caller=caller)
        except httpx.HTTPError:
            return None
        if r.status_code == 429:
            continue
        if r.status_code != 200:
            return None
        try:
            data = r.json()
        except ValueError:
            return None
        return data if isinstance(data, dict) else None
    return None


async def _gecko_pool(client, net: str, pool: str) -> dict:
    data = await _gecko(client, f"{GECKO.format(net=net)}/pools/{pool}")
    if not data:
        return {}
    a = (data.get("data") or {}).get("attributes") or {}
    h24 = (a.get("transactions") or {}).get("h24") or {}
    b, s = _num(h24.get("buyers")), _num(h24.get("sellers"))
    return {"buyers_24h": int(b) if b is not None else None, "sellers_24h": int(s) if s is not None else None}


def _buyers_of(attrs: dict) -> dict:
    h24 = (attrs.get("transactions") or {}).get("h24") or {}
    b, s = _num(h24.get("buyers")), _num(h24.get("sellers"))
    return {"buyers_24h": int(b) if b is not None else None, "sellers_24h": int(s) if s is not None else None}


async def _gecko_pools_multi(client, chain: str, net: str, pools: list[str]) -> dict[str, dict]:
    """Buyers and sellers of up to DEX_BATCH pools in one call (pools/multi):
    a call per pool was a third of the usage measure (19/10)."""
    out: dict[str, dict] = {}
    pools = list(dict.fromkeys(p for p in pools if p))
    for i in range(0, len(pools), DEX_BATCH):
        data = await _gecko(client, f"{GECKO.format(net=net)}/pools/multi/{','.join(pools[i:i + DEX_BATCH])}",
                            caller="usage:pools")
        for row in (data or {}).get("data") or []:
            a = (row or {}).get("attributes") or {}
            if a.get("address"):
                out[_key(chain, a["address"])] = _buyers_of(a)
    return out


DAILY_REFRESH_S = 7 * 86400      # GeckoTerminal's daily candles at most once a week per token
HISTORY_7D_MIN, HISTORY_30D_MIN = 6, 25


def _daily_from_history(chain: str, token: str, now: float) -> dict | None:
    """The 7- and 30-day volume averages from our own daily snapshots (each
    holds DexScreener's 24h volume), between two weekly GeckoTerminal reads;
    None when the history is too thin or the last read too old."""
    h = history(chain, token)
    read = [s for s in h if "geckoterminal_ohlcv" in (s.get("sources") or []) and s.get("days") is not None]
    if not read or now - read[-1]["at"] > DAILY_REFRESH_S:
        return None
    vols = {n: [s["vol_24h"] for s in h if s.get("vol_24h") is not None and now - s["at"] <= n * 86400]
            for n in (7, 30)}
    if len(vols[7]) < HISTORY_7D_MIN:
        return None
    last = read[-1]
    days = int(last["days"]) + int((now - last["at"]) // 86400)
    out = {"days": days, "vol_7d_avg": sum(vols[7]) / len(vols[7]),
           "vol_30d_avg": sum(vols[30]) / len(vols[30]) if len(vols[30]) >= min(HISTORY_30D_MIN, days) else None}
    if out["vol_30d_avg"] is None:
        return None
    return out


async def _gecko_daily(client, net: str, pool: str) -> dict:
    data = await _gecko(client, f"{GECKO.format(net=net)}/pools/{pool}/ohlcv/day",
                        {"limit": 31, "currency": "usd"}, caller="ohlcv:usage")
    if not data:
        return {}
    rows = ((data.get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
    rows = sorted((r for r in rows if isinstance(r, list) and len(r) >= 6 and _num(r[5]) is not None),
                  key=lambda r: r[0])
    if not rows:
        return {"days": 0}
    return _averages(rows, time.time())


def _averages(rows: list[list], now: float) -> dict:
    """Daily volume averages over calendar days, not over candles:
    GeckoTerminal leaves out days without trades (a month with one $200k day
    is not $200k a day), and today's candle is partial, so it is left out.
    A pool younger than the window is averaged over the days it has lived."""
    today = now - now % 86400
    first = _num(rows[0][0]) or today
    out: dict = {"days": sum(1 for r in rows if (_num(r[0]) or 0) < today)}
    for n, key in ((7, "vol_7d_avg"), (30, "vol_30d_avg")):
        start = today - n * 86400
        lived = min(n, int((today - max(first, start)) // 86400)) if first < today else 0
        if lived <= 0:
            out[key] = None
            continue
        out[key] = sum(_num(r[5]) for r in rows if start <= (_num(r[0]) or 0) < today) / lived
    return out


async def _gecko_holders(client, chain: str, token: str) -> dict:
    """Through research.gecko_info and its 6-hour cache: the token sheet asks
    GeckoTerminal for the same page, so one read serves both (19/10)."""
    from app.trading.onchain import research
    info = await research.gecko_info(chain, token, client)
    if not info:
        return {}
    count = _num(info.get("holders"))
    top10 = _num((info.get("holders_split") or {}).get("top_10"))
    return {"holders": int(count) if count is not None else None, "top10_pct": top10}


FIELDS = ("vol_24h", "vol_7d_avg", "vol_30d_avg", "days", "tx_24h", "buyers_24h", "sellers_24h",
          "liq", "mcap", "holders", "top10_pct")


async def _measure(client, chain: str, token: str, pool: str | None, pairs: list[dict] | None,
                   pool_info: dict[str, dict] | None = None) -> dict | None:
    out: dict = {"chain": chain, "token": token, "pool": pool, "at": time.time(),
                 **{f: None for f in FIELDS}, "sources": []}
    pair = _pick_pair(pairs, chain, token, pool) if pairs else None
    if pair:
        d = _from_pair(pair)
        out["pool"] = pool or d.pop("pool")
        d.pop("pool", None)
        out.update(d)
        out["sources"].append("dexscreener")
    net = GECKO_NET.get(chain)
    if net:
        pool_id = out["pool"]
        if pool_id:
            p = pool_info.get(_key(chain, pool_id)) if pool_info is not None else await _gecko_pool(client, net, pool_id)
            if p:
                out.update(p)
                out["sources"].append("geckoterminal_pool")
            derived = _daily_from_history(chain, token, out["at"]) if out.get("vol_24h") is not None else None
            if derived:
                out.update(derived)
                out["sources"].append("history")
            else:
                daily = await _gecko_daily(client, net, pool_id)
                if daily:
                    out.update(daily)
                    out["sources"].append("geckoterminal_ohlcv")
        hold = await _gecko_holders(client, chain, token)
        if hold:
            out.update(hold)
            out["sources"].append("geckoterminal_info")
    return out if out["sources"] else None


async def measure(client: httpx.AsyncClient, chain: str, token: str, pool: str | None = None) -> dict | None:
    """Usage of one token; None only if no source answered at all."""
    pairs = await _dex_pairs(client, chain, [token])
    return await _measure(client, chain, token, pool, pairs)


# --- daily store -----------------------------------------------------------

def _load() -> dict:
    global _cache
    if _cache is None:
        try:
            data = json.loads(storage.data_file(FILE_NAME).read_text())
            _cache = data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            _cache = {}
    return _cache


def _save(data: dict) -> None:
    write_text_atomic(storage.data_file(FILE_NAME), json.dumps(data, separators=(",", ":")))


def record(m: dict, save: bool = True) -> None:
    """One snapshot per token per UTC day (the latest wins), 60 days kept."""
    if not m or not m.get("chain") or not m.get("token"):
        return
    at = m.get("at") or time.time()
    cutoff = _day(time.time() - KEEP_DAYS * 86400)
    with _lock:
        data = _load()
        rows = data.setdefault(_key(m["chain"], m["token"]), {})
        rows[_day(at)] = {**m, "at": at}
        for d in [d for d in rows if d < cutoff]:
            rows.pop(d)
        if save:
            _save(data)


def history(chain: str, token: str) -> list[dict]:
    """Snapshots, oldest first."""
    rows = _load().get(_key(chain, token)) or {}
    return [rows[d] for d in sorted(rows)]


def latest(chain: str, token: str) -> dict | None:
    h = history(chain, token)
    return h[-1] if h else None


GROWTH_MIN_SPAN = 0.7            # of `days`: a day-old comparison is the count's own jitter


def holders_growth(chain: str, token: str, days: int = 30) -> float | None:
    """Relative change in holders vs the snapshot closest to `days` ago;
    None without a holder count on both ends or before the two snapshots
    are GROWTH_MIN_SPAN * days apart."""
    h = [s for s in history(chain, token) if s.get("holders")]
    if len(h) < 2:
        return None
    now = h[-1]
    target = now["at"] - days * 86400
    older = min(h[:-1], key=lambda s: abs(s["at"] - target))
    if now["at"] - older["at"] < GROWTH_MIN_SPAN * days * 86400:
        return None
    return now["holders"] / older["holders"] - 1


def measured_today(chain: str, token: str) -> bool:
    rows = _load().get(_key(chain, token)) or {}
    return _day(time.time()) in rows


# Tokens tried today that no source answered for (a layer, a pool nobody
# lists): not retried until tomorrow, so they neither hold the night open
# nor take every tick's quota.
_tried: dict[str, str] = {}


def tried_today(chain: str, token: str) -> bool:
    return measured_today(chain, token) or _tried.get(_key(chain, token)) == _day(time.time())


def reset_for_tests() -> None:
    global _cache
    with _lock:
        _cache = None
        _tried.clear()


# --- batch -----------------------------------------------------------------

async def refresh(client: httpx.AsyncClient, items: list[dict], max_calls: int | None = None) -> int:
    """Measure and record a batch, skipping tokens done today. One DexScreener
    call per chain per 30 tokens; GeckoTerminal paced by the shared gate.
    max_calls caps how many tokens are measured. Returns how many were."""
    todo, seen = [], set()
    for it in items:
        chain, token = it.get("chain"), it.get("token_address")
        if not chain or not token or _key(chain, token) in seen or tried_today(chain, token):
            continue
        seen.add(_key(chain, token))
        todo.append(it)
    if max_calls is not None:
        todo = todo[:max(max_calls, 0)]
    by_chain: dict[str, list[dict]] = {}
    for it in todo:
        by_chain.setdefault(it["chain"], []).append(it)
    done = 0
    today = _day(time.time())
    try:
        for chain, group in by_chain.items():
            for i in range(0, len(group), DEX_BATCH):
                chunk = group[i:i + DEX_BATCH]
                pairs = await _dex_pairs(client, chain, [it["token_address"] for it in chunk])
                net = GECKO_NET.get(chain)
                pool_info = None
                if net:
                    pools = [it.get("pair_address") or ((_pick_pair(pairs, chain, it["token_address"], None) or {})
                                                        .get("pairAddress") if pairs else None) for it in chunk]
                    pool_info = await _gecko_pools_multi(client, chain, net, [p for p in pools if p])
                for it in chunk:
                    _tried[_key(chain, it["token_address"])] = today
                    m = await _measure(client, chain, it["token_address"], it.get("pair_address"), pairs, pool_info)
                    if m:
                        record(m, save=False)
                        done += 1
    finally:
        if done:
            await _flush()
    return done


async def _flush() -> None:
    """One write per batch, off the event loop (the file grows to ~10 MB)."""
    with _lock:
        text = json.dumps(_load(), separators=(",", ":"))
    await asyncio.to_thread(write_text_atomic, storage.data_file(FILE_NAME), text)
