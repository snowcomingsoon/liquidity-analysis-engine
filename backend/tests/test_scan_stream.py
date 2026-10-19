import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main
from app.auth import get_current_user


def test_stream_sends_id_and_keeps_result_for_a_dropped_client(monkeypatch):
    from app.trading.onchain import manual_scan

    async def fake_scan(query, emit=None, **kw):
        emit({"plan": ["dex"]})
        return {"token": {"symbol": query}}

    monkeypatch.setattr(manual_scan, "scan", fake_scan)
    main.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="u1")
    try:
        c = TestClient(main.app)
        lines = [json.loads(x) for x in c.post("/api/onchain/scan/stream", json={"query": "cpool"}).text.splitlines()]
        assert "id" in lines[0] and lines[1] == {"plan": ["dex"]} and lines[-1]["result"]["token"]["symbol"] == "cpool"
        got = c.get(f"/api/onchain/scan/result/{lines[0]['id']}").json()
        # The steps ride along: whoever reopens the app sees what the scout did.
        assert got == {"done": True, "result": {"token": {"symbol": "cpool"}, "steps": [{"plan": ["dex"]}]}}
        assert c.get("/api/onchain/scan/result/nope").status_code == 404
    finally:
        main.app.dependency_overrides.clear()
