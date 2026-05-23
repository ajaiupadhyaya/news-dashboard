from datetime import date

from sqlalchemy import insert, select

from app.database import bar_cache, get_engine


def test_bar_cache_insert_and_read(db):
    with get_engine().begin() as conn:
        conn.execute(insert(bar_cache).values(
            symbol="SPY", date="2026-01-02",
            open=470.0, high=472.5, low=469.0, close=471.2, adj_close=471.2,
            volume=80_000_000, source="yfinance",
            fetched_at="2026-01-02T22:00:00Z",
        ))
        row = conn.execute(
            select(bar_cache).where(bar_cache.c.symbol == "SPY")
        ).first()
    assert row.close == 471.2
    assert row.adj_close == 471.2
    assert row.source == "yfinance"


def test_bar_cache_primary_key_is_symbol_date(db):
    with get_engine().begin() as conn:
        conn.execute(insert(bar_cache).values(
            symbol="SPY", date="2026-01-02", open=1, high=1, low=1, close=1,
            adj_close=1, volume=1, source="yfinance", fetched_at="x",
        ))
        # Re-inserting the same (symbol, date) must violate the PK.
        import pytest
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            conn.execute(insert(bar_cache).values(
                symbol="SPY", date="2026-01-02", open=2, high=2, low=2, close=2,
                adj_close=2, volume=2, source="yfinance", fetched_at="x",
            ))


def test_strategies_row(db):
    from app.database import strategies
    with get_engine().begin() as conn:
        conn.execute(insert(strategies).values(
            slug="buy-hold-spy",
            name="Buy & Hold SPY",
            category="benchmark",
            methodology_blurb="Always long SPY.",
            universe_kind="spy",
            inception_date="2015-01-02",
            live_start_date="2025-01-02",
            chosen_params="{}",                # JSON-encoded
            cost_model='{"commission":0,"slippage_bps":5,"allow_short":false}',
            enabled=1,
            last_forward_step_date=None,
        ))
        row = conn.execute(
            select(strategies).where(strategies.c.slug == "buy-hold-spy")
        ).first()
    assert row.name == "Buy & Hold SPY"
    assert row.universe_kind == "spy"


def test_strategy_runs_row(db):
    from app.database import strategy_runs
    with get_engine().begin() as conn:
        rid = conn.execute(insert(strategy_runs).values(
            strategy_slug="buy-hold-spy",
            run_kind="inception-walkforward",
            started_at="2026-05-22T22:00:00Z",
            finished_at=None,
            status="running",
            progress='{"windows_done":0,"windows_total":8}',
            error=None,
            summary_metrics=None,
            walkforward_windows=None,
            param_sweep=None,
        )).inserted_primary_key[0]
    assert rid is not None


def test_strategy_equity_pk_is_slug_date(db):
    from app.database import strategy_equity
    import pytest
    from sqlalchemy.exc import IntegrityError
    with get_engine().begin() as conn:
        conn.execute(insert(strategy_equity).values(
            strategy_slug="buy-hold-spy", date="2026-01-02",
            equity=100_000.0, cash=0.0,
            gross_exposure=100_000.0, net_exposure=100_000.0,
            daily_return=0.0, phase="forward",
        ))
        with pytest.raises(IntegrityError):
            conn.execute(insert(strategy_equity).values(
                strategy_slug="buy-hold-spy", date="2026-01-02",
                equity=99_000.0, cash=0.0,
                gross_exposure=99_000.0, net_exposure=99_000.0,
                daily_return=-0.01, phase="forward",
            ))


def test_strategy_trades_round_trip(db):
    from app.database import strategy_trades
    with get_engine().begin() as conn:
        tid = conn.execute(insert(strategy_trades).values(
            strategy_slug="sma-crossover", date="2026-01-02", symbol="SPY",
            side="buy", qty=100, price=471.5, commission=0.0,
            notional=47_150.0, phase="forward",
        )).inserted_primary_key[0]
        row = conn.execute(
            select(strategy_trades).where(strategy_trades.c.id == tid)
        ).first()
    assert row.symbol == "SPY"
    assert row.side == "buy"
    assert row.qty == 100


def test_strategy_positions_pk_is_slug_symbol(db):
    from app.database import strategy_positions
    import pytest
    from sqlalchemy.exc import IntegrityError
    with get_engine().begin() as conn:
        conn.execute(insert(strategy_positions).values(
            strategy_slug="buy-hold-spy", symbol="SPY",
            qty=210, avg_cost=470.5,
            opened_at="2025-01-02", last_marked_at="2026-01-02",
        ))
        with pytest.raises(IntegrityError):
            conn.execute(insert(strategy_positions).values(
                strategy_slug="buy-hold-spy", symbol="SPY",
                qty=1, avg_cost=1.0,
                opened_at="x", last_marked_at="x",
            ))
