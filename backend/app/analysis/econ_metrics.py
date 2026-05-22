"""Pure analysis functions for the Economics domain. No I/O."""
from datetime import date

from app.models import IndicatorPoint


def period_change(values: list[float]) -> float:
    """Latest value minus the prior value. 0.0 if fewer than 2 values."""
    if len(values) < 2:
        return 0.0
    return round(values[-1] - values[-2], 4)


def pct_change(values: list[float]) -> float | None:
    """Percent change from the prior value to the latest. None if too short."""
    if len(values) < 2:
        return None
    base = values[-2]
    return round((values[-1] - base) / base * 100, 4) if base else None


def trend_marker(values: list[float], window: int = 24) -> str:
    """Where the latest value sits within its trailing `window` range.

    Returns "below" / "in" / "above" — bottom third / middle / top third.
    "in" when history is too short or the window is flat.
    """
    if len(values) < 3:
        return "in"
    recent = values[-window:]
    lo, hi = min(recent), max(recent)
    if hi == lo:
        return "in"
    pos = (values[-1] - lo) / (hi - lo)
    if pos < 1 / 3:
        return "below"
    if pos > 2 / 3:
        return "above"
    return "in"


def yoy_change(points: list[IndicatorPoint]) -> float | None:
    """Year-over-year percent change using the observation closest to 365
    days before the latest. None when there is no ~1-year-old observation."""
    if len(points) < 2:
        return None
    latest = points[-1]
    try:
        latest_d = date.fromisoformat(latest.date)
    except ValueError:
        return None
    target_days = 365
    best = None
    best_gap = None
    for p in points[:-1]:
        try:
            gap = abs((latest_d - date.fromisoformat(p.date)).days - target_days)
        except ValueError:
            continue
        if best_gap is None or gap < best_gap:
            best, best_gap = p, gap
    # Require the match to be within ~45 days of a full year.
    if best is None or best_gap is None or best_gap > 45 or not best.value:
        return None
    return round((latest.value - best.value) / best.value * 100, 4)


def momentum_score(values: list[float], window: int = 6) -> float:
    """Recent momentum: percent change over the trailing `window` steps.
    0.0 if history is too short."""
    if len(values) <= window:
        return 0.0
    base = values[-window - 1]
    return round((values[-1] - base) / base * 100, 4) if base else 0.0


def recession_intervals(points: list[IndicatorPoint]) -> list[tuple[str, str]]:
    """Contiguous (start_date, end_date) intervals where a 0/1 indicator
    series is 'on' (value >= 0.5). An interval ends at the first observation
    back below the threshold; an open final run ends at the last point."""
    intervals: list[tuple[str, str]] = []
    start: str | None = None
    for p in points:
        if p.value >= 0.5 and start is None:
            start = p.date
        elif p.value < 0.5 and start is not None:
            intervals.append((start, p.date))
            start = None
    if start is not None and points:
        intervals.append((start, points[-1].date))
    return intervals


def recession_status(signal: str, value: float) -> tuple[str, str]:
    """Status + plain-language detail for a recession signal.

    `signal` is "yield_curve" (10y-2y spread) or "sahm" (Sahm-rule value).
    Returns (status, detail) where status is normal/warning/alert.
    """
    if signal == "yield_curve":
        if value < 0:
            return ("alert",
                    "Inverted — historically a recession precursor.")
        if value < 0.5:
            return ("warning", "Flattening — narrowing growth cushion.")
        return ("normal", "Positively sloped — no curve stress.")
    if signal == "sahm":
        if value >= 0.5:
            return ("alert", "Sahm rule triggered — recession signal.")
        if value >= 0.3:
            return ("warning", "Approaching the Sahm-rule threshold.")
        return ("normal", "Well below the Sahm-rule threshold.")
    return ("normal", "")
