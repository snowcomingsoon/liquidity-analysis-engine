"""DeepSeek on Telegram and its daily ledger (app/notify/deepseek_desk.py)."""
import asyncio
from datetime import datetime

import pytest

from app.notify import deepseek_desk as dd


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setattr(dd, "_STORE_FILE", tmp_path / "u.json")
    dd.reset_for_tests()
    yield
    dd.reset_for_tests()


def test_ledger_counts_per_day_and_kind():
    now = datetime(2026, 9, 27, 12, tzinfo=dd.ROME).timestamp()
    dd.record("chat", 1000, 200, now=now)
    dd.record("chat", 500, 100, now=now)
    dd.record("review", 2000, 300, now=now)
    day = dd._state["days"]["2026-09-27"]
    assert day["chat"] == {"calls": 2, "in": 1500, "out": 300}
    assert dd.spent_today("chat", now=now) == 1800


def test_recap_says_what_it_cost_and_what_claude_would_have():
    text = dd.recap_text("2026-09-27", {"chat": {"calls": 3, "in": 1_000_000, "out": 100_000},
                                        "pr_review": {"calls": 2, "in": 60_000, "out": 4_000}})
    assert "chat Telegram: 3 richieste" in text and "revisioni PR: 2 richieste" in text
    # DeepSeek 1.06M in * 0.28 + 0.104M out * 0.42 = $0.340; Claude 1.06*3 + 0.104*15 = $4.74
    assert "3 richieste, 1.100.000 token" in text and "$0.340" in text and "~$4.74" in text and "Risparmio stimato" in text
    assert "nessun lavoro" in dd.recap_text("2026-09-27", {})


def test_recap_once_a_day_after_the_hour():
    before = datetime(2026, 9, 27, dd.RECAP_HOUR - 1, 30, tzinfo=dd.ROME).timestamp()
    after = datetime(2026, 9, 27, dd.RECAP_HOUR, 5, tzinfo=dd.ROME).timestamp()
    assert dd.recap_due(before) is None
    assert dd.recap_due(after) == "2026-09-27"
    dd.mark_sent("2026-09-27")
    assert dd.recap_due(after + 600) is None


def test_group_messages_only_when_asked():
    private = {"chat": {"type": "private"}, "text": "come va il sistema?"}
    assert dd.wants_answer(private, "laebot") == "come va il sistema?"
    group = {"chat": {"type": "group"}, "text": "ciao a tutti"}
    assert dd.wants_answer(group, "laebot") is None
    assert dd.wants_answer({**group, "text": "/ask quanti alert oggi?"}, "laebot") == "quanti alert oggi?"
    assert dd.wants_answer({**group, "text": "@LaeBot quanti alert?"}, "laebot") == "quanti alert?"
    reply = {**group, "reply_to_message": {"from": {"username": "laebot"}}}
    assert dd.wants_answer(reply, "laebot") == "ciao a tutti"


def test_chat_keeps_a_short_memory_and_a_daily_cap(monkeypatch):
    seen = []

    async def fake(messages, *, kind, **_):
        seen.append(list(messages))
        dd.record(kind, 100, 50)
        return {"content": f"risposta {len(seen)}"}
    monkeypatch.setattr(dd, "ask_message", fake)
    assert asyncio.run(dd.answer("42", "prima", "ctx")) == "risposta 1"
    asyncio.run(dd.answer("42", "seconda", "ctx"))
    assert [m["content"] for m in seen[1][1:]] == ["prima", "risposta 1", "seconda"]
    assert "dimenticato" in asyncio.run(dd.answer("42", "/reset", "ctx")) and "42" not in dd._memory
    monkeypatch.setattr(dd, "CHAT_DAILY_TOKENS", 1)
    assert "budget" in asyncio.run(dd.answer("42", "terza", "ctx"))


def test_pr_review_usage_reads_the_markers():
    class R:
        status_code = 200

        def json(self):
            return [{"body": '<!-- deepseek-review --><!-- deepseek-usage {"at": 150, "in": 30000, "out": 2000} -->\nx'},
                    {"body": '<!-- deepseek-usage {"at": 5000, "in": 1, "out": 1} -->'},
                    {"body": "a human comment"}]

    class H:
        async def get(self, *a, **k):
            return R()
    dd.settings.github_api_token = "t"
    try:
        u = asyncio.run(dd.pr_review_usage(100, 200, http=H()))
    finally:
        dd.settings.github_api_token = ""
    assert u == {"calls": 1, "in": 30000, "out": 2000}


def test_chat_can_look_things_up_in_the_database(monkeypatch):
    rounds = []

    async def fake(messages, *, kind, tools=None, **_):
        rounds.append(tools)
        if len(rounds) == 1:
            return {"content": "", "tool_calls": [{"id": "c1", "type": "function",
                                                   "function": {"name": "cerca_token", "arguments": '{"query": "VISE"}'}}]}
        tool_msg = messages[-1]
        assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "c1" and "rug" in tool_msg["content"]
        return {"content": "VISE e' stato un rug dopo 3 ore."}
    monkeypatch.setattr(dd, "ask_message", fake)
    tools = {"cerca_token": ({"name": "cerca_token", "parameters": {}}, lambda query: [{"symbol": query, "outcome": "rug"}])}
    assert asyncio.run(dd.answer("7", "cos'e' successo a VISE?", "ctx", tools)) == "VISE e' stato un rug dopo 3 ore."
    assert rounds[0][0]["function"]["name"] == "cerca_token"


def test_activity_log_is_short_and_says_when_it_is_working():
    for i in range(dd.ACTIVITY_KEEP + 5):
        dd.note("scan", f"Judged T{i}", now=1000.0 + i)
    a = dd.activity(now=1000.0 + dd.ACTIVITY_KEEP + 60)
    assert len(dd._activity) == dd.ACTIVITY_KEEP and a["items"][0]["text"] == f"Judged T{dd.ACTIVITY_KEEP + 4}"
    assert a["working"] is True
    assert dd.activity(now=5000.0)["working"] is False


def test_activity_survives_a_restart():
    dd.note("scanner", "x")
    dd._activity.clear()
    dd._load()
    assert dd.activity()["items"][0]["text"] == "x"


def test_every_database_tool_answers_and_reports_land_on_the_board(tmp_path, monkeypatch):
    from app import issues as issues_store, main
    monkeypatch.setattr(issues_store, "_STORE_FILE", tmp_path / "issues.json")
    tools = main._deepseek_tools()
    for name in ("cerca_progetti", "classifica_gemme", "alert_ora", "sistema", "scartati", "memoria", "ultimi_rug",
                 "circostanze_rug"):
        spec, fn = tools[name]
        assert spec["name"] == name
        assert fn() is not None
    before = len(issues_store.list_issues())
    out = tools["segnala_bug"][1](titolo="Holder a 0%", dettaglio="top_holder_pct 0.0 su 40 token")
    assert out["ok"] and len(issues_store.list_issues()) == before + 1
    issues_store.delete_issue(out["id"])


def test_recap_counts_every_recorded_kind():
    """#366: kinds missing from KINDS (code, narratives...) were left out of the total."""
    text = dd.recap_text("2026-09-27", {"narratives": {"calls": 2, "in": 1000, "out": 0},
                                        "brand_new": {"calls": 1, "in": 500, "out": 500}})
    assert "narrative: 2 richieste" in text and "brand_new: 1 richieste" in text
    assert "Token lavorati da DeepSeek: <b>2.000</b>" in text


def _fake_http(calls: list):
    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"usage": {"prompt_tokens": 1_500_000, "completion_tokens": 0},
                    "choices": [{"message": {"content": "ok"}}]}

    class H:
        async def post(self, *a, **k):
            calls.append(1)
            return R()
    return H()






def test_findings_of_a_check_are_not_counted_as_work():
    """Issue #366: every consistency finding added a "consistency" to the Agent tab."""
    now = datetime(2026, 9, 29, 12, tzinfo=dd.ROME).timestamp()
    dd.note("consistency", "Checking 10 projects", now=now)
    dd.note("consistency", "ABC: cap vs volume", now=now, tally=False, symbol="ABC")
    assert dd.activity(now)["done"] == {"consistency": 1}
