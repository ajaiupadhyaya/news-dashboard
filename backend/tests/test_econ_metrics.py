from app.analysis import econ_metrics as em
from app.models import IndicatorPoint


def _points(pairs):
    return [IndicatorPoint(date=d, value=v) for d, v in pairs]


def test_period_change_is_latest_minus_prior():
    assert em.period_change([4.3, 4.2, 4.1]) == -0.1
    assert em.period_change([4.1]) == 0.0


def test_pct_change():
    assert em.pct_change([100.0, 110.0]) == 10.0
    assert em.pct_change([100.0]) is None


def test_trend_marker_buckets_position_in_range():
    # latest near the bottom of the trailing range -> "below"
    assert em.trend_marker([10, 9, 8, 7, 6, 5, 4]) == "below"
    # latest near the top -> "above"
    assert em.trend_marker([4, 5, 6, 7, 8, 9, 10]) == "above"
    # latest mid-range -> "in"
    assert em.trend_marker([4, 10, 5, 9, 6, 8, 7]) == "in"
    # too little history -> "in"
    assert em.trend_marker([5.0]) == "in"


def test_yoy_change_uses_observation_a_year_back():
    pts = _points([(f"2025-{m:02d}-01", 100.0) for m in range(1, 13)]
                  + [("2026-01-01", 106.0)])
    # 2026-01-01 vs 2025-01-01 -> +6%
    assert em.yoy_change(pts) == 6.0
    assert em.yoy_change(_points([("2026-01-01", 1.0)])) is None


def test_momentum_score_recent_direction():
    rising = [float(i) for i in range(20)]
    assert em.momentum_score(rising) > 0
    falling = [float(20 - i) for i in range(20)]
    assert em.momentum_score(falling) < 0


def test_recession_status_yield_curve():
    assert em.recession_status("yield_curve", -0.2)[0] == "alert"
    assert em.recession_status("yield_curve", 0.3)[0] == "warning"
    assert em.recession_status("yield_curve", 1.5)[0] == "normal"


def test_recession_status_sahm():
    assert em.recession_status("sahm", 0.6)[0] == "alert"
    assert em.recession_status("sahm", 0.35)[0] == "warning"
    assert em.recession_status("sahm", 0.1)[0] == "normal"
