"""Backtest H24 dei token della schermata Strategie (Top 50).

Lorenzo, 28/09: "voglio che quando il server e' online [...] scansioni
costantemente tutte le strategie e backtest [...] tutti quei token che sono
finiti nella schermata delle strategie [...] deve essere attivo costantemente
H24". Il laboratorio (backtest_lab.py) prova solo i token del diario vecchi
di 48 ore e solo quando GeckoTerminal e' libero: i token della Top non li
vedeva mai, e una Top senza alert non aveva nessun backtest.

Qui un giro al minuto: il token della Top con il backtest piu' vecchio (o
senza) prende le ultime candele da 5 minuti, passa da tutte le strategie
(system.backtest_all, lo stesso motore degli alert) e il risultato resta su
disco. Ogni token si rifa' ogni `REFRESH_S`. Ogni backtest finisce nel
registro dell'agente, cosi' la pagina Agent mostra il lavoro vero.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Awaitable, Callable

import httpx

from app import http_client

from app.notify import deepseek_desk
from app.sniper.scanner import GECKO_NETWORKS
from app.trading.onchain import alert_track, candle_archive, priority, projects_db, sim_backtest, system
from app.trading.onchain.storage import data_file
from app.atomic_write import write_text_atomic

logger = logging.getLogger(__name__)

_STORE_FILE = data_file("onchain_strategy_lab.json")
DEX_TOKENS = "https://api.dexscreener.com/tokens/v1/{chain}/{token}"
TICK_S = 60
FIRST_TICK_DELAY_S = 60
REFRESH_S = 3600
BARS = 1000                      # 5 minuti: circa tre giorni e mezzo
# Lorenzo, 30/09: sui progetti in classifica il trend follower del sito gira
# su 8 ore se il token e' giovane, altrimenti sul giornaliero, e solo se ci
# sono abbastanza candele per generare un trigger. Il filtro di volatilita'
# (deviazione su 16 barre, media su 44) e' vuoto fino alla barra 59: prima
# di 60 candele chiuse Trend EMA non puo' entrare, qualunque sia il grafico.
TRIGGER_MIN_BARS = 60
DAILY_MIN_BARS = TRIGGER_MIN_BARS    # meno di 60 giorni = token giovane: 8 ore
# Lorenzo, 30/09: "5 minuti al listing, poi 8 ore e poi giornaliero [...]
# graduale con un algoritmo che tiene conto di quanta storicita' ha il
# grafico", poi: "se nel backtest il segnale a un giorno scatta c'e'
# abbastanza storicita'. Se non scatta vai a ritroso [...] se da un giorno
# non c'e' pero' a 12 ore ce l'hai, allora prendi quello". La scala parte dal
# gradino piu' largo con almeno TRIGGER_MIN_BARS candele chiuse e scende
# finche' il trend follower non ha almeno un ingresso: vince il primo
# gradino che entra. Nessun ingresso da nessuna parte = il gradino piu' largo.
# (interval, GeckoTerminal timeframe, aggregate): i gradini senza candela
# nativa si compongono da quella piu' fine che li divide.
LADDER = [("1d", "day", 1), ("12h", "hour", 12), ("8h", "hour", 4), ("6h", "hour", 1), ("4h", "hour", 4),
          ("2h", "hour", 1), ("1h", "hour", 1), ("30m", "minute", 15), ("15m", "minute", 15),
          ("5m", "minute", 5)]
STEP_S = {"1d": 86400, "12h": 43200, "8h": 28800, "6h": 21600, "4h": 14400, "2h": 7200, "1h": 3600,
          "30m": 1800, "15m": 900, "5m": 300}
TREND_FOLLOWERS = [("Lorenzo (trend-follower)", "Trend EMA"), ("Lorenzo HF (minuti on-chain)", "Trend HF")]
# Lorenzo, 30/09 sera: "per la strategia RSI piu' BB dobbiamo applicare la
# stessa logica [...] time frame piu' alti per trade piu' duraturi [...] se
# la cripto e' molto recente time frame piu' veloci". Same ladder via
# run_daily(strategies=RSI_BB); today RSI+BB runs on 5m only (backtest_all),
# and scripts/ladder_compare.py measures the ladder first.
RSI_BB = [("Gabriele (RSI+BB reversal)", "RSI+BB")]
# Lorenzo, 30/09: "prima di applicare questa regola fai un po' di prove su
# tutte le 50 cripto [...] dovrebbero essere paritarie o superiori". Until
# scripts/ladder_compare.py says so, the rule in use stays the old one: 1d,
# else 8h, first with TRIGGER_MIN_BARS closed candles, Trend EMA only.
LADDER_RULE = False
# First Top 50 test (30/09, 50 tokens): descending to the first entry took 34
# tokens from 1d straight to 5m, where the trend follower overtrades in
# loss (mean -15.9% against -4.6%). A token with history descends at most
# MAX_DESCENT rungs and never below FLOOR; the narrow rungs are for the
# young ones (Lorenzo: "sulle cripto appena uscite [...] time frame piu'
# ristretti, questo e' normale").
MAX_DESCENT = 3
FLOOR = "1h"
OLD_RUNGS = ("1d", "8h")
KEEP = 300

_results: dict[str, dict] = {}   # chain:token -> {at, pair, symbol, backtests | error}
_state = {"last_tick": 0.0, "last_key": "", "error": ""}
_signal_cbs: list[Callable[[dict], Awaitable[None]]] = []


def on_signal(cb: Callable[[dict], Awaitable[None]]) -> None:
    """cb(signal) for every fresh entry or exit of the trend follower (any LADDER rung)."""
    _signal_cbs.append(cb)


def _load() -> None:
    try:
        raw = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(raw, dict):
        _results.update({k: v for k, v in raw.items() if isinstance(v, dict)})
    # A saved result whose arrows are not its best listed row (events of
    # RSI+BB from before #434, or trend-only events saved before RSI+BB was
    # listed) is redone first; until then the list shows the row the saved
    # arrows belong to, or nothing (main._lab_summary).
    for r in _results.values():
        bt = r.get("backtests") or {}
        row = trend_row(bt)
        if row is not None and ((bt.get("best") or {}).get("label") != row["label"] or drawn_row(bt) is None):
            r["at"] = 0


def trend_row(part: dict) -> dict | None:
    """The best traded listed row of a backtest (system.SPOT_LABELS)."""
    return system.listed_row(part)


drawn_row = system.drawn_row
shown = system.shown


def _save() -> None:
    try:
        write_text_atomic(_STORE_FILE, json.dumps(_results, separators=(",", ":")), encoding="utf-8")
    except OSError:
        pass


def reset_for_tests() -> None:
    _results.clear()
    _state.update(last_tick=0.0, last_key="", error="")


def key_of(chain: str, token: str) -> str:
    return f"{chain}:{token}"


def get(chain: str, token: str) -> dict | None:
    """I backtest di un token, nella forma di system.backtest_all."""
    r = _results.get(key_of(chain, token))
    if not r or r.get("backtests") is None:
        return None
    # The daily trend follower sits next to the 5-minute results: without it
    # every gem page said "No daily backtest on this gem yet".
    return {**r["backtests"], "daily": r.get("daily")} if r.get("daily") else r["backtests"]


def next_due(entries: list[dict], now: float) -> dict | None:
    """Il token da provare adesso: mai provato prima, poi il piu' vecchio
    oltre REFRESH_S. Solo reti che GeckoTerminal conosce."""
    due = []
    for e in entries:
        if not e.get("token_address") or not (e.get("chain") == "layer" or GECKO_NETWORKS.get(e.get("chain"))):
            continue
        r = _results.get(key_of(e["chain"], e["token_address"]))
        at = (r or {}).get("at") or 0
        if now - at >= REFRESH_S:
            due.append((at, e))
    return min(due, key=lambda x: x[0])[1] if due else None


def status(entries: list[dict], now: float | None = None) -> dict:
    now = now or time.time()
    keys = [key_of(e["chain"], e["token_address"]) for e in entries if e.get("token_address")]
    ready = [k for k in keys if (_results.get(k) or {}).get("backtests")]
    fresh = [k for k in ready if now - (_results[k].get("at") or 0) < REFRESH_S]
    return {"total": len(keys), "ready": len(ready), "fresh": len(fresh), "refresh_s": REFRESH_S,
            "last_tick": _state["last_tick"], "error": _state["error"]}


def _net(chain: str) -> str:
    """The GeckoTerminal network name: layer chains live on the exchange."""
    if chain == "layer":
        return "cex"
    return GECKO_NETWORKS[chain]


async def _pair_of(client: httpx.AsyncClient, e: dict) -> str | None:
    """Il pool su cui provare: quello della Top, o il piu' liquido del token."""
    if e.get("pair_address"):
        return e["pair_address"]
    if e["chain"] == "layer":
        row = projects_db.get("layer", e["token_address"])
        cex = (row.get("overall") or {}).get("cex") if row else None
        if cex and cex.get("exchange") and cex.get("pair"):
            return f"{cex['exchange']}:{cex['pair']}"
        return None
    try:
        r = await client.get(DEX_TOKENS.format(chain=e["chain"], token=e["token_address"]))
        pairs = r.json() if r.status_code == 200 else []
    except (httpx.HTTPError, ValueError):
        return None
    pairs = [p for p in pairs if isinstance(p, dict) and p.get("chainId") == e["chain"] and p.get("pairAddress")]
    if not pairs:
        return None
    return max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0)["pairAddress"]


def _best(bt: dict) -> dict | None:
    return system.listed_row(bt)


def _merge(bars: list[list], step: int) -> list[list]:
    """Barre fini in barre da `step` secondi, allineate su ts % step == 0:
    apertura della prima, massimo, minimo, chiusura dell'ultima, volume
    sommato. Le barre sono [ts, o, h, l, c, v]."""
    out: dict[int, list] = {}
    for b in sorted(bars):
        bucket = int(b[0]) // step * step
        cur = out.get(bucket)
        if cur is None:
            out[bucket] = [bucket, b[1], b[2], b[3], b[4], b[5]]
        else:
            cur[2] = max(cur[2], b[2])
            cur[3] = min(cur[3], b[3])
            cur[4] = b[4]
            cur[5] = cur[5] + b[5]
    return [out[k] for k in sorted(out)]


def _merge_8h(bars: list[list]) -> list[list]:
    return _merge(bars, 28800)


def _entered(res: dict) -> bool:
    rows = res.get("rows") or []
    return bool(res.get("best")) or any(r.get("trades") or r.get("in_position") for r in rows)


def _closed(bars: list[list], step: int, now: float) -> list[list]:
    """Only closed candles: a signal on the one still forming can vanish."""
    return [b for b in bars if b[0] + step <= now]


def pick_interval(age_s: float) -> str:
    """The widest rung whose step fits TRIGGER_MIN_BARS times in the
    chart's history; below 5 hours, the 5 minutes anyway."""
    for iv, _tf, _agg in LADDER:
        if age_s >= TRIGGER_MIN_BARS * STEP_S[iv]:
            return iv
    return LADDER[-1][0]


def descent_end(start: int) -> int:
    """Index after the last rung a token starting on LADDER[start] may try."""
    end = min(len(LADDER), start + MAX_DESCENT + 1)
    floor = [r[0] for r in LADDER].index(FLOOR)
    return min(end, floor + 1) if start <= floor else end


async def run_daily(client: httpx.AsyncClient, net: str, pair: str, token: str, now: float,
                    fast: list[list] | None = None, strategies: list[tuple[str, str]] | None = None,
                    rule: bool | None = None) -> dict | None:
    """Il trend-follower del sito sul gradino di LADDER che la storia del
    grafico regge: dal piu' largo con TRIGGER_MIN_BARS candele chiuse in
    giu', il primo in cui la strategia entra almeno una volta. `fast` = le
    candele da 5 minuti gia' scaricate. None = GeckoTerminal non risponde."""
    got: dict[tuple[str, int], list[list]] = {}
    if fast:
        got[("minute", 5)] = fast
    day = await candle_archive.candles(client, net, pair, "day", 1, now, token)
    if day is None:
        return None
    got[("day", 1)] = day
    first = min((b[0] for bars in got.values() for b in bars), default=now)
    start = LADDER.index(next(r for r in LADDER if r[0] == pick_interval(now - first)))
    tried: dict | None = None
    first_ok: dict | None = None
    # Lorenzo, 30/09: "adegua la strategia se non ci sono ingressi". Trend
    # EMA first down the whole ladder; only if it never enters, the on-chain
    # variant of the same trend follower (Trend HF: VWAP, efficiency, ATR
    # trail) down the same rungs. Still trend following, still long only.
    # Candles are fetched lazily, so the fallback costs no extra calls.
    on = LADDER_RULE if rule is None else rule      # rule: the daily check runs both without the global
    ladder = LADDER[start:descent_end(start)] if on else [r for r in LADDER if r[0] in OLD_RUNGS]
    for name, label in strategies or (TREND_FOLLOWERS if on else TREND_FOLLOWERS[:1]):
        for iv, tf, agg in ladder:
            if (tf, agg) not in got:
                raw = await candle_archive.candles(client, net, pair, tf, agg, now, token)
                if raw is None:
                    return None
                got[(tf, agg)] = raw
            raw = got[(tf, agg)]
            native = {"day": 86400, "hour": 3600, "minute": 60}[tf] * agg
            bars = _closed(sorted(raw) if native == STEP_S[iv] else _merge(raw, STEP_S[iv]), STEP_S[iv], now)
            if len(bars) < TRIGGER_MIN_BARS:
                tried = {"interval": iv, "bars": len(bars), "error": "too few candles"}
                continue
            res = {"interval": iv, **await asyncio.to_thread(system.backtest_one, bars, name, label)}
            if _entered(res) or not on:
                return res
            first_ok = first_ok or res
    return first_ok or tried


def _signal(daily: dict, prev: dict | None) -> tuple[dict | None, bool]:
    """The trend follower's last buy or sell, and whether it is fresh news:
    on the last closed candle (a fill lands one bar after the signal) and not
    already announced on the previous run."""
    ev = ((daily.get("best") or {}).get("events") or [])
    if not ev or not daily.get("to"):
        return None, False
    last = ev[-1]
    sig = {k: last.get(k) for k in ("side", "t", "price", "ret") if last.get(k) is not None}
    old = (prev or {}).get("signal") or {}
    # Saved before the arrows moved to the fill candle (30/09): the same
    # signal now carries a later time, and must not be announced twice.
    legacy = bool(old) and not ((prev or {}).get("best") or {}).get("fills")
    fresh = (not legacy and last["t"] >= daily["to"] - STEP_S.get(daily.get("interval"), 86400)
             and (old.get("t"), old.get("side")) != (sig["t"], sig["side"]))
    return sig, fresh


async def run_one(client: httpx.AsyncClient, e: dict, now: float) -> dict | None:
    """Un backtest. None = GeckoTerminal non risponde ora: si riprova al giro dopo."""
    key = key_of(e["chain"], e["token_address"])
    symbol = e.get("symbol") or "?"
    prev_daily = (_results.get(key) or {}).get("daily")
    pair = await _pair_of(client, e)
    if not pair:
        _results[key] = {"at": now, "symbol": symbol, "pair": None, "error": "no pool"}
        return _results[key]
    bars = await alert_track._candles(client, _net(e["chain"]), pair, "minute", 5, now, BARS,
                                      e["token_address"], source="gecko")
    if bars is None:
        return None
    if not bars:
        _results[key] = {"at": now, "symbol": symbol, "pair": pair, "error": "no candles"}
        return _results[key]
    try:     # the archive keeps them past the 1000-candle window
        await asyncio.to_thread(candle_archive.put, candle_archive.key(_net(e["chain"]), pair, "minute", 5,
                                                                       e["token_address"]), bars, now)
    except Exception:
        logger.exception("strategy lab: archivio 5m di %s fallito", symbol)
    bt = await asyncio.to_thread(system.backtest_all, sorted(bars))
    _results[key] = {"at": now, "symbol": symbol, "pair": pair, "backtests": bt}
    if sim_backtest.needs_relabel(e["chain"], e["token_address"]):
        try:    # old Top 50 wallet trades saved without their strategy: rerun each listed one on the same candles
            old = await asyncio.to_thread(candle_archive.get, candle_archive.key(_net(e["chain"]), pair,
                                                                                 "minute", 5, e["token_address"]))
            full = sorted({int(b[0]): b for b in [*(old or []), *bars]}.values())
            times = await asyncio.to_thread(system.trend_trade_times, full)
            sim_backtest.relabel(e["chain"], e["token_address"], times, int(full[0][0]))
        except Exception:
            logger.exception("strategy lab: rietichettatura di %s fallita", symbol)
    # Il daily e' un di piu': se fallisce il 5 minuti resta.
    try:
        daily = await run_daily(client, _net(e["chain"]), pair, e["token_address"], now, bars)
    except Exception:
        logger.exception("strategy lab: daily di %s fallito", symbol)
        daily = None
    if daily is None:
        daily = prev_daily       # a busy GeckoTerminal must not wipe the saved result
    else:
        sig, fresh = _signal(daily, prev_daily)
        if sig:
            daily["signal"] = sig
        if fresh:
            await _announce({"chain": e["chain"], "token": e["token_address"], "symbol": symbol, "pair": pair,
                             "interval": daily["interval"], "liq": e.get("liquidity_usd"), **sig}, now)
    if daily is not None:
        _results[key]["daily"] = daily
    try:    # the Top 50 wallet keeps every trade, even after the window slides past it
        sim_backtest.remember(e["chain"], e["token_address"], symbol, get(e["chain"], e["token_address"]),
                              liq=e.get("liquidity_usd"))
    except Exception:
        logger.exception("strategy lab: registro del portafoglio Top 50 fallito per %s", symbol)
    best = _best(bt)
    hold = bt.get("hold_pct")
    outcome = (f"best {best['label']} {best['return_pct']:+.0f}% in {best['trades']} trades"
               if best else "no strategy entered")
    if hold is not None:
        outcome += f", holding {hold:+.0f}%"
    deepseek_desk.note("backtest", f"Backtested {symbol} on every strategy", now=now,
                       steps=[f"{len(bars)} 5-minute candles", f"{len(bt.get('rows') or [])} strategies"],
                       outcome=outcome, chain=e["chain"], token=e["token_address"])
    return _results[key]


async def _announce(sig: dict, now: float) -> None:
    buy = sig["side"] == "buy"
    deepseek_desk.note("backtest", f"Trend follower {sig['interval']}: {'entry' if buy else 'exit'} on {sig['symbol']}",
                       now=now, outcome=f"{'buy' if buy else 'sell'} at {sig.get('price')}", tally=False,
                       chain=sig["chain"], token=sig["token"])
    for cb in _signal_cbs:
        try:
            await cb(sig)
        except Exception:
            logger.exception("strategy lab: avviso segnale di %s fallito", sig.get("symbol"))


async def tick(entries: list[dict], now: float | None = None) -> dict | None:
    now = now or time.time()
    _state["last_tick"] = now
    if priority.backtests_first():
        return None
    e = next_due(entries, now)
    if e is None:
        return None
    try:
        async with http_client.pooled(timeout=15.0) as client:
            out = await run_one(client, e, now)
        _state.update(last_key=key_of(e["chain"], e["token_address"]), error="")
    except Exception as exc:
        logger.exception("strategy lab: backtest di %s fallito", e.get("symbol"))
        _state["error"] = str(exc)[:200]
        return None
    if len(_results) > KEEP:
        for k in sorted(_results, key=lambda k: _results[k].get("at") or 0)[:len(_results) - KEEP]:
            _results.pop(k, None)
    _save()
    return out


async def lab_loop(entries: Callable[[], list[dict]]) -> None:
    _load()
    await asyncio.sleep(FIRST_TICK_DELAY_S)
    while True:
        try:
            await tick(entries())
        except Exception:
            logger.exception("strategy lab: giro fallito")
        await asyncio.sleep(TICK_S)
