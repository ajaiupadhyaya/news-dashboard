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
