from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_watchlist_crud_flow(db):
    assert client.get("/api/watchlist").json() == {"symbols": []}

    resp = client.post("/api/watchlist", json={"symbol": "aapl"})
    assert resp.status_code == 200
    assert resp.json() == {"symbols": ["AAPL"]}

    client.post("/api/watchlist", json={"symbol": "MSFT"})
    assert client.get("/api/watchlist").json() == {"symbols": ["AAPL", "MSFT"]}

    resp = client.delete("/api/watchlist/aapl")
    assert resp.json() == {"symbols": ["MSFT"]}


def test_post_rejects_blank_symbol(db):
    resp = client.post("/api/watchlist", json={"symbol": "   "})
    assert resp.status_code == 400


def test_watchlist_requires_auth_when_enabled(db, monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    assert client.get("/api/watchlist").status_code == 401
    ok = client.get("/api/watchlist", headers={"Authorization": "Bearer tok-1"})
    assert ok.status_code == 200
