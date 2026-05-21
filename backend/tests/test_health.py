from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_app_starts_with_lifespan(db):
    """Entering the TestClient context runs the lifespan (configure_logging,
    init_db, start_scheduler) and exiting runs shutdown without error."""
    with TestClient(app) as live_client:
        assert live_client.get("/health").status_code == 200


def test_ready_returns_ok_when_db_reachable(db):
    """With a working database, /health/ready reports ok."""
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_ready_returns_503_when_db_unreachable(monkeypatch):
    """If the database cannot be reached, /health/ready returns 503."""
    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr("app.routes.health.get_engine", boom)
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "database unavailable"
