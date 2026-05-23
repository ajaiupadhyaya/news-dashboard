import pytest
from fastapi.testclient import TestClient

from app import database
from app.cache import cache

_TEST_TOKEN = "test-token-quant"


@pytest.fixture(autouse=True)
def _clear_cache():
    """Keep the shared cache from leaking state between tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Fresh SQLite database per test, created from the SQLAlchemy schema."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    database.reset_engine()
    database.init_db()
    yield
    database.reset_engine()


@pytest.fixture
def client(monkeypatch):
    """TestClient with DASHBOARD_TOKEN set so auth-gated routes require a token."""
    monkeypatch.setenv("DASHBOARD_TOKEN", _TEST_TOKEN)
    from app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authorization header matching the test token set by the `client` fixture."""
    return {"Authorization": f"Bearer {_TEST_TOKEN}"}
