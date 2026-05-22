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


def test_economics_dashboard_endpoint(db, monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series", lambda sid, **kw: _series(30))
    monkeypatch.setattr(fred_provider, "get_release_calendar", lambda: [])
    resp = client.get("/api/economics/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert "categories" in body
    assert "recession_signals" in body
    assert "calendar" in body
    assert len(body["categories"]) == 6


def test_economics_indicator_accepts_transform_and_range(db, monkeypatch):
    seen = {}

    def fake_get_series(sid, units="lin", observation_start=None, **kw):
        seen[sid] = {"units": units, "observation_start": observation_start}
        return _series(40)

    monkeypatch.setattr(fred_provider, "get_series", fake_get_series)
    monkeypatch.setattr(fred_provider, "get_recession_periods", lambda: [])
    resp = client.get(
        "/api/economics/indicator/unrate?transform=pc1&range=5y")
    assert resp.status_code == 200
    assert seen["UNRATE"]["units"] == "pc1"
    assert seen["UNRATE"]["observation_start"] is not None
