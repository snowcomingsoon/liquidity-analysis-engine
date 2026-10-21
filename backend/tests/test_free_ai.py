import asyncio
import json

import httpx

from app import free_ai
from app.notify import deepseek_desk

OK = {"choices": [{"message": {"content": json.dumps({"verdict": "ok"})}}]}


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_no_key_no_call():
    assert not free_ai.available()

    async def run():
        try:
            await free_ai.post({"messages": []}, kind="judge")
        except free_ai.Unavailable:
            return True
    assert asyncio.run(run())


def test_a_daily_quota_moves_to_the_next_model_and_then_gemini(monkeypatch):
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k", "gemini": "g"})
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body["model"])
        if "groq" in str(request.url):
            return httpx.Response(429, text="Rate limit reached: tokens per day (TPD)")
        return httpx.Response(200, json=OK)

    async def run():
        async with _client(handler) as c:
            return await free_ai.post({"messages": [], "max_tokens": 100}, kind="judge", http=c)
    data = asyncio.run(run())
    assert data["provider"] == "gemini" and seen[:4] == [m for m in free_ai.PROVIDERS[0][2]]
    # The cooled Groq models are skipped on the next call.
    seen.clear()
    asyncio.run(run())
    assert seen == ["gemini-2.5-flash"]


def test_the_daily_cap_per_kind_and_the_manual_bypass(monkeypatch):
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k"})
    monkeypatch.setitem(free_ai.DAILY, "study", 1)

    async def run(manual=False):
        async with _client(lambda r: httpx.Response(200, json=OK)) as c:
            if manual:
                with free_ai.manual():
                    return await free_ai.post({"messages": []}, kind="study", http=c)
            return await free_ai.post({"messages": []}, kind="study", http=c)
    asyncio.run(run())
    try:
        asyncio.run(run())
        raised = False
    except free_ai.Unavailable:
        raised = True
    assert raised and asyncio.run(run(manual=True))["provider"] == "groq"


def test_deepseek_desk_hands_research_calls_to_the_free_ai(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "research_ai_enabled", False)
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k"})
    assert settings.research_deepseek
    captured = {}

    def handler(request):
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{\"a\": 1}"}}]})

    async def run():
        async with _client(handler) as c:
            return await deepseek_desk.ask([{"role": "user", "content": "x"}], kind="judge", http=c, json_mode=True)
    assert asyncio.run(run()) == '{"a": 1}'
    assert captured["model"] == "openai/gpt-oss-120b" and captured["reasoning_effort"] == "low"


def test_with_paid_deepseek_off_ai_readings_never_move_the_score(monkeypatch):
    from app.config import settings
    from app.trading.onchain import leaderboard as lb
    import time
    e = {"judge": {"score": 90, "at": time.time()}, "code": {"complexity": 90, "innovation": 90, "at": time.time()},
         "pillars": {"site": {"score": 50}}}
    assert lb.deepseek_score(e) == 90 and lb.product_score(e) == 70
    monkeypatch.setattr(settings, "research_ai_enabled", False)
    assert lb.deepseek_score(e) is None and lb.product_score(e) == 50


def test_the_drain_is_low_priority(monkeypatch):
    """Lorenzo, 21/10: the backlog drain "non deve andare a inficiare il resto
    delle operazioni"."""
    import time
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k", "gemini": "g"})
    monkeypatch.setattr(free_ai, "LOW_DAILY", 2)

    async def run(low=True, kind="research"):
        async with _client(lambda r: httpx.Response(200, json=OK)) as c:
            if low:
                with free_ai.low_priority():
                    return await free_ai.post({"messages": []}, kind=kind, http=c)
            return await free_ai.post({"messages": []}, kind=kind, http=c)

    def refused(**kw):
        try:
            asyncio.run(run(**kw))
            return False
        except free_ai.Unavailable:
            return True
    assert not refused() and not refused()
    assert refused()                                   # its own daily share is spent
    assert not refused(low=False)                      # the rest is untouched
    free_ai._calls.clear()
    # A model out of its daily quota: low priority work stops, the rest goes on.
    free_ai._cool["groq/openai/gpt-oss-120b"] = free_ai._next_day(time.time())
    assert refused() and not refused(low=False)
    free_ai._cool.clear()
    # Most models cooling for a minute: low priority waits too.
    for m in free_ai._models_on()[:4]:
        free_ai._cool[m] = time.time() + 60
    assert refused() and not refused(low=False)


def test_github_models_takes_the_call_when_groq_and_gemini_are_spent(monkeypatch):
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k", "gemini": "g", "github": "t"})
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if "models.github.ai" in str(request.url):
            assert request.headers["Authorization"] == "Bearer t"
            return httpx.Response(200, json=OK)
        return httpx.Response(429, text="Rate limit reached: requests per day (RPD)")

    async def run():
        async with _client(handler) as c:
            return await free_ai.post({"messages": [], "max_tokens": 100}, kind="judge", http=c)
    data = asyncio.run(run())
    assert data["provider"] == "github" and data["model"] == "openai/gpt-4.1-mini"
