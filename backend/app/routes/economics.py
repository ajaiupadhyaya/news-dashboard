from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_auth
from app.cache import cache
from app.services import economics_service

router = APIRouter(prefix="/api/economics", dependencies=[Depends(require_auth)])


@router.get("/overview")
def overview():
    """Cached so the frontend never blocks on FRED."""
    return cache.get_or_compute("economics:overview",
                                economics_service.build_overview)


@router.get("/dashboard")
def dashboard():
    """The Economics domain page: categorized indicators + recession + calendar."""
    return cache.get_or_compute("economics:dashboard",
                                economics_service.build_dashboard)


@router.get("/indicator/{series_id}")
def indicator(series_id: str, transform: str | None = None,
              range: str = "max"):
    """`transform` selects the FRED units (lin/pc1/pch); `range` the
    timeframe (1y/5y/10y/max)."""
    sid = series_id.strip().upper()
    key = f"economics:indicator:{sid}:{transform}:{range}"
    result = cache.get_or_compute(
        key, lambda: economics_service.build_indicator(
            sid, transform=transform, range_=range))
    if result is None:
        raise HTTPException(status_code=404,
                            detail=f"No data for {series_id}")
    return result
