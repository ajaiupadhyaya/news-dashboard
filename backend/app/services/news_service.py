"""Assembles the News domain. `refresh_news` runs the heavy fetch → embed →
cluster pipeline (scheduler only); `build_overview`/`build_story` read the
persisted snapshot (request path) — see Task 10."""
import hashlib
import logging
from datetime import datetime, timedelta, timezone

from app.analysis import news_clustering as nc
from app.analysis import news_metrics as nm
from app.database import (ClusterRecord, load_news_cluster,
                          load_news_clusters, save_news)
from app.models import (Article, MomentumPoint, NewsOverview, StoryCluster,
                        StoryDetail)
from app.providers import news_api_provider, rss_provider
from app.services import embeddings

logger = logging.getLogger(__name__)

WINDOW_HOURS = 48          # articles older than this are dropped
MAX_CLUSTERS = 40          # cluster snapshots persisted per refresh
OVERVIEW_LIMIT = 20        # stories returned by build_overview (Task 10)
RELATED_LIMIT = 4          # related stories on a drill-down (Task 10)
RELATED_MIN_SIMILARITY = 0.30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _gather_articles(now: datetime) -> list[Article]:
    """Fetch from RSS + the news API, dedup by id, keep the recent window,
    sorted oldest-first."""
    raw = list(rss_provider.get_articles())
    raw += list(news_api_provider.get_articles())
    cutoff = now - timedelta(hours=WINDOW_HOURS)
    deduped: dict[str, Article] = {}
    for article in raw:
        dt = nm.parse_timestamp(article.published_at)
        if dt is None or dt < cutoff or dt > now:
            continue
        deduped.setdefault(article.id, article)
    return sorted(deduped.values(), key=lambda a: a.published_at)


def _centroid(vectors: list[list[float]], group: list[int]) -> list[float]:
    """Mean embedding vector of a cluster's articles."""
    dim = len(vectors[group[0]])
    return [sum(vectors[i][d] for i in group) / len(group)
            for d in range(dim)]


def _build_records(articles: list[Article], groups: list[list[int]],
                   vectors: list[list[float]] | None,
                   now: datetime) -> list[ClusterRecord]:
    """Turn index groups into ranked ClusterRecords (rank_order 0 = top)."""
    records: list[ClusterRecord] = []
    scores: list[float] = []
    for group in groups:
        members = sorted((articles[i] for i in group),
                         key=lambda a: a.published_at)
        pubs = [a.published_at for a in members]
        rep = members[nc.pick_representative(pubs)]
        source_count = len({a.source for a in members})
        momentum = nm.momentum_score(pubs, now)
        centroid = (_centroid(vectors, group)
                    if vectors is not None and group else [])
        cluster_id = hashlib.sha1(
            "|".join(sorted(a.id for a in members)).encode()).hexdigest()
        records.append(ClusterRecord(
            id=cluster_id, headline=rep.title, summary=rep.summary,
            category=rep.category, source_count=source_count,
            article_count=len(members), momentum=momentum,
            status=nm.momentum_status(momentum),
            first_published_at=pubs[0], latest_published_at=pubs[-1],
            centroid=centroid, rank_order=0, articles=members))
        scores.append(nm.rank_score(source_count, len(members), momentum))

    order = sorted(range(len(records)), key=lambda i: scores[i], reverse=True)
    ranked: list[ClusterRecord] = []
    for new_rank, idx in enumerate(order):
        records[idx].rank_order = new_rank
        ranked.append(records[idx])
    return ranked


def refresh_news() -> None:
    """Fetch, embed, cluster, rank, and persist. Run by the scheduler —
    never on the request path (it loads the embedding model)."""
    now = _now()
    articles = _gather_articles(now)
    if not articles:
        logger.info("refresh_news: no articles gathered")
        return

    texts = [f"{a.title}. {a.summary}" for a in articles]
    vectors = embeddings.embed(texts)
    if len(vectors) == len(articles) and vectors:
        groups = nc.cluster_articles(vectors)
        used_vectors: list[list[float]] | None = vectors
    else:
        logger.warning("refresh_news: embeddings unavailable — "
                       "falling back to title clustering")
        groups = nc.cluster_by_title([a.title for a in articles])
        used_vectors = None

    records = _build_records(articles, groups, used_vectors, now)
    save_news(records[:MAX_CLUSTERS])
    logger.info("refresh_news: saved %d clusters from %d articles",
                min(len(records), MAX_CLUSTERS), len(articles))


def _to_story_cluster(record: ClusterRecord) -> StoryCluster:
    return StoryCluster(
        id=record.id, headline=record.headline, summary=record.summary,
        category=record.category, source_count=record.source_count,
        article_count=record.article_count, momentum=record.momentum,
        status=record.status,
        latest_published_at=record.latest_published_at)


def build_overview() -> NewsOverview:
    """The News overview — the top-ranked story clusters. Reads the
    persisted snapshot; empty-but-valid when nothing has been ingested."""
    clusters = load_news_clusters()
    stories = [_to_story_cluster(c) for c in clusters[:OVERVIEW_LIMIT]]
    return NewsOverview(stories=stories, updated_at=_now().isoformat())


def _momentum_series(articles: list[Article]) -> list[MomentumPoint]:
    """Hourly article counts across the cluster's coverage span."""
    buckets: dict[str, int] = {}
    for article in articles:
        dt = nm.parse_timestamp(article.published_at)
        if dt is None:
            continue
        hour = dt.replace(minute=0, second=0, microsecond=0)
        key = hour.isoformat()
        buckets[key] = buckets.get(key, 0) + 1
    return [MomentumPoint(time=k, count=buckets[k]) for k in sorted(buckets)]


def _related(cluster: ClusterRecord) -> list[StoryCluster]:
    """Other clusters most similar to `cluster` by centroid cosine."""
    if not cluster.centroid:
        return []
    scored: list[tuple[float, ClusterRecord]] = []
    for other in load_news_clusters():
        if other.id == cluster.id or not other.centroid:
            continue
        sim = nc.cosine_similarity(cluster.centroid, other.centroid)
        if sim >= RELATED_MIN_SIMILARITY:
            scored.append((sim, other))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [_to_story_cluster(o) for _, o in scored[:RELATED_LIMIT]]


def build_story(cluster_id: str) -> StoryDetail | None:
    """The drill-down for one story cluster. None if the id is unknown."""
    cluster = load_news_cluster(cluster_id)
    if cluster is None:
        return None
    return StoryDetail(
        id=cluster.id, headline=cluster.headline, summary=cluster.summary,
        category=cluster.category, source_count=cluster.source_count,
        article_count=cluster.article_count, momentum=cluster.momentum,
        status=cluster.status, articles=cluster.articles,
        momentum_series=_momentum_series(cluster.articles),
        related=_related(cluster), updated_at=_now().isoformat())
