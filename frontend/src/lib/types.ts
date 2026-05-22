/** TypeScript mirrors of the Phase 1a backend response shapes. */

export interface Bar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Quote {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  as_of: string;
}

export interface WatchlistQuote extends Quote {
  sparkline: number[];
}

export interface Fundamentals {
  symbol: string;
  name: string;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  pe_ratio: number | null;
  price_to_book: number | null;
  dividend_yield: number | null;
  week52_high: number | null;
  week52_low: number | null;
  beta: number | null;
}

export interface SectorChange {
  symbol: string;
  name: string;
  change_pct: number;
}

export interface Breadth {
  advancers: number;
  decliners: number;
  unchanged: number;
  advance_decline_ratio: number;
}

export interface OverviewResponse {
  watchlist: WatchlistQuote[];
  indices: Quote[];
  sectors: SectorChange[];
  breadth: Breadth;
  updated_at: string;
}

export interface Technicals {
  sma_20: (number | null)[];
  sma_50: (number | null)[];
  sma_200: (number | null)[];
}

export interface InstrumentStats {
  momentum_1m: number;
  momentum_3m: number;
  momentum_6m: number;
  volatility_30d: number;
  week52_high: number | null;
  week52_low: number | null;
}

export interface InstrumentResponse {
  symbol: string;
  profile: Fundamentals;
  bars: Bar[];
  technicals: Technicals;
  stats: InstrumentStats;
  updated_at: string;
}

/** Economics domain (Phase 2) — mirrors the backend economics models. */

export interface IndicatorPoint {
  date: string;
  value: number;
}

export interface ReleaseEvent {
  date: string;
  release_name: string;
}

export type TrendMarker = 'below' | 'in' | 'above';

export interface IndicatorSummary {
  series_id: string;
  name: string;
  unit: string;
  latest: number;
  latest_date: string;
  change: number;
  trend: TrendMarker;
  sparkline: number[];
}

export interface EconomicsOverview {
  indicators: IndicatorSummary[];
  calendar: ReleaseEvent[];
  updated_at: string;
}

export type SignalStatus = 'normal' | 'warning' | 'alert';

export interface RecessionSignal {
  name: string;
  value: number;
  status: SignalStatus;
  detail: string;
}

export interface IndicatorDetail {
  series_id: string;
  name: string;
  unit: string;
  series: IndicatorPoint[];
  latest: number;
  change: number;
  yoy: number | null;
  range_low: number;
  range_high: number;
  momentum: number;
  recession_signals: RecessionSignal[];
  updated_at: string;
}
