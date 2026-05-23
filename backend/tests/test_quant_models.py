from app.models import (
    StrategyMeta, EquityPoint, TradeRecord, WalkforwardWindow,
    ParameterSweepCell, RunStatus, CostModelSchema, TearSheetMetrics,
)


def test_strategy_meta_constructs():
    m = StrategyMeta(
        slug="buy-hold-spy", name="Buy & Hold SPY",
        category="benchmark", methodology_blurb="Always long SPY.",
        universe_kind="spy", inception_date="2015-01-02",
        live_start_date="2025-01-02",
        chosen_params={}, enabled=True,
    )
    assert m.slug == "buy-hold-spy"
    assert m.enabled is True


def test_equity_point_phases():
    p = EquityPoint(date="2026-01-02", equity=100_000.0, cash=0.0,
                    gross_exposure=100_000.0, net_exposure=100_000.0,
                    daily_return=0.0, phase="backtest")
    assert p.phase == "backtest"


def test_trade_record_basic():
    t = TradeRecord(date="2026-01-02", symbol="SPY", side="buy",
                    qty=100, price=471.5, commission=0.0,
                    notional=47_150.0, phase="forward")
    assert t.side == "buy"


def test_walkforward_window_metrics():
    w = WalkforwardWindow(
        train_start="2015-01-02", train_end="2017-12-29",
        test_start="2018-01-02", test_end="2018-12-31",
        chosen_params={"fast": 20, "slow": 100},
        oos_metrics={"sharpe": 0.42, "cagr": 0.07},
    )
    assert w.oos_metrics["sharpe"] == 0.42


def test_parameter_sweep_cell():
    c = ParameterSweepCell(params={"fast": 20, "slow": 100}, sharpe=0.7)
    assert c.params["fast"] == 20


def test_run_status_enum_values():
    s = RunStatus(status="running", progress={"windows_done": 1, "windows_total": 8},
                  error=None)
    assert s.status == "running"


def test_cost_model_schema_defaults():
    c = CostModelSchema()  # all defaults
    assert c.commission == 0.0
    assert c.slippage_bps == 5.0
    assert c.allow_short is False


def test_tear_sheet_metrics_fields():
    t = TearSheetMetrics(total_return=0.34, cagr=0.07, sharpe=0.9,
                         sortino=1.2, calmar=0.5, max_drawdown=-0.18,
                         win_rate=0.55, volatility=0.16)
    assert t.cagr == 0.07
