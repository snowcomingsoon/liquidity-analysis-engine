"""Wallet clusters of a token, built by the server (Lorenzo, 22/10).

"il sito produca questi database internamente con la ricerca [...] quando il
token finisce nella lista dei candidati deve partire automaticamente il
controllo [...] preferirei che tutto il lavoro [...] venga fatto dal nostro
sito, con il nostro programma". So: no AI, no uploads. When a token enters
the candidates (or is scanned by hand) it is queued; one token at a time,
at most MAX_PER_DAY a day, each rebuilt after REBUILD_S.

The method is the one done by hand on VERDEX (22/10):
- every Transfer of the token over RPC (adaptive getLogs windows), balances
  rebuilt from them, the biggest holders by peak balance;
- contracts out (pools, routers, PoolManager, lockers): eth_getCode, but an
  EIP-7702 delegation (0xef0100...) is a wallet;
- links: tokens passed wallet to wallet; one sender feeding several holders
  (not an airdrop: one sender, many receivers, mostly the same amount);
  first buys in the same wave, tested against first buys drawn at random
  from every buyer of the token (a launch burst is not a cluster);
- no common-funder link: many buyers are 7702 wallets with 0 ETH buying via
  Relay and funded on another chain, and the gas comes from public bundlers.

The clusters go to sync_watch (source "auto"), which reads their sells every
6 hours and writes the report that the view and the Telegram alert read. The
full result stays on the data volume: the repo is public, no addresses in it.
"""
from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import random
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

from app.atomic_write import write_text_atomic
from app.trading.onchain import storage, sync_sells, sync_watch, transfer_sources

logger = logging.getLogger(__name__)

# Chains with a free RPC that serves the whole log history. Base, BSC and
# Ethereum public RPCs answer getLogs only for the last hours (22/10, probed:
# publicnode "archive requests require a token", drpc "free plan").
CHAINS = ("robinhood", "ethereum", "base", "bsc", "solana")
MAX_WINDOW = {"robinhood": 5_000_000}     # the RPC takes up to 10M blocks / 10k logs
MIN_WINDOW = 500
MAX_CALLS = 600                           # getLogs calls per token
MAX_LOGS = 150_000                        # past this the history is cut (partial)
TOP_HOLDERS = 120                         # biggest wallets by peak balance
MAX_CLUSTER_WALLETS = 400
# The biggest holders are watched as one group even with no link between
# them: on VERDEX (22/10) the 44 "big holders" had none on-chain, and they
# are the wallets whose sells move the price.
TOP_WATCH = 50
WAVE_S = 30                               # first buys this close are one wave
SIMS = 300
WAVE_P = 0.01                             # a wave bigger than random this often is kept
AIRDROP_MIN_TARGETS = 20
AIRDROP_SAME_SHARE = 0.5
# Lorenzo, 22/10: "il controllo cluster è vitale, deve avere priorità massima
# sui titoli presenti nella nostra app, in qualunque sezione": every token the
# app shows, not only the candidates. One build every LOOP_S, never two at once.
MAX_PER_DAY = 60
LOOP_S = 300
REBUILD_TOP_S = 2 * 86400   # Top/arenas: rebuilt every 2 days, the rest weekly
MANUAL_PER_DAY = 20       # checks asked for by hand: their own budget, first in line
PER_ACCOUNT_PER_DAY = 5   # of which one account may ask (whitekobra: no own cap)


def account_take(who: str, now: float | None = None) -> bool:
    """Counts one manual check for `who` today; False past its cap."""
    now = now if now is not None else time.time()
    st = _state()
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    by = st.get("manual_by") if (st.get("manual_by") or {}).get("day") == day else {"day": day}
    if by.get(who, 0) >= PER_ACCOUNT_PER_DAY:
        return False
    by[who] = by.get(who, 0) + 1
    st["manual_by"] = by
    _save_state(st)
    return True
REBUILD_S = 7 * 86400
RETRY_S = 86400
TS_EXACT = 300                            # exact timestamps for this many sell blocks
DEAD = {"0x" + "0" * 40, "0x000000000000000000000000000000000000dead"}
_lock = asyncio.Lock()
# Manual checks run at once, beside the queue (Lorenzo, 22/10: "voglio vederlo
# partire subito"), at most two together.
_manual_sem = asyncio.Semaphore(2)
_running: dict[str, dict] = {}          # key -> {"phase", "progress", "started_at"}
_log: deque = deque(maxlen=300)         # the console of the Clusters tab, in memory only


def note(kind: str, item: dict, msg: str = "") -> None:
    _log.append({"ts": round(time.time(), 1), "kind": kind, "chain": item.get("chain"),
                 "token": item.get("token"), "symbol": item.get("symbol") or "", "msg": msg})
_current: "contextvars.ContextVar[str | None]" = contextvars.ContextVar("wallet_cluster_key", default=None)


def progress(phase: str, done: float | None = None) -> None:
    """The phase of the token being built in this task, and how far (0..1)."""
    k = _current.get()
    if k and k in _running:
        run = _running[k]
        if run.get("phase") != phase:
            note("phase", run, phase)
        run.update(phase=phase, progress=None if done is None else round(max(0.0, min(1.0, done)), 3))


def live(**data) -> None:
    """Partial results of the token being built, for the live view:
    holders [{wallet, pct}], clusters [{id, wallets, edges}], events."""
    k = _current.get()
    if k and k in _running:
        _running[k].setdefault("live", {}).update(data)


def _dir() -> Path:
    return storage.DATA_DIR / "wallet_clusters"


def _state_path() -> Path:
    return storage.data_file("wallet_clusters_state.json")


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _state() -> dict:
    st = _read(_state_path(), {})
    return st if isinstance(st, dict) else {}


def _save_state(st: dict) -> None:
    write_text_atomic(_state_path(), json.dumps(st))


def _key(chain: str, token: str) -> str:
    return f"{chain}-{sync_watch._n(token)}"


# --- queue -----------------------------------------------------------------

def request(chain: str, token: str, symbol: str = "", created_at: float | None = None,
            urgent: bool = False, now: float | None = None, manual: bool = False,
            rebuild_s: float | None = None, section: str | None = None) -> bool:
    """Queue a token. Cheap and synchronous: the loop does the work. False
    when the chain has no source or the token was built recently."""
    chain, token = (chain or "").lower(), sync_watch._n(token or "")
    if chain not in CHAINS or not sync_watch._ok(token, chain):
        return False
    now = now if now is not None else time.time()
    st = _state()
    k = _key(chain, token)
    cur = st.get("tokens", {}).get(k) or {}
    if cur.get("built_at") and now - cur["built_at"] < (3600 if manual else RETRY_S if urgent
                                                       else rebuild_s or REBUILD_S):
        return False
    if cur.get("failed_at") and now - cur["failed_at"] < (3600 if manual else RETRY_S):
        return False
    if not manual and any(q.get("key") == k for q in st.get("queue", [])):
        return False
    # Never built: a token new to the app goes ahead of the rebuilds, in the
    # order it came (the most important sections are queued first).
    new = not cur
    queue = [q for q in st.get("queue", []) if q.get("key") != k]
    item = {"key": k, "chain": chain, "token": token, "symbol": str(symbol or "")[:24],
            "created_at": created_at, "at": int(now), "manual": manual, "section": section}
    item["new"] = new
    if urgent:
        queue.insert(0, item)
    elif new:
        queue.insert(next((n for n, q in enumerate(queue) if not (q.get("manual") or q.get("new"))), len(queue)), item)
    else:
        queue.append(item)
    st["queue"] = queue[:500]
    _save_state(st)
    return True


def _take(now: float) -> dict | None:
    st = _state()
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    if st.get("day") != day:
        st["day"], st["built_today"], st["manual_today"] = day, 0, 0
    q = st.get("queue") or []
    i = next((n for n, x in enumerate(q) if x.get("manual") and st.get("manual_today", 0) < MANUAL_PER_DAY), None)
    if i is None and q and st.get("built_today", 0) < MAX_PER_DAY:
        i = next((n for n, x in enumerate(q) if not x.get("manual")), None)
    if i is None:
        _save_state(st)
        return None
    item = q.pop(i)
    st["queue"] = q
    field = "manual_today" if item.get("manual") else "built_today"
    st[field] = st.get(field, 0) + 1
    _save_state(st)
    return item


def _done(item: dict, result: dict | None, error: str | None, now: float) -> None:
    st = _state()
    rec = (st.setdefault("tokens", {}).get(item["key"]) or {})
    if error:
        rec.update(failed_at=int(now), error=error[:200])
    else:
        rec.update(built_at=int(now), error=None, clusters=len(result["clusters"]),
                   wallets=sum(len(c["wallets"]) for c in result["clusters"]), partial=result["partial"])
    st["tokens"][item["key"]] = rec
    _save_state(st)


def token_status(chain: str, token: str) -> dict:
    """One token: queued (and where), building, built, failed. No addresses."""
    st = _state()
    k = _key((chain or "").lower(), sync_watch._n(token or ""))
    pos = next((n for n, q in enumerate(st.get("queue", [])) if q.get("key") == k), None)
    rec = (st.get("tokens") or {}).get(k) or {}
    run = _running.get(k) or {}
    return {"queued": pos is not None, "position": pos, "busy": _lock.locked(),
            "running": bool(run), "phase": run.get("phase"), "progress": run.get("progress"),
            "started_at": run.get("started_at"), "live": run.get("live"),
            "built_at": rec.get("built_at"), "clusters": rec.get("clusters"), "wallets": rec.get("wallets"),
            "partial": rec.get("partial"), "error": rec.get("error") if rec.get("failed_at") else None,
            "failed_at": rec.get("failed_at"),
            "manual_left": MANUAL_PER_DAY - (st.get("manual_today", 0) if st.get("day") ==
                                             time.strftime("%Y-%m-%d", time.gmtime()) else 0)}


def prune(keep: set[str]) -> int:
    """Drops automatic queue items for tokens the app no longer shows."""
    st = _state()
    q = st.get("queue") or []
    kept = [x for x in q if x.get("manual") or x.get("key") in keep]
    if len(kept) != len(q):
        st["queue"] = kept
        _save_state(st)
    return len(q) - len(kept)


def queue_view(since: float = 0, limit: int = 100) -> dict:
    """The Clusters tab: what runs now, what waits, the console since `since`."""
    st = _state()
    q = st.get("queue") or []
    today = st.get("day") == time.strftime("%Y-%m-%d", time.gmtime())
    return {"running": [{k: r.get(k) for k in ("chain", "token", "symbol", "phase", "progress", "started_at",
                                               "manual", "section")} for r in _running.values()],
            "queue": [{k: x.get(k) for k in ("chain", "token", "symbol", "section", "manual", "new", "at")}
                      for x in q[:limit]],
            "queued": len(q), "built_today": st.get("built_today", 0) if today else 0, "max_per_day": MAX_PER_DAY,
            "log": [e for e in _log if e["ts"] > since], "now": round(time.time(), 1)}


def status() -> dict:
    st = _state()
    return {"queue": len(st.get("queue", [])), "built_today": st.get("built_today", 0) if st.get("day") ==
            time.strftime("%Y-%m-%d", time.gmtime()) else 0, "max_per_day": MAX_PER_DAY,
            "built": sum(1 for r in (st.get("tokens") or {}).values() if r.get("built_at")),
            "busy": _lock.locked()}


# --- RPC -------------------------------------------------------------------

async def _call(rpc, method: str, params: list, tries: int = 5):
    for i in range(tries):
        try:
            return await rpc(method, params)
        except RuntimeError as exc:
            if i == tries - 1 or "rate" not in str(exc).lower() and "429" not in str(exc) \
                    and "failed" not in str(exc).lower():
                raise
            await asyncio.sleep(2 ** i)


async def _gather(coros, n: int = 4):
    sem = asyncio.Semaphore(n)

    async def one(c):
        async with sem:
            return await c
    return await asyncio.gather(*(one(c) for c in coros))


async def _block_ts(rpc, b: int) -> int | None:
    blk = await _call(rpc, "eth_getBlockByNumber", [hex(b), False]) or {}
    return int(blk["timestamp"], 16) if blk.get("timestamp") else None


async def block_at(rpc, ts: float, latest: int) -> int:
    """The first block at or after `ts`, by bisection on block timestamps."""
    lo, hi = 0, latest
    while lo < hi:
        mid = (lo + hi) // 2
        t = await _block_ts(rpc, mid)
        if t is None or t < ts:
            lo = mid + 1
        else:
            hi = mid
    return lo


def _parse(lg: dict) -> dict | None:
    if len(lg.get("topics") or []) < 3:
        return None
    return {"block": int(lg["blockNumber"], 16), "tx": lg.get("transactionHash"),
            "log_index": int(lg.get("logIndex") or "0x0", 16),
            "from": sync_sells._topic_addr(lg["topics"][1]), "to": sync_sells._topic_addr(lg["topics"][2]),
            "amount": int(lg.get("data") or "0x0", 16)}


async def all_transfers(rpc, chain: str, token: str, start: int, latest: int) -> tuple[list[dict], bool]:
    """Every Transfer of the token, windows halved on a refusal and doubled
    while results stay small. (transfers, partial)."""
    top = MAX_WINDOW.get(chain, 10_000)
    w, b, calls, out = min(top, 1_000_000), start, 0, []
    while b <= latest:
        if calls >= MAX_CALLS or len(out) >= MAX_LOGS:
            return out, True
        end = min(latest, b + w - 1)
        calls += 1
        try:
            logs = await _call(rpc, "eth_getLogs", [{"address": token, "fromBlock": hex(b), "toBlock": hex(end),
                                                     "topics": [sync_sells.TRANSFER_TOPIC]}]) or []
        except RuntimeError:
            if w <= MIN_WINDOW:
                raise
            w = max(MIN_WINDOW, w // 2)
            continue
        out += [t for t in map(_parse, logs) if t]
        b = end + 1
        progress("transfers", (b - start) / max(1, latest + 1 - start))
        if len(logs) < 3000:
            w = min(top, w * 2)
    out.sort(key=lambda t: (t["block"], t["log_index"]))
    return out, False


# --- analysis (pure) -------------------------------------------------------

def balances(transfers: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    """(balance now, peak balance) per address, from the transfers alone."""
    bal: dict[str, int] = defaultdict(int)
    peak: dict[str, int] = defaultdict(int)
    for t in transfers:
        a = int(t["amount"])
        bal[t["from"]] -= a
        bal[t["to"]] += a
        peak[t["to"]] = max(peak[t["to"]], bal[t["to"]])
    return dict(bal), dict(peak)


def airdrop_senders(transfers: list[dict]) -> set[str]:
    sent: dict[str, list[int]] = defaultdict(list)
    for t in transfers:
        sent[t["from"]].append(int(t["amount"]))
    out = set()
    for s, amounts in sent.items():
        if len(amounts) >= AIRDROP_MIN_TARGETS and Counter(amounts).most_common(1)[0][1] / len(amounts) >= AIRDROP_SAME_SHARE:
            out.add(s)
    return out


def first_buys(transfers: list[dict], contracts: set[str]) -> dict[str, int]:
    """Block of each wallet's first receipt from a contract (a swap)."""
    out: dict[str, int] = {}
    for t in transfers:
        if t["from"] in contracts and t["to"] not in contracts and t["to"] not in out:
            out[t["to"]] = t["block"]
    return out


def waves(times: list[tuple[str, float]], gap: float) -> list[list[str]]:
    """Chains of (wallet, time) where each is within `gap` of the previous."""
    out: list[list[str]] = []
    last = None
    for w, t in sorted(times, key=lambda x: x[1]):
        if last is not None and t - last <= gap:
            out[-1].append(w)
        else:
            out.append([w])
        last = t
    return out


def random_wave_sizes(population: list[float], n: int, gap: float, sims: int = SIMS, seed: int = 7) -> list[int]:
    """Biggest wave of `n` first buys drawn from every buyer's, `sims` times."""
    rng = random.Random(seed)
    if n < 2 or len(population) < n:
        return []
    return [max(len(w) for w in waves([(str(i), t) for i, t in enumerate(rng.sample(population, n))], gap))
            for _ in range(sims)]


class _Union:
    def __init__(self):
        self.p: dict[str, str] = {}

    def find(self, a: str) -> str:
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def join(self, a: str, b: str) -> None:
        self.p[self.find(a)] = self.find(b)


def cluster(transfers: list[dict], contracts: set[str], supply: int, block_s: float,
            top_n: int = TOP_HOLDERS) -> dict:
    """The clusters among the biggest wallets. `block_s` = seconds per block
    (average), to turn the wave gap into blocks."""
    bal, peak = balances(transfers)
    skip = contracts | DEAD
    top = [a for a, _ in sorted(peak.items(), key=lambda x: -x[1]) if a not in skip][:top_n]
    tops = set(top)
    links: dict[tuple[str, str], set[str]] = defaultdict(set)

    def link(a: str, b: str, why: str) -> None:
        if a != b:
            links[tuple(sorted((a, b)))].add(why)

    drops = airdrop_senders(transfers)
    fed: dict[str, set[str]] = defaultdict(set)
    for t in transfers:
        if t["from"] in skip or t["to"] in skip or int(t["amount"]) <= 0:
            continue
        if t["from"] in tops and t["to"] in tops and t["from"] not in drops:
            link(t["from"], t["to"], "transfer")
        if t["to"] in tops and t["from"] not in drops:
            fed[t["from"]].add(t["to"])
    for sender, got in fed.items():
        if len(got) >= 2:
            first = sorted(got)
            for b in first[1:]:
                link(first[0], b, "same_sender")
    buys = first_buys(transfers, contracts)
    gap = WAVE_S / max(block_s, 1e-3)
    mine = [(w, float(buys[w])) for w in top if w in buys]
    sizes = sorted(random_wave_sizes([float(b) for b in buys.values()], len(mine), gap))
    wave_info = []
    for wv in waves(mine, gap):
        if len(wv) < 3 or not sizes:
            continue
        p = sum(1 for s in sizes if s >= len(wv)) / len(sizes)
        wave_info.append({"wallets": len(wv), "p": round(p, 3)})
        if p < WAVE_P:
            for b in wv[1:]:
                link(wv[0], b, "same_wave")
    uf = _Union()
    for a, b in links:
        uf.join(a, b)
    groups: dict[str, list[str]] = defaultdict(list)
    for a in {x for pair in links for x in pair}:
        groups[uf.find(a)].append(a)

    def share(x: int) -> float:
        return round(max(0, x) / supply, 6) if supply else 0.0

    out = []
    for ws in groups.values():
        ws = sorted(ws, key=lambda a: -peak.get(a, 0))[:MAX_CLUSTER_WALLETS]
        why = Counter(r for pair, rs in links.items() if pair[0] in ws for r in rs)
        out.append({"wallets": ws, "links": sorted(why),
                    "edges": [list(pair) for pair in links if pair[0] in ws][:2000], "link_counts": dict(why),
                    "share": share(sum(max(0, bal.get(a, 0)) for a in ws)),
                    "peak_share": share(sum(peak.get(a, 0) for a in ws))})
    out.sort(key=lambda c: -c["peak_share"])
    for i, c in enumerate(out, 1):
        c["id"] = f"a{i}"
    return {"clusters": out, "top": top[:TOP_WATCH], "holders": len(top), "buyers": len(buys), "waves": wave_info,
            "random_wave_p99": sizes[int(len(sizes) * 0.99) - 1] if sizes else None,
            "shares": {a: share(bal.get(a, 0)) for a in top}}


# --- one token -------------------------------------------------------------

def _is_contract(code: str | None) -> bool:
    code = (code or "0x").lower()
    return code not in ("0x", "0x0") and not code.startswith("0xef0100")


async def _contracts(rpc, addrs: list[str]) -> set[str]:
    codes = await _gather([_call(rpc, "eth_getCode", [a, "latest"]) for a in addrs])
    return {a for a, c in zip(addrs, codes) if _is_contract(c)}


async def _stamp(rpc, transfers: list[dict], blocks: set[int], anchors: dict[int, int]) -> None:
    """Timestamps: exact for the most recent `TS_EXACT` blocks in `blocks`,
    the rest interpolated between anchors."""
    exact = sorted(blocks, reverse=True)[:TS_EXACT]
    for b, t in zip(exact, await _gather([_block_ts(rpc, b) for b in exact])):
        if t is not None:
            anchors[b] = t
    ks = sorted(anchors)
    for tr in transfers:
        b = tr["block"]
        if b in anchors:
            tr["ts"] = anchors[b]
            continue
        lo = max((k for k in ks if k <= b), default=ks[0])
        hi = min((k for k in ks if k >= b), default=ks[-1])
        tr["ts"] = anchors[lo] if hi == lo else int(anchors[lo] + (anchors[hi] - anchors[lo]) * (b - lo) / (hi - lo))


async def build(chain: str, token: str, symbol: str = "", created_at: float | None = None, rpc=None) -> dict:
    if chain == "solana":
        return await _build_solana(token, symbol)
    rpc = rpc or sync_sells._default_rpc(chain)
    token = token.lower()
    latest = int(await _call(rpc, "eth_blockNumber", []) or "0x0", 16)
    if created_at and created_at > 1e12:
        created_at /= 1000
    progress("transfers", 0)
    if chain in transfer_sources.SOURCES:
        # History from a free explorer: the free RPCs keep only recent logs.
        transfers, partial, source = await transfer_sources.transfers(chain, token)
        start = transfers[0]["block"] if transfers else 0
    else:
        start = await block_at(rpc, created_at - 86400, latest) if created_at else 0
        transfers, partial = await all_transfers(rpc, chain, token, start, latest)
        source = "rpc"
    if not transfers:
        raise RuntimeError("no transfers")
    supply = await sync_sells.total_supply(chain, token, rpc)
    # Contracts: every address that received from or sent to many others,
    # plus the biggest holders' own check (a locker holds a lot, trades little).
    _, peak = balances(transfers)
    touch = Counter()
    for t in transfers:
        touch[t["from"]] += 1
        touch[t["to"]] += 1
    probe = list(dict.fromkeys([a for a, _ in sorted(peak.items(), key=lambda x: -x[1])[:TOP_HOLDERS * 2]]
                               + [a for a, n in touch.most_common(40) if n >= 20]))
    progress("holders", None)
    contracts = await _contracts(rpc, [a for a in probe if a not in DEAD])
    live(holders=[{"address": a, "share": round(v / supply, 5) if supply else None}
                  for a, v in sorted(peak.items(), key=lambda x: -x[1]) if a not in contracts and a not in DEAD][:TOP_WATCH],
         counts={"holders": len(peak), "transfers": len(transfers)})
    first_b, last_b = transfers[0]["block"], transfers[-1]["block"]
    anchors = {t["block"]: t["ts"] for t in transfers if t.get("ts") is not None}
    if not anchors:
        for b in {first_b, last_b, *range(first_b, last_b, max(1, (last_b - first_b) // 24))}:
            t = await _block_ts(rpc, b)
            if t is not None:
                anchors[b] = t
    span_b = max(1, max(anchors) - min(anchors))
    block_s = (anchors[max(anchors)] - anchors[min(anchors)]) / span_b
    progress("clusters", None)
    res = cluster(transfers, contracts, supply, block_s)
    live(clusters=[{"id": c["id"], "wallets": c["wallets"], "edges": c.get("edges", []), "links": c.get("links", [])}
                   for c in res["clusters"]], top=res["top"])
    live(counts={**((_running.get(_current.get()) or {}).get("live", {}).get("counts") or {}),
                 "clusters": len(res["clusters"]), "waves": len(res.get("waves") or [])})
    res.update(chain=chain, token=token, symbol=symbol, built_at=int(time.time()), partial=partial,
               from_block=start, to_block=latest, transfers=len(transfers), supply=str(supply),
               contracts=sorted(contracts), block_s=round(block_s, 4),
               coverage={"source": source, "partial": partial, "from_block": first_b, "to_block": last_b,
                         "from_ts": anchors.get(first_b), "transfers": len(transfers)})
    _dir().mkdir(parents=True, exist_ok=True)
    write_text_atomic(_dir() / f"{_key(chain, token)}.json", json.dumps(res))
    if res["clusters"] or len(res["top"]) >= 2:
        progress("sells", None)
        await _hand_to_watch(rpc, res, transfers, anchors, latest)
    return res


async def _build_solana(mint: str, symbol: str) -> dict:
    from app.trading.onchain import solana_clusters
    res = await solana_clusters.build(mint)
    live(clusters=[{"id": c["id"], "wallets": c["wallets"], "edges": c.get("edges", []), "links": c.get("links", [])}
                   for c in res["clusters"]], top=res["top"])
    live(counts={**((_running.get(_current.get()) or {}).get("live", {}).get("counts") or {}),
                 "clusters": len(res["clusters"]), "waves": len(res.get("waves") or [])})
    res.update(chain="solana", token=mint, symbol=symbol, built_at=int(time.time()),
               partial=True, transfers=res["coverage"]["transfers"])
    _dir().mkdir(parents=True, exist_ok=True)
    write_text_atomic(_dir() / f"{_key('solana', mint)}.json", json.dumps(res))
    clusters = [{"id": c["id"], "wallets": c["wallets"], "links": c["links"], "edges": c["edges"]}
                for c in res["clusters"]] + [{"id": "top", "wallets": res["top"], "links": ["top_holders"]}]
    cfg = sync_watch.save({"chain": "solana", "token": mint, "symbol": symbol, "pools": [],
                           "wallets": res["top"], "shares": res["shares"], "clusters": clusters,
                           "source": "auto", "coverage": res["coverage"], "accounts": res["accounts"],
                           "supply": res["supply"], "decimals": res["decimals"]})
    if cfg:
        # The watch starts from today: older sells were not read.
        cfg["state"] = {"last_sig": res["last_sig"]}
        write_text_atomic(sync_watch._dir() / f"{_key('solana', mint)}.json", json.dumps(cfg))
    return res


async def _hand_to_watch(rpc, res: dict, transfers: list[dict], anchors: dict[int, int], latest: int) -> None:
    """The clusters to the sells watch, with the transfers already read, so
    its first run reads only new blocks."""
    clusters = [{"id": c["id"], "wallets": c["wallets"], "links": c["links"], "edges": c["edges"]} for c in res["clusters"]]
    clusters.append({"id": "top", "wallets": res["top"], "links": ["top_holders"]})
    wallets = list(dict.fromkeys(w for c in clusters for w in c["wallets"]))[:sync_watch.MAX_WALLETS]
    if len(wallets) < 2:
        return
    ws = set(wallets)
    mine = [dict(t) for t in transfers if t["from"] in ws]
    cut = time.time() - sync_watch.KEEP_S
    if any(t.get("ts") is None for t in mine):
        await _stamp(rpc, mine, {t["block"] for t in mine}, dict(anchors))
    mine = [t for t in mine if t["ts"] >= cut]
    cfg = sync_watch.save({"chain": res["chain"], "token": res["token"], "symbol": res["symbol"],
                           "pools": res["contracts"], "wallets": wallets,
                           "shares": {w: res["shares"].get(w, 0.0) for w in wallets},
                           "clusters": clusters, "source": "auto", "coverage": res.get("coverage")})
    # An explorer lags the chain by a few blocks: the watch reads them again.
    # A partial history stops long before today: the watch starts near the head
    # (the free RPCs of these chains keep recent logs only).
    nxt = latest + 1 if res.get("coverage", {}).get("source") == "rpc" else max(latest - 300, 0)
    sync_watch.seed(cfg, mine, nxt)


async def run_once(now: float | None = None) -> dict | None:
    """Builds the next queued token, if today's budget allows."""
    if _lock.locked():
        return None
    async with _lock:
        now = now if now is not None else time.time()
        item = _take(now)
        if not item:
            return None
        res = await _build_tracked(item, now)
        if res is None:
            return None
        logger.info("wallet clusters %s %s: %d clusters, %d transfers%s", item["chain"], item.get("symbol"),
                    len(res["clusters"]), res["transfers"], " (partial)" if res["partial"] else "")
        return res


async def _build_tracked(item: dict, now: float) -> dict | None:
    k = item["key"]
    _running[k] = {**(_running.get(k) or {}), "phase": "holders" if item["chain"] == "solana" else "transfers",
                   "progress": None, "started_at": int(time.time()), "chain": item["chain"], "token": item["token"],
                   "symbol": item.get("symbol", ""), "manual": bool(item.get("manual")), "section": item.get("section")}
    note("start", item, "manual" if item.get("manual") else item.get("section") or "")
    tok = _current.set(k)
    try:
        res = await build(item["chain"], item["token"], item.get("symbol", ""), item.get("created_at"))
        if item.get("manual"):
            # The sells now too, not at the watch's next 6-hour turn.
            progress("sells", None)
            for cfg in sync_watch.watched():
                if _key(cfg["chain"], cfg["token"]) == k:
                    await sync_watch.run_all(force=True, only=k)
                    try:
                        rep = json.loads(sync_sells.report_path(item["chain"], item["token"]).read_text())
                        live(events=rep.get("events", [])[:50], risk=(rep.get("risk") or {}).get("score"))
                    except (OSError, ValueError):
                        pass
    except Exception as exc:  # noqa: BLE001
        logger.exception("wallet clusters %s", item["token"])
        _done(item, None, str(exc) or type(exc).__name__, now)
        note("failed", item, (str(exc) or type(exc).__name__)[:120])
        return None
    finally:
        _current.reset(tok)
        _running.pop(k, None)
    _done(item, res, None, now)
    note("done", item, f"{len(res['clusters'])} clusters" + (", partial" if res.get("partial") else ""))
    return res


def start_manual(chain: str, token: str, symbol: str = "") -> bool:
    """Runs a check asked for by hand at once, in its own task. False when it
    is already running or was built within the hour."""
    chain, token = (chain or "").lower(), sync_watch._n(token or "")
    k = _key(chain, token)
    if k in _running:
        return False
    rec = (_state().get("tokens") or {}).get(k) or {}
    if rec.get("built_at") and time.time() - rec["built_at"] < 3600:
        return False
    item = {"key": k, "chain": chain, "token": token, "symbol": str(symbol or "")[:24], "manual": True}
    _running[k] = {"phase": "waiting", "progress": None, "started_at": int(time.time()), "chain": chain,
                   "token": token, "symbol": item["symbol"], "manual": True}
    note("queued", item, "manual")

    async def go():
        async with _manual_sem:
            await _build_tracked(item, time.time())
    asyncio.get_running_loop().create_task(go())
    return True


async def loop(candidates, every_s: int = LOOP_S) -> None:
    """Queues every token the app shows (main._cluster_candidates, most
    important first; "_top" ones rebuilt sooner) and builds one per turn."""
    while True:
        await asyncio.sleep(every_s)
        try:
            cands = candidates()
            dropped = prune({_key((e.get("chain") or "").lower(), sync_watch._n(e.get("token_address") or ""))
                             for e in cands})
            if dropped:
                note("pruned", {}, f"{dropped} tokens no longer in the app")
            for e in cands:
                request(e.get("chain") or "", e.get("token_address") or "", e.get("symbol") or "",
                        e.get("created_at") or e.get("pair_created_at"),
                        rebuild_s=REBUILD_TOP_S if e.get("_top") else None, section=e.get("_section"))
            await run_once()
        except Exception:  # noqa: BLE001
            logger.exception("wallet clusters loop")
