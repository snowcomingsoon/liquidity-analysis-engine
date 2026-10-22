import asyncio

from app.trading.onchain import sync_sells as ss

S = ss.SAMPLE
W, POOL = S["wallets"], S["pools"][0]
SUPPLY = S["total_supply"]
OTHER = "0x" + "ee" * 20


def t(block, src, dst, pct, ts=None):
    return {"block": block, "ts": ts, "tx": f"0x{block:x}", "from": src, "to": dst,
            "amount": int(SUPPLY * pct / 100)}


def test_same_block_group_scores_high():
    tx = [t(100, w, POOL, 1.0) for w in W] + [t(100, W[0], W[1], 2.0)]
    r = ss.analyze(tx, W, [POOL], SUPPLY)
    assert r["sellers"] == 5 and r["sold_pct"] == 5.0
    assert len(r["groups"]) == 1 and r["groups"][0]["same_block"]
    assert all(e["to"] != W[1] for e in r["timeline"])  # consolidation is not a sale
    assert r["risk"]["level"] == "high"


def test_window_by_blocks_and_seconds():
    tx = [t(100, W[0], POOL, 0.5, ts=1000), t(103, W[1], POOL, 0.5, ts=1006),
          t(400, W[2], POOL, 0.5, ts=1100), t(9000, W[3], POOL, 0.5, ts=50_000)]
    groups = ss.analyze(tx, W, [POOL], SUPPLY)["groups"]
    assert [g["wallets"] for g in groups] == [sorted(W[:3])]
    assert not groups[0]["same_block"]


def test_lone_seller_and_outflow_weight():
    assert ss.analyze([t(1, W[0], POOL, 3.0)], W, [POOL], SUPPLY)["risk"]["score"] == 0
    sell = ss.analyze([t(1, W[0], POOL, 1.0), t(1, W[1], POOL, 1.0)], W, [POOL], SUPPLY)
    out = ss.analyze([t(1, W[0], OTHER, 1.0), t(1, W[1], OTHER, 1.0)], W, [POOL], SUPPLY)
    assert out["outflow_pct"] == 2.0 and out["risk"]["parts"]["share"] < sell["risk"]["parts"]["share"]


def test_run_with_fake_rpc(monkeypatch):
    monkeypatch.setattr(ss, "CHUNK", {})
    def topic(a):
        return "0x" + "0" * 24 + a[2:]
    logs = [{"blockNumber": "0x64", "logIndex": hex(i), "transactionHash": f"0x{i}",
             "topics": [ss.TRANSFER_TOPIC, topic(w), topic(POOL)], "data": hex(SUPPLY // 100)}
            for i, w in enumerate(W[:3])]
    calls = []

    async def rpc(method, params):
        calls.append(method)
        if method == "eth_getLogs":
            assert params[0]["topics"][1] and params[0]["address"] == S["token"]
            return logs if params[0]["fromBlock"] == "0x0" else []
        if method == "eth_getBlockByNumber":
            return {"timestamp": "0x10"}
        return hex(SUPPLY)

    r = asyncio.run(ss.run("robinhood", S["token"], W, [POOL], 0, 6_000, rpc=rpc))
    assert calls.count("eth_getLogs") == 2 and calls.count("eth_getBlockByNumber") == 1
    assert r["sold_pct"] == 3.0 and r["timeline"][0]["ts"] == 16 and r["groups"][0]["same_block"]


def test_report_v1_and_write(tmp_path, monkeypatch):
    import json
    from app.trading.onchain import storage
    tx = [t(100, w, POOL, 1.0, ts=1000 + i) for i, w in enumerate(W[:3])] + [t(100, W[4], POOL, 1.0, ts=1000)]
    clusters = [{"id": "c1", "wallets": W[:3], "links": ["same_funder"]}, {"id": "c2", "wallets": W[3:]}]
    rep = ss.report("robinhood", S["token"].upper().replace("0X", "0x"), tx, clusters, [POOL], SUPPLY,
                    symbol="XYZ", shares={W[0]: 0.02, W[1]: 0.01}, now=2000)
    assert rep["version"] == 1 and rep["token"] == S["token"] and rep["updated_at"] == 2000
    c1, c2 = rep["clusters"]
    assert c1["share"] == 0.03 and c1["links"] == ["same_funder", "same_block_sells"] and c2["risk"] == 0
    [ev] = rep["events"]
    assert ev.pop("sellers") == sorted(W[:3])
    assert ev == {"id": "c1-1000", "cluster": "c1", "ts": 1000, "window_s": 2, "wallets": 3,
                  "share_sold": 0.03, "txs": ["0x64"] * 3}
    assert rep["risk"]["score"] == c1["risk"] > 0 and rep["risk"]["reasons"]
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    ss.write_report(rep)
    assert json.loads((tmp_path / "coordinated_sells" / f"robinhood-{S['token']}.json").read_text()) == rep


def test_structure_risk_counts_supply_in_linked_clusters():
    from app.trading.onchain import sync_sells as m
    a, b, c = ("0x" + x * 40 for x in "abc")
    rep = m.report("robinhood", "0x" + "1" * 40, [], [{"id": "a1", "wallets": [a, b]}, {"id": "top", "wallets": [c]}],
                   [], 10**9, shares={a: 0.10, b: 0.08, c: 0.5})
    assert rep["risk"]["structure"] == {"score": 60, "share": 0.18}
    assert rep["risk"]["score"] == 60 and "18.0%" in rep["risk"]["reasons"][0]
