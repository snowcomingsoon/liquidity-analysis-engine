import pytest

from app.providers import dexscreener, gecko_client


@pytest.fixture(autouse=True)
def _fresh_gecko_gate(monkeypatch):
    """La cache e il tetto di GeckoTerminal sono globali: un test non deve
    vedere le risposte finte di un altro, ne' aspettare il suo minuto (ne'
    i 5 s di pausa dopo un 429 finto senza Retry-After)."""
    monkeypatch.setattr(gecko_client, "DEFAULT_COOLDOWN_S", 0.01)
    # Tests send bursts no real minute would: the learned limit starts high.
    monkeypatch.setattr(gecko_client, "START_PER_MIN", gecko_client.GLOBAL_PER_MIN)
    dexscreener._gecko_seen.clear()
    gecko_client.reset_for_tests()
    from app.trading.onchain import research
    research._gecko.clear()            # token info, shared by the usage measure since 19/10
    yield
    dexscreener._gecko_seen.clear()
    gecko_client.reset_for_tests()


@pytest.fixture(autouse=True)
def _private_projects_db(monkeypatch, tmp_path):
    """The Gem Finder's project database is a file on the volume: every test
    gets its own, empty."""
    from app.trading.onchain import projects_db
    monkeypatch.setattr(projects_db, "_DB_FILE", tmp_path / "projects.db")
    yield


@pytest.fixture(autouse=True)
def _fresh_github_cache():
    """Stessa cosa per la cache e la quota di GitHub."""
    from app.trading.onchain import legit
    legit._gh_cache.clear()
    legit._gh_blocked.clear()
    yield
    legit._gh_cache.clear()
    legit._gh_blocked.clear()


@pytest.fixture(autouse=True)
def _onchain_wallets_on(monkeypatch):
    """Execution tests use made-up owner ids with no user behind them: treat
    their wallets as switched on. Tests of the switch itself re-patch this."""
    from app.trading.onchain import risk
    monkeypatch.setattr(risk, "_wallet_enabled", lambda owner_id, chain: True)
    yield


@pytest.fixture(autouse=True)
def _trading_on(monkeypatch):
    """The trading and strategy tests predate the switch that turned them off
    (Lorenzo, 07/10): they run with it on. Tests of the switch re-patch it."""
    from app.config import settings
    monkeypatch.setattr(settings, "onchain_trading_enabled", True)
    yield


@pytest.fixture(autouse=True)
def _private_arena_ladder(monkeypatch, tmp_path):
    """The arenas' Elo ladder is a file on the volume: every test gets its own."""
    from app.trading.onchain import arenas
    monkeypatch.setattr(arenas, "_FILE", tmp_path / "arena_ladder.json")
    yield


@pytest.fixture(autouse=True)
def _private_deepseek_journal(monkeypatch, tmp_path):
    """The DeepSeek call journal is a file on the volume: every test gets its own."""
    from app.notify import deepseek_calls
    monkeypatch.setattr(deepseek_calls, "_FILE", tmp_path / "deepseek_calls.jsonl")
    deepseek_calls.reset_for_tests()
    yield



@pytest.fixture(autouse=True)
def _private_gem_hold(monkeypatch, tmp_path):
    """Whitekobra's hold clocks (gem_hold.py) start empty in every test."""
    from app.trading.onchain import gem_hold
    monkeypatch.setattr(gem_hold, "_FILE", tmp_path / "gem_hold.json")
    gem_hold.reset_for_tests()
    yield


@pytest.fixture(autouse=True)
def _private_quant_memory(monkeypatch, tmp_path):
    from app.trading.onchain import quant_memory
    monkeypatch.setattr(quant_memory, "_path", tmp_path / "quant.sqlite3")


@pytest.fixture(autouse=True)
def _private_history(monkeypatch, tmp_path):
    """The append-only evaluation history is a file on the volume: every test gets its own."""
    from app.trading.onchain import history
    monkeypatch.setattr(history, "_FILE", tmp_path / "onchain_history.jsonl")
    yield



@pytest.fixture(autouse=True)
def _usage_open(request, monkeypatch):
    """The board tests predate the usage gates (07/10): they see every token as
    used. Tests marked usage_gates measure the gates themselves."""
    if request.node.get_closest_marker("usage_gates"):
        yield
        return
    from app.trading.onchain import leaderboard
    monkeypatch.setattr(leaderboard, "usage_gate", lambda e, cap_floor=True: "")
    yield


def pytest_configure(config):
    config.addinivalue_line("markers", "usage_gates: run with the real usage gates")


@pytest.fixture(autouse=True)
def _private_app_jobs(monkeypatch, tmp_path):
    """App jobs and push subscriptions are files on the volume, and a push is
    a network call: every test gets its own files and no real push."""
    from app import jobs
    from app.notify import web_push
    monkeypatch.setattr(jobs, "_FILE", tmp_path / "app_jobs.json")
    monkeypatch.setattr(jobs, "_jobs", {})
    monkeypatch.setattr(jobs, "_loaded", False)
    monkeypatch.setattr(web_push, "_KEYS_FILE", tmp_path / "vapid_keys.json")
    monkeypatch.setattr(web_push, "_SUBS_FILE", tmp_path / "push_subscriptions.json")
    monkeypatch.setattr(web_push, "_keys", None)
    monkeypatch.setattr(web_push, "_subs", None)
    monkeypatch.setattr(web_push, "_deliver", lambda sub, payload: 201)
    yield


@pytest.fixture(autouse=True)
def _research_ai_on(monkeypatch):
    """The AI readings' own tests run with them on; the switch has its own
    test (test_research_ai_off)."""
    from app.config import settings
    monkeypatch.setattr(settings, "research_ai_enabled", True)


@pytest.fixture(autouse=True)
def _private_market_peaks(monkeypatch, tmp_path):
    """The 24h highs and crashes (market_peaks.py) start empty in every test."""
    from app.trading.onchain import market_peaks
    monkeypatch.setattr(market_peaks, "_FILE", tmp_path / "market_peaks.json")
    market_peaks.reset_for_tests()
    yield
    market_peaks.reset_for_tests()


@pytest.fixture(autouse=True)
def _private_ai_veto(monkeypatch, tmp_path):
    """The free AI's verdicts (ai_veto.py) start empty, and no key is set."""
    from app.trading.onchain import ai_veto
    monkeypatch.setattr(ai_veto, "_FILE", tmp_path / "ai_veto.json")
    ai_veto.reset_for_tests()
    yield
    ai_veto.reset_for_tests()
