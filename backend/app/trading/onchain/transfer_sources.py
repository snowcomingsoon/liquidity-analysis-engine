"""Every Transfer of a token from a free explorer API (etherscan-compatible).

The free RPCs of Ethereum, Base and BSC answer eth_getLogs only for the
last hours (22/10: publicnode "archive requests require a token", drpc
"free plan"), so wallet_clusters reads the history from explorers:
Blockscout (Ethereum, Base) and Routescan (Ethereum, Base, BSC), no key,
one after the other when one refuses. Rate limits are tight: one call at a
time, a pause between calls, a capped number of pages; past the cap the
result says it is partial.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_RS = "https://api.routescan.io/v2/network/mainnet/evm/{}/etherscan/api"
SOURCES = {
    "ethereum": ["https://eth.blockscout.com/api", _RS.format(1)],
    "base": ["https://base.blockscout.com/api", _RS.format(8453)],
    "bsc": [_RS.format(56)],
}
PAGE = 5000            # Blockscout returns up to 10k; Routescan pages of 10k max
MAX_PAGES = 30         # 150k transfers
PAUSE_S = 0.6
_UA = {"user-agent": "Mozilla/5.0 (compatible; liquidityengine/1.0)", "accept": "application/json"}


def _row(r: dict, i: int) -> dict | None:
    try:
        return {"block": int(r["blockNumber"]), "ts": int(r["timeStamp"]), "tx": r.get("hash"),
                "log_index": int(r.get("logIndex") or r.get("transactionIndex") or 0) * 10_000 + i,
                "from": (r.get("from") or "").lower(), "to": (r.get("to") or "").lower(), "amount": int(r["value"])}
    except (KeyError, TypeError, ValueError):
        return None


async def _get(client: httpx.AsyncClient, base: str, params: dict) -> list[dict] | None:
    """One page; None when the source refuses (the caller tries the next)."""
    for i in range(4):
        try:
            r = await client.get(base, params=params)
        except httpx.HTTPError:
            r = None
        if r is not None and r.status_code == 200:
            try:
                d = r.json()
            except ValueError:
                return None
            res = d.get("result")
            if isinstance(res, list):
                return res
            if "no transactions" in str(d.get("message", "")).lower():
                return []
            if "rate" not in str(d).lower() and "too many" not in str(d).lower():
                return None
        elif r is not None and r.status_code not in (429, 502, 503, 504):
            return None
        await asyncio.sleep(2 ** (i + 1))
    return None


async def transfers(chain: str, token: str, client: httpx.AsyncClient | None = None) -> tuple[list[dict], bool, str]:
    """(transfers in order, partial, source). Raises when no source answers."""
    own = client is None
    client = client or httpx.AsyncClient(timeout=40.0, headers=_UA)
    try:
        for base in SOURCES.get(chain, []):
            out, seen, start, partial, ok = [], set(), 0, False, True
            for page in range(MAX_PAGES):
                rows = await _get(client, base, {"module": "account", "action": "tokentx", "contractaddress": token,
                                                 "startblock": start, "page": 1, "offset": PAGE, "sort": "asc"})
                if rows is None:
                    ok = False
                    break
                for i, r in enumerate(rows):
                    t = _row(r, i)
                    k = t and (t["tx"], t["from"], t["to"], t["amount"])
                    if t and k not in seen:
                        seen.add(k)
                        out.append(t)
                from app.trading.onchain import wallet_clusters
                wallet_clusters.progress("transfers", (page + 1) / MAX_PAGES if len(rows) >= PAGE else 1.0)
                if len(rows) < PAGE:
                    break
                nxt = int(rows[-1]["blockNumber"])
                # The last block may be cut: read it again from its start.
                start = nxt if nxt > start else nxt + 1
                if page == MAX_PAGES - 1:
                    partial = True
                await asyncio.sleep(PAUSE_S)
            if ok and out:
                out.sort(key=lambda t: (t["block"], t["log_index"]))
                return out, partial, base.split("/")[2]
            logger.info("transfer source %s refused %s %s", base, chain, token)
        raise RuntimeError(f"no explorer answered for {chain}")
    finally:
        if own:
            await client.aclose()
