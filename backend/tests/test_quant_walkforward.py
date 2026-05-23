from datetime import date

import pandas as pd

from app.quant.walkforward import build_walkforward_windows, stitch_oos_equity


def test_build_windows_basic_3y_train_1y_test_6mo_step():
    dates = pd.date_range("2015-01-02", "2024-12-31", freq="B")
    windows = build_walkforward_windows(
        dates, train_years=3, test_years=1, step_months=6,
    )
    # First window: train 2015-01-02 → 2017-12-31, test 2018-01-02 → 2018-12-31
    assert windows[0].train_start == "2015-01-02"
    assert windows[0].train_end >= "2017-12-29"
    assert windows[0].test_start >= "2018-01-02"
    assert windows[0].test_end >= "2018-12-29"
    # Subsequent windows step forward by 6 months.
    second_test_start = windows[1].test_start
    assert second_test_start >= "2018-06-29"
    # Last window's test_end should be within the last calendar year.
    assert windows[-1].test_end <= "2024-12-31"


def test_build_windows_skips_when_insufficient_data():
    dates = pd.date_range("2024-01-02", "2024-06-30", freq="B")  # 6 months only
    windows = build_walkforward_windows(
        dates, train_years=3, test_years=1, step_months=6,
    )
    assert windows == []


def test_stitch_oos_equity_concatenates_test_segments():
    # Two windows: each has an OOS equity Series indexed by date.
    s1 = pd.Series(
        [100_000, 101_000, 102_000],
        index=pd.to_datetime(["2018-01-02", "2018-01-03", "2018-01-04"]),
    )
    s2 = pd.Series(
        # NB: stitcher should rescale s2 to start where s1 ended.
        [100_000, 99_000, 101_000],
        index=pd.to_datetime(["2018-01-05", "2018-01-08", "2018-01-09"]),
    )
    stitched = stitch_oos_equity([s1, s2])
    # First point preserved.
    assert stitched.iloc[0] == 100_000
    # Stitching: s2 starts at 102_000 (where s1 ended) and applies its returns
    assert round(stitched.iloc[-1], 2) == round(102_000 * (101_000 / 100_000), 2)


def test_stitch_oos_equity_handles_overlap_by_keeping_first_window():
    s1 = pd.Series(
        [100_000, 101_000],
        index=pd.to_datetime(["2018-01-02", "2018-01-03"]),
    )
    s2 = pd.Series(
        [100_000, 102_000, 103_000],
        index=pd.to_datetime(["2018-01-03", "2018-01-04", "2018-01-05"]),
    )
    stitched = stitch_oos_equity([s1, s2])
    # Date 2018-01-03 should come from s1, not s2.
    assert stitched.loc["2018-01-03"] == 101_000


def test_stitch_oos_equity_empty_returns_empty():
    out = stitch_oos_equity([])
    assert out.empty
