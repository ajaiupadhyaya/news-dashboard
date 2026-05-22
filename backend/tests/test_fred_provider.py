from app.providers import fred_provider


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


def test_get_series_parses_observations(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    monkeypatch.setattr(fred_provider, "httpx", _fake_httpx({
        "observations": [
            {"date": "2026-01-01", "value": "2.9"},
            {"date": "2026-02-01", "value": "."},      # missing — skipped
            {"date": "2026-03-01", "value": "3.1"},
        ]}))
    points = fred_provider.get_series("CPIAUCSL")
    assert [p.date for p in points] == ["2026-01-01", "2026-03-01"]
    assert points[-1].value == 3.1


def test_get_series_empty_without_api_key(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    assert fred_provider.get_series("CPIAUCSL") == []


def test_get_series_empty_on_error(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")

    class BoomHttpx:
        @staticmethod
        def get(url, params=None, timeout=None):
            raise RuntimeError("network down")

    monkeypatch.setattr(fred_provider, "httpx", BoomHttpx)
    assert fred_provider.get_series("CPIAUCSL") == []


def test_get_release_calendar_parses_dates(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    monkeypatch.setattr(fred_provider, "httpx", _fake_httpx({
        "release_dates": [
            {"release_id": 10, "release_name": "Consumer Price Index",
             "date": "2026-05-13"},
            {"release_id": 50, "release_name": "Employment Situation",
             "date": "2026-05-02"},
        ]}))
    cal = fred_provider.get_release_calendar()
    assert cal[0].release_name == "Consumer Price Index"
    assert cal[1].date == "2026-05-02"


def test_get_recession_periods_derives_intervals(monkeypatch):
    from app.models import IndicatorPoint
    monkeypatch.setattr(fred_provider, "get_series", lambda sid, **kw: [
        IndicatorPoint(date="2020-01-01", value=0),
        IndicatorPoint(date="2020-02-01", value=1),
        IndicatorPoint(date="2020-03-01", value=0),
    ])
    periods = fred_provider.get_recession_periods()
    assert len(periods) == 1
    assert periods[0].start == "2020-02-01"
    assert periods[0].end == "2020-03-01"


def test_get_recession_periods_empty_on_failure(monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series", lambda sid, **kw: [])
    assert fred_provider.get_recession_periods() == []
