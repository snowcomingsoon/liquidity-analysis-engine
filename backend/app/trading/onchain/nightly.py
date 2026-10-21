"""The gem research in runs at fixed times, Europe/Rome: since 19/10 a full
run at 04:00 and a light one at 16:00 (Lorenzo: "procedi con 04:00 e 16:00
e la ricerca leggera"); the times are `onchain_nightly_hour` plus
`onchain_nightly_extra_times`, the light ones `onchain_nightly_light_times`.
History: 22:00 and 11:35 (08/10), hourly runs (12/10, off), 03:00 (14/10),
03:00 and 18:00 (17/10).

Lorenzo, 07/10: "non lasciare sempre in ascolto il bot che scansiona
costantemente [...] tutto in una tranche a fine serata". Until then five
loops ran around the clock: the board's tick every 10 s (discovery feeds,
market polls, pillars, DeepSeek judge/review/code readings, ranking,
alerts), the weekly re-check of the Top 50, outcomes every 10 minutes,
layers once a day and DeepSeek studies every 5 minutes. Each of them paid
APIs and DeepSeek all day for a board that people read in the evening.

Now, once a night and in this order:
1. the board's ticks until its queue is empty (`leaderboard.drained`) or
   RESEARCH_SHARE of the window is spent;
2. layers, outcomes once;
3. the weekly re-check of the Top for the tokens it still owes, until the
   window closes;
4. DeepSeek studies once;
then one Telegram message in Italian with what changed.

The run is remembered in `data/onchain_nightly.json`: a deploy at 22:30
resumes the night (within its window, MAX_ATTEMPTS times at most), a
server that boots at 23:00 with tonight not run runs it now, one that
boots at 15:00 runs the 11:35 one if it was missed (CATCHUP_S); a run never
overlaps the next, the loop runs one at a time.

What stays immediate: the manual scan and the per-token re-check run their
own steps; a project added by hand is analysed at once
(`leaderboard.analyze_now`).
"""
from __future__ import annotations

import asyncio
import json
import logging
import socket
import time
from datetime import datetime, timedelta
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo

import httpx

from app.atomic_write import write_text_atomic
from app.config import settings
from app.trading.onchain import storage

logger = logging.getLogger(__name__)

ROME = ZoneInfo("Europe/Rome")
_FILE = storage.data_file("onchain_nightly.json")
START_DELAY_S = 60              # let the server come up first
CATCHUP_S = 8 * 3600            # a 03:00 run missed is caught up until 11:00, not in the afternoon
MAX_ATTEMPTS = 3                # a run that keeps crashing the server stops being resumed
RESUME_MIN_S = 10 * 60          # a resumed run gets at least this, even past its window
RESEARCH_SHARE = 0.75           # the board's ticks leave the rest of the window to the re-check
MIN_TICKS = 30                  # 5 minutes: the readings spawned by the tick get their turns
SETTLE_S = 300                  # readings still running when the ticks stop
RECHECK_GAP_S = 5               # between two tokens of the re-check

# The sentinel (Lorenzo, 18/10: "Procedi con la sentinella, notifiche subito
# a qualsiasi ora"): between the research runs, every SENTINEL_EVERY_S a few
# light ticks (leaderboard.tick(light=True)) read the fast sources and the
# launchpads, analyse what is new, and send its alerts at once. It stops as
# soon as nothing new waits, after SENTINEL_MAX_S at most, and never runs
# beside a research run (_research_lock).
SENTINEL_EVERY_S = 600
SENTINEL_MAX_S = 300
SENTINEL_MIN_TICKS = 3
SENTINEL_SETTLE_S = 60
# The drain (Lorenzo, 21/10: "i lavori rimasti in coda [...] vanno fatti
# smaltire dopo la ricerca. Attualmente ce ne sono 230"): while a run left a
# backlog, a sentinel round becomes the night's full ticks for up to
# DRAIN_MAX_S, never closer than DRAIN_GAP_S to the next run. A round that
# leaves as much as it found stops the drain until the next day, so a job
# that cannot be done never keeps the server busy around the clock.
DRAIN_MAX_S = 20 * 60
DRAIN_GAP_S = 30 * 60

_state: dict = {}
_running = False
_research_lock = asyncio.Lock()


def _load() -> None:
    try:
        _state.update(json.loads(_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass


def _save() -> None:
    try:
        write_text_atomic(_FILE, json.dumps(_state, ensure_ascii=False))
    except OSError:
        logger.exception("nightly: state not saved")


def _host() -> str:
    """The container's id (Docker sets it as the hostname). A deploy builds a
    new container; a crash restarted by Docker keeps the same one."""
    return socket.gethostname()


def forgive_redeploy(host: str | None = None) -> bool:
    """An unfinished run whose attempt started in another container was cut
    by a deploy, not by a crash: it does not count towards MAX_ATTEMPTS.

    The CancelledError branch of run_night was meant to do this, but a
    deploy gives the container ten seconds and then kills it: the branch
    rarely ran. 12/10, three deploys between 22:00 and midnight turned into
    "Ricerca delle 22:00 interrotta: e' fallita 3 volte" with nothing failed.
    """
    host = host or _host()
    prev = _state.get("attempt_host")
    if not prev or prev == host or (_state.get("done_slot") or 0) >= (_state.get("slot") or 0):
        return False
    _state["attempts"] = max(0, (_state.get("attempts") or 1) - 1)
    _state["attempt_host"] = host
    if _state.get("gave_up") == _state.get("slot") and _state["attempts"] < MAX_ATTEMPTS:
        _state.pop("gave_up", None)
    _save()
    return True


def is_main_run(slot: float) -> bool:
    """The evening run (onchain_nightly_hour and the extra times): full
    window and a Telegram summary always. Hourly runs are shorter and speak
    only when the Top changed."""
    when = datetime.fromtimestamp(slot, ROME)
    return (when.hour, when.minute) in set(run_times(hourly=False))


def is_light_run(slot: float) -> bool:
    """A run at one of onchain_nightly_light_times (16:00 since 19/10)."""
    when = datetime.fromtimestamp(slot, ROME)
    light = set()
    for part in (settings.onchain_nightly_light_times or "").split(","):
        h, _, m = part.strip().partition(":")
        try:
            light.add((int(h), int(m or 0)))
        except ValueError:
            continue
    return (when.hour, when.minute) in light


def window_s(slot: float) -> float:
    if is_light_run(slot):
        return settings.onchain_nightly_light_max_hours * 3600
    if not settings.onchain_nightly_hourly or is_main_run(slot):
        return settings.onchain_nightly_max_hours * 3600
    return settings.onchain_hourly_max_minutes * 60


def reset_for_tests() -> None:
    global _running
    _state.clear()
    _running = False


# --------------------------------------------------------------- the clock

def run_times(hour: int | None = None, hourly: bool | None = None) -> list[tuple[int, int]]:
    """(hour, minute) of each daily run, Europe/Rome, sorted. A given
    `hour` means that run only."""
    if hour is not None:
        return [(hour, 0)]
    out = {(settings.onchain_nightly_hour, 0)}
    if settings.onchain_nightly_hourly if hourly is None else hourly:
        out |= {(h, 0) for h in range(24)}
    for part in (settings.onchain_nightly_extra_times or "").split(","):
        h, _, m = part.strip().partition(":")
        try:
            hh, mm = int(h), int(m or 0)
        except ValueError:
            continue
        if 0 <= hh < 24 and 0 <= mm < 60:
            out.add((hh, mm))
    return sorted(out)


def _slot_on(day, hour: int, minute: int = 0) -> float:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=ROME).timestamp()


def _slots_around(now_ts: float, hour: int | None) -> list[float]:
    today = datetime.fromtimestamp(now_ts, ROME).date()
    return sorted(_slot_on(today + timedelta(days=d), h, m)
                  for d in (-1, 0, 1) for h, m in run_times(hour))


def latest_slot(now_ts: float, hour: int | None = None) -> float:
    """The most recent run time (Europe/Rome) at or before now."""
    return max(t for t in _slots_around(now_ts, hour) if t <= now_ts)


def next_run(now_ts: float, hour: int | None = None) -> float:
    """The next run time (Europe/Rome) strictly after now (DST included)."""
    return min(t for t in _slots_around(now_ts, hour) if t > now_ts)


def due_slot(now_ts: float, state: dict, hour: int | None = None) -> float | None:
    """The night to run now, or None. Tonight counts until CATCHUP_S after
    the hour: a server booting at 23:00 runs it, one at 15:00 waits."""
    slot = latest_slot(now_ts, hour)
    if (state.get("done_slot") or 0) >= slot or now_ts - slot > CATCHUP_S:
        return None
    if state.get("slot") == slot and (state.get("attempts") or 0) >= MAX_ATTEMPTS:
        return None
    return slot


def forced_due(state: dict) -> str | None:
    """The `onchain_nightly_force` key not yet run, or None."""
    key = (settings.onchain_nightly_force or "").strip()
    return key if key and key not in (state.get("forced") or []) else None


def _consume_force(key: str | None) -> None:
    if key:
        _state["forced"] = [*(_state.get("forced") or [])[-9:], key]
        _save()


def status(now: float | None = None) -> dict:
    """For the board's meta: `nightly: {last_run, next_run, summary}`."""
    if not _state:
        _load()
    now = now or time.time()
    return {"enabled": settings.onchain_nightly_enabled, "running": _running,
            "last_run": _state.get("last_run"), "next_run": next_run(now),
            "summary": _state.get("summary"),
            "sentinel": {"enabled": settings.onchain_sentinel_enabled, **(_state.get("sentinel") or {})},
            "drain": _state.get("drain")}


# --------------------------------------------------------------- the steps

class Steps:
    """What one night does, one method per step: tests swap it for a fake."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def tick(self) -> None:
        from app.trading.onchain import leaderboard
        await leaderboard.tick(self.client)

    async def light_tick(self) -> None:
        from app.trading.onchain import leaderboard
        await leaderboard.tick(self.client, light=True)

    def quiet(self) -> bool:
        """Nothing new waits for the sentinel: no analysis running, no entry
        never analysed."""
        from app.trading.onchain import leaderboard
        return not leaderboard._busy and all(e["pillars"] for e in leaderboard._entries.values())

    def busy(self) -> bool:
        """An optimization is running: the research steps wait for it."""
        from app import jobs
        return jobs.any_running("optimize")

    def drained(self) -> bool:
        from app.trading.onchain import leaderboard
        return leaderboard.drained()

    def backlog(self) -> dict:
        from app.trading.onchain import leaderboard
        return leaderboard.backlog()

    async def settle(self, timeout: float) -> None:
        """Readings the ticks spawned finish before the client closes."""
        from app.trading.onchain import leaderboard
        pending = set(leaderboard._tasks)
        if pending:
            _, pending = await asyncio.wait(pending, timeout=timeout)
        for t in pending:
            t.cancel()
        if leaderboard._dirty:
            leaderboard._save()

    async def alerts(self) -> None:
        """The gems chat hears now about what entered since the last tick."""
        from app.trading.onchain import leaderboard
        await leaderboard.flush_alerts()

    def counters(self) -> dict:
        from app.trading.onchain import discovery, leaderboard
        d = discovery.status()
        return {"discovered": d.get("found") or 0, "skipped": d.get("skipped") or 0,
                "examined": leaderboard._state.get("examined") or 0, "analysed": leaderboard._counts["analysed"]}

    async def layers(self) -> int:
        from app.trading.onchain import layers
        return await layers.run(self.client)

    async def outcomes(self) -> None:
        from app.trading.onchain import outcomes
        await outcomes.tick()

    def next_recheck(self, keys: list[str]) -> str | None:
        from app.trading.onchain import deep_recheck
        return deep_recheck.next_in_sweep(keys, time.time())

    async def recheck(self, key: str) -> str:
        from app.trading.onchain import deep_recheck
        return await deep_recheck.sweep_one(key, self.client)

    async def studies(self) -> int:
        from app.notify import deepseek_studies
        return len(await deepseek_studies.tick())

    def deepseek_calls(self, start: float, end: float) -> int:
        from app.notify import deepseek_calls
        return deepseek_calls.count_between(start, end)


def _top_map(top: Callable[[], list[dict]]) -> dict[str, str]:
    try:
        return {f"{e['chain']}:{e['token_address']}": e.get("symbol") or "?" for e in top()}
    except Exception:
        logger.exception("nightly: Top not readable")
        return {}


async def _duels(top: Callable[[], list[dict]], now: float) -> int:
    """The arenas' ladder: one night of duels between peers (arenas.py)."""
    from app.trading.onchain import arenas
    return arenas.record_night(top(), now)


async def _guard(name: str, coro: Awaitable, default=None):
    try:
        return await coro
    except Exception:
        logger.exception("nightly: %s failed", name)
        return default


PAUSE_POLL_S = 5                 # how often a paused run looks again


async def _yield_to_optimizations(steps, clock, sleep) -> float:
    """Waits while an optimization runs and returns the seconds waited.

    Lorenzo, 13/10, the optimization slow at 22:12: the research shares the
    server's two cores and the process with it. Now the research steps
    stand aside — readings already in flight finish on their own — and the
    window grows by the pause, so the night does not lose its work."""
    if not getattr(steps, "busy", None) or not steps.busy():
        return 0.0
    t0 = clock()
    logger.info("nightly: paused, an optimization is running")
    while steps.busy():
        await sleep(PAUSE_POLL_S)
    waited = clock() - t0
    logger.info("nightly: resumed after %.0f s", waited)
    return waited


async def run_once(top: Callable[[], list[dict]], steps: Steps, deadline: float, *,
                   clock: Callable[[], float] = time.time, sleep=asyncio.sleep,
                   top_before: dict[str, str] | None = None, light: bool = False) -> dict:
    """One night. Returns the summary; stops at `deadline` at the latest
    (the studies, one bounded pass, run even after it). `top_before` is the
    Top as the night found it, kept across a resume after a deploy.
    `light` (the afternoon run, Lorenzo 19/10): the sentinel's ticks until
    nothing new waits, then the alerts; the database queue, layers,
    outcomes, the Top's re-check and the studies wait for the night."""
    from app.trading.onchain import leaderboard
    t0 = clock()
    before = steps.counters()
    top_before = _top_map(top) if top_before is None else top_before
    research_end = t0 + (deadline - t0) * RESEARCH_SHARE
    ticks, stopped, paused = 0, "drained", 0.0
    while True:
        waited = await _yield_to_optimizations(steps, clock, sleep)
        if waited:
            paused += waited
            research_end += waited
            deadline += waited
        if clock() >= research_end:
            stopped = "window"
            break
        await _guard("tick", steps.light_tick() if light else steps.tick())
        ticks += 1
        await sleep(leaderboard.TICK_S)
        if ticks >= MIN_TICKS and (steps.quiet() if light else steps.drained()):
            break
    await _guard("settle", steps.settle(max(30.0, min(SETTLE_S, deadline - clock()))))
    # No tick from here on: what enters the Top now is sent by these calls.
    await _guard("alerts", steps.alerts())
    left = steps.backlog()
    if light:
        t1 = clock()
        after, top_after = steps.counters(), _top_map(top)
        return {
            "started": t0, "ended": t1, "minutes": round((t1 - t0) / 60, 1), "stopped": stopped, "ticks": ticks,
            **{k: after[k] - before.get(k, 0) for k in after},
            "entered": [top_after[k] for k in top_after if k not in top_before],
            "left": [top_before[k] for k in top_before if k not in top_after],
            "top": len(top_after), "layers": 0, "rechecked": 0, "studies": 0, "duels": 0,
            "deepseek_calls": steps.deepseek_calls(t0, t1), "backlog": left,
            "paused_min": round(paused / 60, 1), "light": True,
        }
    n_layers = await _guard("layers", steps.layers(), 0)
    await _guard("outcomes", steps.outcomes())
    rechecked = 0
    keys = list(_top_map(top))
    while clock() < deadline:
        waited = await _yield_to_optimizations(steps, clock, sleep)
        if waited:
            paused += waited
            deadline += waited
        key = steps.next_recheck(keys)
        if key is None:
            break
        res = await _guard("re-check", steps.recheck(key), "down")
        if res == "down":
            break
        rechecked += res == "done"
        if res == "done":
            await _guard("alerts", steps.alerts())
        await sleep(RECHECK_GAP_S)
    else:
        stopped = "window"
    studies = await _guard("studies", steps.studies(), 0)
    duels = await _guard("duels", _duels(top, clock()), 0)
    await _guard("alerts", steps.alerts())
    t1 = clock()
    after, top_after = steps.counters(), _top_map(top)
    return {
        "started": t0, "ended": t1, "minutes": round((t1 - t0) / 60, 1), "stopped": stopped, "ticks": ticks,
        **{k: after[k] - before.get(k, 0) for k in after},
        "entered": [top_after[k] for k in top_after if k not in top_before],
        "left": [top_before[k] for k in top_before if k not in top_after],
        "top": len(top_after), "layers": n_layers or 0, "rechecked": rechecked, "studies": studies or 0,
        "duels": duels or 0,
        "deepseek_calls": steps.deepseek_calls(t0, t1), "backlog": left,
        "paused_min": round(paused / 60, 1),
    }


def text_it(s: dict) -> str:
    """The Telegram message: what the night did, in Italian."""
    def names(xs: list[str]) -> str:
        return ", ".join(xs[:15]) + (f" e altri {len(xs) - 15}" if len(xs) > 15 else "") if xs else "nessuno"
    when = datetime.fromtimestamp(s.get("slot") or s.get("started") or time.time(), ROME)
    lines = [f"Ricerca {'leggera ' if s.get('light') else ''}delle {when:%H:%M} finita in {s.get('minutes', 0):g} min.",
             f"Progetti visti dalla scoperta: {s.get('discovered', 0) + s.get('skipped', 0)} "
             f"(tenuti {s.get('discovered', 0)}), entrati in esame: {s.get('examined', 0)}, "
             f"analizzati: {s.get('analysed', 0)}.",
             f"Entrati nelle arene: {names(s.get('entered') or [])}.",
             f"Usciti dalle arene: {names(s.get('left') or [])}.",
             f"Layer aggiornati: {s.get('layers', 0)}; ricontrolli DeepSeek: {s.get('rechecked', 0)}; "
             f"studi: {s.get('studies', 0)}; duelli della scala: {s.get('duels', 0)}.",
             f"Chiamate DeepSeek: {s.get('deepseek_calls', 0)}."]
    if s.get("paused_min"):
        lines.append(f"In pausa {s['paused_min']:g} min per lasciare il server alle ottimizzazioni.")
    if s.get("resumed"):
        lines.append("Ripresa dopo un riavvio del server: i conteggi coprono solo l'ultima parte, "
                     "entrati e usciti tutta la sera.")
    if s.get("stopped") == "window":
        left = sum((s.get("backlog") or {}).values())
        win = s.get("window_min") or settings.onchain_nightly_max_hours * 60
        lines.append((f"Fermata al limite di {win / 60:g} ore" if win >= 60 else f"Fermata al limite di {win:g} minuti")
                     + (f": restano {left} lavori in coda, li smaltisco nelle prossime ore." if left else "."))
    return "\n".join(lines)


async def _send(text: str) -> None:
    from app.notify import telegram
    await telegram.send_message(text)


async def run_night(slot: float, top: Callable[[], list[dict]], *, steps_factory=Steps,
                    clock: Callable[[], float] = time.time, sleep=asyncio.sleep, send=_send) -> dict:
    """Runs the night of `slot`, remembering it so that a restart neither
    reruns nor skips it."""
    global _running
    now = clock()
    if _state.get("slot") != slot:
        _state.update(slot=slot, first_start=now, attempts=0, top_before=_top_map(top))
    _state["attempts"] = (_state.get("attempts") or 0) + 1
    _state["attempt_host"] = _host()
    _save()
    deadline = max(_state["first_start"] + window_s(slot), now + RESUME_MIN_S)
    _running = True
    try:
        async with _research_lock, \
                httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "Mozilla/5.0 (LiquidityEngine)"}) as client:
            summary = await run_once(top, steps_factory(client), deadline, clock=clock, sleep=sleep,
                                     top_before=_state.get("top_before"), light=is_light_run(slot))
    except asyncio.CancelledError:
        # A clean stop (a deploy) is not a failed try: only crashes count
        # towards MAX_ATTEMPTS, so evening deploys never drop the night.
        _state["attempts"] = max(0, (_state.get("attempts") or 1) - 1)
        _save()
        raise
    finally:
        _running = False
    summary["resumed"] = _state["first_start"] < now
    summary["slot"] = slot
    _state.update(done_slot=slot, last_run=summary["ended"], summary=summary)
    _save()
    summary["window_min"] = round(window_s(slot) / 60)
    # 24 runs a day: an hourly run writes only when the Top changed.
    if not settings.onchain_nightly_hourly or is_main_run(slot) or summary.get("entered") or summary.get("left"):
        try:
            await send(text_it(summary))
        except Exception:
            logger.exception("nightly: Telegram summary not sent")
    return summary


async def _gave_up(now: float, send) -> None:
    """One message when a night crashed MAX_ATTEMPTS times: never silent."""
    slot = latest_slot(now)
    if _state.get("slot") != slot or (_state.get("done_slot") or 0) >= slot or _state.get("gave_up") == slot \
            or (_state.get("attempts") or 0) < MAX_ATTEMPTS:
        return
    _state["gave_up"] = slot
    _save()
    try:
        nxt = datetime.fromtimestamp(next_run(now), ROME)
        await send(f"Ricerca delle {datetime.fromtimestamp(slot, ROME):%H:%M} interrotta: e' fallita "
                   f"{MAX_ATTEMPTS} volte, riprova alle {nxt:%H:%M}. Vedi i log del server.")
    except Exception:
        logger.exception("nightly: give-up note not sent")


async def nightly_loop(top: Callable[[], list[dict]], *, clock: Callable[[], float] = time.time,
                       sleep=asyncio.sleep, steps_factory=Steps, send=_send) -> None:
    """Sleeps until the night's hour, runs it, sleeps again. `top()` gives
    the Top 50 entries (main._top_entries)."""
    from app.trading.onchain import leaderboard
    _load()
    if forgive_redeploy():
        logger.info("nightly: last attempt was cut by a deploy, not counted")
    await sleep(START_DELAY_S)
    leaderboard.startup_requeue()
    try:                            # a night due now measures usage itself
        if due_slot(clock(), _state) is None:
            await leaderboard.warm_usage()
    except Exception:
        logger.exception("nightly: usage warm-up failed")
    while True:
        try:
            now = clock()
            slot = due_slot(now, _state)
            key = forced_due(_state)
            if slot is None and key:
                # Outside the clock: the run's slot is now, so the next
                # scheduled run still sees itself as due.
                _consume_force(key)
                await run_night(now, top, steps_factory=steps_factory, clock=clock, sleep=sleep, send=send)
                continue
            if slot is None:
                await _gave_up(now, send)
                # At most an hour at a time: a changed clock or setting is seen soon.
                await sleep(min(max(next_run(now) - now, 1.0), 3600.0))
                continue
            _consume_force(key)    # a scheduled run due now already covers it
            await run_night(slot, top, steps_factory=steps_factory, clock=clock, sleep=sleep, send=send)
        except Exception:
            logger.exception("nightly: run failed")
            await sleep(600)


async def sentinel_once(steps, *, clock: Callable[[], float] = time.time, sleep=asyncio.sleep) -> int:
    """One sentinel round: light ticks until nothing new waits (at least
    SENTINEL_MIN_TICKS, at most SENTINEL_MAX_S), then the alerts. Returns
    the ticks."""
    from app.trading.onchain import leaderboard
    end = clock() + SENTINEL_MAX_S
    ticks = 0
    while clock() < end:
        await _guard("sentinel", steps.light_tick())
        ticks += 1
        await sleep(leaderboard.TICK_S)
        if ticks >= SENTINEL_MIN_TICKS and steps.quiet():
            break
    await _guard("settle", steps.settle(SENTINEL_SETTLE_S))
    await _guard("alerts", steps.alerts())
    return ticks


def _left(steps) -> int:
    backlog = getattr(steps, "backlog", None)
    return sum((backlog() or {}).values()) if backlog else 0


def _rome_day(now: float) -> str:
    return datetime.fromtimestamp(now, ROME).strftime("%Y-%m-%d")


def drain_due(steps, now: float) -> bool:
    """A backlog to drain, the drain not stalled today, the next run far enough."""
    if (_state.get("drain") or {}).get("stalled_day") == _rome_day(now):
        return False
    return next_run(now) - now > DRAIN_GAP_S + 60 and _left(steps) > 0


async def drain_once(steps, *, clock: Callable[[], float] = time.time, sleep=asyncio.sleep) -> int:
    """One drain round: full ticks until the backlog is empty (at least
    SENTINEL_MIN_TICKS), DRAIN_MAX_S or DRAIN_GAP_S before the next run;
    then the alerts. Returns the ticks."""
    from app.trading.onchain import leaderboard
    start = clock()
    end = min(start + DRAIN_MAX_S, next_run(start) - DRAIN_GAP_S)
    before = _left(steps)
    ticks = 0
    while clock() < end:
        await _guard("drain", steps.tick())
        ticks += 1
        await sleep(leaderboard.TICK_S)
        if ticks >= SENTINEL_MIN_TICKS and steps.drained():
            break
    await _guard("settle", steps.settle(SENTINEL_SETTLE_S))
    await _guard("alerts", steps.alerts())
    after = _left(steps)
    d = _state.setdefault("drain", {})
    d.update(last_at=round(clock()), before=before, after=after, ticks=ticks,
             rounds=int(d.get("rounds") or 0) + 1)
    if after >= before:
        d["stalled_day"] = _rome_day(clock())
    _save()
    return ticks


async def sentinel_loop(*, clock: Callable[[], float] = time.time, sleep=asyncio.sleep,
                        steps_factory=Steps) -> None:
    """A sentinel round every SENTINEL_EVERY_S, skipped while a research
    run or an optimization is on."""
    await sleep(START_DELAY_S * 2)
    while True:
        try:
            if settings.onchain_sentinel_enabled and not _research_lock.locked():
                async with _research_lock, \
                        httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "Mozilla/5.0 (LiquidityEngine)"}) as client:
                    steps = steps_factory(client)
                    if steps.busy():
                        _sentinel_note(clock(), skipped="an optimization is running")
                    elif drain_due(steps, clock()):
                        await drain_once(steps, clock=clock, sleep=sleep)
                    else:
                        start = clock()
                        ticks = await sentinel_once(steps, clock=clock, sleep=sleep)
                        _sentinel_note(clock(), ticks=ticks, secs=clock() - start)
            elif settings.onchain_sentinel_enabled:
                _sentinel_note(clock(), skipped="a research run is on")
        except Exception as exc:
            logger.exception("sentinel: round failed")
            _sentinel_note(clock(), error=f"{type(exc).__name__}: {exc}"[:200])
        await sleep(SENTINEL_EVERY_S)


def _sentinel_note(now: float, *, ticks: int | None = None, secs: float | None = None,
                   skipped: str = "", error: str = "") -> None:
    """The sentinel's last round, kept with the research state (the app logs
    no INFO lines, so this is what shows it runs): GET /api/agent/activity."""
    s = _state.setdefault("sentinel", {})
    s["last_at"] = round(now)
    if ticks is not None:
        s.update(last_round_at=round(now), ticks=ticks, secs=round(secs or 0), rounds=int(s.get("rounds") or 0) + 1)
    s["skipped"] = skipped or None
    if error:
        s.update(error=error, error_at=round(now))
    _save()


def loop_plan(radar_enabled: bool, nightly_enabled: bool) -> list[str]:
    """Which research loops the server starts (main.lifespan). The nightly
    run replaces the five around-the-clock loops; without the radar there is
    no gem research, and the studies keep their own loop as before."""
    if not radar_enabled:
        return ["studies"]
    # The free AI's veto (ai_veto.py) reads the Top's door around the clock.
    if nightly_enabled:
        return ["nightly", "sentinel", "ai_veto"]
    return ["leaderboard", "sweep", "outcomes", "layers", "studies", "ai_veto"]
