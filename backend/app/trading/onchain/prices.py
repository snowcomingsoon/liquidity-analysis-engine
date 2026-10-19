"""Prezzo USD del saldo nativo — solo per mostrare "$" nella hero, non
usato da nessun guardrail (quelli restano in USD gia' calcolato dal
chiamante, vedi risk.py). GeckoTerminal ha gia' un network id "robinhood"
mappato in app.sniper.scanner: stessa fonte gratuita, nessuna chiave,
gia' verificata dal vivo su entrambe le chain il 19/09/2026 (SOL e ETH
su Robinhood Chain tornano prezzi plausibili)."""
import time

import httpx

from app.providers import gecko_client
from app import http_client

from app.models import OnchainChain

GECKOTERMINAL_BASE = "https://api.geckoterminal.com/api/v2"

# Mint/indirizzo del "gas token" nativo di ogni chain, per chiedere il suo
# prezzo — non un token qualsiasi, sempre quello che la balance nativa
# rappresenta davvero.
_NATIVE_TOKEN = {
    "solana": ("solana", "So11111111111111111111111111111111111111112"),
    "robinhood": ("robinhood", "0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73"),
}

# Stesso indirizzo di _NATIVE_TOKEN, ma pubblico: il piano ordini limite
# (main.py) deve sapere qual e' la gamba nativa di un ordine senza
# duplicare l'indirizzo una terza volta.
NATIVE_TOKEN_ADDRESS = {chain: addr for chain, (_network, addr) in _NATIVE_TOKEN.items()}

_CACHE_TTL_S = 30  # il prezzo cambia in continuazione, non serve chiederlo ad ogni render
_cache: dict[str, tuple[float, float]] = {}  # chain -> (price_usd, fetched_at)


async def native_price_usd(chain: OnchainChain) -> float | None:
    """None se il prezzo non e' disponibile (rete giu', token non ancora
    listato) — mai un numero inventato al suo posto: chi chiama deve
    nascondere il "$" piuttosto che mostrarne uno falso."""
    cached = _cache.get(chain)
    if cached and time.time() - cached[1] < _CACHE_TTL_S:
        return cached[0]

    network, token_address = _NATIVE_TOKEN[chain]
    # The live price sources (Jupiter, DexScreener) first, GeckoTerminal only
    # when they have nothing (19/10): its free limit, ~10 calls a minute, is
    # better left to what only it has (candles, trades, holders).
    from app.trading.onchain import live_prices
    key = live_prices._key(chain, token_address)
    try:
        hit = (await live_prices.prices([key])).get(f"{key[0]}:{key[1]}")
    except Exception:
        hit = None
    price = hit["p"] if hit else None
    if price is None:
        price = await _gecko_price(network, token_address)
    if price is None:
        return None

    _cache[chain] = (price, time.time())
    return price


async def _gecko_price(network: str, token_address: str) -> float | None:
    url = f"{GECKOTERMINAL_BASE}/simple/networks/{network}/token_price/{token_address}"
    try:
        async with http_client.pooled(timeout=8.0) as client:
            resp = await gecko_client.request(client, url, caller="prices:token")
        if resp.status_code != 200:
            return None
        prices = resp.json()["data"]["attributes"]["token_prices"]
        price = float(next(iter(prices.values())))
    except (httpx.HTTPError, KeyError, StopIteration, ValueError, TypeError):
        return None
    return price if price > 0 else None


KRAKEN_TICKER_URL = "https://api.kraken.com/0/public/Ticker"
_btc_cache: tuple[float, float] | None = None  # (price_usd, fetched_at)


async def btc_price_usd() -> float | None:
    """Prezzo BTC in USD, solo per mostrare il saldo in BTC nella hero.
    Stessa regola di native_price_usd: None se la fonte non risponde, mai
    un numero inventato. Kraken perche' il ticker pubblico non chiede
    chiavi ed e' raggiungibile dal server in Germania."""
    global _btc_cache
    if _btc_cache and time.time() - _btc_cache[1] < _CACHE_TTL_S:
        return _btc_cache[0]
    try:
        async with http_client.pooled(timeout=8.0) as client:
            resp = await client.get(KRAKEN_TICKER_URL, params={"pair": "XBTUSD"})
        if resp.status_code != 200:
            return None
        body = resp.json()
        if body.get("error"):
            return None
        price = float(next(iter(body["result"].values()))["c"][0])
    except (httpx.HTTPError, KeyError, StopIteration, ValueError, TypeError, IndexError):
        return None
    if price <= 0:
        return None
    _btc_cache = (price, time.time())
    return price
