"""API keys of outside services, set by an admin from the site.

Lorenzo, 20/10, with a free Groq key for the gems' veto: the GitHub
settings and the Hetzner console would not open from his phone, and the
repo is public, so the key can travel neither in git nor in a workflow.
Diagnostics has a field for it (admins only); the key is sealed with the
server's own secret (auth.seal_service_key) and kept on the data volume,
never in the repo. An environment variable of the same name still works
and wins, for a server set up by hand.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import httpx

from app import auth
from app.atomic_write import write_text_atomic

logger = logging.getLogger(__name__)

_FILE = Path(__file__).resolve().parent.parent / "data" / "service_keys.json"
# name -> (environment variable, a cheap authenticated call that proves the key works)
SERVICES = {
    "groq": ("GROQ_API_KEY", "https://api.groq.com/openai/v1/models"),
    # Google's OpenAI-compatible endpoint takes the key as a bearer token too.
    "gemini": ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/models"),
}


def _read() -> dict:
    try:
        raw = json.loads(_FILE.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def get(name: str) -> str:
    env, _ = SERVICES[name]
    if os.environ.get(env):
        return os.environ[env]
    rec = _read().get(name) or {}
    return auth.unseal_service_key(rec["sealed"]) if rec.get("sealed") else ""


def status() -> dict:
    """What the page may show: set or not, where from, the last 4 characters."""
    out = {}
    stored = _read()
    for name, (env, _) in SERVICES.items():
        key = get(name)
        rec = stored.get(name) or {}
        out[name] = {"set": bool(key), "last4": key[-4:] if key else None,
                     "source": "env" if os.environ.get(env) else ("site" if key else None),
                     "at": rec.get("at")}
    return out


async def check(name: str, key: str) -> str:
    """"" when the service accepts the key, the reason otherwise."""
    _, url = SERVICES[name]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {key}"})
    except httpx.HTTPError as exc:
        return f"the service did not answer ({type(exc).__name__})"
    if r.status_code == 200:
        return ""
    if r.status_code in (401, 403):
        return "the service refused the key: check that it was copied whole"
    return f"the service answered {r.status_code}"


def save(name: str, key: str, now: float | None = None) -> None:
    data = _read()
    data[name] = {"sealed": auth.seal_service_key(key), "at": now or time.time()}
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(_FILE, json.dumps(data), encoding="utf-8")


def clear(name: str) -> None:
    data = _read()
    if data.pop(name, None) is not None:
        write_text_atomic(_FILE, json.dumps(data), encoding="utf-8")
