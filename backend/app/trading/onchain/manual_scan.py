"""Scan one token on request, through everything the system does.

Lorenzo, 27/09: "aggiungiamo anche l'opzione di aggiungere un indirizzo di
un token o il suo ticker che poi va a cercare nel database di DexScreener
con le logiche che abbiamo adesso, cosi' da avere un riepilogo [...]
compresa anche la scansione di DeepSeek e tutto il processo fatto
manualmente su un ticker a scelta".

resolve() finds the most liquid pair on a chain we cover; scan() runs the
listing checks (legit.assess, plus the security check even when the
pipeline would stop earlier on a meme name), the rug memory (similar past
cases, this token's own history) and DeepSeek's judgement, and returns
one summary. Nothing is recorded as an alert.

Lorenzo, 29/09: "lo scanner manuale e' insufficiente e non si e' evoluto
seguendo tutti gli aggiornamenti". A project (not a meme name) is judged by
the Gem Finder, not by the meme listing filter: its board entry or database
row (score, pillars, DeepSeek's verdict and code reading), or a place in the
study queue when it was never met, if the user adds it (`add`). The trend follower's backtest comes from
the strategy lab, or is run now and kept there.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from urllib.parse import quote

import httpx

from app import http_client

from app.config import settings
from app.notify import deepseek_desk
from app.trading.onchain import (ai_scan, alert_track, code_review, depth, judge, leaderboard, legit, outcomes,
                                 projects_db, research, rug_memory, scout_recheck, strategy_lab)

logger = logging.getLogger(__name__)

SEARCH = "https://api.dexscreener.com/latest/dex/search?q={q}"


def looks_like_address(q: str) -> bool:
    return bool(re.fullmatch(r"0x[0-9a-fA-F]{40}|[1-9A-HJ-NP-Za-km-z]{32,48}", q))


def pick(pairs: list[dict], query: str) -> dict | None:
    q = query.strip().lstrip("$")
    ok = [p for p in pairs if p.get("chainId") in legit.CHAIN_LABEL]
    if looks_like_address(q):
        ok = [p for p in ok if (p.get("baseToken") or {}).get("address", "").lower() == q.lower()] or ok
    else:
        ok = [p for p in ok if (p.get("baseToken") or {}).get("symbol", "").upper() == q.upper()] or ok
    if not ok:
        return None
    # The token people trade, then its deepest pool. Liquidity alone picked a
    # copy (HYDX: an Ethereum "Hydrex" with $98M of liquidity and $0.01 of
    # volume beat the real HyperDex on Robinhood, $311k a day).
    liq = lambda p: float((p.get("liquidity") or {}).get("usd") or 0)  # noqa: E731
    vol = lambda p: float((p.get("volume") or {}).get("h24") or 0)  # noqa: E731
    tokens: dict[str, list[dict]] = {}
    for p in ok:
        tokens.setdefault(f"{p.get('chainId')}:{((p.get('baseToken') or {}).get('address') or '').lower()}", []).append(p)
    best = max(tokens.values(), key=lambda ps: (sum(vol(p) for p in ps), max(liq(p) for p in ps)))
    return max(best, key=liq)


def item_of(pair: dict) -> dict:
    base = pair.get("baseToken") or {}
    cap = pair.get("marketCap") or pair.get("fdv")
    return {"chain": pair.get("chainId"), "symbol": base.get("symbol") or "?", "name": base.get("name") or "",
            "token_address": base.get("address") or "", "pair_address": pair.get("pairAddress") or "",
            "pair_url": pair.get("url") or "", "dex": pair.get("dexId") or "",
            "liquidity_usd": float((pair.get("liquidity") or {}).get("usd") or 0),
            "market_cap": float(cap) if cap else None, "price_usd": pair.get("priceUsd"),
            "image": (pair.get("info") or {}).get("imageUrl"),
            "created_at": (pair.get("pairCreatedAt") or 0) / 1000 or None,
            "change_24h": (pair.get("priceChange") or {}).get("h24"),
            "volume_24h": (pair.get("volume") or {}).get("h24")}


async def _security(item: dict, client: httpx.AsyncClient) -> dict:
    addr = item.get("token_address") or ""
    if item["chain"] == "solana":
        return legit.judge_rugcheck(await legit.rugcheck(addr, client))
    if item["chain"] in legit.GOPLUS_CHAIN:
        return legit.judge_goplus(await legit.goplus(item["chain"], addr, client))
    return legit._check("security", "Security", None, "chain not covered")


# outcomes.py labels its verdicts in Italian; the site is in English.
OUTCOME_EN = {"buono": "fine", "crollo": "crashed", "piatto": "flat", "finto": "fake volume"}
BACKTEST_TIMEOUT_S = 25
RECENT_KEEP = 200
# What each scan found, so "add" enters what the server read, never what a client sends.
_recent: dict[str, dict] = {}


def english(text: str) -> str:
    return re.sub(r"\b(" + "|".join(OUTCOME_EN) + r")\b", lambda m: OUTCOME_EN[m.group(1)], text or "")


def clean_flags(ai: dict | None) -> dict | None:
    """DeepSeek sometimes restates the rug memory with its own numbers
    (HYDX: "4/5 similar rugged" next to a memory of 1 rug in 5). The memory
    is shown with the real counts, so its flags about it are dropped."""
    if not ai:
        return ai
    return {**ai, "flags": [f for f in ai.get("flags") or [] if "similar" not in str(f).lower()]}


def about(info: dict | None, socials: list[dict] | None) -> dict:
    """What the project says it is, and who holds it (GeckoTerminal)."""
    info = info or {}
    split = info.get("holders_split") or {}
    try:
        top10 = float(split.get("top_10")) if split.get("top_10") is not None else None
    except (TypeError, ValueError):
        top10 = None
    return {"summary": research.summary_line(info.get("description") or "") or None,
            "holders": info.get("holders"), "top10_pct": top10,
            "socials": [{"type": x.get("type"), "url": x.get("url")} for x in (socials or [])
                        if str(x.get("url") or "").startswith("https://")][:4]}


def _pillars(raw: dict | None) -> dict:
    return {k: (v or {}).get("score") for k, v in (raw or {}).items() if isinstance(v, dict)}


def _judge_view(j: dict | None) -> dict | None:
    if not j or j.get("verdict") is None:
        return None
    return {"verdict": j.get("verdict"), "score": j.get("score"),
            "problems": (j.get("problems") or [])[:2], "strengths": (j.get("strengths") or [])[:2]}


def _code_view(c: dict | None) -> dict | None:
    if not c or c.get("complexity") is None:
        return None
    return {"complexity": c.get("complexity"), "innovation": c.get("innovation"), "summary": c.get("summary")}


def gem_view(item: dict, now: float | None = None) -> dict:
    """What the Gem Finder knows about this project: on the board, in the
    database, or queued now for its first study."""
    chain, token = item["chain"], item["token_address"]
    e = leaderboard._entries.get(projects_db.key(chain, token))
    if e is not None:
        why = leaderboard.qualifies(e, now)
        return {"status": "ranked" if e.get("rank") else "studied", "rank": e.get("rank"),
                "score": round(leaderboard.final_score(e)), "why": why, "pillars": _pillars(e.get("pillars")),
                "judge": _judge_view(e.get("judge")), "code": _code_view(e.get("code"))}
    p = projects_db.get(chain, token)
    if p is not None:
        pl = leaderboard.db_entry(p)["pillars"]
        return {"status": p.get("status") or "new", "rank": p.get("rank"),
                "score": round(p["score"]) if p.get("score") is not None else None, "why": p.get("why") or "",
                "pillars": _pillars(pl), "judge": _judge_view(judge.get(chain, token)),
                "code": _code_view(code_review.get(code_review.repo_of({"pillars": pl})))}
    return {"status": "unknown", "rank": None, "score": None, "why": "", "pillars": {}, "judge": None, "code": None}


def add(chain: str, token: str, now: float | None = None) -> dict:
    """Lorenzo, 29/09: "voglio poter aggiungere manualmente un progetto che
    poi entra eventualmente nel circolo di tutte le nostre logiche". The
    scanned project joins the Gem Finder's working set: pillars, research,
    DeepSeek's judge and code reading, then the board and the strategy lab
    if it earns it. A manual add also lifts an earlier rejection: it gets a
    fresh look, and the same rules decide."""
    item = _recent.get(projects_db.key(chain, token))
    if item is None:
        return {"error": "Scan the token first."}
    if legit._looks_like_meme(item.get("symbol") or "", item.get("name") or ""):
        return {"error": "Meme names are followed by the Meme Sniper, not the Gem Finder."}
    k = projects_db.key(chain, token)
    leaderboard._gone.pop(k, None)
    fresh = leaderboard.add(dict(item), "manual", now)
    projects_db.recheck(chain, token)
    if settings.onchain_nightly_enabled:
        # No tick until 22:00 (nightly.py): the project is studied now.
        leaderboard.analyze_now(chain, token)
    deepseek_desk.note("manual", f"Added {item.get('symbol')} to the Gem Finder by hand",
                       symbol=item.get("symbol"), chain=chain)
    return {"added": True, "new": fresh, "gem": gem_view(item, now)}


_PUBLIC_JUDGE = ("score", "verdict", "problems", "strengths", "admit_reason", "x", "tg")
_PUBLIC_CODE = ("complexity", "innovation", "fork_of", "summary", "strengths", "concerns")


def _slim(entry: dict) -> dict:
    """gemWhy reads a pillar's score and flags only: the facts stay home,
    except what the contracts holding the supply are and when they unlock."""
    unl = (((entry.get("pillars") or {}).get("tokenomics") or {}).get("facts") or {}).get("unlocks") or []
    return {**entry, "unlocks": [u for u in unl if u.get("kind") != "wallet"] or None, "pillars": {k: {"score": (v or {}).get("score"), "flags": (v or {}).get("flags") or []}
                                 for k, v in (entry.get("pillars") or {}).items()}}


async def _timed(coro, what: str):
    try:
        return await asyncio.wait_for(coro, DEEP_TIMEOUT_S)
    except Exception as exc:
        logger.info("manual scan: %s failed: %s", what, exc)
        return None


async def report(item: dict, gem: dict, client: httpx.AsyncClient, step: "Steps",
                 kobra: bool = False) -> dict | None:
    """The Scout's report, as the Top shows it (leaderboard.gemWhy): score,
    pillars, research summary, DeepSeek's verdict, the code reading.
    Lorenzo, 30/09: "nella scansione manuale manca tutta la descrizione che
    solitamente lo scout fa nei progetti [...] della top". A project the
    Gem Finder has not studied gets the same work now: the three pillars,
    then the judge and the code reading, on the Top's own allowance."""
    chain, token = item["chain"], item["token_address"]
    board = leaderboard._entries.get(projects_db.key(chain, token))
    p = projects_db.get(chain, token)
    old = (board if board is not None and board.get("pillars")
           else leaderboard.db_entry(p) if p is not None and p.get("pillars") else None)
    # Always a fresh read: a stored one predates the latest fixes and the
    # site as it is now (Lorenzo, 30/09, HYDX: "placeholder text" and "0%
    # locked" still shown from an old reading). The stored one is the fallback.
    step("pillars", "run")
    base = {**item, "launched_at": item.get("created_at"),
            "websites": _recent.get(projects_db.key(chain, token), {}).get("websites")}
    pillars = await _timed(depth.analyze(base, client), "pillars")
    if pillars:
        e = {**(old or {}), **base, "pillars": pillars, "overall": depth.overall(pillars),
             "rank": (old or {}).get("rank"),
             "github": ((pillars.get("github") or {}).get("facts") or {}).get("url") or (old or {}).get("github")}
        e.setdefault("narratives", [])
        e["why"] = None
        step("pillars", "ok", " · ".join(f"{k} {v.get('score')}" for k, v in pillars.items() if v.get("score") is not None))
    elif old is not None:
        e = {**old, "pillars": dict(old["pillars"])}
        step("pillars", "warn", "live read failed: stored reading")
    else:
        step("pillars", "fail", "site, GitHub and tokenomics did not answer")
        for k in ("report", "code"):
            step(k, "skip")
        return None
    rules_why = leaderboard.qualifies(e) if not e.get("why") else e["why"]
    fatal = (e.get("overall") or {}).get("fatal")
    j = judge.get(chain, token)
    if fatal:
        step("report", "skip", f"stopped: {fatal}")
    elif j and not judge.wants_reading(e, rules_why, fresh=True):
        step("report", "ok", f"{j.get('verdict')} · {j.get('score')}/100")
    else:
        step("report", "run")
        j = await _timed(judge.judge(e, rules_why, priority=True, fresh=True), "judge") or j
        step("report", "skip" if not j else "ok" if j.get("verdict") in ("gem", "watch") else "fail",
             f"{j.get('verdict')} · {j.get('score')}/100" if j else "DeepSeek unavailable")
    e["judge"] = j
    repo = code_review.repo_of(e)
    c = code_review.get(repo)
    if not repo:
        step("code", "skip", "no public code")
    elif c:
        step("code", "ok", f"complexity {c.get('complexity')} · innovation {c.get('innovation')}")
    else:
        step("code", "run")
        c = await _timed(code_review.review(e, client, priority=True), "code review")
        step("code", "ok" if c else "skip",
             f"complexity {c.get('complexity')} · innovation {c.get('innovation')}" if c else "not read")
    e["code"] = c
    rc = await _recheck(e, item, client, step)
    j, c = e["judge"], e["code"]
    # The weights of the arenas this account sees (KOBRA_SCORE_WEIGHTS for whitekobra).
    score = leaderboard.final_score(e, kobra=kobra)
    # The reason is the fresh reading's, not the stored rejection's; then the
    # Top's usage bars, so "would qualify" never hides the $300k floor.
    why = leaderboard.qualifies(e) or leaderboard.usage_gate(e)
    if not why and gem.get("status") == "rejected":
        why = "passes on a fresh reading: study again to enter the board"
    gem.update(score=round(score), why=why,
               pillars=_pillars(e.get("pillars")), judge=_judge_view(j), code=_code_view(c))
    if board is not None:
        out = leaderboard._public(e)
        out["recheck"] = _recheck_public(rc)
        return _slim(out)
    f = ((e.get("pillars") or {}).get("site") or {}).get("facts") or {}
    return _slim({"score": score, "rank": e.get("rank"), "early": False, "pillars": e.get("pillars") or {},
            "summary": f.get("summary") or None, "traction": leaderboard.traction_of(e),
            "judge": {k: j.get(k) for k in _PUBLIC_JUDGE} if j else None,
            "code": {k: c.get(k) for k in _PUBLIC_CODE} if c else None, "review": None,
            "recheck": _recheck_public(rc)})


async def _recheck(e: dict, item: dict, client: httpx.AsyncClient, step: "Steps") -> dict | None:
    """Lorenzo, 30/09: the red points of a project added by hand get a
    second, critical look before they are shown (scout_recheck.py). Only
    the confirmed ones stay in the judge's problems and the pillar flags."""
    step("recheck", "run")
    full = {**item, **_recent.get(projects_db.key(item["chain"], item["token_address"]), {})}
    rc = await _timed(scout_recheck.recheck(e, full, client), "recheck")
    if rc is None:
        rc = scout_recheck.quick(e)
    if rc is None:
        step("recheck", "skip", "nothing red to check")
        return None
    step("recheck", "ok" if not rc["confirmed"] else "warn",
         f"{len(rc['confirmed'])} confirmed · {len(rc['unverified'])} not verified · {len(rc['refuted'])} cleared")
    keep = {p["text"] for p in rc["confirmed"]}
    if e.get("judge"):
        e["judge"] = {**e["judge"], "problems": [p for p in e["judge"].get("problems") or [] if p in keep]}
    e["pillars"] = {k: {**v, "flags": [f for f in (v or {}).get("flags") or [] if f in keep]}
                    for k, v in (e.get("pillars") or {}).items()}
    return rc


def _recheck_public(rc: dict | None) -> dict | None:
    if not rc:
        return None
    pick = lambda xs: [{"text": x["text"], "note": x.get("note") or ""} for x in xs]  # noqa: E731
    return {"unverified": pick(rc["unverified"]), "refuted": pick(rc["refuted"]), "found": rc["found"]}


def backtest_view(r: dict | None) -> dict | None:
    """The strategy lab's result in two lines: the best 5-minute strategy
    and the trend follower on the daily chart, each against holding."""
    if not r:
        return None
    bt = r.get("backtests") or {}
    rows = [x for x in bt.get("rows") or [] if x.get("trades") and x.get("return_pct") is not None]
    best = max(rows, key=lambda x: x["return_pct"]) if rows else None
    daily = r.get("daily") or {}
    drow = (daily.get("rows") or [None])[0]
    out = {"at": r.get("at"), "error": r.get("error"),
           "fast": {**{k: best.get(k) for k in ("label", "return_pct", "trades", "win_rate", "max_dd")},
                    "hold_pct": bt.get("hold_pct")} if best else None,
           "daily": {**{k: drow.get(k) for k in ("label", "return_pct", "trades", "win_rate", "max_dd")},
                     "interval": daily.get("interval"), "hold_pct": daily.get("hold_pct")}
           if drow and drow.get("trades") else None}
    return out if out["fast"] or out["daily"] or out["error"] else None


async def backtest(item: dict, now: float | None = None) -> dict | None:
    """The lab's backtest of this token, run now when it has none."""
    k = strategy_lab.key_of(item["chain"], item["token_address"])
    r = strategy_lab._results.get(k)
    if r is None and strategy_lab.GECKO_NETWORKS.get(item["chain"]):
        e = {k2: item.get(k2) for k2 in ("chain", "token_address", "symbol", "pair_address")}
        try:
            async with http_client.pooled(timeout=15.0) as client:
                r = await asyncio.wait_for(strategy_lab.run_one(client, e, now or time.time()), BACKTEST_TIMEOUT_S)
            if r is not None:
                strategy_lab._save()
        except Exception as exc:
            logger.info("manual scan: backtest of %s failed: %s", item.get("symbol"), exc)
            r = None
    return backtest_view(r)


# The steps a scan goes through, in order, as the scanner sheet lists them
# while it works (Lorenzo, 30/09: "tutti gli step che fa, tutte le cose che
# guarda le voglio vedere scritte"). Only checks that really run: no X.
LISTING_STEPS = ("name", "security", "contract", "socials", "site", "github", "ai")
STEPS = ("pool", *LISTING_STEPS, "holders", "gem", "pillars", "report", "code", "recheck", "memory", "risk", "backtest")
DEEP_TIMEOUT_S = 75        # pillars, judge and code reading: each one, on a slow site or repo


class Steps:
    """Sends each step's state (run, ok, warn, fail, skip) to `emit`."""

    def __init__(self, emit):
        self.emit = emit or (lambda ev: None)
        self.seen: set[str] = set()

    def __call__(self, key: str, state: str, detail: str = "") -> None:
        if state != "run":
            self.seen.add(key)
        self.emit({"step": key, "state": state, "detail": (detail or "")[:120]})

    def check(self, c: dict) -> None:
        """A listing check landed: mark it, start the next one."""
        key = c.get("key")
        if key not in LISTING_STEPS:
            return
        ok = c.get("ok")
        self(key, "ok" if ok is True else "fail" if ok is False else "warn", c.get("detail") or "")
        nxt = [k for k in LISTING_STEPS[LISTING_STEPS.index(key) + 1:] if k not in self.seen]
        if nxt:
            self(nxt[0], "run")

    def skip_listing(self) -> None:
        for k in LISTING_STEPS:
            if k not in self.seen:
                self(k, "skip")


async def scan(query: str, emit=None, kobra: bool = False) -> dict:
    query = (query or "").strip()
    if not query:
        return {"error": "Write a ticker or an address."}
    step = Steps(emit)
    step.emit({"plan": [k for k in STEPS if k != "backtest" or settings.onchain_trading_enabled]})
    deepseek_desk.note("manual", f"Manual scan requested: {query[:40]}")
    step("pool", "run")
    async with httpx.AsyncClient(timeout=15.0, headers={"accept": "application/json"}) as client:
        try:
            r = await client.get(SEARCH.format(q=quote(query)))
            pairs = (r.json() or {}).get("pairs") or [] if r.status_code == 200 else []
        except (httpx.HTTPError, ValueError):
            step("pool", "fail", "DexScreener is not answering")
            return {"error": "DexScreener is not answering, try again."}
        pair = pick(pairs, query)
        if not pair:
            step("pool", "fail", "no pool on our chains")
            return {"error": f"No pool for \"{query}\" on Solana, Robinhood, BSC, Base or Ethereum."}
        item = item_of(pair)
        step("pool", "ok", f"{item['symbol']} on {item['chain']} · {item.get('dex') or 'dex'}")
        links = legit.links_from_dexscreener(pair)
        step("name", "run")
        step("holders", "run")

        async def holders() -> dict:
            info = await research.gecko_info(item["chain"], item["token_address"], client)
            n = (info or {}).get("holders")
            step("holders", "ok" if n else "warn", f"{n:,} holders" if n else "not listed")
            return info

        verdict, info = await asyncio.gather(legit.assess(item, links, client, tap=step.check), holders())
        checks = list(verdict.get("checks") or [])
        if not any(c.get("key") == "security" for c in checks):
            sec = await _security(item, client)
            checks.append(sec)
            step.check(sec)
        step.skip_listing()
    item.update(checks=checks, socials=verdict.get("socials"), website=verdict.get("website"),
                report=verdict.get("report"))
    socials = verdict.get("socials") or links["socials"]
    _recent[projects_db.key(item["chain"], item["token_address"])] = {
        **item, "websites": links["websites"], "socials": socials,
        "website": verdict.get("website") or (links["websites"] or [None])[0],
        "description": (info or {}).get("description") or ""}
    while len(_recent) > RECENT_KEEP:
        _recent.pop(next(iter(_recent)))
    meme = legit._looks_like_meme(item.get("symbol") or "", item.get("name") or "")
    step("gem", "run")
    gem = None if meme else gem_view(item)
    step("gem", "skip" if gem is None else "ok" if gem["status"] == "ranked" else "warn",
         "meme name: Meme Sniper's turf" if gem is None else
         f"ranked #{gem['rank']}" if gem["status"] == "ranked" else
         "not studied yet: studying it now" if gem["status"] == "unknown" else gem["why"] or gem["status"])
    rep = None
    if gem is None:
        for k in ("pillars", "report", "code"):
            step(k, "skip")
    else:
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "Mozilla/5.0 (LiquidityEngine)"}) as client:
            rep = await report(item, gem, client, step, kobra=kobra)
        # A score that would enter the arenas enters the board by itself
        # (Lorenzo, 19/10: the scan said it would make it, the arenas never
        # saw it): the board's own analysis and rules decide from here.
        if gem["status"] in ("unknown", "rejected", "studied") and not gem.get("why") and rep is not None:
            gem["added"] = bool(add(item["chain"], item["token_address"]).get("added"))
    step("memory", "run")
    feats = outcomes.features(item)
    pool = rug_memory.cases()
    step("memory", "ok", english(rug_memory.summary(feats, item["chain"], pool=pool)))
    step("risk", "run")
    if settings.onchain_trading_enabled:
        step("backtest", "run")

    async def risk() -> dict | None:
        out = clean_flags(await ai_scan.judge_one(item, feats, pool, project=not meme))
        step("risk", "skip" if not out else "fail" if out["risk"] >= 60 else "warn" if out["risk"] >= 30 else "ok",
             f"rug risk {out['risk']}" if out else "DeepSeek unavailable")
        return out

    async def bt_step() -> dict | None:
        if not settings.onchain_trading_enabled:
            return None             # no strategies in the app (Lorenzo, 07/10)
        out = await backtest(item)
        best = (out or {}).get("daily") or (out or {}).get("fast")
        step("backtest", "skip" if not best else "ok" if (best.get("return_pct") or 0) >= 0 else "warn",
             f"{best['return_pct']:+.0f}% in {best['trades']} trades" if best else (out or {}).get("error") or "no candles")
        return out

    ai, bt = await asyncio.gather(risk(), bt_step())
    deepseek_desk.note("manual", f"Scanned {item['symbol']}: pipeline {verdict['status']}"
                       + (f", rug risk {ai['risk']}" if ai else ""), symbol=item["symbol"], chain=item["chain"])
    tracked = alert_track._alerts.get(f"meme:{item['chain']}:{item['token_address']}")
    return {"token": {k: item.get(k) for k in ("chain", "symbol", "name", "token_address", "pair_address", "pair_url",
                                               "dex", "liquidity_usd", "market_cap", "price_usd", "image",
                                               "created_at", "change_24h", "volume_24h", "website")},
            "pipeline": {"status": verdict["status"], "reason": verdict.get("reason") or ""},
            "checks": [{k: c.get(k) for k in ("key", "label", "ok", "detail")} for c in checks],
            "report": verdict.get("report"),
            "about": about(info, socials),
            "kind": "meme" if meme else "project", "gem": gem, "backtest": bt, "scout": rep,
            "memory": {"summary": english(rug_memory.summary(feats, item["chain"], pool=pool)),
                       "similar": rug_memory.similar(feats, item["chain"], k=5, pool=pool),
                       "history": rug_memory.lookup(item["token_address"])},
            "ai": ai,
            "alert": {"at": tracked["at"], "now": (tracked.get("last") or {}).get("ret")} if tracked else None}
