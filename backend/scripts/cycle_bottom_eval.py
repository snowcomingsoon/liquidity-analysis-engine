"""Measure the Cycle Bottom Index on real daily history (Coinbase candles).

For each symbol: every first day in the green (and in the yellow) zone,
30-day cooldown, and what price did 30/60/90 days later, against every
day as the baseline (a random entry). Run where the network reaches
api.exchange.coinbase.com:  python backend/scripts/cycle_bottom_eval.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.analysis import cycle_bottom  # noqa: E402

SYMBOLS = ("BTC-USD", "ETH-USD", "SOL-USD", "LTC-USD", "LINK-USD", "XRP-USD")
DAY = 86400
HORIZONS = (30, 60, 90)
COOLDOWN = 30


def candles(product: str, days: int = 2400) -> pd.DataFrame:
    rows, end = [], int(time.time()) // DAY * DAY
    with httpx.Client(timeout=20) as c:
        while days > 0:
            n = min(300, days)
            start = end - n * DAY
            r = c.get(f"https://api.exchange.coinbase.com/products/{product}/candles",
                      params={"granularity": DAY, "start": start, "end": end})
            r.raise_for_status()
            chunk = r.json()
            if not chunk:
                break
            rows += chunk
            end, days = start, days - n
            time.sleep(0.4)
    df = pd.DataFrame(rows, columns=["time", "low", "high", "open", "close", "volume"]).drop_duplicates("time")
    return df.sort_values("time").set_index(pd.to_datetime(df.sort_values("time")["time"], unit="s"))


def entries(zone: pd.Series, want: set[str]) -> list[int]:
    out, last = [], -10**9
    inside = zone.isin(want).to_numpy()
    for i in range(1, len(inside)):
        if inside[i] and not inside[i - 1] and i - last >= COOLDOWN:
            out.append(i)
            last = i
    return out


def fwd(close: pd.Series, idx: list[int], h: int) -> pd.Series:
    vals = [close.iloc[i + h] / close.iloc[i] - 1 for i in idx if i + h < len(close)]
    return pd.Series(vals, dtype=float)


def line(name: str, s: pd.Series) -> str:
    if s.empty:
        return f"{name}: n=0"
    return f"{name}: n={len(s)} median {s.median():+.1%} mean {s.mean():+.1%} up {(s > 0).mean():.0%}"


def variants() -> None:
    """Compact comparison of window lengths: all symbols pooled."""
    data = {}
    for sym in SYMBOLS:
        try:
            data[sym] = candles(sym)
        except Exception as exc:  # noqa: BLE001
            print(sym, "no data:", exc)
    for length, cyc in ((200, 50), (120, 40), (90, 30), (60, 25)):
        pool = {h: [] for h in HORIZONS}
        base = {h: [] for h in HORIZONS}
        notes = []
        for sym, df in data.items():
            out = cycle_bottom.compute(df, length=length, cycle_length=cyc)
            close = df["close"].astype(float)
            green = entries(out["zone"], {"green"})
            every = [i for i in range(len(close)) if not pd.isna(out["index"].iloc[i])]
            for h in HORIZONS:
                pool[h] += list(fwd(close, green, h))
                base[h] += list(fwd(close, every, h))
            if sym == "ETH-USD":
                notes.append("ETH 2026 greens: " + ", ".join(str(df.index[i].date()) for i in green if df.index[i].year == 2026)
                             + f" | ETH now {out['index'].iloc[-1]:.0f} {out['zone'].iloc[-1]}")
        print(f"\nlength {length}, cycle {cyc}: " + " | ".join(notes))
        for h in HORIZONS:
            print("  ", h, "d", line("green", pd.Series(pool[h], dtype=float)), "||", line("all", pd.Series(base[h], dtype=float)))


def main() -> None:
    if "--variants" in sys.argv:
        return variants()
    total = {k: {h: [] for h in HORIZONS} for k in ("green", "yellow", "all")}
    for sym in SYMBOLS:
        try:
            df = candles(sym)
        except Exception as exc:  # noqa: BLE001
            print(sym, "no data:", exc)
            continue
        out = cycle_bottom.compute(df)
        close = df["close"].astype(float)
        green = entries(out["zone"], {"green"})
        yellow = entries(out["zone"], {"yellow", "green"})
        every = [i for i in range(len(close)) if not pd.isna(out["index"].iloc[i])]
        print(f"\n{sym}: {len(df)} days {df.index[0].date()} .. {df.index[-1].date()}, last index "
              f"{out['index'].iloc[-1]:.1f} ({out['zone'].iloc[-1]})")
        print("  green days:", ", ".join(str(df.index[i].date()) for i in green))
        for i in green:
            lo = df["low"].astype(float).iloc[i:i + 31].min() / close.iloc[i] - 1
            print(f"    {df.index[i].date()} close {close.iloc[i]:.2f}: worst low within 30d {lo:+.1%}, "
                  + ", ".join(f"{h}d {close.iloc[i + h] / close.iloc[i] - 1:+.1%}" for h in HORIZONS if i + h < len(close)))
        for h in HORIZONS:
            for k, idx in (("green", green), ("yellow", yellow), ("all", every)):
                s = fwd(close, idx, h)
                total[k][h] += list(s)
                print("  ", h, "d", line(k, s))
    print("\nALL SYMBOLS")
    for h in HORIZONS:
        for k in ("green", "yellow", "all"):
            print("  ", h, "d", line(k, pd.Series(total[k][h], dtype=float)))


if __name__ == "__main__":
    main()
