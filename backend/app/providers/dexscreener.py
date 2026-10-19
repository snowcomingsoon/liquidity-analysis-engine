"""Pair DEX (on-chain), come ticker del sito principale — non lo Sniper.

Due API diverse per due bisogni diversi, entrambe pubbliche e gratuite:

* DexScreener (`/latest/dex/search`) per la RICERCA per nome/simbolo — ha
  metadati ricchi (nome, DEX, liquidita') ma la sua API pubblica non da'
  candele storiche, solo prezzo/volume attuali.
* GeckoTerminal (`/networks/{network}/pools/{pool}/ohlcv/{timeframe}`) per
  le CANDELE — stesso servizio gia' usato dallo Sniper per i pool nuovi,
  qui interrogato per un pool specifico invece che per una chain intera.

Le chain sono quelle gia' validate per lo Sniper (app.sniper.scanner):
stesso elenco, stessa mappa verso i network id di GeckoTerminal — un pool
trovabile via ricerca DexScreener ma non elencato li' non e' una chain che
abbiamo mai deciso di supportare altrove nel sito.

Il "symbol" canonico che questo provider restituisce/accetta non e' un
ticker leggibile come "BTCUSDT": e' `BASE@chain:pair_address`, l'unico modo
di portare chain+indirizzo del pool (necessari per le candele) dentro la
singola stringa che il resto del sito passa in giro. Non digitabile a
mano in modo utile — si arriva qui scegliendo un risultato della ricerca,
mai scrivendo il simbolo a memoria.
"""
import asyncio
import re
import time

import httpx

from app import http_client
from app.providers import candle_source, gecko_client
import pandas as pd
from cachetools import TTLCache

from app.providers.base import DataProvider, NoDataYet, ProviderError, ProviderUnreachable
from app.resample import resample_by_count
from app.sniper.scanner import GECKO_NETWORKS, SUPPORTED_CHAINS

DEXSCREENER_SEARCH_URL = "https://api.dexscreener.com/latest/dex/search"
GECKOTERMINAL_BASE = "https://api.geckoterminal.com/api/v2"
_MAX_SUGGESTIONS = 25
GECKO_PAGE = 1000
GECKO_MAX_PAGES = 6
_SEARCH_CACHE_TTL_S = 30  # il prezzo cambia in continuazione, la lista dei pool no

_search_cache: TTLCache = TTLCache(maxsize=200, ttl=_SEARCH_CACHE_TTL_S)

_SYMBOL_RE = re.compile(r"^(?P<base>.+)@(?P<chain>[a-z]+):(?P<pool>0x[a-fA-F0-9]+|[1-9A-HJ-NP-Za-km-z]+)$")

# GeckoTerminal accetta solo questi aggregati per timeframe; i nostri
# intervalli senza corrispondenza diretta si ottengono prendendo l'aggregato
# piu' fine disponibile e ripiegandolo con lo stesso resample_by_count usato
# altrove per 2D/3D/5D — non e' un caso speciale nuovo, e' lo stesso schema.
_INTERVAL_TO_GECKO = {
    "1m": ("minute", 1, 1),
    "5m": ("minute", 5, 1),
    "15m": ("minute", 15, 1),
    "30m": ("minute", 15, 2),
    "1h": ("hour", 1, 1),
    "4h": ("hour", 4, 1),
    "1d": ("day", 1, 1),
    "1w": ("day", 1, 7),
    "1M": ("day", 1, 30),
}


def candles_from_trades(trades: list[dict], bucket_s: int, token_address: str | None = None) -> list[list]:
    """[t, open, high, low, close, volume] dagli scambi GeckoTerminal, piu'
    recenti prima come ohlcv_list. Il prezzo e' quello del token scambiato:
    in un "buy" e' quello ricevuto, in un "sell" quello dato (o, se indicato,
    il lato che corrisponde a `token_address`)."""
    points = []
    for t in trades:
        try:
            ts = int(pd.Timestamp(t["block_timestamp"]).timestamp())
            if token_address and t.get("to_token_address") == token_address:
                price = float(t["price_to_in_usd"])
            elif token_address and t.get("from_token_address") == token_address:
                price = float(t["price_from_in_usd"])
            else:
                price = float(t["price_to_in_usd"] if t.get("kind") == "buy" else t["price_from_in_usd"])
            volume = float(t.get("volume_in_usd") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if price > 0:
            points.append((ts, price, volume))
    buckets: dict[int, list] = {}
    for ts, price, volume in sorted(points):
        start = ts - ts % bucket_s
        row = buckets.get(start)
        if row is None:
            buckets[start] = [start, price, price, price, price, volume]
        else:
            row[2], row[3], row[4] = max(row[2], price), min(row[3], price), price
            row[5] += volume
    return sorted(buckets.values(), reverse=True)


def make_symbol(base_symbol: str, chain: str, pool_address: str) -> str:
    return f"{base_symbol}@{chain}:{pool_address}"


def _parse_symbol(symbol: str) -> tuple[str, str, str]:
    m = _SYMBOL_RE.match(symbol.strip())
    if not m:
        raise ProviderError(
            f"'{symbol}' is not a recognizable DEX pair: pick it from a search result, "
            "don't type it by hand."
        )
    return m["base"], m["chain"], m["pool"]


# GeckoTerminal risponde 429 oltre ~30 richieste al minuto, e grafico,
# backtest dei listing, alert e pilota lo interrogano tutti insieme: un 429
# letto come "nessun dato" lasciava vuoto il grafico di un token che
# DexScreener mostra benissimo (FLIP su Robinhood). Quindi un solo passaggio
# per tutti: stessa richiesta nei 15 s servita una volta sola, un tetto al
# minuto con una riserva per chi sta guardando un grafico, e se GeckoTerminal
# rifiuta comunque, l'ultima risposta buona invece di un errore.
# The window, the urgent reserve and the cooldown after a 429 live in
# gecko_client, shared with every other GeckoTerminal caller (19/10).
_GECKO_WINDOW_S = gecko_client.WINDOW_S
gecko_load = gecko_client.load
_GECKO_BACKGROUND_PER_MIN = gecko_client.BACKGROUND_PER_MIN   # leaves ~15 a minute for someone opening a chart
_GECKO_URGENT_PER_MIN = gecko_client.GLOBAL_PER_MIN
_GECKO_FRESH_S = 15.0
_GECKO_STALE_S = 1800.0
_GECKO_BACKOFF_S = (2.0, 4.0)
gecko_urgent = gecko_client.urgent
_gecko_calls = gecko_client.calls
_gecko_seen: dict[tuple, tuple[float, dict]] = {}
_gecko_locks: dict[tuple, asyncio.Lock] = {}
_gecko_loop: list[int] = [0]


class GeckoBusy(NoDataYet):
    """GeckoTerminal ha rifiutato per troppe richieste: il dato c'e', va
    solo richiesto fra poco — come un pool appena nato, non un guasto."""


def _gecko_lock(key: tuple) -> asyncio.Lock:
    """Uno per richiesta: due chiamate uguali in contemporanea ne fanno una."""
    loop = id(asyncio.get_running_loop())
    if _gecko_loop[0] != loop:
        _gecko_locks.clear()
        _gecko_loop[0] = loop
    for k in [k for k, lock in _gecko_locks.items() if not lock.locked() and k != key]:
        _gecko_locks.pop(k)
    return _gecko_locks.setdefault(key, asyncio.Lock())


async def _gecko_slot(caller: str = "other") -> None:
    await gecko_client.slot(caller)


async def gecko_get(url: str, params: dict | None = None, caller: str = "gecko_get") -> dict | None:
    """Il JSON di GeckoTerminal, None su 404. GeckoBusy se rifiuta anche
    dopo le pause e non c'e' una risposta recente da riusare."""
    key = (url, tuple(sorted((params or {}).items())))
    seen = _gecko_seen.get(key)
    if seen and time.monotonic() - seen[0] < _GECKO_FRESH_S:
        gecko_client.cache_hit(caller)
        return seen[1]
    async with _gecko_lock(key):
        seen = _gecko_seen.get(key)
        if seen and time.monotonic() - seen[0] < _GECKO_FRESH_S:
            gecko_client.cache_hit(caller)
            return seen[1]
        resp = None
        # Someone is waiting on a chart: one short retry, then the last good
        # answer. The background can afford the long pauses; a person can't.
        pauses = (0.0, 1.0) if gecko_urgent.get() else (0.0, *_GECKO_BACKOFF_S)
        for pause in pauses:
            if pause:
                await asyncio.sleep(pause)
            async with http_client.pooled(timeout=20.0) as client:
                resp = await gecko_client.request(client, url, params=params, caller=caller)
            if resp.status_code != 429:
                break
    if resp.status_code == 404:
        return None
    if resp.status_code == 429 or resp.status_code >= 500:
        if seen and time.monotonic() - seen[0] < _GECKO_STALE_S:
            gecko_client.cache_hit(caller)
            return seen[1]
        raise GeckoBusy(f"GeckoTerminal occupato ({resp.status_code})")
    try:
        payload = resp.json()
    except ValueError as exc:
        raise ProviderError("Invalid response from GeckoTerminal") from exc
    if not isinstance(payload, dict):
        raise ProviderError("Invalid response from GeckoTerminal")
    _gecko_seen[key] = (time.monotonic(), payload)
    if len(_gecko_seen) > 512:
        for old in sorted(_gecko_seen, key=lambda k: _gecko_seen[k][0])[:128]:
            _gecko_seen.pop(old, None)
    return payload


class DexScreenerProvider(DataProvider):
    """Crypto on-chain — nessuna chiave richiesta, sola lettura.

    Non e' un exchange con cui operare (niente ordini, niente credenziali):
    solo prezzo e candele per un pool specifico, per guardarlo con gli
    stessi strumenti di analisi del resto del sito.
    """

    def __init__(self, dexscreener_base: str | None = None, geckoterminal_base: str | None = None):
        self._dexscreener_base = dexscreener_base or DEXSCREENER_SEARCH_URL
        self._geckoterminal_base = geckoterminal_base or GECKOTERMINAL_BASE

    async def fetch_ohlcv(
        self, symbol: str, interval: str, outputsize: int, since_ms: int | None = None,
        token_address: str | None = None,
    ) -> pd.DataFrame:
        _base, chain, pool = _parse_symbol(symbol)
        network = GECKO_NETWORKS.get(chain)
        if network is None:
            raise ProviderError(f"Chain \'{chain}\' not supported")
        timeframe, aggregate, fold = _INTERVAL_TO_GECKO.get(interval, ("day", 1, 1))

        # GeckoTerminal gives at most 1000 candles per call: older ones come
        # page by page with before_timestamp, until the pool's history ends.
        # The classic site wants the whole chart for its backtests (Lorenzo,
        # 12/10: "deve avere sempre la priorita' di eseguire backtest
        # sull'intero grafico disponibile"); the pages are capped so one
        # request cannot drain the per-minute budget.
        want = max(outputsize * fold, fold) if since_ms is None else None
        since_s = since_ms // 1000 if since_ms is not None else None

        async def gecko_rows() -> list:
            url = f"{self._geckoterminal_base}/networks/{network}/pools/{pool}/ohlcv/{timeframe}"
            rows: list = []
            before: int | None = None
            for _page in range(GECKO_MAX_PAGES):
                limit = GECKO_PAGE if want is None else min(GECKO_PAGE, want - len(rows))
                params = {"aggregate": aggregate, "limit": limit, "currency": "usd"}
                if before is not None:
                    params["before_timestamp"] = before
                # Il prezzo di quale lato del pool: di default GeckoTerminal da' la
                # base, ma un token puo' essere la quota (MYCE nel pool SHROOM/MYCE).
                if token_address:
                    params["token"] = token_address
                try:
                    payload = await gecko_get(url, params, caller="ohlcv:chart")
                except httpx.HTTPError as exc:
                    if rows:
                        break  # keep the pages already read
                    raise ProviderUnreachable(f"GeckoTerminal unreachable for {symbol}: {exc}") from exc
                except NoDataYet:
                    if rows:
                        break
                    raise
                if payload is None:
                    if rows:
                        break
                    raise ProviderError(f"Pool not found on {chain}: {pool}")
                page = (
                    payload.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
                    if isinstance(payload, dict) else []
                )
                if not page:
                    break
                rows.extend(page)
                oldest = min(int(r[0]) for r in page)
                if len(page) < limit or (want is not None and len(rows) >= want) \
                        or (since_s is not None and oldest <= since_s) or (before is not None and oldest >= before):
                    break
                before = oldest
            if not rows and timeframe == "minute":
                # Pool appena nato: GeckoTerminal ha gli scambi subito, le candele
                # qualche minuto dopo. DexScreener il grafico lo mostra da subito
                # (Lorenzo: "su Dex Screener ci sono sempre"), quindi le candele
                # si costruiscono dagli scambi.
                rows = await self._rows_from_trades(network, pool, aggregate * 60, token_address)
            return rows

        # One provider per call (candle_source.py): the squid only when it
        # covers the whole window, and only with settings.squid_mode "on".
        tf_s = candle_source.TF_SECONDS.get((timeframe, int(aggregate)))
        if candle_source.mode() == "off" or tf_s is None:
            rows, provider = await gecko_rows(), candle_source.PROVIDER_GECKO
        else:
            now = time.time()
            start = since_s if since_s is not None else now - (want or 1) * tf_s
            rows, provider = await candle_source.route(network, pool, timeframe, aggregate, token_address or "",
                                                       start, now, gecko_rows)
        if not rows:
            raise NoDataYet(f"No data available for {symbol} ({interval})")

        # [timestamp_s, open, high, low, close, volume], piu' recenti prima.
        df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["open_time"].astype("int64"), unit="s", utc=True)
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = df[col].astype(float)
        df = df.set_index("datetime").sort_index()
        df = df[~df.index.duplicated(keep="first")]
        df = df[["open", "high", "low", "close", "volume"]]

        df.attrs["provider"] = provider
        if fold > 1:
            df = resample_by_count(df, fold)
        if since_ms is not None:
            return df[df.index >= pd.Timestamp(since_ms, unit="ms", tz="UTC")]
        return df.tail(outputsize)

    async def _rows_from_trades(self, network: str, pool: str, bucket_s: int,
                                token_address: str | None) -> list[list]:
        url = f"{self._geckoterminal_base}/networks/{network}/pools/{pool}/trades"
        try:
            trades = ((await gecko_get(url, caller="trades:chart")) or {}).get("data") or []
        except (httpx.HTTPError, ProviderError):
            return []
        return candles_from_trades([t.get("attributes") or {} for t in trades], bucket_s, token_address)

    async def search_symbols(self, query: str) -> list[dict]:
        query = query.strip()
        if not query:
            return []

        pairs = _search_cache.get(query.lower())
        if pairs is None:
            try:
                async with http_client.pooled(timeout=10.0) as client:
                    resp = await client.get(self._dexscreener_base, params={"q": query})
                payload = resp.json()
            except (httpx.HTTPError, ValueError):
                return []  # una ricerca DEX che non risponde non deve affondare la combinata
            pairs = payload.get("pairs") or [] if isinstance(payload, dict) else []
            _search_cache[query.lower()] = pairs

        candidates = [p for p in pairs if p.get("chainId") in SUPPORTED_CHAINS and p.get("pairAddress")]
        # Piu' liquidita' prima: la stessa coppia ha spesso pool doppioni su
        # DEX diversi della stessa chain, e quello con piu' liquidita' e'
        # quello che vale la pena guardare per primo.
        candidates.sort(key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0), reverse=True)

        out = []
        seen_pools = set()
        for p in candidates:
            pool = p["pairAddress"]
            if pool in seen_pools:
                continue
            seen_pools.add(pool)
            base = p.get("baseToken", {})
            quote = p.get("quoteToken", {})
            base_symbol = base.get("symbol") or "?"
            symbol = make_symbol(base_symbol, p["chainId"], pool)
            out.append({
                "symbol": symbol,
                "name": f"{base_symbol}/{quote.get('symbol', '?')} · {base.get('name', '')}".strip(" ·"),
                "exchange": f"DexScreener ({p['chainId']} · {p.get('dexId', '?')})",
                # L'indirizzo del TOKEN (non del pool): DexScreener lo da'
                # gia' in baseToken.address, prima scartato perche' usato
                # solo per symbol/name. Serve a Fase 4 per chiedere un quote
                # di swap — il pool address da solo non basta.
                "base_token_address": base.get("address") or None,
            })
            if len(out) >= _MAX_SUGGESTIONS:
                break
        return out
