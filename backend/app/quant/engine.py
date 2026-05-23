"""Backtest engine — vectorbt wrappers + custom forward-step simulator.

This module is the boundary between the strategy framework (clean DataFrames
of target weights) and the execution machinery (orders + fills + equity +
metrics).

Adapted for vectorbt 1.0.0:
- pf.stats() has no "Annualized Return [%]" key — CAGR computed manually.
- pf.value() returns a DataFrame for single-column portfolios without
  cash_sharing; we squeeze to a Series.
- orders.records_readable columns: 'Order Id', 'Column', 'Timestamp',
  'Size', 'Price', 'Fees', 'Side' (capitalized).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd
import vectorbt as vbt

from app.quant.cost_model import CostModel, apply_slippage
from app.quant.strategies.base import Strategy, StrategyContext


@dataclass
class EngineResult:
    equity: pd.Series                      # indexed by date
    trades: pd.DataFrame                   # cols: date, symbol, side, qty, price, commission, notional
    metrics: dict[str, float]              # sharpe, max_drawdown, total_return, cagr, ...


def _portfolio_from_weights(
    weights: pd.DataFrame,
    close: pd.DataFrame,
    cost_model: CostModel,
    initial_equity: float,
) -> vbt.Portfolio:
    """Build a vbt.Portfolio from continuous target weights.

    vectorbt 1.0.0 uses fees as a fraction of order *value* (not equity),
    and slippage as a fraction of price.  Commission stored in CostModel is a
    flat per-fill dollar amount; we convert it to a fractional fee using the
    typical first-bar notional as a proxy.
    """
    # Estimate a per-fill notional for converting flat commission to a fraction.
    first_price = float(close.iloc[0].mean())
    approx_notional = initial_equity * float(weights.iloc[0].mean()) if first_price > 0 else initial_equity
    approx_notional = max(approx_notional, 1.0)

    fees = cost_model.commission / approx_notional if cost_model.commission else 0.0
    slippage = cost_model.slippage_bps / 10_000.0

    # Align weights to close index; fill missing dates with 0 (flat).
    weights = weights.reindex(close.index).fillna(0.0)

    # targetpercent size_type: size values are fractions of portfolio value.
    return vbt.Portfolio.from_orders(
        close=close,
        size=weights,
        size_type="targetpercent",
        init_cash=initial_equity,
        fees=fees,
        slippage=slippage,
        freq="D",
    )


def _extract_metrics(pf: vbt.Portfolio, period_days: int) -> dict[str, float]:
    """Extract standardised metrics from a vbt.Portfolio.

    vectorbt 1.0.0 does not expose "Annualized Return [%]"; we compute CAGR
    from total return and the actual period length.
    """
    stats = pf.stats(silence_warnings=True)

    def f(name: str, default: float = float("nan")) -> float:
        try:
            v = stats[name]
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return default
            return float(v)
        except (KeyError, TypeError, ValueError):
            return default

    total_return_pct = f("Total Return [%]", default=0.0)
    total_return = total_return_pct / 100.0

    # CAGR: (1 + r)^(365/days) - 1  — use calendar days if > 1 year
    years = period_days / 365.0
    if years > 0 and total_return > -1.0:
        cagr = (1.0 + total_return) ** (1.0 / years) - 1.0
    else:
        cagr = 0.0

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": f("Sharpe Ratio", default=0.0),
        "sortino": f("Sortino Ratio", default=0.0),
        "calmar": f("Calmar Ratio", default=0.0),
        "max_drawdown": f("Max Drawdown [%]", default=0.0) / 100.0,
        "win_rate": f("Win Rate [%]", default=0.0) / 100.0,
        "volatility": f("Annualized Volatility [%]", default=0.0) / 100.0,
    }


def _extract_trades(pf: vbt.Portfolio) -> pd.DataFrame:
    """Convert vbt's order records to our normalised trade schema.

    vectorbt 1.0.0 records_readable columns (capitalised):
      'Order Id', 'Column', 'Timestamp', 'Size', 'Price', 'Fees', 'Side'
    where 'Side' is 'Buy' or 'Sell'.
    """
    _empty = pd.DataFrame(columns=[
        "date", "symbol", "side", "qty", "price", "commission", "notional",
    ])
    try:
        records = pf.orders.records_readable
    except Exception:
        return _empty

    if records is None or len(records) == 0:
        return _empty

    out = pd.DataFrame({
        "date":       pd.to_datetime(records["Timestamp"]).dt.strftime("%Y-%m-%d"),
        "symbol":     records["Column"].astype(str),
        "side":       records["Side"].astype(str).str.lower(),
        "qty":        records["Size"].astype(float).abs(),
        "price":      records["Price"].astype(float),
        "commission": records["Fees"].astype(float),
    })
    out["notional"] = out["qty"] * out["price"]
    out = out.reset_index(drop=True)
    return out


def run_single(
    strategy: Strategy,
    bars: pd.DataFrame,
    *,
    params: dict,
    cost_model: CostModel | None = None,
    initial_equity: float = 100_000.0,
    ctx: StrategyContext | None = None,
) -> EngineResult:
    """Run a single parameter setting through the engine.

    Args:
        strategy:       Strategy instance with a generate_signals method.
        bars:           OHLCV DataFrame indexed by date; must include columns
                        for every symbol the strategy expects.
        params:         Strategy-specific hyper-parameters dict.
        cost_model:     Fees + slippage specification (default: zero cost).
        initial_equity: Starting cash in dollars.
        ctx:            StrategyContext for walk-forward metadata (optional).

    Returns:
        EngineResult with equity curve, trade log, and performance metrics.
    """
    cost_model = cost_model or CostModel()
    ctx = ctx or StrategyContext()

    weights = strategy.generate_signals(bars, params, ctx)
    pf = _portfolio_from_weights(weights, bars, cost_model, initial_equity)

    # pf.value() returns a DataFrame for non-grouped portfolios in vbt 1.0.0;
    # squeeze to a named Series indexed by date.
    equity = pf.value()
    if isinstance(equity, pd.DataFrame):
        if equity.shape[1] == 1:
            equity = equity.iloc[:, 0]
        else:
            equity = equity.sum(axis=1)
    equity = equity.rename("equity")

    # Derive period length for CAGR calculation.
    period_days = (bars.index[-1] - bars.index[0]).days if len(bars) > 1 else 1

    return EngineResult(
        equity=equity,
        trades=_extract_trades(pf),
        metrics=_extract_metrics(pf, period_days),
    )


def run_grid(
    strategy: Strategy,
    bars: pd.DataFrame,
    *,
    grid: dict[str, list],
    cost_model: CostModel | None = None,
    initial_equity: float = 100_000.0,
    ctx: StrategyContext | None = None,
    constraint: Callable[[dict], bool] | None = None,
) -> pd.DataFrame:
    """Run every parameter combination from `grid` through `run_single`.

    Returns a DataFrame with one row per valid combo. Columns:
        <param names from grid>, sharpe, total_return, cagr, sortino,
        calmar, max_drawdown, win_rate, volatility
    Rows are NOT sorted; caller picks the winner.
    """
    if not grid:
        # Single-row result with empty params.
        res = run_single(
            strategy, bars,
            params={}, cost_model=cost_model,
            initial_equity=initial_equity, ctx=ctx,
        )
        return pd.DataFrame([{**res.metrics}])

    names = list(grid.keys())
    rows: list[dict] = []
    for combo in itertools.product(*(grid[n] for n in names)):
        params = dict(zip(names, combo))
        if constraint and not constraint(params):
            continue
        res = run_single(
            strategy, bars,
            params=params, cost_model=cost_model,
            initial_equity=initial_equity, ctx=ctx,
        )
        rows.append({**params, **res.metrics})
    return pd.DataFrame(rows)


def simulate_fills(
    *,
    current_positions: dict[str, dict],
    target_positions: dict[str, dict],
    prices: dict[str, float],
    cost_model: CostModel,
) -> tuple[list[dict], dict[str, dict]]:
    """Compute the fills required to move from current → target positions
    and return (fills, new_positions).

    `current_positions` / `target_positions`:
        symbol -> {qty: int, avg_cost: float[, weight: float]}
    `prices`: symbol -> close price for the day.

    `fills` is a list of dicts ready for `strategy_trades` insert.
    `new_positions` mirrors `current_positions` after applying the fills.
    """
    fills: list[dict] = []
    new: dict[str, dict] = {sym: dict(pos) for sym, pos in current_positions.items()}

    symbols = set(current_positions) | set(target_positions)
    for sym in sorted(symbols):
        cur_qty = current_positions.get(sym, {}).get("qty", 0)
        tgt_qty = target_positions.get(sym, {}).get("qty", 0)
        delta = tgt_qty - cur_qty
        if delta == 0:
            continue
        price_raw = prices.get(sym)
        if price_raw is None:
            # No price today — skip; the runner decides whether to liquidate.
            continue
        # Side mapping: positive delta when going from short to less-short is a "cover",
        # else "buy". Negative delta when going from long to less-long is "sell",
        # else "short". Q1a strategies are long-only so the simpler branch suffices.
        if delta > 0:
            side = "cover" if cur_qty < 0 else "buy"
        else:
            side = "short" if tgt_qty < 0 and cur_qty >= 0 else "sell"
        fill_price = apply_slippage(
            price_raw, side=side, slippage_bps=cost_model.slippage_bps,
        )
        qty = abs(delta)
        notional = qty * fill_price
        fills.append({
            "symbol": sym,
            "side": side,
            "qty": qty,
            "price": fill_price,
            "commission": cost_model.commission,
            "notional": notional,
        })
        # Update position
        if tgt_qty == 0:
            new.pop(sym, None)
        else:
            # Weighted-average cost basis on additive buys; reset on side flip.
            if cur_qty == 0 or (cur_qty > 0) != (tgt_qty > 0):
                new[sym] = {"qty": tgt_qty, "avg_cost": fill_price}
            elif (tgt_qty > cur_qty > 0) or (tgt_qty < cur_qty < 0):
                old_basis = current_positions[sym].get("avg_cost", fill_price)
                added = qty
                new_avg = (old_basis * abs(cur_qty) + fill_price * added) / abs(tgt_qty)
                new[sym] = {"qty": tgt_qty, "avg_cost": new_avg}
            else:
                # Partial close — keep existing avg_cost.
                new[sym] = {"qty": tgt_qty, "avg_cost": current_positions[sym]["avg_cost"]}
    return fills, new
