"""Outside-service keys set from Diagnostics (service_keys.py, Lorenzo 20/10)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth, config, main, service_keys


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "_USERS_FILE", tmp_path / "users.json")
    monkeypatch.setattr(service_keys, "_FILE", tmp_path / "service_keys.json")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
    auth._users.clear()
    user = auth.create_user("admin@example.com", "correct-horse-battery-9")
    main.app.dependency_overrides[auth.get_current_user] = lambda: auth.get_user(user.id)
    with TestClient(main.app) as c:
        c.user_email = user.email
        yield c
    main.app.dependency_overrides.clear()


def test_only_admins_see_or_set_keys(client, monkeypatch):
    monkeypatch.setattr(config.settings, "admin_emails", "someone-else@example.com")
    monkeypatch.setattr(config.settings, "service_keys_emails", "someone-else@example.com")
    assert client.get("/api/admin/service-keys").status_code == 403
    assert client.post("/api/admin/service-keys", json={"name": "groq", "value": "gsk_x"}).status_code == 403


def test_a_checked_key_is_sealed_on_disk_and_shown_by_its_last_4(client, monkeypatch, tmp_path):
    monkeypatch.setattr(config.settings, "admin_emails", client.user_email)
    seen = []

    async def ok(name, key):
        seen.append(key)
        return ""
    monkeypatch.setattr(service_keys, "check", ok)
    r = client.post("/api/admin/service-keys", json={"name": "groq", "value": " gsk_secret1234 "})
    assert r.status_code == 200 and r.json()["groq"] == {"set": True, "last4": "1234", "source": "site",
                                                          "at": r.json()["groq"]["at"]}
    assert seen == ["gsk_secret1234"] and service_keys.get("groq") == "gsk_secret1234"
    assert "gsk_secret1234" not in (tmp_path / "service_keys.json").read_text()
    assert client.post("/api/admin/service-keys", json={"name": "groq", "value": ""}).json()["groq"]["set"] is False


def test_a_refused_key_is_not_saved(client, monkeypatch):
    monkeypatch.setattr(config.settings, "admin_emails", client.user_email)

    async def refused(name, key):
        return "the service refused the key: check that it was copied whole"
    monkeypatch.setattr(service_keys, "check", refused)
    r = client.post("/api/admin/service-keys", json={"name": "groq", "value": "gsk_wrong"})
    assert r.status_code == 400 and "refused" in r.json()["detail"]
    assert service_keys.get("groq") == ""
    assert client.post("/api/admin/service-keys", json={"name": "groq", "value": "a b"}).status_code == 400
    assert client.post("/api/admin/service-keys", json={"name": "nope", "value": "x"}).status_code == 400


def test_the_environment_wins(client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_fromenv9999")
    assert service_keys.get("groq") == "gsk_fromenv9999"
    assert service_keys.status()["groq"]["source"] == "env"


def test_the_key_keeper_account_is_not_an_admin_but_may_set_keys(client, monkeypatch):
    """whitekobra holds full access, not the admin role (20/10)."""
    monkeypatch.setattr(config.settings, "admin_emails", "someone-else@example.com")
    monkeypatch.setattr(config.settings, "service_keys_emails", client.user_email)
    assert client.get("/api/admin/service-keys").status_code == 200


def test_gemini_is_a_second_key(client, monkeypatch):
    monkeypatch.setattr(config.settings, "service_keys_emails", client.user_email)

    async def ok(name, key):
        return ""
    monkeypatch.setattr(service_keys, "check", ok)
    r = client.post("/api/admin/service-keys", json={"name": "gemini", "value": "AIzaGemini5678"})
    assert r.json()["gemini"]["last4"] == "5678" and r.json()["groq"]["set"] is False


def test_github_models_is_a_third_key_checked_by_a_real_call(client, monkeypatch):
    """Lorenzo, 21/10: GitHub Models as the reserve after Gemini. Its catalog
    answers without a token, so the check is a one-token call."""
    import asyncio

    import httpx
    seen = []

    def handler(request):
        seen.append((request.method, str(request.url)))
        return httpx.Response(401 if request.headers["Authorization"] == "Bearer bad" else 200, json={})
    real = httpx.AsyncClient
    monkeypatch.setattr(service_keys.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler)))
    assert asyncio.run(service_keys.check("github", "good")) == ""
    assert "refused" in asyncio.run(service_keys.check("github", "bad"))
    assert seen[0] == ("POST", "https://models.github.ai/inference/chat/completions")
    monkeypatch.setattr(config.settings, "service_keys_emails", client.user_email)

    async def ok(name, key):
        return ""
    monkeypatch.setattr(service_keys, "check", ok)
    r = client.post("/api/admin/service-keys", json={"name": "github", "value": "github_pat_abcd9876"})
    assert r.json()["github"]["last4"] == "9876"
