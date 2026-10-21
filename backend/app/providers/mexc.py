import asyncio

import httpx

from app import http_client
import pandas as pd
from cachetools import TTLCache

from app.providers.base import DataProvider, ProviderError, ProviderUnreachable
from app.timeframes import INTERVAL_SECONDS

BASE_URL = "https://api.mexc.com"
_CANONICAL_TO_INTERVAL = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "60m",
    "4h": "4h",
    "1d": "1d",
    "1w": "1W",
    "1M": "1M",
}
# MEXC's spot market has no bare-USD-quoted pairs (verified against /api/v3/exchangeInfo) —
# only USDT/USDC/etc. A trailing "USD" is normalized away below, not treated as already-quoted.
_QUOTE_ASSETS = ["USDT", "USDC", "FDUSD", "TUSD", "DAI", "BTC", "ETH"]
_MAX_SUGGESTIONS = 25

_symbols_cache: TTLCache = TTLCache(maxsize=1, ttl=3600)
_last_good: dict[str, list[dict]] = {}


def format_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper().replace("/", "").replace("-", "")
    for quote in _QUOTE_ASSETS:
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return symbol
    if symbol.endswith("USD") and len(symbol) > 3:
        symbol = symbol[:-3]
    return f"{symbol}USDT"


class MexcProvider(DataProvider):
    """Crypto only — public market data, no API key required."""

    # MEXC's klines endpoint caps a single request at 500 rows. A caller
    # asking for more than that (the backtest fetch does — it wants the
    # deepest history the exchange actually has) gets it via pagination:
    # walk endTime backwards one page at a time until either outputsize is
    # satisfied or a page comes back short/empty, which means the listing
    # date has been reached and there's nothing earlier to fetch.
    _PAGE_LIMIT = 500
    _MAX_PAGES = 40   # 40 x 500 = 20000 = settings.backtest_candles
    _MAX_PAGES_SINCE = 10000
    _PARALLEL_PAGES = 5

    def __init__(self, base_url: str | None = None):
        self._base_url = base_url or BASE_URL

    async def fetch_ohlcv(self, symbol: str, interval: str, outputsize: int, since_ms: int | None = None) -> pd.DataFrame:
        formatted_symbol = format_symbol(symbol)
        api_interval = _CANONICAL_TO_INTERVAL[interval]
        # MEXC silently ignores a lone endTime (no startTime) and just
        # returns the latest `limit` candles again — verified empirically,
        # not documented. A startTime windowing the page is required for
        # endTime to actually take effect, so every paginated request after
        # the first carries both.
        interval_ms = INTERVAL_SECONDS[interval] * 1000

        rows: list[list] = []
        max_pages = self._MAX_PAGES_SINCE if since_ms is not None else self._MAX_PAGES
        remaining = int(1e9) if since_ms is not None else outputsize

        async def page(client, limit: int, end_time: int | None) -> list:
            params = {"symbol": formatted_symbol, "interval": api_interval, "limit": limit}
            if end_time is not None:
                params["endTime"] = end_time
                params["startTime"] = end_time - limit * interval_ms
            resp = await client.get(f"{self._base_url}/api/v3/klines", params=params)
            try:
                payload = resp.json()
            except ValueError as exc:
                raise ProviderError(f"Invalid response from MEXC for {formatted_symbol}") from exc
            if isinstance(payload, dict) and "code" in payload:
                raw = payload.get("msg", "unknown error")
                raise ProviderError(
                    f"MEXC does not recognize {formatted_symbol}: {raw}. "
                    f"Check it is written the way MEXC writes it, e.g. BTCUSDT."
                )
            return payload or []

        try:
            async with http_client.pooled(timeout=30.0) as client:
                # Each full page ends exactly limit candles before the previous
                # one, so the windows of the next pages are known in advance:
                # a few go out together instead of one round trip each (BTC
                # on 5d walked 6 pages back to back, ~2 s of the chart's
                # load). Pages past the first short or empty one are dropped,
                # so the result is the same as the old one-by-one walk. "1M"
                # has no fixed length: one page at a time there.
                batch = 1 if interval == "1M" else self._PARALLEL_PAGES
                end_time: int | None = None
                pages_done = 0
                first = True
                while pages_done < max_pages and remaining > 0:
                    plan: list[tuple[int, int | None]] = []
                    left, end = remaining, end_time
                    for _ in range(1 if first else min(batch, max_pages - pages_done)):
                        if left <= 0:
                            break
                        limit = min(left, self._PAGE_LIMIT)
                        plan.append((limit, end))
                        left -= limit
                        if end is not None:
                            end -= limit * interval_ms
                    first = False
                    results = await asyncio.gather(*(page(client, lim, e) for lim, e in plan))
                    stop = False
                    for (limit, _), payload in zip(plan, results):
                        pages_done += 1
                        if not payload:
                            stop = True
                            break
                        rows.extend(payload)
                        remaining -= len(payload)
                        earliest = min(int(row[0]) for row in payload)
                        end_time = earliest - 1
                        if len(payload) < limit:
                            stop = True  # short page — reached the symbol's listing date
                            break
                        if since_ms is not None and earliest <= since_ms:
                            stop = True  # reached the requested origin
                            break
                    if stop:
                        break
        except httpx.HTTPError as exc:
            if not rows:
                raise ProviderUnreachable(f"MEXC unreachable for {formatted_symbol}: {exc}") from exc

        if not rows:
            raise ProviderError(f"No data available for {formatted_symbol} ({api_interval})")

        # [openTime_ms, open, high, low, close, volume, closeTime_ms, quoteVolume]
        df = pd.DataFrame(
            rows, columns=["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume"]
        )
        df["datetime"] = pd.to_datetime(df["open_time"].astype("int64"), unit="ms", utc=True)
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = df[col].astype(float)

        df = df.set_index("datetime").sort_index()
        df = df[~df.index.duplicated(keep="first")]
        if since_ms is not None:
            df = df[df.index >= pd.Timestamp(since_ms, unit="ms", tz="UTC")]
            return df[["open", "high", "low", "close", "volume"]]
        return df[["open", "high", "low", "close", "volume"]].tail(outputsize)

    async def _listed_symbols(self) -> list[dict]:
        """MEXC's pair list, re-read every hour so new listings and delistings
        show up on their own. A failed or empty read keeps the last good list
        instead of caching nothing for an hour."""
        symbols = _symbols_cache.get("all")
        if symbols is not None:
            return symbols
        try:
            async with http_client.pooled(timeout=15.0) as client:
                resp = await client.get(f"{self._base_url}/api/v3/exchangeInfo")
            payload = resp.json()
            fresh = payload.get("symbols", []) if isinstance(payload, dict) else []
        except Exception:  # noqa: BLE001 — network/JSON failure falls back below
            fresh = []
        if fresh:
            _symbols_cache["all"] = fresh
            _last_good["all"] = fresh
            return fresh
        return _last_good.get("all", [])

    async def search_symbols(self, query: str) -> list[dict]:
        query = query.strip()
        if not query:
            return []

        symbols = await self._listed_symbols()

        q = query.upper().replace("/", "")
        # status "1" = listed and trading. isSpotTradingAllowed only says
        # whether the pair takes *API* orders: ~80 live pairs have it false
        # (RAINUSDT, USDEUSDT...) yet trade on the site and serve klines, and
        # filtering on it hid them from search (segnalazione 7410bba2).
        all_spot = [s for s in symbols if s.get("status") == "1"]
        starts = [s for s in all_spot if s.get("symbol", "").startswith(q)]
        contains = [s for s in all_spot if q in s.get("symbol", "") and not s.get("symbol", "").startswith(q)]
        matches = starts + contains
        matches.sort(key=lambda s: (not s.get("symbol", "").startswith(q), s.get("quoteAsset") != "USDT", len(s.get("symbol", ""))))

        out = []
        for s in matches[:_MAX_SUGGESTIONS]:
            base, quote = s.get("baseAsset", ""), s.get("quoteAsset", "")
            out.append({"symbol": s.get("symbol", ""), "name": s.get("fullName", "") or base, "exchange": f"MEXC ({quote})"})
        return out
