"""What a token's developer is paid, and whether the developer sells.

Lorenzo, 22/10: "per dregg voglio una sezione speciale che monitora i
pagamenti che riceve lo sviluppatore", then, on the fee account he sent,
"e capire se vende".

A pump.fun token pays its creator a fee on every trade. With fee sharing the
fees land in a fee account (a PDA, "DistributeCreatorFees" in the logs) and
the developer's wallet takes them out with a claim ("ClaimSocialFeePdaV2").
So the engine reads two things on Solana:

- the fee account: every SOL that comes in is a payment, every SOL that goes
  out is a claim, and whoever receives a claim is a claimer;
- each claimer's account of the token: a drop with SOL coming back is a sell,
  a drop without is a transfer out, the reverse a buy or a transfer in.

The repo is public, so the addresses never live in it: whitekobra pastes the
fee account from the app once, it is saved on the data volume
(data/dev_payments/), and the claimers are found on chain. Every new sell or
transfer out of a claimer goes to Telegram once.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections import defaultdict
from pathlib import Path

from app.atomic_write import write_text_atomic
from app.trading.onchain import solana_clusters, storage

logger = logging.getLogger(__name__)

RUN_EVERY_S = 30 * 60
MAX_TX_PER_RUN = 300            # without a Helius key; a first run of a busy account takes a few runs
HELIUS_TX_PER_RUN = 1500
MAX_EVENTS = 3000
MAX_CLAIMERS = 5
DAYS = 60                       # the daily series of payments
MIN_LAMPORTS = 1000             # rent and fee dust is not a payment
SOL_MINT = "So11111111111111111111111111111111111111112"
_SOL = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
_lock = asyncio.Lock()
_busy = False


def _dir() -> Path:
    return storage.DATA_DIR / "dev_payments"


def _read(p: Path) -> dict:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(p: Path, d: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(p, json.dumps(d, separators=(",", ":")))


def _cfg_path(token: str) -> Path:
    return _dir() / f"{token}.json"


def _rep_path(token: str) -> Path:
    return _dir() / f"{token}-report.json"


def save(body: dict) -> dict:
    """{"token", "symbol"?, "fee_accounts": [..], "wallets"?: [..]} -> the
    saved config. `wallets` are claimers known in advance (optional)."""
    token = str(body.get("token") or "").strip()
    if not _SOL.match(token):
        raise ValueError("token: a Solana mint")
    accs = [str(a).strip() for a in body.get("fee_accounts") or [] if str(a).strip()]
    wallets = [str(a).strip() for a in body.get("wallets") or [] if str(a).strip()]
    if not accs or len(accs) > 3 or not all(_SOL.match(a) for a in accs + wallets) or len(wallets) > MAX_CLAIMERS:
        raise ValueError("fee_accounts: 1-3 Solana addresses; wallets: up to 5")
    old = _read(_cfg_path(token))
    cfg = {"chain": "solana", "token": token, "symbol": str(body.get("symbol") or old.get("symbol") or "")[:20],
           "fee_accounts": accs, "wallets": wallets, "state": old.get("state") or {}}
    _write(_cfg_path(token), cfg)
    return cfg


def configs() -> list[dict]:
    d = _dir()
    out = []
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        if not p.name.endswith("-report.json"):
            c = _read(p)
            if c.get("token") and c.get("fee_accounts"):
                out.append(c)
    return out


def report(token: str) -> dict | None:
    if not _SOL.match(token or ""):
        return None
    r = _read(_rep_path(token))
    return r or None


def busy() -> bool:
    return _busy


# ── reading one transaction ────────────────────────────────────────────────

def _keys(tx: dict) -> list[str]:
    return [k["pubkey"] if isinstance(k, dict) else k for k in tx["transaction"]["message"]["accountKeys"]]


def _sol_deltas(tx: dict) -> dict[str, int]:
    m = tx.get("meta") or {}
    return {a: post - pre for a, pre, post in zip(_keys(tx), m.get("preBalances") or [], m.get("postBalances") or [])
            if post != pre}


def _tok_deltas(tx: dict, mint: str) -> dict[str, float]:
    """owner -> change of `mint` in this tx (whole tokens)."""
    m = tx.get("meta") or {}
    out: dict[str, float] = defaultdict(float)
    for side, sign in (("preTokenBalances", -1), ("postTokenBalances", 1)):
        for b in m.get(side) or []:
            if b.get("mint") == mint and b.get("owner"):
                out[b["owner"]] += sign * float((b.get("uiTokenAmount") or {}).get("uiAmountString") or 0)
    return {k: v for k, v in out.items() if abs(v) > 1e-9}


def _ix(tx: dict) -> list[str]:
    logs = (tx.get("meta") or {}).get("logMessages") or []
    return [line.split("Instruction: ", 1)[1] for line in logs if "Instruction: " in line]


def fee_moves(tx: dict, sig: str, account: str) -> list[dict]:
    """The fee account's SOL in (payment) or out (claim) in one tx."""
    d = _sol_deltas(tx)
    delta = d.get(account, 0)
    if abs(delta) < MIN_LAMPORTS:
        return []
    ts = tx.get("blockTime") or 0
    if delta > 0:
        return [{"id": sig, "ts": ts, "kind": "fee", "sol": delta / 1e9, "account": account}]
    to = max((a for a, v in d.items() if v > 0 and a != account), key=lambda a: d[a], default="")
    return [{"id": sig, "ts": ts, "kind": "claim", "sol": -delta / 1e9, "account": account, "to": to}]


def wallet_moves(tx: dict, sig: str, owner: str, mint: str) -> list[dict]:
    """One claimer's change of the token: sell / buy / transfer out / in."""
    t = _tok_deltas(tx, mint)
    amount = t.get(owner, 0.0)
    if not amount:
        return []
    sol = _sol_deltas(tx).get(owner, 0) / 1e9 + _tok_deltas(tx, SOL_MINT).get(owner, 0.0)
    ix = " ".join(_ix(tx)).lower()
    swap = any(w in ix for w in ("swap", "sell", "buy", "route"))
    if amount < 0 and "createlimitorder" in ix:
        kind = "limit_sell"         # tokens parked in a limit order: a sell waiting for its price
    elif amount < 0:
        kind = "sell" if (sol > 0.001 or swap) else "transfer_out"
    else:
        kind = "buy" if (sol < -0.001 or swap) else "transfer_in"
    other = max((a for a, v in t.items() if a != owner and (v > 0) == (amount < 0)),
                key=lambda a: abs(t[a]), default="")
    return [{"id": f"{sig}:{owner[:8]}", "tx": sig, "ts": tx.get("blockTime") or 0, "kind": kind,
             "wallet": owner, "amount": abs(amount), "sol": round(sol, 6), "other": other}]


# ── one run ─────────────────────────────────────────────────────────────────

async def _tx(sig: str) -> dict | None:
    return await solana_clusters._rpc("getTransaction", [sig, {"encoding": "jsonParsed",
                                                               "maxSupportedTransactionVersion": 1}])


async def _token_accounts(owner: str, mint: str) -> list[tuple[str, float]]:
    r = await solana_clusters._rpc("getTokenAccountsByOwner", [owner, {"mint": mint}, {"encoding": "jsonParsed"}])
    out = []
    for a in (r or {}).get("value") or []:
        info = ((a.get("account") or {}).get("data") or {}).get("parsed", {}).get("info", {})
        out.append((a["pubkey"], float((info.get("tokenAmount") or {}).get("uiAmountString") or 0)))
    return out


async def _read_account(acc: str, cursors: dict, budget: list[int], each) -> None:
    """The account's new signatures, oldest first and within the budget; the
    cursor moves only past what was read, so the rest comes next run."""
    ss = await solana_clusters.signatures(acc, until=cursors.get(acc))
    todo = list(reversed(ss))[: max(0, budget[0])]
    for s in todo:
        tx = await _tx(s["signature"])
        if tx:
            each(tx, s["signature"])
        cursors[acc] = s["signature"]
    budget[0] -= len(todo)


def _merge(events: list[dict], new: list[dict]) -> list[dict]:
    seen = {e["id"] for e in events}
    out = events + [e for e in new if e["id"] not in seen]
    out.sort(key=lambda e: e["ts"], reverse=True)
    return out[:MAX_EVENTS]


def build_report(cfg: dict, events: list[dict], holdings: dict[str, float], now: float) -> dict:
    fees = [e for e in events if e["kind"] == "fee"]
    claims = [e for e in events if e["kind"] == "claim"]
    day = 86400

    def total(rows, since=0.0):
        return round(sum(e["sol"] for e in rows if e["ts"] >= since), 6)

    series = defaultdict(float)
    for e in fees:
        if e["ts"] >= now - DAYS * day:
            series[time.strftime("%Y-%m-%d", time.gmtime(e["ts"]))] += e["sol"]
    claimers = []
    for w in _claimers(cfg, events):
        mine = [e for e in events if e.get("wallet") == w]
        sells = [e for e in mine if e["kind"] == "sell"]
        outs = [e for e in mine if e["kind"] == "transfer_out"]
        orders = [e for e in mine if e["kind"] == "limit_sell"]
        claimers.append({
            "address": w,
            "claimed_sol": total([e for e in claims if e.get("to") == w]),
            "holding": holdings.get(w),
            "sold": round(sum(e["amount"] for e in sells), 4), "sold_sol": round(sum(e["sol"] for e in sells), 6),
            "sells": len(sells), "last_sell": max((e["ts"] for e in sells), default=None),
            "bought": round(sum(e["amount"] for e in mine if e["kind"] == "buy"), 4),
            "sent_out": round(sum(e["amount"] for e in outs), 4), "transfers_out": len(outs),
            "in_orders": round(sum(e["amount"] for e in orders), 4), "limit_sells": len(orders),
        })
    return {
        "chain": "solana", "token": cfg["token"], "symbol": cfg.get("symbol") or "",
        "fee_accounts": cfg["fee_accounts"], "updated_at": int(now),
        "first_ts": min((e["ts"] for e in fees), default=None),
        "fees": {"total": total(fees), "d1": total(fees, now - day), "d7": total(fees, now - 7 * day),
                 "d30": total(fees, now - 30 * day), "count": len(fees),
                 "daily": [{"day": k, "sol": round(v, 6)} for k, v in sorted(series.items())]},
        "claims": {"total": total(claims), "count": len(claims),
                   "unclaimed": round(total(fees) - total(claims), 6)},
        "claimers": claimers,
        "events": events[:400],
        "complete": not (cfg.get("state") or {}).get("behind"),
    }


def _claimers(cfg: dict, events: list[dict]) -> list[str]:
    got: dict[str, float] = defaultdict(float)
    for e in events:
        if e["kind"] == "claim" and e.get("to"):
            got[e["to"]] += e["sol"]
    found = sorted(got, key=lambda a: -got[a])
    out = list(dict.fromkeys((cfg.get("wallets") or []) + found))
    return [a for a in out if a not in cfg["fee_accounts"]][:MAX_CLAIMERS]


async def run(cfg: dict, now: float | None = None) -> dict:
    """Reads what is new for one token and rewrites its report."""
    now = time.time() if now is None else now
    token, state = cfg["token"], dict(cfg.get("state") or {})
    cursors = dict(state.get("cursors") or {})
    budget = [HELIUS_TX_PER_RUN if solana_clusters.helius_key() else MAX_TX_PER_RUN]
    old = report(token) or {}
    events = list(_read(_dir() / f"{token}-events.json").get("events") or old.get("events") or [])
    new: list[dict] = []
    for acc in cfg["fee_accounts"]:
        await _read_account(acc, cursors, budget, lambda tx, sig, a=acc: new.extend(fee_moves(tx, sig, a)))
    events = _merge(events, new)
    holdings: dict[str, float] = {}
    for w in _claimers(cfg, events):
        accs = await _token_accounts(w, token)
        holdings[w] = round(sum(b for _, b in accs), 4)
        for acc, _ in accs:
            got: list[dict] = []
            await _read_account(acc, cursors, budget, lambda tx, sig, o=w: got.extend(wallet_moves(tx, sig, o, token)))
            new += got
            events = _merge(events, got)
    state.update(cursors=cursors, behind=budget[0] <= 0, last_run=int(now))
    cfg = {**cfg, "state": state}
    _write(_cfg_path(token), cfg)
    _write(_dir() / f"{token}-events.json", {"events": events})
    rep = build_report(cfg, events, holdings, now)
    _write(_rep_path(token), rep)
    return rep


async def run_all(force: bool = False) -> int:
    global _busy
    if _lock.locked():
        return 0
    async with _lock:
        _busy = True
        n = 0
        try:
            for cfg in configs():
                last = (cfg.get("state") or {}).get("last_run") or 0
                behind = (cfg.get("state") or {}).get("behind")
                if force or behind or time.time() - last >= RUN_EVERY_S:
                    try:
                        await run(cfg)
                        n += 1
                    except Exception:  # noqa: BLE001
                        logger.exception("dev payments %s", cfg.get("symbol") or cfg["token"][:8])
        finally:
            _busy = False
        return n


# ── Telegram ────────────────────────────────────────────────────────────────

_SENT = "dev_payments_sent.json"
ALERT_KINDS = ("sell", "limit_sell", "transfer_out")
ALERT_MAX_AGE_S = 2 * 86400     # the first run reads months of history: only fresh moves are news


def message(rep: dict, e: dict, url: str) -> str:
    sym = rep.get("symbol") or "token"
    w = e["wallet"]
    head = {"sell": f"🔴 Lo sviluppatore di {sym} ha venduto",
            "limit_sell": f"🟠 Lo sviluppatore di {sym} ha messo un ordine di vendita"}.get(
        e["kind"], f"🟠 Lo sviluppatore di {sym} ha spostato token su un altro wallet")
    lines = [head, f"{e['amount']:,.0f} {sym}".replace(",", ".")]
    if e["kind"] == "sell" and e.get("sol"):
        lines.append(f"Incassati {e['sol']:.2f} SOL")
    c = next((x for x in rep.get("claimers") or [] if x["address"] == w), None)
    if c and c.get("holding") is not None:
        lines.append(f"Gli restano {c['holding']:,.0f} {sym}".replace(",", "."))
    lines += [f"Wallet {w[:4]}…{w[-4:]}", f"https://solscan.io/tx/{e['tx']}", url]
    return "\n".join(lines)


async def notify_once(send, url: str, now: float | None = None) -> int:
    now = time.time() if now is None else now
    path = storage.data_file(_SENT)
    try:
        sent_list = [str(x) for x in json.loads(path.read_text(encoding="utf-8"))]
    except (OSError, ValueError, TypeError):
        sent_list = []
    sent, n = set(sent_list), 0
    for cfg in configs():
        rep = report(cfg["token"])
        if not rep:
            continue
        for e in sorted(rep.get("events") or [], key=lambda e: e["ts"]):
            if e["kind"] in ALERT_KINDS and e["id"] not in sent and now - e["ts"] <= ALERT_MAX_AGE_S:
                if await send(message(rep, e, url)):
                    sent.add(e["id"])
                    sent_list.append(e["id"])
                    n += 1
    if n:
        write_text_atomic(path, json.dumps(sent_list[-2000:]))
    return n
