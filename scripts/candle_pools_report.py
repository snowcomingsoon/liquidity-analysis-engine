"""Which pools the app reads candles for, and which of them are Uniswap V3
pools of the Ethereum factory (ISTRUZIONI_CLAUDE_SQUID.md, phase 2).

Run inside the app container, read-only, standard library only:

    docker exec -i deploy-app-1 python - < scripts/candle_pools_report.py

Reads data/candle_archive.sqlite (series keys "net:pool:token:tfagg") and
data/gecko_metrics.json (requests by caller since the process started).
The protocol is never guessed from the address or the name: for every
Ethereum pool it asks the pool contract its factory() through a public RPC
and compares it with the Uniswap V3 factory. Prints counts and the
Ethereum pools only (public addresses).
"""
import glob
import json
import sqlite3
import time
import urllib.request
from collections import Counter

UNISWAP_V3_FACTORY = "0x1f98431c8ad98523631ae4a59f267346ea31f984"
UNISWAP_V2_FACTORY = "0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f"
RPC = "https://ethereum-rpc.publicnode.com"
FACTORY_SELECTOR = "0xc45a0155"          # factory()

base = next(d for d in ("/srv/backend/data", "/app/backend/data", "backend/data", "data")
            if glob.glob(d + "/onchain_projects.db"))


def factory_of(pool: str) -> str | None:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                       "params": [{"to": pool, "data": FACTORY_SELECTOR}, "latest"]}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            out = json.loads(r.read().decode()).get("result") or ""
    except Exception:
        return None
    return ("0x" + out[-40:]).lower() if len(out) >= 42 else None


now = time.time()
db = sqlite3.connect(f"file:{base}/candle_archive.sqlite?mode=ro", uri=True)
rows = db.execute("SELECT k, at, n FROM fetched").fetchall()
pools: dict[tuple, dict] = {}
for k, at, n in rows:
    net, pool = k.split(":")[:2]
    p = pools.setdefault((net, pool), {"series": 0, "last": 0.0})
    p["series"] += 1
    p["last"] = max(p["last"], at or 0)
print("series", len(rows), "pools", len(pools))
print("pools by chain", Counter(net for net, _ in pools).most_common())
print("pools read in the last 7 days by chain",
      Counter(net for (net, _), p in pools.items() if now - p["last"] < 7 * 86400).most_common())
protocol = Counter()
for (net, pool), p in sorted(pools.items()):
    if net != "eth":
        continue
    f = factory_of(pool)
    kind = ("uniswap-v3" if f == UNISWAP_V3_FACTORY else "uniswap-v2" if f == UNISWAP_V2_FACTORY
            else "unknown" if f is None else "other")
    protocol[kind] += 1
    print("eth pool", pool, kind, f or "-", "series", p["series"],
          "last", time.strftime("%Y-%m-%d", time.gmtime(p["last"])) if p["last"] else "-")
    time.sleep(0.3)
print("eth pools by verified factory", dict(protocol))
try:
    m = json.load(open(base + "/gecko_metrics.json"))
    print("gecko since", time.strftime("%Y-%m-%d %H:%M", time.gmtime(m.get("since") or 0)),
          "total", m.get("total"), "ohlcv", m.get("ohlcv_requests"), "other", m.get("other_requests"))
    for caller, v in (m.get("by_caller") or {}).items():
        print("  caller", caller, v)
except (OSError, ValueError):
    print("gecko metrics: none on file yet (written every 5 minutes after the deploy of 19/10)")
