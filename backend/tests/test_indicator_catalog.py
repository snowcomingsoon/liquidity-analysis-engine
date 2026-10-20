import numpy as np
import pandas as pd
import pytest

from app.analysis import indicator_catalog as ic


def _synthetic_df(n: int = 120) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    close = 100 + np.cumsum(np.random.default_rng(0).normal(size=n))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": abs(np.random.default_rng(1).normal(size=n)) * 1000,
        },
        index=idx,
    )


def test_catalog_covers_all_pandas_ta_functions():
    import pandas_ta

    total = sum(len(names) for names in pandas_ta.Category.values())
    ours = {"cycle_bottom"}               # cycle_bottom.py, not pandas-ta's
    assert len([s for s in ic.CATALOG if s.id not in ours]) == total


def test_catalog_ids_are_unique():
    ids = [s.id for s in ic.CATALOG]
    assert len(ids) == len(set(ids))


def test_every_indicator_is_overlay_or_oscillator():
    assert all(s.kind in ("overlay", "oscillator") for s in ic.CATALOG)


def test_every_indicator_has_its_own_description():
    # Lorenzo: "non conosco i nomi cosi non so cosa cercare" — un fallback
    # generico per categoria basterebbe a non rompere l'endpoint, ma non
    # basterebbe a spiegare niente. Ogni id deve avere la sua riga dedicata.
    missing = [s.id for s in ic.CATALOG if s.id not in ic.DESCRIPTIONS]
    assert not missing, f"indicatori senza descrizione dedicata: {missing}"


def test_catalog_payload_includes_description():
    payload = ic.catalog_payload()
    assert all(entry["description"] for entry in payload)


@pytest.mark.parametrize(
    "indicator_id",
    ["rsi", "supertrend", "macd", "adx", "obv", "vwap", "donchian", "bbands"],
)
def test_compute_indicator_returns_aligned_series(indicator_id):
    df = _synthetic_df()
    out = ic.compute_indicator(df, indicator_id, {})
    assert out, f"{indicator_id} produced no series"
    for series in out:
        assert len(series.values) == len(df)


def test_compute_indicator_applies_declared_defaults():
    df = _synthetic_df()
    out = ic.compute_indicator(df, "supertrend", {})
    # Il default dichiarato in OVERRIDES e' length=10, non il 7 di pandas-ta.
    assert any("10" in s.name for s in out)


def test_compute_indicator_rejects_unknown_id():
    df = _synthetic_df()
    with pytest.raises(ValueError):
        ic.compute_indicator(df, "not_a_real_indicator", {})


def test_compute_indicator_ignores_unknown_params():
    df = _synthetic_df()
    # Un parametro non dichiarato per rsi (es. 'bogus') non deve rompere la chiamata.
    out = ic.compute_indicator(df, "rsi", {"length": 21, "bogus": 999})
    assert out
