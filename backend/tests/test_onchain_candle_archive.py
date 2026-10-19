"""Archivio candele della Top 50 (candle_archive.py)."""
from __future__ import annotations

import asyncio

import pytest

from app.trading.onchain import candle_archive as ca
from app.trading.onchain import strategy_lab


@pytest.fixture(autouse=True)
def fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(ca, "_DB_FILE", tmp_path / "candles.sqlite")
    monkeypatch.setattr(ca.priority, "backtests_first", lambda: None)
    strategy_lab.reset_for_tests()
    yield
    strategy_lab.reset_for_tests()


def test_the_series_grows_past_one_call_and_is_trimmed(monkeypatch):
    monkeypatch.setattr(ca, "MAX_BARS", 150)
    k = ca.key("solana", "P", "minute", 5, "T")
    ca.put(k, [[i * 300, 1, 1, 1, 1, 1] for i in range(100)], 1.0)
    ca.put(k, [[i * 300, 2, 2, 2, 2, 2] for i in range(90, 200)], 2.0)
    got = ca.get(k)
    assert len(got) == 150 and got[0][0] == 50 * 300 and got[45][1] == 2.0
    assert ca.fetched_at(k) == 2.0


def test_the_loop_warms_the_stalest_series_of_the_top(monkeypatch):
    now = 1_800_000_000
    asked = []

    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        asked.append((pool, tf, agg))
        return [[now - 3600, 1, 1, 1, 1, 1]]
    monkeypatch.setattr(ca.alert_track, "_candles", candles)
    from app.providers import dexscreener
    monkeypatch.setattr(dexscreener, "gecko_load", lambda: 99)   # a busy background does not starve it
    strategy_lab._results["solana:T"] = {"pair": "P"}
    entries = [{"chain": "solana", "token_address": "T"}, {"chain": "solana", "token_address": "X"}]
    for _ in range(len(ca.SOURCES) + 1):
        asyncio.run(ca.tick(entries, now=now))
    assert sorted(asked) == sorted(("P", tf, agg) for tf, agg in ca.SOURCES)
    assert ca.status([("solana", "P", "T")], now=now)["fresh"] == len(ca.SOURCES)


def test_a_restart_resumes_the_queue_where_it_was(monkeypatch):
    now = 1_800_000_000
    pairs = [("solana", "P", "T")]
    for tf, agg in ca.SOURCES[:3]:
        ca.put(ca.key("solana", "P", tf, agg, "T"), [[now - 3600, 1, 1, 1, 1, 1]], now)
    ca._conn = None                          # a new process opens the file again
    assert ca.next_due(pairs, now + 60)[3:] == ca.SOURCES[3]
