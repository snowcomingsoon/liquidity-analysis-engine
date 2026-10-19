"""Real module/API integration; no exchange, model or wallet network calls."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.trading.onchain import quant_api, quant_memory as memory, quant_runtime as runtime
from app.trading.onchain import autotrader as trader, alert_track, projects_db, leaderboard, outcomes
from app.trading.onchain.quant_engine import Policy, replay


def candle(t, price=10):
    return [t, price, price + 1, price - 1, price, 100]


def test_closed_first_observation_survives_revision_and_rolling_buffer():
    a = {"chain": "solana", "token": "AbC"}
    assert memory.store_bars(a, [candle(0), candle(300)], 300) == 1
    memory.store_bars(a, [candle(0, 20), candle(300)], 600)
    assert memory.candles(a, 600) == [candle(0), candle(300)]
    assert memory.candles({"chain": "solana", "token": "abc"}, 600) == []
    memory.store_bars(a, [candle(t) for t in range(600, 300 * 30002, 300)], 300 * 30002)
    assert len(memory.candles(a, 300 * 30002)) == 30002
    assert memory.candles(a, 300)[0] == candle(0)


def test_collection_keeps_three_horizons_and_restart_eligibility(monkeypatch):
    monkeypatch.setattr(runtime, "gem_verdict", lambda *a: (True, "fixture"))
    monkeypatch.setattr(projects_db, "get", lambda *a: {"launched_at": 0})
    monkeypatch.setattr(leaderboard, "db_entry", lambda p: p)
    monkeypatch.setattr(outcomes, "features", lambda *a: {"liq": 100})
    a = {"chain": "solana", "token_address": "A"}
    memory.capture_case(a, [candle(0)], 300)
    memory.capture_case(a, [candle(86400)], 86700)
    assert memory.export_cases(complete_only=True)[0]["complete"]
    assert memory.export_cases(horizon=7 * 86400, complete_only=True) == []
    restarted = {"chain": "solana", "token_address": "A"}
    memory.capture_case(restarted, [candle(90000)], 90300)
    assert restarted["quant_observed"]["start"] == 300
    assert len(memory.status()["windows"]) == 3
    assert alert_track._quant_watching(restarted, 7 * 86400)
    assert not alert_track._quant_watching(restarted, 31 * 86400)


def test_partial_window_cannot_validate():
    result = replay({"bars": [candle(0), candle(300)], "start": 0, "end": 600, "born": 0,
                     "gem_eligible": True, "eligibility_at": 0, "complete": False}, Policy(((0, 300),)))
    assert result["state"] == "unavailable"


def test_read_api_auth_scope_integrity_and_database_failure(monkeypatch):
    app = FastAPI()
    def auth():
        raise HTTPException(401, "Login required")
    app.include_router(quant_api.router(auth))
    client = TestClient(app)
    assert client.get("/api/agent/quant").status_code == 401
    app.dependency_overrides[auth] = lambda: object()
    monkeypatch.setattr(runtime, "approved", lambda: None)
    data = client.get("/api/agent/quant").json()
    assert data["approval"] is None and data["llm_calls"] == 0 and data["candles"] == 0
    assert client.get("/api/agent/quant/project?chain=solana&token=x").status_code == 404
    key = memory.save_report({"status": "insufficient_data", "reason": "test"})
    assert client.get(f"/api/agent/quant/reports/{key}").json()["report_hash"] == key
    assert client.get("/api/agent/quant/reports/invalid").status_code == 404
    with pytest.raises(ValueError):
        memory.save_report({"status": "review_required", "report_hash": "fake"})
    def broken():
        raise OSError("private path")
    monkeypatch.setattr(memory, "status", broken)
    response = client.get("/api/agent/quant")
    assert response.status_code == 503 and "private path" not in response.text


def test_paper_approval_blocks_real_and_future_or_replaced_policies(monkeypatch):
    manifest = {"mode": "paper", "active_from": 100, "report_hash": "r"}
    monkeypatch.setattr(runtime, "approved", lambda: manifest)
    monkeypatch.setattr(runtime, "gem_verdict", lambda *args: (True, "fixture"))
    a = {"last": {"price": 10, "at": 100}, "quant_system": {"report_hash": "r", "state": "in", "eligible": True, "in_at": 100, "evaluated_at": 100}}
    assert runtime.can_enter(a, 110, mode="paper")
    assert not runtime.can_enter(a, 110)
    assert not runtime.can_enter(a, 90, mode="paper")
    manifest["report_hash"] = "replacement"
    assert not runtime.can_enter(a, 110, mode="paper")


def test_later_trend_can_reenter_without_replaying_a_consumed_signal(tmp_path, monkeypatch):
    monkeypatch.setattr(trader, "_STORE_FILE", tmp_path / "trader.json")
    monkeypatch.setattr(runtime, "can_enter", lambda a, now, **kwargs: a["quant_system"]["state"] == "in")
    a = {"chain": "solana", "token_address": "T", "pair_address": "P", "kind": "gem", "symbol": "T", "at": 0,
         "last": {"price": 10, "at": 100}, "quant_policy": {"costs": {"commission": 0, "slippage": 0}},
         "quant_system": {"state": "in", "in_at": 100, "policy_id": "p", "report_hash": "r", "mark": 10, "events": []}}
    monkeypatch.setattr(alert_track, "_alerts", {alert_track.key_of(a): a})
    u = {"paper": [], "trades": [], "sim_usdg": 100, "pct": 50}
    assert trader.paper_tick(u, "HF", 110)[0]["side"] == "buy"
    assert trader.paper_tick(u, "HF", 120) == []
    a["quant_system"].update(state="out", events=[{"side": "sell", "t": 130, "price": 11}])
    assert trader.paper_tick(u, "HF", 140)[0]["side"] == "sell"
    restored = json.loads(json.dumps(u))
    restored["trades"] = []  # Display history truncation cannot erase consumption.
    a["quant_system"].update(state="in", events=[])
    assert trader.paper_tick(restored, "HF", 150) == []
    a["quant_system"].update(in_at=160)
    assert trader.paper_tick(restored, "HF", 170)[0]["side"] == "buy"


def test_overlapping_ticks_cannot_send_two_orders(monkeypatch):
    calls = []
    async def run(*args):
        calls.append(1)
        await asyncio.sleep(0)
        return []
    monkeypatch.setattr(trader, "_tick", run)
    async def both():
        await asyncio.gather(trader.tick([]), trader.tick([]))
    asyncio.run(both())
    assert calls == [1]


def test_consumed_real_attempt_is_persisted_before_order(monkeypatch, tmp_path):
    path = tmp_path / "trader.json"
    monkeypatch.setattr(trader, "_STORE_FILE", path)
    a = {"chain": "robinhood", "token_address": "T", "quant_system": {"in_at": 100}}
    u = {"mode": "real", "position": None, "paper": [], "trades": []}
    monkeypatch.setattr(trader, "_state", {"u": u})
    monkeypatch.setattr(alert_track, "system_board", lambda _: {"chosen": "HF"})
    monkeypatch.setattr(trader, "entry_candidate", lambda *args: a if trader._unseen(u, a) else None)
    async def uncertain(*args):
        assert json.loads(path.read_text())["u"]["quant_seen"]
        raise TimeoutError("uncertain submission")
    monkeypatch.setattr(trader, "_buy", uncertain)
    user = SimpleNamespace(id="u", onchain_wallets={"robinhood": object()})
    asyncio.run(trader.tick([user], now=110, market=object()))
    assert "uncertain" in u["note"] and not trader._unseen(u, a)


def test_gem_bar_holes_are_filled_from_geckoterminal(monkeypatch):
    now = 86400 * 3
    start = now - 3600
    a = {"kind": "gem", "chain": "solana", "pair_address": "P", "token_address": "T", "at": start,
         "gone": False, "closed": False, "quant_observed": {"start": start}}
    k = alert_track.key_of(a)
    sampled = [candle(t) for t in range(start, now, 300) if t != start + 900]
    monkeypatch.setitem(alert_track._alerts, k, a)
    monkeypatch.setitem(alert_track._bars, k, [list(r) for r in sampled])
    calls = []

    async def fake_candles(client, net, pool, tf, agg, before, limit, token="", **kw):
        calls.append((pool, tf, agg, limit))
        return [candle(start + 900, 11)]

    seen = []
    monkeypatch.setattr(alert_track, "_candles", fake_candles)
    monkeypatch.setattr(memory, "capture_case", lambda a, bars, now: seen.append(len(bars)) or False)
    monkeypatch.setattr(runtime, "approved", lambda: None)
    asyncio.run(alert_track._refresh_system(None, now, None))
    assert calls == [("P", "minute", 5, 300)]
    assert not alert_track._bar_hole(alert_track._bars[k], start, now)
    assert seen == [len(sampled) + 1]
    asyncio.run(alert_track._refresh_system(None, now + 60, None))
    assert len(calls) == 1


def test_gem_without_holes_or_memes_fetch_nothing():
    rows = [candle(t) for t in range(0, 3000, 300)]
    assert not alert_track._bar_hole(rows, 0, 3000)
    assert alert_track._bar_hole(rows[:3] + rows[4:], 0, 3000)
    assert not alert_track._bar_hole([], 3000, 3000)
