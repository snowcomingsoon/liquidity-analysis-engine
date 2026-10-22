import asyncio
import json

import pytest

from app.trading.onchain import storage, sync_sells as ss, sync_watch as sw, wallet_clusters as wc

TOKEN = "0x" + "77" * 20
POOL = "0x" + "a0" * 20
T0 = 1_800_000_000


def w(i: int) -> str:
    return "0x" + f"{i:040x}"


@pytest.fixture(autouse=True)
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    return tmp_path


def tr(block, src, dst, amount, i=0):
    return {"block": block, "tx": f"0x{block:x}{i}", "log_index": i, "from": src, "to": dst, "amount": amount}


def market():
    """A pool minted the supply; 40 buyers spread over time; wallets 1-2
    pass tokens to each other, 3 feeds 4 and 5, 6-10 buy in one block."""
    zero, out = "0x" + "0" * 40, []
    out.append(tr(1, zero, POOL, 10**9))
    for i in range(11, 51):
        out.append(tr(100 * i, POOL, w(i), 1000 + i))
    out += [tr(200, POOL, w(1), 50_000), tr(9000, POOL, w(2), 40_000), tr(9100, w(1), w(2), 5_000, 1)]
    out += [tr(300, POOL, w(3), 60_000), tr(310, w(3), w(4), 20_000, 1), tr(320, w(3), w(5), 20_000, 1)]
    out += [tr(7000, POOL, w(i), 30_000, i) for i in range(6, 11)]
    return sorted(out, key=lambda t: (t["block"], t["log_index"]))


def test_clusters_by_transfer_sender_and_wave():
    res = wc.cluster(market(), {POOL}, 10**9, block_s=1.0, top_n=10)
    sets = [set(c["wallets"]) for c in res["clusters"]]
    assert {w(1), w(2)} in sets
    assert {w(3), w(4), w(5)} in sets
    assert {w(i) for i in range(6, 11)} in sets
    assert all(POOL not in s for s in sets)
    assert res["top"][0] == w(3)


def test_airdrop_sender_links_nobody():
    out = [tr(1, "0x" + "0" * 40, w(99), 10**9)] + [tr(10 + i, w(99), w(i), 500, i) for i in range(1, 30)]
    res = wc.cluster(out, set(), 10**9, block_s=1.0)
    assert res["clusters"] == []


def test_launch_burst_is_not_a_wave():
    # Every buyer comes in the same few blocks: the top ones too, by chance.
    out = [tr(1, "0x" + "0" * 40, POOL, 10**9)] + [tr(100 + i % 5, POOL, w(i), 1000 + i, i) for i in range(1, 60)]
    res = wc.cluster(out, {POOL}, 10**9, block_s=1.0, top_n=10)
    assert res["clusters"] == []


def test_7702_delegation_is_a_wallet():
    assert not wc._is_contract("0xef0100" + "ab" * 20)
    assert not wc._is_contract("0x")
    assert wc._is_contract("0x6080604052")


class FakeChain:
    def __init__(self, transfers, contracts):
        self.t, self.c, self.calls = transfers, contracts, 0

    async def __call__(self, method, params):
        self.calls += 1
        if method == "eth_blockNumber":
            return hex(10_000)
        if method == "eth_getBlockByNumber":
            return {"timestamp": hex(T0 + int(params[0], 16))}
        if method == "eth_getCode":
            return "0x60806040" if params[0] in self.c else "0x"
        if method == "eth_call":
            return hex(10**9)
        if method == "eth_getLogs":
            f = params[0]
            a, b = int(f["fromBlock"], 16), int(f["toBlock"], 16)
            if b - a > 4000:
                raise RuntimeError("RPC robinhood (eth_getLogs): block range too large")
            senders = f["topics"][1] if len(f["topics"]) > 1 else None
            return [{"blockNumber": hex(x["block"]), "transactionHash": x["tx"], "logIndex": hex(x["log_index"]),
                     "topics": [ss.TRANSFER_TOPIC, "0x" + "0" * 24 + x["from"][2:], "0x" + "0" * 24 + x["to"][2:]],
                     "data": hex(x["amount"])}
                    for x in self.t if a <= x["block"] <= b
                    and (senders is None or "0x" + "0" * 24 + x["from"][2:] in senders)]
        raise AssertionError(method)


def test_build_saves_on_volume_and_feeds_the_watch(data, monkeypatch):
    monkeypatch.setattr(sw, "KEEP_S", 10**10)
    rpc = FakeChain(market(), {POOL})
    monkeypatch.setattr(ss, "_default_rpc", lambda chain: rpc)
    res = asyncio.run(wc.build("robinhood", TOKEN, "TEST", rpc=rpc))
    assert not res["partial"] and res["transfers"] == len(market())
    assert (data / "wallet_clusters" / f"robinhood-{TOKEN}.json").exists()
    cfg = sw.watched()[0]
    assert cfg["source"] == "auto" and cfg["state"]["next_block"] == 10_001
    assert {c["id"] for c in cfg["clusters"]} >= {"a1", "top"}
    seeded = json.loads((data / "coordinated_sells_watch" / f"robinhood-{TOKEN}.transfers.json").read_text())
    assert seeded and all(t["ts"] == T0 + t["block"] for t in seeded)
    # The first watch run reads no old block again.
    before = rpc.calls
    asyncio.run(sw.run_all(force=True))
    assert rpc.calls - before <= 4
    rep = json.loads(ss.report_path("robinhood", TOKEN).read_text())
    assert {c["id"] for c in rep["clusters"]} >= {"a1", "top"}


def test_auto_never_replaces_an_upload(data):
    sw.save({"chain": "robinhood", "token": TOKEN, "wallets": [w(1), w(2)], "pools": [POOL]})
    assert sw.save({"chain": "robinhood", "token": TOKEN, "wallets": [w(3), w(4)], "source": "auto"}) is None
    assert sw.watched()[0]["wallets"] == [w(1), w(2)]


def test_queue_budget_and_cache(data):
    now = 1_900_000_000.0
    assert wc.request("robinhood", TOKEN, now=now)
    assert not wc.request("robinhood", TOKEN, now=now)          # already queued
    assert not wc.request("solana", "So1111", now=now)          # no source
    assert not wc.request("arbitrum", TOKEN, now=now)
    other = "0x" + "88" * 20
    assert wc.request("robinhood", other, urgent=True, now=now)
    assert wc._take(now)["token"] == other                       # by hand: first in line
    wc._done({"key": wc._key("robinhood", other)}, {"clusters": [], "partial": False}, None, now)
    assert not wc.request("robinhood", other, now=now + 3600)    # built: cached a week
    st = wc._state()
    st["built_today"] = wc.MAX_PER_DAY
    wc._save_state(st)
    assert wc._take(now) is None                                 # today's budget spent


def test_edges_and_sellers_reach_the_report(data, monkeypatch):
    monkeypatch.setattr(sw, "KEEP_S", 10**10)
    rpc = FakeChain(market() + [tr(9500, w(1), POOL, 100, 1), tr(9500, w(2), POOL, 100, 2)], {POOL})
    monkeypatch.setattr(ss, "_default_rpc", lambda chain: rpc)
    asyncio.run(wc.build("robinhood", TOKEN, "TEST", rpc=rpc))
    asyncio.run(sw.run_all(force=True))
    from app.trading.onchain import coordinated_sells as cs
    rep = cs.clean(json.loads(ss.report_path("robinhood", TOKEN).read_text()))
    pairs = {tuple(e) for c in rep["clusters"] for e in c["edges"]}
    assert (w(1), w(2)) in pairs
    assert any({w(1), w(2)} <= set(e["sellers"]) for e in rep["events"])


def test_explorer_pages_and_partial(monkeypatch):
    import httpx
    from app.trading.onchain import transfer_sources as ts
    monkeypatch.setattr(ts, "PAGE", 3)
    monkeypatch.setattr(ts, "MAX_PAGES", 3)
    monkeypatch.setattr(ts, "PAUSE_S", 0)
    rows = [{"blockNumber": str(b), "timeStamp": str(T0 + b), "hash": f"0x{b}", "transactionIndex": "0",
             "from": w(1), "to": w(2), "value": str(b)} for b in range(1, 12)]
    calls = []

    def handler(req):
        if "blockscout" in str(req.url):
            return httpx.Response(403)
        start = int(req.url.params["startblock"])
        calls.append(start)
        return httpx.Response(200, json={"message": "OK", "result": [r for r in rows if int(r["blockNumber"]) >= start][:3]})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await ts.transfers("ethereum", TOKEN, c)
    out, partial, source = asyncio.run(go())
    assert source == "api.routescan.io" and partial
    assert [t["block"] for t in out] == [1, 2, 3, 4, 5, 6, 7]   # last block of each page read again
    assert out[0]["ts"] == T0 + 1


def test_build_from_explorer_marks_coverage(data, monkeypatch):
    monkeypatch.setattr(sw, "KEEP_S", 10**10)
    rpc = FakeChain([], {POOL})
    hist = [dict(t, ts=T0 + t["block"]) for t in market()]

    async def fake(chain, token):
        return hist, True, "eth.blockscout.com"
    from app.trading.onchain import transfer_sources as ts
    monkeypatch.setattr(ts, "transfers", fake)
    res = asyncio.run(wc.build("ethereum", TOKEN, "TEST", rpc=rpc))
    assert res["coverage"]["partial"] and res["coverage"]["source"] == "eth.blockscout.com"
    cfg = sw.watched()[0]
    assert cfg["coverage"]["partial"] and cfg["state"]["next_block"] == 10_000 - 300
