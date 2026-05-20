import pytest

from app import database
from app.cache import cache


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
