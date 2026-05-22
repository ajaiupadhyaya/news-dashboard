# Phase 2 — Economics Domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Economics domain end-to-end — a FRED-backed Economics overview panel on the Home dashboard and an indicator drill-down page — mirroring the already-shipped Finance domain.

**Architecture:** Backend: a FRED HTTP provider → pure analysis functions → an economics service → cached, auth-gated API routes, refreshed by the scheduler. Frontend: a new bespoke `LineChart`, an `EconomicsPanel` of indicator tiles + a release calendar, and an indicator drill-down route. Everything mirrors the Finance domain's structure and reuses the existing chart/motion/design systems.

**Tech Stack:** FastAPI, httpx, pydantic, SQLAlchemy, pytest (backend); Vite + React 19 + TypeScript, D3, Motion, TanStack Query, React Router 7, Vitest, Playwright (frontend).

**Spec:** `docs/superpowers/specs/2026-05-21-phase-2-economics-design.md`

**Conventions (from Phase 1 — follow exactly):**
- Backend tests run with `cd backend && .venv/bin/python -m pytest`. The `db` fixture (in `backend/tests/conftest.py`) gives a fresh temp SQLite DB; `monkeypatch` is pytest's builtin; the cache is auto-cleared between tests.
- Frontend tests run with `cd frontend && npm run test`. Test helpers live in `src/test/utils.tsx`.
- Commit messages: `feat(backend|frontend): …`, `test(…): …`. End every commit body with:
  `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
- The frontend feeds the API through a TTL cache so it never blocks on FRED. Providers return `[]`/`None` on any failure (graceful) — never raise.

---

## File Structure

**Backend (`backend/`)**
| File | Responsibility |
|---|---|
| `app/config.py` (modify) | Add `fred_api_key` setting |
| `requirements.txt` (modify) | Add `httpx` as a runtime dependency |
| `app/models.py` (modify) | Economics pydantic models |
| `app/database.py` (modify) | `econ_series` cache table + load/save helpers |
| `app/providers/fred_provider.py` (create) | FRED HTTP adapter |
| `app/analysis/econ_metrics.py` (create) | Pure analysis functions |
| `app/services/economics_service.py` (create) | Assembles overview + indicator detail |
| `app/routes/economics.py` (create) | `/api/economics/*` routes |
| `app/main.py` (modify) | Register the economics router |
| `app/scheduler.py` (modify) | `warm_economics` background job |

**Frontend (`frontend/src/`)**
| File | Responsibility |
|---|---|
| `lib/types.ts` (modify) | Economics TypeScript types |
| `lib/api.ts` (modify) | Economics endpoint functions |
| `lib/econFormat.ts` (create) | Unit-aware indicator value formatting |
| `charts/LineChart.tsx` (create) | Bespoke time-series area/line chart |
| `economics/hooks.ts` (create) | TanStack Query hooks |
| `economics/IndicatorTile.tsx` (create) | One overview tile |
| `economics/ReleaseCalendar.tsx` (create) | Release calendar list |
| `economics/EconomicsPanel.tsx` (create) | The overview panel |
| `economics/RecessionSignals.tsx` (create) | Drill-down recession-signal composite |
| `economics/IndicatorStats.tsx` (create) | Drill-down summary stat tiles |
| `routes/IndicatorRoute.tsx` (create) | The drill-down page |
| `routes/Home.tsx` (modify) | Swap the Economics placeholder for `EconomicsPanel` |
| `router.tsx` (modify) | Add the `/economics/:seriesId` route |
| `e2e/economics-drilldown.spec.ts` (create) | Playwright overview→drill-down flow |

---

## Task 1: FRED config + httpx dependency

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_config.py`:

```python
def test_fred_api_key_read_from_env(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "test-key-123")
    assert get_settings().fred_api_key == "test-key-123"


def test_fred_api_key_none_when_unset(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    assert get_settings().fred_api_key is None
```

If `test_config.py` does not already `from app.config import get_settings`, add that import at the top.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_config.py -v`
Expected: the two new tests FAIL — `Settings` has no `fred_api_key` attribute.

- [ ] **Step 3: Add the setting**

In `backend/app/config.py`, add `fred_api_key` to the `Settings` dataclass (after `dashboard_password`):

```python
    fred_api_key: str | None
```

And in `get_settings()`, add to the `Settings(...)` constructor call (after the `dashboard_password=` line):

```python
        fred_api_key=os.getenv("FRED_API_KEY") or None,
```

- [ ] **Step 4: Add httpx as a runtime dependency**

In `backend/requirements.txt`, add a line (FRED's provider needs httpx at runtime, not just in tests):

```
httpx>=0.27
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_config.py -v`
Expected: all config tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/requirements.txt backend/tests/test_config.py
git commit -m "$(printf 'feat(backend): add FRED_API_KEY setting and httpx dependency\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 2: Economics models

**Files:**
- Modify: `backend/app/models.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_models.py` (add `from app.models import ...` names to the existing import, or add a new import line):

```python
def test_economics_overview_model_roundtrips():
    from app.models import (EconomicsOverview, IndicatorPoint,
                            IndicatorSummary, ReleaseEvent)
    ov = EconomicsOverview(
        indicators=[IndicatorSummary(
            series_id="UNRATE", name="Unemployment Rate", unit="%",
            latest=4.1, latest_date="2026-04-01", change=-0.1,
            trend="in", sparkline=[4.3, 4.2, 4.1])],
        calendar=[ReleaseEvent(date="2026-05-13",
                               release_name="Consumer Price Index")],
        updated_at="2026-05-21T00:00:00+00:00")
    assert ov.indicators[0].series_id == "UNRATE"
    assert ov.calendar[0].release_name == "Consumer Price Index"
    pt = IndicatorPoint(date="2026-04-01", value=4.1)
    assert pt.value == 4.1


def test_indicator_detail_model():
    from app.models import (IndicatorDetail, IndicatorPoint, RecessionSignal)
    detail = IndicatorDetail(
        series_id="UNRATE", name="Unemployment Rate", unit="%",
        series=[IndicatorPoint(date="2026-03-01", value=4.2),
                IndicatorPoint(date="2026-04-01", value=4.1)],
        latest=4.1, change=-0.1, yoy=0.3, range_low=3.4, range_high=4.3,
        momentum=-2.4,
        recession_signals=[RecessionSignal(
            name="Yield curve (10y-2y)", value=-0.15, status="alert",
            detail="Inverted — historically a recession precursor.")],
        updated_at="2026-05-21T00:00:00+00:00")
    assert detail.yoy == 0.3
    assert detail.recession_signals[0].status == "alert"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_models.py -v`
Expected: the two new tests FAIL — the model classes do not exist.

- [ ] **Step 3: Add the models**

Append to `backend/app/models.py`:

```python
class IndicatorPoint(BaseModel):
    date: str          # ISO date, e.g. "2026-04-01"
    value: float


class ReleaseEvent(BaseModel):
    date: str          # ISO date of the release
    release_name: str


class IndicatorSummary(BaseModel):
    series_id: str
    name: str
    unit: str          # display unit: "%", "K", "index", "$"
    latest: float      # headline value
    latest_date: str
    change: float      # change vs. the prior observation, headline units
    trend: str         # trend-relative marker: "below" | "in" | "above"
    sparkline: list[float]


class EconomicsOverview(BaseModel):
    indicators: list[IndicatorSummary]
    calendar: list[ReleaseEvent]
    updated_at: str


class RecessionSignal(BaseModel):
    name: str
    value: float
    status: str        # "normal" | "warning" | "alert"
    detail: str        # plain-language one-liner


class IndicatorDetail(BaseModel):
    series_id: str
    name: str
    unit: str
    series: list[IndicatorPoint]
    latest: float
    change: float
    yoy: float | None = None       # year-over-year %, None when N/A
    range_low: float
    range_high: float
    momentum: float                # momentum/trend composite score
    recession_signals: list[RecessionSignal]
    updated_at: str
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_models.py -v`
Expected: all model tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_models.py
git commit -m "$(printf 'feat(backend): add Economics domain models\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 3: `econ_series` cache table

**Files:**
- Modify: `backend/app/database.py`
- Test: `backend/tests/test_database.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_database.py`:

```python
def test_econ_series_round_trips(db):
    from app.database import load_econ_series, save_econ_series
    from app.models import IndicatorPoint
    points = [IndicatorPoint(date="2026-01-01", value=2.9),
              IndicatorPoint(date="2026-02-01", value=3.1)]
    save_econ_series("CPIAUCSL", points)
    loaded = load_econ_series("CPIAUCSL")
    assert [p.date for p in loaded] == ["2026-01-01", "2026-02-01"]
    assert loaded[1].value == 3.1


def test_save_econ_series_replaces_prior(db):
    from app.database import load_econ_series, save_econ_series
    from app.models import IndicatorPoint
    save_econ_series("UNRATE", [IndicatorPoint(date="2026-01-01", value=4.0)])
    save_econ_series("UNRATE", [IndicatorPoint(date="2026-02-01", value=4.1)])
    loaded = load_econ_series("UNRATE")
    assert len(loaded) == 1 and loaded[0].date == "2026-02-01"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_database.py -v`
Expected: the two new tests FAIL — `save_econ_series`/`load_econ_series` do not exist.

- [ ] **Step 3: Add the table and helpers**

In `backend/app/database.py`, add `IndicatorPoint` to the models import:

```python
from app.models import Bar, IndicatorPoint
```

Add the table definition after the `preferences` table:

```python
econ_series = Table(
    "econ_series", metadata,
    Column("series_id", String(32), primary_key=True),
    Column("date", String(10), primary_key=True),
    Column("value", Float),
)
```

Add these functions at the end of the file:

```python
def save_econ_series(series_id: str, points: list[IndicatorPoint]) -> None:
    """Replace all stored points for `series_id` with `points`."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(delete(econ_series).where(
            econ_series.c.series_id == series_id))
        if points:
            conn.execute(insert(econ_series), [
                {"series_id": series_id, "date": p.date, "value": p.value}
                for p in points
            ])


def load_econ_series(series_id: str) -> list[IndicatorPoint]:
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            select(econ_series).where(econ_series.c.series_id == series_id)
            .order_by(econ_series.c.date)
        ).mappings().all()
    return [IndicatorPoint(date=r["date"], value=r["value"]) for r in rows]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_database.py -v`
Expected: all database tests PASS (`init_db` creates the new table automatically via `metadata.create_all`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/database.py backend/tests/test_database.py
git commit -m "$(printf 'feat(backend): add econ_series cache table\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 4: FRED provider

**Files:**
- Create: `backend/app/providers/fred_provider.py`
- Test: `backend/tests/test_fred_provider.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_fred_provider.py`:

```python
from app.providers import fred_provider


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _fake_httpx(payload):
    class FakeHttpx:
        @staticmethod
        def get(url, params=None, timeout=None):
            return FakeResponse(payload)
    return FakeHttpx


def test_get_series_parses_observations(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    monkeypatch.setattr(fred_provider, "httpx", _fake_httpx({
        "observations": [
            {"date": "2026-01-01", "value": "2.9"},
            {"date": "2026-02-01", "value": "."},      # missing — skipped
            {"date": "2026-03-01", "value": "3.1"},
        ]}))
    points = fred_provider.get_series("CPIAUCSL")
    assert [p.date for p in points] == ["2026-01-01", "2026-03-01"]
    assert points[-1].value == 3.1


def test_get_series_empty_without_api_key(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    assert fred_provider.get_series("CPIAUCSL") == []


def test_get_series_empty_on_error(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")

    class BoomHttpx:
        @staticmethod
        def get(url, params=None, timeout=None):
            raise RuntimeError("network down")

    monkeypatch.setattr(fred_provider, "httpx", BoomHttpx)
    assert fred_provider.get_series("CPIAUCSL") == []


def test_get_release_calendar_parses_dates(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    monkeypatch.setattr(fred_provider, "httpx", _fake_httpx({
        "release_dates": [
            {"release_id": 10, "release_name": "Consumer Price Index",
             "date": "2026-05-13"},
            {"release_id": 50, "release_name": "Employment Situation",
             "date": "2026-05-02"},
        ]}))
    cal = fred_provider.get_release_calendar()
    assert cal[0].release_name == "Consumer Price Index"
    assert cal[1].date == "2026-05-02"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_fred_provider.py -v`
Expected: FAIL — `fred_provider` module does not exist.

- [ ] **Step 3: Write the provider**

Create `backend/app/providers/fred_provider.py`:

```python
import logging

import httpx

from app.config import get_settings
from app.models import IndicatorPoint, ReleaseEvent

logger = logging.getLogger(__name__)

_BASE = "https://api.stlouisfed.org/fred"


def _get(path: str, params: dict) -> dict | None:
    """Single seam over the FRED HTTP API — tests monkeypatch `httpx`.

    Returns None on any failure or when no API key is configured.
    """
    api_key = get_settings().fred_api_key
    if not api_key:
        logger.warning("FRED_API_KEY not set — FRED requests return no data")
        return None
    query = {"api_key": api_key, "file_type": "json", **params}
    try:
        resp = httpx.get(f"{_BASE}/{path}", params=query, timeout=15.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("FRED %s failed: %s", path, e)
        return None


def get_series(series_id: str, units: str = "lin") -> list[IndicatorPoint]:
    """Observations for a FRED series, oldest-first. [] on any failure.

    `units` is a FRED transform code applied server-side: "lin" (raw),
    "pc1" (percent change from a year ago), "chg" (change from the prior
    observation). FRED encodes missing observations as ".", skipped here.
    """
    data = _get("series/observations",
                {"series_id": series_id, "sort_order": "asc", "units": units})
    if not data or "observations" not in data:
        return []
    points: list[IndicatorPoint] = []
    for obs in data["observations"]:
        raw = obs.get("value")
        if raw in (".", "", None):
            continue
        try:
            points.append(IndicatorPoint(date=obs["date"], value=float(raw)))
        except (ValueError, KeyError):
            continue
    return points


def get_release_calendar(limit: int = 60) -> list[ReleaseEvent]:
    """Recent + upcoming economic release dates. [] on any failure."""
    data = _get("releases/dates",
                {"sort_order": "desc", "limit": limit,
                 "include_release_dates_with_no_data": "true"})
    if not data or "release_dates" not in data:
        return []
    events: list[ReleaseEvent] = []
    for rd in data["release_dates"]:
        try:
            events.append(ReleaseEvent(date=rd["date"],
                                       release_name=rd["release_name"]))
        except KeyError:
            continue
    return events
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_fred_provider.py -v`
Expected: all four tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/fred_provider.py backend/tests/test_fred_provider.py
git commit -m "$(printf 'feat(backend): add FRED API provider\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 5: Economics analysis metrics

**Files:**
- Create: `backend/app/analysis/econ_metrics.py`
- Test: `backend/tests/test_econ_metrics.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_econ_metrics.py`:

```python
from app.analysis import econ_metrics as em
from app.models import IndicatorPoint


def _points(pairs):
    return [IndicatorPoint(date=d, value=v) for d, v in pairs]


def test_period_change_is_latest_minus_prior():
    assert em.period_change([4.3, 4.2, 4.1]) == -0.1
    assert em.period_change([4.1]) == 0.0


def test_pct_change():
    assert em.pct_change([100.0, 110.0]) == 10.0
    assert em.pct_change([100.0]) is None


def test_trend_marker_buckets_position_in_range():
    # latest near the bottom of the trailing range -> "below"
    assert em.trend_marker([10, 9, 8, 7, 6, 5, 4]) == "below"
    # latest near the top -> "above"
    assert em.trend_marker([4, 5, 6, 7, 8, 9, 10]) == "above"
    # latest mid-range -> "in"
    assert em.trend_marker([4, 10, 5, 9, 6, 8, 7]) == "in"
    # too little history -> "in"
    assert em.trend_marker([5.0]) == "in"


def test_yoy_change_uses_observation_a_year_back():
    pts = _points([(f"2025-{m:02d}-01", 100.0) for m in range(1, 13)]
                  + [("2026-01-01", 106.0)])
    # 2026-01-01 vs 2025-01-01 -> +6%
    assert em.yoy_change(pts) == 6.0
    assert em.yoy_change(_points([("2026-01-01", 1.0)])) is None


def test_momentum_score_recent_direction():
    rising = [float(i) for i in range(20)]
    assert em.momentum_score(rising) > 0
    falling = [float(20 - i) for i in range(20)]
    assert em.momentum_score(falling) < 0


def test_recession_status_yield_curve():
    assert em.recession_status("yield_curve", -0.2)[0] == "alert"
    assert em.recession_status("yield_curve", 0.3)[0] == "warning"
    assert em.recession_status("yield_curve", 1.5)[0] == "normal"


def test_recession_status_sahm():
    assert em.recession_status("sahm", 0.6)[0] == "alert"
    assert em.recession_status("sahm", 0.35)[0] == "warning"
    assert em.recession_status("sahm", 0.1)[0] == "normal"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_econ_metrics.py -v`
Expected: FAIL — `econ_metrics` module does not exist.

- [ ] **Step 3: Write the metrics**

Create `backend/app/analysis/econ_metrics.py`:

```python
"""Pure analysis functions for the Economics domain. No I/O."""
from datetime import date

from app.models import IndicatorPoint


def period_change(values: list[float]) -> float:
    """Latest value minus the prior value. 0.0 if fewer than 2 values."""
    if len(values) < 2:
        return 0.0
    return round(values[-1] - values[-2], 4)


def pct_change(values: list[float]) -> float | None:
    """Percent change from the prior value to the latest. None if too short."""
    if len(values) < 2:
        return None
    base = values[-2]
    return round((values[-1] - base) / base * 100, 4) if base else None


def trend_marker(values: list[float], window: int = 24) -> str:
    """Where the latest value sits within its trailing `window` range.

    Returns "below" / "in" / "above" — bottom third / middle / top third.
    "in" when history is too short or the window is flat.
    """
    if len(values) < 3:
        return "in"
    recent = values[-window:]
    lo, hi = min(recent), max(recent)
    if hi == lo:
        return "in"
    pos = (values[-1] - lo) / (hi - lo)
    if pos < 1 / 3:
        return "below"
    if pos > 2 / 3:
        return "above"
    return "in"


def yoy_change(points: list[IndicatorPoint]) -> float | None:
    """Year-over-year percent change using the observation closest to 365
    days before the latest. None when there is no ~1-year-old observation."""
    if len(points) < 2:
        return None
    latest = points[-1]
    try:
        latest_d = date.fromisoformat(latest.date)
    except ValueError:
        return None
    target_days = 365
    best = None
    best_gap = None
    for p in points[:-1]:
        try:
            gap = abs((latest_d - date.fromisoformat(p.date)).days - target_days)
        except ValueError:
            continue
        if best_gap is None or gap < best_gap:
            best, best_gap = p, gap
    # Require the match to be within ~45 days of a full year.
    if best is None or best_gap is None or best_gap > 45 or not best.value:
        return None
    return round((latest.value - best.value) / best.value * 100, 4)


def momentum_score(values: list[float], window: int = 6) -> float:
    """Recent momentum: percent change over the trailing `window` steps.
    0.0 if history is too short."""
    if len(values) <= window:
        return 0.0
    base = values[-window - 1]
    return round((values[-1] - base) / base * 100, 4) if base else 0.0


def recession_status(signal: str, value: float) -> tuple[str, str]:
    """Status + plain-language detail for a recession signal.

    `signal` is "yield_curve" (10y-2y spread) or "sahm" (Sahm-rule value).
    Returns (status, detail) where status is normal/warning/alert.
    """
    if signal == "yield_curve":
        if value < 0:
            return ("alert",
                    "Inverted — historically a recession precursor.")
        if value < 0.5:
            return ("warning", "Flattening — narrowing growth cushion.")
        return ("normal", "Positively sloped — no curve stress.")
    if signal == "sahm":
        if value >= 0.5:
            return ("alert", "Sahm rule triggered — recession signal.")
        if value >= 0.3:
            return ("warning", "Approaching the Sahm-rule threshold.")
        return ("normal", "Well below the Sahm-rule threshold.")
    return ("normal", "")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_econ_metrics.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/analysis/econ_metrics.py backend/tests/test_econ_metrics.py
git commit -m "$(printf 'feat(backend): add Economics analysis metrics\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 6: Economics service

**Files:**
- Create: `backend/app/services/economics_service.py`
- Test: `backend/tests/test_economics_service.py`

The service defines the indicator set and assembles the overview + per-indicator
detail. It reuses `metrics.downsample` (from `app/analysis/metrics.py`) for
sparklines, exactly as `finance_service` does.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_economics_service.py`:

```python
from app.models import IndicatorPoint, ReleaseEvent
from app.providers import fred_provider
from app.services import economics_service


def _series(n, start=100.0, step=1.0):
    return [IndicatorPoint(date=f"2026-{(i % 12) + 1:02d}-01",
                           value=start + i * step) for i in range(n)]


def test_build_overview_assembles_indicators_and_calendar(db, monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series",
                        lambda series_id, **kw: _series(30))
    monkeypatch.setattr(fred_provider, "get_release_calendar",
                        lambda: [ReleaseEvent(date="2026-05-13",
                                              release_name="CPI")])
    overview = economics_service.build_overview()
    assert len(overview.indicators) == len(economics_service.INDICATORS)
    first = overview.indicators[0]
    assert first.series_id
    assert first.sparkline           # non-empty
    assert first.trend in ("below", "in", "above")
    assert overview.calendar[0].release_name == "CPI"
    assert overview.updated_at


def test_build_overview_skips_failed_series(db, monkeypatch):
    # One bad series must not blank the panel (per-indicator isolation).
    monkeypatch.setattr(fred_provider, "get_series", lambda series_id, **kw: [])
    monkeypatch.setattr(fred_provider, "get_release_calendar", lambda: [])
    overview = economics_service.build_overview()
    assert overview.indicators == []
    assert overview.updated_at


def test_build_indicator_returns_detail(db, monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series",
                        lambda series_id, **kw: _series(40))
    detail = economics_service.build_indicator("UNRATE")
    assert detail is not None
    assert detail.series_id == "UNRATE"
    assert len(detail.series) == 40
    assert detail.range_low <= detail.latest <= detail.range_high
    assert len(detail.recession_signals) == 2


def test_build_indicator_none_for_unknown(db, monkeypatch):
    detail = economics_service.build_indicator("NOT_A_SERIES")
    assert detail is None


def test_build_indicator_none_when_no_data(db, monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series", lambda series_id, **kw: [])
    assert economics_service.build_indicator("UNRATE") is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_economics_service.py -v`
Expected: FAIL — `economics_service` does not exist.

- [ ] **Step 3: Write the service**

Create `backend/app/services/economics_service.py`:

```python
import logging
from datetime import datetime, timezone

from app.analysis import econ_metrics as em
from app.analysis import metrics
from app.database import save_econ_series
from app.models import (EconomicsOverview, IndicatorDetail, IndicatorSummary,
                        RecessionSignal)
from app.providers import fred_provider as provider

logger = logging.getLogger(__name__)

# (series_id, display name, display unit, FRED units transform).
# "pc1" = percent change from a year ago (CPI -> YoY inflation %);
# "chg" = change from the prior observation (payrolls -> monthly jobs added);
# "lin" = the raw series.
INDICATORS: list[tuple[str, str, str, str]] = [
    ("CPIAUCSL", "Inflation (CPI)", "%", "pc1"),
    ("UNRATE", "Unemployment Rate", "%", "lin"),
    ("PAYEMS", "Nonfarm Payrolls", "K", "chg"),
    ("A191RL1Q225SBEA", "Real GDP Growth", "%", "lin"),
    ("FEDFUNDS", "Fed Funds Rate", "%", "lin"),
    ("DGS10", "10-Year Treasury", "%", "lin"),
]

# Recession-signal series (used by every indicator drill-down).
_YIELD_CURVE = "T10Y2Y"
_SAHM = "SAHMREALTIME"

_NAMES = {sid: name for sid, name, _, _ in INDICATORS}
_UNITS = {sid: unit for sid, _, unit, _ in INDICATORS}
_FRED_UNITS = {sid: fu for sid, _, _, fu in INDICATORS}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_overview() -> EconomicsOverview:
    """Assemble the Economics overview: indicator tiles + release calendar."""
    indicators: list[IndicatorSummary] = []
    for series_id, name, unit, fred_units in INDICATORS:
        points = provider.get_series(series_id, units=fred_units)
        if len(points) < 2:
            continue        # per-indicator isolation: skip, don't fail
        try:
            save_econ_series(series_id, points)
        except Exception as exc:
            logger.warning("save_econ_series(%s) failed: %s", series_id, exc)
        values = [p.value for p in points]
        indicators.append(IndicatorSummary(
            series_id=series_id, name=name, unit=unit,
            latest=points[-1].value, latest_date=points[-1].date,
            change=em.period_change(values),
            trend=em.trend_marker(values),
            sparkline=metrics.downsample(values, 24)))

    calendar = provider.get_release_calendar()
    return EconomicsOverview(indicators=indicators, calendar=calendar,
                             updated_at=_now())


def _recession_signals() -> list[RecessionSignal]:
    signals: list[RecessionSignal] = []
    for series_id, label, kind in (
            (_YIELD_CURVE, "Yield curve (10y-2y)", "yield_curve"),
            (_SAHM, "Sahm rule", "sahm")):
        points = provider.get_series(series_id)
        if not points:
            continue
        value = points[-1].value
        status, detail = em.recession_status(kind, value)
        signals.append(RecessionSignal(name=label, value=round(value, 4),
                                       status=status, detail=detail))
    return signals


def build_indicator(series_id: str) -> IndicatorDetail | None:
    """Assemble the drill-down for one indicator. None if unknown/no data."""
    series_id = series_id.strip().upper()
    if series_id not in _NAMES:
        return None
    points = provider.get_series(series_id, units=_FRED_UNITS[series_id])
    if len(points) < 2:
        return None
    values = [p.value for p in points]
    return IndicatorDetail(
        series_id=series_id, name=_NAMES[series_id], unit=_UNITS[series_id],
        series=points, latest=points[-1].value,
        change=em.period_change(values), yoy=em.yoy_change(points),
        range_low=min(values), range_high=max(values),
        momentum=em.momentum_score(values),
        recession_signals=_recession_signals(), updated_at=_now())
```

Note: `_NAMES`/`_UNITS` lookups use the upper-cased `series_id`; every key in
`INDICATORS` is already upper-case, so `build_indicator("unrate")` resolves.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_economics_service.py -v`
Expected: all five tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/economics_service.py backend/tests/test_economics_service.py
git commit -m "$(printf 'feat(backend): add Economics service\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 7: Economics routes

**Files:**
- Create: `backend/app/routes/economics.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_economics_routes.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_economics_routes.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_economics_routes.py -v`
Expected: FAIL — the routes return 404 for everything (router not registered).

- [ ] **Step 3: Write the router**

Create `backend/app/routes/economics.py`:

```python
from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_auth
from app.cache import cache
from app.services import economics_service

router = APIRouter(prefix="/api/economics", dependencies=[Depends(require_auth)])


@router.get("/overview")
def overview():
    """Cached so the frontend never blocks on FRED."""
    return cache.get_or_compute("economics:overview",
                                economics_service.build_overview)


@router.get("/indicator/{series_id}")
def indicator(series_id: str):
    key = f"economics:indicator:{series_id.strip().upper()}"
    result = cache.get_or_compute(
        key, lambda: economics_service.build_indicator(series_id))
    if result is None:
        raise HTTPException(status_code=404,
                            detail=f"No data for {series_id}")
    return result
```

- [ ] **Step 4: Register the router**

In `backend/app/main.py`, add the import alongside the other route imports:

```python
from app.routes.economics import router as economics_router
```

And register it alongside the others (after `app.include_router(finance_router)`):

```python
app.include_router(economics_router)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_economics_routes.py -v`
Expected: all three tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/economics.py backend/app/main.py backend/tests/test_economics_routes.py
git commit -m "$(printf 'feat(backend): add Economics API routes\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 8: Scheduler — warm the Economics cache

**Files:**
- Modify: `backend/app/scheduler.py`
- Test: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_scheduler.py`:

```python
def test_warm_economics_populates_cache(db, monkeypatch):
    from app.cache import cache
    from app.providers import fred_provider
    from app.models import IndicatorPoint
    from app import scheduler

    monkeypatch.setattr(fred_provider, "get_series",
                        lambda sid, **kw: [IndicatorPoint(
                            date=f"2026-0{i+1}-01", value=100.0 + i)
                            for i in range(5)])
    monkeypatch.setattr(fred_provider, "get_release_calendar", lambda: [])
    scheduler.warm_economics()
    assert cache.get("economics:overview") is not None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_scheduler.py -v`
Expected: FAIL — `warm_economics` does not exist.

- [ ] **Step 3: Add the job**

In `backend/app/scheduler.py`, add an import:

```python
from app.services import economics_service
```

Add the `warm_economics` function after `warm_overview`:

```python
def warm_economics() -> None:
    """Recompute the Economics overview and store it in the cache."""
    try:
        cache.set("economics:overview", economics_service.build_overview())
        logger.info("warmed economics:overview")
    except Exception:
        logger.warning("warm_economics failed", exc_info=True)
```

In `start_scheduler()`, register the job alongside the existing `warm_overview`
job (after that `sched.add_job(...)` call):

```python
    sched.add_job(warm_economics, "interval", hours=6, id="warm_economics",
                  max_instances=1, coalesce=True)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_scheduler.py -v`
Expected: all scheduler tests PASS.

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: the entire backend suite PASSES (Phase 1 tests + all new Economics tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/scheduler.py backend/tests/test_scheduler.py
git commit -m "$(printf 'feat(backend): warm the Economics cache on a schedule\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 9: Economics types + API client

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

Pure types + two thin endpoint wrappers — verified by the type-checker, no new
test file (the hooks task and the Playwright spec exercise them).

- [ ] **Step 1: Add the TypeScript types**

Append to `frontend/src/lib/types.ts`:

```typescript
/** Economics domain (Phase 2) — mirrors the backend economics models. */

export interface IndicatorPoint {
  date: string;
  value: number;
}

export interface ReleaseEvent {
  date: string;
  release_name: string;
}

export type TrendMarker = 'below' | 'in' | 'above';

export interface IndicatorSummary {
  series_id: string;
  name: string;
  unit: string;
  latest: number;
  latest_date: string;
  change: number;
  trend: TrendMarker;
  sparkline: number[];
}

export interface EconomicsOverview {
  indicators: IndicatorSummary[];
  calendar: ReleaseEvent[];
  updated_at: string;
}

export type SignalStatus = 'normal' | 'warning' | 'alert';

export interface RecessionSignal {
  name: string;
  value: number;
  status: SignalStatus;
  detail: string;
}

export interface IndicatorDetail {
  series_id: string;
  name: string;
  unit: string;
  series: IndicatorPoint[];
  latest: number;
  change: number;
  yoy: number | null;
  range_low: number;
  range_high: number;
  momentum: number;
  recession_signals: RecessionSignal[];
  updated_at: string;
}
```

- [ ] **Step 2: Add the endpoint functions**

In `frontend/src/lib/api.ts`, add `EconomicsOverview` and `IndicatorDetail` to
the type import from `./types`:

```typescript
import type {
  EconomicsOverview,
  IndicatorDetail,
  InstrumentResponse,
  OverviewResponse,
} from './types';
```

Add two functions inside the `api` object (after `removeWatchlist`):

```typescript
  economicsOverview: () =>
    apiFetch<EconomicsOverview>('/api/economics/overview'),

  indicator: (seriesId: string) =>
    apiFetch<IndicatorDetail>(
      `/api/economics/indicator/${encodeURIComponent(seriesId)}`,
    ),
```

- [ ] **Step 3: Verify the type-check passes**

Run: `cd frontend && npm run build`
Expected: `tsc --noEmit` passes and the build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "$(printf 'feat(frontend): add Economics types and API client\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 10: Indicator value formatting

**Files:**
- Create: `frontend/src/lib/econFormat.ts`
- Test: `frontend/src/lib/econFormat.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/econFormat.test.ts`:

```typescript
import { formatIndicatorChange, formatIndicatorValue } from './econFormat';

test('formats percent values', () => {
  expect(formatIndicatorValue(4.12, '%')).toBe('4.1%');
});

test('formats index values', () => {
  expect(formatIndicatorValue(310.27, 'index')).toBe('310.3');
});

test('formats large "K" (thousands) levels compactly', () => {
  // PAYEMS is reported in thousands of persons.
  expect(formatIndicatorValue(159000, 'K')).toBe('159M');
});

test('formats a signed percent-point change', () => {
  expect(formatIndicatorChange(-0.1, '%')).toBe('-0.1pp');
  expect(formatIndicatorChange(0.3, '%')).toBe('+0.3pp');
});

test('formats a signed "K" change compactly', () => {
  expect(formatIndicatorChange(150, 'K')).toBe('+150k');
  expect(formatIndicatorChange(-80, 'K')).toBe('-80k');
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- econFormat`
Expected: FAIL — `econFormat` module does not exist.

- [ ] **Step 3: Write the formatter**

Create `frontend/src/lib/econFormat.ts`:

```typescript
import { formatCompact } from './format';

/**
 * Format an economic indicator's headline value for display, by its unit.
 * "%" -> "4.1%"; "K" -> a compact person count; "index"/other -> 1-decimal.
 */
export function formatIndicatorValue(value: number, unit: string): string {
  switch (unit) {
    case '%':
      return `${value.toFixed(1)}%`;
    case 'K': // FRED level in thousands -> compact ("159M", "150k")
      return formatCompact(value * 1000);
    case '$':
      return formatCompact(value);
    default: // "index" and anything else
      return value.toFixed(1);
  }
}

/** Format an indicator's change vs. the prior release, signed, by its unit. */
export function formatIndicatorChange(change: number, unit: string): string {
  if (unit === 'K') {
    const mag = formatCompact(Math.abs(change) * 1000);
    return change < 0 ? `-${mag}` : `+${mag}`;
  }
  const sign = change > 0 ? '+' : '';
  if (unit === '%') return `${sign}${change.toFixed(1)}pp`;
  return `${sign}${change.toFixed(1)}`;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npm run test -- econFormat`
Expected: all five tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/econFormat.ts frontend/src/lib/econFormat.test.ts
git commit -m "$(printf 'feat(frontend): add indicator value formatting\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 11: LineChart — bespoke time-series chart

**Files:**
- Create: `frontend/src/charts/LineChart.tsx`
- Test: `frontend/src/charts/LineChart.test.tsx`

Mirrors `CandlestickChart` (margin convention, `ChartFrame`, `Axis`,
`useChartDimensions`, crosshair tooltip) but draws an area + line over an
`IndicatorPoint[]` series.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/charts/LineChart.test.tsx`:

```typescript
import { render } from '@testing-library/react';
import { LineChart } from './LineChart';
import type { IndicatorPoint } from '../lib/types';

function makePoints(n: number): IndicatorPoint[] {
  return Array.from({ length: n }, (_, i) => ({
    date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
    value: 100 + Math.sin(i / 5) * 10,
  }));
}

test('renders an area path and a line path for the series', () => {
  const { container } = render(<LineChart points={makePoints(40)} />);
  expect(container.querySelector('svg')).not.toBeNull();
  // exactly two <path>: the area fill and the line stroke
  expect(container.querySelectorAll('path')).toHaveLength(2);
});

test('renders nothing for a series shorter than two points', () => {
  const { container } = render(<LineChart points={makePoints(1)} />);
  expect(container.querySelector('svg')).toBeNull();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- LineChart`
Expected: FAIL — `LineChart` does not exist.

- [ ] **Step 3: Write the chart**

Create `frontend/src/charts/LineChart.tsx`:

```tsx
import { useId, useMemo, useRef, useState } from 'react';
import type { MouseEvent } from 'react';
import { scaleLinear } from 'd3-scale';
import { area, curveMonotoneX, line } from 'd3-shape';
import { max, min } from 'd3-array';
import { ChartFrame } from './ChartFrame';
import { Axis } from './Axis';
import { useChartDimensions } from './useChartDimensions';
import { tokens } from '../design/tokens';
import { formatDay } from '../lib/format';
import type { IndicatorPoint } from '../lib/types';

const MARGIN = { top: 12, right: 14, bottom: 26, left: 54 };

interface LineChartProps {
  points: IndicatorPoint[];
  height?: number;
}

/** Bespoke time-series area/line chart with a crosshair tooltip. */
export function LineChart({ points, height = 360 }: LineChartProps) {
  const [wrapRef, dims] = useChartDimensions<HTMLDivElement>({
    width: 820,
    height,
  });
  const [active, setActive] = useState<number | null>(null);
  const plotRef = useRef<SVGRectElement>(null);
  const rawId = useId();
  const gradientId = `line-${rawId.replace(/:/g, '')}`;

  const g = useMemo(() => {
    const innerW = Math.max(0, dims.width - MARGIN.left - MARGIN.right);
    const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);
    if (points.length < 2 || innerW <= 0) return null;

    const x = scaleLinear().domain([0, points.length - 1]).range([0, innerW]);
    const lo = min(points, (p) => p.value) ?? 0;
    const hi = max(points, (p) => p.value) ?? 1;
    const pad = (hi - lo) * 0.08 || 1;
    const y = scaleLinear()
      .domain([lo - pad, hi + pad])
      .range([innerH, 0])
      .nice();

    const linePath =
      line<IndicatorPoint>()
        .x((_, i) => x(i))
        .y((p) => y(p.value))
        .curve(curveMonotoneX)(points) ?? '';
    const areaPath =
      area<IndicatorPoint>()
        .x((_, i) => x(i))
        .y0(innerH)
        .y1((p) => y(p.value))
        .curve(curveMonotoneX)(points) ?? '';

    const step = Math.max(1, Math.ceil(points.length / 6));
    const xTicks = points
      .map((p, i) => ({ p, i }))
      .filter(({ i }) => i % step === 0)
      .map(({ p, i }) => ({
        value: i,
        offset: x(i),
        label: formatDay(p.date),
      }));
    const yTicks = y
      .ticks(5)
      .map((t) => ({ value: t, offset: y(t), label: t.toFixed(1) }));

    return { x, y, innerW, innerH, linePath, areaPath, xTicks, yTicks };
  }, [points, dims.width, height]);

  function onMove(e: MouseEvent) {
    if (!g || !plotRef.current || points.length < 2) return;
    const box = plotRef.current.getBoundingClientRect();
    const rel = e.clientX - box.left;
    const i = Math.round((rel / g.innerW) * (points.length - 1));
    setActive(Math.min(points.length - 1, Math.max(0, i)));
  }

  const activePoint = active !== null ? points[active] : null;

  if (!g) return null;

  return (
    <div ref={wrapRef} className="relative w-full">
      <ChartFrame
        width={dims.width}
        height={height}
        margin={MARGIN}
        label="Indicator time-series chart"
      >
        {() => (
          <>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor={tokens.color.accent}
                  stopOpacity={0.26}
                />
                <stop
                  offset="100%"
                  stopColor={tokens.color.accent}
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>

            {g.yTicks.map((t) => (
              <line
                key={`grid-${t.value}`}
                x1={0}
                x2={g.innerW}
                y1={t.offset}
                y2={t.offset}
                stroke={tokens.color.border}
                strokeWidth={1}
              />
            ))}
            <Axis orientation="left" ticks={g.yTicks} />
            <Axis orientation="bottom" ticks={g.xTicks} />

            <path d={g.areaPath} fill={`url(#${gradientId})`} />
            <path
              d={g.linePath}
              fill="none"
              stroke={tokens.color.accent}
              strokeWidth={1.75}
              strokeLinejoin="round"
            />

            {activePoint && active !== null && (
              <>
                <line
                  x1={g.x(active)}
                  x2={g.x(active)}
                  y1={0}
                  y2={g.innerH}
                  stroke={tokens.color.inkSoft}
                  strokeWidth={1}
                  strokeDasharray="3 3"
                  pointerEvents="none"
                />
                <circle
                  cx={g.x(active)}
                  cy={g.y(activePoint.value)}
                  r={3.5}
                  fill={tokens.color.accent}
                  pointerEvents="none"
                />
              </>
            )}

            <rect
              ref={plotRef}
              x={0}
              y={0}
              width={g.innerW}
              height={g.innerH}
              fill="transparent"
              onMouseMove={onMove}
              onMouseLeave={() => setActive(null)}
            />
          </>
        )}
      </ChartFrame>

      {activePoint && active !== null && (
        <div
          className="pointer-events-none absolute top-2 rounded-md border
                     border-border bg-raised/95 px-3 py-2 font-mono text-[11px]
                     shadow-lg"
          style={{
            left: Math.max(
              MARGIN.left,
              Math.min(dims.width - 130, MARGIN.left + g.x(active)),
            ),
          }}
        >
          <div className="text-ink-soft">{formatDay(activePoint.date)}</div>
          <div className="mt-0.5 text-ink tabular-nums">
            {activePoint.value.toLocaleString('en-US', {
              maximumFractionDigits: 2,
            })}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npm run test -- LineChart`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/charts/LineChart.tsx frontend/src/charts/LineChart.test.tsx
git commit -m "$(printf 'feat(frontend): add LineChart time-series chart\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 12: Economics data hooks

**Files:**
- Create: `frontend/src/economics/hooks.ts`
- Test: `frontend/src/economics/hooks.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/economics/hooks.test.tsx`:

```typescript
import { vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryWrapper } from '../test/utils';
import { useEconomicsOverview, useIndicator } from './hooks';

vi.mock('../lib/api', () => ({
  api: {
    economicsOverview: vi.fn().mockResolvedValue({
      indicators: [],
      calendar: [],
      updated_at: '2026-05-21T00:00:00+00:00',
    }),
    indicator: vi.fn().mockResolvedValue({ series_id: 'UNRATE' }),
  },
}));

test('useEconomicsOverview fetches the overview', async () => {
  const { result } = renderHook(() => useEconomicsOverview(), {
    wrapper: QueryWrapper,
  });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data?.updated_at).toBe('2026-05-21T00:00:00+00:00');
});

test('useIndicator fetches the requested series', async () => {
  const { result } = renderHook(() => useIndicator('UNRATE'), {
    wrapper: QueryWrapper,
  });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data?.series_id).toBe('UNRATE');
});

test('useIndicator stays idle for an empty series id', () => {
  const { result } = renderHook(() => useIndicator(''), {
    wrapper: QueryWrapper,
  });
  expect(result.current.fetchStatus).toBe('idle');
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- economics/hooks`
Expected: FAIL — `economics/hooks` does not exist.

- [ ] **Step 3: Write the hooks**

Create `frontend/src/economics/hooks.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

/** The Economics overview — econ data moves slowly; refetch every 5 min. */
export function useEconomicsOverview() {
  return useQuery({
    queryKey: ['economics-overview'],
    queryFn: api.economicsOverview,
    refetchInterval: 300_000,
  });
}

/** One indicator's drill-down detail. Disabled for an empty series id. */
export function useIndicator(seriesId: string) {
  return useQuery({
    queryKey: ['indicator', seriesId],
    queryFn: () => api.indicator(seriesId),
    enabled: seriesId.length > 0,
  });
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npm run test -- economics/hooks`
Expected: all three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/economics/hooks.ts frontend/src/economics/hooks.test.tsx
git commit -m "$(printf 'feat(frontend): add Economics data hooks\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 13: IndicatorTile

**Files:**
- Create: `frontend/src/economics/IndicatorTile.tsx`
- Test: `frontend/src/economics/IndicatorTile.test.tsx`

One overview tile: indicator name, formatted latest value, signed change
(colored), a trend-relative marker, and a `Sparkline`. The whole tile is a
`<Link>` to the drill-down (shared-element transition via `viewTransition`).

- [ ] **Step 1: Write the failing test**

Create `frontend/src/economics/IndicatorTile.test.tsx`:

```typescript
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { IndicatorTile } from './IndicatorTile';
import type { IndicatorSummary } from '../lib/types';

const summary: IndicatorSummary = {
  series_id: 'UNRATE',
  name: 'Unemployment Rate',
  unit: '%',
  latest: 4.1,
  latest_date: '2026-04-01',
  change: -0.1,
  trend: 'in',
  sparkline: [4.3, 4.2, 4.1, 4.1],
};

test('renders the indicator name, value, and change', () => {
  renderWithProviders(<IndicatorTile summary={summary} />);
  expect(screen.getByText('Unemployment Rate')).toBeInTheDocument();
  expect(screen.getByText('4.1%')).toBeInTheDocument();
  expect(screen.getByText('-0.1pp')).toBeInTheDocument();
});

test('links to the indicator drill-down', () => {
  renderWithProviders(<IndicatorTile summary={summary} />);
  expect(screen.getByRole('link')).toHaveAttribute(
    'href',
    '/economics/UNRATE',
  );
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- IndicatorTile`
Expected: FAIL — `IndicatorTile` does not exist.

- [ ] **Step 3: Write the component**

Create `frontend/src/economics/IndicatorTile.tsx`:

```tsx
import { Link } from 'react-router-dom';
import type { IndicatorSummary } from '../lib/types';
import { formatIndicatorChange, formatIndicatorValue } from '../lib/econFormat';
import { Sparkline } from '../charts/Sparkline';
import { trendColor } from '../charts/colors';
import { tokens } from '../design/tokens';

const TREND_LABEL: Record<IndicatorSummary['trend'], string> = {
  below: 'below normal',
  in: 'in range',
  above: 'above normal',
};

const TREND_COLOR: Record<IndicatorSummary['trend'], string> = {
  below: tokens.color.down,
  in: tokens.color.inkMute,
  above: tokens.color.up,
};

/** One Economics overview tile — links to the indicator drill-down. */
export function IndicatorTile({ summary }: { summary: IndicatorSummary }) {
  return (
    <Link
      to={`/economics/${summary.series_id}`}
      viewTransition
      className="flex flex-col gap-2 rounded-md border border-border
                 bg-surface px-3 py-2.5 transition-colors hover:border-border-strong"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs text-ink-soft">{summary.name}</span>
        <span
          className="font-mono text-[9px] tracking-wide uppercase"
          style={{ color: TREND_COLOR[summary.trend] }}
        >
          {TREND_LABEL[summary.trend]}
        </span>
      </div>
      <div className="flex items-end justify-between gap-2">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-lg tabular-nums text-ink">
            {formatIndicatorValue(summary.latest, summary.unit)}
          </span>
          <span
            className="font-mono text-xs tabular-nums"
            style={{ color: trendColor(summary.change) }}
          >
            {formatIndicatorChange(summary.change, summary.unit)}
          </span>
        </div>
        <Sparkline values={summary.sparkline} />
      </div>
    </Link>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npm run test -- IndicatorTile`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/economics/IndicatorTile.tsx frontend/src/economics/IndicatorTile.test.tsx
git commit -m "$(printf 'feat(frontend): add IndicatorTile\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 14: ReleaseCalendar

**Files:**
- Create: `frontend/src/economics/ReleaseCalendar.tsx`
- Test: `frontend/src/economics/ReleaseCalendar.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/economics/ReleaseCalendar.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { ReleaseCalendar } from './ReleaseCalendar';
import type { ReleaseEvent } from '../lib/types';

const events: ReleaseEvent[] = [
  { date: '2026-05-13', release_name: 'Consumer Price Index' },
  { date: '2026-05-02', release_name: 'Employment Situation' },
];

test('lists each release with its name', () => {
  render(<ReleaseCalendar events={events} />);
  expect(screen.getByText('Consumer Price Index')).toBeInTheDocument();
  expect(screen.getByText('Employment Situation')).toBeInTheDocument();
});

test('shows an empty-state message when there are no releases', () => {
  render(<ReleaseCalendar events={[]} />);
  expect(screen.getByText(/no releases/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- ReleaseCalendar`
Expected: FAIL — `ReleaseCalendar` does not exist.

- [ ] **Step 3: Write the component**

Create `frontend/src/economics/ReleaseCalendar.tsx`:

```tsx
import type { ReleaseEvent } from '../lib/types';
import { formatDay } from '../lib/format';

/** A compact list of recent / upcoming economic releases. */
export function ReleaseCalendar({ events }: { events: ReleaseEvent[] }) {
  if (events.length === 0) {
    return (
      <p className="py-2 text-center text-xs text-ink-mute">
        No releases scheduled.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-1">
      {events.slice(0, 6).map((e, i) => (
        <li
          key={`${e.date}-${i}`}
          className="flex items-baseline justify-between gap-3 text-xs"
        >
          <span className="truncate text-ink-soft">{e.release_name}</span>
          <span className="shrink-0 font-mono text-[10px] text-ink-mute">
            {formatDay(e.date)}
          </span>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npm run test -- ReleaseCalendar`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/economics/ReleaseCalendar.tsx frontend/src/economics/ReleaseCalendar.test.tsx
git commit -m "$(printf 'feat(frontend): add ReleaseCalendar\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 15: EconomicsPanel

**Files:**
- Create: `frontend/src/economics/EconomicsPanel.tsx`
- Test: `frontend/src/economics/EconomicsPanel.test.tsx`

Mirrors `FinancePanel` — uses `Panel`, `PanelSkeleton`, the `useEconomicsOverview`
hook, a stale badge, and renders the indicator tile grid + release calendar.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/economics/EconomicsPanel.test.tsx`:

```typescript
import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { EconomicsPanel } from './EconomicsPanel';

vi.mock('../lib/api', () => ({
  api: {
    economicsOverview: vi.fn().mockResolvedValue({
      indicators: [
        {
          series_id: 'UNRATE', name: 'Unemployment Rate', unit: '%',
          latest: 4.1, latest_date: '2026-04-01', change: -0.1,
          trend: 'in', sparkline: [4.3, 4.2, 4.1],
        },
      ],
      calendar: [{ date: '2026-05-13', release_name: 'Consumer Price Index' }],
      updated_at: '2026-05-21T20:00:00+00:00',
    }),
  },
}));

test('shows a loading skeleton before data arrives', () => {
  renderWithProviders(<EconomicsPanel />);
  expect(screen.getByRole('status')).toBeInTheDocument();
});

test('renders indicator tiles and the release calendar', async () => {
  renderWithProviders(<EconomicsPanel />);
  await waitFor(() =>
    expect(screen.getByText('Unemployment Rate')).toBeInTheDocument(),
  );
  expect(screen.getByText('Consumer Price Index')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- EconomicsPanel`
Expected: FAIL — `EconomicsPanel` does not exist.

- [ ] **Step 3: Write the component**

Create `frontend/src/economics/EconomicsPanel.tsx`:

```tsx
import { Panel } from '../components/Panel';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { formatUpdated } from '../lib/format';
import { useEconomicsOverview } from './hooks';
import { IndicatorTile } from './IndicatorTile';
import { ReleaseCalendar } from './ReleaseCalendar';

/** The Economics quadrant: macro-indicator tiles + a release calendar. */
export function EconomicsPanel() {
  const { data, isLoading, isError, isStale } = useEconomicsOverview();

  return (
    <Panel
      title="Economics"
      icon="📊"
      action={
        data ? (
          <span className="font-mono text-[10px] text-ink-mute">
            {isStale ? 'Stale · ' : ''}
            {formatUpdated(data.updated_at)}
          </span>
        ) : undefined
      }
    >
      {isLoading && <PanelSkeleton rows={6} />}
      {isError && (
        <p className="py-8 text-center text-sm text-down">
          Couldn't load economic data.
        </p>
      )}
      {data && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-2">
            {data.indicators.map((ind) => (
              <IndicatorTile key={ind.series_id} summary={ind} />
            ))}
          </div>
          <div>
            <h3 className="mb-1.5 font-mono text-[10px] tracking-widest
                           text-ink-mute uppercase">
              Release Calendar
            </h3>
            <ReleaseCalendar events={data.calendar} />
          </div>
        </div>
      )}
    </Panel>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npm run test -- EconomicsPanel`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/economics/EconomicsPanel.tsx frontend/src/economics/EconomicsPanel.test.tsx
git commit -m "$(printf 'feat(frontend): add EconomicsPanel\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 16: Wire EconomicsPanel into the Home dashboard

**Files:**
- Modify: `frontend/src/routes/Home.tsx`
- Test: `frontend/src/routes/Home.test.tsx`

- [ ] **Step 1: Update the Home test**

In `frontend/src/routes/Home.test.tsx`, the `vi.mock('../lib/api', …)` mock
currently exposes only finance functions. Add `economicsOverview` so the now-live
`EconomicsPanel` has data. Replace the whole `vi.mock` block with:

```typescript
vi.mock('../lib/api', () => ({
  api: {
    overview: vi.fn().mockResolvedValue({
      watchlist: [], indices: [], sectors: [],
      breadth: {
        advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0,
      },
      updated_at: '2026-05-20T20:00:00+00:00',
    }),
    addWatchlist: vi.fn(),
    removeWatchlist: vi.fn(),
    economicsOverview: vi.fn().mockResolvedValue({
      indicators: [], calendar: [], updated_at: '2026-05-20T20:00:00+00:00',
    }),
  },
}));
```

The existing `test('renders the four-quadrant dashboard shell', …)` is unchanged
and still valid — `Economics` is still on screen (now as the live panel's title).

- [ ] **Step 2: Run the test to verify it still passes (no regression)**

Run: `cd frontend && npm run test -- routes/Home`
Expected: the Home shell test PASSES with the updated mock.

- [ ] **Step 3: Wire in the panel**

Replace the entire contents of `frontend/src/routes/Home.tsx` with:

```tsx
import { AppShell } from '../components/AppShell';
import { QuadrantGrid } from '../components/QuadrantGrid';
import { ComingSoonPanel } from '../components/ComingSoonPanel';
import { FinancePanel } from '../finance/FinancePanel';
import { EconomicsPanel } from '../economics/EconomicsPanel';

export function Home() {
  return (
    <AppShell>
      <QuadrantGrid
        news={<ComingSoonPanel title="News" icon="📰" phase="Phase 3" />}
        politics={<ComingSoonPanel title="Politics" icon="🏛" phase="Phase 4" />}
        economics={<EconomicsPanel />}
        finance={<FinancePanel />}
      />
    </AppShell>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npm run test -- routes/Home`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/Home.tsx frontend/src/routes/Home.test.tsx
git commit -m "$(printf 'feat(frontend): make the Economics quadrant live\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 17: RecessionSignals + IndicatorStats (drill-down pieces)

**Files:**
- Create: `frontend/src/economics/RecessionSignals.tsx`
- Create: `frontend/src/economics/IndicatorStats.tsx`
- Test: `frontend/src/economics/drilldownPieces.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/economics/drilldownPieces.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { RecessionSignals } from './RecessionSignals';
import { IndicatorStats } from './IndicatorStats';
import type { IndicatorDetail, RecessionSignal } from '../lib/types';

const signals: RecessionSignal[] = [
  {
    name: 'Yield curve (10y-2y)', value: -0.15, status: 'alert',
    detail: 'Inverted — historically a recession precursor.',
  },
  {
    name: 'Sahm rule', value: 0.1, status: 'normal',
    detail: 'Well below the Sahm-rule threshold.',
  },
];

const detail: IndicatorDetail = {
  series_id: 'UNRATE', name: 'Unemployment Rate', unit: '%',
  series: [{ date: '2026-04-01', value: 4.1 }],
  latest: 4.1, change: -0.1, yoy: 0.3, range_low: 3.4, range_high: 4.3,
  momentum: -2.4, recession_signals: signals,
  updated_at: '2026-05-21T00:00:00+00:00',
};

test('RecessionSignals lists each signal name and detail', () => {
  render(<RecessionSignals signals={signals} />);
  expect(screen.getByText('Yield curve (10y-2y)')).toBeInTheDocument();
  expect(
    screen.getByText('Inverted — historically a recession precursor.'),
  ).toBeInTheDocument();
  expect(screen.getByText('Sahm rule')).toBeInTheDocument();
});

test('IndicatorStats shows the headline stat tiles', () => {
  render(<IndicatorStats detail={detail} />);
  expect(screen.getByText('Latest')).toBeInTheDocument();
  expect(screen.getByText('4.1%')).toBeInTheDocument();
  expect(screen.getByText('YoY')).toBeInTheDocument();
  expect(screen.getByText('Momentum')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- drilldownPieces`
Expected: FAIL — neither component exists.

- [ ] **Step 3: Write `RecessionSignals.tsx`**

Create `frontend/src/economics/RecessionSignals.tsx`:

```tsx
import type { RecessionSignal, SignalStatus } from '../lib/types';
import { tokens } from '../design/tokens';

const STATUS_COLOR: Record<SignalStatus, string> = {
  normal: tokens.color.up,
  warning: '#d2a44e',
  alert: tokens.color.down,
};

/** The drill-down's recession-signal composite — one row per signal. */
export function RecessionSignals({ signals }: { signals: RecessionSignal[] }) {
  if (signals.length === 0) {
    return (
      <p className="text-xs text-ink-mute">
        Recession signals are unavailable right now.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {signals.map((s) => (
        <div
          key={s.name}
          className="flex items-start gap-3 rounded-md border border-border
                     bg-surface px-3 py-2"
        >
          <span
            className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
            style={{ background: STATUS_COLOR[s.status] }}
          />
          <div className="flex flex-col">
            <div className="flex items-baseline gap-2">
              <span className="text-sm text-ink">{s.name}</span>
              <span className="font-mono text-xs tabular-nums text-ink-soft">
                {s.value.toFixed(2)}
              </span>
            </div>
            <span className="text-xs text-ink-mute">{s.detail}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Write `IndicatorStats.tsx`**

Create `frontend/src/economics/IndicatorStats.tsx`:

```tsx
import type { IndicatorDetail } from '../lib/types';
import { formatIndicatorChange, formatIndicatorValue } from '../lib/econFormat';
import { trendColor } from '../charts/colors';
import { tokens } from '../design/tokens';

/** The drill-down's headline summary stats as compact tiles. */
export function IndicatorStats({ detail }: { detail: IndicatorDetail }) {
  const items: { label: string; value: string; color: string }[] = [
    {
      label: 'Latest',
      value: formatIndicatorValue(detail.latest, detail.unit),
      color: tokens.color.ink,
    },
    {
      label: 'Change',
      value: formatIndicatorChange(detail.change, detail.unit),
      color: trendColor(detail.change),
    },
    {
      label: 'YoY',
      value:
        detail.yoy == null
          ? '—'
          : `${detail.yoy > 0 ? '+' : ''}${detail.yoy.toFixed(1)}%`,
      color: detail.yoy == null ? tokens.color.inkMute : trendColor(detail.yoy),
    },
    {
      label: 'Momentum',
      value: `${detail.momentum > 0 ? '+' : ''}${detail.momentum.toFixed(1)}%`,
      color: trendColor(detail.momentum),
    },
    {
      label: 'Range',
      value: `${formatIndicatorValue(detail.range_low, detail.unit)} – ${formatIndicatorValue(detail.range_high, detail.unit)}`,
      color: tokens.color.ink,
    },
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((it) => (
        <div
          key={it.label}
          className="flex flex-col rounded-md border border-border bg-surface
                     px-3 py-2"
        >
          <span className="font-mono text-[10px] tracking-wide text-ink-mute
                           uppercase">
            {it.label}
          </span>
          <span
            className="font-mono text-sm tabular-nums"
            style={{ color: it.color }}
          >
            {it.value}
          </span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd frontend && npm run test -- drilldownPieces`
Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/economics/RecessionSignals.tsx frontend/src/economics/IndicatorStats.tsx frontend/src/economics/drilldownPieces.test.tsx
git commit -m "$(printf 'feat(frontend): add RecessionSignals and IndicatorStats\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 18: IndicatorRoute drill-down page + route

**Files:**
- Create: `frontend/src/routes/IndicatorRoute.tsx`
- Modify: `frontend/src/router.tsx`
- Test: `frontend/src/routes/IndicatorRoute.test.tsx`

Mirrors `InstrumentRoute` — `AppShell`, a back link, an animated header, the
`LineChart` hero (with a `viewTransitionName` for the shared-element morph), the
summary stats, the recession-signal composite, and the Phase 5 placeholder.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/routes/IndicatorRoute.test.tsx`:

```typescript
import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { IndicatorRoute } from './IndicatorRoute';

vi.mock('../lib/api', () => ({
  api: {
    indicator: vi.fn().mockResolvedValue({
      series_id: 'UNRATE', name: 'Unemployment Rate', unit: '%',
      series: Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
        value: 4 + Math.sin(i / 5) * 0.5,
      })),
      latest: 4.1, change: -0.1, yoy: 0.3, range_low: 3.4, range_high: 4.3,
      momentum: -2.4,
      recession_signals: [
        {
          name: 'Yield curve (10y-2y)', value: -0.15, status: 'alert',
          detail: 'Inverted — historically a recession precursor.',
        },
      ],
      updated_at: '2026-05-21T20:00:00+00:00',
    }),
  },
}));

test('renders the indicator drill-down', async () => {
  renderWithProviders(<IndicatorRoute />, {
    route: '/economics/UNRATE',
    path: '/economics/:seriesId',
  });
  await waitFor(() =>
    expect(
      screen.getByRole('heading', { name: 'Unemployment Rate' }),
    ).toBeInTheDocument(),
  );
  expect(screen.getByText('Recession Signals')).toBeInTheDocument();
  expect(screen.getByText('Yield curve (10y-2y)')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- IndicatorRoute`
Expected: FAIL — `IndicatorRoute` does not exist.

- [ ] **Step 3: Write the route component**

Create `frontend/src/routes/IndicatorRoute.tsx`:

```tsx
import { Link, useParams } from 'react-router-dom';
import { motion } from 'motion/react';
import { useIndicator } from '../economics/hooks';
import { LineChart } from '../charts/LineChart';
import { IndicatorStats } from '../economics/IndicatorStats';
import { RecessionSignals } from '../economics/RecessionSignals';
import { AppShell } from '../components/AppShell';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { formatUpdated } from '../lib/format';
import { spring } from '../design/motion';

export function IndicatorRoute() {
  const { seriesId = '' } = useParams();
  const upper = seriesId.toUpperCase();
  const { data, isLoading, isError } = useIndicator(upper);

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl p-4">
        <Link
          to="/"
          viewTransition
          className="font-mono text-xs text-ink-soft transition-colors
                     hover:text-accent"
        >
          ← Dashboard
        </Link>

        {isLoading && (
          <div className="mt-4">
            <PanelSkeleton rows={8} />
          </div>
        )}

        {isError && (
          <p className="mt-8 text-center text-sm text-down">
            No data available for {upper}.
          </p>
        )}

        {data && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring.gentle}
            className="mt-3"
          >
            <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h1 className="font-mono text-2xl font-semibold text-ink">
                {data.name}
              </h1>
              <span className="font-mono text-sm text-ink-soft">
                {data.series_id}
              </span>
            </header>

            <div
              className="mt-4 rounded-lg border border-border bg-surface p-4"
              style={{ viewTransitionName: 'indicator-hero' }}
            >
              <LineChart points={data.series} />
            </div>

            <h2 className="mt-6 font-mono text-xs tracking-widest text-ink-mute
                           uppercase">
              Summary
            </h2>
            <div className="mt-2">
              <IndicatorStats detail={data} />
            </div>

            <h2 className="mt-6 font-mono text-xs tracking-widest text-ink-mute
                           uppercase">
              Recession Signals
            </h2>
            <div className="mt-2">
              <RecessionSignals signals={data.recession_signals} />
            </div>

            <h2 className="mt-6 font-mono text-xs tracking-widest text-ink-mute
                           uppercase">
              Why this matters
            </h2>
            <p className="mt-2 rounded-md border border-dashed border-border
                          bg-surface px-3 py-3 text-sm text-ink-mute">
              AI-generated context for this indicator arrives in a later phase.
            </p>

            <p className="mt-6 font-mono text-[10px] text-ink-mute">
              {formatUpdated(data.updated_at)}
            </p>
          </motion.div>
        )}
      </div>
    </AppShell>
  );
}
```

- [ ] **Step 4: Register the route**

Replace the entire contents of `frontend/src/router.tsx` with:

```tsx
import { createBrowserRouter } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { Home } from './routes/Home';
import { InstrumentRoute } from './routes/InstrumentRoute';
import { IndicatorRoute } from './routes/IndicatorRoute';

export const routes: RouteObject[] = [
  { path: '/', element: <Home /> },
  { path: '/finance/:symbol', element: <InstrumentRoute /> },
  { path: '/economics/:seriesId', element: <IndicatorRoute /> },
];

export const router = createBrowserRouter(routes);
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd frontend && npm run test -- IndicatorRoute`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/IndicatorRoute.tsx frontend/src/router.tsx frontend/src/routes/IndicatorRoute.test.tsx
git commit -m "$(printf 'feat(frontend): add the indicator drill-down route\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Task 19: End-to-end test + verification

**Files:**
- Create: `frontend/e2e/economics-drilldown.spec.ts`
- Modify: `README.md`

- [ ] **Step 1: Write the Playwright E2E spec**

Create `frontend/e2e/economics-drilldown.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

const financeOverview = {
  watchlist: [],
  indices: [],
  sectors: [],
  breadth: { advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0 },
  updated_at: '2026-05-21T20:00:00+00:00',
};

const economicsOverview = {
  indicators: [
    {
      series_id: 'UNRATE', name: 'Unemployment Rate', unit: '%',
      latest: 4.1, latest_date: '2026-04-01', change: -0.1,
      trend: 'in', sparkline: [4.3, 4.2, 4.1, 4.0, 4.1],
    },
  ],
  calendar: [{ date: '2026-05-13', release_name: 'Consumer Price Index' }],
  updated_at: '2026-05-21T20:00:00+00:00',
};

function makeSeries(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
    value: 4 + Math.sin(i / 6) * 0.6,
  }));
}

const indicatorDetail = {
  series_id: 'UNRATE', name: 'Unemployment Rate', unit: '%',
  series: makeSeries(120),
  latest: 4.1, change: -0.1, yoy: 0.3, range_low: 3.4, range_high: 4.3,
  momentum: -2.4,
  recession_signals: [
    {
      name: 'Yield curve (10y-2y)', value: -0.15, status: 'alert',
      detail: 'Inverted — historically a recession precursor.',
    },
  ],
  updated_at: '2026-05-21T20:00:00+00:00',
};

async function stubApi(page: Page) {
  await page.route('**/api/auth/status', (route) =>
    route.fulfill({ json: { auth_enabled: false } }),
  );
  await page.route('**/api/finance/overview', (route) =>
    route.fulfill({ json: financeOverview }),
  );
  await page.route('**/api/economics/overview', (route) =>
    route.fulfill({ json: economicsOverview }),
  );
  await page.route('**/api/economics/indicator/**', (route) =>
    route.fulfill({ json: indicatorDetail }),
  );
}

test('the economics overview drills down into an indicator page', async ({
  page,
}) => {
  await stubApi(page);
  await page.goto('/');

  await expect(page.getByText('NMD')).toBeVisible();
  await expect(page.getByText('Unemployment Rate')).toBeVisible();

  await page.getByRole('link', { name: /Unemployment Rate/ }).click();

  await expect(page).toHaveURL(/\/economics\/UNRATE$/);
  await expect(
    page.getByRole('heading', { name: 'Unemployment Rate' }),
  ).toBeVisible();
  await expect(page.getByText('Recession Signals')).toBeVisible();
});
```

- [ ] **Step 2: Run the E2E test**

Run: `cd frontend && npm run test:e2e -- economics-drilldown`
Expected: the test PASSES (Playwright starts its own dev server; the API is stubbed).

- [ ] **Step 3: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: ALL backend tests PASS (Phase 1 + Phase 2).

- [ ] **Step 4: Run the full frontend suite + build**

Run: `cd frontend && npm run test && npm run build`
Expected: all Vitest tests PASS; `tsc --noEmit` clean; `vite build` succeeds.

- [ ] **Step 5: Update the README**

In the root `README.md`, the Phase line currently reads "Phase 1 (live): …".
Add a sentence to that paragraph noting Economics is now built:

Find the paragraph beginning `**Phase 1 (live):**` and append this sentence to
the end of that paragraph (before the blank line):

```
Phase 2 adds the Economics domain — a FRED-backed indicator overview and an indicator drill-down.
```

- [ ] **Step 6: Commit**

```bash
git add frontend/e2e/economics-drilldown.spec.ts README.md
git commit -m "$(printf 'test(frontend): end-to-end economics overview-to-drilldown flow\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>')"
```

---

## Plan complete

Phase 2 ships the Economics domain end-to-end: a FRED-backed overview panel
(indicator tiles + release calendar) and an indicator drill-down page, mirroring
the Finance domain and reusing the established chart/motion/design systems.

**Live deploy note:** Going live needs a free FRED API key (register at
fredaccount.stlouisfed.org) set as the `FRED_API_KEY` Fly secret
(`fly secrets set FRED_API_KEY=… -a news-dashboard-api`) and as a Vercel build
env var is **not** needed (the key is backend-only). All build/test work uses
mocked FRED responses, so the key is only required at deploy time. With no key
set, the Economics endpoints return empty-but-valid payloads and the panel
degrades gracefully.

