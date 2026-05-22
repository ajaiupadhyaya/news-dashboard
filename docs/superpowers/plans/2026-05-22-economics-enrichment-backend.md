# Economics Enrichment — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the Economics backend to power a full `/economics` domain page — a 20-indicator categorized registry, a `build_dashboard()` payload, a `/api/economics/dashboard` endpoint, indicator transform + timeframe parameters, and NBER recession periods.

**Architecture:** Purely additive over the existing FRED-backed Economics backend. The 6-indicator tuple list becomes a 20-entry `Indicator` dataclass registry tagged with six macro categories. A new `build_dashboard()` groups every indicator by category and bundles the recession signals + release calendar. The `indicator` endpoint gains optional `transform` (FRED `units`) and `range` (FRED `observation_start`) query params. NBER recession intervals are derived from the FRED `USREC` series via a new pure analysis function. The home Economics panel keeps a curated 6-indicator overview — unchanged.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, httpx (FRED), APScheduler, pytest.

**Working directory:** `~/Documents/news-dashboard`. All paths below are relative to it.

**Conventions for every task:**
- Backend tests run from `backend/`: `cd backend && PYTHONPATH=. .venv/bin/pytest <path> -v`. The `PYTHONPATH=.` is required.
- Commit after each task. Work on a feature branch — never `main`.
- The Economics routes are auth-gated; tests run with auth disabled (no `DASHBOARD_PASSWORD`), exactly like the existing economics tests.
- Per-indicator isolation is sacred: one failed FRED series must never blank a panel — skip and continue.

---

## File structure

**Modified:**
- `backend/app/models.py` — add `RecessionPeriod`, `IndicatorCategory`, `EconomicsDashboard`; extend `IndicatorSummary` with `category`, `IndicatorDetail` with `recession_periods`.
- `backend/app/services/economics_service.py` — the `Indicator` dataclass + 20-entry registry, `_summarize`/`_scale_points`/`_effective_scale` helpers, `build_dashboard()`, `build_indicator()` transform/range params.
- `backend/app/analysis/econ_metrics.py` — add the pure `recession_intervals` function.
- `backend/app/providers/fred_provider.py` — add `get_recession_periods()`; `get_series` gains an `observation_start` param.
- `backend/app/routes/economics.py` — add the `/dashboard` route; add `transform`/`range` params to `/indicator`.
- `backend/app/scheduler.py` — `warm_economics` also warms the dashboard.
- Test files: `tests/test_models.py`, `tests/test_economics_service.py`, `tests/test_econ_metrics.py`, `tests/test_fred_provider.py`, `tests/test_economics_routes.py`, `tests/test_scheduler.py`.

---

## Task 1: Models — recession periods, dashboard, category tagging

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_models.py`:

```python
def test_recession_period_model():
    from app.models import RecessionPeriod
    p = RecessionPeriod(start="2020-02-01", end="2020-04-01")
    assert p.start == "2020-02-01"
    assert p.end == "2020-04-01"


def test_indicator_summary_has_optional_category():
    from app.models import IndicatorSummary
    s = IndicatorSummary(
        series_id="CPIAUCSL", name="Inflation (CPI)", unit="%",
        category="Inflation", latest=3.0, latest_date="2026-04-01",
        change=0.1, trend="in", sparkline=[1.0, 2.0])
    assert s.category == "Inflation"
    # category defaults to "" so older constructions stay valid
    s2 = IndicatorSummary(
        series_id="UNRATE", name="Unemployment Rate", unit="%", latest=4.0,
        latest_date="2026-04-01", change=0.0, trend="in", sparkline=[1.0])
    assert s2.category == ""


def test_indicator_detail_has_recession_periods_default():
    from app.models import IndicatorDetail
    d = IndicatorDetail(
        series_id="UNRATE", name="Unemployment Rate", unit="%", series=[],
        latest=4.0, change=0.0, range_low=3.0, range_high=5.0, momentum=0.0,
        recession_signals=[], updated_at="t")
    assert d.recession_periods == []


def test_economics_dashboard_model():
    from app.models import (EconomicsDashboard, IndicatorCategory,
                            IndicatorSummary)
    summary = IndicatorSummary(
        series_id="CPIAUCSL", name="Inflation (CPI)", unit="%",
        category="Inflation", latest=3.0, latest_date="2026-04-01",
        change=0.1, trend="in", sparkline=[1.0, 2.0])
    cat = IndicatorCategory(name="Inflation", indicators=[summary])
    dash = EconomicsDashboard(categories=[cat], recession_signals=[],
                              calendar=[], updated_at="t")
    assert dash.categories[0].name == "Inflation"
    assert dash.categories[0].indicators[0].category == "Inflation"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_models.py -v`
Expected: FAIL — `ImportError` / `RecessionPeriod` not defined.

- [ ] **Step 3: Add `category` to `IndicatorSummary`**

In `backend/app/models.py`, in the `IndicatorSummary` class, add the `category` field right after `name`:

```python
class IndicatorSummary(BaseModel):
    series_id: str
    name: str
    category: str = ""     # macro category; "" for the home-panel overview
    unit: str          # display unit: "%", "K", "index", "$"
    latest: float      # headline value
    latest_date: str
    change: float      # change vs. the prior observation, headline units
    trend: str         # trend-relative marker: "below" | "in" | "above"
    sparkline: list[float]
```

- [ ] **Step 4: Add `RecessionPeriod` and extend `IndicatorDetail`**

In `backend/app/models.py`, immediately **before** the `class IndicatorDetail` definition, add:

```python
class RecessionPeriod(BaseModel):
    start: str         # ISO date the NBER recession began
    end: str           # ISO date the recession ended
```

Then, inside `IndicatorDetail`, add the `recession_periods` field right after `recession_signals`:

```python
    recession_signals: list[RecessionSignal]
    recession_periods: list[RecessionPeriod] = []
    updated_at: str
```

- [ ] **Step 5: Add `IndicatorCategory` and `EconomicsDashboard`**

In `backend/app/models.py`, immediately **after** the `class IndicatorDetail` definition, add:

```python
class IndicatorCategory(BaseModel):
    name: str          # "Growth" | "Inflation" | "Labor" | "Rates" | "Housing" | "Consumer"
    indicators: list[IndicatorSummary]


class EconomicsDashboard(BaseModel):
    categories: list[IndicatorCategory]
    recession_signals: list[RecessionSignal]
    calendar: list[ReleaseEvent]
    updated_at: str
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_models.py -v`
Expected: PASS (all model tests, old and new).

- [ ] **Step 7: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add backend/app/models.py backend/tests/test_models.py
git commit -m "feat(economics): add dashboard, category, and recession-period models"
```

---

## Task 2: Indicator registry — the `Indicator` dataclass + 20 categorized series

Replace the 6-entry `INDICATORS` tuple list with a frozen `Indicator` dataclass registry of 20 series across six categories, and rewire `build_overview` / `build_indicator` to consume it. The home panel keeps a curated 6-indicator overview.

**Files:**
- Modify: `backend/app/services/economics_service.py`
- Modify: `backend/tests/test_economics_service.py`

- [ ] **Step 1: Write the failing test + update the broken assertion**

In `backend/tests/test_economics_service.py`, append this new test:

```python
def test_indicator_registry_is_categorized():
    from app.services import economics_service as es
    assert len(es.INDICATORS) == 20
    assert es.CATEGORY_ORDER == [
        "Growth", "Inflation", "Labor", "Rates", "Housing", "Consumer"]
    assert all(ind.category in es.CATEGORY_ORDER for ind in es.INDICATORS)
    ids = {ind.series_id for ind in es.INDICATORS}
    assert len(ids) == 20                         # no duplicates
    assert set(es.OVERVIEW_IDS).issubset(ids)
```

Then, in the existing `test_build_overview_assembles_indicators_and_calendar`, change this line:

```python
    assert len(overview.indicators) == len(economics_service.INDICATORS)
```

to:

```python
    assert len(overview.indicators) == len(economics_service.OVERVIEW_IDS)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_economics_service.py -v`
Expected: FAIL — `CATEGORY_ORDER` / `OVERVIEW_IDS` not defined.

- [ ] **Step 3: Replace the registry in `economics_service.py`**

In `backend/app/services/economics_service.py`, replace the import block and the `INDICATORS` / `_NAMES` / `_UNITS` / `_FRED_UNITS` definitions (everything from `from app.analysis import ...` down to the `_FRED_UNITS = {...}` line) with:

```python
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.analysis import econ_metrics as em
from app.analysis import metrics
from app.database import save_econ_series
from app.models import (EconomicsDashboard, EconomicsOverview,
                        IndicatorCategory, IndicatorDetail, IndicatorPoint,
                        IndicatorSummary, RecessionSignal)
from app.providers import fred_provider as provider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Indicator:
    """One macro series in the dashboard registry."""
    series_id: str
    name: str
    unit: str          # display unit: "%" | "K" | "index" | "$"
    fred_units: str    # default FRED transform: "lin" | "pc1" | "chg"
    category: str      # one of CATEGORY_ORDER
    scale: float = 1.0 # display multiplier for raw-level data (e.g. ICSA)


CATEGORY_ORDER = ["Growth", "Inflation", "Labor", "Rates", "Housing",
                  "Consumer"]

# FRED units codes: "lin" = raw level, "pc1" = % change from a year ago,
# "chg" = change from the prior observation.
INDICATORS: list[Indicator] = [
    # Growth
    Indicator("A191RL1Q225SBEA", "Real GDP Growth", "%", "lin", "Growth"),
    Indicator("INDPRO", "Industrial Production", "%", "pc1", "Growth"),
    Indicator("RSAFS", "Retail Sales", "%", "pc1", "Growth"),
    # Inflation
    Indicator("CPIAUCSL", "Inflation (CPI)", "%", "pc1", "Inflation"),
    Indicator("CPILFESL", "Core CPI", "%", "pc1", "Inflation"),
    Indicator("PCEPI", "PCE Price Index", "%", "pc1", "Inflation"),
    # Labor
    Indicator("UNRATE", "Unemployment Rate", "%", "lin", "Labor"),
    Indicator("PAYEMS", "Nonfarm Payrolls", "K", "chg", "Labor"),
    Indicator("CIVPART", "Labor Force Participation", "%", "lin", "Labor"),
    Indicator("ICSA", "Initial Jobless Claims", "K", "lin", "Labor",
              scale=0.001),
    # Rates
    Indicator("FEDFUNDS", "Fed Funds Rate", "%", "lin", "Rates"),
    Indicator("DGS10", "10-Year Treasury", "%", "lin", "Rates"),
    Indicator("DGS2", "2-Year Treasury", "%", "lin", "Rates"),
    Indicator("T10Y2Y", "10y-2y Spread", "%", "lin", "Rates"),
    # Housing
    Indicator("HOUST", "Housing Starts", "K", "lin", "Housing"),
    Indicator("PERMIT", "Building Permits", "K", "lin", "Housing"),
    Indicator("MORTGAGE30US", "30-Year Mortgage Rate", "%", "lin", "Housing"),
    # Consumer
    Indicator("UMCSENT", "Consumer Sentiment", "index", "lin", "Consumer"),
    Indicator("PSAVERT", "Personal Saving Rate", "%", "lin", "Consumer"),
    Indicator("DSPIC96", "Real Disposable Income", "%", "pc1", "Consumer"),
]

# The curated subset shown on the calm four-quadrant home panel.
OVERVIEW_IDS = ["CPIAUCSL", "UNRATE", "PAYEMS", "A191RL1Q225SBEA",
                "FEDFUNDS", "DGS10"]

_BY_ID = {ind.series_id: ind for ind in INDICATORS}

# Recession-signal series (used by every indicator drill-down).
_YIELD_CURVE = "T10Y2Y"
_SAHM = "SAHMREALTIME"
```

Note: this removes the old `_NAMES` / `_UNITS` / `_FRED_UNITS` dicts — they are replaced by `_BY_ID`. Keep the existing `_now()` function as-is below this block.

- [ ] **Step 4: Add the scaling + summary helpers**

In `backend/app/services/economics_service.py`, immediately after the `_now()` function, add:

```python
def _effective_scale(ind: Indicator, units: str) -> float:
    """An indicator's display scale applies only to raw-level data; FRED's
    pc1/pch/chg transforms already yield ready-to-show numbers."""
    return ind.scale if units == "lin" else 1.0


def _scale_points(points: list[IndicatorPoint],
                  scale: float) -> list[IndicatorPoint]:
    """Apply a display scale to a series. Identity when scale == 1.0."""
    if scale == 1.0:
        return points
    return [IndicatorPoint(date=p.date, value=round(p.value * scale, 6))
            for p in points]


def _summarize(ind: Indicator) -> IndicatorSummary | None:
    """Fetch one indicator and build its summary tile. None on no data."""
    points = provider.get_series(ind.series_id, units=ind.fred_units)
    if len(points) < 2:
        return None        # per-indicator isolation: skip, don't fail
    points = _scale_points(points, _effective_scale(ind, ind.fred_units))
    try:
        save_econ_series(ind.series_id, points)
    except Exception as exc:
        logger.warning("save_econ_series(%s) failed: %s", ind.series_id, exc)
    values = [p.value for p in points]
    return IndicatorSummary(
        series_id=ind.series_id, name=ind.name, category=ind.category,
        unit=ind.unit, latest=points[-1].value, latest_date=points[-1].date,
        change=em.period_change(values), trend=em.trend_marker(values),
        sparkline=metrics.downsample(values, 24))
```

- [ ] **Step 5: Rewrite `build_overview` and `build_indicator` to use the registry**

In `backend/app/services/economics_service.py`, replace the entire existing `build_overview` function with:

```python
def build_overview() -> EconomicsOverview:
    """Assemble the Economics overview — the curated home-panel subset."""
    indicators: list[IndicatorSummary] = []
    for series_id in OVERVIEW_IDS:
        summary = _summarize(_BY_ID[series_id])
        if summary is not None:
            indicators.append(summary)
    calendar = provider.get_release_calendar()
    return EconomicsOverview(indicators=indicators, calendar=calendar,
                             updated_at=_now())
```

Then replace the entire existing `build_indicator` function with:

```python
def build_indicator(series_id: str) -> IndicatorDetail | None:
    """Assemble the drill-down for one indicator. None if unknown/no data."""
    series_id = series_id.strip().upper()
    ind = _BY_ID.get(series_id)
    if ind is None:
        return None
    points = provider.get_series(series_id, units=ind.fred_units)
    if len(points) < 2:
        return None
    points = _scale_points(points, _effective_scale(ind, ind.fred_units))
    values = [p.value for p in points]
    return IndicatorDetail(
        series_id=series_id, name=ind.name, unit=ind.unit, series=points,
        latest=points[-1].value, change=em.period_change(values),
        yoy=em.yoy_change(points), range_low=min(values),
        range_high=max(values), momentum=em.momentum_score(values),
        recession_signals=_recession_signals(), updated_at=_now())
```

Leave the `_recession_signals()` function exactly as it is.

- [ ] **Step 6: Run the full economics-service suite to verify it passes**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_economics_service.py -v`
Expected: PASS — the new registry test, the updated overview count test, and all existing service tests.

- [ ] **Step 7: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add backend/app/services/economics_service.py \
  backend/tests/test_economics_service.py
git commit -m "feat(economics): expand to a 20-indicator categorized registry"
```

---

## Task 3: `recession_intervals` — pure NBER-interval derivation

A pure function that turns a 0/1 indicator series (the FRED `USREC` recession flag) into contiguous date intervals.

**Files:**
- Modify: `backend/app/analysis/econ_metrics.py`
- Modify: `backend/tests/test_econ_metrics.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_econ_metrics.py`:

```python
def test_recession_intervals_finds_contiguous_runs():
    pts = _points([("2020-01-01", 0), ("2020-02-01", 1), ("2020-03-01", 1),
                   ("2020-04-01", 0), ("2020-05-01", 0)])
    assert em.recession_intervals(pts) == [("2020-02-01", "2020-04-01")]


def test_recession_intervals_handles_open_final_run():
    pts = _points([("2020-01-01", 0), ("2020-02-01", 1), ("2020-03-01", 1)])
    assert em.recession_intervals(pts) == [("2020-02-01", "2020-03-01")]


def test_recession_intervals_empty_when_no_recession():
    pts = _points([("2020-01-01", 0), ("2020-02-01", 0)])
    assert em.recession_intervals(pts) == []


def test_recession_intervals_handles_multiple_runs():
    pts = _points([("2001-01-01", 1), ("2001-02-01", 0), ("2008-01-01", 1),
                   ("2008-02-01", 0)])
    assert em.recession_intervals(pts) == [
        ("2001-01-01", "2001-02-01"), ("2008-01-01", "2008-02-01")]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_econ_metrics.py -v`
Expected: FAIL — `econ_metrics` has no attribute `recession_intervals`.

- [ ] **Step 3: Implement `recession_intervals`**

Append to `backend/app/analysis/econ_metrics.py`:

```python
def recession_intervals(points: list[IndicatorPoint]) -> list[tuple[str, str]]:
    """Contiguous (start_date, end_date) intervals where a 0/1 indicator
    series is 'on' (value >= 0.5). An interval ends at the first observation
    back below the threshold; an open final run ends at the last point."""
    intervals: list[tuple[str, str]] = []
    start: str | None = None
    for p in points:
        if p.value >= 0.5 and start is None:
            start = p.date
        elif p.value < 0.5 and start is not None:
            intervals.append((start, p.date))
            start = None
    if start is not None and points:
        intervals.append((start, points[-1].date))
    return intervals
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_econ_metrics.py -v`
Expected: PASS (all econ-metrics tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add backend/app/analysis/econ_metrics.py backend/tests/test_econ_metrics.py
git commit -m "feat(economics): add recession_intervals analysis function"
```

---

## Task 4: `get_recession_periods` — the FRED `USREC` provider helper

**Files:**
- Modify: `backend/app/providers/fred_provider.py`
- Modify: `backend/tests/test_fred_provider.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_fred_provider.py`:

```python
def test_get_recession_periods_derives_intervals(monkeypatch):
    from app.models import IndicatorPoint
    monkeypatch.setattr(fred_provider, "get_series", lambda sid, **kw: [
        IndicatorPoint(date="2020-01-01", value=0),
        IndicatorPoint(date="2020-02-01", value=1),
        IndicatorPoint(date="2020-03-01", value=0),
    ])
    periods = fred_provider.get_recession_periods()
    assert len(periods) == 1
    assert periods[0].start == "2020-02-01"
    assert periods[0].end == "2020-03-01"


def test_get_recession_periods_empty_on_failure(monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series", lambda sid, **kw: [])
    assert fred_provider.get_recession_periods() == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_fred_provider.py -v`
Expected: FAIL — `fred_provider` has no attribute `get_recession_periods`.

- [ ] **Step 3: Implement `get_recession_periods`**

In `backend/app/providers/fred_provider.py`, update the model import line:

```python
from app.models import IndicatorPoint, RecessionPeriod, ReleaseEvent
```

Add this import below the existing imports (after `from app.models import ...`):

```python
from app.analysis.econ_metrics import recession_intervals
```

Then append this function to the end of the file:

```python
def get_recession_periods() -> list[RecessionPeriod]:
    """NBER recession intervals derived from the FRED USREC series (a
    monthly 0/1 recession flag). [] on any failure."""
    points = get_series("USREC")
    return [RecessionPeriod(start=start, end=end)
            for start, end in recession_intervals(points)]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_fred_provider.py -v`
Expected: PASS (all fred-provider tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add backend/app/providers/fred_provider.py backend/tests/test_fred_provider.py
git commit -m "feat(economics): add get_recession_periods FRED helper"
```

---

## Task 5: `get_series` — optional `observation_start` parameter

So indicator drill-downs can request a bounded timeframe (1Y / 5Y / 10Y).

**Files:**
- Modify: `backend/app/providers/fred_provider.py`
- Modify: `backend/tests/test_fred_provider.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_fred_provider.py`:

```python
def test_get_series_passes_observation_start(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    captured = {}

    class CapturingHttpx:
        @staticmethod
        def get(url, params=None, timeout=None):
            captured.update(params or {})
            return FakeResponse({"observations": []})

    monkeypatch.setattr(fred_provider, "httpx", CapturingHttpx)
    fred_provider.get_series("CPIAUCSL", observation_start="2020-01-01")
    assert captured["observation_start"] == "2020-01-01"


def test_get_series_omits_observation_start_when_none(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    captured = {}

    class CapturingHttpx:
        @staticmethod
        def get(url, params=None, timeout=None):
            captured.update(params or {})
            return FakeResponse({"observations": []})

    monkeypatch.setattr(fred_provider, "httpx", CapturingHttpx)
    fred_provider.get_series("CPIAUCSL")
    assert "observation_start" not in captured
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_fred_provider.py -v`
Expected: FAIL — `get_series()` got an unexpected keyword argument `observation_start`.

- [ ] **Step 3: Add the `observation_start` parameter**

In `backend/app/providers/fred_provider.py`, replace the entire existing `get_series` function with:

```python
def get_series(series_id: str, units: str = "lin",
               observation_start: str | None = None) -> list[IndicatorPoint]:
    """Observations for a FRED series, oldest-first. [] on any failure.

    `units` is a FRED transform code applied server-side: "lin" (raw),
    "pc1" (percent change from a year ago), "pch" (percent change from the
    prior observation), "chg" (change from the prior observation).
    `observation_start` (ISO date), when given, bounds the returned window;
    FRED still computes transforms over the full underlying series.
    FRED encodes missing observations as ".", skipped here.
    """
    params = {"series_id": series_id, "sort_order": "asc", "units": units}
    if observation_start:
        params["observation_start"] = observation_start
    data = _get("series/observations", params)
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_fred_provider.py -v`
Expected: PASS (all fred-provider tests, old and new).

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add backend/app/providers/fred_provider.py backend/tests/test_fred_provider.py
git commit -m "feat(economics): support observation_start in get_series"
```

---

## Task 6: `build_indicator` — transform + range + recession periods

The drill-down builder gains an optional FRED `transform` (Level / YoY % / MoM %) and a `range_` timeframe, and includes NBER recession periods.

**Files:**
- Modify: `backend/app/services/economics_service.py`
- Modify: `backend/tests/test_economics_service.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_economics_service.py`:

```python
def test_build_indicator_applies_transform(db, monkeypatch):
    seen = {}

    def fake_get_series(sid, units="lin", observation_start=None):
        seen[sid] = units
        return _series(40)

    monkeypatch.setattr(fred_provider, "get_series", fake_get_series)
    monkeypatch.setattr(fred_provider, "get_recession_periods", lambda: [])
    detail = economics_service.build_indicator("UNRATE", transform="pc1")
    assert seen["UNRATE"] == "pc1"
    assert detail.unit == "%"        # pc1 always yields a percentage


def test_build_indicator_range_sets_observation_start(db, monkeypatch):
    seen = {}

    def fake_get_series(sid, units="lin", observation_start=None):
        seen[sid] = observation_start
        return _series(40)

    monkeypatch.setattr(fred_provider, "get_series", fake_get_series)
    monkeypatch.setattr(fred_provider, "get_recession_periods", lambda: [])
    economics_service.build_indicator("UNRATE", range_="5y")
    assert seen["UNRATE"] is not None        # a bounded window was requested
    economics_service.build_indicator("UNRATE", range_="max")
    assert seen["UNRATE"] is None            # max = full history


def test_build_indicator_includes_recession_periods(db, monkeypatch):
    from app.models import RecessionPeriod
    monkeypatch.setattr(fred_provider, "get_series",
                        lambda sid, **kw: _series(40))
    monkeypatch.setattr(
        fred_provider, "get_recession_periods",
        lambda: [RecessionPeriod(start="2020-02-01", end="2020-04-01")])
    detail = economics_service.build_indicator("UNRATE")
    assert len(detail.recession_periods) == 1
    assert detail.recession_periods[0].start == "2020-02-01"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_economics_service.py -v`
Expected: FAIL — `build_indicator()` got an unexpected keyword argument `transform`.

- [ ] **Step 3: Add the range/transform constants**

In `backend/app/services/economics_service.py`, add this directly below the `_BY_ID = {...}` line:

```python
# Drill-down timeframe range -> years of history (None = full series).
_RANGE_YEARS: dict[str, int | None] = {
    "1y": 1, "5y": 5, "10y": 10, "max": None,
}
# FRED transforms exposed by the drill-down toggle (Level / YoY % / MoM %).
_TRANSFORMS = {"lin", "pc1", "pch"}
```

- [ ] **Step 4: Add the `_observation_start` helper**

In `backend/app/services/economics_service.py`, add this directly below the `_now()` function (the `from datetime import datetime, timezone` import is already present from Task 2; add `date` and `timedelta` to it so the line reads `from datetime import date, datetime, timedelta, timezone`):

```python
def _observation_start(range_: str) -> str | None:
    """ISO start date for a drill-down range, or None for the full series."""
    years = _RANGE_YEARS.get(range_)
    if years is None:
        return None
    return (date.today() - timedelta(days=365 * years)).isoformat()
```

- [ ] **Step 5: Rewrite `build_indicator` with the new parameters**

In `backend/app/services/economics_service.py`, replace the entire `build_indicator` function (the version from Task 2) with:

```python
def build_indicator(series_id: str, transform: str | None = None,
                    range_: str = "max") -> IndicatorDetail | None:
    """Assemble the drill-down for one indicator. None if unknown/no data.

    `transform` overrides the FRED units ("lin"/"pc1"/"pch"); when omitted
    the indicator's native default is used. `range_` bounds the timeframe
    ("1y"/"5y"/"10y"/"max").
    """
    series_id = series_id.strip().upper()
    ind = _BY_ID.get(series_id)
    if ind is None:
        return None
    units = transform if transform in _TRANSFORMS else ind.fred_units
    points = provider.get_series(
        series_id, units=units, observation_start=_observation_start(range_))
    if len(points) < 2:
        return None
    points = _scale_points(points, _effective_scale(ind, units))
    values = [p.value for p in points]
    # pc1/pch always yield percentages; otherwise the indicator's own unit.
    unit = "%" if units in ("pc1", "pch") else ind.unit
    return IndicatorDetail(
        series_id=series_id, name=ind.name, unit=unit, series=points,
        latest=points[-1].value, change=em.period_change(values),
        yoy=em.yoy_change(points), range_low=min(values),
        range_high=max(values), momentum=em.momentum_score(values),
        recession_signals=_recession_signals(),
        recession_periods=provider.get_recession_periods(),
        updated_at=_now())
```

- [ ] **Step 6: Run the economics-service suite to verify it passes**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_economics_service.py -v`
Expected: PASS — the three new tests plus all existing service tests. (The existing `build_indicator` tests still pass: `get_series` is globally mocked, so the `get_recession_periods` → `get_series("USREC")` call resolves through the same mock.)

- [ ] **Step 7: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add backend/app/services/economics_service.py \
  backend/tests/test_economics_service.py
git commit -m "feat(economics): add transform, range, and recession periods to build_indicator"
```

---

## Task 7: `build_dashboard` — the categorized domain-page payload

**Files:**
- Modify: `backend/app/services/economics_service.py`
- Modify: `backend/tests/test_economics_service.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_economics_service.py`:

```python
def test_build_dashboard_groups_indicators_by_category(db, monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series",
                        lambda sid, **kw: _series(30))
    monkeypatch.setattr(fred_provider, "get_release_calendar", lambda: [])
    dash = economics_service.build_dashboard()
    assert [c.name for c in dash.categories] == economics_service.CATEGORY_ORDER
    total = sum(len(c.indicators) for c in dash.categories)
    assert total == len(economics_service.INDICATORS)   # all 20 resolved
    assert len(dash.recession_signals) == 2
    assert dash.updated_at


def test_build_dashboard_skips_failed_series(db, monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series", lambda sid, **kw: [])
    monkeypatch.setattr(fred_provider, "get_release_calendar", lambda: [])
    dash = economics_service.build_dashboard()
    # Still all six categories present, each empty — never a blank page.
    assert [c.name for c in dash.categories] == economics_service.CATEGORY_ORDER
    assert all(c.indicators == [] for c in dash.categories)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_economics_service.py -v`
Expected: FAIL — `economics_service` has no attribute `build_dashboard`.

- [ ] **Step 3: Implement `build_dashboard`**

In `backend/app/services/economics_service.py`, append this function to the end of the file:

```python
def build_dashboard() -> EconomicsDashboard:
    """Assemble the Economics domain page: every indicator grouped by
    category, the recession signals, and the release calendar."""
    by_category: dict[str, list[IndicatorSummary]] = {}
    for ind in INDICATORS:
        summary = _summarize(ind)
        if summary is not None:
            by_category.setdefault(ind.category, []).append(summary)
    categories = [
        IndicatorCategory(name=cat, indicators=by_category.get(cat, []))
        for cat in CATEGORY_ORDER
    ]
    return EconomicsDashboard(
        categories=categories, recession_signals=_recession_signals(),
        calendar=provider.get_release_calendar(), updated_at=_now())
```

- [ ] **Step 4: Run the economics-service suite to verify it passes**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_economics_service.py -v`
Expected: PASS (all service tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add backend/app/services/economics_service.py \
  backend/tests/test_economics_service.py
git commit -m "feat(economics): add build_dashboard categorized payload"
```

---

## Task 8: Routes — `/dashboard` endpoint + indicator transform/range params

**Files:**
- Modify: `backend/app/routes/economics.py`
- Modify: `backend/tests/test_economics_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_economics_routes.py`:

```python
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

    def fake_get_series(sid, units="lin", observation_start=None):
        seen[sid] = {"units": units, "observation_start": observation_start}
        return _series(40)

    monkeypatch.setattr(fred_provider, "get_series", fake_get_series)
    monkeypatch.setattr(fred_provider, "get_recession_periods", lambda: [])
    resp = client.get(
        "/api/economics/indicator/unrate?transform=pc1&range=5y")
    assert resp.status_code == 200
    assert seen["UNRATE"]["units"] == "pc1"
    assert seen["UNRATE"]["observation_start"] is not None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_economics_routes.py -v`
Expected: FAIL — `/api/economics/dashboard` returns 404; the transform test fails because the param is ignored.

- [ ] **Step 3: Update the routes**

Replace the entire contents of `backend/app/routes/economics.py` with:

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


@router.get("/dashboard")
def dashboard():
    """The Economics domain page: categorized indicators + recession + calendar."""
    return cache.get_or_compute("economics:dashboard",
                                economics_service.build_dashboard)


@router.get("/indicator/{series_id}")
def indicator(series_id: str, transform: str | None = None,
              range: str = "max"):
    """`transform` selects the FRED units (lin/pc1/pch); `range` the
    timeframe (1y/5y/10y/max)."""
    sid = series_id.strip().upper()
    key = f"economics:indicator:{sid}:{transform}:{range}"
    result = cache.get_or_compute(
        key, lambda: economics_service.build_indicator(
            series_id, transform=transform, range_=range))
    if result is None:
        raise HTTPException(status_code=404,
                            detail=f"No data for {series_id}")
    return result
```

- [ ] **Step 4: Run the routes suite to verify it passes**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_economics_routes.py -v`
Expected: PASS — the two new tests plus the three existing route tests.

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add backend/app/routes/economics.py backend/tests/test_economics_routes.py
git commit -m "feat(economics): add /dashboard route and indicator transform/range params"
```

---

## Task 9: Scheduler — warm the dashboard

**Files:**
- Modify: `backend/app/scheduler.py`
- Modify: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Update the failing test**

In `backend/tests/test_scheduler.py`, replace the entire existing `test_warm_economics_populates_cache` function with:

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
    assert cache.get("economics:dashboard") is not None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_scheduler.py::test_warm_economics_populates_cache -v`
Expected: FAIL — `cache.get("economics:dashboard")` is `None` (the job warms only the overview).

- [ ] **Step 3: Update `warm_economics`**

In `backend/app/scheduler.py`, replace the entire `warm_economics` function with:

```python
def warm_economics() -> None:
    """Recompute the Economics overview + dashboard and store them in cache."""
    try:
        cache.set("economics:overview", economics_service.build_overview())
        cache.set("economics:dashboard", economics_service.build_dashboard())
        logger.info("warmed economics:overview + economics:dashboard")
    except Exception:
        logger.warning("warm_economics failed", exc_info=True)
```

- [ ] **Step 4: Run the scheduler suite to verify it passes**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_scheduler.py -v`
Expected: PASS (all scheduler tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add backend/app/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat(economics): warm the dashboard payload on schedule"
```

---

## Final verification

After all 9 tasks, run the full backend suite:

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard/backend && PYTHONPATH=. .venv/bin/pytest
```

Every test must pass.

---

## Plan self-review notes

- **Spec coverage (§6.3):** expand `INDICATORS` to ~18 categorized → Task 2 (20 indicators, 6 categories). `build_dashboard()` → Task 7. `/api/economics/dashboard` route → Task 8. `indicator` `transform`/`range` params → Tasks 6, 8. `recession_periods` in the response → Tasks 1, 6. `fred_provider` `USREC` helper → Tasks 3, 4. New models `IndicatorCategory`/`EconomicsDashboard`/`RecessionPeriod` → Task 1. `IndicatorSummary.category` / `IndicatorDetail.recession_periods` → Task 1. `warm_economics` warms the dashboard → Task 9.
- **Deliberate scope decision:** the home-panel `build_overview` keeps a curated 6-indicator subset (`OVERVIEW_IDS`) rather than all 20 — the spec §2 non-goal says the calm four-quadrant home is unchanged. The full 20 appear only on the new `/economics` domain page via `build_dashboard`.
- **`scale`:** only `ICSA` (Initial Jobless Claims, a raw count) needs a display scale (×0.001 → thousands). `_effective_scale` ensures the scale applies only to `lin` data, never to FRED percent transforms. Out-of-the-box for any future raw-count series.
- **Type consistency:** `Indicator` fields (`series_id`, `name`, `unit`, `fred_units`, `category`, `scale`) are used identically in `_summarize`, `build_indicator`, `build_dashboard`. `_RANGE_YEARS` keys (`1y`/`5y`/`10y`/`max`) match the route `range` param and the planned frontend. `_TRANSFORMS` (`lin`/`pc1`/`pch`) matches the route `transform` param and the spec.
- **Backward compatibility:** `IndicatorSummary.category` and `IndicatorDetail.recession_periods` are defaulted, so existing constructions and fixtures stay valid. `/api/economics/overview` and the existing `/indicator/{id}` behavior are unchanged for callers that pass no new params.
- **Frontend (separate plan):** the `/economics` bento domain page, the enriched indicator drill-down (transform toggle, timeframe, compare overlay, recession shading) — covered by a following Economics frontend plan; this plan is backend-only and ships working, tested software on its own.
