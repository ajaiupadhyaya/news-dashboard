import pytest

from app.analysis import metrics


def test_simple_returns():
    assert metrics.simple_returns([100.0, 110.0, 99.0]) == pytest.approx([0.1, -0.1])


def test_simple_returns_short_input():
    assert metrics.simple_returns([100.0]) == []


def test_momentum():
    prices = [10.0, 11.0, 12.0, 15.0]
    assert metrics.momentum(prices, 3) == pytest.approx(0.5)


def test_momentum_insufficient_history():
    assert metrics.momentum([10.0, 11.0], 5) == 0.0


def test_annualized_volatility_zero_for_short_input():
    assert metrics.annualized_volatility([0.01]) == 0.0


def test_annualized_volatility_positive():
    assert metrics.annualized_volatility([0.01, -0.02, 0.015, -0.005]) > 0


def test_sma_pads_with_none():
    result = metrics.sma([1.0, 2.0, 3.0, 4.0], 3)
    assert result[:2] == [None, None]
    assert result[2] == pytest.approx(2.0)
    assert result[3] == pytest.approx(3.0)


def test_downsample_keeps_endpoints():
    values = [float(i) for i in range(100)]
    out = metrics.downsample(values, 10)
    assert len(out) == 10
    assert out[0] == 0.0
    assert out[-1] == 99.0


def test_downsample_passthrough_when_short():
    assert metrics.downsample([1.0, 2.0], 10) == [1.0, 2.0]


def test_breadth_counts():
    result = metrics.breadth([1.5, -0.5, 0.0, 2.0, -1.0])
    assert result["advancers"] == 2
    assert result["decliners"] == 2
    assert result["unchanged"] == 1
    assert result["advance_decline_ratio"] == pytest.approx(1.0)


def test_rsi_all_gains_is_100():
    rising = [float(i) for i in range(1, 40)]
    out = metrics.rsi(rising, period=14)
    assert out[:14] == [None] * 14          # not enough deltas yet
    assert out[14] == 100.0                 # only gains -> RSI 100
    assert out[-1] == 100.0


def test_rsi_all_losses_is_zero():
    falling = [float(i) for i in range(40, 1, -1)]
    out = metrics.rsi(falling, period=14)
    assert out[-1] == 0.0


def test_rsi_short_series_is_all_none():
    assert metrics.rsi([1.0, 2.0, 3.0], period=14) == [None, None, None]


def test_macd_shapes_and_alignment():
    prices = [float(i) for i in range(60)]
    m = metrics.macd(prices)
    assert set(m.keys()) == {"macd", "signal", "histogram"}
    assert len(m["macd"]) == 60
    assert m["macd"][:25] == [None] * 25          # None until slow EMA fills
    assert m["macd"][25] is not None
    assert m["signal"][-1] is not None
    assert m["histogram"][-1] is not None


def test_macd_short_series_is_all_none():
    m = metrics.macd([1.0, 2.0, 3.0])
    assert m["macd"] == [None, None, None]
    assert m["signal"] == [None, None, None]
