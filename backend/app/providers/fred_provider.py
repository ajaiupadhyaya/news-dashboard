import logging

import httpx

from app.config import get_settings
from app.models import IndicatorPoint, ReleaseEvent

logger = logging.getLogger(__name__)

_BASE = "https://api.stlouisfed.org/fred"


def _get(path: str, params: dict) -> dict | None:
    """Single seam over the FRED HTTP API — tests monkeypatch `httpx`.

    Returns None on any failure or when no API key is configured.
    """
    api_key = get_settings().fred_api_key
    if not api_key:
        logger.warning("FRED_API_KEY not set — FRED requests return no data")
        return None
    query = {"api_key": api_key, "file_type": "json", **params}
    try:
        resp = httpx.get(f"{_BASE}/{path}", params=query, timeout=15.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("FRED %s failed: %s", path, e)
        return None


def get_series(series_id: str, units: str = "lin") -> list[IndicatorPoint]:
    """Observations for a FRED series, oldest-first. [] on any failure.

    `units` is a FRED transform code applied server-side: "lin" (raw),
    "pc1" (percent change from a year ago), "chg" (change from the prior
    observation). FRED encodes missing observations as ".", skipped here.
    """
    data = _get("series/observations",
                {"series_id": series_id, "sort_order": "asc", "units": units})
    if not data or "observations" not in data:
        return []
    points: list[IndicatorPoint] = []
    for obs in data["observations"]:
        raw = obs.get("value")
        if raw in (".", "", None):
            continue
        try:
            points.append(IndicatorPoint(date=obs["date"], value=float(raw)))
        except (ValueError, KeyError):
            continue
    return points


def get_release_calendar(limit: int = 60) -> list[ReleaseEvent]:
    """Recent + upcoming economic release dates. [] on any failure."""
    data = _get("releases/dates",
                {"sort_order": "desc", "limit": limit,
                 "include_release_dates_with_no_data": "true"})
    if not data or "release_dates" not in data:
        return []
    events: list[ReleaseEvent] = []
    for rd in data["release_dates"]:
        try:
            events.append(ReleaseEvent(date=rd["date"],
                                       release_name=rd["release_name"]))
        except KeyError:
            continue
    return events
