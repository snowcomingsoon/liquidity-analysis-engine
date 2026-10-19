"""Label the top holders of the tokens the gem filters rejected for holder
concentration (one-off probe, 19/10; never merged). Reads ROW lines (JSON)
on stdin, asks RugCheck / GoPlus, prints per token what the top 10 is made
of and whether a stricter "free float" reading would let it pass."""
import json
import re
import sys
import time
import urllib.request

GOPLUS_CHAIN = {"robinhood": "4663", "base": "8453", "bsc": "56", "ethereum": "1", "arc": "5042"}
POOLISH = {"AMM", "LOCKER", "BURN"}
DEAD = {"0x000000000000000000000000000000000000dead", "0x0000000000000000000000000000000000000000"}
CEX_RE = re.compile(r"binance|bybit|okx|okex|coinbase|kraken|kucoin|gate\.?io|mexc|bitget|htx|huobi|crypto\.com|"
                    r"bitmart|lbank|upbit|bithumb|exchange|cex|hot ?wallet", re.I)

# --- ed25519: is a Solana address on the curve (a keypair) or off it (a PDA = a program's account)?
P = 2 ** 255 - 19
D = (-121665 * pow(121666, P - 2, P)) % P
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(s):
    n = 0
    for c in s:
        n = n * 58 + B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\0" * (len(s) - len(s.lstrip("1"))) + raw


def on_curve(addr):
    try:
        b = b58(addr)
    except ValueError:
        return None
    if len(b) != 32:
        return None
    y = int.from_bytes(b, "little") & ((1 << 255) - 1)
    if y >= P:
        return False
    u, v = (y * y - 1) % P, (D * y * y + 1) % P
    x2 = u * pow(v, P - 2, P) % P
    if x2 == 0:
        return True
    return pow(x2, (P - 1) // 2, P) == 1


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode())
        except Exception as exc:  # noqa: BLE001 - a probe: retry, then skip the token
            if attempt == 2:
                print("  !", type(exc).__name__, str(exc)[:80])
                return None
            time.sleep(3 * (attempt + 1))


def solana(token, extra_skip):
    rep = get(f"https://api.rugcheck.xyz/v1/tokens/{token}/report")
    if not rep or not rep.get("topHolders"):
        return None
    known = rep.get("knownAccounts") or {}
    market = set(extra_skip)
    for m in rep.get("markets") or []:
        market |= {v for v in (m.get("pubkey"), m.get("liquidityA"), m.get("liquidityB"),
                               (m.get("liquidityAAccount") or {}).get("owner"),
                               (m.get("liquidityBAccount") or {}).get("owner")) if isinstance(v, str)}
    rows = []
    for h in rep["topHolders"]:
        pct = float(h.get("pct") or 0)
        a, o = h.get("address"), h.get("owner")
        kt = (known.get(o) or known.get(a) or {})
        ktype, kname = kt.get("type"), kt.get("name")
        if a in market or o in market:
            lab = "pool"
        elif ktype in POOLISH:
            lab = {"AMM": "pool", "LOCKER": "lock", "BURN": "burn"}[ktype]
        elif ktype:
            lab = "known:" + str(ktype)
        elif o and on_curve(o) is False:
            lab = "program"
        else:
            lab = "wallet"
        rows.append((pct, lab, kname or ""))
    return rows


def evm(chain, token, pair):
    body = get(f"https://api.gopluslabs.io/api/v1/token_security/{GOPLUS_CHAIN[chain]}?contract_addresses={token}")
    info = ((body or {}).get("result") or {})
    info = info.get(token.lower()) or info.get(token) or None
    if not info or not info.get("holders"):
        return None
    pools = {pair.lower()} | {str(d.get(k) or "").lower() for d in info.get("dex") or []
                              for k in ("pair", "pool_manager")} - {""}
    rows = []
    for h in info["holders"]:
        pct = float(h.get("percent") or 0) * 100
        a, tag = (h.get("address") or "").lower(), h.get("tag") or ""
        if a in DEAD:
            lab = "burn"
        elif a in pools or re.search(r"pool|pair|lp", tag, re.I):
            lab = "pool"
        elif str(h.get("is_locked")) == "1" or re.search(r"lock", tag, re.I):
            lab = "lock"
        elif re.search(r"burn", tag, re.I):
            lab = "burn"
        elif CEX_RE.search(tag):
            lab = "known:CEX"
        elif str(h.get("is_contract")) == "1":
            lab = "program"
        else:
            lab = "wallet"
        rows.append((pct, lab, tag))
    return rows


def main():
    seen, n = set(), 0
    tally = {"tokens": 0, "read": 0, "pass_now": 0, "pass_free_float": 0}
    for line in sys.stdin:
        if not line.startswith("ROW "):
            continue
        r = json.loads(line[4:])
        k = (r["chain"], r["token"])
        if k in seen:
            continue
        seen.add(k)
        if r["chain"] != "solana" and r["chain"] not in GOPLUS_CHAIN:
            continue
        tally["tokens"] += 1
        rows = (solana(r["token"], r.get("skip") or []) if r["chain"] == "solana"
                else evm(r["chain"], r["token"], r.get("pair") or ""))
        time.sleep(1.2)
        if not rows:
            print(f"\n{r['chain']} {r.get('symbol')} {r['token']}: no holder list")
            continue
        tally["read"] += 1
        rows.sort(key=lambda x: -x[0])
        by = {}
        for pct, lab, _ in rows:
            by[lab] = by.get(lab, 0) + pct
        raw10 = sum(p for p, _, _ in rows[:10])
        # what the app counts today: wallets, plus known non-pool accounts on Solana,
        # plus programs on Solana (EVM contracts are already out)
        now = sorted((p for p, lab, _ in rows if lab == "wallet" or lab.startswith("known:")
                      or (lab == "program" and r["chain"] == "solana")), reverse=True)
        free = sorted((p for p, lab, _ in rows if lab == "wallet"), reverse=True)
        big_prog = max((p for p, lab, _ in rows if lab == "program"), default=0)
        now10, free10 = sum(now[:10]), sum(free[:10])
        tally["pass_now"] += now10 < 40
        ok = free10 < 40 and big_prog <= 50
        tally["pass_free_float"] += ok
        print(f"\n{r['chain']} {r.get('symbol')} {r['token']} mcap {r.get('mcap') or 0:,.0f} status {r.get('status')}")
        print(f"  why: {r.get('why')}")
        print(f"  raw top10 {raw10:.1f}% | counted today ~{now10:.1f}% | wallets only {free10:.1f}%"
              f" | biggest program {big_prog:.1f}% -> {'WOULD PASS' if ok and now10 >= 40 else 'same'}")
        print("  by label: " + ", ".join(f"{k} {v:.1f}%" for k, v in sorted(by.items(), key=lambda kv: -kv[1])))
        print("  top 10: " + "; ".join(f"{p:.1f}% {lab}{(' ' + name[:18]) if name else ''}" for p, lab, name in rows[:10]))
        n += 1
        if n >= 120:
            break
    print("\nTALLY", json.dumps(tally))


if __name__ == "__main__":
    main()
