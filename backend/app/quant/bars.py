"""Daily-bar warehouse for Quant Lab.

- `upsert_bars(symbol, df)`: idempotent write of a yfinance-shaped DataFrame
  into `bar_cache`. (symbol, date) is the PK; existing rows are replaced.
- `load_bars(symbols, start, end)`: long DataFrame from cache.
- `load_close_matrix(symbols, start, end)`: wide DataFrame (date × symbol)
  of adj_close, ready for vectorbt.
- `fetch_and_cache(symbols, start, end)`: top-level — checks the cache,
  downloads any missing date ranges per symbol via yfinance, upserts.
- `get_cached_dates(symbol)`: set of ISO dates already in cache.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf
from sqlalchemy import delete, insert, select

from app.database import bar_cache, get_engine

logger = logging.getLogger(__name__)


def _download_yf(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    """Thin wrapper around yfinance — split out for ease of mocking in tests."""
    return yf.download(
        tickers=symbols,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="ticker" if len(symbols) > 1 else "column",
        threads=True,
    )


def upsert_bars(symbol: str, df: pd.DataFrame) -> int:
    """Replace cached rows for `symbol` on every date in `df`.

    `df` is expected to be a yfinance-shaped DataFrame indexed by Timestamp
    with columns Open, High, Low, Close, Adj Close, Volume.
    Returns the number of rows written.
    """
    if df is None or df.empty:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    dates = [ts.strftime("%Y-%m-%d") for ts in df.index]
    rows = [
        {
            "symbol": symbol,
            "date": d,
            "open": float(df.iloc[i]["Open"]),
            "high": float(df.iloc[i]["High"]),
            "low": float(df.iloc[i]["Low"]),
            "close": float(df.iloc[i]["Close"]),
            "adj_close": float(df.iloc[i]["Adj Close"]),
            "volume": int(df.iloc[i]["Volume"]),
            "source": "yfinance",
            "fetched_at": now,
        }
        for i, d in enumerate(dates)
    ]
    with get_engine().begin() as conn:
        conn.execute(
            delete(bar_cache).where(
                (bar_cache.c.symbol == symbol)
                & (bar_cache.c.date.in_(dates))
            )
        )
        conn.execute(insert(bar_cache), rows)
    return len(rows)


def load_bars(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    """Long-format DataFrame of cached bars."""
    with get_engine().begin() as conn:
        result = conn.execute(
            select(bar_cache).where(
                bar_cache.c.symbol.in_(symbols)
                & (bar_cache.c.date >= start)
                & (bar_cache.c.date <= end)
            ).order_by(bar_cache.c.symbol, bar_cache.c.date)
        )
        rows = [dict(r._mapping) for r in result]
    if not rows:
        return pd.DataFrame(columns=[
            "date", "symbol", "open", "high", "low",
            "close", "adj_close", "volume", "source", "fetched_at",
        ])
    return pd.DataFrame(rows)


def load_close_matrix(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    """Wide DataFrame: rows = trading dates, columns = symbols, values = adj_close."""
    long = load_bars(symbols, start, end)
    if long.empty:
        return pd.DataFrame()
    wide = long.pivot(index="date", columns="symbol", values="adj_close")
    wide.index = pd.to_datetime(wide.index)
    wide = wide.sort_index().sort_index(axis=1)
    return wide


def get_cached_dates(symbol: str) -> set[str]:
    with get_engine().begin() as conn:
        result = conn.execute(
            select(bar_cache.c.date).where(bar_cache.c.symbol == symbol)
        )
        return {r[0] for r in result}


def fetch_and_cache(symbols: list[str], start: str, end: str) -> int:
    """Fill the cache for [start, end] across `symbols`. Downloads only when
    the cached coverage is missing the requested range for a symbol.

    Returns the number of rows written.
    """
    business_days = {ts.strftime("%Y-%m-%d") for ts in pd.bdate_range(start, end)}
    symbols_to_fetch = [
        s for s in symbols
        if not business_days.issubset(get_cached_dates(s))
    ]
    if not symbols_to_fetch:
        return 0

    written = 0
    CHUNK = 50
    for i in range(0, len(symbols_to_fetch), CHUNK):
        chunk = symbols_to_fetch[i:i + CHUNK]
        df = _download_yf(chunk, start=start, end=end)
        if df is None or df.empty:
            logger.warning("yfinance returned empty for chunk %s", chunk)
            continue
        for sym in chunk:
            try:
                sub = df[sym] if len(chunk) > 1 else df
                if sub is None or sub.empty:
                    continue
                sub = sub.dropna(subset=["Close", "Adj Close"])
                written += upsert_bars(sym, sub)
            except (KeyError, AttributeError):
                logger.warning("no data returned for %s in chunk %s", sym, chunk)
                continue
    return written
