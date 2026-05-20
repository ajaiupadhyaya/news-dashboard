# Phase 1a — Backend Foundation & Finance API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Execution setup:** Work on a feature branch or git worktree (`git checkout -b phase-1a-backend` from `main`), not directly on `main`. The repo root is `~/Documents/news-dashboard`; all paths below are relative to it.

**Goal:** Build a Python FastAPI backend that serves the Finance domain end-to-end — watchlist management, a market overview, and a per-instrument drill-down — backed by yfinance, a database, a TTL cache, and a scheduler.

**Architecture:** A single FastAPI app under `backend/app/`. Provider adapters wrap external data (yfinance) behind plain functions; a pure-function analysis layer computes metrics; a service layer assembles domain responses; routes serve only cached/computed data so the frontend never blocks on a third-party API. Persistence uses SQLAlchemy with a Python-defined schema that runs on SQLite (local/tests) and Postgres (production) unchanged.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, yfinance, pandas, SQLAlchemy 2.0, APScheduler, pytest.

**Reuses from the Models project (`~/Documents/Models`):** the provider-adapter pattern, the JSON-logging + request-ID middleware pattern (`api/logging_config.py`, `api/main.py`), the `SCHEDULER_ENABLED`-gated APScheduler pattern (`api/scheduler.py`), and the quant formulas (`core/quant_engine.py`). The DB layer is intentionally rebuilt cleaner than Models' raw-SQL `core/db.py`: a Python-defined SQLAlchemy schema, portable across SQLite and Postgres, so it is fully unit-testable without a running Postgres.

**Not in scope for Plan 1a** (deliberately deferred): the frontend (Plan 1b), deploy configs (Plan 1c), the News/Politics/Economics domains (Phases 2–4), the AI layer (Phase 5), and the instrument drill-down's correlations / company-news / filings (later phases). The Plan 1a instrument endpoint covers OHLCV + technicals + fundamentals only.

---

## File Structure

```
backend/
  requirements.txt              Runtime dependencies
  requirements-dev.txt          Test/dev dependencies
  pytest.ini                    pytest configuration
  .env.example                  Documented environment variables
  README.md                     Backend quickstart
  app/
    __init__.py
    main.py                     FastAPI app, middleware, router registration, lifespan
    config.py                   Environment-driven Settings
    logging_config.py           JSON formatter + request-id contextvar
    middleware.py               RequestIDMiddleware
    models.py                   Pydantic response/domain models
    cache.py                    TTLCache class + shared `cache` instance
    database.py                 SQLAlchemy schema, engine, OHLCV save/load
    store.py                    Watchlist + preferences persistence
    auth.py                     login() + require_auth dependency
    providers/
      __init__.py
      yfinance_provider.py      get_history / get_quote / get_fundamentals
    analysis/
      __init__.py
      metrics.py                Pure metric functions
    services/
      __init__.py
      finance_service.py        build_overview / build_instrument
    routes/
      __init__.py
      health.py                 GET /health
      auth_routes.py            POST /api/auth/login, GET /api/auth/status
      watchlist.py              GET/POST/DELETE /api/watchlist
      finance.py                GET /api/finance/overview, /instrument/{symbol}
    scheduler.py                APScheduler setup + warm_overview job
  tests/
    conftest.py                 Shared fixtures (db, cache-clear)
    test_health.py
    test_config.py
    test_middleware.py
    test_models.py
    test_cache.py
    test_database.py
    test_store.py
    test_auth.py
    test_yfinance_provider.py
    test_metrics.py
    test_finance_service.py
    test_watchlist_routes.py
    test_finance_routes.py
    test_scheduler.py
```

Each file has one responsibility. `app/main.py` is the only file modified by multiple tasks; those tasks show its complete contents each time.

---

## Task 1: Backend scaffold + health endpoint

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/pytest.ini`
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/app/routes/__init__.py` (empty)
- Create: `backend/app/routes/health.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Create dependency files**

`backend/requirements.txt`:
```
fastapi>=0.110
uvicorn[standard]>=0.29
yfinance>=0.2.40
pandas>=2.2
SQLAlchemy>=2.0
psycopg2-binary>=2.9
APScheduler>=3.10
python-dotenv>=1.0
```

`backend/requirements-dev.txt`:
```
-r requirements.txt
pytest>=8.0
httpx>=0.27
```

`backend/pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 2: Create empty package files**

Create empty files `backend/app/__init__.py` and `backend/app/routes/__init__.py`.

- [ ] **Step 3: Install dependencies**

Run: `cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt`
Expected: installs complete with "Successfully installed ...". Use this venv for every later command.

- [ ] **Step 4: Write the failing test**

`backend/tests/test_health.py`:
```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 6: Write the implementation**

`backend/app/routes/health.py`:
```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """Liveness probe — never touches the database or external APIs."""
    return {"status": "ok"}
```

`backend/app/main.py`:
```python
from fastapi import FastAPI

from app.routes.health import router as health_router

app = FastAPI(title="News & Markets Dashboard API", version="0.1.0")
app.include_router(health_router)
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: PASS — `test_health_returns_ok PASSED`.

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/requirements-dev.txt backend/pytest.ini \
        backend/app/__init__.py backend/app/routes/__init__.py \
        backend/app/routes/health.py backend/app/main.py backend/tests/test_health.py
git commit -m "feat: backend scaffold with health endpoint"
```

---

## Task 2: Configuration module

**Files:**
- Create: `backend/app/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_config.py`:
```python
from app.config import get_settings


def test_defaults_when_env_unset(monkeypatch):
    for var in ("DATABASE_URL", "DASHBOARD_TOKEN", "DASHBOARD_PASSWORD",
                "SCHEDULER_ENABLED", "CACHE_TTL_SECONDS", "WATCHLIST_DEFAULT"):
        monkeypatch.delenv(var, raising=False)
    s = get_settings()
    assert s.database_url is None
    assert s.dashboard_token is None
    assert s.scheduler_enabled is False
    assert s.cache_ttl_seconds == 300
    assert s.watchlist_default == ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]
    assert s.cors_origins == ["*"]


def test_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "60")
    monkeypatch.setenv("WATCHLIST_DEFAULT", "TSLA, AMD")
    monkeypatch.setenv("CORS_ORIGINS", "https://a.com, https://b.com")
    s = get_settings()
    assert s.database_url == "postgresql://x"
    assert s.scheduler_enabled is True
    assert s.cache_ttl_seconds == 60
    assert s.watchlist_default == ["TSLA", "AMD"]
    assert s.cors_origins == ["https://a.com", "https://b.com"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.config'`.

- [ ] **Step 3: Write the implementation**

`backend/app/config.py`:
```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    dashboard_token: str | None
    dashboard_password: str | None
    scheduler_enabled: bool
    log_level: str
    cors_origins: list[str]
    cache_ttl_seconds: int
    watchlist_default: list[str]


def _env_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_settings() -> Settings:
    """Read settings from the environment on every call (no caching) so tests
    that mutate env vars see fresh values."""
    return Settings(
        database_url=os.getenv("DATABASE_URL") or None,
        dashboard_token=os.getenv("DASHBOARD_TOKEN") or None,
        dashboard_password=os.getenv("DASHBOARD_PASSWORD") or None,
        scheduler_enabled=os.getenv("SCHEDULER_ENABLED", "false").strip().lower()
        in ("1", "true", "yes"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        cors_origins=_env_list("CORS_ORIGINS", "*"),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "300")),
        watchlist_default=_env_list("WATCHLIST_DEFAULT", "AAPL,MSFT,NVDA,GOOGL,AMZN"),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: PASS — both tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat: environment-driven settings"
```

---

## Task 3: JSON logging + request-ID middleware

**Files:**
- Create: `backend/app/logging_config.py`
- Create: `backend/app/middleware.py`
- Modify: `backend/app/main.py` (full new contents shown)
- Test: `backend/tests/test_middleware.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_middleware.py`:
```python
import json

from fastapi.testclient import TestClient

from app.main import app
from app.logging_config import JsonFormatter, request_id_ctx

client = TestClient(app)


def test_response_has_request_id_header():
    resp = client.get("/health")
    assert resp.headers.get("X-Request-ID")


def test_request_id_echoed_when_supplied():
    resp = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert resp.headers["X-Request-ID"] == "abc123"


def test_json_formatter_emits_request_id():
    import logging

    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", None, None)
    token = request_id_ctx.set("rid-9")
    try:
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_ctx.reset(token)
    assert payload["message"] == "hello"
    assert payload["request_id"] == "rid-9"
    assert payload["level"] == "INFO"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_middleware.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.logging_config'`.

- [ ] **Step 3: Write logging_config.py**

`backend/app/logging_config.py`:
```python
import json
import logging
import sys
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    """Render each log record as a single line of JSON, including the
    request id bound to the current context."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
```

- [ ] **Step 4: Write middleware.py**

`backend/app/middleware.py`:
```python
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.logging_config import request_id_ctx


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Bind a request id to the logging context and echo it on the response."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = rid
        return response
```

- [ ] **Step 5: Update main.py to register the middleware**

`backend/app/main.py` (complete new contents):
```python
from fastapi import FastAPI

from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import RequestIDMiddleware
from app.routes.health import router as health_router

configure_logging(get_settings().log_level)

app = FastAPI(title="News & Markets Dashboard API", version="0.1.0")
app.add_middleware(RequestIDMiddleware)
app.include_router(health_router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_middleware.py tests/test_health.py -v`
Expected: PASS — all four tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/logging_config.py backend/app/middleware.py \
        backend/app/main.py backend/tests/test_middleware.py
git commit -m "feat: JSON logging and request-id middleware"
```

---

## Task 4: Domain models

**Files:**
- Create: `backend/app/models.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_models.py`:
```python
from app.models import (
    Bar, Quote, WatchlistQuote, Fundamentals, SectorChange, Breadth,
    OverviewResponse, Technicals, InstrumentStats, InstrumentResponse,
)


def test_bar_and_quote_construct():
    bar = Bar(date="2026-01-02", open=1.0, high=2.0, low=0.5, close=1.5, volume=100)
    assert bar.close == 1.5
    quote = Quote(symbol="AAPL", price=1.5, change=0.1, change_pct=2.0,
                  volume=100, as_of="2026-01-02")
    assert quote.symbol == "AAPL"


def test_watchlist_quote_extends_quote_with_sparkline():
    wq = WatchlistQuote(symbol="AAPL", price=1.5, change=0.1, change_pct=2.0,
                        volume=100, as_of="2026-01-02", sparkline=[1.0, 1.5])
    assert wq.sparkline == [1.0, 1.5]
    assert wq.price == 1.5


def test_fundamentals_optional_fields_default_none():
    f = Fundamentals(symbol="AAPL", name="Apple")
    assert f.sector is None
    assert f.pe_ratio is None


def test_overview_response_assembles():
    resp = OverviewResponse(
        watchlist=[],
        indices=[],
        sectors=[SectorChange(symbol="XLK", name="Technology", change_pct=1.0)],
        breadth=Breadth(advancers=1, decliners=0, unchanged=0,
                        advance_decline_ratio=1.0),
        updated_at="2026-01-02T00:00:00Z",
    )
    assert resp.sectors[0].symbol == "XLK"


def test_instrument_response_assembles():
    resp = InstrumentResponse(
        symbol="AAPL",
        profile=Fundamentals(symbol="AAPL", name="Apple"),
        bars=[Bar(date="2026-01-02", open=1, high=2, low=1, close=1.5, volume=10)],
        technicals=Technicals(sma_20=[None], sma_50=[None], sma_200=[None]),
        stats=InstrumentStats(momentum_1m=1.0, momentum_3m=2.0, momentum_6m=3.0,
                              volatility_30d=10.0),
        updated_at="2026-01-02T00:00:00Z",
    )
    assert resp.symbol == "AAPL"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'`.

- [ ] **Step 3: Write the implementation**

`backend/app/models.py`:
```python
from pydantic import BaseModel


class Bar(BaseModel):
    date: str          # ISO date, e.g. "2026-01-02"
    open: float
    high: float
    low: float
    close: float
    volume: int


class Quote(BaseModel):
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    as_of: str


class WatchlistQuote(Quote):
    sparkline: list[float]


class Fundamentals(BaseModel):
    symbol: str
    name: str
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    price_to_book: float | None = None
    dividend_yield: float | None = None
    week52_high: float | None = None
    week52_low: float | None = None
    beta: float | None = None


class SectorChange(BaseModel):
    symbol: str
    name: str
    change_pct: float


class Breadth(BaseModel):
    advancers: int
    decliners: int
    unchanged: int
    advance_decline_ratio: float


class OverviewResponse(BaseModel):
    watchlist: list[WatchlistQuote]
    indices: list[Quote]
    sectors: list[SectorChange]
    breadth: Breadth
    updated_at: str


class Technicals(BaseModel):
    sma_20: list[float | None]
    sma_50: list[float | None]
    sma_200: list[float | None]


class InstrumentStats(BaseModel):
    momentum_1m: float
    momentum_3m: float
    momentum_6m: float
    volatility_30d: float
    week52_high: float | None = None
    week52_low: float | None = None


class InstrumentResponse(BaseModel):
    symbol: str
    profile: Fundamentals
    bars: list[Bar]
    technicals: Technicals
    stats: InstrumentStats
    updated_at: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: PASS — all five tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_models.py
git commit -m "feat: pydantic domain models"
```

---

## Task 5: TTL cache

**Files:**
- Create: `backend/app/cache.py`
- Test: `backend/tests/test_cache.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_cache.py`:
```python
from app.cache import TTLCache


def test_set_and_get():
    c = TTLCache(ttl_seconds=100, clock=lambda: 0.0)
    c.set("k", 42)
    assert c.get("k") == 42


def test_missing_key_returns_none():
    c = TTLCache(ttl_seconds=100, clock=lambda: 0.0)
    assert c.get("nope") is None


def test_entry_expires_after_ttl():
    now = {"t": 0.0}
    c = TTLCache(ttl_seconds=10, clock=lambda: now["t"])
    c.set("k", "v")
    now["t"] = 9.0
    assert c.get("k") == "v"
    now["t"] = 11.0
    assert c.get("k") is None


def test_get_or_compute_computes_once():
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return "value"

    c = TTLCache(ttl_seconds=100, clock=lambda: 0.0)
    assert c.get_or_compute("k", compute) == "value"
    assert c.get_or_compute("k", compute) == "value"
    assert calls["n"] == 1


def test_clear_empties_the_cache():
    c = TTLCache(ttl_seconds=100, clock=lambda: 0.0)
    c.set("k", 1)
    c.clear()
    assert c.get("k") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_cache.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.cache'`.

- [ ] **Step 3: Write the implementation**

`backend/app/cache.py`:
```python
import time
from typing import Any, Callable

from app.config import get_settings


class TTLCache:
    """In-memory time-to-live cache. The clock is injectable for testing."""

    def __init__(self, ttl_seconds: int = 300,
                 clock: Callable[[], float] = time.monotonic):
        self._ttl = ttl_seconds
        self._clock = clock
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._clock() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (self._clock() + self._ttl, value)

    def get_or_compute(self, key: str, compute: Callable[[], Any]) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = compute()
        self.set(key, value)
        return value

    def clear(self) -> None:
        self._store.clear()


# Shared application cache instance.
cache = TTLCache(ttl_seconds=get_settings().cache_ttl_seconds)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_cache.py -v`
Expected: PASS — all five tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/cache.py backend/tests/test_cache.py
git commit -m "feat: TTL cache"
```

---

## Task 6: Database layer

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_database.py`

- [ ] **Step 1: Write the shared conftest fixtures**

`backend/tests/conftest.py`:
```python
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
```

- [ ] **Step 2: Write the failing test**

`backend/tests/test_database.py`:
```python
from app.database import save_ohlcv, load_ohlcv
from app.models import Bar


def _bar(date: str, close: float) -> Bar:
    return Bar(date=date, open=close, high=close + 1, low=close - 1,
               close=close, volume=1000)


def test_save_and_load_ohlcv(db):
    save_ohlcv("AAPL", [_bar("2026-01-02", 100.0), _bar("2026-01-03", 101.0)])
    rows = load_ohlcv("AAPL")
    assert [r.date for r in rows] == ["2026-01-02", "2026-01-03"]
    assert rows[1].close == 101.0


def test_save_ohlcv_replaces_previous_rows(db):
    save_ohlcv("AAPL", [_bar("2026-01-02", 100.0)])
    save_ohlcv("AAPL", [_bar("2026-01-03", 105.0), _bar("2026-01-04", 106.0)])
    rows = load_ohlcv("AAPL")
    assert [r.date for r in rows] == ["2026-01-03", "2026-01-04"]


def test_load_ohlcv_unknown_symbol_returns_empty(db):
    assert load_ohlcv("ZZZZ") == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_database.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.database'`.

- [ ] **Step 4: Write the implementation**

`backend/app/database.py`:
```python
import logging
import os

from sqlalchemy import (Column, Float, Integer, MetaData, String, Table, Text,
                        create_engine, delete, insert, select)
from sqlalchemy.engine import Engine

from app.config import get_settings
from app.models import Bar

logger = logging.getLogger(__name__)
metadata = MetaData()

ohlcv = Table(
    "ohlcv", metadata,
    Column("symbol", String(20), primary_key=True),
    Column("date", String(10), primary_key=True),
    Column("open", Float),
    Column("high", Float),
    Column("low", Float),
    Column("close", Float),
    Column("volume", Integer),
)

watchlist = Table(
    "watchlist", metadata,
    Column("symbol", String(20), primary_key=True),
    Column("position", Integer),
    Column("added_at", String(32)),
)

preferences = Table(
    "preferences", metadata,
    Column("key", String(64), primary_key=True),
    Column("value", Text),
)

_engine: Engine | None = None


def _resolve_url() -> str:
    url = get_settings().database_url
    if url:
        return url
    os.makedirs("data", exist_ok=True)
    return "sqlite:///data/dashboard.db"


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = _resolve_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
        if not url.startswith("postgresql"):
            logger.warning("DATABASE_URL is not Postgres (%s); "
                           "data is not durable on ephemeral hosts", url)
    return _engine


def init_db() -> None:
    """Create all tables if they do not exist."""
    metadata.create_all(get_engine())


def reset_engine() -> None:
    """Test helper: dispose the cached engine so a new DATABASE_URL is picked up."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def save_ohlcv(symbol: str, bars: list[Bar]) -> None:
    """Replace all stored bars for `symbol` with `bars` (portable upsert)."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(delete(ohlcv).where(ohlcv.c.symbol == symbol))
        if bars:
            conn.execute(insert(ohlcv), [
                {"symbol": symbol, "date": b.date, "open": b.open, "high": b.high,
                 "low": b.low, "close": b.close, "volume": b.volume}
                for b in bars
            ])


def load_ohlcv(symbol: str) -> list[Bar]:
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            select(ohlcv).where(ohlcv.c.symbol == symbol).order_by(ohlcv.c.date)
        ).mappings().all()
    return [Bar(date=r["date"], open=r["open"], high=r["high"], low=r["low"],
                close=r["close"], volume=r["volume"]) for r in rows]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_database.py -v`
Expected: PASS — all three tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/database.py backend/tests/conftest.py backend/tests/test_database.py
git commit -m "feat: SQLAlchemy database layer with OHLCV persistence"
```

---

## Task 7: Watchlist + preferences store

**Files:**
- Create: `backend/app/store.py`
- Test: `backend/tests/test_store.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_store.py`:
```python
from app.store import (get_watchlist, add_to_watchlist, remove_from_watchlist,
                       get_preference, set_preference)


def test_watchlist_starts_empty(db):
    assert get_watchlist() == []


def test_add_preserves_order_and_uppercases(db):
    add_to_watchlist("aapl")
    add_to_watchlist("MSFT")
    assert get_watchlist() == ["AAPL", "MSFT"]


def test_add_is_idempotent(db):
    add_to_watchlist("AAPL")
    add_to_watchlist("AAPL")
    assert get_watchlist() == ["AAPL"]


def test_remove(db):
    add_to_watchlist("AAPL")
    add_to_watchlist("MSFT")
    remove_from_watchlist("aapl")
    assert get_watchlist() == ["MSFT"]


def test_preferences_round_trip(db):
    assert get_preference("theme", "dark") == "dark"
    set_preference("theme", "light")
    assert get_preference("theme", "dark") == "light"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.store'`.

- [ ] **Step 3: Write the implementation**

`backend/app/store.py`:
```python
from datetime import datetime, timezone

from sqlalchemy import delete, func, insert, select

from app.database import get_engine, preferences, watchlist


def get_watchlist() -> list[str]:
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(watchlist.c.symbol).order_by(watchlist.c.position)
        ).all()
    return [r[0] for r in rows]


def add_to_watchlist(symbol: str) -> None:
    symbol = symbol.strip().upper()
    if not symbol:
        return
    with get_engine().begin() as conn:
        exists = conn.execute(
            select(watchlist.c.symbol).where(watchlist.c.symbol == symbol)
        ).first()
        if exists:
            return
        max_pos = conn.execute(select(func.max(watchlist.c.position))).scalar()
        next_pos = 0 if max_pos is None else max_pos + 1
        conn.execute(insert(watchlist).values(
            symbol=symbol, position=next_pos,
            added_at=datetime.now(timezone.utc).isoformat()))


def remove_from_watchlist(symbol: str) -> None:
    symbol = symbol.strip().upper()
    with get_engine().begin() as conn:
        conn.execute(delete(watchlist).where(watchlist.c.symbol == symbol))


def get_preference(key: str, default: str | None = None) -> str | None:
    with get_engine().begin() as conn:
        row = conn.execute(
            select(preferences.c.value).where(preferences.c.key == key)
        ).first()
    return row[0] if row else default


def set_preference(key: str, value: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(delete(preferences).where(preferences.c.key == key))
        conn.execute(insert(preferences).values(key=key, value=value))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_store.py -v`
Expected: PASS — all five tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/store.py backend/tests/test_store.py
git commit -m "feat: watchlist and preferences store"
```

---

## Task 8: Authentication

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/app/routes/auth_routes.py`
- Modify: `backend/app/main.py` (full new contents shown)
- Test: `backend/tests/test_auth.py`

Auth model: a single shared secret. If `DASHBOARD_TOKEN` is unset, auth is disabled (open — for local dev). If set, protected routes require `Authorization: Bearer <DASHBOARD_TOKEN>`. `POST /api/auth/login` exchanges the password for the token.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_auth.py`:
```python
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import login, require_auth
from app.main import app

client = TestClient(app)


def test_login_returns_open_token_when_unconfigured(monkeypatch):
    monkeypatch.delenv("DASHBOARD_TOKEN", raising=False)
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    assert login("anything") == "open"


def test_login_rejects_wrong_password(monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret")
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    with pytest.raises(HTTPException) as exc:
        login("wrong")
    assert exc.value.status_code == 401


def test_login_returns_token_on_correct_password(monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret")
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    assert login("secret") == "tok-1"


def test_require_auth_passes_when_disabled(monkeypatch):
    monkeypatch.delenv("DASHBOARD_TOKEN", raising=False)
    require_auth(authorization=None)  # must not raise


def test_require_auth_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    with pytest.raises(HTTPException) as exc:
        require_auth(authorization=None)
    assert exc.value.status_code == 401


def test_require_auth_accepts_valid_token(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    require_auth(authorization="Bearer tok-1")  # must not raise


def test_login_route_and_status(monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret")
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    resp = client.post("/api/auth/login", json={"password": "secret"})
    assert resp.status_code == 200
    assert resp.json() == {"token": "tok-1"}
    status = client.get("/api/auth/status")
    assert status.json() == {"auth_enabled": True}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.auth'`.

- [ ] **Step 3: Write auth.py**

`backend/app/auth.py`:
```python
from fastapi import Header, HTTPException

from app.config import get_settings


def login(password: str) -> str:
    """Exchange a password for the shared token. When no password is
    configured, login always succeeds (local dev)."""
    settings = get_settings()
    if settings.dashboard_password and password != settings.dashboard_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    return settings.dashboard_token or "open"


def require_auth(authorization: str | None = Header(default=None)) -> None:
    """FastAPI dependency. No-op when DASHBOARD_TOKEN is unset; otherwise
    requires `Authorization: Bearer <DASHBOARD_TOKEN>`."""
    settings = get_settings()
    if not settings.dashboard_token:
        return
    if authorization != f"Bearer {settings.dashboard_token}":
        raise HTTPException(status_code=401, detail="Not authenticated")
```

- [ ] **Step 4: Write auth_routes.py**

`backend/app/routes/auth_routes.py`:
```python
from fastapi import APIRouter
from pydantic import BaseModel

from app.auth import login
from app.config import get_settings

router = APIRouter(prefix="/api/auth")


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def login_route(body: LoginRequest) -> dict:
    return {"token": login(body.password)}


@router.get("/status")
def status_route() -> dict:
    return {"auth_enabled": bool(get_settings().dashboard_token)}
```

- [ ] **Step 5: Update main.py to register the auth router**

`backend/app/main.py` (complete new contents):
```python
from fastapi import FastAPI

from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import RequestIDMiddleware
from app.routes.auth_routes import router as auth_router
from app.routes.health import router as health_router

configure_logging(get_settings().log_level)

app = FastAPI(title="News & Markets Dashboard API", version="0.1.0")
app.add_middleware(RequestIDMiddleware)
app.include_router(health_router)
app.include_router(auth_router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: PASS — all eight tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/auth.py backend/app/routes/auth_routes.py \
        backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: single-user token auth"
```

---

## Task 9: yfinance provider

**Files:**
- Create: `backend/app/providers/__init__.py` (empty)
- Create: `backend/app/providers/yfinance_provider.py`
- Test: `backend/tests/test_yfinance_provider.py`

- [ ] **Step 1: Create the empty package file**

Create empty file `backend/app/providers/__init__.py`.

- [ ] **Step 2: Write the failing test**

`backend/tests/test_yfinance_provider.py`:
```python
import pandas as pd

from app.providers import yfinance_provider


class FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    def history(self, period="1y", interval="1d", auto_adjust=True):
        idx = pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-04"])
        return pd.DataFrame(
            {
                "Open": [100.0, 102.0, 101.0],
                "High": [103.0, 104.0, 102.5],
                "Low": [99.0, 101.0, 100.0],
                "Close": [102.0, 101.0, 102.5],
                "Volume": [1000, 1200, 900],
            },
            index=idx,
        )

    @property
    def info(self):
        return {
            "longName": "Fake Corp", "sector": "Technology",
            "industry": "Software", "marketCap": 1_000_000.0,
            "trailingPE": 25.0, "fiftyTwoWeekHigh": 110.0,
            "fiftyTwoWeekLow": 80.0,
        }


class FakeYF:
    Ticker = FakeTicker


def test_get_history_returns_bars(monkeypatch):
    monkeypatch.setattr(yfinance_provider, "yf", FakeYF)
    bars = yfinance_provider.get_history("AAPL")
    assert len(bars) == 3
    assert bars[0].date == "2026-01-02"
    assert bars[-1].close == 102.5
    assert bars[-1].volume == 900


def test_get_quote_computes_change(monkeypatch):
    monkeypatch.setattr(yfinance_provider, "yf", FakeYF)
    q = yfinance_provider.get_quote("AAPL")
    assert q.symbol == "AAPL"
    assert q.price == 102.5
    assert q.change == round(102.5 - 101.0, 4)
    assert q.change_pct == round((1.5 / 101.0) * 100, 4)


def test_get_fundamentals_maps_info(monkeypatch):
    monkeypatch.setattr(yfinance_provider, "yf", FakeYF)
    f = yfinance_provider.get_fundamentals("AAPL")
    assert f.name == "Fake Corp"
    assert f.sector == "Technology"
    assert f.pe_ratio == 25.0


def test_get_history_returns_empty_on_error(monkeypatch):
    class BoomTicker:
        def __init__(self, symbol):
            raise RuntimeError("network down")

    class BoomYF:
        Ticker = BoomTicker

    monkeypatch.setattr(yfinance_provider, "yf", BoomYF)
    assert yfinance_provider.get_history("AAPL") == []
    assert yfinance_provider.get_quote("AAPL") is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_yfinance_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.providers.yfinance_provider'`.

- [ ] **Step 4: Write the implementation**

`backend/app/providers/yfinance_provider.py`:
```python
import logging

import yfinance as yf

from app.models import Bar, Fundamentals, Quote

logger = logging.getLogger(__name__)


def _ticker(symbol: str):
    """Single seam over yfinance — tests monkeypatch `yf`."""
    return yf.Ticker(symbol)


def get_history(symbol: str, period: str = "1y", interval: str = "1d") -> list[Bar]:
    """Return daily bars for `symbol`, or [] on any failure (graceful no-op)."""
    try:
        df = _ticker(symbol).history(period=period, interval=interval,
                                     auto_adjust=True)
    except Exception as e:
        logger.warning("get_history(%s) failed: %s", symbol, e)
        return []
    if df is None or df.empty:
        return []
    bars: list[Bar] = []
    for idx, row in df.iterrows():
        bars.append(Bar(
            date=idx.date().isoformat(),
            open=round(float(row["Open"]), 4),
            high=round(float(row["High"]), 4),
            low=round(float(row["Low"]), 4),
            close=round(float(row["Close"]), 4),
            volume=int(row["Volume"]),
        ))
    return bars


def get_quote(symbol: str) -> Quote | None:
    """Derive a quote from the last two daily bars. None on failure."""
    bars = get_history(symbol, period="5d", interval="1d")
    if not bars:
        return None
    last = bars[-1]
    prev_close = bars[-2].close if len(bars) >= 2 else last.open
    change = round(last.close - prev_close, 4)
    change_pct = round((change / prev_close) * 100, 4) if prev_close else 0.0
    return Quote(symbol=symbol, price=last.close, change=change,
                 change_pct=change_pct, volume=last.volume, as_of=last.date)


def get_fundamentals(symbol: str) -> Fundamentals | None:
    """Map yfinance `.info` into Fundamentals. None on failure."""
    try:
        info = _ticker(symbol).info
    except Exception as e:
        logger.warning("get_fundamentals(%s) failed: %s", symbol, e)
        return None
    if not info:
        return None
    return Fundamentals(
        symbol=symbol,
        name=info.get("longName") or info.get("shortName") or symbol,
        sector=info.get("sector"),
        industry=info.get("industry"),
        market_cap=info.get("marketCap"),
        pe_ratio=info.get("trailingPE"),
        price_to_book=info.get("priceToBook"),
        dividend_yield=info.get("dividendYield"),
        week52_high=info.get("fiftyTwoWeekHigh"),
        week52_low=info.get("fiftyTwoWeekLow"),
        beta=info.get("beta"),
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_yfinance_provider.py -v`
Expected: PASS — all four tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/providers/__init__.py \
        backend/app/providers/yfinance_provider.py \
        backend/tests/test_yfinance_provider.py
git commit -m "feat: yfinance provider adapter"
```

---

## Task 10: Analysis metrics

**Files:**
- Create: `backend/app/analysis/__init__.py` (empty)
- Create: `backend/app/analysis/metrics.py`
- Test: `backend/tests/test_metrics.py`

- [ ] **Step 1: Create the empty package file**

Create empty file `backend/app/analysis/__init__.py`.

- [ ] **Step 2: Write the failing test**

`backend/tests/test_metrics.py`:
```python
import pytest

from app.analysis import metrics


def test_simple_returns():
    assert metrics.simple_returns([100.0, 110.0, 99.0]) == pytest.approx([0.1, -0.1])


def test_simple_returns_short_input():
    assert metrics.simple_returns([100.0]) == []


def test_momentum():
    prices = [10.0, 11.0, 12.0, 15.0]
    assert metrics.momentum(prices, 3) == pytest.approx(0.5)


def test_momentum_insufficient_history():
    assert metrics.momentum([10.0, 11.0], 5) == 0.0


def test_annualized_volatility_zero_for_short_input():
    assert metrics.annualized_volatility([0.01]) == 0.0


def test_annualized_volatility_positive():
    assert metrics.annualized_volatility([0.01, -0.02, 0.015, -0.005]) > 0


def test_sma_pads_with_none():
    result = metrics.sma([1.0, 2.0, 3.0, 4.0], 3)
    assert result[:2] == [None, None]
    assert result[2] == pytest.approx(2.0)
    assert result[3] == pytest.approx(3.0)


def test_downsample_keeps_endpoints():
    values = [float(i) for i in range(100)]
    out = metrics.downsample(values, 10)
    assert len(out) == 10
    assert out[0] == 0.0
    assert out[-1] == 99.0


def test_downsample_passthrough_when_short():
    assert metrics.downsample([1.0, 2.0], 10) == [1.0, 2.0]


def test_breadth_counts():
    result = metrics.breadth([1.5, -0.5, 0.0, 2.0, -1.0])
    assert result["advancers"] == 2
    assert result["decliners"] == 2
    assert result["unchanged"] == 1
    assert result["advance_decline_ratio"] == pytest.approx(1.0)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.analysis.metrics'`.

- [ ] **Step 4: Write the implementation**

`backend/app/analysis/metrics.py`:
```python
import statistics
from math import sqrt


def simple_returns(prices: list[float]) -> list[float]:
    out: list[float] = []
    for i in range(1, len(prices)):
        prev = prices[i - 1]
        out.append((prices[i] - prev) / prev if prev else 0.0)
    return out


def momentum(prices: list[float], periods: int) -> float:
    """Total return over the last `periods` steps. 0.0 if history too short."""
    if len(prices) <= periods:
        return 0.0
    base = prices[-periods - 1]
    return (prices[-1] / base) - 1.0 if base else 0.0


def annualized_volatility(returns: list[float], periods_per_year: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    return statistics.stdev(returns) * sqrt(periods_per_year)


def sma(prices: list[float], window: int) -> list[float | None]:
    """Simple moving average aligned to `prices`; None until the window fills."""
    out: list[float | None] = []
    for i in range(len(prices)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(round(sum(prices[i + 1 - window: i + 1]) / window, 4))
    return out


def downsample(values: list[float], target: int) -> list[float]:
    """Evenly sample `values` down to `target` points, keeping both endpoints."""
    if target <= 1 or len(values) <= target:
        return list(values)
    step = (len(values) - 1) / (target - 1)
    return [values[round(i * step)] for i in range(target)]


def breadth(changes: list[float]) -> dict:
    advancers = sum(1 for c in changes if c > 0)
    decliners = sum(1 for c in changes if c < 0)
    unchanged = sum(1 for c in changes if c == 0)
    ratio = advancers / decliners if decliners else float(advancers)
    return {
        "advancers": advancers,
        "decliners": decliners,
        "unchanged": unchanged,
        "advance_decline_ratio": round(ratio, 4),
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_metrics.py -v`
Expected: PASS — all ten tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/analysis/__init__.py backend/app/analysis/metrics.py \
        backend/tests/test_metrics.py
git commit -m "feat: analysis metrics"
```

---

## Task 11: Finance service

**Files:**
- Create: `backend/app/services/__init__.py` (empty)
- Create: `backend/app/services/finance_service.py`
- Test: `backend/tests/test_finance_service.py`

- [ ] **Step 1: Create the empty package file**

Create empty file `backend/app/services/__init__.py`.

- [ ] **Step 2: Write the failing test**

`backend/tests/test_finance_service.py`:
```python
from app.models import Bar, Fundamentals, Quote
from app.providers import yfinance_provider
from app.services import finance_service


def _bars(closes: list[float]) -> list[Bar]:
    return [
        Bar(date=f"2026-01-{i + 1:02d}", open=c, high=c + 1, low=c - 1,
            close=c, volume=1000)
        for i, c in enumerate(closes)
    ]


def test_build_overview_assembles_watchlist_and_breadth(db, monkeypatch):
    monkeypatch.setenv("WATCHLIST_DEFAULT", "AAPL")
    monkeypatch.setattr(yfinance_provider, "get_history",
                        lambda *a, **k: _bars([100.0, 101.0, 102.0]))
    monkeypatch.setattr(yfinance_provider, "get_quote",
                        lambda sym: Quote(symbol=sym, price=10.0, change=0.5,
                                          change_pct=1.0, volume=1,
                                          as_of="2026-01-03"))
    overview = finance_service.build_overview()
    assert len(overview.watchlist) == 1
    assert overview.watchlist[0].symbol == "AAPL"
    assert overview.watchlist[0].sparkline  # non-empty
    assert overview.breadth.advancers > 0
    assert overview.updated_at


def test_build_instrument_returns_bars_and_technicals(db, monkeypatch):
    closes = [100.0 + i for i in range(60)]
    monkeypatch.setattr(yfinance_provider, "get_history",
                        lambda *a, **k: _bars(closes))
    monkeypatch.setattr(yfinance_provider, "get_fundamentals",
                        lambda sym: Fundamentals(symbol=sym, name="Test Co"))
    result = finance_service.build_instrument("aapl")
    assert result is not None
    assert result.symbol == "AAPL"
    assert len(result.bars) == 60
    assert len(result.technicals.sma_20) == 60
    assert result.profile.name == "Test Co"
    assert result.stats.momentum_1m != 0.0


def test_build_instrument_none_when_no_data(db, monkeypatch):
    monkeypatch.setattr(yfinance_provider, "get_history", lambda *a, **k: [])
    assert finance_service.build_instrument("ZZZZ") is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_finance_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.finance_service'`.

- [ ] **Step 4: Write the implementation**

`backend/app/services/finance_service.py`:
```python
from datetime import datetime, timezone

from app.analysis import metrics
from app.config import get_settings
from app.database import save_ohlcv
from app.models import (Breadth, Fundamentals, InstrumentResponse,
                        InstrumentStats, OverviewResponse, SectorChange,
                        Technicals, WatchlistQuote)
from app.providers import yfinance_provider as provider
from app.store import get_watchlist

INDICES = [("^GSPC", "S&P 500"), ("^DJI", "Dow Jones"), ("^IXIC", "Nasdaq"),
           ("^RUT", "Russell 2000"), ("^VIX", "VIX")]

SECTORS = [("XLK", "Technology"), ("XLF", "Financials"), ("XLE", "Energy"),
           ("XLV", "Health Care"), ("XLY", "Consumer Discretionary"),
           ("XLP", "Consumer Staples"), ("XLI", "Industrials"),
           ("XLB", "Materials"), ("XLU", "Utilities"),
           ("XLRE", "Real Estate"), ("XLC", "Communication Services")]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_overview() -> OverviewResponse:
    """Assemble the Finance overview: watchlist, indices, sectors, breadth."""
    settings = get_settings()
    symbols = get_watchlist() or settings.watchlist_default

    watchlist_quotes: list[WatchlistQuote] = []
    for sym in symbols:
        bars = provider.get_history(sym, period="1mo", interval="1d")
        if not bars:
            continue
        last = bars[-1]
        prev_close = bars[-2].close if len(bars) >= 2 else last.open
        change = round(last.close - prev_close, 4)
        change_pct = round((change / prev_close) * 100, 4) if prev_close else 0.0
        watchlist_quotes.append(WatchlistQuote(
            symbol=sym, price=last.close, change=change, change_pct=change_pct,
            volume=last.volume, as_of=last.date,
            sparkline=metrics.downsample([b.close for b in bars], 24)))

    indices = [q for q in (provider.get_quote(sym) for sym, _ in INDICES) if q]

    sectors: list[SectorChange] = []
    for sym, name in SECTORS:
        quote = provider.get_quote(sym)
        if quote:
            sectors.append(SectorChange(symbol=sym, name=name,
                                        change_pct=quote.change_pct))

    all_changes = ([q.change_pct for q in watchlist_quotes]
                   + [q.change_pct for q in indices]
                   + [s.change_pct for s in sectors])
    breadth = Breadth(**metrics.breadth(all_changes))

    return OverviewResponse(watchlist=watchlist_quotes, indices=indices,
                            sectors=sectors, breadth=breadth, updated_at=_now())


def build_instrument(symbol: str) -> InstrumentResponse | None:
    """Assemble the drill-down for one instrument: bars, technicals, profile."""
    symbol = symbol.strip().upper()
    bars = provider.get_history(symbol, period="2y", interval="1d")
    if not bars:
        return None
    save_ohlcv(symbol, bars)

    closes = [b.close for b in bars]
    profile = (provider.get_fundamentals(symbol)
               or Fundamentals(symbol=symbol, name=symbol))
    technicals = Technicals(
        sma_20=metrics.sma(closes, 20),
        sma_50=metrics.sma(closes, 50),
        sma_200=metrics.sma(closes, 200))
    recent = bars[-252:]
    stats = InstrumentStats(
        momentum_1m=round(metrics.momentum(closes, 21) * 100, 4),
        momentum_3m=round(metrics.momentum(closes, 63) * 100, 4),
        momentum_6m=round(metrics.momentum(closes, 126) * 100, 4),
        volatility_30d=round(
            metrics.annualized_volatility(
                metrics.simple_returns(closes[-31:])) * 100, 4),
        week52_high=max(b.high for b in recent),
        week52_low=min(b.low for b in recent))

    return InstrumentResponse(symbol=symbol, profile=profile, bars=bars,
                              technicals=technicals, stats=stats,
                              updated_at=_now())
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_finance_service.py -v`
Expected: PASS — all three tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/__init__.py \
        backend/app/services/finance_service.py \
        backend/tests/test_finance_service.py
git commit -m "feat: finance service (overview + instrument)"
```

---

## Task 12: Watchlist API routes

**Files:**
- Create: `backend/app/routes/watchlist.py`
- Modify: `backend/app/main.py` (full new contents shown)
- Test: `backend/tests/test_watchlist_routes.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_watchlist_routes.py`:
```python
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

    resp = client.delete("/api/watchlist/AAPL")
    assert resp.json() == {"symbols": ["MSFT"]}


def test_post_rejects_blank_symbol(db):
    resp = client.post("/api/watchlist", json={"symbol": "   "})
    assert resp.status_code == 400


def test_watchlist_requires_auth_when_enabled(db, monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    assert client.get("/api/watchlist").status_code == 401
    ok = client.get("/api/watchlist", headers={"Authorization": "Bearer tok-1"})
    assert ok.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_watchlist_routes.py -v`
Expected: FAIL — 404 on `/api/watchlist` (router not registered).

- [ ] **Step 3: Write watchlist.py**

`backend/app/routes/watchlist.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_auth
from app.store import add_to_watchlist, get_watchlist, remove_from_watchlist

router = APIRouter(prefix="/api/watchlist", dependencies=[Depends(require_auth)])


class SymbolBody(BaseModel):
    symbol: str


@router.get("")
def list_watchlist() -> dict:
    return {"symbols": get_watchlist()}


@router.post("")
def add_symbol(body: SymbolBody) -> dict:
    symbol = body.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="symbol is required")
    add_to_watchlist(symbol)
    return {"symbols": get_watchlist()}


@router.delete("/{symbol}")
def delete_symbol(symbol: str) -> dict:
    remove_from_watchlist(symbol)
    return {"symbols": get_watchlist()}
```

- [ ] **Step 4: Update main.py to register the watchlist router**

`backend/app/main.py` (complete new contents):
```python
from fastapi import FastAPI

from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import RequestIDMiddleware
from app.routes.auth_routes import router as auth_router
from app.routes.health import router as health_router
from app.routes.watchlist import router as watchlist_router

configure_logging(get_settings().log_level)

app = FastAPI(title="News & Markets Dashboard API", version="0.1.0")
app.add_middleware(RequestIDMiddleware)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(watchlist_router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_watchlist_routes.py -v`
Expected: PASS — all three tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/watchlist.py backend/app/main.py \
        backend/tests/test_watchlist_routes.py
git commit -m "feat: watchlist API routes"
```

---

## Task 13: Finance API routes

**Files:**
- Create: `backend/app/routes/finance.py`
- Modify: `backend/app/main.py` (full new contents shown)
- Test: `backend/tests/test_finance_routes.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_finance_routes.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_finance_routes.py -v`
Expected: FAIL — 404 on `/api/finance/overview` (router not registered).

- [ ] **Step 3: Write finance.py**

`backend/app/routes/finance.py`:
```python
from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_auth
from app.cache import cache
from app.services import finance_service

router = APIRouter(prefix="/api/finance", dependencies=[Depends(require_auth)])


@router.get("/overview")
def overview():
    """Cached so the frontend never blocks on yfinance."""
    return cache.get_or_compute("finance:overview", finance_service.build_overview)


@router.get("/instrument/{symbol}")
def instrument(symbol: str):
    key = f"finance:instrument:{symbol.strip().upper()}"
    result = cache.get_or_compute(
        key, lambda: finance_service.build_instrument(symbol))
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return result
```

- [ ] **Step 4: Update main.py to register the finance router**

`backend/app/main.py` (complete new contents):
```python
from fastapi import FastAPI

from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import RequestIDMiddleware
from app.routes.auth_routes import router as auth_router
from app.routes.finance import router as finance_router
from app.routes.health import router as health_router
from app.routes.watchlist import router as watchlist_router

configure_logging(get_settings().log_level)

app = FastAPI(title="News & Markets Dashboard API", version="0.1.0")
app.add_middleware(RequestIDMiddleware)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(watchlist_router)
app.include_router(finance_router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_finance_routes.py -v`
Expected: PASS — all three tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/finance.py backend/app/main.py \
        backend/tests/test_finance_routes.py
git commit -m "feat: finance API routes (overview + instrument)"
```

---

## Task 14: Scheduler

**Files:**
- Create: `backend/app/scheduler.py`
- Test: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_scheduler.py`:
```python
from app import scheduler
from app.cache import cache
from app.models import Bar, Quote
from app.providers import yfinance_provider


def test_start_scheduler_returns_none_when_disabled(monkeypatch):
    monkeypatch.delenv("SCHEDULER_ENABLED", raising=False)
    assert scheduler.start_scheduler() is None


def test_warm_overview_populates_cache(db, monkeypatch):
    monkeypatch.setenv("WATCHLIST_DEFAULT", "AAPL")
    monkeypatch.setattr(
        yfinance_provider, "get_history",
        lambda *a, **k: [Bar(date="2026-01-02", open=1, high=2, low=1,
                              close=1.5, volume=10)])
    monkeypatch.setattr(
        yfinance_provider, "get_quote",
        lambda sym: Quote(symbol=sym, price=1.0, change=0.0, change_pct=0.0,
                          volume=1, as_of="2026-01-02"))
    assert cache.get("finance:overview") is None
    scheduler.warm_overview()
    assert cache.get("finance:overview") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_scheduler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.scheduler'`.

- [ ] **Step 3: Write the implementation**

`backend/app/scheduler.py`:
```python
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.cache import cache
from app.config import get_settings
from app.services import finance_service

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def warm_overview() -> None:
    """Recompute the Finance overview and store it in the cache."""
    try:
        cache.set("finance:overview", finance_service.build_overview())
        logger.info("warmed finance:overview")
    except Exception as e:
        logger.warning("warm_overview failed: %s", e)


def start_scheduler() -> BackgroundScheduler | None:
    """Start background jobs when SCHEDULER_ENABLED=true; otherwise no-op."""
    global _scheduler
    if not get_settings().scheduler_enabled:
        logger.info("scheduler disabled (set SCHEDULER_ENABLED=true to enable)")
        return None
    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(warm_overview, "interval", minutes=10, id="warm_overview",
                  max_instances=1, coalesce=True)
    sched.start()
    _scheduler = sched
    logger.info("scheduler started")
    return sched


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_scheduler.py -v`
Expected: PASS — both tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat: APScheduler with overview warming job"
```

---

## Task 15: Final wire-up — lifespan, CORS, docs

**Files:**
- Modify: `backend/app/main.py` (full new contents shown)
- Create: `backend/.env.example`
- Create: `backend/README.md`
- Test: `backend/tests/test_health.py` (extend with a startup smoke test)

This task is configuration wiring, not TDD: implement first, then add a smoke
test that exercises the lifespan, then confirm the whole suite is green.

- [ ] **Step 1: Update main.py with the lifespan and CORS**

`backend/app/main.py` (complete new contents):
```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.logging_config import configure_logging
from app.middleware import RequestIDMiddleware
from app.routes.auth_routes import router as auth_router
from app.routes.finance import router as finance_router
from app.routes.health import router as health_router
from app.routes.watchlist import router as watchlist_router
from app.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="News & Markets Dashboard API", version="0.1.0",
              lifespan=lifespan)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials="*" not in _settings.cors_origins,
)
app.add_middleware(RequestIDMiddleware)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(watchlist_router)
app.include_router(finance_router)
```

- [ ] **Step 2: Add a startup smoke test**

Append to `backend/tests/test_health.py`:
```python


def test_app_starts_with_lifespan(db):
    """Entering the TestClient context runs the lifespan (configure_logging,
    init_db, start_scheduler) and exiting runs shutdown without error."""
    with TestClient(app) as live_client:
        assert live_client.get("/health").status_code == 200
```

- [ ] **Step 3: Run the full test suite**

Run: `cd backend && python -m pytest -v`
Expected: PASS — every test in every file passes, including `test_app_starts_with_lifespan`.

- [ ] **Step 4: Write .env.example**

`backend/.env.example`:
```
# --- Auth (single user) ---
# Leave both blank for local dev (auth disabled).
DASHBOARD_PASSWORD=
DASHBOARD_TOKEN=

# --- Database ---
# Blank -> local SQLite at data/dashboard.db.
# Production: a Supabase Postgres pooler URL (postgresql://...).
DATABASE_URL=

# --- Behaviour ---
SCHEDULER_ENABLED=false
CACHE_TTL_SECONDS=300
LOG_LEVEL=INFO
CORS_ORIGINS=*
WATCHLIST_DEFAULT=AAPL,MSFT,NVDA,GOOGL,AMZN
```

- [ ] **Step 5: Write README.md**

`backend/README.md`:
```markdown
# News & Markets Dashboard — Backend

FastAPI backend for the Finance domain (Phase 1a).

## Quickstart

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API.

## Tests

```bash
cd backend && python -m pytest -v
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness probe |
| POST | `/api/auth/login` | Exchange password for token |
| GET | `/api/auth/status` | Whether auth is enabled |
| GET | `/api/watchlist` | List watchlist symbols |
| POST | `/api/watchlist` | Add a symbol `{"symbol": "AAPL"}` |
| DELETE | `/api/watchlist/{symbol}` | Remove a symbol |
| GET | `/api/finance/overview` | Watchlist + indices + sectors + breadth |
| GET | `/api/finance/instrument/{symbol}` | OHLCV + technicals + fundamentals |

## Configuration

See `.env.example`. Auth is disabled unless `DASHBOARD_TOKEN` is set. The
database defaults to local SQLite; set `DATABASE_URL` to Postgres for production.
```

- [ ] **Step 6: Run the full suite once more and commit**

Run: `cd backend && python -m pytest -v`
Expected: PASS — all tests green.

```bash
git add backend/app/main.py backend/.env.example backend/README.md \
        backend/tests/test_health.py
git commit -m "feat: app lifespan, CORS, and backend docs"
```

---

## Self-Review Notes

This plan was checked against the Plan 1a scope (the backend slice of Phase 1 from
`docs/superpowers/specs/2026-05-20-news-dashboard-design.md`):

- **Backend scaffold** — Task 1. **Config** — Task 2. **Logging/middleware** — Task 3.
- **Database schema** — Task 6 (`ohlcv`, `watchlist`, `preferences`). **Auth gate** —
  Task 8 (single-user token, matches spec §4). **Scheduler** — Task 14
  (`SCHEDULER_ENABLED`-gated, matches spec).
- **Finance domain end-to-end (backend)** — provider (Task 9), metrics (Task 10),
  service (Task 11), watchlist routes (Task 12), finance routes (Task 13).
- **"Frontend never waits"** principle — the `/api/finance/*` routes serve only
  cached/computed data via `TTLCache.get_or_compute`; the scheduler warms the cache.
- **Reuse from Models** — provider-adapter pattern, JSON-logging + request-id
  middleware, `SCHEDULER_ENABLED` gating, quant formulas (momentum/volatility/SMA).
- **Type consistency** — model names (`Bar`, `Quote`, `WatchlistQuote`,
  `Fundamentals`, `OverviewResponse`, `InstrumentResponse`, etc.) and function names
  (`get_history`/`get_quote`/`get_fundamentals`, `build_overview`/`build_instrument`,
  `save_ohlcv`/`load_ohlcv`, `get_watchlist`/`add_to_watchlist`) are used identically
  across every task that references them.
- **Deferred (not gaps):** the frontend is Plan 1b; deploy configs are Plan 1c; the
  instrument page's correlations/company-news/filings are later phases, as recorded
  in the spec. The chart design system and motion system live entirely in the
  frontend and are therefore covered by Plan 1b, not here.
```
