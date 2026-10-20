import numpy as np
import pandas as pd

from app.analysis import cycle_bottom, indicator_catalog


def _df(n=700, seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    close = 100 * np.exp(0.3 * np.sin(t / 60) + np.cumsum(rng.normal(0, 0.02, n)))
    high, low = close * 1.02, close * 0.98
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close,
                         "volume": rng.uniform(1e3, 2e3, n)}, index=pd.date_range("2022-01-01", periods=n))


def test_index_is_bounded_and_causal():
    df = _df()
    full = cycle_bottom.compute(df)
    v = full["index"].dropna()
    assert len(v) > 400 and v.min() >= 0 and v.max() <= 100
    # No bar sees a later one: cutting the history leaves the past unchanged.
    for cut in (450, 560, 690):
        part = cycle_bottom.compute(df.iloc[:cut])
        assert np.isclose(part["index"].iloc[-1], full["index"].iloc[cut - 1])
        assert part["zone"].iloc[-1] == full["zone"].iloc[cut - 1]


def test_high_near_lows_low_near_highs():
    df = _df(seed=3)
    out = cycle_bottom.compute(df)
    close = df["close"]
    lo_rank = close.rolling(100).apply(lambda w: (w[-1] <= w.min() * 1.02), raw=True) == 1
    hi_rank = close.rolling(100).apply(lambda w: (w[-1] >= w.max() * 0.98), raw=True) == 1
    assert out["index"][lo_rank].mean() > 65 and out["index"][hi_rank].mean() < 35


def test_green_needs_the_volume_confirmation():
    out = cycle_bottom.compute(_df(seed=5))
    green = out[out["zone"] == "green"]
    assert green["confirmed"].all()
    assert set(out["zone"].dropna()) <= {"red", "orange", "yellow", "green"}


def test_catalog_serves_it_with_colors_and_levels():
    df = _df()
    spec = indicator_catalog.CATALOG_BY_ID["cycle_bottom"]
    assert spec.kind == "oscillator"
    series = indicator_catalog.compute_indicator(df, "cycle_bottom", {})
    assert len(series) == 1 and len(series[0].values) == len(df)
    assert series[0].levels == [60.0, 80.0] and len(series[0].colors) == len(df)
