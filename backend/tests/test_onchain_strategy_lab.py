"""Backtest H24 dei token della schermata Strategie."""
from __future__ import annotations

import asyncio

import httpx
import numpy as np
import pytest

from app.notify import deepseek_desk
from app.trading.onchain import strategy_lab as lab
from app.trading.onchain import candle_archive, sim_backtest


@pytest.fixture(autouse=True)
def fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(lab, "_STORE_FILE", tmp_path / "lab.json")
    monkeypatch.setattr(deepseek_desk, "_STORE_FILE", tmp_path / "desk.json")
    monkeypatch.setattr(sim_backtest, "_FILE", tmp_path / "ledger.json")
    monkeypatch.setattr(candle_archive, "_DB_FILE", tmp_path / "candles.sqlite")
    monkeypatch.setattr(lab, "LADDER_RULE", True)
    sim_backtest.reset_for_tests()
    lab.reset_for_tests()
    deepseek_desk.reset_for_tests()
    yield
    lab.reset_for_tests()


def _e(token, chain="solana", pair="Pair"):
    return {"chain": chain, "token_address": token, "pair_address": pair, "symbol": token.upper()}


def _bars(n=600, t0=1_790_000_000):
    rng = np.random.default_rng(1)
    closes = np.cumprod(1 + rng.normal(0.002, 0.02, n))
    return [[t0 + i * 300, c, c * 1.01, c * 0.99, c, 1000.0] for i, c in enumerate(closes)]


def test_next_due_takes_new_tokens_first_then_the_oldest():
    now = 1_800_000_000
    lab._results.update({"solana:a": {"at": now - 10}, "solana:b": {"at": now - 2 * lab.REFRESH_S},
                         "solana:c": {"at": now - 3 * lab.REFRESH_S}})
    entries = [_e("a"), _e("b"), _e("c"), _e("d"), _e("x", chain="nochain")]
    assert lab.next_due(entries, now)["token_address"] == "d"
    lab._results["solana:d"] = {"at": now}
    assert lab.next_due(entries, now)["token_address"] == "c"
    lab._results["solana:c"] = {"at": now}
    lab._results["solana:b"] = {"at": now}
    assert lab.next_due(entries, now) is None


def test_every_top_token_gets_every_strategy_and_the_agent_says_so(monkeypatch):
    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        assert (net, pool, tf, agg) == ("solana", "Pair", "minute", 5)
        return list(reversed(_bars()))
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    out = asyncio.run(lab.tick([_e("tok")], now=1_800_000_000))
    bt = out["backtests"]
    assert bt["bars"] == 600 and {r["label"] for r in bt["rows"]} >= {"Trend EMA", "RSI+BB"}
    assert lab.get("solana", "tok") is bt
    assert lab.status([_e("tok"), _e("other")], now=1_800_000_000)["ready"] == 1
    line = deepseek_desk.log(1)[0]
    assert line["kind"] == "backtest" and "TOK" in line["text"]


def _daily_bars(n=200, t0=1_780_000_000):
    rng = np.random.default_rng(2)
    closes = np.cumprod(1 + rng.normal(0.003, 0.03, n))
    return [[t0 + i * 86400, c, c * 1.02, c * 0.98, c, 5000.0 + i] for i, c in enumerate(closes)]


def test_daily_backtest_runs_only_the_trend_follower(monkeypatch):
    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        if (tf, agg) == ("day", 1):
            return _daily_bars()
        return _bars()
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    out = asyncio.run(lab.tick([_e("tok")], now=1_800_000_000))
    daily = out["daily"]
    assert daily["interval"] == "1d" and daily["bars"] == 200
    assert [r["label"] for r in daily["rows"]] == ["Trend EMA"]


def _spaced(n, step, now=1_800_000_000):
    rng = np.random.default_rng(3)
    closes = np.cumprod(1 + rng.normal(0.003, 0.03, n))
    return [[now - (n - i) * step, c, c * 1.02, c * 0.98, c, 1000.0] for i, c in enumerate(closes)]


def test_daily_falls_back_to_8h_when_the_daily_is_short(monkeypatch):
    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        if (tf, agg) == ("day", 1):
            return _spaced(30, 86400)
        if (tf, agg) == ("hour", 4):
            return _spaced(180, 14400)
        return [] if (tf, agg) == ("hour", 12) else _bars()
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    _only_enters_on(monkeypatch, 28800)
    out = asyncio.run(lab.tick([_e("tok")], now=1_800_000_000))
    daily = out["daily"]
    assert daily["interval"] == "8h"
    assert all(b[0] % 28800 == 0 for b in lab._merge_8h(_bars(400)))


def test_the_ladder_climbs_with_the_chart_history():
    h, d = 3600, 86400
    ages = (2 * h, 6 * h, 20 * h, 3 * d, 6 * d, 12 * d, 16 * d, 25 * d, 40 * d, 90 * d)
    assert [lab.pick_interval(a) for a in ages] == ["5m", "5m", "15m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"]


def _only_enters_on(monkeypatch, step_s):
    """backtest_one that enters only when the bars are `step_s` apart."""
    def fake(bars, *a, **k):
        entered = bars[1][0] - bars[0][0] == step_s
        return {"bars": len(bars), "rows": [{"label": "Trend EMA", "trades": int(entered), "in_position": False}],
                "best": {"events": [{"side": "buy", "t": bars[-1][0]}]} if entered else None}
    monkeypatch.setattr(lab.system, "backtest_one", fake)


def test_the_ladder_steps_down_to_the_first_timeframe_that_enters(monkeypatch):
    now = 1_800_000_000
    calls = []

    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        calls.append((tf, agg))
        step = {"day": 86400, "hour": 3600, "minute": 60}[tf] * agg
        return _spaced(min(1000, 200 * 86400 // step), step, now)
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    _only_enters_on(monkeypatch, 43200)
    daily = asyncio.run(lab.tick([_e("tok")], now=now))["daily"]
    assert daily["interval"] == "12h"
    assert calls == [("minute", 5), ("day", 1), ("hour", 12)]
    _only_enters_on(monkeypatch, 21600)
    assert asyncio.run(lab.tick([_e("tok2")], now=now))["daily"]["interval"] == "6h"


def test_no_trend_ema_entry_anywhere_adapts_to_trend_hf(monkeypatch):
    now = 1_800_000_000

    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        step = {"day": 86400, "hour": 3600, "minute": 60}[tf] * agg
        return _spaced(min(1000, 200 * 86400 // step), step, now)
    monkeypatch.setattr(lab.alert_track, "_candles", candles)

    def fake(bars, name="Lorenzo (trend-follower)", label="Trend EMA", known=None):
        hf = label == "Trend HF" and bars[1][0] - bars[0][0] == 43200
        return {"bars": len(bars), "rows": [{"label": label, "trades": int(hf), "in_position": False}]}
    monkeypatch.setattr(lab.system, "backtest_one", fake)
    daily = asyncio.run(lab.tick([_e("tok")], now=now))["daily"]
    assert daily["interval"] == "12h" and daily["rows"][0]["label"] == "Trend HF"


def test_until_the_top_50_test_the_old_rule_runs(monkeypatch):
    monkeypatch.setattr(lab, "LADDER_RULE", False)
    now = 1_800_000_000
    asked = []

    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        asked.append((tf, agg))
        step = {"day": 86400, "hour": 3600, "minute": 60}[tf] * agg
        return _spaced(30 if tf == "day" else 180, step, now)
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    _only_enters_on(monkeypatch, 1)
    daily = asyncio.run(lab.tick([_e("tok")], now=now))["daily"]
    assert daily["interval"] == "8h" and daily["rows"][0]["label"] == "Trend EMA"
    assert ("hour", 12) not in asked


def test_the_archive_answers_the_second_run_without_gecko(monkeypatch):
    now = 1_800_000_000
    asked = []

    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        asked.append((tf, agg, limit))
        step = {"day": 86400, "hour": 3600, "minute": 60}[tf] * agg
        return _spaced(min(1000, 200 * 86400 // step), step, now)
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    _only_enters_on(monkeypatch, 86400)
    asyncio.run(lab.run_daily(httpx.AsyncClient(), "solana", "P", "T", now))
    asyncio.run(lab.run_daily(httpx.AsyncClient(), "solana", "P", "T", now + 60))
    assert asked == [("day", 1, 1000)]
    asyncio.run(lab.run_daily(httpx.AsyncClient(), "solana", "P", "T", now + 4000))
    assert asked[-1] == ("day", 1, 10)
    assert len(candle_archive.get(candle_archive.key("solana", "P", "day", 1, "T"))) == 200


def test_no_entry_anywhere_keeps_the_widest_timeframe(monkeypatch):
    now = 1_800_000_000

    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        step = {"day": 86400, "hour": 3600, "minute": 60}[tf] * agg
        return _spaced(min(1000, 200 * 86400 // step), step, now)
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    _only_enters_on(monkeypatch, 1)
    assert asyncio.run(lab.tick([_e("tok")], now=now))["daily"]["interval"] == "1d"


def test_a_young_token_starts_on_the_rung_its_history_allows(monkeypatch):
    now = 1_800_000_000
    calls = []

    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        calls.append((tf, agg))
        if (tf, agg) == ("day", 1):
            return _spaced(4, 86400, now)
        return _spaced(90, 3600, now) if (tf, agg) == ("hour", 1) else _spaced(1000, 300, now)
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    _only_enters_on(monkeypatch, 3600)
    daily = asyncio.run(lab.tick([_e("tok")], now=now))["daily"]
    assert daily["interval"] == "1h" and daily["bars"] == 90
    assert calls == [("minute", 5), ("day", 1), ("hour", 1)]


def test_a_just_listed_token_uses_the_5m_it_already_has(monkeypatch):
    now = 1_800_000_000
    calls = []

    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        calls.append((tf, agg))
        if (tf, agg) == ("day", 1):
            return _spaced(1, 86400, now + 80000)
        return _spaced(100, 300, now)
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    daily = asyncio.run(lab.tick([_e("tok")], now=now))["daily"]
    assert daily["interval"] == "5m" and daily["bars"] == 100
    assert calls == [("minute", 5), ("day", 1)]


def test_daily_too_few_candles_is_an_error_and_does_not_drop_the_5m(monkeypatch):
    now = 1_800_000_000

    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        if (tf, agg) == ("day", 1):
            return _spaced(1, 86400, now + 80000)
        return _spaced(40, 300, now)
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    out = asyncio.run(lab.tick([_e("tok")], now=now))
    assert out["daily"] == {"interval": "5m", "bars": 40, "error": "too few candles"}
    assert out["backtests"]["bars"] == 40


def test_daily_fetch_failure_keeps_the_5m_result(monkeypatch):
    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        if (tf, agg) == ("day", 1):
            return None
        return _bars()
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    out = asyncio.run(lab.tick([_e("tok")], now=1_800_000_000))
    assert "daily" not in out and out["backtests"]["bars"] == 600


def test_the_trigger_needs_60_closed_candles_and_the_forming_one_is_dropped(monkeypatch):
    now = 1_800_000_000
    start = now - 59 * 86400 - 3600          # 59 closed days and one still forming

    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        if (tf, agg) == ("day", 1):
            return [[start + i * 86400, 1, 1, 1, 1, 1] for i in range(60)]
        if (tf, agg) == ("hour", 4):
            return [[now - 600 * 14400 + i * 14400, 1, 1, 1, 1, 1] for i in range(600)]
        return [] if (tf, agg) == ("hour", 12) else _bars()
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    _only_enters_on(monkeypatch, 28800)
    daily = asyncio.run(lab.tick([_e("tok")], now=now))["daily"]
    assert daily["interval"] == "8h" and daily["bars"] == 300 and "rows" in daily


def _daily(events, to=1_000_000, iv="8h"):
    return {"interval": iv, "to": to, "best": {"events": events}}


def test_a_signal_is_news_once_and_only_on_the_last_closed_candle():
    buy = {"side": "buy", "t": 1_000_000, "price": 2.0}
    sig, fresh = lab._signal(_daily([buy]), None)
    assert sig == buy and fresh
    assert lab._signal(_daily([buy]), {"signal": sig}) == (sig, False)
    old = {"side": "buy", "t": 1_000_000 - 2 * 28800, "price": 2.0}
    assert lab._signal(_daily([old]), None)[1] is False
    sell = {"side": "sell", "t": 1_000_000, "price": 3.0, "ret": 0.4}
    assert lab._signal(_daily([buy, sell]), {"signal": buy, "best": {"fills": "next_open"}}) == (sell, True)
    # saved before the arrows moved to the fill candle: never announced twice
    assert lab._signal(_daily([buy, sell]), {"signal": buy}) == (sell, False)
    assert lab._signal(_daily([]), None) == (None, False)


def test_a_fresh_signal_reaches_the_listeners_and_a_busy_gecko_keeps_the_saved_daily(monkeypatch):
    got = []

    async def listen(sig):
        got.append(sig)
    monkeypatch.setattr(lab, "_signal_cbs", [listen])

    async def daily_ok(client, net, pair, token, now, fast=None):
        return {"interval": "1d", "to": now - 86400, "rows": [{"label": "Trend EMA", "trades": 1}],
                "best": {"events": [{"side": "buy", "t": now - 86400, "price": 1.5}]}}

    async def candles(*a, **k):
        return _bars()
    monkeypatch.setattr(lab.alert_track, "_candles", candles)
    monkeypatch.setattr(lab, "run_daily", daily_ok)
    asyncio.run(lab.tick([_e("tok")], now=1_800_000_000))
    assert [(s["symbol"], s["side"], s["interval"]) for s in got] == [("TOK", "buy", "1d")]

    async def daily_busy(*a, **k):
        return None
    monkeypatch.setattr(lab, "run_daily", daily_busy)
    out = asyncio.run(lab.run_one(httpx.AsyncClient(), _e("tok"), 1_800_010_000))
    assert out["daily"]["signal"]["side"] == "buy" and len(got) == 1


def test_gecko_busy_retries_next_tick_and_a_missing_pool_is_resolved(monkeypatch):
    async def busy(*a, **k):
        return None
    monkeypatch.setattr(lab.alert_track, "_candles", busy)
    assert asyncio.run(lab.tick([_e("tok")], now=1_800_000_000)) is None
    assert lab.next_due([_e("tok")], 1_800_000_000) is not None

    seen = {}

    async def candles(client, net, pool, *a, **kw):
        seen["pool"] = pool
        return _bars(50)
    monkeypatch.setattr(lab.alert_track, "_candles", candles)

    def handler(req):
        return httpx.Response(200, json=[{"chainId": "solana", "pairAddress": "Thin", "liquidity": {"usd": 5}},
                                         {"chainId": "solana", "pairAddress": "Deep", "liquidity": {"usd": 900}}])

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await lab.run_one(c, _e("tok", pair=None), 1_800_000_000)
    assert asyncio.run(go())["pair"] == "Deep" and seen["pool"] == "Deep"


def test_backtest_one_returns_only_the_trend_follower():
    from app.trading.onchain import system
    bt = system.backtest_one(_bars(600))
    assert [r["label"] for r in bt["rows"]] == ["Trend EMA"]
    assert bt["bars"] == 600 and bt["best"] is not None


def test_get_returns_the_daily_backtest_next_to_the_fast_one():
    from app.trading.onchain import strategy_lab
    strategy_lab.reset_for_tests()
    strategy_lab._results["solana:T"] = {"at": 1, "backtests": {"rows": [], "hold_pct": 1.0},
                                         "daily": {"interval": "1d", "rows": [{"label": "Trend EMA"}]}}
    assert strategy_lab.get("solana", "T")["daily"]["interval"] == "1d"
    strategy_lab.reset_for_tests()


def test_a_token_with_history_never_descends_to_the_minutes():
    names = [r[0] for r in lab.LADDER]
    rungs = lambda start: names[names.index(start):lab.descent_end(names.index(start))]  # noqa: E731
    assert rungs("1d") == ["1d", "12h", "8h", "6h"]
    assert rungs("4h") == ["4h", "2h", "1h"]
    assert rungs("1h") == ["1h"]
    assert rungs("30m") == ["30m", "15m", "5m"]


def _part(label, trades, sells, best_label=None):
    ev = [{"t": i, "side": "sell"} for i in range(sells)]
    return {"rows": [{"label": label, "trades": trades, "return_pct": 5.0}],
            "best": {"label": best_label or label, "events": ev}}


def test_a_row_is_listed_only_when_its_chart_draws_its_own_trades():
    """Server audit 30/09: BEB1M listed 30 trades over 1 arrow pair, ETHICS
    4 trades over 5 sells: 5-minute events saved before #434 (RSI+BB)."""
    assert lab.drawn_row(_part("Trend HF", 3, 3))["label"] == "Trend HF"
    assert lab.drawn_row(_part("Trend HF", 30, 1)) is None
    assert lab.drawn_row(_part("Trend EMA", 4, 4, best_label="RSI+BB")) is None
    assert lab.drawn_row({"rows": [{"label": "RSI+BB", "trades": 4, "return_pct": 9.0}]}) is None


def test_stale_arrows_are_redone_first(monkeypatch, tmp_path):
    import json as _json
    f = tmp_path / "store.json"
    f.write_text(_json.dumps({"solana:A": {"at": 123, "backtests": _part("Trend HF", 30, 1)},
                              "solana:B": {"at": 456, "backtests": _part("Trend HF", 2, 2)}}))
    monkeypatch.setattr(lab, "_STORE_FILE", f)
    lab.reset_for_tests()
    lab._load()
    assert lab._results["solana:A"]["at"] == 0 and lab._results["solana:B"]["at"] == 456


def test_rsi_bb_runs_down_the_same_ladder(monkeypatch):
    now = 1_800_000_000

    async def candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        step = {"day": 86400, "hour": 3600, "minute": 60}[tf] * agg
        return _spaced(min(1000, 200 * 86400 // step), step, now)
    monkeypatch.setattr(lab.alert_track, "_candles", candles)

    def fake(bars, name="Lorenzo (trend-follower)", label="Trend EMA", known=None):
        hit = label == "RSI+BB" and bars[1][0] - bars[0][0] == 28800
        return {"bars": len(bars), "rows": [{"label": label, "trades": int(hit), "in_position": False}]}
    monkeypatch.setattr(lab.system, "backtest_one", fake)
    d = asyncio.run(lab.run_daily(httpx.AsyncClient(), "solana", "P", "T", now, strategies=lab.RSI_BB))
    assert d["interval"] == "8h" and d["rows"][0]["label"] == "RSI+BB"
