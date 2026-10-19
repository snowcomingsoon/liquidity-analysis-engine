"""What the Telegram alerts would have paid: enter when the message arrives.

Request: "il meme sniper deve avere una leaderboard anch'esso, con anche i
risultati se avessimo seguito l'alert di telegram (non le strategie),
semplicemente se fossimo entrati quando arrivava il messaggio di telegram
quanto guadagno ci sarebbe stato [...] le performance del segnale dopo
1,2,3,4,5,6,8,12,24,48h, e infine aggiornato in tempo reale, oltre a questo
anche il rendimento della miglior strategia backtestata".

Every alert sent (a meme listing, a gem entering the board) is written
down once. Its entry is the first pool price read after the message went
out, so the result is what someone tapping the notification could have
had, not the price the scanner saw before vetting. From then on the pool is
read on DexScreener: every SAMPLE_FAST_S for the first two days (the
checkpoints are the first reading past each hour mark), then every
SAMPLE_SLOW_S until KEEP_WATCHING_S, so the "now" column stays live. A pool
that disappears counts as -100%. For memes the best backtested strategy on
the same token (the listing's own backtest) sits next to it.

Plain price change, no fees: the simulated trades with costs are the Meme
Sniper's track record (meme_engine); this is the raw signal.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import time

import httpx

from app.trading.onchain import storage

logger = logging.getLogger(__name__)

_STORE_FILE = storage.data_file("onchain_alert_track.json")
DEX_PAIRS = "https://api.dexscreener.com/latest/dex/pairs/{chain}/{pairs}"
CHECKPOINTS_H = (1, 2, 3, 4, 5, 6, 8, 12, 24, 48)
SAMPLE_FAST_S = 60
SAMPLE_SLOW_S = 15 * 60
FAST_FOR_S = 49 * 3600
KEEP_WATCHING_S = 14 * 86400
GONE_AFTER = 5                    # readings in a row without the pool
KEEP = 3000
KINDS = ("meme", "gem")

_alerts: dict[str, dict] = {}
_state = {"sampled_at": 0.0, "slow_at": 0.0, "bars_saved_at": 0.0}

# 5-minute bars per alert, for the system (system.py): built from the same
# readings as the returns, plus a warm-up fetched once. Kept only while the
# alert's system window is open, in their own file (they are the bulky part).
_BARS_FILE = storage.data_file("onchain_alert_bars.json")
BAR_S = 300
MAX_BARS = 720
_bars: dict[str, list[list]] = {}


def _load() -> None:
    try:
        raw = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(raw, dict):
        _alerts.update({k: v for k, v in (raw.get("alerts") or {}).items() if isinstance(v, dict)})
    from app.trading.onchain.system import LEGACY_LABELS
    for a in _alerts.values():
        sysr = a.get("system")
        if isinstance(sysr, dict):
            for old, new in LEGACY_LABELS.items():
                if old in sysr and new not in sysr:
                    sysr[new] = sysr.pop(old)
    try:
        bars = json.loads(_BARS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        bars = {}
    if isinstance(bars, dict):
        _bars.update({k: v for k, v in bars.items() if isinstance(v, list)})


def _plain(o):
    """numpy scalars from the backtests (a numpy bool summed into an int64
    `wins`) made json.dumps raise TypeError: save() failed on every call, the
    file on disk stayed hours old, and each restart brought back alerts
    without their backtests, rebuilt from fresh candles (FLOOR, CERT, 28/09)."""
    if hasattr(o, "item"):
        return o.item()
    raise TypeError(f"{type(o).__name__} is not JSON serializable")


def save() -> None:
    if len(_alerts) > KEEP:
        for k in sorted(_alerts, key=lambda k: _alerts[k]["at"])[:len(_alerts) - KEEP]:
            del _alerts[k]
    try:
        tmp = _STORE_FILE.with_suffix(_STORE_FILE.suffix + ".tmp")
        tmp.write_text(json.dumps({"alerts": _alerts}, ensure_ascii=False, default=_plain), encoding="utf-8")
        os.replace(tmp, _STORE_FILE)
    except (OSError, TypeError, ValueError):
        logger.exception("alert track: save failed")


def save_bars(now: float | None = None, force: bool = False) -> None:
    now = now or time.time()
    if not force and now - _state["bars_saved_at"] < 300:
        return
    _state["bars_saved_at"] = now
    live = {k: v for k, v in _bars.items() if k in _alerts}
    try:
        tmp = _BARS_FILE.with_suffix(_BARS_FILE.suffix + ".tmp")
        tmp.write_text(json.dumps(live, separators=(",", ":"), default=_plain), encoding="utf-8")
        os.replace(tmp, _BARS_FILE)
    except (OSError, TypeError, ValueError):
        logger.exception("alert track: bars save failed")


def reset_for_tests() -> None:
    _alerts.clear()
    _bars.clear()
    _state.update(sampled_at=0.0, slow_at=0.0, bars_saved_at=0.0)


def key_of(a: dict) -> str:
    return f"{a['kind']}:{a['chain']}:{a.get('token_address') or a['pair_address']}"


def add_bar(k: str, t: float, price: float, volume: float | None = None) -> None:
    """One reading into its 5-minute bar (open/high/low/close; the pool's
    rolling 5-minute volume, read at the bar's last reading)."""
    b0 = int(t // BAR_S * BAR_S)
    rows = _bars.setdefault(k, [])
    if rows and rows[-1][0] == b0:
        r = rows[-1]
        r[2], r[3], r[4] = max(r[2], price), min(r[3], price), price
        if volume is not None:
            r[5] = volume
    elif not rows or rows[-1][0] < b0:
        rows.append([b0, price, price, price, price, volume or 0.0])
        limit = 30000 if (_alerts.get(k) or {}).get("quant_policy") else MAX_BARS
        del rows[:-limit]


def merge_bars(k: str, candles: list) -> None:
    """GeckoTerminal candles [[ts, o, h, l, c, v], ...] into the alert's bars
    (theirs win where both have the same bar: they saw every trade)."""
    have = {r[0]: r for r in _bars.get(k, [])}
    for c in candles or []:
        if len(c) >= 6 and _num(c[4]):
            t = int(float(c[0]))
            have[t] = [t, float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5] or 0)]
    limit = 30000 if (_alerts.get(k) or {}).get("quant_policy") else MAX_BARS
    _bars[k] = sorted(have.values(), key=lambda r: r[0])[-limit:]


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) and f > 0 else None


def facts_of(item: dict) -> str:
    """What the checks found, in one short line: what ai_scan.py reads."""
    checks = "; ".join(f"{c.get('label')}: {'ok' if c.get('ok') else 'no' if c.get('ok') is False else '?'} "
                       f"{(c.get('detail') or '')[:50]}" for c in item.get("checks") or [])
    socials = ",".join(sorted({s.get("type", "") for s in item.get("socials") or []}))
    site = (item.get("website") or "").split("//")[-1].split("/")[0]
    return f"{checks} | social {socials or 'none'} | site {site or 'none'}"[:400]


def record(item: dict, kind: str, now: float | None = None) -> dict | None:
    """An alert just went out. Once per token and kind."""
    if kind not in KINDS or not item.get("chain") or not item.get("pair_address"):
        return None
    now = now or time.time()
    k = f"{kind}:{item['chain']}:{item.get('token_address') or item['pair_address']}"
    if k in _alerts:
        return None
    _alerts[k] = {
        "kind": kind, "chain": item["chain"], "symbol": item.get("symbol") or "?", "name": item.get("name") or "",
        "token_address": item.get("token_address") or "", "pair_address": item["pair_address"],
        "pair_url": item.get("pair_url") or "", "at": now, "cap0": _num(item.get("market_cap")),
        "liq0": _num(item.get("liquidity_usd")), "quoted": _num(item.get("price_usd")),
        "entry": None, "entry_at": None, "returns": {}, "last": None, "max_ret": None, "min_ret": None,
        "misses": 0, "gone": False, "closed": False, "strategy": None, "score": item.get("score"),
        "launched_at": item.get("launched_at"),
        "image": item.get("image") or None, "facts": facts_of(item), "meme": bool(item.get("meme")),
    }
    save()
    return _alerts[k]


def _quant_watching(a: dict, now: float) -> bool:
    first = a.get("quant_observed")
    return bool(a.get("quant_policy") or first and now < first["start"] + 30 * 86400)


def apply_price(a: dict, price, now: float) -> None:
    """One reading of the pool. None = the pool did not answer."""
    if a["closed"]:
        return
    price = _num(price)
    if price is None:
        if a["entry"] is not None:
            a["misses"] += 1
            if a["misses"] >= GONE_AFTER:
                a.update(gone=True, closed=True, last={"ret": -1.0, "at": now})
                for h in CHECKPOINTS_H:
                    a["returns"].setdefault(str(h), -1.0)
        return
    a["misses"] = 0
    if a["entry"] is None:
        a["entry"], a["entry_at"] = price, now
        return
    ret = round(price / a["entry"] - 1, 4)
    a["last"] = {"ret": ret, "at": now, "price": price}
    a["max_ret"] = ret if a["max_ret"] is None else max(a["max_ret"], ret)
    a["min_ret"] = ret if a["min_ret"] is None else min(a["min_ret"], ret)
    age = now - a["entry_at"]
    for h in CHECKPOINTS_H:
        if str(h) not in a["returns"] and age >= h * 3600:
            a["returns"][str(h)] = ret
    if age >= KEEP_WATCHING_S and not _quant_watching(a, now):
        a["closed"] = True


def set_strategy(kind: str, chain: str, token: str, backtest: dict | None) -> None:
    """The best backtested strategy on the same token (the listing's)."""
    a = _alerts.get(f"{kind}:{chain}:{token}")
    if a is None or not backtest or backtest.get("return_pct") is None:
        return
    a["strategy"] = {"label": backtest.get("label"), "name": backtest.get("strategy_name"),
                     "return_pct": backtest.get("return_pct"), "trades": backtest.get("trades"),
                     "interval": backtest.get("interval"), "at": backtest.get("at")}


# ------------------------------------------------------------- history

# Alerts sent before this file existed ("riesci a riportare i dati storici
# che avevamo nell'altra versione?"): the Meme Sniper kept every listing it
# published, with the moment it went out. Their track is rebuilt from the
# pool's own candles on GeckoTerminal, same rules as a live alert: entry is
# the first close at or after the message, each checkpoint is the last close
# at or before the hour mark. No candle after a time means no trade, not a
# vanished pool, so the last price stands.
GECKO_OHLCV = "https://api.geckoterminal.com/api/v2/networks/{net}/pools/{pool}/ohlcv/{tf}"
BACKFILL_GAP_S = 2.1              # GeckoTerminal allows about 30 calls a minute


def from_candles(a: dict, candles: list, now: float, tail: list | None = None) -> None:
    """Fill an alert recorded after the fact. candles: [[ts, o, h, l, c, v], ...]
    from the message onwards (any order); tail: later candles for the "now"."""
    rows = sorted((float(c[0]), float(c[4])) for c in candles or [] if len(c) >= 5 and _num(c[4]))
    rows = [(t, c) for t, c in rows if t >= a["at"] - 300]
    if not rows:
        a.update(closed=True, nodata=True)   # no trade on record: never priced "now" as if it were the entry
        return
    a["entry_at"], a["entry"] = rows[0]
    rets = [(t, round(c / a["entry"] - 1, 4)) for t, c in rows]
    for h in CHECKPOINTS_H:
        mark = a["entry_at"] + h * 3600
        if mark > now:
            break
        before = [r for t, r in rets if t <= mark]
        if before:
            a["returns"][str(h)] = before[-1]
    later = sorted((float(c[0]), float(c[4])) for c in tail or [] if len(c) >= 5 and _num(c[4]))
    last_t, last_c = max(rows[-1], later[-1]) if later else rows[-1]
    all_rets = [r for _, r in rets] + [round(c / a["entry"] - 1, 4) for _, c in later]
    a["last"] = {"ret": round(last_c / a["entry"] - 1, 4), "at": last_t, "price": last_c}
    a["max_ret"], a["min_ret"] = max(all_rets), min(all_rets)
    a["closed"] = now - a["entry_at"] >= KEEP_WATCHING_S
    a["backfilled"] = True


async def _candles(client, net: str, pool: str, tf: str, aggregate: int, before: float, limit: int,
                   token: str = "", source: str = "auto") -> list | None:
    """Candles through the shared GeckoTerminal limiter. [] = the pool is
    unknown there; None = no answer now (try again on the next start).
    `source="gecko"` never asks the candles squid (candle_archive: one
    provider per archived series)."""
    rows, _ = await _candles_from(client, net, pool, tf, aggregate, before, limit, token, source)
    return rows


async def _candles_from(client, net: str, pool: str, tf: str, aggregate: int, before: float, limit: int,
                        token: str = "", source: str = "auto") -> tuple[list | None, str]:
    """The rows and the provider that gave them (candle_source.py routes the
    pools the candles squid covers, by settings.squid_mode)."""
    if net == "cex":
        from app.trading.onchain import cex_candles
        return await cex_candles.candles(pool, tf, aggregate, before, limit), "cex"
    from app.providers import candle_source
    from app.providers.dexscreener import gecko_get

    async def gecko() -> list | None:
        params = {"aggregate": aggregate, "before_timestamp": int(before), "limit": limit, "currency": "usd"}
        if token:
            params["token"] = token     # the token's side of the pool, not always the base
        try:
            payload = await gecko_get(GECKO_OHLCV.format(net=net, pool=pool, tf=tf), params, caller="ohlcv:alerts")
        except Exception:
            return None
        if payload is None:
            return []
        return ((payload.get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []

    tf_s = candle_source.TF_SECONDS.get((tf, int(aggregate)))
    if source != "auto" or candle_source.mode() == "off" or tf_s is None:
        return await gecko(), candle_source.PROVIDER_GECKO
    return await candle_source.route(net, pool, tf, aggregate, token, before - limit * tf_s, before, gecko)


async def backfill(client: httpx.AsyncClient, items: list[dict], kind: str = "meme",
                   now: float | None = None, gap_s: float = BACKFILL_GAP_S) -> int:
    """Record past alerts ({chain, pair_address, at, ...}) and rebuild their
    track from candles. Already-known alerts are left alone."""
    from app.sniper.scanner import GECKO_NETWORKS
    now = now or time.time()
    n = 0
    for item in sorted(items, key=lambda x: x.get("at") or 0):
        net = GECKO_NETWORKS.get(item.get("chain") or "")
        at = _num(item.get("at"))
        if not net or not at:
            continue
        a = record(item, kind, at)
        if a is None:
            continue
        token = item.get("token_address") or ""
        from app.providers import candle_source
        if candle_source.mode() == "off":
            first, provider = await _candles(client, net, item["pair_address"], "minute", 5,
                                             at + (max(CHECKPOINTS_H) + 1) * 3600, 600, token), "geckoterminal"
        else:
            first, provider = await _candles_from(client, net, item["pair_address"], "minute", 5,
                                                  at + (max(CHECKPOINTS_H) + 1) * 3600, 600, token)
        await asyncio.sleep(gap_s)
        tail = None
        if first is not None and now - at > (max(CHECKPOINTS_H) + 1) * 3600:
            if provider == "geckoterminal":
                tail = await _candles(client, net, item["pair_address"], "hour", 4, min(now, at + KEEP_WATCHING_S),
                                      100, token, source="gecko")
            else:
                # One source per alert: the squid's hourly candles, or both stretches from GeckoTerminal.
                tail, tail_from = await _candles_from(client, net, item["pair_address"], "hour", 1,
                                                      min(now, at + KEEP_WATCHING_S), 400, token)
                if tail_from != provider:
                    first = await _candles(client, net, item["pair_address"], "minute", 5,
                                           at + (max(CHECKPOINTS_H) + 1) * 3600, 600, token, source="gecko")
                    tail = await _candles(client, net, item["pair_address"], "hour", 4,
                                          min(now, at + KEEP_WATCHING_S), 100, token, source="gecko")
                    provider = "geckoterminal"
            await asyncio.sleep(gap_s)
        if first is None:
            # GeckoTerminal did not answer: forget it, the next start tries again.
            _alerts.pop(f"{kind}:{item['chain']}:{item.get('token_address') or item['pair_address']}", None)
            continue
        from_candles(a, first, now, tail)
        a["data_provider"] = provider     # which source the returns were measured on
        merge_bars(key_of(a), first)
        a["bars_fetched"] = True
        n += 1
    save()
    save_bars(force=True)
    return n


# ---------------------------------------------------------------- system

SYSTEM_FETCHES_PER_TICK = 15
GEM_GAP_LOOKBACK_S = 24 * 3600      # sampled gem bars checked for holes this far back
GEM_GAP_RETRY_S = 1800              # a hole GeckoTerminal cannot fill is asked again at most this often
# Bump when system.follow's output changes: finished alerts are fetched and
# recomputed once more (v2: each sell says why, "crash" or "signal").
SYSTEM_VERSION = 10  # 8: rug stop with a reason (liquidity pulled, crash, dead, abandoned, on-chain)
# 9: alert_bt, the trend follower entered on the alert itself (every alert has a trade)
# 10: alert_bt closes on the first bar with the trend down (MESUB -95%)


def backtest_status(kind: str = "meme", now: float | None = None) -> dict:
    """How many of this kind's alerts already carry a current backtest."""
    now = now or time.time()
    total = ready = no_data = 0
    oldest = None
    for a in _alerts.values():
        if a["kind"] != kind:
            continue
        total += 1
        if a.get("nodata"):
            no_data += 1
            continue
        if a.get("backtests") is not None and a.get("system_v") == SYSTEM_VERSION:
            ready += 1
            continue
        if oldest is None or a["at"] < oldest:
            oldest = a["at"]
    pending = total - ready - no_data
    return {"total": total, "ready": ready, "pending": pending, "no_data": no_data,
            "oldest_pending_h": round((now - oldest) / 3600, 1) if oldest is not None else None}


def keep_richer(old: dict | None, new: dict) -> dict:
    """The saved backtest unless the new one saw at least as many bars.

    Lorenzo, 28/09: FLOOR was first with +132% and a few seconds later it was
    gone. "Deve rimanere tutto salvato [...] non deve cambiare ogni volta
    risultato e perdere i precedenti". A rebuild after the bars were dropped
    (a finished alert, a new SYSTEM_VERSION) fetches the pool again, and a
    dead pool gives back fewer candles or none: that must not erase a result
    computed on the full window."""
    if old and (old.get("bars") or 0) > (new.get("bars") or 0):
        return {**old, "kept": True}
    return new


async def refresh_system(client, now: float | None = None, gap_s: float = 0.0) -> int:
    """Keep every meme alert's system result current (system.py).

    Bars an alert does not have yet come from GeckoTerminal once, at
    background priority: the whole window for alerts already past it, the
    hours before the message (warm-up) for live ones, whose later bars come
    from the minute readings. Results are recomputed when the bars change;
    once the window is over the result is frozen and the bars dropped."""
    from app.providers.dexscreener import gecko_urgent
    now = now or time.time()
    urgent = backtest_status("meme", now=now)["pending"] > 0
    token = gecko_urgent.set(True) if urgent else None
    try:
        return await _refresh_system(client, now, gap_s)
    finally:
        if token is not None:
            gecko_urgent.reset(token)


def _bar_hole(rows: list, since: float, now: float) -> bool:
    """A closed 5-minute bar missing between `since` and the last closed bar.
    One hole makes a quant research window unusable."""
    first = int(since // BAR_S * BAR_S)
    last = int(now // BAR_S * BAR_S) - BAR_S
    if last < first:
        return False
    have = {r[0] for r in rows if first <= r[0] <= last}
    return len(have) < (last - first) // BAR_S + 1


async def _refresh_system(client, now: float, gap_s: float | None) -> int:
    from app.sniper.scanner import GECKO_NETWORKS
    from app.trading.onchain import outcomes, system, quant_runtime, quant_memory
    reviewed = quant_runtime.approved()
    fetched = changed = 0
    def _ready(a):
        return a.get("backtests") is not None and a.get("system_v") == SYSTEM_VERSION
    for a in sorted(_alerts.values(), key=lambda x: (_ready(x), -x["at"])):
        if a.get("nodata"):
            continue
        first = a.get("quant_observed")
        net = GECKO_NETWORKS.get(a["chain"])
        if (a["kind"] != "meme" and first and net and not a.get("gone") and _quant_watching(a, now)
                and fetched < SYSTEM_FETCHES_PER_TICK and now - a.get("gem_candles_at", 0) >= GEM_GAP_RETRY_S
                and _bar_hole(_bars.get(key_of(a)) or [], max(first["start"], now - GEM_GAP_LOOKBACK_S), now)):
            # Gem bars come from sampling only: a restart or a DexScreener
            # outage leaves holes. GeckoTerminal saw every trade; its candles
            # fill the holes (stored closed bars are never revised).
            a["gem_candles_at"] = now
            got = await _candles(client, net, a["pair_address"], "minute", 5, now,
                                 GEM_GAP_LOOKBACK_S // BAR_S + 12, a.get("token_address") or "", source="gecko")
            fetched += 1
            if got:
                merge_bars(key_of(a), got)
            if gap_s:
                await asyncio.sleep(gap_s)
        try:
            collected = await asyncio.to_thread(quant_memory.capture_case, a, list(_bars.get(key_of(a)) or []), now)
            if collected:
                changed += 1
                if _quant_watching(a, now) and not a.get("gone"):
                    a["closed"] = False
        except Exception:
            logger.exception("quant research collection unavailable")
        # Research-approved path is separate from the frozen legacy backtest.
        if reviewed or a.get("quant_policy"):
            try:
                await asyncio.to_thread(quant_runtime.refresh, a, _bars.get(key_of(a)) or [], now, reviewed)
                changed += 1
            except Exception:
                logger.exception("quant signal evaluation unavailable")
        if a["kind"] != "meme":
            continue
        if a.get("system_done") and a.get("system_v") != SYSTEM_VERSION and fetched < SYSTEM_FETCHES_PER_TICK:
            a.update(system_done=False, bars_fetched=False)      # older result: rebuild it once
        if a.get("system_done"):
            continue
        k = key_of(a)
        if a.get("bars_fetched") and not _bars.get(k) and not a.get("bars_refetched"):
            # Bars lost (a truncated file, a restart): fetch the candles once
            # more. Once only: a dead pool answers [] every time.
            a.update(bars_fetched=False, bars_refetched=True)
        if not a.get("bars_fetched") and fetched < SYSTEM_FETCHES_PER_TICK:
            net = GECKO_NETWORKS.get(a["chain"])
            past = now >= a["at"] + system.WINDOW_S
            before = a["at"] + system.WINDOW_S + 3600 if past else a["at"]
            got = await _candles(client, net, a["pair_address"], "minute", 5, min(before, now), MAX_BARS if past else 72,
                                 a.get("token_address") or "") if net else []
            fetched += 1
            if got is not None:
                merge_bars(k, got)
                a["bars_fetched"] = True
            if gap_s:
                await asyncio.sleep(gap_s)
        bars = _bars.get(k) or []
        sig = f"{len(bars)}:{bars[-1][0] if bars else 0}:{a['gone']}"
        # Unchanged bars skip only a current result: a closed or vanished
        # alert gets no new bars, and without _ready() one computed by an
        # older SYSTEM_VERSION stayed pending until its 48h were over.
        if not a.get("bars_fetched") or (_ready(a) and sig == a.get("system_sig")
                                         and now < a["at"] + system.WINDOW_S):
            continue
        res = await asyncio.to_thread(system.evaluate, bars, a["at"], gone=a["gone"], now=now)
        j = outcomes._journal.get(f"{a['chain']}:{a.get('token_address')}")
        known = ({"at": j["rug_at"], "why": j.get("rug_why") or ""}
                 if j and j.get("rug") and j.get("rug_at") else None)
        a["backtests"] = keep_richer(a.get("backtests"),
                                     await asyncio.to_thread(system.backtest_all, bars, known))
        alert_bt = await asyncio.to_thread(system.evaluate, bars, a["at"], gone=a["gone"], now=now, on_alert=True)
        if a["backtests"].get("kept") and a.get("system"):
            res = a["system"]            # the followed result goes with its bars
            alert_bt = a.get("alert_bt") or alert_bt
        a["alert_bt"] = alert_bt
        a["system"], a["system_sig"], a["system_v"] = res, sig, SYSTEM_VERSION
        changed += 1
        if all(r.get("done") for r in res.values()):
            a["system_done"] = True
            if not _quant_watching(a, now):
                _bars.pop(k, None)
    if changed or fetched:
        save()
        save_bars(now, force=True)
    st = backtest_status("meme", now=now)
    if st["pending"] == 0 and _state.get("bt_pending"):
        logger.info("alert track: backtests complete, %d alerts", st["ready"])
    _state["bt_pending"] = st["pending"]
    return changed


def system_board(kind: str = "meme") -> dict:
    from app.trading.onchain import system
    results = [a["system"] for a in _alerts.values() if a["kind"] == kind and a.get("system")]
    return {**system.scoreboard(results), "backtests": backtest_status(kind)}


def _due(now: float) -> dict[str, list[dict]]:
    slow = now - _state["slow_at"] >= SAMPLE_SLOW_S
    out: dict[str, list[dict]] = {}
    for a in _alerts.values():
        if a["closed"]:
            continue
        young = now - a["at"] < FAST_FOR_S or _quant_watching(a, now)
        if young or slow:
            out.setdefault(a["chain"], []).append(a)
    if slow:
        _state["slow_at"] = now
    return out


async def sample(client: httpx.AsyncClient, now: float | None = None) -> int:
    now = now or time.time()
    if now - _state["sampled_at"] < SAMPLE_FAST_S:
        return 0
    _state["sampled_at"] = now
    n = 0
    for chain, alerts in _due(now).items():
        for i in range(0, len(alerts), 30):
            batch = alerts[i:i + 30]
            try:
                r = await client.get(DEX_PAIRS.format(chain=chain, pairs=",".join(a["pair_address"] for a in batch)),
                                     timeout=10.0)
                pairs = (r.json() or {}).get("pairs") or [] if r.status_code == 200 else None
            except (httpx.HTTPError, ValueError):
                pairs = None
            if pairs is None:
                continue            # the API did not answer: not a vanished pool
            by = {(p.get("pairAddress") or "").lower(): p for p in pairs}
            for a in batch:
                p = by.get(a["pair_address"].lower())
                apply_price(a, p.get("priceUsd") if p else None, now)
                price = _num(p.get("priceUsd")) if p else None
                if price and not a.get("system_done"):
                    add_bar(key_of(a), now, price, _num(((p.get("volume") or {}).get("m5"))))
                if p and not a.get("image"):
                    a["image"] = (p.get("info") or {}).get("imageUrl") or None
                n += 1
            await asyncio.sleep(0.3)
    save()
    save_bars(now)
    return n


def _median(vals: list[float]) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def _item(a: dict, now: float, chosen) -> dict:
    from app.trading.onchain import narratives, system
    systems = [_system_view(a, c["label"]) for c in system.CANDIDATES]
    return {"symbol": a["symbol"], "name": a["name"], "chain": a["chain"], "token_address": a["token_address"],
            "pair_address": a["pair_address"], "pair_url": a["pair_url"], "image": a.get("image"), "at": a["at"], "cap0": a["cap0"], "returns": a["returns"],
            "now": (a.get("last") or {}).get("ret"), "max": a["max_ret"], "gone": a["gone"],
            "age_h": round((now - a["at"]) / 3600, 1), "strategy": a.get("strategy"),
            "system": _system_view(a, chosen), "systems": [v for v in systems if v],
            "quant": {"status": a.get("quant_status", "not evaluated"),
                      **{k: (a.get("quant_system") or {}).get(k) for k in
                         ("state", "policy_id", "report_hash", "timeframe", "in_at", "evaluated_at", "reason")}},
            "narratives": narratives.labels(narratives.match(a.get("name"), a.get("symbol"), kind="meme")),
            "backtests": a.get("backtests"), "on_alert": _alert_bt_view(a)}


def for_token(chain: str, token: str, now: float | None = None) -> list[dict]:
    """Every alert on one token, of both kinds, newest first, in the same
    shape board() items have. The token page asks for this so Signal is
    complete whichever list opened it (Lorenzo, 27/09)."""
    now = now or time.time()
    rows = [a for a in _alerts.values()
            if a["chain"] == chain and a.get("token_address") == token and a["entry"] is not None]
    rows.sort(key=lambda a: -a["at"])
    chosen = {k: system_board(k)["chosen"] for k in {a["kind"] for a in rows}}
    return [_item(a, now, chosen[a["kind"]]) for a in rows]


def board(kind: str, limit: int = 30, now: float | None = None) -> dict:
    """The alerts ranked by what they are worth now, with every checkpoint,
    and per checkpoint the median and the share in profit."""
    now = now or time.time()
    sysb = system_board(kind)
    chosen = sysb["chosen"]
    rows = [a for a in _alerts.values() if a["kind"] == kind and a["entry"] is not None]
    rows.sort(key=lambda a: -((a.get("last") or {}).get("ret") if a.get("last") else -9))
    items = [_item(a, now, chosen) for a in rows[:limit]]
    summary = []
    for h in CHECKPOINTS_H:
        vals = [a["returns"][str(h)] for a in rows if str(h) in a["returns"]]
        summary.append({"h": h, "n": len(vals), "median": round(_median(vals), 4) if vals else None,
                        "positive": round(sum(v > 0 for v in vals) / len(vals), 3) if vals else None,
                        "mean": round(sum(vals) / len(vals), 4) if vals else None})
    live = [a["last"]["ret"] for a in rows if a.get("last")]
    strat = [a["strategy"]["return_pct"] for a in rows if a.get("strategy")]
    return {"items": items, "total": len(rows), "checkpoints": list(CHECKPOINTS_H), "summary": summary,
            "now": {"n": len(live), "median": round(_median(live), 4) if live else None,
                    "positive": round(sum(v > 0 for v in live) / len(live), 3) if live else None},
            "strategy": {"n": len(strat), "median_pct": round(_median(strat), 2) if strat else None},
            "system": {**sysb, "live": _live(rows, chosen)}}


FRESH_S = 48 * 3600       # an alert older than this leaves the feed (the hall of fame keeps it)
EARLY_S = 6 * 3600


def feed(kind: str = "meme", now: float | None = None, limit: int = 40) -> list[dict]:
    """The Alerts tab: alerts of the last FRESH_S, newest first, without
    rugs (Lorenzo: "non si riempia il sito di alert vecchi o scaduti che
    poi si sono rivelati essere rug pull, questa roba deve sparire")."""
    now = now or time.time()
    chosen = system_board(kind)["chosen"]
    rows = [a for a in _alerts.values() if a["kind"] == kind and now - a["at"] <= FRESH_S and not a.get("gone")
            and not ((a.get("last") or {}).get("ret") or 0) <= -0.8]
    rows.sort(key=lambda a: -a["at"])
    return [{"symbol": a["symbol"], "name": a["name"], "chain": a["chain"], "token_address": a["token_address"],
             "pair_address": a["pair_address"], "pair_url": a["pair_url"], "image": a.get("image"), "at": a["at"],
             "cap0": a["cap0"], "now": (a.get("last") or {}).get("ret"), "max": a["max_ret"], "returns": a["returns"],
             "early": now - a["at"] <= EARLY_S, "ai": a.get("ai"), "system": _system_view(a, chosen),
             "gone": False, "strategy": a.get("strategy")} for a in rows[:limit]]


def reviving(kind: str = "meme", now: float | None = None, limit: int = 6) -> list[dict]:
    """Older alerts (past FRESH_S), still alive, moving again: the price
    back well above its low and buyers ahead of sellers in the last hour
    (outcomes' market reading). Lorenzo: "voglio anche poter riesumare
    roba vecchia che sta ritornando in moda"."""
    from app.trading.onchain import outcomes
    now = now or time.time()
    out = []
    for a in _alerts.values():
        if a["kind"] != kind or now - a["at"] <= FRESH_S or a.get("gone"):
            continue
        e = outcomes._journal.get(f"{a['chain']}:{a['token_address']}") or {}
        m = e.get("market") or {}
        chg = m.get("chg_h6") if m.get("chg_h6") is not None else m.get("chg_h1")
        if chg is None or chg < 30 or (m.get("buys_h1") or 0) <= (m.get("sells_h1") or 0) or e.get("rug"):
            continue
        out.append({"symbol": a["symbol"], "name": a["name"], "chain": a["chain"], "token_address": a["token_address"],
                    "pair_address": a["pair_address"], "pair_url": a["pair_url"], "image": a.get("image"),
                    "at": a["at"], "chg": chg, "buys_h1": m.get("buys_h1"), "sells_h1": m.get("sells_h1")})
    out.sort(key=lambda r: -r["chg"])
    return out[:limit]


def _alert_bt_view(a: dict) -> dict | None:
    """The trend follower entered on the alert: the best of the candidates,
    with trades and wins (Lorenzo, 28/09: every alerted token shows its
    backtest, no "no entry")."""
    rows = [{"label": k, "ret": v.get("ret"), "trades": v.get("trades") or 0, "wins": v.get("wins") or 0,
             "state": v.get("state"), "done": v.get("done"), "entry": v.get("entry"), "in_at": v.get("in_at"),
             "events": v.get("events") or []}
            for k, v in (a.get("alert_bt") or {}).items() if v and v.get("ret") is not None]
    if not rows:
        return None
    return max(rows, key=lambda r: r["ret"])


def _system_view(a: dict, label: str) -> dict | None:
    r = (a.get("system") or {}).get(label)
    if not r:
        return None
    return {"label": label, "ret": r.get("ret"), "trades": r.get("trades"), "state": r.get("state"),
            "entry": r.get("entry"), "in_at": r.get("in_at"), "done": r.get("done"), "events": r.get("events")}


def _live(rows: list[dict], label: str) -> dict:
    """The system on every alert so far, finished or not."""
    vals = [((a.get("system") or {}).get(label) or {}).get("ret") for a in rows]
    vals = [v for v in vals if v is not None]
    holding = sum(1 for a in rows if ((a.get("system") or {}).get(label) or {}).get("state") == "in")
    return {"n": len(vals), "median": round(_median(vals), 4) if vals else None,
            "positive": round(sum(v > 0 for v in vals) / len(vals), 3) if vals else None,
            "mean": round(sum(vals) / len(vals), 4) if vals else None, "holding": holding}


def recent(kind: str, since_s: float, now: float | None = None) -> list[dict]:
    now = now or time.time()
    return [a for a in _alerts.values() if a["kind"] == kind and now - a["at"] <= since_s]


_load()

