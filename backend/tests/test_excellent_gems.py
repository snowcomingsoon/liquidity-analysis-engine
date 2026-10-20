"""21/10, DREGG: GitHub 89 for the best public code of the small projects,
a final 66 under a quality of 82.7, and the AI's "avoid" at 0.6."""
import time

from app import free_ai
from app.trading.onchain import ai_veto, depth, leaderboard as lb

DREGG_GH = {"repo": "emberian/dregg", "commits": "100+", "commits_90d": 3787, "active_days": 5, "active_weeks_12": 8,
            "span_days": 45, "last_commit_days": 18.1, "authors": 3, "contributors": 9, "code_kb": 252233,
            "tests": True, "ci": True, "readme": True, "license": "AGPL-3.0", "trivial_pct": 0}


def _dregg():
    pillars = {"site": {"score": 76, "facts": {}, "flags": []},
               "github": {"score": 89, "facts": dict(DREGG_GH), "flags": []},
               "tokenomics": {"score": 81, "facts": {}, "flags": ["linked wallets hold 40% of supply (815 wallets)"]}}
    return {"chain": "solana", "token_address": "XkeTpump", "symbol": "DREGG", "pillars": pillars,
            "overall": depth.overall(pillars), "launched_at": time.time() - 100 * 86400}


def test_steady_weeks_and_a_recent_commit_get_full_marks():
    assert round(depth.github_score(DREGG_GH, [])) == 100
    pillars = _dregg()["pillars"]
    assert depth.rescore_github(pillars) and pillars["github"]["score"] == 100
    assert not depth.rescore_github(pillars)                     # already today's
    thin = {**DREGG_GH, "active_weeks_12": 2, "last_commit_days": 120, "contributors": 1, "authors": 1}
    assert depth.github_score(thin, []) < 70


def test_excellent_quality_sets_a_floor_under_the_final_score():
    e = _dregg()
    depth.rescore_github(e["pillars"])
    e["overall"] = depth.overall(e["pillars"])
    q = e["overall"]["score"]
    assert q >= 80
    assert lb.final_score(e) >= q - lb.EXCELLENT_FLOOR_GAP
    assert lb.final_score(e, kobra=True) >= q - lb.EXCELLENT_FLOOR_GAP


def test_the_ai_never_takes_out_an_excellent_project(monkeypatch):
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k"})
    e = _dregg()
    depth.rescore_github(e["pillars"])
    e["overall"] = depth.overall(e["pillars"])
    ai_veto._load()
    ai_veto._verdicts["solana:xketpump"] = {"verdict": "avoid", "confidence": 0.95, "reason": "garbled site",
                                            "at": time.time(), "impersonates": None, "meme": False}
    assert ai_veto.excellent(e) and ai_veto.reason(e) == ""
    weak = {**e, "token_address": "WEAKpump", "pillars": {**e["pillars"], "github": {"score": 40, "facts": {}}}}
    weak["overall"] = depth.overall(weak["pillars"])
    ai_veto._verdicts["solana:weakpump"] = dict(ai_veto._verdicts["solana:xketpump"])
    assert "nothing real" in ai_veto.reason(weak)
