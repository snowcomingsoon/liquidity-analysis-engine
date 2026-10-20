"""The journal of DeepSeek calls (issue #358, I00): repeats, failures, cache."""
import asyncio
import json

import pytest

from app.notify import deepseek_calls as dc
from app.notify import deepseek_desk as dd


@pytest.fixture(autouse=True)
def _ledger(tmp_path, monkeypatch):
    from app import free_ai
    monkeypatch.setattr(free_ai, "keys", lambda: {"groq": "k"})
    monkeypatch.setattr(dd, "_STORE_FILE", tmp_path / "u.json")
    dd.reset_for_tests()


class _Resp:
    def __init__(self, content, usage=None, fail=False):
        self._data = {"choices": [{"message": {"content": content}}],
                      "usage": usage or {"prompt_tokens": 100, "completion_tokens": 20, "prompt_cache_hit_tokens": 60}}
        self._fail = fail
        self.status_code = 503 if fail else 200
        self.text = "HTTP 503" if fail else ""

    def raise_for_status(self):
        if self._fail:
            raise RuntimeError("HTTP 503")

    def json(self):
        return self._data


class _Http:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.bodies = []

    async def post(self, url, json=None, headers=None):
        self.bodies.append(json)
        return self.answers.pop(0)


def _ask(http, user="same dossier", subject="solana:AAA"):
    return asyncio.run(dd.ask([{"role": "system", "content": "S"}, {"role": "user", "content": user}], kind="research",
                              json_mode=True, http=http, purpose="judge", subject=subject))


def test_same_question_twice_is_a_repeat_and_the_same_answer_says_it_bought_nothing():
    http = _Http(_Resp('{"score": 7}'), _Resp('{"score": 7}'), _Resp('{"score": 5}'))
    _ask(http)
    _ask(http)
    _ask(http, user="liquidity halved")
    rows = dc.recent()
    assert "dup_age" not in rows[0] and "dup_age" not in rows[2]
    assert rows[1]["same_out"] is True and rows[1]["purpose"] == "judge" and rows[1]["subject"] == "solana:AAA"
    s = dc.stats()
    j = s["by_purpose"]["judge"]
    assert j["calls"] == 3 and j["repeats"] == 1 and j["repeats_same_answer"] == 1
    assert j["repeat_tokens"] == 120 and j["subjects"] == 1 and j["calls_per_subject"] == 3
    assert j["cache_hit_share"] == 0.6


def test_no_prompt_text_is_kept():
    _ask(_Http(_Resp('{"a": 1}')), user="SECRET-LOOKING TEXT")
    line = dc._FILE.read_text()
    assert "SECRET-LOOKING" not in line and json.loads(line)["chars"] == len("S") + len("SECRET-LOOKING TEXT")


def test_failures_and_unparsable_answers_are_counted():
    with pytest.raises(RuntimeError):
        _ask(_Http(*[_Resp("", fail=True) for _ in range(8)]))   # every free model in turn
    from app import free_ai
    free_ai._cool.clear()                                         # they cooled down: back after a minute
    _ask(_Http(_Resp("not json")))
    j = dc.stats()["by_purpose"]["judge"]
    assert j["errors"] == 1 and j["json_bad"] == 1
    assert "503" in dc.recent()[1]["err"]


def test_the_journal_survives_a_restart_and_still_spots_repeats():
    _ask(_Http(_Resp('{"x": 1}')))
    dc._rows.clear()
    dc._last.clear()
    dc._loaded = False
    _ask(_Http(_Resp('{"x": 2}')))
    last = dc.recent()[0]
    assert "dup_age" in last and last["same_out"] is False


def test_old_calls_are_not_repeats():
    body = {"model": "m", "messages": [{"role": "user", "content": "q"}], "max_tokens": 5}
    dc.log(kind="k", purpose="p", subject="s", body=body, content="a", usage={}, ms=1, now=1000.0)
    row = dc.log(kind="k", purpose="p", subject="s", body=body, content="a", usage={}, ms=1,
                 now=1000.0 + dc.DUP_WINDOW_S + 1)
    assert "dup_age" not in row
