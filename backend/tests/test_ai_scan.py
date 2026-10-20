"""DeepSeek's shadow judgement on meme alerts (ai_scan.py)."""
import asyncio
import json

import pytest

from app import free_ai
from app.notify import deepseek_desk
from app.trading.onchain import ai_scan
from app.trading.onchain import alert_track as tr


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setattr(tr, "_STORE_FILE", tmp_path / "t.json")
    monkeypatch.setattr(deepseek_desk, "_STORE_FILE", tmp_path / "u.json")
    tr.reset_for_tests()
    deepseek_desk.reset_for_tests()
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k"})
    yield
    tr.reset_for_tests()


def _alert(i, now, **kw):
    item = {"chain": "solana", "pair_address": f"P{i}", "token_address": f"T{i}", "symbol": f"S{i}", "name": f"Coin {i}",
            "market_cap": 50_000, "liquidity_usd": 10_000,
            "checks": [{"label": "Security", "ok": True, "detail": "mint renounced"}], "socials": [{"type": "twitter"}],
            "website": "https://coin.example/about"}
    a = tr.record(item, "meme", now)
    a.update(kw)
    return a


def test_facts_are_one_short_line():
    a = _alert(0, 1000.0)
    assert a["facts"] == "Security: ok mint renounced | social twitter | site coin.example"


def test_batches_of_ten_one_call_each_and_judged_once(monkeypatch):
    now = 10_000.0
    for i in range(23):
        _alert(i, now - 60)
    calls = []

    async def fake(messages, *, kind, max_tokens, json_mode, **_):
        lines = messages[1]["content"].split("Tokens:\n", 1)[1].splitlines()
        calls.append(len(lines))
        assert kind == "scanner" and json_mode and messages[0]["content"] == ai_scan.SYSTEM
        return json.dumps({"items": [{"i": j, "risk": 70, "flags": ["copycat"], "theme": "dog"} for j in range(len(lines))]})
    monkeypatch.setattr(ai_scan.deepseek_desk, "ask", fake)
    assert asyncio.run(ai_scan.run_once(now)) == 23
    assert calls == [10, 10, 3]
    assert asyncio.run(ai_scan.run_once(now)) == 0 and len(calls) == 3


def test_old_or_gone_alerts_are_skipped():
    now = 100_000.0
    _alert(1, now - ai_scan.MAX_AGE_S - 10)
    _alert(2, now - 60, gone=True)
    assert ai_scan._pending(now) == []


def test_bad_answers_are_ignored():
    a = _alert(1, 1.0)
    assert ai_scan.parse("not json", [a], 1.0) == 0
    assert ai_scan.parse(json.dumps({"items": [{"i": 5, "risk": 10}]}), [a], 1.0) == 0
    assert ai_scan.parse(json.dumps({"items": [{"i": 0, "risk": 250, "flags": ["x"] * 5}]}), [a], 1.0) == 1
    assert a["ai"]["risk"] == 100 and len(a["ai"]["flags"]) == 3


def test_shadow_stats_compare_risk_with_what_happened():
    now = 1_000_000.0
    _alert(1, now - 90_000, ai={"risk": 80}, gone=True, returns={"24": -1.0})
    _alert(2, now - 90_000, ai={"risk": 90}, returns={"24": -0.5})
    _alert(3, now - 90_000, ai={"risk": 10}, returns={"24": 0.4})
    _alert(4, now - 60, ai={"risk": 10})               # too young to count
    s = ai_scan.shadow_stats(now)
    assert s["n"] == 3
    assert s["high"] == {"n": 2, "rug": 0.5, "median_24h": -0.75}
    assert s["low"] == {"n": 1, "rug": 0.0, "median_24h": 0.4}
    assert "rischio alto: 2 (50% rug" in ai_scan.recap_line(now)


def test_gem_site_on_deepseek_is_cached_and_does_not_block(monkeypatch):
    from app.trading.onchain import legit
    legit._ai_cache.clear()
    monkeypatch.setattr(legit.settings, "anthropic_api_key", "")
    monkeypatch.setattr(legit.settings, "legit_ai_gate", False)
    sent = []

    async def fake(messages, *, kind, max_tokens, json_mode, **_):
        sent.append(messages[1]["content"])
        return json.dumps({"legit": False, "score": 2, "reason": "template page", "red_flags": ["no product"]})
    monkeypatch.setattr(deepseek_desk, "ask", fake)
    site = {"final_url": "https://x.io", "title": "X", "text": "a" * 20_000}
    r = asyncio.run(legit.ai_review({"name": "X", "symbol": "X", "chain": "base"}, site, {}))
    asyncio.run(legit.ai_review({"name": "X2", "symbol": "X2", "chain": "base"}, site, {}))
    assert len(sent) == 1 and len(sent[0]) < legit.AI_SITE_CHARS_DEEPSEEK + 500
    check = legit.judge_ai(r)
    assert check["label"] == "DeepSeek on the site" and check["ok"] is None and "not blocking" in check["detail"]
    monkeypatch.setattr(legit.settings, "legit_ai_gate", True)
    assert legit.judge_ai(r)["ok"] is False


def test_the_risk_is_measured_by_the_memory_but_not_used_by_its_model():
    from app.trading.onchain import outcomes
    outcomes.reset_for_tests()
    a = _alert(1, 1.0)
    outcomes._journal[f"solana:{a['token_address']}"] = {"features": {"mcap": 1.0}}
    ai_scan.parse(json.dumps({"items": [{"i": 0, "risk": 77}]}), [a], 1.0)
    assert outcomes._journal["solana:T1"]["features"]["ai_risk"] == 77
    assert "ai_risk" not in outcomes.MODEL_KEYS and "ai_risk" in outcomes.RISK_UP
    outcomes.reset_for_tests()


def test_paid_deep_reading_runs_on_deepseek_without_an_anthropic_key(monkeypatch):
    from app.trading.onchain import legit, plans, research
    monkeypatch.setattr(legit.settings, "anthropic_api_key", "")
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k"})

    async def fake(messages, *, kind, max_tokens, json_mode, **_):
        assert kind == "research" and '"verdict"' in messages[0]["content"]
        return json.dumps({"summary": "s", "stage": "live", "substance": 14, "original": True, "verdict": "promising",
                           "red_flags": []})
    monkeypatch.setattr(deepseek_desk, "ask", fake)
    out = asyncio.run(research.ai_dossier({"name": "P"}, "desc", ["site"], boost=True))
    assert out["substance"] == 10 and out["by"] == "deepseek"
    assert asyncio.run(research.ai_dossier({"name": "P"}, "desc", ["site"])) is None    # background stays off
    assert plans.status("a@b.c")["deep_available"] is True


def test_deepseek_has_half_the_say_on_a_gem_finalist(monkeypatch):
    from app.trading.onchain import legit, research
    monkeypatch.setattr(legit.settings, "anthropic_api_key", "")
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k"})
    reader = {"points": 80, "substance": 8, "red_flags": ["thin docs"], "original": True}
    out = research.blend(reader, {"substance": 4, "verdict": "thin", "red_flags": ["no product"]})
    assert out["points"] == 60 and out["red_flags"] == ["thin docs", "DeepSeek: no product"]
    assert research.blend(reader, {"substance": 9, "verdict": "scam"})["points"] == 40   # a voice, not a veto
    research._cache.clear()
    research._calls.clear()
    calls = []

    async def fake(prompt, subject=None):
        calls.append(prompt)
        return {"substance": 6, "verdict": "promising", "red_flags": []}
    monkeypatch.setattr(research, "_dossier_deepseek", fake)
    monkeypatch.setattr(research, "judge_research", lambda *a: {"score": 70})
    monkeypatch.setattr(research, "_save", lambda: None)
    item = {"finalist": True, "name": "P", "chain": "solana"}
    assert asyncio.run(research._deepseek_reading("k1", item, [], "desc", ["t"]))["substance"] == 6
    asyncio.run(research._deepseek_reading("k1", item, [], "desc", ["t"]))
    assert len(calls) == 1                                      # a week in the cache
    assert asyncio.run(research._deepseek_reading("k2", {**item, "finalist": False}, [], "d", ["t"])) is None


def test_a_report_without_holders_means_unknown_not_zero():
    from app.trading.onchain import legit
    assert legit.holder_concentration({"lpLockedPct": 100}) == (None, None)
    check = legit.judge_rugcheck({"lpLockedPct": 100, "risks": []})
    assert check["ok"] is True and check["facts"]["top_holder_pct"] is None
