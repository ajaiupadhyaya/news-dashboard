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
