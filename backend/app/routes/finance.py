from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_auth
from app.cache import cache
from app.services import finance_service

router = APIRouter(prefix="/api/finance", dependencies=[Depends(require_auth)])


@router.get("/overview")
def overview():
    """Cached so the frontend never blocks on yfinance."""
    return cache.get_or_compute("finance:overview", finance_service.build_overview)


@router.get("/markets")
def markets():
    """The Finance domain page: asset classes, indices, movers, breadth."""
    return cache.get_or_compute("finance:markets", finance_service.build_markets)


@router.get("/instrument/{symbol}")
def instrument(symbol: str, range: str = "1y"):
    """`range` selects the timeframe — 1mo/3mo/6mo/1y/5y/max."""
    key = f"finance:instrument:{symbol.strip().upper()}:{range}"
    result = cache.get_or_compute(
        key, lambda: finance_service.build_instrument(symbol, range))
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return result
