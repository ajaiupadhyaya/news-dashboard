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
