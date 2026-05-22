# Finance Enrichment — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the backend for the enriched Finance domain — technical indicators (RSI, MACD, Bollinger Bands, period returns), a multi-asset markets endpoint with top movers, and timeframe support on the instrument endpoint.

**Architecture:** Purely additive, mirroring the existing Finance backend. New pure analysis functions in `analysis/metrics.py` (TDD'd); new pydantic models; `finance_service` gains `build_markets()` and an enriched `build_instrument()`; `routes/finance.py` gains `/api/finance/markets` and a `range` param; a `warm_markets` scheduler job. No new data sources — yfinance only.

**Tech Stack:** FastAPI, SQLAlchemy, yfinance, APScheduler, pydantic, pytest.

**Spec:** `docs/superpowers/specs/2026-05-22-finance-economics-enrichment-design.md` (§5)

**Scope note:** This is Plan 1a of the Finance & Economics enrichment. It is the Finance **backend**; the Finance **frontend** (shared UI foundations, the domain page, the enriched drill-down) is the next plan. Timeframe ranges are **daily-interval only** (`1mo`/`3mo`/`6mo`/`1y`/`5y`/`max`) — intraday (1D/1W) is deferred because yfinance intraday bars need sub-day timestamp handling across `Bar`, persistence, and chart keys.

**Conventions** (verified against the codebase):
- Tests run from `backend/`: `pytest tests/<file> -v`. The `db` fixture (`tests/conftest.py`) gives a fresh temp SQLite DB; `_clear_cache` is autouse.
- `analysis/metrics.py` holds pure functions (no I/O); `econ_metrics.py` already imports `from app.models import IndicatorPoint`, so importing `Bar` into `metrics.py` follows precedent.
- Providers expose one mockable seam; services degrade per-symbol.
- Commit messages: `feat(backend): …`.

---

## Task 1: RSI analysis function

**Files:**
- Modify: `backend/app/analysis/metrics.py`
- Test: `backend/tests/test_metrics.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_metrics.py`:

```python
def test_rsi_all_gains_is_100():
    rising = [float(i) for i in range(1, 40)]
    out = metrics.rsi(rising, period=14)
    assert out[:14] == [None] * 14          # not enough deltas yet
    assert out[14] == 100.0                 # only gains -> RSI 100
    assert out[-1] == 100.0


def test_rsi_all_losses_is_zero():
    falling = [float(i) for i in range(40, 1, -1)]
    out = metrics.rsi(falling, period=14)
    assert out[-1] == 0.0


def test_rsi_short_series_is_all_none():
    assert metrics.rsi([1.0, 2.0, 3.0], period=14) == [None, None, None]
```

Note: `test_metrics.py` already imports `metrics` (`from app.analysis import metrics`).

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_metrics.py::test_rsi_all_gains_is_100 -v`
Expected: FAIL — `module 'app.analysis.metrics' has no attribute 'rsi'`.

- [ ] **Step 3: Implement RSI**

Append to `backend/app/analysis/metrics.py`:

```python
def rsi(prices: list[float], period: int = 14) -> list[float | None]:
    """Wilder's Relative Strength Index, aligned to `prices`.

    The first `period` entries are None (not enough price changes yet).
    100.0 when there are no losses in the window, 0.0 when no gains.
    """
    n = len(prices)
    out: list[float | None] = [None] * n
    if n <= period:
        return out

    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, n):
        delta = prices[i] - prices[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    def _rsi(avg_gain: float, avg_loss: float) -> float:
        if avg_loss == 0.0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100.0 - 100.0 / (1.0 + rs), 4)

    # gains[k] is the change into prices[k + 1]; the first average covers
    # gains[0:period] -> the first RSI value aligns to prices[period].
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out[period] = _rsi(avg_gain, avg_loss)
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        out[i] = _rsi(avg_gain, avg_loss)
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_metrics.py -v`
Expected: PASS — all metrics tests green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/analysis/metrics.py backend/tests/test_metrics.py
git commit -m "feat(backend): add RSI analysis function"
```

---

## Task 2: MACD analysis function

**Files:**
- Modify: `backend/app/analysis/metrics.py`
- Test: `backend/tests/test_metrics.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_metrics.py`:

```python
def test_macd_shapes_and_alignment():
    prices = [float(i) for i in range(60)]
    m = metrics.macd(prices)
    assert set(m.keys()) == {"macd", "signal", "histogram"}
    assert len(m["macd"]) == 60
    assert m["macd"][:25] == [None] * 25          # None until slow EMA fills
    assert m["macd"][25] is not None
    assert m["signal"][-1] is not None
    assert m["histogram"][-1] is not None


def test_macd_short_series_is_all_none():
    m = metrics.macd([1.0, 2.0, 3.0])
    assert m["macd"] == [None, None, None]
    assert m["signal"] == [None, None, None]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_metrics.py::test_macd_shapes_and_alignment -v`
Expected: FAIL — `module 'app.analysis.metrics' has no attribute 'macd'`.

- [ ] **Step 3: Implement MACD**

Append to `backend/app/analysis/metrics.py`:

```python
def _ema(values: list[float], period: int) -> list[float]:
    """Exponential moving average, seeded with the first value."""
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1.0 - k))
    return out


def macd(prices: list[float], fast: int = 12, slow: int = 26,
         signal: int = 9) -> dict[str, list[float | None]]:
    """MACD line, signal line, and histogram, each aligned to `prices`.

    Entries before the slow EMA has filled (`slow - 1`) are None. Returns a
    dict with keys "macd", "signal", "histogram".
    """
    n = len(prices)
    empty: list[float | None] = [None] * n
    if n < slow:
        return {"macd": empty[:], "signal": empty[:], "histogram": empty[:]}

    ema_fast = _ema(prices, fast)
    ema_slow = _ema(prices, slow)
    macd_line: list[float | None] = [None] * n
    for i in range(slow - 1, n):
        macd_line[i] = round(ema_fast[i] - ema_slow[i], 4)

    defined = [m for m in macd_line if m is not None]
    sig = _ema(defined, signal)
    signal_line: list[float | None] = [None] * n
    histogram: list[float | None] = [None] * n
    for offset, i in enumerate(range(slow - 1, n)):
        signal_line[i] = round(sig[offset], 4)
        histogram[i] = round((macd_line[i] or 0.0) - sig[offset], 4)
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_metrics.py -v`
Expected: PASS — all metrics tests green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/analysis/metrics.py backend/tests/test_metrics.py
git commit -m "feat(backend): add MACD analysis function"
```

---

## Task 3: Bollinger Bands analysis function

**Files:**
- Modify: `backend/app/analysis/metrics.py`
- Test: `backend/tests/test_metrics.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_metrics.py`:

```python
def test_bollinger_bands_constant_series():
    bb = metrics.bollinger_bands([5.0] * 30, period=20)
    assert set(bb.keys()) == {"upper", "middle", "lower"}
    assert bb["upper"][:19] == [None] * 19      # None until the window fills
    assert bb["middle"][-1] == 5.0
    assert bb["upper"][-1] == 5.0               # zero variance -> bands collapse
    assert bb["lower"][-1] == 5.0


def test_bollinger_bands_rising_series_spreads():
    bb = metrics.bollinger_bands([float(i) for i in range(40)], period=20)
    assert bb["upper"][-1] > bb["middle"][-1] > bb["lower"][-1]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_metrics.py::test_bollinger_bands_constant_series -v`
Expected: FAIL — `module 'app.analysis.metrics' has no attribute 'bollinger_bands'`.

- [ ] **Step 3: Implement Bollinger Bands**

Append to `backend/app/analysis/metrics.py`:

```python
def bollinger_bands(prices: list[float], period: int = 20,
                    mult: float = 2.0) -> dict[str, list[float | None]]:
    """Bollinger Bands aligned to `prices`. The middle band is the SMA;
    the upper/lower bands are `mult` population standard deviations away.
    Entries before the window fills are None."""
    n = len(prices)
    upper: list[float | None] = [None] * n
    middle: list[float | None] = [None] * n
    lower: list[float | None] = [None] * n
    for i in range(period - 1, n):
        window = prices[i - period + 1: i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        sd = sqrt(variance)
        middle[i] = round(mean, 4)
        upper[i] = round(mean + mult * sd, 4)
        lower[i] = round(mean - mult * sd, 4)
    return {"upper": upper, "middle": middle, "lower": lower}
```

Note: `metrics.py` already imports `from math import sqrt`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_metrics.py -v`
Expected: PASS — all metrics tests green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/analysis/metrics.py backend/tests/test_metrics.py
git commit -m "feat(backend): add Bollinger Bands analysis function"
```

---

## Task 4: Period-returns analysis function

**Files:**
- Modify: `backend/app/analysis/metrics.py`
- Test: `backend/tests/test_metrics.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_metrics.py`:

```python
def test_period_returns():
    from app.models import Bar

    # 260 daily bars, all 2026, every close 100.0 except the last at 110.0.
    bars = [
        Bar(date=f"2026-{i // 28 % 12 + 1:02d}-{i % 28 + 1:02d}",
            open=100.0, high=100.0, low=100.0, close=100.0, volume=1)
        for i in range(259)
    ]
    bars.append(Bar(date="2026-12-28", open=110.0, high=110.0, low=110.0,
                    close=110.0, volume=1))
    r = metrics.period_returns(bars)
    assert r["week_1"] == 10.0           # 110 / 100 - 1
    assert r["month_1"] == 10.0
    assert r["year_1"] == 10.0
    assert r["year_3"] is None           # only 260 bars, < 756
    assert r["ytd"] == 10.0


def test_period_returns_empty():
    r = metrics.period_returns([])
    assert all(v is None for v in r.values())
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_metrics.py::test_period_returns -v`
Expected: FAIL — `module 'app.analysis.metrics' has no attribute 'period_returns'`.

- [ ] **Step 3: Implement period_returns**

Add the import at the top of `backend/app/analysis/metrics.py` (after the existing `from math import sqrt`):

```python
import statistics
from math import sqrt

from app.models import Bar
```

Append to `backend/app/analysis/metrics.py`:

```python
def period_returns(bars: list[Bar]) -> dict[str, float | None]:
    """Total percent return over standard lookbacks, plus year-to-date.

    Lookbacks are in trading days (≈ 5/21/63/126/252/756). A return is
    None when there is not enough history. Keys match the `Returns` model.
    """
    closes = [b.close for b in bars]
    n = len(closes)
    latest = closes[-1] if closes else None

    def _ret(lookback: int) -> float | None:
        if latest is None or n <= lookback:
            return None
        base = closes[-lookback - 1]
        return round((latest / base - 1.0) * 100.0, 4) if base else None

    result: dict[str, float | None] = {
        "week_1": _ret(5), "month_1": _ret(21), "month_3": _ret(63),
        "month_6": _ret(126), "year_1": _ret(252), "year_3": _ret(756),
        "ytd": None,
    }
    if bars and latest is not None:
        year = bars[-1].date[:4]
        base = next((b.close for b in bars if b.date[:4] == year), None)
        if base:
            result["ytd"] = round((latest / base - 1.0) * 100.0, 4)
    return result
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_metrics.py -v`
Expected: PASS — all metrics tests green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/analysis/metrics.py backend/tests/test_metrics.py
git commit -m "feat(backend): add period-returns analysis function"
```

---

## Task 5: Markets and technical-indicator models

**Files:**
- Modify: `backend/app/models.py`
- Test: `backend/tests/test_models.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_models.py`:

```python
def test_technicals_new_fields_default_empty():
    from app.models import Technicals
    t = Technicals(sma_20=[1.0], sma_50=[None], sma_200=[None])
    assert t.rsi == []
    assert t.macd_line == []
    assert t.bb_upper == []
    assert t.volume == []


def test_returns_model():
    from app.models import Returns
    r = Returns(week_1=1.5, ytd=3.0)
    assert r.week_1 == 1.5
    assert r.ytd == 3.0
    assert r.year_3 is None


def test_markets_response_model():
    from app.models import (AssetClass, Breadth, MarketsResponse, Mover,
                            SectorChange, WatchlistQuote)
    markets = MarketsResponse(
        asset_classes=[AssetClass(label="Crypto", symbol="BTC-USD",
                                  price=1.0, change_pct=2.0,
                                  sparkline=[1.0, 2.0])],
        indices=[WatchlistQuote(symbol="^GSPC", price=1.0, change=0.1,
                                change_pct=1.0, volume=1,
                                as_of="2026-01-02", sparkline=[1.0])],
        gainers=[Mover(symbol="AAA", price=2.0, change_pct=9.0)],
        losers=[Mover(symbol="BBB", price=2.0, change_pct=-9.0)],
        sectors=[SectorChange(symbol="XLK", name="Tech", change_pct=1.0)],
        breadth=Breadth(advancers=1, decliners=1, unchanged=0,
                        advance_decline_ratio=1.0),
        updated_at="2026-01-02T00:00:00Z")
    assert markets.asset_classes[0].label == "Crypto"
    assert markets.gainers[0].change_pct == 9.0
    assert markets.losers[0].symbol == "BBB"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_models.py::test_returns_model -v`
Expected: FAIL — `cannot import name 'Returns'`.

- [ ] **Step 3: Extend `Technicals` and `InstrumentResponse`**

In `backend/app/models.py`, replace the existing `Technicals` class with:

```python
class Technicals(BaseModel):
    sma_20: list[float | None]
    sma_50: list[float | None]
    sma_200: list[float | None]
    # Enrichment fields — default empty so existing constructions stay valid.
    rsi: list[float | None] = []
    macd_line: list[float | None] = []
    macd_signal: list[float | None] = []
    macd_histogram: list[float | None] = []
    bb_upper: list[float | None] = []
    bb_middle: list[float | None] = []
    bb_lower: list[float | None] = []
    volume: list[int] = []
```

Add the `Returns` model immediately before `InstrumentResponse`:

```python
class Returns(BaseModel):
    week_1: float | None = None
    month_1: float | None = None
    month_3: float | None = None
    month_6: float | None = None
    ytd: float | None = None
    year_1: float | None = None
    year_3: float | None = None
```

In the `InstrumentResponse` class, add the `returns` field after `stats`:

```python
class InstrumentResponse(BaseModel):
    symbol: str
    profile: Fundamentals
    bars: list[Bar]
    technicals: Technicals
    stats: InstrumentStats
    returns: Returns = Returns()
    updated_at: str
```

- [ ] **Step 4: Append the markets models**

Append to the end of `backend/app/models.py`:

```python
class AssetClass(BaseModel):
    label: str          # "Equities", "Crypto", "Commodities", "Rates", "FX"
    symbol: str
    price: float
    change_pct: float
    sparkline: list[float]


class Mover(BaseModel):
    symbol: str
    price: float
    change_pct: float


class MarketsResponse(BaseModel):
    asset_classes: list[AssetClass]
    indices: list[WatchlistQuote]
    gainers: list[Mover]
    losers: list[Mover]
    sectors: list[SectorChange]
    breadth: Breadth
    updated_at: str
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: PASS — every model test green, including the existing
`test_instrument_response_assembles` (the new fields all have defaults).

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py backend/tests/test_models.py
git commit -m "feat(backend): add markets and technical-indicator models"
```

---

## Task 6: `build_markets` service function

**Files:**
- Modify: `backend/app/services/finance_service.py`
- Test: `backend/tests/test_finance_service.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_finance_service.py`:

```python
def test_build_markets_assembles(db, monkeypatch):
    from app.models import Quote

    monkeypatch.setattr(yfinance_provider, "get_history",
                        lambda *a, **k: _bars([100.0, 101.0, 102.0]))
    monkeypatch.setattr(yfinance_provider, "get_quote",
                        lambda sym: Quote(symbol=sym, price=10.0, change=0.5,
                                          change_pct=5.0, volume=1,
                                          as_of="2026-01-03"))
    markets = finance_service.build_markets()
    assert len(markets.asset_classes) == len(finance_service.ASSET_CLASSES)
    assert len(markets.indices) == len(finance_service.INDICES)
    assert len(markets.gainers) == 5
    assert len(markets.losers) == 5
    assert markets.asset_classes[0].sparkline          # non-empty
    assert markets.updated_at


def test_build_markets_skips_failed_symbols(db, monkeypatch):
    # Every fetch fails -> empty-but-valid payload (per-symbol isolation).
    monkeypatch.setattr(yfinance_provider, "get_history", lambda *a, **k: [])
    monkeypatch.setattr(yfinance_provider, "get_quote", lambda sym: None)
    markets = finance_service.build_markets()
    assert markets.asset_classes == []
    assert markets.gainers == []
    assert markets.updated_at
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_finance_service.py::test_build_markets_assembles -v`
Expected: FAIL — `module 'app.services.finance_service' has no attribute 'build_markets'`.

- [ ] **Step 3: Implement `build_markets`**

In `backend/app/services/finance_service.py`, extend the models import to add the new types:

```python
from app.models import (AssetClass, Breadth, Fundamentals, InstrumentResponse,
                        InstrumentStats, MarketsResponse, Mover,
                        OverviewResponse, Returns, SectorChange, Technicals,
                        WatchlistQuote)
```

(Replace the existing `from app.models import (...)` line with the above.)

Add these module-level constants after the existing `SECTORS` list:

```python
# Representative ticker for each asset-class tile on the Finance domain page.
ASSET_CLASSES = [
    ("Equities", "^GSPC"),
    ("Crypto", "BTC-USD"),
    ("Commodities", "GC=F"),
    ("Rates", "^TNX"),
    ("FX", "DX-Y.NYB"),
]

# Large-cap universe screened for the day's top movers.
MOVERS_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "TSLA",
    "BRK-B", "LLY", "JPM", "V", "XOM", "UNH", "MA", "COST", "HD", "PG",
    "JNJ", "ABBV", "NFLX", "BAC", "KO", "CRM", "CVX", "MRK", "AMD", "PEP",
    "WMT", "ADBE", "ORCL", "TMO", "ACN", "MCD", "CSCO", "ABT", "QCOM",
    "DIS", "WFC", "INTC",
]
```

Append this function to `backend/app/services/finance_service.py`:

```python
def build_markets() -> MarketsResponse:
    """Assemble the Finance domain page: asset classes, indices, movers,
    sectors, breadth. Per-symbol isolation — a failed fetch is skipped."""
    asset_classes: list[AssetClass] = []
    for label, sym in ASSET_CLASSES:
        bars = provider.get_history(sym, period="1mo", interval="1d")
        if len(bars) < 2:
            continue
        last, prev = bars[-1], bars[-2]
        change_pct = (round((last.close - prev.close) / prev.close * 100, 4)
                      if prev.close else 0.0)
        asset_classes.append(AssetClass(
            label=label, symbol=sym, price=last.close, change_pct=change_pct,
            sparkline=metrics.downsample([b.close for b in bars], 24)))

    indices: list[WatchlistQuote] = []
    for sym, _ in INDICES:
        bars = provider.get_history(sym, period="1mo", interval="1d")
        if len(bars) < 2:
            continue
        last, prev = bars[-1], bars[-2]
        change = round(last.close - prev.close, 4)
        change_pct = (round(change / prev.close * 100, 4)
                      if prev.close else 0.0)
        indices.append(WatchlistQuote(
            symbol=sym, price=last.close, change=change,
            change_pct=change_pct, volume=last.volume, as_of=last.date,
            sparkline=metrics.downsample([b.close for b in bars], 24)))

    movers: list[Mover] = []
    for sym in MOVERS_UNIVERSE:
        quote = provider.get_quote(sym)
        if quote:
            movers.append(Mover(symbol=quote.symbol, price=quote.price,
                                change_pct=quote.change_pct))
    gainers = sorted(movers, key=lambda m: m.change_pct, reverse=True)[:5]
    losers = sorted(movers, key=lambda m: m.change_pct)[:5]

    sectors: list[SectorChange] = []
    for sym, name in SECTORS:
        quote = provider.get_quote(sym)
        if quote:
            sectors.append(SectorChange(symbol=sym, name=name,
                                        change_pct=quote.change_pct))

    all_changes = ([a.change_pct for a in asset_classes]
                   + [i.change_pct for i in indices]
                   + [m.change_pct for m in movers]
                   + [s.change_pct for s in sectors])
    breadth = Breadth(**metrics.breadth(all_changes))

    return MarketsResponse(asset_classes=asset_classes, indices=indices,
                           gainers=gainers, losers=losers, sectors=sectors,
                           breadth=breadth, updated_at=_now())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_finance_service.py -v`
Expected: PASS — all finance-service tests green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/finance_service.py backend/tests/test_finance_service.py
git commit -m "feat(backend): add build_markets service function"
```

---

## Task 7: Enriched `build_instrument` — timeframe range, technicals, returns

**Files:**
- Modify: `backend/app/services/finance_service.py`
- Test: `backend/tests/test_finance_service.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_finance_service.py`:

```python
def test_build_instrument_includes_rich_technicals_and_returns(db, monkeypatch):
    closes = [100.0 + i for i in range(60)]
    monkeypatch.setattr(yfinance_provider, "get_history",
                        lambda *a, **k: _bars(closes))
    monkeypatch.setattr(yfinance_provider, "get_fundamentals",
                        lambda sym: Fundamentals(symbol=sym, name="Test Co"))
    result = finance_service.build_instrument("AAPL", "1y")
    assert result is not None
    assert len(result.technicals.rsi) == 60
    assert len(result.technicals.volume) == 60
    assert len(result.technicals.macd_line) == 60
    assert result.technicals.bb_middle[-1] is not None
    assert result.returns is not None


def test_build_instrument_range_maps_to_period(db, monkeypatch):
    seen = {}

    def _capture(symbol, period="1y", interval="1d"):
        seen["period"], seen["interval"] = period, interval
        return _bars([100.0 + i for i in range(30)])

    monkeypatch.setattr(yfinance_provider, "get_history", _capture)
    monkeypatch.setattr(yfinance_provider, "get_fundamentals",
                        lambda sym: None)
    finance_service.build_instrument("AAPL", "5y")
    assert seen == {"period": "5y", "interval": "1d"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_finance_service.py::test_build_instrument_includes_rich_technicals_and_returns -v`
Expected: FAIL — `AttributeError`/empty list (`technicals.rsi` is `[]`).

- [ ] **Step 3: Rewrite `build_instrument`**

In `backend/app/services/finance_service.py`, add this constant after the `MOVERS_UNIVERSE` constant:

```python
# Timeframe range -> (yfinance period, interval). Daily interval only.
_RANGE_MAP = {
    "1mo": ("1mo", "1d"),
    "3mo": ("3mo", "1d"),
    "6mo": ("6mo", "1d"),
    "1y": ("1y", "1d"),
    "5y": ("5y", "1d"),
    "max": ("max", "1d"),
}
```

Replace the entire existing `build_instrument` function with:

```python
def build_instrument(symbol: str,
                     range_: str = "1y") -> InstrumentResponse | None:
    """Assemble the drill-down for one instrument over the given timeframe
    range: bars, technicals (SMA/RSI/MACD/Bollinger/volume), stats,
    returns, and the fundamentals profile. None when there is no data."""
    symbol = symbol.strip().upper()
    period, interval = _RANGE_MAP.get(range_, ("1y", "1d"))
    bars = provider.get_history(symbol, period=period, interval=interval)
    if not bars:
        return None
    try:
        save_ohlcv(symbol, bars)
    except Exception as exc:
        logger.warning("save_ohlcv(%s) failed — skipping persistence: %s",
                       symbol, exc)

    closes = [b.close for b in bars]
    profile = (provider.get_fundamentals(symbol)
               or Fundamentals(symbol=symbol, name=symbol))

    macd_data = metrics.macd(closes)
    bb = metrics.bollinger_bands(closes)
    technicals = Technicals(
        sma_20=metrics.sma(closes, 20),
        sma_50=metrics.sma(closes, 50),
        sma_200=metrics.sma(closes, 200),
        rsi=metrics.rsi(closes),
        macd_line=macd_data["macd"],
        macd_signal=macd_data["signal"],
        macd_histogram=macd_data["histogram"],
        bb_upper=bb["upper"],
        bb_middle=bb["middle"],
        bb_lower=bb["lower"],
        volume=[b.volume for b in bars])

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
    returns = Returns(**metrics.period_returns(bars))

    return InstrumentResponse(symbol=symbol, profile=profile, bars=bars,
                              technicals=technicals, stats=stats,
                              returns=returns, updated_at=_now())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_finance_service.py -v`
Expected: PASS — all finance-service tests green, including the existing
`test_build_instrument_*` tests (they call `build_instrument` with no range,
so `range_` defaults to `"1y"`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/finance_service.py backend/tests/test_finance_service.py
git commit -m "feat(backend): enrich build_instrument with ranges, technicals, returns"
```

---

## Task 8: Markets route + instrument `range` param

**Files:**
- Modify: `backend/app/routes/finance.py`
- Test: `backend/tests/test_finance_routes.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_finance_routes.py`:

```python
def test_markets_endpoint(db, monkeypatch):
    monkeypatch.setattr(yfinance_provider, "get_history",
                        lambda *a, **k: _bars([100.0, 101.0, 102.0]))
    monkeypatch.setattr(yfinance_provider, "get_quote",
                        lambda sym: Quote(symbol=sym, price=10.0, change=0.5,
                                          change_pct=3.0, volume=1,
                                          as_of="2026-01-03"))
    resp = client.get("/api/finance/markets")
    assert resp.status_code == 200
    body = resp.json()
    assert "asset_classes" in body
    assert "gainers" in body and "losers" in body
    assert "breadth" in body and "updated_at" in body


def test_instrument_endpoint_accepts_range(db, monkeypatch):
    seen = {}

    def _capture(symbol, period="1y", interval="1d"):
        seen["period"] = period
        return _bars([100.0 + i for i in range(30)])

    monkeypatch.setattr(yfinance_provider, "get_history", _capture)
    monkeypatch.setattr(yfinance_provider, "get_fundamentals",
                        lambda sym: Fundamentals(symbol=sym, name="Test Co"))
    resp = client.get("/api/finance/instrument/aapl?range=5y")
    assert resp.status_code == 200
    assert seen["period"] == "5y"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_finance_routes.py::test_markets_endpoint -v`
Expected: FAIL — 404 for `/api/finance/markets`.

- [ ] **Step 3: Update the routes**

Replace the entire contents of `backend/app/routes/finance.py` with:

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


@router.get("/markets")
def markets():
    """The Finance domain page: asset classes, indices, movers, breadth."""
    return cache.get_or_compute("finance:markets", finance_service.build_markets)


@router.get("/instrument/{symbol}")
def instrument(symbol: str, range: str = "1y"):
    """`range` selects the timeframe — 1mo/3mo/6mo/1y/5y/max."""
    key = f"finance:instrument:{symbol.strip().upper()}:{range}"
    result = cache.get_or_compute(
        key, lambda: finance_service.build_instrument(symbol, range))
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return result
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_finance_routes.py -v`
Expected: PASS — all finance-route tests green, including the existing
`test_instrument_endpoint` (no `range` → defaults to `1y`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/finance.py backend/tests/test_finance_routes.py
git commit -m "feat(backend): add markets route and instrument range param"
```

---

## Task 9: `warm_markets` scheduler job

**Files:**
- Modify: `backend/app/scheduler.py`
- Test: `backend/tests/test_scheduler.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_scheduler.py`:

```python
def test_warm_markets_populates_cache(db, monkeypatch):
    from app.cache import cache
    from app.models import Bar, Quote
    from app.providers import yfinance_provider

    monkeypatch.setattr(
        yfinance_provider, "get_history",
        lambda *a, **k: [Bar(date="2026-01-02", open=1, high=2, low=1,
                              close=1.5, volume=10),
                         Bar(date="2026-01-03", open=1, high=2, low=1,
                             close=1.6, volume=10)])
    monkeypatch.setattr(
        yfinance_provider, "get_quote",
        lambda sym: Quote(symbol=sym, price=1.0, change=0.0, change_pct=0.0,
                          volume=1, as_of="2026-01-03"))
    scheduler.warm_markets()
    assert cache.get("finance:markets") is not None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_scheduler.py::test_warm_markets_populates_cache -v`
Expected: FAIL — `module 'app.scheduler' has no attribute 'warm_markets'`.

- [ ] **Step 3: Add the job**

In `backend/app/scheduler.py`, add the `warm_markets` function immediately
after `warm_overview`:

```python
def warm_markets() -> None:
    """Recompute the Finance markets page and store it in the cache."""
    try:
        cache.set("finance:markets", finance_service.build_markets())
        logger.info("warmed finance:markets")
    except Exception:
        logger.warning("warm_markets failed", exc_info=True)
```

In `start_scheduler()`, register the job after the `warm_overview` job:

```python
    sched.add_job(warm_overview, "interval", minutes=10, id="warm_overview",
                  max_instances=1, coalesce=True)
    sched.add_job(warm_markets, "interval", minutes=10, id="warm_markets",
                  max_instances=1, coalesce=True)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_scheduler.py -v`
Expected: PASS — all scheduler tests green.

- [ ] **Step 5: Run the full backend suite**

Run: `pytest -q`
Expected: PASS — every backend test green (Phases 1 + 2 + Finance enrichment).

- [ ] **Step 6: Commit**

```bash
git add backend/app/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat(backend): add warm_markets scheduler job"
```

---

## Final Verification

After all 9 tasks:

- [ ] From `backend/`, run `pytest -q` — every test green.
- [ ] Spot-check the new endpoint locally if desired: `uvicorn app.main:app` then
      `GET http://127.0.0.1:8000/api/finance/markets` (returns an empty-but-valid
      payload offline, real data with network).
- [ ] Dispatch the final holistic code review, then proceed to
      `superpowers:finishing-a-development-branch`.

Then the **Finance frontend** plan (shared UI foundations, the bento domain page,
the enriched instrument drill-down) is written and built next.

---

## Notes for the Implementer

- **Backward compatibility:** every new `Technicals` field and `InstrumentResponse.returns`
  has a default, so the existing `test_instrument_response_assembles` and the live
  frontend (which ignores unknown JSON fields) keep working. This backend plan ships
  independently without touching the frontend.
- **Range scope:** ranges are daily-interval only (`1mo`/`3mo`/`6mo`/`1y`/`5y`/`max`).
  An unknown `range` value falls back to `("1y", "1d")` — never an error.
- **Per-symbol isolation:** `build_markets` must never raise because one ticker
  failed — a failed `get_history`/`get_quote` is skipped, exactly as `build_overview`
  already does.
- **`range` as a param name** in the route shadows the Python builtin within that
  function only; this is intentional for the clean `?range=` query API.
