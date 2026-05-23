import pytest

from app.quant.registry import STRATEGIES, get_strategy, list_strategy_slugs


def test_strategies_contains_q1a_set():
    slugs = {s.spec.slug for s in STRATEGIES}
    assert {"buy-hold-spy", "sma-crossover"}.issubset(slugs)


def test_get_strategy_returns_instance():
    s = get_strategy("buy-hold-spy")
    assert s.spec.slug == "buy-hold-spy"


def test_get_strategy_unknown_raises():
    with pytest.raises(KeyError):
        get_strategy("not-a-strategy")


def test_list_strategy_slugs_is_sorted_with_benchmark_last():
    slugs = list_strategy_slugs()
    assert "buy-hold-spy" in slugs
    assert "sma-crossover" in slugs
    # Benchmark goes last for display ordering.
    assert slugs.index("buy-hold-spy") > slugs.index("sma-crossover")
