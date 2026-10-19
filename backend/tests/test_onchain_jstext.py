"""JavaScript-built sites are read as a visitor sees them, and a page we
could not read is unknown, never a weak project (PFWA, 29/09)."""
import asyncio
import json
import time

import httpx
import pytest

from app.trading.onchain import depth, jstext, leaderboard as lb, legit, research as rs

PFWA_DESC = ("PFWA is an independent, decentralized prediction market protocol built on the Robinhood Chain. "
             "We allow users to create and trade markets on token metrics, community sentiment, and protocol "
             "milestones for any token on the network.")


def _push(s: str) -> str:
    return f"<script>self.__next_f.push([1,{json.dumps(s)}])</script>"


def _app_router_page() -> str:
    """A Next.js app-router page: empty body, the text in escaped RSC chunks."""
    body = "Every outcome is its own token on a bonding curve, so the odds move with every trade."
    tree = ["$", "main", None, {"className": "min-h-screen flex flex-col px-4 md:flex", "children": [
        ["$", "h1", None, {"className": "text-3xl font-bold", "children": "PFWA Docs"}],
        ["$", "p", None, {"children": PFWA_DESC}],
        ["$", "a", None, {"href": "/docs", "children": "Docs"}],
        ["$", "p", None, {"children": "$L1f"}],
        ["$", "div", None, {"children": "404: This page could not be found."}]]}]
    flight = ('1:"$Sreact.fragment"\n2:I[248337,["/_next/static/chunks/14sumbkzggy9f.js?dpl=dpl_Cjyt6RSD"],"default"]\n'
              f"0:{json.dumps(tree)}\n")
    t_row = f"5:T{len(body.encode()):x},{body}"
    return ('<!DOCTYPE html><html><head><title>PFWA</title>'
            '<script src="/_next/static/chunks/main.js" async></script></head>'
            '<body class="font-mono"><div hidden=""></div>'
            + _push(flight[:40]) + _push(flight[40:]) + _push(t_row) + "</body></html>")


def test_next_app_router_text_is_read():
    raw = _app_router_page()
    _, text = legit.page_text(raw)
    assert "decentralized prediction market protocol" in text
    assert "bonding curve" in text and "PFWA Docs" in text
    for noise in ("min-h-screen", "text-3xl", "_next/static", "$L1f", "could not be found", "Sreact"):
        assert noise not in text
    assert "/docs" in jstext.links(raw)


def test_next_pages_router_data_is_read():
    data = {"props": {"pageProps": {"hero": {"title": "Private AI inference on Solana",
                                             "body": "Queries are encrypted client-side and processed inside a TEE."},
                                    "className": "bg-black text-white"}},
            "page": "/", "buildId": "a1b2c3d4e5f6g7h8i9j0"}
    raw = ('<html><head><meta name="description" content="Solrouter routes private prompts."></head>'
           '<body><div id="__next"></div><script id="__NEXT_DATA__" type="application/json">'
           + json.dumps(data) + "</script></body></html>")
    _, text = legit.page_text(raw)
    assert "Private AI inference on Solana" in text and "processed inside a TEE" in text
    assert "Solrouter routes private prompts." in text
    assert "bg-black" not in text and "a1b2c3" not in text


def test_json_ld_and_noscript_are_read():
    ld = {"@type": "Organization", "description": "A permissionless lending market for real-world assets."}
    raw = ('<html><body><div id="root"></div><script type="application/ld+json">' + json.dumps(ld)
           + "</script><noscript>You need JavaScript to run this app.</noscript></body></html>")
    _, text = legit.page_text(raw)
    assert "permissionless lending market" in text and "You need JavaScript" in text


def test_bare_shell_is_unreadable_not_weak():
    raw = ('<html><head><title>App</title><script type="module" src="/assets/index-abc123.js"></script></head>'
           '<body><div id="root"></div></body></html>')
    _, text = legit.page_text(raw)
    assert jstext.is_shell(raw, len(text.split()))
    page = depth.anatomy(raw, "https://example.org/")
    page.update(url="https://example.org/", https=True, not_own=None, shell=True)
    site = depth.judge_site(page, [], None)
    assert site["score"] is None and site["unreadable"] and not site["fatal"]
    # With a description, and without: neutral, flagged, never a fail.
    for desc in (PFWA_DESC, ""):
        p = rs.judge_research([site], desc, None)
        assert p["score"] == rs.UNREAD_SCORE and not p["fatal"] and not p.get("pending")
        assert "JavaScript" in p["facts"]["unreadable"]


def test_a_readable_static_page_is_not_a_shell():
    raw = "<html><body><div id='root'></div><p>" + "real words " * 40 + "</p></body></html>"
    _, text = legit.page_text(raw)
    assert not jstext.is_shell(raw, len(text.split()))


def test_site_that_timed_out_is_unread_but_a_404_is_gone():
    down = depth._pending("site", "ConnectTimeout")
    p = rs.judge_research([down], PFWA_DESC, None)
    assert p["score"] == rs.UNREAD_SCORE and p["facts"]["unreadable"]
    gone = rs.judge_research([depth._pending("site", "responds 404")], PFWA_DESC, None)
    assert not gone["facts"].get("unreadable") and gone["score"] < rs.UNREAD_SCORE
    assert rs.judge_research([down], "", None).get("pending")   # nothing to read at all: retry later


def test_fetch_site_renders_a_shell_when_a_browser_is_there(monkeypatch):
    shell = '<html><body><div id="root"></div><script type="module" src="/assets/index-x.js"></script></body></html>'

    async def public(host):
        return True

    async def render(url, allow):
        return "<html><body><h1>Grid Arena</h1><p>" + "an onchain strategy game " * 20 + "</p></body></html>"

    async def run():
        transport = httpx.MockTransport(lambda r: httpx.Response(200, text=shell,
                                                                 headers={"content-type": "text/html"}))
        async with httpx.AsyncClient(transport=transport) as c:
            return await legit.fetch_site("https://grid.example/", c)

    monkeypatch.setattr(legit, "_public_host", public)
    monkeypatch.setattr(jstext, "_unavailable", True)          # no browser: stays a shell
    site = asyncio.run(run())
    assert site["ok"] and site["shell"] and not site["rendered"]
    assert site["render_error"] == "no headless browser on this server"   # the reason travels with the page
    monkeypatch.setattr(jstext, "render", render)
    site = asyncio.run(run())
    assert site["rendered"] and not site["shell"] and "onchain strategy game" in site["text"]


def test_render_skips_silently_without_playwright(monkeypatch):
    monkeypatch.setattr(jstext, "_unavailable", False)
    monkeypatch.setenv(jstext.RENDER_ENV, "0")
    assert asyncio.run(jstext.render("https://x.example/", None)) is None


def test_a_browser_that_did_not_start_is_retried_not_off_for_good(monkeypatch):
    # AUREON, 08/10: one failed start used to leave every JS site unreadable until a restart.
    monkeypatch.setattr(jstext, "_unavailable", False)
    monkeypatch.setattr(jstext, "_down_until", jstext.time.time() + 60)
    assert asyncio.run(jstext.render("https://a.example/", None)) is None
    assert "retrying" in jstext.last_failure["https://a.example/"]
    monkeypatch.setattr(jstext, "_down_until", 0.0)
    monkeypatch.setitem(jstext._cache, "https://a.example/", (jstext.time.time(), "<html>built</html>"))
    assert asyncio.run(jstext.render("https://a.example/", None)) == "<html>built</html>"


@pytest.fixture
def _board():
    lb.reset_for_tests()
    yield
    lb.reset_for_tests()


def test_unreadable_site_does_not_fail_the_floor(_board):
    item = {"chain": "solana", "token_address": "PFWAmint", "pair_address": "PFWApool", "symbol": "PFWA",
            "market_cap": 300_000, "created_at": time.time() - 30 * 86400}
    lb.add(item, "coingecko")
    k = lb._key("solana", "PFWAmint")
    site = {"key": "site", "score": 30, "facts": {"unreadable": depth.UNREADABLE_JS}, "flags": [], "fatal": ""}
    lb.apply_analysis(k, {"github": {"key": "github", "score": 80, "facts": {}, "flags": [], "fatal": ""},
                          "site": site,
                          "tokenomics": {"key": "tokenomics", "score": 80, "facts": {}, "flags": [], "fatal": ""}})
    assert lb.qualifies(lb._entries[k]) == ""
    lb._entries[k]["pillars"]["site"]["facts"] = {}
    assert lb.qualifies(lb._entries[k]).startswith("site too weak")


def test_unreadable_site_with_an_empty_description_rejects():
    """Spidey Show, 19/10: a script-built site took a neutral 50 while the
    reader had found nothing in the description (substance 1)."""
    raw = ('<html><head><script type="module" src="/assets/index.js"></script></head>'
           '<body><div id="root"></div></body></html>')
    page = depth.anatomy(raw, "https://spidey.example/")
    page.update(url="https://spidey.example/", https=True, not_own=None, shell=True)
    site = depth.judge_site(page, [], None)
    thin = {"substance": 1, "verdict": "thin", "points": 10, "red_flags": ["nothing built, token has no role"]}
    p = rs.judge_research([site], "Meet Spidey Show. A world of its own.", thin)
    assert p["fatal"] and "nothing built" in p["fatal"]
    real = {"substance": 6, "verdict": "promising", "points": 60}
    assert not rs.judge_research([site], PFWA_DESC, real)["fatal"]
    assert not rs.judge_research([site], PFWA_DESC, {**thin, "substance": 3})["fatal"]
