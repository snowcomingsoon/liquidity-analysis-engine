from enum import Enum
from typing import Literal

from pydantic import BaseModel

from app.timeframes import IntervalChoice

AssetType = Literal["stock", "crypto", "dex"]
CryptoExchange = Literal["mexc", "binance", "kucoin", "kraken"]
TimeframeKey = Literal["htf", "mtf", "ltf"]
LevelType = Literal["order_block", "fvg", "eqh", "eql", "bos", "choch"]


class SymbolSuggestion(BaseModel):
    symbol: str
    name: str
    exchange: str  # human label, e.g. "NASDAQ", "MEXC (USDT)", "Binance (USDT)"
    asset_type: AssetType
    provider: Literal["stock", "mexc", "binance", "kucoin", "kraken", "dexscreener"]
    # Solo per provider="dexscreener": l'indirizzo del token BASE (mint su
    # Solana, contratto su EVM) — il simbolo BASE@chain:pool porta solo
    # quello del pool, che non basta a chiedere un quote di swap.
    base_token_address: str | None = None


class Candle(BaseModel):
    time: int  # unix seconds, required by Lightweight Charts
    open: float
    high: float
    low: float
    close: float
    volume: float


class LiquidityLevel(BaseModel):
    type: LevelType
    direction: Literal["bullish", "bearish"]
    price_high: float
    price_low: float
    start_time: int
    end_time: int | None = None
    mitigated: bool = False
    label: str


class IndicatorSeries(BaseModel):
    name: str
    values: list[float | None]
    colors: list[str | None] | None = None   # per-point line colour (zones), when the indicator has them
    levels: list[float] | None = None        # horizontal guide lines in its pane


class FibZone(BaseModel):
    kind: Literal["retracement", "extension"]
    direction: Literal["bullish", "bearish"]
    anchor_time: int  # where the level lines start being drawn from (leg start for a retracement, the C pivot for an extension)
    levels: dict[str, float]  # ratio (as string, e.g. "0.618") -> price
    label: str


class TimeframeAnalysis(BaseModel):
    interval: str
    candles: list[Candle]
    levels: list[LiquidityLevel]
    indicators: list[IndicatorSeries]
    bias: Literal["bullish", "bearish", "neutral"]
    dealing_range: tuple[float, float] | None = None
    fib_zones: list[FibZone] = []


class StrategySignal(BaseModel):
    time: int
    type: Literal["entry_long", "entry_short", "exit_long", "exit_short", "flip_to_long", "flip_to_short"]
    price: float
    label: str


class StrategyState(BaseModel):
    name: str
    position: Literal["long", "short", "flat"]
    signals: list[StrategySignal]


class BacktestTrade(BaseModel):
    direction: Literal["long", "short"]
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    pnl_pct: float
    pnl_abs: float
    equity_after: float
    # Futures-only fields — None/0 on every spot trade, so existing trades
    # serialize identically to before these were added.
    leverage: int | None = None
    liquidation_price: float | None = None
    funding_paid: float = 0.0
    margin_used: float | None = None
    liquidated: bool = False


class BacktestResult(BaseModel):
    # Dichiarato nel risultato, non solo nella richiesta: un numero di
    # rendimento senza sapere a che prezzo si e' entrati non e' confrontabile
    # con nessun altro.
    fill_at: str = "signal_close"
    # fill_at "on_condition": how many signals filled inside the candle
    # (the rest filled at the close). None when the replay did not run.
    intrabar_fills: int | None = None
    # The interval the simulation actually ran on — deliberately coarser
    # than the chart's own timeframe when that's finer than daily, so this
    # can differ from whatever TimeframeAnalysis.interval says for "ltf".
    interval: str
    initial_capital: float
    final_equity: float
    total_return_pct: float
    num_trades: int
    win_rate_pct: float | None
    max_drawdown_pct: float
    profit_factor: float | None
    equity_curve: list[tuple[int, float]]
    trades: list[BacktestTrade]
    data_start: int | None = None   # unix ms del primo candle usato
    data_end: int | None = None     # unix ms dell'ultimo candle usato
    sharpe_ratio: float | None = None
    max_consecutive_losses: int | None = None
    ticker_volatility_pct: float | None = None   # ATR(14)/close medio × 100
    oos_trades: list[BacktestTrade] = []          # trade out-of-sample (solo ottimizzazione)
    # Futures-only: quante posizioni si sono chiuse per liquidazione invece
    # che per segnale della strategia — 0 su ogni backtest spot.
    liquidated_count: int = 0
    # Simple, not compounded (Lorenzo, 15/10: "il risultato percentuale puro
    # di ogni trade [...] e poi sommate", for whoever does not reinvest
    # everything): every trade on the same stake — the initial capital x
    # the position size — net of fees. total_return_pct / max_drawdown_pct
    # stay the compounded ones. Drawdown in points of the initial capital,
    # on closed trades like the compounded one. None where not computed.
    simple_return_pct: float | None = None
    simple_max_drawdown_pct: float | None = None
    position_pct: float | None = None         # % of the equity a trade used (the stake)
    avg_trade_pct: float | None = None       # net % of one trade, mean
    median_trade_pct: float | None = None    # ... and median


class ExchangeCredential(BaseModel):
    api_key_enc: str = ""      # encrypted API key (empty = not configured)
    api_secret_enc: str = ""   # encrypted API secret
    passphrase_enc: str = ""   # encrypted passphrase (KuCoin only)
    enabled: bool = False      # whether to auto-execute orders on this exchange
    size_mode: Literal["fixed_usdt", "pct_balance"] = "fixed_usdt"
    size_value: float = 50.0   # USDT amount or percentage (0-100)
    created_at: float = 0.0    # epoch seconds; set once, when api_key_enc first becomes non-empty


# Massimo assoluto di leva consentito ovunque nel sistema, controllato
# lato server indipendentemente da cosa manda il frontend — un form
# modificabile da devtools non deve poter aggirarlo. Vedi il piano
# "Operazioni futures" (seed-futures-0001).
MAX_FUTURES_LEVERAGE = 1

# Tetto della *simulazione*, separato da quello dell'esecuzione.
#
# Sono due domande diverse: "quanta leva posso rischiare davvero" e "quanta
# leva voglio studiare". Applicare il tetto dell'esecuzione anche al motore
# di backtest lo rendeva inutile — a 1x una posizione isolata non si
# liquida mai, quindi liquidazione e funding, che sono il motivo per cui
# quel motore esiste, non erano piu' osservabili. Simulare non muove
# denaro: qui il limite serve solo a impedire numeri assurdi.
MAX_SIMULATED_LEVERAGE = 10


class FuturesCredential(BaseModel):
    """Credenziali futures — modello separato da ExchangeCredential apposta:
    un bug qui non deve poter toccare l'esecuzione spot, e viceversa."""

    api_key_enc: str = ""
    api_secret_enc: str = ""
    passphrase_enc: str = ""
    enabled: bool = False       # kill switch: spegnibile senza toccare le chiavi
    size_mode: Literal["fixed_usdt", "pct_balance"] = "fixed_usdt"
    size_value: float = 50.0
    leverage: int = 1           # default 1 = economicamente equivalente allo spot
    margin_mode: Literal["isolated"] = "isolated"  # mai cross: vedi il piano
    created_at: float = 0.0     # epoch seconds; set once, when api_key_enc first becomes non-empty


OnchainChain = Literal["solana", "robinhood"]


class OnchainWallet(BaseModel):
    """Un wallet generato da noi, mai importato: la chiave privata nasce
    cifrata sul server (stesso schema di FuturesCredential) e non e' mai
    stata altrove — non e' legato a nessuna identita', a differenza di un
    wallet aperto su un servizio KYC. Modello separato da FuturesCredential
    apposta: qui non c'e' un exchange che fa da rete di sicurezza (nessun
    prelievo bloccabile, nessun controllo anti-frode) — un bug qui non deve
    poter toccare le credenziali exchange, e viceversa."""

    address: str = ""
    private_key_enc: str = ""
    enabled: bool = False       # kill switch: spegnibile senza toccare la chiave
    created_at: float = 0.0


class Passkey(BaseModel):
    """Un passkey WebAuthn (Face ID/Touch ID su iPhone, biometria/PIN su
    Android) registrato per approvare la rivelazione di una chiave
    on-chain da un secondo dispositivo, senza dover ridigitare la password
    li'. Solo materiale pubblico: credential_id e public_key non bastano a
    nessuno per autenticarsi come l'utente, la firma vera resta dentro
    l'elemento sicuro del telefono e non lo lascia mai."""

    credential_id: str      # base64url
    public_key: str         # base64url della chiave pubblica COSE
    sign_count: int = 0
    label: str = ""         # es. "iPhone di Lorenzo" — solo per riconoscerlo in una lista, non usato per verificare
    created_at: float = 0.0


class User(BaseModel):
    id: str
    email: str
    password_hash: str
    telegram_chat_id: str = ""  # user pastes this in from their own DM with the shared bot
    # A separate chat for strategy signals only (segnalazione a6b36231); empty = telegram_chat_id
    telegram_signal_chat_id: str = ""
    # A chat for the Gem Finder only (Lorenzo, 16/10: the gems chat got
    # nothing, the main chat being the alerts one); empty = the main chat
    telegram_gems_chat_id: str = ""
    trading_credentials: dict[str, ExchangeCredential] = {}  # key = exchange slug ("binance", "mexc", "kucoin")
    futures_credentials: dict[str, FuturesCredential] = {}  # key = exchange slug — mai popolato da trading_credentials
    onchain_wallets: dict[OnchainChain, OnchainWallet] = {}  # key = chain ("solana", "robinhood")
    # Chain su cui lo sniper (scanner di nuovi arrivi DEX, gia' in piedi per
    # il resto del sito) puo' aggiungere da solo un token alla watchlist con
    # la strategia "lorenzo" attiva — vuoto/assente = spento, mai acceso di
    # default. L'esecuzione resta comunque dietro onchain_execution_enabled
    # e gli stessi tetti di rischio di qualunque altro ordine automatico.
    sniper_autotrade_chains: list[OnchainChain] = []
    passkeys: list[Passkey] = []
    preferences: dict = {}  # last session state: ticker, interval, strategy, layers, etc.
    # Server-side session revocation (audit 29/09, S06): bumping the version
    # logs out every device; a revoked session id (-> its expiry) one device.
    session_version: int = 0
    revoked_sessions: dict[str, int] = {}


class FavoriteEntry(BaseModel):
    id: str
    owner_id: str
    symbol: str
    asset_type: AssetType
    exchange: CryptoExchange = "mexc"


class WatchlistEntry(BaseModel):
    id: str
    owner_id: str
    symbol: str
    asset_type: AssetType
    exchange: CryptoExchange = "mexc"
    # Solo per asset_type="dex": indirizzo del token base, salvato dalla
    # ricerca DexScreener al momento in cui la entry viene creata. Assente
    # per le entry aggiunte prima di questo campo, e in quel caso
    # l'esecuzione automatica on-chain resta "saltata" — vedi main.py.
    base_token_address: str | None = None
    strategies: list[str] = []  # which strategies fire Telegram alerts for this ticker
    interval: IntervalChoice = "1d"  # which timeframe those strategies are evaluated on
    on_close: bool = True  # False = also evaluate the still-forming candle (faster, but a signal can vanish before the bar closes)
    strategy_params: dict[str, dict] = {}  # per-strategy parameter overrides, keyed by strategy name; missing/empty = use that strategy's defaults
    alert_frequency: dict[str, Literal["once", "every"]] = {}  # "once" | "every" per strategy; default "every"
    strategy_intervals: dict[str, str] = {}  # per-strategy timeframe override; missing = use entry.interval
    # Per-strategy opt-in a ordini reali: default False ovunque, quindi ogni
    # strategia esistente resta "solo alert" finche' l'utente non lo sceglie
    # esplicitamente da questa voce. Le chiavi API restano una precondizione
    # separata (owner.trading_credentials) — questo flag decide solo se
    # QUESTA strategia su QUESTO ticker puo' usarle.
    auto_trade: dict[str, bool] = {}
    # Mercato su cui l'esecuzione automatica opera, per strategia — assente
    # o "spot" e' lo stesso comportamento di sempre. "futures" richiede che
    # entry.exchange sia anche un exchange futures registrato (vedi
    # app/trading/futures/registry.py); il server lo rifiuta altrimenti.
    market: dict[str, Literal["spot", "futures"]] = {}
    # Tetto in USDT per SINGOLO ingresso automatico di questa strategia su
    # questo ticker — assente/0 = nessun tetto, si usa il size_mode/size_value
    # della credenziale exchange cosi' com'e' (comportamento di sempre).
    # Impostato apposta per strategia, non sull'exchange: quella credenziale
    # e' condivisa da tutte le strategie che ci operano sopra, quindi non
    # basta da sola a limitare quanto rischia CIASCUNA. Si applica solo agli
    # ingressi (mai alle chiusure, che devono sempre chiudere per intero) —
    # vedi place_order_for_signal/place_futures_order_for_signal.
    size_cap_usdt: dict[str, float] = {}


class PriceAlertCondition(str, Enum):
    crosses_above = "crosses_above"
    crosses_below = "crosses_below"


class PriceAlert(BaseModel):
    id: str
    owner_id: str
    symbol: str
    asset_type: AssetType
    exchange: CryptoExchange = "mexc"
    condition: PriceAlertCondition
    price: float
    note: str = ""
    active: bool = True
    last_triggered: int | None = None  # unix seconds
    trigger_count: int = 0
    once_only: bool = True  # se True si disattiva dopo il primo trigger
    created_at: int = 0


class ConfluenceZone(BaseModel):
    price_high: float
    price_low: float
    timeframes: list[TimeframeKey]
    types: list[LevelType]
    score: int
    label: str


class AnalysisSummary(BaseModel):
    htf_bias: Literal["bullish", "bearish", "neutral"]
    text: str
    indicator_readout: list[str]
    long_term_context: list[str]
    top_confluence_zones: list[ConfluenceZone]
    unmitigated_gaps: int
    nearest_liquidity_above: float | None
    nearest_liquidity_below: float | None


class AnalysisResponse(BaseModel):
    symbol: str
    asset_type: AssetType
    current_price: float
    timeframes: dict[TimeframeKey, TimeframeAnalysis]
    confluence_zones: list[ConfluenceZone]
    summary: AnalysisSummary
    strategies: dict[TimeframeKey, list[StrategyState]]
    backtests: dict[TimeframeKey, BacktestResult]
    disclaimer: str = (
        "Automated technical analysis tool. Not financial advice, "
        "an investment recommendation or a trading signal."
    )
