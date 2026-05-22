import hashlib
import logging
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.models import Article

logger = logging.getLogger(__name__)

_BASE = "https://newsdata.io/api/1"


def _get(path: str, params: dict) -> dict | None:
    """Single seam over the NewsData.io HTTP API — tests monkeypatch `httpx`.

    Returns None on any failure or when no API key is configured.
    """
    api_key = get_settings().news_api_key
    if not api_key:
        logger.warning("NEWS_API_KEY not set — news API returns no data")
        return None
    try:
        resp = httpx.get(f"{_BASE}/{path}",
                         params={"apikey": api_key, **params}, timeout=15.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:        # noqa: BLE001 — degrade gracefully
        logger.warning("news API %s failed: %s", path, exc)
        return None


def _published_iso(pub_date: str | None) -> str:
    """NewsData.io pubDate ('YYYY-MM-DD HH:MM:SS', UTC) -> ISO datetime."""
    if not pub_date:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = datetime.strptime(pub_date, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def get_articles() -> list[Article]:
    """Recent articles from NewsData.io, normalized to `Article`.
    [] on any failure or when no API key is set."""
    data = _get("latest", {"language": "en"})
    if not data or "results" not in data:
        return []
    articles: list[Article] = []
    for r in data["results"]:
        link = r.get("link")
        title = r.get("title")
        if not link or not title:
            continue
        cats = r.get("category") or []
        category = cats[0] if isinstance(cats, list) and cats else "general"
        articles.append(Article(
            id=hashlib.sha1(link.encode()).hexdigest(),
            title=title.strip(),
            summary=(r.get("description") or "")[:400],
            url=link,
            source=r.get("source_name") or r.get("source_id") or "NewsData",
            published_at=_published_iso(r.get("pubDate")),
            category=category,
            image_url=r.get("image_url")))
    return articles
