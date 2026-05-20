import pandas as pd

from app.providers import yfinance_provider


class FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    def history(self, period="1y", interval="1d", auto_adjust=True):
        idx = pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-04"])
        return pd.DataFrame(
            {
                "Open": [100.0, 102.0, 101.0],
                "High": [103.0, 104.0, 102.5],
                "Low": [99.0, 101.0, 100.0],
                "Close": [102.0, 101.0, 102.5],
                "Volume": [1000, 1200, 900],
            },
            index=idx,
        )

    @property
    def info(self):
        return {
            "longName": "Fake Corp", "sector": "Technology",
            "industry": "Software", "marketCap": 1_000_000.0,
            "trailingPE": 25.0, "fiftyTwoWeekHigh": 110.0,
            "fiftyTwoWeekLow": 80.0,
        }


class FakeYF:
    Ticker = FakeTicker


def test_get_history_returns_bars(monkeypatch):
    monkeypatch.setattr(yfinance_provider, "yf", FakeYF)
    bars = yfinance_provider.get_history("AAPL")
    assert len(bars) == 3
    assert bars[0].date == "2026-01-02"
    assert bars[-1].close == 102.5
    assert bars[-1].volume == 900


def test_get_quote_computes_change(monkeypatch):
    monkeypatch.setattr(yfinance_provider, "yf", FakeYF)
    q = yfinance_provider.get_quote("AAPL")
    assert q.symbol == "AAPL"
    assert q.price == 102.5
    assert q.change == round(102.5 - 101.0, 4)
    assert q.change_pct == round((1.5 / 101.0) * 100, 4)


def test_get_fundamentals_maps_info(monkeypatch):
    monkeypatch.setattr(yfinance_provider, "yf", FakeYF)
    f = yfinance_provider.get_fundamentals("AAPL")
    assert f.name == "Fake Corp"
    assert f.sector == "Technology"
    assert f.pe_ratio == 25.0


def test_get_history_returns_empty_on_error(monkeypatch):
    class BoomTicker:
        def __init__(self, symbol):
            raise RuntimeError("network down")

    class BoomYF:
        Ticker = BoomTicker

    monkeypatch.setattr(yfinance_provider, "yf", BoomYF)
    assert yfinance_provider.get_history("AAPL") == []
    assert yfinance_provider.get_quote("AAPL") is None


def test_get_fundamentals_returns_none_on_error(monkeypatch):
    class BoomTicker:
        def __init__(self, symbol):
            pass

        @property
        def info(self):
            raise RuntimeError("network down")

    class BoomYF:
        Ticker = BoomTicker

    monkeypatch.setattr(yfinance_provider, "yf", BoomYF)
    assert yfinance_provider.get_fundamentals("AAPL") is None
