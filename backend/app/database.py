import logging
import os

from sqlalchemy import (Column, Float, Integer, MetaData, String, Table, Text,
                        create_engine, delete, insert, select)
from sqlalchemy.engine import Engine

from app.config import get_settings
from app.models import Bar

logger = logging.getLogger(__name__)
metadata = MetaData()

ohlcv = Table(
    "ohlcv", metadata,
    Column("symbol", String(20), primary_key=True),
    Column("date", String(10), primary_key=True),
    Column("open", Float),
    Column("high", Float),
    Column("low", Float),
    Column("close", Float),
    Column("volume", Integer),
)

watchlist = Table(
    "watchlist", metadata,
    Column("symbol", String(20), primary_key=True),
    Column("position", Integer),
    Column("added_at", String(32)),
)

preferences = Table(
    "preferences", metadata,
    Column("key", String(64), primary_key=True),
    Column("value", Text),
)

_engine: Engine | None = None


def _resolve_url() -> str:
    url = get_settings().database_url
    if url:
        return url
    os.makedirs("data", exist_ok=True)
    return "sqlite:///data/dashboard.db"


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = _resolve_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
        if not url.startswith("postgresql"):
            logger.warning("DATABASE_URL is not Postgres (%s); "
                           "data is not durable on ephemeral hosts", url)
    return _engine


def init_db() -> None:
    """Create all tables if they do not exist."""
    metadata.create_all(get_engine())


def reset_engine() -> None:
    """Test helper: dispose the cached engine so a new DATABASE_URL is picked up."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def save_ohlcv(symbol: str, bars: list[Bar]) -> None:
    """Replace all stored bars for `symbol` with `bars` (portable upsert)."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(delete(ohlcv).where(ohlcv.c.symbol == symbol))
        if bars:
            conn.execute(insert(ohlcv), [
                {"symbol": symbol, "date": b.date, "open": b.open, "high": b.high,
                 "low": b.low, "close": b.close, "volume": b.volume}
                for b in bars
            ])


def load_ohlcv(symbol: str) -> list[Bar]:
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            select(ohlcv).where(ohlcv.c.symbol == symbol).order_by(ohlcv.c.date)
        ).mappings().all()
    return [Bar(date=r["date"], open=r["open"], high=r["high"], low=r["low"],
                close=r["close"], volume=r["volume"]) for r in rows]
