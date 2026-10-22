"""/app, the on-chain app rebuilt in React, for settings.onchain_next_emails
only; everyone else is sent to the app they already have."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth, main

_PASSWORD = "app-next-pass-123"


@pytest.fixture
def users(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "_USERS_FILE", tmp_path / "users.json")
    monkeypatch.setattr(main.settings, "onchain_next_emails", "lorenzo@example.com")
    monkeypatch.setattr(main.settings, "onchain_next_for_all", False)
    index = tmp_path / "index.html"
    index.write_text("<head><!--onchain-boot--></head><div id=root></div>", encoding="utf-8")
    monkeypatch.setattr(main, "_NEXT_INDEX", index)
    auth._users.clear()
    auth.create_user("lorenzo@example.com", _PASSWORD)
    auth.create_user("other@example.com", _PASSWORD)
    yield index


def _get(email: str | None):
    with TestClient(main.app) as client:
        if email:
            assert client.post("/api/auth/login", json={"email": email, "password": _PASSWORD}).status_code == 200
        return client.get("/app", follow_redirects=False)


def test_listed_account_gets_the_react_app_with_its_boot_data(users):
    resp = _get("lorenzo@example.com")
    assert resp.status_code == 200
    assert '<script type="application/json" id="onchain-boot">' in resp.text
    assert "<!--onchain-boot-->" not in resp.text


@pytest.mark.parametrize("email", ["other@example.com", None])
def test_anyone_else_goes_to_the_current_app(users, email):
    resp = _get(email)
    assert resp.status_code == 303 and resp.headers["location"] == "/onchain-app.html"


def test_a_missing_build_falls_back_to_the_current_app(users):
    users.unlink()
    assert _get("lorenzo@example.com").status_code == 303


def test_open_to_all_serves_every_account_and_sends_phones_there(users, monkeypatch):
    monkeypatch.setattr(main.settings, "onchain_next_for_all", True)
    assert _get("other@example.com").status_code == 200
    assert _get(None).status_code == 303
    with TestClient(main.app) as client:
        client.post("/api/auth/login", json={"email": "other@example.com", "password": _PASSWORD})
        assert 'location.replace("/app"' in client.get("/onchain-app.html").text


def test_the_allowlist_alone_does_not_redirect_others(users):
    with TestClient(main.app) as client:
        client.post("/api/auth/login", json={"email": "other@example.com", "password": _PASSWORD})
        assert 'location.replace("/app"' not in client.get("/onchain-app.html").text
