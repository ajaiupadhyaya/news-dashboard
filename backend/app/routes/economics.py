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


@router.get("/indicator/{series_id}")
def indicator(series_id: str):
    key = f"economics:indicator:{series_id.strip().upper()}"
    result = cache.get_or_compute(
        key, lambda: economics_service.build_indicator(series_id))
    if result is None:
        raise HTTPException(status_code=404,
                            detail=f"No data for {series_id}")
    return result
