"""The app's mic button (POST /api/agent/ask): same assistant and read-only
tools as the Telegram chat, per-account hourly limit, no guests."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import free_ai
from app import auth, main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "_USERS_FILE", tmp_path / "users.json")
    auth._users.clear()
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k"})
    main._ask_log.clear()
    seen = {}

    async def _answer(chat_id, text, context, tools=None, can_teach=False):
        seen.update(chat_id=chat_id, text=text, context=context, tools=tools, can_teach=can_teach)
        return "risposta"

    async def _ctx(chat_id, user=None):
        return f"ctx for {user.email}"

    monkeypatch.setattr(main.deepseek_desk, "answer", _answer)
    monkeypatch.setattr(main, "_deepseek_context", _ctx)
    user = auth.create_user("asker@example.com", "correct-horse-battery-9")
    main.app.dependency_overrides[auth.get_current_user] = lambda: auth.get_user(user.id)
    with TestClient(main.app) as c:
        c.seen, c.user_id = seen, user.id
        yield c
    main.app.dependency_overrides.clear()


def test_ask_answers_with_the_database_tools(client):
    r = client.post("/api/agent/ask", json={"text": "come va la top 50?", "voice": True})
    assert r.status_code == 200 and r.json() == {"answer": "risposta"}
    s = client.seen
    assert s["chat_id"] == f"web:{client.user_id}"
    assert "ctx for asker@example.com" in s["context"] and "dettato a voce" in s["context"]
    assert {"portafoglio_top50", "layer_engine", "classifica_gemme"} <= set(s["tools"])
    assert s["can_teach"] is False


def test_talk_mode_asks_for_a_short_spoken_answer(client):
    client.post("/api/agent/ask", json={"text": "e la top 50?", "talk": True})
    assert "letta ad alta voce" in client.seen["context"]
    client.post("/api/agent/ask", json={"text": "e la top 50?"})
    assert "letta ad alta voce" not in client.seen["context"]


def test_ask_is_rate_limited(client):
    for _ in range(main.ASK_PER_HOUR):
        assert client.post("/api/agent/ask", json={"text": "x"}).status_code == 200
    assert client.post("/api/agent/ask", json={"text": "x"}).status_code == 429


def test_ask_rejects_empty_and_long(client):
    assert client.post("/api/agent/ask", json={"text": ""}).status_code == 422
    assert client.post("/api/agent/ask", json={"text": "a" * 1501}).status_code == 422


def test_new_tools_serialize_on_empty_stores():
    tools = main._deepseek_tools()
    json.dumps(tools["portafoglio_top50"][1](), default=str)
    json.dumps(tools["layer_engine"][1](), default=str)


def test_speak_without_installed_voice_is_503(client, tmp_path, monkeypatch):
    from app.notify import voice
    monkeypatch.setattr(voice, "VOICES_DIR", tmp_path / "none")
    assert client.post("/api/agent/speak", json={"text": "ciao"}).status_code == 503


def test_speak_returns_wav(client, monkeypatch):
    from app.notify import voice

    async def _speak(text, lang="it"):
        return b"RIFFfake"
    monkeypatch.setattr(voice, "speak", _speak)
    r = client.post("/api/agent/speak", json={"text": "ciao", "lang": "it"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav" and r.content == b"RIFFfake"


def test_app_guide_explains_without_secret_modules():
    from app.notify import app_guide
    files = {e["file"] for e in app_guide.index()}
    assert "trading/onchain/system.py" in files
    assert not any(f in files for f in ("auth.py", "config.py", "trading/crypto.py", "trading/onchain/keys.py"))
    out = main._deepseek_tools()["come_funziona"][1](query="trend EMA")
    assert out["passages"] and len(json.dumps(out)) < 8000


def test_carlo_introduces_himself_only_at_the_start(client, monkeypatch):
    monkeypatch.setattr(main.deepseek_desk, "_memory", {})
    client.post("/api/agent/ask", json={"text": "ciao"})
    assert "Ti chiami Carlo" in client.seen["context"]
    main.deepseek_desk._memory[f"web:{client.user_id}"] = [{"role": "user", "content": "ciao"}]
    client.post("/api/agent/ask", json={"text": "e la top 50?"})
    assert "Ti chiami Carlo" not in client.seen["context"]
