import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import (Column, Float, Integer, MetaData, String, Table, Text,
                        create_engine, delete, insert, select)
from sqlalchemy.engine import Engine

from app.config import get_settings
from app.models import Article, Bar, IndicatorPoint

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

news_articles = Table(
    "news_articles", metadata,
    Column("id", String(64), primary_key=True),
    Column("cluster_id", String(64)),
    Column("title", Text),
    Column("summary", Text),
    Column("url", Text),
    Column("source", String(80)),
    Column("published_at", String(32)),
    Column("category", String(40)),
    Column("image_url", Text),
)

news_clusters = Table(
    "news_clusters", metadata,
    Column("id", String(64), primary_key=True),
    Column("headline", Text),
    Column("summary", Text),
    Column("category", String(40)),
    Column("source_count", Integer),
    Column("article_count", Integer),
    Column("momentum", Float),
    Column("status", String(12)),
    Column("first_published_at", String(32)),
    Column("latest_published_at", String(32)),
    Column("centroid", Text),          # JSON-encoded list[float]
    Column("rank_order", Integer),     # 0 = top story
)

bar_cache = Table(
    "bar_cache", metadata,
    Column("symbol", String(20), primary_key=True),
    Column("date", String(10), primary_key=True),     # ISO yyyy-mm-dd
    Column("open", Float),
    Column("high", Float),
    Column("low", Float),
    Column("close", Float),
    Column("adj_close", Float),
    Column("volume", Integer),
    Column("source", String(20)),                     # "yfinance"
    Column("fetched_at", String(32)),
)

strategies = Table(
    "strategies", metadata,
    Column("slug", String(64), primary_key=True),
    Column("name", String(128)),
    Column("category", String(40)),                  # "classic" | "alpha" | "benchmark"
    Column("methodology_blurb", Text),
    Column("universe_kind", String(32)),             # "spy" | "sp500" | "pairs-fixed" | "news-top100"
    Column("inception_date", String(10)),            # ISO
    Column("live_start_date", String(10)),           # ISO
    Column("chosen_params", Text),                   # JSON
    Column("cost_model", Text),                      # JSON {commission, slippage_bps, allow_short}
    Column("enabled", Integer),                      # 0/1
    Column("last_forward_step_date", String(10)),    # ISO, nullable
)

strategy_runs = Table(
    "strategy_runs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("strategy_slug", String(64), index=True),
    Column("run_kind", String(40)),                  # "inception-walkforward" | "param-sweep"
    Column("started_at", String(32)),
    Column("finished_at", String(32)),               # nullable
    Column("status", String(16)),                    # "pending"|"running"|"success"|"failed"
    Column("progress", Text),                        # JSON {windows_done, windows_total}
    Column("error", Text),                           # nullable
    Column("summary_metrics", Text),                 # JSON, nullable
    Column("walkforward_windows", Text),             # JSON, nullable
    Column("param_sweep", Text),                     # JSON, nullable
)

strategy_equity = Table(
    "strategy_equity", metadata,
    Column("strategy_slug", String(64), primary_key=True),
    Column("date", String(10), primary_key=True),
    Column("equity", Float),
    Column("cash", Float),
    Column("gross_exposure", Float),
    Column("net_exposure", Float),
    Column("daily_return", Float),
    Column("phase", String(10)),                     # "backtest" | "forward"
)

strategy_trades = Table(
    "strategy_trades", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("strategy_slug", String(64), index=True),
    Column("date", String(10), index=True),
    Column("symbol", String(20)),
    Column("side", String(10)),                      # "buy"|"sell"|"short"|"cover"
    Column("qty", Integer),
    Column("price", Float),
    Column("commission", Float),
    Column("notional", Float),
    Column("phase", String(10)),
)

strategy_positions = Table(
    "strategy_positions", metadata,
    Column("strategy_slug", String(64), primary_key=True),
    Column("symbol", String(20), primary_key=True),
    Column("qty", Integer),
    Column("avg_cost", Float),
    Column("opened_at", String(10)),
    Column("last_marked_at", String(10)),
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


@dataclass
class ClusterRecord:
    """A clustered story as it is persisted — cluster metadata plus the
    article rows that belong to it. `articles` is empty for list loads."""
    id: str
    headline: str
    summary: str
    category: str
    source_count: int
    article_count: int
    momentum: float
    status: str
    first_published_at: str
    latest_published_at: str
    centroid: list[float]
    rank_order: int
    articles: list[Article] = field(default_factory=list)


def _cluster_from_row(row, articles: list[Article]) -> ClusterRecord:
    return ClusterRecord(
        id=row["id"], headline=row["headline"], summary=row["summary"],
        category=row["category"], source_count=row["source_count"],
        article_count=row["article_count"], momentum=row["momentum"],
        status=row["status"], first_published_at=row["first_published_at"],
        latest_published_at=row["latest_published_at"],
        centroid=json.loads(row["centroid"]) if row["centroid"] else [],
        rank_order=row["rank_order"], articles=articles)


def _article_from_row(row) -> Article:
    return Article(id=row["id"], title=row["title"], summary=row["summary"],
                   url=row["url"], source=row["source"],
                   published_at=row["published_at"], category=row["category"],
                   image_url=row["image_url"])


def save_news(clusters: list[ClusterRecord]) -> None:
    """Replace the entire news snapshot — clusters and their articles."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(delete(news_articles))
        conn.execute(delete(news_clusters))
        cluster_rows = []
        article_rows = []
        for c in clusters:
            cluster_rows.append({
                "id": c.id, "headline": c.headline, "summary": c.summary,
                "category": c.category, "source_count": c.source_count,
                "article_count": c.article_count, "momentum": c.momentum,
                "status": c.status,
                "first_published_at": c.first_published_at,
                "latest_published_at": c.latest_published_at,
                "centroid": json.dumps(c.centroid),
                "rank_order": c.rank_order})
            for a in c.articles:
                article_rows.append({
                    "id": a.id, "cluster_id": c.id, "title": a.title,
                    "summary": a.summary, "url": a.url, "source": a.source,
                    "published_at": a.published_at, "category": a.category,
                    "image_url": a.image_url})
        if cluster_rows:
            conn.execute(insert(news_clusters), cluster_rows)
        if article_rows:
            conn.execute(insert(news_articles), article_rows)


def load_news_clusters() -> list[ClusterRecord]:
    """All cluster snapshots, ordered by rank (top story first). Articles
    are not loaded — use `load_news_cluster` for one cluster's articles."""
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            select(news_clusters).order_by(news_clusters.c.rank_order)
        ).mappings().all()
    return [_cluster_from_row(r, []) for r in rows]


def load_news_cluster(cluster_id: str) -> ClusterRecord | None:
    """One cluster snapshot with all of its articles, oldest-first."""
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            select(news_clusters).where(news_clusters.c.id == cluster_id)
        ).mappings().first()
        if row is None:
            return None
        art_rows = conn.execute(
            select(news_articles)
            .where(news_articles.c.cluster_id == cluster_id)
            .order_by(news_articles.c.published_at)
        ).mappings().all()
    return _cluster_from_row(row, [_article_from_row(a) for a in art_rows])
