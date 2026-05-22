"""Pure analysis functions for news story metrics. No I/O."""
from datetime import datetime, timedelta, timezone


def parse_timestamp(ts: str) -> datetime | None:
    """Parse an ISO timestamp into a timezone-aware datetime (assumes UTC
    when the string carries no offset). None on a malformed string."""
    try:
        dt = datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def momentum_score(published_ats: list[str], now: datetime,
                   recent_hours: int = 6, window_hours: int = 48) -> float:
    """Coverage acceleration for a story cluster.

    Compares the article count in the last `recent_hours` against the rate
    implied by the full `window_hours`. 1.0 = steady; >1 accelerating;
    <1 decelerating. 0.0 when the window holds no articles.
    """
    cutoff_recent = now - timedelta(hours=recent_hours)
    cutoff_window = now - timedelta(hours=window_hours)
    recent = 0
    total = 0
    for ts in published_ats:
        dt = parse_timestamp(ts)
        if dt is None or dt < cutoff_window or dt > now:
            continue
        total += 1
        if dt >= cutoff_recent:
            recent += 1
    if total == 0:
        return 0.0
    expected = total * (recent_hours / window_hours)
    return round(recent / expected, 4) if expected else 0.0


def momentum_status(score: float) -> str:
    """Bucket a momentum score: surging / steady / fading."""
    if score >= 1.5:
        return "surging"
    if score <= 0.6:
        return "fading"
    return "steady"


def rank_score(source_count: int, article_count: int,
               momentum: float) -> float:
    """Overview-ranking weight. Source diversity dominates (many outlets =
    an important story), then article volume, then momentum."""
    return round(source_count * 2.0 + article_count * 0.5
                 + momentum * 1.5, 4)
