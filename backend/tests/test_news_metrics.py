from datetime import datetime, timedelta, timezone

from app.analysis import news_metrics as nm


def test_parse_timestamp_handles_aware_naive_and_bad():
    aware = nm.parse_timestamp("2026-05-22T12:00:00+00:00")
    assert aware is not None and aware.tzinfo is not None
    naive = nm.parse_timestamp("2026-05-22T12:00:00")
    assert naive is not None and naive.tzinfo is not None
    assert nm.parse_timestamp("not a date") is None


def test_momentum_score_surges_on_a_recent_burst():
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    pubs = [(now - timedelta(hours=h)).isoformat() for h in (1, 2, 3)]
    # all 3 articles inside the 6h recent window, none older -> 8x the
    # uniform rate (48h / 6h)
    assert nm.momentum_score(pubs, now) == 8.0


def test_momentum_score_zero_without_recent_articles():
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    pubs = [(now - timedelta(hours=h)).isoformat() for h in (30, 40)]
    assert nm.momentum_score(pubs, now) == 0.0


def test_momentum_score_zero_with_no_articles():
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    assert nm.momentum_score([], now) == 0.0


def test_momentum_status_buckets():
    assert nm.momentum_status(8.0) == "surging"
    assert nm.momentum_status(1.0) == "steady"
    assert nm.momentum_status(0.0) == "fading"


def test_rank_score_weights_source_diversity_highest():
    # broad coverage beats a high-volume, high-momentum single-source story
    assert nm.rank_score(10, 10, 1.0) > nm.rank_score(1, 30, 5.0)
