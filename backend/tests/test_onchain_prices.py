"""Prezzo USD del gas token, per la hero della UI. Verificato anche con
una vera chiamata di rete (GeckoTerminal e' pubblico, nessuna chiave) —
lo stesso spirito di test_jupiter_quote_real_network_call."""
from __future__ import annotations

import asyncio

import httpx

from app.trading.onchain import live_prices, prices

_RealAsyncClient = httpx.AsyncClient


def _run(coro):
    return asyncio.run(coro)


def _client_factory(handler):
    def factory(*args, **kwargs):
        transport = httpx.MockTransport(handler)
        kwargs.pop("proxies", None)
        return _RealAsyncClient(*args, transport=transport, **kwargs)
    return factory


def test_native_price_usd_real_network_call_solana():
    prices._cache.clear()
    price = _run(prices.native_price_usd("solana"))
    assert price is not None
    assert price > 0


def test_native_price_usd_real_network_call_robinhood():
    prices._cache.clear()
    price = _run(prices.native_price_usd("robinhood"))
    assert price is not None
    assert price > 0


def test_native_price_usd_returns_none_on_http_error(monkeypatch):
    prices._cache.clear()
    live_prices.reset_for_tests()     # the fallback's cache: no price from an earlier test

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(handler))
    assert _run(prices.native_price_usd("solana")) is None


def test_native_price_usd_falls_back_to_live_prices_when_gecko_fails(monkeypatch):
    prices._cache.clear()

    async def gecko(network, addr):
        return None

    async def live(keys):
        return {f"{keys[0][0]}:{keys[0][1]}": {"p": 150.0, "age": 0.0, "src": "jupiter"}}

    monkeypatch.setattr(prices, "_gecko_price", gecko)
    monkeypatch.setattr(live_prices, "prices", live)
    assert _run(prices.native_price_usd("solana")) == 150.0


def test_native_price_usd_returns_none_on_malformed_payload(monkeypatch):
    prices._cache.clear()
    live_prices.reset_for_tests()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"attributes": {}}})

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(handler))
    assert _run(prices.native_price_usd("solana")) is None


def test_native_price_usd_is_cached_within_ttl(monkeypatch):
    prices._cache.clear()
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json={
            "data": {"attributes": {"token_prices": {"So111...": "123.45"}}},
        })

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(handler))
    first = _run(prices.native_price_usd("solana"))
    after_first = calls["count"]
    second = _run(prices.native_price_usd("solana"))
    assert first == second == 123.45
    assert after_first >= 1 and calls["count"] == after_first     # the second read is the cache


def _kraken(price: str):
    return {"error": [], "result": {"XXBTZUSD": {"c": [price, "0.1"]}}}


def test_btc_price_usd_reads_kraken_last_trade(monkeypatch):
    prices._btc_cache = None

    def handler(request: httpx.Request) -> httpx.Response:
        assert "kraken" in str(request.url)
        return httpx.Response(200, json=_kraken("84000.5"))

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(handler))
    assert _run(prices.btc_price_usd()) == 84000.5


def test_btc_price_usd_returns_none_on_error_or_bad_payload(monkeypatch):
    for response in (
        httpx.Response(500, text="boom"),
        httpx.Response(200, json={"error": ["EQuery:Unknown asset pair"], "result": {}}),
        httpx.Response(200, json={"error": [], "result": {"X": {}}}),
        httpx.Response(200, json=_kraken("0")),
    ):
        prices._btc_cache = None
        monkeypatch.setattr(httpx, "AsyncClient", _client_factory(lambda request, r=response: r))
        assert _run(prices.btc_price_usd()) is None
