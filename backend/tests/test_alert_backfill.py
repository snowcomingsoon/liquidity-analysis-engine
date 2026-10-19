import asyncio

import pytest

from app.trading.onchain import alert_track as at

H = 3600
T0 = 1_790_000_000


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setattr(at, "_STORE_FILE", tmp_path / "t.json")
    at.reset_for_tests()
    yield
    at.reset_for_tests()


def _item(**kw):
    return {"chain": "solana", "pair_address": "P1", "token_address": "T1", "symbol": "FROG", "at": T0, **kw}


def test_from_candles_rebuilds_checkpoints_from_the_message_on():
    a = at.record(_item(), "meme", T0)
    candles = [[T0 - 3 * H, 0, 0, 0, 5.0, 0],          # before the message: ignored
               [T0 + 60, 0, 0, 0, 1.0, 0],
               [T0 + H + 30, 0, 0, 0, 1.5, 0],          # just before the 1h mark (entry is T0+60)
               [T0 + 3 * H, 0, 0, 0, 0.8, 0]]
    at.from_candles(a, candles, T0 + 60 * H)
    assert a["entry"] == 1.0
    assert a["returns"]["1"] == 0.5 and a["returns"]["2"] == 0.5 and a["returns"]["3"] == -0.2
    assert a["returns"]["48"] == -0.2 and a["max_ret"] == 0.5 and a["last"]["ret"] == -0.2
    assert not a["closed"] and a["backfilled"]


def test_no_candles_is_closed_not_priced_later():
    a = at.record(_item(), "meme", T0)
    at.from_candles(a, [], T0 + 10 * H)
    assert a["closed"] and a["entry"] is None
    assert at.board("meme")["total"] == 0


def test_backfill_skips_known_and_retries_when_gecko_is_down(monkeypatch):
    calls = []

    async def fake(client, net, pool, tf, agg, before, limit, token="", **kw):
        calls.append((net, pool, tf))
        return None if pool == "DOWN" else [[T0 + 60, 0, 0, 0, 2.0, 0], [T0 + 2 * H, 0, 0, 0, 3.0, 0]]

    monkeypatch.setattr(at, "_candles", fake)
    items = [_item(), _item(pair_address="DOWN", token_address="T2"), _item(chain="nochain", token_address="T3")]
    n = asyncio.run(at.backfill(None, items, "meme", now=T0 + 5 * H, gap_s=0))
    assert n == 1 and calls == [("solana", "P1", "minute"), ("solana", "DOWN", "minute")]
    b = at.board("meme", now=T0 + 5 * H)
    assert b["total"] == 1 and b["items"][0]["returns"]["2"] == 0.5
    assert asyncio.run(at.backfill(None, items[:1], "meme", now=T0 + 5 * H, gap_s=0)) == 0
