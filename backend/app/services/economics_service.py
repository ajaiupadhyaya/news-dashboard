import logging
from datetime import datetime, timezone

from app.analysis import econ_metrics as em
from app.analysis import metrics
from app.database import save_econ_series
from app.models import (EconomicsOverview, IndicatorDetail, IndicatorSummary,
                        RecessionSignal)
from app.providers import fred_provider as provider

logger = logging.getLogger(__name__)

# (series_id, display name, display unit, FRED units transform).
# "pc1" = percent change from a year ago (CPI -> YoY inflation %);
# "chg" = change from the prior observation (payrolls -> monthly jobs added);
# "lin" = the raw series.
INDICATORS: list[tuple[str, str, str, str]] = [
    ("CPIAUCSL", "Inflation (CPI)", "%", "pc1"),
    ("UNRATE", "Unemployment Rate", "%", "lin"),
    ("PAYEMS", "Nonfarm Payrolls", "K", "chg"),
    ("A191RL1Q225SBEA", "Real GDP Growth", "%", "lin"),
    ("FEDFUNDS", "Fed Funds Rate", "%", "lin"),
    ("DGS10", "10-Year Treasury", "%", "lin"),
]

# Recession-signal series (used by every indicator drill-down).
_YIELD_CURVE = "T10Y2Y"
_SAHM = "SAHMREALTIME"

_NAMES = {sid: name for sid, name, _, _ in INDICATORS}
_UNITS = {sid: unit for sid, _, unit, _ in INDICATORS}
_FRED_UNITS = {sid: fu for sid, _, _, fu in INDICATORS}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_overview() -> EconomicsOverview:
    """Assemble the Economics overview: indicator tiles + release calendar."""
    indicators: list[IndicatorSummary] = []
    for series_id, name, unit, fred_units in INDICATORS:
        points = provider.get_series(series_id, units=fred_units)
        if len(points) < 2:
            continue        # per-indicator isolation: skip, don't fail
        try:
            save_econ_series(series_id, points)
        except Exception as exc:
            logger.warning("save_econ_series(%s) failed: %s", series_id, exc)
        values = [p.value for p in points]
        indicators.append(IndicatorSummary(
            series_id=series_id, name=name, unit=unit,
            latest=points[-1].value, latest_date=points[-1].date,
            change=em.period_change(values),
            trend=em.trend_marker(values),
            sparkline=metrics.downsample(values, 24)))

    calendar = provider.get_release_calendar()
    return EconomicsOverview(indicators=indicators, calendar=calendar,
                             updated_at=_now())


def _recession_signals() -> list[RecessionSignal]:
    signals: list[RecessionSignal] = []
    for series_id, label, kind in (
            (_YIELD_CURVE, "Yield curve (10y-2y)", "yield_curve"),
            (_SAHM, "Sahm rule", "sahm")):
        points = provider.get_series(series_id)
        if not points:
            continue
        value = points[-1].value
        status, detail = em.recession_status(kind, value)
        signals.append(RecessionSignal(name=label, value=round(value, 4),
                                       status=status, detail=detail))
    return signals


def build_indicator(series_id: str) -> IndicatorDetail | None:
    """Assemble the drill-down for one indicator. None if unknown/no data."""
    series_id = series_id.strip().upper()
    if series_id not in _NAMES:
        return None
    points = provider.get_series(series_id, units=_FRED_UNITS[series_id])
    if len(points) < 2:
        return None
    values = [p.value for p in points]
    return IndicatorDetail(
        series_id=series_id, name=_NAMES[series_id], unit=_UNITS[series_id],
        series=points, latest=points[-1].value,
        change=em.period_change(values), yoy=em.yoy_change(points),
        range_low=min(values), range_high=max(values),
        momentum=em.momentum_score(values),
        recession_signals=_recession_signals(), updated_at=_now())
