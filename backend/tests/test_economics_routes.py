from fastapi.testclient import TestClient

from app.main import app
from app.models import IndicatorPoint
from app.providers import fred_provider

client = TestClient(app)


def _series(n):
    return [IndicatorPoint(date=f"2026-{(i % 12) + 1:02d}-01",
                           value=100.0 + i) for i in range(n)]


def test_economics_overview_endpoint(db, monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series",
                        lambda sid, **kw: _series(30))
    monkeypatch.setattr(fred_provider, "get_release_calendar", lambda: [])
    resp = client.get("/api/economics/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert "indicators" in body and "calendar" in body
    assert "updated_at" in body


def test_economics_indicator_endpoint(db, monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series",
                        lambda sid, **kw: _series(40))
    resp = client.get("/api/economics/indicator/unrate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["series_id"] == "UNRATE"
    assert len(body["series"]) == 40


def test_economics_indicator_404_for_unknown(db, monkeypatch):
    resp = client.get("/api/economics/indicator/NOT_A_SERIES")
    assert resp.status_code == 404
