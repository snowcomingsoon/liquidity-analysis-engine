"""Whitekobra's Quality list: the excellent projects he picks by hand.

Lorenzo, 21/10, after DREGG: "una nuova sezione che si potrebbe chiamare
quality [...] progetti di alta qualita', quelli che magari raggiungono una
quota di 80% o piu' [...] valutare manualmente e decidere poi con un
pulsante se accettarli all'interno delle gemme oppure scartarli". Then:
only projects not in his Top 25, and once accepted "se poi non dovessero
rispettare i parametri che caratterizzano tutte le gemme [...] escono".

So the list shows every project whose quality (depth.overall) is at least
QUALITY_MIN, whatever its score or usage. Accepting one lifts only the
score's bars (the gem view's 60 and the pillar floors that keep it off the
board): every other rule of the gems still holds, crash first, and a
project failing one stays out until it passes again. Discarding hides it.
Only his account sees the list (settings.onchain_full_score_emails).
"""
from __future__ import annotations

import json
import logging
import time

from app.atomic_write import write_text_atomic
from app.trading.onchain import projects_db, storage

logger = logging.getLogger(__name__)

_FILE = storage.data_file("onchain_quality_picks.json")
QUALITY_MIN = 80
ACTIONS = ("accept", "discard", "reset")

_picks: dict[str, dict] = {}      # projects_db.key -> {"state", "at", "symbol"}
_state = {"loaded": False}


def _load() -> None:
    if _state["loaded"]:
        return
    _state["loaded"] = True
    try:
        _picks.update(json.loads(_FILE.read_text(encoding="utf-8")).get("picks") or {})
    except (OSError, ValueError):
        pass


def _save() -> None:
    try:
        write_text_atomic(_FILE, json.dumps({"picks": _picks}), encoding="utf-8")
    except OSError:
        logger.exception("quality picks not saved")


def reset_for_tests() -> None:
    _picks.clear()
    _state["loaded"] = True


def key(chain: str, token: str) -> str:
    return projects_db.key(chain or "", token or "")


def state(chain: str, token: str) -> str | None:
    _load()
    return (_picks.get(key(chain, token)) or {}).get("state")


def accepted() -> set[str]:
    _load()
    return {k for k, p in _picks.items() if p.get("state") == "accepted"}


def is_accepted(chain: str, token: str) -> bool:
    return state(chain, token) == "accepted"


def picks() -> dict[str, dict]:
    _load()
    return dict(_picks)


def decide(chain: str, token: str, action: str, symbol: str | None = None, now: float | None = None) -> str | None:
    """accept, discard, or reset (back to the list). Returns the new state."""
    if action not in ACTIONS:
        raise ValueError(action)
    _load()
    k = key(chain, token)
    if action == "reset":
        _picks.pop(k, None)
    else:
        _picks[k] = {"state": "accepted" if action == "accept" else "discarded",
                     "at": now or time.time(), "symbol": symbol}
    _save()
    return (_picks.get(k) or {}).get("state")


def quality(e: dict) -> float | None:
    """The project's quality (depth.overall), None when fatal or not read."""
    o = e.get("overall") or {}
    if o.get("fatal") or o.get("score") is None:
        return None
    return float(o["score"])
