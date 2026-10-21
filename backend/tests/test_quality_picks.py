"""Whitekobra's Quality list (Lorenzo, 21/10): projects of quality 80 or
more outside his Top 25, accepted or discarded by hand; an accepted one
skips the score's bars only, every other gem rule still holds."""
import time

from app.trading.onchain import market_peaks
from app.trading.onchain import quality_picks as qp

DAY = 86400


def test_a_decision_is_kept_and_undone():
    assert qp.decide("base", "0xABCdef", "accept", "ABC") == "accepted"
    assert qp.is_accepted("base", "0xabcDEF")              # EVM addresses in any case
    assert qp.accepted() == {"base:0xabcdef"}
    qp._state["loaded"] = False
    qp._picks.clear()
    assert qp.is_accepted("base", "0xabcdef")               # read back from the file
    assert qp.decide("base", "0xabcdef", "discard") == "discarded" and not qp.accepted()
    assert qp.decide("base", "0xabcdef", "reset") is None and qp.state("base", "0xabcdef") is None


def _row(now, **kw):
    return {"chain": "solana", "token": "QUALmint", "symbol": "QUAL", "name": "Quality Project", "mcap": 2_000_000,
            "liq": 300_000, "score": 40, "status": "rejected", "why": "github too weak (20)",
            "analyzed_at": now - 60 * DAY, "launched_at": now - 90 * DAY,
            "overall": {"score": 86.0}, "pillars": {}, **kw}


def _wire(monkeypatch, row):
    import app.main as m
    monkeypatch.setattr(m.onchain_projects_db, "search", lambda **kw: {"items": []})
    monkeypatch.setattr(m.onchain_projects_db, "get", lambda c, t: row if t.lower() == row["token"].lower() else None)
    monkeypatch.setattr(m.onchain_judge, "get", lambda *a: None)
    monkeypatch.setattr(m.onchain_leaderboard, "board", lambda: {"entries": [], "early": []})
    monkeypatch.setattr(m.onchain_leaderboard, "usage_gate", lambda e, cap_floor=True: "")
    monkeypatch.setattr(m.onchain_leaderboard, "final_score", lambda e, kobra=False: 40)
    return m


def test_an_accepted_project_enters_the_gems_and_leaves_on_a_crash(monkeypatch):
    now = time.time()
    row = _row(now)
    m = _wire(monkeypatch, row)
    syms = lambda: [e["symbol"] for e in m._kobra_lists()[0]]  # noqa: E731
    assert syms() == []                                       # not studied, old, scoring 40
    qp.decide("solana", "QUALmint", "accept")
    assert syms() == ["QUAL"]                                 # in, its 40 included
    assert m._top_entries(10, full=True)[0]["quality_pick"]
    assert [e["symbol"] for e in m._top_entries(10)] == []    # only in whitekobra's view
    # Lorenzo: "Se Dregg domani dovesse avere un crollo [...] esce".
    key = m.onchain_leaderboard._key("solana", "QUALmint").lower()
    market_peaks.record(key, 2_000_000, 300_000, now - 600)
    market_peaks.record(key, 300_000, 100_000, now - 300)
    market_peaks.record(key, 300_000, 100_000, now - 100)
    assert syms() == []


def test_an_accepted_project_still_needs_the_usage_bars(monkeypatch):
    now = time.time()
    m = _wire(monkeypatch, _row(now))
    monkeypatch.setattr(m.onchain_leaderboard, "usage_gate", lambda e, cap_floor=True: "volume under $10k a day")
    qp.decide("solana", "QUALmint", "accept")
    assert m._kobra_lists() == ([], [])


def test_an_accepted_project_under_the_floor_goes_to_early(monkeypatch):
    now = time.time()
    m = _wire(monkeypatch, _row(now, mcap=200_000))
    monkeypatch.setattr(m.onchain_leaderboard, "usage_gate",
                        lambda e, cap_floor=True: "under $300k (early list)" if cap_floor else "")
    qp.decide("solana", "QUALmint", "accept")
    pool, early = m._kobra_lists()
    assert pool == [] and [e["symbol"] for e in early] == ["QUAL"]


def test_the_quality_list_waits_accepts_and_discards(monkeypatch):
    import app.main as m
    from app.trading.onchain import leaderboard as lb
    now = time.time()
    e = {"chain": "solana", "token_address": "DREGGmint", "symbol": "DREGG", "name": "Dregg", "market_cap": 900_000,
         "liquidity_usd": 120_000, "launched_at": now - 40 * DAY, "overall": {"score": 87.1}, "pillars": {}}
    low = {**e, "token_address": "LOWmint", "symbol": "LOW", "overall": {"score": 70.0}}
    monkeypatch.setattr(lb, "_entries", {lb._key("solana", "DREGGmint"): e, lb._key("solana", "LOWmint"): low})
    monkeypatch.setattr(m, "_kobra_lists", lambda narrative="": ([], []))
    monkeypatch.setattr(lb, "final_score", lambda x, kobra=False: 66)
    v = m._quality_view(now)
    assert [r["symbol"] for r in v["waiting"]] == ["DREGG"] and v["waiting"][0]["quality"] == 87.1
    qp.decide("solana", "DREGGmint", "accept")
    v = m._quality_view(now)
    assert v["waiting"] == [] and v["accepted"][0]["where"] == "out" and v["accepted"][0]["why"]
    qp.decide("solana", "DREGGmint", "discard")
    assert [r["symbol"] for r in m._quality_view(now)["discarded"]] == ["DREGG"]


def test_the_top_25_is_not_on_the_quality_list(monkeypatch):
    import app.main as m
    from app.trading.onchain import leaderboard as lb
    now = time.time()
    e = {"chain": "solana", "token_address": "DREGGmint", "symbol": "DREGG", "name": "Dregg",
         "overall": {"score": 87.1}, "pillars": {}, "score": 77}
    monkeypatch.setattr(lb, "_entries", {lb._key("solana", "DREGGmint"): e})
    monkeypatch.setattr(m, "_kobra_lists", lambda narrative="": ([dict(e)], []))
    assert m._quality_view(now)["waiting"] == []


def test_a_dead_pool_is_not_on_the_quality_list(monkeypatch):
    """BORLY (21/10): quality 94, $3k left, its rug from before the crash rule."""
    import app.main as m
    from app.trading.onchain import leaderboard as lb
    e = {"chain": "solana", "token_address": "BORLYpump", "symbol": "BORLY", "name": "Borly", "market_cap": 3_100,
         "liquidity_usd": 2_000, "overall": {"score": 94.0}, "pillars": {}}
    monkeypatch.setattr(lb, "_entries", {lb._key("solana", "BORLYpump"): e})
    monkeypatch.setattr(m, "_kobra_lists", lambda narrative="": ([], []))
    assert m._quality_view()["waiting"] == []
