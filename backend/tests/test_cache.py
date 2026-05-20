from app.cache import TTLCache


def test_set_and_get():
    c = TTLCache(ttl_seconds=100, clock=lambda: 0.0)
    c.set("k", 42)
    assert c.get("k") == 42


def test_missing_key_returns_none():
    c = TTLCache(ttl_seconds=100, clock=lambda: 0.0)
    assert c.get("nope") is None


def test_entry_expires_after_ttl():
    now = {"t": 0.0}
    c = TTLCache(ttl_seconds=10, clock=lambda: now["t"])
    c.set("k", "v")
    now["t"] = 9.0
    assert c.get("k") == "v"
    now["t"] = 11.0
    assert c.get("k") is None


def test_get_or_compute_computes_once():
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return "value"

    c = TTLCache(ttl_seconds=100, clock=lambda: 0.0)
    assert c.get_or_compute("k", compute) == "value"
    assert c.get_or_compute("k", compute) == "value"
    assert calls["n"] == 1


def test_clear_empties_the_cache():
    c = TTLCache(ttl_seconds=100, clock=lambda: 0.0)
    c.set("k", 1)
    c.clear()
    assert c.get("k") is None
