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
