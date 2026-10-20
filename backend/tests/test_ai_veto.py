import asyncio
import json
import time

import httpx
from app.trading.onchain import ai_veto, leaderboard as lb

PUMP = "So1aNaMint1111111111111111111111111111pump"


def _e(**kw):
    e = {"chain": "solana", "token_address": PUMP, "symbol": "BORLY", "name": "Borly", "launched_at": time.time() - 3 * 86400,
         "description": "Every token funds a model", "pillars": {"site": {"score": 88, "facts": {"excerpt": "Launch a token"}}}}
    e.update(kw)
    return e


def _answer(content: dict, status: int = 200):
    def handler(request):
        return httpx.Response(status, json={"choices": [{"message": {"content": json.dumps(content)}}]})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_no_key_means_no_wait_and_no_veto():
    assert ai_veto.reason(_e()) == ""


def test_a_launchpad_token_waits_for_its_verdict_when_a_key_is_set(monkeypatch):
    monkeypatch.setattr(ai_veto, "_keys", lambda: {"groq": "k"})
    assert "waiting for the AI check" in ai_veto.reason(_e())
    assert ai_veto.reason(_e(token_address="Mint1111", source="jupiter")) == ""


def test_a_confident_avoid_vetoes_and_reaches_qualifies(monkeypatch):
    monkeypatch.setattr(ai_veto, "_keys", lambda: {"groq": "k"})

    async def run():
        async with _answer({"verdict": "avoid", "impersonates": None, "meme": False, "confidence": 0.9,
                            "reason": "a token launcher whose only product is more tokens"}) as c:
            v = await ai_veto.judge(_e(), c)
        assert v["provider"] == "groq" and "nothing real" in ai_veto.reason(_e())
        assert "nothing real" in lb.qualifies({**_e(), "market_cap": 1_000_000, "liquidity_usd": 100_000})
    asyncio.run(run())


def test_an_unsure_answer_vetoes_nothing_and_copies_are_named(monkeypatch):
    monkeypatch.setattr(ai_veto, "_keys", lambda: {"groq": "k"})

    async def run():
        async with _answer({"verdict": "avoid", "confidence": 0.5, "reason": "thin"}) as c:
            await ai_veto.judge(_e(), c)
        assert ai_veto.reason(_e()) == ""
        async with _answer({"verdict": "ok", "impersonates": "Apple", "confidence": 0.95, "reason": "uses the Apple name"}) as c:
            await ai_veto.judge(_e(token_address="X" * 40 + "pump"), c)
        assert "copies Apple" in ai_veto.reason(_e(token_address="X" * 40 + "pump"))
    asyncio.run(run())


def test_gemini_answers_when_groq_fails(monkeypatch):
    monkeypatch.setattr(ai_veto, "_keys", lambda: {"groq": "k", "gemini": "g"})

    async def run():

        def handler(request):
            if "groq" in str(request.url):
                return httpx.Response(503, json={})
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(
                {"verdict": "ok", "confidence": 0.8, "reason": "real product"})}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            v = await ai_veto.judge(_e(), c)
        assert v["provider"] == "gemini" and ai_veto.reason(_e()) == ""
    asyncio.run(run())


def test_run_once_reads_each_candidate_once_within_the_turn(monkeypatch):
    monkeypatch.setattr(ai_veto, "_keys", lambda: {"groq": "k"})

    async def run():
        calls = []

        def handler(request):
            calls.append(1)
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(
                {"verdict": "ok", "confidence": 0.9, "reason": "fine"})}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            n = await ai_veto.run_once([_e(), _e(), _e(token_address="B" * 40)], c)
            again = await ai_veto.run_once([_e()], c)
        assert n == 2 and again == 0 and len(calls) == 2
    asyncio.run(run())
