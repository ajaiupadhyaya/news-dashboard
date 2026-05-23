from app.quant.universe import (
    SP500_SYMBOLS, PAIRS, get_universe, list_universe_kinds,
)


def test_sp500_symbols_is_a_nonempty_list_of_strings():
    assert isinstance(SP500_SYMBOLS, tuple)
    assert len(SP500_SYMBOLS) >= 480       # allow some drift over time
    assert all(isinstance(s, str) and s.isupper() for s in SP500_SYMBOLS)
    assert "AAPL" in SP500_SYMBOLS
    assert "MSFT" in SP500_SYMBOLS
    assert "SPY" not in SP500_SYMBOLS      # SPY is the ETF, not in S&P 500 itself


def test_pairs_are_well_formed():
    assert isinstance(PAIRS, tuple)
    assert len(PAIRS) == 5
    for a, b in PAIRS:
        assert isinstance(a, str) and isinstance(b, str)
        assert a != b


def test_get_universe_spy():
    assert get_universe("spy") == ("SPY",)


def test_get_universe_sp500():
    u = get_universe("sp500")
    assert isinstance(u, tuple)
    assert "AAPL" in u


def test_get_universe_pairs_fixed():
    u = get_universe("pairs-fixed")
    # All unique symbols from the 5 pairs
    assert "KO" in u and "PEP" in u and "GOOG" in u and "META" in u


def test_get_universe_unknown_raises():
    import pytest
    with pytest.raises(ValueError):
        get_universe("not-a-real-universe-kind")


def test_list_universe_kinds():
    kinds = list_universe_kinds()
    assert set(kinds) == {"spy", "sp500", "pairs-fixed", "news-top100"}
