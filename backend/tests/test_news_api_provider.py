from app.providers import news_api_provider


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _fake_httpx(payload):
    class FakeHttpx:
        @staticmethod
        def get(url, params=None, timeout=None):
            return FakeResponse(payload)
    return FakeHttpx


def test_get_articles_parses_results(monkeypatch):
    monkeypatch.setenv("NEWS_API_KEY", "k")
    monkeypatch.setattr(news_api_provider, "httpx", _fake_httpx({
        "status": "success",
        "results": [
            {"title": "A story", "link": "https://ex.com/a",
             "description": "Body text", "source_name": "Example",
             "pubDate": "2026-05-22 09:30:00", "category": ["world"],
             "image_url": "https://ex.com/a.jpg"},
            {"title": None, "link": "https://ex.com/skip"},  # no title -> skip
        ]}))
    articles = news_api_provider.get_articles()
    assert len(articles) == 1
    a = articles[0]
    assert a.title == "A story"
    assert a.source == "Example"
    assert a.category == "world"
    assert a.published_at.startswith("2026-05-22T09:30:00")
    assert a.image_url == "https://ex.com/a.jpg"


def test_get_articles_empty_without_api_key(monkeypatch):
    monkeypatch.delenv("NEWS_API_KEY", raising=False)
    assert news_api_provider.get_articles() == []


def test_get_articles_empty_on_error(monkeypatch):
    monkeypatch.setenv("NEWS_API_KEY", "k")

    class BoomHttpx:
        @staticmethod
        def get(url, params=None, timeout=None):
            raise RuntimeError("network down")

    monkeypatch.setattr(news_api_provider, "httpx", BoomHttpx)
    assert news_api_provider.get_articles() == []
