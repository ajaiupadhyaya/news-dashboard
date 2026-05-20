from fastapi.testclient import TestClient

from app.main import app
from app.models import Bar, Fundamentals, Quote
from app.providers import yfinance_provider

client = TestClient(app)


def _bars(closes):
    return [
        Bar(date=f"2026-01-{i + 1:02d}", open=c, high=c + 1, low=c - 1,
            close=c, volume=1000)
        for i, c in enumerate(closes)
    ]


def test_overview_endpoint(db, monkeypatch):
    monkeypatch.setenv("WATCHLIST_DEFAULT", "AAPL")
    monkeypatch.setattr(yfinance_provider, "get_history",
                        lambda *a, **k: _bars([100.0, 101.0]))
    monkeypatch.setattr(yfinance_provider, "get_quote",
                        lambda sym: Quote(symbol=sym, price=5.0, change=0.1,
                                          change_pct=2.0, volume=1,
                                          as_of="2026-01-02"))
    resp = client.get("/api/finance/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["watchlist"][0]["symbol"] == "AAPL"
    assert "breadth" in body and "updated_at" in body


def test_instrument_endpoint(db, monkeypatch):
    monkeypatch.setattr(yfinance_provider, "get_history",
                        lambda *a, **k: _bars([100.0 + i for i in range(30)]))
    monkeypatch.setattr(yfinance_provider, "get_fundamentals",
                        lambda sym: Fundamentals(symbol=sym, name="Test Co"))
    resp = client.get("/api/finance/instrument/aapl")
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "AAPL"
    assert len(body["bars"]) == 30
    assert body["profile"]["name"] == "Test Co"


def test_instrument_endpoint_404_for_unknown(db, monkeypatch):
    monkeypatch.setattr(yfinance_provider, "get_history", lambda *a, **k: [])
    assert client.get("/api/finance/instrument/ZZZZ").status_code == 404
