import time
from typing import Any, Callable

from app.config import get_settings


class TTLCache:
    """In-memory time-to-live cache. The clock is injectable for testing."""

    def __init__(self, ttl_seconds: int = 300,
                 clock: Callable[[], float] = time.monotonic):
        self._ttl = ttl_seconds
        self._clock = clock
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._clock() >= expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (self._clock() + self._ttl, value)

    def get_or_compute(self, key: str, compute: Callable[[], Any]) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = compute()
        self.set(key, value)
        return value

    def clear(self) -> None:
        self._store.clear()


# Shared application cache instance.
cache = TTLCache(ttl_seconds=get_settings().cache_ttl_seconds)
