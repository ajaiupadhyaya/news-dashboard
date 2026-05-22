from datetime import datetime, timedelta, timezone

from app.models import Article
from app.providers import news_api_provider, rss_provider
from app.services import embeddings, news_service


def _article(i, hours_ago, source=None):
    now = datetime.now(timezone.utc)
    return Article(
        id=f"a{i}", title=f"Story {i}", summary="summary text",
        url=f"https://ex.com/{i}", source=source or f"Source {i}",
        published_at=(now - timedelta(hours=hours_ago)).isoformat(),
        category="general")


def _patch_sources(monkeypatch, articles, vectors):
    monkeypatch.setattr(rss_provider, "get_articles", lambda: articles)
    monkeypatch.setattr(news_api_provider, "get_articles", lambda: [])
    monkeypatch.setattr(embeddings, "embed", lambda texts: vectors)


def test_refresh_news_clusters_and_persists(db, monkeypatch):
    # Articles oldest-first: a2 (3h), a1 (2h), a0 (1h). embed() receives them
    # in that order — the first two vectors are similar, the third distinct.
    articles = [_article(0, 1), _article(1, 2), _article(2, 3)]
    _patch_sources(monkeypatch, articles,
                   [[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]])
    news_service.refresh_news()

    from app.database import load_news_clusters
    clusters = load_news_clusters()
    assert len(clusters) == 2          # one 2-article cluster, one singleton
    assert clusters[0].rank_order == 0


def test_refresh_news_no_articles_is_a_noop(db, monkeypatch):
    _patch_sources(monkeypatch, [], [])
    news_service.refresh_news()        # must not raise
    from app.database import load_news_clusters
    assert load_news_clusters() == []


def test_refresh_news_falls_back_when_embeddings_unavailable(db, monkeypatch):
    articles = [_article(0, 1), _article(1, 2)]
    # embeddings.embed returns [] -> title fallback; distinct titles -> 2
    _patch_sources(monkeypatch, articles, [])
    news_service.refresh_news()
    from app.database import load_news_clusters
    assert len(load_news_clusters()) == 2


def test_build_overview_returns_ranked_stories(db, monkeypatch):
    articles = [_article(0, 1), _article(1, 2), _article(2, 3)]
    _patch_sources(monkeypatch, articles,
                   [[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]])
    news_service.refresh_news()
    overview = news_service.build_overview()
    assert len(overview.stories) == 2
    assert overview.updated_at
    assert overview.stories[0].status in ("surging", "steady", "fading")


def test_build_overview_empty_when_nothing_persisted(db):
    overview = news_service.build_overview()
    assert overview.stories == []
    assert overview.updated_at


def test_build_story_returns_detail_with_timeline(db, monkeypatch):
    articles = [_article(0, 1), _article(1, 2), _article(2, 3)]
    _patch_sources(monkeypatch, articles,
                   [[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]])
    news_service.refresh_news()
    overview = news_service.build_overview()
    detail = news_service.build_story(overview.stories[0].id)
    assert detail is not None
    assert detail.id == overview.stories[0].id
    assert len(detail.articles) >= 1
    assert isinstance(detail.momentum_series, list)
    assert isinstance(detail.related, list)


def test_build_story_unknown_id_returns_none(db):
    assert news_service.build_story("does-not-exist") is None
