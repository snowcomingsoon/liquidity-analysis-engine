"""
Favorites: tickers a user pins to the Watchlist tab purely for quick chart
navigation — clicking one loads it on the main chart. Distinct from
watchlist.py's WatchlistEntry, which is about background Telegram alerts;
a ticker can be a favorite, an alert entry, both, or neither.

Persisted to disk (backend/data/favorites.json), same convention as
watchlist.py.
"""

import json
import uuid
from pathlib import Path

from app.models import AssetType, CryptoExchange, FavoriteEntry
from app.atomic_write import write_text_atomic

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_STORE_FILE = _DATA_DIR / "favorites.json"

_entries: dict[str, FavoriteEntry] = {}


def _load() -> None:
    if not _STORE_FILE.exists():
        return
    try:
        raw = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    for item in raw:
        try:
            if isinstance(item, dict) and isinstance(item.get("symbol"), str):
                item = {**item, "symbol": _dex_symbol_fixed(item["symbol"])}
            entry = FavoriteEntry(**item)
            _entries[entry.id] = entry
        except (TypeError, ValueError):
            continue


def normalize_symbol(symbol: str) -> str:
    """Tickers in upper case; a DEX pair ("BASE@chain:pool") as given, since
    a Solana pool address is case-sensitive and the chain is lower case."""
    symbol = symbol.strip()
    return symbol if "@" in symbol and ":" in symbol else symbol.upper()


def _dex_symbol_fixed(symbol: str) -> str:
    """DEX pairs saved upper-cased before 19/10 ("WOOD@ROBINHOOD:0XF683..."):
    an EVM pool comes back (its address is case-insensitive); a Solana one
    cannot, and is left as it is."""
    base, sep, rest = symbol.partition("@")
    chain, sep2, pool = rest.partition(":")
    if sep and sep2 and pool[:2] in ("0X", "0x"):
        return f"{base}@{chain.lower()}:{pool.lower()}"
    return symbol


def _save() -> None:
    payload = [e.model_dump() for e in _entries.values()]
    write_text_atomic(_STORE_FILE, json.dumps(payload), encoding="utf-8")


_load()


def list_entries(owner_id: str | None = None) -> list[FavoriteEntry]:
    entries = list(_entries.values())
    if owner_id is not None:
        entries = [e for e in entries if e.owner_id == owner_id]
    return entries


def get_entry(entry_id: str) -> FavoriteEntry | None:
    return _entries.get(entry_id)


def add_entry(
    owner_id: str,
    symbol: str,
    asset_type: AssetType,
    exchange: CryptoExchange = "mexc",
) -> FavoriteEntry:
    """Upsert: pinning a ticker that's already a favorite for this owner
    just returns the existing entry instead of creating a duplicate row."""
    symbol = normalize_symbol(symbol)
    for entry in _entries.values():
        if (
            entry.owner_id == owner_id
            and entry.symbol == symbol
            and entry.asset_type == asset_type
            and entry.exchange == exchange
        ):
            return entry

    entry = FavoriteEntry(
        id=uuid.uuid4().hex[:12],
        owner_id=owner_id,
        symbol=symbol,
        asset_type=asset_type,
        exchange=exchange,
    )
    _entries[entry.id] = entry
    _save()
    return entry


def remove_entry(entry_id: str) -> None:
    if _entries.pop(entry_id, None) is not None:
        _save()
