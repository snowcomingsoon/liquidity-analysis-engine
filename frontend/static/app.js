(() => {
  "use strict";

  // Terminal noir — dark mode chart palette
  const COLORS_DARK = {
    paperBg: "#080b0f",
    ink: "#c9d1d9",
    inkDim: "#6e7681",
    gridMinor: "rgba(26, 37, 53, 0.55)",
    gridMajor: "rgba(26, 37, 53, 0.85)",
    bull: "#00d68f",
    bear: "#ff4560",
    accent: "#00d68f",
    stamp: "#f0a500",
    bullFill: "rgba(0, 214, 143, 0.12)",
    bullBorder: "rgba(0, 214, 143, 0.75)",
    bearFill: "rgba(255, 69, 96, 0.12)",
    bearBorder: "rgba(255, 69, 96, 0.75)",
    // Grigie e non colorate per direzione: su TradingView una imbalance e' una
    // zona di prezzo, non un segnale rialzista o ribassista, e il colore lo
    // suggeriva. Il verde/rosso resta agli order block, che una direzione ce
    // l'hanno davvero.
    fvgBullFill: "rgba(148, 158, 170, 0.16)",
    fvgBullBorder: "rgba(148, 158, 170, 0.55)",
    fvgBearFill: "rgba(148, 158, 170, 0.16)",
    fvgBearBorder: "rgba(148, 158, 170, 0.55)",
    confluenceFill: "rgba(0, 214, 143, 0.07)",
    confluenceBorder: "rgba(0, 214, 143, 0.40)",
    ema20: "#5b9cf6",
    ema50: "#f0a500",
    bbUpper: "rgba(91, 156, 246, 0.85)",
    bbMid: "rgba(91, 156, 246, 0.45)",
    bbLower: "rgba(91, 156, 246, 0.85)",
    vwap: "#8b8bff",
    bmsbSma: "#ff6b6b",
    bmsbEma: "#2ec27e",
    rsi: "#5b9cf6",
    macd: "#5b9cf6",
    macdSignal: "#f0a500",
  };

  // Minimal Ink — light mode chart palette: monochrome candles, only P&L uses color
  const COLORS_LIGHT = {
    paperBg: "#ffffff",
    ink: "#000000",
    inkDim: "#666666",
    gridMinor: "rgba(0, 0, 0, 0.05)",
    gridMajor: "rgba(0, 0, 0, 0.10)",
    bull: "#1a1a1a",
    bear: "#1a1a1a",
    accent: "#000000",
    stamp: "#d97706",
    bullFill: "rgba(0, 0, 0, 0.04)",
    bullBorder: "#00a86b",
    bearFill: "rgba(0, 0, 0, 0.06)",
    bearBorder: "#e03040",
    fvgBullFill: "rgba(120, 128, 138, 0.14)",
    fvgBullBorder: "rgba(120, 128, 138, 0.50)",
    fvgBearFill: "rgba(120, 128, 138, 0.14)",
    fvgBearBorder: "rgba(120, 128, 138, 0.50)",
    confluenceFill: "rgba(0, 0, 0, 0.03)",
    confluenceBorder: "rgba(0, 0, 0, 0.22)",
    // Candles stay monochrome, indicator lines do not: in shades of grey
    // EMA 20 and 50, MACD and its signal, the two BMSB lines could not be
    // told apart, and nothing said which was which.
    ema20: "#2962ff",
    ema50: "#e8710a",
    bbUpper: "rgba(41, 98, 255, 0.60)",
    bbMid: "rgba(41, 98, 255, 0.40)",
    bbLower: "rgba(41, 98, 255, 0.60)",
    vwap: "#8e24aa",
    bmsbSma: "#d32f2f",
    bmsbEma: "#00875a",
    rsi: "#7e57c2",
    macd: "#2962ff",
    macdSignal: "#e8710a",
  };

  // Il contenuto viene sostituito quando si cambia tema, ma l'oggetto resta lo
  // stesso: le decine di riferimenti a COLORS.x sparsi nel file leggono al
  // momento della chiamata, quindi continuano a funzionare senza toccarli.
  // Riassegnare la variabile invece li lascerebbe legati alla vecchia palette.
  const COLORS = {};

  // Same anchors as backend indicators.VWAP_ANCHORS: where the VWAP restarts.
  const VWAP_ANCHOR_LABEL = {
    "1m": "D", "5m": "D", "15m": "D", "30m": "D", "1h": "W", "4h": "W",
    "1d": "M", "2d": "M", "3d": "M", "5d": "M", "1w": "Y", "1M": "Y",
  };

  // Dichiarata qui e non piu' in basso: `applyTheme` gira subito, prima ancora
  // che il resto del file venga valutato, e con `const` in fondo cadeva nella
  // temporal dead zone — "Cannot access 'el' before initialization". Non un
  // difetto parziale: l'eccezione interrompe l'intero modulo, quindi la pagina
  // restava ferma sul suo stato vuoto senza che nulla si inizializzasse.
  const el = (id) => document.getElementById(id);

  // Strategy names are storage/API keys ("Lorenzo (trend-follower)", ...):
  // they never change, but what the user reads is a neutral label. Any
  // suffix after " · " (e.g. a timeframe) is kept as is.
  function strategyLabel(name) {
    if (name == null) return "";
    const s = String(name);
    const i = s.indexOf(" · ");
    const head = i < 0 ? s : s.slice(0, i);
    const tail = i < 0 ? "" : s.slice(i);
    let label = head;
    if (/^Lorenzo HF\b/.test(head)) label = "Trend HF";
    else if (/^Lorenzo reversal\b/.test(head)) label = "Trend EMA Reversal";
    else if (/^Combined reversal\b/.test(head)) label = "Combined Reversal (Trend EMA + RSI+BB)";
    else if (/^RSI\+BB BTC band\b/.test(head)) label = "RSI+BB Reversal (BTC band)";
    else if (/^Lorenzo\b/.test(head)) label = "Trend EMA";
    else if (/^Gabriele 2\b/.test(head)) label = "RSI+BB Long/Short";
    else if (/^Gabriele\b/.test(head)) label = "RSI+BB Reversal";
    else if (/^Accumulo\b/.test(head)) label = "Accumulation / Distribution";
    else if (/^Claudio\b/.test(head)) label = head;
    return label + tail;
  }
  window.strategyLabel = strategyLabel;

  // The four figures that matter (Lorenzo, 15/10: "i quattro adesso valori
  // fondamentali sono profitto semplice, profitto composto, drawdown
  // semplice, drawdown composto [...] entrambi grandi visibili e con sotto
  // spiegato bene di che tipo di rendimento si tratta"). Same size each,
  // a line under each saying what it is; the rest stays small elsewhere.
  function fourFigures(f, compact = false) {
    const p = (x) => (x == null ? "–" : `${x >= 0 ? "+" : ""}${Number(x).toFixed(1)}%`);
    const d = (x) => (x == null ? "–" : `-${Math.abs(Number(x)).toFixed(1)}%`);
    const c = (x) => (x == null ? "" : x >= 0 ? "pos" : "neg");
    const cell = (val, cls, label, hint) => `<div class="ff-cell"><div class="ff-val ${cls}">${val}</div>`
      + `<div class="ff-lbl">${label}</div>${compact ? "" : `<div class="ff-hint">${hint}</div>`}</div>`;
    return `<div class="four-fig${compact ? " compact" : ""}">`
      + cell(p(f.simple), c(f.simple), "Simple profit", "every trade on the same stake, gains not reinvested")
      + cell(p(f.compounded), c(f.compounded), "Compounded profit", "every trade reinvests all the equity so far")
      + cell(d(f.simpleDd), "neg", "Simple drawdown", "worst drop, in % of the starting capital")
      + cell(d(f.dd), "neg", "Compounded drawdown", "worst drop from the equity peak")
      + `</div>`;
  }
  function perTrade(f) {
    const p = (x) => (x == null ? "–" : `${x >= 0 ? "+" : ""}${Number(x).toFixed(2)}%`);
    return `average trade ${p(f.avg)} · median trade ${p(f.median)}`;
  }

  // `applyTheme` gira subito, prima che il resto del file sia valutato: senza
  // questa bandiera `repaintCharts` toccherebbe `mainChart`, dichiarato con
  // `let` settecento righe piu' sotto, e cadrebbe nella stessa temporal dead
  // zone che ha gia' spento l'app una volta.
  let chartsReady = false;

  const THEME_KEY = "lae.theme";

  function preferredTheme() {
    try {
      const saved = localStorage.getItem(THEME_KEY);
      if (saved === "dark" || saved === "light") return saved;
    } catch { /* localStorage non disponibile: si usa la preferenza di sistema */ }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(mode, { persist = true, redraw = true } = {}) {
    document.documentElement.setAttribute("data-theme", mode);
    try { bumpDraw(); } catch { /* drawing layer not set up yet */ }
    Object.keys(COLORS).forEach((k) => delete COLORS[k]);
    Object.assign(COLORS, mode === "dark" ? COLORS_DARK : COLORS_LIGHT);
    const btn = el("theme-toggle-btn");
    if (btn) {
      btn.textContent = mode === "dark" ? "☾" : "☀";
      btn.title = mode === "dark" ? "Switch to light theme" : "Switch to dark theme";
      btn.setAttribute("aria-label", btn.title);
    }
    if (persist) {
      try { localStorage.setItem(THEME_KEY, mode); } catch { /* ignora */ }
    }
    // I colori del grafico non stanno nel CSS: sono opzioni passate alla
    // libreria alla creazione, quindi vanno riapplicati a mano.
    //
    // Ridisegnare non bastava: `render()` aggiorna i DATI delle serie, non le
    // opzioni del grafico. Lo sfondo, la griglia e il crosshair restavano
    // quelli con cui il grafico era nato — ed e' il motivo per cui passando al
    // tema chiaro il riquadro restava nero.
    repaintCharts();
    if (redraw && state.data) render();
  }

  function repaintCharts() {
    if (!chartsReady) return;
    const opts = {
      layout: { background: { color: COLORS.paperBg }, textColor: COLORS.inkDim },
      grid: { vertLines: { color: COLORS.gridMinor }, horzLines: { color: COLORS.gridMinor } },
      rightPriceScale: { borderColor: COLORS.gridMajor },
      timeScale: { borderColor: COLORS.gridMajor },
      crosshair: {
        vertLine: { color: COLORS.inkDim, labelBackgroundColor: COLORS.ink },
        horzLine: { color: COLORS.inkDim, labelBackgroundColor: COLORS.ink },
      },
    };
    [mainChart, rsiChart, macdChart, stochChart, ...Object.values(customOscCharts).map((x) => x.chart)].forEach((c) => {
      if (c) { try { c.applyOptions(opts); } catch { /* grafico non ancora creato */ } }
    });
    // Anche le serie portano colori propri, decisi alla creazione.
    if (candleSeries) {
      candleSeries.applyOptions({
        downColor: COLORS.bear, borderUpColor: COLORS.bull, borderDownColor: COLORS.bear,
        wickUpColor: COLORS.bull, wickDownColor: COLORS.bear,
        priceLineColor: COLORS.stamp,
      });
    }
    if (rsiSeries) rsiSeries.applyOptions({ color: COLORS.rsi });
    if (macdLineSeries) macdLineSeries.applyOptions({ color: COLORS.macd });
    if (macdSignalSeries) macdSignalSeries.applyOptions({ color: COLORS.macdSignal });
    if (stochKSeries) stochKSeries.applyOptions({ color: COLORS.rsi });
    if (stochDSeries) stochDSeries.applyOptions({ color: COLORS.stamp });
  }

  applyTheme(preferredTheme(), { persist: false, redraw: false });

  const CANONICAL_INTERVALS = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "2d", "3d", "5d", "1w", "1M"];
  const DEFAULT_INTERVALS = { htf: "1d", mtf: "1h", ltf: "15m" };
  const DEFAULT_PRIMARY_INTERVAL = "15m";

  // Per-strategy parameter fields for the watchlist's inline "personalizza"
  // panel — mirrors each strategy's own default-params dict on the backend
  // (app/analysis/strategies.py) so an alert can override just the params
  // that strategy actually reads. Keyed by the exact strategy name returned
  // from /api/strategies.
  const STRATEGY_PARAM_FIELDS = {
    "Lorenzo (trend-follower)": [
      { key: "average", label: "MA type", type: "select", options: ["EMA", "SMA"], default: "EMA" },
      { key: "len", label: "MA length", type: "number", min: 2, default: 130 },
      { key: "slopeFlen", label: "Fast slope", type: "number", min: 1, default: 7 },
      { key: "slopeSlen", label: "Slow slope", type: "number", min: 1, default: 27 },
      { key: "trendfilter", label: "Trend filter", type: "checkbox", default: true },
      { key: "trendfilterperiod", label: "Trend period", type: "number", min: 2, default: 268 },
      { key: "trendfiltertype", label: "Trend type", type: "select", options: ["EMA", "SMA"], default: "EMA" },
      { key: "volatilityfilter", label: "Volatility filter", type: "checkbox", default: true },
      { key: "volatilitystdevlength", label: "Stdev length", type: "number", min: 1, default: 16 },
      { key: "volatilitystdevmalength", label: "Stdev MA length", type: "number", min: 1, default: 44 },
      // La variabile che mancava: quanta pendenza serve perché conti come
      // direzione, in unità di deviazione standard della pendenza stessa —
      // così la stessa soglia significa la stessa cosa su BTC e su una
      // altcoin che fa il 15% al giorno. Zero = spenta, come è sempre stato.
      { key: "slope_threshold_sigma", label: "Slope threshold (σ)", type: "number", min: 0, max: 3, step: 0.1, default: 0 },
      { key: "slope_sigma_length", label: "Slope σ window", type: "number", min: 10, default: 100 },
    ],
    // l'utente sulle candele da un minuto dei token on-chain: stesso incrocio
    // sulla pendenza, filtri pensati per un token di poche ore (VWAP dal
    // lancio al posto della EMA lunga, regime per token, trailing stop).
    "Lorenzo HF (minuti on-chain)": [
      { key: "len", label: "MA length", type: "number", min: 2, default: 30 },
      { key: "slopeFlen", label: "Fast slope", type: "number", min: 1, default: 4 },
      { key: "slopeSlen", label: "Slow slope", type: "number", min: 1, default: 14 },
      { key: "slope_threshold_sigma", label: "Slope threshold (σ)", type: "number", min: 0, max: 3, step: 0.1, default: 0.5 },
      { key: "slope_sigma_length", label: "Slope σ window", type: "number", min: 10, default: 60 },
      { key: "vwap_filter", label: "Above VWAP since launch", type: "checkbox", default: true },
      { key: "er_len", label: "Efficiency window", type: "number", min: 2, default: 10 },
      { key: "er_min", label: "Min efficiency", type: "number", min: 0, max: 1, step: 0.05, default: 0.5 },
      { key: "vr_len", label: "Regime window", type: "number", min: 10, default: 60 },
      { key: "vr_min", label: "Min regime (VR)", type: "number", min: 0, max: 3, step: 0.1, default: 1.0 },
      { key: "volume_len", label: "Volume window", type: "number", min: 3, default: 30 },
      { key: "volume_mult", label: "Volume spike (x)", type: "number", min: 0, step: 0.1, default: 0 },
      { key: "atr_len", label: "ATR length", type: "number", min: 2, default: 14 },
      { key: "trail_atr", label: "Trailing stop (ATR)", type: "number", min: 0, step: 0.5, default: 4 },
    ],
    "Accumulo / Distribuzione (long-term)": [
      { key: "enable_divergence", label: "RSI divergence on swings", type: "checkbox", default: true },
      { key: "enable_contraction", label: "Volatility-contraction breakout", type: "checkbox", default: true },
      { key: "enable_range_bounce", label: "Range support/resistance bounce", type: "checkbox", default: true },
      { key: "swing_length", label: "Swing length", type: "number", min: 1, default: 8 },
      { key: "rsi_length", label: "RSI length", type: "number", min: 1, default: 14 },
      { key: "rsi_oversold", label: "RSI oversold", type: "number", min: 0, max: 100, default: 40 },
      { key: "rsi_overbought", label: "RSI overbought", type: "number", min: 0, max: 100, default: 60 },
      { key: "rsi_min_gap", label: "RSI min divergence gap", type: "number", min: 0, step: 0.1, default: 3.0 },
      { key: "low_tolerance_pct", label: "New-low tolerance %", type: "number", min: 0, step: 0.1, default: 1.0 },
      { key: "divergence_lookback", label: "Divergence swing lookback", type: "number", min: 1, default: 3 },
      { key: "volume_ma_length", label: "Volume MA", type: "number", min: 1, default: 20 },
      { key: "volume_multiplier", label: "Volume multiplier", type: "number", min: 0, step: 0.1, default: 1.3 },
      { key: "trend_filter", label: "Trend filter", type: "checkbox", default: true },
      { key: "trend_ema_length", label: "EMA trend", type: "number", min: 1, default: 50 },
      { key: "confirmation_lookahead", label: "Confirmation bars", type: "number", min: 1, default: 10 },
      { key: "contraction_lookback", label: "Contraction lookback", type: "number", min: 1, default: 10 },
      { key: "contraction_prior_lookback", label: "Pre-contraction lookback", type: "number", min: 1, default: 30 },
      { key: "contraction_ratio", label: "Volatility contraction ratio", type: "number", min: 0, step: 0.05, default: 0.55 },
      { key: "range_lookback", label: "Lookback range", type: "number", min: 1, default: 40 },
      { key: "range_zone_pct", label: "Range zone %", type: "number", min: 0, max: 1, step: 0.05, default: 0.25 },
    ],
    "Gabriele (RSI+BB reversal)": [
      { key: "rsi_length", label: "RSI length", type: "number", min: 1, default: 14 },
      { key: "bb_length", label: "Bollinger length", type: "number", min: 1, default: 20 },
      { key: "bb_mult", label: "Bollinger multiplier", type: "number", min: 0, step: 0.1, default: 2.0 },
      { key: "rsi_oversold", label: "RSI oversold", type: "number", min: 0, max: 100, default: 28 },
      { key: "rsi_overbought", label: "RSI overbought", type: "number", min: 0, max: 100, default: 72 },
    ],
    // Stessi parametri della precedente, di proposito: una configurazione
    // trovata per l'una si porta sull'altra e le due si confrontano sugli
    // stessi assi. Cambia cosa succede sull'ipercomprato — apre uno short
    // invece di limitarsi a chiudere il long.
    "Gabriele 2 (RSI+BB long/short)": [
      { key: "rsi_length", label: "RSI length", type: "number", min: 1, default: 14 },
      { key: "bb_length", label: "Bollinger length", type: "number", min: 1, default: 20 },
      { key: "bb_mult", label: "Bollinger multiplier", type: "number", min: 0, step: 0.1, default: 2.0 },
      { key: "rsi_oversold", label: "RSI oversold", type: "number", min: 0, max: 100, default: 28 },
      { key: "rsi_overbought", label: "RSI overbought", type: "number", min: 0, max: 100, default: 72 },
    ],
    // Claudio 4H (15/10): rebound in ranging markets, confirmation candle,
    // exits at the band's middle / ATR stop / time stop. Searched by Max return.
    "Claudio 4H": [
      { key: "cl_rsi_os", label: "RSI oversold (setup)", type: "number", min: 1, max: 99, default: 30 },
      { key: "cl_bb_mult", label: "Bollinger multiplier", type: "number", min: 0.5, step: 0.1, default: 2.2 },
      { key: "cl_atr_stop", label: "Stop (× ATR)", type: "number", min: 0.5, step: 0.25, default: 2.5 },
      { key: "cl_er_max", label: "Ranging if efficiency ≤", type: "number", min: 0, max: 1, step: 0.05, default: 0.3 },
      { key: "cl_ema_len", label: "Long average (candles)", type: "number", min: 10, default: 200 },
      { key: "cl_time_stop", label: "Time stop (candles)", type: "number", min: 1, default: 30 },
    ],
  };

  // Trend EMA Reversal (15/10): the very same fields as Trend EMA — same
  // values, only it never shorts (the short signal closes the long).
  STRATEGY_PARAM_FIELDS["Lorenzo reversal (long only)"] =
    STRATEGY_PARAM_FIELDS["Lorenzo (trend-follower)"].map((f) => ({ ...f }));
  // Combined Reversal (16/10): both strategies' own fields, which never share
  // a name; one position, in on either entry, out at the first exit.
  STRATEGY_PARAM_FIELDS["Combined reversal (long only)"] = [
    ...STRATEGY_PARAM_FIELDS["Lorenzo (trend-follower)"],
    ...STRATEGY_PARAM_FIELDS["Gabriele (RSI+BB reversal)"],
  ].map((f) => ({ ...f }));

  // BTC filter (Lorenzo, 15/10: "il filtro Btc [...] da attivare/disattivare
  // su tutte le strategie"): no long entry while BTC's last closed week is
  // under its weekly EMA 21. Off by default; Run, alerts, archive and the
  // optimizations all honour it (backend analysis/btc_regime.py).
  Object.keys(STRATEGY_PARAM_FIELDS).forEach((name) => {
    if (name === "Lorenzo HF (minuti on-chain)") return;
    STRATEGY_PARAM_FIELDS[name].push({
      key: "btc_filter", label: "BTC filter (no long while BTC < weekly EMA 21)",
      type: "checkbox", default: false,
    }, {
      // 15/10: worth it on the old RSI+BB 4H (worst 2022 -61% -> -12%), costly on 1D
      key: "btc_filter_exit", label: "BTC filter: also close longs when it turns off",
      type: "checkbox", default: false,
    });
  });

  // ── Strategy menu: grouped by kind, then one-line descriptions and the
  // recommended settings. Lorenzo, 16/10: Trend EMA Reversal together with
  // RSI+BB Reversal, Trend EMA (long/short) together with RSI+BB long/short,
  // no star. Anything new the backend adds goes under "Other".
  const STRATEGY_GROUPS = [
    ["Reversal · long only", ["Lorenzo reversal (long only)", "Gabriele (RSI+BB reversal)", "Combined reversal (long only)"]],
    ["Long / short", ["Lorenzo (trend-follower)", "Gabriele 2 (RSI+BB long/short)"]],
    ["Other", ["Accumulo / Distribuzione (long-term)", "Lorenzo HF (minuti on-chain)"]],
  ];
  const STRATEGY_ORDER = STRATEGY_GROUPS.flatMap(([, names]) => names);
  const STRATEGY_DESCRIPTIONS = {
    "Lorenzo reversal (long only)": "Trend follower, long only: buys when the slope of the average turns up, sells when it turns down. Best result in the 1D test with the BTC filter on (median of 35 pairs: 2021 +136%, 2022 0%, 2023–26 +67%).",
    "Lorenzo (trend-follower)": "Trend follower, long and short: the slope of the average turning up opens a long, turning down flips to a short.",
    "Gabriele (RSI+BB reversal)": "Buys extremes, long only: RSI oversold and a close under the lower band on the same candle; sells when RSI is overbought and the close is over the upper band. Few trades on 1D (about 1 a year).",
    "Combined reversal (long only)": "Trend EMA Reversal and RSI+BB Reversal in one position: in on either entry, out at the first exit. About 3× the trades of Trend EMA Reversal, with a higher drawdown.",
    "Gabriele 2 (RSI+BB long/short)": "RSI+BB both ways: the overbought signal opens a short instead of only closing the long.",
    "Accumulo / Distribuzione (long-term)": "Counter-trend: RSI divergences at swing lows and highs, range breakouts and bounces off the range support. Holds until the opposite signal.",
    "Lorenzo HF (minuti on-chain)": "Trend follower for minute candles of on-chain tokens.",
  };
  // The best setup measured for each strategy, applied on request: the
  // defaults stay as they are, so saved results do not change.
  const RECOMMENDED_SETTINGS = {
    "Lorenzo reversal (long only)": { btc_filter: true },
    "Combined reversal (long only)": { btc_filter: true },
  };

  function orderStrategies(list) {
    const rank = (n) => { const i = STRATEGY_ORDER.indexOf(n); return i < 0 ? STRATEGY_ORDER.length : i; };
    return [...list].sort((a, b) => rank(a) - rank(b));
  }

  function strategyOptionLabel(name) {
    return strategyLabel(name);
  }

  // <option>s for a strategy <select>, under one <optgroup> per kind.
  function strategyOptionsHtml(list) {
    const opt = (s) => `<option value="${escapeHtml(s)}">${escapeHtml(strategyOptionLabel(s))}</option>`;
    const known = new Set(STRATEGY_ORDER);
    const groups = STRATEGY_GROUPS.map(([label, names]) => [label, names.filter((n) => list.includes(n))]);
    groups[groups.length - 1][1].push(...list.filter((n) => !known.has(n)));
    return groups.filter(([, names]) => names.length)
      .map(([label, names]) => `<optgroup label="${escapeHtml(label)}">${names.map(opt).join("")}</optgroup>`).join("");
  }

  // Description + "Use recommended settings" on top of a strategy's fields.
  function addStrategyExtras(container, strategyName) {
    const desc = STRATEGY_DESCRIPTIONS[strategyName];
    const rec = RECOMMENDED_SETTINGS[strategyName];
    if (!desc && !rec) return;
    const box = document.createElement("div");
    box.className = "strat-extras full-width";
    if (desc) {
      const p = document.createElement("p");
      p.className = "strat-desc";
      p.textContent = desc;
      box.appendChild(p);
    }
    if (rec) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "strat-rec-btn";
      btn.textContent = "★ Use recommended settings";
      btn.title = Object.keys(rec).map((k) => (STRATEGY_PARAM_FIELDS[strategyName] || []).find((f) => f.key === k)?.label || k).join(" · ");
      btn.addEventListener("click", () => {
        (STRATEGY_PARAM_FIELDS[strategyName] || []).forEach((f) => {
          const input = container.querySelector(`[name="${f.key}"]`);
          if (!input) return;
          const v = f.key in rec ? rec[f.key] : f.default;
          if (f.type === "checkbox") input.checked = !!v; else input.value = v;
          input.dispatchEvent(new Event("input", { bubbles: true }));
          input.dispatchEvent(new Event("change", { bubbles: true }));
        });
        btn.textContent = "✓ Recommended settings applied";
        setTimeout(() => { btn.textContent = "★ Use recommended settings"; }, 2500);
      });
      box.appendChild(btn);
    }
    container.prepend(box);
  }

  // ── Leggere un campo numerico senza produrre un 422 ────────────────────────
  //
  // Tre modi diversi di scrivere un numero finivano tutti nello stesso errore
  // muto — "Errore 422" — ed erano tre cose diverse:
  //
  //   * il campo svuotato per riscriverlo, e la richiesta parte in quel
  //     momento: `len=` arriva al server come stringa vuota;
  //   * la virgola decimale. `1,5` in un <input type="number"> non e' un
  //     numero per il browser, che restituisce stringa vuota — e la virgola
  //     e' come scrive i decimali chi usa questa app;
  //   * un decimale dentro un parametro che e' un numero di barre. `27,5`
  //     barre non esiste, ma nessuno lo diceva.
  //
  // Qui il valore viene normalizzato e RISCRITTO nel campo: cosi' quello che
  // gira e' quello che si legge a schermo. Sostituirlo in silenzio, lasciando
  // scritto altro, sarebbe peggio dell'errore.
  //
  // Un campo e' intero quando non dichiara `step` — e' la stessa distinzione
  // che fa il modello lato server (int contro float), e c'e' un test che
  // verifica che le due restino allineate.
  function fieldIsInteger(field) {
    return field.step === undefined;
  }

  function parseLooseNumber(raw) {
    const text = String(raw ?? "").trim().replace(",", ".");
    if (text === "") return null;
    const n = Number(text);
    return Number.isFinite(n) ? n : null;
  }

  function fieldNumber(input, field) {
    let n = parseLooseNumber(input.value);
    if (n === null) n = Number(field.default);
    if (fieldIsInteger(field)) n = Math.round(n);
    if (field.min !== undefined && n < field.min) n = field.min;
    if (field.max !== undefined && n > field.max) n = field.max;
    const text = String(n);
    if (input.value !== text) input.value = text;
    return text;
  }

  // I quattro campi del backtest non stanno nella tabella dei parametri:
  // vivono in pagina. Stessa regola, stessa riscrittura.
  function inputNumber(input, fallback, opts) {
    if (!input) return String(fallback);
    return fieldNumber(input, {
      default: fallback,
      step: opts && opts.integer ? undefined : (opts && opts.step) || 0.01,
      min: opts ? opts.min : undefined,
      max: opts ? opts.max : undefined,
    });
  }

  // I parametri di una strategia come oggetto, per chi li manda in JSON
  // (alert e archivio) invece che in query. Stesse regole: mai un NaN, che in
  // JSON diventa null e arriverebbe al server come parametro cancellato.
  function collectStrategyParams(container, strategyName) {
    const out = {};
    if (!container) return out;
    (STRATEGY_PARAM_FIELDS[strategyName] || []).forEach((field) => {
      const input = container.querySelector(`[name="${field.key}"]`);
      if (!input) return;
      if (field.type === "checkbox") out[field.key] = input.checked;
      else if (field.type === "select") out[field.key] = input.value;
      else out[field.key] = Number(fieldNumber(input, field));
    });
    return out;
  }

  // One dropdown is all the user picks — HTF/MTF for the multi-timeframe SMC
  // confluence engine are derived automatically from it (two and four steps
  // up the canonical ladder), instead of three interval pickers that could
  // drift out of sync with each other.
  const PRIMARY_TO_TRIAD = {
    "1m": { ltf: "1m", mtf: "15m", htf: "4h" },
    "5m": { ltf: "5m", mtf: "1h", htf: "1d" },
    "15m": { ltf: "15m", mtf: "1h", htf: "1d" },
    "30m": { ltf: "30m", mtf: "4h", htf: "1d" },
    "1h": { ltf: "1h", mtf: "4h", htf: "1w" },
    "4h": { ltf: "4h", mtf: "1d", htf: "1w" },
    "1d": { ltf: "1d", mtf: "1w", htf: "1M" },
    "2d": { ltf: "2d", mtf: "1w", htf: "1M" },
    "3d": { ltf: "3d", mtf: "1w", htf: "1M" },
    "5d": { ltf: "5d", mtf: "1M", htf: "1M" },
    "1w": { ltf: "1w", mtf: "1M", htf: "1M" },
    "1M": { ltf: "1M", mtf: "1M", htf: "1M" },
  };

  // ---- Shared helpers ----

  // showTabError: inject a visible error paragraph inside a container element.
  function showTabError(containerId, msg) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const existing = container.querySelector(".tab-error-msg");
    if (existing) existing.remove();
    const p = document.createElement("p");
    p.className = "tab-error-msg";
    p.textContent = msg;
    container.prepend(p);
  }

  // withAsyncButton: disable a button while an async fn runs, then restore it.
  async function withAsyncButton(btn, fn, loadingText) {
    const original = btn.textContent;
    btn.disabled = true;
    if (loadingText !== undefined) btn.textContent = loadingText;
    try {
      await fn();
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  }

  // Every pair-suggestion list is placed here (Lorenzo, 16/10: "vanno visti
  // tutti nella loro interezza"). The list moves to <body>, so position:fixed
  // is measured on the screen and not on an animated or transformed panel
  // (in the Lab that pushed it off the right edge); it is at least 560px
  // wide whatever the field, never wider than the screen, and opens above
  // the field when there is more room there.
  function placeSuggestionList(list, anchorEl) {
    if (!list || !anchorEl) return;
    if (list.parentElement !== document.body) document.body.appendChild(list);
    const rect = anchorEl.getBoundingClientRect();
    const vw = window.innerWidth, vh = window.innerHeight;
    const width = Math.min(Math.max(rect.width, 560), vw - 16);
    const left = Math.min(Math.max(rect.left, 8), vw - width - 8);
    const below = vh - rect.bottom - 12, above = rect.top - 12;
    list.style.left = `${left}px`;
    list.style.width = `${width}px`;
    if (below >= 220 || below >= above) {
      list.style.top = `${rect.bottom + 4}px`;
      list.style.bottom = "";
      list.style.maxHeight = `${Math.max(160, Math.min(420, below))}px`;
    } else {
      list.style.top = "";
      list.style.bottom = `${vh - rect.top + 4}px`;
      list.style.maxHeight = `${Math.max(160, Math.min(420, above))}px`;
    }
  }

  // makeSuggestController: unified autocomplete factory for symbol search inputs.
  // Each controller returned is a plain object with { suggestions, activeIndex, resolved }
  // plus methods { fetch(query), render(anchorEl?), clear(), handleKey(e) }.
  // - fetchItems: async (query) => Item[]  — custom fetch logic
  // - listId:     id of the <ul> dropdown element
  // - anchorId:   id of the element used to position the dropdown
  // - onSelect:   called with the chosen Item
  // - elFn:       element lookup function, defaults to the global el()
  function makeSuggestController({ fetchItems, listId, anchorId, onSelect, elFn }) {
    const _el = elFn || el;
    let _anchorEl = null;

    const ctrl = {
      suggestions: [],
      activeIndex: -1,
      resolved: null,

      async fetch(query) {
        try {
          ctrl.suggestions = await fetchItems(query);
        } catch (err) {
          console.error("pair suggestions failed for", listId, err);
          ctrl.suggestions = [];
        }
        ctrl.activeIndex = -1;
        // Lazily resolve anchor element on first use.
        if (!_anchorEl && anchorId) _anchorEl = _el(anchorId);
        ctrl.render(_anchorEl);
      },

      render(anchorEl) {
        if (anchorEl) _anchorEl = anchorEl;
        const list = _el(listId);
        list.innerHTML = "";
        if (!ctrl.suggestions.length) { list.classList.add("hidden"); return; }
        placeSuggestionList(list, _anchorEl);
        ctrl.suggestions.forEach((item, i) => {
          const li = document.createElement("li");
          li.className = i === ctrl.activeIndex ? "active" : "";
          const main = document.createElement("span");
          main.className = "sug-main";
          const sym = document.createElement("span");
          sym.className = "sug-symbol";
          sym.textContent = shortSymbol(item.symbol);
          sym.title = item.symbol;
          const name = document.createElement("span");
          name.className = "sug-name";
          name.textContent = item.name || "";
          main.appendChild(sym);
          main.appendChild(name);
          const exch = document.createElement("span");
          exch.className = "sug-exchange sug-exchange-" + (item.provider || "");
          exch.textContent = item.exchange || "";
          li.appendChild(main);
          li.appendChild(exch);
          li.addEventListener("mousedown", (e) => { e.preventDefault(); onSelect(item); });
          list.appendChild(li);
        });
        list.classList.remove("hidden");
      },

      clear() {
        ctrl.suggestions = [];
        ctrl.activeIndex = -1;
        const list = _el(listId);
        list.classList.add("hidden");
        list.innerHTML = "";
      },

      handleKey(e) {
        const list = _el(listId);
        if (list.classList.contains("hidden")) return;
        if (e.key === "ArrowDown") {
          e.preventDefault();
          ctrl.activeIndex = Math.min(ctrl.activeIndex + 1, ctrl.suggestions.length - 1);
          ctrl.render();
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          ctrl.activeIndex = Math.max(ctrl.activeIndex - 1, 0);
          ctrl.render();
        } else if (e.key === "Enter") {
          if (ctrl.activeIndex >= 0) {
            e.preventDefault();
            onSelect(ctrl.suggestions[ctrl.activeIndex]);
          } else {
            ctrl.clear();
          }
        } else if (e.key === "Escape") {
          ctrl.clear();
        }
      },
    };

    return ctrl;
  }

  // ---- Series Primitive: filled rectangle between two (time, price) points ----
  function positionsBox(pos1, pos2, pixelRatio) {
    const a = Math.round(pixelRatio * pos1);
    const b = Math.round(pixelRatio * pos2);
    return { position: Math.min(a, b), length: Math.abs(b - a) + 1 };
  }

  class RectangleRenderer {
    constructor(p1, p2, fillColor, borderColor, style) {
      this._p1 = p1;
      this._p2 = p2;
      this._fillColor = fillColor;
      this._borderColor = borderColor;
      // { extendRight: bool } — una zona non ancora riempita non finisce
      // sull'ultima candela: continua a valere finche' il prezzo non ci torna
      // dentro, ed e' cosi' che la disegna TradingView. Fermarla sull'ultima
      // barra le fa sembrare tutte scadute.
      this._style = style || {};
    }
    draw(target) {
      target.useBitmapCoordinateSpace((scope) => {
        if (this._p1.x === null || this._p1.y === null || this._p2.x === null || this._p2.y === null) return;
        const ctx = scope.context;
        const h = positionsBox(this._p1.x, this._p2.x, scope.horizontalPixelRatio);
        const v = positionsBox(this._p1.y, this._p2.y, scope.verticalPixelRatio);
        // Fino al bordo destro del riquadro, non fino all'ultima candela: lo
        // spazio vuoto a destra del grafico fa parte del futuro in cui la zona
        // e' ancora valida.
        const width = this._style.extendRight
          ? Math.max(0, scope.bitmapSize.width - h.position)
          : h.length;
        ctx.fillStyle = this._fillColor;
        ctx.fillRect(h.position, v.position, width, v.length);
        ctx.strokeStyle = this._borderColor;
        ctx.lineWidth = 1;
        if (this._style.extendRight) {
          // Tre lati: quello destro chiuderebbe una zona che non e' finita.
          ctx.beginPath();
          ctx.moveTo(h.position + 0.5, v.position);
          ctx.lineTo(h.position + 0.5, v.position + v.length);
          ctx.moveTo(h.position, v.position + 0.5);
          ctx.lineTo(h.position + width, v.position + 0.5);
          ctx.moveTo(h.position, v.position + v.length - 0.5);
          ctx.lineTo(h.position + width, v.position + v.length - 0.5);
          ctx.stroke();
        } else {
          ctx.strokeRect(h.position, v.position, h.length, v.length);
        }
      });
    }
  }

  class RectanglePaneView {
    constructor(source) {
      this._source = source;
      this._p1 = { x: null, y: null };
      this._p2 = { x: null, y: null };
    }
    update() {
      const { chart, series, point1, point2 } = this._source;
      if (!chart || !series) return;
      const y1 = series.priceToCoordinate(point1.price);
      const y2 = series.priceToCoordinate(point2.price);
      const timeScale = chart.timeScale();
      const x1 = timeScale.timeToCoordinate(point1.time);
      const x2 = timeScale.timeToCoordinate(point2.time);
      this._p1 = { x: x1, y: y1 };
      this._p2 = { x: x2, y: y2 };
    }
    renderer() {
      return new RectangleRenderer(
        this._p1, this._p2, this._source.fillColor, this._source.borderColor,
        this._source.style,
      );
    }
    zOrder() {
      return "normal";
    }
  }

  class RectanglePrimitive {
    constructor(point1, point2, fillColor, borderColor, style) {
      this.point1 = point1;
      this.point2 = point2;
      this.fillColor = fillColor;
      this.borderColor = borderColor;
      this.style = style || {};
      this.chart = null;
      this.series = null;
      this._paneViews = [new RectanglePaneView(this)];
    }
    attached({ chart, series }) {
      this.chart = chart;
      this.series = series;
    }
    detached() {
      this.chart = null;
      this.series = null;
    }
    updateAllViews() {
      this._paneViews.forEach((v) => v.update());
    }
    paneViews() {
      return this._paneViews;
    }
  }

  // ---- Series Primitive: a full-height vertical band behind the candles,
  // used to shade alternating calendar days on intraday timeframes
  // (TradingView's faint day-separator stripes). zOrder "bottom" so it
  // never covers the candles or any other overlay. ----
  class SessionBandRenderer {
    constructor(p1x, p2x, fillColor) {
      this._p1x = p1x;
      this._p2x = p2x;
      this._fillColor = fillColor;
    }
    draw(target) {
      target.useBitmapCoordinateSpace((scope) => {
        if (this._p1x === null || this._p2x === null) return;
        const ctx = scope.context;
        const h = positionsBox(this._p1x, this._p2x, scope.horizontalPixelRatio);
        ctx.fillStyle = this._fillColor;
        ctx.fillRect(h.position, 0, h.length, scope.bitmapSize.height);
      });
    }
  }

  class SessionBandPaneView {
    constructor(source) {
      this._source = source;
      this._p1x = null;
      this._p2x = null;
    }
    update() {
      const { chart, point1, point2 } = this._source;
      if (!chart) return;
      this._p1x = chart.timeScale().timeToCoordinate(point1.time);
      this._p2x = chart.timeScale().timeToCoordinate(point2.time);
    }
    renderer() {
      return new SessionBandRenderer(this._p1x, this._p2x, this._source.fillColor);
    }
    zOrder() {
      return "bottom";
    }
  }

  class SessionBandPrimitive {
    constructor(point1, point2, fillColor) {
      this.point1 = point1;
      this.point2 = point2;
      this.fillColor = fillColor;
      this.chart = null;
      this.series = null;
      this._paneViews = [new SessionBandPaneView(this)];
    }
    attached({ chart, series }) {
      this.chart = chart;
      this.series = series;
    }
    detached() {
      this.chart = null;
      this.series = null;
    }
    updateAllViews() {
      this._paneViews.forEach((v) => v.update());
    }
    paneViews() {
      return this._paneViews;
    }
  }

  // ---- Series Primitive: freehand line between two (time, price) points,
  // optionally with an arrowhead at the second point (reused for both the
  // Trend Line and Arrow drawing tools) ----
  class LineRenderer {
    constructor(p1, p2, color, width, arrow) {
      this._p1 = p1;
      this._p2 = p2;
      this._color = color;
      this._width = width;
      this._arrow = arrow;
    }
    draw(target) {
      target.useBitmapCoordinateSpace((scope) => {
        if (this._p1.x === null || this._p1.y === null || this._p2.x === null || this._p2.y === null) return;
        const ctx = scope.context;
        const x1 = this._p1.x * scope.horizontalPixelRatio;
        const y1 = this._p1.y * scope.verticalPixelRatio;
        const x2 = this._p2.x * scope.horizontalPixelRatio;
        const y2 = this._p2.y * scope.verticalPixelRatio;
        ctx.strokeStyle = this._color;
        ctx.lineWidth = this._width * scope.horizontalPixelRatio;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
        if (this._arrow) {
          const angle = Math.atan2(y2 - y1, x2 - x1);
          const headLen = 9 * scope.horizontalPixelRatio;
          ctx.beginPath();
          ctx.moveTo(x2, y2);
          ctx.lineTo(x2 - headLen * Math.cos(angle - Math.PI / 6), y2 - headLen * Math.sin(angle - Math.PI / 6));
          ctx.lineTo(x2 - headLen * Math.cos(angle + Math.PI / 6), y2 - headLen * Math.sin(angle + Math.PI / 6));
          ctx.closePath();
          ctx.fillStyle = this._color;
          ctx.fill();
        }
      });
    }
  }

  class LinePaneView {
    constructor(source) {
      this._source = source;
      this._p1 = { x: null, y: null };
      this._p2 = { x: null, y: null };
    }
    update() {
      const { chart, series, point1, point2 } = this._source;
      if (!chart || !series) return;
      this._p1 = { x: chart.timeScale().timeToCoordinate(point1.time), y: series.priceToCoordinate(point1.price) };
      this._p2 = { x: chart.timeScale().timeToCoordinate(point2.time), y: series.priceToCoordinate(point2.price) };
    }
    renderer() {
      return new LineRenderer(this._p1, this._p2, this._source.color, this._source.width, this._source.arrow);
    }
    zOrder() {
      return "normal";
    }
  }

  class LinePrimitive {
    constructor(point1, point2, color, width, arrow) {
      this.point1 = point1;
      this.point2 = point2;
      this.color = color;
      this.width = width;
      this.arrow = arrow;
      this.chart = null;
      this.series = null;
      this._paneViews = [new LinePaneView(this)];
    }
    attached({ chart, series }) {
      this.chart = chart;
      this.series = series;
    }
    detached() {
      this.chart = null;
      this.series = null;
    }
    updateAllViews() {
      this._paneViews.forEach((v) => v.update());
    }
    paneViews() {
      return this._paneViews;
    }
  }

  // ---- Series Primitive: a text label anchored to one (time, price) point ----
  class TextRenderer {
    constructor(p, text, color) {
      this._p = p;
      this._text = text;
      this._color = color;
    }
    draw(target) {
      target.useBitmapCoordinateSpace((scope) => {
        if (this._p.x === null || this._p.y === null || !this._text) return;
        const ctx = scope.context;
        ctx.font = `${11 * scope.verticalPixelRatio}px "IBM Plex Mono", monospace`;
        ctx.fillStyle = this._color;
        ctx.textBaseline = "bottom";
        ctx.fillText(this._text, this._p.x * scope.horizontalPixelRatio + 5, this._p.y * scope.verticalPixelRatio - 5);
      });
    }
  }

  class TextPaneView {
    constructor(source) {
      this._source = source;
      this._p = { x: null, y: null };
    }
    update() {
      const { chart, series, point } = this._source;
      if (!chart || !series) return;
      this._p = { x: chart.timeScale().timeToCoordinate(point.time), y: series.priceToCoordinate(point.price) };
    }
    renderer() {
      return new TextRenderer(this._p, this._source.text, this._source.color);
    }
    zOrder() {
      return "normal";
    }
  }

  class TextPrimitive {
    constructor(point, text, color) {
      this.point = point;
      this.text = text;
      this.color = color;
      this.chart = null;
      this.series = null;
      this._paneViews = [new TextPaneView(this)];
    }
    attached({ chart, series }) {
      this.chart = chart;
      this.series = series;
    }
    detached() {
      this.chart = null;
      this.series = null;
    }
    updateAllViews() {
      this._paneViews.forEach((v) => v.update());
    }
    paneViews() {
      return this._paneViews;
    }
  }

  // ---- Series Primitive: Fibonacci retracement — horizontal levels spanning
  // the two anchor points, each labeled with its ratio and price ----
  const FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];

  class FibRenderer {
    constructor(x1, x2, levels, color) {
      this._x1 = x1;
      this._x2 = x2;
      this._levels = levels; // [{ y, label }]
      this._color = color;
    }
    draw(target) {
      target.useBitmapCoordinateSpace((scope) => {
        if (this._x1 === null || this._x2 === null) return;
        const ctx = scope.context;
        const xa = Math.min(this._x1, this._x2) * scope.horizontalPixelRatio;
        const xb = Math.max(this._x1, this._x2) * scope.horizontalPixelRatio;
        ctx.lineWidth = Math.max(1, scope.verticalPixelRatio);
        ctx.font = `${10 * scope.verticalPixelRatio}px "IBM Plex Mono", monospace`;
        this._levels.forEach(({ y, label }) => {
          if (y === null) return;
          const yy = y * scope.verticalPixelRatio;
          ctx.strokeStyle = this._color;
          ctx.beginPath();
          ctx.moveTo(xa, yy);
          ctx.lineTo(xb, yy);
          ctx.stroke();
          ctx.fillStyle = this._color;
          ctx.fillText(label, xb + 4, yy + 4);
        });
      });
    }
  }

  class FibPaneView {
    constructor(source) {
      this._source = source;
      this._x1 = null;
      this._x2 = null;
      this._levels = [];
    }
    update() {
      const { chart, series, point1, point2 } = this._source;
      if (!chart || !series) return;
      this._x1 = chart.timeScale().timeToCoordinate(point1.time);
      this._x2 = chart.timeScale().timeToCoordinate(point2.time);
      this._levels = FIB_LEVELS.map((ratio) => {
        const price = point1.price + ratio * (point2.price - point1.price);
        return { y: series.priceToCoordinate(price), label: `${(ratio * 100).toFixed(1)}% (${price.toFixed(2)})` };
      });
    }
    renderer() {
      return new FibRenderer(this._x1, this._x2, this._levels, this._source.color);
    }
    zOrder() {
      return "normal";
    }
  }

  class FibPrimitive {
    constructor(point1, point2, color) {
      this.point1 = point1;
      this.point2 = point2;
      this.color = color;
      this.chart = null;
      this.series = null;
      this._paneViews = [new FibPaneView(this)];
    }
    attached({ chart, series }) {
      this.chart = chart;
      this.series = series;
    }
    detached() {
      this.chart = null;
      this.series = null;
    }
    updateAllViews() {
      this._paneViews.forEach((v) => v.update());
    }
    paneViews() {
      return this._paneViews;
    }
  }

  // ---- App state ----
  const state = {
    user: null, // { id, email, telegram_chat_id } | null — set by checkAuth()
    // Crypto per difetto: le azioni sono spente lato server
    // (settings.stocks_enabled), e partire da "stock" faceva sbagliare la
    // prima richiesta a ogni caricamento.
    assetType: "crypto",
    cryptoExchange: "mexc", // set automatically from the picked search suggestion
    // Always "ltf" now — the single timeframe dropdown *is* the chart's
    // timeframe; MTF/HTF exist only for the derived confluence context.
    activeTimeframe: "ltf",
    data: null,
    suggestions: [],
    activeSuggestionIndex: -1,
    liveSocket: null,
    liveRefreshTimer: null,
    seenAlertKeys: new Set(),
    alertsSeeded: false,
    watchlistAssetType: "stock",
    favorites: [], // [{ id, symbol, asset_type, exchange }] — Watchlist tab, quick chart navigation
    favoriteQuotes: {}, // entry id -> { price, change_pct } from /api/favorites/quotes
    autoOpenFavoriteId: null, // ticker appena aggiunto: apre la riga e chiede subito la strategia
    favoriteFilter: "all", // "all" | "stock" | "crypto"
    alertEntries: [], // last /api/watchlist load — cross-checked for the favorite row's alert-bell indicator
    pineScripts: [],
    activePineScriptId: null,
    activePineParams: [],
    activePineIsStrategy: true,
    pineActive: false,
    pineLastResult: null,
    // I parametri di ESECUZIONE del backtest (capitale, taglia, commissione,
    // slippage) con cui e' stato applicato l'ultimo risultato del Laboratorio
    // o dell'archivio — null quando non e' mai stato applicato niente, e in
    // quel caso il grafico usa i suoi valori "puliti" di sempre (100%
    // equity, zero costi). Vedi getStrategyAndBacktestQuery().
    chartBacktestOverride: null,
    availableStrategies: [],
    logScale: false,
    // Libreria indicatori pandas-ta (151 voci) selezionati dall'utente dalla
    // tendina cercabile — persistono per browser, indipendenti dal ticker
    // aperto, perche' sono strumenti generici come EMA/RSI, non livelli
    // specifici di un simbolo.
    indicatorCatalog: null, // popolato al primo uso da /api/indicators/catalog
    customIndicators: JSON.parse(localStorage.getItem("customIndicators") || "[]"), // [{id, label, kind}]
    favoriteIndicatorIds: new Set(JSON.parse(localStorage.getItem("favoriteIndicatorIds") || "[]")),
    // Kept minimal by default — every structure/liquidity level draws its own
    // chart label, and turning them all on at once buries the price action
    // (especially on narrow screens).
    layers: {
      order_block: false,
      fvg: false,
      liquidity: false,
      structure: false,
      confluence: false,
      ema: false,
      bbands: false,
      vwap: false,
      bmsb: false,
      rsi: false,
      macd: false,
      stoch: false,
      fibonacci: false,
      patterns: false,
      hints: false,
      divergences: false,
      angleLines: false,
      elliott: false,
    },
  };

  const overlays = {
    lineSeries: [],
    priceLines: [],
    primitives: [],
    hitZones: [], // {price_low, price_high, start_time, end_time, label}
  };

  let mainChart, candleSeries, rsiChart, rsiSeries, macdChart, macdLineSeries, macdSignalSeries, macdHistSeries;
  let stochChart, stochKSeries, stochDSeries;
  let equityChart, equitySeries;

  // Indicatori scelti dalla libreria pandas-ta: quelli "overlay" vivono come
  // linee extra su mainChart (in overlaySeriesList, ripulite ad ogni giro
  // insieme al resto in clearOverlays); quelli "oscillator" aprono un
  // riquadro proprio, creato e distrutto dinamicamente perche' — a differenza
  // di RSI/MACD/Stocastico — non hanno un contenitore fisso in index.html.
  let customOverlaySeriesList = [];
  let customOscCharts = {}; // indicator id -> { container, chart }
  const CUSTOM_IND_COLORS = ["#5b9cf6", "#f6a25b", "#c17ee8", "#5bc9c9", "#e85b8f", "#a8c95b"];

  // "Frattali": ricopia un intervallo di candele gia' successo subito dopo
  // l'ultima candela vera, come un TradingView-style pattern replay — per
  // confrontare a occhio se un movimento passato si sta ripetendo ora.
  // Ogni voce: { id, series, label, startTime, interval, projected }.
  let fractalReplays = [];
  let selectedFractalId = null;
  // { id, startTime, startPrice, startPixelX, baseLabelLeft, originalProjected, moved }
  let fractalDragState = null;

  const tooltipEl = el("tooltip");

  // Chart containers start hidden (display:none) until the first search
  // succeeds, so the library's built-in autoSize can miss the 0 -> real
  // size transition. A manual ResizeObserver per container is more robust.
  function observeResize(container, chart) {
    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) {
        chart.resize(width, height);
        // A pane switched on is laid out at width 0 and fits its whole
        // history: RSI/MACD/Stoch showed years under a chart of weeks.
        if (mainChart && chart !== mainChart) syncPaneRange(chart);
      }
    });
    ro.observe(container);
  }

  function syncPaneRange(chart) {
    const range = mainChart?.timeScale().getVisibleLogicalRange();
    if (range) {
      try { chart.timeScale().setVisibleLogicalRange(range); } catch { /* chart being removed */ }
    }
    scheduleScaleAlign();
  }

  // Two-way sync of the time axis. The price chart is the hub: a pane that
  // moves sets the price chart's range, which hands it on to the others.
  // `rangeSyncing` and the equality check stop the echo of our own calls.
  let rangeSyncing = false;
  function sameRange(a, b) {
    return !!a && !!b && Math.abs(a.from - b.from) < 1e-3 && Math.abs(a.to - b.to) < 1e-3;
  }
  function followPane(chart, container) {
    chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (!range || rangeSyncing || !mainChart) return;
      // A hidden or empty pane clamps its range on its own: never let it
      // drag the price chart along.
      if (container.classList.contains("hidden") || !container.offsetWidth) return;
      if (sameRange(range, mainChart.timeScale().getVisibleLogicalRange())) return;
      rangeSyncing = true;
      try { mainChart.timeScale().setVisibleLogicalRange(range); } catch { /* chart being removed */ }
      finally { rangeSyncing = false; }
    });
  }

  // The panes share the logical range, not the pixels: a price scale wider
  // than the oscillators' ("-0.000500" against "80.00") leaves the candles a
  // narrower plot, and the same bar lands further right in the panes below
  // (12/10, low of the price under the stochastic's dip 40 px later).
  // `minimumWidth: 72` was not enough as soon as the prices had 6 decimals:
  // every chart gets the widest scale's width.
  const BASE_SCALE_WIDTH = 72;
  let scaleAlignRaf = 0;
  function syncedCharts() {
    const list = [mainChart, rsiChart, macdChart, stochChart];
    Object.values(customOscCharts || {}).forEach(({ chart }) => list.push(chart));
    return list.filter(Boolean);
  }
  function scheduleScaleAlign() {
    if (scaleAlignRaf || !mainChart) return;
    scaleAlignRaf = requestAnimationFrame(() => {
      scaleAlignRaf = 0;
      // Two frames: the library lays the new labels out on its own frame.
      requestAnimationFrame(alignPaneScales);
    });
  }
  function alignPaneScales() {
    const charts = syncedCharts();
    let widest = BASE_SCALE_WIDTH;
    charts.forEach((c) => {
      try { widest = Math.max(widest, Math.ceil(c.priceScale("right").width())); } catch { /* removed */ }
    });
    charts.forEach((c) => {
      try {
        if (c.options().rightPriceScale.minimumWidth !== widest) {
          c.applyOptions({ rightPriceScale: { minimumWidth: widest } });
        }
      } catch { /* removed */ }
    });
  }
  // A new symbol starts from the base width again, or a scale that was once
  // wide (a coin with many decimals) would keep every chart wide forever.
  function resetPaneScales() {
    syncedCharts().forEach((c) => {
      try { c.applyOptions({ rightPriceScale: { minimumWidth: BASE_SCALE_WIDTH } }); } catch { /* removed */ }
    });
    scheduleScaleAlign();
  }

  // Price format for an oscillator in price units (MACD): two decimals
  // turned every value of a $0.000004 coin into "0.00".
  function oscPrecisionFor(values) {
    let max = 0;
    values.forEach((v) => { if (v != null && Number.isFinite(v)) max = Math.max(max, Math.abs(v)); });
    if (!max || max >= 1) return { type: "price", precision: 2, minMove: 0.01 };
    const precision = Math.min(12, Math.max(2, -Math.floor(Math.log10(max)) + 2));
    return { type: "price", precision, minMove: 1 / 10 ** precision };
  }

  const SUB_CHART_MIN_H = 70;
  const SUB_CHART_MAX_H = 420;

  function loadSubChartHeights() {
    try { return JSON.parse(localStorage.getItem("subChartHeights") || "{}"); } catch { return {}; }
  }

  function saveSubChartHeight(key, h) {
    const all = loadSubChartHeights();
    all[key] = h;
    try { localStorage.setItem("subChartHeights", JSON.stringify(all)); } catch { /* storage piena o bloccata */ }
  }

  // Un manico in cima al riquadro (RSI/MACD/Stocastico, o uno degli
  // oscillatori custom creati al volo) — trascinarlo su/giu' regola solo
  // quel riquadro, l'altezza persiste per browser cosi' non si riparte da
  // zero ad ogni ricarica. observeResize() gia' presente si accorge da solo
  // del nuovo container.clientHeight, niente da richiamare qui a mano.
  function makeSubChartResizable(container, key) {
    const saved = loadSubChartHeights()[key];
    if (saved) container.style.height = `${saved}px`;
    const handle = document.createElement("div");
    handle.className = "sub-chart-resize-handle";
    handle.title = "Drag to resize";
    container.appendChild(handle);
    let startY = 0, startH = 0;
    const onMove = (e) => {
      const h = Math.max(SUB_CHART_MIN_H, Math.min(SUB_CHART_MAX_H, startH + (startY - e.clientY)));
      container.style.height = `${h}px`;
    };
    const onUp = () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      saveSubChartHeight(key, container.clientHeight);
    };
    handle.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      startY = e.clientY;
      startH = container.clientHeight;
      document.addEventListener("pointermove", onMove);
      document.addEventListener("pointerup", onUp);
    });
  }

  // `refit` va chiesto quando a cambiare e' stato il *layout*, non la
  // finestra: passando da Analizza al Lab la colonna del grafico si
  // restringe, e ridimensionare la tela senza riadattare l'intervallo
  // visibile lasciava le candele schiacciate in un angolo con mezzo
  // riquadro bianco. Su un semplice ridimensionamento della finestra non
  // si riadatta invece niente, o si butterebbe via lo zoom dell'utente a
  // ogni pixel.
  function resizeAllCharts(refit = false) {
    [
      [el("main-chart"), mainChart],
      [el("rsi-chart"), rsiChart],
      [el("macd-chart"), macdChart],
      [el("stoch-chart"), stochChart],
      ...Object.values(customOscCharts).map(({ container, chart }) => [container, chart]),
    ].forEach(([container, chart]) => {
      // I sub-chart nascono solo quando il loro indicatore viene acceso:
      // prima di allora qui c'e' null, e senza questo controllo l'errore
      // fermava anche il ridimensionamento dei grafici che esistono.
      if (!container || !chart) return;
      if (container.clientWidth > 0 && container.clientHeight > 0) {
        chart.resize(container.clientWidth, container.clientHeight);
        if (refit) {
          try { chart.timeScale().fitContent(); } catch { /* niente dati ancora */ }
        }
      }
    });
    repositionFractalLabels();
  }

  function populateIntervalSelects() {
    const select = el("interval-primary");
    CANONICAL_INTERVALS.forEach((iv) => {
      const opt = document.createElement("option");
      opt.value = iv;
      opt.textContent = iv;
      if (iv === DEFAULT_PRIMARY_INTERVAL) opt.selected = true;
      select.appendChild(opt);
    });

    const wlSelect = el("watchlist-interval");
    CANONICAL_INTERVALS.forEach((iv) => {
      const opt = document.createElement("option");
      opt.value = iv;
      opt.textContent = iv;
      if (iv === "1d") opt.selected = true;
      wlSelect.appendChild(opt);
    });
  }

  function hasStrategyOption(name) {
    const sel = el("active-strategy-select");
    return !!sel && [...sel.options].some((o) => o.value === name);
  }

  async function populateStrategySelects() {
    let strategies = [];
    try {
      const resp = await fetch("/api/strategies");
      if (resp.ok) strategies = await resp.json();
    } catch (err) {
      strategies = [];
    }
    // the backend's first strategy stays the one selected at start
    state.defaultStrategy = strategies[0] || "";
    strategies = orderStrategies(strategies);
    state.availableStrategies = strategies;
    const select = el("active-strategy-select");
    select.innerHTML = strategyOptionsHtml(strategies);
    if (state.defaultStrategy) select.value = state.defaultStrategy;
    renderStrategyParamsFields();
    updateOptimizeButtonVisibility();
  }

  // ---- Auto-optimize: random-search the active strategy's own parameter
  // space (STRATEGY_PARAM_FIELDS) against the deep backtest history, scored
  // by profit factor. Every strategy in the registry has one — the backend
  // rejects strategy names it has no search space for, so this list just
  // has to stay a subset of that. ----
  const OPTIMIZABLE_STRATEGIES = new Set([
    "Lorenzo (trend-follower)",
    "Lorenzo reversal (long only)",
    "Accumulo / Distribuzione (long-term)",
    "Gabriele (RSI+BB reversal)",
    "Gabriele 2 (RSI+BB long/short)",
    "Claudio 4H",
  ]);

  function updateOptimizeButtonVisibility() {
    const optimizable = OPTIMIZABLE_STRATEGIES.has(el("active-strategy-select").value);
    el("optimize-strategy-btn").classList.toggle("hidden", !optimizable);
    if (!optimizable) el("optimize-strategy-result").classList.add("hidden");
  }

  async function runStrategyOptimize() {
    if (!state.data) return;
    const btn = el("optimize-strategy-btn");
    const resultEl = el("optimize-strategy-result");
    resultEl.classList.add("hidden");
    await withAsyncButton(btn, async () => {
      const strategyName = el("active-strategy-select").value;
      const backtestParams = new URLSearchParams({
        initial_capital: "1000", qty_pct_of_equity: "100",
        commission_pct: "0", slippage_pct: "0",
        stop_loss_pct: "0", take_profit_pct: "0",
      });
      const url =
        `/api/optimize?symbol=${encodeURIComponent(state.data.symbol)}&asset_type=${state.assetType}` +
        `&exchange=${state.cryptoExchange}&ltf_interval=${getSelectedIntervals().ltf}` +
        `&strategy_name=${encodeURIComponent(strategyName)}&${backtestParams.toString()}`;
      const resp = await fetch(url);
      const body = await resp.json();
      if (!resp.ok) {
        const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
        throw new Error(detail || `Error ${resp.status}`);
      }

      Object.entries(body.params).forEach(([key, value]) => {
        const field = form.elements[key];
        if (!field) return;
        if (field.type === "checkbox") field.checked = !!value;
        else field.value = value;
      });

      const bt = body.backtest;
      const pf = bt.profit_factor !== null ? bt.profit_factor.toFixed(2) : "∞";
      const dd = Math.abs(bt.max_drawdown_pct).toFixed(1);
      resultEl.innerHTML = `Best found across <b>${body.trials_evaluated}</b> combinations (${bt.interval}): profit factor <b>${pf}</b>, drawdown <b>-${dd}%</b>, ${bt.num_trades} trades, win rate ${bt.win_rate_pct !== null ? bt.win_rate_pct.toFixed(0) : "—"}%.`;
      resultEl.classList.remove("hidden");

      await runAnalysis(state.data.symbol);
    }, "Optimizing… (10-25s)").catch((err) => {
      showError(err.message || "Optimization failed.");
    });
  }

  // Each ticker is a card that expands to show one on/off toggle per
  // available strategy — a ticker can have several strategies watched at
  // once (previously one strategy meant one whole separate watchlist row).
  // ---- Auth: cookie session, login/register modal, per-user Telegram chat id ----
  let _prefSaveTimer = null;
  async function loadPreferences() {
    if (!state.user) return null;
    try {
      const resp = await fetch("/api/preferences");
      return resp.ok ? await resp.json() : null;
    } catch { return null; }
  }
  // Embedded in the on-chain app's token page (?embed=1): the chart only,
  // and nothing the embed does may overwrite the user's saved session.
  const EMBED = new URLSearchParams(location.search).get("embed") === "1";
  if (EMBED) document.documentElement.classList.add("embed-chart");
  function notifyParent(ok, why = "") {
    if (EMBED && window.parent !== window) window.parent.postMessage({ type: "embed-chart", ok, why }, location.origin);
  }
  let embedRetried = false;

  function savePreferences() {
    if (EMBED) return;
    if (!state.user) return;
    clearTimeout(_prefSaveTimer);
    _prefSaveTimer = setTimeout(async () => {
      const prefs = {
        ticker: el("ticker-input").value.trim() || "BTC",
        asset_type: state.assetType || "crypto",
        exchange: state.cryptoExchange || "mexc",
        interval: el("interval-primary")?.value || "1d",
        strategy: el("active-strategy-select")?.value || "",
        layers: { ...state.layers },
        log_scale: el("log-scale-toggle")?.checked || false,
        // Il tema viaggia con l'account e non col dispositivo: era salvato solo
        // nel browser, quindi lo stesso utente su due computer vedeva due temi
        // diversi — e chi non aveva mai scelto seguiva le impostazioni del suo
        // sistema operativo, che e' il motivo per cui uno vedeva bianco e
        // l'altro nero.
        theme: document.documentElement.getAttribute("data-theme") || "",
      };
      try {
        await fetch("/api/preferences", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(prefs),
        });
      } catch {}
    }, 2000);
  }

  let authMode = "login";
  let authGateActive = false; // true while the modal is blocking the whole app (not logged in yet)
  let appStarted = false; // startApp() runs once, either immediately or right after the gate clears

  // Fly.io scale-to-zero means the very first request of a cold session can
  // take several seconds while the machine boots — checkAuth() is that first
  // request, so a hint arms here and only surfaces if it actually runs long.
  let slowServerTimer = null;
  function armSlowServerHint() {
    clearTimeout(slowServerTimer);
    slowServerTimer = setTimeout(() => {
      el("server-wake-hint").classList.remove("hidden");
    }, 1200);
  }
  function disarmSlowServerHint() {
    clearTimeout(slowServerTimer);
    el("server-wake-hint").classList.add("hidden");
  }

  async function checkAuth() {
    armSlowServerHint();
    try {
      const resp = await fetch("/api/auth/me");
      const body = await resp.json();
      state.user = body.user;
    } catch (err) {
      state.user = null;
    } finally {
      disarmSlowServerHint();
    }
    updateAuthUI();
    // A chart opened before the login was known has not asked the account
    // for its drawings yet.
    if (state.user) { try { syncCurrentDrawings(); } catch { /* drawing layer not ready */ } }
  }

  function updateAuthUI() {
    const loggedIn = !!state.user;
    el("auth-toggle-btn").classList.toggle("hidden", loggedIn);
    el("auth-logout-btn").classList.toggle("hidden", !loggedIn);
    const emailEl = el("auth-user-email");
    emailEl.classList.toggle("hidden", !loggedIn);
    if (loggedIn) {
      emailEl.textContent = state.user.email;
      // narrow bars show only the initial (style.css, top bar compaction)
      emailEl.title = state.user.email;
      emailEl.dataset.initial = (state.user.email || "?").charAt(0).toUpperCase();
    }
    el("alert-login-prompt").classList.toggle("hidden", loggedIn);
    el("alert-authenticated").classList.toggle("hidden", !loggedIn);
    // Opera e' un'area separata da Alert ma con lo stesso cancello: le chiavi
    // di trading sono per utente, non per browser.
    el("opera-login-prompt").classList.toggle("hidden", loggedIn);
    el("opera-authenticated").classList.toggle("hidden", !loggedIn);
    if (loggedIn) {
      el("telegram-chat-id-input").value = state.user.telegram_chat_id || "";
      el("telegram-signal-chat-id-input").value = state.user.telegram_signal_chat_id || "";
      el("telegram-gems-chat-id-input").value = state.user.telegram_gems_chat_id || "";
      updateTelegramSetupUI();
      loadWatchlist();
      loadArchive();
      loadTradingJournal();
      loadAlertLog();
      loadPriceAlerts();
      startAlertLogPoll();
      loadBalances();
      loadTradingCredentials();
      loadFuturesCredentials();
      loadFavorites();
    } else {
      setBalancesVisible(false);
      if (_alertLogPollTimer) { clearInterval(_alertLogPollTimer); _alertLogPollTimer = null; }
    }
  }

  // The chat-ID setup box (with its raw bot-API URL instructions) only needs
  // to be seen once — after it's saved, collapse it to a one-line status chip
  // so it doesn't compete with the watchlist every time Alert is opened.
  // forceOpen re-expands it for editing, from the chip's "Modifica" link.
  function updateTelegramSetupUI(forceOpen) {
    const configured = !!(state.user && state.user.telegram_chat_id);
    el("telegram-status-chip").classList.toggle("hidden", !configured || forceOpen);
    el("telegram-setup").classList.toggle("hidden", configured && !forceOpen);
  }

  // Saldi is reachable two ways — the desktop right-panel tab and the Altro
  // menu item on mobile — both mirroring the same "visible only if the
  // account actually has exchange balances to show" condition.
  function setBalancesVisible(visible) {
    el("balances-tab-btn").classList.toggle("hidden", !visible);
    el("altro-saldi-item").classList.toggle("hidden", !visible);
  }

  // ---- Saldi tab: read-only exchange balances (MEXC/KuCoin) ----
  function renderBalanceAccount(name, data) {
    if (!data.configured) {
      return `<div class="balance-acct"><div class="balance-acct-head">${name}</div><p class="balance-empty">API keys not configured.</p></div>`;
    }
    if (data.error) {
      return `<div class="balance-acct"><div class="balance-acct-head">${name}</div><p class="balance-error">${data.error}</p></div>`;
    }
    if (!data.balances.length) {
      return `<div class="balance-acct"><div class="balance-acct-head">${name}</div><p class="balance-empty">No balance available.</p></div>`;
    }
    const rows = data.balances
      .map(
        (b) =>
          `<div class="balance-row"><span class="b-asset">${b.asset}</span><span class="b-qty">${b.total.toLocaleString("en-US", { maximumFractionDigits: 8 })}</span></div>`
      )
      .join("");
    return `<div class="balance-acct"><div class="balance-acct-head">${name}</div>${rows}</div>`;
  }

  async function loadBalances() {
    try {
      const resp = await fetch("/api/balances");
      if (resp.status === 403) {
        setBalancesVisible(false);
        return;
      }
      if (!resp.ok) {
        showTabError("balances-content", `Error loading balances (${resp.status}).`);
        return;
      }
      const body = await resp.json();
      setBalancesVisible(true);
      el("balances-content").innerHTML = renderBalanceAccount("MEXC", body.mexc) + renderBalanceAccount("KuCoin", body.kucoin);
      el("balances-updated").textContent = `Updated at ${new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}`;
    } catch (err) {
      showTabError("balances-content", "Couldn't load balances: network problem.");
    }
  }

  // ---- Trading Automatico: per-exchange API key config + enable toggle ----
  const TRADING_EXCHANGE_NAMES = { mexc: "MEXC", binance: "Binance", kucoin: "KuCoin", kraken: "Kraken", coinbase: "Coinbase", bitstamp: "Bitstamp" };
  const TRADING_EXCHANGES = Object.keys(TRADING_EXCHANGE_NAMES);

  // seed-0025 (il 422 muto sui parametri di strategia) ha gia' stabilito il
  // principio: un valore non valido non si sostituisce in silenzio, mandando
  // al server un numero diverso da quello scritto a schermo. Qui il campo
  // pilota quanto denaro si muove per trade sugli ordini automatici, quindi
  // lo stesso difetto conta ancora di piu'. Il valore corretto viene
  // RISCRITTO nel campo prima di partire, cosi' quello che gira e' quello
  // che si legge.
  function readNumericField(input, fallback, { min = 0, max = Infinity, integer = false } = {}) {
    if (!input) return fallback;
    let v = integer ? parseInt(input.value, 10) : parseFloat(input.value);
    if (!Number.isFinite(v) || v < min || v > max) {
      v = fallback;
      input.value = String(fallback);
    }
    return v;
  }

  async function loadTradingCredentials() {
    try {
      const resp = await fetch("/api/auth/trading");
      if (resp.status === 401) return; // not logged in — silently skip
      if (!resp.ok) return;
      const data = await resp.json();
      renderTradingCredentials(data);
    } catch (_) {
      // network error — silently skip
    }
  }

  function renderTradingCredentials(creds) {
    const container = el("trading-credentials-list");
    if (!container) return;

    container.innerHTML = creds.filter(c => TRADING_EXCHANGES.includes(c.exchange)).map(c => {
      const name = TRADING_EXCHANGE_NAMES[c.exchange] || c.exchange;
      const summaryText = c.api_key_set ? "Edit key" : "Set up API key";
      const savedNote = c.api_key_set
        ? `<div class="trading-cred-saved">🔒 Key saved and encrypted${c.created_at ? " — added on " + escapeHtml(new Date(c.created_at * 1000).toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" })) : ""}
             <button type="button" class="trading-cred-delete-btn" title="Delete this key">Delete</button></div>`
        : "";
      const passphraseField = c.exchange === "kucoin"
        ? `<label>Passphrase <input type="password" class="trading-passphrase" placeholder="leave empty to keep unchanged" /></label>`
        : "";
      return `<div class="trading-cred-card" data-exchange="${c.exchange}">
        <div class="trading-cred-exchange-row">
          <span class="trading-cred-name">${name}</span>
          <label class="trading-enabled-toggle">
            <input type="checkbox" class="trading-enabled-cb" ${c.enabled ? "checked" : ""}> Enabled
          </label>
        </div>
        ${savedNote}
        <details class="trading-cred-details">
          <summary>${summaryText}</summary>
          <div class="trading-cred-fields">
            <label>API Key <input type="text" class="trading-api-key" placeholder="leave empty to keep unchanged" autocomplete="off" /></label>
            <label>API Secret <input type="password" class="trading-api-secret" placeholder="leave empty to keep unchanged" autocomplete="off" /></label>
            ${passphraseField}
            <div class="trading-size-row">
              <label>Size type
                <select class="trading-size-mode">
                  <option value="fixed_usdt" ${c.size_mode === "fixed_usdt" ? "selected" : ""}>Fixed USDT</option>
                  <option value="pct_balance" ${c.size_mode === "pct_balance" ? "selected" : ""}>% of balance</option>
                </select>
              </label>
              <label>Value <input type="number" class="trading-size-val" value="${c.size_value}" min="1" step="1" /></label>
            </div>
            <button type="button" class="trading-save-btn">Save</button>
            <span class="trading-save-status"></span>
          </div>
        </details>
      </div>`;
    }).join("");

    // Save button handler (event delegation)
    container.addEventListener("click", async function handleTradingSave(e) {
      if (!e.target.classList.contains("trading-save-btn")) return;
      const card = e.target.closest(".trading-cred-card");
      if (!card) return;
      const exchange = card.dataset.exchange;
      const statusEl = card.querySelector(".trading-save-status");
      const body = {
        exchange,
        api_key: card.querySelector(".trading-api-key")?.value || "",
        api_secret: card.querySelector(".trading-api-secret")?.value || "",
        passphrase: card.querySelector(".trading-passphrase")?.value || "",
        enabled: card.querySelector(".trading-enabled-cb")?.checked || false,
        size_mode: card.querySelector(".trading-size-mode")?.value || "fixed_usdt",
        size_value: readNumericField(card.querySelector(".trading-size-val"), 10, { min: 1 }),
      };
      try {
        const resp = await fetch("/api/auth/trading", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (resp.ok) {
          statusEl.textContent = "Saved ✓";
          setTimeout(() => { statusEl.textContent = ""; }, 3000);
        } else {
          const err = await resp.json().catch(() => ({}));
          statusEl.textContent = err.detail || `Error (${resp.status})`;
        }
      } catch (_) {
        statusEl.textContent = "Network error";
      }
    });

    // Elimina: la chiave sparisce subito (nessuna riconferma richiesta,
    // l'azione e' gia' dietro un pannello aperto solo apposta) e la card
    // torna allo stato "non configurata" senza dover ricaricare la pagina.
    container.addEventListener("click", async function handleTradingDelete(e) {
      if (!e.target.classList.contains("trading-cred-delete-btn")) return;
      const card = e.target.closest(".trading-cred-card");
      if (!card) return;
      await fetch(`/api/auth/trading/${card.dataset.exchange}`, { method: "DELETE" });
      loadTradingCredentials();
    });

    // Enabled toggle handler (event delegation)
    container.addEventListener("change", async function handleTradingToggle(e) {
      if (!e.target.classList.contains("trading-enabled-cb")) return;
      const card = e.target.closest(".trading-cred-card");
      if (!card) return;
      const exchange = card.dataset.exchange;
      const body = {
        exchange,
        api_key: "",
        api_secret: "",
        passphrase: "",
        enabled: e.target.checked,
        size_mode: card.querySelector(".trading-size-mode")?.value || "fixed_usdt",
        size_value: readNumericField(card.querySelector(".trading-size-val"), 10, { min: 1 }),
      };
      try {
        await fetch("/api/auth/trading", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      } catch (_) {
        // silently ignore
      }
    });
  }

  // Il pair dell'ordine manuale si scrive a mano, ed e' l'unico campo di
  // tutta l'app che manda denaro vero senza che nessuno abbia confermato che
  // quella stringa esista sull'exchange scelto. Qui ha gli stessi
  // suggerimenti della watchlist, dalla stessa fonte (/api/symbols), filtrati
  // sull'exchange selezionato. Tre exchange su sei non hanno un provider dati
  // in questa app: li' il campo resta libero, ma lo dice invece di lasciar
  // credere che il silenzio sia una conferma.
  const MANUAL_PAIR_EXCHANGES = new Set(["mexc", "binance", "kucoin", "kraken"]);

  function manualPairHint(text, kind) {
    const p = el("manual-pair-hint");
    if (!p) return;
    p.textContent = text || "";
    p.className = "mo-pair-hint" + (kind ? " " + kind : "");
    p.classList.toggle("hidden", !text);
  }

  const moSuggest = makeSuggestController({
    listId: "manual-symbol-suggestions",
    anchorId: "manual-symbol",
    fetchItems: async (query) => {
      const exchange = el("manual-exchange")?.value;
      if (!MANUAL_PAIR_EXCHANGES.has(exchange)) return [];
      const resp = await fetch(`/api/symbols?query=${encodeURIComponent(query)}`);
      const all = resp.ok ? await resp.json() : [];
      return all.filter((s) => s.asset_type === "crypto" && s.provider === exchange);
    },
    onSelect: (item) => {
      el("manual-symbol").value = item.symbol;
      moSuggest.resolved = item;
      moSuggest.clear();
      manualPairHint(`✓ ${item.symbol} — ${item.exchange}`, "ok");
    },
  });
  let moSuggestTimer = null;

  function bindManualPairAutocomplete() {
    const input = el("manual-symbol");
    const exchangeSel = el("manual-exchange");
    if (!input) return;

    function unverifiedNotice() {
      const exchange = exchangeSel?.value;
      if (!MANUAL_PAIR_EXCHANGES.has(exchange)) {
        manualPairHint(`On ${exchange} the pair can't be verified from here: `
          + "type it exactly as the exchange writes it.", "warn");
        return true;
      }
      return false;
    }

    input.addEventListener("input", () => {
      moSuggest.resolved = null;   // scrivere annulla la conferma precedente
      manualPairHint("");
      const value = input.value.trim();
      clearTimeout(moSuggestTimer);
      if (!value) { moSuggest.clear(); unverifiedNotice(); return; }
      if (unverifiedNotice()) { moSuggest.clear(); return; }
      moSuggestTimer = setTimeout(() => moSuggest.fetch(value), 300);
    });
    input.addEventListener("keydown", (e) => moSuggest.handleKey(e));
    input.addEventListener("blur", () => setTimeout(() => moSuggest.clear(), 150));
    exchangeSel?.addEventListener("change", () => {
      // Cambiare exchange invalida la conferma: lo stesso nome puo' non
      // esistere altrove, o esistere scritto in un altro modo.
      moSuggest.resolved = null;
      moSuggest.clear();
      manualPairHint("");
      unverifiedNotice();
    });
  }

  // "% saldo" senza mostrare il saldo ordina alla cieca: l'utente non sa a
  // quanti USDT corrisponde finche' l'ordine non e' gia' partito. Riusiamo
  // /api/balances (la stessa fonte della tab Saldi), che oggi copre solo
  // MEXC e KuCoin: per gli altri quattro exchange lo diciamo esplicitamente
  // invece di lasciar credere che il silenzio sia un numero pari a zero.
  const MANUAL_BALANCE_EXCHANGES = new Set(["mexc", "kucoin"]);

  function ensureManualBalanceHint() {
    let hint = el("manual-balance-hint");
    if (hint) return hint;
    const row = document.querySelector(".mo-size-mode-row");
    if (!row) return null;
    hint = document.createElement("p");
    hint.id = "manual-balance-hint";
    hint.style.cssText = "font-size:12px;margin:6px 0 0;color:var(--ink-dim);";
    row.insertAdjacentElement("afterend", hint);
    return hint;
  }

  async function updateManualBalanceHint() {
    const hint = ensureManualBalanceHint();
    if (!hint) return;
    const mode = document.querySelector('input[name="mo-size-mode"]:checked')?.value;
    if (mode !== "pct_balance") { hint.classList.add("hidden"); return; }
    hint.classList.remove("hidden");
    const exchange = el("manual-exchange")?.value;
    if (!MANUAL_BALANCE_EXCHANGES.has(exchange)) {
      hint.style.color = "var(--warn)";
      hint.textContent = "Balance not available here for this exchange.";
      return;
    }
    hint.style.color = "var(--ink-dim)";
    hint.textContent = "Free balance: loading…";
    try {
      const resp = await fetch("/api/balances");
      if (!resp.ok) throw new Error("bad status");
      const body = await resp.json();
      const acct = body[exchange];
      const usdt = acct?.balances?.find((b) => b.asset === "USDT");
      if (usdt) {
        hint.textContent = `Free balance: ${usdt.total.toLocaleString("en-US", { maximumFractionDigits: 2 })} USDT`;
      } else {
        hint.style.color = "var(--warn)";
        hint.textContent = "No USDT balance on this exchange.";
      }
    } catch (_) {
      hint.style.color = "var(--warn)";
      hint.textContent = "Balance not available (network error).";
    }
  }

  function bindManualOrderUI() {
    let activeSide = "BUY";
    bindManualPairAutocomplete();

    // La conferma nomina esattamente cosa sta per partire, come per i futures:
    // exchange, pair, lato, taglia. Qualunque campo cambi dopo, la spunta si
    // resetta — non si conferma un ordine diverso da quello che si e' letto.
    function invalidateManualConfirm() {
      const box = el("manual-confirm-box");
      if (box) box.checked = false;
      updateManualExecuteState();
    }

    function updateManualConfirmSummary() {
      const summary = el("manual-confirm-summary");
      if (!summary) return;
      const exchange = el("manual-exchange")?.value || "—";
      const symbol = el("manual-symbol")?.value.trim().toUpperCase() || "—";
      const sizeVal = el("manual-size-val")?.value || "—";
      const unit = el("manual-size-unit")?.textContent || "";
      summary.textContent = `${activeSide} ${symbol} on ${exchange}, ${sizeVal}${unit}`;
    }

    function updateManualExecuteState() {
      const btn = el("manual-execute-btn");
      if (!btn) return;
      const symbol = el("manual-symbol")?.value.trim();
      const confirmed = !!el("manual-confirm-box")?.checked;
      btn.disabled = !symbol || !confirmed;
    }

    function syncSideUI() {
      document.querySelectorAll(".mo-side-tab").forEach(btn => {
        btn.classList.toggle("mo-tab-active", btn.dataset.side === activeSide);
      });
      const execBtn = el("manual-execute-btn");
      if (!execBtn) return;
      execBtn.textContent = activeSide;
      execBtn.classList.toggle("mo-execute-buy", activeSide === "BUY");
      execBtn.classList.toggle("mo-execute-sell", activeSide === "SELL");
    }

    function syncSliderUnit() {
      const mode = document.querySelector('input[name="mo-size-mode"]:checked')?.value;
      const unit = el("manual-size-unit");
      const slider = el("manual-size-slider");
      const valInput = el("manual-size-val");
      if (!unit || !slider) return;
      if (mode === "pct_balance") {
        unit.textContent = "%";
        slider.max = 100;
        slider.min = 1;
        valInput.max = 100;
      } else {
        unit.textContent = "USDT";
        slider.max = 10000;
        slider.min = 1;
        valInput.max = 10000;
      }
    }

    document.querySelectorAll(".mo-side-tab").forEach(btn => {
      btn.addEventListener("click", () => {
        activeSide = btn.dataset.side; syncSideUI();
        updateManualConfirmSummary(); invalidateManualConfirm();
      });
    });

    document.querySelectorAll('input[name="mo-size-mode"]').forEach(r => {
      r.addEventListener("change", () => {
        syncSliderUnit();
        updateManualConfirmSummary(); invalidateManualConfirm();
        updateManualBalanceHint();
      });
    });

    const slider = el("manual-size-slider");
    const valInput = el("manual-size-val");
    slider?.addEventListener("input", () => {
      if (valInput) valInput.value = slider.value;
      updateManualConfirmSummary(); invalidateManualConfirm();
    });
    valInput?.addEventListener("input", () => {
      if (slider) slider.value = valInput.value;
      updateManualConfirmSummary(); invalidateManualConfirm();
    });
    el("manual-exchange")?.addEventListener("change", () => {
      updateManualConfirmSummary(); invalidateManualConfirm();
      updateManualBalanceHint();
    });
    updateManualBalanceHint();
    el("manual-symbol")?.addEventListener("input", () => {
      updateManualConfirmSummary(); updateManualExecuteState(); invalidateManualConfirm();
    });
    el("manual-confirm-box")?.addEventListener("change", updateManualExecuteState);

    async function submitManualOrder() {
      const exchange = el("manual-exchange")?.value;
      const symbol = el("manual-symbol")?.value.trim().toUpperCase();
      const sizeMode = document.querySelector('input[name="mo-size-mode"]:checked')?.value || "pct_balance";
      const sizeValue = parseFloat(el("manual-size-val")?.value);
      const statusEl = el("manual-order-status");
      if (!symbol) { statusEl.textContent = "Enter the pair (e.g. BTCUSDT)"; statusEl.classList.remove("hidden"); return; }
      if (!el("manual-confirm-box")?.checked) {
        statusEl.textContent = "Confirm the order before sending it";
        statusEl.classList.remove("hidden");
        return;
      }
      statusEl.textContent = "Sending order…";
      statusEl.classList.remove("hidden", "ok", "error");
      try {
        const resp = await fetch("/api/trading/order", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ exchange, symbol, side: activeSide, size_mode: sizeMode, size_value: sizeValue }),
        });
        const data = await resp.json().catch(() => ({}));
        if (resp.ok) {
          statusEl.textContent = `✓ ${activeSide} order ${data.symbol || symbol} sent`;
          statusEl.classList.add("ok");
        } else {
          statusEl.textContent = `✗ ${data.detail || "Error " + resp.status}`;
          statusEl.classList.add("error");
        }
        // Riuscito o fallito, il tentativo e' ora nel diario: il riquadro di
        // stato sparisce ricaricando la pagina, il diario no.
        loadTradingJournal();
        invalidateManualConfirm();
      } catch (_) {
        statusEl.textContent = "✗ Network error";
        statusEl.classList.add("error");
      }
    }

    // Chiusura spot: non passa dalla casella di conferma del form qui sopra
    // (che descrive l'ordine BUY/SELL con la sua dimensione, un'altra cosa) —
    // ha la sua conferma, che nomina il pair e dice che vende tutto.
    async function submitSpotClose() {
      const exchange = el("manual-exchange")?.value;
      const symbol = el("manual-symbol")?.value.trim().toUpperCase();
      const statusEl = el("spot-close-status");
      if (!symbol) {
        statusEl.textContent = "Enter the pair to close (e.g. BTCUSDT)";
        statusEl.className = "manual-order-status error";
        return;
      }
      if (!confirm(`Sell your ENTIRE ${symbol} balance on ${exchange}?\n\nMarket order, real money.`)) return;
      const btn = el("spot-close-btn");
      btn.disabled = true;
      statusEl.textContent = "Closing…";
      statusEl.className = "manual-order-status";
      try {
        const resp = await fetch("/api/trading/spot/close", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ exchange, symbol, confirm: true }),
        });
        const data = await readJson(resp);
        if (resp.ok) {
          statusEl.textContent = `✓ Sold the entire ${data.symbol || symbol} balance`;
          statusEl.className = "manual-order-status ok";
        } else {
          statusEl.textContent = `✗ ${data.detail || "Error " + resp.status}`;
          statusEl.className = "manual-order-status error";
        }
        loadTradingJournal();
      } catch (err) {
        statusEl.textContent = "✗ " + (err.message || "Network error");
        statusEl.className = "manual-order-status error";
      } finally {
        btn.disabled = false;
      }
    }

    el("manual-execute-btn")?.addEventListener("click", submitManualOrder);
    el("spot-close-btn")?.addEventListener("click", submitSpotClose);
    syncSliderUnit();
    updateManualConfirmSummary();
    updateManualExecuteState();
  }
  bindManualOrderUI();

  // ── Ordine futures ────────────────────────────────────────────────────
  // Tenuto separato dallo spot come il backend: nessuna funzione dello spot
  // viene riusata qui, cosi' un errore su questo lato non puo' arrivare a un
  // ordine spot. Il tetto di leva e' comunque riapplicato dal server.
  //
  // Gli exchange non sono piu' un elenco scritto qui: arrivano da
  // /api/auth/futures, la stessa chiamata che porta le credenziali, perche'
  // il perimetro (leva accessibile dall'Europa — vedi registry.py sul
  // backend) e' deciso in un posto solo.
  let futuresExchanges = []; // [{exchange, name, needs_passphrase, max_leverage, isolated_margin, ...}]
  let futuresSide = "BUY";
  let futuresQuote = null;
  let futuresQuoteTimer = null;

  // Stesso principio del pair manuale spot (vedi MANUAL_PAIR_EXCHANGES piu'
  // sopra): niente autocomplete non e' una conferma, e' silenzio. Qui il
  // campo restava muto per ogni exchange futures — bug segnalato da l'utente
  // su MEXC ("non trova nessun pair" scrivendo BTCUSDT). /api/symbols copre
  // mexc, binance, kucoin e kraken fra i provider crypto; fra i futures mexc,
  // binance e kraken sono anche exchange futures registrati (kucoin no),
  // quindi sono i tre per cui possiamo verificare il pair da qui.
  const FUTURES_PAIR_EXCHANGES = new Set(["mexc", "binance", "kraken"]);

  const futuresSuggest = makeSuggestController({
    listId: "futures-symbol-suggestions",
    anchorId: "futures-symbol",
    fetchItems: async (query) => {
      const exchange = el("futures-exchange")?.value;
      if (!FUTURES_PAIR_EXCHANGES.has(exchange)) return [];
      const resp = await fetch(`/api/symbols?query=${encodeURIComponent(query)}`);
      const all = resp.ok ? await resp.json() : [];
      return all.filter((s) => s.asset_type === "crypto" && s.provider === exchange);
    },
    onSelect: (item) => {
      el("futures-symbol").value = item.symbol;
      futuresSuggest.resolved = item;
      futuresSuggest.clear();
      queueFuturesQuote();
    },
  });
  let futuresSuggestTimer = null;

  function currentFuturesExchangeInfo() {
    const slug = el("futures-exchange")?.value;
    return futuresExchanges.find((x) => x.exchange === slug) || null;
  }

  function futuresSizeMode() {
    const checked = document.querySelector('input[name="futures-size-mode"]:checked');
    return checked ? checked.value : "fixed_usdt";
  }

  // "Quantità" (base_qty) ha un campo suo, separato dallo slider USDT/%:
  // stesso numero scritto in caselle diverse a seconda del modo, mai lo
  // stesso campo reinterpretato — e' la fonte piu' comune di ordini
  // sbagliati di un fattore mille (500 lette come USDT invece che come
  // quantita' di un token, o viceversa).
  function futuresSizeValue() {
    if (futuresSizeMode() === "base_qty") return Number(el("futures-qty-val").value) || 0;
    return Number(el("futures-size-val").value) || 0;
  }

  // Estrae l'asset base dal pair per etichettare il campo "Quantità" con la
  // sua vera unita' (es. BTCUSDT -> BTC) invece di un generico "token" —
  // la stessa euristica usata lato server per lo spot (_base_asset).
  function baseAssetFromSymbol(symbol) {
    const s = (symbol || "").trim().toUpperCase();
    for (const quote of ["USDT", "USDC", "BTC", "ETH"]) {
      if (s.length > quote.length && s.endsWith(quote)) return s.slice(0, -quote.length);
    }
    return s || "token";
  }

  // Mostra il campo giusto per il modo scelto: slider+USDT/% per gli altri
  // due, solo il numero libero per Quantità — nessuno slider ha una scala
  // sensata per una quantita' di token, che va da 0.0001 a milioni a
  // seconda della moneta.
  function updateFuturesSizeUI() {
    const isQty = futuresSizeMode() === "base_qty";
    el("futures-size-slider-row").classList.toggle("hidden", isQty);
    el("futures-qty-row").classList.toggle("hidden", !isQty);
    el("futures-qty-hint").classList.toggle("hidden", !isQty);
    if (isQty) el("futures-qty-unit").textContent = baseAssetFromSymbol(el("futures-symbol").value);
  }

  // Il tetto di leva e se il margine e' davvero isolato dipendono
  // dall'exchange scelto (Kraken non ha isolated — vedi registry.py):
  // aggiorna lo slider e l'avviso quando cambia la tendina.
  function applyFuturesExchangeLimits() {
    const info = currentFuturesExchangeInfo();
    const maxLev = info ? info.max_leverage : 10;
    const slider = el("futures-leverage");
    slider.max = maxLev;
    if (Number(slider.value) > maxLev) slider.value = maxLev;
    const scale = el("futures-lev-scale");
    if (scale) {
      const steps = [1, Math.round(maxLev * 0.3) || 1, Math.round(maxLev * 0.5), Math.round(maxLev * 0.7), maxLev];
      scale.innerHTML = [...new Set(steps)].map((s) => `<span>${s}×</span>`).join("");
    }
    const modeNode = el("futures-margin-mode");
    if (modeNode) {
      modeNode.innerHTML = info && !info.isolated_margin
        ? '<b>shared</b> margin — this exchange has no isolated mode: a losing position eats into the others'
        : '<b>isolated</b> margin — enforced';
      modeNode.classList.toggle("lev-mode-warn", !!(info && !info.isolated_margin));
    }
    const passField = el("futures-passphrase-field");
    if (passField) passField.classList.toggle("hidden", !(info && info.needs_passphrase));
  }

  function renderFuturesQuote() {
    const info = currentFuturesExchangeInfo();
    const maxLev = info ? info.max_leverage : 10;
    const lev = Number(el("futures-leverage").value);
    el("futures-lev-val").textContent = lev + "×";
    el("futures-confirm-lev").textContent = lev + "×";
    const cap = el("futures-lev-cap");
    cap.textContent = lev >= maxLev ? "server cap reached" : `server cap ${maxLev}×`;
    cap.classList.toggle("lev-cap-hot", lev >= maxLev * 0.7);

    const q = futuresQuote;
    const setv = (id, txt, cls) => {
      const node = el(id);
      node.textContent = txt;
      node.className = cls || "";
    };
    const note = el("fq-rounding-note");
    if (!q) {
      setv("fq-notional", "—"); setv("fq-margin", "—");
      setv("fq-liq", "—"); setv("fq-dist", "—");
      el("futures-confirm-liq").textContent = "—";
      if (note) note.classList.add("hidden");
      return;
    }
    // L'exchange puo' arrotondare la dimensione (MEXC conta contratti
    // interi): quando succede, l'anteprima lo dice invece di mostrare
    // l'importo chiesto e lasciar scoprire dopo quello eseguito.
    if (note) {
      note.textContent = q.rounding_note || "";
      note.classList.toggle("hidden", !q.rounding_note);
    }
    const dist = (q.liquidation_price / q.mark_price - 1) * 100;
    setv("fq-notional", fmtNum(q.notional, 2) + " USDT");
    setv("fq-margin", fmtNum(q.margin_used, 2) + " USDT" + (q.margin_sufficient ? "" : " — insufficient"),
         q.margin_sufficient ? "" : "fq-bad");
    setv("fq-liq", fmtNum(q.liquidation_price, 2), "fq-bad");
    setv("fq-dist", (dist >= 0 ? "+" : "") + dist.toFixed(1) + "%",
         Math.abs(dist) < 8 ? "fq-bad" : Math.abs(dist) < 15 ? "fq-warn" : "fq-ok");
    el("futures-confirm-liq").textContent = fmtNum(q.liquidation_price, 2);
  }

  function fmtNum(v, d) {
    if (v === null || v === undefined || Number.isNaN(v)) return "—";
    return Number(v).toLocaleString("en-US", { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 });
  }

  // L'anteprima e' obbligatoria: senza una quote fresca il bottone resta
  // spento, cosi' non si puo' confermare una liquidazione che non si e' vista.
  async function refreshFuturesQuote() {
    const symbol = el("futures-symbol").value.trim().toUpperCase();
    if (!symbol || !state.user) { futuresQuote = null; renderFuturesQuote(); updateFuturesExecuteState(); return; }
    try {
      const res = await fetch("/api/trading/futures/quote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          exchange: el("futures-exchange").value,
          symbol,
          side: futuresSide,
          size_mode: futuresSizeMode(),
          size_value: futuresSizeValue(),
          leverage: Number(el("futures-leverage").value),
        }),
      });
      // La quote non manda mai la passphrase: usa quella gia' salvata sul
      // server, come chiave e secret — vedi submitFuturesOrder per lo stesso
      // principio sull'ordine vero.
      futuresQuote = res.ok ? await res.json() : null;
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setFuturesStatus(err.detail || "Preview not available", true);
      } else {
        el("futures-order-status").classList.add("hidden");
      }
    } catch {
      futuresQuote = null;
    }
    renderFuturesQuote();
    updateFuturesExecuteState();
  }

  function queueFuturesQuote() {
    // Ogni modifica invalida la conferma: non si conferma un numero vecchio.
    el("futures-confirm-box").checked = false;
    futuresQuote = null;
    renderFuturesQuote();
    updateFuturesExecuteState();
    clearTimeout(futuresQuoteTimer);
    futuresQuoteTimer = setTimeout(refreshFuturesQuote, 350);
  }

  function updateFuturesExecuteState() {
    const btn = el("futures-execute-btn");
    if (!btn) return;
    const ok = !!futuresQuote && futuresQuote.margin_sufficient && el("futures-confirm-box").checked;
    btn.disabled = !ok;
    btn.textContent = (futuresSide === "BUY" ? "OPEN LONG" : "OPEN SHORT")
      + (futuresQuote ? " " + Number(el("futures-leverage").value) + "×" : "");
    btn.classList.toggle("mo-execute-buy", futuresSide === "BUY");
    btn.classList.toggle("mo-execute-sell", futuresSide === "SELL");
  }

  function setFuturesStatus(msg, isError) {
    const node = el("futures-order-status");
    node.textContent = msg;
    node.classList.remove("hidden");
    node.classList.toggle("error", !!isError);
  }

  // Quando il rifiuto e' solo "l'esecuzione e' spenta per questo exchange"
  // (kill switch, cred.enabled=false — vedi place_manual_futures_order),
  // il problema si risolve con un tocco: un bottone qui, non solo il
  // messaggio, invece di far tornare la persona su alla card giusta a
  // cercare il toggle "Attivo" (segnalazione 6237708e).
  function offerFuturesActivation(exchange) {
    const node = el("futures-order-status");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "futures-activate-btn";
    btn.textContent = "Enable now";
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      btn.textContent = "Enabling…";
      try {
        const cred = getFuturesCredCache(exchange);
        await fetch("/api/auth/futures", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            exchange,
            api_key: "", api_secret: "", passphrase: "",
            enabled: true,
            size_mode: cred?.size_mode || "fixed_usdt",
            size_value: cred?.size_value || 50,
            leverage: cred?.leverage || 1,
          }),
        });
        await loadFuturesCredentials();
        setFuturesStatus(`Execution enabled for ${exchange.toUpperCase()} — press again to send the order.`, false);
      } catch (_e) {
        btn.disabled = false;
        btn.textContent = "Enable now";
      }
    });
    node.appendChild(document.createTextNode(" "));
    node.appendChild(btn);
  }

  // Il PATCH di attivazione deve rimandare size/leva gia' impostati per
  // quell'exchange, non i default: altrimenti "Enable now" azzererebbe in
  // silenzio una taglia o una leva gia' scelte in precedenza. futuresExchanges
  // (la cache caricata da loadFuturesCredentials) e' l'unica fonte gia' in
  // memoria — nessuna richiesta in piu' solo per leggerla.
  function getFuturesCredCache(exchange) {
    return (futuresExchanges || []).find((c) => c.exchange === exchange);
  }

  async function submitFuturesOrder() {
    const btn = el("futures-execute-btn");
    btn.disabled = true;
    setFuturesStatus("Sending order…", false);
    try {
      const res = await fetch("/api/trading/futures/order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          exchange: el("futures-exchange").value,
          symbol: el("futures-symbol").value.trim().toUpperCase(),
          side: futuresSide,
          size_mode: futuresSizeMode(),
          size_value: futuresSizeValue(),
          leverage: Number(el("futures-leverage").value),
          confirm: true,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || "Order rejected";
        setFuturesStatus(detail, true);
        if (typeof detail === "string" && detail.includes("disabled")) {
          offerFuturesActivation(el("futures-exchange").value);
        }
      } else {
        setFuturesStatus("Order executed.", false);
        loadExecutedOrders();
        loadPositions();
        el("futures-confirm-box").checked = false;
        futuresQuote = null;
        renderFuturesQuote();
        // La funzione si chiama loadTradingJournal: `loadJournal?.()` non era
        // una chiamata facoltativa ma un nome inesistente, e `?.` non protegge
        // da una variabile mai dichiarata — lanciava un ReferenceError PROPRIO
        // QUI, dentro il ramo del successo, e il catch qui sotto lo riscriveva
        // come "Network error": l'ordine era passato davvero e l'interfaccia
        // diceva il contrario, sullo stesso schermo da cui si rischia di
        // rifarlo una seconda volta.
        loadTradingJournal();
      }
    } catch (e) {
      setFuturesStatus("Network error: " + e.message, true);
    }
    updateFuturesExecuteState();
  }

  // Le opzioni del select e le card delle credenziali vengono dalla stessa
  // risposta: un solo giro di rete, e l'elenco degli exchange non puo' mai
  // disallinearsi fra le due parti dello schermo.
  async function loadFuturesCredentials() {
    try {
      const resp = await fetch("/api/auth/futures");
      if (resp.status === 401) return;
      if (!resp.ok) return;
      futuresExchanges = await resp.json();
      renderFuturesExchangeOptions();
      renderFuturesCredentials();
      applyFuturesExchangeLimits();
    } catch (_) {
      // rete assente — i controlli restano con i valori di default
    }
  }

  function renderFuturesExchangeOptions() {
    const select = el("futures-exchange");
    if (!select) return;
    const prev = select.value;
    select.innerHTML = futuresExchanges.map((x) =>
      `<option value="${x.exchange}">${x.name}</option>`).join("");
    if (futuresExchanges.some((x) => x.exchange === prev)) select.value = prev;
  }

  function renderFuturesCredentials() {
    const container = el("futures-credentials-list");
    if (!container) return;
    container.innerHTML = futuresExchanges.map((c) => {
      const summaryText = c.api_key_set ? "Edit key" : "Set up API key";
      const savedNote = c.api_key_set
        ? `<div class="trading-cred-saved">🔒 Key saved and encrypted${c.created_at ? " — added on " + escapeHtml(new Date(c.created_at * 1000).toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" })) : ""}
             <button type="button" class="trading-cred-delete-btn" title="Delete this key">Delete</button></div>`
        : "";
      const riskNote = c.isolated_margin ? "" :
        `<p class="panel-hint futures-risk-note">${c.name} has no isolated margin: a losing position can eat into the others on the account.</p>`;
      const passphraseField = c.needs_passphrase
        ? `<label>Passphrase ${c.passphrase_set ? "" : "<span class=\"trading-cred-missing\">required</span>"} <input type="password" class="futures-cred-passphrase" placeholder="leave empty to keep unchanged" /></label>`
        : "";
      return `<div class="trading-cred-card" data-exchange="${c.exchange}">
        <div class="trading-cred-exchange-row">
          <span class="trading-cred-name">${c.name}</span>
          <label class="trading-enabled-toggle">
            <input type="checkbox" class="futures-cred-enabled-cb" ${c.enabled ? "checked" : ""}> Enabled
          </label>
        </div>
        ${savedNote}
        ${riskNote}
        <details class="trading-cred-details">
          <summary>${summaryText}</summary>
          <div class="trading-cred-fields">
            <p class="panel-hint">${c.key_hint || ""}</p>
            <label>API Key <input type="text" class="futures-cred-api-key" placeholder="leave empty to keep unchanged" autocomplete="off" /></label>
            <label>API Secret <input type="password" class="futures-cred-api-secret" placeholder="leave empty to keep unchanged" autocomplete="off" /></label>
            ${passphraseField}
            <div class="trading-size-row">
              <label>Size type
                <select class="futures-cred-size-mode">
                  <option value="fixed_usdt" ${c.size_mode === "fixed_usdt" ? "selected" : ""}>Fixed USDT</option>
                  <option value="pct_balance" ${c.size_mode === "pct_balance" ? "selected" : ""}>% of balance</option>
                </select>
              </label>
              <label>Value <input type="number" class="futures-cred-size-val" value="${c.size_value}" min="1" step="1" /></label>
              <label>Default leverage <input type="number" class="futures-cred-leverage" value="${c.leverage}" min="1" max="${c.max_leverage}" step="1" /></label>
            </div>
            <button type="button" class="trading-save-btn">Save</button>
            <span class="trading-save-status"></span>
          </div>
        </details>
      </div>`;
    }).join("");

    // Delega sul contenitore, che e' un nodo persistente: renderFuturesCredentials()
    // riscrive solo il suo innerHTML a ogni chiamata, non lo ricrea. Un
    // { once: true } qui presumeva il contrario: bastava che il primo
    // salvataggio fallisse (leva oltre il tetto server, per esempio) perche'
    // quel listener si autodistruggesse senza che uno nuovo lo sostituisse
    // (il rebind avveniva solo dentro il ramo "successo"), e ogni click
    // successivo su Salva restava silenzioso — nessuna richiesta, nessun
    // errore. Il flag sotto lega gli handler una volta sola per davvero,
    // indipendentemente da quante volte il markup interno viene rigenerato.
    if (container.dataset.futuresHandlersBound) return;
    container.dataset.futuresHandlersBound = "1";

    container.addEventListener("click", async function handleFuturesCredSave(e) {
      if (!e.target.classList.contains("trading-save-btn")) return;
      const card = e.target.closest(".trading-cred-card");
      if (!card) return;
      const exchange = card.dataset.exchange;
      const statusEl = card.querySelector(".trading-save-status");
      const body = {
        exchange,
        api_key: card.querySelector(".futures-cred-api-key")?.value || "",
        api_secret: card.querySelector(".futures-cred-api-secret")?.value || "",
        passphrase: card.querySelector(".futures-cred-passphrase")?.value || "",
        enabled: card.querySelector(".futures-cred-enabled-cb")?.checked || false,
        size_mode: card.querySelector(".futures-cred-size-mode")?.value || "fixed_usdt",
        size_value: readNumericField(card.querySelector(".futures-cred-size-val"), 50, { min: 1 }),
        leverage: readNumericField(card.querySelector(".futures-cred-leverage"), 1, { min: 1, max: parseInt(card.querySelector(".futures-cred-leverage")?.max, 10) || 1, integer: true }),
      };
      try {
        const resp = await fetch("/api/auth/futures", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (resp.ok) {
          statusEl.textContent = "Saved ✓";
          loadFuturesCredentials();
          setTimeout(() => { statusEl.textContent = ""; }, 3000);
        } else {
          const err = await resp.json().catch(() => ({}));
          statusEl.textContent = err.detail || `Error (${resp.status})`;
        }
      } catch (_) {
        statusEl.textContent = "Network error";
      }
    });

    container.addEventListener("click", async function handleFuturesCredDelete(e) {
      if (!e.target.classList.contains("trading-cred-delete-btn")) return;
      const card = e.target.closest(".trading-cred-card");
      if (!card) return;
      await fetch(`/api/auth/futures/${card.dataset.exchange}`, { method: "DELETE" });
      loadFuturesCredentials();
    });

    container.addEventListener("change", async function handleFuturesCredToggle(e) {
      if (!e.target.classList.contains("futures-cred-enabled-cb")) return;
      const card = e.target.closest(".trading-cred-card");
      if (!card) return;
      const exchange = card.dataset.exchange;
      try {
        await fetch("/api/auth/futures", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            exchange, api_key: "", api_secret: "", passphrase: "",
            enabled: e.target.checked,
            size_mode: card.querySelector(".futures-cred-size-mode")?.value || "fixed_usdt",
            size_value: readNumericField(card.querySelector(".futures-cred-size-val"), 50, { min: 1 }),
            leverage: readNumericField(card.querySelector(".futures-cred-leverage"), 1, { min: 1, max: parseInt(card.querySelector(".futures-cred-leverage")?.max, 10) || 1, integer: true }),
          }),
        });
      } catch (_) {
        // silenzioso: il toggle torna visivamente com'era al prossimo load
      }
    });
  }

  function bindFuturesOrderUI() {
    if (!el("futures-execute-btn")) return;

    el("futures-exchange")?.addEventListener("change", () => {
      applyFuturesExchangeLimits();
      // Cambiare exchange invalida la conferma dell'autocomplete: lo stesso
      // pair puo' non esistere altrove, o esistere scritto in un altro modo.
      futuresSuggest.resolved = null;
      futuresSuggest.clear();
      queueFuturesQuote();
    });

    document.querySelectorAll("[data-futures-side]").forEach((tab) => {
      tab.addEventListener("click", () => {
        futuresSide = tab.dataset.futuresSide;
        document.querySelectorAll("[data-futures-side]").forEach((t) => t.classList.toggle("mo-tab-active", t === tab));
        queueFuturesQuote();
      });
    });

    el("futures-leverage").addEventListener("input", () => { renderFuturesQuote(); queueFuturesQuote(); });

    const slider = el("futures-size-slider");
    const valInput = el("futures-size-val");
    slider.addEventListener("input", () => {
      valInput.value = futuresSizeMode() === "pct_balance" ? slider.value : slider.value * 10;
      queueFuturesQuote();
    });
    valInput.addEventListener("input", queueFuturesQuote);
    el("futures-symbol").addEventListener("input", () => {
      futuresSuggest.resolved = null; // scrivere annulla la scelta precedente
      if (futuresSizeMode() === "base_qty") el("futures-qty-unit").textContent = baseAssetFromSymbol(el("futures-symbol").value);
      queueFuturesQuote();
      const value = el("futures-symbol").value.trim();
      clearTimeout(futuresSuggestTimer);
      if (!value) { futuresSuggest.clear(); return; }
      futuresSuggestTimer = setTimeout(() => futuresSuggest.fetch(value), 300);
    });
    el("futures-symbol").addEventListener("keydown", (e) => futuresSuggest.handleKey(e));
    el("futures-symbol").addEventListener("blur", () => setTimeout(() => futuresSuggest.clear(), 150));
    el("futures-qty-val").addEventListener("input", queueFuturesQuote);
    document.querySelectorAll('input[name="futures-size-mode"]').forEach((r) => {
      r.addEventListener("change", () => {
        el("futures-size-unit").textContent = futuresSizeMode() === "pct_balance" ? "%" : "USDT";
        updateFuturesSizeUI();
        queueFuturesQuote();
      });
    });
    el("futures-confirm-box").addEventListener("change", updateFuturesExecuteState);
    el("futures-execute-btn").addEventListener("click", submitFuturesOrder);
    el("positions-refresh-btn")?.addEventListener("click", loadPositions);
    el("opera-login-btn")?.addEventListener("click", () => openAuthModal("login"));

    updateFuturesSizeUI();
    renderFuturesQuote();
    updateFuturesExecuteState();
  }


  // ── Posizioni aperte ──────────────────────────────────────────────────
  // La distanza dalla liquidazione e' disegnata come nastro con lancetta
  // invece che scritta in una riga: una lancetta nel rosso si vede prima di
  // un errore, un numero in tabella lo racconta dopo. Non e' piu' sola
  // lettura: da qui si chiude, perche' vedere una posizione a lega andare
  // storta senza poterci fare niente e' il modo peggiore di guardarla.
  async function loadPositions() {
    const list = el("positions-list");
    if (!list || !state.user) return;
    try {
      const res = await fetch("/api/trading/futures/positions");
      if (!res.ok) { list.innerHTML = ""; el("positions-count").textContent = ""; return; }
      renderPositions(await res.json());
    } catch {
      /* una posizione non mostrata e' meno grave di una pagina rotta */
    }
  }

  // Gauge SVG a lancetta per la distanza da liquidazione: semicerchio con
  // tre settori (danger/warn/bull, stessa soglia del vecchio nastro) e una
  // lancetta che ruota da -90deg (liquidazione) a +90deg (zona sicura).
  function renderLiqGauge(safety, distClass) {
    const angle = -90 + safety * 180;
    const rad = (angle - 90) * Math.PI / 180;
    const cx = 60, cy = 54, r = 22;
    const nx = (cx + r * Math.cos(rad)).toFixed(1);
    const ny = (cy + r * Math.sin(rad)).toFixed(1);
    return `<div class="liq-gauge">
      <svg viewBox="0 0 120 62" class="liq-gauge-svg">
        <path d="M 8 54 A 52 52 0 0 1 33.6 11.8" class="liq-arc liq-arc-danger" />
        <path d="M 33.6 11.8 A 52 52 0 0 1 86.4 11.8" class="liq-arc liq-arc-warn" />
        <path d="M 86.4 11.8 A 52 52 0 0 1 112 54" class="liq-arc liq-arc-bull" />
        <line x1="${cx}" y1="${cy}" x2="${nx}" y2="${ny}" class="liq-gauge-needle" />
        <circle cx="${cx}" cy="${cy}" r="4" class="liq-gauge-hub" />
      </svg>
      <div class="liq-gauge-label ${distClass}">${distClass === "bear" ? "close" : distClass === "warnc" ? "caution" : "safe"}</div>
    </div>`;
  }

  function renderPositions(positions) {
    const list = el("positions-list");
    const count = el("positions-count");
    count.textContent = positions.length ? `${positions.length} open` : "";
    if (!positions.length) {
      list.innerHTML = '<li class="pos-empty">No open leveraged positions.</li>';
      return;
    }
    list.innerHTML = positions.map((p) => {
      const pnl = p.unrealized_pnl || 0;
      const dist = p.distance_to_liquidation_pct;
      // La lancetta: 0% = liquidazione, 25% o piu' di margine = zona verde.
      const safety = dist === null || dist === undefined ? 0.5
        : Math.max(0, Math.min(1, Math.abs(dist) / 25));
      const distClass = dist === null || dist === undefined ? ""
        : Math.abs(dist) < 8 ? "bear" : Math.abs(dist) < 15 ? "warnc" : "bull";
      return `<li class="pos-item leveraged">
        <div class="pos-item-top">
          <span class="trading-auto-badge futures-badge">${p.leverage}× isolated</span>
          <b>${p.symbol}</b>
          <span class="section-count">${p.side === "long" ? "LONG" : "SHORT"}</span>
          <span class="section-count">${p.exchange}</span>
        </div>
        <div class="pos-pnl ${pnl >= 0 ? "bull" : "bear"}">${pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}</div>
        <div class="fq-row"><span>Entry / mark</span><span>${p.entry_price} → ${p.mark_price}</span></div>
        <div class="fq-row"><span>Quantity / margin</span><span>${p.quantity} · ${p.margin.toFixed(2)} USDT</span></div>
        ${renderLiqGauge(safety, distClass)}
        <div class="liq-foot">
          <span class="bear">liq. ${p.liquidation_price}</span>
          <span class="${distClass}">${dist === null || dist === undefined ? "—" : (dist >= 0 ? "+" : "") + dist.toFixed(1) + "%"}</span>
        </div>
        <div class="pos-actions">
          <button type="button" class="pos-close-btn" data-exchange="${escapeHtml(p.exchange)}" data-symbol="${escapeHtml(p.symbol)}">Close position</button>
        </div>
      </li>`;
    }).join("");
    bindCloseButtons(list, "futures");
  }

  // Chiusura, spot e futures: due endpoint diversi ma lo stesso gesto e la
  // stessa cautela — una conferma esplicita, il pulsante bloccato mentre
  // parte, e l'esito scritto sulla card invece che in un alert che sparisce.
  function bindCloseButtons(root, market) {
    root.querySelectorAll(".pos-close-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const exchange = btn.dataset.exchange;
        const symbol = btn.dataset.symbol;
        const what = market === "futures"
          ? `Close the ${symbol} position on ${exchange}?`
          : `Sell your ENTIRE ${symbol} balance on ${exchange}?`;
        if (!confirm(`${what}\n\nMarket order, real money.`)) return;
        // Lo stato vive fuori dalla lista: loadPositions() qui sotto la
        // ridisegna, e una conferma scritta dentro la card sparirebbe
        // insieme alla posizione appena chiusa.
        const status = el("positions-close-status");
        const say = (text, kind) => {
          if (!status) return;
          status.textContent = `${symbol}: ${text}`;
          status.className = "pos-close-status" + (kind ? " " + kind : "");
          status.classList.remove("hidden");
        };
        btn.disabled = true;
        const prev = btn.textContent;
        btn.textContent = "Closing…";
        try {
          const resp = await fetch(`/api/trading/${market}/close`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ exchange, symbol, confirm: true }),
          });
          const data = await readJson(resp);
          if (!resp.ok) {
            say("✗ " + (data.detail || `Error ${resp.status}`), "error");
            return;
          }
          // closed:false = non c'era niente da chiudere. Non e' un errore, ma
          // nemmeno un successo da festeggiare: dirlo com'e'.
          say(data.closed === false ? (data.detail || "No position to close.") : "✓ Position closed.",
              data.closed === false ? "" : "ok");
          loadPositions();
          loadTradingJournal();
        } catch (err) {
          say("✗ " + (err.message || "Network error"), "error");
        } finally {
          btn.disabled = false;
          btn.textContent = prev;
        }
      });
    });
  }

  bindFuturesOrderUI();

  function openAuthModal(mode, opts) {
    authMode = mode || "login";
    authGateActive = !!(opts && opts.gate);
    el("auth-modal-title").textContent = authMode === "login" ? "Log in" : "Sign up";
    el("auth-submit-btn").textContent = authMode === "login" ? "Log in" : "Sign up";
    el("auth-switch-text").textContent = authMode === "login" ? "Don't have an account?" : "Already have an account?";
    el("auth-switch-btn").textContent = authMode === "login" ? "Sign up" : "Log in";
    el("auth-error").classList.add("hidden");
    el("auth-gate-hint").classList.toggle("hidden", !authGateActive);
    el("auth-form").reset();
    el("auth-modal").classList.remove("hidden");
    el("auth-modal").classList.toggle("gate", authGateActive);
  }

  function closeAuthModal() {
    if (authGateActive) return; // login is mandatory before the page unlocks — can't be dismissed
    el("auth-modal").classList.add("hidden");
  }

  function bindAuth() {
    el("auth-toggle-btn").addEventListener("click", () => openAuthModal("login"));
    el("alert-login-btn").addEventListener("click", () => openAuthModal("login"));
    document.querySelectorAll("[data-close-auth]").forEach((node) => node.addEventListener("click", closeAuthModal));
    el("auth-switch-btn").addEventListener("click", () =>
      openAuthModal(authMode === "login" ? "register" : "login", { gate: authGateActive })
    );

    el("auth-logout-btn").addEventListener("click", async () => {
      await fetch("/api/auth/logout", { method: "POST" });
      state.user = null;
      updateAuthUI();
      openAuthModal("login", { gate: true }); // re-lock the page immediately, same as first load
    });

    el("telegram-chat-id-save").addEventListener("click", async () => {
      const chatId = el("telegram-chat-id-input").value.trim();
      const signalChatId = el("telegram-signal-chat-id-input").value.trim();
      const gemsChatId = el("telegram-gems-chat-id-input").value.trim();
      const resp = await fetch("/api/auth/telegram", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telegram_chat_id: chatId, telegram_signal_chat_id: signalChatId,
                               telegram_gems_chat_id: gemsChatId }),
      });
      if (resp.ok) {
        const body = await resp.json();
        state.user = body;
        renderTelegramCheck(body.telegram_check);
      }
      updateTelegramSetupUI();
    });

    // One line per chat after Save (Lorenzo, 16/10: "la conferma mi e' arrivata
    // sull'altra chat"): which field it is, what it receives, delivered or not.
    function renderTelegramCheck(rows) {
      const box = el("telegram-check");
      if (!box) return;
      if (!Array.isArray(rows) || !rows.length) { box.classList.add("hidden"); box.innerHTML = ""; return; }
      const FIELD = { main: "Main chat", alerts: "Alerts chat", gems: "Gems chat" };
      box.innerHTML = rows.map((r) => {
        const who = (r.fields || []).map((f) => `<b>${escapeHtml(FIELD[f] || f)}</b>`).join(" = ");
        const state = !r.chat ? "Nowhere: the main chat is the alerts chat. Fill in the gems chat ID."
          : r.delivered ? "Test message delivered." : "Not delivered: wrong ID, or the bot is not in that chat.";
        return `<li class="${r.chat && r.delivered ? "ok" : "bad"}">${who}${r.chat ? ` <code>${escapeHtml(r.chat)}</code>` : ""}`
          + ` · <span>${escapeHtml(r.roles.join("; "))}</span> · <span>${state}</span></li>`;
      }).join("");
      box.classList.remove("hidden");
    }

    el("telegram-edit-btn").addEventListener("click", () => updateTelegramSetupUI(true));

    el("auth-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = el("auth-email").value.trim();
      const password = el("auth-password").value;
      const endpoint = authMode === "login" ? "/api/auth/login" : "/api/auth/register";
      const errorEl = el("auth-error");
      errorEl.classList.add("hidden");
      try {
        const resp = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        const body = await readJson(resp);
        if (!resp.ok) {
          errorEl.textContent = body.detail || "Error, try again.";
          errorEl.classList.remove("hidden");
          return;
        }
        state.user = body;
        updateAuthUI();
        authGateActive = false;
        closeAuthModal();
        if (!appStarted) startApp();
      } catch (err) {
        errorEl.textContent = err.message || "Network error.";
        errorEl.classList.remove("hidden");
      }
    });
  }

  // Inline "personalizza parametri" panel shown under one strategy row in a
  // watchlist card — pre-filled with this ticker's override (if any) or the
  // strategy's own defaults, so the field always shows a concrete value.
  // Hidden by default; the row's gear button toggles it open.
  function buildStrategyParamsPanel(entry, strategyName, fields, customParams) {
    const panel = document.createElement("div");
    panel.className = "strat-params-inline hidden";
    panel.addEventListener("click", (e) => e.stopPropagation());

    const inputs = {};
    fields.forEach((field) => {
      const row = document.createElement("div");
      row.className = "param-row";
      const value = customParams && field.key in customParams ? customParams[field.key] : field.default;

      if (field.type === "checkbox") {
        const label = document.createElement("label");
        label.className = "param-check";
        const input = document.createElement("input");
        input.type = "checkbox";
        input.checked = Boolean(value);
        label.appendChild(input);
        label.appendChild(document.createTextNode(field.label));
        row.appendChild(label);
        inputs[field.key] = input;
      } else {
        const label = document.createElement("span");
        label.className = "param-label";
        label.textContent = field.label;
        row.appendChild(label);
        let input;
        if (field.type === "select") {
          input = document.createElement("select");
          input.className = "param-select";
          field.options.forEach((opt) => {
            const o = document.createElement("option");
            o.value = opt;
            o.textContent = opt;
            if (opt === value) o.selected = true;
            input.appendChild(o);
          });
        } else {
          input = document.createElement("input");
          input.type = "number";
          input.className = "param-input";
          if (field.min !== undefined) input.min = field.min;
          if (field.max !== undefined) input.max = field.max;
          input.step = field.step || 1;
          input.value = value;
        }
        row.appendChild(input);
        inputs[field.key] = input;
      }
      panel.appendChild(row);
    });

    const actions = document.createElement("div");
    actions.className = "param-actions";

    const resetBtn = document.createElement("button");
    resetBtn.type = "button";
    resetBtn.className = "param-btn-reset";
    resetBtn.textContent = "Reset to default";
    resetBtn.addEventListener("click", async () => {
      try {
        await fetch(`/api/watchlist/${entry.id}/strategy_params`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ strategy_name: strategyName, params: {} }),
        });
      } finally {
        loadWatchlist();
      }
    });

    const saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.className = "param-btn-save";
    saveBtn.textContent = "Save";
    saveBtn.addEventListener("click", async () => {
      const params = {};
      fields.forEach((field) => {
        const input = inputs[field.key];
        if (field.type === "checkbox") params[field.key] = input.checked;
        else if (field.type === "select") params[field.key] = input.value;
        else params[field.key] = parseFloat(input.value);
      });
      try {
        await fetch(`/api/watchlist/${entry.id}/strategy_params`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ strategy_name: strategyName, params }),
        });
      } finally {
        loadWatchlist();
      }
    });

    actions.appendChild(resetBtn);
    actions.appendChild(saveBtn);
    panel.appendChild(actions);
    return panel;
  }

  // Diramazione richiesta esplicitamente: ticker -> "solo alert" o "anche
  // operazioni automatiche" -> (se automatiche) spot/futures -> (se manca
  // la chiave) collegala li' -> scegli la strategia dall'archivio. Niente
  // lista di exchange sempre visibile: la chiave si chiede solo quando e
  // dove serve davvero.
  function buildActivationFlow(entry, autoOpen) {
    const wrap = document.createElement("div");
    wrap.className = "wl-activate-wrap";

    const openBtn = document.createElement("button");
    openBtn.type = "button";
    openBtn.className = "wl-activate-btn";
    openBtn.textContent = "+ Activate strategy from archive";
    wrap.appendChild(openBtn);

    const box = document.createElement("div");
    box.className = "wl-activate-flow hidden";
    wrap.appendChild(box);

    let flowMode = null;   // "alert" | "auto"
    let flowMarket = "spot";
    let flowCap = 0;       // tetto USDT per singolo ingresso automatico, 0 = nessuno

    const mkBtn = (label, onClick, danger) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "wl-mode-btn" + (danger ? " wl-mode-danger" : "");
      b.textContent = label;
      b.addEventListener("click", onClick);
      return b;
    };

    function stepMode() {
      box.innerHTML = "";
      const q = document.createElement("p");
      q.className = "wl-flow-q";
      q.textContent = `${entry.symbol}: should this strategy only alert you, or also trade on its own?`;
      box.appendChild(q);
      const row = document.createElement("div");
      row.className = "wl-mode-row";
      row.appendChild(mkBtn("Alerts only", () => { flowMode = "alert"; stepArchive(); }));
      row.appendChild(mkBtn("Also auto-trade", () => {
        flowMode = "auto";
        if (FUTURES_PAIR_EXCHANGES.has(entry.exchange)) stepMarket(); else stepCredCheck();
      }, true));
      box.appendChild(row);
    }

    function stepMarket() {
      box.innerHTML = "";
      const q = document.createElement("p");
      q.className = "wl-flow-q";
      q.textContent = `On ${entry.exchange.toUpperCase()}: spot or leveraged futures?`;
      box.appendChild(q);
      const row = document.createElement("div");
      row.className = "wl-mode-row";
      row.appendChild(mkBtn("Spot", () => { flowMarket = "spot"; stepCredCheck(); }));
      row.appendChild(mkBtn("Futures (leverage)", () => { flowMarket = "futures"; stepCredCheck(); }, true));
      box.appendChild(row);
    }

    async function stepCredCheck() {
      box.innerHTML = `<p class="wl-flow-q">Checking API key…</p>`;
      const endpoint = flowMarket === "futures" ? "/api/auth/futures" : "/api/auth/trading";
      let list = [];
      try { list = await fetch(endpoint).then((r) => r.json()); } catch { list = []; }
      const cred = Array.isArray(list) ? list.find((c) => c.exchange === entry.exchange) : null;
      const connected = !!(cred && cred.api_key_set && cred.enabled);
      if (!connected) { stepConnect(cred); return; }
      // Il tetto ha senso solo per l'operativa automatica: un alert da solo
      // non manda mai ordini, quindi non c'e' niente da limitare.
      if (flowMode === "auto") stepCap(); else stepArchive();
    }

    // Tetto in USDT sul SINGOLO ingresso automatico di questa strategia —
    // impostato qui, prima di attivare, perche' la credenziale exchange e'
    // condivisa da tutte le strategie che ci operano sopra e da sola non
    // basta a limitare quanto rischia ciascuna. Mai applicato alle chiusure,
    // che chiudono sempre per intero.
    function stepCap() {
      box.innerHTML = "";
      const q = document.createElement("p");
      q.className = "wl-flow-q";
      q.textContent = "Max cap per single entry order (optional):";
      box.appendChild(q);
      const hint = document.createElement("p");
      hint.className = "panel-hint";
      hint.textContent = "Leave empty to always use the amount/percentage set on the exchange key, with no extra limit. Never affects exits, which always close in full.";
      box.appendChild(hint);
      const capInput = document.createElement("input");
      capInput.type = "number";
      capInput.min = "0";
      capInput.step = "1";
      capInput.placeholder = "No cap (e.g. 500 for 500 USDT)";
      box.appendChild(capInput);
      const row = document.createElement("div");
      row.className = "wl-mode-row";
      row.appendChild(mkBtn("Continue", () => {
        const v = parseFloat(capInput.value);
        flowCap = Number.isFinite(v) && v > 0 ? v : 0;
        stepArchive();
      }, true));
      box.appendChild(row);
    }

    function stepConnect(cred) {
      box.innerHTML = "";
      const q = document.createElement("p");
      q.className = "wl-flow-q";
      q.textContent = `Connect ${entry.exchange.toUpperCase()} (${flowMarket === "futures" ? "futures" : "spot"}) — key with trading permissions, never withdrawal.`;
      box.appendChild(q);
      const keyInput = document.createElement("input");
      keyInput.type = "text"; keyInput.placeholder = "API Key"; keyInput.autocomplete = "off";
      const secretInput = document.createElement("input");
      secretInput.type = "password"; secretInput.placeholder = "API Secret"; secretInput.autocomplete = "off";
      box.appendChild(keyInput);
      box.appendChild(secretInput);
      let passInput = null;
      if (entry.exchange === "kucoin" || cred?.needs_passphrase) {
        passInput = document.createElement("input");
        passInput.type = "password"; passInput.placeholder = "Passphrase"; passInput.autocomplete = "off";
        box.appendChild(passInput);
      }
      const status = document.createElement("span");
      status.className = "wl-flow-status";
      const submitBtn = document.createElement("button");
      submitBtn.type = "button";
      submitBtn.className = "wl-mode-btn wl-mode-danger active";
      submitBtn.textContent = "Connect";
      submitBtn.addEventListener("click", async () => {
        if (!keyInput.value || !secretInput.value) { status.textContent = "Key and secret are required"; return; }
        submitBtn.disabled = true;
        const endpoint = flowMarket === "futures" ? "/api/auth/futures" : "/api/auth/trading";
        const body = {
          exchange: entry.exchange, api_key: keyInput.value, api_secret: secretInput.value,
          passphrase: passInput?.value || "", enabled: true, size_mode: "fixed_usdt", size_value: 50,
        };
        try {
          const resp = await fetch(endpoint, {
            method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
          });
          if (resp.ok) { if (flowMode === "auto") stepCap(); else stepArchive(); }
          else status.textContent = (await resp.json().catch(() => ({}))).detail || `Error (${resp.status})`;
        } catch { status.textContent = "Network error"; }
        submitBtn.disabled = false;
      });
      box.appendChild(submitBtn);
      box.appendChild(status);
    }

    async function stepArchive() {
      box.innerHTML = `<p class="wl-flow-q">Loading archive…</p>`;
      let data = { items: [] };
      try { data = await fetch("/api/archive").then((r) => r.json()); } catch { /* fallback sotto */ }
      const norm = (s) => (s || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
      const matches = (data.items || []).filter((it) =>
        norm(it.symbol) === norm(entry.symbol) && it.asset_type === entry.asset_type &&
        it.exchange === entry.exchange && it.state === "pronto"
      );
      box.innerHTML = "";
      if (!matches.length) {
        const p = document.createElement("p");
        p.className = "panel-hint";
        p.textContent = `No ready configuration in the archive for ${entry.symbol} on ${entry.exchange.toUpperCase()}.`;
        box.appendChild(p);
        stepFresh();
        return;
      }
      const q = document.createElement("p");
      q.className = "wl-flow-q";
      q.textContent = "Pick a strategy from the archive:";
      box.appendChild(q);
      const fmtPct = (v) => (v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`);
      matches.forEach((it) => {
        const m = it.metrics || {};
        const card = document.createElement("div");
        card.className = "wl-archive-pick";
        // Ogni dato qui viene da un backtest reale gia' misurato e salvato —
        // non solo il rendimento, tutto cio' che serve per giudicare se
        // fidarsi: trade, drawdown, profit factor, sharpe, quante candele.
        card.innerHTML = `
          <div class="wl-archive-head"><b>${escapeHtml(strategyLabel(it.strategy_name))}</b></div>
          ${fourFigures({ simple: m.simple_return_pct, compounded: m.total_return_pct, simpleDd: m.simple_max_drawdown_pct, dd: m.max_drawdown_pct }, true)}
          <div class="wl-archive-stats">
            <span>${m.num_trades ?? "—"} trades</span>
            <span>win ${m.win_rate_pct != null ? m.win_rate_pct.toFixed(0) + "%" : "—"}</span>
            <span>PF ${m.profit_factor != null ? m.profit_factor.toFixed(2) : "—"}</span>
            <span>Sharpe ${m.sharpe_ratio != null ? m.sharpe_ratio.toFixed(2) : "—"}</span>
            <span>${m.interval || entry.interval || "—"} · ${m.candles ?? "—"} candles</span>
          </div>
          <button type="button" class="wl-archive-use-btn">Use this</button>
          <span class="wl-flow-status"></span>
        `;
        const useBtn = card.querySelector(".wl-archive-use-btn");
        const status = card.querySelector(".wl-flow-status");
        useBtn.addEventListener("click", async () => {
          useBtn.disabled = true;
          status.textContent = "Activating…";
          try {
            const resp = await fetch(`/api/archive/${it.id}/apply-to-alert`, {
              method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ auto_trade: flowMode === "auto", market: flowMarket }),
            });
            if (resp.ok) {
              if (flowMode === "auto" && flowCap > 0) {
                const applied = await resp.json().catch(() => null);
                const watchId = applied?.watchlist_entry?.id;
                if (watchId) {
                  await fetch(`/api/watchlist/${watchId}/size_cap`, {
                    method: "PATCH", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ strategy_name: it.strategy_name, cap_usdt: flowCap }),
                  });
                }
              }
              status.textContent = "✓ Activated";
              loadWatchlist();
            } else {
              const err = await resp.json().catch(() => ({}));
              status.textContent = err.detail || `Error (${resp.status})`;
              useBtn.disabled = false;
            }
          } catch {
            status.textContent = "Network error";
            useBtn.disabled = false;
          }
        });
        box.appendChild(card);
      });
      const freshBtn = document.createElement("button");
      freshBtn.type = "button";
      freshBtn.className = "wl-activate-btn";
      freshBtn.textContent = "Test a new strategy instead";
      freshBtn.addEventListener("click", () => { box.innerHTML = ""; stepFresh(); });
      box.appendChild(freshBtn);
    }

    // Niente in archivio (o l'utente lo vuole comunque): sceglie la
    // strategia con i parametri di default e parte da li', direttamente in
    // questa tab — senza dover prima passare da un backtest o da Alert.
    function stepFresh() {
      const q = document.createElement("p");
      q.className = "wl-flow-q";
      q.textContent = "Test a strategy with default parameters:";
      box.appendChild(q);
      (state.availableStrategies || []).forEach((name) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "wl-archive-pick";
        btn.textContent = strategyLabel(name);
        btn.addEventListener("click", async () => {
          btn.disabled = true;
          try {
            const watch = await fetch("/api/watchlist", {
              method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                symbol: entry.symbol, asset_type: entry.asset_type,
                exchange: entry.exchange, interval: entry.interval || "1d", on_close: true,
                base_token_address: entry.base_token_address || null,
              }),
            }).then((r) => r.json());
            await fetch(`/api/watchlist/${watch.id}/strategy`, {
              method: "PATCH", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ strategy_name: name, enabled: true }),
            });
            if (flowMode === "auto") {
              await fetch(`/api/watchlist/${watch.id}/auto_trade`, {
                method: "PATCH", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ strategy_name: name, enabled: true }),
              });
              if (flowMarket === "futures") {
                await fetch(`/api/watchlist/${watch.id}/market`, {
                  method: "PATCH", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ strategy_name: name, market: "futures" }),
                });
              }
              if (flowCap > 0) {
                await fetch(`/api/watchlist/${watch.id}/size_cap`, {
                  method: "PATCH", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ strategy_name: name, cap_usdt: flowCap }),
                });
              }
            }
          } finally {
            loadWatchlist();
            loadArchive();
          }
        });
        box.appendChild(btn);
      });
    }

    openBtn.addEventListener("click", () => {
      box.classList.toggle("hidden");
      if (!box.classList.contains("hidden")) stepMode();
    });

    // Un ticker appena aggiunto chiede subito la strategia, senza dover
    // prima aprire la riga e poi cliccare "+ Attiva" — due clic in meno
    // esattamente dove l'utente si aspettava la domanda.
    if (autoOpen) {
      box.classList.remove("hidden");
      stepMode();
    }

    return wrap;
  }

  async function loadWatchlist() {
    let entries = [];
    try {
      const resp = await fetch("/api/watchlist");
      if (resp.ok) {
        entries = await resp.json();
      } else {
        showTabError("watchlist-list", `Error loading watchlist (${resp.status}).`);
      }
    } catch (err) {
      showTabError("watchlist-list", "Couldn't load the watchlist: network problem.");
    }
    state.alertEntries = entries; // read by renderFavorites() for the alert-bell indicator
    renderFavorites();
    const list = el("watchlist-list");
    const openIds = new Set(
      Array.from(list.querySelectorAll(".tick-card.open")).map((c) => c.dataset.entryId)
    );
    list.innerHTML = "";
    el("watchlist-count").textContent = entries.length ? `${entries.length} active` : "";
    if (!entries.length) {
      const li = document.createElement("li");
      li.className = "panel-hint";
      li.textContent = "No tickers in watchlist.";
      list.appendChild(li);
      return;
    }
    entries.forEach((entry) => {
      const card = document.createElement("li");
      card.className = "tick-card" + (openIds.has(entry.id) ? " open" : "");
      card.dataset.entryId = entry.id;

      const head = document.createElement("div");
      head.className = "tick-card-head";
      const activeCount = entry.strategies.length;
      const hasCustomParams = Object.keys(entry.strategy_params || {}).length > 0;
      head.innerHTML = `
        <span><span class="wl-symbol">${entry.symbol}</span><span class="wl-exch">${entry.asset_type === "crypto" ? entry.exchange.toUpperCase() : "Stocks"} · ${entry.interval}</span></span>
        ${entry.on_close ? '<span class="wl-close-badge" title="Alert on candle close">CLOSE</span>' : ""}
        ${hasCustomParams ? '<span class="wl-custom-badge" title="One or more custom parameters">★</span>' : ""}
        <span class="wl-summary">${activeCount ? `${activeCount} active` : "none active"}</span>
        <button type="button" class="wl-head-remove" title="Remove this ticker from the watchlist">✕</button>
        <span class="wl-caret">▾</span>
      `;
      // La x sulla riga chiusa toglie l'intero ticker senza dover prima
      // aprirla — quella dentro la riga aperta ("Rimuovi ticker" in fondo)
      // restava l'unica strada, e l'utente l'ha chiesta qui perché non si vede
      // finché non espandi.
      head.querySelector(".wl-head-remove").addEventListener("click", async (e) => {
        e.stopPropagation();
        // Lorenzo, 13/10: always ask first, a stray tap deleted active alerts.
        if (!confirmAlertDelete(entry.symbol)) return;
        await fetch(`/api/watchlist/${entry.id}`, { method: "DELETE" });
        loadWatchlist();
      });
      head.addEventListener("click", (e) => {
        if (e.target.closest(".wl-head-remove")) return;
        card.classList.toggle("open");
      });

      const body = document.createElement("div");
      body.className = "tick-card-body";

      const intervalRow = document.createElement("div");
      intervalRow.className = "strat-row wl-interval-row";
      const intervalLabel = document.createElement("span");
      intervalLabel.textContent = "Strategy timeframe";
      const intervalSelect = document.createElement("select");
      intervalSelect.className = "wl-interval-select";
      CANONICAL_INTERVALS.forEach((iv) => {
        const opt = document.createElement("option");
        opt.value = iv;
        opt.textContent = iv;
        if (iv === entry.interval) opt.selected = true;
        intervalSelect.appendChild(opt);
      });
      intervalSelect.addEventListener("click", (e) => e.stopPropagation());
      intervalSelect.addEventListener("change", async () => {
        try {
          await fetch(`/api/watchlist/${entry.id}/interval`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ interval: intervalSelect.value }),
          });
        } finally {
          loadWatchlist();
        }
      });
      intervalRow.appendChild(intervalLabel);
      intervalRow.appendChild(intervalSelect);
      body.appendChild(intervalRow);

      // Applies to the whole ticker (not per-strategy) — matches the
      // background scanner in main.py, which drops the still-forming
      // candle for this entry only when on_close is true.
      const onCloseRow = document.createElement("div");
      onCloseRow.className = "strat-row wl-onclose-row";
      const onCloseLabel = document.createElement("span");
      onCloseLabel.textContent = "On candle close";
      const onCloseToggle = document.createElement("button");
      onCloseToggle.type = "button";
      onCloseToggle.className = "wl-toggle" + (entry.on_close ? " on" : "");
      onCloseToggle.title = "When on, the alert fires only when the candle closes — no false intra-bar signals";
      onCloseToggle.innerHTML = '<span class="knob"></span>';
      onCloseToggle.addEventListener("click", async () => {
        const nextOn = !onCloseToggle.classList.contains("on");
        onCloseToggle.classList.toggle("on", nextOn);
        try {
          await fetch(`/api/watchlist/${entry.id}/on_close`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ on_close: nextOn }),
          });
        } finally {
          loadWatchlist();
        }
      });
      onCloseRow.appendChild(onCloseLabel);
      onCloseRow.appendChild(onCloseToggle);
      body.appendChild(onCloseRow);

      body.appendChild(buildActivationFlow(entry));

      state.availableStrategies.forEach((name) => {
        const isOn = entry.strategies.includes(name);
        const customParams = (entry.strategy_params || {})[name];
        const fields = STRATEGY_PARAM_FIELDS[name] || [];

        const row = document.createElement("div");
        row.className = "strat-row";
        const label = document.createElement("span");
        label.className = "strat-name";
        label.textContent = strategyLabel(name);
        row.appendChild(label);
        const levels = rsiLevelsChip(name, customParams);
        if (levels) row.appendChild(levels);

        let paramsPanel = null;
        if (fields.length) {
          const gearBtn = document.createElement("button");
          gearBtn.type = "button";
          gearBtn.className = "strat-gear" + (customParams ? " active" : "");
          gearBtn.title = "This strategy's parameters for this ticker";
          gearBtn.innerHTML =
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';
          gearBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (paramsPanel) paramsPanel.classList.toggle("hidden");
          });
          row.appendChild(gearBtn);
        }

        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "wl-toggle" + (isOn ? " on" : "");
        toggle.innerHTML = '<span class="knob"></span>';
        toggle.addEventListener("click", async () => {
          const nextOn = !toggle.classList.contains("on");
          toggle.classList.toggle("on", nextOn);
          try {
            await fetch(`/api/watchlist/${entry.id}/strategy`, {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ strategy_name: name, enabled: nextOn }),
            });
          } finally {
            loadWatchlist();
          }
        });
        row.appendChild(toggle);
        body.appendChild(row);

        if (fields.length) {
          paramsPanel = buildStrategyParamsPanel(entry, name, fields, customParams);
          body.appendChild(paramsPanel);
        }

        if (isOn) {
          // Frequency selector
          const freqRow = document.createElement("div");
          freqRow.className = "strat-sub-row";
          const freqSel = document.createElement("select");
          freqSel.className = "wl-freq-select";
          freqSel.title = "Alert frequency for this strategy";
          [["every", "Every signal"], ["once", "First time only"]].forEach(([val, label]) => {
            const opt = document.createElement("option");
            opt.value = val;
            opt.textContent = label;
            if ((entry.alert_frequency?.[name] || "every") === val) opt.selected = true;
            freqSel.appendChild(opt);
          });
          freqSel.addEventListener("change", async () => {
            await fetch(`/api/watchlist/${entry.id}/alert_frequency`, {
              method: "PATCH", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ strategy_name: name, frequency: freqSel.value }),
            });
          });

          // Per-strategy interval selector
          const stratIvSel = document.createElement("select");
          stratIvSel.className = "wl-freq-select";
          stratIvSel.title = "Timeframe specific to this strategy";
          const defaultOpt = document.createElement("option");
          defaultOpt.value = "";
          defaultOpt.textContent = `Default (${entry.interval})`;
          stratIvSel.appendChild(defaultOpt);
          CANONICAL_INTERVALS.forEach(iv => {
            const opt = document.createElement("option");
            opt.value = iv;
            opt.textContent = iv;
            if ((entry.strategy_intervals?.[name] || "") === iv) opt.selected = true;
            stratIvSel.appendChild(opt);
          });
          stratIvSel.addEventListener("change", async () => {
            await fetch(`/api/watchlist/${entry.id}/strategy_interval`, {
              method: "PATCH", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ strategy_name: name, interval: stratIvSel.value || null }),
            });
          });

          // Test alert button
          const testBtn = document.createElement("button");
          testBtn.type = "button";
          testBtn.className = "wl-test-btn";
          testBtn.title = "Send a Telegram test with the latest detected signal";
          testBtn.textContent = "🧪";
          testBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            testBtn.disabled = true;
            testBtn.textContent = "…";
            try {
              const resp = await fetch(`/api/watchlist/${entry.id}/test-alert`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ strategy_name: name }),
              });
              const data = await resp.json();
              testBtn.textContent = data.sent ? "✓" : "—";
            } catch { testBtn.textContent = "✕"; }
            setTimeout(() => { testBtn.disabled = false; testBtn.textContent = "🧪"; }, 2000);
          });

          freqRow.appendChild(freqSel);
          freqRow.appendChild(stratIvSel);
          freqRow.appendChild(testBtn);
          body.appendChild(freqRow);

          // Alert vs trading automatico: la decisione vive qui, per strategia
          // e per ticker — non piu' un interruttore unico per exchange in Opera.
          const tradeRow = document.createElement("div");
          tradeRow.className = "strat-sub-row wl-autotrade-row";
          const isAuto = !!entry.auto_trade?.[name];
          const alertBtn = document.createElement("button");
          alertBtn.type = "button";
          alertBtn.className = "wl-mode-btn" + (isAuto ? "" : " active");
          alertBtn.textContent = "Alerts only";
          const autoBtn = document.createElement("button");
          autoBtn.type = "button";
          autoBtn.className = "wl-mode-btn wl-mode-danger" + (isAuto ? " active" : "");
          autoBtn.textContent = "Auto-trading";
          const setMode = async (auto) => {
            alertBtn.classList.toggle("active", !auto);
            autoBtn.classList.toggle("active", auto);
            await fetch(`/api/watchlist/${entry.id}/auto_trade`, {
              method: "PATCH", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ strategy_name: name, enabled: auto }),
            });
          };
          alertBtn.addEventListener("click", () => setMode(false));
          autoBtn.addEventListener("click", () => setMode(true));
          tradeRow.appendChild(alertBtn);
          tradeRow.appendChild(autoBtn);
          body.appendChild(tradeRow);
          if (isAuto) {
            const hint = document.createElement("p");
            hint.className = "panel-hint wl-autotrade-hint";
            hint.textContent = `Real orders on ${entry.exchange.toUpperCase()} on every signal — requires API keys set up and enabled below for this exchange.`;
            body.appendChild(hint);

            // Spot/futures esiste solo dove l'exchange ha anche un adattatore
            // futures registrato — stesso insieme usato per l'autocomplete
            // pair futures in Opera (FUTURES_PAIR_EXCHANGES).
            if (FUTURES_PAIR_EXCHANGES.has(entry.exchange)) {
              const marketRow = document.createElement("div");
              marketRow.className = "strat-sub-row wl-autotrade-row";
              const isFutures = entry.market?.[name] === "futures";
              const spotBtn = document.createElement("button");
              spotBtn.type = "button";
              spotBtn.className = "wl-mode-btn" + (isFutures ? "" : " active");
              spotBtn.textContent = "Spot";
              const futBtn = document.createElement("button");
              futBtn.type = "button";
              futBtn.className = "wl-mode-btn wl-mode-danger" + (isFutures ? " active" : "");
              futBtn.textContent = "Futures (leverage)";
              const setMarket = async (market) => {
                spotBtn.classList.toggle("active", market === "spot");
                futBtn.classList.toggle("active", market === "futures");
                await fetch(`/api/watchlist/${entry.id}/market`, {
                  method: "PATCH", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ strategy_name: name, market }),
                });
              };
              spotBtn.addEventListener("click", () => setMarket("spot"));
              futBtn.addEventListener("click", () => setMarket("futures"));
              marketRow.appendChild(spotBtn);
              marketRow.appendChild(futBtn);
              body.appendChild(marketRow);
              if (isFutures) {
                const futHint = document.createElement("p");
                futHint.className = "panel-hint wl-autotrade-hint";
                futHint.textContent = "Leverage and margin follow the futures credentials set up below for this exchange.";
                body.appendChild(futHint);
              }
            }

            // Tetto USDT per singolo ingresso di QUESTA strategia — la
            // credenziale exchange (size_mode/size_value) e' condivisa da
            // tutte le strategie che ci operano sopra, quindi da sola non
            // basta a limitare quanto rischia ciascuna. Mai sulle chiusure.
            const capRow = document.createElement("div");
            capRow.className = "strat-sub-row wl-cap-row";
            const capLabel = document.createElement("span");
            capLabel.className = "wl-cap-label";
            capLabel.textContent = "Cap per entry (USDT):";
            const capInput = document.createElement("input");
            capInput.type = "number";
            capInput.min = "0";
            capInput.step = "1";
            capInput.className = "wl-cap-input";
            capInput.placeholder = "none";
            capInput.value = entry.size_cap_usdt?.[name] || "";
            let capTimer = null;
            capInput.addEventListener("input", () => {
              clearTimeout(capTimer);
              capTimer = setTimeout(async () => {
                const v = parseFloat(capInput.value);
                await fetch(`/api/watchlist/${entry.id}/size_cap`, {
                  method: "PATCH", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ strategy_name: name, cap_usdt: Number.isFinite(v) && v > 0 ? v : 0 }),
                });
              }, 600);
            });
            capRow.appendChild(capLabel);
            capRow.appendChild(capInput);
            body.appendChild(capRow);
          }

          // Last trigger + count (async fetch stats)
          const statsRow = document.createElement("div");
          statsRow.className = "strat-sub-row strat-stats";
          statsRow.textContent = "…";
          body.appendChild(statsRow);
          fetch(`/api/watchlist/${entry.id}/stats`).then(r => r.json()).then(stats => {
            const s = stats[name];
            if (!s || !s.last_ts) { statsRow.textContent = "No alerts sent"; return; }
            const diff = Math.floor(Date.now() / 1000) - s.last_ts;
            const ago = diff < 3600 ? `${Math.floor(diff / 60)}m ago` : diff < 86400 ? `${Math.floor(diff / 3600)}h ago` : new Date(s.last_ts * 1000).toLocaleDateString("en-US");
            statsRow.textContent = `Last: ${ago} · ${s.count} alerts total`;
          }).catch(() => { statsRow.textContent = ""; });
        }
      });

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "wl-remove";
      removeBtn.textContent = "✕ Remove ticker";
      removeBtn.style.marginTop = "4px";
      removeBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!confirmAlertDelete(entry.symbol)) return;
        await fetch(`/api/watchlist/${entry.id}`, { method: "DELETE" });
        loadWatchlist();
      });
      body.appendChild(removeBtn);

      card.appendChild(head);
      card.appendChild(body);
      list.appendChild(card);
    });
  }

  function confirmAlertDelete(symbol) {
    return window.confirm(`Delete ${symbol} from the alerts? Its active strategies stop sending signals.`);
  }

  // RSI+BB only (Lorenzo, 13/10): the two levels the alert fires on, visible
  // next to the strategy name without opening the gear.
  function rsiLevelsChip(name, customParams) {
    if (!/RSI\+BB/.test(name)) return null;
    const fields = STRATEGY_PARAM_FIELDS[name] || [];
    const value = (key) => {
      const v = customParams?.[key];
      if (v !== undefined && v !== null && v !== "") return v;
      return fields.find((f) => f.key === key)?.default;
    };
    const os = value("rsi_oversold"), ob = value("rsi_overbought");
    if (os === undefined && ob === undefined) return null;
    const chip = document.createElement("span");
    chip.className = "strat-rsi-levels";
    chip.title = "RSI oversold / overbought this alert uses";
    chip.textContent = `OS ${os ?? "–"} · OB ${ob ?? "–"}`;
    return chip;
  }

  // ── Archivio strategie ─────────────────────────────────────────────────────
  //
  // Una voce nasce senza numeri: il backtest gira in background, perche'
  // accendere un alert non deve aspettarlo. Per questo lo stato "in corso"
  // esiste ed e' mostrato — e per questo la lista si ricarica da sola una volta
  // sola dopo qualche secondo, invece di lasciare "in corso" a schermo finche'
  // qualcuno non ricarica la pagina.

  let _archiveRecheck = null;

  async function loadArchive() {
    if (!state.user) return;
    const list = el("archive-list");
    if (!list) return;
    try {
      const resp = await fetch("/api/archive");
      if (!resp.ok) return;
      const body = await resp.json();
      renderArchive(body.items || []);
    } catch {
      list.innerHTML = '<li class="panel-hint">Archive unreachable.</li>';
    }
  }

  function renderArchive(items) {
    const list = el("archive-list");
    const count = el("archive-count");
    if (!list) return;
    if (count) count.textContent = items.length ? String(items.length) : "";
    if (!items.length) {
      list.innerHTML = '<li class="panel-hint">No archived strategies. Activate one from the watchlist, or save one from the Lab.</li>';
      return;
    }

    const pct = (v) => (v === null || v === undefined ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`);
    const num = (v, d = 2) => (v === null || v === undefined ? "—" : v.toFixed(d));
    const when = (ts) => new Date(ts * 1000).toLocaleDateString("en-US",
      { day: "2-digit", month: "short", year: "2-digit" });

    // Condivisa fra la card (dove avvisa) e il confronto fra voci dello
    // stesso ticker (dove pesa nel punteggio) — gli stessi controlli devono
    // dire la stessa cosa nei due posti, non due versioni leggermente diverse.
    const warnFlagsFor = (e) => {
      const o = e.optimizer || {};
      const warn = [];
      if (o.regime_passed === false) warn.push("gate not passed");
      if (o.overfitted) warn.push("overfitted");
      if (o.deterministic === false) warn.push("partly sampled");
      if (o.pbo != null && o.pbo >= 0.2) warn.push(`over-optimization ${(o.pbo * 100).toFixed(0)}%`);
      return warn;
    };

    const renderCard = (e, badge) => {
      const m = e.metrics;
      const body = e.state === "pronto" && m
        ? `${fourFigures({ simple: m.simple_return_pct, compounded: m.total_return_pct, simpleDd: m.simple_max_drawdown_pct, dd: m.max_drawdown_pct }, true)}
           <div class="arch-metrics">
             <span>${m.num_trades} trades</span>
             <span>PF ${num(m.profit_factor)}</span>
             <span>${m.candles} candles · ${m.interval}</span>
           </div>`
        : e.state === "fallito"
        ? `<div class="arch-failed">Backtest failed: ${escapeHtml(e.error || "reason not recorded")}</div>`
        : '<div class="arch-pending">Backtest running…</div>';
      const params = Object.entries(e.params || {})
        .map(([k, v]) => `${escapeHtml(k)}=${escapeHtml(String(v))}`).join(" · ");
      // Come si è arrivati a quei parametri. Senza, due risultati con lo stesso
      // rendimento — uno enumerato e uno sorteggiato, uno con il gate superato
      // e uno no — sembrerebbero la stessa cosa.
      const o = e.optimizer || {};
      const flags = [];
      if (o.mode) flags.push(`${o.mode === "plateau" ? "stable" : o.mode === "grid" ? "grid" : o.mode === "max_return" ? "max return" : "quick"} search`);
      if (o.evaluations) flags.push(`${o.evaluations} backtest`);
      if (o.out_of_sample_return_pct != null) {
        flags.push(`out-of-sample ${o.out_of_sample_return_pct >= 0 ? "+" : ""}${o.out_of_sample_return_pct.toFixed(1)}%`);
      }
      const warn = warnFlagsFor(e);
      const badgeHtml = badge === "best"
        ? '<span class="arch-best-badge" title="Among this ticker\'s entries, the one that holds up best under the checks">★ Recommended</span>'
        : badge === "least-bad"
        ? '<span class="arch-best-badge arch-caution-badge" title="No entry for this ticker passes every check — this is the least bad">least bad</span>'
        : "";
      return `
        <li class="arch-card${badge === "best" ? " arch-best" : ""}" data-id="${e.id}">
          <div class="arch-head">
            ${badgeHtml}
            <span class="arch-strat">${escapeHtml(strategyLabel(e.strategy_name))}</span>
            <span class="arch-src">${e.source === "alert" ? "from alert" : "saved manually"}</span>
            <span class="arch-date">${when(e.created_at)}</span>
          </div>
          ${body}
          ${flags.length ? `<div class="arch-how">${flags.map(escapeHtml).join(" · ")}</div>` : ""}
          ${warn.length ? `<div class="arch-warn">⚠ ${warn.map(escapeHtml).join(" · ")}</div>` : ""}
          ${params ? `<div class="arch-params">${params}</div>` : '<div class="arch-params">default parameters</div>'}
          ${e.note ? `<div class="arch-note">${escapeHtml(e.note)}</div>` : ""}
          <div class="arch-actions">
            <button type="button" class="arch-apply" data-id="${e.id}">Apply to chart</button>
            <button type="button" class="arch-alert" data-id="${e.id}">Enable alert</button>
            <button type="button" class="arch-testpair" data-id="${e.id}" title="Same values on another pair: candles the search never saw">Test on another pair</button>
            <button type="button" class="arch-export" data-id="${e.id}">⤓ Excel</button>
            <button type="button" class="arch-share" data-id="${e.id}">⇪ Share</button>
            <button type="button" class="arch-del" data-id="${e.id}">Delete</button>
          </div>
          <form class="arch-testpair-form hidden" data-form="${e.id}">
            <input type="text" class="arch-testpair-symbol" placeholder="Pair, e.g. ETHUSDT" list="arch-pairs-${e.id}" autocomplete="off" required />
            <datalist id="arch-pairs-${e.id}"></datalist>
            <select class="arch-testpair-exch">
              ${["mexc", "binance", "kucoin", "kraken"].map((x) => `<option value="${x}"${x === (e.exchange || "mexc") ? " selected" : ""}>${x.toUpperCase()}</option>`).join("")}
            </select>
            <button type="submit">Test</button>
          </form>
          <div class="arch-testpair-out" data-out="${e.id}"></div>
          <p class="arch-status hidden" data-status="${e.id}"></p>
        </li>`;
    };

    // Confronto fra le voci di uno stesso ticker: non un punteggio arbitrario,
    // ma la stessa logica gia' usata per i warning sulla card, ridotta a un
    // ordinamento. Un gate saltato pesa piu' di qualunque differenza di
    // rendimento (coerente con "il PBO conferma il verdetto dello Sharpe
    // deflazionato" — i controlli statistici vengono prima del numero), il
    // rendimento fuori campione conta piu' di quello in-sample quando c'e'
    // (e' la stima meno viziata), e pochi trade valgono meno fiducia.
    const scoreEntry = (e) => {
      if (e.state !== "pronto" || !e.metrics) return null;
      const m = e.metrics;
      const o = e.optimizer || {};
      const flags = warnFlagsFor(e);
      const usedOOS = o.out_of_sample_return_pct != null;
      const ret = usedOOS ? o.out_of_sample_return_pct : m.total_return_pct;
      const dd = Math.abs(m.max_drawdown_pct || 0);
      const tradeConfidence = Math.min(1, (m.num_trades || 0) / 20);
      const riskAdjusted = ret / (1 + dd / 100);
      const score = riskAdjusted * (0.5 + 0.5 * tradeConfidence) - flags.length * 50;
      return { entry: e, score, flags, ret, usedOOS, dd };
    };

    const buildRecommendation = (entries) => {
      const scored = entries.map(scoreEntry).filter(Boolean);
      if (scored.length < 2) return null;
      scored.sort((a, b) => b.score - a.score);
      const [best, runnerUp] = scored;

      const bits = [];
      bits.push(best.flags.length
        ? `⚠ ${best.flags.join(", ")}`
        : "no statistical check skipped");
      bits.push(`${best.usedOOS ? "out-of-sample return" : "return"} ${pct(best.ret)}, drawdown ${pct(-best.dd)}`);
      const deltaRet = best.ret - runnerUp.ret;
      if (Math.abs(deltaRet) >= 0.5) {
        bits.push(`${Math.abs(deltaRet).toFixed(1)} points ${deltaRet >= 0 ? "above" : "below"} the runner-up`);
      }
      if (best.flags.length === 0 && runnerUp.flags.length > 0) {
        bits.push("the others fail at least one check");
      }

      // Nessuna voce pulita: dirlo chiaro invece di consigliarne comunque una
      // come se fosse affidabile — coerente con "il gate blocca" del progetto,
      // qui applicato a un confronto invece che a un singolo risultato.
      const allFlagged = scored.every((s) => s.flags.length > 0);

      return {
        // Il badge verde "Consigliata" sulla card avrebbe contraddetto
        // l'avviso qui sopra se applicato anche quando nessuna voce e' pulita
        // — in quel caso la migliore resta segnalata, ma come "meno peggio",
        // non come una scelta approvata.
        bestId: allFlagged ? null : best.entry.id,
        leastBadId: allFlagged ? best.entry.id : null,
        html: allFlagged
          ? `<div class="arch-recommend arch-recommend-warn">No entry for ${escapeHtml(best.entry.symbol)} passes every check — treat them as exploratory, not as a trading signal. The one that holds up best: <b>${escapeHtml(strategyLabel(best.entry.strategy_name))}</b> (${bits.map(escapeHtml).join(" · ")}).</div>`
          : `<div class="arch-recommend">★ Recommended: <b>${escapeHtml(strategyLabel(best.entry.strategy_name))}</b> — ${bits.map(escapeHtml).join(" · ")}</div>`,
      };
    };

    // Con tante strategie salvate diventava una lista piatta da scorrere
    // senza punti di riferimento, tutte mischiate fra ticker diversi.
    // Raggruppate per simbolo (ordine di prima comparsa, che segue quello
    // gia' dato dal server — piu' recenti prima), col ticker come titolo
    // invece che ripetuto su ogni card.
    const groups = new Map();
    items.forEach((e) => {
      if (!groups.has(e.symbol)) groups.set(e.symbol, []);
      groups.get(e.symbol).push(e);
    });
    list.innerHTML = [...groups.entries()].map(([symbol, entries]) => {
      const rec = buildRecommendation(entries);
      return `
      <li class="arch-group">
        <details class="arch-group-details" open>
          <summary class="arch-group-head">
            <span class="arch-symbol">${escapeHtml(symbol)}</span>
            <span class="arch-group-count">${entries.length}</span>
          </summary>
          ${rec ? rec.html : ""}
          <ul class="arch-group-cards">${entries.map((e) => renderCard(e,
            rec && e.id === rec.bestId ? "best" : rec && e.id === rec.leastBadId ? "least-bad" : null,
          )).join("")}</ul>
        </details>
      </li>`;
    }).join("");

    list.querySelectorAll(".arch-del").forEach((btn) => {
      btn.addEventListener("click", async () => {
        // 15/10 (Lorenzo): ask first, as for the alerts
        const e = items.find((x) => x.id === btn.dataset.id) || {};
        const what = [strategyLabel(e.strategy_name), e.symbol, e.interval].filter(Boolean).join(" · ");
        if (!window.confirm(`Delete ${what || "this strategy"} from the archive? This cannot be undone.`)) return;
        await fetch(`/api/archive/${btn.dataset.id}`, { method: "DELETE" });
        loadArchive();
      });
    });
    // Test on another pair (Lorenzo, 15/10): same values, candles the search
    // never saw — the whole history of the new pair.
    list.querySelectorAll(".arch-testpair").forEach((btn) => {
      btn.addEventListener("click", () => {
        const form = list.querySelector(`[data-form="${btn.dataset.id}"]`);
        form.classList.toggle("hidden");
        if (!form.classList.contains("hidden")) form.querySelector("input").focus();
      });
    });
    list.querySelectorAll(".arch-testpair-form").forEach((form) => {
      const id = form.dataset.form;
      const input = form.querySelector("input");
      const dl = form.querySelector("datalist");
      let t = null;
      input.addEventListener("input", () => {
        clearTimeout(t);
        t = setTimeout(async () => {
          const q = input.value.trim();
          if (q.length < 2) return;
          try {
            const items = await fetch(`/api/symbols?query=${encodeURIComponent(q)}`).then((r) => r.json());
            dl.innerHTML = (items || []).filter((it) => it.asset_type === "crypto").slice(0, 12)
              .map((it) => `<option value="${escapeHtml(it.symbol)}">${escapeHtml(it.provider || "")}</option>`).join("");
          } catch { /* suggestions are optional */ }
        }, 250);
      });
      form.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const out = list.querySelector(`[data-out="${id}"]`);
        const symbol = input.value.trim().toUpperCase();
        if (!symbol) return;
        out.innerHTML = `<p class="panel-hint">Backtesting ${escapeHtml(symbol)} with the same values…</p>`;
        try {
          const resp = await fetch(`/api/archive/${id}/test-on-pair`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol, asset_type: "crypto", exchange: form.querySelector("select").value }),
          });
          const body = await resp.json();
          if (!resp.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Error ${resp.status}`);
          // 15/10 (Lorenzo): "un tasto per decidere se salvare o eliminare
          // l'esito del test" — it stayed on the card with no way to remove it.
          out.innerHTML = pairTestTable(body) + `
            <div class="arch-testpair-actions">
              <button type="button" class="arch-testpair-save">Save to archive</button>
              <button type="button" class="arch-testpair-discard">Discard</button>
            </div>`;
          out.querySelector(".arch-testpair-discard").addEventListener("click", () => { out.innerHTML = ""; });
          out.querySelector(".arch-testpair-save").addEventListener("click", async (ev2) => {
            const btn = ev2.currentTarget;
            const entry = items.find((x) => x.id === id) || {};
            const bp = entry.backtest_params || {};
            btn.disabled = true;
            btn.textContent = "Saving…";
            try {
              const r2 = await fetch("/api/archive", {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  symbol: body.symbol, asset_type: body.asset_type, exchange: body.exchange,
                  ltf_interval: body.interval, strategy_name: body.strategy_name,
                  params: entry.params || body.params || {}, backtest_params: bp,
                  intrabar: bp.fill_at === "on_condition",
                  note: `Tested from the ${entry.symbol || "archived"} entry, same values`,
                }),
              });
              const b2 = await r2.json();
              if (!r2.ok) throw new Error(typeof b2.detail === "string" ? b2.detail : `Error ${r2.status}`);
              loadArchive();
            } catch (err2) {
              btn.disabled = false;
              btn.textContent = "Save to archive";
              out.insertAdjacentHTML("beforeend", `<p class="arch-warn">⚠ ${escapeHtml(err2.message || "Save failed")}</p>`);
            }
          });
        } catch (err) {
          out.innerHTML = `<p class="arch-warn">⚠ ${escapeHtml(err.message || "Test failed")}</p>`;
        }
      });
    });

    list.querySelectorAll(".arch-apply").forEach((btn) => {
      btn.addEventListener("click", () => {
        const entry = items.find((x) => x.id === btn.dataset.id);
        if (entry) applyArchiveEntry(entry);
      });
    });

    // Condividi: scarica il file che un altro account puo' importare
    // (1c2880d2) — il server lo costruisce dalla voce vera, non da questi
    // dati gia' in pagina, cosi' non puo' divergere da cio' che ha davvero.
    list.querySelectorAll(".arch-share").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const resp = await fetch(`/api/archive/${btn.dataset.id}/export`);
          if (!resp.ok) throw new Error(`Error ${resp.status}`);
          const data = await resp.json();
          const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${data.symbol}-${strategyLabel(data.strategy_name)}.json`.replace(/[^\w.\-]+/g, "_");
          a.click();
          URL.revokeObjectURL(url);
        } catch (err) {
          alert("Couldn't export: " + err.message);
        }
      });
    });

    // Esportare dall'archivio senza dover prima riportare i parametri sul
    // Laboratorio: il file lo costruisce comunque il server rieseguendo il
    // backtest sui parametri della voce, non su numeri che qui arriverebbero
    // solo riportati. Un campo lasciato "di default" (params/backtest_params
    // vuoti — succede per le voci piu' vecchie, o quelle nate da un alert) si
    // manda cosi' com'e': il server applica i suoi stessi valori di default,
    // gli stessi con cui questa voce e' stata misurata la prima volta.
    list.querySelectorAll(".arch-export").forEach((btn) => {
      btn.addEventListener("click", () => {
        const entry = items.find((x) => x.id === btn.dataset.id);
        if (!entry) return;
        const params = new URLSearchParams();
        params.set("symbol", entry.symbol);
        params.set("asset_type", entry.asset_type);
        params.set("exchange", entry.exchange);
        params.set("ltf_interval", entry.interval);
        params.set("strategy_name", entry.strategy_name);
        Object.entries(entry.params || {}).forEach(([k, v]) => params.set(k, v));
        Object.entries(entry.backtest_params || {}).forEach(([k, v]) => params.set(k, v));
        const link = document.createElement("a");
        link.href = `/api/export/backtest.xlsx?${params.toString()}`;
        link.rel = "noopener";
        document.body.appendChild(link);
        link.click();
        link.remove();
      });
    });

    // Accendere l'alert con i parametri archiviati. Prima l'unico modo era
    // riscriverli a mano nella scheda del ticker, e chi non lo faceva teneva
    // acceso un alert sui valori di default — uguale d'aspetto a uno
    // ottimizzato. I parametri li applica il server leggendoli dalla voce
    // d'archivio, non da qui.
    list.querySelectorAll(".arch-alert").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.id;
        const status = list.querySelector(`[data-status="${id}"]`);
        const say = (text, kind) => {
          if (!status) return;
          status.textContent = text;
          status.className = "arch-status" + (kind ? " " + kind : "");
          status.classList.remove("hidden");
        };
        const entry = items.find((x) => x.id === id);
        btn.disabled = true;
        const prev = btn.textContent;
        btn.textContent = "…";
        try {
          const resp = await fetch(`/api/archive/${id}/apply-to-alert`, { method: "POST" });
          const data = await readJson(resp);
          if (!resp.ok) {
            say("✗ " + (data.detail || `Error ${resp.status}`), "error");
            return;
          }
          const n = Object.keys(data.params || {}).length;
          say(`✓ Alert active on ${entry ? entry.symbol : ""} (${data.interval || ""}) — `
              + `${strategyLabel(data.strategy_name)}, ${n ? n + " archived parameters applied" : "default parameters"}`, "ok");
          loadWatchlist();
        } catch (err) {
          // readJson() alza un errore che nomina stato e corpo della risposta
          // (un 502 di Caddy, una pagina di login, un HTML qualsiasi). Scriverlo
          // qui e' l'unica differenza fra "il server ha risposto male" e "il
          // browser non e' arrivato al server": scartarlo lasciava un "Errore
          // di rete" che non si puo' diagnosticare.
          say("✗ " + (err.message || "Network error"), "error");
        } finally {
          btn.disabled = false;
          btn.textContent = prev;
        }
      });
    });

    // Una sola ricontrollata, e solo se c'e' davvero qualcosa da aspettare:
    // un polling perenne per una lista che cambia una volta al mese sarebbe
    // traffico speso per nulla.
    if (items.some((e) => e.state === "in corso") && !_archiveRecheck) {
      _archiveRecheck = setTimeout(() => { _archiveRecheck = null; loadArchive(); }, 8000);
    }
  }

  // Portare una configurazione sul grafico e' una cosa sola, e va fatta
  // INTERA: pair, timeframe, strategia e i parametri di quella strategia. I
  // trade disegnati sul grafico vengono da un backtest fatto con tutti e
  // quattro; cambiarne solo una parte disegna i trade di una configurazione
  // sopra il grafico di un'altra, e sembrano semplicemente sbagliati. Era la
  // segnalazione: "devono sempre coincidere".
  function applyConfigToChart({ assetType, exchange, symbol, displaySymbol,
                                interval, strategyName, params, backtestParams }) {
    if (assetType) state.assetType = assetType;
    if (exchange) state.cryptoExchange = exchange;
    if (symbol) {
      const shown = displaySymbol || symbol;
      el("ticker-input").value = shown;
      el("ticker-input").title = shown;
    }

    // I costi e la taglia con cui e' stato trovato questo risultato vengono
    // con lui — vedi getStrategyAndBacktestQuery(). Un chiamante che non li
    // passa proprio (l'archivio, quando la voce non li ha mai registrati)
    // lascia l'override cosi' com'era invece di azzerarlo: e' meglio
    // riproporre l'ultimo applicato che tornare in silenzio ai valori puliti.
    if (backtestParams) state.chartBacktestOverride = { ...backtestParams };

    const tfSelect = el("interval-primary");
    if (tfSelect && interval && tfSelect.value !== interval) {
      // Solo se il timeframe e' uno di quelli in elenco: assegnare un valore
      // che non c'e' lascerebbe il select su quello di prima, in silenzio.
      const known = Array.from(tfSelect.options).some((o) => o.value === interval);
      if (known) {
        tfSelect.value = interval;
        syncMobileTfWheel();
      }
    }

    const stratSel = el("active-strategy-select");
    if (stratSel && strategyName && stratSel.value !== strategyName && hasStrategyOption(strategyName)) {
      stratSel.value = strategyName;
      renderStrategyParamsFields();   // ogni strategia ha campi suoi
      updateOptimizeButtonVisibility();
    }

    const container = el("strategy-params-fields");
    if (container && params) {
      Object.entries(params).forEach(([key, value]) => {
        const input = container.querySelector(`[name="${key}"]`);
        if (!input) return;
        if (input.type === "checkbox") input.checked = !!value;
        else input.value = value;
      });
    }
  }

  // Lorenzo: "puoi usare anche il grafico del sito principale volendo, era
  // ideale per visualizzare ingressi". Il dettaglio di un token apre il
  // grafico di qui con un link: pair, timeframe e strategia arrivano
  // nell'URL, e i trade disegnati sono quelli di quella strategia.
  function openDeepLink() {
    const q = new URLSearchParams(location.search);
    const dex = q.get("dex");
    if (!dex) return false;
    // Called where the boot would open the saved ticker: strategies are
    // loaded, and nothing opens BTC over it afterwards. The area comes from
    // ?area=analizza, which bindSidenav() already honours.
    applyConfigToChart({
      assetType: "dex",
      symbol: dex,
      displaySymbol: q.get("name") || dex,
      interval: q.get("interval") || "5m",
      strategyName: q.get("strategy") || undefined,
      params: null,
      backtestParams: null,
    });
    // Lorenzo, 28/09: "usi il grafico del sito principale ma devi adattare la
    // grafica dello stesso per visualizzarlo qui.. sfondo nero".
    const EMBED_DARK = {
      paperBg: "#09090b",
      ink: "#e4e4e7",
      inkDim: "#71717a",
      gridMinor: "rgba(255, 255, 255, 0.035)",
      gridMajor: "rgba(255, 255, 255, 0.08)",
      bull: "#2de0a8",
      bear: "#f87171",
      accent: "#2de0a8",
    };
    if (EMBED) {
      // Lorenzo, 28/09: "il nostro grafico nel nostro sito principale aveva
      // tutti i dati… USA QUELLO". The token page shows this chart in an
      // iframe: the chart area alone, full page.
      const area = document.querySelector(".chart-area");
      if (area) document.body.append(area);
      Object.assign(COLORS_DARK, EMBED_DARK);
      applyTheme("dark", { persist: false });   // the app is dark; the user's own choice stays saved
      requestAnimationFrame(() => resizeAllCharts(true));
    }
    runAnalysis(dex);
    return true;
  }

  function applyArchiveEntry(entry) {
    // Le voci vecchie sono state salvate quando l'archivio ignorava ancora i
    // costi impostati dall'utente (backtest_params arrivava sempre vuoto):
    // per quelle un oggetto vuoto {} e' onesto, non un difetto — non c'e'
    // niente da riproporre. Per le nuove, sono i quattro valori veri.
    const bp = entry.backtest_params && Object.keys(entry.backtest_params).length
      ? entry.backtest_params : null;
    applyConfigToChart({
      assetType: entry.asset_type,
      exchange: entry.exchange,
      symbol: entry.symbol,
      interval: entry.interval,
      strategyName: entry.strategy_name,
      params: entry.params,
      backtestParams: bp,
    });
    if (!bp) state.chartBacktestOverride = null;
    runAnalysis(entry.symbol);
  }

  async function saveLabToArchive() {
    if (!state.user) {
      labEl("lab-status").textContent = "Log in to save to the archive.";
      labEl("lab-status").classList.remove("hidden");
      return;
    }
    if (!labState.symbol) return;
    const params = collectStrategyParams(labEl("lab-params-fields"), labState.strategy);
    const resp = await fetch("/api/archive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symbol: labState.symbol,
        asset_type: labState.assetType,
        exchange: labExchange(),
        ltf_interval: labState.tf,
        strategy_name: labState.strategy,
        params,
        // I quattro campi che l'utente ha davvero impostato, non i default:
        // altrimenti l'archivio ricalcola un backtest con capitale/taglia/
        // costi diversi da quello appena mostrato in schermo, e la voce
        // salvata racconta un risultato che non e' quello che ha convinto a
        // salvarla.
        backtest_params: labBacktestParams(),
        // The candles of the result on screen (board issue f3cdcc63): a period
        // set in the Lab, or the in-sample slice an optimisation shows, was
        // recomputed over the whole history and the archive disagreed.
        data_start: labState.lastBt ? labState.lastBt.data_start : null,
        data_end: labState.lastBt ? labState.lastBt.data_end : null,
        intrabar: !labState.lastBt || labState.lastBt.intrabar_fills != null,
      }),
    });
    const status = labEl("lab-status");
    status.textContent = resp.ok
      ? "Saved to the archive (Watchlist tab). The backtest is recomputed by the server."
      : "Save failed.";
    status.classList.remove("hidden");
    if (resp.ok) loadArchive();
  }

  function bindArchive() {
    const refresh = el("archive-refresh-btn");
    if (refresh) refresh.addEventListener("click", loadArchive);
    const save = labEl("lab-archive-btn");
    if (save) save.addEventListener("click", saveLabToArchive);

    // Importa: file scaricato da un altro account via "Condividi" — lo si
    // manda cosi' com'e' al server, che ricrea la voce e segna le metriche
    // come non verificate qui (1c2880d2).
    const importBtn = el("archive-import-btn");
    const importFile = el("archive-import-file");
    if (importBtn && importFile) {
      importBtn.addEventListener("click", () => importFile.click());
      importFile.addEventListener("change", async () => {
        const file = importFile.files[0];
        importFile.value = "";
        if (!file) return;
        try {
          const data = JSON.parse(await file.text());
          const resp = await fetch("/api/archive/import", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
          });
          if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Error ${resp.status}`);
          }
          loadArchive();
        } catch (err) {
          alert("Couldn't import: " + err.message);
        }
      });
    }
  }

  // ── Ottimizzazione seguita in diretta ──────────────────────────────────────
  //
  // L'errore arrivato sulla bacheca — "The string did not match the expected
  // pattern" — e' Safari che prova a leggere come JSON una pagina d'errore:
  // la richiesta lunga era caduta prima di rispondere. Ora la ricerca e' un
  // lavoro che il server porta avanti per conto suo e di cui qui si chiede lo
  // stato, quindi non c'e' piu' nessuna richiesta lunga da far cadere.

  // Piu' ricerche insieme, ognuna con la sua storia. Il lavoro vive sul
  // server: chiudere la finestra non lo ferma e non deve nemmeno farlo
  // sparire di vista, altrimenti l'unico modo di sapere a che punto e' era
  // tenere aperta una finestra per nove minuti.
  const optJobs = new Map();   // id -> {id, title, sub, state, elapsed, log, seen, error, result, applied}
  // Quanti giri di polling consecutivi falliti si accettano (503 di un
  // deploy, un timeout) prima di arrendersi davvero e segnare il lavoro
  // come fallito lato client — vedi pollOnce().
  const _POLL_MAX_FAILURES = 5;
  let optViewing = null;       // quale lavoro sta guardando la finestra
  let optTimer = null;

  // Una risposta non-JSON non deve arrivare a JSON.parse: il messaggio che ne
  // esce parla di stringhe e non dice nulla di cosa e' andato storto.
  async function readJson(resp) {
    const text = await resp.text();
    try {
      return JSON.parse(text);
    } catch {
      const head = text.trim().slice(0, 120);
      throw new Error(
        `The server responded ${resp.status} ${resp.statusText || ""} without JSON`
        + (head ? ` — "${head}"` : "")
      );
    }
  }

  function optRunning() {
    return [...optJobs.values()].filter((j) => j.state === "in corso");
  }

  function renderOptPill() {
    const pill = el("opt-pill");
    if (!pill) return;
    const running = optRunning();
    const done = [...optJobs.values()].filter((j) => j.state !== "in corso" && !j.seenDone);
    if (!running.length && !done.length) { pill.classList.add("hidden"); return; }

    if (running.length) {
      const secs = Math.max(...running.map((j) => j.elapsed || 0));
      pill.className = "opt-pill";
      pill.innerHTML = `<span class="op-spin" aria-hidden="true"></span>`
        + `<span class="op-text">${running.length === 1 ? "1 search" : running.length + " searches"} · `
        + `${Math.floor(secs / 60)}:${String(Math.floor(secs % 60)).padStart(2, "0")}</span>`;
      pill.title = running.map((j) => j.sub).join(" · ");
    } else {
      const failed = done.filter((j) => j.state === "fallito").length;
      const stopped = done.filter((j) => j.state === "annullato").length;
      const kind = failed ? "failed" : stopped ? "" : "done";
      pill.className = "opt-pill " + kind;
      pill.innerHTML = `<span class="op-mark">${failed ? "✕" : stopped ? "◼" : "✓"}</span>`
        + `<span class="op-text">${failed ? "search failed"
          : stopped ? "search stopped" : "search done"}</span>`;
    }
    pill.classList.remove("hidden");
  }

  // ── La ricerca stabile, disegnata ───────────────────────────────────────────
  //
  // Solo per la modalita' "stabile" (plateau_search): e' l'unica che scrive nel
  // log le cinque fasi di cui parla — confini, griglia, apertura guidata,
  // scuotimento, scelta. Il log gia' le dice a parole; qui sono le stesse
  // frasi, lette e disegnate, non un secondo canale dal server. Il disegno
  // gira su un ciclo continuo (particelle, impulsi, aloni che respirano):
  // e' quello che rende "viva" un'attesa che altrimenti sarebbe un elenco di
  // righe. Stilizzata di proposito: il log non manda il punteggio di ogni
  // singola cella, quindi l'apertura si vede come un campo che si accende via
  // via che le celle vengono aperte (celle aperte / celle distinte, numeri
  // veri), non come un terreno con un rilievo — quello richiederebbe il
  // server a mandare coordinate che oggi non manda, e sarebbe inventarsele.
  // Lo scuotimento e la scelta invece sono per intero numeri veri: li' il log
  // gia' porta rendimento, trade e quante volte un finalista regge.
  const plateauAnim = {
    canvas: null, ctx: null, raf: null, t0: null,
    totalAxes: 0, axes: [], axisBusy: 0, gridCells: 0, budget: 0,
    openedSoFar: 0, distinctSoFar: 0, openedFinal: 0, distinctFinal: 0,
    finalistsExpected: 0, probeSamples: 0, finalists: [], picked: null,
  };

  function plateauAnimReset() {
    Object.assign(plateauAnim, {
      totalAxes: 0, axes: [], axisBusy: 0, gridCells: 0, budget: 0,
      openedSoFar: 0, distinctSoFar: 0, openedFinal: 0, distinctFinal: 0,
      finalistsExpected: 0, probeSamples: 0, finalists: [], picked: null,
    });
  }

  // Un generatore deterministico: la stessa stringa da' sempre la stessa
  // sequenza. Serve a disegnare forme che sembrano libere (il tracciato a
  // gradini di un asse, la disposizione delle particelle) senza che
  // ridisegnare lo stesso stato — un ridimensionamento, un riapertura della
  // finestra — le faccia saltare in un'altra posizione.
  function plateauSeed(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  function plateauRng(seed) {
    let s = seed >>> 0;
    return function () {
      s = (s + 0x6d2b79f5) | 0;
      let t = Math.imul(s ^ (s >>> 15), 1 | s);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // Le frasi sono quelle scritte da plateau.py — vedi say(...) li' dentro.
  // Un parametro che ne cambiasse la forma va cambiato in entrambi i posti.
  function plateauAnimParseLine(m) {
    let mm;
    if ((mm = /^mapping boundaries on (\d+) axes/.exec(m))) {
      plateauAnim.totalAxes = +mm[1];
    } else if ((mm = /^axis (.+?): (\d+) boundar\w+ \S+ (\d+) interval\w* \((\d+) backtests\)/.exec(m))) {
      plateauAnim.axes.push({ name: mm[1], boundaries: +mm[2], cells: +mm[3], usedBt: +mm[4] });
      plateauAnim.axisBusy = 0;   // quell'asse e' chiuso, si riparte da zero sul prossimo
    } else if ((mm = /^axis .+?: still working \S+ (\d+) backtests so far/.exec(m))) {
      // Un asse pesante puo' metterci decine di secondi prima della riga che
      // lo chiude: senza questa, il pannello restava fermo su "asse N/tot"
      // senza dire nulla — sembrava bloccato. Non e' un asse in piu', e'
      // quanto si e' gia' lavorato su quello ancora aperto.
      plateauAnim.axisBusy = +mm[1];
    } else if ((mm = /= (\d+) cells(?:\s|$)/.exec(m)) && m.startsWith("grid:")) {
      plateauAnim.gridCells = +mm[1];
    } else if ((mm = /^(\d+) cells over the budget of (\d+):/.exec(m))) {
      plateauAnim.gridCells = +mm[1];
      plateauAnim.budget = +mm[2];
    } else if ((mm = /^trying the center of (\d+) cells \(all enumerated\)/.exec(m))) {
      plateauAnim.budget = +mm[1];
    } else if ((mm = /^cells (\d+) \S+ (\d+) distinct configurations so far/.exec(m))) {
      plateauAnim.openedSoFar = +mm[1];
      plateauAnim.distinctSoFar = +mm[2];
    } else if ((mm = /^(\d+) distinct configurations over (\d+) cells tried/.exec(m))) {
      plateauAnim.distinctFinal = +mm[1];
      plateauAnim.openedFinal = +mm[2];
    } else if ((mm = /shaking (\d+) with (\d+) random shifts/.exec(m))) {
      plateauAnim.finalistsExpected = +mm[1];
      plateauAnim.probeSamples = +mm[2];
    } else if ((mm = /^finalist (\d+)\/(\d+): holds (\d+) times? out of (\d+) \S+ ([+-][\d.]+)% over (\d+) trades/.exec(m))) {
      plateauAnim.finalists.push({
        rank: +mm[1], total: +mm[2], agreeN: +mm[3], agreeTotal: +mm[4],
        ret: parseFloat(mm[5]), trades: +mm[6],
      });
    } else if ((mm = /^picked: ([+-][\d.]+)% over (\d+) trades, stable (\d+)% of the time/.exec(m))) {
      plateauAnim.picked = { ret: parseFloat(mm[1]), trades: +mm[2], stablePct: +mm[3] };
    }
  }

  function plateauAnimFeed(lines) {
    if (!lines || !lines.length) return;
    lines.forEach((line) => plateauAnimParseLine(line.m));
    // Il disegno non parte da qui: gira per conto suo (plateauAnimLoop), cosi'
    // le particelle e gli aloni continuano a muoversi anche nei secondi fra
    // una riga di log e la prossima invece di restare fermi in attesa.
  }

  function plateauAnimAct() {
    if (plateauAnim.picked) return 4;
    if (plateauAnim.finalists.length || plateauAnim.finalistsExpected) return 3;
    if (plateauAnim.gridCells && !plateauAnim.openedFinal) return 2;
    if (plateauAnim.gridCells) return 1;
    return 0;
  }

  function plateauAnimTheme() {
    const cs = getComputedStyle(document.documentElement);
    const g = (n) => cs.getPropertyValue(n).trim();
    // --accent NON e' usato qui: in tema chiaro l'app lo tiene nero (e' il
    // colore dei pulsanti, non un colore di dato). --bull e' verde in
    // entrambi i temi ed e' gia' il colore che l'app usa per "sale/va bene".
    return {
      ink: g("--ink"), dim: g("--ink-dim"), bull: g("--bull"), bear: g("--bear"),
      border: g("--border"), raised: g("--bg-raised"), panel: g("--bg-panel"),
      dark: document.documentElement.getAttribute("data-theme") === "dark",
    };
  }

  function plateauShade(hex, amt) {
    // hex e' un valore CSS qualunque (var risolta) — se non e' #rrggbb lo
    // restituisce com'e', va bene anche senza scurirlo.
    const m = /^#([0-9a-f]{6})$/i.exec(hex.trim());
    if (!m) return hex;
    const n = parseInt(m[1], 16);
    const clamp = (v) => Math.max(0, Math.min(255, v));
    const r = clamp(((n >> 16) & 255) + amt), gg = clamp(((n >> 8) & 255) + amt), b = clamp((n & 255) + amt);
    return `rgb(${r},${gg},${b})`;
  }

  function plateauAlpha(hex, a) {
    const m = /^#([0-9a-f]{6})$/i.exec(hex.trim());
    if (!m) return hex;
    const n = parseInt(m[1], 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  }

  // Un alone morbido: un cerchio pieno con un bordo che sfuma verso
  // trasparente. E' il mattone di tutta l'estetica "particelle" — un punto
  // acceso, un impulso, il bagliore dietro un numero.
  function plateauGlow(ctx, x, y, r, color, alpha, dark) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, plateauAlpha(color, alpha));
    g.addColorStop(1, plateauAlpha(color, 0));
    if (dark) { ctx.save(); ctx.globalCompositeOperation = "lighter"; }
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
    if (dark) ctx.restore();
  }

  // Un anello che si espande e sfuma — l'impulso sonar/battito che ricorre
  // in piu' atti (l'asse ancora al lavoro, il finalista scosso, la scelta).
  // `phase` in [0,1): 0 = appena nato, 1 = appena svanito.
  function plateauRing(ctx, x, y, rMax, phase, color, width, dark) {
    const r = 4 + rMax * phase;
    const alpha = (1 - phase) * 0.55;
    if (alpha <= 0.01) return;
    if (dark) { ctx.save(); ctx.globalCompositeOperation = "lighter"; }
    ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832);
    ctx.strokeStyle = plateauAlpha(color, alpha);
    ctx.lineWidth = width || 1.4;
    ctx.stroke();
    if (dark) ctx.restore();
  }

  const easeOut = (x) => 1 - Math.pow(1 - Math.min(Math.max(x, 0), 1), 3);
  const clamp01 = (x) => Math.min(Math.max(x, 0), 1);

  // Il campo di sfondo: una manciata di puntini fiochi che respirano piano.
  // Costa pochissimo e da' subito la sensazione che qualcosa sia vivo, anche
  // nell'istante prima che arrivi la prima riga di log.
  const PLATEAU_FIELD = (() => {
    const rng = plateauRng(plateauSeed("campo"));
    return Array.from({ length: 46 }, () => ({ fx: rng(), fy: rng(), ph: rng() * 6.283, sp: 0.4 + rng() * 0.5 }));
  })();

  function plateauField(ctx, W, H, t, T) {
    PLATEAU_FIELD.forEach((p) => {
      const a = 0.10 + 0.10 * (0.5 + 0.5 * Math.sin(t / 1000 * p.sp + p.ph));
      ctx.beginPath();
      ctx.arc(p.fx * W, p.fy * H, 1.1, 0, 6.2832);
      ctx.fillStyle = plateauAlpha(T.dim.startsWith("#") ? T.dim : "#888888", a);
      ctx.fill();
    });
  }

  // ── Atto 1: i confini — ogni asse e' un canale che traccia dove il
  // risultato cambia, come un tracciato che si aggiorna dal vivo. E' quello
  // che l'algoritmo fa per davvero: percorrere l'asse e segnare i gradini. ──
  function plateauStepPath(seedStr, steps, x0, x1, yMid, amp) {
    const rng = plateauRng(plateauSeed(seedStr));
    const n = Math.max(1, steps);
    const xs = [x0];
    for (let i = 1; i < n; i++) xs.push(x0 + (x1 - x0) * (i / n));
    xs.push(x1);
    let level = rng() > 0.5 ? 1 : -1;
    const pts = [];
    for (let i = 0; i < xs.length - 1; i++) {
      const y = yMid + level * amp * (0.4 + 0.6 * rng());
      pts.push([xs[i], y], [xs[i + 1], y]);
      level = -level;
    }
    return pts;
  }

  function plateauActBoundaries(ctx, W, H, t, T, pad) {
    const label = `The bounds — axis ${plateauAnim.axes.length}/${plateauAnim.totalAxes || "?"}`;
    ctx.font = `500 10px var(--font-mono)`; ctx.fillStyle = T.dim;
    ctx.textAlign = "left"; ctx.textBaseline = "top";
    ctx.fillText(label, pad, 6);

    const lanes = Math.max(plateauAnim.totalAxes, plateauAnim.axes.length + 1, 3);
    const top = 26, bottom = H - 10;
    const laneH = Math.min(30, (bottom - top) / lanes);
    const x0 = pad, x1 = W - pad - 78;

    for (let i = 0; i < lanes; i++) {
      const y = top + i * laneH + laneH / 2;
      const axis = plateauAnim.axes[i];
      const isBusy = !axis && i === plateauAnim.axes.length && plateauAnim.axisBusy > 0;

      ctx.strokeStyle = T.border; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();

      if (axis) {
        const pts = plateauStepPath(axis.name, Math.max(axis.cells, 2), x0, x1, y, laneH * 0.32);
        ctx.beginPath();
        ctx.strokeStyle = T.bull; ctx.lineWidth = 1.6;
        if (T.dark) { ctx.shadowColor = T.bull; ctx.shadowBlur = 6; }
        pts.forEach(([px, py], k) => (k === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)));
        ctx.stroke();
        ctx.shadowBlur = 0;
        // una scintilla che ripercorre il tracciato in loop — il "sto
        // ancora leggendo questo asse", anche a mappatura gia' fatta.
        const period = 2600 + (i % 3) * 400;
        const along = ((t + i * 700) % period) / period;
        const segIdx = Math.min(pts.length - 2, Math.floor(along * (pts.length - 1)));
        const segT = along * (pts.length - 1) - segIdx;
        const hx = pts[segIdx][0] + (pts[segIdx + 1][0] - pts[segIdx][0]) * segT;
        const hy = pts[segIdx][1] + (pts[segIdx + 1][1] - pts[segIdx][1]) * segT;
        plateauGlow(ctx, hx, hy, 7, T.bull, T.dark ? 0.9 : 0.55, T.dark);
        ctx.beginPath(); ctx.arc(hx, hy, 2, 0, 6.2832); ctx.fillStyle = T.bull; ctx.fill();

        ctx.font = "400 9px var(--font-mono)"; ctx.fillStyle = T.dim;
        ctx.textAlign = "left"; ctx.textBaseline = "middle";
        ctx.fillText(`${axis.name.length > 9 ? axis.name.slice(0, 8) + "…" : axis.name} · ${axis.cells}`, x1 + 6, y);
      } else if (isBusy) {
        const scan = 0.5 + 0.5 * Math.sin(t / 420);
        const sx = x0 + (x1 - x0) * (0.5 + 0.46 * Math.sin(t / 900));
        plateauGlow(ctx, sx, y, 8 + 3 * scan, T.bull, T.dark ? 0.7 : 0.4, T.dark);
        ctx.beginPath(); ctx.arc(sx, y, 2.4, 0, 6.2832); ctx.fillStyle = T.bull; ctx.fill();
        ctx.font = "400 9px var(--font-mono)"; ctx.fillStyle = T.bull;
        ctx.textAlign = "left"; ctx.textBaseline = "middle";
        ctx.fillText(`${plateauAnim.axisBusy} bt · working…`, x1 + 6, y);
      } else {
        ctx.font = "400 9px var(--font-mono)"; ctx.fillStyle = T.border;
        ctx.textAlign = "left"; ctx.textBaseline = "middle";
        ctx.fillText("waiting", x1 + 6, y);
      }
    }
  }

  // ── Atto 2: la griglia — un battito che annuncia quante combinazioni ci
  // sono, prima di aprirle una per una. ──
  function plateauActGrid(ctx, W, H, t, T) {
    const cx = W / 2, cy = H / 2 - 4;
    for (let i = 0; i < 3; i++) {
      const phase = ((t / 1600) + i / 3) % 1;
      plateauRing(ctx, cx, cy, Math.min(W, H) * 0.42, phase, T.bull, 1.4, T.dark);
    }
    plateauGlow(ctx, cx, cy, 46, T.bull, T.dark ? 0.22 : 0.10, T.dark);
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = "700 21px var(--font-mono)"; ctx.fillStyle = T.ink;
    ctx.fillText(plateauAnim.gridCells.toLocaleString("en-US") + " cells", cx, cy - 8);
    ctx.font = "400 10px var(--font-mono)"; ctx.fillStyle = T.dim;
    ctx.fillText(plateauAnim.budget
      ? `budget of ${plateauAnim.budget.toLocaleString("en-US")} backtests`
      : "all tried", cx, cy + 15);
  }

  // ── Atto 3: l'apertura guidata — una spirale che si accende dal centro
  // verso fuori, nell'ordine in cui le celle vengono davvero aperte
  // (best-first: si parte da poche partenze e ci si espande verso il
  // promettente). L'angolo aureo la fa leggere come cresciuta, non piazzata. ──
  const PLATEAU_GOLDEN = 2.399963229728653;

  function plateauActOpen(ctx, W, H, t, T) {
    ctx.font = "500 10px var(--font-mono)"; ctx.fillStyle = T.dim;
    ctx.textAlign = "left"; ctx.textBaseline = "top";
    ctx.fillText("Guided expansion", 14, 6);
    ctx.textAlign = "right";
    ctx.fillText(`${plateauAnim.gridCells.toLocaleString("en-US")} cells · budget `
      + `${(plateauAnim.budget || plateauAnim.gridCells).toLocaleString("en-US")}`, W - 14, 6);
    ctx.textAlign = "left";

    const budget = plateauAnim.budget || plateauAnim.gridCells || 1;
    const opened = plateauAnim.openedSoFar || 0;
    const frac = clamp01(opened / budget);
    const distinctFrac = opened ? plateauAnim.distinctSoFar / opened : 0;

    const total = 220;
    const cx = W / 2, cy = H / 2 + 6;
    const scale = Math.min(W, H) * 0.052;
    const litCount = Math.round(total * frac);

    for (let k = 0; k < total; k++) {
      const ang = k * PLATEAU_GOLDEN;
      const r = scale * Math.sqrt(k);
      const x = cx + r * Math.cos(ang), y = cy + r * Math.sin(ang);
      if (x < 2 || x > W - 2 || y < 22 || y > H - 4) continue;
      const lit = k < litCount;
      const bright = lit && (k / Math.max(litCount, 1)) < distinctFrac;
      if (!lit) {
        ctx.beginPath(); ctx.arc(x, y, 1, 0, 6.2832);
        ctx.fillStyle = T.border; ctx.fill();
        continue;
      }
      const isNewest = k === litCount - 1;
      const size = bright ? 2.6 : 1.7;
      if (bright || isNewest) plateauGlow(ctx, x, y, isNewest ? 12 : 6, T.bull, T.dark ? 0.55 : 0.3, T.dark);
      ctx.beginPath(); ctx.arc(x, y, size, 0, 6.2832);
      ctx.fillStyle = bright ? T.bull : plateauShade(T.bull, T.dark ? -10 : 70);
      ctx.fill();
      if (isNewest) {
        const pulse = 0.5 + 0.5 * Math.sin(t / 220);
        ctx.beginPath(); ctx.arc(x, y, 4 + pulse * 3, 0, 6.2832);
        ctx.strokeStyle = plateauAlpha(T.bull, 0.6); ctx.lineWidth = 1.2; ctx.stroke();
      }
    }

    ctx.font = "400 10px var(--font-mono)"; ctx.fillStyle = T.ink;
    ctx.fillText(`${opened.toLocaleString("en-US")} cells opened`, 14, H - 26);
    ctx.fillStyle = T.bull;
    ctx.fillText(`${plateauAnim.distinctSoFar.toLocaleString("en-US")} distinct configurations`, 14, H - 12);
  }

  // ── Atti 4-5: lo scuotimento e la scelta — orbite di puntini veri (verdi
  // quanto ha retto, rossi quanto no) intorno a ogni finalista. ──
  function plateauActShakeAndPick(ctx, W, H, t, T, act) {
    const title = act === 4 ? "The pick" : "The shake-out";
    ctx.font = "500 10px var(--font-mono)"; ctx.fillStyle = T.dim;
    ctx.textAlign = "left"; ctx.textBaseline = "top";
    ctx.fillText(title, 14, 6);

    const list = plateauAnim.finalists;
    const n = Math.max(list.length, plateauAnim.finalistsExpected, 1);
    const pad = 20, top = 30, bottom = H - 24;
    const slotW = (W - pad * 2) / n;
    const maxRet = Math.max(1, ...list.map((f) => Math.abs(f.ret)));

    list.forEach((f, i) => {
      const isPicked = act === 4 && plateauAnim.picked
        && Math.abs(f.ret - plateauAnim.picked.ret) < 0.05 && f.trades === plateauAnim.picked.trades;
      const isActive = i === list.length - 1 && act === 3;
      const cx = pad + slotW * (i + 0.5);
      const cy = top + (bottom - top) * (1 - clamp01(Math.abs(f.ret) / maxRet) * 0.82) - (bottom - top) * 0.06;
      const baseR = 5 + 5 * clamp01(Math.abs(f.ret) / maxRet);
      const r = isPicked ? baseR + 3 + Math.sin(t / 260) * 1.4 : baseR;
      const color = isPicked || isActive ? T.bull : T.border;

      if (isPicked) {
        for (let k = 0; k < 3; k++) {
          const phase = ((t / 1100) + k / 3) % 1;
          plateauRing(ctx, cx, cy, 30, phase, T.bull, 1.3, T.dark);
        }
        plateauGlow(ctx, cx, cy, 26, T.bull, T.dark ? 0.32 : 0.16, T.dark);
      } else if (isActive) {
        const phase = (t / 900) % 1;
        plateauRing(ctx, cx, cy, 20, phase, T.bull, 1.1, T.dark);
      }

      // Le orbite: puntini veri, uno per spostamento, verde se il finalista
      // ha retto quella volta, rosso se no — sono i numeri dello scuotimento,
      // non una stima. Quelli rossi, sul finalista attivo, si allontanano
      // invece di stare fermi: e' l'unico modo di "vedere" un fallimento.
      const dotN = f.agreeTotal || 0;
      for (let d = 0; d < dotN; d++) {
        const spin = isActive || isPicked ? t / (isPicked ? 5200 : 2600) : 0;
        const ang = (d / dotN) * 6.2832 + spin;
        const survived = d < f.agreeN;
        const orbit = r + 8 + (survived ? 0 : (isActive ? 10 * clamp01((t % 2600) / 2600) : 8));
        const dx = cx + Math.cos(ang) * orbit, dy = cy + Math.sin(ang) * orbit * 0.62;
        const fade = survived ? 1 : (isActive ? 1 - clamp01((t % 2600) / 2600) * 0.7 : 0.45);
        ctx.beginPath(); ctx.arc(dx, dy, 1.5, 0, 6.2832);
        ctx.fillStyle = plateauAlpha(survived ? T.bull : T.bear, fade);
        ctx.fill();
      }

      ctx.beginPath(); ctx.arc(cx, cy, r, 0, 6.2832);
      ctx.fillStyle = color; ctx.fill();

      ctx.font = "400 9px var(--font-mono)"; ctx.fillStyle = T.dim;
      ctx.textAlign = "center"; ctx.textBaseline = "top";
      ctx.fillText(`${f.ret >= 0 ? "+" : ""}${f.ret.toFixed(0)}%`, cx, bottom + 4);
    });

    if (act === 4 && plateauAnim.picked) {
      ctx.font = "600 11px var(--font-mono)"; ctx.fillStyle = T.ink;
      ctx.textAlign = "right"; ctx.textBaseline = "top";
      ctx.fillText(`stable ${plateauAnim.picked.stablePct}% of the time`, W - 14, 6);
    }
    ctx.textAlign = "left"; ctx.textBaseline = "top";
    ctx.fillStyle = T.border;
    ctx.fillRect(pad, bottom, W - pad * 2, 1);
  }

  function plateauAnimDraw(now) {
    const canvas = plateauAnim.canvas;
    if (!canvas || canvas.classList.contains("hidden")) return;
    const ctx = plateauAnim.ctx;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = canvas.clientWidth || 600, H = canvas.clientHeight || 148;
    if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) {
      canvas.width = Math.round(W * dpr);
      canvas.height = Math.round(H * dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const T = plateauAnimTheme();
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = T.panel; ctx.fillRect(0, 0, W, H);

    if (plateauAnim.t0 === null) plateauAnim.t0 = now || performance.now();
    const t = (now || performance.now()) - plateauAnim.t0;

    plateauField(ctx, W, H, t, T);

    const act = plateauAnimAct();
    if (act === 0) plateauActBoundaries(ctx, W, H, t, T, 14);
    else if (act === 1) plateauActGrid(ctx, W, H, t, T);
    else if (act === 2) plateauActOpen(ctx, W, H, t, T);
    else plateauActShakeAndPick(ctx, W, H, t, T, act);
  }

  // Il ciclo gira solo mentre il pannello e' aperto su una ricerca stabile:
  // e' l'unico costo continuo di tutta questa roba, e uno solo, piccolo
  // canvas non pesa — ma non ha senso farlo girare quando non lo vede nessuno.
  function plateauAnimLoop(now) {
    plateauAnim.raf = null;
    if (!plateauAnim.canvas || plateauAnim.canvas.classList.contains("hidden")) return;
    plateauAnimDraw(now);
    plateauAnim.raf = requestAnimationFrame(plateauAnimLoop);
  }
  function plateauAnimStart() {
    if (plateauAnim.raf) return;
    plateauAnim.raf = requestAnimationFrame(plateauAnimLoop);
  }
  function plateauAnimStop() {
    if (plateauAnim.raf) { cancelAnimationFrame(plateauAnim.raf); plateauAnim.raf = null; }
  }

  function plateauAnimShow(job) {
    const canvas = el("opt-progress-anim");
    if (!canvas) return;
    plateauAnim.canvas = canvas;
    if (!plateauAnim.ctx) plateauAnim.ctx = canvas.getContext("2d");
    const isPlateau = job.mode === "plateau";
    canvas.classList.toggle("hidden", !isPlateau);
    if (!isPlateau) { plateauAnimStop(); return; }
    plateauAnimReset();
    plateauAnim.t0 = null;   // la prossima draw() la fissa di nuovo, per questa apertura
    plateauAnimFeed(job.log);
    plateauAnimStart();
  }

  function openOptProgress(jobId) {
    const job = optJobs.get(jobId);
    if (!job) return;
    optViewing = jobId;
    job.seenDone = true;
    el("opt-progress-title").textContent = job.title;
    // La ricerca gira sul server: chiudere questa finestra, la scheda o il
    // telefono non la ferma. Va detto, altrimenti si resta a guardare.
    el("opt-progress-sub").textContent = job.sub
      + " — you can close this: it keeps running on the server, an indicator stays at the bottom, "
      + "a summary arrives on Telegram. To keep the result, save it with Archive.";
    const list = el("opt-progress-log");
    list.innerHTML = "";
    appendOptLog(job.log);
    plateauAnimShow(job);
    el("opt-progress-time").textContent = `${Math.round(job.elapsed || 0)}s`;
    el("opt-progress").classList.remove("hidden", "done", "failed");
    el("opt-progress-stop").classList.toggle("hidden", job.state !== "in corso");
    if (job.state !== "in corso") optProgressFoot(job.footText, job.footKind);
    renderOptPill();
  }

  function closeOptProgress() {
    // Solo la finestra si chiude: il lavoro resta, e la pastiglia continua a
    // dire a che punto e'.
    el("opt-progress").classList.add("hidden");
    plateauAnimStop();
    optViewing = null;
    renderOptPill();
  }

  function appendOptLog(lines) {
    const list = el("opt-progress-log");
    lines.forEach((line) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="opt-t">${line.t.toFixed(1)}s</span>${escapeHtml(line.m)}`;
      list.appendChild(li);
    });
    // Solo se l'utente non ha scorso indietro a leggere: trascinargli via la
    // riga che sta guardando e' peggio che non seguire l'ultima.
    const nearBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 40;
    if (nearBottom) list.scrollTop = list.scrollHeight;
  }

  function optProgressFoot(text, kind) {
    const foot = el("opt-progress-foot");
    if (!foot || !text) return;
    foot.textContent = text;
    foot.className = "opt-progress-foot " + (kind || "");
    foot.classList.remove("hidden");
    el("opt-progress").classList.add(kind === "error" ? "failed" : "done");
  }

  function startOptPolling() {
    if (optTimer) return;
    const tick = async () => {
      const running = optRunning();
      if (!running.length) { optTimer = null; renderOptPill(); return; }
      await Promise.all(running.map(pollOnce));
      renderOptPill();
      optTimer = setTimeout(tick, 1000);
    };
    optTimer = setTimeout(tick, 600);
  }

  // Un lavoro si segue chiedendo solo le righe nuove: `since` e' quante se ne
  // hanno gia', cosi' ogni giro porta le novita' invece del log intero.
  //
  // Un intoppo di un solo giro (503 durante un deploy, un timeout di rete)
  // NON significa che la ricerca sul server sia morta — prima bastava un
  // giro sfortunato su nove minuti di polling per marcare "fallita" una
  // ricerca che sul server stava proseguendo tranquilla. Solo un 404 vero
  // (il job non c'e' piu' — il processo e' stato riavviato e la memoria
  // persa per davvero) e' un fallimento definitivo; qualunque altro errore
  // si accetta fino a _POLL_MAX_FAILURES giri consecutivi prima di arrendersi.
  async function pollOnce(job) {
    try {
      const resp = await fetch(`/api/jobs/${job.id}?since=${job.seen}`);
      if (resp.status === 404) {
        const body = await readJson(resp).catch(() => ({}));
        const err = new Error(body.detail || "Job not found or expired");
        err.terminal = true;
        throw err;
      }
      if (!resp.ok) {
        throw new Error(`Job unreachable (${resp.status})`);
      }
      job.pollFailures = 0;
      const data = await readJson(resp);
      job.seen = data.log_total;
      job.elapsed = data.elapsed_s;
      job.log.push(...(data.log || []));
      if (optViewing === job.id) {
        appendOptLog(data.log || []);
        if (job.mode === "plateau") plateauAnimFeed(data.log || []);
        el("opt-progress-time").textContent = `${Math.round(job.elapsed)}s`;
      }
      if (data.state === "annullato") {
        // Fermata apposta: non e' un fallimento e non va raccontata come tale.
        job.state = "annullato";
        job.footText = "Stopped.";
        job.footKind = "";
        job.seenDone = true;
        if (optViewing === job.id) {
          optProgressFoot(job.footText, job.footKind);
          el("opt-progress-stop").classList.add("hidden");
        }
      } else if (data.state === "finito") {
        job.state = "finito";
        job.result = data.result;
        // 15/10: nothing is archived on its own (13/10), so no "saved" here
        job.footText = "Done.";
        job.footKind = "ok";
        job.seenDone = optViewing === job.id;
        if (optViewing === job.id) optProgressFoot(job.footText, job.footKind);
        onOptFinished(job);
      } else if (data.state === "fallito") {
        job.state = "fallito";
        job.error = data.error || "Optimization failed";
        job.footText = job.error;
        job.footKind = "error";
        job.seenDone = optViewing === job.id;
        if (optViewing === job.id) optProgressFoot(job.footText, job.footKind);
        labEl("lab-status").textContent = "Optimization error: " + job.error;
        labEl("lab-status").classList.remove("hidden");
      }
    } catch (err) {
      job.pollFailures = (job.pollFailures || 0) + 1;
      if (!err.terminal && job.pollFailures < _POLL_MAX_FAILURES) {
        // Non definitivo, e non ancora troppi giri persi: il prossimo tick
        // (fra un secondo, vedi startOptPolling) riprova da solo — niente
        // scritto nel piede (quello segnala solo stati definitivi: farlo
        // qui marcherebbe la finestra come "fatta" o "fallita" per un
        // intoppo che al giro successivo potrebbe gia' essersi risolto).
        return;
      }
      job.state = "fallito";
      job.error = err.message || "Network error";
      job.footText = job.error;
      job.footKind = "error";
      if (optViewing === job.id) optProgressFoot(job.footText, job.footKind);
    }
  }

  // I risultati si applicano al Laboratorio solo se sta ancora guardando la
  // stessa cosa: con piu' ricerche in volo, sovrascrivere i campi con quelli
  // di un'altra coppia sarebbe peggio che non applicarli.
  function onOptFinished(job) {
    loadArchive();
    const body = job.result;
    if (!body) return;
    if (labState.symbol !== job.symbol || labState.strategy !== job.strategy) {
      // Nothing is archived on its own any more (13/10): the result lives in
      // the job, so the Lab offers to bring it back instead of losing it.
      const status = labEl("lab-status");
      status.textContent = `Search on ${job.symbol} finished while the Lab showed something else. `;
      const open = document.createElement("button");
      open.type = "button";
      open.className = "lab-status-link";
      open.textContent = "Open it";
      open.addEventListener("click", () => {
        labState.symbol = job.symbol;
        labState.displaySymbol = job.displaySymbol || job.symbol;
        if (job.assetType) labState.assetType = job.assetType;
        if (job.exchange) labState.exchange = job.exchange;
        labEl("lab-ticker-val").textContent = shortSymbol(job.symbol);
        const sel = labEl("lab-strategy-select");
        if (sel && sel.querySelector(`option[value="${job.strategy}"]`)) sel.value = job.strategy;
        labState.strategy = job.strategy;
        renderLabParamFields();
        onOptFinished(job);
      });
      status.appendChild(open);
      status.classList.remove("hidden");
      return;
    }
    const container = labEl("lab-params-fields");
    Object.entries(body.params).forEach(([key, value]) => {
      const input = container.querySelector(`[name="${key}"]`);
      if (!input) return;
      if (input.type === "checkbox") input.checked = !!value;
      else input.value = value;
    });
    labState.paramsDirty = true;
    labEl("lab-status").classList.add("hidden");
    renderLabResults(body.backtest);
    renderPlateauMap(body);
    renderBestTwo(body);
    renderDataUsed(body);
    renderRegimeBox(body);
    renderBranchBox(body);
  }

  // ── Diario degli ordini automatici ─────────────────────────────────────────
  //
  // La riga che sarebbe servita mesi fa: un segnale c'era, e l'ordine non e'
  // partito perche' le chiavi mancavano. Senza, i due casi — nessun segnale e
  // percorso morto — si vedevano identici, cioe' non si vedevano affatto.

  async function loadTradingJournal() {
    if (!state.user) return;
    const list = el("journal-list");
    if (!list) return;
    try {
      const resp = await fetch("/api/trading/journal");
      if (!resp.ok) return;
      const body = await resp.json();
      renderTradingJournal(body.items || []);
    } catch {
      list.innerHTML = '<li class="panel-hint">Order log unreachable.</li>';
    }
  }

  function renderTradingJournal(items) {
    const list = el("journal-list");
    const count = el("journal-count");
    if (!list) return;
    if (count) count.textContent = items.length ? String(items.length) : "";
    if (!items.length) {
      list.innerHTML = '<li class="panel-hint">No attempts recorded. With keys set up, every order shows up here — executed, failed or skipped, with the reason.</li>';
      return;
    }
    const when = (ts) => {
      const diff = Math.floor(Date.now() / 1000) - ts;
      if (diff < 60) return "now";
      if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
      if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
      return new Date(ts * 1000).toLocaleDateString("en-US", { day: "2-digit", month: "short" });
    };
    const mark = { eseguito: "✓", fallito: "✕", saltato: "–" };
    const pnlLabel = (e) => {
      if (e.pnl_pct == null) return "";
      const sign = e.pnl_pct >= 0 ? "+" : "";
      const cls = e.pnl_pct >= 0 ? "jr-pnl bull" : "jr-pnl bear";
      return `<span class="${cls}">${sign}${e.pnl_pct.toFixed(2)}%</span>`;
    };
    const priceLabel = (e) => {
      if (!e.price) return "";
      if (e.entry_price && e.exit_price == null) return `@ ${e.price}`;
      if (e.entry_price) return `${e.entry_price} → ${e.price}`;
      if (e.exit_price) return `→ ${e.price}`;
      return `@ ${e.price}`;
    };
    list.innerHTML = items.map((e) => `
      <li class="journal-row ${escapeHtml(e.outcome)}">
        <span class="jr-mark">${mark[e.outcome] || "·"}</span>
        <span class="jr-body">
          <span class="jr-head">${escapeHtml(e.symbol)} · ${escapeHtml(e.signal_type)} · ${escapeHtml(e.exchange)} <span class="jr-price">${priceLabel(e)}</span>${pnlLabel(e)}</span>
          <span class="jr-detail">${escapeHtml(strategyLabel(e.strategy_name))}${e.detail ? " — " + escapeHtml(e.detail) : ""}</span>
        </span>
        <span class="jr-when">${when(e.ts)}</span>
      </li>`).join("");
  }

  function bindTradingJournal() {
    const btn = el("journal-refresh-btn");
    if (btn) btn.addEventListener("click", loadTradingJournal);
  }

  // ── Alert log ──────────────────────────────────────────────────────────────

  let _alertLogLastTs = 0;
  let _alertLogPollTimer = null;

  async function loadAlertLog() {
    if (!state.user) return;
    try {
      const resp = await fetch("/api/alerts/log?limit=100");
      if (!resp.ok) return;
      const entries = await resp.json();
      renderAlertLog(entries);
      if (entries.length) _alertLogLastTs = entries[0].ts; // newest first
    } catch { /* ignore */ }
  }

  function renderAlertLog(entries) {
    const container = el("alert-log-list");
    if (!container) return;
    if (!entries.length) {
      container.innerHTML = '<li class="panel-hint">No alerts sent yet.</li>';
      return;
    }
    const fmtTs = (ts) => {
      const diff = Math.floor(Date.now() / 1000) - ts;
      if (diff < 60) return "Now";
      if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
      if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
      return new Date(ts * 1000).toLocaleDateString("en-US", { day: "2-digit", month: "short" });
    };
    const icon = (type) => {
      if (type.includes("long") || type.includes("above")) return "▲";
      if (type.includes("short") || type.includes("below")) return "▼";
      return "◆";
    };
    const cls = (type) => (type.includes("long") || type.includes("above")) ? "bull" : "bear";
    container.innerHTML = entries.map(e => `
      <li class="alert-log-row">
        <span class="al-icon ${cls(e.signal_type)}">${icon(e.signal_type)}</span>
        <span class="al-body">
          <span class="al-symbol">${e.symbol}</span>
          <span class="al-strat">${escapeHtml(strategyLabel(e.strategy_name))} · ${e.interval}</span>
          <span class="al-label">${e.label}</span>
        </span>
        <span class="al-time">${fmtTs(e.ts)}</span>
      </li>`).join("");
  }

  async function clearAlertLog() {
    await fetch("/api/alerts/log", { method: "DELETE" });
    renderAlertLog([]);
  }

  function startAlertLogPoll() {
    if (_alertLogPollTimer) return;
    _alertLogPollTimer = setInterval(async () => {
      if (!state.user) return;
      try {
        const resp = await fetch(`/api/alerts/log?limit=20&since=${_alertLogLastTs}`);
        if (!resp.ok) return;
        const fresh = await resp.json();
        if (!fresh.length) return;
        _alertLogLastTs = fresh[0].ts;
        // Show in-app toast for each new alert
        fresh.forEach(e => showAlertToast(e));
        // Reload the full log if the tab is visible
        const logEl = el("alert-log-list");
        if (logEl && !logEl.closest(".hidden") && document.visibilityState !== "hidden") {
          loadAlertLog();
        }
        // Browser push notification
        if (Notification.permission === "granted" && el("strategy-notify-toggle")?.checked) {
          fresh.forEach(e => {
            try {
              new Notification(`${e.symbol} — ${e.label}`, {
                body: `${strategyLabel(e.strategy_name)} · ${e.interval}`,
                icon: "/favicon.ico",
              });
            } catch { /* ignore */ }
          });
        }
      } catch { /* ignore */ }
    }, 30000);
  }

  function showAlertToast(e) {
    const container = el("alert-toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    const isBull = e.signal_type.includes("long") || e.signal_type.includes("above");
    toast.className = `alert-toast ${isBull ? "bull" : "bear"}`;
    toast.innerHTML = `<b>${e.symbol}</b> ${e.label}<span class="toast-strat">${escapeHtml(strategyLabel(e.strategy_name))}</span>`;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add("fade-out"), 4500);
    setTimeout(() => toast.remove(), 5000);
  }

  // ── Price alerts ────────────────────────────────────────────────────────────

  async function loadPriceAlerts() {
    if (!state.user) return;
    try {
      const resp = await fetch("/api/price-alerts");
      if (!resp.ok) return;
      renderPriceAlerts(await resp.json());
    } catch { /* ignore */ }
  }

  function renderPriceAlerts(alerts) {
    const container = el("price-alerts-list");
    if (!container) return;
    if (!alerts.length) {
      container.innerHTML = '<li class="panel-hint">No price alerts set up.</li>';
      return;
    }
    const fmtTs = (ts) => ts ? new Date(ts * 1000).toLocaleString("en-US", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—";
    container.innerHTML = alerts.map(a => {
      const dirLabel = a.condition === "crosses_above" ? "▲ above" : "▼ below";
      const dirCls = a.condition === "crosses_above" ? "bull" : "bear";
      const statusBadge = !a.active ? '<span class="pa-badge inactive">inactive</span>' : a.once_only ? '<span class="pa-badge once">once</span>' : '<span class="pa-badge repeat">repeating</span>';
      const lastTrig = a.last_triggered ? `Triggered: ${fmtTs(a.last_triggered)}` : "Never triggered";
      return `<li class="pa-card ${a.active ? "" : "pa-inactive"}" data-id="${a.id}">
        <div class="pa-head">
          <span class="pa-symbol">${a.symbol}</span>
          <span class="${dirCls} pa-dir">${dirLabel}</span>
          <span class="pa-price">${a.price.toLocaleString("en-US", { maximumFractionDigits: 6 })}</span>
          ${statusBadge}
        </div>
        ${a.note ? `<div class="pa-note">${a.note}</div>` : ""}
        <div class="pa-meta">${lastTrig}${a.trigger_count > 0 ? ` · ${a.trigger_count}× triggered` : ""}</div>
        <div class="pa-actions">
          <button class="pa-toggle-btn" data-id="${a.id}" data-active="${a.active}">${a.active ? "Disable" : "Re-enable"}</button>
          <button class="pa-del-btn" data-id="${a.id}">✕</button>
        </div>
      </li>`;
    }).join("");

    container.querySelectorAll(".pa-del-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const a = (alerts || []).find((x) => String(x.id) === btn.dataset.id);
        const what = a ? `the price alert on ${a.symbol} at ${a.price}` : "this price alert";
        if (!window.confirm(`Delete ${what}?`)) return;
        await fetch(`/api/price-alerts/${btn.dataset.id}`, { method: "DELETE" });
        loadPriceAlerts();
      });
    });
    container.querySelectorAll(".pa-toggle-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const active = btn.dataset.active === "true";
        await fetch(`/api/price-alerts/${btn.dataset.id}/active`, {
          method: "PATCH", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ active: !active }),
        });
        loadPriceAlerts();
      });
    });
  }

  function getSelectedIntervals() {
    return PRIMARY_TO_TRIAD[el("interval-primary").value];
  }

  function initCharts() {
    // TradingView's own mobile app keeps chart gridlines barely-there —
    // dense gridlines that read as "considered" on a wide desktop screen
    // just look busy/dated on a phone. Same hue, much lower opacity.
    const isMobile = window.matchMedia("(max-width: 760px)").matches;
    const chartGridColor = isMobile ? "rgba(255, 255, 255, 0.035)" : COLORS.gridMinor;
    const baseOptions = {
      layout: { background: { color: COLORS.paperBg }, textColor: COLORS.inkDim, fontFamily: "'JetBrains Mono', 'IBM Plex Mono', monospace" },
      grid: { vertLines: { color: chartGridColor }, horzLines: { color: chartGridColor } },
      // Larghezza minima uguale per tutte le scale: senza, il pannello con le
      // etichette più corte disegna un'area più larga e le sue barre non
      // cadono sotto quelle del prezzo.
      rightPriceScale: { borderColor: COLORS.gridMajor, minimumWidth: 72 },
      timeScale: { borderColor: COLORS.gridMajor, timeVisible: true, secondsVisible: false },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: { color: COLORS.inkDim, labelBackgroundColor: COLORS.ink },
        horzLine: { color: COLORS.inkDim, labelBackgroundColor: COLORS.ink },
      },
    };

    const mainContainer = el("main-chart");
    mainChart = LightweightCharts.createChart(mainContainer, baseOptions);
    candleSeries = mainChart.addCandlestickSeries({
      upColor: "rgba(0, 0, 0, 0)",
      downColor: COLORS.bear,
      borderVisible: true,
      borderUpColor: COLORS.bull,
      borderDownColor: COLORS.bear,
      wickUpColor: COLORS.bull,
      wickDownColor: COLORS.bear,
      // La proiezione del prezzo corrente fino all'asse, come su TradingView.
      // Il colore va detto: lasciato vuoto la libreria lo prende dal corpo
      // dell'ultima candela, e qui le candele rialziste sono vuote
      // (upColor trasparente, stile hollow) — quindi dopo una candela verde
      // la linea e' trasparente e l'etichetta del prezzo sparisce, che e'
      // esattamente quando serve.
      priceLineVisible: true,
      priceLineColor: COLORS.stamp,
      priceLineWidth: 1,
      priceLineStyle: LightweightCharts.LineStyle.Dashed,
      lastValueVisible: true,
    });
    observeResize(mainContainer, mainChart);

    const rsiContainer = el("rsi-chart");
    rsiChart = LightweightCharts.createChart(rsiContainer, baseOptions);
    rsiSeries = rsiChart.addLineSeries({ color: COLORS.rsi, lineWidth: 2, priceLineVisible: true, priceLineStyle: LightweightCharts.LineStyle.Dashed, priceLineWidth: 1, lastValueVisible: true });
    rsiSeries.createPriceLine({ price: 70, color: "rgba(255,69,96,0.45)", lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: "OB" });
    rsiSeries.createPriceLine({ price: 50, color: "rgba(110,120,134,0.35)", lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: false, title: "" });
    rsiSeries.createPriceLine({ price: 30, color: "rgba(0,214,143,0.45)", lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: "OS" });
    observeResize(rsiContainer, rsiChart);

    const macdContainer = el("macd-chart");
    macdChart = LightweightCharts.createChart(macdContainer, baseOptions);
    macdLineSeries = macdChart.addLineSeries({ color: COLORS.macd, lineWidth: 2, priceLineVisible: true, priceLineStyle: LightweightCharts.LineStyle.Dashed, priceLineWidth: 1, lastValueVisible: true });
    macdSignalSeries = macdChart.addLineSeries({ color: COLORS.macdSignal, lineWidth: 1 });
    macdHistSeries = macdChart.addHistogramSeries({ color: "rgba(91,156,246,0.3)" });
    macdLineSeries.createPriceLine({ price: 0, color: "rgba(110,120,134,0.5)", lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Solid, axisLabelVisible: false, title: "" });
    observeResize(macdContainer, macdChart);

    const stochContainer = el("stoch-chart");
    stochChart = LightweightCharts.createChart(stochContainer, baseOptions);
    stochKSeries = stochChart.addLineSeries({ color: COLORS.rsi, lineWidth: 2, priceLineVisible: true, priceLineStyle: LightweightCharts.LineStyle.Dashed, priceLineWidth: 1, lastValueVisible: true });
    stochDSeries = stochChart.addLineSeries({ color: COLORS.stamp, lineWidth: 1 });
    stochKSeries.createPriceLine({ price: 80, color: "rgba(255,69,96,0.45)", lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: "OB" });
    stochKSeries.createPriceLine({ price: 50, color: "rgba(110,120,134,0.35)", lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: false, title: "" });
    stochKSeries.createPriceLine({ price: 20, color: "rgba(0,214,143,0.45)", lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: "OS" });
    observeResize(stochContainer, stochChart);

    // Dragging or zooming a pane moves the price chart too, and through it
    // every other pane (6a8fdae8: "the RSI moves, the candles stay put").
    followPane(rsiChart, rsiContainer);
    followPane(macdChart, macdContainer);
    followPane(stochChart, stochContainer);

    makeSubChartResizable(rsiContainer, "rsi-chart");
    makeSubChartResizable(macdContainer, "macd-chart");
    makeSubChartResizable(stochContainer, "stoch-chart");

    // equity-chart panel removed — equityChart/equitySeries stay null
    equityChart = null;
    equitySeries = null;

    mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (!range) return;
      rangeSyncing = true;
      try {
        rsiChart.timeScale().setVisibleLogicalRange(range);
        macdChart.timeScale().setVisibleLogicalRange(range);
        stochChart.timeScale().setVisibleLogicalRange(range);
      } finally { rangeSyncing = false; }
      // customOscCharts si popola/svuota dinamicamente (vedi
      // refreshCustomIndicators) — questa callback e' registrata una sola
      // volta ma legge il contenuto corrente dell'oggetto ad ogni chiamata.
      rangeSyncing = true;
      Object.values(customOscCharts).forEach(({ chart }) => {
        try { chart.timeScale().setVisibleLogicalRange(range); } catch { /* in fase di rimozione */ }
      });
      rangeSyncing = false;
      repositionFractalLabels();
      // Zooming changes the labels, and with them the scale width.
      scheduleScaleAlign();
    });

    // Il valore dell'RSI va letto sul punto della curva, non dove capita il
    // cursore. L'etichetta della scala segue la y del puntatore, quindi
    // muovendo il mouse in verticale sulla stessa barra cambia il numero pur
    // restando lo stesso RSI: un valore che si legge cosi' non e' un valore.
    attachValueBadge(rsiChart, rsiContainer, rsiSeries, "RSI", COLORS.rsi);
    attachValueBadge(stochChart, stochContainer, stochKSeries, "%K", COLORS.rsi);

    mainChart.subscribeCrosshairMove(handleCrosshairMove);
    bindDrawClickCapture();
    bindChartContextMenu();
    bindMarkerClickPopup();
    bindCustomOverlayRemoval();
    bindBreakoutButton();
    initDrawCanvas();
    chartsReady = true;
  }

  // Chart-relative point + bar time as last reported by the library's own
  // crosshair tracking — proven correct (it drives the working tooltip),
  // unlike hand-computing offsets from a raw DOM pointer event's
  // clientX/clientY, which don't line up with what coordinateToPrice/
  // coordinateToTime expect. The drawing-tools click capture below reuses
  // this instead of recomputing its own coordinates.
  let lastCrosshairPoint = null;

  // Candle values under the cursor (board issue 229c5103): O/H/L/C plus the
  // change from the previous close, TradingView-style. With the cursor off
  // the chart the row shows the last candle, so it is never empty.
  let ohlcCandles = [];
  let ohlcIndex = new Map();
  let ohlcHoverTime = null;

  function setOhlcCandles(candles) {
    ohlcCandles = candles || [];
    ohlcIndex = new Map(ohlcCandles.map((c, i) => [c.time, i]));
    renderOhlc();
  }

  function noteOhlcCandle(candles) {
    // The live feed replaces or appends the last candle of the same array.
    if (candles !== ohlcCandles || !candles.length) return;
    ohlcIndex.set(candles[candles.length - 1].time, candles.length - 1);
    if (ohlcHoverTime === null) renderOhlc();
  }

  function renderOhlc() {
    const box = el("chart-ohlc");
    if (!box) return;
    if (!ohlcCandles.length) {
      box.classList.add("hidden");
      return;
    }
    let i = ohlcHoverTime !== null ? ohlcIndex.get(ohlcHoverTime) : undefined;
    if (i === undefined) i = ohlcCandles.length - 1;
    const c = ohlcCandles[i];
    const prev = i > 0 ? ohlcCandles[i - 1].close : c.open;
    const precision = pricePrecisionFor(c.close).precision;
    const f = (v) => Number(v).toFixed(precision);
    const diff = c.close - prev;
    const pct = prev ? (diff / prev) * 100 : 0;
    const cls = c.close >= c.open ? "up" : "down";
    const sign = diff >= 0 ? "+" : "";
    box.innerHTML =
      `<span>O <b class="${cls}">${f(c.open)}</b></span>` +
      `<span>H <b class="${cls}">${f(c.high)}</b></span>` +
      `<span>L <b class="${cls}">${f(c.low)}</b></span>` +
      `<span>C <b class="${cls}">${f(c.close)}</b></span>` +
      `<span class="${diff >= 0 ? "up" : "down"}">${sign}${f(diff)} (${sign}${pct.toFixed(2)}%)</span>`;
    box.classList.remove("hidden");
  }

  function handleCrosshairMove(param) {
    lastCrosshairPoint =
      param.point && param.time !== undefined ? { x: param.point.x, y: param.point.y, time: param.time } : null;
    ohlcHoverTime = lastCrosshairPoint ? param.time : null;
    renderOhlc();
    updateGhost();
    updateHandleDrag();
    updateDragPreview();
    updateFractalDrag();
    updateCursorHover();
    if (!param.point || param.time === undefined || !overlays.hitZones.length) {
      tooltipEl.classList.add("hidden");
      return;
    }
    const price = candleSeries.coordinateToPrice(param.point.y);
    if (price === null) {
      tooltipEl.classList.add("hidden");
      return;
    }
    const hit = overlays.hitZones.find(
      (z) => param.time >= z.start_time && param.time <= z.end_time && price <= z.price_high && price >= z.price_low
    );
    if (!hit) {
      tooltipEl.classList.add("hidden");
      return;
    }
    const rect = el("main-chart").getBoundingClientRect();
    tooltipEl.textContent = hit.label;
    tooltipEl.style.left = `${rect.left + param.point.x + 14}px`;
    tooltipEl.style.top = `${rect.top + param.point.y + 14}px`;
    tooltipEl.classList.remove("hidden");
  }

  // Etichetta ancorata al punto della serie sotto il crosshair — il "pallino"
  // che la libreria disegna sulla curva — invece che alla punta del cursore.
  // Segue la x del crosshair e la y del valore: e' il numero che quella barra
  // ha davvero, e resta fermo mentre il puntatore si muove in verticale.
  function attachValueBadge(chart, container, series, label, color) {
    if (!chart || !container || !series) return;
    if (getComputedStyle(container).position === "static") {
      container.style.position = "relative";
    }
    const badge = document.createElement("div");
    badge.className = "series-value-badge hidden";
    badge.style.borderColor = color;
    container.appendChild(badge);

    chart.subscribeCrosshairMove((param) => {
      const point = param.point;
      const data = param.seriesData ? param.seriesData.get(series) : null;
      const value = data ? (data.value !== undefined ? data.value : data.close) : null;
      if (!point || param.time === undefined || value === null || value === undefined) {
        badge.classList.add("hidden");
        return;
      }
      const y = series.priceToCoordinate(value);
      if (y === null) {
        badge.classList.add("hidden");
        return;
      }
      badge.textContent = `${label} ${value.toFixed(2)}`;
      badge.classList.remove("hidden");
      // Si sposta a sinistra del punto quando altrimenti uscirebbe dal
      // riquadro: un'etichetta tagliata a meta' e' peggio di nessuna.
      const w = badge.offsetWidth || 60;
      const left = point.x + 10 + w > container.clientWidth ? point.x - 10 - w : point.x + 10;
      badge.style.left = `${Math.max(2, left)}px`;
      badge.style.top = `${Math.max(2, Math.min(container.clientHeight - 20, y - 10))}px`;
    });
  }

  function clearOverlays() {
    overlays.lineSeries.forEach((s) => {
      try {
        s.chart.removeSeries(s.series);
      } catch (e) {
        /* series already gone */
      }
    });
    overlays.priceLines.forEach(({ series, line }) => {
      try {
        series.removePriceLine(line);
      } catch (e) {
        /* already removed */
      }
    });
    overlays.primitives.forEach(({ series, primitive }) => {
      try {
        series.detachPrimitive(primitive);
      } catch (e) {
        /* already removed */
      }
    });
    overlays.lineSeries = [];
    overlays.priceLines = [];
    overlays.primitives = [];
    overlays.hitZones = [];
  }

  // Una barra per candela, sempre — anche dove l'indicatore non ha ancora un
  // valore. Le barre di riscaldamento diventano punti vuoti ("whitespace"),
  // che la libreria accetta e non disegna.
  //
  // Saltarle sembrava innocuo e non lo era: i pannelli sotto il grafico sono
  // sincronizzati per INDICE logico, quindi una serie con meno punti fa
  // corrispondere l'indice N a una candela diversa e il pannello scivola
  // rispetto al prezzo. Con un RSI a 14 periodi lo scarto è di 14 barre, e si
  // vede a occhio sull'asse dei tempi.
  // The VWAP restarts every anchor period; a line joining the old period's
  // last value to the new one's first drew a vertical wall at each reset.
  // The segment into a period's first bar is drawn transparent (a whitespace
  // point does not break a line series in this chart library), so the line
  // breaks at the reset as on TradingView and every bar keeps its value.
  function vwapWithBreaks(candles, values, anchor) {
    const period = (t) => {
      const d = new Date(t * 1000);
      if (anchor === "Y") return d.getUTCFullYear();
      if (anchor === "M") return d.getUTCFullYear() * 12 + d.getUTCMonth();
      const day = Math.floor(t / 86400);
      return anchor === "W" ? Math.floor((day + 3) / 7) : day;   // weeks start on Monday
    };
    return seriesFromIndicatorValues(candles, values).map((p, i) =>
      (i > 0 && p.value != null && period(candles[i].time) !== period(candles[i - 1].time) ? { ...p, color: "rgba(0,0,0,0)" } : p));
  }

  function seriesFromIndicatorValues(candles, values) {
    const out = [];
    for (let i = 0; i < candles.length; i++) {
      const v = values[i];
      out.push(v === null || v === undefined || Number.isNaN(v)
        ? { time: candles[i].time }
        : { time: candles[i].time, value: v });
    }
    return out;
  }

  // Stessa cosa ma per gli indicatori custom (libreria pandas-ta), che
  // arrivano come due array paralleli (times/values) invece che gia' incollati
  // alle candele. Un punto "vuoto" (senza value) invece di ometterlo del tutto
  // e' quello che tiene l'indice logico allineato al grafico principale: se si
  // filtrano via i valori nulli del periodo di riscaldamento, la serie ha meno
  // punti delle candele e lo stesso indice logico smette di puntare alla
  // stessa data nei due grafici — la barra sincronizzata mostra un pezzo
  // diverso di storia in ciascuno (segnalato su ENTROPY e altri).
  function pointsFromTimesValues(times, values) {
    const out = [];
    for (let i = 0; i < times.length; i++) {
      const v = values[i];
      out.push(v === null || v === undefined || Number.isNaN(v)
        ? { time: times[i] }
        : { time: times[i], value: v });
    }
    return out;
  }

  function findIndicator(indicators, name) {
    const found = indicators.find((s) => s.name === name);
    return found ? found.values : null;
  }

  function addLineOverlay(chart, series, target, chartRef) {
    overlays.lineSeries.push({ chart: chartRef, series });
  }

  // TradingView shows a short code directly on each level's box (e.g.
  // "FVG", "Top Liq") rather than only on hover — the full descriptive
  // text stays in the hover tooltip (hitZones), this is just the
  // always-visible short form drawn on the chart itself.
  const LEVEL_SHORT_LABELS = { order_block: "OB", fvg: "FVG", eqh: "EQH", eql: "EQL", bos: "BOS", choch: "CHoCH" };

  function addRectangle(point1, point2, fillColor, borderColor, label, shortLabel, style) {
    const rect = new RectanglePrimitive(point1, point2, fillColor, borderColor, style);
    candleSeries.attachPrimitive(rect);
    overlays.primitives.push({ series: candleSeries, primitive: rect });
    if (shortLabel) {
      const topPoint = point1.price >= point2.price ? point1 : point2;
      const labelPrim = new TextPrimitive(topPoint, shortLabel, borderColor);
      candleSeries.attachPrimitive(labelPrim);
      overlays.primitives.push({ series: candleSeries, primitive: labelPrim });
    }
    if (label) {
      overlays.hitZones.push({
        price_low: Math.min(point1.price, point2.price),
        price_high: Math.max(point1.price, point2.price),
        start_time: Math.min(point1.time, point2.time),
        end_time: Math.max(point1.time, point2.time),
        label,
      });
    }
  }

  // Only meaningful on intraday timeframes — on 1d+ each candle already
  // spans a day or more, so day-shading would just paint every other bar.
  const DAY_PLUS_INTERVALS = new Set(["1d", "2d", "3d", "5d", "1w", "1M"]);

  function addSessionShading(candles, interval) {
    if (DAY_PLUS_INTERVALS.has(interval) || candles.length < 2) return;
    let dayKey = null;
    let groupStart = null;
    let dayIndex = -1;
    const bands = [];
    candles.forEach((c, i) => {
      const d = new Date(c.time * 1000);
      const key = `${d.getUTCFullYear()}-${d.getUTCMonth()}-${d.getUTCDate()}`;
      if (key !== dayKey) {
        if (dayKey !== null) bands.push({ start: groupStart, end: candles[i - 1].time, index: dayIndex });
        dayKey = key;
        groupStart = c.time;
        dayIndex++;
      }
    });
    bands.push({ start: groupStart, end: candles[candles.length - 1].time, index: dayIndex });

    bands.forEach((b) => {
      if (b.index % 2 === 0) return; // shade every other day only
      const prim = new SessionBandPrimitive({ time: b.start }, { time: b.end }, "rgba(255, 255, 255, 0.025)");
      candleSeries.attachPrimitive(prim);
      overlays.primitives.push({ series: candleSeries, primitive: prim });
    });
  }

  function pricePrecisionFor(price) {
    if (!price || price <= 0 || price >= 1) return { type: "price", precision: 2, minMove: 0.01 };
    const magnitude = Math.floor(Math.log10(price));
    const precision = Math.min(8, Math.max(2, -magnitude + 3));
    return { type: "price", precision, minMove: 1 / 10 ** precision };
  }

  // ---- Drawing tools (drawing tools plan, 12/10/2026) ----
  // Geometry and painting live in draw-engine.js (DrawEngine, tested in
  // node); this part wires them to the chart: where a point lands, what the
  // pointer does, when the canvas repaints, where drawings are saved.
  //
  // A point stays {time, price}. Its x comes from a fractional bar index
  // (DrawEngine.makeTimeMapper + logicalToCoordinate), so a point drawn on
  // 4h still sits in the right place on 1D, before the first candle and in
  // the empty area after the last one — before, any time that was not
  // exactly a candle of the current timeframe was thrown to the canvas
  // edge or not drawn. Input comes from the pointer event itself, not from
  // the chart's crosshair, which on a phone does not follow the finger.
  const DE = window.DrawEngine;
  const DRAW_TOOL_POINTS = DE.POINTS;
  const DRAW_TOOL_LABELS = {
    trend_line: "Trend line",
    extended_line: "Extended line",
    hline: "Horizontal line",
    hray: "Horizontal ray",
    rectangle: "Rectangle",
    range: "Measure (price + time)",
    fib: "Fibonacci retracement",
    text: "Text",
    arrow: "Arrow",
    channel: "Parallel channel",
    ellipse: "Ellipse",
    fractal: "Fractal",
  };

  function readDrawPref(key, fallback) {
    try { const v = localStorage.getItem(key); return v === null ? fallback : JSON.parse(v); } catch { return fallback; }
  }
  function writeDrawPref(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* per-device convenience only */ }
  }

  const drawState = {
    tool: "cursor",
    pending: [],
    drawings: [],
    attached: {},            // id -> { priceLine } — axis label of an hline
    selected: null,          // id of the selected drawing
    hover: null,             // id under the pointer
    sticky: false,           // tool stays on after a drawing (double click on its button)
    hidden: false,           // "hide all"
    magnet: readDrawPref("drawMagnet", false),
    style: readDrawPref("drawStyle", { color: null, width: 2, dash: "solid" }),
    updatedAt: 0,
  };
  const drawHistory = { undo: [], redo: [] };
  let drawPointer = null;    // last pointer position over the chart, in pane pixels
  let drawVersion = 0;       // bumped on every change the canvas must show
  let dragState = null;      // { drawing, startLogical, startPrice, originalPoints }
  let handleDragState = null; // { drawing, handleIndex, originalPoints }
  const appearAt = {};       // id -> ms when it was placed (150 ms fade-in)

  function bumpDraw() { drawVersion++; }

  // Keyed by what the chart shows (the answer's asset type), not by the
  // asset type the search box last had: the two can differ for a moment.
  function drawChartKey() {
    if (!state.data) return null;
    return `${state.data.asset_type || state.assetType}:${state.data.symbol}`;
  }
  function drawStorageKey() {
    const k = drawChartKey();
    return k ? `draw:${k}` : null;
  }
  function fractalStorageKey() {
    const k = drawChartKey();
    return k ? `fractal:${k}` : null;
  }

  function setDrawTool(tool, { sticky = false } = {}) {
    drawState.tool = tool;
    drawState.sticky = tool !== "cursor" && sticky;
    drawState.pending = [];
    dragState = null; // abandon any in-progress drag rather than leaving it half-applied
    handleDragState = null;
    document.querySelectorAll(".draw-tool-btn[data-draw-tool]").forEach((btn) => {
      btn.classList.toggle("selected", btn.dataset.drawTool === tool);
      btn.classList.toggle("sticky", btn.dataset.drawTool === tool && drawState.sticky);
    });
    const container = el("main-chart");
    if (container) {
      container.style.cursor = tool === "cursor" ? "default" : "crosshair";
      // a finger drawing must not scroll the page
      container.style.touchAction = tool === "cursor" ? "" : "none";
    }
    if (mainChart) mainChart.applyOptions({ handleScroll: tool === "cursor", handleScale: tool === "cursor" });
    bumpDraw();
  }

  // ---- coordinates ----
  let drawCanvas = null;
  let drawCtx = null;
  let drawRafId = null;
  let timeMapper = DE.makeTimeMapper([]);

  function setDrawTimes(candles) {
    timeMapper = DE.makeTimeMapper((candles || []).map((c) => c.time));
    bumpDraw();
  }

  // logicalToCoordinate of Lightweight Charts 4.2 answers 0 for a
  // fractional index (measured: 395 -> 682 px, 393.67 -> 0): interpolate
  // between the two whole bars around it, which it places correctly.
  function logicalToX(logical) {
    const ts = mainChart.timeScale();
    const i = Math.floor(logical);
    const x0 = ts.logicalToCoordinate(i);
    if (x0 === null) return null;
    const frac = logical - i;
    if (frac < 1e-9) return x0;
    const x1 = ts.logicalToCoordinate(i + 1);
    return x1 === null ? x0 : x0 + frac * (x1 - x0);
  }

  function timeToX(time) {
    if (!mainChart) return null;
    const logical = timeMapper.timeToLogical(time);
    if (logical === null) return mainChart.timeScale().timeToCoordinate(time);
    return logicalToX(logical);
  }
  // Kept for the divergence and Elliott layers that call it: with the
  // mapper every time has a real x, so there is no edge to clamp to.
  function timeToXEdge(time) {
    return timeToX(time);
  }
  function xToTime(x) {
    if (!mainChart) return null;
    const logical = mainChart.timeScale().coordinateToLogical(x);
    return logical === null ? null : timeMapper.logicalToTime(logical);
  }
  function priceToY(price) {
    return candleSeries ? candleSeries.priceToCoordinate(price) : null;
  }

  // A DEX pair's symbol is "TICKER@chain:pool-address": shown whole it runs
  // off the phone screen. Ticker plus a short address is enough to tell two
  // pools apart; the full symbol stays in the tooltip.
  function shortSymbol(symbol) {
    const sym = String(symbol || "");
    const at = sym.indexOf("@");
    if (at < 0) return sym;
    const addr = sym.slice(sym.indexOf(":", at) + 1);
    return addr.length > 10 ? `${sym.slice(0, at)} · ${addr.slice(0, 4)}…${addr.slice(-4)}` : sym.slice(0, at);
  }

  function extendLineToBounds(x1, y1, x2, y2, w, h) {
    const e = DE.extendLine(x1, y1, x2, y2, w, h);
    return { lx1: e.x1, ly1: e.y1, lx2: e.x2, ly2: e.y2 };
  }

  // The candle pane: the chart without its price scale and time axis.
  function paneSize() {
    const container = el("main-chart");
    if (!container || !mainChart) return { w: 0, h: 0 };
    let ps = 0, th = 0;
    try { ps = mainChart.priceScale("right").width(); } catch { ps = 0; }
    try { th = mainChart.timeScale().height(); } catch { th = 0; }
    return { w: Math.max(0, container.clientWidth - ps), h: Math.max(0, container.clientHeight - th) };
  }

  function formatDrawPrice(p) {
    const fmt = pricePrecisionFor(Math.abs(p) || 1);
    return Number(p).toFixed(fmt.precision);
  }

  // Pixel points of a drawing (+ offsetY for a channel's parallel line).
  function drawingPx(d) {
    const P = d.points.map((p) => ({ x: timeToX(p.time), y: priceToY(p.price) }));
    if (P.some((p) => p.x === null || p.y === null)) return null;
    if (d.type === "channel" && d.points.length >= 3) {
      const off = DE.channelOffset(d);
      const [p1, p2] = d.points;
      const ya = priceToY(p1.price + off), yb = priceToY(p2.price + off);
      if (ya !== null && yb !== null) P.offsetY = { a: ya - P[0].y, b: yb - P[1].y };
    }
    return P;
  }

  // Where the pointer is, as a drawing point. With the magnet on, the price
  // snaps to the nearest open/high/low/close of the candle under it.
  function pointerToPoint(x, y) {
    const time = xToTime(x);
    let price = candleSeries ? candleSeries.coordinateToPrice(y) : null;
    if (time === null || price === null) return null;
    let t = time;
    // The measure reads the swing it is put on: the nearest high or low of
    // the bars around the pointer, whatever the magnet says.
    const measuring = drawState.tool === "range" || (handleDragState && handleDragState.drawing.type === "range");
    if (measuring && ohlcCandles.length) {
      const idx = timeMapper.nearestIndex(mainChart.timeScale().coordinateToLogical(x));
      if (idx !== null && idx >= 0 && idx < ohlcCandles.length) {
        const near = ohlcCandles.slice(Math.max(0, idx - 2), idx + 3);
        const hit = DE.pickExtreme(near, y, priceToY, 40);
        if (hit) return { time: hit.time, price: hit.price };
      }
      return { time, price };
    }
    if (drawState.magnet && ohlcCandles.length) {
      const logical = mainChart.timeScale().coordinateToLogical(x);
      const idx = timeMapper.nearestIndex(logical);
      const c = idx === null ? null : ohlcCandles[idx];
      if (c) {
        let best = null;
        [c.open, c.high, c.low, c.close].forEach((v) => {
          const vy = priceToY(v);
          if (vy !== null && (best === null || Math.abs(vy - y) < best.d)) best = { v, d: Math.abs(vy - y) };
        });
        if (best && best.d <= 28) { price = best.v; t = c.time; }
      }
    }
    return { time: t, price };
  }

  function drawLook() {
    const dark = document.documentElement.dataset.theme !== "light";
    return {
      panel: dark ? "rgba(22, 27, 34, 0.88)" : "rgba(255, 255, 255, 0.92)",
      ink: COLORS.ink,
      bull: COLORS.bull,
      bear: COLORS.bear,
      defaultColor: DE.PALETTE[0],
    };
  }

  function formatRangeLabel(p1, p2) {
    const l1 = timeMapper.timeToLogical(p1.time), l2 = timeMapper.timeToLogical(p2.time);
    const bars = l1 === null || l2 === null ? null : l2 - l1;
    return DE.formatRange(p1, p2, bars, formatDrawPrice);
  }

  // ---- painting ----
  function paintDrawing(d, flags, size, look) {
    const P = drawingPx(d);
    if (!P) return;
    const born = appearAt[d.id];
    let appear = null;
    if (born) {
      appear = Math.min(1, (performance.now() - born) / 150);
      if (appear >= 1) delete appearAt[d.id];
    }
    DE.paint(drawCtx, d, P, {
      w: size.w, h: size.h, priceToY, formatPrice: formatDrawPrice, look,
      state: { ...flags, appear, activeHandle: handleDragState && handleDragState.drawing === d ? handleDragState.handleIndex : null },
    });
  }

  // Price and time of the selected drawing on the axes, like the reference
  // platforms: a pill on the price scale for each price, on the time axis
  // for each time.
  function paintAxisMarks(d, size, look) {
    const color = d.color || look.defaultColor;
    const fullW = drawCanvas.width / (drawCanvas._dpr || 1);
    const fullH = drawCanvas.height / (drawCanvas._dpr || 1);
    const pts = d.type === "hline" ? [] : d.points;
    const prices = d.type === "fib" ? [] : pts.map((p) => p.price);
    prices.forEach((price) => {
      const y = priceToY(price);
      if (y === null || y < 0 || y > size.h) return;
      DE.pill(drawCtx, formatDrawPrice(price), size.w + 2, y, look, { bg: color, fg: "#ffffff", fit: { w: fullW, h: size.h } });
    });
    if (d.type === "hline" || d.type === "text") return;
    pts.forEach((p) => {
      const x = timeToX(p.time);
      if (x === null || x < 0 || x > size.w) return;
      const label = drawTimeLabel(p.time);
      DE.pill(drawCtx, label, x, size.h + 12, look, { align: "center", bg: color, fg: "#ffffff", fit: { w: size.w, h: fullH } });
    });
  }

  let drawTimeFmt = null;
  function drawTimeLabel(time) {
    if (!drawTimeFmt) {
      const opts = { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" };
      try { drawTimeFmt = new Intl.DateTimeFormat(undefined, opts); } catch { drawTimeFmt = new Intl.DateTimeFormat("en-GB", opts); }
    }
    try { return drawTimeFmt.format(new Date(time * 1000)); } catch { return new Date(time * 1000).toISOString().slice(0, 16).replace("T", " "); }
  }

  function renderDrawCanvas() {
    if (!drawCanvas || !drawCtx || !candleSeries || !mainChart) return;
    const container = el("main-chart");
    if (!container) return;
    const w = container.clientWidth, h = container.clientHeight;
    // Pixels of the screen, not CSS pixels: sharp lines on iPhone and Mac.
    const dpr = Math.min(window.devicePixelRatio || 1, 3);
    if (drawCanvas.width !== Math.round(w * dpr) || drawCanvas.height !== Math.round(h * dpr)) {
      drawCanvas.width = Math.round(w * dpr);
      drawCanvas.height = Math.round(h * dpr);
      drawCanvas._dpr = dpr;
    }
    drawCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawCtx.clearRect(0, 0, w, h);
    window.__drawStats = window.__drawStats || { renders: 0 };
    window.__drawStats.renders++;

    const size = paneSize();
    drawCtx.save();
    // Everything stays on the candles: nothing over the price scale or the time axis.
    drawCtx.beginPath(); drawCtx.rect(0, 0, size.w, size.h); drawCtx.clip();

    renderDivergences(drawCtx, performance.now());
    renderElliott(drawCtx);

    autoPatternZones.forEach((z) => {
      const x1 = timeToX(z.time1), x2 = timeToX(z.time2);
      const y1 = priceToY(z.price1), y2 = priceToY(z.price2);
      if (x1 === null || x2 === null || y1 === null || y2 === null) return;
      drawCtx.save();
      drawCtx.fillStyle = z.color;
      drawCtx.strokeStyle = z.color.replace("0.15", "0.5");
      drawCtx.lineWidth = 1;
      const fx = Math.min(x1, x2), fy = Math.min(y1, y2), fw = Math.abs(x2 - x1), fh = Math.abs(y2 - y1);
      drawCtx.beginPath(); drawCtx.rect(fx, fy, fw, fh); drawCtx.fill(); drawCtx.stroke();
      drawCtx.fillStyle = z.color.replace("0.15", "0.8");
      drawCtx.font = "10px system-ui, sans-serif";
      drawCtx.fillText(z.label, fx + 2, fy - 3);
      drawCtx.restore();
    });

    const look = drawLook();
    let selected = null;
    if (!drawState.hidden) {
      drawState.drawings.forEach((d) => {
        const isSelected = drawState.selected === d.id;
        if (isSelected) selected = d;
        paintDrawing(d, { selected: isSelected, hover: !isSelected && drawState.hover === d.id }, size, look);
      });
    }

    // Preview while placing the next point
    if (drawState.tool !== "cursor" && drawState.pending.length >= 1 && drawPointer) {
      const next = pointerToPoint(drawPointer.x, drawPointer.y);
      if (next) {
        const ghost = { id: "ghost", type: drawState.tool, points: [...drawState.pending, next], v: 2, ...currentDrawStyle() };
        if (ghost.type === "range") ghost.text = formatRangeLabel(ghost.points[0], ghost.points[ghost.points.length - 1]);
        paintDrawing(ghost, { ghost: true }, size, look);
      }
    }
    drawCtx.restore();

    if (selected) paintAxisMarks(selected, size, look);
    positionDrawToolbar(selected);
  }

  function currentDrawStyle() {
    const s = drawState.style || {};
    return { color: s.color || null, width: s.width || 2, dash: s.dash || "solid" };
  }

  // Repaint only when something visible changed: the visible bars, the
  // price scale, the size, the drawings, the pointer while drawing. The
  // check costs a few numbers a frame; the repaint used to run 60 times a
  // second forever, chart still or not.
  let lastDrawSig = "";
  function drawSignature() {
    const container = el("main-chart");
    const ts = mainChart.timeScale();
    const r = ts.getVisibleLogicalRange();
    const ref = ohlcCandles.length ? ohlcCandles[ohlcCandles.length - 1].close : 1;
    return [
      container ? container.clientWidth : 0, container ? container.clientHeight : 0, window.devicePixelRatio,
      r ? r.from.toFixed(4) : "", r ? r.to.toFixed(4) : "",
      priceToY(ref), priceToY(ref * 1.1), drawVersion,
    ].join("|");
  }
  function drawAnimating() {
    return (state.layers.divergences && divergenceLines.length > 0) || Object.keys(appearAt).length > 0;
  }

  function startDrawRaf() {
    if (drawRafId) return;
    function loop() {
      if (mainChart && candleSeries) {
        const sig = drawSignature();
        if (sig !== lastDrawSig || drawAnimating()) {
          lastDrawSig = sig;
          // One bad frame must not stop the loop: before, an exception here
          // ended requestAnimationFrame for good and every drawing vanished.
          try { renderDrawCanvas(); } catch (err) { console.warn("drawing layer:", err); }
        }
      }
      drawRafId = requestAnimationFrame(loop);
    }
    drawRafId = requestAnimationFrame(loop);
  }

  function initDrawCanvas() {
    drawCanvas = el("draw-canvas");
    if (!drawCanvas) return;
    drawCtx = drawCanvas.getContext("2d");
    buildDrawToolbar();
    startDrawRaf();
    // Read-only window for the browser tests (scripts/e2e/draw.e2e.mjs),
    // only when asked for: ?drawdebug in the address.
    if (/[?&]drawdebug\b/.test(location.search)) {
      window.__drawDebug = {
        state: drawState,
        px: (time, price) => ({ x: timeToX(time), y: priceToY(price) }),
        logical: (time) => timeMapper.timeToLogical(time),
        candleAt: (time) => ohlcCandles.find((c) => c.time === time) || null,
        lastCandles: (n) => ohlcCandles.slice(-n),
        bars: () => timeMapper.size,
        pane: () => paneSize(),
        chart: () => mainChart,
      };
    }
  }

  // Kept for call-site compatibility: the crosshair no longer drives drawing.
  function startGhost() {}
  function updateGhost() {}

  // ---- Auto pattern recognition ----
  let autoPatternMarkers = []; // TW series markers for candle patterns
  let autoPatternZones = [];   // { time1, time2, price1, price2, color, label }

  function detectCandlePatterns(candles, rsiValues) {
    const markers = [];
    const zones = [];
    const rsiMap = {};
    if (rsiValues) rsiValues.forEach((r) => { if (r.value != null) rsiMap[r.time] = r.value; });

    for (let i = 2; i < candles.length; i++) {
      const c = candles[i], prev = candles[i - 1], prev2 = candles[i - 2];
      const body = Math.abs(c.close - c.open);
      const range = c.high - c.low || 0.0001;
      const isBull = c.close > c.open;
      const upperWick = c.high - Math.max(c.open, c.close);
      const lowerWick = Math.min(c.open, c.close) - c.low;
      const prevBody = Math.abs(prev.close - prev.open);
      const prevBull = prev.close > prev.open;

      // Doji: body ≤ 10% of range
      if (body / range <= 0.10 && range > 0) {
        markers.push({ time: c.time, position: "aboveBar", color: "#a78bfa", shape: "circle", text: "Doji" });
        continue;
      }

      // Hammer: at bottom, lower wick ≥ 2× body, upper wick ≤ 0.3× body
      if (!isBull && lowerWick >= 2 * body && upperWick <= 0.3 * body && prev.close < prev2.close) {
        markers.push({ time: c.time, position: "belowBar", color: "#34d399", shape: "arrowUp", text: "Hammer" });
        continue;
      }

      // Long upper wick, small lower one: after a fall it is an inverted
      // hammer (bullish), after a rise a shooting star (bearish). It was
      // always drawn as a bearish "Inv.Hammer", the opposite of its meaning
      // at a bottom.
      if (upperWick >= 2 * body && lowerWick <= 0.3 * body) {
        if (prev.close < prev2.close) {
          markers.push({ time: c.time, position: "belowBar", color: "#34d399", shape: "arrowUp", text: "Inv.Hammer" });
          continue;
        }
        if (prev.close > prev2.close) {
          markers.push({ time: c.time, position: "aboveBar", color: "#f87171", shape: "arrowDown", text: "Star" });
          continue;
        }
      }

      // Bullish engulfing
      if (isBull && !prevBull && c.open <= prev.close && c.close >= prev.open && body > prevBody * 0.9) {
        markers.push({ time: c.time, position: "belowBar", color: "#34d399", shape: "arrowUp", text: "Eng↑" });
        continue;
      }

      // Bearish engulfing
      if (!isBull && prevBull && c.open >= prev.close && c.close <= prev.open && body > prevBody * 0.9) {
        markers.push({ time: c.time, position: "aboveBar", color: "#f87171", shape: "arrowDown", text: "Eng↓" });
        continue;
      }

      // Momentum slowdown: last 3 candles same direction but shrinking body
      if (i >= 3) {
        const prev3 = candles[i - 3];
        const p3Body = Math.abs(prev2.close - prev2.open);
        const p2Body = Math.abs(prev.close - prev.open);
        const sameDir = (prev3.close > prev3.open) === (prev2.close > prev2.open) && (prev2.close > prev2.open) === prevBull;
        if (sameDir && p3Body > p2Body && p2Body > prevBody * 1.1 && body < prevBody * 0.6) {
          markers.push({ time: c.time, position: prevBull ? "aboveBar" : "belowBar", color: "#fbbf24", shape: "circle", text: "Slowing" });
          continue;
        }
      }
    }

    // RSI divergence: look for swing lows/highs in last 30 candles
    const lookback = Math.min(30, candles.length - 1);
    const start = candles.length - lookback;
    for (let i = start + 5; i < candles.length - 2; i++) {
      const rsiCur = rsiMap[candles[i].time];
      if (rsiCur == null) continue;

      // Bullish RSI divergence: price lower low, RSI higher low
      let lowestPriceIdx = i;
      for (let j = start; j < i; j++) { if (candles[j].low < candles[lowestPriceIdx].low) lowestPriceIdx = j; }
      if (lowestPriceIdx !== i && candles[i].low < candles[lowestPriceIdx].low * 1.01) {
        const rsiRef = rsiMap[candles[lowestPriceIdx].time];
        if (rsiRef != null && rsiCur > rsiRef + 3 && rsiCur < 45) {
          const t1 = candles[lowestPriceIdx].time, t2 = candles[i].time;
          const p = Math.min(candles[lowestPriceIdx].low, candles[i].low) * 0.998;
          zones.push({ time1: t1, time2: t2, price1: p * 0.997, price2: p, color: "rgba(52,211,153,0.15)", label: "Div RSI↑" });
        }
      }

      // Bearish RSI divergence: price higher high, RSI lower high
      let highestPriceIdx = i;
      for (let j = start; j < i; j++) { if (candles[j].high > candles[highestPriceIdx].high) highestPriceIdx = j; }
      if (highestPriceIdx !== i && candles[i].high > candles[highestPriceIdx].high * 0.99) {
        const rsiRef = rsiMap[candles[highestPriceIdx].time];
        if (rsiRef != null && rsiCur < rsiRef - 3 && rsiCur > 55) {
          const t1 = candles[highestPriceIdx].time, t2 = candles[i].time;
          const p = Math.max(candles[highestPriceIdx].high, candles[i].high) * 1.002;
          zones.push({ time1: t1, time2: t2, price1: p, price2: p * 1.003, color: "rgba(248,113,113,0.15)", label: "Div RSI↓" });
        }
      }
    }

    return { markers, zones };
  }

  function applyAutoPatterns() {
    if (!candleSeries) return;
    autoPatternMarkers = [];
    autoPatternZones = [];
    if (!state.layers.patterns || !state.data) return;
    const tf = state.activeTimeframe;
    const analysis = state.data.timeframes[tf];
    if (!analysis) return;
    const candles = analysis.candles;
    const rsiValues = findIndicator(analysis.indicators, "RSI14");
    const rsiSeries = rsiValues ? seriesFromIndicatorValues(candles, rsiValues).filter((d) => d.value != null) : null;
    const { markers, zones } = detectCandlePatterns(candles, rsiSeries);
    autoPatternMarkers = markers;
    autoPatternZones = zones;
    applyChartMarkers();
  }

  // ---- Segnali contestuali — "cosa sta succedendo al grafico" ----
  // Non indicatori classici: annotazioni che leggono le candele,
  // l'angolo del trend EMA e l'RSI per dire in italiano semplice
  // cosa sta accadendo e se ci si sta avvicinando a un reversal.

  let contextualHintMarkers = [];
  let divergenceLines = []; // [{type:'bear'|'bull', t1,t2, p1,p2, confirmed}]
  let _predictBtnTimer = null;

  // ── Swing point detection (ZigZag) ────────────────────────────────────────
  function findSwings(candles, n = 5) {
    const highs = [], lows = [];
    for (let i = n; i < candles.length - n; i++) {
      let isHigh = true, isLow = true;
      for (let j = i - n; j <= i + n; j++) {
        if (j === i) continue;
        if (candles[j].high >= candles[i].high) isHigh = false;
        if (candles[j].low  <= candles[i].low)  isLow  = false;
      }
      if (isHigh) highs.push({ i, time: candles[i].time, price: candles[i].high });
      if (isLow)  lows.push({ i, time: candles[i].time, price: candles[i].low });
    }
    return { highs, lows };
  }

  function _atrAt(candles, i, w = 14) {
    const start = Math.max(1, i - w + 1);
    let sum = 0, n = 0;
    for (let k = start; k <= i; k++) {
      const c = candles[k], prev = candles[k - 1];
      if (!prev) continue;
      const tr = Math.max(c.high - c.low, Math.abs(c.high - prev.close), Math.abs(c.low - prev.close));
      sum += tr; n++;
    }
    return n > 0 ? sum / n : 1;
  }

  // ── Divergence detection ──────────────────────────────────────────────────
  function detectDivergences(candles, indicators) {
    const lines = [];
    if (!candles || candles.length < 20) return lines;

    const rsiRaw = findIndicator(indicators, "RSI14") || findIndicator(indicators, "RSI");
    if (!rsiRaw) return lines;
    const rsiMap = {};
    seriesFromIndicatorValues(candles, rsiRaw).forEach((d) => { if (d.value != null) rsiMap[d.time] = d.value; });

    const swingN = 4;
    const { highs, lows } = findSwings(candles, swingN);
    const lastI = candles.length - 1;
    const confirmBars = swingN; // una swing è confermata dopo N barre

    // Bearish: prezzo HH, RSI LH — prendo le ultime 2 coppie di highs
    for (let a = Math.max(0, highs.length - 4); a < highs.length - 1; a++) {
      for (let b = a + 1; b < highs.length; b++) {
        const h1 = highs[a], h2 = highs[b];
        if (h2.price <= h1.price) continue; // serve HH
        const rsi1 = rsiMap[h1.time], rsi2 = rsiMap[h2.time];
        if (rsi1 == null || rsi2 == null) continue;
        if (rsi2 >= rsi1 - 2) continue; // serve LH su RSI (divergenza)
        const confirmed = (lastI - h2.i) >= confirmBars;
        lines.push({ type: "bear", t1: h1.time, t2: h2.time, p1: h1.price, p2: h2.price, rsi1, rsi2, confirmed });
      }
    }

    // Bullish: prezzo LL, RSI HL — prendo le ultime 2 coppie di lows
    for (let a = Math.max(0, lows.length - 4); a < lows.length - 1; a++) {
      for (let b = a + 1; b < lows.length; b++) {
        const l1 = lows[a], l2 = lows[b];
        if (l2.price >= l1.price) continue; // serve LL
        const rsi1 = rsiMap[l1.time], rsi2 = rsiMap[l2.time];
        if (rsi1 == null || rsi2 == null) continue;
        if (rsi2 <= rsi1 + 2) continue; // serve HL su RSI (divergenza)
        const confirmed = (lastI - l2.i) >= confirmBars;
        lines.push({ type: "bull", t1: l1.time, t2: l2.time, p1: l1.price, p2: l2.price, rsi1, rsi2, confirmed });
      }
    }

    // Limita a max 3 per tipo, le più recenti
    const bears = lines.filter(d => d.type === "bear").slice(-3);
    const bulls = lines.filter(d => d.type === "bull").slice(-3);
    return [...bears, ...bulls];
  }

  function applyDivergences() {
    divergenceLines = [];
    if (!state.layers.divergences || !state.data) return;
    const tf = state.activeTimeframe;
    const analysis = state.data.timeframes[tf];
    if (!analysis) return;
    divergenceLines = detectDivergences(analysis.candles, analysis.indicators || []);
  }

  // ── Elliott Waves (segnalazione 7f9cd5ed) ─────────────────────────────────
  // Detection lives in elliott.js; here it is only drawn on the canvas, like
  // the divergences: motive 1-5 and corrective a-b-c on the zigzag, dashed
  // while the last point can still move or once the correction breaks the
  // motive's start, and the latest motive's Fibonacci retracements.
  let elliottWaves = null;
  const ELLIOTT_LEN = 10;

  function applyElliott() {
    elliottWaves = null;
    if (!state.layers.elliott || !state.data || !window.ElliottWave) return;
    const analysis = state.data.timeframes[state.activeTimeframe];
    if (!analysis) return;
    elliottWaves = window.ElliottWave.detect(analysis.candles, ELLIOTT_LEN);
  }

  function renderElliott(ctx) {
    if (!state.layers.elliott || !elliottWaves) return;
    const rgba = (dir, a) => (dir === "bull" ? `rgba(0,214,143,${a})` : `rgba(255,69,96,${a})`);
    const drawLeg = (pts, labels, dir, dashed, alpha) => {
      const xy = pts.map((p) => ({ x: timeToXEdge(p.time), y: priceToY(p.price), up: false }));
      if (xy.some((q) => q.x === null || q.y === null)) return;
      ctx.save();
      ctx.strokeStyle = rgba(dir, alpha);
      ctx.lineWidth = 1.4;
      ctx.setLineDash(dashed ? [5, 4] : []);
      ctx.beginPath();
      xy.forEach((q, i) => (i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y)));
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.font = "bold 11px 'JetBrains Mono', monospace";
      ctx.textAlign = "center";
      ctx.fillStyle = rgba(dir, Math.min(1, alpha + 0.2));
      xy.forEach((q, i) => {
        if (!labels[i]) return;
        // A label sits on the outside of its turn: above a peak, below a trough.
        const prev = xy[i - 1] || xy[i + 1];
        const peak = prev ? q.y < prev.y : true;
        ctx.fillText(labels[i], q.x, peak ? q.y - 7 : q.y + 15);
      });
      ctx.restore();
    };
    elliottWaves.motives.forEach((m) =>
      drawLeg(m.points, ["", "1", "2", "3", "4", "5"], m.dir, m.tentative, 0.75));
    elliottWaves.corrections.forEach((c) =>
      drawLeg(c.points, ["", "a", "b", "c"], c.dir, c.invalid || c.tentative, c.invalid ? 0.35 : 0.6));
    const fib = elliottWaves.fib;
    if (fib) {
      const x1 = timeToXEdge(fib.time);
      if (x1 === null) return;
      // The plot ends where the price axis starts: the lines and labels ran
      // over the axis numbers.
      const x2 = mainChart.timeScale().width();
      if (x1 >= x2) return;
      const light = COLORS.paperBg === "#ffffff";
      ctx.save();
      ctx.font = "10px 'JetBrains Mono', monospace";
      ctx.textAlign = "right";
      Object.entries(fib.levels).forEach(([ratio, price]) => {
        const y = priceToY(price);
        if (y === null) return;
        ctx.strokeStyle = light ? "rgba(217,119,6,0.55)" : "rgba(255,193,7,0.45)";
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(x2, y); ctx.stroke();
        ctx.fillStyle = light ? "rgba(180,83,9,0.95)" : "rgba(255,193,7,0.85)";
        ctx.fillText(`EW ${ratio}`, x2 - 6, y - 3);
      });
      ctx.restore();
    }
  }

  // ── Divergence rendering (chiamato dentro renderDrawCanvas) ───────────────
  function renderDivergences(ctx, ts) {
    if (!state.layers.divergences || !divergenceLines.length) return;

    divergenceLines.forEach((d) => {
      const x1 = timeToXEdge(d.t1), x2 = timeToXEdge(d.t2);
      const y1 = priceToY(d.p1), y2 = priceToY(d.p2);
      if (x1 === null || x2 === null || y1 === null || y2 === null) return;

      const color = d.type === "bear" ? "#ff4560" : "#00d68f";
      const colorA = d.type === "bear" ? "rgba(255,69,96," : "rgba(0,214,143,";

      ctx.save();
      ctx.lineCap = "round";

      if (d.confirmed) {
        // linea piena sottile
        ctx.strokeStyle = colorA + "0.55)";
        ctx.lineWidth = 1.2;
        ctx.setLineDash([]);
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
        // dot agli endpoint
        [{ x: x1, y: y1 }, { x: x2, y: y2 }].forEach(({ x, y }) => {
          ctx.beginPath(); ctx.arc(x, y, 2.5, 0, Math.PI * 2);
          ctx.fillStyle = colorA + "0.8)"; ctx.fill();
        });
        // etichetta al midpoint
        const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
        const label = d.type === "bear" ? "div↓" : "div↑";
        ctx.font = "9px 'JetBrains Mono', monospace";
        ctx.textAlign = "center";
        const tw = ctx.measureText(label).width;
        ctx.fillStyle = COLORS.paperBg === "#ffffff" ? "rgba(255,255,255,0.85)" : "rgba(8,11,12,0.75)";
        ctx.fillRect(mx - tw / 2 - 3, my - 8, tw + 6, 12);
        ctx.fillStyle = colorA + "0.85)";
        ctx.fillText(label, mx, my + 2);
      } else {
        // linea tratteggiata (forming) con dot pulsante sull'estremità destra
        const dash = ts * 0.04 % 10;
        ctx.strokeStyle = colorA + "0.4)";
        ctx.lineWidth = 1;
        ctx.setLineDash([5, 4]);
        ctx.lineDashOffset = -dash;
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
        ctx.setLineDash([]);
        // dot pulsante
        const pulse = 0.45 + 0.35 * Math.sin(ts * 0.004);
        ctx.beginPath(); ctx.arc(x2, y2, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = colorA + pulse + ")"; ctx.fill();
      }

      ctx.restore();
    });
  }

  function detectContextualHints(candles, indicators) {
    const markers = [];
    if (!candles || candles.length < 10) return markers;

    // Ricava valori EMA20 e RSI14 dalla lista indicatori
    const emaRaw = findIndicator(indicators, "EMA20") || findIndicator(indicators, "EMA 20/50");
    const rsiRaw = findIndicator(indicators, "RSI14") || findIndicator(indicators, "RSI");
    const emaMap = {}, rsiMap = {};
    if (emaRaw) seriesFromIndicatorValues(candles, emaRaw).forEach((d) => { if (d.value != null) emaMap[d.time] = d.value; });
    if (rsiRaw) seriesFromIndicatorValues(candles, rsiRaw).forEach((d) => { if (d.value != null) rsiMap[d.time] = d.value; });

    // ATR rolling (14 periodi) per normalizzare le pendenze
    const atrWindow = 14;
    function atrAt(i) {
      const start = Math.max(0, i - atrWindow + 1);
      let sum = 0, n = 0;
      for (let k = start; k <= i; k++) {
        const c = candles[k], prev = candles[k - 1];
        if (!prev) continue;
        const tr = Math.max(c.high - c.low, Math.abs(c.high - prev.close), Math.abs(c.low - prev.close));
        sum += tr; n++;
      }
      return n > 0 ? sum / n : 1;
    }

    // Pendenza EMA: delta tra barra corrente e N barre fa, normalizzata su ATR.
    // Valori assoluti > 0.5 = trend significativo; < 0.1 = piatto.
    const SLOPE_WINDOW = 5;

    for (let i = Math.max(SLOPE_WINDOW + 2, 3); i < candles.length; i++) {
      const c = candles[i];
      const prev = candles[i - 1];
      const prev2 = candles[i - 2];
      const t = c.time;

      const body = Math.abs(c.close - c.open);
      const range = c.high - c.low || 0.0001;
      const isBull = c.close >= c.open;
      const upperWick = c.high - Math.max(c.open, c.close);
      const lowerWick = Math.min(c.open, c.close) - c.low;
      const prevBody = Math.abs(prev.close - prev.open);
      const prev2Body = Math.abs(prev2.close - prev2.open);
      const prevBull = prev.close >= prev.open;
      const atr = atrAt(i);

      const rsi = rsiMap[t];
      const emaNow = emaMap[t];
      const emaPrev = emaMap[prev.time];
      const emaPrev5 = emaMap[candles[i - SLOPE_WINDOW]?.time];

      // ── Analisi angolo trend EMA ─────────────────────────────────────────
      if (emaNow != null && emaPrev != null && emaPrev5 != null && atr > 0) {
        const slope = (emaNow - emaPrev) / atr;           // slope corrente
        const slopePrev = (emaPrev - emaPrev5) / (atr * SLOPE_WINDOW); // slope media recente

        const trendUp = slope > 0.08;
        const trendDown = slope < -0.08;
        const slopeAccel = Math.abs(slope) > Math.abs(slopePrev) * 1.3;
        const slopeDecel = Math.abs(slopePrev) > 0.05 && Math.abs(slope) < Math.abs(slopePrev) * 0.6;

        if (slopeDecel && trendUp && i === candles.length - 1) {
          markers.push({ time: t, position: "aboveBar", color: "#f59e0b", shape: "circle", text: "↘ Trend slowing" });
        } else if (slopeDecel && trendDown && i === candles.length - 1) {
          markers.push({ time: t, position: "belowBar", color: "#f59e0b", shape: "circle", text: "↗ Trend slowing" });
        }

        // Trend forte in accelerazione — solo sull'ultima candela per non affollare
        if (slopeAccel && Math.abs(slope) > 0.3 && i === candles.length - 1) {
          const col = trendUp ? "#22c55e" : "#ef4444";
          const lbl = trendUp ? "⚡ Strong trend ↑" : "⚡ Strong trend ↓";
          markers.push({ time: t, position: trendUp ? "belowBar" : "aboveBar", color: col, shape: "arrowUp", text: lbl });
        }
      }

      // ── Esaurimento del trend (3 candele stessa dir con corpi decrescenti) ──
      if (i >= 3) {
        const c3 = candles[i - 2];
        const allUp = isBull && prevBull && c3.close >= c3.open;
        const allDown = !isBull && !prevBull && c3.close < c3.open;
        const shrinking = body < prevBody && prevBody < prev2Body;
        if ((allUp || allDown) && shrinking && body < atr * 0.4) {
          const col = allUp ? "#f59e0b" : "#f59e0b";
          const lbl = allUp ? "⚠ Exhaustion ↑" : "⚠ Exhaustion ↓";
          markers.push({ time: t, position: allUp ? "aboveBar" : "belowBar", color: col, shape: "circle", text: lbl });
        }
      }

      // ── Inside bar — contrazione di volatilità ──────────────────────────
      if (c.high < prev.high && c.low > prev.low && range < atr * 0.6) {
        markers.push({ time: t, position: "aboveBar", color: "#a78bfa", shape: "circle", text: "◼ Contraction" });
        continue; // non sovrapporre altri segnali sulla stessa barra
      }

      // ── Marubozu — momentum puro senza wick ────────────────────────────
      if (body / range > 0.88 && range > atr * 0.8) {
        const col = isBull ? "#22c55e" : "#ef4444";
        const lbl = isBull ? "→ Momentum ↑" : "→ Momentum ↓";
        markers.push({ time: t, position: isBull ? "belowBar" : "aboveBar", color: col, shape: isBull ? "arrowUp" : "arrowDown", text: lbl });
        continue;
      }

      // ── Segnali combinati RSI + candela ────────────────────────────────
      if (rsi != null) {
        if (rsi > 72 && !isBull && upperWick > body * 0.8) {
          markers.push({ time: t, position: "aboveBar", color: "#ef4444", shape: "arrowDown", text: "↙ RSI+ saturated" });
          continue;
        }
        if (rsi < 28 && isBull && lowerWick > body * 0.8) {
          markers.push({ time: t, position: "belowBar", color: "#22c55e", shape: "arrowUp", text: "↗ RSI− exhausted" });
          continue;
        }
        // RSI neutrale su zona di supporto/resistenza (range 43-57)
        if (rsi >= 43 && rsi <= 57 && body / range < 0.35 && i === candles.length - 1) {
          markers.push({ time: t, position: "aboveBar", color: "#6b7280", shape: "circle", text: "~ Indecision" });
        }
      }
    }

    return markers;
  }

  function applyContextualHints() {
    if (!candleSeries) return;
    contextualHintMarkers = [];
    if (!state.layers.hints || !state.data) return;
    const tf = state.activeTimeframe;
    const analysis = state.data.timeframes[tf];
    if (!analysis) return;
    contextualHintMarkers = detectContextualHints(analysis.candles, analysis.indicators || []);
    applyChartMarkers();
  }

  function clearGhost() {}

  // ---- hit test ----
  const HIT_TOLERANCE_PX = 6;

  function drawTextWidth(text) {
    if (!drawCtx) return 60;
    drawCtx.save();
    drawCtx.font = "600 13px -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif";
    const w = drawCtx.measureText(text).width;
    drawCtx.restore();
    return w;
  }

  function hitTestDrawing(d, px, py, tol) {
    const P = drawingPx(d);
    if (!P) return false;
    const size = paneSize();
    return DE.hitTest(d, P, px, py, { w: size.w, h: size.h, priceToY, textWidth: drawTextWidth }, tol);
  }

  function isTouchPointer() {
    return lastPointerType === "touch" || lastPointerType === "pen";
  }

  function findHitDrawing(px, py) {
    if (drawState.hidden) return null;
    const tol = isTouchPointer() ? 14 : HIT_TOLERANCE_PX;
    for (let i = drawState.drawings.length - 1; i >= 0; i--) {
      if (hitTestDrawing(drawState.drawings[i], px, py, tol)) return drawState.drawings[i];
    }
    return null;
  }

  // 44 px targets on touch, as the platform guidelines ask.
  function findHitHandle(px, py) {
    if (!drawState.selected || drawState.hidden) return null;
    const d = drawState.drawings.find((x) => x.id === drawState.selected);
    if (!d || d.type === "hline" || d.locked) return null;
    const P = drawingPx(d);
    if (!P) return null;
    const radius = isTouchPointer() ? 22 : 10;
    const n = Math.min(P.length, DRAW_TOOL_POINTS[d.type] || P.length);
    for (let i = 0; i < n; i++) {
      if (Math.hypot(px - P[i].x, py - P[i].y) <= radius) return { drawing: d, handleIndex: i };
    }
    return null;
  }

  function setDrawHover(id) {
    if (drawState.hover !== id) { drawState.hover = id; bumpDraw(); }
  }

  function updateCursorHover() {} // pointer-driven now (bindDrawClickCapture)
  function updateHandleDrag() {}
  function updateDragPreview() {}

  // ---- hline axis label ----
  function attachDrawing(d) {
    if (!candleSeries || d.type !== "hline") return;
    // The canvas draws the line; the price line only gives the axis label,
    // so it is never drawn twice and never recreated while dragging.
    const line = candleSeries.createPriceLine({
      price: d.points[0].price,
      color: d.color || DE.PALETTE[0],
      lineWidth: 1,
      lineVisible: false,
      axisLabelVisible: true,
      title: d.text || "",
    });
    drawState.attached[d.id] = { priceLine: line };
  }

  function repositionDrawingPrimitives(d) {
    const ref = drawState.attached[d.id];
    if (!ref || !ref.priceLine) return;
    ref.priceLine.applyOptions({ price: d.points[0].price, color: d.color || DE.PALETTE[0], title: d.text || "" });
  }

  function detachDrawing(id) {
    const ref = drawState.attached[id];
    if (!ref) return;
    if (ref.priceLine) {
      try { candleSeries.removePriceLine(ref.priceLine); } catch { /* already gone */ }
    }
    delete drawState.attached[id];
  }

  function clearAllDrawingPrimitives() {
    Object.keys(drawState.attached).forEach(detachDrawing);
  }

  function reattachAll() {
    clearAllDrawingPrimitives();
    if (!drawState.hidden) drawState.drawings.forEach(attachDrawing);
  }

  // ---- history (undo / redo) ----
  function pushDrawHistory() {
    drawHistory.undo.push(JSON.stringify(drawState.drawings));
    if (drawHistory.undo.length > 100) drawHistory.undo.shift();
    drawHistory.redo = [];
  }
  function restoreDrawSnapshot(json) {
    drawState.drawings = JSON.parse(json);
    if (!drawState.drawings.some((d) => d.id === drawState.selected)) drawState.selected = null;
    reattachAll();
    saveDrawings();
    renderDrawingsList();
    bumpDraw();
  }
  function undoDrawing() {
    if (!drawHistory.undo.length) return;
    drawHistory.redo.push(JSON.stringify(drawState.drawings));
    restoreDrawSnapshot(drawHistory.undo.pop());
  }
  function redoDrawing() {
    if (!drawHistory.redo.length) return;
    drawHistory.undo.push(JSON.stringify(drawState.drawings));
    restoreDrawSnapshot(drawHistory.redo.pop());
  }

  // ---- saving: this browser at once, the account a moment later ----
  let drawSyncTimer = null;
  function saveDrawings() {
    const key = drawStorageKey();
    if (!key) return;
    drawState.updatedAt = Date.now();
    try {
      localStorage.setItem(key, JSON.stringify({ drawings: drawState.drawings, updated_at: drawState.updatedAt }));
    } catch (e) {
      /* storage unavailable/full — the account copy below still keeps them */
    }
    scheduleDrawSync(key, drawState.drawings, drawState.updatedAt);
  }

  const pendingDrawSync = {};
  function scheduleDrawSync(key, drawings, updatedAt) {
    if (!state.user) return;
    pendingDrawSync[key] = { drawings, updated_at: updatedAt };
    clearTimeout(drawSyncTimer);
    drawSyncTimer = setTimeout(flushDrawSync, 800);
  }
  function flushDrawSync() {
    Object.entries(pendingDrawSync).forEach(([key, body]) => {
      delete pendingDrawSync[key];
      fetch("/api/drawings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, drawings: body.drawings, updated_at: body.updated_at }),
        keepalive: true,
      }).catch(() => { /* offline: the local copy stays, next save retries */ });
    });
  }
  window.addEventListener("pagehide", flushDrawSync);

  function readLocalDrawings(key) {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return { drawings: [], updated_at: 0 };
      const parsed = JSON.parse(raw);
      // Before 12/10 the value was the bare array.
      if (Array.isArray(parsed)) return { drawings: parsed, updated_at: 0 };
      return { drawings: Array.isArray(parsed.drawings) ? parsed.drawings : [], updated_at: parsed.updated_at || 0 };
    } catch {
      return { drawings: [], updated_at: 0 };
    }
  }

  // The account's copy, when newer than this browser's, replaces it; when
  // older (or missing) this browser's goes up.
  async function syncDrawingsFromServer(key, local, apply) {
    if (!state.user) return;
    try {
      const resp = await fetch(`/api/drawings?key=${encodeURIComponent(key)}`);
      if (!resp.ok) return;
      const remote = await resp.json();
      if (remote.drawings && remote.updated_at > local.updated_at) {
        try { localStorage.setItem(key, JSON.stringify(remote)); } catch { /* ignore */ }
        apply(remote);
      } else if (local.drawings.length && local.updated_at >= (remote.updated_at || 0)) {
        scheduleDrawSync(key, local.drawings, local.updated_at || Date.now());
      }
    } catch { /* offline: keep the local copy */ }
  }

  function renderDrawingsList() {
    const list = el("draw-list");
    if (!list) return;
    list.innerHTML = "";
    if (!drawState.drawings.length) {
      const li = document.createElement("li");
      li.className = "panel-hint";
      li.textContent = "No drawings on this chart.";
      list.appendChild(li);
      return;
    }
    drawState.drawings.forEach((d) => {
      const li = document.createElement("li");
      li.className = "draw-list-item";
      const dot = document.createElement("span");
      dot.className = "draw-list-dot";
      dot.style.background = d.color || DE.PALETTE[0];
      const label = document.createElement("span");
      label.textContent = DRAW_TOOL_LABELS[d.type] || d.type;
      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "draw-list-remove";
      removeBtn.textContent = "✕";
      removeBtn.setAttribute("aria-label", `Remove ${label.textContent}`);
      removeBtn.addEventListener("click", () => removeDrawing(d.id));
      li.appendChild(dot);
      li.appendChild(label);
      li.appendChild(removeBtn);
      list.appendChild(li);
    });
  }

  function removeDrawing(id) {
    pushDrawHistory();
    detachDrawing(id);
    drawState.drawings = drawState.drawings.filter((d) => d.id !== id);
    if (drawState.selected === id) drawState.selected = null;
    saveDrawings();
    renderDrawingsList();
    bumpDraw();
  }

  function clearAllDrawings() {
    pushDrawHistory();
    clearAllDrawingPrimitives();
    drawState.drawings = [];
    drawState.selected = null;
    saveDrawings();
    renderDrawingsList();
    bumpDraw();
  }

  function updateDrawing(id, patch) {
    const d = drawState.drawings.find((x) => x.id === id);
    if (!d) return;
    pushDrawHistory();
    Object.assign(d, patch);
    repositionDrawingPrimitives(d);
    saveDrawings();
    renderDrawingsList();
    bumpDraw();
  }

  function duplicateDrawing(id) {
    const d = drawState.drawings.find((x) => x.id === id);
    if (!d) return;
    pushDrawHistory();
    const shift = Math.max(1, Math.round((timeMapper.stepLast || 60) * 3));
    const copy = { ...JSON.parse(JSON.stringify(d)), id: newDrawingId(), locked: false };
    copy.points = copy.points.map((p) => ({ time: p.time + shift, price: p.price }));
    drawState.drawings.push(copy);
    attachDrawing(copy);
    drawState.selected = copy.id;
    appearAt[copy.id] = performance.now();
    saveDrawings();
    renderDrawingsList();
    bumpDraw();
  }

  function toggleHideDrawings() {
    drawState.hidden = !drawState.hidden;
    reattachAll();
    const btn = el("draw-hide-btn");
    if (btn) { btn.classList.toggle("selected", drawState.hidden); btn.setAttribute("aria-pressed", String(drawState.hidden)); }
    bumpDraw();
  }

  function toggleMagnet() {
    drawState.magnet = !drawState.magnet;
    writeDrawPref("drawMagnet", drawState.magnet);
    const btn = el("draw-magnet-btn");
    if (btn) { btn.classList.toggle("selected", drawState.magnet); btn.setAttribute("aria-pressed", String(drawState.magnet)); }
  }

  // ---- toolbar of the selected drawing: colour, width, dash, lock, copy, delete ----
  let drawToolbar = null;
  function buildDrawToolbar() {
    const container = el("main-chart");
    if (!container || drawToolbar) return;
    drawToolbar = document.createElement("div");
    drawToolbar.className = "draw-toolbar hidden";
    drawToolbar.setAttribute("role", "toolbar");
    drawToolbar.setAttribute("aria-label", "Selected drawing");
    const swatches = DE.PALETTE.map((c) => `<button type="button" class="draw-swatch" data-color="${c}" style="--sw:${c}" aria-label="Colour ${c}"></button>`).join("");
    drawToolbar.innerHTML =
      `<div class="draw-tb-group">${swatches}</div>` +
      `<div class="draw-tb-sep"></div>` +
      `<div class="draw-tb-group">${[1, 2, 3].map((w) => `<button type="button" class="draw-tb-btn" data-width="${w}" aria-label="Width ${w}"><span class="draw-tb-line" style="height:${w}px"></span></button>`).join("")}</div>` +
      `<div class="draw-tb-group">` +
      `<button type="button" class="draw-tb-btn" data-dash="solid" aria-label="Solid"><span class="draw-tb-line"></span></button>` +
      `<button type="button" class="draw-tb-btn" data-dash="dashed" aria-label="Dashed"><span class="draw-tb-line dashed"></span></button>` +
      `<button type="button" class="draw-tb-btn" data-dash="dotted" aria-label="Dotted"><span class="draw-tb-line dotted"></span></button>` +
      `</div><div class="draw-tb-sep"></div>` +
      `<button type="button" class="draw-tb-btn" data-act="lock" aria-label="Lock"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg></button>` +
      `<button type="button" class="draw-tb-btn" data-act="copy" aria-label="Duplicate"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/></svg></button>` +
      `<button type="button" class="draw-tb-btn danger" data-act="delete" aria-label="Delete"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg></button>`;
    drawToolbar.addEventListener("pointerdown", (e) => e.stopPropagation());
    drawToolbar.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      const id = drawState.selected;
      if (!btn || !id) return;
      if (btn.dataset.color) { updateDrawing(id, { color: btn.dataset.color }); rememberStyle({ color: btn.dataset.color }); }
      else if (btn.dataset.width) { updateDrawing(id, { width: Number(btn.dataset.width) }); rememberStyle({ width: Number(btn.dataset.width) }); }
      else if (btn.dataset.dash) { updateDrawing(id, { dash: btn.dataset.dash }); rememberStyle({ dash: btn.dataset.dash }); }
      else if (btn.dataset.act === "lock") {
        const d = drawState.drawings.find((x) => x.id === id);
        updateDrawing(id, { locked: !(d && d.locked) });
      } else if (btn.dataset.act === "copy") duplicateDrawing(id);
      else if (btn.dataset.act === "delete") removeDrawing(id);
    });
    container.appendChild(drawToolbar);
  }

  function rememberStyle(patch) {
    drawState.style = { ...currentDrawStyle(), ...patch };
    writeDrawPref("drawStyle", drawState.style);
  }

  function positionDrawToolbar(d) {
    if (!drawToolbar) return;
    if (!d || dragState || handleDragState || drawState.tool !== "cursor") { drawToolbar.classList.add("hidden"); return; }
    const P = drawingPx(d);
    if (!P) { drawToolbar.classList.add("hidden"); return; }
    const size = paneSize();
    const xs = P.map((p) => p.x), ys = P.map((p) => p.y);
    const midX = Math.max(0, Math.min(size.w, (Math.min(...xs) + Math.max(...xs)) / 2));
    const top = Math.min(...ys);
    drawToolbar.classList.remove("hidden");
    const tw = drawToolbar.offsetWidth || 300, th = drawToolbar.offsetHeight || 36;
    const left = Math.max(4, Math.min(size.w - tw - 4, midX - tw / 2));
    const y = top - th - 14 >= 4 ? top - th - 14 : Math.min(size.h - th - 4, Math.max(...ys) + 14);
    drawToolbar.style.transform = `translate(${Math.round(left)}px, ${Math.round(y)}px)`;
    drawToolbar.querySelectorAll("[data-color]").forEach((b) => b.classList.toggle("on", (d.color || DE.PALETTE[0]) === b.dataset.color));
    drawToolbar.querySelectorAll("[data-width]").forEach((b) => b.classList.toggle("on", (d.width || 2) === Number(b.dataset.width)));
    drawToolbar.querySelectorAll("[data-dash]").forEach((b) => b.classList.toggle("on", (d.dash || "solid") === b.dataset.dash));
    const lock = drawToolbar.querySelector('[data-act="lock"]');
    lock.classList.toggle("on", !!d.locked);
    lock.setAttribute("aria-pressed", String(!!d.locked));
  }

  // Spegne ogni indicatore che vive sul prezzo (livelli strutturali, EMA,
  // Bollinger, VWAP, Fibonacci, retta d'angolo, indicatori custom "overlay"
  // dalla libreria pandas-ta) — RSI/MACD/Stocastico restano fuori, hanno un
  // riquadro proprio e non sono "sul prezzo".
  function clearAllPriceIndicators() {
    const priceLayerKeys = Object.keys(state.layers).filter(
      (k) => k !== "rsi" && k !== "macd" && k !== "stoch"
    );
    let changed = false;
    priceLayerKeys.forEach((k) => {
      if (state.layers[k]) { state.layers[k] = false; changed = true; }
    });
    document.querySelectorAll("[data-layer]").forEach((input) => {
      if (priceLayerKeys.includes(input.dataset.layer)) input.checked = false;
    });
    const hadOverlay = state.customIndicators.some((c) => c.kind === "overlay");
    if (hadOverlay) {
      state.customIndicators = state.customIndicators.filter((c) => c.kind !== "overlay");
      localStorage.setItem("customIndicators", JSON.stringify(state.customIndicators));
      changed = true;
    }
    if (!changed) return;
    render();
    requestAnimationFrame(() => resizeAllCharts());
    savePreferences();
    refreshCustomIndicators();
    const search = el("indicator-library-search");
    renderIndicatorLibraryList(search ? search.value : "");
    renderActiveIndicatorChips();
    renderChartIndicatorLegend();
  }

  function loadDrawingsForSymbol() {
    clearAllDrawingPrimitives();
    clearFractalReplays();
    drawState.drawings = [];
    drawState.selected = null;
    drawState.hover = null;
    drawHistory.undo = [];
    drawHistory.redo = [];
    const key = drawStorageKey();
    if (key) {
      const local = readLocalDrawings(key);
      drawState.drawings = local.drawings;
      drawState.updatedAt = local.updated_at;
      syncDrawingsFromServer(key, local, (remote) => {
        if (drawStorageKey() !== key) return; // another chart by now
        drawState.drawings = remote.drawings;
        drawState.updatedAt = remote.updated_at;
        reattachAll();
        renderDrawingsList();
        bumpDraw();
      });
    }
    reattachAll();
    renderDrawingsList();
    // The fractals need the candles of the new chart: after it is drawn.
    requestAnimationFrame(() => restoreFractals());
    bumpDraw();
  }

  function syncCurrentDrawings() {
    const key = drawStorageKey();
    if (!key) return;
    syncDrawingsFromServer(key, readLocalDrawings(key), (remote) => {
      if (drawStorageKey() !== key) return;
      drawState.drawings = remote.drawings;
      drawState.updatedAt = remote.updated_at;
      reattachAll();
      renderDrawingsList();
      bumpDraw();
    });
    restoreFractals();
  }

  function newDrawingId() {
    return `d${Date.now()}${Math.random().toString(36).slice(2, 7)}`;
  }

  // Text written on the chart itself, not in window.prompt (which on a
  // phone covers the chart): an input at the point, Enter to keep, Escape
  // to drop. A double click on a text drawing opens it again.
  function openDrawTextInput(point, initial, onDone) {
    const container = el("main-chart");
    if (!container) return;
    const x = timeToX(point.time), y = priceToY(point.price);
    const input = document.createElement("input");
    input.type = "text";
    input.className = "draw-text-input";
    input.value = initial || "";
    input.placeholder = "Text";
    input.setAttribute("aria-label", "Drawing text");
    input.style.left = `${Math.max(4, (x || 0) + 6)}px`;
    input.style.top = `${Math.max(4, (y || 0) - 26)}px`;
    let done = false;
    const finish = (keep) => {
      if (done) return;
      done = true;
      const value = input.value.trim();
      input.remove();
      onDone(keep ? value : null);
    };
    input.addEventListener("keydown", (e) => {
      e.stopPropagation();
      if (e.key === "Enter") finish(true);
      else if (e.key === "Escape") finish(false);
    });
    input.addEventListener("blur", () => finish(true));
    input.addEventListener("pointerdown", (e) => e.stopPropagation());
    container.appendChild(input);
    setTimeout(() => input.focus(), 0);
  }

  function addDrawing(drawing) {
    pushDrawHistory();
    drawState.drawings.push(drawing);
    attachDrawing(drawing);
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) appearAt[drawing.id] = performance.now();
    drawState.selected = drawing.id;
    saveDrawings();
    renderDrawingsList();
    bumpDraw();
  }

  function finalizeDrawing() {
    const type = drawState.tool;
    const points = drawState.pending;
    drawState.pending = [];
    const keepTool = drawState.sticky;
    const done = () => { if (!keepTool) setDrawTool("cursor"); else bumpDraw(); };

    // The fractal is not a shape: it copies a real stretch of history right
    // after the last candle. It lives in its own list (fractalReplays).
    if (type === "fractal") {
      createFractalReplay(points[0], points[1]);
      done();
      return;
    }
    const base = { id: newDrawingId(), type, points, v: 2, ...currentDrawStyle() };
    if (type === "text") {
      done();
      openDrawTextInput(points[0], "", (text) => { if (text) addDrawing({ ...base, text }); });
      return;
    }
    if (type === "range") base.text = formatRangeLabel(points[0], points[1]);
    addDrawing(base);
    done();
  }

  function editDrawingText(d) {
    openDrawTextInput(d.points[0], d.text || "", (text) => {
      if (text === null) return;
      if (!text) removeDrawing(d.id);
      else updateDrawing(d.id, { text });
    });
  }

  // ---- fractals: saved like the drawings, with their copied candles ----
  function saveFractals() {
    const key = fractalStorageKey();
    if (!key) return;
    const list = fractalReplays.map((f) => ({ id: f.id, interval: f.interval, count: f.count, projected: f.projected }));
    const body = { drawings: list, updated_at: Date.now() };
    try { localStorage.setItem(key, JSON.stringify(body)); } catch { /* ignore */ }
    scheduleDrawSync(key, list, body.updated_at);
  }

  function restoreFractals() {
    const key = fractalStorageKey();
    if (!key || !mainChart) return;
    const mount = (list) => {
      if (fractalStorageKey() !== key) return;
      clearFractalReplays();
      (list || []).forEach((f) => {
        if (Array.isArray(f.projected) && f.projected.length) mountFractal(f.projected, f.interval, f.count || f.projected.length, f.id);
      });
    };
    const local = readLocalDrawings(key);
    mount(local.drawings);
    syncDrawingsFromServer(key, local, (remote) => mount(remote.drawings));
  }

  // Lightweight Charts' own subscribeClick() disambiguates click-vs-drag
  // internally, and with panning enabled on the chart, ordinary mouse
  // jitter between press and release can get swallowed as a micro-pan
  // instead of firing a click — the exact symptom reported ("clicco e non
  // succede niente"). Capturing pointerdown/up directly, with our own
  // small-movement tolerance, sidesteps that entirely — and pan/zoom are
  // disabled for the duration so the chart doesn't drift under the cursor
  // while placing a point (see setDrawTool).
  function clearFractalReplays() {
    fractalReplays.forEach(({ series, label }) => {
      try { mainChart.removeSeries(series); } catch { /* gia' rimossa */ }
      label.remove();
    });
    fractalReplays = [];
    selectedFractalId = null;
    fractalDragState = null;
  }

  function removeFractalReplay(id) {
    const entry = fractalReplays.find((f) => f.id === id);
    if (!entry) return;
    try { mainChart.removeSeries(entry.series); } catch { /* gia' rimossa */ }
    entry.label.remove();
    fractalReplays = fractalReplays.filter((f) => f.id !== id);
    if (selectedFractalId === id) selectedFractalId = null;
    saveFractals();
  }

  // Piazza la label ("Frattale ✕") sopra l'inizio della copia, e la
  // riposiziona ad ogni pan/zoom/resize — non e' un elemento del canvas dei
  // disegni, e' un div assoluto sopra #main-chart, come il badge di rimozione
  // degli overlay e la legenda degli indicatori.
  function repositionFractalLabels() {
    if (!mainChart || !fractalReplays.length) return;
    fractalReplays.forEach(({ label, startTime }, i) => {
      const x = mainChart.timeScale().timeToCoordinate(startTime);
      if (x === null) { label.classList.add("hidden"); return; }
      // Impilate una sopra l'altra quando piu' frattali cadono vicini, invece
      // di sovrapporsi illeggibili.
      label.style.left = `${Math.max(0, x)}px`;
      label.style.top = `${8 + i * 22}px`;
      label.classList.remove("hidden");
    });
  }

  function selectFractal(id) {
    selectedFractalId = id;
    fractalReplays.forEach((f) => f.label.classList.toggle("selected", f.id === id));
  }

  function deselectFractal() {
    if (!selectedFractalId) return;
    selectedFractalId = null;
    fractalReplays.forEach((f) => f.label.classList.remove("selected"));
  }

  function createFractalReplay(p1, p2) {
    const analysis = state.data && state.data.timeframes && state.data.timeframes[state.activeTimeframe];
    const candles = analysis && analysis.candles;
    if (!candles || candles.length < 2) return;
    const t0 = Math.min(p1.time, p2.time);
    const t1 = Math.max(p1.time, p2.time);
    const segment = candles.filter((c) => c.time >= t0 && c.time <= t1);
    if (segment.length < 3) {
      const banner = el("error-banner");
      banner.textContent = "Select a wider range: at least 3 candles are needed to copy.";
      banner.classList.remove("hidden");
      return;
    }
    const baseClose = segment[0].close;
    if (!baseClose) return;
    const lastCandle = candles[candles.length - 1];
    const interval = candles.length >= 2
      ? candles[candles.length - 1].time - candles[candles.length - 2].time
      : 86400;

    const projected = segment.map((c, i) => {
      const scale = (v) => lastCandle.close * (v / baseClose);
      return {
        time: lastCandle.time + interval * (i + 1),
        open: scale(c.open), high: scale(c.high), low: scale(c.low), close: scale(c.close),
      };
    });

    mountFractal(projected, interval, segment.length);
    saveFractals();
  }

  // Puts a copy on the chart: from a new selection, or from what was saved.
  function mountFractal(projected, interval, count, givenId) {
    const id = givenId || `fr${Date.now()}${Math.random().toString(36).slice(2, 7)}`;
    const series = mainChart.addCandlestickSeries({
      upColor: "rgba(140,120,255,0.45)",
      downColor: "rgba(140,120,255,0.20)",
      borderUpColor: "#8c78ff",
      borderDownColor: "#8c78ff",
      wickUpColor: "#8c78ff",
      wickDownColor: "#8c78ff",
      priceLineVisible: false,
      lastValueVisible: false,
    });
    series.setData(projected);

    const container = el("main-chart");
    const label = document.createElement("div");
    label.className = "fractal-label";
    label.title = "Drag here or directly on the candles to move the fractal";
    label.innerHTML = `<span>Fractal — ${count} candles copied</span>` +
      `<button type="button" class="fractal-label-close" title="Remove">✕</button>`;
    label.querySelector(".fractal-label-close").addEventListener("click", (e) => {
      e.stopPropagation();
      removeFractalReplay(id);
    });
    // La label resta un secondo modo di afferrare il frattale (comodo
    // quando le candele sono strette), ma il trascinamento vero avviene
    // sulle candele stesse — vedi hitTestFractal/startFractalDrag, agganciati
    // al pointerdown del grafico in bindDrawClickCapture.
    label.addEventListener("mousedown", (e) => {
      if (e.target.closest(".fractal-label-close")) return;
      e.preventDefault();
      e.stopPropagation();
      const entry = fractalReplays.find((f) => f.id === id);
      if (entry) startFractalDrag(entry);
    });
    container.appendChild(label);

    fractalReplays.push({ id, series, label, startTime: projected[0].time, interval, projected, count });
    repositionFractalLabels();
  }

  // Un frattale e' "colpito" se il punto cade nel suo intervallo di tempo E
  // nella fascia di prezzo che occupa (massimo/minimo di tutta la copia, con
  // un margine): un candlestick non ha un unico hit-test come una linea, e
  // provare a colpire esattamente un corpo/stoppino sarebbe fragile — questo
  // basta a renderlo afferrabile ovunque sopra le sue barre.
  const FRACTAL_HIT_PAD_PX = 8;

  function hitTestFractal(time, py) {
    for (let i = fractalReplays.length - 1; i >= 0; i--) {
      const entry = fractalReplays[i];
      const times = entry.projected.map((p) => p.time);
      const tMin = Math.min(...times), tMax = Math.max(...times);
      if (time < tMin || time > tMax) continue;
      const highs = entry.projected.map((p) => p.high);
      const lows = entry.projected.map((p) => p.low);
      const yTop = entry.series.priceToCoordinate(Math.max(...highs));
      const yBottom = entry.series.priceToCoordinate(Math.min(...lows));
      if (yTop === null || yBottom === null) continue;
      if (py >= yTop - FRACTAL_HIT_PAD_PX && py <= yBottom + FRACTAL_HIT_PAD_PX) return entry;
    }
    return null;
  }

  function startFractalDrag(entry) {
    if (!lastCrosshairPoint) return;
    const price = candleSeries.coordinateToPrice(lastCrosshairPoint.y);
    if (price === null) return;
    fractalDragState = {
      id: entry.id,
      startTime: lastCrosshairPoint.time,
      startPrice: price,
      startPixelX: lastCrosshairPoint.x,
      baseLabelLeft: parseFloat(entry.label.style.left) || 0,
      originalProjected: entry.projected.map((p) => ({ ...p })),
      moved: false,
    };
    // Senza disattivarlo, il grafico sotto interpreta lo stesso trascinamento
    // anche come pan/zoom: le due logiche si accavallavano, ognuna spostando
    // la copia (o il grafico) a modo suo nello stesso gesto.
    mainChart.applyOptions({ handleScroll: false, handleScale: false });
  }

  // setData() su una serie puo' far scattare un nuovo evento di crosshair-move
  // in modo sincrono (il grafico si ridisegna, il cursore risulta "ancora"
  // sopra dati appena cambiati) — senza questa guardia quell'evento richiama
  // updateFractalDrag() da dentro se stessa, ricorsione che non si ferma mai
  // finche' non esaurisce lo stack ("Maximum call stack size exceeded").
  let _updatingFractalDrag = false;

  function updateFractalDrag() {
    if (_updatingFractalDrag) return;
    if (!fractalDragState || !lastCrosshairPoint) return;
    const entry = fractalReplays.find((f) => f.id === fractalDragState.id);
    if (!entry) { fractalDragState = null; return; }
    const price = candleSeries.coordinateToPrice(lastCrosshairPoint.y);
    if (price === null) return;
    const dTimeRaw = lastCrosshairPoint.time - fractalDragState.startTime;
    const deltaBars = Math.round(dTimeRaw / entry.interval);
    const dPrice = price - fractalDragState.startPrice;
    if (Math.abs(dTimeRaw) >= entry.interval || Math.abs(dPrice) > 0) fractalDragState.moved = true;
    const shifted = fractalDragState.originalProjected.map((p) => ({
      time: p.time + deltaBars * entry.interval,
      open: p.open + dPrice, high: p.high + dPrice, low: p.low + dPrice, close: p.close + dPrice,
    }));
    _updatingFractalDrag = true;
    try {
      entry.series.setData(shifted);
    } finally {
      _updatingFractalDrag = false;
    }
    entry.projected = shifted;
    entry.startTime = shifted[0].time;
    // La label segue il cursore in pixel puri (differenza dalla posizione X
    // del crosshair all'inizio del trascinamento) invece di essere ricavata
    // da timeToCoordinate ad ogni fotogramma: richiamato subito dopo
    // setData() quel valore era di un fotogramma indietro e la label
    // tornava a saltellare verso la posizione di partenza.
    entry.label.style.left = `${Math.max(0, fractalDragState.baseLabelLeft + (lastCrosshairPoint.x - fractalDragState.startPixelX))}px`;
  }

  function finishFractalDrag() {
    if (!fractalDragState) return;
    if (!fractalDragState.moved) selectFractal(fractalDragState.id);
    else saveFractals();
    fractalDragState = null;
    if (mainChart) mainChart.applyOptions({ handleScroll: drawState.tool === "cursor", handleScale: drawState.tool === "cursor" });
    // Niente riallineamento verticale della label da timeToCoordinate qui,
    // stesso motivo di sopra — resta dove il trascinamento l'ha lasciata; il
    // prossimo pan/zoom/resize la ricalcola comunque dal tempo vero.
  }

  // Pointer events on the chart, read where the pointer really is (not the
  // chart's crosshair, which a finger does not move). Placing a point: a
  // click or a tap; a two-point tool also takes press-drag-release. Moving
  // a drawing or one of its points keeps the pointer captured, so it
  // follows over the scales and outside the chart too.
  const DRAW_CLICK_TOLERANCE_PX = 6;
  let lastPointerType = "mouse";

  function bindDrawClickCapture() {
    const container = el("main-chart");
    let down = null; // { x, y, point, onPane, startedDrag }

    const local = (e) => {
      const rect = container.getBoundingClientRect();
      return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };
    const onPane = (p) => {
      const size = paneSize();
      return p.x >= 0 && p.y >= 0 && p.x <= size.w && p.y <= size.h;
    };
    // Controls that sit over the chart (this toolbar, the text field, the
    // fractal labels, the legend chips) handle their own pointer.
    const OVER_CHART_UI = ".draw-toolbar, .draw-text-input, .fractal-label, .chart-top-left, .overlay-remove-badge, button, input, a";
    const onUi = (e) => !!(e.target && e.target.closest && e.target.closest(OVER_CHART_UI));
    const lockChart = () => mainChart.applyOptions({ handleScroll: false, handleScale: false });
    const unlockChart = () => mainChart.applyOptions({ handleScroll: drawState.tool === "cursor", handleScale: drawState.tool === "cursor" });

    container.addEventListener("pointermove", (e) => {
      lastPointerType = e.pointerType || "mouse";
      const p = local(e);
      drawPointer = p;
      if (handleDragState) {
        const pt = pointerToPoint(p.x, p.y);
        if (!pt) return;
        const d = handleDragState.drawing;
        d.points = handleDragState.originalPoints.map((q, i) => (i === handleDragState.handleIndex ? pt : { ...q }));
        if (d.type === "range") d.text = formatRangeLabel(d.points[0], d.points[1]);
        repositionDrawingPrimitives(d);
        handleDragState.moved = true;
        bumpDraw();
        return;
      }
      if (dragState) {
        const logical = mainChart.timeScale().coordinateToLogical(p.x);
        const price = candleSeries.coordinateToPrice(p.y);
        if (logical === null || price === null) return;
        const dl = logical - dragState.startLogical;
        const dPrice = price - dragState.startPrice;
        const d = dragState.drawing;
        d.points = dragState.originalPoints.map((q) => {
          const l0 = timeMapper.timeToLogical(q.time);
          return { time: l0 === null ? q.time : timeMapper.logicalToTime(l0 + dl), price: q.price + dPrice };
        });
        if (d.type === "range") d.text = formatRangeLabel(d.points[0], d.points[1]);
        repositionDrawingPrimitives(d);
        dragState.moved = true;
        bumpDraw();
        return;
      }
      if (drawState.tool !== "cursor") { bumpDraw(); return; }
      if (fractalDragState) return;
      const handleHit = findHitHandle(p.x, p.y);
      const hit = handleHit ? handleHit.drawing : findHitDrawing(p.x, p.y);
      setDrawHover(hit ? hit.id : null);
      container.style.cursor = handleHit ? "grab" : hit ? (hit.locked ? "default" : "move") : "default";
    });

    container.addEventListener("pointerleave", () => {
      if (dragState || handleDragState) return;
      drawPointer = null;
      setDrawHover(null);
      bumpDraw();
    });

    container.addEventListener("pointerdown", (e) => {
      if (e.button !== undefined && e.button > 0) return;
      if (onUi(e)) { down = null; return; }
      lastPointerType = e.pointerType || "mouse";
      const p = local(e);
      drawPointer = p;
      down = { x: p.x, y: p.y, onPane: onPane(p), point: onPane(p) ? pointerToPoint(p.x, p.y) : null };
      if (!down.onPane || !state.data) return;

      if (drawState.tool !== "cursor") {
        // placing: the chart must not pan under the pointer
        e.stopPropagation();
        try { container.setPointerCapture(e.pointerId); } catch { /* old browser */ }
        return;
      }

      // 1. Handle hit → move one point
      const handleHit = findHitHandle(p.x, p.y);
      if (handleHit) {
        pushDrawHistory();
        handleDragState = { drawing: handleHit.drawing, handleIndex: handleHit.handleIndex, originalPoints: handleHit.drawing.points.map((q) => ({ ...q })) };
        lockChart();
        e.stopPropagation();
        try { container.setPointerCapture(e.pointerId); } catch { /* ignore */ }
        bumpDraw();
        return;
      }

      // 2. Body hit → select, and move it unless it is locked
      const hit = findHitDrawing(p.x, p.y);
      if (hit) {
        drawState.selected = hit.id;
        deselectFractal();
        bumpDraw();
        if (hit.locked) { e.stopPropagation(); return; }
        const logical = mainChart.timeScale().coordinateToLogical(p.x);
        const startPrice = candleSeries.coordinateToPrice(p.y);
        if (logical !== null && startPrice !== null) {
          pushDrawHistory();
          dragState = { drawing: hit, startLogical: logical, startPrice, originalPoints: hit.points.map((q) => ({ ...q })) };
          lockChart();
          e.stopPropagation();
          try { container.setPointerCapture(e.pointerId); } catch { /* ignore */ }
        }
        return;
      }

      // 3. A fractal hit directly on its candles → drag it (time and price)
      if (lastCrosshairPoint) {
        const fractalHit = hitTestFractal(xToTime(p.x), p.y);
        if (fractalHit) startFractalDrag(fractalHit);
      }
    }, true);

    const endPointer = (e) => {
      if (!down && !dragState && !handleDragState && !fractalDragState && onUi(e)) return;
      const p = local(e);
      const start = down;
      down = null;
      const moved = start ? Math.hypot(p.x - start.x, p.y - start.y) > DRAW_CLICK_TOLERANCE_PX : false;
      try { container.releasePointerCapture(e.pointerId); } catch { /* not captured */ }

      if (handleDragState) {
        const changed = handleDragState.moved;
        handleDragState = null;
        unlockChart();
        if (changed) saveDrawings(); else drawHistory.undo.pop();
        bumpDraw();
        return;
      }
      if (dragState) {
        const changed = dragState.moved;
        dragState = null;
        unlockChart();
        if (changed) saveDrawings(); else drawHistory.undo.pop();
        bumpDraw();
        return;
      }
      if (fractalDragState) { finishFractalDrag(); return; }
      if (!start || !start.onPane || !state.data) return;

      if (drawState.tool === "cursor") {
        if (moved) return; // a pan of the chart
        if (!findHitDrawing(p.x, p.y)) { drawState.selected = null; bumpDraw(); }
        deselectFractal();
        return;
      }

      const end = pointerToPoint(p.x, p.y);
      if (!end) return;
      const needed = DRAW_TOOL_POINTS[drawState.tool];
      if (moved && start.point && drawState.pending.length === 0 && needed === 2) {
        // press-drag-release: both points in one gesture
        drawState.pending = [start.point, end];
      } else {
        drawState.pending.push(end);
      }
      if (drawState.pending.length >= needed) finalizeDrawing();
      bumpDraw();
    };
    container.addEventListener("pointerup", endPointer, true);
    container.addEventListener("pointercancel", (e) => {
      down = null;
      try { container.releasePointerCapture(e.pointerId); } catch { /* ignore */ }
      if (handleDragState || dragState) {
        const st = handleDragState || dragState;
        st.drawing.points = st.originalPoints;
        repositionDrawingPrimitives(st.drawing);
        handleDragState = null; dragState = null;
        drawHistory.undo.pop();
        unlockChart();
        bumpDraw();
      }
    });

    container.addEventListener("dblclick", (e) => {
      if (drawState.tool !== "cursor") return;
      const p = local(e);
      const hit = findHitDrawing(p.x, p.y);
      if (hit && hit.type === "text" && !hit.locked) { e.stopPropagation(); editDrawingText(hit); }
    });

    document.addEventListener("keydown", (e) => {
      const tag = document.activeElement?.tagName;
      const typing = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || document.activeElement?.isContentEditable;
      if (e.key === "Escape") {
        if (drawState.tool !== "cursor") setDrawTool("cursor");
        else { drawState.selected = null; deselectFractal(); bumpDraw(); }
        return;
      }
      if (typing) return;
      const mod = e.ctrlKey || e.metaKey;
      if (mod && (e.key === "z" || e.key === "Z")) {
        e.preventDefault();
        if (e.shiftKey) redoDrawing(); else undoDrawing();
        return;
      }
      if (mod && (e.key === "y" || e.key === "Y")) { e.preventDefault(); redoDrawing(); return; }
      if (e.key === "Delete" || e.key === "Backspace") {
        if (drawState.selected) { removeDrawing(drawState.selected); drawState.selected = null; }
        if (selectedFractalId) removeFractalReplay(selectedFractalId);
      }
    });
  }

  // ── Marker click popup ────────────────────────────────────────────────────
  // Ogni tipo di segnale contestuale ha una descrizione e un peso 1-10.
  const MARKER_INFO = {
    "↘ Trend slowing": {
      desc: "EMA20 was accelerating upward but is now slowing. The current trend's momentum is fading — may precede a pause or a reversal.",
      score: 6,
    },
    "↗ Trend slowing": {
      desc: "EMA20 was accelerating downward but is now slowing. Bearish momentum is weakening — potential short-term floor.",
      score: 6,
    },
    "⚡ Strong trend ↑": {
      desc: "EMA slope in strong bullish acceleration (>0.3 ATR per bar). High trend momentum: pullbacks are typically short and shallow.",
      score: 8,
    },
    "⚡ Strong trend ↓": {
      desc: "EMA slope in strong bearish acceleration. Heavy selling pressure: avoid counter-trend longs without confirmation.",
      score: 8,
    },
    "⚠ Exhaustion ↑": {
      desc: "Three consecutive bullish candles with shrinking bodies — the rally is losing steam. Common before a pullback or consolidation.",
      score: 5,
    },
    "⚠ Exhaustion ↓": {
      desc: "Three consecutive bearish candles with shrinking bodies — the sell-off is losing steam. Potential short-term technical bounce.",
      score: 5,
    },
    "◼ Contraction": {
      desc: "Inside bar: high and low contained within the previous candle, range < 0.6 ATR. Volatility compression — often precedes a directional breakout.",
      score: 7,
    },
    "→ Momentum ↑": {
      desc: "Bullish marubozu: body > 88% of the range, no significant wicks. Buyers in full control for the whole candle.",
      score: 7,
    },
    "→ Momentum ↓": {
      desc: "Bearish marubozu: sellers dominate without a breather. Often continues into the next candle.",
      score: 7,
    },
    "↙ RSI+ saturated": {
      desc: "RSI > 72 + bearish candle with a long upper wick. Double overbought signal: price tested higher levels but got rejected.",
      score: 8,
    },
    "↗ RSI− exhausted": {
      desc: "RSI < 28 + bullish candle with a long lower wick. Double oversold signal: price tested the lows but bounced.",
      score: 8,
    },
    "~ Indecision": {
      desc: "Neutral RSI (43-57) + small body (<35% of the range). No directional strength: better to wait for a confirmation candle before entering.",
      score: 3,
    },
    "IN long": { desc: "Long entry signal from the active strategy.", score: 9 },
    "IN short": { desc: "Short entry signal from the active strategy.", score: 9 },
    "OUT": { desc: "Exit signal for the current position.", score: 8 },
  };

  function scoreColor(s) {
    if (s >= 8) return "#00d68f";
    if (s >= 6) return "#f2a93b";
    return "#4fd8a8";
  }

  function showMarkerPopup(marker, px, py) {
    const popup = el("marker-popup");
    const info = MARKER_INFO[marker.text] || { desc: "Automatic chart signal.", score: 5 };
    const fillColor = scoreColor(info.score);
    popup.innerHTML = `
      <div class="marker-popup-header">
        <span class="marker-popup-label" style="color:${marker.color}">${marker.text}</span>
        <button class="marker-popup-close" onclick="document.getElementById('marker-popup').classList.add('hidden')" aria-label="Close">×</button>
      </div>
      <div class="marker-popup-desc">${info.desc}</div>
      <div class="marker-popup-score">
        <span class="marker-popup-score-label">PESO</span>
        <div class="marker-popup-score-bar"><div class="marker-popup-score-fill" style="width:${info.score*10}%;background:${fillColor}"></div></div>
        <span class="marker-popup-score-num" style="color:${fillColor}">${info.score}/10</span>
      </div>`;
    // Posiziona vicino al click, tenendosi nei bordi
    const vw = window.innerWidth, vh = window.innerHeight;
    const W = 280, H = 160;
    let left = px + 14, top = py + 14;
    if (left + W > vw - 8) left = px - W - 8;
    if (top + H > vh - 8) top = py - H - 8;
    popup.style.left = `${Math.max(8, left)}px`;
    popup.style.top  = `${Math.max(8, top)}px`;
    popup.classList.remove("hidden");
  }

  // ── Motore previsionale breakout (multi-timeframe) ────────────────────────

  // Gerarchia: per ogni intervallo, quale è il contesto (1 livello su) e il macro (2 livelli su)
  const TF_HIERARCHY = {
    "1m":  { context: "15m", macro: "1h"  },
    "5m":  { context: "1h",  macro: "4h"  },
    "15m": { context: "1h",  macro: "4h"  },
    "30m": { context: "4h",  macro: "1d"  },
    "1h":  { context: "4h",  macro: "1d"  },
    "4h":  { context: "1d",  macro: "1w"  },
    "1d":  { context: "1w",  macro: "1M"  },
    "2d":  { context: "1w",  macro: "1M"  },
    "3d":  { context: "1w",  macro: "1M"  },
    "5d":  { context: "1M",  macro: null  },
    "1w":  { context: "1M",  macro: null  },
    "1M":  { context: null,  macro: null  },
  };

  // Trova l'analisi per intervallo (le chiavi di timeframes sono ID, non intervalli)
  function _analysisByInterval(intervalStr) {
    if (!state.data || !state.data.timeframes) return null;
    return Object.values(state.data.timeframes).find((a) => a.interval === intervalStr) || null;
  }

  // Calcola direzione di trend per un dato insieme di candele e indicatori
  // Restituisce { dir: "bull"|"bear"|"neutral", pct, emaSlope, label }
  function _computeTrend(candles, indicators, label) {
    if (!candles || candles.length < 5) return null;
    const N = Math.min(50, candles.length);
    const recent = candles.slice(-N);

    // Priorità 1: slope EMA (usa EMA20 → EMA50 → qualsiasi EMA)
    const ema = findIndicator(indicators || [], "EMA20")
             || findIndicator(indicators || [], "EMA50")
             || findIndicator(indicators || [], "EMA");
    if (ema) {
      const vals = seriesFromIndicatorValues(candles, ema).filter((d) => d.value != null).slice(-10);
      if (vals.length >= 4) {
        const slope = (vals[vals.length - 1].value - vals[0].value) / vals[0].value * 100;
        const dir = slope > 0.15 ? "bull" : slope < -0.15 ? "bear" : "neutral";
        const strength = Math.min(1, Math.abs(slope) / 3);
        return { dir, strength, label, detail: `EMA slope ${slope > 0 ? "+" : ""}${slope.toFixed(2)}%` };
      }
    }

    // Fallback: prezzo first vs last sulle ultime N candele
    const first = recent[0].close, last = recent[recent.length - 1].close;
    const pct = (last - first) / first * 100;
    const dir = pct > 0.5 ? "bull" : pct < -0.5 ? "bear" : "neutral";
    const strength = Math.min(1, Math.abs(pct) / 5);
    return { dir, strength, label, detail: `${pct > 0 ? "+" : ""}${pct.toFixed(2)}% over ${N} candles` };
  }

  // ── Phase detection (Agent 1) ─────────────────────────────────────────────
  function _detectPhase(candles, swings) {
    if (candles.length < 20 || swings.highs.length < 2 || swings.lows.length < 2)
      return { phase: "LATERALE", trend: "flat", confidence: 0.2, retracePct: 0, exhaustSignals: 0 };

    const bodyOf  = c => Math.abs(c.close - c.open);
    const rangeOf = c => c.high - c.low || 0.0001;
    const wickLo  = c => Math.min(c.open, c.close) - c.low;
    const wickHi  = c => c.high - Math.max(c.open, c.close);
    const bodyRatio = c => bodyOf(c) / rangeOf(c);

    const H = swings.highs, L = swings.lows;
    let bullScore = 0, bearScore = 0;
    const rH = H.slice(-3), rL = L.slice(-3);
    for (let k = 1; k < rH.length; k++) rH[k].price > rH[k-1].price ? bullScore++ : bearScore++;
    for (let k = 1; k < rL.length; k++) rL[k].price > rL[k-1].price ? bullScore++ : bearScore++;
    let trend = bullScore >= bearScore + 2 ? "bull" : bearScore >= bullScore + 2 ? "bear" : "flat";

    if (trend === "flat") return { phase: "LATERALE", trend, confidence: 0.3, retracePct: 0, exhaustSignals: 0 };

    const last  = candles[candles.length - 1];
    const last3 = candles.slice(-3);

    const apexPoint = trend === "bull" ? H.slice(-1)[0] : L.slice(-1)[0];
    const basePoint  = trend === "bull" ? L.slice(-2)[0] : H.slice(-2)[0];
    const impulseRange = basePoint ? Math.abs(apexPoint.price - basePoint.price) : 0;
    const currentDelta = trend === "bull" ? apexPoint.price - last.close : last.close - apexPoint.price;
    const retracePct   = impulseRange > 0 ? Math.max(0, currentDelta / impulseRange) : 0;

    const retrSwings = (trend === "bull" ? L : H).slice(-3);
    let exhaustSignals = 0;
    if (retrSwings.length === 3) {
      const [s0, s1, s2] = retrSwings;
      const sp = (a, b) => Math.abs(b.price - a.price) / Math.max(1, b.i - a.i);
      if (sp(s1, s2) < sp(s0, s1) * 0.70) exhaustSignals++;
      const d1 = s1.i - s0.i, d2 = s2.i - s1.i;
      if (d1 > 0 && d2 < d1 * 0.65) exhaustSignals++;
    }
    const wicks = last3.map(c => rangeOf(c) > 0 ? (trend === "bull" ? wickLo(c) : wickHi(c)) / rangeOf(c) : 0);
    if (wicks[2] > wicks[0] * 1.4) exhaustSignals++;
    const prev5avg = candles.slice(-8, -3).reduce((s, c) => s + bodyOf(c), 0) / 5;
    const last3avg = last3.reduce((s, c) => s + bodyOf(c), 0) / 3;
    if (prev5avg > 0 && last3avg < prev5avg * 0.40) exhaustSignals++;

    const lastRetracPeak = (trend === "bull" ? H : L).slice(-1)[0];
    const bosConfirmed = lastRetracPeak && (trend === "bull"
      ? last.close > lastRetracPeak.price
      : last.close < lastRetracPeak.price);

    const HH = H.slice(-2), HL = L.slice(-2);
    const structOk = trend === "bull"
      ? HH.length === 2 && HH[1].price > HH[0].price && HL.length === 2 && HL[1].price > HL[0].price
      : HH.length === 2 && HH[1].price < HH[0].price && HL.length === 2 && HL[1].price < HL[0].price;
    const avgBR = last3.reduce((s, c) => s + bodyRatio(c), 0) / 3;
    const trendCandles = trend === "bull" ? last3.filter(c => c.close > c.open).length : last3.filter(c => c.close < c.open).length;
    const isImpulse = structOk && avgBR >= 0.55 && trendCandles >= 2;

    if (bosConfirmed && retracePct > 0.10)
      return { phase: "PIVOT",        trend, confidence: 0.85, retracePct, exhaustSignals };
    if (exhaustSignals >= 2 && retracePct > 0.20)
      return { phase: "ESAURIMENTO",  trend, confidence: Math.min(0.95, 0.60 + exhaustSignals * 0.10), retracePct, exhaustSignals };
    if (retracePct > 0.236)
      return { phase: "RITRACCIAMENTO", trend, confidence: 0.75, retracePct, exhaustSignals };
    if (isImpulse)
      return { phase: "IMPULSO",      trend, confidence: 0.80, retracePct, exhaustSignals };
    return   { phase: "LATERALE",     trend, confidence: 0.40, retracePct, exhaustSignals };
  }

  // ── Impulse angle measurement (Agent 0 — highest priority) ───────────────
  // Misura l'angolo di ogni leg di swing (slope = prezzo/barra normalizzato per ATR)
  // e rileva quando l'angolo si appiattisce + le chiusure si comprimono.
  // Questa è la dinamica più importante: impulso ripido → decel angolare → compressione → rottura inversa.
  function _measureImpulseAngle(candles, swings) {
    const nil = { impulseDir: null, impulseAngle: 0, decelRatio: 1, isDecelerating: false, compression: 0, compressing: false };
    if (candles.length < 12) return nil;
    const atr = _atrAt(candles, candles.length - 1);
    if (atr <= 0) return nil;

    // Costruisce una sequenza di leg dai punti di swing ordinati per barra
    const pts = [];
    swings.highs.forEach(p => pts.push({ i: p.i, price: p.price }));
    swings.lows.forEach(p =>  pts.push({ i: p.i, price: p.price }));
    pts.sort((a, b) => a.i - b.i);

    const legs = [];
    for (let k = 1; k < pts.length; k++) {
      const bars = pts[k].i - pts[k - 1].i;
      if (bars < 1) continue;
      // slope normalizzato: unità di ATR per barra — è l'angolo del leg
      legs.push({ slope: (pts[k].price - pts[k - 1].price) / (bars * atr), bars });
    }
    if (legs.length < 2) return nil;

    // Confronta leg recenti vs leg precedenti
    const nR  = Math.min(3, Math.ceil(legs.length / 2));
    const rec = legs.slice(-nR);
    const prv = legs.slice(-nR * 2, -nR);

    const avgAbs = arr => arr.reduce((s, l) => s + Math.abs(l.slope), 0) / arr.length;
    const avgAbsRec = avgAbs(rec);
    const avgAbsPrv = prv.length > 0 ? avgAbs(prv) : avgAbsRec;
    const decelRatio = avgAbsPrv > 0.01 ? avgAbsRec / avgAbsPrv : 1;

    // Direzione dell'impulso che sta decelerando (dai leg precedenti)
    const prvNetSlope = prv.length > 0 ? prv.reduce((s, l) => s + l.slope, 0) / prv.length : 0;
    const impulseDir  = prvNetSlope > 0.12 ? "bull" : prvNetSlope < -0.12 ? "bear" : null;
    const impulseAngle = avgAbsPrv;

    // Decelerazione: leg recenti significativamente meno ripidi dei precedenti
    const isDecelerating = decelRatio < 0.62 && impulseAngle > 0.18;

    // Compressione: le ultime chiusure sono molto ravvicinate rispetto all'ATR
    const last8 = candles.slice(-Math.min(8, candles.length));
    const cls   = last8.map(c => c.close);
    const meanC = cls.reduce((a, b) => a + b, 0) / cls.length;
    const stdC  = Math.sqrt(cls.reduce((s, c) => s + (c - meanC) ** 2, 0) / cls.length);
    const compression = Math.max(0, Math.min(1, 1 - stdC / (atr * 0.9)));

    // Compressing: cluster di chiusure ravvicinate dopo un impulso ripido
    const compressing = isDecelerating && compression > 0.48;

    return { impulseDir, impulseAngle, decelRatio, isDecelerating, compression, compressing };
  }

  // ── Velocity/deceleration measurement (Agent 2) ───────────────────────────
  function _measureVelocity(candles, indicators) {
    if (!candles || candles.length < 20)
      return { slopeDeccel: 0, bodyDeccel: 0, swingDeccel: null, rsiVelocity: 0, composite: 0 };

    const N = 10, last = candles.length - 1;
    const atr = _atrAt(candles, last);
    const clamp01 = v => Math.max(0, Math.min(1, v));
    const clamp11 = v => Math.max(-1, Math.min(1, v));

    let slopeDeccel = 0;
    if (candles.length >= 2 * N) {
      const linreg = arr => {
        const n = arr.length, xm = (n-1)/2, ym = arr.reduce((a,b) => a+b, 0) / n;
        let num = 0, den = 0;
        for (let j = 0; j < n; j++) { num += (j-xm)*(arr[j]-ym); den += (j-xm)**2; }
        return den > 0 ? num/den : 0;
      };
      const closes = candles.map(c => c.close);
      const sC = linreg(closes.slice(-N)) / atr;
      const sP = linreg(closes.slice(-2*N, -N)) / atr;
      if (Math.abs(sP) > 0.05)
        slopeDeccel = clamp01((Math.abs(sP) - Math.abs(sC)) / (Math.abs(sP) + 0.001));
    }

    let bodyDeccel = 0;
    if (candles.length >= 6) {
      const sl = candles.slice(-6);
      const b = sl.map(c => Math.abs(c.close - c.open) / atr);
      const recent = (b[3]+b[4]+b[5]) / 3, older = (b[0]+b[1]+b[2]) / 3;
      const bearN = sl.slice(-3).filter(c => c.close < c.open).length;
      if (older > 0.15 && bearN >= 2)
        bodyDeccel = clamp01((older - recent) / (older + 0.001));
    }

    let swingDeccel = null;
    const sw60 = findSwings(candles.slice(-60), 4);
    const swLo60 = sw60.lows;
    if (swLo60.length >= 3) {
      const [s0, s1, s2] = swLo60.slice(-3);
      const ss = (a, b) => (b.i - a.i) > 0 ? ((b.price - a.price) / (b.i - a.i)) / atr : 0;
      const sAB = ss(s0, s1), sBC = ss(s1, s2);
      if (sAB < 0 && sBC < 0)
        swingDeccel = clamp01((Math.abs(sAB) - Math.abs(sBC)) / (Math.abs(sAB) + 0.001));
    }

    let rsiVelocity = 0;
    const rsiRawV = findIndicator(indicators || [], "RSI14") || findIndicator(indicators || [], "RSI");
    if (rsiRawV) {
      const rs = seriesFromIndicatorValues(candles, rsiRawV).filter(d => d.value != null);
      if (rs.length >= 7) {
        const rv = rs.slice(-7).map(d => d.value);
        const dC = (rv[6]-rv[3])/3, dP = (rv[3]-rv[0])/3;
        rsiVelocity = clamp11((dC - dP) / 10);
      }
    }

    let composite = swingDeccel !== null
      ? slopeDeccel*0.35 + bodyDeccel*0.25 + swingDeccel*0.30 + rsiVelocity*0.10
      : slopeDeccel*0.40 + bodyDeccel*0.30 + rsiVelocity*0.30;
    composite = clamp11(composite * 2 - 1);

    return { slopeDeccel, bodyDeccel, swingDeccel, rsiVelocity, composite };
  }

  function predictBreakout() {
    if (!mainChart || !state.data) return null;
    const tf = state.activeTimeframe;
    const analysis = state.data.timeframes[tf];
    if (!analysis || !analysis.candles || analysis.candles.length < 10) return null;

    const allCandles = analysis.candles;
    const indicators = analysis.indicators || [];
    const iv = analysis.interval || "1d";

    let range = { from: 0, to: allCandles.length - 1 };
    try {
      const vr = mainChart.timeScale().getVisibleLogicalRange();
      if (vr) { range.from = Math.max(0, Math.floor(vr.from)); range.to = Math.min(allCandles.length - 1, Math.ceil(vr.to)); }
    } catch {}
    const visible = allCandles.slice(range.from, range.to + 1);
    if (visible.length < 6) return null;

    // ── A. MTF context ──────────────────────────────────────────────────────
    const mtfContext = [];
    const hier = TF_HIERARCHY[iv] || {};
    let macroBias = "neutral", contextBias = "neutral";

    // Proxy macro: if higher TF not loaded, use last N candles of current TF as a stand-in
    const _trendOrProxy = (tfStr, windowPct, role) => {
      const a = _analysisByInterval(tfStr);
      if (a) return _computeTrend(a.candles, a.indicators || [], tfStr);
      // fallback: use a proportional tail of allCandles
      const n = Math.max(20, Math.floor(allCandles.length * windowPct));
      const proxy = allCandles.slice(-n);
      const t = _computeTrend(proxy, indicators, tfStr);
      if (t) t.detail = `estimate over ${n} ${iv} candles`;
      return t;
    };

    if (hier.macro) {
      const mt = _trendOrProxy(hier.macro, 0.6, "macro");
      macroBias = mt ? mt.dir : "neutral";
      mtfContext.push({ tf: hier.macro, dir: mt ? mt.dir : "neutral", detail: mt ? mt.detail : "—", role: "macro" });
    }
    if (hier.context) {
      const ct = _trendOrProxy(hier.context, 0.3, "context");
      contextBias = ct ? ct.dir : "neutral";
      mtfContext.push({ tf: hier.context, dir: ct ? ct.dir : "neutral", detail: ct ? ct.detail : "—", role: "context" });
    }

    // ── B. Phase + velocity + impulse angle ────────────────────────────────
    const swings = findSwings(visible, Math.max(3, Math.floor(visible.length / 8)));
    const phaseResult = _detectPhase(visible, swings);
    const vel = _measureVelocity(visible, indicators);
    const impAngle = _measureImpulseAngle(visible, swings);

    const phase = phaseResult.phase;
    const trend = phaseResult.trend;
    const resumeDir = macroBias !== "neutral" ? macroBias : trend !== "flat" ? trend : "neutral";

    // Quando c'è decel angolare + compressione, la direzione attesa è il CONTRARIO dell'impulso
    const direction = (impAngle.compressing && impAngle.impulseDir)
      ? (impAngle.impulseDir === "bear" ? "bull" : "bear")
      : resumeDir;

    // ── C. Gate conditions ──────────────────────────────────────────────────
    // La compressione post-impulso è di per sé un gate: bypassa gatePhase e gateVelocity
    const gatePhase    = phase === "ESAURIMENTO" || phase === "PIVOT" || impAngle.compressing;
    const gateMacro    = macroBias !== "neutral";
    const gateVelocity = impAngle.compressing
      ? true
      : (direction === "bull" ? vel.composite > 0.10 : direction === "bear" ? vel.composite < -0.10 : false);

    let currentRSI = null;
    const rsiRawMain = findIndicator(indicators, "RSI14") || findIndicator(indicators, "RSI");
    if (rsiRawMain) {
      const rm = {};
      seriesFromIndicatorValues(allCandles, rsiRawMain).forEach(d => { if (d.value != null) rm[d.time] = d.value; });
      currentRSI = rm[visible[visible.length - 1].time];
    }
    const gateRSI = currentRSI == null || (resumeDir === "bull" ? currentRSI < 72 : currentRSI > 28);
    const gateATR  = _atrAt(visible, visible.length - 1) / (visible[visible.length - 1].close || 1) * 100 > 0.05;

    const setupValid = gatePhase && (gateMacro || trend !== "flat" || impAngle.compressing) && gateVelocity && gateRSI && gateATR;

    // ── D. Quality scoring ────────────────────────────────────────────────
    // Pesi: F0=25 F1=22 F2=16 F3=11 F4=10 F5=8 F6=5 F7=3 = 100
    const factors = [];
    let setupScore = 0;

    {
      const t0 = visible[0].time, t1v = visible[visible.length - 1].time;

      // F0. Decel angolare + compressione (25%) — segnale più importante
      if (impAngle.compressing) {
        setupScore += 25;
        factors.push({ label: `Impulse angle decelerating (${(impAngle.decelRatio * 100).toFixed(0)}%) + compression`, present: true });
      } else if (impAngle.isDecelerating) {
        setupScore += 12;
        factors.push({ label: `Impulse angle decelerating (${(impAngle.decelRatio * 100).toFixed(0)}%)`, present: true });
      } else {
        factors.push({ label: "No angular deceleration", present: false });
      }

      // F1. RSI divergence (22%)
      const relDivs = divergenceLines.filter(d => d.t2 >= t0 && d.t1 <= t1v && d.type === (direction === "bull" ? "bull" : "bear"));
      if (relDivs.length > 0) { setupScore += 22; factors.push({ label: "RSI divergence confirmed", present: true }); }
      else { factors.push({ label: "No RSI divergence", present: false }); }

      // F2. Swing structure HL/LH (16%)
      const hasStruct = direction === "bull"
        ? swings.lows.length >= 2 && swings.lows.slice(-1)[0].price > swings.lows.slice(-2)[0].price
        : swings.highs.length >= 2 && swings.highs.slice(-1)[0].price < swings.highs.slice(-2)[0].price;
      if (hasStruct) { setupScore += 16; factors.push({ label: direction === "bull" ? "Higher lows (HL)" : "Lower highs (LH)", present: true }); }
      else { factors.push({ label: direction === "bull" ? "HL structure not confirmed" : "LH structure not confirmed", present: false }); }

      // F3. MTF alignment (11%)
      const mtfAligned = macroBias !== "neutral" && contextBias !== "neutral" && macroBias === contextBias && macroBias === direction;
      if (mtfAligned) { setupScore += 11; factors.push({ label: `MTF aligned ${hier.macro || ""}+${hier.context || ""}`, present: true }); }
      else { factors.push({ label: "MTF not aligned", present: false }); }

      // F4. Slope/body deceleration (10%)
      const hasDecel = vel.slopeDeccel > 0.3 || vel.bodyDeccel > 0.3 || (vel.swingDeccel != null && vel.swingDeccel > 0.3);
      if (hasDecel) { setupScore += 10; factors.push({ label: `${vel.slopeDeccel > vel.bodyDeccel ? "Slope" : "Body"} deceleration`, present: true }); }
      else { factors.push({ label: "No significant deceleration", present: false }); }

      // F5. Inside bar / NR (8%)
      const lc = visible[visible.length - 1], pc = visible[visible.length - 2];
      const isInsideBar = lc && pc && lc.high < pc.high && lc.low > pc.low;
      const isNR = lc && pc && (lc.high - lc.low) < (pc.high - pc.low) * 0.75;
      if (isInsideBar || isNR) { setupScore += 8; factors.push({ label: isInsideBar ? "Inside bar (compression)" : "NR: narrowing range", present: true }); }
      else { factors.push({ label: "No contraction", present: false }); }

      // F6. Exhaustion signal count (5%)
      if (phaseResult.exhaustSignals >= 2) { setupScore += 5; factors.push({ label: `${phaseResult.exhaustSignals} exhaustion signals`, present: true }); }
      else { factors.push({ label: "Exhaustion not confirmed", present: false }); }

      // F7. Velocity composite (3%)
      if (Math.abs(vel.composite) > 0.20) { setupScore += 3; factors.push({ label: `Momentum ${vel.composite > 0 ? "decreasing" : "increasing"} (${(vel.composite*100).toFixed(0)}%)`, present: true }); }
      else { factors.push({ label: "Momentum stable", present: false }); }
    }

    const phaseLabels = {
      "IMPULSO":        "Trend in progress — wait for a pullback",
      "RITRACCIAMENTO": "Pullback in progress",
      "ESAURIMENTO":    impAngle.compressing ? `${impAngle.impulseDir === "bear" ? "Bearish" : "Bullish"} impulse exhausted — waiting for a break` : "Pullback running out of steam",
      "PIVOT":          "Pivot confirmed — setup active",
      "LATERALE":       impAngle.compressing ? `Post-impulse compression (${impAngle.impulseDir === "bear" ? "bearish" : "bullish"})` : "Sideways structure",
    };

    const scoreColor  = setupScore >= 75 ? "#00d68f" : setupScore >= 50 ? "#f2a93b" : "#8899aa";
    const timeWindow  = phase === "PIVOT" ? "Entry confirmed" :
                        phase === "ESAURIMENTO" ? "1-3 candles to the pivot" :
                        phase === "RITRACCIAMENTO" ? "Wait for exhaustion signals" :
                        phase === "IMPULSO" ? "Wait for a pullback" : "No active setup";

    let keyLevel = null;
    if (direction === "bull" && swings.lows.length > 0)
      keyLevel = { price: swings.lows.slice(-1)[0].price, desc: "Last swing low — support" };
    else if (direction === "bear" && swings.highs.length > 0)
      keyLevel = { price: swings.highs.slice(-1)[0].price, desc: "Last swing high — resistance" };

    const mainRisk = impAngle.compressing && !gateMacro ? "Macro not aligned with the expected break" :
                     !gateMacro       ? "Macro bias undetermined" :
                     !gateVelocity    ? "Momentum still in the pullback direction" :
                     !gateRSI         ? (direction === "bull" ? "RSI in overbought zone" : "RSI in oversold zone") :
                     phaseResult.retracePct > 0.618 ? "Deep pullback — possible structural reversal" :
                     "Setup within normal range";

    return {
      phase, phaseLabel: phaseLabels[phase] || phase, trend, phaseTrend: trend,
      phaseConf: phaseResult.confidence, retracePct: phaseResult.retracePct,
      velocity: vel, setupValid, setupScore, scoreColor,
      timeWindow, keyLevel, mainRisk, factors, direction: resumeDir,
      impAngle, mtfContext, candleCount: visible.length, iv,
      aligned: macroBias === "neutral" || macroBias === resumeDir,
      macroBias, contextBias,
    };
  }

  function _renderBreakoutResult(res, popup) {
    if (!res) {
      popup.innerHTML = `<div class="bp-header"><span class="bp-title">Setup analysis</span><button class="marker-popup-close" onclick="document.getElementById('breakout-popup').classList.add('hidden')">×</button></div><p style="color:var(--ink-dim);font-size:12px;margin:8px 0 0">Not enough data in the visible range.</p>`;
      return;
    }

    const dirLabel = res.direction === "bull" ? "▲ LONG" : res.direction === "bear" ? "▼ SHORT" : "→ NEUTRAL";
    const dirColor = res.direction === "bull" ? "#00d68f" : res.direction === "bear" ? "#ff4560" : "#8899aa";
    const phaseColors = { "IMPULSO": "#8899aa", "RITRACCIAMENTO": "#f2a93b", "ESAURIMENTO": "#ffb347", "PIVOT": "#00d68f", "LATERALE": "#667788" };
    const phaseColor = phaseColors[res.phase] || "#8899aa";

    const mtfRows = res.mtfContext.map(m => {
      const icon = m.dir === "bull" ? "▲" : m.dir === "bear" ? "▼" : "→";
      const col  = m.dir === "bull" ? "#00d68f" : m.dir === "bear" ? "#ff4560" : "#8899aa";
      return `<div class="bp-mtf-row"><span class="bp-mtf-tf">${m.role === "macro" ? "MACRO" : "CONTEXT"} ${m.tf.toUpperCase()}</span><span class="bp-mtf-dir" style="color:${col}">${icon} ${m.dir.toUpperCase()}</span><span class="bp-mtf-detail">${m.detail}</span></div>`;
    }).join("");

    const factorRows = res.factors.map(f => {
      const col = f.present ? (res.direction === "bull" ? "#00d68f" : "#ff4560") : "#445566";
      return `<div class="bp-factor"><span class="bp-factor-icon" style="color:${col}">${f.present ? "✓" : "·"}</span><span class="bp-factor-label" style="opacity:${f.present ? "1" : "0.5"}">${f.label}</span></div>`;
    }).join("");

    const keyLevelHtml = res.keyLevel
      ? `<div class="bp-factor" style="margin-top:4px"><span class="bp-factor-icon" style="color:#8899aa">⊙</span><span class="bp-factor-label">${res.keyLevel.price.toLocaleString(undefined, {maximumFractionDigits:6})} — ${res.keyLevel.desc}</span></div>`
      : "";

    const retrStr = res.retracePct > 0 ? ` · retr. ${(res.retracePct * 100).toFixed(0)}%` : "";
    const velStr  = ` · vel. ${(res.velocity.composite * 100).toFixed(0)}%`;

    popup.innerHTML = `
      <div class="bp-header">
        <span class="bp-title">Setup · ${res.iv.toUpperCase()}</span>
        <button class="marker-popup-close" onclick="document.getElementById('breakout-popup').classList.add('hidden')" aria-label="Close">×</button>
      </div>
      <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:4px">
        <span style="font-family:var(--font-mono);font-size:10px;font-weight:700;color:${phaseColor};text-transform:uppercase;letter-spacing:.06em">${({ IMPULSO: "IMPULSE", RITRACCIAMENTO: "PULLBACK", ESAURIMENTO: "EXHAUSTION", LATERALE: "SIDEWAYS" })[res.phase] || res.phase}</span>
        <span style="color:${dirColor};font-size:16px;font-weight:700">${dirLabel}</span>
      </div>
      <div style="font-size:11px;color:var(--ink-dim);margin-bottom:8px">${res.phaseLabel}</div>
      ${res.setupValid ? `
      <div class="bp-conf-row" style="margin-bottom:4px">
        <span class="bp-conf-label">SETUP SCORE</span>
        <div class="marker-popup-score-bar" style="flex:1"><div class="marker-popup-score-fill" style="width:${res.setupScore}%;background:${res.scoreColor}"></div></div>
        <span class="bp-conf-num" style="color:${res.scoreColor}">${res.setupScore}/100</span>
      </div>
      <div style="font-size:10px;color:var(--ink-dim);margin-bottom:8px">⏱ ${res.timeWindow}</div>
      ` : `<div style="font-size:11px;color:#8899aa;margin-bottom:8px">⏳ ${res.timeWindow}</div>`}
      ${mtfRows ? `<div class="bp-mtf" style="margin-bottom:6px">${mtfRows}</div>` : ""}
      <div class="bp-section-label">${res.setupValid ? "QUALITY FACTORS" : "STRUCTURE"}</div>
      <div class="bp-factors">${factorRows}${keyLevelHtml}</div>
      ${res.setupValid ? `<div style="font-size:10px;color:#8899aa;margin-top:4px">⚠ ${res.mainRisk}</div>` : ""}
      <div class="bp-footer">${res.candleCount} candles${velStr}${retrStr}</div>
    `;
    popup.classList.remove("hidden");

    setTimeout(() => {
      const close = e => {
        if (!popup.contains(e.target) && !el("mobile-strip-predict-btn")?.contains(e.target)) {
          popup.classList.add("hidden");
          document.removeEventListener("pointerdown", close, true);
        }
      };
      document.addEventListener("pointerdown", close, true);
    }, 50);
  }

  function schedulePredictButton(delaySec = 5) {
    const btn = el("mobile-strip-predict-btn");
    if (!btn) return;
    btn.classList.remove("predict-ready", "predict-thinking");
    clearTimeout(_predictBtnTimer);
    _predictBtnTimer = setTimeout(() => {
      btn.classList.add("predict-ready");
    }, delaySec * 1000);
  }

  function showBreakoutPopup() {
    const popup = el("breakout-popup");
    const btn = el("mobile-strip-predict-btn");
    if (!popup) return;

    // Show loading state immediately
    popup.innerHTML = `
      <div class="bp-header">
        <span class="bp-title">Setup analysis</span>
        <button class="marker-popup-close" onclick="document.getElementById('breakout-popup').classList.add('hidden')" aria-label="Close">×</button>
      </div>
      <div class="bp-thinking">
        <div class="bp-dots"><span></span><span></span><span></span></div>
        <div class="bp-thinking-label">Analyzing…</div>
      </div>
    `;
    popup.classList.remove("hidden");
    if (btn) btn.classList.add("predict-thinking");

    setTimeout(() => {
      const res = predictBreakout();
      _renderBreakoutResult(res, popup);
      if (btn) {
        btn.classList.remove("predict-thinking");
        btn.classList.add("predict-ready");
      }
    }, 2000);
  }

  function bindBreakoutButton() {
    const btn = el("mobile-strip-predict-btn");
    if (!btn) return;
    btn.addEventListener("click", showBreakoutPopup);
  }

  // ── fine motore previsionale ───────────────────────────────────────────────

  function bindMarkerClickPopup() {
    const popup = el("marker-popup");
    // Click fuori dal popup lo chiude
    document.addEventListener("pointerdown", (e) => {
      if (popup && !popup.contains(e.target)) popup.classList.add("hidden");
    }, { capture: true });

    // subscribeClick di LightweightCharts: click disambiguato da drag
    mainChart.subscribeClick((param) => {
      if (!param || param.time === undefined) return;
      // Raccoglie tutti i marker correnti (strategy + pattern + hints)
      const allMarkers = [
        ...buildStrategyMarkers(_lastStrategySignals || []),
        ...autoPatternMarkers,
        ...contextualHintMarkers,
      ];
      // Trova il marker con lo stesso time (o a 1 barra di distanza)
      const hit = allMarkers.find((m) => Math.abs(m.time - param.time) < 2);
      if (!hit) return;
      const rect = el("main-chart").getBoundingClientRect();
      const px = rect.left + (param.point?.x || 0);
      const py = rect.top  + (param.point?.y || 0);
      showMarkerPopup(hit, px, py);
    });
  }

  // Un indicatore aggiunto dalla libreria si toglie passandoci sopra il
  // mouse: appare una "x" vicino alla linea, si clicca quella e si
  // rimuove — niente rimozione al primo click sul grafico, che sarebbe
  // troppo facile da far scattare per sbaglio mentre si guarda il prezzo.
  // Per gli overlay (linee sul prezzo, disegnate su canvas, non elementi
  // DOM separati) serve un test di prossimita' verticale ad ogni
  // movimento della crosshair: subscribeCrosshairMove da' il valore di
  // ogni serie al tempo corrente (param.seriesData), non se il cursore e'
  // visivamente sopra quella linea — lo si ricava confrontando la
  // coordinata y del valore con quella del cursore, con qualche pixel di
  // tolleranza. Attivo solo con lo strumento cursore: con un altro
  // strumento selezionato si sta disegnando, non rimuovendo indicatori.
  const OVERLAY_HIT_TOLERANCE_PX = 6;
  let hoveredOverlayId = null;
  let overlayBadgePinned = false; // true mentre il mouse e' sopra il badge stesso

  function bindCustomOverlayRemoval() {
    const badge = el("overlay-remove-badge");
    if (!badge) return;
    // Il badge e' un elemento DOM sopra il canvas del grafico: appena il
    // cursore lo raggiunge, il grafico sotto smette di ricevere il
    // movimento e subscribeCrosshairMove non arriva piu' — senza questa
    // guardia il badge sparirebbe un attimo prima di poterci cliccare
    // sopra, rendendolo impossibile da usare.
    badge.addEventListener("mouseenter", () => { overlayBadgePinned = true; });
    badge.addEventListener("mouseleave", () => {
      overlayBadgePinned = false;
      badge.classList.add("hidden");
    });
    mainChart.subscribeCrosshairMove((param) => {
      if (overlayBadgePinned) return;
      if (drawState.tool !== "cursor" || !param || !param.point || !param.seriesData || !customOverlaySeriesList.length) {
        hoveredOverlayId = null;
        badge.classList.add("hidden");
        return;
      }
      for (const entry of customOverlaySeriesList) {
        const data = param.seriesData.get(entry.series);
        if (data == null) continue;
        const value = typeof data === "object" ? data.value : data;
        if (value == null) continue;
        const y = entry.series.priceToCoordinate(value);
        if (y == null) continue;
        if (Math.abs(y - param.point.y) <= OVERLAY_HIT_TOLERANCE_PX) {
          hoveredOverlayId = entry.id;
          badge.style.left = `${param.point.x}px`;
          badge.style.top = `${y}px`;
          badge.classList.remove("hidden");
          return;
        }
      }
      hoveredOverlayId = null;
      badge.classList.add("hidden");
    });
    badge.addEventListener("click", (e) => {
      e.stopPropagation();
      if (hoveredOverlayId) toggleCustomIndicator(hoveredOverlayId);
      badge.classList.add("hidden");
    });
  }

  function bindChartContextMenu() {
    const container = el("main-chart");
    let menuEl = null;
    let ctxPrice = null;

    function closeMenu() {
      if (menuEl) { menuEl.remove(); menuEl = null; }
    }

    function openMenu(clientX, clientY, price) {
      closeMenu();
      ctxPrice = price;
      const sym = (el("ticker-input")?.value || "").trim().toUpperCase() || "—";
      const priceStr = price != null ? price.toFixed(4).replace(/\.?0+$/, (m, o, s) => s.includes(".") ? "" : m) : null;
      const items = [
        { label: "Reset view", key: "Alt+R", action: () => { try { mainChart.timeScale().fitContent(); } catch { /* */ } } },
        priceStr ? { label: `Copy price  ${priceStr}`, action: () => navigator.clipboard?.writeText(priceStr) } : null,
        { label: `Copy symbol  ${sym}`, action: () => navigator.clipboard?.writeText(sym) },
        { separator: true },
        priceStr ? { label: `Add alert on ${sym} at ${priceStr}…`, action: () => {
          const tab = document.querySelector('[data-tab="alert"]');
          if (tab) tab.click();
          const inp = document.getElementById("pa-price");
          if (inp) { inp.value = priceStr; inp.focus(); }
        }} : null,
        { label: "Open in Lab →", action: () => { setArea("lab"); } },
        { separator: true },
        { label: "Horizontal line", action: () => setDrawTool("hline") },
        { label: "Horizontal ray →", action: () => setDrawTool("hray") },
        { label: "Trend line", action: () => setDrawTool("trend_line") },
        { label: "Extended line ↔", action: () => setDrawTool("extended_line") },
        { label: "Rectangle", action: () => setDrawTool("rectangle") },
        { label: "Ruler (measure price/time)", action: () => setDrawTool("range") },
        { label: "Ellipse", action: () => setDrawTool("ellipse") },
        { label: "Parallel channel", action: () => setDrawTool("channel") },
        { label: "Arrow", action: () => setDrawTool("arrow") },
        { label: "Fibonacci", action: () => setDrawTool("fib") },
        { label: "Text", action: () => setDrawTool("text") },
        { separator: true },
        { label: "Fractal (copy a range)", action: () => setDrawTool("fractal") },
        { separator: true },
        drawState.drawings.length
          ? { label: "Remove all drawings", action: () => {
              if (window.confirm("Delete all drawings on this chart?")) clearAllDrawings();
            } }
          : null,
        { label: "Remove all price indicators", action: () => clearAllPriceIndicators() },
        { separator: true },
        { label: "Chart settings…", action: () => { const btn = document.getElementById("chart-settings-btn"); if (btn) btn.click(); } },
      ].filter(Boolean);

      menuEl = document.createElement("ul");
      menuEl.className = "chart-ctx-menu";
      items.forEach((item) => {
        const li = document.createElement("li");
        if (item.separator) { li.className = "chart-ctx-sep"; menuEl.appendChild(li); return; }
        li.className = "chart-ctx-item";
        const span = document.createElement("span"); span.textContent = item.label; li.appendChild(span);
        if (item.key) { const k = document.createElement("span"); k.className = "chart-ctx-key"; k.textContent = item.key; li.appendChild(k); }
        li.addEventListener("mousedown", (e) => { e.preventDefault(); closeMenu(); item.action(); });
        menuEl.appendChild(li);
      });

      const vw = window.innerWidth, vh = window.innerHeight;
      document.body.appendChild(menuEl);
      const mw = menuEl.offsetWidth || 240, mh = menuEl.offsetHeight || 160;
      menuEl.style.left = (clientX + mw > vw ? clientX - mw : clientX) + "px";
      menuEl.style.top  = (clientY + mh > vh ? clientY - mh : clientY) + "px";
    }

    document.addEventListener("contextmenu", (e) => {
      if (!container.contains(e.target)) return;
      e.preventDefault();
      const price = lastCrosshairPoint && candleSeries
        ? candleSeries.coordinateToPrice(lastCrosshairPoint.y)
        : null;
      openMenu(e.clientX, e.clientY, price);
    }, true);

    document.addEventListener("mousedown", (e) => { if (menuEl && !menuEl.contains(e.target)) closeMenu(); }, true);
    document.addEventListener("keydown",    (e) => { if (e.key === "Escape") closeMenu(); }, true);
  }

  function bindDrawRail() {
    document.querySelectorAll(".draw-tool-btn[data-draw-tool]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tool = btn.dataset.drawTool;
        setDrawTool(drawState.tool === tool && !drawState.sticky ? "cursor" : tool);
      });
      // Double click: the tool stays on for several drawings in a row.
      btn.addEventListener("dblclick", () => {
        const tool = btn.dataset.drawTool;
        if (tool !== "cursor") setDrawTool(tool, { sticky: true });
      });
    });
    const bind = (id, fn) => { const b = el(id); if (b) b.addEventListener("click", fn); };
    bind("draw-magnet-btn", toggleMagnet);
    bind("draw-hide-btn", toggleHideDrawings);
    bind("draw-undo-btn", undoDrawing);
    bind("draw-redo-btn", redoDrawing);
    const mag = el("draw-magnet-btn");
    if (mag) { mag.classList.toggle("selected", drawState.magnet); mag.setAttribute("aria-pressed", String(drawState.magnet)); }
    el("draw-clear-btn").addEventListener("click", () => {
      if (drawState.drawings.length && window.confirm("Delete all drawings on this chart?")) {
        clearAllDrawings();
      }
    });
  }

  // .draw-rail is hidden outright below 760px (there's no room for a fixed
  // side column) — these two chart-strip buttons are how mobile reaches
  // drawing tools instead: the pencil opens the same rail repositioned as
  // a horizontal dock right above this row, the trash mirrors
  // #draw-clear-btn. Picking a tool or tapping the pencil again closes the
  // dock, same as the desktop rail's own click-away behavior.
  function bindMobileDrawTools() {
    const drawBtn = el("mobile-strip-draw-btn");
    const clearBtn = el("mobile-strip-clear-btn");
    const rail = el("draw-rail");
    drawBtn.addEventListener("click", () => {
      rail.classList.toggle("mobile-tools-open");
      drawBtn.classList.toggle("active", rail.classList.contains("mobile-tools-open"));
    });
    clearBtn.addEventListener("click", () => {
      if (drawState.drawings.length && window.confirm("Delete all drawings on this chart?")) {
        clearAllDrawings();
      }
    });
    rail.querySelectorAll(".draw-tool-btn[data-draw-tool]").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (window.matchMedia("(max-width: 760px)").matches) {
          rail.classList.remove("mobile-tools-open");
          drawBtn.classList.remove("active");
        }
      });
    });
  }

  // The wheel is a thin skin over the real #interval-primary select — it
  // never duplicates the interval list or the "what happens on change"
  // logic, it just reads the select's options once and, from then on,
  // keeps select.value and this UI in sync in both directions.
  const TF_WHEEL_ITEM_H = 18;

  function buildMobileTfWheel() {
    const track = el("tf-wheel-track");
    if (track.dataset.built) return;
    track.dataset.built = "1";
    const select = el("interval-primary");
    Array.from(select.options).forEach((opt) => {
      const item = document.createElement("div");
      item.className = "tf-wheel-item";
      item.textContent = opt.value;
      item.dataset.value = opt.value;
      item.addEventListener("click", () => {
        track.scrollTo({ top: item.offsetTop - (track.clientHeight - TF_WHEEL_ITEM_H) / 2, behavior: "smooth" });
      });
      track.appendChild(item);
    });

    let settleTimer = null;
    track.addEventListener("scroll", () => {
      markTfWheelClosest();
      clearTimeout(settleTimer);
      settleTimer = setTimeout(() => {
        const closest = markTfWheelClosest();
        if (closest && closest.dataset.value !== select.value) {
          select.value = closest.dataset.value;
          select.dispatchEvent(new Event("change"));
        }
      }, 130);
    });
  }

  // Whichever item's center is nearest the track's own center becomes
  // "current" (the one sitting inside the dark pill); its immediate
  // neighbors get a lighter "near" tint so the fade toward the edges
  // reads as a wheel, not a flat list.
  function markTfWheelClosest() {
    const track = el("tf-wheel-track");
    const items = Array.from(track.children);
    if (!items.length) return null;
    const center = track.scrollTop + track.clientHeight / 2;
    let closest = items[0];
    let closestDist = Infinity;
    items.forEach((it) => {
      const dist = Math.abs(it.offsetTop + TF_WHEEL_ITEM_H / 2 - center);
      if (dist < closestDist) { closestDist = dist; closest = it; }
    });
    const closestIdx = items.indexOf(closest);
    items.forEach((it, idx) => {
      it.classList.toggle("current", it === closest);
      it.classList.toggle("near", Math.abs(idx - closestIdx) === 1);
    });
    return closest;
  }

  // Re-centers the wheel on the select's current value — needed whenever
  // the value changes from outside the wheel (initial load, resize onto
  // mobile) since scrollTop math needs real layout, which only exists once
  // the strip is actually visible (display:none elsewhere gives 0 height).
  function syncMobileTfWheel() {
    if (!window.matchMedia("(max-width: 760px)").matches) return;
    const track = el("tf-wheel-track");
    if (!track.dataset.built) return;
    const select = el("interval-primary");
    const target = track.querySelector(`.tf-wheel-item[data-value="${select.value}"]`);
    if (!target) return;
    track.scrollTop = target.offsetTop - (track.clientHeight - TF_WHEEL_ITEM_H) / 2;
    markTfWheelClosest();
  }

  function updateMobileChartStrip() {
    const strip = el("mobile-chart-strip");
    const tools = el("mobile-strip-tools");
    const onChartScreen = document.querySelector('.mobile-nav-btn[data-mobile-target="chart"]').classList.contains("active");
    if (!state.data) {
      strip.classList.add("hidden");
      tools.classList.add("hidden");
      return;
    }
    el("mobile-chart-symbol").textContent = shortSymbol(state.data.symbol);
    el("mobile-chart-symbol").title = state.data.symbol;
    // Keep the strategy pill updated with the currently-active strategy name.
    // Abbreviate long names so the pill stays compact on small screens.
    const pill = el("mobile-strategy-pill");
    const stratName = el("active-strategy-select").value || "—";
    const stratAbbr = strategyLabel(stratName).replace("(long-term)", "").trim();
    pill.textContent = stratAbbr;
    strip.classList.remove("hidden");
    tools.classList.toggle("hidden", !onChartScreen);
    syncMobileTfWheel();
  }

  // Disegna le linee di pendenza tra i punti di swing usando LinePrimitive.
  //   rosso vivo  = impulso bear ripido    verde vivo = impulso bull ripido
  //   grigio      = leg debole / compressione
  function renderAngleLines(candles, indicators) {
    if (!candles || candles.length < 6) return;
    const atr = _atrAt(candles, candles.length - 1);
    if (atr <= 0) return;

    const swings = findSwings(candles, 5);
    const pts = [];
    swings.highs.forEach(p => pts.push({ i: p.i, price: p.price, time: p.time }));
    swings.lows.forEach(p =>  pts.push({ i: p.i, price: p.price, time: p.time }));
    pts.sort((a, b) => a.i - b.i);

    const legs = [];
    for (let k = 1; k < pts.length; k++) {
      const bars = pts[k].i - pts[k - 1].i;
      if (bars < 1 || !pts[k - 1].time || !pts[k].time || pts[k].time <= pts[k - 1].time) continue;
      const slope = (pts[k].price - pts[k - 1].price) / (bars * atr);
      legs.push({ from: pts[k - 1], to: pts[k], slope });
    }
    if (!legs.length) return;

    const recentLegs = legs.slice(-10);
    const maxAbs = recentLegs.reduce((m, l) => Math.max(m, Math.abs(l.slope)), 0.01);

    recentLegs.forEach((leg, idx) => {
      const isLast = idx === recentLegs.length - 1;
      const norm = Math.min(1, Math.abs(leg.slope) / maxAbs);
      const isBull = leg.slope >= 0;
      let color;
      if (norm > 0.45) {
        const alpha = 0.5 + norm * 0.5;
        color = isBull ? `rgba(0,214,143,${alpha.toFixed(2)})` : `rgba(255,69,96,${alpha.toFixed(2)})`;
      } else {
        color = COLORS.paperBg === "#ffffff"
          ? `rgba(70,80,95,${(0.45 + norm * 0.40).toFixed(2)})`
          : `rgba(140,150,165,${(0.30 + norm * 0.40).toFixed(2)})`;
      }
      const width = isLast ? 2 : 1;
      const prim = new LinePrimitive(
        { time: leg.from.time, price: leg.from.price },
        { time: leg.to.time,   price: leg.to.price   },
        color, width, false
      );
      candleSeries.attachPrimitive(prim);
      overlays.primitives.push({ series: candleSeries, primitive: prim });

      // Etichetta sul punto finale del leg (è un timestamp di candela reale)
      if (isLast || norm > 0.55) {
        const label = `${leg.slope > 0 ? "+" : ""}${leg.slope.toFixed(1)}σ`;
        const textPrim = new TextPrimitive({ time: leg.to.time, price: leg.to.price }, label, color);
        candleSeries.attachPrimitive(textPrim);
        overlays.primitives.push({ series: candleSeries, primitive: textPrim });
      }
    });
  }

  let scaleKey = null;
  function render() {
    if (!state.data) return;
    updateWatchStar();
    clearOverlays();
    const nextScaleKey = `${drawChartKey()}:${state.activeTimeframe}`;
    if (nextScaleKey !== scaleKey) { scaleKey = nextScaleKey; resetPaneScales(); }
    updateMobileChartStrip();

    const tf = state.activeTimeframe;
    const analysis = state.data.timeframes[tf];
    const candles = analysis.candles;
    const lastTime = candles[candles.length - 1].time;
    const firstTime = candles[0].time;

    // Switching symbol/timeframe can jump price magnitude by orders of
    // magnitude (a $90,000 BTC chart vs. a $0.00001 microcap) — the default
    // fixed 2-decimal price format rounds small prices straight to 0.00.
    candleSeries.applyOptions({ priceFormat: pricePrecisionFor(candles[candles.length - 1].close) });
    candleSeries.setData(candles.map((c) => ({ time: c.time, open: c.open, high: c.high, low: c.low, close: c.close })));
    setOhlcCandles(candles);
    setDrawTimes(candles);
    addSessionShading(candles, el("interval-primary").value);

    // --- price-scale indicator overlays ---
    if (state.layers.ema) {
      const ema20 = findIndicator(analysis.indicators, "EMA20");
      const ema50 = findIndicator(analysis.indicators, "EMA50");
      if (ema20) {
        const s = mainChart.addLineSeries({ color: COLORS.ema20, lineWidth: 1.5, priceLineVisible: false, title: "EMA 20" });
        s.setData(seriesFromIndicatorValues(candles, ema20));
        addLineOverlay(mainChart, s, null, mainChart);
      }
      if (ema50) {
        const s = mainChart.addLineSeries({ color: COLORS.ema50, lineWidth: 1.5, priceLineVisible: false, title: "EMA 50" });
        s.setData(seriesFromIndicatorValues(candles, ema50));
        addLineOverlay(mainChart, s, null, mainChart);
      }
    }
    if (state.layers.bbands) {
      const bbBands = [
        { name: "BB_upper", color: COLORS.bbUpper, lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Solid, title: "BB 20,2" },
        { name: "BB_mid", color: COLORS.bbMid, lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, title: "" },
        { name: "BB_lower", color: COLORS.bbLower, lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Solid, title: "" },
      ];
      bbBands.forEach(({ name, color, lineWidth, lineStyle, title }) => {
        const vals = findIndicator(analysis.indicators, name);
        if (!vals) return;
        const s = mainChart.addLineSeries({ color, lineWidth, lineStyle, priceLineVisible: false, title });
        s.setData(seriesFromIndicatorValues(candles, vals));
        addLineOverlay(mainChart, s, null, mainChart);
      });
    }
    if (state.layers.vwap) {
      const vals = findIndicator(analysis.indicators, "VWAP");
      if (vals) {
        const anchor = VWAP_ANCHOR_LABEL[el("interval-primary").value] || "D";
        const s = mainChart.addLineSeries({ color: COLORS.vwap, lineWidth: 1.5, priceLineVisible: false, title: `VWAP ${anchor}` });
        s.setData(vwapWithBreaks(candles, vals, anchor));
        addLineOverlay(mainChart, s, null, mainChart);
      }
    }

    // Bull Market Support Band: SMA 20 and EMA 21 of the weekly close.
    if (state.layers.bmsb) {
      [["BMSB_SMA20W", COLORS.bmsbSma, "SMA 20W"], ["BMSB_EMA21W", COLORS.bmsbEma, "EMA 21W"]].forEach(([name, color, title]) => {
        const vals = findIndicator(analysis.indicators, name);
        if (!vals) return;
        const s = mainChart.addLineSeries({ color, lineWidth: 2, priceLineVisible: false, title });
        s.setData(seriesFromIndicatorValues(candles, vals));
        addLineOverlay(mainChart, s, null, mainChart);
      });
    }

    // --- RSI / MACD sub-panes ---
    el("rsi-chart").classList.toggle("hidden", !state.layers.rsi);
    if (state.layers.rsi) {
      const vals = findIndicator(analysis.indicators, "RSI14");
      rsiSeries.setData(vals ? seriesFromIndicatorValues(candles, vals) : []);
    }
    el("macd-chart").classList.toggle("hidden", !state.layers.macd);
    if (state.layers.macd) {
      const macdVals = findIndicator(analysis.indicators, "MACD");
      const signalVals = findIndicator(analysis.indicators, "MACD_signal");
      const histVals = findIndicator(analysis.indicators, "MACD_hist");
      const macdFormat = oscPrecisionFor([...(macdVals || []), ...(signalVals || [])]);
      [macdLineSeries, macdSignalSeries, macdHistSeries].forEach((s) => s.applyOptions({ priceFormat: macdFormat }));
      macdLineSeries.setData(macdVals ? seriesFromIndicatorValues(candles, macdVals) : []);
      macdSignalSeries.setData(signalVals ? seriesFromIndicatorValues(candles, signalVals) : []);
      if (histVals) {
        macdHistSeries.setData(
          seriesFromIndicatorValues(candles, histVals).map((d, i, arr) => {
            const prev = arr[i - 1]?.value ?? d.value;
            const rising = d.value > prev;
            let color;
            if (d.value >= 0) {
              color = rising ? "rgba(0,214,143,0.85)" : "rgba(0,214,143,0.38)";
            } else {
              color = !rising ? "rgba(255,69,96,0.85)" : "rgba(255,69,96,0.38)";
            }
            return { time: d.time, value: d.value, color };
          })
        );
      } else {
        macdHistSeries.setData([]);
      }
    }

    el("stoch-chart").classList.toggle("hidden", !state.layers.stoch);
    if (state.layers.stoch) {
      const kVals = findIndicator(analysis.indicators, "STOCH_K");
      const dVals = findIndicator(analysis.indicators, "STOCH_D");
      stochKSeries.setData(kVals ? seriesFromIndicatorValues(candles, kVals) : []);
      stochDSeries.setData(dVals ? seriesFromIndicatorValues(candles, dVals) : []);
    }
    [rsiChart, macdChart, stochChart].forEach(syncPaneRange);

    // --- structure / liquidity overlays ---
    analysis.levels.forEach((lvl) => {
      const isZone = lvl.type === "order_block" || lvl.type === "fvg";
      const layerKey = lvl.type === "order_block" ? "order_block" : lvl.type === "fvg" ? "fvg" : lvl.type === "eqh" || lvl.type === "eql" ? "liquidity" : "structure";
      if (!state.layers[layerKey]) return;

      const isBullish = lvl.direction === "bullish";
      const isFvg = lvl.type === "fvg";
      const isMitigated = isFvg && lvl.mitigated;
      let fill = isFvg ? (isBullish ? COLORS.fvgBullFill : COLORS.fvgBearFill) : isBullish ? COLORS.bullFill : COLORS.bearFill;
      let border = isFvg ? (isBullish ? COLORS.fvgBullBorder : COLORS.fvgBearBorder) : isBullish ? COLORS.bullBorder : COLORS.bearBorder;
      if (isMitigated) {
        // Mitigated FVGs: still visible but clearly "used" — half opacity
        fill = fill.replace(/[\d.]+\)$/, (m) => `${(parseFloat(m) * 0.5).toFixed(2)})`);
        border = border.replace(/[\d.]+\)$/, (m) => `${(parseFloat(m) * 0.5).toFixed(2)})`);
      }
      const endTime = lvl.end_time ?? lastTime;

      if (isZone) {
        addRectangle(
          { time: lvl.start_time, price: lvl.price_high },
          { time: endTime, price: lvl.price_low },
          fill,
          border,
          lvl.label,
          // Niente scritta sopra le imbalance: su TradingView il box e' muto e
          // il nome sta nel tooltip. La fascia con la mediana che avevo messo
          // prima era una mia invenzione, non lo stile di riferimento.
          isFvg ? "" : LEVEL_SHORT_LABELS[lvl.type],
          // Non riempita = ancora valida, e continua oltre l'ultima candela.
          // Riempita = si ferma dove il prezzo l'ha richiusa, che e' il punto
          // di tutta l'informazione.
          isFvg && !lvl.mitigated ? { extendRight: true } : undefined
        );
      } else {
        const line = candleSeries.createPriceLine({
          price: lvl.price_high,
          color: border,
          lineWidth: 1,
          lineStyle: LightweightCharts.LineStyle.Dashed,
          axisLabelVisible: true,
          title: lvl.label,
        });
        overlays.priceLines.push({ series: candleSeries, line });
      }
    });

    if (state.layers.confluence) {
      state.data.confluence_zones.forEach((z) => {
        addRectangle(
          { time: firstTime, price: z.price_high },
          { time: lastTime, price: z.price_low },
          COLORS.confluenceFill,
          COLORS.confluenceBorder,
          z.label,
          "CONF"
        );
      });
    }

    // --- automatic Fibonacci retracement / extension ---
    // Only the single most recent leg (and, when a pullback has confirmed
    // it, its extension) — same "most actionable, not full history"
    // philosophy as the dealing range and confluence zones above.
    if (state.layers.fibonacci && analysis.fib_zones) {
      analysis.fib_zones.forEach((zone) => {
        const isBull = zone.direction === "bullish";
        const isExt = zone.kind === "extension";
        const lineColor = isExt ? COLORS.accent : isBull ? COLORS.bull : COLORS.bear;
        const ratioEntries = Object.entries(zone.levels);

        ratioEntries.forEach(([ratio, price]) => {
          const isKeyRatio = ["0", "1", "0.382", "0.618", "1.618"].includes(ratio);
          // Only the key ratios get an axis label + title box — the rest
          // (0.236/0.5/0.786 retracement, 1.414/2/2.618 extension) still
          // mark the price but stay unlabeled and near-invisible, so the
          // chart doesn't turn into a stack of a dozen labeled price lines.
          const line = candleSeries.createPriceLine({
            price,
            color: lineColor,
            lineWidth: isKeyRatio ? 2 : 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: isKeyRatio,
            title: isKeyRatio ? `Fib ${isExt ? "ext" : "ret"} ${(parseFloat(ratio) * 100).toFixed(1)}%` : "",
          });
          overlays.priceLines.push({ series: candleSeries, line });
        });

        if (!isExt && zone.levels["0.382"] !== undefined && zone.levels["0.618"] !== undefined) {
          // Golden-pocket fill (38.2%-61.8%) — the zone traders actually watch.
          addRectangle(
            { time: zone.anchor_time, price: zone.levels["0.382"] },
            { time: lastTime, price: zone.levels["0.618"] },
            isBull ? COLORS.bullFill : COLORS.bearFill,
            isBull ? COLORS.bullBorder : COLORS.bearBorder,
            null,
            null
          );
        }
      });
    }

    applyAutoPatterns();
    applyContextualHints();
    applyDivergences();
    applyElliott();
    if (state.layers.angleLines) renderAngleLines(candles, analysis.indicators || []);

    renderSummary();
    renderStrategy();
    renderBacktest();
    resizeAllCharts();
    zoomToOptimal();
    refreshCustomIndicators();
  }

  // Mappa stringa intervallo → minuti per candle
  const IV_MINUTES = { "1m":1,"5m":5,"15m":15,"30m":30,"1h":60,"4h":240,"1d":1440,"2d":2880,"3d":4320,"5d":7200,"1w":10080,"1M":43200 };

  // Giorni ottimali per ogni timeframe: abbastanza candele da vedere struttura, non troppo da fare rumore
  const IV_OPTIMAL_DAYS = { "1m":0.04,"5m":0.17,"15m":0.5,"30m":1,"1h":2,"4h":8,"1d":50,"2d":100,"3d":150,"5d":250,"1w":350,"1M":1500 };

  function zoomToOptimal() {
    if (!mainChart || !state.data) { try { mainChart && mainChart.timeScale().fitContent(); } catch {} return; }
    const tf = state.activeTimeframe;
    const analysis = state.data.timeframes[tf];
    if (!analysis || !analysis.candles || !analysis.candles.length) { try { mainChart.timeScale().fitContent(); } catch {} return; }
    const iv = analysis.interval || el("interval-primary")?.value || "1d";
    const mins = IV_MINUTES[iv] || 1440;
    const days = IV_OPTIMAL_DAYS[iv] || 7;
    const candlesPerDay = 1440 / mins;
    const targetBars = Math.ceil(days * candlesPerDay);
    const total = analysis.candles.length;
    const fromBar = Math.max(0, total - targetBars);
    try {
      mainChart.timeScale().setVisibleLogicalRange({ from: fromBar, to: total + 2 });
    } catch { try { mainChart.timeScale().fitContent(); } catch {} }
    schedulePredictButton(5);
  }

  function renderStrategy() {
    const allSignals = [];
    ["htf", "mtf", "ltf"].forEach((tf) => {
      const states = state.data.strategies[tf];
      if (!states || !states.length) return;
      states[0].signals.forEach((sig) => allSignals.push({ ...sig, tf }));
    });
    allSignals.sort((a, b) => a.time - b.time);

    const activeState = (state.data.strategies[state.activeTimeframe] || [])[0];
    const badge = el("strategy-position-badge");
    if (activeState) {
      badge.textContent = activeState.position.toUpperCase();
      badge.className = "position-badge " + activeState.position;
    }

    const log = el("strategy-alert-log");
    log.innerHTML = "";
    allSignals.slice(-40).forEach((sig) => {
      const li = document.createElement("li");
      li.className = sig.type.includes("long") ? "long-signal" : "short-signal";
      const time = new Date(sig.time * 1000).toLocaleString("en-US");
      li.innerHTML = `[${sig.tf.toUpperCase()}] ${sig.label} — ${sig.price.toPrecision(6)}<span class="alert-time">${time}</span>`;
      log.appendChild(li);
    });

    _lastStrategySignals = activeState ? activeState.signals : [];
    applyChartMarkers();

    notifyNewAlerts(allSignals);
  }

  // Entry/exit/flip need to read unambiguously at a glance: shape says
  // in-or-out (triangle vs. circle), color says which side (bull green vs.
  // bear red — flips get the stamp accent since they're neither purely "in"
  // nor "out"), and the label spells it out instead of a bare cryptic letter.
  function buildStrategyMarkers(signals) {
    return signals.map((sig) => {
      const isLongSide = sig.type.includes("long");
      if (sig.type.startsWith("entry")) {
        return {
          time: sig.time,
          position: isLongSide ? "belowBar" : "aboveBar",
          color: isLongSide ? COLORS.bullBorder : COLORS.bearBorder,
          shape: isLongSide ? "arrowUp" : "arrowDown",
          text: isLongSide ? "IN long" : "IN short",
        };
      }
      if (sig.type.startsWith("exit")) {
        return {
          time: sig.time,
          position: isLongSide ? "aboveBar" : "belowBar",
          color: isLongSide ? COLORS.bullBorder : COLORS.bearBorder,
          shape: "circle",
          text: "OUT",
        };
      }
      // flip_to_long / flip_to_short: closes one side and opens the other in
      // the same bar — mark it distinctly rather than as a plain entry.
      const flippingToLong = sig.type === "flip_to_long";
      return {
        time: sig.time,
        position: flippingToLong ? "belowBar" : "aboveBar",
        color: COLORS.stamp,
        shape: flippingToLong ? "arrowUp" : "arrowDown",
        text: flippingToLong ? "FLIP long" : "FLIP short",
      };
    });
  }

  // I marker sulla strategia e quelli sui trade del backtest finiscono nella
  // stessa chiamata: `setMarkers` sostituisce l'intero elenco, quindi due
  // scritture separate si cancellerebbero a vicenda.
  let _lastStrategySignals = [];


  // ── Ordini reali sul grafico ──────────────────────────────────────────
  // Un segnale della strategia e un ordine davvero eseguito non sono la
  // stessa cosa, e finora sul grafico si vedeva solo il primo: la domanda
  // "ma quella volta sono entrato davvero?" non aveva risposta guardando la
  // serie. Gli ordini del diario diventano marker propri — forma piena,
  // etichetta con il prezzo di riempimento — cosi' la differenza fra cosa
  // la strategia diceva e cosa e' successo si legge a colpo d'occhio.
  let _executedOrders = [];

  async function loadExecutedOrders() {
    if (!state.user) { _executedOrders = []; return; }
    try {
      const res = await fetch("/api/trading/journal?limit=200");
      if (!res.ok) { _executedOrders = []; return; }
      const data = await res.json();
      _executedOrders = Array.isArray(data) ? data : (data.entries || []);
    } catch {
      _executedOrders = [];   // il grafico deve reggere anche senza diario
    }
    applyChartMarkers();
  }

  function buildExecutedOrderMarkers() {
    if (!_executedOrders.length || !state.data) return [];
    const chartSymbol = (state.data.symbol || "").toUpperCase();
    const tf = state.data.timeframes && state.data.timeframes[state.activeTimeframe];
    const candles = (tf && tf.candles) || [];
    if (!candles.length) return [];

    // Il diario segna l'istante dell'ordine, che quasi mai coincide con
    // l'inizio di una candela: va agganciato alla barra che lo contiene.
    const times = candles.map((c) => c.time);
    const snap = (t) => {
      if (t < times[0]) return null;
      let lo = 0, hi = times.length - 1, best = null;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (times[mid] <= t) { best = times[mid]; lo = mid + 1; } else { hi = mid - 1; }
      }
      return best;
    };

    return _executedOrders
      .filter((o) => {
        if ((o.symbol || "").toUpperCase() !== chartSymbol) return false;
        // Solo gli ordini andati a buon fine lasciano traccia: un tentativo
        // fallito appartiene al diario, non alla serie dei prezzi.
        return o.outcome === "ok" || o.outcome === "executed" || o.outcome === "eseguito";
      })
      .map((o) => {
        const t = snap(o.ts);
        if (t === null) return null;
        const isBuy = /long|buy|entry/i.test(o.signal_type || "");
        const auto = o.strategy_name && o.strategy_name !== "manuale";
        const price = o.price ? ` @ ${o.price}` : "";
        return {
          time: t,
          position: isBuy ? "belowBar" : "aboveBar",
          color: isBuy ? COLORS.bull : COLORS.bear,
          shape: isBuy ? "arrowUp" : "arrowDown",
          // L'etichetta dice sempre da dove viene l'ordine: automatico dalla
          // strategia, oppure premuto a mano.
          text: `● ${auto ? strategyLabel(o.strategy_name) : "manual"}${price}`,
        };
      })
      .filter(Boolean);
  }


  // Striscia sotto il grafico. Legge quello che c'e' gia' in state.data:
  // nessuna chiamata in piu', si aggiorna quando si aggiorna il grafico.
  function renderChartStats() {
    const box = el("chart-stats");
    if (!box) return;
    const tf = state.data && state.data.timeframes && state.data.timeframes[state.activeTimeframe];
    const candles = tf && tf.candles;
    if (!candles || !candles.length) { box.classList.add("hidden"); return; }
    const first = candles[0], last = candles[candles.length - 1];
    const hi = Math.max(...candles.map((c) => c.high));
    const lo = Math.min(...candles.map((c) => c.low));
    const chg = (last.close / first.close - 1) * 100;
    const fmt = (v) => Number(v).toLocaleString("en-US", { maximumFractionDigits: v < 10 ? 6 : 2 });
    el("cs-last").textContent = fmt(last.close);
    const c = el("cs-chg");
    c.textContent = (chg >= 0 ? "+" : "") + chg.toFixed(2) + "%";
    c.className = "cs-v " + (chg >= 0 ? "bull" : "bear");
    el("cs-high").textContent = fmt(hi);
    el("cs-low").textContent = fmt(lo);
    el("cs-bars").textContent = candles.length;
    const pos = el("strategy-position-badge");
    el("cs-pos").textContent = pos ? pos.textContent : "—";
    box.classList.remove("hidden");
  }

  // Distanza minima in barre tra marker di pattern/hint sullo stesso lato.
  // I marker di strategia, backtest e ordini eseguiti non vengono filtrati.
  const MARKER_MIN_BAR_GAP = 4;

  function _thinMarkers(toThin, candles) {
    if (!candles || !candles.length || !toThin.length) return toThin;
    // time→barIndex lookup
    const barIdx = new Map();
    candles.forEach((c, i) => barIdx.set(c.time, i));
    const getIdx = t => { const v = barIdx.get(t); return v !== undefined ? v : -1; };

    // Priority groups: strategy/trade/orders skip thinning; pattern/hint are thinned
    const result = [];
    const lastPerSide = { aboveBar: -Infinity, belowBar: -Infinity };
    for (const m of toThin) {
      const idx = getIdx(m.time);
      const side = m.position === "belowBar" ? "belowBar" : "aboveBar";
      if (idx < 0 || idx - lastPerSide[side] >= MARKER_MIN_BAR_GAP) {
        result.push(m);
        lastPerSide[side] = idx;
      }
    }
    return result;
  }

  function applyChartMarkers() {
    if (!candleSeries) return;
    const candles = state.data?.timeframes?.[state.activeTimeframe]?.candles || [];
    let fixed = [];   // strategy/trades/orders — never thinned
    let thinnable = []; // patterns + hints — subject to distance filter

    if (el("strategy-markers-toggle").checked) {
      fixed = fixed.concat(buildStrategyMarkers(_lastStrategySignals));
    }
    renderStrategyMarkersNote(candles);
    const tradesToggle = el("backtest-trades-toggle");
    if (tradesToggle && tradesToggle.checked) {
      fixed = fixed.concat(buildBacktestTradeMarkers());
    }
    const ordersToggle = el("executed-orders-toggle");
    if (!ordersToggle || ordersToggle.checked) {
      fixed = fixed.concat(buildExecutedOrderMarkers());
    }
    if (state.layers.patterns) {
      thinnable = thinnable.concat(autoPatternMarkers);
    }
    if (state.layers.hints) {
      thinnable = thinnable.concat(contextualHintMarkers);
    }

    // Ordina per tempo poi applica il filtro di distanza
    thinnable.sort((a, b) => a.time - b.time);
    const thinned = _thinMarkers(thinnable, candles);

    const markers = fixed.concat(thinned);
    markers.sort((a, b) => a.time - b.time);
    candleSeries.setMarkers(markers);
  }

  // Segnalazione 6da2bba6: le frecce della strategia e il numero di trade del
  // backtest non tornano per due motivi misurati, non per un errore di
  // calcolo. Il backtest profondo legge fino a backtest_candles (5000) candele
  // mentre il grafico ne ha ltf_candles (3000), quindi conta trade fuori
  // dallo schermo (SOLUSDT 4h: 67 ingressi sul grafico, 105 trade); e una
  // posizione ancora aperta ha la sua freccia ma non e' un trade chiuso.
  // Lo si dice accanto all'interruttore invece di lasciare due numeri diversi.
  function renderStrategyMarkersNote(candles) {
    const note = el("strategy-markers-note");
    if (!note) return;
    const bt = state.data && state.data.backtests ? state.data.backtests[state.activeTimeframe] : null;
    if (!el("strategy-markers-toggle").checked || !bt || !bt.trades || !candles.length) {
      note.classList.add("hidden");
      return;
    }
    const entries = _lastStrategySignals.filter((s) => s.type.startsWith("entry") || s.type.startsWith("flip")).length;
    const t0 = candles[0].time;
    const before = bt.trades.filter((t) => t.entry_time < t0).length;
    const parts = [`${entries} entries on the chart`, `backtest ${bt.num_trades} trades`];
    if (before) parts.push(`${before} of them before the chart's first candle`);
    // Si guarda l'ultimo segnale, non `position`: un ingresso senza uscita
    // successiva e' una posizione viva anche quando lo stato dice "flat".
    const last = _lastStrategySignals[_lastStrategySignals.length - 1];
    // Con stop/target attivi il backtest puo' aver gia' chiuso quell'ingresso.
    if (last && !last.type.startsWith("exit") && !bt.trades.some((t) => t.entry_time === last.time)) {
      parts.push("the last entry is still open, so it has an arrow but is not a closed trade yet");
    }
    note.textContent = parts.join(" · ") + ".";
    note.classList.remove("hidden");
  }

  // Le operazioni vere del backtest, non i segnali della strategia sul
  // timeframe del grafico. Sono cose diverse: il backtest gira su un feed piu'
  // grosso (vedi backtest_interval_for lato server), quindi le frecce dei
  // segnali non sono le righe della tabella delle operazioni — ed e' il motivo
  // per cui il grafico sembrava non tornare con il backtest.
  function buildBacktestTradeMarkers() {
    const note = el("backtest-trades-note");
    const bt = state.data && state.data.backtests
      ? state.data.backtests[state.activeTimeframe] : null;
    const candles = state.data && state.data.timeframes[state.activeTimeframe]
      ? state.data.timeframes[state.activeTimeframe].candles : null;
    if (!bt || !bt.trades || !candles || !candles.length) {
      if (note) note.classList.add("hidden");
      return [];
    }

    // Un marker deve cadere su una candela che il grafico ha davvero: il
    // backtest lavora su un timeframe piu' grosso, quindi i suoi istanti non
    // coincidono con quelli del grafico. Si aggancia alla candela aperta in
    // quel momento (l'ultima con tempo <= t) invece di sparire in silenzio.
    const times = candles.map((c) => c.time);
    const snap = (t) => {
      if (t < times[0] || t > times[times.length - 1]) return null;
      let lo = 0, hi = times.length - 1, best = null;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (times[mid] <= t) { best = times[mid]; lo = mid + 1; } else { hi = mid - 1; }
      }
      return best;
    };

    const markers = [];
    let outside = 0;
    bt.trades.forEach((t, i) => {
      const inT = snap(t.entry_time);
      const outT = snap(t.exit_time);
      if (inT === null || outT === null) { outside += 1; return; }
      const isLong = t.direction === "long";
      markers.push({
        time: inT,
        position: isLong ? "belowBar" : "aboveBar",
        color: isLong ? COLORS.bull : COLORS.bear,
        shape: isLong ? "arrowUp" : "arrowDown",
        text: `#${i + 1} ${isLong ? "long" : "short"}`,
      });
      markers.push({
        time: outT,
        position: isLong ? "aboveBar" : "belowBar",
        color: t.pnl_pct >= 0 ? COLORS.bull : COLORS.bear,
        shape: "square",
        text: `#${i + 1} ${t.pnl_pct >= 0 ? "+" : ""}${t.pnl_pct.toFixed(1)}%`,
      });
    });

    if (note) {
      const parts = [`${bt.trades.length - outside} of ${bt.trades.length} trades on the chart`];
      if (outside) parts.push(`${outside} outside the visible range`);
      const shown = state.data.timeframes[state.activeTimeframe].interval;
      if (bt.interval && shown && bt.interval !== shown) {
        parts.push(`backtest on ${bt.interval}, chart on ${shown}: each trade is pinned to the candle open at that moment`);
      }
      note.textContent = parts.join(" · ") + ".";
      note.classList.remove("hidden");
    }
    return markers;
  }

  function notifyNewAlerts(allSignals) {
    const isFirstPass = !state.alertsSeeded;
    allSignals.forEach((sig) => {
      const key = `${state.data.symbol}|${sig.tf}|${sig.time}|${sig.type}`;
      if (state.seenAlertKeys.has(key)) return;
      state.seenAlertKeys.add(key);
      if (isFirstPass) return;
      if (
        el("strategy-notify-toggle").checked &&
        "Notification" in window &&
        Notification.permission === "granted"
      ) {
        new Notification(`${state.data.symbol} [${sig.tf.toUpperCase()}] Trend EMA`, {
          body: `${sig.label} @ ${sig.price}`,
        });
      }
    });
    state.alertsSeeded = true;
  }

  // Shared by both the built-in strategy backtest (renderBacktest) and a
  // Pine script override (renderPineBacktest) — same result shape, same UI.
  // Equity chart is the hero: the % return + final equity are stamped on it
  // directly instead of living in a KPI tile, and its time axis is left on
  // (see initCharts) so the curve reads against real dates. Below it, only
  // the 3 ratios a trader actually scans for stay always-visible as chips;
  // trade count/final equity move into "Dettagli", and every individual
  // trade — with its entry/exit date — gets its own row in Operazioni so
  // "when did this happen" has an actual answer instead of just an aggregate.
  function renderBacktestUI(bt) {
    if (!bt) return;

    // The backtest runs on a deliberately coarser feed than the chart when
    // ltf is finer than daily (see backtest_interval_for on the backend) —
    // surface which interval it actually used instead of implying it always
    // matches the chart's own timeframe.
    // These elements were in the old Backtest panel — now removed. Guard
    // against null so the function still works for operations/equity.
    const tagEl = el("backtest-interval-tag");
    if (tagEl) tagEl.textContent = bt.interval ? `(${bt.interval})` : "";

    const pctEl = el("equity-stamp-pct");
    if (pctEl) {
      // 15/10: simple and compounded side by side, same size
      const sp = bt.simple_return_pct;
      const f = (x) => `${x >= 0 ? "+" : ""}${x.toFixed(1)}%`;
      pctEl.innerHTML = (sp != null ? `<span class="${sp >= 0 ? "positive" : "negative"}" title="Simple: every trade on the same stake, gains not reinvested">${f(sp)}<small> simple</small></span> · ` : "")
        + `<span class="${bt.total_return_pct >= 0 ? "positive" : "negative"}" title="Compounded: every trade reinvests all the equity so far">${f(bt.total_return_pct)}<small> compounded</small></span>`;
      pctEl.className = "equity-stamp-pct";
    }
    const subEl = el("equity-stamp-sub");
    if (subEl) subEl.textContent = `equity ${bt.final_equity.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;

    const chipsEl = el("backtest-chips");
    if (chipsEl) {
      chipsEl.innerHTML = "";
      [
        ["Win rate", bt.win_rate_pct !== null ? `${bt.win_rate_pct.toFixed(0)}%` : "—", ""],
        ["Simple drawdown", bt.simple_max_drawdown_pct != null ? `-${bt.simple_max_drawdown_pct.toFixed(1)}%` : "—", "negative"],
        ["Compounded drawdown", `-${bt.max_drawdown_pct.toFixed(1)}%`, "negative"],
        ["Profit factor", bt.profit_factor !== null ? bt.profit_factor.toFixed(2) : "—", ""],
      ].forEach(([label, value, cls]) => {
        const div = document.createElement("div");
        div.className = "chip";
        div.innerHTML = `<div class="chip-label">${label}</div><div class="chip-value ${cls}">${value}</div>`;
        chipsEl.appendChild(div);
      });
    }

    const detailsEl = el("backtest-details");
    if (detailsEl) detailsEl.innerHTML = `
      <div class="stat"><div class="stat-label">Trade</div><div class="stat-value">${bt.num_trades}</div></div>
      <div class="stat"><div class="stat-label">Final equity</div><div class="stat-value">${bt.final_equity.toLocaleString("en-US", { maximumFractionDigits: 0 })}</div></div>
    `;

    el("operations-count").textContent = bt.num_trades ? `${bt.num_trades}` : "";
    const opsList = el("operations-list");
    opsList.innerHTML = "";
    if (!bt.trades.length) {
      opsList.innerHTML = `<li class="operations-empty">No trades in the period</li>`;
    } else {
      const dateFmt = { day: "2-digit", month: "short", year: "2-digit" };
      [...bt.trades].reverse().forEach((t) => {
        const li = document.createElement("li");
        li.className = "operation-row";
        const dirIcon = t.direction === "long" ? "▲" : "▼";
        const entryDate = new Date(t.entry_time * 1000).toLocaleDateString("en-US", dateFmt);
        const exitDate = new Date(t.exit_time * 1000).toLocaleDateString("en-US", dateFmt);
        const pnlClass = t.pnl_pct >= 0 ? "positive" : "negative";
        li.innerHTML = `
          <span class="op-dir ${t.direction}">${dirIcon}</span>
          <span class="op-dates">${entryDate} → ${exitDate}</span>
          <span class="op-pnl ${pnlClass}">${t.pnl_pct >= 0 ? "+" : ""}${t.pnl_pct.toFixed(1)}%</span>
        `;
        opsList.appendChild(li);
      });
    }

    if (equitySeries) {
      equitySeries.setData(bt.equity_curve.map(([time, equity]) => ({ time, value: equity })));
      equityChart.timeScale().fitContent();
    }
  }

  function renderBacktest() {
    renderBacktestUI(state.data.backtests[state.activeTimeframe]);
  }

  function getStrategyAndBacktestQuery() {
    const form = el("params-form");
    const params = new URLSearchParams();
    const strategyName = el("active-strategy-select").value;
    (STRATEGY_PARAM_FIELDS[strategyName] || []).forEach((field) => {
      const input = form.elements[field.key];
      if (!input) return;
      params.set(field.key, field.type === "checkbox" ? input.checked
        : field.type === "select" ? input.value
        : fieldNumber(input, field));
    });
    // Backtest params: puliti per default — 100% equity, zero costi — cosi'
    // il grafico resta un riferimento stabile quando si sceglie una
    // strategia dalla toolbar. Ma se l'ultima cosa fatta e' stata "Applica al
    // grafico" dal Laboratorio o dall'archivio, il grafico deve mostrare
    // ESATTAMENTE quel backtest — capitale, taglia, commissione, slippage
    // compresi — non una sua versione ripulita: e' la segnalazione
    // "i trade continuano a non essere correttamente applicati".
    const bp = state.chartBacktestOverride;
    params.set("initial_capital", String(bp ? bp.initial_capital : 1000));
    params.set("qty_pct_of_equity", String(bp ? bp.qty_pct_of_equity : 100));
    params.set("commission_pct", String(bp ? bp.commission_pct : 0));
    params.set("slippage_pct", String(bp ? bp.slippage_pct : 0));
    // Same fill rule as the Lab run it came from (316219de): without it the
    // chart quietly fell back to the candle close.
    if (bp && bp.fill_at) params.set("fill_at", bp.fill_at);
    params.set("stop_loss_pct", "0");
    params.set("take_profit_pct", "0");
    params.set("strategy_name", strategyName);
    return params.toString();
  }

  // Rebuilds the "Strategia" fieldset's fields for whichever strategy is
  // currently active — each one has its own differently-shaped parameter
  // set (STRATEGY_PARAM_FIELDS), so this is what actually makes them
  // visible/editable instead of only ever showing l'utente's.
  function renderStrategyParamsFields() {
    const strategyName = el("active-strategy-select").value;
    const fields = STRATEGY_PARAM_FIELDS[strategyName] || [];
    const container = el("strategy-params-fields");
    container.innerHTML = "";
    fields.forEach((field) => {
      const label = document.createElement("label");
      if (field.type === "checkbox") {
        label.innerHTML = `<input type="checkbox" name="${field.key}" ${field.default ? "checked" : ""} /> ${field.label}`;
      } else if (field.type === "select") {
        const options = field.options
          .map((opt) => `<option value="${opt}"${opt === field.default ? " selected" : ""}>${opt}</option>`)
          .join("");
        label.innerHTML = `${field.label} <select name="${field.key}">${options}</select>`;
      } else {
        // Testo con tastiera numerica, non <input type="number">: quello
        // scarta la virgola decimale a seconda del browser — la butta via in
        // silenzio o svuota il campo — e in entrambi i casi quello che parte
        // non e' quello che era stato scritto. Qui il testo resta com'e' e
        // lo normalizza fieldNumber() al momento di mandarlo.
        label.innerHTML = `${field.label} <input type="text" inputmode="decimal" name="${field.key}" value="${field.default}" />`;
      }
      container.appendChild(label);
    });
    addStrategyExtras(container, strategyName);
  }

  function renderSummary() {
    const summary = state.data.summary;
    el("summary-text").textContent = summary.text;

    const ltcList = el("long-term-context");
    ltcList.innerHTML = "";
    summary.long_term_context.forEach((line) => {
      const li = document.createElement("li");
      li.textContent = line;
      ltcList.appendChild(li);
    });

    const readoutList = el("indicator-readout");
    readoutList.innerHTML = "";
    summary.indicator_readout.forEach((line) => {
      const li = document.createElement("li");
      li.textContent = line;
      readoutList.appendChild(li);
    });

    const list = el("confluence-list");
    list.innerHTML = "";
    if (summary.top_confluence_zones.length === 0) {
      const li = document.createElement("li");
      li.textContent = "No multi-timeframe confluence zones detected right now.";
      list.appendChild(li);
    }
    summary.top_confluence_zones.forEach((z) => {
      const li = document.createElement("li");
      const range = document.createElement("div");
      range.className = "cz-range";
      range.textContent = `${z.price_low.toPrecision(6)} — ${z.price_high.toPrecision(6)}`;
      const label = document.createElement("div");
      label.textContent = z.label;
      // Il punteggio come barra: quante conferme coincidono in quella zona si
      // confronta a colpo d'occhio fra righe, un numero no.
      const maxScore = Math.max(...summary.top_confluence_zones.map((x) => x.score || 0), 1);
      const bar = document.createElement("div");
      bar.className = "cz-bar";
      const fill = document.createElement("i");
      fill.style.width = `${Math.round(((z.score || 0) / maxScore) * 100)}%`;
      bar.appendChild(fill);
      const tfs = document.createElement("span");
      tfs.className = "cz-tf";
      tfs.textContent = `${(z.timeframes || []).length} TF`;
      li.appendChild(label);
      li.appendChild(range);
      li.appendChild(bar);
      li.appendChild(tfs);
      list.appendChild(li);
    });
  }

  function showError(message) {
    const banner = el("error-banner");
    banner.textContent = `${message} Check the ticker and the selected asset type (Stocks/Crypto).`;
    banner.classList.remove("hidden");
  }

  function clearError() {
    el("error-banner").classList.add("hidden");
  }

  function applyLiveCandle(timeframe, candle) {
    if (!state.data || !state.data.timeframes[timeframe]) return;
    const candles = state.data.timeframes[timeframe].candles;
    const last = candles[candles.length - 1];
    if (last && last.time === candle.time) {
      candles[candles.length - 1] = candle;
    } else if (!last || candle.time > last.time) {
      candles.push(candle);
      if (timeframe === state.activeTimeframe) setDrawTimes(candles);
    } else {
      return; // out-of-order/stale tick
    }
    noteOhlcCandle(candles);
    if (timeframe === state.activeTimeframe) {
      try {
        candleSeries.update(candle);
      } catch (err) {
        /* rare out-of-order update from the live feed; next tick self-corrects */
      }
    }
  }

  function disconnectLiveFeed() {
    if (state.liveSocket) {
      const ws = state.liveSocket;
      state.liveSocket = null; // cleared first so the socket's own close handler won't reconnect
      ws.close();
    }
    if (state.liveRefreshTimer) {
      clearInterval(state.liveRefreshTimer);
      state.liveRefreshTimer = null;
    }
    el("live-badge").classList.add("hidden");
    el("polling-badge").classList.add("hidden");
  }

  function intervalQuery() {
    const iv = getSelectedIntervals();
    return `htf_interval=${iv.htf}&mtf_interval=${iv.mtf}&ltf_interval=${iv.ltf}`;
  }

  function connectLiveFeed(symbol) {
    disconnectLiveFeed();
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(
      `${proto}://${location.host}/ws/live?symbol=${encodeURIComponent(symbol)}&exchange=${state.cryptoExchange}&${intervalQuery()}`
    );
    state.liveSocket = ws;

    ws.addEventListener("open", () => el("live-badge").classList.remove("hidden"));
    ws.addEventListener("message", (event) => {
      try {
        const msg = JSON.parse(event.data);
        state.liveLastMsg = Date.now();
        applyLiveCandle(msg.timeframe, msg.candle);
      } catch (err) {
        /* ignore malformed frame */
      }
    });
    ws.addEventListener("close", () => {
      el("live-badge").classList.add("hidden");
      if (state.liveSocket === ws && state.assetType === "crypto" && state.data && state.data.symbol === symbol) {
        setTimeout(() => connectLiveFeed(symbol), 3000);
      }
    });
    ws.addEventListener("error", () => ws.close());
  }

  // The 60 s full /api/analyze (3000 candles, every indicator, the
  // backtest) is the fallback for a missing or silent live feed. With the
  // feed alive, candles already arrive tick by tick: the full pass only has
  // to catch new strategy markers, so once per candle, at most every 5 min
  // (overhaul plan, week 4).
  const TF_SECONDS = { "1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600 };
  function liveFeedHealthy() {
    return !!state.liveSocket && state.liveSocket.readyState === 1
      && Date.now() - (state.liveLastMsg || 0) < 90000;
  }
  function fullRefreshEveryMs() {
    const sec = TF_SECONDS[getSelectedIntervals().ltf] || 300;
    return Math.min(300, Math.max(60, sec)) * 1000;
  }

  async function silentRefresh(symbol) {
    if (!state.data || state.data.symbol !== symbol) return;
    const seq = state.analyzeSeq;
    try {
      const url = `/api/analyze?symbol=${encodeURIComponent(symbol)}&asset_type=${state.assetType}&exchange=${state.cryptoExchange}&${intervalQuery()}&${getStrategyAndBacktestQuery()}`;
      const resp = await fetch(url);
      // A search started meanwhile owns the chart now.
      if (seq !== state.analyzeSeq || !state.data || state.data.symbol !== symbol) return;
      if (!resp.ok) {
        showTabError("error-banner", `Auto-refresh failed (${resp.status}).`);
        return;
      }
      // Il backtest "profondo" gia' caricato (refreshDeepBacktest, sulla
      // storia intera) e' sempre piu' completo di quello "superficiale" che
      // /api/analyze ricalcola ogni volta (solo l'ultima pagina di candele)
      // — sovrascriverlo qui senza guardare riportava indietro i marker sul
      // grafico a un sottoinsieme di trade diverso ogni 60 secondi, anche
      // dopo che il profondo era gia' arrivato una volta. Le chiavi del
      // profondo vincono; quelle di un timeframe non ancora approfondito
      // restano quelle fresche appena arrivate.
      const deepBacktests = state.data.backtests;
      state.data = await resp.json();
      if (deepBacktests) {
        state.data.backtests = { ...state.data.backtests, ...deepBacktests };
      }
      state.lastFullRefresh = Date.now();
      render();
    } catch (err) {
      /* keep last known state; live ticks keep flowing independently */
    }
  }

  async function runAnalysis(symbol) {
    clearError();
    el("loading").classList.remove("hidden");
    el("empty-state").classList.add("hidden");
    el("chart-wrap").classList.add("hidden");
    disconnectLiveFeed();

    // Only the latest request may draw (overhaul plan, week 1): a timeframe
    // change and a new search in flight together let the older answer land
    // last and show the previous ticker.
    const seq = (state.analyzeSeq = (state.analyzeSeq || 0) + 1);
    await withAsyncButton(el("search-btn"), async () => {
      const url = `/api/analyze?symbol=${encodeURIComponent(symbol)}&asset_type=${state.assetType}&exchange=${state.cryptoExchange}&${intervalQuery()}&${getStrategyAndBacktestQuery()}`;
      const resp = await fetch(url);
      const body = await resp.json();
      if (seq !== state.analyzeSeq) return;
      if (!resp.ok) {
        const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
        throw new Error(detail || `Error ${resp.status}`);
      }
      state.data = body;
      // Whatever opened the chart (watchlist, archive, a link), the box at
      // the top names what is on it — unless the user is typing there.
      const box = el("ticker-input");
      if (box && document.activeElement !== box && body.symbol && body.asset_type !== "dex") {
        box.value = body.symbol;
        box.title = body.symbol;
      }
      state.seenAlertKeys = new Set();
      state.alertsSeeded = false;
      if (state.pineActive) clearPineOverride();
      el("chart-wrap").classList.remove("hidden");
      resizeAllCharts();
      // Detach the previous symbol's drawings before the new candle data
      // loads, not after — a leftover horizontal-line price line (or any
      // primitive) from the old symbol staying attached while render()
      // sets data at a wildly different price magnitude (e.g. BTC's
      // ~90000 vs. a $1-2 altcoin) stretches the price scale's autoscale
      // to cover both, squeezing the real candles down to an invisible
      // sliver — and it doesn't shrink back down on its own afterward.
      loadDrawingsForSymbol();
      render();
      notifyParent(true);
      renderFavorites();
      savePreferences();
      refreshDeepBacktest(symbol);
      // Live WS streaming is wired up for MEXC and Kraken; every crypto
      // symbol still gets the periodic refresh below regardless of exchange,
      // as a fallback if the live feed drops or the pair has no ws channel.
      const LIVE_WS_EXCHANGES = new Set(["mexc", "kraken"]);
      if (state.assetType === "crypto" && LIVE_WS_EXCHANGES.has(state.cryptoExchange)) {
        connectLiveFeed(body.symbol);
      }
      if (state.assetType === "crypto") {
        state.lastFullRefresh = Date.now();
        state.liveRefreshTimer = setInterval(() => {
          if (liveFeedHealthy() && Date.now() - (state.lastFullRefresh || 0) < fullRefreshEveryMs()) return;
          silentRefresh(body.symbol);
        }, 60000);
        // No WebSocket wired up for Binance/KuCoin yet — say so plainly
        // instead of leaving the user guessing whether the chart updates.
        if (!LIVE_WS_EXCHANGES.has(state.cryptoExchange)) {
          el("polling-badge").classList.remove("hidden");
        }
      }
    }).catch((err) => {
      if (seq !== state.analyzeSeq) return; // a newer search owns the screen
      if (EMBED && !embedRetried) {
        embedRetried = true;
        setTimeout(() => runAnalysis(symbol), 4000);
        return;
      }
      notifyParent(false, err.message || "");
      showError(err.message || "Error while analyzing the ticker.");
      el("empty-state").classList.remove("hidden");
    }).finally(() => {
      if (seq === state.analyzeSeq) el("loading").classList.add("hidden");
    });
  }

  // /api/analyze answers instantly using whatever ltf_candles fetched (a
  // single page per exchange), so the backtest shown at first is only as
  // deep as that — good enough to not block the chart on. This follows up
  // in the background with the real, paginated deep-history backtest and
  // swaps the Strategia panel over once it resolves. A monotonically
  // increasing token guards against a slow response from an earlier
  // symbol/timeframe landing after a newer one already replaced it.
  let deepBacktestSeq = 0;

  async function refreshDeepBacktest(symbol) {
    const seq = ++deepBacktestSeq;
    try {
      const url = `/api/backtest/deep?symbol=${encodeURIComponent(symbol)}&asset_type=${state.assetType}&exchange=${state.cryptoExchange}&ltf_interval=${getSelectedIntervals().ltf}&${getStrategyAndBacktestQuery()}`;
      const resp = await fetch(url);
      if (!resp.ok || seq !== deepBacktestSeq || !state.data) return;
      const bt = await resp.json();
      state.data.backtests[state.activeTimeframe] = bt;
      renderBacktest();
      // Il backtest profondo arriva dopo il primo disegno: i marker delle
      // operazioni vanno rifatti su questo, non su quello della passata rapida.
      applyChartMarkers();
    } catch (err) {
      // The fast-pass backtest already rendered — losing the deeper one
      // silently is fine, nothing on screen depends on it.
    }
  }

  // ---- Alert tab: ticker autocomplete that also confirms the exact pair
  // + exchange before the ticker can be added, instead of trusting free
  // text — the same source of truth as the main search (/api/symbols), just
  // filtered to the asset type/exchange currently selected in the form. ----
  const wlSuggest = makeSuggestController({
    listId: "watchlist-suggestions",
    anchorId: "watchlist-symbol",
    fetchItems: async (query) => {
      const resp = await fetch(`/api/symbols?query=${encodeURIComponent(query)}`);
      const all = resp.ok ? await resp.json() : [];
      return state.watchlistAssetType === "crypto"
        ? all.filter((s) => s.asset_type === "crypto" && s.provider === el("watchlist-exchange").value)
        : all.filter((s) => s.asset_type === "stock");
    },
    onSelect: (item) => {
      el("watchlist-symbol").value = item.symbol;
      wlSuggest.resolved = item;
      wlSuggest.clear();
      showResolvedPair(item);
    },
  });
  let wlSuggestTimer = null;

  function showResolvedPair(item) {
    const p = el("watchlist-resolved-pair");
    if (!item) {
      p.classList.add("hidden");
      p.textContent = "";
      return;
    }
    p.textContent = `✓ ${item.symbol} — ${item.exchange}`;
    p.classList.remove("hidden");
  }

  function bindWatchlistAutocomplete() {
    const input = el("watchlist-symbol");
    input.addEventListener("input", () => {
      wlSuggest.resolved = null; // typing invalidates whatever was confirmed before
      showResolvedPair(null);
      const value = input.value.trim();
      clearTimeout(wlSuggestTimer);
      if (!value) { wlSuggest.clear(); return; }
      wlSuggestTimer = setTimeout(() => wlSuggest.fetch(value), 300);
    });
    input.addEventListener("keydown", (e) => wlSuggest.handleKey(e));
    input.addEventListener("blur", () => setTimeout(() => wlSuggest.clear(), 150));
  }

  // ---- Watchlist tab: a plain list of favorite tickers for one-click chart
  // navigation. Separate from the Alert tab's watchlist (background Telegram
  // monitoring) — a ticker can be pinned here, watched there, both, or
  // neither. The add form searches the same /api/symbols source as the main
  // header search (each result already carries its own asset_type/exchange,
  // so there's no separate asset-type toggle to get right before adding). ----
  const favSuggest = makeSuggestController({
    listId: "favorite-suggestions",
    anchorId: "favorite-symbol",
    fetchItems: async (query) => {
      const resp = await fetch(`/api/symbols?query=${encodeURIComponent(query)}`);
      return resp.ok ? await resp.json() : [];
    },
    onSelect: (item) => {
      el("favorite-symbol").value = item.symbol;
      favSuggest.resolved = item;
      favSuggest.clear();
    },
  });
  let favSuggestTimer = null;

  function bindFavoriteAutocomplete() {
    const input = el("favorite-symbol");
    input.addEventListener("input", () => {
      favSuggest.resolved = null;
      const value = input.value.trim();
      clearTimeout(favSuggestTimer);
      if (!value) { favSuggest.clear(); return; }
      favSuggestTimer = setTimeout(() => favSuggest.fetch(value), 300);
    });
    input.addEventListener("keydown", (e) => favSuggest.handleKey(e));
    input.addEventListener("blur", () => setTimeout(() => favSuggest.clear(), 150));
  }

  const FAV_AVATAR_COLORS = ["#f0b90b", "#23af91", "#5850ec", "#94a3b8", "#2962ff", "#f23645", "#089981"];
  function favAvatarColor(symbol) {
    let hash = 0;
    for (let i = 0; i < symbol.length; i++) hash = (hash * 31 + symbol.charCodeAt(i)) >>> 0;
    return FAV_AVATAR_COLORS[hash % FAV_AVATAR_COLORS.length];
  }

  // Star next to the ticker field (board issue 227a6142): adds the pair on
  // the chart to YOUR TICKERS, or removes it when it is already there.
  function currentChartPair() {
    if (!state.data || !state.data.symbol) return null;
    return {
      symbol: state.data.symbol,
      asset_type: state.assetType,
      exchange: state.assetType === "crypto" ? state.cryptoExchange : "mexc",
    };
  }

  function favoriteForPair(pair) {
    if (!pair) return null;
    return (state.favorites || []).find((f) =>
      f.symbol === pair.symbol && f.asset_type === pair.asset_type &&
      (pair.asset_type !== "crypto" || f.exchange === pair.exchange)) || null;
  }

  function updateWatchStar() {
    const btn = el("watch-star-btn");
    if (!btn) return;
    const pair = currentChartPair();
    btn.classList.toggle("hidden", !pair);
    if (!pair) return;
    const saved = !!favoriteForPair(pair);
    btn.classList.toggle("saved", saved);
    btn.setAttribute("aria-pressed", saved ? "true" : "false");
    btn.title = saved
      ? `${shortSymbol(pair.symbol)} is in the Watchlist — click to remove it`
      : `Add ${shortSymbol(pair.symbol)} to the Watchlist`;
  }

  // The error banner, without showError's "check the ticker" tail: here the
  // ticker is fine.
  function watchStarNotice(message) {
    const banner = el("error-banner");
    banner.textContent = message;
    banner.classList.remove("hidden");
  }

  function bindWatchStar() {
    const btn = el("watch-star-btn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
      const pair = currentChartPair();
      if (!pair) return;
      if (!state.user) {
        watchStarNotice("Log in to save tickers to the Watchlist.");
        return;
      }
      btn.disabled = true;
      try {
        const existing = favoriteForPair(pair);
        const resp = existing
          ? await fetch(`/api/favorites/${existing.id}`, { method: "DELETE" })
          : await fetch("/api/favorites", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(pair),
            });
        if (!resp.ok) throw new Error(`Error ${resp.status}`);
        await loadFavorites();
      } catch (err) {
        watchStarNotice(`Couldn't update the Watchlist: ${err.message || "network problem"}.`);
      } finally {
        btn.disabled = false;
      }
    });
  }

  async function loadFavorites() {
    try {
      const resp = await fetch("/api/favorites");
      state.favorites = resp.ok ? await resp.json() : [];
    } catch (err) {
      state.favorites = [];
    }
    renderFavorites();
    loadFavoriteQuotes();
  }

  async function loadFavoriteQuotes() {
    if (!state.favorites.length) return;
    try {
      const resp = await fetch("/api/favorites/quotes");
      if (resp.ok) {
        const quotes = await resp.json();
        state.favoriteQuotes = {};
        quotes.forEach((q) => { state.favoriteQuotes[q.id] = q; });
      } else {
        showTabError("favorite-rows", `Error refreshing quotes (${resp.status}).`);
      }
    } catch (err) {
      showTabError("favorite-rows", "Couldn't refresh quotes: network problem.");
    }
    renderFavorites();
  }

  // YOUR TICKERS ordering (board issue d46f02f7): saved order, day % change
  // or market-cap rank, each in both directions. A second tap on the active
  // key flips the direction. Rows without a value always go last.
  const FAV_SORT_KEY = "favoriteSort";
  function loadFavoriteSort() {
    try {
      const v = JSON.parse(localStorage.getItem(FAV_SORT_KEY) || "null");
      if (v && ["saved", "change", "rank"].includes(v.key) && (v.dir === 1 || v.dir === -1)) return v;
    } catch { /* storage unavailable */ }
    return { key: "saved", dir: 1 };
  }
  let favoriteSort = loadFavoriteSort();

  function sortFavorites(items) {
    const { key, dir } = favoriteSort;
    if (key === "saved") return items;
    const val = (f) => {
      const q = state.favoriteQuotes[f.id];
      const v = q ? (key === "rank" ? q.rank : q.change_pct) : null;
      return v == null || !Number.isFinite(v) ? null : v;
    };
    return items
      .map((f, i) => ({ f, i, v: val(f) }))
      .sort((a, b) => {
        if (a.v === null && b.v === null) return a.i - b.i;
        if (a.v === null) return 1;
        if (b.v === null) return -1;
        return (a.v - b.v) * dir || a.i - b.i;
      })
      .map((x) => x.f);
  }

  function renderFavoriteSortButtons() {
    document.querySelectorAll("[data-fav-sort]").forEach((btn) => {
      const key = btn.dataset.favSort;
      const on = key === favoriteSort.key;
      btn.classList.toggle("active", on);
      const label = key === "saved" ? "Saved" : key === "change" ? "Day %" : "Rank";
      btn.textContent = on && key !== "saved" ? `${label} ${favoriteSort.dir === 1 ? "↑" : "↓"}` : label;
    });
  }

  function bindFavoriteSort() {
    document.querySelectorAll("[data-fav-sort]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.favSort;
        if (key === favoriteSort.key && key !== "saved") {
          favoriteSort = { key, dir: -favoriteSort.dir };
        } else {
          // First tap: best first — biggest gain, rank #1.
          favoriteSort = { key, dir: key === "change" ? -1 : 1 };
        }
        try { localStorage.setItem(FAV_SORT_KEY, JSON.stringify(favoriteSort)); } catch { /* ignore */ }
        renderFavorites();
      });
    });
  }

  function renderFavorites() {
    updateWatchStar();
    const rows = el("favorite-rows");
    const empty = el("favorite-empty");
    const openIds = new Set(
      Array.from(rows.querySelectorAll(".wl-row-wrap.open")).map((li) => li.dataset.favId)
    );
    const autoOpenId = state.autoOpenFavoriteId;
    if (autoOpenId) openIds.add(autoOpenId);
    state.autoOpenFavoriteId = null; // un solo giro: non riaprirlo ad ogni refresh successivo
    rows.innerHTML = "";

    const items = sortFavorites(state.favorites.filter(
      (f) => state.favoriteFilter === "all" || f.asset_type === state.favoriteFilter
    ));
    renderFavoriteSortButtons();

    el("favorites-count").textContent = state.favorites.length
      ? `${state.favorites.length} saved`
      : "";
    empty.classList.toggle("hidden", state.favorites.length > 0);
    if (!items.length) return;

    const activeSymbol = state.data && state.data.symbol;

    items.forEach((entry) => {
      const wrap = document.createElement("li");
      wrap.className = "wl-row-wrap" + (openIds.has(entry.id) ? " open" : "");
      wrap.dataset.favId = entry.id;

      const li = document.createElement("div");
      const isActive =
        !!activeSymbol &&
        entry.symbol === activeSymbol &&
        entry.asset_type === state.assetType &&
        (entry.asset_type !== "crypto" || entry.exchange === state.cryptoExchange);
      li.className = "wl-row" + (isActive ? " active" : "");

      const avatar = document.createElement("div");
      avatar.className = "wl-avatar";
      avatar.style.background = favAvatarColor(entry.symbol);
      avatar.textContent = entry.symbol.charAt(0);

      const main = document.createElement("div");
      main.className = "wl-main";
      const symRow = document.createElement("div");
      symRow.className = "wl-sym-row";
      const sym = document.createElement("span");
      sym.className = "wl-sym";
      sym.textContent = shortSymbol(entry.symbol);
      sym.title = entry.symbol;
      symRow.appendChild(sym);
      const rankQ = state.favoriteQuotes[entry.id];
      if (rankQ && rankQ.rank != null) {
        const rk = document.createElement("span");
        rk.className = "wl-rank";
        rk.title = "Global market-cap rank (CoinPaprika)";
        rk.textContent = `#${rankQ.rank}`;
        symRow.appendChild(rk);
      }
      const badge = document.createElement("span");
      badge.className = "wl-badge";
      badge.textContent = entry.asset_type === "crypto" ? entry.exchange : "stocks";
      symRow.appendChild(badge);
      const hasAlert = (state.alertEntries || []).some(
        (a) => a.symbol === entry.symbol && a.asset_type === entry.asset_type && a.exchange === entry.exchange
      );
      if (hasAlert) {
        const bell = document.createElement("span");
        bell.className = "wl-bell";
        bell.title = "Telegram alert active on this ticker";
        bell.textContent = "●";
        symRow.appendChild(bell);
      }
      main.appendChild(symRow);
      const exch = document.createElement("div");
      exch.className = "wl-exch";
      exch.textContent = isActive ? "On chart now" : entry.asset_type === "crypto" ? `${entry.exchange} · crypto` : "stocks";
      main.appendChild(exch);

      const quote = state.favoriteQuotes[entry.id];
      // Sparkline: the /api/favorites/quotes endpoint only ever gives the
      // last price and the day-over-day % change, never a full history —
      // so a full wiggly line would be invented data. What IS real is the
      // two points that change_pct already implies (yesterday's close,
      // derived from price and pct, and today's price): draw those, not a
      // fabricated curve.
      const sparkWrap = document.createElement("div");
      sparkWrap.className = "wl-spark-wrap";
      if (quote && quote.price != null && quote.change_pct != null) {
        const prevClose = quote.price / (1 + quote.change_pct / 100);
        const up = quote.change_pct >= 0;
        const y0 = 20, y1 = up ? 4 : 20, yMid = up ? 20 : 4;
        // simple 2-segment path: flat lead-in, then the real move.
        sparkWrap.innerHTML =
          `<svg class="wl-spark" viewBox="0 0 48 24" role="img" aria-label="Change ${quote.change_pct.toFixed(2)}%">` +
          `<path d="M2,${y0} L24,${y0} L46,${y1}" fill="none" stroke="${up ? "var(--bull)" : "var(--bear)"}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>` +
          `<circle cx="46" cy="${y1}" r="2" fill="${up ? "var(--bull)" : "var(--bear)"}"/>` +
          `</svg>`;
      } else {
        sparkWrap.innerHTML = `<span class="wl-spark-empty">—</span>`;
      }

      const right = document.createElement("div");
      right.className = "wl-right";
      const price = document.createElement("div");
      price.className = "wl-price";
      price.textContent =
        quote && quote.price != null
          ? quote.price.toLocaleString("en-US", { maximumFractionDigits: quote.price < 10 ? 4 : 2 })
          : "—";
      right.appendChild(price);
      const change = document.createElement("div");
      const pct = quote && quote.change_pct;
      change.className = "wl-change " + (pct > 0 ? "up" : pct < 0 ? "down" : "flat");
      change.textContent = pct != null ? `${pct > 0 ? "+" : ""}${pct.toFixed(2)}%` : "—";
      right.appendChild(change);

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "wl-remove";
      remove.textContent = "✕";
      remove.title = "Remove from watchlist";
      remove.addEventListener("click", async (e) => {
        e.stopPropagation();
        await fetch(`/api/favorites/${entry.id}`, { method: "DELETE" });
        loadFavorites();
      });

      // Il clic sulla riga carica il grafico (comportamento di sempre); la
      // freccia apre/chiude — separata apposta — il pannello dove si decide
      // alert/automatico e si sceglie la strategia. E' il punto di ingresso
      // unico chiesto da Richiesta: tutto parte da qui, non da una tab diversa.
      const caret = document.createElement("button");
      caret.type = "button";
      caret.className = "wl-row-caret";
      caret.title = "Alerts and auto-trading for this ticker";
      caret.textContent = "▾";
      caret.addEventListener("click", (e) => {
        e.stopPropagation();
        wrap.classList.toggle("open");
        if (wrap.classList.contains("open")) renderFavoriteExpansion(wrap, entry);
      });

      li.appendChild(avatar);
      li.appendChild(main);
      li.appendChild(sparkWrap);
      // La freccetta sta PRIMA di .wl-right apposta: .wl-remove e' assoluto
      // nell'angolo in alto a destra della riga, la stessa zona dove il
      // clic per aprire/chiudere aveva finito per finire sotto la ✕ al
      // passaggio del mouse.
      li.appendChild(caret);
      li.appendChild(right);
      li.appendChild(remove);
      li.addEventListener("click", () => {
        state.assetType = entry.asset_type;
        if (entry.asset_type === "crypto") state.cryptoExchange = entry.exchange;
        // The search box at the top is where the pair is named: it kept the
        // previous one while the chart showed this (58512aa5).
        el("ticker-input").value = entry.symbol;
        el("ticker-input").title = entry.symbol;
        runAnalysis(entry.symbol);
      });
      wrap.appendChild(li);

      const expand = document.createElement("div");
      expand.className = "wl-row-expand";
      wrap.appendChild(expand);
      if (wrap.classList.contains("open")) renderFavoriteExpansion(wrap, entry, entry.id === autoOpenId);

      rows.appendChild(wrap);
    });
  }

  // Pannello aperto dalla freccia di una riga Watchlist: mostra le strategie
  // gia' attive su questo ticker (se un WatchlistEntry corrispondente esiste
  // gia', creato da un'attivazione precedente) e sempre il modo per
  // aggiungerne un'altra — stesso buildActivationFlow usato in Alert,
  // qui e' solo il punto da cui si apre.
  function renderFavoriteExpansion(wrap, favEntry, autoOpen) {
    const box = wrap.querySelector(".wl-row-expand");
    box.innerHTML = "";
    const match = (state.alertEntries || []).find(
      (a) => a.symbol === favEntry.symbol && a.asset_type === favEntry.asset_type && a.exchange === favEntry.exchange
    );
    if (match && match.strategies.length) {
      const list = document.createElement("div");
      list.className = "wl-row-strats";
      match.strategies.forEach((name) => {
        const row = document.createElement("div");
        row.className = "wl-row-strat-item";
        const isAuto = !!match.auto_trade?.[name];
        const isFutures = match.market?.[name] === "futures";
        row.innerHTML = `<b>${escapeHtml(strategyLabel(name))}</b> <span class="wl-mini-badge${isAuto ? " danger" : ""}">${isAuto ? (isFutures ? "Futures" : "Auto") : "Alert"}</span>`;
        list.appendChild(row);
      });
      box.appendChild(list);
      const hint = document.createElement("p");
      hint.className = "panel-hint";
      hint.textContent = "Fine-tuning (parameters, frequency, timeframe) stays in the Alert tab.";
      box.appendChild(hint);
    }
    box.appendChild(buildActivationFlow(match || favEntry, autoOpen));
  }

  function bindFavorites() {
    bindFavoriteAutocomplete();
    bindWatchStar();

    el("favorite-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const input = el("favorite-symbol");
      const typed = input.value.trim();
      if (!typed) return;

      let resolved = favSuggest.resolved && favSuggest.resolved.symbol === typed ? favSuggest.resolved : null;
      if (!resolved) {
        await favSuggest.fetch(typed);
        resolved = favSuggest.suggestions.find((s) => s.symbol.toUpperCase() === typed.toUpperCase()) || null;
      }
      if (!resolved) return; // no matching ticker — nothing to add

      const created = await fetch("/api/favorites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: resolved.symbol,
          asset_type: resolved.asset_type,
          exchange: resolved.provider || "mexc",
        }),
      }).then((r) => r.json()).catch(() => null);
      input.value = "";
      favSuggest.resolved = null;
      favSuggest.clear();
      // Chiede subito la strategia sul ticker appena aggiunto — non serve
      // aprire la riga a mano e poi cliccare "+ Attiva".
      if (created?.id) state.autoOpenFavoriteId = created.id;
      loadFavorites();
    });

    bindFavoriteSort();

    document.querySelectorAll("#favorite-filter [data-favorite-filter]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.favoriteFilter = btn.dataset.favoriteFilter;
        document.querySelectorAll("#favorite-filter [data-favorite-filter]").forEach((b) => {
          b.classList.toggle("active", b === btn);
        });
        renderFavorites();
      });
    });
  }

  let suggestTimer = null;

  async function fetchSuggestions(query) {
    try {
      const url = `/api/symbols?query=${encodeURIComponent(query)}`;
      const resp = await fetch(url);
      state.suggestions = resp.ok ? await resp.json() : [];
    } catch (err) {
      state.suggestions = [];
    }
    state.activeSuggestionIndex = -1;
    renderSuggestions();
  }

  function positionSuggestions() {
    placeSuggestionList(el("ticker-suggestions"), el("ticker-input"));
  }

  function renderSuggestions() {
    renderMobileTickerResults();
    const list = el("ticker-suggestions");
    list.innerHTML = "";
    if (!state.suggestions.length) {
      list.classList.add("hidden");
      return;
    }
    positionSuggestions();
    state.suggestions.forEach((item, i) => {
      const li = document.createElement("li");
      li.className = i === state.activeSuggestionIndex ? "active" : "";
      const main = document.createElement("span");
      main.className = "sug-main";
      const sym = document.createElement("span");
      sym.className = "sug-symbol";
      sym.textContent = shortSymbol(item.symbol);
      sym.title = item.symbol;
      const name = document.createElement("span");
      name.className = "sug-name";
      name.textContent = item.name || "";
      main.appendChild(sym);
      main.appendChild(name);
      const exchange = document.createElement("span");
      exchange.className = "sug-exchange sug-exchange-" + item.provider;
      exchange.textContent = item.exchange;
      if (item.asset_type === "crypto") {
        exchange.title = "Prices and levels computed on this exchange — they may differ slightly from other exchanges for the same symbol.";
      }
      li.appendChild(main);
      li.appendChild(exchange);
      // mousedown (not click) fires before the input's blur handler hides the list
      li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        selectSuggestion(item);
      });
      list.appendChild(li);
    });
    list.classList.remove("hidden");
  }

  function hideSuggestions() {
    state.suggestions = [];
    state.activeSuggestionIndex = -1;
    const list = el("ticker-suggestions");
    list.classList.add("hidden");
    list.innerHTML = "";
  }

  function selectSuggestion(item) {
    const input = el("ticker-input");
    input.value = item.symbol;
    // Un simbolo DEX non ci sta nella casella (vedi CSS, text-overflow):
    // il title nativo lo mostra per intero al passaggio del mouse invece
    // di lasciarlo leggibile solo trascinando il cursore da fermo.
    input.title = item.symbol;
    state.assetType = item.asset_type;
    if (item.asset_type === "crypto") state.cryptoExchange = item.provider;
    hideSuggestions();
    closeMobileTickerSearch();
    runAnalysis(item.symbol);
  }

  // Colors are picked deterministically from the symbol so the same ticker
  // always gets the same avatar, without needing a real logo per symbol
  // (which we don't have data for).
  const MTS_AVATAR_COLORS = ["#f0b90b", "#23af91", "#5850ec", "#94a3b8", "#2962ff", "#f23645", "#089981"];
  function mtsAvatarColor(symbol) {
    let hash = 0;
    for (let i = 0; i < symbol.length; i++) hash = (hash * 31 + symbol.charCodeAt(i)) >>> 0;
    return MTS_AVATAR_COLORS[hash % MTS_AVATAR_COLORS.length];
  }

  // Same suggestions the small desktop dropdown uses (state.suggestions,
  // populated by fetchSuggestions) — just a different, full-screen renderer
  // for mobile, with a client-side Tutti/Azioni/Crypto filter on top since
  // asset_type is already on every result.
  function renderMobileTickerResults() {
    const list = el("mts-list");
    list.innerHTML = "";
    const filter = document.querySelector(".mts-tab.active")?.dataset.filter || "all";
    const items = state.suggestions.filter((s) => filter === "all" || s.asset_type === filter);
    if (!items.length) {
      const li = document.createElement("li");
      li.className = "mts-empty";
      li.textContent = state.suggestions.length ? "No results for this filter" : "Type to search a ticker";
      list.appendChild(li);
      return;
    }
    items.forEach((item) => {
      const li = document.createElement("li");
      li.className = "mts-row";

      const avatar = document.createElement("span");
      avatar.className = "mts-avatar";
      avatar.style.background = mtsAvatarColor(item.symbol);
      avatar.textContent = item.symbol.charAt(0);

      const main = document.createElement("span");
      main.className = "mts-main";
      const symRow = document.createElement("span");
      symRow.className = "mts-sym-row";
      const sym = document.createElement("span");
      sym.className = "mts-sym";
      sym.textContent = shortSymbol(item.symbol);
      sym.title = item.symbol;
      const badge = document.createElement("span");
      badge.className = "mts-badge";
      badge.textContent = item.asset_type === "crypto" ? "crypto" : item.asset_type === "dex" ? "dex" : "stocks";
      symRow.appendChild(sym);
      symRow.appendChild(badge);
      const name = document.createElement("span");
      name.className = "mts-name";
      name.textContent = item.name || "";
      main.appendChild(symRow);
      main.appendChild(name);

      const right = document.createElement("span");
      right.className = "mts-right";
      const exch = document.createElement("span");
      exch.className = "mts-exch";
      exch.textContent = item.exchange;
      right.appendChild(exch);

      li.appendChild(avatar);
      li.appendChild(main);
      li.appendChild(right);
      li.addEventListener("click", () => selectSuggestion(item));
      list.appendChild(li);
    });
  }

  function openMobileTickerSearch() {
    if (!window.matchMedia("(max-width: 760px)").matches) return;
    const slot = el("mts-field-slot");
    const field = document.querySelector(".ticker-field");
    if (field.parentElement !== slot) slot.appendChild(field);
    document.querySelectorAll(".mts-tab").forEach((t) => t.classList.toggle("active", t.dataset.filter === "all"));
    renderMobileTickerResults();
    el("mobile-ticker-search").classList.remove("hidden");
    el("ticker-input").focus();
  }

  function closeMobileTickerSearch() {
    const overlay = el("mobile-ticker-search");
    if (overlay.classList.contains("hidden")) return;
    const searchForm = el("search-form");
    const field = document.querySelector(".ticker-field");
    if (field.parentElement !== searchForm) searchForm.appendChild(field);
    overlay.classList.add("hidden");
    el("ticker-input").blur();
  }

  function bindMobileTickerSearch() {
    el("ticker-input").addEventListener("focus", openMobileTickerSearch);
    // The chart-strip symbol sits right next to the timeframe wheel, where
    // the thumb already is — tapping it opens the same search instead of
    // making the user reach back up to the toolbar field.
    el("mobile-chart-symbol").addEventListener("click", openMobileTickerSearch);
    el("mts-close-btn").addEventListener("click", closeMobileTickerSearch);
    document.querySelectorAll(".mts-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".mts-tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        renderMobileTickerResults();
      });
    });
  }

  function bindTickerAutocomplete() {
    const input = el("ticker-input");

    input.addEventListener("input", () => {
      const value = input.value.trim();
      clearTimeout(suggestTimer);
      if (!value) {
        hideSuggestions();
        return;
      }
      suggestTimer = setTimeout(() => fetchSuggestions(value), 300);
    });

    input.addEventListener("keydown", (e) => {
      if (el("ticker-suggestions").classList.contains("hidden")) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        state.activeSuggestionIndex = Math.min(state.activeSuggestionIndex + 1, state.suggestions.length - 1);
        renderSuggestions();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        state.activeSuggestionIndex = Math.max(state.activeSuggestionIndex - 1, 0);
        renderSuggestions();
      } else if (e.key === "Enter") {
        if (state.activeSuggestionIndex >= 0) {
          e.preventDefault();
          selectSuggestion(state.suggestions[state.activeSuggestionIndex]);
        } else {
          hideSuggestions();
        }
      } else if (e.key === "Escape") {
        hideSuggestions();
      }
    });

    input.addEventListener("blur", () => {
      setTimeout(hideSuggestions, 150);
    });
  }

  // ---- Script Pine: upload/parse/apply, editor via CodeMirror ----

  let pineCM = null;

  // CodeMirror (~400 KB) is only for the Pine editor,
  // which few open: it no longer blocks the first paint (overhaul plan,
  // week 3). Until it arrives the textarea itself stands in, with the two
  // methods the rest of the code calls; it is fetched when the browser is
  // idle, or at once when someone touches the editor.
  let pineEditorLoading = null;

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const tag = document.createElement("script");
      tag.src = src;
      tag.onload = resolve;
      tag.onerror = () => reject(new Error(`could not load ${src}`));
      document.head.appendChild(tag);
    });
  }

  function upgradePineEditor() {
    if (pineEditorLoading) return pineEditorLoading;
    const v = document.querySelector('meta[name="lae-asset-version"]')?.content || "";
    const q = v ? `?v=${v}` : "";
    const css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = `/static/codemirror.css${q}`;
    document.head.appendChild(css);
    pineEditorLoading = loadScript(`/static/codemirror.js${q}`)
      .then(() => {
        pineCM = CodeMirror.fromTextArea(el("pine-source"), {
          lineNumbers: true,
          lineWrapping: false,
          styleActiveLine: true,
          indentUnit: 4,
          tabSize: 4,
          viewportMargin: Infinity,
        });
      })
      .catch((err) => console.error("Pine editor stays a plain textarea:", err));
    return pineEditorLoading;
  }

  function initPineEditor() {
    const ta = el("pine-source");
    pineCM = { getValue: () => ta.value, setValue: (text) => { ta.value = text; } };
    ta.addEventListener("focus", upgradePineEditor, { once: true });
    const idle = window.requestIdleCallback || ((fn) => setTimeout(fn, 2500));
    idle(() => upgradePineEditor(), { timeout: 8000 });
  }

  async function loadPineScripts() {
    const resp = await fetch("/api/pinescript");
    state.pineScripts = resp.ok ? await resp.json() : [];
    const select = el("pine-script-select");
    const current = select.value;
    select.innerHTML = '<option value="">— New script —</option>';
    state.pineScripts.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.name;
      select.appendChild(opt);
    });
    if (state.pineScripts.some((s) => s.id === current)) select.value = current;
  }

  function pineSetStatus(elId, text, cls) {
    const node = el(elId);
    node.textContent = text || "";
    node.className = "pine-status" + (cls ? " " + cls : "");
  }

  function renderPineParamsForm(script) {
    state.activePineParams = script.params;
    state.activePineIsStrategy = script.is_strategy_style;
    const container = el("pine-params-fields");
    container.innerHTML = "";
    script.params.forEach((p) => {
      const row = document.createElement("div");
      row.className = "pine-param-row";
      let input;
      if (p.kind === "bool") {
        input = `<input type="checkbox" data-pine-param="${p.var_name}" ${p.default ? "checked" : ""} />`;
      } else if (p.kind === "int" || p.kind === "float") {
        const step = p.kind === "int" ? "1" : "any";
        input = `<input type="number" step="${step}" data-pine-param="${p.var_name}" value="${p.default ?? ""}" />`;
      } else {
        input = `<input type="text" data-pine-param="${p.var_name}" value="${p.default ?? ""}" />`;
      }
      row.innerHTML = `<label>${p.title}</label>${input}`;
      container.appendChild(row);
    });
    el("pine-params-form").classList.remove("hidden");
    el("pine-delete-btn").classList.remove("hidden");
    el("pine-signal-mapping").classList.toggle("hidden", script.is_strategy_style);
  }

  function collectPineParams() {
    const params = {};
    document.querySelectorAll("[data-pine-param]").forEach((input) => {
      const name = input.dataset.pineParam;
      if (input.type === "checkbox") params[name] = input.checked;
      else if (input.type === "number") params[name] = input.value === "" ? null : parseFloat(input.value);
      else params[name] = input.value;
    });
    return params;
  }

  function collectSignalMap() {
    const map = {};
    document.querySelectorAll("#pine-signal-mapping select[data-role]").forEach((select) => {
      if (select.value) map[select.dataset.role] = select.value;
    });
    return map;
  }

  function populateSignalMappingCandidates(candidates) {
    document.querySelectorAll("#pine-signal-mapping select[data-role]").forEach((select) => {
      const current = select.value;
      select.innerHTML = '<option value="">—</option>';
      candidates.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.name;
        opt.textContent = `${c.name} (${c.true_count}x)`;
        select.appendChild(opt);
      });
      if (candidates.some((c) => c.name === current)) select.value = current;
    });
    el("pine-signal-mapping").classList.remove("hidden");
  }

  async function analyzePineSource() {
    const name = el("pine-script-name").value.trim() || "Untitled script";
    const source = pineCM.getValue();
    if (!source.trim()) {
      pineSetStatus("pine-parse-status", "Paste or upload a script before analyzing.", "error");
      return;
    }
    pineSetStatus("pine-parse-status", "Analyzing…", "");
    try {
      const resp = await fetch("/api/pinescript", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, source }),
      });
      const body = await resp.json();
      if (!resp.ok) {
        pineSetStatus("pine-parse-status", typeof body.detail === "string" ? body.detail : "Parse error.", "error");
        return;
      }
      pineSetStatus("pine-parse-status", `Valid script — ${body.params.length} parameters detected.`, "ok");
      await loadPineScripts();
      el("pine-script-select").value = body.id;
      renderPineParamsForm(body);
    } catch (err) {
      pineSetStatus("pine-parse-status", "Network error during analysis.", "error");
    }
  }

  async function selectPineScript(id) {
    if (!id) {
      state.activePineScriptId = null;
      el("pine-params-form").classList.add("hidden");
      el("pine-delete-btn").classList.add("hidden");
      el("pine-script-name").value = "";
      pineCM.setValue("");
      return;
    }
    const resp = await fetch(`/api/pinescript/${id}`);
    if (!resp.ok) return;
    const body = await resp.json();
    state.activePineScriptId = id;
    el("pine-script-name").value = body.name;
    pineCM.setValue(body.source);
    renderPineParamsForm(body);
    pineSetStatus("pine-parse-status", `Script loaded — ${body.params.length} parameters.`, "ok");
  }

  async function applyPineScript() {
    if (!state.activePineScriptId) {
      pineSetStatus("pine-run-status", "Analyze and save a script before applying it.", "error");
      return;
    }
    if (!state.data) {
      pineSetStatus("pine-run-status", "Search a ticker first.", "error");
      return;
    }
    pineSetStatus("pine-run-status", "Running script…", "");
    try {
      const resp = await fetch(`/api/pinescript/${state.activePineScriptId}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: state.data.symbol,
          asset_type: state.assetType,
          exchange: state.cryptoExchange,
          timeframe: state.activeTimeframe,
          params: collectPineParams(),
          signal_map: state.activePineIsStrategy ? null : collectSignalMap(),
        }),
      });
      const body = await resp.json();
      if (!resp.ok) {
        pineSetStatus("pine-run-status", typeof body.detail === "string" ? body.detail : "Execution error.", "error");
        return;
      }
      if (body.needs_mapping) {
        populateSignalMappingCandidates(body.candidates);
        pineSetStatus("pine-run-status", body.warning || "Select the signal mapping.", "error");
        return;
      }
      state.pineActive = true;
      state.pineLastResult = body;
      el("pine-clear-btn").classList.remove("hidden");
      renderPineStrategy(body.strategy);
      renderPineBacktest(body.backtest);
      pineSetStatus("pine-run-status", "Applied to chart.", "ok");
    } catch (err) {
      pineSetStatus("pine-run-status", "Network error during execution.", "error");
    }
  }

  function clearPineOverride() {
    state.pineActive = false;
    state.pineLastResult = null;
    el("pine-clear-btn").classList.add("hidden");
    pineSetStatus("pine-run-status", "", "");
    if (state.data) {
      renderStrategy();
      renderBacktest();
    }
  }

  function renderPineStrategy(strategyState) {
    const badge = el("strategy-position-badge");
    badge.textContent = strategyState.position.toUpperCase();
    badge.className = "position-badge " + strategyState.position;

    const log = el("strategy-alert-log");
    log.innerHTML = "";
    strategyState.signals.slice(-40).forEach((sig) => {
      const li = document.createElement("li");
      li.className = sig.type.includes("long") ? "long-signal" : "short-signal";
      const time = new Date(sig.time * 1000).toLocaleString("en-US");
      li.innerHTML = `[${state.activeTimeframe.toUpperCase()}] ${sig.label} — ${sig.price.toPrecision(6)}<span class="alert-time">${time}</span>`;
      log.appendChild(li);
    });

    _lastStrategySignals = strategyState.signals;
    applyChartMarkers();
    renderChartStats();
    // Gli ordini veri arrivano da un'altra sorgente: si ricaricano a ogni
    // analisi, altrimenti cambiando ticker resterebbero quelli di prima.
    loadExecutedOrders();
  }

  function renderPineBacktest(bt) {
    renderBacktestUI(bt);
  }

  function bindPineUI() {
    el("pine-file-input").addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        pineCM.setValue(reader.result);
        if (!el("pine-script-name").value.trim()) {
          el("pine-script-name").value = file.name.replace(/\.(pine|txt)$/i, "");
        }
      };
      reader.readAsText(file);
    });

    el("pine-analyze-btn").addEventListener("click", analyzePineSource);

    el("pine-script-select").addEventListener("change", (e) => selectPineScript(e.target.value));

    el("pine-delete-btn").addEventListener("click", async () => {
      if (!state.activePineScriptId) return;
      if (!confirm("Delete this script?")) return;
      await fetch(`/api/pinescript/${state.activePineScriptId}`, { method: "DELETE" });
      state.activePineScriptId = null;
      el("pine-params-form").classList.add("hidden");
      el("pine-delete-btn").classList.add("hidden");
      el("pine-script-name").value = "";
      pineCM.setValue("");
      loadPineScripts();
    });

    el("pine-params-form").addEventListener("submit", (e) => {
      e.preventDefault();
      applyPineScript();
    });

    el("pine-clear-btn").addEventListener("click", clearPineOverride);
  }

  // Desktop-only: a rail icon opens/closes its panel as a flyout that
  // reflows the chart (not an overlay) — click the icon again, click
  // anywhere outside it, or open the other rail panel, to close it.
  const RAIL_PANELS = [
    ["rail-levels-btn", "levels-panel"],
    ["rail-issues-btn", "issues-panel"],
    ["rail-script-btn", "script-panel"],
  ];


  // ---- Segnalazioni -------------------------------------------------------
  // Le segnalazioni vivono sul server e le scrivete voi; le risoluzioni
  // arrivano dal repo col deploy e le scrive Claude. Il server le unisce per
  // id, quindi qui basta renderizzare quello che arriva senza sapere da quale
  // dei due lati viene ogni pezzo.

  const ISSUE_STATUS_LABEL = {
    "aperto": "Open",
    "in corso": "In progress",
    "risolto": "Resolved",
    "riaperto": "Reopened",
    "scartato": "Dismissed",
  };

  async function loadIssues() {
    const list = el("issues-list");
    if (!list) return;
    // Uno stato esplicito prima della richiesta: un pannello vuoto altrimenti
    // significa contemporaneamente "sto caricando", "non c'e' niente" e "e'
    // fallito", e chi guarda non puo' distinguerli. E' successo davvero.
    list.innerHTML = '<p class="issues-empty">Loading…</p>';
    try {
      const resp = await fetch("/api/issues", { cache: "no-store" });
      if (!resp.ok) throw new Error(`the server responded ${resp.status}`);
      const body = await resp.json();
      if (!body || !Array.isArray(body.items)) throw new Error("unexpected response from the server");
      renderIssues(body);
    } catch (err) {
      list.innerHTML =
        `<p class="issues-empty">Couldn't load reports: `
        + `${escapeHtml(err && err.message ? err.message : String(err))}`
        + `<br><button type="button" id="issues-retry" class="issues-retry">Retry</button></p>`;
      const retry = el("issues-retry");
      if (retry) retry.addEventListener("click", loadIssues);
    }
  }

  // Cosa e' stato cercato e filtrato: tenuto fuori dal render, altrimenti ogni
  // ricarica (ne parte una a ogni risposta inviata) riporterebbe l'elenco a
  // capo mentre stai leggendo.
  const issuesView = { query: "", filter: "tutte" };
  let issuesLast = null;

  function issueMatches(it, q) {
    if (!q) return true;
    const hay = [it.title, it.detail, it.id, it.priority, it.status,
                 it.resolution ? it.resolution.summary : "",
                 it.resolution ? it.resolution.detail : "",
                 ...(it.replies || []).map((r) => r.text)]
      .join(" ").toLowerCase();
    // Tutte le parole devono comparire, non una qualsiasi: cercare "grafico
    // tema" deve restringere, non allargare.
    return q.toLowerCase().split(/\s+/).filter(Boolean).every((w) => hay.includes(w));
  }

  function renderIssues(body) {
    issuesLast = body;
    const items = body.items || [];
    const counts = body.counts || {};
    const cEl = el("issues-counts");
    if (cEl) {
      cEl.innerHTML = ["aperto", "riaperto", "in corso", "risolto"]
        .filter((k) => counts[k] || k !== "riaperto")
        .map((k) => `<span class="issues-count is-${k.replace(" ", "-")}">`
          + `<b>${counts[k] || 0}</b> ${ISSUE_STATUS_LABEL[k].toLowerCase()}</span>`)
        .join("");
    }

    const list = el("issues-list");
    if (!items.length) {
      list.innerHTML = '<p class="issues-empty">No reports yet. Write the first one above.</p>';
      return;
    }
    // Aperte per prime: una bacheca che apre sulle cose gia' chiuse nasconde
    // proprio quelle su cui bisogna agire.
    // Le riaperte per prime: sono quelle su cui una correzione non ha risolto,
    // ed e' l'informazione piu' urgente della bacheca.
    const order = { "riaperto": 0, "aperto": 1, "in corso": 2, "risolto": 3, "scartato": 4 };
    const prio = { alta: 0, media: 1, bassa: 2 };
    const wanted = issuesView.filter;
    const filtered = items.filter((it) => {
      if (wanted === "da-fare" && it.status === "risolto") return false;
      if (wanted !== "tutte" && wanted !== "da-fare" && it.status !== wanted) return false;
      return issueMatches(it, issuesView.query);
    });

    const found = el("issues-found");
    if (found) {
      const filtering = issuesView.query || wanted !== "tutte";
      found.textContent = filtering
        ? `${filtered.length} of ${items.length}`
        : "";
      found.classList.toggle("hidden", !filtering);
    }
    if (!filtered.length) {
      list.innerHTML = '<p class="issues-empty">No matching reports.</p>';
      return;
    }

    const sorted = [...filtered].sort((a, b) =>
      (order[a.status] ?? 9) - (order[b.status] ?? 9)
      || (prio[a.priority] ?? 9) - (prio[b.priority] ?? 9));

    // Stessa card di sempre (stesso <details class="issue-card">, stesso
    // form di risposta) — solo estratta in una funzione cosi' la si puo'
    // smistare in tre colonne invece che in un'unica lista piatta.
    const cardHtml = (it) => {
      const r = it.resolution;
      const when = it.created_at
        ? new Date(it.created_at * 1000).toLocaleDateString("en-US")
        : "";
      // Richiudibile: con decine di voci, tenerle tutte aperte di default
      // (anche solo quelle "da fare") e' un muro di testo — ogni colonna
      // diventa una parete di risoluzioni e form invece di un elenco
      // leggibile. Restano compatte finche' non le si apre a mano, tranne
      // quelle che stai cercando.
      const openByDefault = !!issuesView.query;
      return `<details class="issue-card is-${(it.status || "aperto").replace(" ", "-")}"${openByDefault ? " open" : ""}>
        <summary class="issue-head">
          <span class="issue-status">${ISSUE_STATUS_LABEL[it.status] || it.status}</span>
          <span class="issue-prio p-${it.priority}">${it.priority}</span>
          <span class="issue-title">${escapeHtml(it.title)}</span>
        </summary>
        ${it.detail ? `<p class="issue-detail">${escapeHtml(it.detail)}</p>` : ""}
        <p class="issue-meta">${escapeHtml(it.author || "")}${when ? " · " + when : ""} · <code>${escapeHtml(it.id)}</code></p>
        ${r ? `<div class="issue-res">
          <div class="issue-res-head">Claude</div>
          <p class="issue-res-summary">${escapeHtml(r.summary || "")}</p>
          ${r.detail ? `<pre class="issue-res-detail">${escapeHtml(r.detail)}</pre>` : ""}
          ${r.next ? `<p class="issue-res-next"><b>Next step:</b> ${escapeHtml(r.next)}</p>` : ""}
          ${r.commit ? `<p class="issue-res-commit">commit <code>${escapeHtml(r.commit)}</code></p>` : ""}
        </div>` : ""}
        ${(it.replies || []).map((rp) => `
          <div class="issue-reply ${rp.side === "claude" ? "from-claude" : ""}">
            <span class="ir-who">${rp.side === "claude" ? "Claude" : escapeHtml(rp.author || "you")}</span>
            ${rp.reopen ? '<span class="ir-reopen">reopened</span>' : ""}
            <p>${escapeHtml(rp.text)}</p>
          </div>`).join("")}
        <form class="issue-reply-form" data-issue="${escapeHtml(it.id)}">
          <textarea rows="2" placeholder="Reply — if the problem still shows up, say so here" required></textarea>
          <div class="irf-row">
            <label><input type="checkbox" name="reopen" /> Not resolved, reopen</label>
            <button type="submit">Send</button>
          </div>
          <p class="irf-status hidden"></p>
        </form>
        <div class="issue-manual-row" data-issue="${escapeHtml(it.id)}">
          ${it.status === "risolto" || it.status === "scartato"
            ? `<button type="button" class="issue-manual-btn is-reopen" data-status="aperto">Reopen</button>`
            : `<button type="button" class="issue-manual-btn is-close" data-status="risolto">Close manually</button>`}
          <p class="issue-manual-status hidden"></p>
        </div>
      </details>`;
    };

    // Board a tre colonne: stessa lista ordinata, smistata per stato invece
    // che mostrata in fila. "riaperto" resta con "aperto" (e' ancora da
    // fare), "scartato" con "risolto" (e' comunque chiuso).
    const columns = [
      { key: "aperto", label: "Open", items: [] },
      { key: "in-corso", label: "In progress", items: [] },
      { key: "risolto", label: "Resolved", items: [] },
    ];
    const colFor = (status) => {
      if (status === "in corso") return 1;
      if (status === "risolto" || status === "scartato") return 2;
      return 0; // aperto, riaperto
    };
    sorted.forEach((it) => columns[colFor(it.status)].items.push(it));

    list.innerHTML = `<div class="issues-board">${columns.map((col) => `
      <div class="board-col" data-col="${col.key}">
        <div class="board-col-hd">
          <span class="board-col-dot is-${col.key}"></span>${col.label}
          <span class="board-count">${col.items.length}</span>
        </div>
        <div class="board-col-body">
          ${col.items.length ? col.items.map(cardHtml).join("") : '<p class="issues-empty board-col-empty">Nothing here.</p>'}
        </div>
      </div>`).join("")}</div>`;

    list.querySelectorAll(".issue-reply-form").forEach((form) => {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const area = form.querySelector("textarea");
        const status = form.querySelector(".irf-status");
        const reopen = form.querySelector('[name="reopen"]').checked;
        const text = area.value.trim();
        if (!text) return;
        status.classList.remove("hidden");
        status.textContent = "Sending…";
        try {
          const resp = await fetch(`/api/issues/${form.dataset.issue}/replies`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, reopen }),
          });
          if (!resp.ok) {
            const body = await resp.json().catch(() => ({}));
            status.textContent = body.detail === "Sign-in required"
              ? "Log in to reply."
              : (body.detail || "Not sent.");
            return;
          }
          area.value = "";
          loadIssues();
        } catch {
          status.textContent = "Network unreachable.";
        }
      });
    });

    list.querySelectorAll(".issue-manual-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const row = btn.closest(".issue-manual-row");
        const statusEl = row.querySelector(".issue-manual-status");
        const issueId = row.dataset.issue;
        const newStatus = btn.dataset.status;
        btn.disabled = true;
        statusEl.classList.remove("hidden");
        statusEl.textContent = newStatus === "risolto" ? "Closing…" : "Reopening…";
        try {
          const resp = await fetch(`/api/issues/${issueId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus }),
          });
          if (!resp.ok) {
            const body = await resp.json().catch(() => ({}));
            statusEl.textContent = body.detail === "Sign-in required"
              ? "Log in to do this."
              : (body.detail || "Failed.");
            btn.disabled = false;
            return;
          }
          loadIssues();
        } catch {
          statusEl.textContent = "Network unreachable.";
          btn.disabled = false;
        }
      });
    });
  }


  // Una pagina vecchia non se ne accorge da sola. Il `no-cache` sull'HTML vale
  // dal deploy in poi, ma chi l'aveva gia' in cache da prima puo' restarci per
  // ore: e' successo davvero — grafico nero dopo che la correzione era in
  // produzione da un pezzo, perche' il browser continuava a chiedere il vecchio
  // app.js. Qui la pagina chiede al server quale versione sta servendo e, se
  // non e' la sua, si ricarica una volta sola.
  // Quando il server e' partito l'ultima volta, scritto nel piede della
  // sidebar: la stessa domanda che ha creato confusione in chat ("ma e'
  // stato distribuito davvero?") qui si legge a schermo invece di dedurla
  // da un messaggio Telegram che puo' anche non arrivare (seed-0051).
  function renderDeployInfo(deployedAtEpoch) {
    const el2 = el("sidenav-deploy-info");
    if (!el2 || !deployedAtEpoch) return;
    const d = new Date(deployedAtEpoch * 1000);
    const stamp = d.toLocaleString("en-US", {
      day: "2-digit", month: "2-digit", year: "2-digit",
      hour: "2-digit", minute: "2-digit",
    });
    el2.textContent = `Updated ${stamp}`;
  }

  async function checkAssetVersion() {
    const meta = document.querySelector('meta[name="lae-asset-version"]');
    const mine = meta ? meta.getAttribute("content") : "";
    if (!mine) return;
    try {
      const resp = await fetch("/api/version", { cache: "no-store" });
      if (!resp.ok) return;
      const { asset_version: live, deployed_at } = await resp.json();
      renderDeployInfo(deployed_at);
      if (!live || live === mine) return;
      // Una sola ricarica per versione: se dopo il giro la pagina fosse ancora
      // vecchia — cache intermedia, proxy — ricaricare all'infinito sarebbe
      // peggio del difetto che sto correggendo.
      const key = `lae.reloaded.${live}`;
      if (sessionStorage.getItem(key)) return;
      sessionStorage.setItem(key, "1");
      location.reload();
    } catch { /* offline: la pagina vecchia e' comunque meglio di niente */ }
  }

  function bindTheme() {
    const btn = el("theme-toggle-btn");
    if (btn) {
      btn.addEventListener("click", () => {
        const now = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
        applyTheme(now);
        savePreferences();   // cosi' la scelta ti segue sull'altro computer
      });
    }
    // Se non e' mai stata fatta una scelta esplicita, il tema continua a
    // seguire il sistema: chi passa a scuro la sera se lo ritrova.
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onSystemChange = (e) => {
      let saved = null;
      try { saved = localStorage.getItem(THEME_KEY); } catch { /* ignora */ }
      if (!saved) applyTheme(e.matches ? "dark" : "light", { persist: false });
    };
    if (mq.addEventListener) mq.addEventListener("change", onSystemChange);
    else if (mq.addListener) mq.addListener(onSystemChange);
  }

  function bindIssues() {
    const search = el("issues-search");
    if (search) {
      // Si filtra su quello che c'e' gia' in memoria: la bacheca sta in una
      // risposta sola, quindi cercare non deve fare un giro sul server.
      search.addEventListener("input", () => {
        issuesView.query = search.value.trim();
        if (issuesLast) renderIssues(issuesLast);
      });
    }
    const filter = el("issues-filter");
    if (filter) {
      filter.addEventListener("change", () => {
        issuesView.filter = filter.value;
        if (issuesLast) renderIssues(issuesLast);
      });
    }

    const form = el("issue-form");
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const status = el("issue-form-status");
      const title = el("issue-title").value.trim();
      if (!title) return;
      status.textContent = "Sending…";
      try {
        const resp = await fetch("/api/issues", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title,
            detail: el("issue-detail").value,
            priority: el("issue-priority").value,
          }),
        });
        if (resp.status === 401) {
          status.textContent = "Log in to report (Log in button at the top).";
          return;
        }
        if (!resp.ok) {
          const b = await resp.json().catch(() => ({}));
          throw new Error(typeof b.detail === "string" ? b.detail : `Error ${resp.status}`);
        }
        el("issue-title").value = "";
        el("issue-detail").value = "";
        status.textContent = "Report submitted.";
        setTimeout(() => { status.textContent = ""; }, 3000);
        loadIssues();
      } catch (err) {
        status.textContent = err.message;
      }
    });

    const btn = el("rail-issues-btn");
    if (btn) btn.addEventListener("click", () => loadIssues());

    // The rail is hidden below 760px, so on a phone the tab is unreachable
    // from there: the bottom bar has five slots and they are all taken, which
    // is what "Altro" exists for.
    const altroItem = el("altro-issues-item");
    if (altroItem) altroItem.addEventListener("click", () => {
      showMobileScreen("issues");
      loadIssues();
    });

    // Anche all'avvio: se una via d'accesso non chiama loadIssues, il pannello
    // e' comunque gia' popolato quando lo si apre, invece di restare vuoto.
    loadIssues();

    // A count on the entry, so an open report is visible without opening it.
    fetch("/api/issues")
      .then((r) => (r.ok ? r.json() : null))
      .then((b) => {
        if (!b) return;
        const n = (b.counts || {})["aperto"] || 0;
        const badge = el("altro-issues-badge");
        if (badge && n > 0) {
          badge.textContent = n;
          badge.classList.remove("hidden");
        }
      })
      .catch(() => {});
  }

  function bindRail() {
    RAIL_PANELS.forEach(([btnId, panelId]) => {
      const btn = el(btnId);
      const panel = el(panelId);
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const opening = !panel.classList.contains("open");
        RAIL_PANELS.forEach(([otherBtnId, otherPanelId]) => {
          el(otherPanelId).classList.remove("open");
          el(otherBtnId).classList.remove("active");
        });
        panel.classList.toggle("open", opening);
        btn.classList.toggle("active", opening);
        resizeAllCharts();
      });
    });
    document.addEventListener("click", (e) => {
      // La sidebar e' il modo legittimo di aprire questi pannelli: senza
      // questa riga lo stesso click che apre la Bacheca la richiude subito
      // dopo, perche' in fase di risalita risulta un "click fuori".
      if (e.target.closest && e.target.closest(".sidenav")) return;
      RAIL_PANELS.forEach(([btnId, panelId]) => {
        const btn = el(btnId);
        const panel = el(panelId);
        if (!panel.classList.contains("open")) return;
        if (panel.contains(e.target) || btn.contains(e.target)) return;
        panel.classList.remove("open");
        btn.classList.remove("active");
        resizeAllCharts();
      });
    });

    // Desktop: il tasto ✕ Chiudi dentro ogni pannello laterale chiude
    // il pannello e riporta il focus sull'item Analizza nella sidenav.
    RAIL_PANELS.forEach(([btnId, panelId]) => {
      const panel = el(panelId);
      const btn = el(btnId);
      const closeBtn = panel?.querySelector(".drawer-close-btn");
      if (!closeBtn) return;
      closeBtn.addEventListener("click", () => {
        if (window.matchMedia("(max-width: 760px)").matches) return;
        panel.classList.remove("open");
        btn.classList.remove("active");
        const analizzaItem = document.querySelector(".sidenav-item[data-area='analizza']");
        document.querySelectorAll(".sidenav-item").forEach((b) => b.classList.toggle("active", b === analizzaItem));
        resizeAllCharts();
      });
    });

    // Desktop: ✕ Chiudi nel pannello destro mentre si e' nel Lab → torna
    // ad Analizza (la tab di default che mostra watchlist + grafico affiancati).
    const rightPanelClose = document.querySelector(".right-panel .drawer-close-btn");
    if (rightPanelClose) {
      rightPanelClose.addEventListener("click", () => {
        if (window.matchMedia("(max-width: 760px)").matches) return;
        const cockpit = document.querySelector(".cockpit");
        if (cockpit && cockpit.dataset.area === "lab") {
          setArea("analizza");
        }
      });
    }
  }

  function bindTabs() {
    document.querySelectorAll(".tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        const name = tab.dataset.tab;
        document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
        document.querySelectorAll(".tab-content").forEach((c) => {
          c.classList.toggle("active", c.dataset.tabContent === name);
        });
        resizeAllCharts();
      });
    });
  }

  // Mobile app-shell: five real full-screen destinations reached from the
  // bottom nav — Grafico, Livelli, Backtest, Alert, Altro — not overlay
  // sheets with a backdrop. Each tap shows exactly one screen and hides the
  // rest; there is no "tap again to close" ambiguity like the old drawer
  // model had. Backtest and Alert reuse the same underlying .right-panel
  // (and its internal .tabs) that desktop already has. Script Pine and Saldi
  // are reached through the Altro menu, not the bottom nav itself, so they
  // still map onto the same mechanism without a 6th/7th tab.
  const RIGHT_PANEL_TITLES = { backtest: "Backtest", alert: "Alert", strategie: "Strategies", trading: "Trading", saldi: "Balances", analisi: "Analysis", watchlist: "Watchlist" };

  let mobileScreen = "chart";
  // The two Lab <-> chart syncs live inside the boot function, out of reach
  // from here: on the phone, opening the Lab threw "syncLabFromChart is not
  // defined" and the screen never opened (13/10: "la sezione backtest non
  // funziona da app, solo da browser"). The boot fills these in.
  let labSync = { fromChart: () => {}, toChart: () => {} };

  function showMobileScreen(target) {
    if (!window.matchMedia("(max-width: 760px)").matches) return;

    el("levels-panel").classList.remove("mobile-open");
    el("script-panel").classList.remove("mobile-open");
    el("altro-panel").classList.remove("mobile-open");
    el("issues-panel").classList.remove("mobile-open");
    document.querySelector(".right-panel").classList.remove("mobile-open");
    el("draw-rail").classList.remove("mobile-tools-open");

    // On the phone the Lab is the "backtest" screen: same two-way sync as the
    // desktop sidebar (segnalazione 87cc755b).
    const prevScreen = mobileScreen;
    mobileScreen = target;
    if (target === "backtest" && prevScreen !== "backtest") labSync.fromChart();
    else if (prevScreen === "backtest" && (target === "chart" || target === "levels")) labSync.toChart();

    const NAV_TARGET_FOR = { script: "altro", saldi: "altro", analisi: "altro", watchlist: "altro", backtest: "altro", issues: "altro", strategie: "altro", trading: "altro" };
    const navTarget = NAV_TARGET_FOR[target] || target;
    document.querySelectorAll(".mobile-nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.mobileTarget === navTarget));

    // Drawing tools only make sense over the chart itself — everywhere else
    // there's nothing to draw on.
    el("mobile-strip-tools").classList.toggle("hidden", target !== "chart" || !state.data);

    if (target === "chart") {
      resizeAllCharts();
      return;
    }
    if (target === "levels") {
      el("levels-panel").classList.add("mobile-open");
    } else if (target === "script") {
      el("script-panel").classList.add("mobile-open");
    } else if (target === "altro") {
      el("altro-panel").classList.add("mobile-open");
    } else if (target === "issues") {
      el("issues-panel").classList.add("mobile-open");
      loadIssues();
    } else {
      // backtest | alert | saldi | analisi — shared right-panel, pick the internal tab
      const panel = document.querySelector(".right-panel");
      panel.classList.add("mobile-open");
      panel.querySelector(".drawer-header span").textContent = RIGHT_PANEL_TITLES[target] || "Panel";
      document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === target));
      document.querySelectorAll(".tab-content").forEach((c) => {
        c.classList.toggle("active", c.dataset.tabContent === target);
      });
    }
    resizeAllCharts();
  }

  // Used by links that open a specific panel outside the bottom nav (e.g.
  // "Script Pine personalizzato" inside Alert) — works the same on desktop
  // (flyout via the matching rail button) and mobile (full-screen tab).
  function openPanel(panelId) {
    if (window.matchMedia("(max-width: 760px)").matches) {
      showMobileScreen(
        panelId === "script-panel" ? "script"
        : panelId === "issues-panel" ? "issues"
        : "levels");
      return;
    }
    RAIL_PANELS.forEach(([btnId, pid]) => {
      el(pid).classList.toggle("open", pid === panelId);
      el(btnId).classList.toggle("active", pid === panelId);
    });
    resizeAllCharts();
  }

  function bindMobileNav() {
    document.querySelectorAll(".mobile-nav-btn").forEach((btn) => {
      btn.addEventListener("click", () => showMobileScreen(btn.dataset.mobileTarget));
    });
    // Strategy pill in the chart strip opens the Livelli panel (where the
    // strategy selector lives) so the user can change it in one tap.
    el("mobile-strategy-pill").addEventListener("click", () => showMobileScreen("levels"));
    document.querySelectorAll("[data-close-drawer]").forEach((btn) => {
      btn.addEventListener("click", () => showMobileScreen("chart"));
    });
    el("open-script-from-altro").addEventListener("click", () => openPanel("script-panel"));
    el("open-indicators-from-altro").addEventListener("click", () => {
      showMobileScreen("chart"); // chiude il menu Altro, il modale sta sopra a tutto
      openIndicatorLibraryModal();
    });
    el("altro-saldi-item").addEventListener("click", () => showMobileScreen("saldi"));
    el("altro-analisi-item").addEventListener("click", () => showMobileScreen("analisi"));
    el("altro-watchlist-item").addEventListener("click", () => showMobileScreen("watchlist"));
    el("altro-backtest-item").addEventListener("click", () => showMobileScreen("backtest"));
    el("altro-strategie-item").addEventListener("click", () => showMobileScreen("strategie"));
    el("altro-trading-item").addEventListener("click", () => showMobileScreen("trading"));
  }

  // ── Libreria indicatori (pandas-ta, 151 voci) ─────────────────────────────
  // Modale centrale (non un cassetto laterale): l'utente — "vorrei che si
  // aprisse in verticale e non che si aprisse una finestra laterale" —
  // colonna categorie a sinistra (con Preferiti), ricerca e risultati a
  // destra. Elenco completo con la spiegazione di ciascuno, perche' "non
  // conosco i nomi cosi non so cosa cercare".
  let indicatorLibraryFilter = null; // null = tutti; "__favorites"; oppure un id di categoria

  // A failed load is not remembered: an empty library stayed empty until
  // a reload (a server restart during a deploy was enough). Next open retries.
  async function ensureIndicatorCatalog() {
    if (state.indicatorCatalog && state.indicatorCatalog.length) return state.indicatorCatalog;
    try {
      const resp = await fetch("/api/indicators/catalog", { signal: AbortSignal.timeout(15000) });
      const list = resp.ok ? await resp.json() : [];
      state.indicatorCatalog = Array.isArray(list) && list.length ? list : null;
    } catch {
      state.indicatorCatalog = null;
    }
    return state.indicatorCatalog || [];
  }

  function toggleFavoriteIndicator(id) {
    if (state.favoriteIndicatorIds.has(id)) state.favoriteIndicatorIds.delete(id);
    else state.favoriteIndicatorIds.add(id);
    localStorage.setItem("favoriteIndicatorIds", JSON.stringify([...state.favoriteIndicatorIds]));
    renderIndicatorModalNav();
    renderIndicatorLibraryList(el("indicator-library-search")?.value || "");
  }

  function renderIndicatorModalNav() {
    const nav = el("indicator-modal-nav");
    if (!nav) return;
    const catalog = state.indicatorCatalog || [];
    const byCategory = new Map(); // category id -> {label, count}
    catalog.forEach((s) => {
      if (!byCategory.has(s.category)) byCategory.set(s.category, { label: s.category_label, count: 0 });
      byCategory.get(s.category).count += 1;
    });
    const favCount = state.favoriteIndicatorIds.size;
    const btn = (filterVal, label, count, extraClass) =>
      `<button type="button" data-filter="${filterVal}" class="${filterVal === indicatorLibraryFilter ? "active" : ""} ${extraClass || ""}">` +
      `<span>${escapeHtml(label)}</span><span class="icl-count">${count}</span></button>`;
    const parts = [
      indicatorLibraryFilter === null
        ? `<button type="button" data-filter="" class="active"><span>All</span><span class="icl-count">${catalog.length}</span></button>`
        : `<button type="button" data-filter=""><span>All</span><span class="icl-count">${catalog.length}</span></button>`,
      btn("__favorites", "★ Favorites", favCount),
      `<div class="indicator-modal-nav-label">Categories</div>`,
    ];
    [...byCategory.entries()]
      .sort((a, b) => a[1].label.localeCompare(b[1].label))
      .forEach(([catId, info]) => parts.push(btn(catId, info.label, info.count)));
    nav.innerHTML = parts.join("");
    nav.querySelectorAll("[data-filter]").forEach((b) => {
      b.addEventListener("click", () => {
        indicatorLibraryFilter = b.dataset.filter || null;
        renderIndicatorModalNav();
        renderIndicatorLibraryList(el("indicator-library-search")?.value || "");
      });
    });
  }

  function renderIndicatorLibraryList(filterText) {
    const box = el("indicator-library-list");
    if (!box) return;
    const catalog = state.indicatorCatalog || [];
    const q = (filterText || "").trim().toLowerCase();
    const activeIds = new Set(state.customIndicators.map((c) => c.id));

    let base = catalog;
    if (indicatorLibraryFilter === "__favorites") {
      base = catalog.filter((s) => state.favoriteIndicatorIds.has(s.id));
    } else if (indicatorLibraryFilter) {
      base = catalog.filter((s) => s.category === indicatorLibraryFilter);
    }
    const filtered = q
      ? base.filter((s) =>
          s.label.toLowerCase().includes(q) || s.id.includes(q) ||
          s.category_label.toLowerCase().includes(q) || (s.description || "").toLowerCase().includes(q))
      : base;

    if (!filtered.length) {
      const msg = indicatorLibraryFilter === "__favorites"
        ? "No favorites yet — click the star on an indicator to add it here."
        : "No indicator found — try another term.";
      box.innerHTML = `<div class="icl-empty">${msg}</div>`;
      return;
    }

    // Un filtro di categoria (o i preferiti) mostra gia' un unico gruppo:
    // l'intestazione di categoria ha senso solo sfogliando "Tutti".
    const groupByCategory = indicatorLibraryFilter === null;
    const byCategory = new Map();
    filtered.forEach((s) => {
      const key = groupByCategory ? s.category_label : "__flat";
      if (!byCategory.has(key)) byCategory.set(key, []);
      byCategory.get(key).push(s);
    });

    const rowHtml = (s) => {
      const isActive = activeIds.has(s.id);
      const isFav = state.favoriteIndicatorIds.has(s.id);
      return `<div class="icl-item${isActive ? " active" : ""}" data-indicator-id="${escapeHtml(s.id)}">` +
        `<button type="button" class="icl-star${isFav ? " on" : ""}" data-fav-indicator="${escapeHtml(s.id)}" title="${isFav ? "Remove from favorites" : "Add to favorites"}">${isFav ? "★" : "☆"}</button>` +
        `<div class="icl-item-main"><div class="icl-item-head"><span class="icl-item-label">${escapeHtml(s.label)}</span>` +
        `<span class="icl-kind">${s.kind === "overlay" ? "on price" : "own pane"}</span></div>` +
        `<p class="icl-desc">${escapeHtml(s.description || "")}</p></div></div>`;
    };
    const parts = [];
    byCategory.forEach((items, key) => {
      if (groupByCategory) parts.push(`<div class="icl-group-label">${escapeHtml(key)}</div>`);
      items.forEach((s) => parts.push(rowHtml(s)));
    });
    box.innerHTML = parts.join("");
    box.querySelectorAll("[data-fav-indicator]").forEach((star) => {
      star.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleFavoriteIndicator(star.dataset.favIndicator);
      });
    });
    box.querySelectorAll("[data-indicator-id]").forEach((row) => {
      row.addEventListener("click", () => toggleCustomIndicator(row.dataset.indicatorId));
    });
  }

  function renderActiveIndicatorChips() {
    const box = el("active-indicators-chips");
    if (!box) return;
    if (!state.customIndicators.length) {
      box.innerHTML = "";
      return;
    }
    box.innerHTML = state.customIndicators
      .map((c) => `<span class="indicator-chip">${escapeHtml(c.label)}` +
        `<button type="button" data-remove-indicator="${escapeHtml(c.id)}" title="Remove">✕</button></span>`)
      .join("");
    box.querySelectorAll("[data-remove-indicator]").forEach((btn) => {
      btn.addEventListener("click", () => toggleCustomIndicator(btn.dataset.removeIndicator));
    });
  }

  // Legenda fissa in alto a sinistra sul grafico: senza, un indicatore
  // aggiunto dalla libreria finisce come una linea o un riquadro anonimo —
  // Richiesta: "se li attivo finiscono nel grafico ma non so cosa sono e cosa
  // ho attivo". Click sul nome apre la spiegazione (stessa riga scritta nel
  // catalogo), click sulla x lo rimuove — stessa lista di sempre,
  // semplicemente resa visibile anche sopra il grafico, non solo in Livelli.
  function renderChartIndicatorLegend() {
    const box = el("chart-indicator-legend");
    if (!box) return;
    if (!state.customIndicators.length) {
      box.innerHTML = "";
      return;
    }
    box.innerHTML = state.customIndicators
      .map((c, i) => {
        const color = CUSTOM_IND_COLORS[i % CUSTOM_IND_COLORS.length];
        return `<span class="chart-legend-chip">` +
          `<span class="chart-legend-dot" style="background:${color}"></span>` +
          `<span class="chart-legend-name" data-info-indicator="${escapeHtml(c.id)}">${escapeHtml(c.label)}</span>` +
          `<button type="button" data-remove-indicator="${escapeHtml(c.id)}" title="Remove">✕</button></span>`;
      })
      .join("");
    box.querySelectorAll("[data-remove-indicator]").forEach((btn) => {
      btn.addEventListener("click", () => toggleCustomIndicator(btn.dataset.removeIndicator));
    });
    box.querySelectorAll("[data-info-indicator]").forEach((nameEl) => {
      nameEl.addEventListener("click", (e) => {
        showIndicatorInfoPopup(nameEl.dataset.infoIndicator, e.clientX, e.clientY);
      });
    });
  }

  // Popup con la spiegazione di un indicatore attivo — riusa lo stesso
  // elemento e la stessa logica di chiusura di showMarkerPopup (click
  // fuori lo chiude, gia' agganciato da bindMarkerClickPopup), con un
  // contenuto diverso: qui non c'e' un punteggio 1-10, solo nome e
  // descrizione dalla libreria.
  function showIndicatorInfoPopup(indId, px, py) {
    const popup = el("marker-popup");
    const spec = (state.indicatorCatalog || []).find((s) => s.id === indId);
    if (!popup || !spec) return;
    popup.innerHTML = `
      <div class="marker-popup-header">
        <span class="marker-popup-label">${escapeHtml(spec.label)}</span>
        <button class="marker-popup-close" onclick="document.getElementById('marker-popup').classList.add('hidden')" aria-label="Close">×</button>
      </div>
      <div class="marker-popup-desc">${escapeHtml(spec.description || "")}</div>
      <div class="marker-popup-score">
        <span class="marker-popup-score-label">${spec.kind === "overlay" ? "ON PRICE" : "OWN PANE"}</span>
      </div>`;
    const vw = window.innerWidth, vh = window.innerHeight;
    const W = 280, H = 120;
    let left = px + 10, top = py + 10;
    if (left + W > vw - 8) left = px - W - 8;
    if (top + H > vh - 8) top = py - H - 8;
    popup.style.left = `${Math.max(8, left)}px`;
    popup.style.top  = `${Math.max(8, top)}px`;
    popup.classList.remove("hidden");
  }

  function toggleCustomIndicator(id) {
    const catalog = state.indicatorCatalog || [];
    const idx = state.customIndicators.findIndex((c) => c.id === id);
    if (idx >= 0) {
      state.customIndicators.splice(idx, 1);
    } else {
      const spec = catalog.find((s) => s.id === id);
      if (!spec) return;
      state.customIndicators.push({ id: spec.id, label: spec.label, kind: spec.kind });
    }
    localStorage.setItem("customIndicators", JSON.stringify(state.customIndicators));
    // Rimandato al prossimo tick: sostituire subito l'HTML della lista
    // stacca dal DOM l'elemento appena cliccato, e il listener globale che
    // chiude i pannelli alla pressione "fuori" (bindUI, RAIL_PANELS) vede
    // l'evento risalire da un nodo ormai scollegato — panel.contains(e.target)
    // torna false e richiude il pannello nello stesso click che doveva solo
    // aggiungere l'indicatore.
    setTimeout(() => {
      const search = el("indicator-library-search");
      renderIndicatorLibraryList(search ? search.value : "");
      renderActiveIndicatorChips();
      renderChartIndicatorLegend();
    }, 0);
    refreshCustomIndicators();
  }

  // Modale indipendente dal sistema di pannelli laterali (RAIL_PANELS):
  // niente cassetto, niente area del cockpit da cambiare, funziona identico
  // su desktop e mobile. Tre punti d'ingresso (toolbar, sidebar, Livelli)
  // chiamano tutti la stessa apertura diretta — senza il giro di click
  // sintetico che serviva quando era un cassetto (e senza il bug di
  // richiusura che quel giro portava con se').
  async function openIndicatorLibraryModal() {
    if (!(state.indicatorCatalog && state.indicatorCatalog.length)) {
      el("indicator-library-modal")?.classList.remove("hidden");
      const box = el("indicator-library-list");
      if (box) box.innerHTML = `<div class="icl-empty">Loading indicators…</div>`;
      await ensureIndicatorCatalog();
      if (!(state.indicatorCatalog && state.indicatorCatalog.length) && box) {
        box.innerHTML = `<div class="icl-empty">The list did not load. Close and open again to retry.</div>`;
        return;
      }
    }
    renderIndicatorModalNav();
    renderIndicatorLibraryList(el("indicator-library-search")?.value || "");
    el("indicator-library-modal")?.classList.remove("hidden");
    el("indicator-library-search")?.focus();
  }

  function closeIndicatorLibraryModal() {
    el("indicator-library-modal")?.classList.add("hidden");
  }

  function bindIndicatorCatalog() {
    const search = el("indicator-library-search");
    const modal = el("indicator-library-modal");
    if (!search || !modal) return;
    search.addEventListener("input", () => renderIndicatorLibraryList(search.value));

    el("indicator-modal-close")?.addEventListener("click", closeIndicatorLibraryModal);
    // Click sullo sfondo scuro chiude; click dentro il riquadro no.
    modal.addEventListener("click", (e) => { if (e.target === modal) closeIndicatorLibraryModal(); });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !modal.classList.contains("hidden")) closeIndicatorLibraryModal();
    });

    el("open-indicator-library-btn")?.addEventListener("click", () => openIndicatorLibraryModal());
    el("toolbar-indicators-btn")?.addEventListener("click", () => openIndicatorLibraryModal());

    renderActiveIndicatorChips();
    renderChartIndicatorLegend();
  }

  function dynamicSubChartOptions() {
    return {
      layout: { background: { color: COLORS.paperBg }, textColor: COLORS.inkDim, fontFamily: "'JetBrains Mono', 'IBM Plex Mono', monospace" },
      grid: { vertLines: { color: COLORS.gridMinor }, horzLines: { color: COLORS.gridMinor } },
      rightPriceScale: { borderColor: COLORS.gridMajor, minimumWidth: 72 },
      timeScale: { borderColor: COLORS.gridMajor, timeVisible: true, secondsVisible: false },
    };
  }

  // Calcola e disegna gli indicatori scelti dalla libreria. Chiamata alla
  // fine di ogni render(): ripulisce le linee/riquadri del giro precedente e
  // li ricrea da zero, cosi' cambiare ticker o timeframe non lascia residui
  // di un simbolo diverso appesi al grafico.
  //
  // Due click ravvicinati sulla libreria (o un render() che scatta mentre
  // la chiamata precedente e' ancora in volo sulla rete) avviano due
  // esecuzioni sovrapposte: senza guardia, quella piu' vecchia riprende
  // dopo il proprio await e aggiunge un secondo riquadro per lo stesso
  // indicatore, gia' creato nel frattempo da quella piu' recente. Un
  // numero di sequenza fa desistere ogni esecuzione superata non appena
  // se ne accorge, subito dopo il primo punto di attesa.
  let indicatorsRefreshSeq = 0;
  async function refreshCustomIndicators() {
    const mySeq = ++indicatorsRefreshSeq;
    customOverlaySeriesList.forEach(({ chart, series }) => {
      try { chart.removeSeries(series); } catch { /* gia' rimossa */ }
    });
    customOverlaySeriesList = [];
    Object.values(customOscCharts).forEach(({ container, chart }) => {
      try { chart.remove(); } catch { /* gia' rimosso */ }
      container.remove();
    });
    customOscCharts = {};

    if (!state.customIndicators.length || !state.data || !mainChart) return;
    const symbol = state.data.symbol;
    const analysis = state.data.timeframes[state.activeTimeframe];
    const interval = analysis && analysis.interval;
    if (!symbol || !interval) return;

    // All requests at once, each with a time limit: one slow indicator used
    // to hold back every pane after it. Drawn in the list's order.
    const requests = state.customIndicators.map((ind) => fetch("/api/indicators/compute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(30000),
      body: JSON.stringify({
        symbol,
        asset_type: state.assetType,
        exchange: state.cryptoExchange || "mexc",
        timeframe: state.activeTimeframe,
        interval,
        indicator: ind.id,
        params: {},
      }),
    }).then((resp) => (resp.ok ? resp.json() : null)).catch(() => null));
    for (const [n, ind] of state.customIndicators.slice().entries()) {
      const data = await requests[n];
      if (mySeq !== indicatorsRefreshSeq) return; // superata da un'esecuzione piu' recente
      if (!data) continue; // un indicatore che fallisce non deve bloccare gli altri
      const times = data.times || [];
      const seriesList = data.series || [];
      if (data.kind === "overlay") {
        seriesList.forEach((s, i) => {
          const color = CUSTOM_IND_COLORS[i % CUSTOM_IND_COLORS.length];
          const line = mainChart.addLineSeries({ color, lineWidth: 1.4, priceLineVisible: false, lastValueVisible: false });
          const points = pointsFromTimesValues(times, s.values);
          line.setData(points);
          customOverlaySeriesList.push({ chart: mainChart, series: line, id: ind.id });
        });
      } else {
        const container = document.createElement("div");
        container.className = "sub-chart";
        const wrap = el("chart-wrap");
        if (!wrap) continue;
        wrap.appendChild(container);
        const chart = LightweightCharts.createChart(container, dynamicSubChartOptions());
        seriesList.forEach((s, i) => {
          const color = CUSTOM_IND_COLORS[i % CUSTOM_IND_COLORS.length];
          const line = chart.addLineSeries({ color, lineWidth: s.colors ? 2 : 1.4 });
          const points = pointsFromTimesValues(times, s.values);
          // Zones drawn on the line itself (Cycle Bottom Index: red..green).
          if (s.colors) points.forEach((p, k) => { if (p.value !== undefined && s.colors[k]) p.color = s.colors[k]; });
          line.setData(points);
          (s.levels || []).forEach((price) => line.createPriceLine({
            price, color: "rgba(148,163,184,0.6)", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "",
          }));
        });
        const range = mainChart.timeScale().getVisibleLogicalRange();
        if (range) chart.timeScale().setVisibleLogicalRange(range);
        scheduleScaleAlign();
        observeResize(container, chart);
        followPane(chart, container);
        makeSubChartResizable(container, `custom:${ind.id}`);
        // Il riquadro appartiene a un solo indicatore: una "x" appare
        // nell'angolo al passaggio del mouse (CSS, .sub-chart:hover), stesso
        // comportamento delle linee sul prezzo — niente rimozione al primo
        // click, solo quando si clicca la x apposta.
        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "osc-remove-btn";
        removeBtn.title = "Remove this indicator";
        removeBtn.textContent = "✕";
        removeBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          toggleCustomIndicator(ind.id);
        });
        container.appendChild(removeBtn);
        // Nome sempre visibile (non solo al passaggio del mouse, a
        // differenza della x): senza, un riquadro con solo delle linee
        // colorate non dice quale indicatore sia. Click sul nome apre la
        // spiegazione — la stessa scritta nella libreria.
        const title = document.createElement("span");
        title.className = "osc-chart-title";
        title.textContent = ind.label;
        title.addEventListener("click", (e) => {
          e.stopPropagation();
          const rect = container.getBoundingClientRect();
          showIndicatorInfoPopup(ind.id, rect.left + 10, rect.top + 24);
        });
        container.appendChild(title);
        customOscCharts[ind.id] = { container, chart };
      }
    }
  }

  function bindUI() {
    bindIndicatorCatalog();
    document.querySelectorAll("[data-layer]").forEach((input) => {
      input.addEventListener("change", () => {
        state.layers[input.dataset.layer] = input.checked;
        render();
        // Sub-charts (RSI, MACD, Stoch) go from display:none → visible inside render().
        // The ResizeObserver fires asynchronously after the layout reflow, so the
        // chart may still have zero dimensions at the time render() calls resize.
        // A single rAF after the paint ensures the new dimensions are available.
        requestAnimationFrame(() => resizeAllCharts());
        savePreferences();
      });
    });

    el("search-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const symbol = el("ticker-input").value.trim();
      if (!symbol) return;
      // Cercare un ticker a mano e' l'uscita dal contesto di "sto guardando
      // il risultato che ho applicato": da qui il grafico torna al suo
      // backtest pulito, come prima che qualcosa venisse applicato.
      state.chartBacktestOverride = null;
      // No suggestion explicitly picked (e.g. hit Enter right away) — if the
      // typed text exactly matches a suggestion already fetched, use its
      // asset type/exchange instead of falling back to whatever was set last.
      const exact = state.suggestions.find((s) => s.symbol.toLowerCase() === symbol.toLowerCase());
      if (exact) {
        state.assetType = exact.asset_type;
        if (exact.asset_type === "crypto") state.cryptoExchange = exact.provider;
      }
      hideSuggestions();
      closeMobileTickerSearch();
      runAnalysis(symbol);
    });

    bindTickerAutocomplete();
    bindMobileTickerSearch();
    bindWatchlistAutocomplete();
    bindFavorites();

    el("interval-primary").addEventListener("change", () => {
      if (state.pineActive) clearPineOverride();
      if (state.data) runAnalysis(state.data.symbol);
    });

    el("params-form").addEventListener("submit", (e) => {
      e.preventDefault();
      if (state.data) runAnalysis(state.data.symbol);
    });

    el("active-strategy-select").addEventListener("change", () => {
      // Scegliere una strategia dalla toolbar e' manuale, non "riproponi
      // quello che ho trovato nel Laboratorio": stessa uscita di sopra.
      state.chartBacktestOverride = null;
      renderStrategyParamsFields();
      updateOptimizeButtonVisibility();
      if (state.data) runAnalysis(state.data.symbol);
    });

    el("optimize-strategy-btn").addEventListener("click", runStrategyOptimize);

    document.querySelectorAll(".wl-asset-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".wl-asset-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.watchlistAssetType = btn.dataset.watchlistAsset;
        el("watchlist-exchange").classList.toggle("hidden", state.watchlistAssetType !== "crypto");
        wlSuggest.resolved = null; // asset type changed — whatever pair was confirmed no longer applies
        showResolvedPair(null);
      });
    });

    el("watchlist-exchange").addEventListener("change", () => {
      wlSuggest.resolved = null; // exchange changed — re-verify against the new one
      showResolvedPair(null);
    });

    el("watchlist-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const symbolInput = el("watchlist-symbol");
      const typed = symbolInput.value.trim();
      if (!typed) return;

      // The ticker must have been actively verified against this exact
      // asset type/exchange (picked from the suggestions list) — a symbol
      // typed and never confirmed could resolve to the wrong pair
      // (or nothing at all) on the selected exchange.
      let resolved = wlSuggest.resolved && wlSuggest.resolved.symbol === typed ? wlSuggest.resolved : null;
      if (!resolved) {
        await wlSuggest.fetch(typed);
        const exact = wlSuggest.suggestions.find((s) => s.symbol.toUpperCase() === typed.toUpperCase());
        if (exact) {
          resolved = exact;
          el("watchlist-symbol").value = exact.symbol;
          wlSuggest.resolved = exact;
          wlSuggest.clear();
          showResolvedPair(exact);
        }
      }
      if (!resolved) {
        showResolvedPair(null);
        const hint = el("watchlist-resolved-pair");
        hint.textContent =
          "Ticker not found on this exchange — pick a pair from the menu that appears as you type.";
        hint.classList.remove("hidden");
        hint.classList.add("wl-resolved-pair-error");
        return;
      }

      await fetch("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: resolved.symbol,
          asset_type: state.watchlistAssetType,
          exchange: el("watchlist-exchange").value,
          interval: el("watchlist-interval").value,
          on_close: el("watchlist-onclose").checked,
          // Solo per un pair dex: l'indirizzo del token base, gia' nella
          // ricerca (DexScreener), serve a Fase 4 per un ordine automatico.
          base_token_address: resolved.base_token_address || null,
        }),
      });
      symbolInput.value = "";
      wlSuggest.resolved = null;
      showResolvedPair(null);
      el("watchlist-resolved-pair").classList.remove("wl-resolved-pair-error");
      loadWatchlist();
    });

    el("open-script-from-alert").addEventListener("click", (e) => {
      e.stopPropagation();
      openPanel("script-panel");
    });

    el("price-alert-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const symbol = el("pa-symbol").value.trim().toUpperCase();
      const condition = el("pa-condition").value;
      const price = parseFloat(el("pa-price").value);
      const note = el("pa-note").value.trim();
      const once_only = el("pa-once").checked;
      if (!symbol || isNaN(price) || price <= 0) return;
      try {
        const resp = await fetch("/api/price-alerts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbol, condition, price, note, once_only, asset_type: "crypto", exchange: "mexc" }),
        });
        if (resp.ok) {
          e.target.reset();
          loadPriceAlerts();
        }
      } catch { /* ignore */ }
    });

    el("alert-log-clear-btn").addEventListener("click", () => clearAlertLog());

    el("strategy-markers-toggle").addEventListener("change", applyChartMarkers);
    el("executed-orders-toggle")?.addEventListener("change", applyChartMarkers);

    const btTrades = el("backtest-trades-toggle");
    if (btTrades) {
      btTrades.addEventListener("change", () => {
        if (!btTrades.checked) el("backtest-trades-note").classList.add("hidden");
        applyChartMarkers();
      });
    }

    el("strategy-notify-toggle").addEventListener("change", async (e) => {
      if (!e.target.checked) return;
      if (!("Notification" in window)) {
        e.target.checked = false;
        return;
      }
      if (Notification.permission === "default") {
        const permission = await Notification.requestPermission();
        if (permission !== "granted") e.target.checked = false;
      } else if (Notification.permission === "denied") {
        e.target.checked = false;
      }
    });

    el("log-scale-toggle").addEventListener("change", (e) => {
      state.logScale = e.target.checked;
      mainChart.priceScale("right").applyOptions({
        mode: state.logScale ? LightweightCharts.PriceScaleMode.Logarithmic : LightweightCharts.PriceScaleMode.Normal,
      });
      savePreferences();
    });
  }

  // On phones the toolbar has no room to also carry the timeframe/strategy/
  // log-scale controls without burying the chart below the fold (a TradingView
  // mobile screen shows almost nothing but the chart). Relocate that one group
  // — moving the real nodes, not cloning them, so there's still exactly one
  // #interval-primary etc. in the DOM — into the Livelli drawer on mobile, and
  // back into the toolbar on desktop.
  function relocateChartSettings() {
    const group = el("chart-settings-group");
    const isMobile = window.matchMedia("(max-width: 760px)").matches;
    const targetParent = isMobile ? el("levels-panel") : document.querySelector(".toolbar");
    if (group.parentElement === targetParent) return;
    if (isMobile) {
      const header = targetParent.querySelector(".drawer-header");
      targetParent.insertBefore(group, header.nextSibling);
    } else {
      const spacer = targetParent.querySelector(".toolbar-spacer");
      targetParent.insertBefore(group, spacer);
    }
  }

  // Same relocation trick as chart-settings-group above, for the account
  // widget (email + Accedi/Esci) — it moves into the Altro screen's account
  // row on mobile instead of staying in the toolbar, which is exactly what
  // was squeezing the ticker search field down to an unreadable sliver.
  function relocateAuthWidget() {
    const widget = document.querySelector(".auth-widget");
    const isMobile = window.matchMedia("(max-width: 760px)").matches;
    const targetParent = isMobile ? el("altro-account-slot") : document.querySelector(".toolbar");
    if (widget.parentElement === targetParent) return;
    targetParent.appendChild(widget);
  }

  // The timeframe select otherwise only lives inside the Livelli screen —
  // reachable, but not from the chart itself, which is where "change the
  // timeframe" actually happens. On mobile it moves into the persistent
  // strip pinned above the bottom nav, kept visually hidden there (see
  // #mobile-chart-interval-slot in style.css) — the wheel widget next to
  // it is the real UI, driven off this select (buildMobileTfWheel/
  // syncMobileTfWheel), so the one source of truth stays this element.
  // Desktop keeps it visible in the toolbar's chart-settings-group.
  function relocateIntervalSelect() {
    const select = el("interval-primary");
    const isMobile = window.matchMedia("(max-width: 760px)").matches;
    const targetParent = isMobile ? el("mobile-chart-interval-slot") : document.querySelector("#chart-settings-group .toolbar-intervals");
    if (select.parentElement === targetParent) return;
    targetParent.appendChild(select);
  }

  // Switching which strategy drives the backtest/markers is a Strategia
  // concern, not a Livelli one — but on mobile it used to travel with the
  // rest of chart-settings-group into the Livelli screen, so switching
  // strategy meant leaving Strategia entirely. Pull just this one control
  // out and drop it at the top of the Strategia screen instead; desktop is
  // unaffected, it stays in the toolbar.
  function relocateStrategySelect() {
    const select = el("active-strategy-select");
    const isMobile = window.matchMedia("(max-width: 760px)").matches;
    const targetParent = isMobile ? el("strategy-select-slot") : el("chart-settings-group");
    if (select.parentElement === targetParent) return;
    select.classList.toggle("mobile-strategy-select", isMobile);
    if (isMobile) {
      targetParent.appendChild(select);
    } else {
      targetParent.insertBefore(select, targetParent.querySelector(".toolbar-check"));
    }
  }

  // Runs once, either right away (already logged in) or right after the
  // login gate clears — everything that fetches real data or auto-loads a
  // chart waits behind auth so nothing renders before the page unlocks.
  async function startApp() {
    appStarted = true;
    try {
      // Stessa guardia di initCharts() sopra, stesso motivo: se l'editor
      // Pine non parte non deve portarsi dietro bindPineUI, il caricamento
      // strategie e l'auto-load del ticker che vengono subito dopo in
      // questa stessa funzione — sarebbe un intero avvio dell'app rotto
      // per un componente che quasi nessuno apre in ogni sessione.
      initPineEditor();
    } catch (err) {
      console.error("initPineEditor() failed — Pine Script may not work, the rest of the app does, continuing:", err);
    }
    bindPineUI();
    loadPineScripts();
    relocateChartSettings();
    relocateIntervalSelect();
    relocateStrategySelect();
    // active-strategy-select must be populated before the auto-load below
    // reads its value, or the request goes out with an empty strategy_name.
    await populateStrategySelects();
    // La watchlist puo' gia' essere stata caricata (checkAuth() la chiama
    // presto, per mostrare qualcosa prima possibile) con
    // state.availableStrategies ancora vuoto: ogni riga rendeva solo
    // timeframe/chiusura, senza i toggle/parametri per strategia — la
    // segnalazione "mancano le impostazioni per verificare i parametri della
    // strategia" era questa corsa, non una funzione rimossa. Ridisegnarla
    // ora che le strategie ci sono la corregge senza aspettare un'altra
    // azione dell'utente.
    if (el("watchlist-list")?.children.length) loadWatchlist();
    initLabState(state.availableStrategies || []);
    renderBtcBadge();
    setInterval(renderBtcBadge, 3600 * 1000);
    // Ripristina l'ultima sessione dal server; fallback a BTC/MEXC.
    const prefs = await loadPreferences();
    state.assetType = prefs?.asset_type || "crypto";
    state.cryptoExchange = prefs?.exchange || "mexc";
    const ticker = prefs?.ticker || "BTC";
    el("ticker-input").value = ticker;
    el("ticker-input").title = ticker;
    if (prefs?.interval) {
      const sel = el("interval-primary");
      if (sel) sel.value = prefs.interval;
    }
    // A saved strategy that is no longer offered (hidden or removed, e.g.
    // RSI+BB 4H on 16/10) would leave the select empty and every request
    // would go out with strategy_name="": keep the default instead.
    if (prefs?.strategy && hasStrategyOption(prefs.strategy)) {
      el("active-strategy-select").value = prefs.strategy;
    }
    if (prefs?.layers) {
      Object.entries(prefs.layers).forEach(([k, v]) => {
        state.layers[k] = v;
        const inp = document.querySelector(`[data-layer="${k}"]`);
        if (inp) inp.checked = v;
      });
    }
    // Il tema scelto sull'account vince su quello del dispositivo, ma solo se
    // una scelta e' stata fatta davvero: chi non ha mai toccato l'interruttore
    // continua a seguire il proprio sistema.
    if (prefs?.theme === "dark" || prefs?.theme === "light") {
      applyTheme(prefs.theme);
    }
    if (prefs?.log_scale) {
      const tog = el("log-scale-toggle");
      if (tog) tog.checked = true;
      state.logScale = true;
      // La spunta e lo stato non bastano da soli: il grafico nasce sempre in
      // scala lineare (baseOptions non dichiara un mode), e senza questa
      // riga restava lineare anche con la preferenza gia' salvata su log,
      // finche' non si ritoccava a mano l'interruttore. "a volte la
      // visualizzazione appare in scala lineare" — sempre, in realta', al
      // primo caricamento con la preferenza gia' attiva.
      if (mainChart) {
        mainChart.priceScale("right").applyOptions({ mode: LightweightCharts.PriceScaleMode.Logarithmic });
      }
    }
    if (!openDeepLink()) runAnalysis(ticker);
  }

  // ── Backtest Lab (independent from chart) ──────────────────────────────
  const labState = {
    symbol: null,       // resolved symbol string (e.g. "BTCUSDT")
    displaySymbol: null,// short name for display (e.g. "BTC")
    assetType: "crypto",
    exchange: "mexc",
    tf: "1d",
    strategy: null,     // set after populateStrategySelects
    resolved: null,     // full suggestion item
    seq: 0,             // monotonic to discard stale responses
    lastBt: null,       // last successful BacktestResult
  };

  function labEl(id) { return document.getElementById(id); }

  // Gli stessi quattro campi letti da buildLabQuery(), ma come oggetto: e'
  // quello che "Applica al grafico" porta con se', cosi' il grafico riproduce
  // esattamente il backtest appena mostrato invece di una sua versione
  // ripulita.
  function labBacktestParams() {
    return {
      initial_capital: Number(inputNumber(labEl("lab-initial-capital"), 1000, { min: 1 })),
      qty_pct_of_equity: Number(inputNumber(labEl("lab-qty-pct"), 100, { min: 1, max: 100 })),
      commission_pct: Number(inputNumber(labEl("lab-commission"), 0, { min: 0 })),
      slippage_pct: Number(inputNumber(labEl("lab-slippage"), 0, { min: 0 })),
      fill_at: labEl("lab-fill-at")?.value || "signal_close",
    };
  }

  function buildLabQuery() {
    const strategyName = labState.strategy || "";
    // Exchange selector overrides labState when explicitly changed by user
    const exchangeSel = el("lab-exchange-select");
    // A DEX pair ignores the exchange (the backend reads the pool), but the
    // parameter still has to be one of the four exchanges.
    const picked = exchangeSel ? exchangeSel.value : (labState.exchange || "mexc");
    const exchange = labState.assetType === "dex" || picked === "dexscreener" ? "mexc" : picked;
    const params = new URLSearchParams();
    params.set("symbol", labState.symbol || "BTCUSDT");
    params.set("asset_type", labState.assetType);
    params.set("exchange", exchange);
    params.set("ltf_interval", labState.tf);
    params.set("strategy_name", strategyName);
    params.set("initial_capital", inputNumber(labEl("lab-initial-capital"), 1000, { min: 1 }));
    params.set("qty_pct_of_equity", inputNumber(labEl("lab-qty-pct"), 100, { min: 1, max: 100 }));
    params.set("commission_pct", inputNumber(labEl("lab-commission"), 0, { min: 0 }));
    params.set("slippage_pct", inputNumber(labEl("lab-slippage"), 0, { min: 0 }));
    params.set("fill_at", labEl("lab-fill-at")?.value || "signal_close");
    params.set("stop_loss_pct", "0");
    params.set("take_profit_pct", "0");
    // Periodo facoltativo: vuoto = tutta la storia disponibile (comportamento
    // di sempre). Il backend ritaglia la serie PRIMA del backtest, non dopo.
    const dateStart = labEl("lab-date-start")?.value;
    const dateEnd = labEl("lab-date-end")?.value;
    if (dateStart) params.set("start_date", dateStart);
    if (dateEnd) params.set("end_date", dateEnd);
    const container = labEl("lab-params-fields");
    const fields = STRATEGY_PARAM_FIELDS[strategyName] || [];
    fields.forEach((field) => {
      const input = container.querySelector(`[name="${field.key}"]`);
      if (!input) return;
      params.set(field.key, field.type === "checkbox" ? input.checked
        : field.type === "select" ? input.value
        : fieldNumber(input, field));
    });
    return params;
  }

  // Strategies for which the backend has a full discrete grid (grid mode).
  const GRID_STRATEGIES = new Set([
    "Gabriele (RSI+BB reversal)",
    "Gabriele 2 (RSI+BB long/short)",
    "Accumulo / Distribuzione (long-term)",
  ]);


  // Reason strings and branch labels are built server-side and interpolated
  // into innerHTML below; escape them rather than trusting their shape.
  function escapeHtml(str) {
    return String(str ?? "").replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
  }

  // Which optimisation mode the user picked in the lab.
  function labOptMode() {
    const checked = document.querySelector('input[name="lab-opt-mode"]:checked');
    return checked ? checked.value : "random";
  }

  // Filtri sul risultato dell'ottimizzazione. Vuoto significa "nessun vincolo",
  // e va tenuto distinto da 0, che e' il vincolo piu' stringente e legittimo:
  // "nessun trade in perdita", "drawdown nullo". Per questo il valore si legge
  // con un confronto esplicito sulla stringa vuota, non con un test di verita'
  // — con quest'ultimo uno 0 scritto a mano sparirebbe in silenzio.
  function labFilterValue(id) {
    const input = labEl(id);
    if (!input) return null;
    const raw = (input.value || "").trim();
    if (raw === "") return null;
    const n = Number(raw);
    return Number.isFinite(n) && n >= 0 ? n : null;
  }

  function labFilters() {
    return {
      min_losing_trades: labFilterValue("lab-min-losing"),
      max_losing_trades: labFilterValue("lab-max-losing"),
      max_drawdown_pct: labFilterValue("lab-max-dd"),
    };
  }

  function applyLabFilters(params) {
    const f = labFilters();
    let active = 0;
    Object.entries(f).forEach(([key, value]) => {
      if (value === null) return;
      params.set(key, String(value));
      active += 1;
    });
    const badge = labEl("lab-filters-badge");
    if (badge) {
      badge.textContent = active ? `${active} active` : "";
      badge.classList.toggle("hidden", active === 0);
    }
    return active;
  }

  function bindLabFilters() {
    const clear = labEl("lab-filters-clear");
    if (clear) {
      clear.addEventListener("click", () => {
        ["lab-min-losing", "lab-max-losing", "lab-max-dd"].forEach((id) => {
          const input = labEl(id);
          if (input) input.value = "";
        });
        const badge = labEl("lab-filters-badge");
        if (badge) { badge.textContent = ""; badge.classList.add("hidden"); }
      });
    }
  }

  // The regime gate answers a question that comes before "which parameters":
  // does this strategy have an edge to find on this series at all? A failed
  // gate means any configuration returned is fitted to noise, so it is shown
  // as a warning rather than folded into the numbers.

  // Su quali dati e' realmente girata l'ottimizzazione. Va mostrato sempre,
  // non solo quando differisce: sapere che i due coincidono e' informazione
  // quanto sapere che divergono, e chi legge non deve indovinare quale dei due
  // casi ha davanti.
  function renderDataUsed(body) {
    const box = labEl("lab-data-used");
    if (!box) return;
    const d = body.data_used;
    if (!d) { box.classList.add("hidden"); return; }
    box.classList.toggle("mismatch", !!d.differs_from_chart);
    box.innerHTML =
      `<div class="lab-du-head">${d.differs_from_chart ? "⚠ Data differs from the chart" : "Data used"}</div>`
      + `<div class="lab-du-row"><span>Optimization timeframe</span><b>${escapeHtml(d.interval)}</b></div>`
      + `<div class="lab-du-row"><span>Chart timeframe</span><b>${escapeHtml(d.chart_interval)}</b></div>`
      + `<div class="lab-du-row"><span>Candles</span><b>${d.candles}</b></div>`
      + `<p class="lab-du-note">${escapeHtml(d.note || "")}</p>`;
    box.classList.remove("hidden");
  }

  function renderRegimeBox(body) {
    const box = labEl("lab-regime-box");
    if (!box) return;
    if (!body.regime) { box.classList.add("hidden"); return; }
    const r = body.regime;
    const ok = r.passed;
    const det = body.deterministic;
    const bits = [];
    bits.push(`<div class="lab-regime-head ${ok ? "ok" : "warn"}">`
      + `${ok ? "✓ Compatible regime" : "⚠ Incompatible regime"}</div>`);
    bits.push(`<div class="lab-regime-reason">${escapeHtml(r.reason || "")}</div>`);
    const stats = [];
    if (r.variance_ratio != null) {
      stats.push(`<span title="Variance ratio: how far the variance of multi-period returns strays from that of a random walk. 1.0 = random walk.">VR ${r.variance_ratio.toFixed(3)}</span>`);
    }
    if (r.vr_z != null) {
      stats.push(`<span title="VR z-score: how many standard deviations it is from 1 (random walk).">z ${r.vr_z >= 0 ? "+" : ""}${r.vr_z.toFixed(2)}</span>`);
    }
    if (r.vr_p_one_sided != null) {
      stats.push(`<span title="One-sided p-value: probability of seeing this VR (or more extreme) if the series really were a random walk. Below 0.05 is considered significant.">p ${r.vr_p_one_sided.toFixed(4)}</span>`);
    }
    if (r.hurst != null) {
      stats.push(`<span title="Hurst exponent: above 0.5 means persistence (trend), below 0.5 mean-reversion, 0.5 is a random walk.">H ${r.hurst.toFixed(3)}</span>`);
    }
    if (stats.length) bits.push(`<div class="lab-regime-stats">${stats.join(" · ")}</div>`);
    // Il VR da solo non basta: e' la combinazione con il p-value che dice se
    // la direzione osservata e' reale o solo rumore campionato.
    if (r.variance_ratio != null && r.vr_p_one_sided != null) {
      const vr = r.variance_ratio;
      const p = r.vr_p_one_sided;
      const farFromOne = Math.abs(vr - 1) >= 0.1;
      const significant = p < 0.05;
      const regimeVerdict = (farFromOne && significant)
        ? `VR significantly ${vr < 1 ? "below" : "above"} 1 (p ${p.toFixed(4)}): the series shows a real direction, not just noise.`
        : `VR close to 1 or not significant (p ${p.toFixed(4)}): the series behaves like a random walk, no reliable direction.`;
      bits.push(`<div class="lab-regime-sub">${regimeVerdict}</div>`);
    }
    if (det != null) {
      bits.push(`<div class="lab-regime-det ${det ? "ok" : "warn"}">`
        + (det
          ? "Reproducible result: re-running on the same data will give the same parameters."
          : "Some branches exceeded the budget and were sampled: that part of the result is not reproducible.")
        + "</div>");
    }
    const d = body.deflated_sharpe;
    if (d && d.deflated != null) {
      const ok = d.acceptable;
      bits.push(
        `<div class="lab-regime-det ${ok ? "ok" : "warn"}">`
        + `Sharpe ${d.sharpe != null ? d.sharpe.toFixed(2) : "—"} · `
        + `threshold for ${d.n_trials} trials ${d.sharpe_threshold != null ? d.sharpe_threshold.toFixed(2) : "—"} · `
        + `reliability ${(d.deflated * 100).toFixed(1)}%`
        + (ok ? "" : " — indistinguishable from the best of as many trials on pure noise")
        + "</div>");
    }
    // Il PBO non e' un doppione dello Sharpe deflazionato: quello corregge un
    // numero, questo giudica la selezione. Un risultato puo' superare l'uno e
    // fallire l'altro, e i due casi si leggono diversamente.
    const o = body.overfitting;
    if (o && o.pbo != null) {
      bits.push(
        `<div class="lab-regime-det ${o.acceptable ? "ok" : "warn"}">`
        + `Over-optimization ${(o.pbo * 100).toFixed(0)}% `
        + `<span class="lab-regime-sub">(${o.n_candidates} candidates, ${o.n_splits} splits)</span>`
        + (o.acceptable
          ? " — the chosen configuration also holds on the halves that didn't select it"
          : " — how often, among the candidates, the in-sample best ends up below the out-of-sample median")
        + "</div>");
    }
    (body.pipeline_notes || []).forEach((n) => {
      bits.push(`<div class="lab-regime-note">${escapeHtml(n)}</div>`);
    });
    box.innerHTML = bits.join("");
    box.classList.remove("hidden");
  }

  // Branch comparison. Showing these side by side is the point: a branch with
  // more free parameters can score higher in-sample and worse out-of-sample,
  // and a single returned number hides exactly that.
  function renderBranchBox(body) {
    const box = labEl("lab-branch-box");
    if (!box) return;
    const rows = body.branches || [];
    if (rows.length < 2) { box.classList.add("hidden"); return; }
    const head = `<div class="lab-branch-title">Variants compared</div>`
      + `<table class="lab-branch-tbl"><thead><tr>`
      + `<th>variant</th><th>par.</th><th>history</th><th>validation</th><th>trades</th>`
      + `</tr></thead><tbody>`;
    const trs = rows.map((b) => {
      const val = b.validation_return_pct == null
        ? "—"
        : `${b.validation_return_pct >= 0 ? "+" : ""}${b.validation_return_pct.toFixed(1)}%`;
      const vt = b.validation_trades == null ? "" : ` <span class="lab-branch-tr">(${b.validation_trades})</span>`;
      return `<tr class="${b.chosen ? "chosen" : ""}">`
        + `<td>${escapeHtml(b.label)}${b.chosen ? ' <span class="lab-branch-pick">chosen</span>' : ""}`
        + `${b.enumerated ? "" : ' <span class="lab-branch-samp" title="Space too large to explore fully: this row is not reproducible">sampled</span>'}</td>`
        + `<td class="n">${b.dims}</td>`
        + `<td class="n">${b.total_return_pct >= 0 ? "+" : ""}${b.total_return_pct.toFixed(1)}%</td>`
        + `<td class="n">${val}${vt}</td>`
        + `<td class="n">${b.num_trades}</td></tr>`;
    }).join("");
    box.innerHTML = head + trs + "</tbody></table>";
    box.classList.remove("hidden");
  }

  function renderLabParamFields() {
    const strategyName = labState.strategy || "";
    // 16/10 (Lorenzo): a strategy with no automatic optimization shows no
    // Optimize button, search modes or result filters — only Run.
    const canOptimize = OPTIMIZABLE_STRATEGIES.has(strategyName);
    labEl("lab-optimize-btn")?.classList.toggle("hidden", !canOptimize);
    document.querySelector(".lab-mode-picker")?.classList.toggle("hidden", !canOptimize);
    labEl("lab-filters")?.classList.toggle("hidden", !canOptimize);
    const fields = STRATEGY_PARAM_FIELDS[strategyName] || [];
    const container = labEl("lab-params-fields");
    container.innerHTML = "";
    // Show grid-mode toggle only for strategies that support it.
    const gridWrap = labEl("lab-mode-grid-wrap");
    if (gridWrap) gridWrap.classList.toggle("hidden", !GRID_STRATEGIES.has(strategyName));
    // Max return searches the two RSI levels: RSI+BB strategies only.
    // Claudio 4H is searched by Max return only.
    const claudio = strategyName === "Claudio 4H";
    document.querySelectorAll('input[name="lab-opt-mode"]').forEach((r) => {
      if (r.value !== "max_return") r.closest("label").classList.toggle("hidden", claudio || (r.value === "grid" && !GRID_STRATEGIES.has(strategyName)));
    });
    if (claudio) { const mr = document.querySelector('input[name="lab-opt-mode"][value="max_return"]'); if (mr) mr.checked = true; }
    const maxWrap = labEl("lab-mode-maxret-wrap");
    if (maxWrap) {
      const ok = /RSI\+BB/.test(strategyName || "") || claudio;
      maxWrap.classList.toggle("hidden", !ok);
      // 15/10 (Lorenzo): on the RSI+BB strategies Max return is the
      // recommended search, Stable on the others — and it is preselected.
      const stableWrap = labEl("lab-mode-stable-wrap");
      maxWrap.classList.toggle("lab-mode-recommended", ok);
      maxWrap.querySelector(".lab-rec-tag")?.classList.toggle("hidden", !ok);
      if (stableWrap) {
        stableWrap.classList.toggle("lab-mode-recommended", !ok);
        stableWrap.querySelector(".lab-rec-tag")?.classList.toggle("hidden", ok);
      }
      const radio = maxWrap.querySelector("input");
      const stableRadio = document.querySelector('input[name="lab-opt-mode"][value="plateau"]');
      if (ok && radio && stableRadio && stableRadio.checked) radio.checked = true;
      if (!ok && radio && radio.checked) {
        radio.checked = false;
        const quick = stableRadio || document.querySelector('input[name="lab-opt-mode"][value="random"]');
        if (quick) quick.checked = true;
      }
    }
    fields.forEach((field) => {
      const label = document.createElement("label");
      if (field.type === "checkbox") {
        label.className = "full-width";
        label.innerHTML = `<input type="checkbox" name="${field.key}" ${field.default ? "checked" : ""} /> ${field.label}`;
      } else if (field.type === "select") {
        const options = field.options
          .map((opt) => `<option value="${opt}"${opt === field.default ? " selected" : ""}>${opt}</option>`)
          .join("");
        label.innerHTML = `<span>${field.label}</span><select name="${field.key}">${options}</select>`;
      } else {
        // Vedi la nota in renderStrategyParamsFields(): testo, non number.
        label.innerHTML = `<span>${field.label}</span><input type="text" inputmode="decimal" name="${field.key}" value="${field.default}" />`;
      }
      container.appendChild(label);
    });
    addStrategyExtras(container, strategyName);
  }

  function drawLabEquityCanvas(equityCurve) {
    const canvas = labEl("lab-equity-canvas");
    if (!canvas || !equityCurve || equityCurve.length < 2) return;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.offsetWidth || 270;
    const h = 90;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.height = h + "px";
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    const values = equityCurve.map((p) => p[1]);
    const initial = values[0];
    const minV = Math.min(...values);
    const maxV = Math.max(...values);
    const range = maxV - minV || 1;
    const pad = { t: 6, b: 6, l: 4, r: 4 };
    const ew = w - pad.l - pad.r;
    const eh = h - pad.t - pad.b;
    const toX = (i) => pad.l + (i / (values.length - 1)) * ew;
    const toY = (v) => pad.t + eh - ((v - minV) / range) * eh;
    const points = values.map((v, i) => [toX(i), toY(v)]);
    const isPos = values[values.length - 1] >= initial;
    const stroke = isPos ? COLORS.bull : COLORS.bear;

    // Drawdown shading — area below the running peak
    const peaks = [];
    let peak = values[0];
    values.forEach((v) => { if (v > peak) peak = v; peaks.push(peak); });
    ctx.beginPath();
    ctx.moveTo(points[0][0], toY(peaks[0]));
    peaks.forEach((pk, i) => { ctx.lineTo(toX(i), toY(pk)); });
    for (let i = values.length - 1; i >= 0; i--) ctx.lineTo(toX(i), toY(values[i]));
    ctx.closePath();
    ctx.fillStyle = "rgba(242,54,69,0.10)";
    ctx.fill();

    // Equity area fill
    const grad = ctx.createLinearGradient(0, pad.t, 0, h - pad.b);
    grad.addColorStop(0, isPos ? "rgba(8,153,129,0.22)" : "rgba(242,54,69,0.18)");
    grad.addColorStop(1, "rgba(0,0,0,0)");
    ctx.beginPath();
    ctx.moveTo(points[0][0], h - pad.b);
    ctx.lineTo(points[0][0], points[0][1]);
    points.slice(1).forEach(([x, y]) => ctx.lineTo(x, y));
    ctx.lineTo(points[points.length - 1][0], h - pad.b);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Baseline at initial capital
    const baseY = toY(initial);
    ctx.beginPath();
    ctx.moveTo(pad.l, baseY);
    ctx.lineTo(w - pad.r, baseY);
    ctx.strokeStyle = "rgba(120,123,134,0.25)";
    ctx.lineWidth = 0.8;
    ctx.setLineDash([3, 3]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Equity line
    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);
    points.slice(1).forEach(([x, y]) => ctx.lineTo(x, y));
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 1.8;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.stroke();

    // Endpoint dot
    const last = points[points.length - 1];
    ctx.beginPath();
    ctx.arc(last[0], last[1], 3, 0, Math.PI * 2);
    ctx.fillStyle = stroke;
    ctx.fill();
  }


  // ── Mappa del plateau ─────────────────────────────────────────────────
  // Il backend restituisce da sempre i dieci candidati migliori con il loro
  // punteggio, e il commento accanto al modello dice a cosa servono: far
  // vedere la dispersione, perche' una rosa i cui membri litigano e' essa
  // stessa il segnale che il vincitore e' un colpo di fortuna. Nessuna
  // schermata li aveva mai mostrati. Qui diventano una mappa: i due
  // parametri che variano di piu' sugli assi, il punteggio nel colore, il
  // vincitore marcato. Se il rombo sta in mezzo a celle chiare regge; se sta
  // da solo in mezzo al vuoto, quel risultato non si ripetera'.
  // Max return gives the two best pairs (Lorenzo, 13/10: "avere come esito
  // finale i due migliori risultati"). The first is already in the fields;
  // "Use" puts the other one there and runs it, the same backtest as Run.
  // "Verifica sull'ultimo anno": the values of this very card on the last
  // year of candles (15/10: "applicando i valori della strategia").
  function verifyLine(v) {
    if (!v) return "";
    if (v.skipped) return `<div class="lab-best2-verify muted">Last year: ${escapeHtml(v.skipped)}</div>`;
    const pct = (x) => (x == null ? "–" : `${x >= 0 ? "+" : ""}${x.toFixed(1)}%`);
    const from = new Date(v.from * 1000).toLocaleDateString("it-IT");
    const good = v.test_return_pct > 0;
    return `<div class="lab-best2-verify ${good ? "pos" : "neg"}">${v.unseen ? `Last 12 months, never seen by the search (from ${from})` : `Last year (from ${from}), these values`}: `
      + `<b>${pct(v.test_return_pct)}</b> · ${v.test_trades} trades · DD ${pct(-Math.abs(v.test_max_drawdown_pct))} `
      + `· buy & hold ${pct(v.buy_hold_pct)}</div>`;
  }

  // 15/10: whole history only ("gli ultimi 12 mesi [...] ormai non servono piu'")
  function pairTestTable(r) {
    const pct = (x) => (x == null ? "–" : `${x >= 0 ? "+" : ""}${Number(x).toFixed(1)}%`);
    const num = (x, d = 0) => (x == null ? "–" : Number(x).toFixed(d));
    const day = (t) => (t ? new Date(t * 1000).toLocaleDateString("it-IT") : "–");
    const cls = (x) => (x == null ? "" : x >= 0 ? "pos" : "neg");
    const h = r.history;
    const row = (label, a) => `<tr><th>${label}</th><td>${a}</td></tr>`;
    return `
      <div class="arch-testpair-title">${escapeHtml(r.symbol)} · ${escapeHtml(r.exchange.toUpperCase())} · ${escapeHtml(r.interval)} · ${r.candles} candles · same values</div>
      <table class="lab-detail">
        <thead><tr><th></th><th>Whole history</th></tr></thead>
        <tbody>
          ${row("Period", `${day(h.from)} → ${day(h.to)}<br><small>${num(h.years, 1)} years</small>`)}
          ${row("Simple profit", `<b class="${cls(h.simple_return_pct)}">${pct(h.simple_return_pct)}</b><br><small>every trade on the same stake</small>`)}
          ${row("Compounded profit", `<b class="${cls(h.return_pct)}">${pct(h.return_pct)}</b><br><small>reinvesting all the equity</small>`)}
          ${row("Per year (average)", `<b class="${cls(h.annual_pct)}">${pct(h.annual_pct)}</b>`)}
          ${row("Trades", `${num(h.trades)} <small>(${num(h.trades_per_year, 1)}/year)</small>`)}
          ${row("Won / lost", `${num(h.wins)} / ${num(h.losses)}`)}
          ${row("Win rate", h.win_rate_pct == null ? "–" : `${num(h.win_rate_pct)}%`)}
          ${row("Profit factor", num(h.profit_factor, 2))}
          ${row("Simple drawdown", `<b>${pct(h.simple_max_drawdown_pct == null ? null : -Math.abs(h.simple_max_drawdown_pct))}</b><br><small>in % of the starting capital</small>`)}
          ${row("Compounded drawdown", `<b>${pct(-Math.abs(h.max_drawdown_pct))}</b><br><small>from the equity peak</small>`)}
          ${row("Average / median trade", `${pct(h.avg_trade_pct)} / ${pct(h.median_trade_pct)}`)}
          ${row("Best / worst trade", `${pct(h.best_trade_pct)} / ${pct(h.worst_trade_pct)}`)}
          ${row("Buy & hold", pct(h.buy_hold_pct))}
        </tbody>
      </table>`;
  }

  function detailTable(c) {
    const h = c.history, v = c.verification || {};
    const pct = (x) => (x == null ? "–" : `${x >= 0 ? "+" : ""}${Number(x).toFixed(1)}%`);
    const num = (x, d = 0) => (x == null ? "–" : Number(x).toFixed(d));
    const day = (t) => (t ? new Date(t * 1000).toLocaleDateString("it-IT") : "–");
    const cls = (x) => (x == null ? "" : x >= 0 ? "pos" : "neg");
    const t = v.unseen;
    // 15/10: no unseen year on the site any more (tested in the test
    // environment on 2021 and 2022), so one column unless a result has one
    const row = (label, a, b, hint = "") => `<tr><th title="${hint}">${label}</th><td>${a}</td>${t ? `<td>${b}</td>` : ""}</tr>`;
    let verdict = "";
    if (t && h.annual_pct != null && v.return_pct != null) {
      const gap = v.return_pct - h.annual_pct;
      verdict = v.return_pct <= 0
        ? `Lost money on candles it never saw (${pct(v.return_pct)}): the history figure does not hold.`
        : gap >= -h.annual_pct * 0.3
          ? `Held up: the unseen year (${pct(v.return_pct)}) is in line with the average year of the history (${pct(h.annual_pct)}).`
          : `Positive but well below the average year of the history (${pct(v.return_pct)} vs ${pct(h.annual_pct)}): part of the history figure was fitted to the past.`;
      verdict += ` Buy & hold in the same 12 months: ${pct(v.buy_hold_pct)} (${v.vs_buy_hold_pct >= 0 ? "strategy ahead by" : "strategy behind by"} ${pct(Math.abs(v.vs_buy_hold_pct)).replace("+", "")}).`;
    }
    return `
      <table class="lab-detail">
        <thead><tr><th></th>${t ? "<th>History (chosen on)</th><th>Last 12 months · never seen</th>" : "<th>Whole history</th>"}</tr></thead>
        <tbody>
          ${row("Period", `${day(h.from)} → ${day(h.to)}<br><small>${num(h.years, 1)} years</small>`, `${day(v.from)} → ${day(v.to)}`)}
          ${row("Simple profit", `<b class="${cls(h.simple_return_pct)}">${pct(h.simple_return_pct)}</b>`, `<b class="${cls(v.simple_return_pct)}">${pct(v.simple_return_pct)}</b>`, "Every trade on the same stake, gains not reinvested")}
          ${row("Compounded profit", `<b class="${cls(h.return_pct)}">${pct(h.return_pct)}</b>`, `<b class="${cls(v.return_pct)}">${pct(v.return_pct)}</b>`, "Every trade reinvests all the equity so far")}
          ${row("Per year (average)", `<b class="${cls(h.annual_pct)}">${pct(h.annual_pct)}</b>`, `<b class="${cls(v.return_pct)}">${pct(v.return_pct)}</b>`, "Compounded yearly return: the fair comparison between the two columns")}
          ${row("Trades", `${num(h.trades)} <small>(${num(h.trades_per_year, 1)}/year)</small>`, num(v.trades))}
          ${row("Won / lost", `${num(h.wins)} / ${num(h.losses)}`, `${num(v.wins)} / ${num(v.losses)}`)}
          ${row("Win rate", h.win_rate_pct == null ? "–" : `${num(h.win_rate_pct)}%`, v.win_rate_pct == null ? "–" : `${num(v.win_rate_pct)}%`)}
          ${row("Profit factor", num(h.profit_factor, 2), num(v.profit_factor, 2), "Gross gains / gross losses: above 1 the strategy earns")}
          ${row("Simple drawdown", pct(h.simple_max_drawdown_pct == null ? null : -Math.abs(h.simple_max_drawdown_pct)), pct(v.simple_max_drawdown_pct == null ? null : -Math.abs(v.simple_max_drawdown_pct)), "Worst drop, in % of the starting capital")}
          ${row("Compounded drawdown", pct(-Math.abs(h.max_drawdown_pct)), pct(-Math.abs(v.max_drawdown_pct)), "Worst drop from the equity peak")}
          ${row("Average / median trade", `${pct(h.avg_trade_pct)} / ${pct(h.median_trade_pct)}`, `${pct(v.avg_trade_pct)} / ${pct(v.median_trade_pct)}`)}
          ${row("Best / worst trade", `${pct(h.best_trade_pct)} / ${pct(h.worst_trade_pct)}`, `${pct(v.best_trade_pct)} / ${pct(v.worst_trade_pct)}`)}
          ${t ? row("Buy & hold", "", pct(v.buy_hold_pct)) : ""}
        </tbody>
      </table>
      ${verdict ? `<div class="lab-best2-verify ${v.return_pct > 0 ? "pos" : "neg"}">${verdict}</div>` : ""}
      ${!t && v.skipped ? `<div class="lab-best2-verify muted">${escapeHtml(v.skipped)}</div>` : ""}`;
  }

  function renderBestTwo(body) {
    const box = labEl("lab-best2-box");
    if (!box) return;
    const cands = (body && body.mode === "max_return" && body.top_candidates) || [];
    if (!cands.length) { box.classList.add("hidden"); box.innerHTML = ""; return; }
    const pct = (v) => (v == null ? "–" : `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`);
    // Claudio 4H: the most solid and the most profitable, with how
    // much of the return the neighbouring settings keep.
    const KIND = { solid: "Most solid", profitable: "Most profitable", "solid+profitable": "Most solid and most profitable" };
    const kinds = cands.some((c) => c.kind);
    const held = cands.some((c) => c.verification && c.verification.unseen);
    box.innerHTML = `<div class="lab-best2-title">${kinds ? "Most solid · most profitable" : `Best ${cands.length === 1 ? "result" : "two results"}`} · ${held ? "chosen without the last 12 months, then tested on them" : "whole chart, ranked by simple profit"}</div>`
      + (kinds && body.data_used && body.data_used.note ? `<div class="lab-best2-note">${escapeHtml(body.data_used.note)} ${body.trials_evaluated ? `${body.trials_evaluated} combinations backtested.` : ""}</div>` : "")
      + cands.map((c, i) => `
      <div class="lab-best2-card${i === 0 ? " active" : ""}" data-i="${i}">
        <div class="lab-best2-rank">${kinds ? (c.kind === "profitable" ? "↑" : "◆") : `#${c.rank}`}</div>
        <div class="lab-best2-main">
          ${kinds ? `<div class="lab-best2-kind">${KIND[c.kind] || c.kind}</div>` : ""}
          <div class="lab-best2-levels">${c.params.cl_rsi_os != null
            ? `RSI &lt; ${c.params.cl_rsi_os} · BB ×${Number(c.params.cl_bb_mult).toFixed(1)} · stop ${Number(c.params.cl_atr_stop).toFixed(2)}×ATR`
            : `OS ${c.params.rsi_oversold} · OB ${c.params.rsi_overbought}${kinds ? ` · BB ×${Number(c.params.bb_mult).toFixed(1)}` : ""}`}</div>
          ${fourFigures({ simple: c.simple_return_pct, compounded: c.total_return_pct, simpleDd: c.simple_max_drawdown_pct, dd: c.max_drawdown_pct })}
          <div class="lab-best2-meta">${c.num_trades} trades${c.win_rate_pct != null ? ` · win ${c.win_rate_pct.toFixed(0)}%` : ""} · ${perTrade({ avg: c.avg_trade_pct, median: c.median_trade_pct })}</div>
          ${c.solidity != null ? `<div class="lab-best2-meta">Solidity <b>${Math.round(c.solidity * 100)}%</b>${c.neighbours ? ` · ×${(Number(c.params.bb_mult) - 0.1).toFixed(1)}: ${pct(c.neighbours.mult_down)} · ×${(Number(c.params.bb_mult) + 0.1).toFixed(1)}: ${pct(c.neighbours.mult_up)}` : ""}</div>` : ""}
          ${c.history ? detailTable(c) : verifyLine(c.verification)}
        </div>
        <button type="button" class="lab-best2-use">${i === 0 ? "In use" : "Use"}</button>
      </div>`).join("");
    box.classList.remove("hidden");
    box.querySelectorAll(".lab-best2-card").forEach((card) => {
      card.querySelector(".lab-best2-use").addEventListener("click", () => {
        const c = cands[Number(card.dataset.i)];
        const container = labEl("lab-params-fields");
        Object.entries(c.params).forEach(([key, value]) => {
          const input = container.querySelector(`[name="${key}"]`);
          if (input) input.value = value;
        });
        labState.paramsDirty = true;
        box.querySelectorAll(".lab-best2-card").forEach((x) => {
          const on = x === card;
          x.classList.toggle("active", on);
          x.querySelector(".lab-best2-use").textContent = on ? "In use" : "Use";
        });
        labState.keepBest2 = true;
        runLabBacktest();
      });
    });
  }

  function renderPlateauMap(body) {
    const box = labEl("lab-plateau-box");
    if (!box) return;
    const cands = (body && body.top_candidates) || [];
    if (cands.length < 3) { box.classList.add("hidden"); box.innerHTML = ""; return; }

    // Gli assi sono i due parametri numerici che cambiano davvero: mostrare
    // un parametro costante sprecherebbe meta' della mappa.
    const keys = Object.keys(cands[0].params || {}).filter((k) => {
      const vals = cands.map((c) => c.params[k]);
      return vals.every((v) => typeof v === "number") && new Set(vals).size > 1;
    });
    if (keys.length < 2) { box.classList.add("hidden"); box.innerHTML = ""; return; }

    const spread = (k) => {
      const vals = cands.map((c) => c.params[k]);
      return (Math.max(...vals) - Math.min(...vals)) / (Math.abs(Math.max(...vals)) || 1);
    };
    const [kx, ky] = keys.sort((a, b) => spread(b) - spread(a)).slice(0, 2);

    const xs = cands.map((c) => c.params[kx]);
    const ys = cands.map((c) => c.params[ky]);
    const scores = cands.map((c) => c.score);
    const xMin = Math.min(...xs), xMax = Math.max(...xs);
    const yMin = Math.min(...ys), yMax = Math.max(...ys);
    const sMin = Math.min(...scores), sMax = Math.max(...scores);
    const norm = (v, lo, hi) => (hi === lo ? 0.5 : (v - lo) / (hi - lo));

    const W = 300, H = 210, padL = 40, padB = 30, padT = 12, padR = 12;
    const px = (v) => padL + norm(v, xMin, xMax) * (W - padL - padR);
    const py = (v) => H - padB - norm(v, yMin, yMax) * (H - padT - padB);

    const dots = cands.map((c) => {
      const t = norm(c.score, sMin, sMax);
      const r = 5 + t * 6;
      const best = c.rank === 1;
      const fill = `color-mix(in srgb, var(--accent) ${Math.round(18 + t * 72)}%, var(--bg-sunk))`;
      return `<g>
        <circle cx="${px(c.params[kx]).toFixed(1)}" cy="${py(c.params[ky]).toFixed(1)}" r="${r.toFixed(1)}"
          fill="${fill}" stroke="${best ? "var(--accent)" : "var(--border-strong)"}" stroke-width="${best ? 2 : 1}">
          <title>#${c.rank} · score ${c.score.toFixed(2)} · ${kx}=${c.params[kx]} ${ky}=${c.params[ky]} · rend. ${c.total_return_pct.toFixed(1)}% · DD ${c.max_drawdown_pct.toFixed(1)}%</title>
        </circle>
        ${best ? `<text x="${px(c.params[kx]).toFixed(1)}" y="${(py(c.params[ky]) + 3.5).toFixed(1)}" text-anchor="middle" font-size="9" fill="var(--accent-ink)">◆</text>` : ""}
      </g>`;
    }).join("");

    // Quanto e' isolato il vincitore: la stessa domanda che la ricerca
    // stabile si pone, scritta in una riga.
    const best = cands.find((c) => c.rank === 1) || cands[0];
    const near = cands.filter((c) => c !== best && c.score >= best.score * 0.9).length;
    const verdict = near >= 3
      ? `<b class="bull">${near} neighbors</b> within 10% of the best: the area holds.`
      : near >= 1
      ? `<b class="warnc">only ${near}</b> within 10% of the best: narrow area.`
      : `<b class="bear">no neighbors</b> within 10%: the best is isolated, unlikely to repeat.`;
    const badge = near >= 3
      ? `<span class="plateau-badge plateau-badge-bull">Stable plateau</span>`
      : near >= 1
      ? `<span class="plateau-badge plateau-badge-warn">Narrow area</span>`
      : `<span class="plateau-badge plateau-badge-bear">Isolated</span>`;

    box.classList.remove("hidden");
    box.innerHTML = `
      <div class="plateau-head">
        <span class="section-eyebrow">Candidate map</span>
        ${badge}
        <span class="section-count">${cands.length} shortlisted</span>
      </div>
      <svg class="plateau-svg" viewBox="0 0 ${W} ${H}" width="100%" role="img"
           aria-label="Scatter of the top candidates on ${kx} and ${ky}">
        <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${H - padB}" stroke="var(--border)"/>
        <line x1="${padL}" y1="${H - padB}" x2="${W - padR}" y2="${H - padB}" stroke="var(--border)"/>
        <text x="${padL - 6}" y="${padT + 8}" text-anchor="end" font-size="9" fill="var(--ink-faint)" font-family="var(--font-mono)">${yMax}</text>
        <text x="${padL - 6}" y="${H - padB}" text-anchor="end" font-size="9" fill="var(--ink-faint)" font-family="var(--font-mono)">${yMin}</text>
        <text x="${padL}" y="${H - padB + 13}" font-size="9" fill="var(--ink-faint)" font-family="var(--font-mono)">${xMin}</text>
        <text x="${W - padR}" y="${H - padB + 13}" text-anchor="end" font-size="9" fill="var(--ink-faint)" font-family="var(--font-mono)">${xMax}</text>
        <text x="${W / 2}" y="${H - 3}" text-anchor="middle" font-size="9" fill="var(--ink-dim)" font-family="var(--font-mono)">${kx}</text>
        <text x="10" y="${H / 2}" font-size="9" fill="var(--ink-dim)" font-family="var(--font-mono)" transform="rotate(-90 10 ${H / 2})" text-anchor="middle">${ky}</text>
        ${dots}
      </svg>
      <p class="plateau-note">${verdict} The largest, brightest circle is the top score; <b>◆</b> is the chosen configuration.</p>`;
  }

  function renderLabResults(bt) {
    labState.lastBt = bt;
    const pct = bt.total_return_pct;
    const isPos = pct >= 0;
    const retEl = labEl("lab-return-val");
    retEl.innerHTML = fourFigures({ simple: bt.simple_return_pct, compounded: pct,
                                    simpleDd: bt.simple_max_drawdown_pct, dd: bt.max_drawdown_pct });
    retEl.className = "lab-return-four";

    const finalEquity = bt.equity_curve.length ? bt.equity_curve[bt.equity_curve.length - 1][1] : 0;
    const initCap = parseFloat(labEl("lab-initial-capital").value) || 1000;
    const sideEl = labEl("lab-return-side");
    // 15/10 (Lorenzo): the simple final equity too, as visible as the other
    const cap0 = bt.initial_capital || initCap;
    const simpleEq = bt.simple_return_pct != null ? cap0 * (1 + bt.simple_return_pct / 100) : null;
    const money = (v) => `${Math.round(v).toLocaleString("en-US")} $`;
    sideEl.innerHTML = `<div class="lab-eq-row"><span>final equity · simple</span><b class="${simpleEq != null && simpleEq < cap0 ? "neg" : ""}">${simpleEq != null ? money(simpleEq) : "–"}</b></div>`
      + `<div class="lab-eq-row"><span>final equity · compounded</span><b class="${isPos ? "" : "neg"}">${money(finalEquity)}</b></div>`
      + `<div class="lab-eq-from">from ${cap0.toLocaleString("en-US")} $</div>`;

    const pf = bt.profit_factor !== null ? bt.profit_factor.toFixed(2) : "∞";
    const wr = bt.win_rate_pct !== null ? bt.win_rate_pct.toFixed(0) + "%" : "—";
    const dd = "-" + Math.abs(bt.max_drawdown_pct).toFixed(1) + "%";
    const sharpe = bt.sharpe_ratio != null ? bt.sharpe_ratio.toFixed(2) : null;
    const consec = bt.max_consecutive_losses != null ? bt.max_consecutive_losses : null;

    // Date range from backend
    const fmtDate = (ms) => ms ? new Date(ms).toLocaleDateString("en-US", { month: "short", year: "numeric" }) : null;
    const ds = fmtDate(bt.data_start);
    const de = fmtDate(bt.data_end);
    const dateRange = ds && de ? ` · <span class="meta-dates">${ds} → ${de}</span>` : "";

    // Quale ipotesi di esecuzione ha prodotto questi numeri va detto accanto ai
    // numeri, non sepolto in un pannello di impostazioni: due rendimenti
    // ottenuti con ipotesi diverse non sono confrontabili fra loro.
    const fillAt = bt.fill_at || "signal_close";
    const fillTag = fillAt === "next_open"
      ? ' · <span class="fill-tag fill-real" title="Entries and exits filled at the open of the candle after the signal: the price you can actually get.">next open</span>'
      : fillAt === "on_condition"
      ? ` · <span class="fill-tag fill-real" title="Filled where the condition first turns true inside the signal candle, replaying the candle along open → low → high → close (green) or open → high → low → close (red), as TradingView does.${bt.intrabar_fills != null ? ` ${bt.intrabar_fills} signals filled inside the candle, the rest at the close.` : ""}">on condition</span>`
      : ' · <span class="fill-tag fill-real" title="Entries and exits filled at the close of the signal candle: the same moment the live alert fires.">candle close</span>';

    labEl("lab-result-meta").innerHTML = `<button type="button" class="lab-trades-link">${bt.num_trades} trades</button> · ${bt.interval || labState.tf}${dateRange}${fillTag}`;

    // 3-chip base row + optional Sharpe chip
    let chipsHtml = `
      <div><div class="chip-lbl">Win rate</div><div class="chip-val ${bt.win_rate_pct >= 50 ? "pos" : "neg"}">${wr}</div></div>
      <div><div class="chip-lbl">Prof. factor</div><div class="chip-val" title="How much the winning trades make compared to what the losing ones lose: above 1 means the system is profitable overall.">${pf}</div></div>`;
    if (sharpe !== null) chipsHtml += `<div><div class="chip-lbl">Sharpe</div><div class="chip-val ${parseFloat(sharpe) >= 1 ? "pos" : ""}" title="Return relative to the risk taken: above 1 is considered good, below 0 means losing while taking risk.">${sharpe}</div></div>`;
    if (consec !== null) chipsHtml += `<div><div class="chip-lbl">Max loss streak</div><div class="chip-val neg">${consec}</div></div>`;
    if (bt.avg_trade_pct != null) chipsHtml += `<div><div class="chip-lbl">Avg / median trade</div><div class="chip-val" title="Net % of a single trade on its position: the mean, and the typical one. A mean far above the median means a few exceptional trades carry the result.">${bt.avg_trade_pct >= 0 ? "+" : ""}${bt.avg_trade_pct.toFixed(2)}% / ${bt.median_trade_pct >= 0 ? "+" : ""}${bt.median_trade_pct.toFixed(2)}%</div></div>`;
    labEl("lab-stat-chips").innerHTML = chipsHtml;
    labEl("lab-result-block").classList.remove("hidden");
    drawLabEquityCanvas(bt.equity_curve);

    // Apply strip
    const chartSymbol = state.data ? state.data.symbol : null;
    const applyText = labEl("lab-apply-text");
    if (chartSymbol && chartSymbol !== labState.symbol) {
      applyText.innerHTML = `The chart shows <b>${chartSymbol}</b> — applying will switch to <b>${labState.symbol}</b> with the test's entries/exits.`;
    } else {
      applyText.innerHTML = `Apply the <b>${labState.symbol}</b> results to the chart (the test's entries/exits).`;
    }
    labEl("lab-apply-strip").classList.remove("hidden");

    // Wire "N trade" button to open the trade detail drawer
    const tradeLink = labEl("lab-result-meta").querySelector(".lab-trades-link");
    if (tradeLink) {
      tradeLink.addEventListener("click", () => openLabTradesDrawer(bt));
    }
  }

  function openLabTradesDrawer(bt) {
    const drawer = el("lab-trades-drawer");
    const body = el("lab-trades-body");
    const oosTrades = bt.oos_trades || [];
    const isTrades = bt.trades || [];
    const totalCount = isTrades.length + oosTrades.length;
    el("lab-trades-title").textContent = oosTrades.length
      ? `${isTrades.length} IS trades + ${oosTrades.length} OOS`
      : `${bt.num_trades} trades`;

    // 15/10 (Lorenzo): shorter dates, prices with at most two decimals, and
    // the simple figures next to the compounded ones. Prices under 1 keep
    // four significant digits (two decimals would read 0.00 on PEPE); the
    // hour goes under the date on intraday timeframes.
    const intraday = /^(\d+)(m|h)$/.test(String(bt.interval || ""));
    const fmtTs = (s) => {
      const d = new Date(s * 1000);
      const day = d.toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "2-digit" });
      return intraday
        ? `${day}<br><small>${d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}</small>`
        : day;
    };
    const fmtPrice = (p) => (Math.abs(p) >= 1
      ? p.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : Number(p.toPrecision(4)).toString());
    const fmtMoney = (v) => v.toLocaleString("en-US", { maximumFractionDigits: 0 });
    const sgn = (v) => (v >= 0 ? "+" : "");
    const q = (bt.position_pct != null ? bt.position_pct : 100) / 100;
    const stake = (bt.initial_capital || 0) * q;
    let simpleCum = 0;

    const renderRow = (t, i, isOos) => {
      const isWin = t.pnl_abs > 0;
      const dir = t.direction === "long" ? "▲ L" : "▼ S";
      const dirClass = t.direction === "long" ? "bull" : "bear";
      const pnlClass = isWin ? "pos" : "neg";
      const rowClass = isOos ? ' class="oos-row"' : "";
      const numLabel = isOos ? `<span class="oos-badge">OOS</span>${i + 1}` : i + 1;
      // net % of the trade on its position: the same for both columns
      const before = t.equity_after - t.pnl_abs;
      const net = before * q > 0 ? (t.pnl_abs / (before * q)) * 100 : t.pnl_pct;
      const simple = stake * net / 100;
      simpleCum += simple;
      return `<tr${rowClass}>
        <td class="td-num">${numLabel}</td>
        <td class="td-dir ${dirClass}">${dir}</td>
        <td class="td-date">${fmtTs(t.entry_time)}</td>
        <td class="td-date">${fmtTs(t.exit_time)}</td>
        <td class="td-price">${fmtPrice(t.entry_price)}</td>
        <td class="td-price">${fmtPrice(t.exit_price)}</td>
        <td class="td-pnl ${pnlClass}">${sgn(net)}${net.toFixed(2)}%</td>
        <td class="td-pnl td-grp ${pnlClass}">${sgn(simple)}${fmtMoney(simple)}</td>
        <td class="td-equity">${fmtMoney((bt.initial_capital || 0) + simpleCum)}</td>
        <td class="td-pnl td-grp ${pnlClass}">${sgn(t.pnl_abs)}${fmtMoney(t.pnl_abs)}</td>
        <td class="td-equity">${fmtMoney(t.equity_after)}</td>
      </tr>`;
    };

    let html = `<table class="lab-trades-table">
      <thead>
      <tr class="th-groups"><th colspan="7"></th><th colspan="2" class="td-grp" title="Every trade on the same stake (${fmtMoney(stake)} $), gains not reinvested">Simple</th><th colspan="2" class="td-grp" title="Every trade reinvests all the equity so far">Compounded</th></tr>
      <tr>
        <th>#</th><th>Dir</th><th>Entry</th><th>Exit</th>
        <th>Entry $</th><th>Exit $</th><th title="Net % of the trade on its position, fees included">Trade %</th>
        <th class="td-grp">P&amp;L $</th><th>Capital</th><th class="td-grp">P&amp;L $</th><th>Equity</th>
      </tr></thead><tbody>`;

    if (!isTrades.length && !oosTrades.length) {
      html += `<tr><td colspan="11" style="text-align:center;padding:16px;color:var(--ink-dim)">No trades</td></tr>`;
    } else {
      isTrades.forEach((t, i) => { html += renderRow(t, i, false); });
      if (oosTrades.length) {
        html += `<tr class="oos-separator"><td colspan="11">— Out-of-sample (${oosTrades.length} trades) — data not used in optimization</td></tr>`;
        oosTrades.forEach((t, i) => { html += renderRow(t, i, true); });
      }
    }

    html += `</tbody></table>`;
    body.innerHTML = html;
    drawer.classList.remove("hidden");
  }

  el("lab-trades-export").addEventListener("click", () => {
    // Il file lo costruisce il server rieseguendo il backtest sugli stessi
    // parametri: cosi' i numeri del foglio sono misurati, non riportati da qui.
    // Basta un link — nessun fetch, nessun blob: il browser scarica e la pagina
    // resta dov'e'.
    const params = buildLabQuery();
    const link = document.createElement("a");
    link.href = `/api/export/backtest.xlsx?${params.toString()}`;
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    link.remove();
  });

  el("lab-trades-close").addEventListener("click", () => {
    el("lab-trades-drawer").classList.add("hidden");
  });

  // Every run starts from an empty result column (segnalazione e67ae945):
  // a previous backtest's numbers or a previous optimization's boxes left on
  // screen read as part of the new result.
  function clearLabResults() {
    labState.lastBt = null;
    // The two best of a max-return search stay while one of them is being run.
    if (!labState.keepBest2) labEl("lab-best2-box")?.classList.add("hidden");
    labState.keepBest2 = false;
    ["lab-result-block", "lab-apply-strip", "lab-plateau-box", "lab-data-used",
      "lab-regime-box", "lab-branch-box", "lab-signal-status"].forEach((id) => {
      const node = labEl(id);
      if (node) node.classList.add("hidden");
    });
    ["lab-result-meta", "lab-stat-chips", "lab-return-side"].forEach((id) => {
      const node = labEl(id);
      if (node) node.innerHTML = "";
    });
    const ret = labEl("lab-return-val");
    if (ret) ret.textContent = "";
    const canvas = labEl("lab-equity-canvas");
    if (canvas && canvas.getContext) canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
    const drawer = el("lab-trades-drawer");
    if (drawer) drawer.classList.add("hidden");
  }

  async function runLabBacktest() {
    if (!labState.symbol) {
      labEl("lab-status").textContent = "Enter a ticker first.";
      labEl("lab-status").classList.remove("hidden");
      return;
    }
    const seq = ++labState.seq;
    const runBtn = labEl("lab-run-btn");
    const optBtn = labEl("lab-optimize-btn");
    optBtn.disabled = true;
    clearLabResults();
    labEl("lab-status").textContent = "Backtest running… (may take a few seconds)";
    labEl("lab-status").classList.remove("hidden");
    await withAsyncButton(runBtn, async () => {
      const params = buildLabQuery();
      const resp = await fetch(`/api/backtest/deep?${params.toString()}`);
      if (seq !== labState.seq) return;
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : `Error ${resp.status}`);
      }
      const bt = await resp.json();
      labEl("lab-status").classList.add("hidden");
      renderLabResults(bt);
    }).catch((err) => {
      if (seq !== labState.seq) return;
      labEl("lab-status").textContent = "Error: " + (err.message || "backtest failed.");
    }).finally(() => { optBtn.disabled = false; });
  }

  async function runLabOptimize() {
    if (!labState.symbol) {
      labEl("lab-status").textContent = "Enter a ticker first.";
      labEl("lab-status").classList.remove("hidden");
      return;
    }
    if (!OPTIMIZABLE_STRATEGIES.has(labState.strategy)) {
      labEl("lab-status").textContent = "This strategy doesn't support automatic optimization.";
      labEl("lab-status").classList.remove("hidden");
      return;
    }
    const optMode = labOptMode();
    clearLabResults();
    labEl("lab-status").textContent = "Avvio…";
    labEl("lab-status").classList.remove("hidden");

    const params = buildLabQuery();
    if (optMode !== "random") params.set("mode", optMode);
    applyLabFilters(params);
    try {
      const resp = await fetch(`/api/optimize/start?${params.toString()}`, { method: "POST" });
      const started = await readJson(resp);
      if (!resp.ok) {
        throw new Error(typeof started.detail === "string" ? started.detail : `Error ${resp.status}`);
      }
      const symbol = labState.symbol;
      optJobs.set(started.job_id, {
        id: started.job_id,
        symbol,
        displaySymbol: labState.displaySymbol,
        assetType: labState.assetType,
        exchange: labState.exchange,
        strategy: labState.strategy,
        mode: optMode,
        title: optMode === "plateau" ? "Stable search running" : optMode === "max_return" ? "Max return search running" : "Optimizing",
        sub: `${labState.displaySymbol || symbol} · ${strategyLabel(labState.strategy)}`,
        state: "in corso",
        elapsed: 0,
        log: [],
        seen: 0,
        seenDone: false,
      });
      openOptProgress(started.job_id);
      startOptPolling();
      // Il pulsante torna subito disponibile: il lavoro e' sul server, quindi
      // niente vieta di lanciarne un altro mentre questo continua.
      labEl("lab-status").textContent =
        "Running on the server. You can close the window or start another one.";
    } catch (err) {
      labEl("lab-status").textContent = "Optimization error: " + (err.message || "");
    }
  }

  // Lab ticker autocomplete
  const labSuggest = makeSuggestController({
    listId: "lab-suggestions",
    anchorId: "lab-ticker-hero",
    elFn: labEl,
    fetchItems: async (query) => {
      const resp = await fetch(`/api/symbols?query=${encodeURIComponent(query)}`);
      return resp.ok ? await resp.json() : [];
    },
    onSelect: selectLabSuggestion,
  });
  let labSuggestTimer = null;

  // The exchange to send for the Lab's pair: a DEX pool has none, and the
  // backend only takes one of the four exchanges there (it ignores it).
  const labExchange = () => (labState.assetType === "dex" ? "mexc" : labState.exchange || "mexc");

  function selectLabSuggestion(item) {
    labState.symbol = item.symbol;
    labState.displaySymbol = item.symbol.replace(/USDT$|USD$|BTC$/, "") || item.symbol;
    labState.assetType = item.asset_type || "crypto";
    labState.exchange = item.provider || "mexc";
    labState.baseTokenAddress = item.base_token_address || null;
    labSuggest.resolved = item;
    labEl("lab-ticker-val").textContent = shortSymbol(item.symbol);
    labEl("lab-ticker-input").value = "";
    labEl("lab-ticker-input").blur();
    labEl("lab-suggestions").classList.add("hidden");
    // Sync exchange selector to match the result's provider — solo se il
    // menu offre davvero quel valore: assegnare un value senza <option>
    // corrispondente lascia il <select> silenziosamente vuoto (segnalato da
    // l'utente su CRVUSDT/Binance: "exchange: valore non ammesso, campo
    // vuoto" — il menu non aveva ancora Binance fra le opzioni).
    const sel = el("lab-exchange-select");
    if (sel && item.provider && [...sel.options].some((o) => o.value === item.provider)) {
      sel.value = item.provider;
    }
  }

  // "DEX" in the exchange menu (segnalazione 1f9baaea): the same ticker,
  // read from its best on-chain pool (DexScreener search, most liquid first),
  // so a token listed on no exchange can be backtested and get alerts.
  async function switchLabToDex(sel) {
    const base = (labState.displaySymbol || labState.symbol || "").split("@")[0].replace(/USDT$|USDC$|USD$/, "");
    if (!base) return;
    const status = labEl("lab-status");
    status.textContent = `Looking for ${base} on DEX…`;
    status.classList.remove("hidden");
    try {
      const resp = await fetch(`/api/symbols?query=${encodeURIComponent(base)}`);
      const items = resp.ok ? await resp.json() : [];
      // Same ticker only: another token's pool would be a different backtest.
      const hit = items.find((i) => i.asset_type === "dex" && i.symbol.split("@")[0].toUpperCase() === base.toUpperCase());
      if (!hit) {
        status.textContent = `${base} not found on DEX.`;
        sel.value = labState.exchange || "mexc";
        return;
      }
      selectLabSuggestion(hit);
      status.textContent = `${hit.name} · ${hit.exchange}`;
    } catch {
      status.textContent = "DEX search failed.";
      sel.value = labState.exchange || "mexc";
    }
  }

  function bindLabUI() {
    el("lab-exchange-select")?.addEventListener("change", (ev) => {
      const sel = ev.target;
      if (sel.value === "dexscreener") {
        if (labState.assetType !== "dex") switchLabToDex(sel);
        return;
      }
      if (labState.assetType === "dex") {
        // Back to an exchange: the plain ticker, quoted in USDT.
        const base = (labState.symbol || "").split("@")[0].toUpperCase();
        labState.assetType = "crypto";
        labState.baseTokenAddress = null;
        labState.symbol = base ? base + "USDT" : labState.symbol;
        labState.displaySymbol = base || labState.displaySymbol;
        labEl("lab-ticker-val").textContent = shortSymbol(labState.symbol) || "—";
      }
      labState.exchange = sel.value;
    });
    const input = labEl("lab-ticker-input");
    const hero = labEl("lab-ticker-hero");

    // Show input on hero click
    hero.addEventListener("click", () => { input.focus(); });
    input.addEventListener("focus", () => {
      input.style.opacity = "1";
      input.style.background = "var(--bg-panel)";
      input.style.zIndex = "2";
    });
    input.addEventListener("blur", () => {
      setTimeout(() => {
        input.style.opacity = "0";
        labEl("lab-suggestions").classList.add("hidden");
      }, 150);
    });
    input.addEventListener("input", () => {
      clearTimeout(labSuggestTimer);
      const q = input.value.trim();
      if (q.length < 1) { labSuggest.clear(); return; }
      labSuggestTimer = setTimeout(() => labSuggest.fetch(q), 200);
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const typed = input.value.trim().toUpperCase().replace(/\//g, "");
        if (typed && !labSuggest.resolved) {
          // Accept the typed symbol directly — normalise to XXXUSDT if no quote
          const sym = /USDT$|USD$|BTC$|ETH$|USDC$/.test(typed) ? typed : typed + "USDT";
          labState.symbol = sym;
          labState.displaySymbol = sym.replace(/USDT$|USD$|BTC$/, "") || sym;
          labState.assetType = "crypto";
          labState.exchange = "mexc";
          labEl("lab-ticker-val").textContent = sym;
          input.value = "";
          input.blur();
          labEl("lab-suggestions").classList.add("hidden");
        } else {
          labSuggest.handleKey(e);
        }
        return;
      }
      labSuggest.resolved = null;
      labSuggest.handleKey(e);
    });

    // Timeframe pills
    const LAB_TF_ORDER = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "2d", "3d", "5d", "1w", "1M"];

    labEl("lab-tf-row").addEventListener("click", (e) => {
      const btn = e.target.closest(".lab-tf-btn");
      if (!btn) return;
      labEl("lab-tf-row").querySelectorAll(".lab-tf-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      labState.tf = btn.dataset.labTf;
    });

    // Periodo di riferimento del backtest, facoltativo
    labEl("lab-daterange-clear").addEventListener("click", () => {
      labEl("lab-date-start").value = "";
      labEl("lab-date-end").value = "";
    });

    // Values typed in the Lab are the Lab's own (see syncLabFromChart).
    ["input", "change"].forEach((ev) => labEl("lab-params-fields")?.addEventListener(ev, () => {
      labState.paramsDirty = true;
    }));

    // Strategy select — keep toolbar in sync so chart markers match the lab
    labEl("lab-strategy-select").addEventListener("change", () => {
      labState.strategy = labEl("lab-strategy-select").value;
      renderLabParamFields();
      const toolbarSel = el("active-strategy-select");
      if (toolbarSel && toolbarSel.value !== labState.strategy) {
        toolbarSel.value = labState.strategy;
        renderStrategyParamsFields();
        if (state.data) runAnalysis(state.data.symbol);
      }
    });

    labEl("lab-run-btn").addEventListener("click", runLabBacktest);
    // Two ways for the alert to fire (segnalazione 8bd7884c), and since
    // 316219de two different fills in the backtest too.
    labEl("lab-fill-at")?.addEventListener("change", (ev) => {
      const hint = labEl("lab-fill-hint");
      if (hint) hint.textContent = ev.target.value === "on_condition"
        ? "The alert fires as soon as the condition is met on the forming candle. The backtest replays each signal candle (open → low → high → close if green, open → high → low → close if red) and fills at the first price where the condition is true. Signals that appear and then vanish before the close are not in the backtest."
        : "The alert fires when the timeframe candle closes; the backtest fills at that close.";
    });
    labEl("lab-optimize-btn").addEventListener("click", runLabOptimize);

    labEl("lab-apply-btn").addEventListener("click", () => {
      if (!labState.symbol || !labState.lastBt) return;
      // Tutta la configurazione, non solo il pair: prima il grafico prendeva
      // il ticker del laboratorio ma restava sul proprio timeframe e sulla
      // propria strategia, con i propri parametri. I trade disegnati erano
      // quelli di un'altra cosa.
      applyConfigToChart({
        assetType: labState.assetType,
        exchange: labExch,
        symbol: labState.symbol,
        displaySymbol: labState.displaySymbol,
        interval: labState.tf,
        strategyName: labState.strategy,
        params: collectStrategyParams(labEl("lab-params-fields"), labState.strategy),
        backtestParams: labBacktestParams(),
      });
      runAnalysis(labState.symbol);
      // Switch to Backtest tab so user sees the matching result
      document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === "backtest"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.toggle("active", c.dataset.tabContent === "backtest"));
    });

    labEl("lab-signal-btn").addEventListener("click", async () => {
      const statusEl = el("lab-signal-status");
      const btn = labEl("lab-signal-btn");
      if (!labState.symbol || !labState.lastBt) return;

      const show = (msg, isError) => {
        statusEl.textContent = msg;
        statusEl.className = "lab-signal-status" + (isError ? " error" : " ok");
        statusEl.classList.remove("hidden");
      };

      btn.disabled = true;
      const prevText = btn.textContent;
      btn.textContent = "…";

      const labOnClose = labEl("lab-fill-at")?.value !== "on_condition";
      try {
        // 1. Add (or upsert) the ticker to watchlist
        const addResp = await fetch("/api/watchlist", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            symbol: labState.symbol,
            asset_type: labState.assetType,
            exchange: labExchange(),
            interval: labState.tf,
            on_close: labOnClose,
            base_token_address: labState.baseTokenAddress || null,
          }),
        });

        if (addResp.status === 401) {
          show("Log in to activate signals.", true);
          btn.disabled = false; btn.textContent = prevText; return;
        }
        if (!addResp.ok) {
          const err = await addResp.json().catch(() => ({}));
          show("Error: " + (err.detail || addResp.status), true);
          btn.disabled = false; btn.textContent = prevText; return;
        }
        const entry = await addResp.json();
        // A ticker already in the watchlist keeps its old setting on add.
        if (entry.on_close !== labOnClose) {
          await fetch(`/api/watchlist/${entry.id}/on_close`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ on_close: labOnClose }),
          });
        }

        // 2. I parametri trovati dal laboratorio PRIMA di accendere. Accendere
        // scatta la fotografia che finisce in archivio: fatta prima, quella
        // fotografia registra i parametri di default e resta a dire che
        // l'alert e' partito con la configurazione non ottimizzata — cioe'
        // l'archivio racconta una cosa diversa da quella che sta girando.
        const labParams = collectStrategyParams(labEl("lab-params-fields"), labState.strategy);
        if (Object.keys(labParams).length > 0) {
          const paramsResp = await fetch(`/api/watchlist/${entry.id}/strategy_params`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ strategy_name: labState.strategy, params: labParams }),
          });
          if (!paramsResp.ok) {
            const err = await paramsResp.json().catch(() => ({}));
            show("Parameters not saved: " + (err.detail || paramsResp.status), true);
            btn.disabled = false; btn.textContent = prevText; return;
          }
        }

        // 3. Ora si accende, con i parametri gia' al loro posto
        const stratResp = await fetch(`/api/watchlist/${entry.id}/strategy`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ strategy_name: labState.strategy, enabled: true }),
        });
        if (!stratResp.ok) {
          const err = await stratResp.json().catch(() => ({}));
          show("Strategy not activated: " + (err.detail || stratResp.status), true);
          btn.disabled = false; btn.textContent = prevText; return;
        }
        loadWatchlist();
        loadArchive();

        show(`✅ Signals active for ${labState.symbol} (${labState.tf}) — ${strategyLabel(labState.strategy)}`, false);
        btn.textContent = "✅ Active";
      } catch (err) {
        show("Network error: " + err.message, true);
        btn.disabled = false; btn.textContent = prevText;
      }
    });
  }

  // ── BTC badge in the top bar (Lorenzo, 16/10): BTC against its weekly
  // EMA 21 (BTC filter), closed weeks only (the Bull Market Band part went
  // with the RSI+BB BTC band strategy), with the Monday each verdict took effect. Hourly refresh.
  async function renderBtcBadge() {
    const badge = el("btc-badge");
    if (!badge) return;
    let st = null;
    try {
      const r = await fetch("/api/btc-regime");
      if (r.ok) st = await r.json();
    } catch { st = null; }
    if (!st || !st.loaded) { badge.classList.add("hidden"); return; }
    const part = (s, name, upText, downText) => {
      if (!s) return "";
      const cls = s.up ? "up" : "down";
      const title = `BTC ${s.up ? "above" : "below"} its ${name} since ${s.since}: ${s.up ? upText : downText}`;
      return `<span class="btc-badge-part ${cls}" title="${escapeHtml(title)}">${escapeHtml(name === "weekly EMA 21" ? "EMA21" : "Band")} ${s.up ? "▲" : "▼"}</span>`;
    };
    badge.innerHTML = `<span class="btc-badge-label">BTC</span>` +
      part(st.ema21, "weekly EMA 21", "the BTC filter lets longs in.", "the BTC filter blocks new longs.");
    badge.classList.remove("hidden");
  }

  function initLabState(strategies) {
    // Pick the first available strategy
    labState.strategy = strategies[0] || "";
    const sel = labEl("lab-strategy-select");
    sel.innerHTML = strategyOptionsHtml(strategies);
    if (state.defaultStrategy && strategies.includes(state.defaultStrategy)) sel.value = state.defaultStrategy;
    labState.strategy = sel.value;
    renderLabParamFields();
    // Default ticker same as chart
    labState.symbol = "BTCUSDT";
    labState.displaySymbol = "BTC";
    labEl("lab-ticker-val").textContent = "BTCUSDT";
  }

  document.addEventListener("DOMContentLoaded", async () => {
    populateIntervalSelects();
    buildMobileTfWheel();
    try {
      // Se la libreria del grafico non si carica (CDN irraggiungibile,
      // rete dell'utente, disservizio) initCharts() lanciava un'eccezione
      // non gestita qui, e da un handler async una throw non catturata
      // fermava tutto cio' che veniva dopo — bindUI, bindLabUI, la ricerca
      // ticker, ogni form — con nessun errore visibile: sembrava che il
      // sito "non trovasse piu' i pair" ovunque, quando in realta' nessun
      // listener si era mai agganciato. Isolato qui: un grafico che non
      // parte resta un problema del grafico, non di tutto il resto.
      initCharts();
    } catch (err) {
      console.error("initCharts() failed — the chart may not work, the rest of the app does, continuing:", err);
    }
    bindUI();
    bindLabUI();
    bindMobileNav();

  labSync = { fromChart: () => syncLabFromChart(), toChart: () => syncChartFromLab() };

  // The Lab's own values win over the chart's while the user is working in
  // the Lab. Before, every return to the Lab (from Alert, the Archive, the
  // phone's menu) copied the chart's parameters back over the ones typed in
  // the Lab — and the chart had the defaults, because choosing the strategy
  // in the Lab resets the chart's fields — so Archive saved the defaults
  // (Lorenzo, 13/10: "le strategie testate con valori scritti a mano [...]
  // vengono salvate con i valori di default"). `paramsDirty` = the Lab holds
  // values the chart does not have: typed, or filled by an optimization.
  function syncLabFromChart() {
    if (!state.data || !state.data.symbol) return;
    const chartStrat = el("active-strategy-select")?.value;
    if (labState.paramsDirty && labState.symbol === state.data.symbol && labState.strategy === chartStrat) return;
    labState.paramsDirty = false;
    const sym = state.data.symbol;
    if (labState.symbol !== sym) {
      labState.symbol = sym;
      labState.displaySymbol = sym.replace(/USDT$|USD$|BTC$|ETH$/, "") || sym;
      const val = el("lab-ticker-val");
      if (val) val.textContent = shortSymbol(sym);
    }
    // The chart's exchange lives in state.cryptoExchange (segnalazione
    // 87cc755b): reading state.exchange, which is never set, left the Lab on
    // its own exchange. Synced even when the pair is the same.
    const exchSelect = el("lab-exchange-select");
    const chartExchange = state.cryptoExchange;
    labState.assetType = state.assetType === "dex" ? "dex" : "crypto";
    if (exchSelect && labState.assetType === "dex") {
      exchSelect.value = "dexscreener";
    } else if (exchSelect && chartExchange && exchSelect.querySelector(`option[value="${chartExchange}"]`)) {
      exchSelect.value = chartExchange;
      labState.exchange = chartExchange;
    }
    const tf = el("interval-primary")?.value;
    const tfBtn = tf && labEl("lab-tf-row")?.querySelector(`.lab-tf-btn[data-lab-tf="${tf}"]`);
    if (tfBtn) {
      labEl("lab-tf-row").querySelectorAll(".lab-tf-btn").forEach((b) => b.classList.toggle("active", b === tfBtn));
      labState.tf = tf;
    }
    const strat = el("active-strategy-select")?.value;
    const labSel = labEl("lab-strategy-select");
    if (strat && labSel && labSel.querySelector(`option[value="${strat}"]`)) {
      if (labState.strategy !== strat) {
        labSel.value = strat;
        labState.strategy = strat;
        renderLabParamFields();
      }
      const params = collectStrategyParams(el("strategy-params-fields"), strat);
      const box = labEl("lab-params-fields");
      Object.entries(params).forEach(([key, value]) => {
        const input = box && box.querySelector(`[name="${key}"]`);
        if (!input) return;
        if (input.type === "checkbox") input.checked = !!value;
        else input.value = value;
      });
    }
  }

  function syncChartFromLab() {
    if (!labState.symbol) return;
    const params = collectStrategyParams(labEl("lab-params-fields"), labState.strategy);
    const labExch = labState.assetType === "dex" ? "mexc" : (el("lab-exchange-select")?.value || labState.exchange);
    const same = state.data && state.data.symbol === labState.symbol
      && state.assetType === labState.assetType
      && (labState.assetType === "dex" || state.cryptoExchange === labExch)
      && el("interval-primary")?.value === labState.tf
      && el("active-strategy-select")?.value === labState.strategy
      && JSON.stringify(collectStrategyParams(el("strategy-params-fields"), labState.strategy)) === JSON.stringify(params);
    if (same) return;
    applyConfigToChart({
      assetType: labState.assetType,
      exchange: labExch,
      symbol: labState.symbol,
      displaySymbol: labState.displaySymbol,
      interval: labState.tf,
      strategyName: labState.strategy,
      params,
    });
    runAnalysis(labState.symbol);
    labState.paramsDirty = false;      // the chart now has the Lab's values
  }

  // ── Sidebar ───────────────────────────────────────────────────────────
  // Unica navigazione su desktop. Non duplica la logica delle tab: le
  // pilota, cosi' resta un solo posto che decide quale contenuto e' vivo.
  function setArea(area) {
    const cockpit = document.querySelector(".cockpit");
    const item = document.querySelector(`.sidenav-item[data-area="${area}"]`);

    // I drawer (Livelli, Script, Bacheca) sono flyout sopra il grafico:
    // restano solo dentro Analizza, dove c'e' un grafico su cui contano.
    // Livelli e' un cassetto accanto al grafico, non una colonna di lettura:
    // i suoi interruttori agiscono sulla serie che si sta guardando, quindi
    // l'area resta Analizza e il grafico resta largo. Gli altri due invece
    // sostituiscono il lavoro con del testo da leggere.
    if (area === "livelli") {
      cockpit.dataset.area = "analizza";
      // Il grafico allargato nasconde il pannello Livelli via CSS (regola
      // pensata per quando il flyout era solo un'appendice di Analizza): chi
      // clicca Livelli lo vuole vedere, quindi l'allargamento cede il posto
      // invece di lasciare il pannello invisibile senza spiegazione.
      if (cockpit.classList.contains("chart-wide")) {
        el("chart-expand-btn")?.click();
      }
      openPanel("levels-panel");
      document.querySelectorAll(".sidenav-item").forEach((b) => b.classList.toggle("active", b === item));
      resizeAllCharts();
      return;
    }

    const drawerFor = { script: "script-panel", issues: "issues-panel" };
    if (drawerFor[area]) {
      openPanel(drawerFor[area]);
      // L'area viene dichiarata anche per questi: da cassetto stretto sopra
      // il grafico diventano una colonna di lettura vera, che e' cio' che
      // servono a essere — la bacheca si legge, non si sbircia.
      cockpit.dataset.area = area;
      if (area === "issues") loadIssues();
      document.querySelectorAll(".sidenav-item").forEach((b) => b.classList.toggle("active", b === item));
      requestAnimationFrame(() => resizeAllCharts(true));
      return;
    }

    RAIL_PANELS.forEach(([btnId, pid]) => {
      el(pid).classList.remove("open");
      el(btnId).classList.remove("active");
    });

    const prevArea = cockpit.dataset.area;
    cockpit.dataset.area = area;
    document.querySelectorAll(".sidenav-item").forEach((b) => b.classList.toggle("active", b === item));

    if (area === "trading") loadPositions();

    // Lab e Analizza mostrano la stessa cosa (segnalazione 411e4c7c): pair,
    // timeframe, strategia e parametri passano dall'uno all'altro quando si
    // cambia area, in entrambi i versi.
    if (area === "lab") syncLabFromChart();
    else if (prevArea === "lab" && area === "analizza") syncChartFromLab();

    // Senza questo, il tab-content marcato "active" nell'HTML statico
    // (Backtest) restava visibile per qualunque voce non ancora sincronizzata
    // al primo caricamento.
    const tabTarget = item && item.dataset.tabTarget;
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", !!tabTarget && t.dataset.tab === tabTarget));
    document.querySelectorAll(".tab-content").forEach((c) => {
      c.classList.toggle("active", !!tabTarget && c.dataset.tabContent === tabTarget);
    });
    requestAnimationFrame(() => resizeAllCharts(true));
  }


  // Il Lab a tutta larghezza vuole due colonne vere. Con la sola griglia CSS
  // i blocchi del risultato finivano nella riga corrispondente al loro posto
  // nel DOM, cioe' sotto tutti i controlli: colonna destra vuota per mezzo
  // schermo e il risultato spinto in fondo. Raggruppandoli in un contenitore
  // solo la colonna parte in alto. Gli id non cambiano, app.js li ritrova.
  function groupLabResultColumn() {
    const panel = el("lab-panel");
    if (!panel || panel.querySelector(".lab-results-col")) return;
    const col = document.createElement("div");
    col.className = "lab-results-col";
    [
      "lab-plateau-box", "lab-data-used", "lab-regime-box", "lab-branch-box",
      "lab-status", "lab-result-block", "lab-apply-strip", "lab-signal-status",
    ].forEach((id) => {
      const node = document.getElementById(id);
      if (node) col.appendChild(node);
    });
    panel.appendChild(col);
  }


  // Allargare il grafico vale in ogni area, non solo in Analizza: a volte
  // serve guardarlo e basta, senza cambiare schermata e perdere il punto in
  // cui si era. La scelta resta fra un ricaricamento e l'altro.
  function bindChartExpand() {
    const btn = el("chart-expand-btn");
    if (!btn) return;
    const cockpit = document.querySelector(".cockpit");
    const apply = (on) => {
      cockpit.classList.toggle("chart-wide", on);
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", String(on));
      btn.title = on ? "Shrink chart" : "Expand chart";
      requestAnimationFrame(() => resizeAllCharts(true));
    };
    let saved = false;
    try { saved = localStorage.getItem("lae-chart-wide") === "1"; } catch { saved = false; }
    apply(saved);
    btn.addEventListener("click", () => {
      const on = !cockpit.classList.contains("chart-wide");
      try { localStorage.setItem("lae-chart-wide", on ? "1" : "0"); } catch { /* modalita' privata */ }
      apply(on);
    });
  }

  function bindSidenav() {
    document.querySelectorAll(".sidenav-item[data-area]").forEach((btn) => {
      btn.addEventListener("click", () => setArea(btn.dataset.area));
    });
    // Chi arriva dallo Sniper (o da un link salvato) chiede un'area precisa:
    // senza questo tornerebbe sempre su Analizza, perdendo il punto in cui era.
    const wanted = new URLSearchParams(location.search).get("area");
    if (wanted && document.querySelector(`.sidenav-item[data-area="${wanted}"]`)) {
      setArea(wanted);
      return;
    }
    // All'apertura, accanto al grafico la Watchlist (Lorenzo, 14/10: "deve
    // apparire subito la Watchlist"), non la lettura della struttura, che
    // resta alla voce Structure.
    setArea("analizza");
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === "watchlist"));
    document.querySelectorAll(".tab-content").forEach((c) => {
      c.classList.toggle("active", c.dataset.tabContent === "watchlist");
    });
  }

    bindRail();
    bindIssues();
    bindTheme();
    checkAssetVersion();
    bindLabFilters();
    bindArchive();
    bindTradingJournal();
    el("opt-progress-close").addEventListener("click", closeOptProgress);
    el("opt-progress-stop").addEventListener("click", async () => {
      if (!optViewing) return;
      const btn = el("opt-progress-stop");
      btn.disabled = true;
      btn.textContent = "Stopping…";
      try {
        await fetch(`/api/jobs/${optViewing}/cancel`, { method: "POST" });
      } catch { /* il prossimo giro di polling lo dira' comunque */ }
      btn.disabled = false;
      btn.textContent = "Stop";
    });
    // La pastiglia riapre il log del lavoro piu' recente: e' l'unico modo di
    // tornare a vedere una ricerca dopo aver chiuso la finestra.
    const pill = el("opt-pill");
    if (pill) {
      pill.addEventListener("click", () => {
        const running = optRunning();
        const target = running.length ? running[running.length - 1]
          : [...optJobs.values()].pop();
        if (target) openOptProgress(target.id);
      });
    }
    bindTabs();
    groupLabResultColumn();
    bindSidenav();
    bindChartExpand();
    bindDrawRail();
    bindMobileDrawTools();
    bindAuth();
    relocateAuthWidget();
    await checkAuth();
    if (state.user) {
      await startApp();
    } else {
      openAuthModal("login", { gate: true });
    }
    let relocateTimer = null;
    window.addEventListener("resize", () => {
      resizeAllCharts();
      plateauAnimDraw();
      clearTimeout(relocateTimer);
      relocateTimer = setTimeout(() => {
        relocateChartSettings();
        relocateAuthWidget();
        relocateIntervalSelect();
        relocateStrategySelect();
        syncMobileTfWheel();
      }, 150);
    });
  });

  // Ponte minimo per Modalita' Semplice (simple-mode.js, un modulo isolato
  // separato): sposta il VERO nodo .chart-area — non una sua
  // ricostruzione — dentro un contenitore di quel modulo quando serve
  // mostrare li' grafico, indicatori e ingressi, e lo riporta al suo posto
  // in seguito. Stesso grafico, stessa pipeline (applyConfigToChart +
  // runAnalysis), mai una copia: e' il requisito esplicito di seed-0064
  // ("le nostre grafiche, non un altro grafico").
  const _chartAreaHome = { parent: null, next: null };
  window.LiquidityChartBridge = {
    mount(container) {
      const area = document.querySelector(".chart-area");
      if (!area || !container) return false;
      if (!_chartAreaHome.parent) {
        _chartAreaHome.parent = area.parentNode;
        _chartAreaHome.next = area.nextSibling;
      }
      container.innerHTML = "";
      container.appendChild(area);
      resizeAllCharts(true);
      return true;
    },
    restore() {
      const area = document.querySelector(".chart-area");
      if (area && _chartAreaHome.parent && area.parentNode !== _chartAreaHome.parent) {
        _chartAreaHome.parent.insertBefore(area, _chartAreaHome.next);
        resizeAllCharts(true);
      }
    },
    // cfg: lo stesso oggetto di applyConfigToChart (assetType, exchange,
    // symbol, interval, strategyName, params, backtestParams).
    show(cfg, symbol) {
      applyConfigToChart(cfg);
      // Stesso comportamento di applyArchiveEntry(): un chiamante che passa
      // backtestParams nullo O VUOTO ({}) intende costi/taglia di default,
      // non "lascia l'ultimo override attivo" — un oggetto vuoto e' truthy
      // in JS, quindi un controllo solo su `if (!cfg.backtestParams)`
      // lasciava passare {} come se fosse un override reale: ogni campo
      // (initial_capital, qty_pct_of_equity, ...) restava undefined e
      // finiva cosi', come testo, nella query — 422 "serve un numero
      // (ricevuto 'undefined')". Le voci d'archivio piu' vecchie hanno
      // sempre backtest_params={} (mai registrato niente), quindi questo
      // non e' un caso raro.
      if (!cfg.backtestParams || !Object.keys(cfg.backtestParams).length) state.chartBacktestOverride = null;
      return runAnalysis(symbol);
    },
    // Un click sul grafico reale -> il tempo (in secondi, stessa unita' di
    // t.entry_time/exit_time nei trade) della candela toccata. Chi chiama
    // trova da solo il trade piu' vicino a quel tempo — qui non si sa cosa
    // farne, solo dove e' avvenuto il click. Ogni chiamata sostituisce la
    // precedente sottoscrizione: un solo ascoltatore alla volta, mai
    // accumulati a ogni nuovo montaggio del grafico.
    onChartClick(cb) {
      if (!mainChart) return () => {};
      if (this._clickUnsub) this._clickUnsub();
      const handler = (param) => { if (param && param.time) cb(param.time); };
      mainChart.subscribeClick(handler);
      this._clickUnsub = () => mainChart.unsubscribeClick(handler);
      return this._clickUnsub;
    },
    offChartClick() {
      if (this._clickUnsub) { this._clickUnsub(); this._clickUnsub = null; }
    },
  };

  // Stesso ponte, per la finestra di avanzamento dell'ottimizzazione
  // (#opt-progress — animazione della ricerca stabile, log reale, pulsante
  // Ferma gia' cablato su /api/jobs/{id}/cancel). Modalita' Semplice chiama
  // gia' da sola POST /api/optimize/start (i parametri del suo wizard non
  // coincidono con quelli del Laboratorio); da qui in poi e' la STESSA
  // finestra, la STESSA mappa di lavori (optJobs) e lo STESSO polling —
  // seed-0067, "eredita tutta la logica anche grafica che abbiamo creato
  // nel sito per ottimizzazione stabile".
  window.LiquidityOptBridge = {
    start(jobId, { symbol, strategy, mode, title, sub } = {}) {
      optJobs.set(jobId, {
        id: jobId, symbol, strategy, mode,
        title: title || (mode === "plateau" ? "Stable search running" : "Optimizing"),
        sub: sub || `${symbol} · ${strategyLabel(strategy)}`,
        state: "in corso", elapsed: 0, log: [], seen: 0, seenDone: false,
      });
      openOptProgress(jobId);
      startOptPolling();
    },
    // Letto dalla stessa mappa che il polling reale aggiorna — nessuna
    // seconda chiamata di rete solo per sapere a che punto e'.
    getState(jobId) {
      const job = optJobs.get(jobId);
      if (!job) return null;
      return { state: job.state, result: job.result, error: job.error };
    },
    close() {
      closeOptProgress();
    },
  };

})();

// Wallet on-chain fuso nella tab Trading (sotto-sezione "Wallet on-chain"):
// i moduli ES (fetch a /api/onchain/..., in futuro forse un EventSource)
// partono solo alla prima apertura di questo <details>, non al caricamento
// della pagina — altrimenti ogni utente del sito farebbe chiamate on-chain
// anche senza mai voler vedere il wallet. import() dinamico rispetta
// comunque l'import map dichiarato in <head> (vedi _onchain_importmap in
// main.py), anche chiamato da questo script classico non-module.
(function initOnchainEmbedLazy() {
  const details = document.getElementById("onchain-embed-details");
  if (!details) return;
  let started = false;
  details.addEventListener("toggle", () => {
    if (!details.open || started) return;
    started = true;
    import("@onchain/main.js").catch((error) => {
      console.error("On-chain wallet: module failed to start", error);
    });
  });
})();
