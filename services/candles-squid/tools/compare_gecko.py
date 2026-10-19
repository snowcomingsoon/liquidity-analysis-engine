"""Compare the squid's closed candles with GeckoTerminal's on the same pools,
token side, timeframe and buckets (ISTRUZIONI_CLAUDE_SQUID.md, verification).

    python tools/compare_gecko.py http://localhost:4350/graphql POOL[,POOL...]

For each pool: GeckoTerminal's base token is the side compared, in USD.
Only buckets closed on both sides are compared (end <= the squid's indexed
timestamp and <= now). Reports coverage (buckets on each side), and for the
shared ones the relative differences of open/high/low/close and of volume.
The two are different methods (GeckoTerminal's USD conversion and volume
definition are its own): the differences are measured, not assumed zero,
and a match with GeckoTerminal is not by itself proof of correctness.
"""
import json
import statistics
import sys
import time
import urllib.request

GT = "https://api.geckoterminal.com/api/v2/networks/eth/pools/{pool}"
TFS = {300: ("minute", 5), 900: ("minute", 15), 3600: ("hour", 1)}


def get(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json", "Accept": "application/json",
                                          "User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as exc:  # noqa: BLE001 - a report: retry the 429s, then give up
            if "429" in str(exc) and attempt < 3:
                time.sleep(20)
                continue
            raise


def gql(api, query, variables=None):
    out = get(api, {"query": query, "variables": variables or {}})
    if out.get("errors"):
        raise RuntimeError(out["errors"])
    return out["data"]


def rel(a, b):
    return abs(a - b) / abs(b) if b else (0.0 if a == b else float("inf"))


def main():
    api, pools = sys.argv[1], [p.strip().lower() for p in sys.argv[2].split(",") if p.strip()]
    st = gql(api, "{ syncStatuses { block timestamp finalizedBlock } }")["syncStatuses"]
    indexed_ts = st[0]["timestamp"] if st else 0
    print("squid indexed to", st)
    for pool in pools:
        info = get(GT.format(pool=pool) + "?include=base_token")
        base = info["data"]["relationships"]["base_token"]["data"]["id"].split("_", 1)[1].lower()
        print(f"\npool {pool} base token {base}")
        time.sleep(2.5)
        for tf, (unit, agg) in TFS.items():
            g = get(GT.format(pool=pool) + f"/ohlcv/{unit}?aggregate={agg}&limit=300&currency=usd&token={base}")
            time.sleep(2.5)
            grows = {int(r[0]): r for r in g["data"]["attributes"]["ohlcv_list"]}
            q = """query($pool:String!,$token:String!,$tf:Int!){ candles(where:{pool_eq:$pool, token_eq:$token,
                   timeframe_eq:$tf}, orderBy: start_ASC, limit: 2000){ start openUsd highUsd lowUsd closeUsd volumeUsd
                   swaps pricedSwaps pricing } }"""
            srows = {c["start"]: c for c in gql(api, q, {"pool": pool, "token": base, "tf": tf})["candles"]}
            if not srows:
                print(f"  tf {tf}s: squid has no candle")
                continue
            lo = min(srows)
            now = time.time()
            closed = lambda s: s >= lo and s + tf <= indexed_ts and s + tf <= now  # noqa: E731
            gk = {s for s in grows if closed(s)}
            sk = {s for s in srows if closed(s) and srows[s]["closeUsd"] is not None}
            both = sorted(gk & sk)
            diffs = {k: [] for k in ("open", "high", "low", "close", "volume")}
            for s in both:
                gr, sr = grows[s], srows[s]
                for i, k in enumerate(("open", "high", "low", "close"), start=1):
                    diffs[k].append(rel(float(sr[k + "Usd"]), float(gr[i])))
                diffs["volume"].append(rel(float(sr["volumeUsd"]), float(gr[5])))
            print(f"  tf {tf}s: gecko {len(gk)} buckets, squid {len(sk)}, both {len(both)}, "
                  f"only gecko {len(gk - sk)}, only squid {len(sk - gk)}")
            for k, v in diffs.items():
                if v:
                    print(f"    {k:6s} median {statistics.median(v):.4%}  p95 {sorted(v)[int(0.95 * (len(v) - 1))]:.4%}  max {max(v):.4%}")
            pricing = {srows[s]["pricing"] for s in sk}
            print("    pricing", sorted(pricing))


if __name__ == "__main__":
    main()
