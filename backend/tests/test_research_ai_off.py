"""research_ai_enabled off (Lorenzo, 10/10: "neanche deepseek"): no
DeepSeek call leaves the server except the chat, and the Anthropic key is
ignored."""
import asyncio

import pytest

from app.config import Settings, settings
from app.notify import deepseek_desk


class _Http:
    def __init__(self):
        self.calls = 0

    async def post(self, url, json, headers):
        self.calls += 1

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "ok"}}], "usage": {}}
        return R()


def test_default_is_off():
    assert Settings(_env_file=None).research_ai_enabled is False


def test_research_kinds_never_reach_deepseek(monkeypatch):
    monkeypatch.setattr(settings, "research_ai_enabled", False)
    http = _Http()
    for kind in ("research", "review", "study", "scanner", "code", "consistency", "narratives"):
        with pytest.raises(deepseek_desk.BudgetExceeded):
            asyncio.run(deepseek_desk.ask([{"role": "user", "content": "x"}], kind=kind, http=http))
    assert http.calls == 0


def test_chat_still_answers(monkeypatch):
    from app import free_ai
    monkeypatch.setattr(settings, "research_ai_enabled", False)
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k"})
    http = _Http()
    assert asyncio.run(deepseek_desk.ask([{"role": "user", "content": "x"}], kind="chat", http=http)) == "ok"
    assert http.calls == 1


def test_anthropic_key_is_ignored_when_off():
    from app.config import without_paid_ai
    off = without_paid_ai(Settings(_env_file=None, anthropic_api_key="sk-x"))
    assert off.anthropic_api_key == ""
    on = without_paid_ai(Settings(_env_file=None, anthropic_api_key="sk-x", research_ai_enabled=True))
    assert on.anthropic_api_key == "sk-x"
