from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_auth
from app.store import add_to_watchlist, get_watchlist, remove_from_watchlist

router = APIRouter(prefix="/api/watchlist", dependencies=[Depends(require_auth)])


class SymbolBody(BaseModel):
    symbol: str


@router.get("")
def list_watchlist() -> dict:
    return {"symbols": get_watchlist()}


@router.post("")
def add_symbol(body: SymbolBody) -> dict:
    symbol = body.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="symbol is required")
    add_to_watchlist(symbol)
    return {"symbols": get_watchlist()}


@router.delete("/{symbol}")
def delete_symbol(symbol: str) -> dict:
    remove_from_watchlist(symbol.strip().upper())
    return {"symbols": get_watchlist()}
