from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_auth
from app.cache import cache
from app.services import finance_service

router = APIRouter(prefix="/api/finance", dependencies=[Depends(require_auth)])


@router.get("/overview")
def overview():
    """Cached so the frontend never blocks on yfinance."""
    return cache.get_or_compute("finance:overview", finance_service.build_overview)


@router.get("/instrument/{symbol}")
def instrument(symbol: str):
    key = f"finance:instrument:{symbol.strip().upper()}"
    result = cache.get_or_compute(
        key, lambda: finance_service.build_instrument(symbol))
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return result
