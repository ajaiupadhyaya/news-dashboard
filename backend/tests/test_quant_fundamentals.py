from unittest.mock import patch

import pytest

from app.quant.fundamentals import (
    Fundamentals, clear_cache, get_fundamentals, get_fundamentals_batch,
)


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_FUNDAMENTALS_CACHE", str(tmp_path / "f.json"))
    clear_cache()
    yield
    clear_cache()


def test_get_fundamentals_uses_yfinance_first_time():
    with patch("app.quant.fundamentals._fetch_yf") as mocked:
        mocked.return_value = {"priceToBook": 5.0, "returnOnEquity": 0.18}
        f = get_fundamentals("AAPL")
    assert isinstance(f, Fundamentals)
    assert f.price_to_book == 5.0
    assert f.roe == 0.18


def test_get_fundamentals_hits_cache_second_time():
    with patch("app.quant.fundamentals._fetch_yf") as mocked:
        mocked.return_value = {"priceToBook": 5.0, "returnOnEquity": 0.18}
        get_fundamentals("AAPL")
        get_fundamentals("AAPL")
        assert mocked.call_count == 1


def test_get_fundamentals_missing_fields_return_none():
    with patch("app.quant.fundamentals._fetch_yf") as mocked:
        mocked.return_value = {}
        f = get_fundamentals("XXX")
    assert f.price_to_book is None
    assert f.roe is None


def test_get_fundamentals_batch_uses_one_call_per_uncached():
    with patch("app.quant.fundamentals._fetch_yf") as mocked:
        mocked.return_value = {"priceToBook": 1.0, "returnOnEquity": 0.05}
        out = get_fundamentals_batch(["AAPL", "MSFT"])
        assert mocked.call_count == 2
        assert set(out.keys()) == {"AAPL", "MSFT"}
