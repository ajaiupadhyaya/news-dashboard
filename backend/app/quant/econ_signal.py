"""Econ-signal accessor — macro regime classification from FRED data.

Reads the dashboard's existing `econ_series` table (Phase 2). Exposes:
  - load_series(series_id, start, end) → pd.Series (date-indexed floats)
  - classify_regime(as_of, ...) → "risk_on" | "risk_off"

The macro-regime overlay strategy calls classify_regime to decide whether
to halve gross exposure (risk_off) or stay full-on (risk_on).
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from app.database import econ_series, get_engine


def load_series(series_id: str, *, start: str, end: str) -> pd.Series:
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(econ_series).where(
                (econ_series.c.series_id == series_id)
                & (econ_series.c.date >= start)
                & (econ_series.c.date <= end)
            ).order_by(econ_series.c.date)
        ).all()
    if not rows:
        return pd.Series(dtype="float64", name=series_id)
    return pd.Series(
        {r.date: float(r.value) for r in rows if r.value is not None},
        name=series_id,
    )


def _latest_value_on_or_before(s: pd.Series, as_of: str) -> float | None:
    if s.empty:
        return None
    sub = s[s.index <= as_of]
    if sub.empty:
        return None
    return float(sub.iloc[-1])


def _trend(s: pd.Series, as_of: str, lookback_days: int = 90) -> float | None:
    if s.empty:
        return None
    sub = s[s.index <= as_of]
    if len(sub) < 2:
        return None
    cutoff = (pd.Timestamp(as_of) - pd.Timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    sub = sub[sub.index >= cutoff]
    if len(sub) < 2 or sub.iloc[0] == 0:
        return None
    return float(sub.iloc[-1] / sub.iloc[0] - 1.0)


def classify_regime(*, as_of: str, lookback_days: int = 90) -> str:
    """Return 'risk_on' or 'risk_off' based on T10Y2Y, UNRATE, INDPRO."""
    start = (pd.Timestamp(as_of) - pd.Timedelta(days=lookback_days * 4)).strftime("%Y-%m-%d")
    t10y2y = load_series("T10Y2Y", start=start, end=as_of)
    unrate = load_series("UNRATE", start=start, end=as_of)
    indpro = load_series("INDPRO", start=start, end=as_of)

    curve = _latest_value_on_or_before(t10y2y, as_of)
    unrate_trend = _trend(unrate, as_of, lookback_days)
    indpro_trend = _trend(indpro, as_of, lookback_days)

    score = 0
    if curve is not None and curve < 0:
        score += 2
    if unrate_trend is not None and unrate_trend > 0:
        score += 1
    if indpro_trend is not None and indpro_trend < 0:
        score += 1

    return "risk_off" if score >= 2 else "risk_on"
