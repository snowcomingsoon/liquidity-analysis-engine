"""Cycle Bottom Index: our take on a cycle-bottom oscillator (0-100).

Lorenzo, 20/10, from a chart of Luca - Cryptic Trades' Cycle Bottom Index
(private code): "mettilo solo nel sito classico per tutti, prima pero'
testane il corretto funzionamento". The original is closed; this one is
built from the three ideas it is described with, every piece causal (no
bar sees a later one):

1. cycle: an Ehlers roofing filter (high-pass + super smoother) strips the
   trend and the daily noise; where the filtered line sits in its own
   recent range says how close the dominant cycle is to its trough;
2. exhaustion: the Z-score of log price against a long mean, and where the
   close sits in its long range (a slow stochastic) - how stretched down;
3. pressure: accumulation/distribution. The green zone needs it: a bullish
   divergence (price under its previous low, A/D above it) or money flowing
   in (Chaikin Money Flow > 0). Without it a high reading stays yellow.

High = close to a bottom. Open interest and funding (the original's
"pressure engine") exist only on futures exchanges, not for every symbol
this site charts: left out, so the index means the same everywhere.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

YELLOW = 60.0
GREEN = 80.0
COLORS = {"red": "#e5484d", "orange": "#f59e0b", "yellow": "#facc15", "green": "#22c55e"}

W_CYCLE, W_Z, W_STOCH = 0.3, 0.4, 0.3
DIVERGENCE_LOOKBACK = 60
DIVERGENCE_GAP = 10           # bars between the two lows compared


def _roofing(close: np.ndarray, hp_period: int = 48, ss_period: int = 10) -> np.ndarray:
    """Ehlers' roofing filter: a two-pole high-pass, then a super smoother."""
    n = len(close)
    hp = np.zeros(n)
    a = (math.cos(0.707 * 2 * math.pi / hp_period) + math.sin(0.707 * 2 * math.pi / hp_period) - 1) \
        / math.cos(0.707 * 2 * math.pi / hp_period)
    for i in range(2, n):
        hp[i] = ((1 - a / 2) ** 2 * (close[i] - 2 * close[i - 1] + close[i - 2])
                 + 2 * (1 - a) * hp[i - 1] - (1 - a) ** 2 * hp[i - 2])
    a1 = math.exp(-1.414 * math.pi / ss_period)
    c2 = 2 * a1 * math.cos(1.414 * math.pi / ss_period)
    c3 = -a1 * a1
    c1 = 1 - c2 - c3
    out = np.zeros(n)
    for i in range(2, n):
        out[i] = c1 * (hp[i] + hp[i - 1]) / 2 + c2 * out[i - 1] + c3 * out[i - 2]
    out[:hp_period] = np.nan          # the filter is still settling
    return out


def _low_in_range(s: pd.Series, length: int) -> pd.Series:
    """100 at the bottom of the rolling range, 0 at its top."""
    lo, hi = s.rolling(length).min(), s.rolling(length).max()
    return 100 * (hi - s) / (hi - lo).replace(0, np.nan)


def compute(df: pd.DataFrame, length: int = 200, cycle_length: int = 50, smooth: int = 5) -> pd.DataFrame:
    """Columns: index (0-100), zone (red/orange/yellow/green), confirmed (bool)."""
    close = df["close"].astype(float)
    logc = np.log(close.where(close > 0))
    cyc = _low_in_range(pd.Series(_roofing(close.to_numpy()), index=df.index), cycle_length)
    mean, std = logc.rolling(length).mean(), logc.rolling(length).std()
    z = (logc - mean) / std.replace(0, np.nan)
    z_part = (-z).apply(lambda v: np.nan if pd.isna(v) else 100 * 0.5 * (1 + math.erf(v / math.sqrt(2))))
    stoch = _low_in_range(close, max(20, length // 2))
    raw = W_CYCLE * cyc + W_Z * z_part + W_STOCH * stoch
    index = raw.ewm(span=smooth, adjust=False, min_periods=1).mean().where(raw.notna())

    high, low = df["high"].astype(float), df["low"].astype(float)
    vol = df["volume"].astype(float).fillna(0)
    mfm = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    flow = (mfm.fillna(0) * vol)
    ad = flow.cumsum()
    cmf = flow.rolling(20).sum() / vol.rolling(20).sum().replace(0, np.nan)
    # Bullish divergence: this close under the lowest close of an earlier
    # window, while A/D stands above its value at that low.
    prior = close.shift(DIVERGENCE_GAP)
    prior_low = prior.rolling(DIVERGENCE_LOOKBACK).min()
    at_low = prior.rolling(DIVERGENCE_LOOKBACK).apply(lambda w: int(np.argmin(w)), raw=True)
    ad_prior = ad.shift(DIVERGENCE_GAP)
    ad_at_low = pd.Series(
        [np.nan if pd.isna(k) or i < DIVERGENCE_LOOKBACK else ad_prior.iloc[i - DIVERGENCE_LOOKBACK + 1 + int(k)]
         for i, k in enumerate(at_low)], index=df.index)
    divergence = (close.rolling(DIVERGENCE_GAP).min() < prior_low) & (ad > ad_at_low)
    confirmed = divergence.rolling(DIVERGENCE_GAP).max().fillna(0).astype(bool) | (cmf > 0)

    def zone(v, ok):
        if pd.isna(v):
            return None
        if v >= GREEN and ok:
            return "green"
        if v >= YELLOW:
            return "yellow"
        return "orange" if v >= 25 else "red"

    zones = [zone(v, ok) for v, ok in zip(index, confirmed)]
    return pd.DataFrame({"index": index, "zone": zones, "confirmed": confirmed}, index=df.index)


def series_payload(df: pd.DataFrame, length: int = 200) -> dict:
    """values, colors per point and the zone levels, for the chart."""
    out = compute(df, length=length, cycle_length=max(25, length // 4))
    return {"values": [None if pd.isna(v) else round(float(v), 2) for v in out["index"]],
            "colors": [COLORS.get(z) if z else None for z in out["zone"]],
            "levels": [YELLOW, GREEN]}
