import logging
from datetime import datetime, timezone

from app.analysis import metrics
from app.config import get_settings
from app.database import save_ohlcv
from app.models import (AssetClass, Breadth, Fundamentals, InstrumentResponse,
                        InstrumentStats, MarketsResponse, Mover,
                        OverviewResponse, Returns, SectorChange, Technicals,
                        WatchlistQuote)
from app.providers import yfinance_provider as provider
from app.store import get_watchlist

logger = logging.getLogger(__name__)

INDICES = [("^GSPC", "S&P 500"), ("^DJI", "Dow Jones"), ("^IXIC", "Nasdaq"),
           ("^RUT", "Russell 2000"), ("^VIX", "VIX")]

SECTORS = [("XLK", "Technology"), ("XLF", "Financials"), ("XLE", "Energy"),
           ("XLV", "Health Care"), ("XLY", "Consumer Discretionary"),
           ("XLP", "Consumer Staples"), ("XLI", "Industrials"),
           ("XLB", "Materials"), ("XLU", "Utilities"),
           ("XLRE", "Real Estate"), ("XLC", "Communication Services")]

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

# Timeframe range -> (yfinance period, interval). Daily interval only.
_RANGE_MAP = {
    "1mo": ("1mo", "1d"),
    "3mo": ("3mo", "1d"),
    "6mo": ("6mo", "1d"),
    "1y": ("1y", "1d"),
    "5y": ("5y", "1d"),
    "max": ("max", "1d"),
}


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
        # change/change_pct are computed directly from the 1mo bars already
        # fetched for the sparkline, avoiding a redundant get_quote() fetch.
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
