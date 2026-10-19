"""Lorenzo, 19/10: every GeckoTerminal request through one window."""
import asyncio
import time

import httpx

from app.providers import gecko_client as g


class _Client:
    def __init__(self, statuses, headers=None):
        self.statuses, self.headers, self.sent = list(statuses), headers or {}, []

    async def get(self, url, **kw):
        self.sent.append((url, kw))
        code = self.statuses.pop(0) if self.statuses else 200
        return httpx.Response(code, headers=self.headers if code == 429 else {}, json={},
                              request=httpx.Request("GET", url))


def test_background_and_urgent_share_one_ceiling():
    now = time.monotonic()
    background, top = g.caps()
    g.calls.extend([now] * background)

    async def run():
        tok = g.urgent.set(True)
        try:
            await asyncio.wait_for(g.slot("chart"), 0.5)          # a person still gets through
        finally:
            g.urgent.reset(tok)
        try:
            await asyncio.wait_for(g.slot("background"), 0.2)     # the background waits
            return "passed"
        except asyncio.TimeoutError:
            return "waited"
    assert asyncio.run(run()) == "waited"
    g.calls.extend([now] * (top - len(g.calls)))

    async def urgent_full():
        tok = g.urgent.set(True)
        try:
            await asyncio.wait_for(g.slot("chart"), 0.2)
            return "passed"
        except asyncio.TimeoutError:
            return "waited"
        finally:
            g.urgent.reset(tok)
    assert asyncio.run(urgent_full()) == "waited"                  # urgent is inside the ceiling


def test_a_429_makes_every_caller_wait_its_retry_after():
    c = _Client([429], headers={"Retry-After": "2"})
    r = asyncio.run(g.request(c, "https://api.geckoterminal.com/x", caller="scanner"))
    assert r.status_code == 429
    assert 1.5 < g.metrics()["cooldown_s"] <= 2.0
    m = g.metrics()["by_caller"]["scanner"]
    assert m["requests"] == 1 and m["http_429"] == 1


def test_retry_after_forms():
    resp = lambda h: httpx.Response(429, headers=h, request=httpx.Request("GET", "https://x"))  # noqa: E731
    assert g.retry_after_s(resp({})) == g.DEFAULT_COOLDOWN_S
    assert g.retry_after_s(resp({"Retry-After": "7"})) == 7.0
    assert g.retry_after_s(resp({"Retry-After": "99999"})) == g.MAX_COOLDOWN_S
    assert g.retry_after_s(resp({"Retry-After": "soon"})) == g.DEFAULT_COOLDOWN_S


def test_the_counters_tell_ohlcv_from_the_rest():
    c = _Client([200, 200, 500])
    asyncio.run(g.request(c, "https://api.geckoterminal.com/a", caller="ohlcv:chart"))
    asyncio.run(g.request(c, "https://api.geckoterminal.com/b", caller="discovery"))
    asyncio.run(g.request(c, "https://api.geckoterminal.com/c", caller="discovery"))
    g.cache_hit("ohlcv:chart")
    m = g.metrics()
    assert m["ohlcv_requests"] == 1 and m["other_requests"] == 2
    assert m["by_caller"]["discovery"]["errors"] == 1 and m["by_caller"]["ohlcv:chart"]["cache_hits"] == 1


def test_a_transport_error_is_counted_and_raised():
    class Broken:
        async def get(self, url, **kw):
            raise httpx.ConnectTimeout("slow")
    try:
        asyncio.run(g.request(Broken(), "https://api.geckoterminal.com/a", caller="radar"))
        raise AssertionError("no error")
    except httpx.ConnectTimeout:
        pass
    assert g.metrics()["by_caller"]["radar"]["errors"] == 1


def test_metrics_are_saved_for_a_look_from_outside(tmp_path):
    p = tmp_path / "gecko_metrics.json"
    assert g.save(p, now=1_000.0) and p.exists()
    assert not g.save(p, now=1_010.0)                              # every 5 minutes


def test_the_limit_is_learned_from_the_429s():
    """19/10: GeckoTerminal refused 36% at 13 a minute; the limit follows it."""
    g._state["limit"] = float(g.START_PER_MIN)
    start = g.caps()[1]
    asyncio.run(g.request(_Client([429], headers={"Retry-After": "0"}), "https://x", caller="usage"))
    lowered = g.caps()[1]
    assert lowered < start
    asyncio.run(g.request(_Client([429], headers={"Retry-After": "0"}), "https://x", caller="usage"))
    assert g.caps()[1] < lowered
    for _ in range(40):
        g.calls.clear()
        asyncio.run(g.request(_Client([429], headers={"Retry-After": "0"}), "https://x", caller="usage"))
    assert g.caps()[1] == g.MIN_PER_MIN
    now = time.monotonic()
    assert g.caps(now + 3 * g.RAISE_EVERY_S + 1)[1] == g.MIN_PER_MIN + 3
    assert g.caps(now + 1000 * g.RAISE_EVERY_S)[1] == g.GLOBAL_PER_MIN
