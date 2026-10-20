from app.trading.onchain import launchpad, leaderboard as lb

PUMP = "So1aNaMint1111111111111111111111111111pump"


def _e(**kw):
    good = {"site": {"score": 70, "facts": {"verdict": "promising"}},
            "github": {"score": 0, "fatal": "no GitHub", "facts": {}},
            "tokenomics": {"score": 80, "facts": {"linked_pct": 5, "top10_all_pct": 30}}}
    e = {"chain": "solana", "token_address": PUMP, "symbol": "VEIL", "name": "Veil", "pillars": good}
    e.update(kw)
    return e


def test_only_launchpad_tokens_are_judged():
    assert launchpad.is_launchpad(_e())
    assert launchpad.is_launchpad({"chain": "robinhood", "token_address": "0xab", "sources": ["launchpad"]})
    assert not launchpad.is_launchpad({"chain": "solana", "token_address": "Mint111", "source": "jupiter"})
    assert launchpad.gate({"chain": "solana", "token_address": "Mint111", "symbol": "AAPL", "name": "Apple"}) == ""


def test_famous_names_are_out_on_launchpads():
    """Lorenzo, 20/10: an "Apple" token on pump.fun ranked as if it were the real one."""
    assert "apple" in launchpad.gate(_e(symbol="APPLE", name="Apple Inc"))
    assert "coca cola" in launchpad.gate(_e(symbol="COKE", name="Coca-Cola"))
    assert launchpad.gate(_e(symbol="PNAPL", name="Pineapple Labs")) == ""
    assert launchpad.gate(_e()) == ""


def test_older_rules_hold_on_launchpads():
    def with_(**facts):
        e = _e()
        e["pillars"]["tokenomics"]["facts"].update(facts)
        return launchpad.gate(e)
    assert "linked wallets" in with_(linked_pct=35)
    assert "minted" in with_(mint_by="a program")
    assert "top 10" in with_(top10_all_pct=70)
    unread = _e()
    unread["pillars"]["site"] = {"score": 50, "facts": {"unreadable": "empty page"}}
    assert "not readable" in launchpad.gate(unread)
    thin = _e()
    thin["pillars"]["site"] = {"score": 55, "facts": {"verdict": "thin"}}
    assert "neither real code" in launchpad.gate(thin)
    thin["pillars"]["github"] = {"score": 60, "facts": {"code_kb": 400}, "flags": []}
    assert launchpad.gate(thin) == ""


def test_qualifies_applies_the_launchpad_gate():
    assert "famous name" in lb.qualifies(_e(symbol="TSLA", name="Tesla"))
