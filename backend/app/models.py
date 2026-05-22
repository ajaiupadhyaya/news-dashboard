from pydantic import BaseModel


class Bar(BaseModel):
    date: str          # ISO date, e.g. "2026-01-02"
    open: float
    high: float
    low: float
    close: float
    volume: int


class Quote(BaseModel):
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    as_of: str


class WatchlistQuote(Quote):
    sparkline: list[float]


class Fundamentals(BaseModel):
    symbol: str
    name: str
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    price_to_book: float | None = None
    dividend_yield: float | None = None
    week52_high: float | None = None
    week52_low: float | None = None
    beta: float | None = None


class SectorChange(BaseModel):
    symbol: str
    name: str
    change_pct: float


class Breadth(BaseModel):
    advancers: int
    decliners: int
    unchanged: int
    advance_decline_ratio: float


class OverviewResponse(BaseModel):
    watchlist: list[WatchlistQuote]
    indices: list[Quote]
    sectors: list[SectorChange]
    breadth: Breadth
    updated_at: str


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


class InstrumentStats(BaseModel):
    momentum_1m: float
    momentum_3m: float
    momentum_6m: float
    volatility_30d: float
    week52_high: float | None = None
    week52_low: float | None = None


class Returns(BaseModel):
    week_1: float | None = None
    month_1: float | None = None
    month_3: float | None = None
    month_6: float | None = None
    ytd: float | None = None
    year_1: float | None = None
    year_3: float | None = None


class InstrumentResponse(BaseModel):
    symbol: str
    profile: Fundamentals
    bars: list[Bar]
    technicals: Technicals
    stats: InstrumentStats
    returns: Returns = Returns()
    updated_at: str


class IndicatorPoint(BaseModel):
    date: str          # ISO date, e.g. "2026-04-01"
    value: float


class ReleaseEvent(BaseModel):
    date: str          # ISO date of the release
    release_name: str


class IndicatorSummary(BaseModel):
    series_id: str
    name: str
    unit: str          # display unit: "%", "K", "index", "$"
    latest: float      # headline value
    latest_date: str
    change: float      # change vs. the prior observation, headline units
    trend: str         # trend-relative marker: "below" | "in" | "above"
    sparkline: list[float]


class EconomicsOverview(BaseModel):
    indicators: list[IndicatorSummary]
    calendar: list[ReleaseEvent]
    updated_at: str


class RecessionSignal(BaseModel):
    name: str
    value: float
    status: str        # "normal" | "warning" | "alert"
    detail: str        # plain-language one-liner


class IndicatorDetail(BaseModel):
    series_id: str
    name: str
    unit: str
    series: list[IndicatorPoint]
    latest: float
    change: float
    yoy: float | None = None       # year-over-year %, None when N/A
    range_low: float
    range_high: float
    momentum: float                # momentum/trend composite score
    recession_signals: list[RecessionSignal]
    updated_at: str


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
