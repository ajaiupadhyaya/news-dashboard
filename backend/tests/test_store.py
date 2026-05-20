from app.store import (get_watchlist, add_to_watchlist, remove_from_watchlist,
                       get_preference, set_preference)


def test_watchlist_starts_empty(db):
    assert get_watchlist() == []


def test_add_preserves_order_and_uppercases(db):
    add_to_watchlist("aapl")
    add_to_watchlist("MSFT")
    assert get_watchlist() == ["AAPL", "MSFT"]


def test_add_is_idempotent(db):
    add_to_watchlist("AAPL")
    add_to_watchlist("AAPL")
    assert get_watchlist() == ["AAPL"]


def test_remove(db):
    add_to_watchlist("AAPL")
    add_to_watchlist("MSFT")
    remove_from_watchlist("aapl")
    assert get_watchlist() == ["MSFT"]


def test_preferences_round_trip(db):
    assert get_preference("theme", "dark") == "dark"
    set_preference("theme", "light")
    assert get_preference("theme", "dark") == "light"
