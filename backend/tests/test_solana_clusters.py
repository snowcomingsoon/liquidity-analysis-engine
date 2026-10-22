import asyncio
import json

import pytest

from app.trading.onchain import solana_clusters as sc, storage, sync_sells as ss, sync_watch as sw, wallet_clusters as wc

MINT = "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr"
# On-curve (wallet) owners, case kept: Solana addresses are case-sensitive.
W = ["4ncj9vRi8ZACsJkbts24swLFgcSzvVrNMA2FRnyT4VTL", "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1",
     "6hNRqrwpY44nfKhqNC1NH1eG5pjdMEWD6pCpDCLeCbqn"]
ACC = ["Acc1" + "a" * 40, "Acc2" + "b" * 40, "Acc3" + "c" * 40]


@pytest.fixture(autouse=True)
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sc, "helius_key", lambda: "")
    return tmp_path


def test_same_slot_links():
    assert sc.same_slot_links({"a": 5, "b": 5, "c": 9}) == [("a", "b")]


def test_moves_sell_vs_outflow(monkeypatch):
    monkeypatch.setattr(sc.legit, "is_program_account", lambda o: o == "POOL")

    def tx(gainer):
        return {"slot": 7, "blockTime": 100, "transaction": {"signatures": ["sig"]},
                "meta": {"preTokenBalances": [{"mint": MINT, "owner": W[0], "uiTokenAmount": {"amount": "50"}}],
                         "postTokenBalances": [{"mint": MINT, "owner": W[0], "uiTokenAmount": {"amount": "20"}},
                                               {"mint": MINT, "owner": gainer, "uiTokenAmount": {"amount": "30"}}]}}
    assert sc._moves(tx("POOL"), MINT, W[0])[0] | {} == {"block": 7, "ts": 100, "tx": "sig", "log_index": 0,
                                                         "from": W[0], "to": "pool", "amount": 30}
    assert sc._moves(tx(W[1]), MINT, W[0])[0]["to"] == W[1]
    assert sc._moves(tx(W[1]), MINT, W[1]) == []


def test_build_and_watch_keep_case(data, monkeypatch):
    rep = {"token": {"supply": 1000, "decimals": 6}, "markets": [], "knownAccounts": {},
           "topHolders": [{"owner": o, "address": a, "pct": 10} for o, a in zip(W, ACC)]}

    async def fake_report(mint):
        return rep

    async def fake_sigs(acc, until=None):
        slot = {ACC[0]: 5, ACC[1]: 5, ACC[2]: 9}[acc]
        return [{"signature": acc + "new", "slot": slot + 1}, {"signature": acc + "old", "slot": slot}]

    async def fake_sells(cfg):
        return [{"block": 10, "ts": 2_000_000_000, "tx": "t1", "log_index": 0, "from": W[0], "to": "pool", "amount": 40},
                {"block": 10, "ts": 2_000_000_001, "tx": "t2", "log_index": 0, "from": W[1], "to": "pool", "amount": 40}], {}
    monkeypatch.setattr(sc, "report", fake_report)
    monkeypatch.setattr(sc, "signatures", fake_sigs)
    monkeypatch.setattr(sc, "new_sells", fake_sells)
    monkeypatch.setattr(sc.legit, "is_program_account", lambda o: False)
    monkeypatch.setattr(sw, "KEEP_S", 10**10)
    res = asyncio.run(wc.build("solana", MINT, "X"))
    assert [set(c["wallets"]) for c in res["clusters"]] == [{W[0], W[1]}]
    cfg = sw.watched()[0]
    assert cfg["token"] == MINT and cfg["accounts"][W[0]] == ACC[0] and cfg["state"]["last_sig"][ACC[0]] == ACC[0] + "new"
    asyncio.run(sw.run_all(force=True))
    out = json.loads(ss.report_path("solana", MINT).read_text())
    assert out["token"] == MINT and out["coverage"]["note"].endswith("no transfer links")
    assert out["events"] and out["risk"]["score"] > 0
    assert wc.request("solana", "not-an-address", now=0) is False


def test_sender_links_skip_programs_and_airdrops(monkeypatch):
    monkeypatch.setattr(sc.legit, "is_program_account", lambda o: o == "POOL")
    senders = {W[0]: "POOL", W[1]: "F", W[2]: "F", "X": W[0]}
    links = sc.sender_links(senders, {W[0], W[1], W[2], "X"})
    assert (W[0], "X", "transfer") in links and (W[1], W[2], "same_sender") in links
    drop = {f"h{i}": "D" for i in range(sc.AIRDROP_MIN)}
    assert sc.sender_links(drop, set(drop)) == []


def test_helius_holders_sum_by_owner(monkeypatch):
    monkeypatch.setattr(sc.legit, "is_program_account", lambda o: o == "POOL")

    async def fake_rpc(method, params):
        return {"token_accounts": [{"owner": W[0], "address": ACC[0], "amount": 5},
                                   {"owner": W[0], "address": ACC[2], "amount": 7},
                                   {"owner": "POOL", "address": "P", "amount": 99},
                                   {"owner": W[1], "address": ACC[1], "amount": 3}]}
    monkeypatch.setattr(sc, "_rpc", fake_rpc)
    hs = asyncio.run(sc.helius_holders(MINT, set()))
    assert [(h["owner"], h["account"], h["amount"]) for h in hs] == [(W[0], ACC[2], 12), (W[1], ACC[1], 3)]


def test_helius_errors_never_show_the_key(monkeypatch):
    import httpx

    class Boom(httpx.AsyncClient):
        async def post(self, url, **kw):
            raise httpx.ConnectError(f"failed {url}")
    monkeypatch.setattr(sc.httpx, "AsyncClient", Boom)
    with pytest.raises(RuntimeError) as e:
        asyncio.run(sc._helius("getHealth", [], "SECRETKEY"))
    assert "SECRETKEY" not in str(e.value)
