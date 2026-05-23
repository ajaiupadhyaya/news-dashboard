import pandas as pd
from sqlalchemy import insert

from app.database import econ_series, get_engine
from app.quant.econ_signal import classify_regime, load_series


def _seed(db, rows):
    with get_engine().begin() as conn:
        conn.execute(insert(econ_series), rows)


def test_load_series_returns_dated_floats(db):
    _seed(db, [
        {"series_id": "T10Y2Y", "date": "2026-01-02", "value": 0.5},
        {"series_id": "T10Y2Y", "date": "2026-01-03", "value": 0.4},
        {"series_id": "T10Y2Y", "date": "2026-01-04", "value": 0.3},
    ])
    s = load_series("T10Y2Y", start="2026-01-01", end="2026-12-31")
    assert isinstance(s, pd.Series)
    assert s.loc["2026-01-02"] == 0.5
    assert len(s) == 3


def test_classify_regime_risk_off_when_yield_curve_inverted(db):
    _seed(db, [
        {"series_id": "T10Y2Y", "date": "2026-05-01", "value": -0.3},
        {"series_id": "UNRATE", "date": "2026-04-01", "value": 4.0},
        {"series_id": "UNRATE", "date": "2026-05-01", "value": 4.3},
        {"series_id": "INDPRO", "date": "2026-04-01", "value": 102.0},
        {"series_id": "INDPRO", "date": "2026-05-01", "value": 101.5},
    ])
    regime = classify_regime(as_of="2026-05-15")
    assert regime == "risk_off"


def test_classify_regime_risk_on_when_curve_steep(db):
    _seed(db, [
        {"series_id": "T10Y2Y", "date": "2026-05-01", "value": 1.2},
        {"series_id": "UNRATE", "date": "2026-04-01", "value": 3.8},
        {"series_id": "UNRATE", "date": "2026-05-01", "value": 3.7},
        {"series_id": "INDPRO", "date": "2026-04-01", "value": 101.0},
        {"series_id": "INDPRO", "date": "2026-05-01", "value": 101.5},
    ])
    regime = classify_regime(as_of="2026-05-15")
    assert regime == "risk_on"
