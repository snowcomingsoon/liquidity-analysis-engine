"""The last 24 hours' highs of every token the live market loop reads, and
the crash rule built on them.

Lorenzo, 20/10, after BORLY (first in the Top, a rug within hours, still in
his Top when it was worth $3k): "Noi dobbiamo assolutamente evitare queste
situazioni". A token whose price fell by three quarters from its high of the last
24 hours (by half until 21/10), or whose liquidity halved, leaves at once - whatever hold or band
would keep it - and the Top's followers are told.

Hourly buckets of the highest market cap and liquidity seen (from
leaderboard.apply_live, every minute); a crash counts only once two readings
at least CONFIRM_S apart agree, so one bad answer from DexScreener moves
nothing.
"""
from __future__ import annotations

import json
import logging
import time

from app.atomic_write import write_text_atomic
from app.trading.onchain import storage

logger = logging.getLogger(__name__)

_FILE = storage.data_file("onchain_market_peaks.json")
HOUR = 3600
WINDOW_H = 24
# Lorenzo, 21/10: the price threshold up from -50% to -75% ("l'alzerei intorno
# al 75%"). Liquidity stays at -50%: an AMM pool's value moves with the square
# root of the price, so -50% of liquidity is a -75% price move already, and a
# rug (liquidity pulled) goes far past both.
PRICE_DROP = 0.25           # price (cap) at a quarter of its 24h high, or under
LIQ_DROP = 0.5              # liquidity at half its 24h high, or under
CONFIRM_S = 120             # two readings this far apart, both crashed
SAVE_EVERY_S = 300
BLOCK_S = 7 * 86400         # a crashed token stays out this long, even once its highs roll off

_peaks: dict[str, dict[str, list[float]]] = {}   # key -> hour -> [cap_max, liq_max]
_last: dict[str, dict] = {}                      # key -> {"cap", "liq", "at"}
_crash_since: dict[str, float] = {}              # key -> first crashed reading
_down: dict[str, dict] = {}                      # key -> {"at", "why"} of a confirmed crash
_state = {"loaded": False, "saved_at": 0.0, "dirty": False}


def _load() -> None:
    if _state["loaded"]:
        return
    _state["loaded"] = True
    try:
        raw = json.loads(_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    _peaks.update(raw.get("peaks") or {})
    _last.update(raw.get("last") or {})
    _crash_since.update(raw.get("crash_since") or {})
    _down.update(raw.get("down") or {})


def save(now: float | None = None, force: bool = False) -> None:
    now = now or time.time()
    if not _state["dirty"] or (not force and now - _state["saved_at"] < SAVE_EVERY_S):
        return
    _state["saved_at"] = now
    try:
        write_text_atomic(_FILE, json.dumps({"peaks": _peaks, "last": _last, "crash_since": _crash_since, "down": _down}),
                          encoding="utf-8")
        _state["dirty"] = False
    except OSError:
        logger.exception("market peaks not saved")


def reset_for_tests() -> None:
    _peaks.clear()
    _last.clear()
    _crash_since.clear()
    _down.clear()
    _state.update(loaded=True, saved_at=0.0, dirty=False)


def record(key: str, cap: float | None, liq: float | None, now: float | None = None) -> None:
    """One reading of the token's deepest pool."""
    _load()
    now = now or time.time()
    hour = int(now // HOUR)
    buckets = _peaks.setdefault(key, {})
    b = buckets.setdefault(str(hour), [0.0, 0.0])
    b[0] = max(b[0], float(cap or 0))
    b[1] = max(b[1], float(liq or 0))
    for h in [h for h in buckets if int(h) <= hour - WINDOW_H]:
        del buckets[h]
    _last[key] = {"cap": float(cap or 0), "liq": float(liq or 0), "at": now}
    why = _crash_now(key)
    if why:
        since = _crash_since.setdefault(key, now)
        if now - since >= CONFIRM_S and key not in _down:
            _down[key] = {"at": now, "why": why}
    else:
        _crash_since.pop(key, None)
    for k in [k for k, d in _down.items() if now - d["at"] >= BLOCK_S]:
        del _down[k]
    _state["dirty"] = True


def _highs(key: str) -> tuple[float, float]:
    buckets = (_peaks.get(key) or {}).values()
    return max((b[0] for b in buckets), default=0.0), max((b[1] for b in buckets), default=0.0)


def _crash_now(key: str) -> str:
    last = _last.get(key)
    if not last:
        return ""
    cap_hi, liq_hi = _highs(key)
    if cap_hi > 0 and last["cap"] > 0 and last["cap"] <= cap_hi * PRICE_DROP:
        return f"price down {1 - last['cap'] / cap_hi:.0%} from its 24h high"
    if liq_hi > 0 and last["liq"] <= liq_hi * LIQ_DROP:
        return f"liquidity down {1 - last['liq'] / liq_hi:.0%} from its 24h high"
    return ""


def crashed(key: str, now: float | None = None) -> str:
    """The reason when the token crashed in the last BLOCK_S (confirmed by two
    readings CONFIRM_S apart), else ""."""
    _load()
    now = now or time.time()
    d = _down.get(key)
    if not d or now - d["at"] >= BLOCK_S:
        return ""
    return f"crashed: {d['why']}"


def new_crashes(since: float) -> list[str]:
    """Keys whose crash was confirmed at or after `since`."""
    _load()
    return [k for k, d in _down.items() if d["at"] >= since]
