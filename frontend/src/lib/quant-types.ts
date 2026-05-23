export interface StrategySummary {
  slug: string;
  name: string;
  category: 'classic' | 'alpha' | 'benchmark';
  sparkline: number[];
  live_since: string | null;
  total_return: number;
  sharpe: number;
  max_drawdown: number;
}

export interface HeroEquityPoint {
  date: string;
  equity: number;
}

export interface TradeRow {
  id?: number;
  strategy_slug?: string;
  date: string;
  symbol: string;
  side: 'buy' | 'sell' | 'short' | 'cover';
  qty: number;
  price: number;
  commission?: number;
  notional: number;
  phase: 'backtest' | 'forward';
}

export interface UniverseHealth {
  latest_bar_fetched_at: string | null;
  last_forward_step_per_strategy: Record<string, string | null>;
}

export interface QuantOverview {
  leaderboard: StrategySummary[];
  hero_equity: HeroEquityPoint[];
  recent_trades: TradeRow[];
  universe_health: UniverseHealth;
}

export interface EquityPoint {
  date: string;
  equity: number;
  phase: 'backtest' | 'forward';
  daily_return: number;
}

export interface DrawdownPoint {
  date: string;
  drawdown: number;
}

export interface WalkforwardWindow {
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  chosen_params: Record<string, unknown>;
  oos_metrics: Record<string, number>;
}

export interface ParameterSweepCell {
  params: Record<string, unknown>;
  sharpe: number;
}

export interface PositionRow {
  symbol: string;
  qty: number;
  avg_cost: number;
  opened_at: string;
}

export interface StrategyDetail {
  slug: string;
  name: string;
  category: string;
  methodology_blurb: string;
  universe_kind: string;
  inception_date: string;
  live_start_date: string;
  chosen_params: Record<string, unknown>;
  cost_model: { commission: number; slippage_bps: number; allow_short: boolean };
  last_forward_step_date: string | null;
  equity_series: EquityPoint[];
  drawdown_series: DrawdownPoint[];
  monthly_returns: Record<string, Record<number, number>>;
  tear_sheet: { total_return: number; sharpe: number; max_drawdown: number };
  walkforward_windows: WalkforwardWindow[];
  param_sweep: ParameterSweepCell[];
  current_positions: PositionRow[];
  recent_trades: TradeRow[];
}

export interface TradesPage {
  trades: TradeRow[];
  next_cursor: string | null;
}

export interface RunStatus {
  id: number;
  strategy_slug: string;
  run_kind: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  started_at: string;
  finished_at: string | null;
  progress: { windows_done?: number; windows_total?: number };
  error: string | null;
  summary_metrics: Record<string, number> | null;
}
