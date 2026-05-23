"""Walk-forward windows + OOS equity stitching.

A walk-forward analysis splits a long time series into rolling
(train, test) windows: parameters are optimized on `train` then evaluated
out-of-sample on `test`. The OOS equity from each test window is stitched
together to form the displayed "backtest" equity curve — every point is
out-of-sample so the curve is not in-sample fit.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from dateutil.relativedelta import relativedelta


@dataclass(frozen=True)
class Window:
    train_start: str   # ISO yyyy-mm-dd
    train_end: str
    test_start: str
    test_end: str


def build_walkforward_windows(
    dates: pd.DatetimeIndex,
    *,
    train_years: int,
    test_years: int,
    step_months: int,
) -> list[Window]:
    """Return all walk-forward windows that fit inside `dates`."""
    if len(dates) == 0:
        return []
    first = dates[0]
    last = dates[-1]
    windows: list[Window] = []

    train_start = first
    while True:
        train_end = train_start + relativedelta(years=train_years) - relativedelta(days=1)
        test_start = train_end + relativedelta(days=1)
        test_end = test_start + relativedelta(years=test_years) - relativedelta(days=1)
        if test_end > last:
            break

        # Snap to actual trading dates contained in `dates`.
        ts = dates[(dates >= train_start) & (dates <= train_end)]
        te = dates[(dates >= test_start) & (dates <= test_end)]
        if len(ts) == 0 or len(te) == 0:
            train_start += relativedelta(months=step_months)
            continue
        windows.append(Window(
            train_start=ts[0].strftime("%Y-%m-%d"),
            train_end=ts[-1].strftime("%Y-%m-%d"),
            test_start=te[0].strftime("%Y-%m-%d"),
            test_end=te[-1].strftime("%Y-%m-%d"),
        ))
        train_start += relativedelta(months=step_months)
    return windows


def stitch_oos_equity(segments: list[pd.Series]) -> pd.Series:
    """Stitch per-window OOS equity series into a single continuous equity curve.

    Each segment is rescaled to start at the previous segment's last value,
    so the resulting curve compounds returns across windows.
    Overlapping dates are resolved by keeping the earlier window's value.
    """
    if not segments:
        return pd.Series(dtype="float64")

    # First segment carried as-is.
    out: pd.Series = segments[0].copy()
    for seg in segments[1:]:
        if seg.empty:
            continue
        new = seg[~seg.index.isin(out.index)]
        if new.empty:
            continue
        last_existing = out.iloc[-1]
        first_seg = seg.iloc[0]
        if first_seg == 0:
            continue
        rescaled = new * (last_existing / first_seg)
        out = pd.concat([out, rescaled])
    return out.sort_index()
