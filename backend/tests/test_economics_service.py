from app.models import IndicatorPoint, ReleaseEvent
from app.providers import fred_provider
from app.services import economics_service


def _series(n, start=100.0, step=1.0):
    return [IndicatorPoint(date=f"2026-{(i % 12) + 1:02d}-01",
                           value=start + i * step) for i in range(n)]


def test_build_overview_assembles_indicators_and_calendar(db, monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series",
                        lambda series_id, **kw: _series(30))
    monkeypatch.setattr(fred_provider, "get_release_calendar",
                        lambda: [ReleaseEvent(date="2026-05-13",
                                              release_name="CPI")])
    overview = economics_service.build_overview()
    assert len(overview.indicators) == len(economics_service.OVERVIEW_IDS)
    first = overview.indicators[0]
    assert first.series_id
    assert first.sparkline           # non-empty
    assert first.trend in ("below", "in", "above")
    assert overview.calendar[0].release_name == "CPI"
    assert overview.updated_at


def test_build_overview_skips_failed_series(db, monkeypatch):
    # One bad series must not blank the panel (per-indicator isolation).
    monkeypatch.setattr(fred_provider, "get_series", lambda series_id, **kw: [])
    monkeypatch.setattr(fred_provider, "get_release_calendar", lambda: [])
    overview = economics_service.build_overview()
    assert overview.indicators == []
    assert overview.updated_at


def test_build_indicator_returns_detail(db, monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series",
                        lambda series_id, **kw: _series(40))
    detail = economics_service.build_indicator("UNRATE")
    assert detail is not None
    assert detail.series_id == "UNRATE"
    assert len(detail.series) == 40
    assert detail.range_low <= detail.latest <= detail.range_high
    assert len(detail.recession_signals) == 2


def test_build_indicator_none_for_unknown(db, monkeypatch):
    detail = economics_service.build_indicator("NOT_A_SERIES")
    assert detail is None


def test_build_indicator_none_when_no_data(db, monkeypatch):
    monkeypatch.setattr(fred_provider, "get_series", lambda series_id, **kw: [])
    assert economics_service.build_indicator("UNRATE") is None


def test_indicator_registry_is_categorized():
    from app.services import economics_service as es
    assert len(es.INDICATORS) == 20
    assert es.CATEGORY_ORDER == [
        "Growth", "Inflation", "Labor", "Rates", "Housing", "Consumer"]
    assert all(ind.category in es.CATEGORY_ORDER for ind in es.INDICATORS)
    ids = {ind.series_id for ind in es.INDICATORS}
    assert len(ids) == 20                         # no duplicates
    assert set(es.OVERVIEW_IDS).issubset(ids)


def test_scale_points_multiplies_raw_values():
    from app.models import IndicatorPoint
    from app.services.economics_service import _scale_points
    pts = [IndicatorPoint(date="2026-01-01", value=220000.0),
           IndicatorPoint(date="2026-01-08", value=235000.0)]
    scaled = _scale_points(pts, 0.001)
    assert [p.value for p in scaled] == [220.0, 235.0]
    # identity (same object) when scale == 1.0
    assert _scale_points(pts, 1.0) is pts
