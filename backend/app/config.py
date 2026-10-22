import hashlib
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# When frozen (PyInstaller sidecar exe), read .env from next to the exe itself
# — not from the temp extraction dir, which never contains the user's real
# secrets. Same pattern as the DegenScan sidecar (binaries/.env next to the
# server exe, both shipped as Tauri resources).
if getattr(sys, "frozen", False):
    _ENV_FILE = Path(sys.executable).resolve().parent / ".env"
else:
    _ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8")

    # Le azioni sono spente: qui si opera solo in USDT/USDC. Tenerle accese
    # significava dipendere da TwelveData (7 richieste al minuto, il collo di
    # bottiglia piu' stretto del sistema) e ricevere avvisi di errore per
    # ticker che nessuno guarda. Rimettila a True e tutto torna com'era.
    stocks_enabled: bool = False

    # Lo sniper nasce come cacciatore di lanci, e un cacciatore di lanci trova
    # meme coin: Pump.fun e' un lanciatore di meme, e le soglie d'ingresso
    # (MC $1k, liquidita' $500, 30 giorni) sono quelle. Spento, il feed
    # Pump.fun non parte e l'archivio smette di riempirsi di quella roba.
    sniper_memecoins_enabled: bool = False

    # Interruttore generale, separato da quello sopra (che spegne solo il
    # feed Pump.fun): a False nessuno dei tre loop di fondo dello sniper
    # parte (polling dell'archivio, arricchimento CEX, agenti), e le scansioni
    # manuali rispondono che il servizio e' spento invece di girare comunque.
    # Spento su richiesta di Lorenzo il 17/09, riacceso il 23/09 ("non deve
    # essere spento sul server"). Il pilota pero' prende solo i token che
    # superano il filtro di legittimita' (vedi _sniper_onchain_bridge_tick).
    sniper_enabled: bool = True

    # Interruttore generale per l'intero sistema wallet on-chain (Fase 1: solo
    # generazione chiave + saldo, ancora nessuna firma) — a False ogni
    # endpoint /api/onchain/* risponde "disattivato" invece di girare
    # comunque. Serve come leva unica in caso di incidente: non tocca i dati
    # gia' salvati (le chiavi restano cifrate al loro posto), spegne solo
    # l'accesso.
    onchain_enabled: bool = True

    # Radar dei token giovani su Solana e Robinhood (app/trading/onchain/radar.py):
    # sola lettura, propone e non compra. A False il giro di fondo non parte.
    onchain_radar_enabled: bool = True
    # Trading and automatic strategies on the on-chain app: trend follower,
    # RSI+BB lab, autotrader/pilot, simulated portfolio, Meme Sniper (radar,
    # listings, sniper agents), swaps, limit orders and TWAP. Lorenzo, 07/10:
    # "non voglio piu' vedere strategie automatiche [...] questa parte di
    # trading deve sparire". False stops their loops and hides them in the
    # app; saved data stays in backend/data. The gem research keeps running.
    onchain_trading_enabled: bool = False
    # Accounts that keep the on-chain app as it was on 15/10 (frontend/
    # onchain-app-v1.html + static/onchain-v1/): an email allowlist like
    # admin_emails, the default is the admin account. Lorenzo,
    # 16/10: his own account back to before that day's changes, everyone
    # else on the current app.
    onchain_v1_emails: str = "sha256:ec987139be8d4d3991504dbe9bd5c8f92ce102948dee4e4305db5e84e841eb0e"
    # Accounts that may open /app, the on-chain app rebuilt in React
    # (frontend/app-next). Lorenzo, 21/10: "non x whitekobra ma per lorenzo
    # devi farla": his own account only, everyone else keeps their app.
    onchain_next_emails: str = "sha256:ec987139be8d4d3991504dbe9bd5c8f92ce102948dee4e4305db5e84e841eb0e"
    # Lorenzo, 22/10: "rinnova l'app per tutto [...] va applicato a tutti".
    # True opens /app to every signed-in account (guest links aside) and sends
    # phones from /onchain-app.html to it; False goes back to the list above.
    onchain_next_for_all: bool = True
    # Accounts whose Top and arenas score the database rows on the whole row,
    # as the token page does (Lorenzo, 17/10: "per ora falla solo per
    # whitekobra"). Everyone else keeps the lighter rows, and the Telegram
    # alerts and the nightly run read the Top as before.
    onchain_full_score_emails: str = "sha256:fdfcf4ae2f1823a2e1f24d0f48c3fcd8cf128541133709ad272f21f2e62f3f58"
    # Accounts that may set outside-service keys in Diagnostics (service_keys.py)
    # besides the admins: whitekobra (Lorenzo, 20/10, the Groq key).
    service_keys_emails: str = "sha256:fdfcf4ae2f1823a2e1f24d0f48c3fcd8cf128541133709ad272f21f2e62f3f58"
    # Accounts with no cap on their Telegram alerts (gems, listings), their
    # chats paced instead (telegram.PACE_S between two messages), and gems
    # announced only on their first entry into any ranking (Lorenzo, 17/10:
    # "Solo per account whitekobra: Rimuovi tutti i limiti per tutte le chat
    # Telegram").
    telegram_unlimited_emails: str = "sha256:fdfcf4ae2f1823a2e1f24d0f48c3fcd8cf128541133709ad272f21f2e62f3f58"
    # Off on Hetzner (deploy/docker-compose.yml): Caddy compresses there.
    app_gzip: bool = True
    # The gem research (discovery, pillars, DeepSeek readings, layers,
    # outcomes, weekly re-check, studies) in one run a night instead of loops
    # around the clock (app/trading/onchain/nightly.py). Lorenzo, 07/10: "non
    # lasciare sempre in ascolto il bot [...] tutto in una tranche a fine
    # serata". Hour in Europe/Rome; the run stops when the queue is empty or
    # after max_hours. False: the old loops, as before.
    onchain_nightly_enabled: bool = True
    # Lorenzo, 14/10: "La ricerca delle gemme falla solo di notte [...] alle
    # tre va bene [...] farne una bella grossa": one run at 03:00, long.
    # Lorenzo, 19/10: twelve hours apart, "procedi con 04:00 e 16:00 e la
    # ricerca leggera": 04:00 the full run, 16:00 a light one (below).
    onchain_nightly_hour: int = 4
    # More daily runs, "HH:MM" comma-separated, same logic and window.
    # Lorenzo, 08/10: "aggiungi un check oltre che alle 22, anche alle 11.35".
    # Lorenzo, 17/10: "aggiungi per tutti gli account una nuova ricerca alle
    # ore 18 [...] Due ricerche al giorno": 03:00 and 18:00.
    onchain_nightly_extra_times: str = "16:00"
    onchain_nightly_max_hours: float = 6.0   # 04:00-10:00 at most
    # Runs at these times are light (nightly.run_once(light=True)): new
    # projects, the Top and its alerts only, no database re-check queue, no
    # layers, outcomes, Top re-check or studies, at most light_max_hours: in
    # the afternoon GeckoTerminal's free limit is the charts' too.
    onchain_nightly_light_times: str = "16:00"
    onchain_nightly_light_max_hours: float = 2.5
    # Lorenzo, 18/10: between the runs, a light round every 10 minutes on
    # the fast sources and the launchpads, alerts at once (nightly.sentinel_loop).
    onchain_sentinel_enabled: bool = True
    # Lorenzo, 12/10: "la nostra selezione non e' molto popolata, aggiungi
    # controllo ogni ora". A run at every whole hour besides the ones above;
    # those runs get onchain_hourly_max_minutes, the main one keeps max_hours.
    onchain_nightly_hourly: bool = False
    onchain_hourly_max_minutes: float = 45.0
    # A new value runs one extra run as soon as the server starts (so after
    # the deploy that sets it), once: the key is remembered in the nightly
    # state. Lorenzo, 08/10: "forza il giro ora".
    onchain_nightly_force: str = "2026-10-08-1"
    # La memoria degli esiti (app/trading/onchain/outcomes.py) scarta un token
    # che somiglia ai rug passati, solo quando il modello prevede i rug fuori
    # campione. Vale anche per il pilota con soldi veri, che usa lo stesso
    # filtro: Lorenzo il 24/09, "accendi". A False il controllo "Memoria"
    # compare nella pagella ma non blocca.
    onchain_memory_gate: bool = True
    # Facoltativa: con la chiave, Claude legge il sito di ogni token nuovo e
    # da' un parere prima dell'avviso (app/trading/onchain/legit.py). Vuota =
    # restano i controlli automatici, il passaggio IA risulta "non attivo".
    anthropic_api_key: str = ""
    # Where plan payments will arrive (plans.py). Empty: payments not open yet.
    payment_address: str = ""
    legit_ai_model: str = "claude-opus-5"
    # Without anthropic_api_key, DeepSeek reads the gem's site instead
    # (legit.ai_review); its verdict shows on the report card and blocks
    # only with this on, once its record says it can be trusted.
    legit_ai_gate: bool = False
    # Meme coins back in the Meme alerts (Lorenzo, 29/09: "riattiviamo le
    # memecoin per gli alert [...] cercando di evitare i rugpull"): a meme
    # name, no website and a low DeepSeek grade no longer block; the rug
    # checks (RugCheck, GoPlus, holders, locked liquidity) still do. False
    # puts back the old gate (project site + DeepSeek pass).
    # Off again 30/09 (Lorenzo: "non le voglio le meme [...] dobbiamo avere
    # strategia e alert solo su roba buona").
    listings_allow_memes: bool = False
    # The daily reviewer (app/trading/onchain/ai_review.py): once a day
    # Claude reads what really happened to the signals and writes lessons.
    # Request: "un'istanza di claude sonnet nel server [...] con un massimo di
    # token al giorno, cosi' impariamo dagli errori". Needs anthropic_api_key or deepseek_api_key.
    # Cost: one review is ~15k tokens (~$0.06 on Sonnet 5), so ~$2 a month.
    # Two hard caps, counted from the API's own usage: per UTC day and per
    # calendar month. The key is a separate API key from the Console, billed
    # apart from any Claude subscription: it never uses the founder's chat quota.
    ai_review_enabled: bool = True
    # DeepSeek as the reviewer instead of Claude (Lorenzo: "DeepSeek perche'
    # e' un modello gratuito"): the open weights are free, running the full
    # model is not (hundreds of GB of GPU memory), so it is used through
    # DeepSeek's API, far cheaper per token than Claude. "auto" = DeepSeek
    # when deepseek_api_key is set, else Claude.
    ai_review_provider: str = "auto"      # "auto" | "deepseek" | "claude"
    deepseek_api_key: str = ""
    # X (Twitter) API v2 bearer token: recent posts about each project go into
    # DeepSeek's dossier (app/trading/onchain/x_signal.py). Empty: X is not read.
    x_bearer_token: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    # One daily cap for every DeepSeek call on the server, at list price
    # (Lorenzo, 29/09: $0.50, then $0.80). 0 = no cap.
    deepseek_daily_usd: float = 0.80
    # Lorenzo, 10/10: "facciamo ripartire la ricerca bella costante ma basta
    # che non si usi token [...] e neanche deepseek". False: no paid AI on
    # the server. DeepSeek answers only the chat (Telegram and the app's
    # agent, kind "chat"); the research runs on free APIs and the rules.
    # The Anthropic key is ignored as well (cleared below).
    research_ai_enabled: bool = False

    @property
    def research_deepseek(self) -> bool:
        """The research may call DeepSeek: a key and research_ai_enabled.
        Off, the research's DeepSeek steps stop before doing anything else
        (Lorenzo, 19/10: "impedire direttamente che chiamino DeepSeek che
        comunque e' spento"), instead of reading GitHub or X for a call
        deepseek_desk refuses anyway."""
        # DeepSeek is gone (20/10): the free AI (free_ai.py: Groq, Gemini)
        # does the same work when a key is set.
        try:
            from app import free_ai
            return free_ai.available()
        except Exception:
            return False
    # USDC contract on Robinhood Chain for the autotrader's cash; empty = found
    # from the most liquid USDC/USDG pool (autotrader.find_usdc).
    robinhood_usdc_address: str = ""
    # Card deposits: an on-ramp's buy link (MoonPay, Transak, ...) with the
    # operator's own key in it; "{address}" becomes the user's Solana wallet.
    # Empty = the Debit option says it is not set up (deposit.py).
    onramp_url: str = ""
    ai_review_model: str = "claude-sonnet-5"
    ai_review_daily_tokens: int = 40_000
    ai_review_monthly_tokens: int = 600_000
    # Non piu' usata: Token Sniffer e' stato sostituito da GoPlus, pubblico.
    # Resta perche' un .env che la contiene non blocchi l'avvio.
    tokensniffer_api_key: str = ""

    # Serve solo a costruire il link/QR di approvazione dal telefono per
    # rivelare una chiave on-chain — un URL relativo non e' scansionabile da
    # un secondo dispositivo.
    public_base_url: str = "https://liquidityengine.app"

    # Fase 3 (esecuzione reale) — interruttore SEPARATO da onchain_enabled:
    # quello sopra spegne tutto (anche la sola lettura del saldo), questo
    # spegne SOLO la firma/invio di una transazione vera. Nasce a False
    # apposta: il codice che firma esiste e passa i suoi test, ma nessuna
    # transazione vera parte finche' non lo si accende esplicitamente da qui
    # — mai da un parametro di richiesta, che l'utente potrebbe alzare per
    # sbaglio.
    onchain_execution_enabled: bool = False
    # Confermati da Lorenzo il 19/09/2026 — non aumentabili da nessun
    # parametro di richiesta, solo cambiando questo file/env.
    onchain_max_usd_per_trade: float = 20.0
    onchain_max_usd_per_day: float = 100.0
    # Tetto della size per ingresso (Lorenzo, 30/09): nessun ingresso oltre
    # lo slippage stimato sul pool (slippage.py). Sim, portafoglio Top 50 e Real.
    # 0.5 dal 01/10: negli scenari sul server (scripts/slippage_scenarios.py)
    # stesso saldo dell'1% ($11.665) con drawdown 7.7% invece di 12.5%.
    onchain_max_slippage_pct: float = 0.5
    onchain_max_token_concentration_pct: float = 15.0  # % del capitale gestito in un solo token

    # Piano MEV: instradare gli ordini Solana via Jito bundle invece
    # dell'RPC diretto. Acceso di default: la richiesta a Jito (jito.py) e'
    # verificata contro la doc reale e ricade su send_signed_solana_tx se
    # non risponde (execute.py) — non e' un percorso che rischia di
    # bloccare un ordine se Jito e' irraggiungibile. Quello che NON e'
    # stato verificato dal vivo e' un invio reale con fondi veri (nessuna
    # tip transaction vera mandata in questa sessione): per questo resta
    # comunque dietro onchain_execution_enabled come ogni invio.
    onchain_use_jito: bool = True

    twelve_data_api_key: str = ""
    twelve_data_base_url: str = "https://api.twelvedata.com"

    # Nessun concetto di "owner/admin" esiste altrove nel sito (User non ha
    # un ruolo) — /admin/status usa questa allowlist dedicata, stesso
    # meccanismo di telegram_allowed_emails/registration_allowed_emails
    # sotto, con lo stesso default (chi gia' amministra il sito oggi).
    # Email allowlists (16/10, the repo is public): an entry is an address or
    # "sha256:<hex of the lowercased address>", so the defaults name the two
    # accounts without printing them. Match with email_allowlist() below.
    admin_emails: str = "sha256:ec987139be8d4d3991504dbe9bd5c8f92ce102948dee4e4305db5e84e841eb0e"
    # Every service without admin powers (plans, guest links, /admin/status,
    # teaching DeepSeek). Lorenzo, 29/09: "un utente che accede a tutti i
    # servizi, non admin".
    full_access_emails: str = "sha256:fdfcf4ae2f1823a2e1f24d0f48c3fcd8cf128541133709ad272f21f2e62f3f58"

    telegram_bot_token: str = ""
    telegram_chat_ids: str = ""  # comma-separated
    # Dove finiscono i messaggi di SISTEMA (deploy, errori 500), separati dagli
    # alert di trading che vanno alla chat personale di ogni utente. Vuota =
    # vanno in telegram_chat_ids, com'e' sempre stato.
    telegram_dev_chat_ids: str = ""  # comma-separated
    # Chats that get strategy signals and nothing else, comma-separated, on
    # top of every account's alerts chat. Lorenzo, 13/10: "La chat alert
    # continua a ricevere anche ottimizzazioni e gemme": the group is set as
    # an account's MAIN chat, so the alerts-chat setting alone did not catch it.
    telegram_signal_only_chats: str = "-5359869020"
    github_api_token: str = ""   # PAT for fetching commit history on deploy notify
    github_repo: str = "snowcomingsoon/liquidity-analysis-engine"  # owner/name, GITHUB_REPO in .env

    # Registration is open to anyone, but actual Telegram delivery is
    # deliberately locked to specific account emails (comma-separated) —
    # other registered users can still use the app/watchlist, just without
    # alerts going out, until this is opened up more broadly.
    telegram_allowed_emails: str = "sha256:ec987139be8d4d3991504dbe9bd5c8f92ce102948dee4e4305db5e84e841eb0e,sha256:fdfcf4ae2f1823a2e1f24d0f48c3fcd8cf128541133709ad272f21f2e62f3f58"

    # Chi puo' aprire un account. Il sito e' pubblico, e un account non e' un
    # dettaglio estetico: da' accesso all'ottimizzatore, che occupa un core
    # per minuti, e alla parte che conserva chiavi di trading. Vuoto =
    # registrazione aperta a chiunque (com'era prima, e non e' una buona idea
    # su un indirizzo pubblico).
    registration_allowed_emails: str = "sha256:ec987139be8d4d3991504dbe9bd5c8f92ce102948dee4e4305db5e84e841eb0e,sha256:fdfcf4ae2f1823a2e1f24d0f48c3fcd8cf128541133709ad272f21f2e62f3f58"

    # Read-only exchange account credentials, used ONLY for GET
    # account/balance endpoints (app/exchange_balances.py) — never for any
    # order/trade/withdrawal endpoint. Empty = that exchange's balance card
    # just shows "not configured" instead of erroring.
    mexc_api_key: str = ""
    mexc_api_secret: str = ""
    kucoin_api_key: str = ""
    kucoin_api_secret: str = ""
    kucoin_api_passphrase: str = ""

    # Personal exchange balances are sensitive — visible only to these
    # account emails (comma-separated), separate from the Telegram
    # allowlist since this isn't necessarily the same audience.
    balance_visible_emails: str = "sha256:ec987139be8d4d3991504dbe9bd5c8f92ce102948dee4e4305db5e84e841eb0e"

    # Timeframe set: HTF -> MTF -> LTF, matches PROMPT_SPEC.md section 5.
    # Each DataProvider maps these neutral keys to its own interval format.
    timeframe_keys: tuple[str, str, str] = ("htf", "mtf", "ltf")
    # 500 = MEXC's REST max; gives the "Lorenzo" strategy's 268-period trend
    # filter enough settled history instead of just ~30 usable candles. Only
    # used for htf/mtf, which need recent context, not deep history.
    candles_per_timeframe: int = 500
    # LTF drives the chart — kept at MEXC's own single-page cap (the
    # smallest of the three exchanges') so the chart's own fetch never
    # triggers pagination and stays a single fast request regardless of
    # exchange. Deeper history is what the dedicated backtest fetch below is
    # for, not this one.
    ltf_candles: int = 3000
    # The backtest is a separate, deliberately coarser fetch (see
    # `_backtest_interval` in main.py) so a chart set to 1m/5m doesn't cap
    # its own lookback to a few hours — 5000 daily candles is more than any
    # symbol's real listing history, so providers that support pagination
    # (the crypto exchanges) will walk pages back to the actual listing date
    # and stop there; it's a ceiling, not a target.
    # Lorenzo, 14/10: 5000 four-hour candles were ~2 years, too few for the 4H tests
    # (a trade every year, last-year check). 20000 = ~9 years at 4h.
    backtest_candles: int = 20000

    # Kill switch: mette in pausa tutta l'esecuzione automatica degli ordini
    # senza toccare alert, backtest o ottimizzatore. Si attiva via endpoint
    # POST /api/trading/halt (richiede autenticazione) o da .env.
    trading_halt: bool = False


def without_paid_ai(s: Settings) -> Settings:
    """research_ai_enabled off: the Anthropic key is never used."""
    if not s.research_ai_enabled:
        s.anthropic_api_key = ""
    return s


settings = without_paid_ai(Settings())


class EmailAllowlist:
    """A comma-separated allowlist: plain addresses and/or "sha256:<hex>"
    entries. `email in allowlist` matches either; empty is falsy."""

    def __init__(self, csv: str):
        entries = [e.strip().lower() for e in (csv or "").split(",") if e.strip()]
        self._hashes = {e[7:] for e in entries if e.startswith("sha256:")}
        self._plain = {e for e in entries if not e.startswith("sha256:")}

    def __contains__(self, email: object) -> bool:
        if not isinstance(email, str):
            return False
        e = email.strip().lower()
        return e in self._plain or hashlib.sha256(e.encode()).hexdigest() in self._hashes

    def __bool__(self) -> bool:
        return bool(self._plain or self._hashes)


def email_allowlist(csv: str) -> EmailAllowlist:
    return EmailAllowlist(csv)

