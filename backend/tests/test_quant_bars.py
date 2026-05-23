from datetime import date
from unittest.mock import patch

import pandas as pd
from sqlalchemy import select

from app.database import bar_cache, get_engine
from app.quant.bars import upsert_bars, load_bars, get_cached_dates


def _fake_yf_df(symbol: str, start: str, end: str) -> pd.DataFrame:
    idx = pd.date_range(start=start, end=end, freq="B")
    return pd.DataFrame({
        "Open":      [100.0 + i for i in range(len(idx))],
        "High":      [101.0 + i for i in range(len(idx))],
        "Low":       [ 99.0 + i for i in range(len(idx))],
        "Close":     [100.5 + i for i in range(len(idx))],
        "Adj Close": [100.5 + i for i in range(len(idx))],
        "Volume":    [1_000_000 for _ in range(len(idx))],
    }, index=idx)


def test_upsert_bars_writes_to_cache(db):
    df = _fake_yf_df("SPY", "2026-01-02", "2026-01-09")
    upsert_bars("SPY", df)
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(bar_cache).where(bar_cache.c.symbol == "SPY")
        ).all()
    assert len(rows) == len(df)
    # Spot check the first row.
    first = rows[0]
    assert first.symbol == "SPY"
    assert first.close == df.iloc[0]["Close"]


def test_upsert_bars_is_idempotent(db):
    df = _fake_yf_df("SPY", "2026-01-02", "2026-01-09")
    upsert_bars("SPY", df)
    upsert_bars("SPY", df)   # re-run — must NOT duplicate rows
    with get_engine().begin() as conn:
        n = conn.execute(
            select(bar_cache).where(bar_cache.c.symbol == "SPY")
        ).all()
    assert len(n) == len(df)


def test_upsert_bars_updates_existing_row_when_close_changes(db):
    df = _fake_yf_df("SPY", "2026-01-02", "2026-01-09")
    upsert_bars("SPY", df)
    # Simulate yfinance returning a corrected adj_close
    df2 = df.copy()
    df2["Adj Close"] = df2["Adj Close"] + 0.5
    upsert_bars("SPY", df2)
    with get_engine().begin() as conn:
        row = conn.execute(
            select(bar_cache).where(
                (bar_cache.c.symbol == "SPY")
                & (bar_cache.c.date == df.index[0].strftime("%Y-%m-%d"))
            )
        ).first()
    assert row.adj_close == df2.iloc[0]["Adj Close"]


def test_load_bars_returns_long_dataframe(db):
    upsert_bars("SPY", _fake_yf_df("SPY", "2026-01-02", "2026-01-09"))
    upsert_bars("AAPL", _fake_yf_df("AAPL", "2026-01-02", "2026-01-09"))
    df = load_bars(["SPY", "AAPL"], start="2026-01-02", end="2026-01-09")
    # Columns: date, symbol, open, high, low, close, adj_close, volume
    assert set(df.columns) >= {"date", "symbol", "open", "high", "low",
                               "close", "adj_close", "volume"}
    assert set(df["symbol"].unique()) == {"SPY", "AAPL"}


def test_load_bars_pivot_close_helper(db):
    upsert_bars("SPY", _fake_yf_df("SPY", "2026-01-02", "2026-01-09"))
    upsert_bars("AAPL", _fake_yf_df("AAPL", "2026-01-02", "2026-01-09"))
    from app.quant.bars import load_close_matrix
    wide = load_close_matrix(["SPY", "AAPL"], start="2026-01-02", end="2026-01-09")
    # rows = dates, columns = symbols, values = adj_close
    assert list(wide.columns) == ["AAPL", "SPY"]
    assert wide.shape[0] == 6   # 6 business days Jan 2–9 2026


def test_get_cached_dates_returns_set(db):
    upsert_bars("SPY", _fake_yf_df("SPY", "2026-01-02", "2026-01-09"))
    d = get_cached_dates("SPY")
    assert "2026-01-02" in d
    assert isinstance(d, set)


def test_fetch_and_cache_uses_yfinance_when_missing(db):
    """fetch_and_cache should call yfinance only for missing dates."""
    from app.quant.bars import fetch_and_cache
    with patch("app.quant.bars._download_yf") as mocked:
        mocked.return_value = _fake_yf_df("SPY", "2026-01-02", "2026-01-09")
        fetch_and_cache(["SPY"], start="2026-01-02", end="2026-01-09")
        assert mocked.called
    # Second call should hit the cache and NOT re-download (start/end cover same range).
    with patch("app.quant.bars._download_yf") as mocked:
        fetch_and_cache(["SPY"], start="2026-01-02", end="2026-01-09")
        assert not mocked.called
