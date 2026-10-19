"""Scan dei progetti seri: filtri su CoinGecko e DexScreener, senza rete."""
import asyncio

import pytest

from app.trading.onchain import depth, discovery as d


@pytest.fixture(autouse=True)
def _clean():
    d.reset_for_tests()
    d.legit._found.clear()
    yield
    d.reset_for_tests()


def test_market_candidates_keeps_cap_band_and_drops_meme_names():
    rows = [{"id": "big", "symbol": "big", "name": "Big", "market_cap": 9_000_000},
            {"id": "huge", "symbol": "huge", "name": "Huge", "market_cap": 30_000_000},  # over the cap
            {"id": "tiny", "symbol": "tiny", "name": "Tiny", "market_cap": 5_000},   # under the early-gem floor
            {"id": "dog", "symbol": "doge2", "name": "Doge Inu", "market_cap": 500_000},
            {"id": "grid", "symbol": "grid", "name": "Grid Protocol", "market_cap": 900_000}]
    assert [c["id"] for c in d.market_candidates("robinhood", rows)] == ["big", "grid"]


def _coin(**kw):
    coin = {"symbol": "grid", "name": "Grid Protocol", "platforms": {"robinhood": "0xabc"},
            "categories": ["Robinhood Ecosystem", "Artificial Intelligence (AI)"],
            "links": {"homepage": ["https://grid.xyz"], "repos_url": {"github": ["https://github.com/grid/core"]},
                      "twitter_screen_name": "grid"},
            "description": {"en": "Inference network"}, "genesis_date": "2026-07-01"}
    coin.update(kw)
    return coin


def test_coin_detail_builds_item():
    item, why = d.from_coin_detail("robinhood", _coin(), {"symbol": "GRID", "market_cap": 900_000})
    assert why == "" and item["token_address"] == "0xabc" and item["github"] == "https://github.com/grid/core"
    assert item["website"] == "https://grid.xyz" and item["launched_at"]


def test_coin_detail_rejects_a_large_coin_bridged_onto_our_chain():
    big = _coin(market_data={"market_cap": {"usd": 2_000_000_000}})
    item, why = d.from_coin_detail("robinhood", big, {"symbol": "AAVE", "market_cap": 531_000})
    assert item is None and why.startswith("global market cap")
    small = _coin(market_data={"market_cap": {"usd": 500_000}})
    item, why = d.from_coin_detail("robinhood", small, {"symbol": "GRID", "market_cap": 900_000})
    assert why == "" and item["market_cap"] == 500_000


def test_coin_detail_rejects_meme_stock_and_missing_contract():
    assert d.from_coin_detail("robinhood", _coin(categories=["Robinhood Chain Meme"]))[1].startswith("category")
    assert d.from_coin_detail("robinhood", _coin(categories=["Tokenized Stocks"]))[1].startswith("category")
    assert d.from_coin_detail("solana", _coin())[1] == "no contract on this chain"


def test_coin_detail_without_github_goes_to_site_analysis():
    item, _ = d.from_coin_detail("robinhood", _coin(links={"homepage": ["https://grid.xyz"]}))
    assert item and item["github"] is None


def test_profiles_keep_own_site_on_our_chains():
    profiles = [
        {"chainId": "solana", "tokenAddress": "M1", "description": "ZK proving network",
         "links": [{"label": "Website", "url": "https://prover.io"}, {"type": "github", "url": "https://github.com/p/r"}]},
        {"chainId": "bsc", "tokenAddress": "M2", "links": [{"label": "Website", "url": "https://x.io"}]},
        {"chainId": "solana", "tokenAddress": "M3", "description": "the funniest meme on solana",
         "links": [{"label": "Website", "url": "https://lol.io"}]},
        {"chainId": "solana", "tokenAddress": "M4", "links": [{"type": "twitter", "url": "https://x.com/a"}]},
    ]
    out = d.profile_candidates(profiles)
    assert [c["token_address"] for c in out] == ["M1"] and out[0]["github"] == "https://github.com/p/r"


def test_step_queues_pages_then_details(monkeypatch):
    calls = []

    async def fake_get(client, path, params=None):
        calls.append(path)
        if path == "/coins/markets":
            return [{"id": "grid", "symbol": "grid", "name": "Grid Protocol", "market_cap": 900_000}]
        return _coin()

    monkeypatch.setattr(d, "_cg_get", fake_get)
    monkeypatch.setattr(d, "_save", lambda: None)
    monkeypatch.setattr(d.narratives, "coingecko_categories", lambda **k: [])
    added = []
    add = lambda item, source: added.append((item["symbol"], source)) or True  # noqa: E731
    now = 1_790_000_000.0
    asyncio.run(d._cg_step(None, add, now))                 # prepara il giro
    asyncio.run(d._cg_step(None, add, now + 1))             # troppo presto
    assert calls == []
    for i in range(1, 13):
        asyncio.run(d._cg_step(None, add, now + i * d.CG_GAP_S))
    assert ("GRID", "coingecko") in added
    assert d.status()["found"] >= 1


def test_github_of_another_project_counts_as_missing(monkeypatch):
    async def repo(owner, name, client):
        return {"full_name": "alice/rust-utils", "homepage": "", "description": "misc helpers"}

    monkeypatch.setattr(depth.legit, "github_repo", repo)
    out = asyncio.run(depth.analyze_github(["https://github.com/alice/rust-utils"], None, None,
                                           token={"chain": "solana", "token_address": "M", "symbol": "GRID",
                                                  "name": "Grid Protocol"}, website="https://grid.xyz"))
    assert out["fatal"] == "" and out["score"] is None and out["facts"]["missing"]


class _Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


class _Client:
    def __init__(self, routes):
        self.routes = routes
        self.urls = []

    async def get(self, url, **kw):
        self.urls.append(url)
        return next((r for k, r in self.routes.items() if k in url), _Resp(404, {}))


def test_github_found_by_account_declaring_the_site():
    c = _Client({"/users/gridarena": _Resp(200, {"blog": "gridarena.xyz"})})
    assert asyncio.run(d.legit.github_find("https://www.gridarena.xyz/", c)) == "https://github.com/gridarena"


def test_github_found_by_repo_homepage_only_on_exact_domain():
    items = [{"html_url": "https://github.com/x/other", "homepage": "https://gridarena.xyz.evil.io"},
             {"html_url": "https://github.com/y/arena", "homepage": "https://gridarena.xyz"}]
    c = _Client({"/search/repositories": _Resp(200, {"items": items})})
    assert asyncio.run(d.legit.github_find("https://gridarena.xyz", c)) == "https://github.com/y/arena"
    d.legit._found.clear()
    c = _Client({"/search/repositories": _Resp(200, {"items": items[:1]})})
    assert asyncio.run(d.legit.github_find("https://gridarena.xyz", c)) is None


def test_github_lookup_is_cached_but_not_when_github_fails():
    c = _Client({"/users/gridarena": _Resp(403, {})})
    assert asyncio.run(d.legit.github_find("https://gridarena.xyz", c)) is None
    c = _Client({"/users/gridarena": _Resp(200, {"blog": "https://gridarena.xyz"})})
    assert asyncio.run(d.legit.github_find("https://gridarena.xyz", c)) == "https://github.com/gridarena"
    c = _Client({})
    assert asyncio.run(d.legit.github_find("https://gridarena.xyz", c)) == "https://github.com/gridarena"
    assert c.urls == []


MINT = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
EVM = "0xDEd852De9fe9bA9b6f27f39e8e81cF851a5c79cC"


def test_readme_addresses_skips_words_and_known_programs():
    text = (f"## Token\nCA: `{MINT}`\nUses So11111111111111111111111111111111111111112 and "
            f"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA. Robinhood: {EVM}\n"
            "abcdefghijkmnopqrstuvwxyzabcdefghijk")
    out = d.readme_addresses(text)
    assert out == {"solana": [MINT], "robinhood": [EVM], "base": [EVM], "ethereum": [EVM], "arc": [EVM]}


def test_search_candidates_keeps_fresh_own_repos():
    now = 1_790_000_000.0
    items = [{"full_name": "a/live", "size": 900, "pushed_at": "2026-09-20T10:00:00Z"},
             {"full_name": "a/fork", "size": 900, "fork": True, "pushed_at": "2026-09-20T10:00:00Z"},
             {"full_name": "a/stale", "size": 900, "pushed_at": "2025-01-01T10:00:00Z"},
             {"full_name": "a/empty", "size": 0, "pushed_at": "2026-09-20T10:00:00Z"}]
    assert [c["full_name"] for c in d.search_candidates(items, now)] == ["a/live"]


def _pair(addr, cap, liq=20_000, chain="solana", symbol="PRVR", name="Prover Network"):
    return {"chainId": chain, "baseToken": {"address": addr, "symbol": symbol, "name": name},
            "marketCap": cap, "liquidity": {"usd": liq}, "pairAddress": "pool", "pairCreatedAt": 1_785_000_000_000,
            "info": {"websites": [{"url": "https://prover.io"}]}}


def test_token_from_pairs_picks_liquid_pool_in_band():
    repo = {"html_url": "https://github.com/p/r", "homepage": ""}
    item, why = d.token_from_pairs("solana", [_pair(MINT, 800_000, 5_000), _pair(MINT, 900_000, 50_000)], repo)
    assert why == "" and item["market_cap"] == 900_000 and item["github_verified"]
    assert item["website"] == "https://prover.io" and item["launched_at"] == 1_785_000_000
    assert d.token_from_pairs("solana", [_pair(MINT, 30_000_000)], repo)[1].startswith("cap")
    assert d.token_from_pairs("solana", [_pair(MINT, 500_000, symbol="PEPE", name="Pepe Inu")], repo)[1] == "meme name"


def test_repo_readme_to_leaderboard():
    d._state["gh_queue"].append({"full_name": "p/r", "html_url": "https://github.com/p/r", "homepage": "",
                                 "default_branch": "main"})
    c = _Client({"raw.githubusercontent.com/p/r/main/README.md": _Resp(200, {}),
                 "tokens/v1/solana/": _Resp(200, [_pair(MINT, 700_000)])})
    c.routes["raw.githubusercontent.com/p/r/main/README.md"].text = f"Our token: {MINT}"
    added = []
    asyncio.run(d._gh_repo(c, lambda item, src: added.append((item["token_address"], src)) or True, 1_790_000_000.0))
    assert added == [(MINT, "github")] and d._seen["gh:p/r"]["ok"]


def test_verified_readme_skips_ownership_check(monkeypatch):
    async def repo(owner, name, client):
        return {"full_name": "alice/rust-utils", "homepage": "", "description": "misc"}

    async def fetch(full, client):
        return {}

    monkeypatch.setattr(depth.legit, "github_repo", repo)
    monkeypatch.setattr(depth, "fetch_github", fetch)
    out = asyncio.run(depth.analyze_github(["https://github.com/alice/rust-utils"], None, None,
                                           token={"chain": "solana", "token_address": "M", "symbol": "GRID",
                                                  "github_verified": True}, website="https://grid.xyz"))
    assert out["fatal"] != "GitHub does not belong to the project"


def test_github_rate_limit_is_recorded():
    d.legit.github_rate.clear()
    r = _Resp(200, {})
    r.headers = {"x-ratelimit-limit": "60", "x-ratelimit-remaining": "0", "x-ratelimit-reset": "1790000000",
                 "x-ratelimit-resource": "core"}
    asyncio.run(d.legit.gh_get(_Client({"/x": r}), "https://api.github.com/x"))
    assert d.legit.github_rate["core"]["limit"] == 60 and d.legit.github_rate["core"]["remaining"] == 0


def test_jupiter_verified_list_keeps_real_projects_in_band():
    import time as _t
    from app.trading.onchain import discovery as dv
    now = _t.time()
    old = _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime(now - 60 * 86400))
    base = {"mcap": 2_000_000, "liquidity": 120_000, "website": "https://solrouter.com", "tags": ["verified"],
            "audit": {"mintAuthorityDisabled": True}, "firstPool": {"createdAt": old}}
    rows = [{**base, "id": "R", "symbol": "ROUTER", "name": "Solrouter"},
            {**base, "id": "M", "symbol": "PEPE2", "name": "Pepe", "tags": ["verified", "meme"]},
            {**base, "id": "B", "symbol": "ZAMA", "name": "Zama", "audit": {}},          # mint on: judged later
            {**base, "id": "Y", "symbol": "NEW", "name": "New", "firstPool": {"createdAt": _t.strftime(
                "%Y-%m-%dT%H:%M:%SZ", _t.gmtime(now - 86400))}},
            {**base, "id": "C", "symbol": "BIG", "name": "Big", "mcap": 30_000_000}]
    out = dv.jupiter_candidates(rows, now)
    # A pool of one day is not a reason (29/09: "il limite di data non ha granche' senso").
    assert [x["token_address"] for x in out] == ["R", "B", "Y"] and out[0]["website"] == "https://solrouter.com"


def test_base_is_searched_like_the_other_chains():
    profiles = [{"chainId": "base", "tokenAddress": "0xabc", "description": "Onchain order book",
                 "links": [{"label": "Website", "url": "https://book.xyz"}]}]
    assert [c["chain"] for c in d.profile_candidates(profiles)] == ["base"]
    addrs = d.readme_addresses("CA: 0x1111111111111111111111111111111111111111")
    assert addrs["base"] == addrs["robinhood"] == ["0x1111111111111111111111111111111111111111"]
    rows = [{"id": "book", "platforms": {"base": "0xAbC"}}]
    assert d.chain_index(rows)["base"] == {"book"}


def test_arc_is_a_read_only_gem_chain():
    """Arc (Circle's L1, chain id 5042): searched for gems, never traded (07/10)."""
    from app.sniper import scanner
    from app.trading.onchain import judge, legit, live_prices, radar, research, traction
    assert "arc" in legit.GEM_CHAINS and "arc" not in legit.MEME_CHAINS and "arc" not in radar.CHAINS
    assert legit.GOPLUS_CHAIN["arc"] == "5042" and legit.CHAIN_LABEL["arc"] == "Arc"
    assert d.CG_CATEGORIES["arc"][0] == "arc-ecosystem" and d.CG_PLATFORMS["arc"] == ("arc",)
    assert research.GECKO_NET["arc"] == live_prices.CHAINS["arc"] == scanner.GECKO_NETWORKS["arc"] == "arc"
    assert "arc" in scanner.SUPPORTED_CHAINS and "arc" in judge.LOCKERS
    assert traction._token("arc", "arc:0xAbC") == "0xabc" and traction._token("arc", "0xAbC") is None
    profiles = [{"chainId": "arc", "tokenAddress": "0xabc", "description": "Stablecoin FX",
                 "links": [{"label": "Website", "url": "https://fx.xyz"}]}]
    assert [c["chain"] for c in d.profile_candidates(profiles)] == ["arc"]
    assert d.chain_index([{"id": "fx", "platforms": {"arc": "0xAbC"}}])["arc"] == {"fx"}


def test_meme_and_gem_chains_are_split():
    from app.trading.onchain import legit, radar, traction
    # "BSC per le Meme insieme a Sol e Robinhood. Poi Eth e Base solo per le Gemme"
    assert set(radar.CHAINS) == {"solana", "robinhood", "bsc"}
    assert set(d.CG_CATEGORIES) == set(d.CG_PLATFORMS) == {"solana", "robinhood", "base", "ethereum", "arc"}
    assert all(c in legit.GOPLUS_CHAIN for c in ("bsc", "base", "ethereum"))
    assert traction._token("ethereum", "0xAbC") == "0xabc" and traction._token("base", "0xAbC") is None


def test_github_tries_every_linked_repo(monkeypatch):
    """A dead first link (404) is not "no repository" when another works (BV7X, 29/09)."""
    async def repo(owner, name, client):
        return {} if name == "old-repo" else {"full_name": f"{owner}/{name}"}

    async def fetch(full_name, client):
        return None

    monkeypatch.setattr(depth.legit, "github_repo", repo)
    monkeypatch.setattr(depth, "fetch_github", fetch)
    out = asyncio.run(depth.analyze_github(["https://github.com/bob/old-repo", "https://github.com/bob/protocol"],
                                           None, None))
    assert out.get("pending") == "GitHub not responding" and not out["fatal"]


def test_github_private_links_fall_back_to_the_account(monkeypatch):
    """BV7X: both linked repos 404, the account has a public one; none at all is missing, not fatal."""
    seen = []

    async def repo(owner, name, client):
        seen.append((owner, name))
        return {}

    monkeypatch.setattr(depth.legit, "github_repo", repo)
    out = asyncio.run(depth.analyze_github(["https://github.com/bob/a", "https://github.com/bob/b/tree/main"],
                                           None, None))
    assert seen[-1] == ("bob", None)
    assert out["fatal"] == "" and out["facts"]["missing"] and out["facts"]["linked"] == ["bob/a", "bob/b"]


def _gt_pools():
    tok = lambda i, sym, name: {"id": f"base_{i}", "type": "token",            # noqa: E731
                                "attributes": {"address": i, "symbol": sym, "name": name, "image_url": "missing.png"}}
    pool = lambda i, cap, liq: {"attributes": {"market_cap_usd": None, "fdv_usd": str(cap),  # noqa: E731
                                               "reserve_in_usd": str(liq), "pool_created_at": "2026-10-17T10:00:00Z"},
                                "relationships": {"base_token": {"data": {"id": f"base_{i}"}}}}
    return {"data": [pool("0xgood", 800_000, 40_000), pool("0xbig", 50_000_000, 900_000),
                     pool("0xthin", 300_000, 900), pool("0xweth", 400_000, 40_000), pool("0xpepe", 300_000, 40_000)],
            "included": [tok("0xgood", "AGNT", "Agent Protocol"), tok("0xbig", "BIG", "Big"), tok("0xthin", "THIN", "Thin"),
                         tok("0xweth", "WETH", "Wrapped Ether"), tok("0xpepe", "PEPE2", "Pepe Inu")]}


def test_new_pools_on_ethereum_and_base_feed_the_research(monkeypatch):
    """Lorenzo, 17/10: a source of new tokens for Ethereum and Base, as
    Jupiter is for Solana. In the band, liquid, not a meme, with a website."""
    import app.trading.onchain.usage as u
    monkeypatch.setattr(d, "GT_LAUNCHPADS", {})
    assert [c["token_address"] for c in d.new_pool_candidates("base", _gt_pools())] == ["0xgood"]
    asked = []

    async def gecko(client, url, params=None, caller=None):
        asked.append(url)
        if url.endswith("/info"):
            return {"data": {"attributes": {"websites": ["https://agent.example"], "twitter_handle": "agentp",
                                            "description": "An agent protocol"}}}
        return _gt_pools() if (params or {}).get("page") == 1 else None
    monkeypatch.setattr(u, "_gecko", gecko)
    added = []
    asyncio.run(d._poll_new_pools(None, lambda item, src: added.append((item["chain"], item["token_address"], item["website"], src)) or True, 1_000.0))
    assert added == [("ethereum", "0xgood", "https://agent.example", "geckoterminal"),
                     ("base", "0xgood", "https://agent.example", "geckoterminal")]
    assert any("/networks/eth/" in a for a in asked) and any("/networks/base/" in a for a in asked)
    added.clear()
    asyncio.run(d._poll_new_pools(None, lambda item, src: added.append(item) or True, 1_100.0))
    assert added == []                         # every 10 minutes, and each token once


def test_a_new_pool_without_a_website_is_not_analysed():
    assert d.token_info_fields({"data": {"attributes": {"websites": []}}}) == {}
    assert d.token_info_fields({"data": {"attributes": {"websites": ["https://x.example"], "description": "a meme coin"}}}) == {}


def test_each_chain_has_its_own_budget_of_token_pages(monkeypatch):
    """Review on #582: one shared budget let Ethereum starve Base."""
    import app.trading.onchain.usage as u
    monkeypatch.setattr(d, "GT_LAUNCHPADS", {})
    many = lambda: {"data": [{"attributes": {"market_cap_usd": "0", "fdv_usd": "500000", "reserve_in_usd": "20000"},  # noqa: E731
                              "relationships": {"base_token": {"data": {"id": f"t{i}"}}}} for i in range(8)],
                    "included": [{"id": f"t{i}", "attributes": {"address": f"0x{i}", "symbol": f"P{i}", "name": f"Project {i}"}}
                                 for i in range(8)]}
    reads = []

    async def gecko(client, url, params=None, caller=None):
        if url.endswith("/info"):
            reads.append(url.split("/networks/")[1].split("/")[0])
            return {"data": {"attributes": {"websites": [], "twitter_handle": "@x"}}}
        return many() if (params or {}).get("page") == 1 else None
    monkeypatch.setattr(u, "_gecko", gecko)
    asyncio.run(d._poll_new_pools(None, lambda item, src: True, 5_000.0))
    assert reads.count("eth") == d.GT_INFO_PER_CHAIN and reads.count("base") == d.GT_INFO_PER_CHAIN


def test_token_page_handles_are_normalised():
    f = d.token_info_fields({"data": {"attributes": {"websites": ["https://p.example"],
                                                     "twitter_handle": "https://twitter.com/proj", "telegram_handle": "@projchat"}}})
    assert {s["url"] for s in f["socials"]} == {"https://x.com/proj", "https://t.me/projchat"}


def test_the_bulk_sweep_waits_when_asked(monkeypatch):
    """18/10: tick(bulk=False) skips CoinGecko, runs the fast sources."""
    ran = []
    for name in ("_poll_jupiter", "_poll_new_pools", "_cg_step", "_poll_profiles", "_gh_repo"):
        async def step(client, add, now, _n=name):
            ran.append(_n)
        monkeypatch.setattr(d, name, step)

    async def gh(client, now):
        ran.append("_gh_search")
    monkeypatch.setattr(d, "_gh_search", gh)

    async def traction(client, add, now):
        ran.append("traction")
    monkeypatch.setattr(d.traction, "poll", traction)
    asyncio.run(d.tick(None, lambda item, src: True, now=1.0, bulk=False))
    assert "_cg_step" not in ran and {"_poll_jupiter", "_poll_new_pools", "_poll_profiles"} <= set(ran)
    ran.clear()
    asyncio.run(d.tick(None, lambda item, src: True, now=1.0))
    assert "_cg_step" in ran


def test_launchpads_feed_the_research(monkeypatch):
    """Lorenzo, 18/10: pump.fun (Veil), Meteora, Pons. Each launchpad's most
    traded pools, with the same filters as the new pools."""
    import app.trading.onchain.usage as u
    monkeypatch.setattr(d, "GT_CHAINS", {})
    asked = []

    async def gecko(client, url, params=None, caller=None):
        asked.append((url, (params or {}).get("sort")))
        if url.endswith("/info"):
            return {"data": {"attributes": {"websites": ["https://agent.example"], "description": "An agent protocol"}}}
        return _gt_pools() if "/dexes/pumpswap/" in url or "/dexes/pons-dot-family/" in url else None
    monkeypatch.setattr(u, "_gecko", gecko)
    added = []
    asyncio.run(d._poll_new_pools(None, lambda item, src: added.append((item["chain"], item["token_address"], src)) or True, 1_000.0))
    assert added == [("solana", "0xgood", "launchpad"), ("robinhood", "0xgood", "launchpad")]
    pads = [a for a in asked if "/dexes/" in a[0]]
    assert {a[1] for a in pads} == {"h24_tx_count_desc"}
    assert any("/networks/solana/dexes/meteora-dbc/" in a[0] for a in pads)


def test_each_poll_starts_from_the_next_launchpad(monkeypatch):
    """Review on #591: the first launchpads must not use up the budget every time."""
    import app.trading.onchain.usage as u
    monkeypatch.setattr(d, "GT_CHAINS", {})
    monkeypatch.setattr(d, "GT_LAUNCHPADS", {"solana": ("solana", ("a", "b", "c"))})
    first = []

    async def gecko(client, url, params=None, caller=None):
        if "/dexes/" in url and len(first) < 10:
            first.append(url.split("/dexes/")[1].split("/")[0])
        return None
    monkeypatch.setattr(u, "_gecko", gecko)
    for i in range(3):
        n = len(first)
        asyncio.run(d._poll_new_pools(None, lambda item, src: True, 1_000.0 + i * d.GT_POLL_S))
        first.append("|")
        assert first[n] == "abc"[i]
