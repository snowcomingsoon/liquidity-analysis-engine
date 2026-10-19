"""Favorites keep a DEX pair's case (19/10: an upper-cased Robinhood pair
failed every quote)."""
from app import favorites


def test_dex_pairs_keep_their_case_and_tickers_are_upper():
    assert favorites.normalize_symbol(" btcusdt ") == "BTCUSDT"
    pair = "JUP@solana:JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
    assert favorites.normalize_symbol(pair) == pair


def test_upper_cased_evm_pairs_are_recovered():
    assert favorites._dex_symbol_fixed("WOOD@ROBINHOOD:0XF6831AAF374B353757F0DE6B3DD2A74697671C69") == \
        "WOOD@robinhood:0xf6831aaf374b353757f0de6b3dd2a74697671c69"
    assert favorites._dex_symbol_fixed("BTCUSDT") == "BTCUSDT"
    assert favorites._dex_symbol_fixed("X@SOLANA:ABCdef") == "X@SOLANA:ABCdef"
