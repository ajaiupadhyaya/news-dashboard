from datetime import datetime, timezone

from sqlalchemy import delete, func, insert, select

from app.database import get_engine, preferences, watchlist


def get_watchlist() -> list[str]:
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(watchlist.c.symbol).order_by(watchlist.c.position)
        ).all()
    return [r[0] for r in rows]


def add_to_watchlist(symbol: str) -> None:
    symbol = symbol.strip().upper()
    if not symbol:
        return
    with get_engine().begin() as conn:
        exists = conn.execute(
            select(watchlist.c.symbol).where(watchlist.c.symbol == symbol)
        ).first()
        if exists:
            return
        max_pos = conn.execute(select(func.max(watchlist.c.position))).scalar()
        next_pos = 0 if max_pos is None else max_pos + 1
        conn.execute(insert(watchlist).values(
            symbol=symbol, position=next_pos,
            added_at=datetime.now(timezone.utc).isoformat()))


def remove_from_watchlist(symbol: str) -> None:
    symbol = symbol.strip().upper()
    with get_engine().begin() as conn:
        conn.execute(delete(watchlist).where(watchlist.c.symbol == symbol))


def get_preference(key: str, default: str | None = None) -> str | None:
    with get_engine().begin() as conn:
        row = conn.execute(
            select(preferences.c.value).where(preferences.c.key == key)
        ).first()
    return row[0] if row else default


def set_preference(key: str, value: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(delete(preferences).where(preferences.c.key == key))
        conn.execute(insert(preferences).values(key=key, value=value))
