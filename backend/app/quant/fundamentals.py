"""Fundamentals accessor for the multi-factor strategy.

Wraps yfinance.Ticker(sym).info — slow and rate-limited — behind a
persistent JSON cache at backend/data/fundamentals_cache.json (overridable
via QUANT_FUNDAMENTALS_CACHE env var).

Used by `multi-factor-combo` strategy for the P/B (value) and ROE
(quality) factors.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Fundamentals:
    symbol: str
    price_to_book: float | None
    roe: float | None


_DEFAULT_CACHE = str(
    Path(__file__).resolve().parent.parent.parent / "data" / "fundamentals_cache.json"
)


def _cache_path() -> Path:
    return Path(os.environ.get("QUANT_FUNDAMENTALS_CACHE", _DEFAULT_CACHE))


def _load_cache() -> dict:
    p = _cache_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def _save_cache(d: dict) -> None:
    p = _cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2))


def clear_cache() -> None:
    p = _cache_path()
    if p.exists():
        p.unlink()


def _fetch_yf(symbol: str) -> dict:
    """Real network call — split out so tests can mock it."""
    return yf.Ticker(symbol).info or {}


def get_fundamentals(symbol: str) -> Fundamentals:
    cache = _load_cache()
    if symbol in cache:
        c = cache[symbol]
        return Fundamentals(
            symbol=symbol,
            price_to_book=c.get("price_to_book"),
            roe=c.get("roe"),
        )
    raw = _fetch_yf(symbol)
    f = Fundamentals(
        symbol=symbol,
        price_to_book=raw.get("priceToBook"),
        roe=raw.get("returnOnEquity"),
    )
    cache[symbol] = {"price_to_book": f.price_to_book, "roe": f.roe}
    _save_cache(cache)
    return f


def get_fundamentals_batch(symbols: list[str]) -> dict[str, Fundamentals]:
    return {sym: get_fundamentals(sym) for sym in symbols}
