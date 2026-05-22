from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import Article
from app.providers import news_api_provider, rss_provider
from app.services import embeddings, news_service

client = TestClient(app)


def _seed(monkeypatch):
    now = datetime.now(timezone.utc)
    articles = [
        Article(id=f"a{i}", title=f"Story {i}", summary="summary",
                url=f"https://ex.com/{i}", source=f"Source {i}",
                published_at=(now - timedelta(hours=i + 1)).isoformat(),
                category="general")
        for i in range(3)
    ]
    monkeypatch.setattr(rss_provider, "get_articles", lambda: articles)
    monkeypatch.setattr(news_api_provider, "get_articles", lambda: [])
    monkeypatch.setattr(embeddings, "embed",
                        lambda texts: [[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]])


def test_news_overview_endpoint(db, monkeypatch):
    _seed(monkeypatch)
    news_service.refresh_news()
    resp = client.get("/api/news/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert "stories" in body
    assert "updated_at" in body


def test_news_story_endpoint(db, monkeypatch):
    _seed(monkeypatch)
    news_service.refresh_news()
    cluster_id = news_service.build_overview().stories[0].id
    resp = client.get(f"/api/news/story/{cluster_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cluster_id


def test_news_story_404_for_unknown(db):
    resp = client.get("/api/news/story/not-a-real-cluster")
    assert resp.status_code == 404
