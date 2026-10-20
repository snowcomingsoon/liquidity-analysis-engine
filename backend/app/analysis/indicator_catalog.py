"""Catalogo dei 151 indicatori di pandas-ta, con classificazione per il grafico.

pandas-ta e' gia' una dipendenza (vedi indicators.py, che ne usa solo 6 dei
151 disponibili). Questo modulo espone gli altri: un registro che dice per
ciascuno come chiamarlo, se va disegnato sul prezzo o in un riquadro separato,
e quali parametri ha senso esporre in UI. Il frontend lo usa per popolare la
libreria a tendina; nessun indicatore viene calcolato finche' l'utente non lo
sceglie esplicitamente, cosi' /api/analyze non si appesantisce.
"""
from __future__ import annotations

import pandas as pd
import pandas_ta  # noqa: F401  (registra l'accessor .ta)

from app.analysis import cycle_bottom
from app.models import IndicatorSeries

Param = dict  # {"name": str, "label": str, "default": float, "min": float, "max": float}


class IndicatorSpec:
    __slots__ = ("id", "label", "category", "kind", "params", "output_labels")

    def __init__(self, id_: str, label: str, category: str, kind: str,
                 params: list[Param] | None = None, output_labels: list[str] | None = None):
        self.id = id_
        self.label = label
        self.category = category
        self.kind = kind  # "overlay" (sul prezzo) o "oscillator" (riquadro proprio)
        self.params = params or []
        self.output_labels = output_labels  # nomi delle colonne quando l'output ha piu' linee


def _p(name: str, label: str, default: float, lo: float, hi: float) -> Param:
    return {"name": name, "label": label, "default": default, "min": lo, "max": hi}


LENGTH = lambda d=14: [_p("length", "Period", d, 2, 400)]  # noqa: E731

CATEGORY_LABELS = {
    "candle": "Candle patterns",
    "cycle": "Cycles",
    "momentum": "Momentum",
    "overlap": "Averages & overlays",
    "performance": "Performance",
    "statistics": "Statistics",
    "trend": "Trend",
    "volatility": "Volatility",
    "volume": "Volume",
}

# Indicatori con parametri o output non banali: classificazione a mano.
# Tutto il resto (la stragrande maggioranza) prende un default ragionevole
# per categoria (vedi _default_kind_for_category) e un solo parametro
# "length" quando la funzione lo accetta.
OVERRIDES: dict[str, IndicatorSpec] = {
    "supertrend": IndicatorSpec("supertrend", "SuperTrend", "overlap", "overlay",
        [_p("length", "Period", 10, 2, 100), _p("multiplier", "ATR multiplier", 3.0, 0.5, 10)],
        ["SUPERT", "SUPERTd"]),
    "ichimoku": IndicatorSpec("ichimoku", "Ichimoku Kinko Hyo", "overlap", "overlay",
        [_p("tenkan", "Tenkan", 9, 2, 60), _p("kijun", "Kijun", 26, 2, 120), _p("senkou", "Senkou", 52, 2, 200)]),
    "vwma": IndicatorSpec("vwma", "VWMA", "overlap", "overlay", LENGTH(20)),
    "hilo": IndicatorSpec("hilo", "Gann HiLo", "overlap", "overlay",
        [_p("high_length", "Highs period", 13, 2, 100), _p("low_length", "Lows period", 21, 2, 100)]),
    "hl2": IndicatorSpec("hl2", "HL2", "overlap", "overlay", []),
    "hlc3": IndicatorSpec("hlc3", "HLC3", "overlap", "overlay", []),
    "ohlc4": IndicatorSpec("ohlc4", "OHLC4", "overlap", "overlay", []),
    "donchian": IndicatorSpec("donchian", "Donchian Channel", "volatility", "overlay",
        [_p("lower_length", "Lower period", 20, 2, 200), _p("upper_length", "Upper period", 20, 2, 200)],
        ["DCL", "DCM", "DCU"]),
    "kc": IndicatorSpec("kc", "Keltner Channel", "volatility", "overlay", LENGTH(20),
        ["KCL", "KCB", "KCU"]),
    "bbands": IndicatorSpec("bbands", "Bollinger Bands", "volatility", "overlay", LENGTH(20),
        ["BBL", "BBM", "BBU"]),
    "accbands": IndicatorSpec("accbands", "Acceleration Bands", "volatility", "overlay", LENGTH(20),
        ["ACCBL", "ACCBM", "ACCBU"]),
    "chandelier_exit": IndicatorSpec("chandelier_exit", "Chandelier Exit", "volatility", "overlay",
        [_p("length", "Period", 22, 2, 100), _p("multiplier", "ATR multiplier", 3.0, 0.5, 10)]),
    "psar": IndicatorSpec("psar", "Parabolic SAR", "trend", "overlay",
        [_p("af0", "Initial acceleration", 0.02, 0.001, 0.5), _p("max_af", "Max acceleration", 0.2, 0.01, 1)]),
    "vwap": IndicatorSpec("vwap", "VWAP", "overlap", "overlay", []),
    "alligator": IndicatorSpec("alligator", "Alligator (Williams)", "overlap", "overlay", []),
    "adx": IndicatorSpec("adx", "ADX / Directional Movement", "trend", "oscillator", LENGTH(14),
        ["ADX", "DMP", "DMN"]),
    "aroon": IndicatorSpec("aroon", "Aroon", "trend", "oscillator", LENGTH(14), ["AROOND", "AROONU"]),
    "macd": IndicatorSpec("macd", "MACD", "momentum", "oscillator",
        [_p("fast", "Fast", 12, 2, 100), _p("slow", "Slow", 26, 2, 200), _p("signal", "Signal", 9, 2, 100)],
        ["MACD", "MACDh", "MACDs"]),
    "stoch": IndicatorSpec("stoch", "Stochastic", "momentum", "oscillator",
        [_p("k", "%K", 14, 2, 100), _p("d", "%D", 3, 2, 50)], ["STOCHk", "STOCHd"]),
    "rsi": IndicatorSpec("rsi", "RSI", "momentum", "oscillator", LENGTH(14)),
    "cci": IndicatorSpec("cci", "CCI", "momentum", "oscillator", LENGTH(20)),
    "willr": IndicatorSpec("willr", "Williams %R", "momentum", "oscillator", LENGTH(14)),
    "mfi": IndicatorSpec("mfi", "Money Flow Index", "volume", "oscillator", LENGTH(14)),
    "obv": IndicatorSpec("obv", "On Balance Volume", "volume", "oscillator", []),
    "cmf": IndicatorSpec("cmf", "Chaikin Money Flow", "volume", "oscillator", LENGTH(20)),
    "atr": IndicatorSpec("atr", "ATR", "volatility", "oscillator", LENGTH(14)),
    "chop": IndicatorSpec("chop", "Choppiness Index", "trend", "oscillator", LENGTH(14)),
    "vortex": IndicatorSpec("vortex", "Vortex Indicator", "trend", "oscillator", LENGTH(14), ["VTXP", "VTXM"]),
    "cdl_pattern": IndicatorSpec("cdl_pattern", "Candlestick patterns (all)", "candle", "overlay", []),
}

_OSCILLATOR_CATEGORIES = {"momentum", "trend", "volatility", "volume", "cycle", "performance", "statistics"}

# Una riga per ciascuno dei 151: cosa misura e a cosa serve, in italiano
# semplice. Lorenzo: "non conosco i nomi cosi non so cosa cercare" — senza
# questo la libreria sarebbe solo un elenco di sigle.
DESCRIPTIONS: dict[str, str] = {
    # candle
    "cycle_bottom": "0-100, high near a cycle bottom: Ehlers cycle filter, how far price sits under its long mean (Z-score) and in its long range. Yellow from 60; green from 80 only when volumes confirm (bullish A/D divergence or money flowing in).",
    "cdl_pattern": "Automatically spots classic candlestick patterns (doji, hammer, engulfing...) on the chart.",
    "cdl_z": "Normalizes candle bodies and wicks into statistical units, to compare candles of different sizes.",
    "ha": "Heikin-Ashi: redraws candles by averaging prices, to see the trend without single-bar noise.",
    # cycle
    "ebsw": "Even Better Sinewave — estimates the phase of a market cycle with an adaptive filter, useful in ranging markets.",
    "reflex": "Ehlers filter that isolates the dominant price cycle by removing high-frequency noise.",
    # momentum
    "ao": "Awesome Oscillator — difference between a fast and slow average of the midpoint, measures move momentum.",
    "apo": "Absolute difference between two moving averages, like MACD but without a signal line.",
    "bias": "Percentage deviation of price from its moving average: how 'stretched' it is from its own equilibrium.",
    "bop": "Balance of Power — compares buyer and seller strength inside each single candle.",
    "brar": "Pair of indicators measuring buy/sell pressure on the open relative to the previous day.",
    "cci": "Commodity Channel Index — how far price deviates from its typical average; extremes = overbought/oversold.",
    "cfo": "Chande Forecast Oscillator — percentage gap between price and a linear projection of its trend.",
    "cg": "Center of Gravity — very low-lag oscillator designed to anticipate turning points.",
    "cmo": "Chande Momentum Oscillator — similar to RSI but uses the net sum of moves instead of the average.",
    "coppock": "Coppock Curve — designed to flag the start of a new long-term uptrend.",
    "crsi": "Connors RSI — combines RSI, streak length and return rank for a more responsive overbought/oversold.",
    "cti": "Correlation Trend Indicator — correlates price with a straight line to tell how clean the trend is.",
    "er": "Efficiency Ratio (Kaufman) — how much of the distance price traveled is real movement and how much is noise.",
    "eri": "Elder Ray Index — separates bull power from bear power.",
    "exhc": "Exhaustion Count — counts consecutive closes above/below the average, flags an exhausted move.",
    "fisher": "Fisher Transform — transforms price to make highs and lows sharper and easier to spot.",
    "inertia": "Smoothed version of the Relative Vigor Index, cuts false short-term trend signals.",
    "kdj": "KDJ — Stochastic variant with a third line (J) more sensitive to direction changes.",
    "kst": "Know Sure Thing — weighted sum of several ROC oscillators, a momentum picture across multiple horizons.",
    "macd": "MACD — difference between two moving averages with a signal line: the classic for trends and crossovers.",
    "mom": "Momentum — raw difference between the current price and the price N bars ago.",
    "pgo": "Pretty Good Oscillator — distance of price from its average, measured in ATR units.",
    "ppo": "Like MACD but in percent, so it's comparable across assets with very different prices.",
    "psl": "Psychological Line — percentage of up bars over the last N, measures recent sentiment.",
    "qqe": "Smoothed RSI with dynamic bands, designed to stay in the trend longer before exiting.",
    "roc": "Rate of Change — percentage price change over N bars: the pure speed of the move.",
    "rsi": "RSI — the most popular: measures the speed of recent gains versus losses, on a 0-100 scale.",
    "rsx": "RSI smoothed further to cut noise without adding meaningful lag.",
    "rvgi": "Relative Vigor Index — compares where the candle closes versus where it opens, measures trend conviction.",
    "slope": "Slope of the price regression line over the last N bars.",
    "smc": "Oscillator derived from Smart Money Concepts.",
    "smi": "Stochastic Momentum Index — smoother version of the Stochastic, less jumpy near the extremes.",
    "squeeze": "TTM Squeeze — flags when Bollinger tightens inside Keltner: compression before a breakout.",
    "squeeze_pro": "Like Squeeze but with three compression levels instead of one.",
    "stc": "Schaff Trend Cycle — MACD run through a Stochastic, to catch trend changes faster.",
    "stoch": "Stochastic — where the close sits in the recent range; the classic for overbought/oversold.",
    "stochf": "Fast Stochastic — the unsmoothed version of the classic Stochastic, more responsive and noisier.",
    "stochrsi": "Stochastic applied to RSI instead of price: a double filter, even more sensitive to extremes.",
    "tmo": "True Momentum Oscillator — momentum computed on the sign of daily changes, smoothed twice.",
    "trix": "Rate of change of a triple exponential average: filters out almost all short-term noise.",
    "tsi": "True Strength Index — double-smoothed momentum, useful to confirm a trend already underway.",
    "uo": "Ultimate Oscillator — combines three time horizons to cut the false signals of a single period.",
    "willr": "Williams %R — like the Stochastic but flipped: measures the distance from the recent high.",
    # overlap
    "alligator": "Alligator (Williams) — three offset averages: intertwined = market asleep, spread = trend underway.",
    "alma": "Gaussian moving average designed to cut lag without losing smoothness.",
    "dema": "Double EMA — double exponential to halve the typical lag of a single moving average.",
    "ema": "Exponential Moving Average — weighs recent candles more; the basis of many other strategies.",
    "fwma": "Moving average weighted by Fibonacci numbers instead of linearly.",
    "hilo": "Gann HiLo — a line following recent highs or lows, flips side when the trend reverses.",
    "hl2": "Midpoint (high+low)/2 — a steadier reference price than the close alone.",
    "hlc3": "Typical price (high+low+close)/3 — average of the candle's three main prices.",
    "hma": "Hull MA — moving average designed to be both smooth and responsive, a rare combo among averages.",
    "hwma": "Moving average with adaptive damping, adjusts itself to recent volatility.",
    "ichimoku": "Ichimoku Kinko Hyo — a complete Japanese system: trend, support/resistance and momentum together.",
    "jma": "Jurik MA — proprietary moving average known for low lag and noise resistance.",
    "kama": "Kaufman Adaptive MA — slows down in ranging markets and speeds up in trends, adapts on its own.",
    "linreg": "Linear regression — the line that best fits price over the last N bars.",
    "mama": "Moving average that changes speed based on the dominant price cycle (MESA Adaptive).",
    "mcgd": "McGinley Dynamic — self-correcting moving average that tracks price without overreacting.",
    "midpoint": "Midpoint between the highest and lowest close over the last N bars.",
    "midprice": "Midpoint between the absolute high and low (not closes) over the last N bars.",
    "ohlc4": "Average of the candle's four prices: open, high, low, close.",
    "pivots": "Pivot points — support/resistance levels from the previous session, widely used intraday.",
    "pwma": "Moving average weighted by Pascal's triangle, softer at the edges.",
    "rma": "The smoothing used inside RSI and ATR (Wilder's average), slower than a classic EMA.",
    "sinwma": "Moving average weighted by a sine curve, very smooth.",
    "sma": "Simple Moving Average — arithmetic mean of price over the last N bars, the most basic one.",
    "smma": "Smoothed moving average, reacts more slowly than the SMA to the latest prices.",
    "ssf": "Ehlers Super Smoother — low-pass filter that smooths price with very little lag.",
    "ssf3": "3-pole Ehlers Super Smoother — an even smoother version of the previous one.",
    "supertrend": "SuperTrend — a line trailing price at an ATR distance, flips side at every trend reversal.",
    "swma": "Moving average weighted symmetrically around the center of the window.",
    "t3": "Very smooth multi-stage moving average, often used instead of the EMA in trend systems.",
    "tema": "Triple EMA — triple exponential, even less lag than the double (DEMA).",
    "trima": "Triangular MA — moving average that weighs the center of the window more, very smooth.",
    "vidya": "Moving average that speeds up with recent volatility (Variable Index Dynamic Average).",
    "wcp": "Close weighted twice as much as high and low (Weighted Close Price).",
    "wma": "Weighted Moving Average — weighs recent candles linearly more than older ones.",
    "zlma": "Zero-Lag MA — moving average built specifically to remove an average's structural lag.",
    "vwap": "VWAP — volume-weighted average price since session start: the day's institutional benchmark.",
    "vwma": "Volume Weighted MA — moving average that weighs higher-volume candles more.",
    # performance
    "log_return": "Bar-over-bar log return — the preferred measure in statistics thanks to its additive properties.",
    "percent_return": "Bar-over-bar percent return — how much price rose or fell since the previous candle.",
    # statistics
    "entropy": "Entropy — how unpredictable the distribution of recent returns is; higher = more chaotic market.",
    "kurtosis": "Kurtosis — how fat-tailed recent returns are, i.e. extreme moves more frequent than normal.",
    "mad": "Mean absolute deviation — dispersion of prices around their mean, a robust alternative to standard deviation.",
    "median": "Rolling median — the middle price value over the last N bars, less sensitive to extremes than the mean.",
    "quantile": "Rolling quantile — the threshold below which a given share of recent prices falls.",
    "skew": "Skewness — whether recent returns lean toward extreme rallies or extreme drops.",
    "stdev": "Standard deviation — the classic volatility measure: how far price strays from its mean.",
    "tos_stdevall": "Standard deviation bands (thinkorswim style) around a linear regression of price.",
    "variance": "Variance — the square of the standard deviation, the same volatility in a different unit.",
    "zscore": "Z-score — how many standard deviations the current price is from its recent mean.",
    # trend
    "adx": "ADX — how strong a trend is, without its direction (comes with the +DI/-DI lines).",
    "alphatrend": "Combines ATR and volume to draw a less noisy trend line.",
    "amat": "Flags when two moving averages jointly confirm an uptrend or downtrend.",
    "aroon": "How many bars since the last high and the last low: tells whether the trend is still fresh.",
    "chop": "Choppiness Index — whether the market is trending or just chopping sideways, regardless of direction.",
    "cksp": "Chande Kroll Stop — dynamic stop based on recent volatility, designed to keep you in the trend.",
    "decay": "Exponential price decay — weighs the past with a progressively smaller attenuation.",
    "decreasing": "Flags for how many consecutive bars price (or another indicator) has been falling.",
    "dpo": "Detrended Price Oscillator — strips out the underlying trend to reveal shorter cycles.",
    "ht_trendline": "Estimates a trend line using signal phase analysis (Hilbert transform).",
    "increasing": "Flags for how many consecutive bars price (or another indicator) has been rising.",
    "long_run": "Flags a sustained uptrend phase, combining the average's speed and acceleration.",
    "psar": "Parabolic SAR — dots that trail price and flip at every trend change, handy for stops.",
    "qstick": "Moving average of close minus open: the sentiment of the latest candles.",
    "rwi": "Random Walk Index — whether the recent move is larger than pure chance would suggest.",
    "short_run": "Flags a sustained downtrend phase, combining the average's speed and acceleration.",
    "trendflex": "Ehlers TrendFlex — trend-following oscillator with very low lag.",
    "vhf": "Vertical Horizontal Filter — whether the market moves vertically (trend) or horizontally (range).",
    "vortex": "Two lines that cross to flag the start of a new trend.",
    "zigzag": "Connects only significant highs and lows, ignoring minor swings: the clean structure of price.",
    # volatility
    "aberration": "Bands around an average, flag when price strays abnormally far.",
    "accbands": "Acceleration Bands — bands around price that widen with volatility.",
    "atr": "Average True Range — the average size of a candle's move: the standard volatility measure.",
    "atrts": "A stop trailing price at an ATR distance, tightening as volatility drops.",
    "bbands": "Bollinger Bands — a channel that widens and narrows with volatility around a moving average.",
    "chandelier_exit": "Stop computed from the recent high/low minus a multiple of ATR.",
    "donchian": "Donchian Channel — the high and low of the last N bars: the basis of breakout strategies.",
    "hwc": "Volatility channel built around the Holt-Winters average.",
    "kc": "Keltner Channel — like Bollinger but uses ATR instead of standard deviation for its width.",
    "massi": "Mass Index — spots an imminent reversal when candle ranges widen quickly.",
    "natr": "ATR expressed as a percentage of price, so it's comparable across assets.",
    "pdist": "How wide a single candle's range was compared to the previous one.",
    "rvi": "Relative Volatility Index — like RSI but applied to standard deviation instead of price.",
    "thermo": "Elder Thermometer — how 'hot' the current candle is relative to the recent range.",
    "true_range": "The true size of a single candle, gaps included: the basis of ATR.",
    "ui": "Ulcer Index — measures the pain of a drawdown: how deep and how long price stays below its highs.",
    # volume
    "ad": "Accumulation/Distribution — cumulative volume flow weighted by where the candle closes in its range.",
    "adosc": "Difference between two averages of Accumulation/Distribution: measures its momentum.",
    "aobv": "OBV with built-in bands and overbought/oversold signals.",
    "cmf": "Chaikin Money Flow — whether recent volume is flowing into or out of the asset.",
    "efi": "Elder's Force Index — combines price change and volume into one measure of move strength.",
    "eom": "Ease of Movement — how easily price moves per unit of traded volume.",
    "kvo": "Klinger Volume Oscillator — designed to anticipate long-term reversals through volume.",
    "mfi": "Money Flow Index — an RSI that also uses volume, often called 'volume-weighted RSI'.",
    "nvi": "Tracks price only on falling-volume days, isolating 'smart money' behavior (Negative Volume Index).",
    "obv": "On Balance Volume — adds or subtracts each day's full volume depending on price direction.",
    "pvi": "Like NVI but on rising-volume days (Positive Volume Index).",
    "pvo": "MACD applied to volume instead of price.",
    "pvol": "Price times volume — the traded value in each candle.",
    "pvr": "Ranks each candle by its combination of price direction and volume.",
    "pvt": "Like OBV but weighted by the size of the price change, not just its sign (Price Volume Trend).",
    "tsv": "Splits volume into time intervals to tell whether money is flowing into or out of the market.",
    "vhm": "Change in volume relative to its recent average.",
}


def _default_kind_for(category: str) -> str:
    return "overlay" if category == "overlap" else "oscillator"


def _humanize(fn_name: str) -> str:
    return fn_name.replace("_", " ").upper()


def build_catalog() -> list[IndicatorSpec]:
    """Introspeziona pandas_ta.Category e produce una voce per ogni funzione,
    usando OVERRIDES dove serve una definizione precisa e un default
    ragionevole ovunque altro."""
    out: list[IndicatorSpec] = []
    seen: set[str] = set()
    for category, names in pandas_ta.Category.items():
        for name in names:
            if name in seen or name.startswith("_"):
                continue
            seen.add(name)
            if name in OVERRIDES:
                out.append(OVERRIDES[name])
                continue
            fn = getattr(pandas_ta, name, None)
            has_length = False
            if fn is not None:
                try:
                    has_length = "length" in fn.__code__.co_varnames
                except AttributeError:
                    has_length = False
            out.append(IndicatorSpec(
                id_=name,
                label=_humanize(name),
                category=category,
                kind=_default_kind_for(category),
                params=LENGTH() if has_length else [],
            ))
    out.sort(key=lambda s: (s.category, s.label))
    return out


CATALOG: list[IndicatorSpec] = build_catalog()
# Ours, not pandas-ta's (cycle_bottom.py, Lorenzo 20/10).
# Period 200 measured best (20/10: green +8.1% median at 60 days on six coins, every day +0.9%).
CATALOG.append(IndicatorSpec("cycle_bottom", "Cycle Bottom Index", "cycle", "oscillator",
                            [_p("length", "Period", 200, 60, 400)]))
CATALOG_BY_ID: dict[str, IndicatorSpec] = {s.id: s for s in CATALOG}


_FALLBACK_DESCRIPTION = {
    "candle": "Reads candle shapes to recognize patterns.",
    "cycle": "Estimates the dominant price cycle with an adaptive filter.",
    "momentum": "Measures the speed and strength of price movement.",
    "overlap": "An average or reference price drawn on top of the chart.",
    "performance": "Measures bar-over-bar price return.",
    "statistics": "A statistical measure computed on recent prices.",
    "trend": "Tells whether and how strongly the market is trending.",
    "volatility": "Measures how much price moves, regardless of direction.",
    "volume": "Combines price and traded volume.",
}


def catalog_payload() -> list[dict]:
    return [
        {
            "id": s.id,
            "label": s.label,
            "category": s.category,
            "category_label": CATEGORY_LABELS.get(s.category, s.category),
            "kind": s.kind,
            "params": s.params,
            "description": DESCRIPTIONS.get(s.id, _FALLBACK_DESCRIPTION.get(s.category, "")),
        }
        for s in CATALOG
    ]


def compute_indicator(df: pd.DataFrame, indicator_id: str, params: dict) -> list[IndicatorSeries]:
    """Calcola un indicatore del catalogo e lo riporta nella stessa forma di
    compute_indicators(): una IndicatorSeries per ciascuna linea d'uscita,
    allineata per indice alle candele di df."""
    spec = CATALOG_BY_ID.get(indicator_id)
    if spec is None:
        raise ValueError(f"Unknown indicator: {indicator_id}")
    if indicator_id == "cycle_bottom":
        length = int((params or {}).get("length") or 200)
        return [IndicatorSeries(name=spec.label, **cycle_bottom.series_payload(df, max(60, min(length, 400))))]
    fn = getattr(df.ta, indicator_id, None)
    if fn is None:
        raise ValueError(f"pandas-ta does not expose '{indicator_id}'")
    # Parte dai default dichiarati nello spec (senza, un indicatore invocato
    # senza parametri prenderebbe quelli di default di pandas-ta, che spesso
    # non coincidono con i nostri — es. supertrend length=7 contro il nostro 10).
    clean_params = {p["name"]: p["default"] for p in spec.params}
    allowed = {p["name"] for p in spec.params}
    for k, v in (params or {}).items():
        if k in allowed:
            clean_params[k] = v
    result = fn(**clean_params)
    n = len(df)
    # Alcuni indicatori (ichimoku) restituiscono una tupla di dataframe — il
    # secondo e' la proiezione futura fuori dall'asse delle candele attuali,
    # non allineabile 1:1: si prende solo il primo, l'unico della stessa
    # lunghezza della serie richiesta.
    if isinstance(result, tuple):
        result = next((r for r in result if hasattr(r, "__len__") and len(r) == n), result[0])
    out: list[IndicatorSeries] = []
    if isinstance(result, pd.Series) and len(result) == n:
        out.append(IndicatorSeries(
            name=spec.label,
            values=[None if pd.isna(v) else float(v) for v in result],
        ))
    elif isinstance(result, pd.DataFrame) and len(result) == n:
        wanted = spec.output_labels
        cols = result.columns
        if wanted:
            for w in wanted:
                col = next((c for c in cols if c.upper().startswith(w.upper())), None)
                if col is not None:
                    s = result[col]
                    out.append(IndicatorSeries(name=f"{spec.label} ({col})",
                                                values=[None if pd.isna(v) else float(v) for v in s]))
        else:
            for col in cols:
                s = result[col]
                if pd.api.types.is_numeric_dtype(s):
                    out.append(IndicatorSeries(name=f"{spec.label} ({col})",
                                                values=[None if pd.isna(v) else float(v) for v in s]))
    return out
