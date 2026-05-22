import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.analysis import econ_metrics as em
from app.analysis import metrics
from app.database import save_econ_series
from app.models import (EconomicsDashboard, EconomicsOverview,
                        IndicatorCategory, IndicatorDetail, IndicatorPoint,
                        IndicatorSummary, RecessionSignal)
from app.providers import fred_provider as provider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Indicator:
    """One macro series in the dashboard registry."""
    series_id: str
    name: str
    unit: str          # display unit: "%" | "K" | "index" | "$"
    fred_units: str    # default FRED transform: "lin" | "pc1" | "chg"
    category: str      # one of CATEGORY_ORDER
    scale: float = 1.0 # display multiplier for raw-level data (e.g. ICSA)


CATEGORY_ORDER = ["Growth", "Inflation", "Labor", "Rates", "Housing",
                  "Consumer"]

# FRED units codes: "lin" = raw level, "pc1" = % change from a year ago,
# "chg" = change from the prior observation.
INDICATORS: list[Indicator] = [
    # Growth
    Indicator("A191RL1Q225SBEA", "Real GDP Growth", "%", "lin", "Growth"),
    Indicator("INDPRO", "Industrial Production", "%", "pc1", "Growth"),
    Indicator("RSAFS", "Retail Sales", "%", "pc1", "Growth"),
    # Inflation
    Indicator("CPIAUCSL", "Inflation (CPI)", "%", "pc1", "Inflation"),
    Indicator("CPILFESL", "Core CPI", "%", "pc1", "Inflation"),
    Indicator("PCEPI", "PCE Price Index", "%", "pc1", "Inflation"),
    # Labor
    Indicator("UNRATE", "Unemployment Rate", "%", "lin", "Labor"),
    Indicator("PAYEMS", "Nonfarm Payrolls", "K", "chg", "Labor"),
    Indicator("CIVPART", "Labor Force Participation", "%", "lin", "Labor"),
    Indicator("ICSA", "Initial Jobless Claims", "K", "lin", "Labor",
              scale=0.001),
    # Rates
    Indicator("FEDFUNDS", "Fed Funds Rate", "%", "lin", "Rates"),
    Indicator("DGS10", "10-Year Treasury", "%", "lin", "Rates"),
    Indicator("DGS2", "2-Year Treasury", "%", "lin", "Rates"),
    Indicator("T10Y2Y", "10y-2y Spread", "%", "lin", "Rates"),
    # Housing — HOUST and PERMIT are reported in thousands of units natively.
    Indicator("HOUST", "Housing Starts", "K", "lin", "Housing"),
    Indicator("PERMIT", "Building Permits", "K", "lin", "Housing"),
    Indicator("MORTGAGE30US", "30-Year Mortgage Rate", "%", "lin", "Housing"),
    # Consumer
    Indicator("UMCSENT", "Consumer Sentiment", "index", "lin", "Consumer"),
    Indicator("PSAVERT", "Personal Saving Rate", "%", "lin", "Consumer"),
    Indicator("DSPIC96", "Real Disposable Income", "%", "pc1", "Consumer"),
]

# The curated subset shown on the calm four-quadrant home panel.
OVERVIEW_IDS = ["CPIAUCSL", "UNRATE", "PAYEMS", "A191RL1Q225SBEA",
                "FEDFUNDS", "DGS10"]

_BY_ID = {ind.series_id: ind for ind in INDICATORS}

# Recession-signal series (used by every indicator drill-down).
_YIELD_CURVE = "T10Y2Y"
_SAHM = "SAHMREALTIME"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _effective_scale(ind: Indicator, units: str) -> float:
    """An indicator's display scale applies only to raw-level data; any
    non-lin FRED transform already yields ready-to-show numbers."""
    return ind.scale if units == "lin" else 1.0


def _scale_points(points: list[IndicatorPoint],
                  scale: float) -> list[IndicatorPoint]:
    """Apply a display scale to a series. Identity when scale == 1.0."""
    if scale == 1.0:
        return points
    return [IndicatorPoint(date=p.date, value=round(p.value * scale, 6))
            for p in points]


def _summarize(ind: Indicator) -> IndicatorSummary | None:
    """Fetch one indicator and build its summary tile. None on no data."""
    points = provider.get_series(ind.series_id, units=ind.fred_units)
    if len(points) < 2:
        return None        # per-indicator isolation: skip, don't fail
    points = _scale_points(points, _effective_scale(ind, ind.fred_units))
    try:
        save_econ_series(ind.series_id, points)
    except Exception as exc:
        logger.warning("save_econ_series(%s) failed: %s", ind.series_id, exc)
    values = [p.value for p in points]
    return IndicatorSummary(
        series_id=ind.series_id, name=ind.name, category=ind.category,
        unit=ind.unit, latest=points[-1].value, latest_date=points[-1].date,
        change=em.period_change(values), trend=em.trend_marker(values),
        sparkline=metrics.downsample(values, 24))


def build_overview() -> EconomicsOverview:
    """Assemble the Economics overview — the curated home-panel subset."""
    indicators: list[IndicatorSummary] = []
    for series_id in OVERVIEW_IDS:
        ind = _BY_ID.get(series_id)
        if ind is None:
            continue
        summary = _summarize(ind)
        if summary is not None:
            indicators.append(summary)
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
    ind = _BY_ID.get(series_id)
    if ind is None:
        return None
    points = provider.get_series(series_id, units=ind.fred_units)
    if len(points) < 2:
        return None
    points = _scale_points(points, _effective_scale(ind, ind.fred_units))
    values = [p.value for p in points]
    return IndicatorDetail(
        series_id=series_id, name=ind.name, unit=ind.unit, series=points,
        latest=points[-1].value, change=em.period_change(values),
        yoy=em.yoy_change(points), range_low=min(values),
        range_high=max(values), momentum=em.momentum_score(values),
        recession_signals=_recession_signals(), updated_at=_now())
