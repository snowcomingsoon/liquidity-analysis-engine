"""Plans: the Gem Finder works for everyone; paying buys a boost.

Lorenzo (25/09): "con il tier free impostiamo un limite di utilizzo [...]
il sistema deve funzionare lo stesso, però per avere il boost [...] bisogna
che paghi, perché le chiamate costano. Sicuramente si potrebbe fare con
Sonnet". Payments are still to be defined: the receiving address comes
later (`settings.payment_address`), and until then an admin assigns plans
by hand.

Two kinds of use, counted per user per day:
- `reads`: a project read on demand by the deterministic reader (free to
  run, but each one hits DexScreener, GeckoTerminal and the project's
  sites, so the free plan has a limit);
- `deep`: the same reading done by Claude Sonnet, which costs money. Only
  paid plans have it, and only when the server has an Anthropic key.
"""
from __future__ import annotations

import json
import time

import httpx

from app.trading.onchain import discovery, legit, research, storage
from app.atomic_write import write_text_atomic

PLANS: dict[str, dict] = {
    "free": {"label": "Free", "reads": 5, "deep": 0, "price_usd_month": 0},
    "boost": {"label": "Boost", "reads": 50, "deep": 10, "price_usd_month": None},
    "pro": {"label": "Pro", "reads": 300, "deep": 60, "price_usd_month": None},
}
DEFAULT_PLAN = "free"

_STORE = storage.data_file("onchain_plans.json")
_state: dict = {"users": {}, "usage": {}}   # email -> plan; "YYYY-MM-DD" -> email -> {reads, deep}



def _free_ai() -> bool:
    """DeepSeek is gone (20/10): the free AI (free_ai.py) does the deep reading."""
    from app import free_ai
    return free_ai.available()

def _load() -> None:
    try:
        raw = json.loads(_STORE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if isinstance(raw, dict):
        _state["users"].update(raw.get("users") or {})
        _state["usage"].update(raw.get("usage") or {})


def _save() -> None:
    _state["usage"] = dict(sorted(_state["usage"].items())[-7:])
    try:
        write_text_atomic(_STORE, json.dumps(_state), encoding="utf-8")
    except OSError:
        pass


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def plan_of(email: str, admin: bool = False) -> str:
    return "pro" if admin else _state["users"].get(email.lower(), DEFAULT_PLAN)


def set_plan(email: str, plan: str) -> None:
    if plan not in PLANS:
        raise ValueError(f"unknown plan {plan}")
    _state["users"][email.lower()] = plan
    _save()


def usage(email: str) -> dict:
    return dict(_state["usage"].get(_today(), {}).get(email.lower(), {"reads": 0, "deep": 0}))


def status(email: str, admin: bool = False) -> dict:
    plan = plan_of(email, admin)
    return {"plan": plan, "limits": PLANS[plan], "used": usage(email), "plans": PLANS,
            "deep_available": bool(legit.settings.anthropic_api_key or _free_ai()),
            "payment_address": legit.settings.payment_address or None}


def allow(email: str, kind: str, admin: bool = False) -> str:
    """"" if the user may, else why not."""
    plan = plan_of(email, admin)
    if kind == "deep" and not (legit.settings.anthropic_api_key or _free_ai()):
        return "deep reading is not available yet"
    limit = PLANS[plan][kind]
    if usage(email).get(kind, 0) >= limit:
        return (f"{PLANS[plan]['label']} plan: {limit} a day, used" if limit
                else "deep reading needs a paid plan")
    return ""


def charge(email: str, kind: str) -> None:
    day = _state["usage"].setdefault(_today(), {})
    u = day.setdefault(email.lower(), {"reads": 0, "deep": 0})
    u[kind] = u.get(kind, 0) + 1
    _save()


async def token_item(chain: str, token: str, client: httpx.AsyncClient) -> dict | None:
    """What the reader needs about any token, from its most liquid pool."""
    try:
        r = await client.get(discovery.DEX_TOKENS.format(chain=chain, addresses=token), timeout=10.0)
        pairs = r.json() if r.status_code == 200 else []
    except (httpx.HTTPError, ValueError):
        return None
    pairs = [p for p in pairs if isinstance(p, dict) and p.get("chainId") == chain]
    if not pairs:
        return None
    best = max(pairs, key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0))
    base = best.get("baseToken") or {}
    links = legit.links_from_dexscreener(best)
    return {"chain": chain, "token_address": base.get("address") or token, "symbol": base.get("symbol") or "",
            "name": base.get("name") or "", "website": legit.pick_website(links["websites"]),
            "websites": links["websites"], "market_cap": float(best.get("marketCap") or best.get("fdv") or 0),
            "liquidity_usd": float((best.get("liquidity") or {}).get("usd") or 0),
            "launched_at": (best.get("pairCreatedAt") or 0) / 1000 or None, "pair_url": best.get("url")}


async def read_project(email: str, chain: str, token: str, *, deep: bool = False, admin: bool = False) -> dict:
    """One project read on demand, counted against the user's plan."""
    kind = "deep" if deep else "reads"
    why = allow(email, kind, admin)
    if why:
        return {"ok": False, "error": why, **status(email, admin)}
    async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
        item = await token_item(chain, token, client)
        if item is None:
            return {"ok": False, "error": "token not found on DexScreener"}
        item["boost"] = deep
        pillar, _ = await research.analyze(item, client, item.get("launched_at"))
    charge(email, kind)
    item.pop("boost", None)
    return {"ok": True, "project": item, "research": pillar, **status(email, admin)}


_load()
