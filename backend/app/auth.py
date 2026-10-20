"""
Minimal cookie-based auth for a small multi-user personal tool.

Password hashing: stdlib PBKDF2-HMAC (no new dependency). Sessions: a
signed cookie (userid:expiry:HMAC-signature) rather than a server-side
session table — stateless, so logins survive a server restart/redeploy
without needing extra persistence beyond the signing secret itself.

No email verification (deliberately skipped for now — registration is
just email+password). Each user pastes in their own Telegram chat_id
(grabbed from a DM with the shared bot) so watchlist alerts reach them
individually instead of a single shared broadcast list.
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
from pathlib import Path

from fastapi import Cookie, HTTPException

from app.models import OnchainChain, OnchainWallet, Passkey, User
from app.trading import crypto as _crypto
from app.trading.crypto import decrypt as _legacy_dec

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)
_USERS_FILE = _DATA_DIR / "users.json"
_SECRET_FILE = _DATA_DIR / "session_secret.txt"

SESSION_COOKIE = "session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days

_PBKDF2_ITERATIONS = 200_000

_users: dict[str, User] = {}


def _get_secret() -> bytes:
    # Env-var wins: always available even before the volume mounts, so a
    # rolling deploy never regenerates the secret and logs everyone out.
    import os
    env_secret = os.environ.get("SESSION_SECRET", "").strip()
    if env_secret:
        return env_secret.encode("utf-8")
    # Fallback: persistent file on the Fly volume (works for local dev and
    # as a one-time seed before the env-var is set).
    if _SECRET_FILE.exists():
        secret = _SECRET_FILE.read_text(encoding="utf-8").strip()
        if secret:
            return secret.encode("utf-8")
    secret = secrets.token_hex(32)
    _SECRET_FILE.write_text(secret, encoding="utf-8")
    return secret.encode("utf-8")


_SECRET = _get_secret()
# Segreto derivato, non riusato: _SECRET firma anche i cookie di sessione, e
# una chiave che sposta fondi veri non deve dipendere dallo stesso materiale
# di una che autentica un browser. HMAC come PRF con un'etichetta fissa —
# stesso principio di HKDF, senza bisogno di una libreria in piu'.
_ONCHAIN_SECRET = hmac.new(_SECRET, b"onchain-wallet-v1", hashlib.sha256).digest()   # legacy records only


def _wallet_keys() -> tuple[dict[str, bytes], str]:
    """Keys that can open v2 wallet records, and the id of the one that seals
    new ones (audit 29/09, S07). With WALLET_ENCRYPTION_KEY set, custody no
    longer derives from SESSION_SECRET: whoever can sign cookies can't
    decrypt keys. Without it, a key derived from SESSION_SECRET under its own
    label ("s"). Records sealed with "s" move to "w" the first time they're
    read after the variable is set."""
    import os
    keys = {"s": _crypto.derive_key(_SECRET, b"onchain-wallet-aead-v2")}
    env = os.environ.get("WALLET_ENCRYPTION_KEY", "").strip()
    if env:
        keys["w"] = _crypto.derive_key(env.encode(), b"onchain-wallet-aead-v2")
        return keys, "w"
    return keys, "s"


_WALLET_KEYS, _WALLET_KID = _wallet_keys()
_CRED_KEYS = {"c": _crypto.derive_key(_SECRET, b"exchange-credential-aead-v2")}
_SERVICE_KEYS = {"k": _crypto.derive_key(_SECRET, b"service-key-aead-v1")}


def seal_service_key(plaintext: str) -> str:
    """An outside service's API key (service_keys.py), sealed like the exchange credentials."""
    return _crypto.seal(plaintext, _SERVICE_KEYS["k"], "k", b"service-key")


def unseal_service_key(token: str) -> str:
    try:
        return _crypto.unseal(token, _SERVICE_KEYS, b"service-key")
    except _crypto.SealError:
        logger.error("service key failed authentication: ignored")
        return ""


def _enc(plaintext: str, _secret: bytes = b"") -> str:
    """Exchange credentials: sealed with AES-GCM (v2); _secret is ignored and
    kept only so the call sites read as before."""
    return _crypto.seal(plaintext, _CRED_KEYS["c"], "c", b"exchange-credential")


def _dec(token: str, secret: bytes) -> str:
    """v2 or legacy. A v2 record that fails to authenticate reads as empty,
    like a missing credential, never as garbage."""
    if _crypto.is_sealed(token):
        try:
            return _crypto.unseal(token, _CRED_KEYS, b"exchange-credential")
        except _crypto.SealError:
            logger.error("exchange credential failed authentication: ignored")
            return ""
    return _legacy_dec(token, secret)


def _wallet_aad(user_id: str, chain: str) -> bytes:
    return f"onchain-wallet|{user_id}|{chain}".encode()


_load_failed = False


def _read_users_file(path) -> list | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    return raw if isinstance(raw, list) else None


def _load_users() -> None:
    """users.json holds the wallet keys. If it can't be read, fall back to
    the last good copy; if that fails too, refuse to write anything (audit
    29/09): the old code started empty and the next save erased every
    wallet for good."""
    global _load_failed
    if not _USERS_FILE.exists():
        return
    raw = _read_users_file(_USERS_FILE)
    if raw is None:
        backup = _USERS_FILE.with_suffix(".json.bak")
        raw = _read_users_file(backup) if backup.exists() else None
        if raw is None:
            _load_failed = True
            logger.critical("users.json unreadable and no good backup: writes to it are blocked")
            return
        logger.critical("users.json unreadable: loaded %s instead", backup.name)
    for item in raw:
        try:
            user = User(**item)
            _users[user.id] = user
        except (TypeError, ValueError):
            logger.error("users.json: skipped an unreadable user record")
            continue


def _save_users() -> None:
    """Atomic: a crash mid-write leaves the old file whole, and the previous
    version stays as users.json.bak."""
    if _load_failed:
        raise RuntimeError("users.json could not be read at startup: not overwriting it")
    import os
    payload = json.dumps([u.model_dump() for u in _users.values()])
    tmp = _USERS_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    if _USERS_FILE.exists() and _read_users_file(_USERS_FILE) is not None:
        os.replace(_USERS_FILE, _USERS_FILE.with_suffix(".json.bak"))
    os.replace(tmp, _USERS_FILE)


_load_users()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, _ = stored.split("$", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    return hmac.compare_digest(_hash_password(password, salt), stored)


# A short blocklist of the passwords most likely to appear in a leaked
# credential-stuffing list — not a substitute for a real breach-check API,
# just cheap insurance against the most obvious choices.
_COMMON_WEAK_PASSWORDS = {
    "password", "password1", "password12", "password123",
    "12345678", "123456789", "1234567890",
    "qwerty123", "qwertyui", "qwertyuiop",
    "letmein1", "letmein123", "admin1234", "iloveyou1", "welcome1",
}


def is_strong_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if password.lower() in _COMMON_WEAK_PASSWORDS:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit


def get_user(user_id: str) -> User | None:
    return _users.get(user_id)


def list_users() -> list[User]:
    return list(_users.values())


def find_by_email(email: str) -> User | None:
    email = email.strip().lower()
    return next((u for u in _users.values() if u.email == email), None)


def create_user(email: str, password: str) -> User:
    user = User(
        id=secrets.token_hex(8),
        email=email.strip().lower(),
        password_hash=_hash_password(password),
        telegram_chat_id="",
    )
    _users[user.id] = user
    _save_users()
    return user


def verify_login(email: str, password: str) -> User | None:
    user = find_by_email(email)
    if user is None or not _verify_password(password, user.password_hash):
        return None
    return user


def set_telegram_chat_id(user_id: str, chat_id: str, signal_chat_id: str | None = None,
                         gems_chat_id: str | None = None) -> User | None:
    user = _users.get(user_id)
    if user is None:
        return None
    update = {"telegram_chat_id": chat_id.strip()}
    if signal_chat_id is not None:
        update["telegram_signal_chat_id"] = signal_chat_id.strip()
    if gems_chat_id is not None:
        update["telegram_gems_chat_id"] = gems_chat_id.strip()
    updated = user.model_copy(update=update)
    _users[user_id] = updated
    _save_users()
    return updated


def set_sniper_autotrade_chain(user_id: str, chain: str, enabled: bool) -> User | None:
    user = _users.get(user_id)
    if user is None:
        return None
    chains = set(user.sniper_autotrade_chains)
    if enabled:
        chains.add(chain)
    else:
        chains.discard(chain)
    updated = user.model_copy(update={"sniper_autotrade_chains": sorted(chains)})
    _users[user_id] = updated
    _save_users()
    return updated


def set_preferences(user_id: str, prefs: dict) -> User | None:
    user = _users.get(user_id)
    if user is None:
        return None
    updated = user.model_copy(update={"preferences": prefs})
    _users[user_id] = updated
    _save_users()
    return updated


def set_trading_credential(
    user_id: str,
    exchange: str,
    api_key: str,
    api_secret: str,
    passphrase: str,
    enabled: bool,
    size_mode: str,
    size_value: float,
) -> User | None:
    from app.models import ExchangeCredential
    user = _users.get(user_id)
    if user is None:
        return None
    creds = dict(user.trading_credentials)
    existing = creds.get(exchange, ExchangeCredential())
    new_key = _enc(api_key, _SECRET) if api_key else existing.api_key_enc
    creds[exchange] = ExchangeCredential(
        api_key_enc=new_key,
        api_secret_enc=_enc(api_secret, _SECRET) if api_secret else existing.api_secret_enc,
        passphrase_enc=_enc(passphrase, _SECRET) if passphrase else existing.passphrase_enc,
        enabled=enabled,
        size_mode=size_mode,
        size_value=size_value,
        # Impostata solo la prima volta che la chiave smette di essere vuota —
        # una modifica successiva (leva, size, toggle) non deve azzerare la
        # data di registrazione mostrata all'utente.
        created_at=existing.created_at or (time.time() if new_key else 0.0),
    )
    updated = user.model_copy(update={"trading_credentials": creds})
    _users[user_id] = updated
    _save_users()
    return updated


def delete_trading_credential(user_id: str, exchange: str) -> User | None:
    user = _users.get(user_id)
    if user is None:
        return None
    creds = dict(user.trading_credentials)
    creds.pop(exchange, None)
    updated = user.model_copy(update={"trading_credentials": creds})
    _users[user_id] = updated
    _save_users()
    return updated


def delete_futures_credential(user_id: str, exchange: str) -> User | None:
    user = _users.get(user_id)
    if user is None:
        return None
    creds = dict(user.futures_credentials)
    creds.pop(exchange, None)
    updated = user.model_copy(update={"futures_credentials": creds})
    _users[user_id] = updated
    _save_users()
    return updated


def get_decrypted_credential(user: User, exchange: str) -> tuple[str, str, str]:
    """Returns (api_key, api_secret, passphrase) decrypted. Empty strings if not configured."""
    cred = user.trading_credentials.get(exchange)
    if cred is None:
        return "", "", ""
    return _dec(cred.api_key_enc, _SECRET), _dec(cred.api_secret_enc, _SECRET), _dec(cred.passphrase_enc, _SECRET)


def set_futures_credential(
    user_id: str,
    exchange: str,
    api_key: str,
    api_secret: str,
    enabled: bool,
    size_mode: str,
    size_value: float,
    leverage: int,
    passphrase: str = "",
) -> User | None:
    """Modello e file separati da set_trading_credential() apposta — vedi
    FuturesCredential nel piano "Operazioni futures": un bug qui non deve
    poter toccare le credenziali spot, e viceversa."""
    from app.models import MAX_FUTURES_LEVERAGE, FuturesCredential
    if not (1 <= leverage <= MAX_FUTURES_LEVERAGE):
        raise ValueError(f"Leverage {leverage}x outside the allowed range (1-{MAX_FUTURES_LEVERAGE}x)")
    user = _users.get(user_id)
    if user is None:
        return None
    creds = dict(user.futures_credentials)
    existing = creds.get(exchange, FuturesCredential())
    new_key = _enc(api_key, _SECRET) if api_key else existing.api_key_enc
    creds[exchange] = FuturesCredential(
        api_key_enc=new_key,
        api_secret_enc=_enc(api_secret, _SECRET) if api_secret else existing.api_secret_enc,
        # Vuota = non cambiare, come per chiave e secret: chi salva solo un
        # cambio di leva non deve riscrivere tutte le credenziali.
        passphrase_enc=_enc(passphrase, _SECRET) if passphrase else existing.passphrase_enc,
        enabled=enabled,
        size_mode=size_mode,
        size_value=size_value,
        leverage=leverage,
        created_at=existing.created_at or (time.time() if new_key else 0.0),
    )
    updated = user.model_copy(update={"futures_credentials": creds})
    _users[user_id] = updated
    _save_users()
    return updated


def get_decrypted_futures_credential(user: User, exchange: str) -> tuple[str, str, str]:
    """Returns (api_key, api_secret, passphrase) decrypted. Empty strings if
    not configured. La passphrase resta vuota dove l'exchange non la chiede
    (Binance, Bybit, Kraken) ed e' obbligatoria dove la chiede (OKX,
    Bitget) — a saperlo e' l'adattatore, non questo modulo."""
    cred = user.futures_credentials.get(exchange)
    if cred is None:
        return "", "", ""
    return (
        _dec(cred.api_key_enc, _SECRET),
        _dec(cred.api_secret_enc, _SECRET),
        _dec(cred.passphrase_enc, _SECRET),
    )


def create_onchain_wallet(user_id: str, chain: OnchainChain) -> User | None:
    """Genera una chiave nuova per quella chain — mai due volte: una
    seconda chiamata su una chain che ha gia' un wallet lo lascia intatto
    (rigenerare in silenzio orfanerebbe qualunque fondo gia' mandato al
    vecchio indirizzo). Nasce spenta (enabled=False): un kill switch
    esplicito va acceso a parte, non e' un effetto collaterale del crearla."""
    from app.trading.onchain.keys import generate  # import qui: onchain.keys non deve mai importare auth

    user = _users.get(user_id)
    if user is None:
        return None
    if chain in user.onchain_wallets:
        return user
    key = generate(chain)
    wallets = dict(user.onchain_wallets)
    wallets[chain] = OnchainWallet(
        address=key.address,
        private_key_enc=_crypto.seal(key.private_key_hex, _WALLET_KEYS[_WALLET_KID], _WALLET_KID,
                                     _wallet_aad(user_id, chain)),
        enabled=False,
        created_at=time.time(),
    )
    updated = user.model_copy(update={"onchain_wallets": wallets})
    _users[user_id] = updated
    _save_users()
    return updated


def set_onchain_wallet_enabled(user_id: str, chain: OnchainChain, enabled: bool) -> User | None:
    user = _users.get(user_id)
    if user is None or chain not in user.onchain_wallets:
        return None
    wallets = dict(user.onchain_wallets)
    wallets[chain] = wallets[chain].model_copy(update={"enabled": enabled})
    updated = user.model_copy(update={"onchain_wallets": wallets})
    _users[user_id] = updated
    _save_users()
    return updated


class OnchainKeyIntegrityError(Exception):
    """La chiave decifrata non ricava piu' l'indirizzo salvato — non e'
    un errore silenzioso da ignorare: il cifrario usato altrove in questo
    file basta per un'API key (l'exchange la rifiuta se sbagliata), ma qui
    una corruzione andrebbe rilevata prima di firmare qualunque cosa con
    lei, non dopo aver perso l'accesso al wallet."""


def get_decrypted_onchain_private_key(user: User, chain: OnchainChain) -> str:
    from app.trading.onchain.keys import address_from_private_key

    wallet = user.onchain_wallets.get(chain)
    if wallet is None:
        return ""
    token = wallet.private_key_enc
    if _crypto.is_sealed(token):
        try:
            private_key_hex = _crypto.unseal(token, _WALLET_KEYS, _wallet_aad(user.id, chain))
        except _crypto.SealError as exc:
            raise OnchainKeyIntegrityError(
                f"The saved key for {chain} does not authenticate ({exc}) — tampered, moved or wrong "
                "server key; not used."
            ) from exc
    else:
        private_key_hex = _legacy_dec(token, _ONCHAIN_SECRET)
    if not private_key_hex:
        return ""
    if address_from_private_key(chain, private_key_hex) != wallet.address:
        raise OnchainKeyIntegrityError(
            f"The decrypted key for {chain} does not match the saved address "
            f"({wallet.address}) — corrupted data, not used."
        )
    if _crypto.key_id_of(token) != _WALLET_KID:
        _reseal_wallet(user.id, chain, token, private_key_hex)
    return private_key_hex


def _reseal_wallet(user_id: str, chain: OnchainChain, old_token: str, private_key_hex: str) -> None:
    """Migrate one record to the current v2 key, only after the address
    check passed, and only if nobody changed it meanwhile. The old record
    goes to a backup file first: a failed migration never loses a key."""
    user = _users.get(user_id)
    wallet = user.onchain_wallets.get(chain) if user else None
    if wallet is None or wallet.private_key_enc != old_token:
        return
    new_token = _crypto.seal(private_key_hex, _WALLET_KEYS[_WALLET_KID], _WALLET_KID, _wallet_aad(user_id, chain))
    if _crypto.unseal(new_token, _WALLET_KEYS, _wallet_aad(user_id, chain)) != private_key_hex:
        return
    backup = _USERS_FILE.with_name("wallet_keys_pre_v2.jsonl")
    with backup.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"user_id": user_id, "chain": chain, "address": wallet.address,
                             "private_key_enc": old_token, "at": time.time()}) + "\n")
    wallets = dict(user.onchain_wallets)
    wallets[chain] = wallet.model_copy(update={"private_key_enc": new_token})
    _users[user_id] = user.model_copy(update={"onchain_wallets": wallets})
    _save_users()


def add_passkey(user_id: str, passkey: Passkey) -> User | None:
    user = _users.get(user_id)
    if user is None:
        return None
    updated = user.model_copy(update={"passkeys": [*user.passkeys, passkey]})
    _users[user_id] = updated
    _save_users()
    return updated


def delete_passkey(user_id: str, credential_id: str) -> User | None:
    user = _users.get(user_id)
    if user is None:
        return None
    updated = user.model_copy(update={"passkeys": [pk for pk in user.passkeys if pk.credential_id != credential_id]})
    _users[user_id] = updated
    _save_users()
    return updated


def update_passkey_sign_count(user_id: str, credential_id: str, new_sign_count: int) -> User | None:
    """Aggiornato dopo OGNI autenticazione riuscita — un sign_count che
    smette di crescere rispetto a quello salvato e' come WebAuthn segnala
    un passkey clonato, quindi va scritto subito, non in un giro comodo."""
    user = _users.get(user_id)
    if user is None:
        return None
    passkeys = [
        pk.model_copy(update={"sign_count": new_sign_count}) if pk.credential_id == credential_id else pk
        for pk in user.passkeys
    ]
    updated = user.model_copy(update={"passkeys": passkeys})
    _users[user_id] = updated
    _save_users()
    return updated


def make_session_cookie(user_id: str) -> str:
    """user_id:expires:sid-version:sig. The sid lets logout revoke this one
    cookie on the server; the version lets "log out everywhere" revoke all
    of them (audit 29/09, S06)."""
    expires = int(time.time()) + SESSION_MAX_AGE_SECONDS
    user = _users.get(user_id)
    version = user.session_version if user else 0
    payload = f"{user_id}:{expires}:{secrets.token_hex(8)}-{version}"
    sig = hmac.new(_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def _parse_session_cookie(cookie: str) -> tuple[str, int, str | None, int] | None:
    """(user_id, expires, sid, version) of a cookie with a valid signature,
    or None. Cookies from before S06 have no sid and count as version 0."""
    parts = cookie.split(":")
    if len(parts) == 3:
        user_id, expires_s, sig = parts
        payload, sid, version = f"{user_id}:{expires_s}", None, 0
    elif len(parts) == 4:
        user_id, expires_s, sid_version, sig = parts
        payload = f"{user_id}:{expires_s}:{sid_version}"
        sid, _, version_s = sid_version.partition("-")
        try:
            version = int(version_s)
        except ValueError:
            return None
    else:
        return None
    expected = hmac.new(_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        expires = int(expires_s)
    except ValueError:
        return None
    return user_id, expires, sid, version


def _verify_session_cookie(cookie: str) -> str | None:
    parsed = _parse_session_cookie(cookie)
    if parsed is None:
        return None
    user_id, expires, sid, version = parsed
    if expires < time.time():
        return None
    user = _users.get(user_id)
    if user is not None and (version != user.session_version or (sid and sid in user.revoked_sessions)):
        return None
    return user_id


def revoke_session(cookie: str) -> None:
    """Logout: this cookie stops working on the server too, not only in the
    browser that deleted it. A pre-S06 cookie has no id of its own, so it
    can only be revoked with every other session of the account."""
    parsed = _parse_session_cookie(cookie or "")
    if parsed is None:
        return
    user_id, expires, sid, _version = parsed
    user = _users.get(user_id)
    if user is None:
        return
    if sid is None:
        revoke_all_sessions(user_id)
        return
    now = int(time.time())
    revoked = {k: v for k, v in user.revoked_sessions.items() if v > now}
    revoked[sid] = expires
    _users[user_id] = user.model_copy(update={"revoked_sessions": revoked})
    _save_users()


def revoke_all_sessions(user_id: str) -> None:
    user = _users.get(user_id)
    if user is None:
        return
    _users[user_id] = user.model_copy(update={"session_version": user.session_version + 1, "revoked_sessions": {}})
    _save_users()


async def get_current_user_optional(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    guest: str | None = Cookie(default=None),
) -> User | None:
    user_id = _verify_session_cookie(session) if session else None
    if user_id and user_id in _users:
        return _users[user_id]
    # Link ospite (app/guest.py): utente sintetico in sola lettura. Una
    # sessione vera vince sempre, cosi' Lorenzo non diventa ospite a casa sua.
    from app import guest as guest_links
    link = guest_links.verify_cookie(guest)
    return guest_links.guest_user(link) if link else None


async def get_current_user(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    guest: str | None = Cookie(default=None),
) -> User:
    user = await get_current_user_optional(session, guest)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign-in required")
    return user
