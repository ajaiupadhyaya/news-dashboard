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
