"""Tokens born on a launchpad (pump.fun, letsbonk, bags, Pons): stricter gems rules.

Lorenzo, 20/10: "su PumpFun purtroppo ha molti token truffa [...] un token
Apple che di fatto sembrerebbe quello ufficiale della Apple, ma non lo e'
assolutamente". The 18-19/10 changes (launchpads as a source, unreadable
sites and program-held mints as penalties, program accounts out of the
wallet limits) were right for real projects and opened the door on
launchpads, where a script-built page with nothing in it is the norm. Here,
and only here, the older rules hold again, all but a minimum age ("ci
perdiamo i progetti [...] appena nati [...] come Veil").

Everything is read from the stored pillar facts: no call, so the board, the
Top's database rows and the early list judge alike, and a rule change applies
at the next ranking without a re-read.
"""
from __future__ import annotations

import re

from app.trading.onchain import depth

# Mint suffixes the launchpads grind for their tokens (Solana).
SUFFIXES = ("pump", "bonk", "BAGS")
SOURCE = "launchpad"               # discovery.GT_LAUNCHPADS
LINKED_MAX_PCT = 30.0              # linked wallets: 50% elsewhere (depth.LINKED_REJECT_PCT)

# A famous name on a launchpad is someone else's brand: nobody launches the
# real Apple on pump.fun. Whole words of the name, or the ticker itself.
BRANDS = frozenset("""
apple aapl tesla tsla nvidia nvda google googl alphabet amazon amzn microsoft msft meta facebook
instagram whatsapp netflix nflx openai chatgpt anthropic claude gemini grok xai deepmind spacex
starlink neuralink nike adidas disney cocacola pepsi mcdonalds starbucks samsung sony nintendo
playstation xbox ferrari lamborghini porsche bmw mercedes rolex gucci chanel prada visa
mastercard paypal blackrock jpmorgan goldman coinbase binance elon musk trump melania
biden obama nasa fifa uefa nba nfl youtube tiktok twitter reddit uber airbnb shopify
intel amd ibm walmart costco boeing
""".split())
BRAND_PHRASES = ("coca cola", "louis vuitton", "goldman sachs", "jp morgan", "red bull", "burger king")

_WORD = re.compile(r"[a-z0-9]+")


def is_launchpad(e: dict) -> bool:
    token = e.get("token_address") or ""
    if e.get("chain") == "solana" and token.endswith(SUFFIXES):
        return True
    return e.get("source") == SOURCE or SOURCE in (e.get("sources") or [])


def brand_of(symbol: str | None, name: str | None) -> str | None:
    """The famous brand a name or ticker borrows, if any."""
    text = f"{name or ''} {symbol or ''}".lower()
    words = set(_WORD.findall(text))
    joined = " ".join(_WORD.findall(text))
    for p in BRAND_PHRASES:
        if f" {p} " in f" {joined} ":
            return p
    hit = sorted(words & BRANDS)
    return hit[0] if hit else None


def gate(e: dict) -> str:
    """"" unless a launchpad token fails the stricter rules; the reason otherwise."""
    if not is_launchpad(e):
        return ""
    brand = brand_of(e.get("symbol"), e.get("name"))
    if brand:
        return f"launchpad token with a famous name ({brand}): not the real brand"
    pillars = e.get("pillars") or {}
    site, gh, tok = (pillars.get(k) or {} for k in ("site", "github", "tokenomics"))
    sf, gf, tf = (p.get("facts") or {} for p in (site, gh, tok))
    if sf.get("unreadable"):
        return "launchpad token: site not readable"
    linked = tf.get("linked_pct")
    if linked is not None and linked >= LINKED_MAX_PCT:
        return f"launchpad token: linked wallets hold {linked:.0f}% of supply"
    if tf.get("mint_by"):
        return f"launchpad token: new tokens can be minted by {tf['mint_by']}"
    top10 = tf.get("top10_all_pct")
    if top10 is not None and top10 > depth.TOP10_MAX_PCT:
        return f"launchpad token: top 10 accounts hold {top10:.0f}% (programs included)"
    if not site and not gh:
        return ""                       # not analysed yet: qualifies says so
    code = (gh.get("score") is not None and not gh.get("fatal")
            and (gf.get("code_kb") or 0) * 1024 >= depth.GH_REAL_CODE_BYTES
            and "all commits on a single day" not in (gh.get("flags") or []))
    product = (site.get("score") is not None and not site.get("fatal")
               and sf.get("verdict") not in ("thin", "scam") and site["score"] >= 50)
    if not code and not product:
        return "launchpad token: neither real code on GitHub nor a site that shows a product"
    return ""
