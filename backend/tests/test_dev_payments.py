import asyncio

import pytest

from app.trading.onchain import dev_payments as dp, solana_clusters, storage

MINT = "Mint1111111111111111111111111111111111pump"
FEE = "Fee11111111111111111111111111111111111111"
DEV = "Dev11111111111111111111111111111111111111"
DEV_ATA = "DevAta111111111111111111111111111111111111"
POOL = "Pool1111111111111111111111111111111111111"
VAULT = "Vau1t111111111111111111111111111111111111"
FRIEND = "Friend1111111111111111111111111111111111"


@pytest.fixture(autouse=True)
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(solana_clusters, "helius_key", lambda: "")
    return tmp_path


def tx(ts, sol=None, tok=None, logs=()):
    """sol: {account: lamports delta}; tok: {owner: (mint, pre, post)}."""
    sol = sol or {}
    keys = list(sol) or [DEV]
    pre = [10**10 for _ in keys]
    post = [p + sol.get(k, 0) for p, k in zip(pre, keys)]
    tb = lambda i: [{"accountIndex": n, "mint": m, "owner": o, "uiTokenAmount": {"uiAmountString": str(v[i])}}  # noqa: E731
                    for n, (o, (m, *v)) in enumerate((tok or {}).items())]
    return {"blockTime": ts, "transaction": {"message": {"accountKeys": [{"pubkey": k} for k in keys]}},
            "meta": {"preBalances": pre, "postBalances": post, "preTokenBalances": tb(0),
                     "postTokenBalances": tb(1), "logMessages": [f"Program log: Instruction: {x}" for x in logs]}}


def test_fee_account_payment_and_claim():
    pay = dp.fee_moves(tx(100, {VAULT: -2 * 10**9, FEE: 2 * 10**9}, logs=["DistributeCreatorFees"]), "s1", FEE)
    claim = dp.fee_moves(tx(200, {FEE: -2 * 10**9, DEV: 2 * 10**9}, logs=["ClaimSocialFeePdaV2"]), "s2", FEE)
    assert pay == [{"id": "s1", "ts": 100, "kind": "fee", "sol": 2.0, "account": FEE}]
    assert claim[0]["kind"] == "claim" and claim[0]["to"] == DEV and claim[0]["sol"] == 2.0
    assert dp.fee_moves(tx(1, {FEE: 5}), "s3", FEE) == []          # dust


def test_wallet_sell_buy_and_transfer():
    sell = tx(10, {DEV: 3 * 10**9, POOL: -3 * 10**9}, {DEV: (MINT, 1000, 400), POOL: (MINT, 0, 600)}, ["Sell"])
    (e,) = dp.wallet_moves(sell, "a", DEV, MINT)
    assert (e["kind"], e["amount"], e["sol"], e["other"]) == ("sell", 600, 3.0, POOL)
    move = tx(11, {DEV: -5000}, {DEV: (MINT, 400, 100), FRIEND: (MINT, 0, 300)}, ["Transfer"])
    assert dp.wallet_moves(move, "b", DEV, MINT)[0]["kind"] == "transfer_out"
    order = tx(11, {DEV: -5000}, {DEV: (MINT, 400, 100), FRIEND: (MINT, 0, 300)}, ["CreateLimitOrder", "Transfer"])
    assert dp.wallet_moves(order, "o", DEV, MINT)[0]["kind"] == "limit_sell"
    buy = tx(12, {DEV: -10**9, POOL: 10**9}, {DEV: (MINT, 100, 900)}, ["Buy"])
    assert dp.wallet_moves(buy, "c", DEV, MINT)[0]["kind"] == "buy"
    assert dp.wallet_moves(tx(13, {DEV: 10**9}), "d", DEV, MINT) == []


def test_save_rejects_bad_input_and_keeps_state():
    with pytest.raises(ValueError):
        dp.save({"token": "../x", "fee_accounts": [FEE]})
    with pytest.raises(ValueError):
        dp.save({"token": MINT, "fee_accounts": []})
    dp.save({"token": MINT, "symbol": "DREGG", "fee_accounts": [FEE]})
    assert dp.configs()[0]["symbol"] == "DREGG"
    assert dp.report("../../etc") is None


def test_run_finds_claimer_reads_sells_and_alerts_once(monkeypatch):
    now = 1_000_000
    txs = {
        "p1": tx(now - 3000, {VAULT: -10**9, FEE: 10**9}),
        "p2": tx(now - 2000, {VAULT: -3 * 10**9, FEE: 3 * 10**9}),
        "c1": tx(now - 1000, {FEE: -4 * 10**9, DEV: 4 * 10**9}),
        "s1": tx(now - 500, {DEV: 2 * 10**9, POOL: -2 * 10**9}, {DEV: (MINT, 1000, 0), POOL: (MINT, 0, 1000)}, ["Sell"]),
    }
    sigs = {FEE: ["c1", "p2", "p1"], DEV_ATA: ["s1"]}

    async def rpc(method, params):
        if method == "getSignaturesForAddress":
            return [{"signature": s} for s in sigs[params[0]]]
        if method == "getTransaction":
            return txs[params[0]]
        if method == "getTokenAccountsByOwner":
            assert params[0] == DEV and params[1] == {"mint": MINT}
            return {"value": [{"pubkey": DEV_ATA, "account": {"data": {"parsed": {"info": {"tokenAmount": {"uiAmountString": "0"}}}}}}]}
        raise AssertionError(method)

    monkeypatch.setattr(solana_clusters, "_rpc", rpc)
    monkeypatch.setattr(dp.time, "time", lambda: now)
    dp.save({"token": MINT, "symbol": "DREGG", "fee_accounts": [FEE]})
    rep = asyncio.run(dp.run(dp.configs()[0], now=now))
    assert rep["fees"]["total"] == 4.0 and rep["fees"]["count"] == 2 and rep["claims"]["unclaimed"] == 0
    (c,) = rep["claimers"]
    assert c["address"] == DEV and c["sold"] == 1000 and c["sold_sol"] == 2.0 and c["holding"] == 0

    sent = []

    async def send(text):
        sent.append(text)
        return True

    assert asyncio.run(dp.notify_once(send, "https://x/app", now=now)) == 1
    assert "venduto" in sent[0] and "1.000 DREGG" in sent[0]
    assert asyncio.run(dp.notify_once(send, "https://x/app", now=now)) == 0

    # The next run reads only what is new (cursors), and keeps the history.
    sigs[FEE] = []
    sigs[DEV_ATA] = []
    rep = asyncio.run(dp.run(dp.configs()[0], now=now + 60))
    assert rep["fees"]["total"] == 4.0 and rep["claimers"][0]["sells"] == 1
