"""The nightly research run (nightly.py): the clock, the catch-up after a
restart, the loop choice in lifespan and the window that stops the run."""
import asyncio
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.config import settings
from app.trading.onchain import nightly

ROME = ZoneInfo("Europe/Rome")


def ts(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=ROME).timestamp()


def rome(t):
    return datetime.fromtimestamp(t, ROME)


@pytest.fixture(autouse=True)
def _fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(nightly, "_FILE", tmp_path / "onchain_nightly.json")
    monkeypatch.setattr(settings, "onchain_nightly_hour", 22)
    monkeypatch.setattr(settings, "onchain_nightly_extra_times", "")
    monkeypatch.setattr(settings, "onchain_nightly_max_hours", 2.0)
    monkeypatch.setattr(settings, "onchain_nightly_force", "")
    monkeypatch.setattr(settings, "onchain_nightly_hourly", False)
    monkeypatch.setattr(nightly, "_host", lambda: "c1")
    nightly.reset_for_tests()
    yield
    nightly.reset_for_tests()


def test_next_run_around_the_hour():
    assert nightly.next_run(ts(2026, 10, 7, 21, 59)) == ts(2026, 10, 7, 22)
    # exactly at 22:00 the next one is tomorrow's
    assert nightly.next_run(ts(2026, 10, 7, 22)) == ts(2026, 10, 8, 22)
    assert nightly.next_run(ts(2026, 10, 7, 23, 30)) == ts(2026, 10, 8, 22)
    assert nightly.next_run(ts(2026, 10, 8, 1)) == ts(2026, 10, 8, 22)


@pytest.mark.parametrize("before,after", [((2026, 10, 24), (2026, 10, 25)),   # summer time ends
                                          ((2026, 3, 28), (2026, 3, 29))])    # summer time starts
def test_next_run_across_dst(before, after):
    nxt = nightly.next_run(ts(*before, 22, 30))
    assert rome(nxt).hour == 22 and rome(nxt).date() == datetime(*after).date()
    # the day is 25 or 23 hours long: the local hour stays 22:00
    assert nxt - ts(*before, 22) in (25 * 3600, 23 * 3600)


def test_second_run_at_11_35(monkeypatch):
    monkeypatch.setattr(settings, "onchain_nightly_extra_times", "11:35, bad, 25:00")
    assert nightly.run_times() == [(11, 35), (22, 0)]
    assert nightly.next_run(ts(2026, 10, 7, 23)) == ts(2026, 10, 8, 11, 35)
    assert nightly.next_run(ts(2026, 10, 8, 11, 35)) == ts(2026, 10, 8, 22)
    assert nightly.latest_slot(ts(2026, 10, 8, 15)) == ts(2026, 10, 8, 11, 35)
    morning = ts(2026, 10, 8, 11, 35)
    # the evening done does not hide the morning; the morning done does not hide the evening
    assert nightly.due_slot(ts(2026, 10, 8, 12), {"done_slot": ts(2026, 10, 7, 22)}) == morning
    assert nightly.due_slot(ts(2026, 10, 8, 12), {"done_slot": morning}) is None
    assert nightly.due_slot(ts(2026, 10, 8, 22, 5), {"done_slot": morning}) == ts(2026, 10, 8, 22)
    assert nightly.due_slot(ts(2026, 10, 8, 11, 34), {"done_slot": ts(2026, 10, 7, 22)}) is None


def test_boot_after_the_hour_runs_tonight_now():
    slot = ts(2026, 10, 7, 22)
    assert nightly.due_slot(ts(2026, 10, 7, 23), {}) == slot
    assert nightly.due_slot(ts(2026, 10, 8, 1), {"done_slot": ts(2026, 10, 6, 22)}) == slot
    # tonight already done: nothing until tomorrow
    assert nightly.due_slot(ts(2026, 10, 7, 23), {"done_slot": slot}) is None
    # a boot in the afternoon does not catch up last night: it waits for 22:00
    assert nightly.due_slot(ts(2026, 10, 8, 15), {}) is None
    assert nightly.due_slot(ts(2026, 10, 7, 21, 59), {}) is None
    # an interrupted run is resumed, but not forever
    assert nightly.due_slot(ts(2026, 10, 7, 22, 40), {"slot": slot, "attempts": 1}) == slot
    assert nightly.due_slot(ts(2026, 10, 7, 22, 40), {"slot": slot, "attempts": nightly.MAX_ATTEMPTS}) is None


def test_loop_plan_follows_the_flag():
    assert nightly.loop_plan(True, True) == ["nightly", "sentinel", "ai_veto"]
    assert nightly.loop_plan(True, False) == ["leaderboard", "sweep", "outcomes", "layers", "studies", "ai_veto"]
    assert nightly.loop_plan(False, True) == ["studies"]
    assert nightly.loop_plan(False, False) == ["studies"]


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t

    async def sleep(self, s):
        self.t += s


class FakeSteps:
    """Never drained: only the window can stop the ticks."""

    def __init__(self, clock, drained_after=None, recheck_keys=()):
        self.clock, self.ticks, self.drained_after = clock, 0, drained_after
        self.order, self.left = [], list(recheck_keys)
        self.c = {"discovered": 0, "skipped": 0, "examined": 0, "analysed": 0}

    async def tick(self):
        self.ticks += 1
        self.c["analysed"] += 2
        self.clock.t += 20          # a tick takes time too

    def drained(self):
        return self.drained_after is not None and self.ticks >= self.drained_after

    def backlog(self):
        return {"running": 0, "unanalysed": 0, "database": 0 if self.drained() else 7, "discovery": 0}

    async def settle(self, timeout):
        self.order.append("settle")

    async def alerts(self):
        self.order.append("alerts")

    def counters(self):
        return dict(self.c)

    async def layers(self):
        self.order.append("layers")
        return 3

    async def outcomes(self):
        self.order.append("outcomes")

    def next_recheck(self, keys):
        return self.left[0] if self.left else None

    async def recheck(self, key):
        self.order.append("recheck")
        self.left.pop(0)
        self.clock.t += 600
        return "done"

    async def studies(self):
        self.order.append("studies")
        return 1

    def deepseek_calls(self, start, end):
        return 4


def test_window_stops_the_run_at_max_hours():
    clock = Clock(ts(2026, 10, 7, 22))
    deadline = clock.t + 2 * 3600
    steps = FakeSteps(clock, recheck_keys=[f"solana:T{i}" for i in range(50)])
    tops = iter([[{"chain": "solana", "token_address": "A", "symbol": "AAA"},
                  {"chain": "solana", "token_address": "B", "symbol": "BBB"}],
                 [{"chain": "solana", "token_address": "B", "symbol": "BBB"},
                  {"chain": "base", "token_address": "C", "symbol": "CCC"}]])
    last = []

    def top():
        last[:] = next(tops, last)
        return last
    s = asyncio.run(nightly.run_once(top, steps, deadline, clock=clock, sleep=clock.sleep))
    assert s["stopped"] == "window"
    # the ticks used their share, the re-check the rest; studies once at the end
    assert clock.t - deadline < 700
    assert s["ticks"] == int(2 * 3600 * nightly.RESEARCH_SHARE // 30)    # 20 s of work + 10 s of pause
    # the alerts after the settle, after every re-check and once at the end:
    # no tick runs there (Lorenzo, 17/10: the gems chat heard nothing)
    assert steps.order[:4] == ["settle", "alerts", "layers", "outcomes"] and steps.order[-2:] == ["studies", "alerts"]
    assert steps.order.count("alerts") == 2 + steps.order.count("recheck")
    assert 0 < s["rechecked"] < 50
    assert s["entered"] == ["CCC"] and s["left"] == ["AAA"]
    assert s["analysed"] == 2 * s["ticks"] and s["deepseek_calls"] == 4 and s["layers"] == 3
    text = nightly.text_it(s)
    assert "Entrati nelle arene: CCC" in text and "Usciti dalle arene: AAA" in text
    assert "Fermata al limite di 2 ore: restano 7 lavori" in text


def test_drained_queue_ends_the_ticks_early():
    clock = Clock(ts(2026, 10, 7, 22))
    steps = FakeSteps(clock, drained_after=nightly.MIN_TICKS + 5)
    s = asyncio.run(nightly.run_once(lambda: [], steps, clock.t + 7200, clock=clock, sleep=clock.sleep))
    assert s["stopped"] == "drained" and s["ticks"] == nightly.MIN_TICKS + 5


def test_run_night_remembers_the_night_and_sends_one_message(monkeypatch):
    clock = Clock(ts(2026, 10, 7, 23))
    sent = []

    async def send(text):
        sent.append(text)
    slot = nightly.due_slot(clock.t, nightly._state)
    s = asyncio.run(nightly.run_night(slot, lambda: [], steps_factory=lambda client: FakeSteps(clock, drained_after=1),
                                      clock=clock, sleep=clock.sleep, send=send))
    assert len(sent) == 1 and sent[0].startswith("Ricerca delle 22:00 finita")
    assert nightly.due_slot(clock.t, nightly._state) is None
    # a restart reads the night back from the file
    nightly.reset_for_tests()
    nightly._load()
    assert nightly._state["done_slot"] == slot and nightly._state["summary"]["ticks"] == s["ticks"]
    st = nightly.status(clock.t)
    assert st["last_run"] == s["ended"] and st["next_run"] == ts(2026, 10, 8, 22)


def test_backlog_counts_what_tonight_still_owes(monkeypatch):
    from app.trading.onchain import discovery, leaderboard as lb
    lb.reset_for_tests()
    monkeypatch.setattr(discovery, "status", lambda: {"queue": 0})
    try:
        assert lb.drained()
        lb.add({"chain": "solana", "token_address": "Tok1", "symbol": "TOK", "website": "https://tok.io"}, "manual")
        assert lb.backlog()["unanalysed"] == 1 and not lb.drained()
        lb._entries[lb._key("solana", "Tok1")]["pillars"] = {"site": {"score": 50}}
        assert lb.backlog()["unanalysed"] == 0
    finally:
        lb.reset_for_tests()


def test_a_project_added_by_hand_is_analysed_at_once(monkeypatch):
    """With the nightly run no tick comes before 22:00: analyze_now does the step."""
    from app.trading.onchain import leaderboard as lb
    lb.reset_for_tests()
    seen = []

    async def fake_analyze(k, skip, client):
        seen.append((k, skip))
        lb._busy.discard(k)
    monkeypatch.setattr(lb, "_analyze", fake_analyze)
    monkeypatch.setattr(lb, "_save", lambda: None)       # the board's file lives on the volume
    lb.add({"chain": "base", "token_address": "0xabc", "symbol": "ABC", "website": "https://abc.io"}, "manual")

    async def go():
        assert lb.analyze_now("base", "0xabc")
        assert not lb.analyze_now("base", "0xabc")       # already running
        assert not lb.analyze_now("base", "0xmissing")   # not in the working set
        await asyncio.gather(*list(lb._tasks))
    try:
        asyncio.run(go())
        assert seen == [(lb._key("base", "0xabc"), set())] and not lb._busy
        assert not lb.analyze_now("base", "0xabc")       # no running loop: nothing started
    finally:
        lb.reset_for_tests()


class _Stop(BaseException):
    pass


def test_forced_run_starts_at_boot_once(monkeypatch):
    from app.trading.onchain import leaderboard as lb
    monkeypatch.setattr(lb, "startup_requeue", lambda: None)

    async def warm():
        return None
    monkeypatch.setattr(lb, "warm_usage", warm)
    monkeypatch.setattr(settings, "onchain_nightly_extra_times", "11:35")
    monkeypatch.setattr(settings, "onchain_nightly_force", "k1")
    clock = Clock(ts(2026, 10, 8, 13, 40))
    nightly._state.update(done_slot=ts(2026, 10, 8, 11, 35))
    nightly._save()
    sent = []

    async def send(text):
        sent.append(text)

    async def sleep(s):
        if s >= 1000:
            raise _Stop
        clock.t += s
    with pytest.raises(_Stop):
        asyncio.run(nightly.nightly_loop(lambda: [], clock=clock, sleep=sleep, send=send,
                                         steps_factory=lambda client: FakeSteps(clock, drained_after=1)))
    assert len(sent) == 1 and nightly._state["forced"] == ["k1"]
    assert nightly.forced_due(nightly._state) is None
    # tonight's run is still due at 22:00
    assert nightly.due_slot(ts(2026, 10, 8, 22, 1), nightly._state) == ts(2026, 10, 8, 22)


# Lorenzo, 12/10: "la nostra selezione non e' molto popolata, aggiungi
# controllo ogni ora" — and the 22:00 run given up after three deploys.
def test_hourly_runs_every_whole_hour(monkeypatch):
    monkeypatch.setattr(settings, "onchain_nightly_hourly", True)
    monkeypatch.setattr(settings, "onchain_nightly_extra_times", "11:35")
    times = nightly.run_times()
    assert {(h, 0) for h in range(24)} <= set(times) and (11, 35) in times
    assert nightly.next_run(ts(2026, 10, 13, 9, 10)) == ts(2026, 10, 13, 10)
    assert nightly.is_main_run(ts(2026, 10, 13, 22)) and nightly.is_main_run(ts(2026, 10, 13, 11, 35))
    assert not nightly.is_main_run(ts(2026, 10, 13, 10))
    monkeypatch.setattr(settings, "onchain_hourly_max_minutes", 45.0)
    assert nightly.window_s(ts(2026, 10, 13, 10)) == 45 * 60
    assert nightly.window_s(ts(2026, 10, 13, 22)) == 2 * 3600


def test_a_deploy_does_not_count_as_a_failed_attempt():
    slot = ts(2026, 10, 12, 22)
    nightly._state.update(slot=slot, attempts=3, attempt_host="old-container", gave_up=slot)
    assert nightly.forgive_redeploy("new-container")
    assert nightly._state["attempts"] == 2 and "gave_up" not in nightly._state
    assert nightly.due_slot(ts(2026, 10, 12, 23, 50), nightly._state) == slot


def test_a_crash_in_the_same_container_still_counts():
    slot = ts(2026, 10, 12, 22)
    nightly._state.update(slot=slot, attempts=3, attempt_host="c1")
    assert not nightly.forgive_redeploy("c1")
    assert nightly.due_slot(ts(2026, 10, 12, 23, 50), nightly._state) is None


def test_hourly_run_is_quiet_unless_the_top_changed(monkeypatch):
    monkeypatch.setattr(settings, "onchain_nightly_hourly", True)
    sent = []

    async def send(text):
        sent.append(text)

    class Quiet:
        def __init__(self, client): ...
        async def tick(self): ...
        def drained(self): return True
        def backlog(self): return {}
        async def settle(self, timeout): ...
        async def alerts(self): ...
        def counters(self): return {"discovered": 0, "skipped": 0, "examined": 0, "analysed": 0}
        async def layers(self): return 0
        async def outcomes(self): ...
        def next_recheck(self, keys): return None
        async def recheck(self, key): return "done"
        async def studies(self): return 0
        def deepseek_calls(self, a, b): return 0

    monkeypatch.setattr(nightly, "_duels", lambda top, now: asyncio.sleep(0, result=0))
    clock = Clock(ts(2026, 10, 13, 10))
    asyncio.run(nightly.run_night(ts(2026, 10, 13, 10), lambda: [], steps_factory=Quiet,
                                  clock=clock, sleep=clock.sleep, send=send))
    assert sent == []
    clock2 = Clock(ts(2026, 10, 13, 22))
    asyncio.run(nightly.run_night(ts(2026, 10, 13, 22), lambda: [], steps_factory=Quiet,
                                  clock=clock2, sleep=clock2.sleep, send=send))
    assert len(sent) == 1


def test_the_research_waits_while_an_optimization_runs(monkeypatch):
    # Lorenzo, 13/10: "la ricerca gemme si mette in pausa e riprende appena finisce"
    clock = Clock(ts(2026, 10, 13, 22))
    busy_until = clock() + 600
    ticks_while_busy = []

    class Steps:
        def __init__(self, client=None): ...
        def busy(self): return clock() < busy_until
        async def tick(self): ticks_while_busy.append(self.busy())
        def drained(self): return True
        def backlog(self): return {}
        async def settle(self, timeout): ...
        async def alerts(self): ...
        def counters(self): return {"discovered": 0, "skipped": 0, "examined": 0, "analysed": 0}
        async def layers(self): return 0
        async def outcomes(self): ...
        def next_recheck(self, keys): return None
        async def recheck(self, key): return "done"
        async def studies(self): return 0
        def deepseek_calls(self, a, b): return 0

    monkeypatch.setattr(nightly, "_duels", lambda top, now: asyncio.sleep(0, result=0))

    async def go():
        return await nightly.run_once(lambda: [], Steps(), clock() + 3600, clock=clock, sleep=clock.sleep)
    s = asyncio.run(go())
    assert ticks_while_busy and not any(ticks_while_busy)
    assert s["paused_min"] >= 10
    assert "In pausa" in nightly.text_it(s)


def test_shipped_schedule_is_a_full_run_at_4_and_a_light_one_at_16(monkeypatch):
    # Lorenzo, 19/10: "procedi con 04:00 e 16:00 e la ricerca leggera".
    from app.config import Settings
    s = Settings()
    assert (s.onchain_nightly_hour, s.onchain_nightly_extra_times, s.onchain_nightly_hourly) == (4, "16:00", False)
    assert s.onchain_nightly_max_hours >= 6 and s.onchain_nightly_light_times == "16:00"
    for k in ("onchain_nightly_hour", "onchain_nightly_extra_times", "onchain_nightly_hourly",
              "onchain_nightly_light_times", "onchain_nightly_light_max_hours", "onchain_nightly_max_hours"):
        monkeypatch.setattr(settings, k, getattr(s, k))
    assert nightly.run_times() == [(4, 0), (16, 0)]
    night, afternoon = (nightly._slot_on(date(2026, 10, 20), h) for h in (4, 16))
    assert not nightly.is_light_run(night) and nightly.is_light_run(afternoon)
    assert nightly.window_s(night) == 6 * 3600 and nightly.window_s(afternoon) == 2.5 * 3600


def test_the_light_run_ticks_light_and_skips_the_night_work():
    clock = _Clock()

    async def sleep(s):
        clock.t += s

    class Light(FakeSteps):
        async def light_tick(self):
            self.order.append("light")
            await self.tick()

        def quiet(self):
            return self.ticks >= 3

        def deepseek_calls(self, a, b):
            return 0

    steps = Light(clock)
    s = asyncio.run(nightly.run_once(lambda: [], steps, clock.t + 9000, clock=clock, sleep=sleep, light=True))
    assert s["light"] and s["stopped"] == "drained" and s["ticks"] == max(3, nightly.MIN_TICKS)
    assert "light" in steps.order and "layers" not in steps.order and "outcomes" not in steps.order
    assert steps.order[-1] == "alerts"
    assert "leggera" in nightly.text_it({**s, "slot": nightly._slot_on(date(2026, 10, 20), 16)})


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class _SentinelSteps:
    def __init__(self, clock, quiet_after=None):
        self.clock, self.ticks, self.quiet_after, self.order = clock, 0, quiet_after, []

    async def light_tick(self):
        self.ticks += 1
        self.clock.t += 5

    def quiet(self):
        return self.quiet_after is not None and self.ticks >= self.quiet_after

    async def settle(self, timeout):
        self.order.append("settle")

    async def alerts(self):
        self.order.append("alerts")


def test_the_sentinel_stops_when_nothing_new_waits():
    """Lorenzo, 18/10: a light round between the runs, alerts at once."""
    clock = _Clock()

    async def sleep(s):
        clock.t += s
    steps = _SentinelSteps(clock, quiet_after=1)
    assert asyncio.run(nightly.sentinel_once(steps, clock=clock, sleep=sleep)) == nightly.SENTINEL_MIN_TICKS
    assert steps.order == ["settle", "alerts"]


def test_the_sentinel_round_is_bounded():
    clock = _Clock()

    async def sleep(s):
        clock.t += s
    steps = _SentinelSteps(clock)              # always something new
    ticks = asyncio.run(nightly.sentinel_once(steps, clock=clock, sleep=sleep))
    assert clock.t <= nightly.SENTINEL_MAX_S + 20 and ticks < nightly.SENTINEL_MAX_S / 10 + 1


def test_the_sentinel_leaves_a_trace_of_each_round(monkeypatch):
    """19/10: the app logs no INFO lines, so the last round is kept in the
    research state and shown by status() (Lorenzo: "controlla che la
    sentinella si attiva e lavori senza problemi")."""
    monkeypatch.setattr(nightly, "_state", {})
    monkeypatch.setattr(settings, "onchain_sentinel_enabled", True)
    clock = _Clock()

    class Steps(_SentinelSteps):
        def busy(self):
            return False

    async def sleep(s):
        if s == nightly.SENTINEL_EVERY_S:
            raise asyncio.CancelledError
        clock.t += s
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(nightly.sentinel_loop(clock=clock, sleep=sleep, steps_factory=lambda c: Steps(clock, quiet_after=1)))
    s = nightly.status(now=clock.t)["sentinel"]
    assert s["enabled"] and s["rounds"] == 1 and s["ticks"] == nightly.SENTINEL_MIN_TICKS and not s["skipped"]
    assert s["last_round_at"] == round(clock.t)
