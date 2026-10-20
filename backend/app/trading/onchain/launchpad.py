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
import time

from app.trading.onchain import depth

# Mint suffixes the launchpads grind for their tokens (Solana).
SUFFIXES = ("pump", "bonk", "BAGS")
SOURCE = "launchpad"               # discovery.GT_LAUNCHPADS
LINKED_MAX_PCT = 30.0              # linked wallets: 50% elsewhere (depth.LINKED_REJECT_PCT)
# BORLY (20/10): first in the Top 26 minutes after its launch, a rug 12 hours
# later. Lorenzo: "Imposta i punti per tutti gli account, tranne il punto C".
PROBATION_S = 24 * 3600            # A: out of the Top (Early only) for its first day
DOMAIN_MIN_DAYS = 7                # B: a site younger than this is not a product

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


def born_at(e: dict) -> float | None:
    t = e.get("launched_at") or e.get("found_at") or e.get("first_seen")
    return float(t) if t else None


def on_probation(e: dict, now: float | None = None) -> bool:
    """A launchpad token in its first PROBATION_S: Early, never the Top or the podium."""
    born = born_at(e)
    return is_launchpad(e) and born is not None and (now or time.time()) - born < PROBATION_S


def gate(e: dict, now: float | None = None, top: bool = True) -> str:
    """"" unless a launchpad token fails the stricter rules; the reason
    otherwise. top=False asks for the Early list, where the trial day is no bar."""
    if not is_launchpad(e):
        return ""
    now = now or time.time()
    brand = brand_of(e.get("symbol"), e.get("name"))
    if brand:
        return f"launchpad token with a famous name ({brand}): not the real brand"
    born = born_at(e)
    if top and on_probation(e, now):
        until = time.strftime("%d/%m %H:%M", time.gmtime(born + PROBATION_S))
        return f"launchpad token on its first-day trial (until {until} UTC)"
    # D: holders read in the first hours show a launch, not a distribution
    # (RugCheck had not linked BORLY's wallets yet): a reading after the
    # first day is needed.
    pillars = e.get("pillars") or {}
    tok_at = (e.get("checked_at") or {}).get("tokenomics") or e.get("analyzed_at")
    if top and born is not None and tok_at and float(tok_at) < born + PROBATION_S \
            and now - born >= PROBATION_S and pillars.get("tokenomics"):
        return "launchpad token: holders read in its first day, waiting for a new reading"
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
    # B: a domain registered with the token (borly.fun: 0 days) is no product.
    young_domain = sf.get("domain_days") is not None and sf["domain_days"] < DOMAIN_MIN_DAYS
    product = (site.get("score") is not None and not site.get("fatal") and not young_domain
               and sf.get("verdict") not in ("thin", "scam") and site["score"] >= 50)
    if not code and not product:
        return ("launchpad token: site domain only a few days old and no real code on GitHub" if young_domain
                else "launchpad token: neither real code on GitHub nor a site that shows a product")
    return ""
