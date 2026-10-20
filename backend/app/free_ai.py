"""The free AI that does DeepSeek's research work: Groq first, Gemini next.

Lorenzo, 20/10: "le opzioni che avevamo per analizzare le gemme dove era
attivo DeepSeek, come ad esempio la scansione manuale o la rescansione con
DeepSeek, vanno tutte risistemate e fatte fare a Groq oppure a Gemini".
DeepSeek has been off for the research since 10/10 (cost); the free keys
are set from Diagnostics (service_keys.py).

deepseek_desk._post hands every research call here when DeepSeek is off,
and ai_veto calls `post` directly: one OpenAI-shaped request, the same
answer shape back. Free tiers count requests and tokens per model and per
day, so each provider has a list of models, and a model that answers 429
cools down (for the seconds it asks, or until the next UTC day when the
daily quota is gone) while the next one takes the call. Each kind of work
has its own daily cap so the background research never eats what manual
scans and the veto need; a call made inside a manual scan (`manual()`)
skips the caps.
"""
from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import time

import httpx

logger = logging.getLogger(__name__)

PROVIDERS = (
    ("groq", "https://api.groq.com/openai/v1/chat/completions",
     ("openai/gpt-oss-120b", "meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.3-70b-versatile",
      "openai/gpt-oss-20b")),
    ("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
     ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash")),
)
# Requests a day per kind of work (deepseek_desk.KINDS, plus the veto).
# Manual scans are not counted against these.
DAILY = {"veto": 400, "judge": 120, "research": 120, "code": 40, "scanner": 40, "review": 20,
         "narratives": 20, "consistency": 10, "study": 5}
DAILY_DEFAULT = 10
WAIT_MAX_S = 20               # a 429 asking for longer moves to the next model
PER_PROVIDER = 2              # calls at once on one provider (free tiers count per minute)

_manual = contextvars.ContextVar("free_ai_manual", default=False)
_cool: dict[str, float] = {}                 # "provider/model" -> usable again at
_calls: dict[str, dict[str, int]] = {}       # day -> kind -> requests
_used: dict[str, dict[str, int]] = {}        # day -> "provider/model" -> answers
_sems: dict[str, asyncio.Semaphore] = {}
_keys_cache: dict = {"at": 0.0, "keys": {}}


class Unavailable(RuntimeError):
    """No free provider could take the call (no key, caps spent, all cooling)."""


def reset_for_tests() -> None:
    _cool.clear()
    _calls.clear()
    _used.clear()
    _sems.clear()
    _keys_cache.update(at=time.time(), keys={})


def manual():
    """`with free_ai.manual():` around a manual scan: its calls skip the daily caps."""
    class _Ctx:
        def __enter__(self):
            self.token = _manual.set(True)

        def __exit__(self, *exc):
            _manual.reset(self.token)
    return _Ctx()


def keys() -> dict[str, str]:
    now = time.time()
    if now - _keys_cache["at"] > 60:
        from app import service_keys
        _keys_cache.update(at=now, keys={n: k for n in ("groq", "gemini") if (k := service_keys.get(n))})
    return _keys_cache["keys"]


def available() -> bool:
    return bool(keys())


def _day(now: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(now))


def _next_day(now: float) -> float:
    return (int(now // 86400) + 1) * 86400 + 60


def allowed(kind: str, now: float | None = None) -> bool:
    if _manual.get():
        return True
    now = now or time.time()
    return (_calls.get(_day(now)) or {}).get(kind, 0) < DAILY.get(kind, DAILY_DEFAULT)


def status(now: float | None = None) -> dict:
    now = now or time.time()
    d = _day(now)
    return {"providers": sorted(keys()), "calls_today": dict(_calls.get(d) or {}),
            "answers_today": dict(_used.get(d) or {}),
            "cooling": {m: round(t - now) for m, t in _cool.items() if t > now}}


def _body_for(body: dict, provider: str, model: str) -> dict:
    out = {k: v for k, v in body.items() if k != "model"}
    out["model"] = model
    if provider == "groq" and model.startswith("openai/gpt-oss"):
        # A reasoning model: its thinking counts as output. Little of it, and
        # room for it, or the answer is cut short.
        out["reasoning_effort"] = "low"
        out["max_tokens"] = int(body.get("max_tokens") or 1200) + 800
    return out


def _daily_quota(r: httpx.Response) -> bool:
    text = r.text.lower()
    return any(w in text for w in ("per day", "tokens per day", "requests per day", "(tpd)", "(rpd)", "daily"))


async def post(body: dict, *, kind: str, http: httpx.AsyncClient | None = None, now: float | None = None) -> dict:
    """One chat call on the first free model that answers; OpenAI-shaped
    data back, with "provider" and "model" added. Raises Unavailable."""
    ks = keys()
    if not ks:
        raise Unavailable("no free AI key set (Diagnostics)")
    now = now or time.time()
    if not allowed(kind, now):
        raise Unavailable(f"daily cap of {DAILY.get(kind, DAILY_DEFAULT)} reached for {kind}")
    day = _day(now)
    _calls.setdefault(day, {})[kind] = _calls.get(day, {}).get(kind, 0) + 1
    own = http is None
    client = http or httpx.AsyncClient(timeout=60.0)
    try:
        for provider, url, models in PROVIDERS:
            if provider not in ks:
                continue
            sem = _sems.setdefault(provider, asyncio.Semaphore(PER_PROVIDER))
            for model in models:
                tag = f"{provider}/{model}"
                if _cool.get(tag, 0) > time.time():
                    continue
                for attempt in (1, 2):
                    try:
                        async with sem:
                            r = await client.post(url, json=_body_for(body, provider, model), timeout=60.0,
                                                  headers={"Authorization": f"Bearer {ks[provider]}"})
                    except httpx.HTTPError as exc:
                        logger.info("free ai: %s did not answer: %s", tag, exc)
                        _cool[tag] = time.time() + 60
                        break
                    if r.status_code == 429:
                        try:
                            wait = float(r.headers.get("retry-after") or 0)
                        except ValueError:
                            wait = 0.0
                        if _daily_quota(r):
                            _cool[tag] = _next_day(time.time())
                            break
                        if attempt == 1 and 0 < wait <= WAIT_MAX_S:
                            await asyncio.sleep(wait)
                            continue
                        _cool[tag] = time.time() + max(wait, 60)
                        break
                    gone = r.status_code == 404 or (r.status_code == 400 and "model" in r.text.lower() and any(
                        w in r.text.lower() for w in ("decommission", "not found", "does not exist", "not supported")))
                    if gone:
                        _cool[tag] = _next_day(time.time())     # retired or unknown here: the next model
                        break
                    if r.status_code >= 500:
                        _cool[tag] = time.time() + 60
                        break
                    if r.status_code != 200:
                        logger.info("free ai: %s answered %s: %s", tag, r.status_code, r.text[:200])
                        break
                    try:
                        data = r.json()
                    except ValueError:
                        break
                    _used.setdefault(day, {})[tag] = _used.get(day, {}).get(tag, 0) + 1
                    data["provider"], data["model"] = provider, model
                    return data
    finally:
        if own:
            await client.aclose()
    raise Unavailable("every free model refused or is cooling down")


def content(data: dict) -> str:
    message = ((data.get("choices") or [{}])[0].get("message") or {})
    text = message.get("content") or ""
    if message.get("tool_calls"):
        text += json.dumps(message["tool_calls"], sort_keys=True)
    return text
