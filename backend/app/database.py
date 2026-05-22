import logging
from pathlib import Path

from sqlalchemy import (Column, Float, Integer, MetaData, String, Table, Text,
                        create_engine, delete, insert, select)
from sqlalchemy.engine import Engine

from app.config import get_settings
from app.models import Bar, IndicatorPoint

logger = logging.getLogger(__name__)
_BASE_DIR = Path(__file__).resolve().parent.parent  # the backend/ directory

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

econ_series = Table(
    "econ_series", metadata,
    Column("series_id", String(32), primary_key=True),
    Column("date", String(10), primary_key=True),
    Column("value", Float),
)

_engine: Engine | None = None


def _resolve_url() -> str:
    url = get_settings().database_url
    if url:
        return url
    data_dir = _BASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{data_dir / 'dashboard.db'}"


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


def save_econ_series(series_id: str, points: list[IndicatorPoint]) -> None:
    """Replace all stored points for `series_id` with `points`."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(delete(econ_series).where(
            econ_series.c.series_id == series_id))
        if points:
            conn.execute(insert(econ_series), [
                {"series_id": series_id, "date": p.date, "value": p.value}
                for p in points
            ])


def load_econ_series(series_id: str) -> list[IndicatorPoint]:
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            select(econ_series).where(econ_series.c.series_id == series_id)
            .order_by(econ_series.c.date)
        ).mappings().all()
    return [IndicatorPoint(date=r["date"], value=r["value"]) for r in rows]
