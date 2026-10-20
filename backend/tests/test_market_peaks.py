import pytest

from app.trading.onchain import market_peaks as mp

K = "solana:borlypump"
T0 = 1_792_465_200.0


@pytest.fixture(autouse=True)
def _clean():
    mp.reset_for_tests()
    yield
    mp.reset_for_tests()


def test_a_crash_needs_two_readings_and_then_stays():
    """BORLY, 20/10: $1.5M to $3k in hours."""
    mp.record(K, 1_500_000, 110_000, T0)
    mp.record(K, 1_400_000, 105_000, T0 + 3600)
    assert mp.crashed(K, T0 + 3600) == ""
    mp.record(K, 600_000, 90_000, T0 + 7200)            # first crashed reading
    assert mp.crashed(K, T0 + 7200) == ""
    mp.record(K, 500_000, 80_000, T0 + 7200 + 180)      # confirmed
    assert "price down" in mp.crashed(K, T0 + 7300)
    assert K in mp.new_crashes(T0 + 7000)
    # The highs roll off after a day, the block does not.
    mp.record(K, 4_000, 3_000, T0 + 30 * 3600)
    assert "crashed" in mp.crashed(K, T0 + 30 * 3600)
    assert mp.crashed(K, T0 + 8 * 86400) == ""


def test_one_bad_reading_moves_nothing():
    mp.record(K, 1_000_000, 100_000, T0)
    mp.record(K, 100_000, 100_000, T0 + 60)              # a glitch
    mp.record(K, 990_000, 100_000, T0 + 120)
    mp.record(K, 1_000_000, 100_000, T0 + 300)
    assert mp.crashed(K, T0 + 300) == ""


def test_liquidity_halved_is_a_crash_too():
    mp.record(K, 1_000_000, 100_000, T0)
    mp.record(K, 900_000, 40_000, T0 + 600)
    mp.record(K, 900_000, 40_000, T0 + 800)
    assert "liquidity down 60%" in mp.crashed(K, T0 + 800)


def test_qualifies_and_early_follow_the_crash_and_the_trial():
    import time
    from app.trading.onchain import leaderboard as lb
    now = time.time()
    e = {"chain": "solana", "token_address": "BorlyMint1111111111111111111111111pump", "symbol": "BORLY",
         "name": "Borly", "launched_at": now - 1800, "market_cap": 1_500_000, "liquidity_usd": 100_000}
    assert "first-day trial" in lb.qualifies(e, now)
    key = lb._key(e["chain"], e["token_address"]).lower()
    mp.record(key, 1_500_000, 100_000, now - 600)
    mp.record(key, 3_000, 3_000, now - 300)
    mp.record(key, 3_000, 3_000, now - 100)
    assert lb.qualifies(e, now).startswith("crashed")
