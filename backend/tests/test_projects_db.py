"""The Gem Finder's project database. Request: "il gem hunter deve trovare
progetti di qualita', ma vedi sempre i soliti... ma fatti un database no?"."""
from __future__ import annotations

import pytest

from app.trading.onchain import discovery, projects_db as db
from app.trading.onchain import leaderboard as lb

T0 = 1_790_000_000.0
D = 86400.0


@pytest.fixture(autouse=True)
def _clean():
    lb.reset_for_tests()
    yield
    lb.reset_for_tests()


def _pair(token, cap, liq, vol=5_000):
    return {"baseToken": {"address": token}, "marketCap": cap, "liquidity": {"usd": liq},
            "volume": {"h24": vol}, "priceUsd": "0.01", "pairCreatedAt": (T0 - 90 * D) * 1000}


def test_upsert_merges_sources_and_never_erases_known_fields():
    assert db.upsert({"chain": "solana", "token_address": "A", "symbol": "AAA", "website": "https://a.io"}, "jupiter", T0)
    assert not db.upsert({"chain": "solana", "token_address": "A", "symbol": "?", "github": "https://github.com/a/a"},
                         "coingecko", T0 + 1)
    p = db.get("solana", "A")
    assert p["symbol"] == "AAA" and p["website"] == "https://a.io" and p["github"] == "https://github.com/a/a"
    assert p["sources"] == ["jupiter", "coingecko"] and p["first_seen"] == T0 and p["last_seen"] == T0 + 1


def test_global_cap_keeps_a_bridged_copy_out_of_the_band():
    db.upsert({"chain": "solana", "token_address": "AAVEmint", "symbol": "AAVE", "name": "Aave",
               "cg_id": "aave", "market_cap": 531_000, "liquidity_usd": 900_000}, "coingecko-list", T0)
    assert [p["symbol"] for p in db.search("", "", "score", 50, 0, True)["items"]] == ["AAVE"]
    db.mark_detail("solana", "aave", T0, 2_000_000_000)
    assert db.search("", "", "score", 50, 0, True)["items"] == []
    db.reject_cg("solana", "aave", "global market cap $2,000,000,000", T0)
    assert db.get("solana", "AAVEmint")["status"] == "rejected"


def test_coingecko_list_fills_the_universe_and_market_puts_it_in_band():
    rows = [{"id": "alpha", "symbol": "alp", "name": "Alpha", "platforms": {"solana": "AlphaMint"}},
            {"id": "eth", "symbol": "e", "name": "E", "platforms": {"arbitrum": "0x1"}},
            {"id": "rh", "symbol": "r", "name": "R", "platforms": {"robinhood": "0xabc"}}]
    assert db.upsert_many(discovery.universe(rows), "coingecko-list", T0) == 2
    assert db.stale_market(10, T0) == {"solana": ["AlphaMint"], "robinhood": ["0xabc"]}
    db.apply_pairs("solana", ["AlphaMint"], [_pair("AlphaMint", 800_000, 60_000)], T0)
    db.apply_pairs("robinhood", ["0xabc"], [], T0)
    assert db.stale_market(10, T0 + 60) == {}
    assert db.get("solana", "AlphaMint")["mcap"] == 800_000
    assert [b["id"] for b in db.need_detail(10, T0)] == ["alpha"]
    db.mark_detail("solana", "alpha", T0)
    assert db.need_detail(10, T0 + 60) == []


def test_due_for_analysis_needs_band_and_something_to_read_code_first():
    for tok, cap, liq, site, gh in [("A", 500_000, 50_000, "https://a.io", None),
                                     ("B", 400_000, 20_000, "https://b.io", "https://github.com/b/b"),
                                     ("C", 90_000_000, 5e6, "https://c.io", None),
                                     ("D", 300_000, 30_000, None, None)]:
        db.upsert({"chain": "solana", "token_address": tok, "symbol": tok, "website": site, "github": gh,
                   "market_cap": cap, "liquidity_usd": liq}, "x", T0)
    assert [p["token"] for p in db.due_for_analysis(10, now=T0)] == ["B", "A"]
    assert [p["token"] for p in db.due_for_analysis(10, {"solana:B"}, T0)] == ["A"]


def test_rejection_is_remembered_and_rechecked_later():
    db.upsert({"chain": "solana", "token_address": "A", "symbol": "A", "website": "https://a.io",
               "market_cap": 500_000, "liquidity_usd": 50_000}, "x", T0)
    e = {"chain": "solana", "token_address": "A", "pillars": {"github": {"score": 0}}, "overall": {"fatal": "x"}}
    db.record(e, "rejected", "github: A is a fork", now=T0)
    assert db.due_for_analysis(10, now=T0 + D) == []
    assert [p["token"] for p in db.due_for_analysis(10, now=T0 + db.RECHECK_S + 1)] == ["A"]
    db.record(e, "rejected", "site: website unreachable", now=T0)
    assert db.due_for_analysis(10, now=T0 + db.RECHECK_DATA_S + 1)
    s = db.stats()
    assert s["total"] == 1 and s["by_status"] == {"rejected": 1} and s["top_rejections"][0]["n"] == 1


def test_board_takes_work_from_the_database_and_writes_verdicts_back():
    db.upsert({"chain": "solana", "token_address": "Gem", "symbol": "GEM", "name": "Gem Labs",
               "website": "https://gem.io", "market_cap": 900_000, "liquidity_usd": 80_000,
               "launched_at": T0 - 100 * D}, "coingecko", T0)
    db.upsert({"chain": "solana", "token_address": "Frog", "symbol": "PEPEFROG", "name": "Pepe Frog Inu",
               "website": "https://frog.io", "market_cap": 900_000, "liquidity_usd": 80_000}, "coingecko", T0)
    assert lb.feed_from_database(T0) == 1
    assert "solana:Gem" in lb._entries and lb._entries["solana:Gem"]["source"] == "database"
    assert db.get("solana", "Frog")["status"] == "rejected"
    lb.apply_analysis("solana:Gem", {"github": {"key": "github", "score": 0, "facts": {}, "flags": [],
                                                "fatal": "empty repository"}}, T0 + 60)
    p = db.get("solana", "Gem")
    assert p["status"] == "rejected" and "empty repository" in p["why"]
    # A rejected project comes back when the database says it is time.
    lb._entries.clear()
    assert lb.add(db.as_item(p), "coingecko", T0 + 120) is False
    assert lb.add(db.as_item(p), "database", T0 + db.RECHECK_S) is True


def test_search_filters_and_sorts():
    for tok, sc in [("A", 80.0), ("B", 60.0), ("C", None)]:
        db.upsert({"chain": "solana", "token_address": tok, "symbol": f"S{tok}", "name": f"Name {tok}"}, "x", T0)
        if sc is not None:
            db.record({"chain": "solana", "token_address": tok}, "studied", "GitHub only 50", sc, now=T0)
    r = db.search(sort="score")
    assert [i["token"] for i in r["items"]] == ["A", "B", "C"] and r["total"] == 3
    assert [i["token"] for i in db.search(q="Name B")["items"]] == ["B"]
    assert db.search(status="studied")["total"] == 2
def test_recheck_studied_requeues_old_limits(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "projects.db")
    monkeypatch.setattr(db, "_conn", None)
    db._db().execute(
        "INSERT INTO projects (key, chain, token, symbol, status, why, next_check, first_seen, last_seen) VALUES"
        " ('solana:A', 'solana', 'A', 'A', 'studied', 'market cap over $3M', 9999999999, 0, 0),"
        " ('solana:B', 'solana', 'B', 'B', 'studied', 'launched over 400 days ago', 9999999999, 0, 0),"
        " ('solana:C', 'solana', 'C', 'C', 'studied', 'no website', 9999999999, 0, 0),"
        " ('solana:D', 'solana', 'D', 'D', 'rejected', 'market cap over $3M', 9999999999, 0, 0)")
    db._db().commit()
    n = db.recheck_studied(("over $%", "over % days%"))
    assert n == 2
    rows = {r["token"]: r["next_check"] for r in db._db().execute(
        "SELECT token, next_check FROM projects").fetchall()}
    assert rows["A"] == 0 and rows["B"] == 0 and rows["C"] != 0 and rows["D"] != 0
    # Rules dropped outright (29/09) requeue rejected rows too.
    assert db.recheck_studied(("over $3M",), ("studied", "rejected")) == 2
    assert db._db().execute("SELECT next_check FROM projects WHERE token = 'D'").fetchone()[0] == 0


def test_search_filters_by_narrative():
    db.upsert({"chain": "solana", "token_address": "A", "symbol": "AAA"}, "t", T0)
    db.upsert({"chain": "solana", "token_address": "B", "symbol": "BBB"}, "t", T0)
    db.upsert({"chain": "solana", "token_address": "C", "symbol": "CCC"}, "t", T0)
    db.set_narratives("solana", "A", ["rwa", "depin"], T0)
    db.set_narratives("solana", "B", ["meme_dogs"], T0)
    assert [p["symbol"] for p in db.search(narrative="rwa")["items"]] == ["AAA"]
    assert sorted(p["symbol"] for p in db.search(narrative="meme_dogs,depin")["items"]) == ["AAA", "BBB"]
    assert db.search(narrative="meme_cats")["total"] == 0


def test_record_keeps_mapped_narratives():
    db.upsert({"chain": "solana", "token_address": "A", "symbol": "AAA"}, "t", T0)
    db.set_narratives("solana", "A", ["rwa"], T0)
    db.record({"chain": "solana", "token_address": "A", "narratives": ["depin"]}, "studied", score=50, now=T0)
    assert db.search(narrative="rwa")["total"] == 1 and db.search(narrative="depin")["total"] == 1


def test_migration_adds_narr_at(monkeypatch, tmp_path):
    import sqlite3
    path = tmp_path / "old.db"
    c = sqlite3.connect(path)
    c.executescript(db._SCHEMA.replace(",\n    narr_at REAL", ""))  # the table as it was before
    c.commit()
    c.close()
    monkeypatch.setattr(db, "_DB_FILE", path)
    cols = {r[1] for r in db._db().execute("PRAGMA table_info(projects)")}
    assert {"narr_at", "cg_mcap"} <= cols


def test_full_working_set_makes_room_for_a_waiting_project(monkeypatch):
    """400 places went to whoever came first and the feed stopped for good (AUREON, 29/09)."""
    monkeypatch.setattr(lb, "MAX_ENTRIES", 2)
    for tok in ("Old1", "Old2"):
        item = {"chain": "solana", "token_address": tok, "symbol": tok.upper(), "name": tok, "website": "https://x.io",
                "market_cap": 900_000, "liquidity_usd": 80_000}
        db.upsert(item, "x", T0)
        lb.add(item, "x", T0)
        lb._entries[f"solana:{tok}"]["pillars"] = {"site": {"score": 60 if tok == "Old1" else 80, "facts": {}}}
        lb._entries[f"solana:{tok}"]["overall"] = {"score": 60}
    db.upsert({"chain": "solana", "token_address": "New", "symbol": "NEWCO", "name": "Newco", "website": "https://n.io",
               "market_cap": 900_000, "liquidity_usd": 80_000}, "coingecko", T0)
    assert lb.feed_from_database(T0) == 1
    assert "solana:New" in lb._entries and len(lb._entries) == 2
    gone = "solana:Old1" if "solana:Old1" not in lb._entries else "solana:Old2"
    assert db.get("solana", gone.split(":")[1])["status"] == "studied"


def test_search_filters_by_chain_and_layer_type():
    db.upsert({"chain": "solana", "token_address": "A", "symbol": "AAA"}, "t", T0)
    for gid, sym, layer in (("kaspa", "KAS", "L1"), ("zeta", "ZETA", "L0"), ("mantle", "MNT", "L2")):
        item = {"chain": "layer", "token_address": gid, "symbol": sym}
        db.upsert(item, "layers", T0)
        db.record({**item, "overall": {"score": 50, "layer": layer}}, "studied", score=50, now=T0)
    assert [p["symbol"] for p in db.search(layer="L1")["items"]] == ["KAS"]
    assert db.search(layer="L1")["items"][0]["overall"]["layer"] == "L1"
    assert db.search(chain="layer")["total"] == 3
    assert [p["symbol"] for p in db.search(chain="solana")["items"]] == ["AAA"]
    assert db.search(layer="L9")["total"] == 4
    assert db.stats()["by_layer"] == {"L0": 1, "L1": 1, "L2": 1}


def test_rescore_and_requeue_touch_only_their_rows():
    for t in ("S", "R", "D", "F"):
        db.upsert({"chain": "solana", "token_address": t, "symbol": t, "website": f"https://{t}.io"}, "jupiter", T0)
    e = lambda t: {"chain": "solana", "token_address": t}  # noqa: E731
    db.record(e("S"), "studied", "volume $712 a day", 90.0, now=T0)
    db.record(e("R"), "ranked", "", 80.0, now=T0)
    db.record(e("D"), "rejected", "DeepSeek: no product", now=T0)
    db.record(e("F"), "rejected", "honeypot", now=T0)
    assert {r["token"] for r in db.scored_rows()} == {"S", "R"}
    assert db.rescore_many([("solana:S", 61.5, ""), ("solana:F", 99.0, "x")]) == 1
    assert db.get("solana", "S")["score"] == 61.5 and db.get("solana", "S")["why"] is None
    assert db.get("solana", "F")["score"] is None
    assert db.requeue(("studied", "ranked")) == 2 and db.requeue(("rejected",), ("DeepSeek",)) == 1
    assert db.get("solana", "F")["next_check"] > 0 and db.get("solana", "D")["next_check"] == 0


def test_band_reaches_the_board_ceiling_and_the_funnel_counts_inside_it():
    # Lorenzo, 07/10: "ce ne mancano tanti". The database band stopped at $3M
    # while the board takes up to $10M, and by_status counted every row.
    db.upsert({"chain": "solana", "token_address": "Mid", "symbol": "MID", "website": "https://mid.io",
               "market_cap": 6_000_000, "liquidity_usd": 80_000}, "x", T0)
    db.upsert({"chain": "solana", "token_address": "Big", "symbol": "BIG", "website": "https://big.io",
               "market_cap": 40_000_000, "liquidity_usd": 80_000}, "x", T0)
    assert [p["token"] for p in db.due_for_analysis(10, now=T0)] == ["Mid"]
    db.record({"chain": "solana", "token_address": "Big"}, "rejected", "over $10M", now=T0)
    s = db.stats()
    assert s["in_band"] == 1 and s["band_by_status"] == {"new": 1} and s["band_waiting"] == 1
    assert s["by_status"] == {"new": 1, "rejected": 1} and s["band"] == [db.CAP_MIN, db.CAP_MAX]


def test_linkless_rows_get_a_verdict_and_return_when_links_appear():
    db.upsert({"chain": "solana", "token_address": "Bare", "symbol": "BARE",
               "market_cap": 500_000, "liquidity_usd": 50_000}, "x", T0)
    assert db.due_for_analysis(10, now=T0) == []
    assert db.reject_linkless(T0) == 1
    p = db.get("solana", "Bare")
    assert p["status"] == "rejected" and p["why"] == db.NO_LINKS
    assert db.stats()["band_waiting"] == 0
    db.apply_pairs("solana", ["Bare"], [{**_pair("Bare", 500_000, 50_000),
                                          "info": {"websites": [{"url": "https://bare.io"}]}}], T0 + 60)
    assert [p["token"] for p in db.due_for_analysis(10, now=T0 + 60)] == ["Bare"]


def test_one_evm_contract_is_one_project_whatever_the_case():
    """PRIORS entered twice, checksummed and lowercase (Lorenzo, 19/10)."""
    mixed, low = "0xAbCdEf0000000000000000000000000000000001", "0xabcdef0000000000000000000000000000000001"
    assert lb.add({"chain": "base", "token_address": mixed, "symbol": "PRIORS"}, "jupiter", T0)
    assert not lb.add({"chain": "base", "token_address": low, "symbol": "Priors Agents"}, "coingecko", T0 + 1)
    assert list(lb._entries) == [f"base:{low}"] and lb._entries[f"base:{low}"]["token_address"] == low
    assert db.get("base", mixed)["token"] == low
    # Solana addresses are case-sensitive: two spellings are two tokens.
    assert db.upsert({"chain": "solana", "token_address": "AbC"}, "jupiter", T0)
    assert db.upsert({"chain": "solana", "token_address": "abc"}, "jupiter", T0)


def test_mixed_case_rows_merge_into_the_lowercase_one(monkeypatch, tmp_path):
    import sqlite3
    path = tmp_path / "old.db"
    c = sqlite3.connect(path)
    c.executescript(db._SCHEMA)
    rows = [("base:0xAB", "base", "0xAB", "ranked", 70), ("base:0xab", "base", "0xab", "rejected", None),
            ("bsc:0xCD", "bsc", "0xCD", "studied", 60)]
    c.executemany("INSERT INTO projects (key, chain, token, status, score, first_seen, last_seen)"
                  " VALUES (?, ?, ?, ?, ?, 0, 0)", rows)
    c.commit()
    c.close()
    monkeypatch.setattr(db, "_DB_FILE", path)
    got = {r["key"]: r["status"] for r in db._db().execute("SELECT key, status FROM projects")}
    assert got == {"base:0xab": "ranked", "bsc:0xcd": "studied"}


def test_board_entries_merge_their_spellings():
    lb._entries.update({
        "base:0xAB": {"chain": "base", "token_address": "0xAB", "rank": 3, "pillars": {"site": {}}, "found_at": 2},
        "base:0xab": {"chain": "base", "token_address": "0xab", "rank": None, "pillars": {}, "found_at": 1},
    })
    lb._gone["bsc:0xEF"] = 5.0
    lb._merge_spellings()
    assert list(lb._entries) == ["base:0xab"] and lb._entries["base:0xab"]["rank"] == 3
    assert lb._gone == {"bsc:0xef": 5.0}
