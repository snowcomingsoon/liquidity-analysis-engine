"""Arenas: the Top by narrative, pound for pound, and the nightly ladder."""
from app.trading.onchain import arenas

CAT = {"ai_agents": {"key": "ai_agents", "label": "AI Agents", "kind": None, "heat": 3},
       "privacy": {"key": "privacy", "label": "Privacy", "kind": None, "heat": 3},
       "rwa": {"key": "rwa", "label": "RWA", "kind": None, "heat": 2},
       "meme_dogs": {"key": "meme_dogs", "label": "Dog Memes", "kind": "meme", "heat": 3}}


def _e(sym, score, narr=(), chain="solana", blocks=None):
    return {"chain": chain, "token_address": sym, "symbol": sym, "score": score,
            "narratives": list(narr), "blocks": blocks}


def test_candidates_skip_memes_and_route_layers():
    assert arenas.candidates(_e("A", 50, ["meme_dogs", "privacy"]), CAT) == ["privacy"]
    assert arenas.candidates(_e("B", 50, ["meme_dogs"]), CAT) == [arenas.OTHER]
    assert arenas.candidates(_e("C", 50, ["privacy"], chain="layer"), CAT) == [arenas.CHAINS]
    assert arenas.candidates(_e("D", 50, [{"key": "rwa", "label": "RWA"}]), CAT) == ["rwa"]


def test_project_goes_where_it_leads_its_peers_most():
    es = [_e("X", 80, ["ai_agents", "privacy"]), _e("A1", 90, ["ai_agents"]), _e("A2", 88, ["ai_agents"]),
          _e("P1", 60, ["privacy"]), _e("P2", 55, ["privacy"])]
    where = arenas.assign(es, CAT)
    assert where["solana:X"] == "privacy"      # first among weak peers beats third among strong ones


def test_lonely_arena_is_dropped():
    es = [_e("R", 70, ["rwa", "privacy"]), _e("P1", 60, ["privacy"]), _e("P2", 50, ["privacy"]),
          _e("Z", 40, ["rwa"])]
    es.pop()                                   # RWA would hold R alone
    where = arenas.assign(es, CAT)
    assert where["solana:R"] == "privacy"
    lone = arenas.assign([_e("Q", 50, ["rwa"]), _e("P1", 60, ["privacy"]), _e("P2", 50, ["privacy"])], CAT)
    assert lone["solana:Q"] == arenas.OTHER


def test_build_marks_bench_and_pound_for_pound(monkeypatch):
    monkeypatch.setattr(arenas, "_catalog", lambda: CAT)
    es = [_e(f"A{i}", s, ["ai_agents"]) for i, s in enumerate([90, 70, 65, 60])] + \
         [_e(f"P{i}", s, ["privacy"]) for i, s in enumerate([62, 61, 60])]
    out = arenas.build(es, ladder={}, tenure={})
    ai = next(a for a in out["arenas"] if a["key"] == "ai_agents")
    assert [e["symbol"] for e in ai["entries"]] == ["A0", "A1", "A2", "A3"]
    assert [e["in"] for e in ai["entries"]] == [True, True, False, False]
    assert out["p4p"][0]["symbol"] == "A0" and out["p4p"][0]["arena_label"] == "AI Agents"
    # Three near-equal scores: the spread floor keeps the lead small.
    assert next(e for e in out["p4p"] if e["symbol"] == "P0")["z"] <= 0.4
    assert out["ladder"] == {"nights": 0, "ready": False}


def test_tenure_keeps_a_surpassed_project_in_for_three_days(monkeypatch):
    monkeypatch.setattr(arenas, "_catalog", lambda: CAT)
    tenure: dict = {}
    first = [_e("A", 80, ["ai_agents"]), _e("B", 60, ["ai_agents"])]
    arenas.build(first, ladder={}, tenure=tenure, now=0)
    assert set(tenure) == {"solana:A"}
    # Three newcomers push A below the median the next day: it stays in.
    later = first + [_e(f"N{i}", 90 + i, ["ai_agents"]) for i in range(3)]
    out = arenas.build(later, ladder={}, tenure=tenure, now=86400)
    a = next(e for e in out["arenas"][0]["entries"] if e["symbol"] == "A")
    assert a["in"] and a["held"]
    assert tenure["solana:A"] == 0             # counted from its entry, not refreshed
    out = arenas.build(later, ladder={}, tenure=tenure, now=arenas.TENURE_S + 1)
    a = next(e for e in out["arenas"][0]["entries"] if e["symbol"] == "A")
    assert not a["in"] and "solana:A" not in tenure


def test_tenure_ends_at_once_when_a_project_leaves_the_pool(monkeypatch):
    monkeypatch.setattr(arenas, "_catalog", lambda: CAT)
    tenure = {"solana:GONE": 0.0}
    arenas.build([_e("A", 80, ["ai_agents"]), _e("B", 60, ["ai_agents"])], ladder={}, tenure=tenure, now=10)
    assert "solana:GONE" not in tenure
    # A narrative filter reads the tenure but never writes it.
    tenure = {}
    arenas.build([_e("A", 80, ["ai_agents"]), _e("B", 60, ["ai_agents"])], ladder={}, prefer={"ai_agents"},
                 tenure=tenure, now=10)
    assert tenure == {}


def test_duel_counts_blocks_both_measured():
    a = {"blocks": {"usage": 50, "product": 80, "token": None}}
    b = {"blocks": {"usage": 60, "product": 70, "token": 90}}
    assert arenas.duel(a, b) == 0.5
    assert arenas.duel({"blocks": {"product": 90}}, b) == 1.0
    assert arenas.duel({"blocks": {}}, b) is None


def test_record_night_moves_ratings_once_per_night(monkeypatch):
    monkeypatch.setattr(arenas, "_catalog", lambda: CAT)
    strong = {k: 80 for k in arenas.BLOCKS}
    weak = {k: 40 for k in arenas.BLOCKS}
    es = [_e("S", 80, ["ai_agents"], blocks=strong), _e("W", 40, ["ai_agents"], blocks=weak)]
    state = {}
    assert arenas.record_night(es, now=1e6, state=state) == 1
    r = state["ratings"]
    assert r["solana:S"]["r"] > arenas.RATING_START > r["solana:W"]["r"]
    assert r["solana:S"]["nights"] == ["w"] and r["solana:W"]["nights"] == ["l"]
    assert arenas.record_night(es, now=1e6 + 3600, state=state) == 0     # same evening
    assert arenas.record_night(es, now=1e6 + 86400, state=state) == 1
    assert state["nights"] == 2


def test_privacy_holds_zk_and_tee_and_comes_first(monkeypatch):
    cat = {**CAT, "zero_knowledge": {"key": "zero_knowledge", "label": "Zero Knowledge", "kind": None, "heat": 3},
           "fhe_mpc_tee": {"key": "fhe_mpc_tee", "label": "FHE / MPC / TEE", "kind": None, "heat": 3}}
    monkeypatch.setattr(arenas, "_catalog", lambda: cat)
    es = [_e("DREGG", 70, ["zero_knowledge"]), _e("ROUTER", 75, ["fhe_mpc_tee", "ai_agents"]),
          _e("A1", 90, ["ai_agents"]), _e("A2", 88, ["ai_agents"]), _e("A3", 95, ["ai_agents"])]
    out = arenas.build(es, ladder={})
    assert out["arenas"][0]["key"] == "privacy"
    assert {e["symbol"] for e in out["arenas"][0]["entries"]} == {"DREGG", "ROUTER"}


def test_filter_keeps_projects_in_the_arena_asked(monkeypatch):
    monkeypatch.setattr(arenas, "_catalog", lambda: CAT)
    es = [_e("X", 95, ["ai_agents", "privacy"]), _e("P1", 60, ["privacy"]), _e("P2", 50, ["privacy"])]
    out = arenas.build(es, ladder={}, prefer={"privacy"})
    assert [a["key"] for a in out["arenas"]] == ["privacy"]


def test_filtered_arena_survives_with_one_project(monkeypatch):
    monkeypatch.setattr(arenas, "_catalog", lambda: CAT)
    out = arenas.build([_e("P", 60, ["privacy"])], ladder={}, prefer={"privacy"})
    assert [a["key"] for a in out["arenas"]] == ["privacy"]


def test_compute_keeps_its_projects_privacy_first():
    cat = {**CAT, "decentralized_compute": {"key": "decentralized_compute", "label": "Compute", "kind": None,
                                            "heat": 3}}
    assert arenas.candidates(_e("G", 50, ["ai_agents", "decentralized_compute"]), cat) == ["decentralized_compute"]
    assert arenas.candidates(_e("H", 50, ["decentralized_compute", "privacy"]), cat) == ["privacy"]


def test_claimed_arenas_always_offered(monkeypatch):
    cat = {**CAT, "decentralized_compute": {"key": "decentralized_compute", "label": "Compute", "kind": None,
                                            "heat": 3}}
    monkeypatch.setattr(arenas, "_catalog", lambda: cat)
    es = [_e("A1", 90, ["ai_agents"]), _e("A2", 80, ["ai_agents"]), _e("G1", 70, ["decentralized_compute"])]
    out = {a["key"]: a for a in arenas.build(es, ladder={})["arenas"]}
    assert out["decentralized_compute"]["size"] == 1      # one project is enough to keep the arena
    assert out["privacy"]["size"] == 0 and out["privacy"]["entries"] == []
    assert [a["key"] for a in arenas.build(es, ladder={})["arenas"]][-1] == "privacy"   # empty tiles last


def test_new_catalogue_keys_reach_stored_projects_at_read_time():
    from app import main
    e = {"narratives": ["rwa"], "description": "A decentralized exchange with concentrated liquidity pools"}
    assert main._narr_now(e) == {"rwa", "dex_amm"}
    assert main._narr_now({"narratives": [{"key": "privacy"}, None]}) == {"privacy"}


def test_project_also_shows_in_its_other_narratives(monkeypatch):
    monkeypatch.setattr(arenas, "_catalog", lambda: CAT)
    es = [_e("R", 70, ["rwa", "privacy"]), _e("P1", 60, ["privacy"]), _e("P2", 50, ["privacy"])]
    out = arenas.build(es, ladder={}, tenure={}, now=0)
    rwa = next(a for a in out["arenas"] if a["key"] == "rwa")
    assert [(e["symbol"], e["also"]) for e in rwa["entries"]] == [("R", True)]
    # One podium place, in the arena it competes for.
    assert [(e["symbol"], e["arena"]) for e in out["p4p"]] == [("R", "privacy")]


def test_podium_fills_three_steps_from_small_arenas(monkeypatch):
    """Two arenas of two have no spread: their leaders still stand on the
    podium after the ones that lead by a z (Lorenzo, 19/10: two steps only)."""
    monkeypatch.setattr(arenas, "_catalog", lambda: CAT)
    es = [_e(f"A{i}", s, ["ai_agents"]) for i, s in enumerate([90, 70, 60])] + \
         [_e("P0", 80, ["privacy"]), _e("P1", 50, ["privacy"]), _e("R0", 75, ["rwa"]), _e("R1", 55, ["rwa"])]
    out = arenas.build(es, ladder={}, tenure={})
    assert [e["symbol"] for e in out["p4p"]][:3] == ["A0", "P0", "R0"]
