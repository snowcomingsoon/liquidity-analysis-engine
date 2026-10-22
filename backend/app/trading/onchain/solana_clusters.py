"""Wallet clusters and coordinated sells on Solana, from free sources.

Solana has no Transfer logs to read in bulk and the public RPC refuses
getTokenLargestAccounts, so (22/10, probed):
- holders: RugCheck's report (top 20 token accounts with their owners);
  pools, known accounts and program-owned accounts (off-curve owners) out;
- each holder's token account has its own signature list (only this
  token), read with getSignaturesForAddress: its oldest one is the first
  receipt. Holders whose first receipt landed in the same slot are linked
  ("same_slot": a bundle). Wallet-to-wallet transfers are not read: that
  needs every transaction, too many calls for the free RPC;
- sells: the new signatures of each watched token account since the last
  run, each read with getTransaction (capped), the account's own balance
  change from pre/post token balances; a decrease is a sell when a
  program-owned account of the same mint grew in that transaction (a pool),
  an outflow otherwise.
Coverage says "top 20 holders, no transfer links".

With a Helius key (Diagnostics, service_keys "helius", free plan, 22/10)
the same RPC calls go to Helius instead, the holders come from its DAS
getTokenAccounts (every holder, not 20), each holder's first receipt is
read with getTransaction to link wallets fed by the same sender or by one
another, and the sells budget per run is higher. The key never leaves the
server and never appears in logs or errors.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

import httpx

from app.trading.onchain import legit, rpc_client

logger = logging.getLogger(__name__)

SIG_PAGES = 5            # x1000 signatures per token account
MAX_TX_PER_RUN = 250     # getTransaction calls per watch run
HELIUS_TX_PER_RUN = 1000
HELIUS_HOLDERS = 100     # biggest wallets read with a Helius key
HELIUS_PAGES = 5         # x1000 token accounts from DAS
AIRDROP_MIN = 20         # a sender feeding this many holders is an airdrop, not a link
_SEM = asyncio.Semaphore(2)


def helius_key() -> str:
    from app import service_keys
    try:
        return service_keys.get("helius")
    except Exception:  # noqa: BLE001
        return ""


async def _helius(method: str, params, key: str):
    try:
        async with httpx.AsyncClient(timeout=25.0) as c:
            r = await c.post(f"https://mainnet.helius-rpc.com/?api-key={key}",
                             json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Helius failed ({type(exc).__name__})") from None   # no URL: it holds the key
    if r.status_code == 429:
        raise RuntimeError("Helius rate 429")
    if r.status_code != 200:
        raise RuntimeError(f"Helius failed {r.status_code}")
    d = r.json()
    if "error" in d:
        raise RuntimeError(f"Helius {method}: {str(d['error'])[:120]}")
    return d.get("result")


async def _rpc(method: str, params):
    key = helius_key()
    for i in range(5):
        try:
            async with _SEM:
                if key:
                    return await _helius(method, params, key)
                return await rpc_client.call_rpc("solana", method, params, timeout=25.0)
        except RuntimeError as exc:
            if i == 4 or not any(s in str(exc).lower() for s in ("429", "rate", "failed", "too many")):
                raise
            await asyncio.sleep(2 ** (i + 1))


async def signatures(account: str, until: str | None = None) -> list[dict]:
    """Newest first, back to `until` (exclusive) or SIG_PAGES pages."""
    out, before = [], None
    for _ in range(SIG_PAGES):
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        if until:
            opts["until"] = until
        page = await _rpc("getSignaturesForAddress", [account, opts]) or []
        out += [s for s in page if not s.get("err")]
        if len(page) < 1000:
            break
        before = page[-1]["signature"]
    return out


async def report(mint: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.get(legit.RUGCHECK_REPORT.format(mint=mint))
        r.raise_for_status()
        return r.json()


def holders(rep: dict) -> list[dict]:
    """Wallet holders: [{"owner", "account", "pct"}], pools and programs out."""
    skip = set((rep.get("knownAccounts") or {}).keys())
    for m in rep.get("markets") or []:
        skip |= {m.get("pubkey"), m.get("liquidityA"), m.get("liquidityB")}
    out = []
    for h in rep.get("topHolders") or []:
        o, a = h.get("owner"), h.get("address")
        if not o or not a or o in skip or a in skip or legit.is_program_account(o):
            continue
        out.append({"owner": o, "account": a, "pct": float(h.get("pct") or 0)})
    return out


async def helius_holders(mint: str, skip: set[str]) -> list[dict]:
    """Every token account of the mint (DAS), summed by owner, biggest first."""
    per: dict[str, list] = {}
    for page in range(1, HELIUS_PAGES + 1):
        res = await _rpc("getTokenAccounts", {"mint": mint, "limit": 1000, "page": page}) or {}
        rows = res.get("token_accounts") or []
        for t in rows:
            o, a, amt = t.get("owner"), t.get("address"), int(t.get("amount") or 0)
            if not o or not a or amt <= 0 or o in skip or a in skip or legit.is_program_account(o):
                continue
            cur = per.get(o)
            if cur is None or amt > cur[1]:
                per[o] = [a, amt, (cur[2] if cur else 0) + amt]
            else:
                cur[2] += amt
        if len(rows) < 1000:
            break
    top = sorted(per.items(), key=lambda x: -x[1][2])[:HELIUS_HOLDERS]
    return [{"owner": o, "account": v[0], "amount": v[2]} for o, v in top]


def _first_sender(tx: dict, mint: str, owner: str) -> str | None:
    """Who the owner's first tokens came from: the account of the same mint
    that shrank in that transaction (a pool shows up as a program owner)."""
    meta = tx.get("meta") or {}

    def bal(rows):
        out = defaultdict(int)
        for b in rows or []:
            if b.get("mint") == mint:
                out[b.get("owner")] += int((b.get("uiTokenAmount") or {}).get("amount") or 0)
        return out
    pre, post = bal(meta.get("preTokenBalances")), bal(meta.get("postTokenBalances"))
    losers = [o for o in set(pre) | set(post) if o != owner and post.get(o, 0) < pre.get(o, 0)]
    return max(losers, key=lambda o: pre.get(o, 0) - post.get(o, 0)) if losers else None


def sender_links(senders: dict[str, str], holders: set[str]) -> list[tuple[str, str, str]]:
    """(a, b, why): fed by another holder ("transfer") or by one wallet that
    fed several holders but is not an airdrop ("same_sender")."""
    out, fed = [], defaultdict(list)
    for owner, s in senders.items():
        if not s or legit.is_program_account(s):
            continue
        if s in holders:
            out.append((s, owner, "transfer"))
        fed[s].append(owner)
    for s, got in fed.items():
        if 2 <= len(got) < AIRDROP_MIN:
            out += [(got[0], b, "same_sender") for b in got[1:]]
    return out


def same_slot_links(first: dict[str, int]) -> list[tuple[str, str]]:
    by_slot: dict[int, list[str]] = defaultdict(list)
    for owner, slot in first.items():
        by_slot[slot].append(owner)
    return [(ws[0], b) for ws in by_slot.values() if len(ws) >= 2 for b in ws[1:]]


async def build(mint: str) -> dict:
    key = helius_key()
    try:
        rep = await report(mint)
    except (httpx.HTTPError, ValueError):
        if not key:
            raise
        rep = {}
    hs = holders(rep)
    if key:
        skip = set((rep.get("knownAccounts") or {}).keys())
        for m in rep.get("markets") or []:
            skip |= {m.get("pubkey"), m.get("liquidityA"), m.get("liquidityB")}
        supply = int((rep.get("token") or {}).get("supply") or 0)
        if not supply:
            sup = await _rpc("getTokenSupply", [mint]) or {}
            supply = int(((sup.get("value") or {}).get("amount")) or 0)
        hs = [{"owner": h["owner"], "account": h["account"], "pct": 100 * h["amount"] / supply if supply else 0}
              for h in await helius_holders(mint, skip)]
    if len(hs) < 2:
        raise RuntimeError("fewer than 2 wallet holders")
    from app.trading.onchain import wallet_clusters
    wallet_clusters.progress("transfers", 0)
    wallet_clusters.live(holders=[{"address": h["owner"], "share": round(h["pct"] / 100, 5)} for h in hs],
                         counts={"holders": len(hs)})
    left = [len(hs)]

    async def one(h):
        r = await signatures(h["account"])
        left[0] -= 1
        wallet_clusters.progress("transfers", 1 - left[0] / len(hs))
        return r
    sigs = await asyncio.gather(*(one(h) for h in hs))
    first, last_sig, partial = {}, {}, False
    for h, ss in zip(hs, sigs):
        if not ss:
            continue
        last_sig[h["account"]] = ss[0]["signature"]
        if len(ss) >= SIG_PAGES * 1000:
            partial = True          # the first receipt is further back: no slot link
            continue
        first[h["owner"]] = ss[-1]["slot"]
    wallet_clusters.progress("clusters", None)
    pairs = same_slot_links(first)
    why_of = {p: "same_slot" for p in pairs}
    if key:
        # Each holder's first receipt: who sent it (only with complete lists).
        senders = {}
        for h, ss in zip(hs, sigs):
            if ss and h["owner"] in first:
                tx = await _rpc("getTransaction", [ss[-1]["signature"], {"encoding": "jsonParsed",
                                                                         "maxSupportedTransactionVersion": 1}])
                senders[h["owner"]] = _first_sender(tx or {}, mint, h["owner"])
        for a, b, why in sender_links(senders, {h["owner"] for h in hs}):
            pairs.append((a, b))
            why_of[(a, b)] = why
    groups: dict[str, set[str]] = {}
    for a, b in pairs:
        g = groups.get(a) or groups.get(b) or set()
        g |= {a, b}
        for x in g:
            groups[x] = g
    seen, clusters = set(), []
    pct = {h["owner"]: h["pct"] / 100 for h in hs}
    for g in groups.values():
        if id(g) in seen:
            continue
        seen.add(id(g))
        ws = sorted(g, key=lambda o: -pct.get(o, 0))
        clusters.append({"wallets": ws, "links": sorted({why_of.get(p, "same_slot") for p in pairs if p[0] in g}),
                         "edges": [[a, b] for a, b in pairs if a in g], "share": round(sum(pct[o] for o in ws), 6)})
    clusters.sort(key=lambda c: -c["share"])
    for i, c in enumerate(clusters, 1):
        c["id"] = f"a{i}"
    token = rep.get("token") or {}
    return {"clusters": clusters, "top": [h["owner"] for h in hs], "shares": pct,
            "accounts": {h["owner"]: h["account"] for h in hs}, "last_sig": last_sig,
            "supply": str(int((supply if key else 0) or token.get("supply") or 0)), "decimals": int(token.get("decimals") or 0),
            "coverage": {"source": "helius" if key else "rugcheck+solana-rpc", "partial": not key, "holders": len(hs),
                         "note": f"top {len(hs)} holders" + ("" if key else ", no transfer links"), "from_ts": None,
                         "transfers": sum(len(s) for s in sigs), "deep": not partial}}


def _moves(tx: dict, mint: str, owner: str) -> list[dict]:
    """The owner's decrease of `mint` in one transaction, as a transfer."""
    meta = tx.get("meta") or {}

    def bal(rows):
        out = defaultdict(int)
        for b in rows or []:
            if b.get("mint") == mint:
                out[b.get("owner")] += int((b.get("uiTokenAmount") or {}).get("amount") or 0)
        return out
    pre, post = bal(meta.get("preTokenBalances")), bal(meta.get("postTokenBalances"))
    delta = post.get(owner, 0) - pre.get(owner, 0)
    if delta >= 0:
        return []
    gainers = [o for o in set(pre) | set(post) if o != owner and post.get(o, 0) > pre.get(o, 0)]
    pool = next((o for o in gainers if legit.is_program_account(o)), None)
    dest = pool or (gainers[0] if gainers else "unknown")
    sig = (tx.get("transaction") or {}).get("signatures", [""])[0]
    return [{"block": tx.get("slot") or 0, "ts": tx.get("blockTime"), "tx": sig, "log_index": 0,
             "from": owner, "to": "pool" if pool else dest, "amount": -delta}]


async def new_sells(cfg: dict) -> tuple[list[dict], dict]:
    """The watched accounts' moves since the last run, and the new cursors."""
    accounts, cursors = cfg.get("accounts") or {}, dict((cfg.get("state") or {}).get("last_sig") or {})
    out, budget = [], HELIUS_TX_PER_RUN if helius_key() else MAX_TX_PER_RUN
    for owner in cfg["wallets"]:
        acc = accounts.get(owner)
        if not acc:
            continue
        ss = await signatures(acc, until=cursors.get(acc))
        if ss:
            cursors[acc] = ss[0]["signature"]
        for s in ss[:budget]:
            tx = await _rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed",
                                                                "maxSupportedTransactionVersion": 1}])
            if tx:
                out += _moves(tx, cfg["token"], owner)
        budget -= min(budget, len(ss))
    return out, cursors

