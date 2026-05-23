import json
from sqlalchemy import insert

from app.database import get_engine, strategies, strategy_runs


def test_overview_requires_auth(client):
    resp = client.get("/api/quant/overview")
    assert resp.status_code == 401


def test_overview_returns_payload(client, db, auth_headers):
    resp = client.get("/api/quant/overview", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "leaderboard" in body


def test_strategy_detail_404_when_unknown(client, db, auth_headers):
    resp = client.get("/api/quant/strategy/no-such-thing", headers=auth_headers)
    assert resp.status_code == 404


def test_strategy_detail_returns_payload(client, db, auth_headers):
    with get_engine().begin() as conn:
        conn.execute(insert(strategies).values(
            slug="buy-hold-spy", name="Buy Hold SPY", category="benchmark",
            methodology_blurb="x", universe_kind="spy",
            inception_date="2024-01-02", live_start_date="2025-01-02",
            chosen_params="{}",
            cost_model='{"commission":0,"slippage_bps":5,"allow_short":false}',
            enabled=1, last_forward_step_date=None,
        ))
    resp = client.get("/api/quant/strategy/buy-hold-spy", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["slug"] == "buy-hold-spy"


def test_recompute_backtest_returns_202_run_id(client, db, auth_headers, monkeypatch):
    # Patch the background job so it doesn't actually run the orchestrator.
    import app.routes.quant as quant_routes
    monkeypatch.setattr(quant_routes, "run_inception_walkforward_async", lambda slug: None)
    # Seed an enabled strategy.
    with get_engine().begin() as conn:
        conn.execute(insert(strategies).values(
            slug="buy-hold-spy", name="x", category="benchmark",
            methodology_blurb="x", universe_kind="spy",
            inception_date="2024-01-02", live_start_date="2025-01-02",
            chosen_params="{}",
            cost_model='{"commission":0,"slippage_bps":5,"allow_short":false}',
            enabled=1, last_forward_step_date=None,
        ))
    resp = client.post(
        "/api/quant/strategy/buy-hold-spy/recompute-backtest",
        headers=auth_headers,
    )
    assert resp.status_code == 202
    assert "run_id" in resp.json()


def test_recompute_backtest_409_if_in_flight(client, db, auth_headers):
    with get_engine().begin() as conn:
        conn.execute(insert(strategies).values(
            slug="buy-hold-spy", name="x", category="benchmark",
            methodology_blurb="x", universe_kind="spy",
            inception_date="2024-01-02", live_start_date="2025-01-02",
            chosen_params="{}",
            cost_model='{"commission":0,"slippage_bps":5,"allow_short":false}',
            enabled=1, last_forward_step_date=None,
        ))
        conn.execute(insert(strategy_runs).values(
            strategy_slug="buy-hold-spy", run_kind="inception-walkforward",
            started_at="2025-05-22T00:00:00Z", finished_at=None,
            status="running", progress="{}",
            summary_metrics=None, walkforward_windows=None, param_sweep=None,
        ))
    resp = client.post(
        "/api/quant/strategy/buy-hold-spy/recompute-backtest",
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_runs_endpoint_returns_status(client, db, auth_headers):
    with get_engine().begin() as conn:
        rid = conn.execute(insert(strategy_runs).values(
            strategy_slug="buy-hold-spy", run_kind="inception-walkforward",
            started_at="2025-05-22T00:00:00Z", finished_at=None,
            status="running", progress='{"windows_done":1,"windows_total":4}',
            summary_metrics=None, walkforward_windows=None, param_sweep=None,
        )).inserted_primary_key[0]
    resp = client.get(f"/api/quant/runs/{rid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"
