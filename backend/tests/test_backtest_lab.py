"""Il laboratorio di backtest: prende i token maturi del diario, li analizza
nei momenti morti e li conserva."""
import asyncio
import time

from app.providers import dexscreener
from app.trading.onchain import alert_track, backtest_lab, outcomes


def _bars(start: float, n: int = 300) -> list:
    """Barre 5m con un pump e poi una caduta, volume variabile."""
    out = []
    price = 1.0
    for i in range(n):
        ts = start + i * 300
        if i < 60:
            price *= 1.03
        else:
            price *= 0.985
        o = price * 0.995
        h = price * 1.01
        low = price * 0.99
        c = price
        vol = 1000 + (i % 7) * 250
        out.append([ts, o, h, low, c, vol])
    return out


def _journal(now: float) -> dict:
    return {
        "solana:mature": {
            "chain": "solana", "symbol": "PUMP", "token_address": "tok1",
            "pair_address": "pair1", "decision": "proposed", "source": "alert",
            "at": now - 3 * 86400,
        },
        "solana:fresh": {
            "chain": "solana", "symbol": "NEW", "token_address": "tok2",
            "pair_address": "pair2", "decision": "proposed", "source": "alert",
            "at": now - 3600,
        },
    }


def _setup(monkeypatch, tmp_path, now: float):
    monkeypatch.setattr(backtest_lab, "_DB_FILE", tmp_path / "lab.sqlite")
    monkeypatch.setattr(backtest_lab, "_conn", None)
    monkeypatch.setattr(backtest_lab, "_conn_path", None)
    monkeypatch.setattr(outcomes, "_journal", _journal(now))
    monkeypatch.setattr(outcomes, "_archive", {})
    monkeypatch.setattr(dexscreener, "gecko_load", lambda: 0)


def test_fill_stores_mature_token(monkeypatch, tmp_path):
    now = time.time()
    _setup(monkeypatch, tmp_path, now)
    entry = outcomes._journal["solana:mature"]

    async def fake_candles(client, net, pool, tf, aggregate, before, limit, token="", **kw):
        return _bars(entry["at"])

    monkeypatch.setattr(alert_track, "_candles", fake_candles)

    stored = asyncio.run(backtest_lab.fill(now))
    assert stored == 1

    row = backtest_lab.get("solana:mature")
    assert row is not None
    assert row["result"]["backtests"]["rows"]
    assert len(row["result"]["backtests"]["rows"]) == 4
    assert row["result"]["path"]["max_mult"] > 1

    assert asyncio.run(backtest_lab.fill(now)) == 0


def test_fill_skips_when_gecko_busy(monkeypatch, tmp_path):
    now = time.time()
    _setup(monkeypatch, tmp_path, now)
    monkeypatch.setattr(dexscreener, "gecko_load", lambda: 99)
    assert asyncio.run(backtest_lab.fill(now)) == 0


def test_fill_marks_gone_pool(monkeypatch, tmp_path):
    now = time.time()
    _setup(monkeypatch, tmp_path, now)

    async def fake_candles(client, net, pool, tf, aggregate, before, limit, token="", **kw):
        return []

    monkeypatch.setattr(alert_track, "_candles", fake_candles)
    assert asyncio.run(backtest_lab.fill(now)) == 1
    row = backtest_lab.get("solana:mature")
    assert row["result"] == {"gone": True}


def test_summary_counts_rows(monkeypatch, tmp_path):
    now = time.time()
    _setup(monkeypatch, tmp_path, now)
    entry = outcomes._journal["solana:mature"]

    async def fake_candles(client, net, pool, tf, aggregate, before, limit, token="", **kw):
        return _bars(entry["at"])

    monkeypatch.setattr(alert_track, "_candles", fake_candles)
    asyncio.run(backtest_lab.fill(now))
    s = backtest_lab.summary()
    assert s["rows"] == 1
    assert "proposed" in s["by_decision"]


def test_done_count_empty_and_after_write(monkeypatch, tmp_path):
    now = time.time()
    _setup(monkeypatch, tmp_path, now)
    assert backtest_lab.done_count() == 0

    entry = outcomes._journal["solana:mature"]

    async def fake_candles(client, net, pool, tf, aggregate, before, limit, token="", **kw):
        return _bars(entry["at"])

    monkeypatch.setattr(alert_track, "_candles", fake_candles)
    asyncio.run(backtest_lab.fill(now))
    assert backtest_lab.done_count() == 1


def test_rugs_are_archived_and_backtested_even_after_the_journal_drops_them(monkeypatch, tmp_path):
    """Lorenzo, 29/09: "dobbiamo documentare tutti i rug [...] anche quelli
    morti sopratutto": a rug stays after the journal's prune, and goes to the
    lab an hour after the rug, without waiting 48h, ahead of other tokens."""
    now = time.time()
    _setup(monkeypatch, tmp_path, now)
    monkeypatch.setattr(outcomes, "_STORE_FILE", tmp_path / "outcomes.json")
    monkeypatch.setattr(outcomes, "_ARCHIVE_FILE", tmp_path / "archive.json")
    rug = {"chain": "solana", "symbol": "RUG", "token_address": "tok3", "pair_address": "pair3",
           "decision": "rejected", "source": "listings", "at": now - 3 * 3600, "rug": True, "rug_at": now - 2 * 3600}
    outcomes._journal["solana:tok3"] = rug
    outcomes._save()
    outcomes._journal.pop("solana:tok3")          # what the prune does to an old rug
    outcomes._save()
    outcomes._journal.clear()
    outcomes._archive.clear()
    outcomes._load()                              # after a restart
    assert "solana:tok3" not in outcomes._journal
    assert outcomes.entries()["solana:tok3"]["symbol"] == "RUG"
    keys = [k for k, _e in backtest_lab.queue(now)]
    assert keys[:2] == ["solana:mature", "solana:tok3"]
