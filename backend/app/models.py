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


class InstrumentStats(BaseModel):
    momentum_1m: float
    momentum_3m: float
    momentum_6m: float
    volatility_30d: float
    week52_high: float | None = None
    week52_low: float | None = None


class InstrumentResponse(BaseModel):
    symbol: str
    profile: Fundamentals
    bars: list[Bar]
    technicals: Technicals
    stats: InstrumentStats
    updated_at: str
