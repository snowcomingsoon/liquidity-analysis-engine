"""Coordinated sells: given a token and a set of wallets, find sells that
land in the same block or within a short window of each other.

Read-only. `fetch_transfers` reads ERC-20 Transfer logs over JSON-RPC
(Robinhood Chain first, any EVM chain known to `rpc_client`); `analyze` is
pure and works on any list of transfers, so the wallet list can come from
the holder-cluster work or from `SAMPLE` while that is not ready.

A transfer from a watched wallet to a pool is a "sell". A transfer to an
address that is neither a pool nor another watched wallet is an "outflow"
(could be a CEX deposit or a hop before selling) and weighs half in the
score. Transfers between watched wallets are consolidation, not selling.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Awaitable, Callable

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TOTAL_SUPPLY = "0x18160ddd"

WINDOW_BLOCKS = 5        # "close" when within this many blocks...
WINDOW_S = 120           # ...or this many seconds (whichever is known)
MIN_WALLETS = 2          # a group needs at least this many distinct wallets
LOG_CHUNK = 5_000        # blocks per eth_getLogs call
# The Robinhood Chain RPC takes 100k blocks per call when filtered on the
# senders (~0.1 s blocks): 5,000 would be 43 calls per token every 6 hours.
# Ethereum/Base/BSC public RPCs keep recent logs only and take small ranges.
CHUNK = {"robinhood": 100_000, "ethereum": 2_000, "base": 2_000, "bsc": 2_000}

# Score weights (sum 100).
W_SHARE, W_WALLETS, W_SAME_BLOCK, W_REPEAT = 45, 25, 20, 10
SHARE_FULL = 0.05        # 5% of supply sold in sync groups = full share points
WALLETS_FULL = 6         # 6+ wallets in one group = full wallet points
REPEAT_FULL = 3          # 3+ separate groups = full repeat points
OUTFLOW_WEIGHT = 0.5

# Placeholder input until the cluster thread hands over real wallets.
# Addresses are obviously fake; nothing here is on-chain data.
SAMPLE = {
    "chain": "robinhood",
    "token": "0x96f455a90a80dcf0c2df6703ea4ba3bedf286e43",
    "decimals": 18,
    "total_supply": 1_000_000_000 * 10**18,
    "pools": ["0x" + "a0" * 20],
    "wallets": ["0x" + f"{i:02x}" * 20 for i in range(1, 6)],
}


def _addr(v: str) -> str:
    """EVM addresses compare lower-case; Solana's are case-sensitive."""
    v = v or ""
    return v.lower() if v.startswith("0x") else v


def _topic_addr(t: str) -> str:
    return "0x" + t[-40:].lower()


def classify(transfers: list[dict], wallets: list[str], pools: list[str]) -> list[dict]:
    """Keep the transfers that leave a watched wallet and tag each one."""
    ws, ps = {_addr(w) for w in wallets}, {_addr(p) for p in pools}
    out = []
    for t in transfers:
        src, dst = _addr(t["from"]), _addr(t["to"])
        if src not in ws or dst in ws or int(t["amount"]) <= 0:
            continue
        out.append({**t, "from": src, "to": dst, "kind": "sell" if dst in ps else "outflow"})
    out.sort(key=lambda t: (t["block"], t.get("log_index", 0)))
    return out


def _close(a: dict, b: dict, window_blocks: int, window_s: int) -> bool:
    if b["block"] - a["block"] <= window_blocks:
        return True
    ta, tb = a.get("ts"), b.get("ts")
    return ta is not None and tb is not None and tb - ta <= window_s


def group(moves: list[dict], window_blocks: int = WINDOW_BLOCKS, window_s: int = WINDOW_S,
          min_wallets: int = MIN_WALLETS) -> list[dict]:
    """Chain moves that are close to the previous one; keep chains with
    enough distinct wallets."""
    chains: list[list[dict]] = []
    for m in moves:
        if chains and _close(chains[-1][-1], m, window_blocks, window_s):
            chains[-1].append(m)
        else:
            chains.append([m])
    groups = []
    for c in chains:
        wallets = {m["from"] for m in c}
        if len(wallets) < min_wallets:
            continue
        per_block = defaultdict(set)
        for m in c:
            per_block[m["block"]].add(m["from"])
        groups.append({
            "first_block": c[0]["block"], "last_block": c[-1]["block"],
            "first_ts": c[0].get("ts"), "last_ts": c[-1].get("ts"),
            "wallets": sorted(wallets),
            "same_block": max(len(s) for s in per_block.values()) >= min_wallets,
            "moves": c,
        })
    return groups


def _weighted(moves: list[dict]) -> float:
    return sum(int(m["amount"]) * (1.0 if m["kind"] == "sell" else OUTFLOW_WEIGHT) for m in moves)


def score(groups: list[dict], total_supply: int) -> dict:
    """0-100: how much of the supply left in sync, by how many wallets,
    how tightly (same block) and how often."""
    if not groups or total_supply <= 0:
        return {"score": 0, "level": "none", "parts": {}}
    share = sum(_weighted(g["moves"]) for g in groups) / total_supply
    parts = {
        "share": W_SHARE * min(1.0, share / SHARE_FULL),
        "wallets": W_WALLETS * min(1.0, max(len(g["wallets"]) for g in groups) / WALLETS_FULL),
        "same_block": W_SAME_BLOCK * sum(g["same_block"] for g in groups) / len(groups),
        "repeat": W_REPEAT * min(1.0, len(groups) / REPEAT_FULL),
    }
    s = round(sum(parts.values()))
    level = "high" if s >= 60 else "medium" if s >= 30 else "low"
    return {"score": s, "level": level, "parts": {k: round(v, 1) for k, v in parts.items()}}


def analyze(transfers: list[dict], wallets: list[str], pools: list[str], total_supply: int,
            decimals: int = 18, **window) -> dict:
    moves = classify(transfers, wallets, pools)
    groups = group(moves, **window)
    unit = 10 ** decimals

    def pct(x: float) -> float:
        return round(100 * x / total_supply, 4) if total_supply else 0.0

    timeline = [{"block": m["block"], "ts": m.get("ts"), "tx": m.get("tx"), "wallet": m["from"],
                 "to": m["to"], "kind": m["kind"], "amount": int(m["amount"]) / unit,
                 "supply_pct": pct(int(m["amount"]))} for m in moves]
    sold = sum(int(m["amount"]) for m in moves if m["kind"] == "sell")
    out = sum(int(m["amount"]) for m in moves if m["kind"] == "outflow")
    return {
        "wallets": len({_addr(w) for w in wallets}),
        "sellers": len({m["from"] for m in moves}),
        "sold_pct": pct(sold), "outflow_pct": pct(out),
        "sync_pct": pct(sum(int(m["amount"]) for g in groups for m in g["moves"])),
        "groups": [{k: v for k, v in g.items() if k != "moves"}
                   | {"supply_pct": pct(sum(int(m["amount"]) for m in g["moves"])),
                      "txs": len(g["moves"])} for g in groups],
        "timeline": timeline,
        "risk": score(groups, total_supply),
    }


Rpc = Callable[[str, list], Awaitable[object]]


def _default_rpc(chain: str) -> Rpc:
    from app.trading.onchain import rpc_client

    async def rpc(method: str, params: list):
        return await rpc_client.call_rpc(chain, method, params)
    return rpc


async def fetch_transfers(chain: str, token: str, wallets: list[str], from_block: int, to_block: int,
                          rpc: Rpc | None = None) -> list[dict]:
    """Transfer logs of `token` sent by `wallets` (topic1 filter), with block
    timestamps. One getLogs per chunk, one getBlock per distinct block."""
    rpc = rpc or _default_rpc(chain)
    senders = ["0x" + "0" * 24 + _addr(w)[2:] for w in wallets]
    logs: list[dict] = []
    step = CHUNK.get(chain, LOG_CHUNK)
    for start in range(from_block, to_block + 1, step):
        end = min(to_block, start + step - 1)
        logs += await rpc("eth_getLogs", [{"address": token, "fromBlock": hex(start), "toBlock": hex(end),
                                           "topics": [TRANSFER_TOPIC, senders]}]) or []
    ts: dict[int, int] = {}
    for b in sorted({int(lg["blockNumber"], 16) for lg in logs}):
        blk = await rpc("eth_getBlockByNumber", [hex(b), False]) or {}
        if blk.get("timestamp"):
            ts[b] = int(blk["timestamp"], 16)
    out = []
    for lg in logs:
        if len(lg.get("topics", [])) < 3:
            continue
        b = int(lg["blockNumber"], 16)
        out.append({"block": b, "ts": ts.get(b), "tx": lg.get("transactionHash"),
                    "log_index": int(lg.get("logIndex", "0x0"), 16),
                    "from": _topic_addr(lg["topics"][1]), "to": _topic_addr(lg["topics"][2]),
                    "amount": int(lg.get("data") or "0x0", 16)})
    return out


async def total_supply(chain: str, token: str, rpc: Rpc | None = None) -> int:
    rpc = rpc or _default_rpc(chain)
    return int(await rpc("eth_call", [{"to": token, "data": TOTAL_SUPPLY}, "latest"]) or "0x0", 16)


async def run(chain: str, token: str, wallets: list[str], pools: list[str], from_block: int, to_block: int,
              decimals: int = 18, rpc: Rpc | None = None, **window) -> dict:
    rpc = rpc or _default_rpc(chain)
    transfers = await fetch_transfers(chain, token, wallets, from_block, to_block, rpc)
    supply = await total_supply(chain, token, rpc)
    return {"chain": chain, "token": _addr(token), "from_block": from_block, "to_block": to_block,
            **analyze(transfers, wallets, pools, supply, decimals, **window)}


# --- Report v1 (contract in coordinated_sells.py): one file per token in
# backend/data/coordinated_sells/<chain>-<token>.json, read by the view and
# the Telegram alert. Shares are fractions of supply, never percentages.

REPORT_VERSION = 1
# Structure risk (Lorenzo 22/10, "conta anche la struttura"): the supply held
# by linked wallets, before they sell. STRUCT_FULL of supply in clusters = 100,
# so 18% reaches the exclusion line of 60.
STRUCT_FULL = 0.30


def structure(out_clusters: list[dict]) -> dict:
    """Share of supply held by linked clusters (not the plain top-holders group)."""
    held = sum(c["share"] for c in out_clusters if c["id"] != "top" and len(c["wallets"]) >= 2)
    return {"score": round(100 * min(1.0, held / STRUCT_FULL)), "share": round(held, 6)}


def _reasons(cid: str, groups: list[dict], parts: dict) -> list[str]:
    if not groups:
        return []
    top = max(len(g["wallets"]) for g in groups)
    out = [f"{cid}: {len(groups)} wave(s), up to {top} wallets selling together"]
    if any(g["same_block"] for g in groups):
        out.append(f"{cid}: sells in the same block")
    if parts.get("share", 0) >= W_SHARE / 2:
        out.append(f"{cid}: large share of supply sold in sync")
    return out


def report(chain: str, token: str, transfers: list[dict], clusters: list[dict], pools: list[str],
           supply: int, symbol: str = "", shares: dict[str, float] | None = None,
           now: float | None = None, **window) -> dict:
    """Build the v1 report. `clusters` = [{"id", "wallets": [addr], "links"?}]
    from the holder-cluster work; `shares` = address -> fraction of supply held."""
    import time
    shares = {_addr(k): float(v) for k, v in (shares or {}).items()}
    out_clusters, events, reasons, best = [], [], [], 0
    for c in clusters:
        cid, ws = str(c["id"]), [_addr(w) for w in c["wallets"]]
        groups = group(classify(transfers, ws, pools), **window)
        risk = score(groups, supply)
        best = max(best, risk["score"])
        reasons += _reasons(cid, groups, risk["parts"])
        links = list(dict.fromkeys(list(c.get("links") or [])
                                   + (["same_block_sells"] if any(g["same_block"] for g in groups) else [])))
        out_clusters.append({"id": cid, "wallets": [{"address": w, "share": shares.get(w, 0.0)} for w in ws],
                             "share": round(sum(shares.get(w, 0.0) for w in ws), 6),
                             "links": links, "risk": risk["score"], "edges": c.get("edges") or []})
        for g in groups:
            ts0, ts1 = g["first_ts"], g["last_ts"]
            events.append({
                "id": f"{cid}-{ts0 if ts0 is not None else 'b%d' % g['first_block']}",
                "cluster": cid, "ts": ts0,
                "window_s": ts1 - ts0 if ts0 is not None and ts1 is not None else None,
                "wallets": len(g["wallets"]), "sellers": g["wallets"],
                "share_sold": round(sum(int(m["amount"]) for m in g["moves"]) / supply, 6) if supply else 0.0,
                "txs": [m["tx"] for m in g["moves"] if m.get("tx")],
            })
    events.sort(key=lambda e: e["ts"] or 0)
    st = structure(out_clusters)
    if st["score"] > best:
        reasons.insert(0, f"linked wallets hold {100 * st['share']:.1f}% of supply")
    best = max(best, st["score"])
    return {"version": REPORT_VERSION, "chain": chain, "token": _addr(token), "symbol": symbol,
            "updated_at": int(now if now is not None else time.time()),
            "risk": {"score": best, "reasons": reasons, "structure": st}, "clusters": out_clusters, "events": events}


def report_path(chain: str, token: str):
    from app.trading.onchain import storage
    return storage.DATA_DIR / "coordinated_sells" / f"{chain}-{_addr(token)}.json"


def write_report(rep: dict) -> None:
    import json
    from app.atomic_write import write_text_atomic
    path = report_path(rep["chain"], rep["token"])
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(path, json.dumps(rep, indent=1))
