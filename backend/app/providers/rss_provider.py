import hashlib
import logging
import re
from datetime import datetime, timezone

import feedparser

from app.models import Article

logger = logging.getLogger(__name__)

# Curated general-news RSS feeds: (feed URL, source name, category).
# Per-feed isolation means a dead or malformed feed is simply skipped,
# so this list can grow or shrink freely.
RSS_FEEDS: list[tuple[str, str, str]] = [
    ("https://feeds.bbci.co.uk/news/rss.xml", "BBC News", "general"),
    ("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC News", "world"),
    ("https://feeds.npr.org/1001/rss.xml", "NPR", "general"),
    ("https://www.theguardian.com/world/rss", "The Guardian", "world"),
    ("https://www.theguardian.com/us-news/rss", "The Guardian", "general"),
    ("https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
     "The New York Times", "general"),
    ("https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
     "The New York Times", "world"),
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera", "world"),
    ("https://www.pbs.org/newshour/feeds/rss/headlines", "PBS NewsHour",
     "general"),
    ("https://www.cbsnews.com/latest/rss/main", "CBS News", "general"),
    ("https://abcnews.go.com/abcnews/topstories", "ABC News", "general"),
    ("http://feeds.nbcnews.com/nbcnews/public/news", "NBC News", "general"),
    ("http://rss.cnn.com/rss/cnn_topstories.rss", "CNN", "general"),
    ("https://feeds.washingtonpost.com/rss/world", "The Washington Post",
     "world"),
    ("https://feeds.skynews.com/feeds/rss/world.xml", "Sky News", "world"),
    ("https://rss.dw.com/rdf/rss-en-all", "Deutsche Welle", "world"),
    ("https://www.france24.com/en/rss", "France 24", "world"),
    ("https://www.cnbc.com/id/100003114/device/rss/rss.html", "CNBC",
     "business"),
    ("https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
     "The Wall Street Journal", "world"),
    ("https://moxie.foxnews.com/google-publisher/latest.xml", "Fox News",
     "general"),
    ("https://www.latimes.com/rss2.0.xml", "Los Angeles Times", "general"),
    ("https://feeds.arstechnica.com/arstechnica/index", "Ars Technica",
     "technology"),
]

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str:
    """Strip HTML tags and surrounding whitespace."""
    return _TAG_RE.sub("", text or "").strip()


def _published_iso(entry) -> str:
    """ISO datetime for an entry, falling back to now() when absent."""
    tm = (getattr(entry, "published_parsed", None)
          or getattr(entry, "updated_parsed", None))
    if tm is None:
        return datetime.now(timezone.utc).isoformat()
    return datetime(*tm[:6], tzinfo=timezone.utc).isoformat()


def _parse_feed(url: str, source: str, category: str) -> list[Article]:
    parsed = feedparser.parse(url)
    articles: list[Article] = []
    for entry in getattr(parsed, "entries", []):
        link = getattr(entry, "link", "")
        title = _clean(getattr(entry, "title", ""))
        if not link or not title:
            continue
        articles.append(Article(
            id=hashlib.sha1(link.encode()).hexdigest(),
            title=title,
            summary=_clean(getattr(entry, "summary", ""))[:400],
            url=link,
            source=source,
            published_at=_published_iso(entry),
            category=category,
            image_url=None))
    return articles


def get_articles() -> list[Article]:
    """All articles from every configured feed. A failing feed is skipped
    and logged — it never blanks the others (per-feed isolation)."""
    articles: list[Article] = []
    for url, source, category in RSS_FEEDS:
        try:
            articles.extend(_parse_feed(url, source, category))
        except Exception as exc:        # noqa: BLE001 — isolate every feed
            logger.warning("RSS feed %s (%s) failed: %s", source, url, exc)
    return articles
