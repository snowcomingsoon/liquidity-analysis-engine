import asyncio
import json
import time

import pytest

from app import free_ai
from app.trading.onchain import deep_recheck, leaderboard, projects_db, scout_recheck


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(deep_recheck, "_STORE", tmp_path / "deep.json")
    deep_recheck.reset_for_tests()
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k"})
    yield
    deep_recheck.reset_for_tests()


def _row(tok):
    projects_db.upsert({"chain": "solana", "token_address": tok, "symbol": "T"}, "test", now=100)
    projects_db.record({"chain": "solana", "token_address": tok, "pillars": {}}, "studied", why="DeepSeek review: old",
                       score=40, now=100)


def _fake_ask(payload):
    async def ask(messages, **kw):
        return json.dumps(payload)
    return ask


def _fake_recheck(rc):
    async def recheck(entry, item, client, ask=None):
        return rc
    return recheck


def test_dropped_token_kept_clears_why(monkeypatch):
    _row("tok1")
    monkeypatch.setattr(scout_recheck, "recheck", _fake_recheck(
        {"confirmed": [], "unverified": [], "refuted": [{"text": "x", "note": "ok"}], "found": [], "evidence": "ev"}))
    ask = _fake_ask({"keep": True, "score": 70, "verdict": "gem", "reason": "real product",
                     "strengths": ["ships"], "problems": []})
    res = asyncio.run(deep_recheck.run("solana", "tok1", None, ask=ask))
    assert res["keep"] is True
    assert deep_recheck.get("solana", "tok1")["score"] == 70
    row = projects_db.get("solana", "tok1")
    assert not (row.get("why") or "").startswith("DeepSeek")


def test_second_call_within_cooldown(monkeypatch):
    _row("tok2")
    monkeypatch.setattr(scout_recheck, "recheck", _fake_recheck(
        {"confirmed": [], "unverified": [], "refuted": [], "found": [], "evidence": ""}))
    ask = _fake_ask({"keep": False, "score": 10, "verdict": "avoid", "reason": "nothing",
                     "strengths": [], "problems": ["no product"]})
    asyncio.run(deep_recheck.run("solana", "tok2", None, ask=ask))
    with pytest.raises(deep_recheck.TooSoon) as exc:
        asyncio.run(deep_recheck.run("solana", "tok2", None, ask=ask))
    assert exc.value.wait_s > 0


def test_daily_max(monkeypatch):
    _row("tok3")
    monkeypatch.setattr(scout_recheck, "recheck", _fake_recheck(
        {"confirmed": [], "unverified": [], "refuted": [], "found": [], "evidence": ""}))
    ask = _fake_ask({"keep": False, "score": 10, "verdict": "avoid", "reason": "nothing",
                     "strengths": [], "problems": []})
    day = time.strftime("%Y-%m-%d", time.gmtime())
    deep_recheck._state["calls"][day] = deep_recheck.DAILY_MAX
    with pytest.raises(deep_recheck.TooSoon):
        asyncio.run(deep_recheck.run("solana", "tok3", None, ask=ask))


def test_unreadable_json_counts(monkeypatch):
    _row("tok4")
    monkeypatch.setattr(scout_recheck, "recheck", _fake_recheck(
        {"confirmed": [], "unverified": [], "refuted": [], "found": [], "evidence": ""}))

    async def ask(messages, **kw):
        return "not json"

    day = time.strftime("%Y-%m-%d", time.gmtime())
    before = deep_recheck._state["calls"].get(day, 0)
    with pytest.raises(RuntimeError):
        asyncio.run(deep_recheck.run("solana", "tok4", None, ask=ask))
    assert deep_recheck._state["calls"].get(day, 0) == before + 1


def test_board_entry_gets_deep_review(monkeypatch):
    entry = {"chain": "solana", "token_address": "tok5", "name": "T", "symbol": "T",
             "pillars": {}, "judge": {"verdict": "watch", "score": 30, "problems": ["p"]}}
    leaderboard._entries["solana:tok5"] = entry
    monkeypatch.setattr(scout_recheck, "recheck", _fake_recheck(
        {"confirmed": [], "unverified": [], "refuted": [], "found": [], "evidence": ""}))
    ask = _fake_ask({"keep": True, "score": 80, "verdict": "gem", "reason": "good",
                     "strengths": [], "problems": []})
    asyncio.run(deep_recheck.run("solana", "tok5", None, ask=ask))
    assert leaderboard._entries["solana:tok5"]["review"]["deep"] is True
    leaderboard._entries.pop("solana:tok5", None)


def test_double_tap_asks_once(monkeypatch):
    _row("tok6")
    monkeypatch.setattr(scout_recheck, "recheck", _fake_recheck(
        {"confirmed": [], "unverified": [], "refuted": [], "found": [], "evidence": ""}))
    calls = []

    async def ask(messages, **kw):
        calls.append(1)
        await asyncio.sleep(0.01)
        return json.dumps({"keep": True, "score": 60, "verdict": "watch", "reason": "ok"})

    async def both():
        return await asyncio.gather(deep_recheck.run("solana", "tok6", None, ask=ask),
                                    deep_recheck.run("solana", "tok6", None, ask=ask), return_exceptions=True)

    res = asyncio.run(both())
    assert len(calls) == 1
    assert sum(isinstance(r, deep_recheck.TooSoon) for r in res) == 1


def test_failed_second_search_still_asks(monkeypatch):
    _row("tok7")

    async def boom(*a, **kw):
        raise ValueError("network")

    monkeypatch.setattr(scout_recheck, "recheck", boom)
    res = asyncio.run(deep_recheck.run("solana", "tok7", None, ask=_fake_ask(
        {"keep": False, "score": 20, "verdict": "avoid", "reason": "thin"})))
    assert res["unsupported"] is True and res["claims"] == []


def test_a_drop_needs_a_problem_backed_by_a_real_quote(monkeypatch):
    _row("tok8")
    ev = "Checked sources:\nsite html: found — 200, 900 bytes\nliquidity $3,100 against a $2,400,000 cap"
    monkeypatch.setattr(scout_recheck, "recheck", _fake_recheck(
        {"confirmed": [], "unverified": [], "refuted": [], "found": [], "evidence": ev}))
    made_up = {"keep": False, "score": 10, "verdict": "avoid", "reason": "no product",
               "problems": [{"text": "no product", "evidence": "the product does not exist"}]}
    res = asyncio.run(deep_recheck.run("solana", "tok8", None, ask=_fake_ask(made_up)))
    assert res["unsupported"] is True and res["keep"] is True and res["problems"] == []
    row = projects_db.get("solana", "tok8")
    assert (row.get("why") or "").startswith("DeepSeek review")       # an unsupported answer changes nothing

    _row("tok9")
    real = {**made_up, "problems": [{"text": "pool is tiny for the cap",
                                     "evidence": "liquidity $3,100 against a $2,400,000 cap"}]}
    res = asyncio.run(deep_recheck.run("solana", "tok9", None, ask=_fake_ask(real)))
    assert res["keep"] is False and res["problems"][0]["evidence"].startswith("liquidity $3,100")


def test_a_drop_on_gaps_alone_changes_nothing(monkeypatch):
    _row("tok10")
    ev = "Checked sources:\nGitHub: not found — no public repository found\nhttps://x.io/docs: unreadable — no text"
    monkeypatch.setattr(scout_recheck, "recheck", _fake_recheck(
        {"confirmed": [], "unverified": [], "refuted": [], "found": [], "evidence": ev}))
    gaps = {"keep": False, "score": 20, "verdict": "avoid", "reason": "no code",
            "problems": [{"text": "No public GitHub", "evidence": "GitHub: not found — no public repository found"},
                         {"text": "Docs not readable", "evidence": "https://x.io/docs: unreadable — no text"}]}
    res = asyncio.run(deep_recheck.run("solana", "tok10", None, ask=_fake_ask(gaps)))
    # "Docs not readable" is our reader's gap: not even listed as a problem (08/10).
    assert res["unsupported"] is True and len(res["problems"]) == 1


def test_account_holders_recheck_whenever_they_want(monkeypatch):
    _row("tok9")
    monkeypatch.setattr(scout_recheck, "recheck", _fake_recheck(
        {"confirmed": [], "unverified": [], "refuted": [], "found": [], "evidence": ""}))
    ask = _fake_ask({"keep": True, "score": 60, "verdict": "watch", "reason": "fine",
                     "strengths": [], "problems": []})
    now = time.time()
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    deep_recheck._state["calls"][day] = deep_recheck.DAILY_MAX
    asyncio.run(deep_recheck.run("solana", "tok9", None, now=now, ask=ask, limited=False))
    with pytest.raises(deep_recheck.TooSoon):   # a double tap
        asyncio.run(deep_recheck.run("solana", "tok9", None, now=now + 2, ask=ask, limited=False))
    asyncio.run(deep_recheck.run("solana", "tok9", None, now=now + deep_recheck.TAP_GAP_S + 1, ask=ask, limited=False))
    assert deep_recheck.wait_s("solana", "tok9", now + 3600, limited=False) == 0
    assert deep_recheck.wait_s("solana", "tok9", now + 3600) > 0


def test_weekly_sweep_walks_the_board_once_a_week():
    t0 = 1_800_000_000.0
    keys = ["solana:a", "robinhood:b"]
    assert deep_recheck.next_in_sweep(keys, t0) == "solana:a"
    deep_recheck._sweep_done("solana:a")
    assert deep_recheck.next_in_sweep(keys, t0 + 90) == "robinhood:b"
    deep_recheck._sweep_done("robinhood:b")
    assert deep_recheck.next_in_sweep(keys, t0 + 180) is None
    assert deep_recheck.next_in_sweep(keys + ["base:c"], t0 + 86400) is None
    assert deep_recheck.next_in_sweep(keys + ["base:c"], t0 + deep_recheck.WEEK_S) == "solana:a"
    assert deep_recheck._state["sweep"]["keys"] == keys + ["base:c"]


def test_a_stalled_sweep_restarts_after_a_week():
    t0 = 1_800_000_000.0
    assert deep_recheck.next_in_sweep(["solana:a"], t0) == "solana:a"
    assert deep_recheck.next_in_sweep(["base:z"], t0 + deep_recheck.WEEK_S) == "base:z"


def test_progress_shows_the_real_steps(monkeypatch):
    _row("tok7")
    monkeypatch.setattr(scout_recheck, "recheck", _fake_recheck(
        {"confirmed": [], "unverified": [], "refuted": [], "found": [], "evidence": ""}))
    ask = _fake_ask({"keep": True, "score": 60, "verdict": "watch", "reason": "fine",
                     "strengths": [], "problems": []})
    asyncio.run(deep_recheck.run("solana", "tok7", None, ask=ask, limited=False))
    p = deep_recheck.progress("solana", "tok7")
    labels = [s["label"] for s in p["steps"]]
    assert p["running"] is False and all(s["state"] == "done" for s in p["steps"])
    assert labels[0] == "Loading the project and its last review"
    assert "Asking DeepSeek for the verdict" in labels and labels[-1] == "Verdict: kept"
    assert scout_recheck.PROGRESS.get() is None


def test_tidy_shows_each_fact_once_with_matching_counts():
    res = {"problems": [{"text": "SDK repo has a single author", "evidence": "q"},
                        {"text": "Marketing site is JavaScript-only and unreadable", "evidence": "q"},
                        {"text": "Pool holds 2% of the cap", "evidence": "q"}],
           "claims": [{"text": "Only 1 author on the SDK repo", "status": "confirmed"},
                      {"text": "single author", "status": "confirmed"},
                      {"text": "site built in JavaScript, not readable", "status": "confirmed"},
                      {"text": "Site is a JavaScript shell with no mechanisms", "status": "refuted", "evidence": "e"}],
           "cleared": 1, "unverified": 0, "confirmed": 3}
    out = deep_recheck.tidy(res)
    assert [p["text"] for p in out["problems"]] == ["Pool holds 2% of the cap"]
    assert [c["status"] for c in out["claims"]] == ["confirmed", "refuted"]
    assert (out["cleared"], out["unverified"], out["confirmed"]) == (1, 0, 1)


def test_progress_carries_the_log_of_what_was_opened(monkeypatch):
    _row("tok8")

    async def rc(entry, item, client, ask=None):
        scout_recheck.TRACE.get()("GitHub", "github.com/a/b")["code"] = 200
        return {"confirmed": [], "unverified": [], "refuted": [], "found": [], "evidence": ""}
    monkeypatch.setattr(scout_recheck, "recheck", rc)
    ask = _fake_ask({"keep": True, "score": 60, "verdict": "watch", "reason": "fine", "strengths": [], "problems": []})
    asyncio.run(deep_recheck.run("solana", "tok8", None, ask=ask, limited=False))
    p = deep_recheck.progress("solana", "tok8")
    assert p["log"] == [{"n": 0, "src": "GitHub", "text": "github.com/a/b", "code": 200}]
    assert scout_recheck.TRACE.get() is None
