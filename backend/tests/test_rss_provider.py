import time

from app.providers import rss_provider


class FakeEntry(dict):
    """Stand-in for a feedparser entry — attribute access over a dict."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key) from None


def _fake_feedparser(entries):
    class FakeParsed:
        pass
    parsed = FakeParsed()
    parsed.entries = entries

    class FakeFeedparser:
        @staticmethod
        def parse(url):
            return parsed
    return FakeFeedparser


def test_get_articles_parses_and_cleans_entries(monkeypatch):
    entry = FakeEntry(
        title="Big <b>Story</b>", link="https://ex.com/1",
        summary="A <i>summary</i> here",
        published_parsed=time.struct_time((2026, 5, 22, 10, 0, 0, 0, 0, 0)))
    monkeypatch.setattr(rss_provider, "feedparser",
                        _fake_feedparser([entry]))
    monkeypatch.setattr(rss_provider, "RSS_FEEDS",
                        [("https://feed", "Test Source", "general")])
    articles = rss_provider.get_articles()
    assert len(articles) == 1
    a = articles[0]
    assert a.title == "Big Story"            # HTML stripped
    assert a.summary == "A summary here"
    assert a.source == "Test Source"
    assert a.category == "general"
    assert a.published_at.startswith("2026-05-22T10:00:00")
    assert a.id                              # a non-empty hash


def test_get_articles_skips_entries_without_link_or_title(monkeypatch):
    good = FakeEntry(title="Has link", link="https://ex.com/ok")
    no_link = FakeEntry(title="No link")
    monkeypatch.setattr(rss_provider, "feedparser",
                        _fake_feedparser([good, no_link]))
    monkeypatch.setattr(rss_provider, "RSS_FEEDS",
                        [("https://feed", "Src", "general")])
    articles = rss_provider.get_articles()
    assert [a.title for a in articles] == ["Has link"]


def test_get_articles_skips_a_failing_feed(monkeypatch):
    class BoomFeedparser:
        @staticmethod
        def parse(url):
            raise RuntimeError("feed unreachable")
    monkeypatch.setattr(rss_provider, "feedparser", BoomFeedparser)
    monkeypatch.setattr(rss_provider, "RSS_FEEDS",
                        [("https://feed", "Src", "general")])
    assert rss_provider.get_articles() == []
