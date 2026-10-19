"""Every GeckoTerminal request of the app goes through here (Lorenzo, 19/10:
"coordinando prima tutte le richieste GeckoTerminal").

GeckoTerminal's free API answers 429 past a limit it does not publish
(about 10 a minute measured on 19/10, ~30 documented earlier), and
the charts, the backtests, the usage measure, discovery, the scanners and
the price fallbacks all ask it. Until 19/10 only part of them shared a
limiter (providers/dexscreener.gecko_get, usage._gecko): the others paced
themselves with local sleeps, which are no limit when they run side by side.

What this module owns, for the whole process:
- one window of the requests sent in the last minute: background callers
  stop at BACKGROUND_SHARE of the learned limit, urgent ones (someone
  waiting on a chart, `urgent` context) at the limit, the same window:
  urgent capacity is part of the ceiling, never added to it (caps(),
  following the share of 429s);
- a cooldown after a 429, as long as its Retry-After (DEFAULT_COOLDOWN_S
  without one), that every caller waits out;
- counters per caller: requests, 429s, other errors, time spent waiting,
  cache hits reported by the callers that cache.

It sends one request per call and never retries: the callers keep their
own retry policy (gecko_get, usage._gecko, the scanner), so no level piles
retries on another. It returns httpx's Response as is, so every caller
keeps its parsing and its contract.

One process: the app runs a single uvicorn worker (Dockerfile CMD), so an
in-memory window is the global one. A second worker or replica would need
a shared limiter; until then GeckoTerminal has a single owner, this module.
"""
from __future__ import annotations

import asyncio
import contextvars
import email.utils
import json
import logging
import time
from pathlib import Path
from collections import deque

import httpx

logger = logging.getLogger(__name__)

WINDOW_S = 60.0
# The ceiling is learned, not assumed (19/10): at 13 requests a minute, under
# the old fixed 28, GeckoTerminal refused 30 of 84 (36%); dropping by a quarter
# on every 429 then sank it to 5 a minute, where it still refused 5% and the
# answers fell from 8.3 to 3.9 a minute. A few 429s are GeckoTerminal's
# noise: the limit follows the share of 429s over the last RATE_WINDOW_S,
# down when it passes LOWER_ABOVE, up one step when it stays under RAISE_BELOW.
GLOBAL_PER_MIN = 28          # never above this
MIN_PER_MIN = 8              # never below this
START_PER_MIN = 12           # where a restart begins
RAISE_EVERY_S = 120.0        # at most one step up per this
LOWER_EVERY_S = 60.0         # at most one step down per this
RATE_WINDOW_S = 300.0
LOWER_ABOVE, RAISE_BELOW = 0.15, 0.05
MIN_SAMPLE = 10              # answers in the window before the share means anything
BACKGROUND_SHARE = 0.6       # of the limit the background may use: the rest waits for a person
BACKGROUND_PER_MIN = round(GLOBAL_PER_MIN * BACKGROUND_SHARE)    # at the top of the range
DEFAULT_COOLDOWN_S = 5.0     # a 429 without Retry-After
MAX_COOLDOWN_S = 120.0       # a Retry-After beyond this is read as a mistake, not a two-hour ban
MAX_WAIT_STEP_S = 5.0

urgent: contextvars.ContextVar[bool] = contextvars.ContextVar("gecko_urgent", default=False)
calls: deque[float] = deque()            # monotonic times of the requests in the window
_state = {"cooldown_until": 0.0, "limit": float(START_PER_MIN), "changed_at": 0.0}
answers: deque[tuple[float, bool]] = deque()     # (monotonic time, was a 429) of the last RATE_WINDOW_S
_metrics: dict[str, dict[str, float]] = {}
_started = time.time()


def reset_for_tests() -> None:
    _saved["at"] = 0.0
    calls.clear()
    answers.clear()
    _state.update(cooldown_until=0.0, limit=float(START_PER_MIN), changed_at=0.0)
    _metrics.clear()


def refused_share(now: float | None = None) -> tuple[float, int]:
    """(share of 429s, answers) over the last RATE_WINDOW_S."""
    now = time.monotonic() if now is None else now
    while answers and now - answers[0][0] > RATE_WINDOW_S:
        answers.popleft()
    n = len(answers)
    return (sum(1 for _, r in answers if r) / n if n else 0.0), n


def caps(now: float | None = None) -> tuple[int, int]:
    """(background, urgent) requests a minute allowed now, the limit moved
    by the share of 429s: down 15% past LOWER_ABOVE, up one under RAISE_BELOW."""
    now = time.monotonic() if now is None else now
    if not _state["changed_at"]:
        _state["changed_at"] = now
    share, n = refused_share(now)
    since = now - _state["changed_at"]
    if n >= MIN_SAMPLE and share > LOWER_ABOVE and since >= LOWER_EVERY_S:
        _state.update(limit=max(float(MIN_PER_MIN), _state["limit"] * 0.85), changed_at=now)
    elif share < RAISE_BELOW and since >= RAISE_EVERY_S and _state["limit"] < GLOBAL_PER_MIN:
        _state.update(limit=min(float(GLOBAL_PER_MIN), _state["limit"] + 1), changed_at=now)
    limit = int(_state["limit"])
    return max(1, round(limit * BACKGROUND_SHARE)), limit


def load() -> int:
    """Requests sent in the last minute."""
    now = time.monotonic()
    while calls and now - calls[0] > WINDOW_S:
        calls.popleft()
    return len(calls)


def _m(caller: str) -> dict[str, float]:
    return _metrics.setdefault(caller, {"requests": 0, "http_429": 0, "errors": 0, "wait_s": 0.0,
                                        "max_wait_s": 0.0, "cache_hits": 0})


def cache_hit(caller: str) -> None:
    _m(caller)["cache_hits"] += 1


async def slot(caller: str = "other") -> float:
    """Waits for room in the window and for the cooldown; returns the
    seconds waited. Takes the slot (the request is counted when it leaves)."""
    t0 = time.monotonic()
    while True:
        now = time.monotonic()
        cool = _state["cooldown_until"] - now
        if cool > 0:
            await asyncio.sleep(min(cool, MAX_WAIT_STEP_S))
            continue
        background, top = caps(now)
        cap = top if urgent.get() else background
        while calls and now - calls[0] > WINDOW_S:
            calls.popleft()
        if len(calls) < cap:
            calls.append(now)
            break
        await asyncio.sleep(min(WINDOW_S - (now - calls[0]) + 0.05, MAX_WAIT_STEP_S))
    waited = time.monotonic() - t0
    m = _m(caller)
    m["wait_s"] += waited
    m["max_wait_s"] = max(m["max_wait_s"], waited)
    return waited


def retry_after_s(resp: httpx.Response) -> float:
    """Seconds asked by a 429's Retry-After (seconds or an HTTP date)."""
    raw = (resp.headers.get("retry-after") or "").strip()
    if not raw:
        return DEFAULT_COOLDOWN_S
    try:
        s = float(raw)
    except ValueError:
        try:
            s = email.utils.parsedate_to_datetime(raw).timestamp() - time.time()
        except (TypeError, ValueError, OverflowError):
            return DEFAULT_COOLDOWN_S
    return max(0.0, min(s, MAX_COOLDOWN_S))


def note_response(resp: httpx.Response, caller: str) -> None:
    answers.append((time.monotonic(), resp.status_code == 429))
    if resp.status_code == 429:
        _m(caller)["http_429"] += 1
        until = time.monotonic() + retry_after_s(resp)
        if until > _state["cooldown_until"]:
            _state["cooldown_until"] = until
            logger.info("GeckoTerminal 429 (%s): every caller waits %.0fs", caller, until - time.monotonic())
    elif resp.status_code >= 500:
        _m(caller)["errors"] += 1


async def request(client: httpx.AsyncClient, url: str, *, caller: str, params: dict | None = None,
                  headers: dict | None = None, timeout: float | None = None) -> httpx.Response:
    """One GeckoTerminal GET through the shared window. Raises what httpx
    raises (a timeout, a connection error), counted as an error."""
    await slot(caller)
    _m(caller)["requests"] += 1
    kwargs: dict = {}
    if params is not None:
        kwargs["params"] = params
    if headers is not None:
        kwargs["headers"] = headers
    if timeout is not None:
        kwargs["timeout"] = timeout
    try:
        resp = await client.get(url, **kwargs)
    except Exception:
        _m(caller)["errors"] += 1
        raise
    note_response(resp, caller)
    return resp


def metrics() -> dict:
    """Counters since the process started, by caller, and the window now."""
    rows = {k: {**v, "wait_s": round(v["wait_s"], 1), "max_wait_s": round(v["max_wait_s"], 1)}
            for k, v in sorted(_metrics.items())}
    total = {f: sum(r[f] for r in _metrics.values()) for f in ("requests", "http_429", "errors", "cache_hits")}
    ohlcv = sum(v["requests"] for k, v in _metrics.items() if k.startswith("ohlcv"))
    background, top = caps()
    share, n = refused_share()
    return {"since": _started, "window_now": load(), "global_per_min": top,
            "refused_share_5min": round(share, 3), "answers_5min": n,
            "background_per_min": background, "ceiling_per_min": GLOBAL_PER_MIN,
            "cooldown_s": round(max(0.0, _state["cooldown_until"] - time.monotonic()), 1),
            "total": total, "ohlcv_requests": ohlcv, "other_requests": total["requests"] - ohlcv,
            "by_caller": rows}


SAVE_EVERY_S = 300
_saved = {"at": 0.0}


def save(path: Path, now: float | None = None) -> bool:
    """The counters on file every SAVE_EVERY_S, for a read-only look from
    outside the process (the server-read workflow): they live in memory."""
    now = now or time.time()
    if now - _saved["at"] < SAVE_EVERY_S:
        return False
    _saved["at"] = now
    try:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({**metrics(), "saved_at": now}), encoding="utf-8")
        tmp.replace(path)
        return True
    except OSError:
        logger.exception("GeckoTerminal metrics not saved")
        return False
