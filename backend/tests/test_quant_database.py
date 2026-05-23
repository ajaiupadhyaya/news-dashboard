from datetime import date

from sqlalchemy import insert, select

from app.database import bar_cache, get_engine


def test_bar_cache_insert_and_read(db):
    with get_engine().begin() as conn:
        conn.execute(insert(bar_cache).values(
            symbol="SPY", date="2026-01-02",
            open=470.0, high=472.5, low=469.0, close=471.2, adj_close=471.2,
            volume=80_000_000, source="yfinance",
            fetched_at="2026-01-02T22:00:00Z",
        ))
        row = conn.execute(
            select(bar_cache).where(bar_cache.c.symbol == "SPY")
        ).first()
    assert row.close == 471.2
    assert row.adj_close == 471.2
    assert row.source == "yfinance"


def test_bar_cache_primary_key_is_symbol_date(db):
    with get_engine().begin() as conn:
        conn.execute(insert(bar_cache).values(
            symbol="SPY", date="2026-01-02", open=1, high=1, low=1, close=1,
            adj_close=1, volume=1, source="yfinance", fetched_at="x",
        ))
        # Re-inserting the same (symbol, date) must violate the PK.
        import pytest
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            conn.execute(insert(bar_cache).values(
                symbol="SPY", date="2026-01-02", open=2, high=2, low=2, close=2,
                adj_close=2, volume=2, source="yfinance", fetched_at="x",
            ))
