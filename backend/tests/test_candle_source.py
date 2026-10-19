"""Candle source router (candle_source.py): squid or GeckoTerminal, one per request."""
from __future__ import annotations

import asyncio
import sqlite3
import time

import pytest

from app.config import settings
from app.providers import candle_source as cs
from app.trading.onchain import candle_archive as ca

POOL = "0x54252a8124ef08a4db8edb530c0a153c33406c53"
TOKEN = "0xdefa1d21c5f1cbeac00eeb54b44c7d86467cc3a3"
QUOTE = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"


@pytest.fixture
def squid(monkeypatch):
    """A fake squid: indexed to `now`, pool indexed from `from_ts`, the
    candles in `candles`. Counts the GraphQL calls."""
    now = time.time()
    state = {"indexed": now, "from_ts": now - 30 * 86400, "candles": [], "calls": 0, "down": False}

    async def gql(query, variables=None):
        state["calls"] += 1
        if state["down"]:
            raise OSError("squid down")
        if "syncStatuses" in query:
            return {"syncStatuses": [{"block": 1, "timestamp": state["indexed"], "finalizedBlock": 1}]}
        if "pools" in query:
            return {"pools": [{"id": POOL, "token0": TOKEN, "token1": QUOTE, "fromBlock": 1,
                               "fromTimestamp": state["from_ts"]}]}
        v = variables
        return {"candles": [c for c in state["candles"] if v["from"] <= c["start"] < v["to"]]}

    monkeypatch.setattr(cs, "_gql", gql)
    monkeypatch.setattr(settings, "squid_pools", POOL)
    monkeypatch.setattr(settings, "squid_max_lag_s", 900)
    return state


def candle(start, close=2.0, swaps=3, priced=3):
    return {"start": start, "openUsd": "1", "highUsd": "3", "lowUsd": "0.5", "closeUsd": str(close),
            "volumeUsd": "100", "swaps": swaps, "pricedSwaps": priced}


def run(coro):
    return asyncio.run(coro)


def window(state, n=10, tf=300):
    end = state["indexed"]
    return end - n * tf, end


def test_off_never_calls_the_squid(squid, monkeypatch):
    monkeypatch.setattr(settings, "squid_mode", "off")

    async def gecko():
        return [[1, 1, 1, 1, 1, 1]]
    rows, provider = run(cs.route("eth", POOL, "minute", 5, TOKEN, 0, time.time(), gecko))
    assert provider == cs.PROVIDER_GECKO and rows == [[1, 1, 1, 1, 1, 1]] and squid["calls"] == 0


def test_on_serves_a_covered_window_from_the_squid_only(squid, monkeypatch):
    monkeypatch.setattr(settings, "squid_mode", "on")
    start, end = window(squid)
    squid["candles"] = [candle(int(start // 300 * 300) + 300 * i) for i in range(1, 9)]
    called = []

    async def gecko():
        called.append(1)
        return []
    rows, provider = run(cs.route("eth", POOL, "minute", 5, TOKEN, start, end, gecko))
    assert provider == cs.PROVIDER_SQUID and not called
    assert len(rows) == 8 and rows[0][4] == 2.0 and rows[0][5] == 100.0


@pytest.mark.parametrize("case,status", [
    ("before_start", "incomplete"), ("lagging", "lagging"), ("unpriced", "incomplete"),
    ("empty", "no_trades"), ("down", "error"), ("other_side", "unsupported"),
    ("not_listed", "unsupported"), ("tf", "unsupported"),
])
def test_anything_short_of_full_coverage_goes_whole_to_gecko(squid, monkeypatch, case, status):
    """Never stitched: the whole answer is GeckoTerminal's."""
    monkeypatch.setattr(settings, "squid_mode", "on")
    start, end = window(squid)
    squid["candles"] = [candle(int(start // 300 * 300) + 300)]
    pool, token, tf, agg = POOL, TOKEN, "minute", 5
    if case == "before_start":
        squid["from_ts"] = start + 600
    elif case == "lagging":
        squid["indexed"] = time.time() - 3600
        start, end = squid["indexed"] - 3000, squid["indexed"]
    elif case == "unpriced":
        squid["candles"] = [candle(int(start // 300 * 300) + 300, priced=2)]
    elif case == "empty":
        squid["candles"] = []
    elif case == "down":
        squid["down"] = True
    elif case == "other_side":
        token = "0x" + "1" * 40
    elif case == "not_listed":
        pool = "0x" + "2" * 40
    elif case == "tf":
        tf, agg = "hour", 4
    gecko_rows = [[int(end) - 300, 9, 9, 9, 9, 9]]

    async def gecko():
        return gecko_rows
    assert run(cs.fetch("eth", pool, tf, agg, token, start, end)).status == status
    rows, provider = run(cs.route("eth", pool, tf, agg, token, start, end, gecko))
    assert provider == cs.PROVIDER_GECKO and rows == gecko_rows


def test_a_window_past_the_indexed_block_is_incomplete(squid, monkeypatch):
    start, end = window(squid)
    assert run(cs.fetch("eth", POOL, "minute", 5, TOKEN, start, end + 3600)).status == "incomplete"


def test_compare_answers_from_gecko_and_measures_the_squid(squid, monkeypatch):
    monkeypatch.setattr(settings, "squid_mode", "compare")
    start, end = window(squid)
    b = int(start // 300 * 300)
    squid["candles"] = [candle(b + 300, close=2.0), candle(b + 600, close=2.0)]
    gecko_rows = [[b + 300, 1, 3, 0.5, 2.2, 110], [b + 900, 1, 3, 0.5, 2.0, 50]]

    async def gecko():
        return gecko_rows

    async def go():
        out = await cs.route("eth", POOL, "minute", 5, TOKEN, start, end, gecko)
        await asyncio.gather(*cs._tasks)
        return out
    rows, provider = run(go())
    assert provider == cs.PROVIDER_GECKO and rows == gecko_rows
    m = cs.metrics()
    assert m["compared_buckets"] == 1 and m["only_gecko"] == 1 and m["only_squid"] == 1
    assert m["close_diff"]["median"] == pytest.approx(0.2 / 2.2, rel=1e-4)
    assert m["volume_diff"]["median"] == pytest.approx(10 / 110, rel=1e-4)
    assert m["requests_by_status"] == {"ok": 1}


def test_an_unknown_mode_is_off(monkeypatch):
    monkeypatch.setattr(settings, "squid_mode", "maybe")
    assert cs.mode() == "off"


def test_save_only_when_in_use(squid, monkeypatch, tmp_path):
    f = tmp_path / "cs.json"
    monkeypatch.setattr(settings, "squid_mode", "off")
    assert not cs.save(f, now=1000.0) and not f.exists()
    monkeypatch.setattr(settings, "squid_mode", "compare")
    assert cs.save(f, now=1000.0) and f.exists()
    assert not cs.save(f, now=1100.0)


def test_the_archive_labels_its_legacy_series(monkeypatch, tmp_path):
    """Series written before the provenance table: GeckoTerminal's, or the
    exchange's for net "cex"; new ones get their provider when written."""
    db = tmp_path / "old.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE fetched (k TEXT PRIMARY KEY, at REAL, n INTEGER)")
    con.executemany("INSERT INTO fetched VALUES (?, ?, ?)",
                    [("eth:P::minute5", 1.0, 3), ("cex:BTCUSDT::hour1", 1.0, 3)])
    con.commit()
    con.close()
    monkeypatch.setattr(ca, "_DB_FILE", db)
    assert ca.series_provider("eth:P::minute5") == ca.PROVIDER_GECKO
    assert ca.series_provider("cex:BTCUSDT::hour1") == ca.PROVIDER_CEX
    k = ca.key("solana", "Q", "minute", 5)
    assert ca.series_provider(k) is None
    ca.put(k, [[300, 1, 1, 1, 1, 1]], 2.0)
    assert ca.series_provider(k) == ca.PROVIDER_GECKO


def test_the_chart_takes_one_provider_per_call(squid, monkeypatch):
    from app.providers import dexscreener
    monkeypatch.setattr(settings, "squid_mode", "on")
    now = time.time()
    b = int((now - 3 * 300) // 300 * 300)
    squid["indexed"] = now
    squid["candles"] = [candle(b + 300 * i) for i in range(1, 3)]
    gecko_calls = []

    async def gecko_get(url, params=None, caller="gecko_get"):
        gecko_calls.append(url)
        return {"data": {"attributes": {"ohlcv_list": [[b, 7, 7, 7, 7, 7]]}}}
    monkeypatch.setattr(dexscreener, "gecko_get", gecko_get)
    p = dexscreener.DexScreenerProvider()
    df = run(p.fetch_ohlcv(f"X@ethereum:{POOL}", "5m", 3, token_address=TOKEN))
    assert df.attrs["provider"] == cs.PROVIDER_SQUID and not gecko_calls and len(df) == 2
    squid["from_ts"] = now          # the window reaches before the squid's start: all from GeckoTerminal
    cs.reset_for_tests()
    df = run(p.fetch_ohlcv(f"X@ethereum:{POOL}", "5m", 3, token_address=TOKEN))
    assert df.attrs["provider"] == cs.PROVIDER_GECKO and gecko_calls and list(df["close"]) == [7.0]
