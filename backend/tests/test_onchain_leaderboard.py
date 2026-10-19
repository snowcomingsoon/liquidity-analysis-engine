"""Classifica dei progetti: analisi profonda (GitHub, sito, tokenomics) e
ordine. Tutto senza rete: i giudizi sono funzioni pure."""
import time

import asyncio

import pytest

from app.trading.onchain import depth, legit, leaderboard as lb

NOW = 1_790_000_000.0
DAY = 86400


def _commit(t: float, msg: str = "Fix order routing", login: str = "alice") -> dict:
    iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
    return {"commit": {"author": {"date": iso, "email": f"{login}@x"}, "message": msg}, "author": {"login": login}}


def _repo(**kw) -> dict:
    return {"repo": {"full_name": "acme/core", "html_url": "https://github.com/acme/core", "fork": False,
                     "created_at": "2025-01-01T00:00:00Z", "stargazers_count": 40, **kw.pop("repo", {})},
            "commits": kw.get("commits", []), "contributors": kw.get("contributors", [{"login": "a"}]),
            "languages": kw.get("languages", {"Rust": 400_000, "TypeScript": 120_000}),
            "root": kw.get("root", [{"name": "tests"}, {"name": ".github"}, {"name": "README.md"}]),
            "participation": kw.get("participation", {})}


@pytest.fixture(autouse=True)
def _clean():
    lb.reset_for_tests()
    yield
    lb.reset_for_tests()


# ------------------------------------------------------------------ GitHub

def test_github_real_work_scores_high():
    commits = [_commit(NOW - i * 2 * DAY, login=("alice", "bob", "carol")[i % 3]) for i in range(40)]
    p = depth.judge_github(_repo(commits=commits, contributors=[{}, {}, {}, {}]), now=NOW)
    assert not p["fatal"] and p["score"] >= 70
    assert p["facts"]["tests"] and p["facts"]["ci"] and p["facts"]["authors"] == 3


def test_github_upload_only_repo_is_rejected():
    commits = [_commit(NOW - i * DAY, msg=m) for i, m in
               enumerate(["Add files via upload", "Update README.md", "Create index.html", "Initial commit"])]
    p = depth.judge_github(_repo(commits=commits), now=NOW)
    assert "uploads" in p["fatal"]


def test_github_one_day_and_tiny_code_are_rejected():
    same_day = [_commit(NOW - i * 60) for i in range(20)]
    assert "single day" in depth.judge_github(_repo(commits=same_day, languages={"Rust": 12_000}), now=NOW)["fatal"]
    spread = [_commit(NOW - i * DAY) for i in range(20)]
    assert "code" in depth.judge_github(_repo(commits=spread, languages={"HTML": 900}), now=NOW)["fatal"]


def test_github_fork_and_missing_and_rate_limited():
    assert "fork" in depth.judge_github(_repo(repo={"fork": True}), now=NOW)["fatal"]
    assert depth.judge_github({}, now=NOW)["fatal"]
    assert depth.judge_github(None)["pending"]


def test_github_born_with_token_is_flagged():
    commits = [_commit(NOW - i * 3600 * 4) for i in range(10)]
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - 2 * DAY))
    p = depth.judge_github(_repo(commits=commits, repo={"created_at": created}), launched_at=NOW - DAY, now=NOW)
    assert "repository born with the token" in p["flags"]


def test_github_uses_participation_when_available():
    commits = [_commit(NOW - i * 600) for i in range(100)] + [_commit(NOW - 3 * DAY)]
    p = depth.judge_github(_repo(commits=commits, participation={"all": [0] * 40 + [5] * 12}), now=NOW)
    assert p["facts"]["active_weeks_12"] == 12 and p["facts"]["commits_90d"] == 60


# -------------------------------------------------------------------- sito

RICH = """<html><head><title>Acme</title><meta name="description" content="x">
<meta property="og:image" content="x.png"><link rel="icon" href="/f.ico"></head><body>
<nav><a href="/about">About</a><a href="/blog">Blog</a><a href="https://docs.acme.io/intro">Docs</a>
<a href="https://app.acme.io">Launch App</a><a href="https://github.com/acme/core">GitHub</a></nav>
<h1>Acme</h1><h2>Roadmap</h2><h2>Team</h2><h2>Tokenomics</h2><p>""" + "real words " * 400 + "</p></body></html>"


def test_anatomy_reads_structure():
    a = depth.anatomy(RICH, "https://acme.io/")
    assert a["docs"] == ["https://docs.acme.io/intro"]
    assert a["app"] == ["https://app.acme.io"]
    assert a["github"] == ["https://github.com/acme/core"]
    assert {"roadmap", "team", "tokenomics"} <= set(a["sections"])
    assert len(a["internal"]) >= 3 and a["meta_description"] and a["og_image"] and a["icon"]


def test_site_with_something_behind_beats_a_landing_page():
    rich = {**depth.anatomy(RICH, "https://acme.io/"), "url": "https://acme.io/", "https": True}
    followed = [{"kind": "docs", "ok": True, "words": 900}, {"kind": "app", "ok": True, "words": 20},
                {"kind": "page", "ok": True, "words": 300}]
    good = depth.judge_site(rich, followed, NOW - 400 * DAY, now=NOW)
    landing_html = "<html><body><h1>MOON</h1><p>" + "buy now " * 60 + "</p><a href='https://x.com/m'>X</a></body></html>"
    landing = {**depth.anatomy(landing_html, "https://moon.xyz/"), "url": "https://moon.xyz/", "https": True}
    bad = depth.judge_site(landing, [], NOW - 2 * DAY, launched_at=NOW - DAY, now=NOW)
    assert good["score"] >= 80 and bad["score"] <= 25
    assert "single page, nothing behind it" in bad["flags"]
    assert "domain registered with the token" not in bad["flags"]


def test_site_placeholder_and_empty_and_not_own():
    lorem = {**depth.anatomy("<p>Lorem ipsum dolor sit amet " + "x " * 100 + "</p>", "https://a.io/"), "url": "https://a.io/"}
    assert "lorem" in depth.judge_site(lorem, [], None, now=NOW)["fatal"]
    empty = {**depth.anatomy("<h1>Soon</h1>", "https://b.io/"), "url": "https://b.io/"}
    assert depth.judge_site(empty, [], None, now=NOW)["fatal"] == "empty page"
    wiki = {**depth.anatomy(RICH, "https://en.wikipedia.org/wiki/Frogger"), "not_own": "wikipedia.org"}
    assert "not the project's website" in depth.judge_site(wiki, [], None, now=NOW)["fatal"]


def test_rdap_registration():
    rdap = {"events": [{"eventAction": "expiration", "eventDate": "2027-01-01T00:00:00Z"},
                       {"eventAction": "registration", "eventDate": "2026-09-22T08:02:21.826Z"}]}
    assert depth._registration(rdap) == pytest.approx(1790064141.826)


# -------------------------------------------------------------- tokenomics

def _rug(**kw) -> dict:
    return {"token": {"supply": 1_000_000}, "creatorBalance": kw.get("creator", 0),
            "topHolders": kw.get("holders", [{"address": f"h{i}", "owner": f"o{i}", "pct": 2.0} for i in range(10)]),
            "totalHolders": kw.get("total", 3000), "mintAuthority": kw.get("mint"), "freezeAuthority": None,
            "markets": [{"pubkey": "pool", "liquidityA": "liqA", "liquidityAAccount": {"owner": "poolAuth"},
                         "lp": {"lpLockedPct": 100}}],
            "knownAccounts": {"amm1": {"type": "AMM"}}, "transferFee": {"pct": 0}, "rugged": False}


def test_tokenomics_clean_distribution_scores_high():
    p = depth.judge_tokenomics_solana(_rug())
    assert not p["fatal"] and p["score"] >= 80 and p["facts"]["top10_pct"] == 20.0


def test_tokenomics_pools_and_curve_are_not_holders():
    holders = [{"address": "liqA", "owner": "poolAuth", "pct": 40.0},
               {"address": "x", "owner": "amm1", "pct": 30.0},
               {"address": "curve-ata", "owner": "curve", "pct": 20.0},
               {"address": "h1", "owner": "o1", "pct": 3.0}]
    p = depth.judge_tokenomics_solana(_rug(holders=holders), exclude={"curve"})
    assert p["facts"]["top1_pct"] == 3.0 and not p["fatal"]


def test_tokenomics_linked_wallets_judged_by_supply_share():
    dust = {**_rug(), "graphInsidersDetected": 800,
            "insiderNetworks": [{"size": 800, "currentHolding": 5_000}]}
    p = depth.judge_tokenomics_solana(dust)
    assert p["facts"]["linked_pct"] == 0.5 and not any("linked" in f for f in p["flags"])
    heavy = {**dust, "insiderNetworks": [{"size": 9, "currentHolding": 200_000}]}
    p2 = depth.judge_tokenomics_solana(heavy)
    assert "linked wallets hold 20% of supply (800 wallets)" in p2["flags"] and p2["score"] < p["score"]


@pytest.mark.parametrize("kw,needle", [
    ({"creator": 790_000}, "creator"),
    ({"holders": [{"address": "w", "owner": "w", "pct": 35.0}]}, "a single wallet"),
    ({"holders": [{"address": f"w{i}", "owner": f"w{i}", "pct": 9.0} for i in range(10)]}, "top 10"),
    ({"mint": "someone"}, "mint"),
])
def test_tokenomics_scams_are_rejected(kw, needle):
    assert needle in depth.judge_tokenomics_solana(_rug(**kw))["fatal"]


def test_tokenomics_evm_goplus():
    info = {"holders": [{"address": "0xpair", "percent": "0.5"}, {"address": "0xdead00", "percent": "0.1", "is_locked": 1},
                        {"address": "0xa", "percent": "0.04"}],
            "holder_count": "1200", "creator_percent": "0.01", "lp_holders": [{"address": "0x1", "percent": "0.95", "is_locked": 1}],
            "is_mintable": "0", "buy_tax": "0", "sell_tax": "0"}
    p = depth.judge_tokenomics_evm(info, "0xPAIR")
    assert p["facts"]["top1_pct"] == 4.0 and p["facts"]["lp_locked_pct"] == 95.0 and not p["fatal"]
    assert "tax" in depth.judge_tokenomics_evm({**info, "sell_tax": "0.2"}, "0xpair")["fatal"]
    # Contracts (v4 PoolManager, vesting) are not "a single wallet": flagged, not fatal.
    held = {**info, "holders": [{"address": "0xc1", "percent": "0.41", "is_contract": 1},
                                {"address": "0xc2", "percent": "0.26", "is_contract": 1}, *info["holders"]]}
    p = depth.judge_tokenomics_evm(held, "0xpair")
    assert not p["fatal"] and p["facts"]["contracts_pct"] == 67.0 and "contracts" in p["flags"][-1]
    assert p["score"] < depth.judge_tokenomics_evm(info, "0xpair")["score"]
    assert "single wallet" in depth.judge_tokenomics_evm(
        {**info, "holders": [{"address": "0xw", "percent": "0.41", "is_contract": 0}]}, "0xpair")["fatal"]


def test_overall_fatal_and_pending():
    ok = {"score": 80, "fatal": "", "flags": []}
    assert depth.overall({"github": ok, "site": ok, "tokenomics": ok})["score"] == 80
    assert depth.overall({"github": {**ok, "fatal": "fork", "score": 0}, "site": ok})["fatal"].startswith("github")
    assert depth.overall({"github": ok, "tokenomics": {"score": None, "pending": "RugCheck"}})["pending"]


# -------------------------------------------------------------- classifica

def _entry(sym: str, gh: int, site: int, tok: int, cap: float = 50_000, age_days: float = 30, source: str = "coingecko",
           **item) -> dict:
    item = {"chain": "solana", "token_address": sym + "mint", "pair_address": sym + "pool", "symbol": sym,
            "market_cap": cap, "created_at": time.time() - age_days * DAY, **item}
    lb.add(item, source)
    k = lb._key("solana", sym + "mint")
    lb.apply_analysis(k, {n: {"key": n, "score": s, "facts": {}, "flags": [], "fatal": ""}
                          for n, s in (("github", gh), ("site", site), ("tokenomics", tok))})
    return lb._entries[k]


def test_board_orders_by_score_and_tracks_movement():
    _entry("AAA", 75, 60, 60, age_days=16, source="radar")
    _entry("BBB", 90, 80, 85, age_days=16, source="radar")
    b = lb.board()
    assert [e["symbol"] for e in b["entries"]] == ["BBB", "AAA"]
    assert [e["rank"] for e in b["entries"]] == [1, 2]
    _entry("CCC", 95, 95, 95, age_days=16, source="radar")
    b = lb.board()
    assert b["entries"][0]["symbol"] == "CCC" and b["entries"][1]["rank_before"] == 1


def test_fatal_pillar_excludes_for_good():
    _entry("BAD", 80, 80, 80)
    k = lb._key("solana", "BADmint")
    lb.apply_analysis(k, {"tokenomics": {"key": "tokenomics", "score": 0, "facts": {}, "flags": [],
                                         "fatal": "il creatore tiene il 79%"}})
    assert k not in lb._entries and lb.board()["excluded"][0]["reason"].endswith("79%")
    assert lb.add({"chain": "solana", "token_address": "BADmint"}, "radar") is False


def test_weak_pillar_and_gem_rule():
    assert lb.qualifies(_entry("WEAK", 90, 20, 90, age_days=16, source="radar")).startswith("site")
    admitted = _entry("ADM", 90, 20, 90, age_days=16, source="radar")
    admitted["judge"] = {"score": 85, "verdict": "gem", "confidence": 0.8, "at": time.time()}
    assert lb.qualifies(admitted) == ""
    assert "site" in lb.qualifies(_entry("MID", 60, 45, 60, cap=500_000, age_days=16, source="radar"))
    assert lb.qualifies(_entry("GEM", 88, 90, 90, cap=500_000, age_days=16, source="radar")) == ""
    vetoed = _entry("SCAM", 90, 90, 90, age_days=16, source="radar")
    vetoed["judge"] = {"score": 20, "verdict": "scam", "confidence": 0.9, "problems": ["x"]}
    assert lb.qualifies(vetoed).startswith("DeepSeek")


def test_above_2m_no_score_band():
    """Lorenzo, 29/09: "alziamo semmai il tetto della market cap sopra i
    100k, perche' tanto le gemme possono arrivare anche a 1 o 2 milioni".
    Since 07/10 the $2M score band is gone: usage decides (usage_gate), and
    age is never a reason."""
    mid = _entry("MIDCAP", 75, 65, 62, cap=3_000_000, age_days=88, source="database")
    assert lb.qualifies(mid) == ""
    assert lb.qualifies(_entry("STRONG", 95, 95, 95, cap=3_000_000, age_days=900, source="database")) == ""
    assert lb.qualifies(_entry("HUGE", 99, 99, 99, cap=12_000_000, age_days=88)).startswith("over $10M")
    assert next(x for x in lb.board()["entries"] if x["symbol"] == "STRONG")["exception"] is True


def test_young_small_caps_up_to_2m_enter_on_solid_pillars():
    # STEALF (Solana, $617k, pool 14 days) and BV7X ($1.4M, 12 days on this
    # chain, 8 months elsewhere): solid, not excellent, pillars.
    stealf = _entry("STEALF", 75, 68, 65, cap=617_000, age_days=14, source="database", liquidity_usd=190_000)
    assert lb.qualifies(stealf) == ""
    bv7x = _entry("BV7X", 72, 70, 66, cap=1_400_000, age_days=12, source="database", liquidity_usd=150_000)
    assert lb.qualifies(bv7x) == ""
    assert lb.research_floor(_entry("NEWBORN", 80, 80, 80, age_days=1)) == ""


def test_due_refreshes_by_pillar():
    e = _entry("R", 80, 80, 80)
    now = time.time()
    assert lb.due(e, now) == set()
    assert lb.due(e, now + 25 * 60) == {"tokenomics"}
    assert lb.due(e, now + 13 * 3600) == {"tokenomics", "github", "site"}


def test_market_update_keeps_the_most_liquid_pool_and_launch():
    _entry("M", 80, 80, 80)
    lb.apply_market([
        {"chainId": "solana", "baseToken": {"address": "Mmint"}, "liquidity": {"usd": 5000}, "marketCap": 70000,
         "pairCreatedAt": 1_000_000_000_000, "pairAddress": "p1", "dexId": "pumpfun"},
        {"chainId": "solana", "baseToken": {"address": "Mmint"}, "liquidity": {"usd": 20000}, "marketCap": 90000,
         "pairCreatedAt": 1_100_000_000_000, "pairAddress": "p2", "dexId": "pumpswap", "priceChange": {"h24": 12}},
    ])
    e = lb._entries[lb._key("solana", "Mmint")]
    assert e["market_cap"] == 90000 and e["liquidity_usd"] == 20000 and e["change_24h"] == 12
    assert e["launched_at"] == 1_000_000_000 and not e["bonding"]


# ------------------------------------------------------------- riferimento

from app.trading.onchain import benchmark  # noqa: E402

DREGG_GITHUB = {"description": "Formally verified distributed object-capability OS",
                "topics": ["lean4", "stark", "zero-knowledge"], "languages_all": ["Rust", "Lean", "TypeScript"],
                "root_dirs": ["metatheory", "circuit", "node", "blocklace", "sdk", "cli", "docs"],
                "total_commits": 10_203}


def test_dregg_is_the_top_of_its_own_benchmark():
    sim = benchmark.similarity(benchmark.signals(DREGG_GITHUB, benchmark.site_terms(
        "machine-checked kernel, zkvm, consensus, wasm playground, no independent external audit, research software")))
    assert sim["score"] >= 90


def test_a_plain_web_project_is_far_from_dregg():
    web = {"description": "Community token with a website", "languages_all": ["JavaScript", "HTML", "CSS"],
           "root_dirs": ["public", "src"], "total_commits": 40}
    assert benchmark.similarity(benchmark.signals(web, benchmark.site_terms("buy, stake, earn")))["score"] <= 10


def test_site_terms_are_small():
    terms = benchmark.site_terms("We use STARK proofs, Plonky3 and a BFT consensus. Research software.")
    assert terms["zk"] == ["plonky3", "stark"] and "consensus" in terms["protocol"] and terms["candor"]


def test_the_board_is_by_score_and_dregg_keeps_only_its_honor():
    # Lorenzo, 27/09: the podium must not show lower scores than the others.
    _entry("BEST", 99, 99, 99)
    lb.add(benchmark.seed_item(), "riferimento")
    k = lb._key(benchmark.CHAIN, benchmark.TOKEN)
    lb.apply_analysis(k, {"github": {"key": "github", "score": 70, "facts": DREGG_GITHUB, "flags": [], "fatal": ""},
                          "tokenomics": {"key": "tokenomics", "score": None, "facts": {}, "flags": [], "fatal": "",
                                         "pending": "RugCheck"}})
    b = lb.board()
    assert b["entries"][0]["symbol"] == "BEST"
    dregg = next(e for e in b["entries"] if e["symbol"] == "DREGG")
    assert dregg["benchmark"] and dregg["honor"]


def test_similarity_is_a_label_not_points():
    """07/10: DREGG's likeness no longer lifts the score; better pillars win."""
    plain = _entry("PLAIN", 80, 80, 80)
    like = _entry("LIKE", 78, 78, 78)
    lb.apply_analysis(lb._key("solana", "LIKEmint"),
                      {"github": {"key": "github", "score": 78, "facts": DREGG_GITHUB, "flags": [], "fatal": ""}})
    assert lb.final_score(like) < lb.final_score(plain)
    assert [e["symbol"] for e in lb.board()["entries"]][:2] == ["PLAIN", "LIKE"]


def test_benchmark_is_never_excluded():
    lb.add(benchmark.seed_item(), "riferimento")
    k = lb._key(benchmark.CHAIN, benchmark.TOKEN)
    lb.apply_analysis(k, {"site": {"key": "site", "score": 0, "facts": {}, "flags": [], "fatal": "pagina vuota"}})
    assert k in lb._entries


def test_serious_project_enters_up_to_10_million_at_any_age():
    # Lorenzo, 28/09: "massimo consideriamo 10 milioni di market cap"
    e = _entry("SER", 90, 90, 90, cap=9_000_000, age_days=400, source="coingecko")
    assert lb.qualifies(e) == ""
    e["market_cap"] = 12_000_000
    assert "over $10M" in lb.qualifies(e)
    old = _entry("OLD", 80, 70, 65, cap=900_000, age_days=1200, source="coingecko")
    assert lb.qualifies(old) == ""


def test_one_floor_per_pillar_with_or_without_code():
    # 29/09: weak public code never fares worse than no code at all.
    assert lb.qualifies(_entry("THIN", 60, 55, 65, cap=500_000, source="dexscreener")) == ""
    assert lb.qualifies(_closed("SHUT", 55, 65, cap=500_000, source="dexscreener")) == ""
    assert "github" in lb.qualifies(_entry("SHELL", 30, 90, 90, cap=500_000, source="dexscreener"))
    assert "site" in lb.qualifies(_entry("WEAK", 85, 45, 90, cap=500_000, source="coingecko"))
    assert "tokenomics" in lb.qualifies(_closed("TOKW", 80, 55, cap=500_000))


def test_serious_project_survives_prune_past_radar_age():
    _entry("MID", 80, 70, 65, cap=800_000, age_days=60, source="coingecko")
    lb._prune(time.time())
    assert lb._key("solana", "MIDmint") in lb._entries


def test_github_channel_counts_as_serious_source():
    e = _entry("GHX", 80, 65, 65, cap=1_500_000, age_days=100, source="github")
    assert lb.qualifies(e) == ""


def test_data_that_never_arrives_does_not_ban_the_project():
    e = _entry("SLOW", 80, 80, 80)
    k = lb._key("solana", "SLOWmint")
    e["overall"]["pending"] = "GitHub not answering"
    e["found_at"] = time.time() - lb.PENDING_GIVE_UP_S - 60
    lb._prune(time.time())
    assert k not in lb._entries and k not in lb._gone


def _closed(sym, site, tok, **kw):
    e = _entry(sym, 0, site, tok, **kw)
    lb.apply_analysis(lb._key("solana", sym + "mint"), {"github": depth.missing_github("no public GitHub")})
    return e


def test_no_public_github_is_not_a_ban():
    e = _closed("CLS", 80, 80, cap=900_000, source="coingecko")
    assert not e["overall"]["fatal"] and lb.qualifies(e) == ""
    assert lb._key("solana", "CLSmint") not in lb._gone


def test_no_public_github_ranks_lower():
    weak = _closed("WK", 45, 90, cap=900_000, source="coingecko")
    assert "site" in lb.qualifies(weak)
    closed = _closed("CL", 80, 80, cap=50_000)
    open_ = _entry("OP", 80, 80, 80, cap=50_000)
    assert lb.final_score(open_) > lb.final_score(closed)
    b = lb.board()
    assert [x["symbol"] for x in b["entries"]].index("OP") < [x["symbol"] for x in b["entries"]].index("CL")
    assert next(x for x in b["entries"] if x["symbol"] == "CL")["closed_source"]


def test_old_bans_are_lifted_on_new_rules(tmp_path, monkeypatch):
    f = tmp_path / "lb.json"
    f.write_text('{"entries": {}, "gone": {"solana:X": 1790000000}, "excluded": [{"symbol": "X"}]}')
    monkeypatch.setattr(lb, "_STORE_FILE", f)
    lb._load()
    assert "solana:X" not in lb._gone and not lb._excluded


def test_rules_4_rereads_research_and_lifts_v3_bans(tmp_path, monkeypatch):
    f = tmp_path / "lb.json"
    e = {"chain": "solana", "token_address": "S", "symbol": "S", "source": "coingecko",
         "pillars": {"site": {"score": 20}, "tokenomics": {"score": 70}}, "checked_at": {"site": 1, "tokenomics": 1}}
    import json
    f.write_text(json.dumps({"entries": {"solana:S": e}, "gone": {"solana:X": 1}, "rules": 3}))
    monkeypatch.setattr(lb, "_STORE_FILE", f)
    lb._load()
    s = lb._entries["solana:S"]
    assert "site" not in s["pillars"] and "solana:X" not in lb._gone   # tokenomics is redone too since rules 9


def test_references_are_never_banned():
    ref = dict(lb.REFERENCES[0])
    k = lb._key(ref["chain"], ref["token_address"])
    lb._gone[k] = 1.0
    lb.collect_saved()
    assert k in lb._entries
    lb.apply_analysis(k, {"site": {"key": "site", "score": 0, "facts": {}, "flags": [], "fatal": "empty page"}})
    assert k in lb._entries and lb.qualifies(lb._entries[k])


def test_close_calls_show_what_keeps_projects_out():
    _entry("NEAR", 80, 40, 80)
    _entry("KID", 80, 90, 80, liquidity_usd=1_000)
    close = lb.board()["close"]
    assert [c["symbol"] for c in close] == ["NEAR"] and "site" in close[0]["why"]


def test_closed_source_is_not_scored_on_code_similarity():
    e = _closed("SR", 78, 64)
    assert lb.final_score(e) >= 60


def test_board_has_a_hard_10m_ceiling_on_the_global_cap():
    small = _entry("SML", 90, 90, 90, cap=500_000)
    assert lb.qualifies(small) == ""
    small["global_cap"] = 2_245_803_096          # AAVE's Solana copy: local $585k, global $2.2B
    assert lb.qualifies(small).startswith("over $10M")
    big = _entry("BIG", 90, 90, 90, cap=12_000_000)
    assert lb.qualifies(big).startswith("over $10M")
    assert "SML" not in [x["symbol"] for x in lb.board()["entries"]]


def test_global_cap_is_read_from_coingecko(monkeypatch):
    import asyncio
    e = _entry("AAV", 90, 90, 90, cap=585_000)

    class R:
        status_code = 200

        def json(self):
            return {"market_data": {"market_cap": {"usd": 2.2e9}, "fully_diluted_valuation": {"usd": 2.3e9}}}

    class C:
        async def get(self, url, **kw):
            assert "AAVmint" in url
            return R()

    asyncio.run(lb._check_global_cap(C(), time.time()))
    assert e["global_cap"] == 2.3e9 and lb.qualifies(e).startswith("over $10M")


def test_deepseek_review_can_drop_and_reorder_the_board(monkeypatch):
    import asyncio
    import json as _json
    from app.trading.onchain import judge
    monkeypatch.setattr(lb.settings, "research_ai_enabled", True)      # a faked DeepSeek, switched on
    monkeypatch.setattr(lb.settings, "deepseek_api_key", "test")
    judge.reset_for_tests()
    monkeypatch.setattr(judge, "_save", lambda: None)
    _entry("CLAUPUMP", 90, 90, 90)
    _entry("REAL", 80, 80, 80)
    b = lb.board()
    assert [x["symbol"] for x in b["entries"]][:2] == ["CLAUPUMP", "REAL"]
    seen = {}

    async def ask(messages, **kw):
        seen["brief"] = messages[1]["content"]
        return _json.dumps({"projects": [
            {"id": "solana:CLAUPUMPmint", "keep": False, "score": 10, "reason": "parody brand name, no product"},
            {"id": "solana:REALmint", "keep": True, "score": 90, "reason": "live product"}]})

    import app.notify.deepseek_desk as desk
    monkeypatch.setattr(desk, "ask", ask)
    monkeypatch.setattr(desk, "note", lambda *a, **k: None)
    asyncio.run(lb._review_board(time.time()))
    assert "CLAUPUMP" in seen["brief"]
    syms = [x["symbol"] for x in lb.board()["entries"]]
    assert "CLAUPUMP" not in syms and "REAL" in syms
    assert lb.qualifies(lb._entries["solana:CLAUPUMPmint"]).startswith("DeepSeek review: parody")


def test_review_ignores_unknown_ids_and_bad_rows():
    from app.trading.onchain import judge
    raw = '{"projects": [{"id": "x", "keep": false, "score": 1}, {"id": "a", "keep": "no"}, {"id": "a", "keep": true, "score": 70}]}'
    assert judge.parse_review(raw, {"a"}) == {"a": {"keep": True, "score": 70, "reason": ""}}


def test_a_copy_of_a_top_coin_is_out_even_if_coingecko_lists_it_small():
    from app.trading.onchain import big_coins
    big_coins.set_for_tests([{"symbol": "aave", "name": "Aave", "cap": 2.2e9},
                             {"symbol": "tiny", "name": "Tiny", "cap": 5e6}])
    e = _entry("AAVE", 90, 90, 90, cap=450_000)
    e["global_cap"] = 450_000                      # "Aave (Wormhole)", its own coin on CoinGecko
    assert lb.qualifies(e).startswith("over $10M")
    w = _entry("WAAVE", 90, 90, 90, cap=450_000)
    w["name"] = "Aave Token"
    assert lb.qualifies(w).startswith("over $10M")
    assert lb.qualifies(_entry("TINY", 90, 90, 90, cap=450_000)) == ""
    assert lb.qualifies(_entry("SAVE", 90, 90, 90, cap=450_000)) == ""


def test_ported_tokens_are_recognised_by_name_and_the_seed_works_offline(monkeypatch):
    from app.trading.onchain import big_coins
    for name in ("Aave (Wormhole)", "Wrapped ETH (Portal)", "USDC (Allbridge from Ethereum)", "Chainlink (WH)"):
        e = _entry("XYZ", 90, 90, 90, cap=450_000)
        e["name"] = name
        assert lb.qualifies(e).startswith("bridged"), name
    assert not big_coins.bridged({"name": "Portalverse Labs", "symbol": "PVL"})
    monkeypatch.setattr(big_coins, "_loaded", False)
    monkeypatch.setattr(big_coins, "_STORE", big_coins._SEED.with_name("missing.json"))
    big_coins._state.update(coins=[])
    assert big_coins.match("AAVE", "Aave") and big_coins.match("aave", "Aave")["cap"] > 1e9


def test_the_top_list_drops_database_rows_of_big_coins(monkeypatch):
    import app.main as m
    from app.trading.onchain import big_coins
    big_coins.set_for_tests([{"symbol": "aave", "name": "Aave", "cap": 2.2e9}])
    now = time.time()
    rows = [{"chain": "solana", "token": "AAVEmint", "symbol": "AAVE", "name": "Aave", "mcap": 450_000,
             "score": 99, "analyzed_at": now},
            {"chain": "solana", "token": "OKmint", "symbol": "OKP", "name": "Ok Project", "mcap": 450_000,
             "score": 70, "analyzed_at": now}]
    monkeypatch.setattr(m.onchain_projects_db, "search", lambda **kw: {"items": rows})
    monkeypatch.setattr(m.onchain_judge, "get", lambda *a: None)
    assert [e["symbol"] for e in m._top_entries(10) if not e["on_board"]] == ["OKP"]

def test_code_review_lifts_the_final_score():
    plain = _entry("PLAIN", 80, 80, 80)
    coded = _entry("CODED", 80, 80, 80)
    coded["code"] = {"complexity": 90, "innovation": 90, "at": time.time()}
    assert lb.final_score(coded) > lb.final_score(plain)
    assert lb._public(coded)["code"]["complexity"] == 90


def test_database_follows_later_score_changes(monkeypatch):
    calls = []
    monkeypatch.setattr(lb.projects_db, "set_standing", lambda *a: calls.append(a))
    e = _entry("THR", 90, 90, 90, cap=500_000)
    lb._rank()
    first = [c for c in calls if c[1] == e["token_address"]][-1]
    assert first[2] == "ranked"
    e["judge"] = {"score": 10, "verdict": "avoid", "at": time.time()}
    lb._rank()
    last = [c for c in calls if c[1] == e["token_address"]][-1]
    assert last[3] < first[3]
    n = len(calls)
    lb._rank()
    assert len(calls) == n          # nothing changed, nothing written


def test_a_null_symbol_is_no_name():
    """Lorenzo, 28/09: two BSC tokens sat in the Top as "null"."""
    from app.trading.onchain import leaderboard as lb
    for s in (None, "", "?", "null", "NULL", " none ", "undefined"):
        assert lb.no_name(s)
    assert not lb.no_name("NULLX") and not lb.no_name("DREGG")
    assert lb.research_floor({"symbol": "null", "chain": "bsc", "token_address": "0x1"}) == "no name"


def test_discovery_pauses_on_a_full_pool_with_work_left(monkeypatch):
    monkeypatch.setattr(lb.settings, "research_ai_enabled", True)
    monkeypatch.setattr(lb.projects_db, "stats", lambda: {"by_status": {"studied": 280, "ranked": 20}})
    for i in range(lb.BACKLOG_LOW + 1):
        _entry(f"P{i}", 90, 90, 90, cap=500_000)      # analysed, no DeepSeek report yet
    now = time.time()
    assert lb.pool_status(now)["paused"] and not lb.discovery_open(now)
    monkeypatch.setattr(lb.projects_db, "stats", lambda: {"by_status": {"studied": 50}})
    assert lb.discovery_open(now)                       # small pool: keep scanning


def test_a_report_that_cannot_come_does_not_pause_discovery(monkeypatch):
    """18/10: with the research's DeepSeek off, 204 projects waited for a
    report that never comes, and discovery stayed paused for good."""
    monkeypatch.setattr(lb.settings, "research_ai_enabled", False)
    monkeypatch.setattr(lb.projects_db, "stats", lambda: {"by_status": {"studied": 4000}})
    for i in range(lb.BACKLOG_LOW + 1):
        _entry(f"P{i}", 90, 90, 90, cap=500_000)
    assert not lb.pool_status(time.time())["paused"]


def test_the_fast_sources_run_while_the_pool_is_paused(monkeypatch):
    """18/10: the pause stopped every source; now it holds CoinGecko only."""
    import asyncio
    seen = []
    monkeypatch.setattr(lb, "discovery_open", lambda now: False)

    async def tick(client, add, now, bulk):
        seen.append(bulk)
    monkeypatch.setattr(lb.discovery, "tick", tick)
    asyncio.run(lb._step("progetti", lb.discovery.tick, None, lb.add, 0.0, lb.discovery_open(0.0)))
    assert seen == [False]


def test_young_projects_are_analysed_first():
    now = time.time()
    assert lb.young({"launched_at": now - 3 * DAY}, now)
    assert not lb.young({"launched_at": now - 30 * DAY}, now) and not lb.young({}, now)


# ------------------------------------------------------------ the Top first

def _top_db_row(now: float) -> dict:
    return {"chain": "solana", "token": "DBmint", "symbol": "DBR", "name": "Db Row", "mcap": 400_000,
            "liq": 50_000, "launched_at": now - 60 * DAY, "score": 88, "analyzed_at": now, "status": "studied",
            "why": "", "overall": {"score": 80},
            "pillars": {"github": {"score": 70, "facts": {"repo": "acme/dbrow"}},
                        "site": {"score": 70, "facts": {"summary": "an agent OS"}}, "tokenomics": {"score": 60}}}


@pytest.fixture
def _deepseek_off(tmp_path, monkeypatch):
    """Fake DeepSeek, X and GitHub: nothing touches the network or real files."""
    import json

    from app.notify import deepseek_desk
    from app.trading.onchain import code_review, judge, x_signal
    monkeypatch.setattr(deepseek_desk, "_STORE_FILE", tmp_path / "desk.json")
    monkeypatch.setattr(judge, "_FILE", tmp_path / "judge.json")
    monkeypatch.setattr(judge, "_cache", {})
    monkeypatch.setattr(judge, "_calls", {})
    monkeypatch.setattr(code_review, "_FILE", tmp_path / "code.json")
    monkeypatch.setattr(code_review, "_cache", {})
    monkeypatch.setattr(code_review, "_calls", {})
    calls = []

    async def ask(messages, kind="", **_):
        calls.append(kind)
        if kind == "code":
            return json.dumps({"complexity": 70, "innovation": 60, "fork_of": None, "summary": "real code",
                               "strengths": ["tests"], "concerns": []})
        return json.dumps({"score": 82, "verdict": "gem", "confidence": 0.8, "problems": [],
                           "strengths": ["ships"], "admit_reason": "real product"})

    async def no_x(*a, **k):
        return None

    async def fetch(repo, client):
        return {"pushed_at": "2026-09-01T00:00:00Z", "files": []}

    monkeypatch.setattr(deepseek_desk, "ask", ask)
    monkeypatch.setattr(x_signal, "lookup", no_x)
    monkeypatch.setattr(code_review, "fetch_code", fetch)
    deepseek_desk.reset_for_tests()
    yield calls
    deepseek_desk.reset_for_tests()


def test_top_fill_judges_a_database_row_even_with_the_daily_cap_spent(monkeypatch, _deepseek_off):
    import asyncio
    monkeypatch.setattr(lb.settings, "research_ai_enabled", True)
    monkeypatch.setattr(lb.settings, "deepseek_api_key", "test")

    from app.trading.onchain import code_review, judge
    now = time.time()
    row = _top_db_row(now)
    monkeypatch.setattr(lb.projects_db, "get", lambda c, t: row if (c, t) == ("solana", "DBmint") else None)
    monkeypatch.setattr(judge, "DAILY_MAX", 0)
    monkeypatch.setattr(code_review, "DAILY_MAX", 0)
    lb.set_top_source(lambda n: [{"chain": "solana", "token_address": "DBmint", "on_board": False}])
    assert asyncio.run(lb.top_fill(None, now)) == 2
    assert sorted(_deepseek_off) == ["code", "research"]
    assert judge.get("solana", "DBmint")["verdict"] == "gem"
    assert code_review.get("acme/dbrow")["summary"] == "real code"
    # Read once: the next turn has nothing left to do.
    assert asyncio.run(lb.top_fill(None, now + 120)) == 0


def test_the_token_endpoint_carries_the_report_of_a_database_row(monkeypatch, _deepseek_off):
    import asyncio

    import app.main as m
    from app.trading.onchain import code_review, judge
    now = time.time()
    row = _top_db_row(now)
    monkeypatch.setattr(m, "_require_onchain_enabled", lambda: None)
    monkeypatch.setattr(m.onchain_projects_db, "get", lambda c, t: row)
    monkeypatch.setattr(m.onchain_strategy_lab, "get", lambda c, t: None)
    monkeypatch.setattr(m.onchain_alert_track, "for_token", lambda c, t: [])
    judge._cache["solana:DBmint"] = {"score": 82, "verdict": "gem", "confidence": 0.8, "problems": [],
                                     "strengths": ["ships"], "admit_reason": "real product", "at": now}
    code_review._cache["acme/dbrow"] = {"at": now, "summary": "real code", "complexity": 70}
    out = asyncio.run(m.onchain_token("solana", "DBmint", user=None))
    assert out["entry"]["on_board"] is False
    assert out["entry"]["judge"]["verdict"] == "gem" and out["entry"]["judge"]["strengths"] == ["ships"]
    assert out["entry"]["code"]["summary"] == "real code"


def test_tokenomics_falls_back_to_geckoterminal(monkeypatch):
    """GoPlus has nothing (new Robinhood token): GeckoTerminal's holders give a
    modest, informational pillar; its top 10 includes pools, so a high share
    is not fatal. Nothing from either source: still pending."""
    import asyncio

    from app.trading.onchain import legit, research

    async def no_goplus(chain, token, client):
        return None
    gecko = {"holders": 2149, "holders_split": {"top_10": "92.4", "11_30": "3", "31_50": "1", "rest": "3.6"}}

    async def info(chain, token, client):
        return gecko
    monkeypatch.setattr(legit, "goplus", no_goplus)
    monkeypatch.setattr(research, "gecko_info", info)
    p = asyncio.run(depth.analyze_tokenomics("robinhood", "0xabc", None))
    assert not p["fatal"] and not p.get("pending")
    assert p["facts"] == {"holders": 2149, "source": "geckoterminal", "gecko_top10_pct": 92.4}
    assert "pools included" in p["flags"][0]
    assert depth.GECKO_TOKENOMICS_BASE < p["score"] <= depth.GECKO_TOKENOMICS_MAX
    assert depth.judge_tokenomics_gecko({"holders": 10**6})["score"] == depth.GECKO_TOKENOMICS_MAX
    gecko = {}
    assert "GoPlus" in asyncio.run(depth.analyze_tokenomics("robinhood", "0xabc", None))["pending"]


def test_audit_scoring_gates():
    """29/09 audit: M03 benchmark keeps fatal findings, M05 admission needs
    confidence, M04 stale AI readings stop counting."""
    from app.trading.onchain import benchmark
    bench = {"chain": benchmark.CHAIN, "token_address": benchmark.TOKEN, "overall": {"fatal": "tokenomics: rugged"}}
    assert lb.qualifies(bench) == "tokenomics: rugged"
    unsure = _entry("UNSURE", 90, 20, 90, age_days=16, source="radar")
    unsure["judge"] = {"score": 85, "verdict": "gem", "confidence": 0.0, "at": time.time()}
    assert lb.qualifies(unsure).startswith("site")
    fresh, stale = _entry("FRESH", 50, 50, 50), _entry("STALE", 50, 50, 50)
    fresh["review"] = {"keep": True, "score": 100, "at": time.time()}
    stale["review"] = {"keep": True, "score": 100, "at": 1}
    assert lb.final_score(fresh) > lb.final_score(stale)


def test_goplus_lock_of_a_side_pool_is_not_the_market():
    info = {"holder_count": 900, "holders": [{"address": "0x1", "percent": "0.05", "is_contract": 0}],
            "is_mintable": "0", "transfer_pausable": "0", "buy_tax": "0", "sell_tax": "0",
            "lp_holders": [{"address": "0x7", "percent": "0.97", "is_locked": 0, "value": "595.3"}]}
    side = depth.judge_tokenomics_evm(info, "0xpair", 63_000)
    assert side["facts"]["lp_locked_pct"] is None and "lp_note" in side["facts"]
    assert not any("locked" in f for f in side["flags"])
    main = depth.judge_tokenomics_evm(info, "0xpair", 800)
    assert main["facts"]["lp_locked_pct"] == 0.0


def test_coming_soon_on_a_full_page_is_not_a_placeholder():
    body = " ".join(f"word{i}" for i in range(300))
    full = depth.anatomy(f"<html><body><p>{body} Staking coming soon</p></body></html>", "https://x.io")
    short = depth.anatomy("<html><body><p>Our app is coming soon, stay tuned</p></body></html>", "https://x.io")
    assert not full["lorem"] and short["lorem"]


def test_the_v4_pool_manager_is_a_pool_not_a_holder():
    info = {"holder_count": 900, "is_mintable": "0", "transfer_pausable": "0", "buy_tax": "0", "sell_tax": "0",
            "dex": [{"pair": "0xp", "pool_manager": "0xPM"}],
            "holders": [{"address": "0xpm", "percent": "0.30", "is_contract": 1},
                        {"address": "0x1", "percent": "0.05", "is_contract": 0}]}
    p = depth.judge_tokenomics_evm(info)
    assert p["facts"]["contracts_pct"] == 0.0 and not any("contracts" in f for f in p["flags"])


def test_the_token_page_shows_the_top_s_score(monkeypatch):
    # Lorenzo, 16/10: VEIL 89 in its arena, 73 on its token page — the page
    # read the score stored at the last analysis, the Top today's formula.
    import asyncio
    import app.main as m
    from app.models import User
    now = time.time()
    row = {"chain": "solana", "token": "OKmint", "symbol": "OKP", "name": "Ok Project", "mcap": 450_000,
           "score": 12, "analyzed_at": now}
    monkeypatch.setattr(m.onchain_projects_db, "search", lambda **kw: {"items": [row]})
    monkeypatch.setattr(m.onchain_projects_db, "get", lambda chain, token: row)
    monkeypatch.setattr(m.onchain_judge, "get", lambda *a: None)
    monkeypatch.setattr(m.onchain_leaderboard, "board", lambda: {"entries": []})
    monkeypatch.setattr(m, "_require_onchain_enabled", lambda: None)
    top = next(e for e in m._top_entries(10) if e["symbol"] == "OKP")
    page = asyncio.run(m.onchain_token("solana", "OKmint", user=User.model_construct(id="u", email="x@y.z")))
    assert page["entry"]["score"] == top["score"] != 12
    # and its place is the Top's (16/10 review: "Rank #—" for database rows)
    assert page["entry"]["top_rank"] == 1


def test_the_arenas_score_a_database_row_with_its_pillars(monkeypatch):
    # Lorenzo, 17/10: still one score in the narrative arenas, another under
    # the chart. The Top read its rows through projects_db.search, which left
    # out pillars and cg_mcap: no tokenomics, no product pillars, no
    # closed-code penalty. The page read the whole row. Real database here,
    # not a mocked search/get pair that hands both sides the same dict.
    import asyncio
    import app.main as m
    from app.models import User
    from app.trading.onchain import projects_db
    item = {"chain": "solana", "token_address": "PILmint", "symbol": "PIL", "name": "Pillar Project",
            "market_cap": 450_000, "liquidity_usd": 60_000, "launched_at": time.time() - 30 * 86400}
    projects_db.upsert(item, "test")
    pillars = {"tokenomics": {"score": 95}, "site": {"score": 90},
               "github": {"score": 10, "facts": {"missing": True}}}
    projects_db.record({**item, "pillars": pillars}, "studied", score=50)
    monkeypatch.setattr(m.onchain_judge, "get", lambda *a: None)
    monkeypatch.setattr(m.onchain_leaderboard, "board", lambda: {"entries": []})
    monkeypatch.setattr(m, "_require_onchain_enabled", lambda: None)
    # Only the listed accounts for now (Lorenzo, 17/10: "solo per whitekobra").
    monkeypatch.setattr(m.settings, "onchain_full_score_emails", "Kobra@Example.com")
    monkeypatch.setattr(m.settings, "onchain_trading_enabled", False)
    kobra = User.model_construct(id="k", email="kobra@example.com")
    other = User.model_construct(id="o", email="other@example.com")

    def arena_score(user):
        top = asyncio.run(m.onchain_top(n=10, narrative="", user=user))
        return next(e for a in top["arenas"] for e in a["entries"] if e["symbol"] == "PIL")["score"]
    page = asyncio.run(m.onchain_token("solana", "PILmint", user=kobra))
    row = m.onchain_leaderboard.db_entry(projects_db.get("solana", "PILmint"))
    full = m.onchain_leaderboard.final_score(row, kobra=True)     # whitekobra's weights too
    assert arena_score(kobra) == page["entry"]["score"] == full
    # everyone else: the Top as it was, light rows and the old weights
    assert arena_score(other) not in (full, m.onchain_leaderboard.final_score(row))


def test_live_market_reaches_the_top_s_database_rows(monkeypatch):
    # Lorenzo, 16/10: "la MarketCap" always up to date — the research runs
    # at night only, so the Top's market is read every minute on its own.
    import asyncio
    import app.main as m
    now = time.time()
    row = {"chain": "solana", "token": "OKmint", "symbol": "OKP", "name": "Ok Project", "mcap": 450_000,
           "score": 70, "analyzed_at": now}
    monkeypatch.setattr(m.onchain_projects_db, "search", lambda **kw: {"items": [row]})
    monkeypatch.setattr(m.onchain_judge, "get", lambda *a: None)
    monkeypatch.setattr(lb, "_top_source", m._top_entries)
    asked = []

    class _Resp:
        status_code = 200
        def json(self):
            return [{"chainId": "solana", "baseToken": {"address": "OKmint"}, "marketCap": 612_000,
                     "priceUsd": "0.0061", "liquidity": {"usd": 90_000}, "priceChange": {"h24": 12.5},
                     "url": "https://dexscreener.com/solana/okpool", "pairAddress": "okpool"}]

    class _Client:
        async def get(self, url, timeout=None):
            asked.append(url)
            return _Resp()
    real_sleep = asyncio.sleep

    async def no_wait(_s):
        await real_sleep(0)
    monkeypatch.setattr(lb.asyncio, "sleep", no_wait)
    assert asyncio.run(lb.poll_live(_Client(), now)) == 1
    assert any("OKmint" in u for u in asked)
    top = next(e for e in m._top_entries(10) if e["symbol"] == "OKP")
    assert top["market_cap"] == 612_000 and top["change_24h"] == 12.5 and top["pair_address"] == "okpool"
    lb._live.clear()


def test_scout_reports_the_research_without_ai(monkeypatch):
    import app.main as m
    from app.models import User
    monkeypatch.setattr(m.settings, "research_ai_enabled", False)
    out = m.agent_activity(user=User.model_construct(id="u", email="x@y.z"))
    r = out["research"]
    assert r["ai"] is False and r["next_run"] > time.time()
    assert set(r) >= {"last_run", "examined", "entered", "running", "nightly"}


def test_whitekobra_s_top_drops_duplicates_old_and_weak_gems(monkeypatch):
    """Lorenzo, 17/10, for whitekobra only: one row per project, nothing over
    1000 days old, nothing under 60 — in the arenas and in Early."""
    import asyncio
    import app.main as m
    from app.models import User
    now = time.time()
    rows = [{"chain": "base", "token_address": "S1", "symbol": "SHW", "name": "Sherwood Protocol", "score": 81,
             "liquidity_usd": 40_000, "launched_at": now - 90 * 86400, "on_board": True, "narratives": []},
            {"chain": "solana", "token_address": "S2", "symbol": "SHW", "name": "Sherwood Protocol", "score": 66,
             "liquidity_usd": 150_000, "launched_at": now - 90 * 86400, "on_board": False, "narratives": []},
            {"chain": "base", "token_address": "W", "symbol": "WEAK", "name": "Weak", "score": 50,
             "launched_at": now - 9 * 86400, "on_board": True, "narratives": []}]
    early = [{"chain": "base", "token_address": "E", "symbol": "OLDE", "name": "Old Early", "score": 75,
              "launched_at": now - 1200 * 86400}]
    monkeypatch.setattr(m, "_top_entries", lambda n=50, narrative="", full=False: [dict(r) for r in rows])
    monkeypatch.setattr(m.onchain_leaderboard, "board", lambda: {"entries": [], "early": early})
    monkeypatch.setattr(m, "_require_onchain_enabled", lambda: None)
    monkeypatch.setattr(m.settings, "onchain_trading_enabled", False)
    monkeypatch.setattr(m.settings, "onchain_full_score_emails", "kobra@example.com")
    kobra = asyncio.run(m.onchain_top(n=50, narrative="", user=User.model_construct(id="k", email="kobra@example.com")))
    other = asyncio.run(m.onchain_top(n=50, narrative="", user=User.model_construct(id="o", email="other@example.com")))
    assert [e["token_address"] for e in kobra["entries"]] == ["S2"] and kobra["early"] == []
    assert len(other["entries"]) == 3 and len(other["early"]) == 1


def test_whitekobra_s_weights(monkeypatch):
    """Lorenzo, 17/10, his account only: product 35, usage 25 (with the
    holders' growth), token 20, DeepSeek 20, no participation; closed code -5."""
    from app.trading.onchain import usage
    e = {"chain": "solana", "token_address": "W", "pillars": {"site": {"score": 80}, "tokenomics": {"score": 60},
         "github": {"score": 10, "facts": {"missing": True}}}}
    monkeypatch.setattr(lb, "usage_score", lambda e, growth=False: 40.0 if growth else 30.0)
    monkeypatch.setattr(lb, "participation_score", lambda e: 90.0)
    monkeypatch.setattr(lb, "deepseek_score", lambda e: 50.0)
    monkeypatch.setattr(lb.gem_learn, "approved", lambda: None)
    # product 80 (site only), usage 40, token 60, deepseek 50 -> 61.0, minus 5
    assert lb.final_score(e, kobra=True) == round(0.35 * 80 + 0.25 * 40 + 0.20 * 60 + 0.20 * 50 - 5, 1)
    # everyone else: the old weights, participation in, -10
    old = lb.SCORE_WEIGHTS
    assert lb.final_score(e) == round((old["usage"] * 30 + old["participation"] * 90 + old["product"] * 80
                                       + old["token"] * 60 + old["deepseek"] * 50) / sum(old.values()) - 10, 1)
    monkeypatch.undo()
    # the holders' growth is part of usage for whitekobra, and only when measured
    monkeypatch.setattr(usage, "latest", lambda c, t: {"vol_7d_avg": 100_000, "buyers_24h": 300})
    monkeypatch.setattr(lb, "true_cap", lambda e: 1_000_000)
    monkeypatch.setattr(lb, "traction_of", lambda e: None)
    monkeypatch.setattr(usage, "holders_growth", lambda c, t, d: None)
    plain = lb.usage_score(e)
    assert lb.usage_score(e, growth=True) == plain
    monkeypatch.setattr(usage, "holders_growth", lambda c, t, d: 0.30)
    assert lb.usage_score(e, growth=True) > plain


def test_the_light_tick_leaves_the_heavy_work_to_the_runs(monkeypatch):
    """18/10: the sentinel's tick reads the fast sources and analyses what is
    new; the database feed, DeepSeek and the CoinGecko sweep wait."""
    import asyncio
    called, bulk = [], []

    async def disc(client, add, now, b):
        bulk.append(b)
    monkeypatch.setattr(lb.discovery, "tick", disc)
    monkeypatch.setattr(lb, "discovery_open", lambda now: True)
    for name in ("_from_database", "_review_board", "_read_code", "_audit", "_map_narratives", "_refresh_big_coins"):
        async def mark(*a, _n=name, **k):
            called.append(_n)
        monkeypatch.setattr(lb, name, mark)

    async def run():
        await lb.tick(None, light=True)
        await asyncio.sleep(0)
    asyncio.run(run())
    assert bulk == [False]
    assert not set(called) & {"_from_database", "_review_board", "_read_code", "_audit", "_map_narratives", "_refresh_big_coins"}


def test_whitekobra_s_gem_leaves_for_its_cap_after_seven_days(monkeypatch):
    """Lorenzo, 18/10: "per uscire per capitalizzazione dalle gemme deve
    superare il tetto [...] per almeno 7 giorni consecutivi"; no emergency
    ceiling. The other accounts still drop it at once."""
    import app.main as m
    from app.trading.onchain import gem_hold
    clock = {"t": time.time()}
    monkeypatch.setattr(gem_hold.time, "time", lambda: clock["t"])
    row = {"chain": "solana", "token": "CAPmint", "symbol": "CAP", "name": "Cap Project", "mcap": 5_000_000,
           "score": 70, "analyzed_at": clock["t"]}
    monkeypatch.setattr(m.onchain_projects_db, "search", lambda **kw: {"items": [row]})
    monkeypatch.setattr(m.onchain_judge, "get", lambda *a: None)
    monkeypatch.setattr(m.onchain_leaderboard, "board", lambda: {"entries": []})
    monkeypatch.setattr(m.onchain_leaderboard, "usage_gate", lambda e, cap_floor=True: "")
    syms = lambda full: [e["symbol"] for e in m._top_entries(10, full=full)]  # noqa: E731
    assert syms(True) == ["CAP"]
    row["mcap"] = 30_000_000                                  # a flash to $30M
    assert syms(True) == ["CAP"] and syms(False) == []
    clock["t"] += 6 * DAY
    assert syms(True) == ["CAP"]
    clock["t"] += 1 * DAY + 1                                 # 7 days over: out
    assert syms(True) == []
    row["mcap"] = 8_000_000
    assert syms(True) == ["CAP"]                              # back under: in again


def test_whitekobra_s_arena_gem_waits_before_falling_back_to_early(monkeypatch):
    import app.main as m
    row = {"chain": "solana", "token": "FLmint", "symbol": "FL", "name": "Floor Project", "mcap": 400_000,
           "score": 70, "analyzed_at": time.time()}
    monkeypatch.setattr(m.onchain_projects_db, "search", lambda **kw: {"items": [row]})
    monkeypatch.setattr(m.onchain_judge, "get", lambda *a: None)
    monkeypatch.setattr(m.onchain_leaderboard, "board", lambda: {"entries": []})
    floor = lambda e, cap_floor=True: "under $300k (early list)" if cap_floor and (e.get("market_cap") or 0) < 300_000 else ""  # noqa: E731
    monkeypatch.setattr(m.onchain_leaderboard, "usage_gate", floor)
    assert [e["symbol"] for e in m._top_entries(10, full=True)] == ["FL"]
    row["mcap"] = 290_000
    assert [e["symbol"] for e in m._top_entries(10, full=True)] == ["FL"]
    assert [e["symbol"] for e in m._top_entries(10)] == []


def test_with_deepseek_off_the_research_steps_do_nothing_else(monkeypatch):
    """Lorenzo, 19/10: "impedire direttamente che chiamino DeepSeek che
    comunque e' spento": no GitHub read for the code, no X/Telegram reads
    for the judge, no narrative batch."""
    import asyncio
    from app.trading.onchain import code_review, judge, narrative_map
    monkeypatch.setattr(lb.settings, "research_ai_enabled", False)
    monkeypatch.setattr(lb.settings, "deepseek_api_key", "test")
    touched = []

    async def fetch(repo, client):
        touched.append(repo)
    monkeypatch.setattr(code_review, "fetch_code", fetch)
    e = _entry("OFF", 80, 80, 80)
    e["pillars"]["github"] = {"score": 80, "facts": {"repo": "acme/off"}}
    assert asyncio.run(code_review.review(e, None)) is None and touched == []
    assert asyncio.run(judge.judge(e, "")) is None
    assert asyncio.run(judge.review_board([e])) == {}
    assert asyncio.run(narrative_map.step(time.time() + 10 ** 6)) == {}


# Raydium's AMM authority (a program-derived address) and an ordinary wallet.
PDA = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"
WALLET = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"


def test_program_accounts_are_told_from_wallets():
    assert legit.is_program_account(PDA)
    assert not legit.is_program_account(WALLET)
    assert not legit.is_program_account("o1") and not legit.is_program_account(None)


def test_solana_program_accounts_leave_the_wallet_limits():
    """Lorenzo, 19/10: staking, vesting and locks are not whales (MNDE, SONIC)."""
    holders = [{"address": "vault", "owner": PDA, "pct": 30.0}] + \
              [{"address": f"h{i}", "owner": f"o{i}", "pct": 2.0} for i in range(10)]
    p = depth.judge_tokenomics_solana(_rug(holders=holders))
    assert not p["fatal"]
    assert p["facts"]["top10_pct"] == 20.0 and p["facts"]["contracts_pct"] == 30.0
    assert p["facts"]["top10_all_pct"] == 48.0
    assert any("held by programs" in f for f in p["flags"])
    top, top10 = legit.holder_concentration(_rug(holders=holders))
    assert (top, top10) == (2.0, 20.0)


def test_one_program_account_with_most_of_the_supply_still_fails():
    holders = [{"address": "vault", "owner": PDA, "pct": 55.0},
               {"address": "h1", "owner": "o1", "pct": 2.0}]
    assert "one program account holds 55%" in depth.judge_tokenomics_solana(_rug(holders=holders))["fatal"]
    assert legit.program_share(_rug(holders=holders)) == (55.0, 55.0)
    check = legit.judge_rugcheck({**_rug(holders=holders), "risks": []})
    assert check["ok"] is False and "one program account holds 55%" in check["detail"]


def test_github_code_drop_and_busy_repo_are_not_fakes():
    """19/10: real code published in one day costs points; a full page of
    commits on one day is a busy repository (elizaOS), not a fake."""
    same_day = [_commit(NOW - i * 60) for i in range(20)]
    spread = [_commit(NOW - i * DAY) for i in range(20)]
    drop = depth.judge_github(_repo(commits=same_day), now=NOW)
    assert not drop["fatal"] and "all commits on a single day" in drop["flags"]
    assert drop["score"] < depth.judge_github(_repo(commits=spread), now=NOW)["score"]
    busy = [_commit(NOW - i * 60) for i in range(depth.GH_COMMITS_PAGE)]
    p = depth.judge_github(_repo(commits=busy, languages={"Rust": 12_000}), now=NOW)
    assert not p["fatal"] and "all commits on a single day" not in p["flags"]


def test_solana_mint_by_a_program_costs_points_not_the_project():
    clean = depth.judge_tokenomics_solana(_rug())
    by_program = depth.judge_tokenomics_solana({**_rug(), "token": {"supply": 1_000_000, "mintAuthority": PDA},
                                                 "mintAuthority": PDA})
    assert not by_program["fatal"] and by_program["score"] == clean["score"] - depth.MINT_CONTROLLED_PENALTY
    assert "program" in by_program["facts"]["mint_by"]
    by_wallet = depth.judge_tokenomics_solana({**_rug(), "mintAuthority": WALLET})
    assert "minted" in by_wallet["fatal"]
    risk = {"risks": [{"name": "Mint Authority still enabled", "level": "danger"}]}
    assert "Mint" not in (legit.judge_rugcheck({**_rug(), **risk, "mintAuthority": PDA})["detail"] or "")
    assert legit.judge_rugcheck({**_rug(), **risk, "mintAuthority": WALLET})["ok"] is False


def _goplus(**kw):
    return {"is_mintable": "1", "holder_count": "3000", "transfer_pausable": "0", "buy_tax": "0", "sell_tax": "0",
            "holders": [{"address": f"0x{i:040x}", "percent": "0.02", "is_contract": 0} for i in range(1, 11)],
            "lp_holders": [], **kw}


@pytest.mark.parametrize("control,fatal", [("wallet", True), ("unknown", True), (None, True),
                                           ("contract", False), ("no owner", False), ("bridge", False)])
def test_evm_mint_is_fatal_only_with_a_wallet_behind_it(control, fatal):
    p = depth.judge_tokenomics_evm(_goplus(**({"mint_control": control} if control else {})))
    assert bool(p["fatal"]) == fatal
    assert ("supply can be minted" in (legit.judge_goplus(_goplus(**({"mint_control": control} if control else {})))
                                       .get("detail") or "")) == fatal


def test_evm_mint_control_reads_bridge_owner_and_code(monkeypatch):
    from app.trading.onchain import unlocks
    answers = {}

    async def rpc(chain, method, params, client):
        key = params[0]["data"] if method == "eth_call" else params[0]
        return answers.get((method, key))
    monkeypatch.setattr(unlocks, "_rpc", rpc)
    word = "0x" + "0" * 24 + "ab" * 20
    run = lambda info: asyncio.run(legit.evm_mint_control("base", "0xt", info, None))  # noqa: E731
    answers[("eth_call", "0xd6c0b2c4")] = word
    assert run({}) == legit.MINT_BRIDGE
    answers.clear()
    assert run({}) == legit.MINT_NO_OWNER
    owner = "0x" + "ab" * 20
    answers[("eth_getCode", owner)] = "0x6080"
    assert run({"owner_address": owner}) == legit.MINT_CONTRACT
    answers[("eth_getCode", owner)] = "0x"
    assert run({"owner_address": owner}) == legit.MINT_WALLET
    answers.pop(("eth_getCode", owner))
    assert run({"owner_address": owner}) == legit.MINT_UNKNOWN


def test_an_account_is_judged_by_its_main_repository(monkeypatch):
    class R:
        status_code = 200

        def json(self):
            return [{"name": ".github", "size": 5, "pushed_at": "2026-10-19", "stargazers_count": 0},
                    {"name": "data", "size": 900, "pushed_at": "2026-10-18", "stargazers_count": 1},
                    {"name": "beefy-v2", "size": 50_000, "pushed_at": "2026-09-01", "stargazers_count": 300},
                    {"name": "fork", "size": 90_000, "fork": True, "stargazers_count": 999}]

    async def gh_get(client, url, **kw):
        return R()
    monkeypatch.setattr(legit, "gh_get", gh_get)
    assert asyncio.run(legit.github_repo("beefyfinance", None, None))["name"] == "beefy-v2"


def test_a_script_built_page_is_unreadable_not_empty():
    html = "<html><head>" + "<script>var x=1;</script>" * 600 + "</head><body><p>Loading</p></body></html>"
    page = {**depth.anatomy(html, "https://x.io"), "url": "https://x.io"}
    assert page["html_bytes"] >= depth.EMPTY_BIG_HTML and page["words"] < 40
    site = depth.judge_site(page, [], None, now=NOW)
    assert not site["fatal"] and site["unreadable"]
    small = {**depth.anatomy("<html><body><p>Hi</p></body></html>", "https://x.io"), "url": "https://x.io"}
    assert depth.judge_site(small, [], None, now=NOW)["fatal"] == "empty page"


def test_a_linked_majority_is_a_bundled_launch():
    """Spidey Show, 19/10: 68% of the supply in 54 linked wallets."""
    p = depth._judge_tokenomics(top1=2, top10=12, creator=0, holders=2430, insiders=54, lp_locked=100,
                                mintable=False, freezable=False, tax=0, rugged=False, linked_pct=68.0)
    assert "linked wallets hold 68%" in p["fatal"]
    ok = depth._judge_tokenomics(top1=2, top10=12, creator=0, holders=2430, insiders=54, lp_locked=100,
                                 mintable=False, freezable=False, tax=0, rugged=False, linked_pct=40.0)
    assert not ok["fatal"]
    bundled = {**_rug(), "risks": [], "insiderNetworks": [{"currentHolding": 680_000}]}   # supply 1M
    check = legit.judge_rugcheck(bundled)
    assert check["ok"] is False and "linked wallets hold 68%" in check["detail"]
    assert legit.judge_rugcheck({**bundled, "insiderNetworks": [{"currentHolding": 400_000}]})["ok"] is not False
