"""Bootstrap script — fetch bars + run inception walk-forward for all 9 strategies.

Idempotent. Safe to re-run:
- `bar_cache` has (symbol, date) as PK; rerunning skips already-cached dates.
- `inception_walkforward` wipes prior backtest-phase rows for the strategy
  before writing new ones.

Usage (against the live Fly DB, pulling a copy of the prod DATABASE_URL):

    export DATABASE_URL='<paste-prod-postgres-url-here>'
    cd /Users/ajaiupadhyaya/Documents/news-dashboard/backend
    .venv/bin/python -m scripts.bootstrap_quant

Expected wall-clock: 10-15 min to fetch ~1.4M bar rows, then 30-60 min total
across the 9 strategies for the walk-forward analysis. Progress is printed
as it goes; failures on individual strategies do not abort the rest.

After it finishes, refresh https://news-dashboard-two-rho.vercel.app/quant
and the leaderboard + tiles should populate.
"""

from __future__ import annotations

import logging
import os
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# yfinance logs every "possibly delisted" symbol at ERROR level — for our
# static S&P 500 snapshot that means ~30-50 acquired/delisted names spamming
# ERROR lines that ARE handled correctly by fetch_and_cache's try/except.
# Silence the noise so the bootstrap's progress stays readable. (Production
# scheduler jobs keep their own warm_bars logging.)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

from app.database import init_db
from app.quant.bars import fetch_and_cache, get_cached_dates
from app.quant.orchestration import inception_walkforward
from app.quant.registry import STRATEGIES
from app.quant.universe import SP500_SYMBOLS


def _banner(msg: str) -> None:
    print()
    print("=" * 72)
    print(msg)
    print("=" * 72)


def main() -> None:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url.startswith("postgres"):
        print("⚠️  DATABASE_URL is not Postgres. You are bootstrapping a LOCAL")
        print("    SQLite database, not production. If you meant to bootstrap")
        print("    prod, export DATABASE_URL='<prod-postgres-url>' first.")
        print()
        choice = input("Continue against local SQLite anyway? [y/N] ").strip().lower()
        if choice != "y":
            return

    init_db()

    # 1. Fetch bars for the full universe (≥7 years of daily data).
    _banner("[1/2] Fetching daily bars (~1.4M rows expected)")
    print(
        "    (yfinance ERROR lines for delisted/acquired tickers are noise — "
        "ignore them.)"
    )
    universe = sorted(
        set(SP500_SYMBOLS) | {"SPY", "XLP", "XLU", "XLV"}
    )
    t0 = time.time()
    n = fetch_and_cache(universe, start="2018-01-02", end="2025-01-02")
    dt = time.time() - t0
    # Summarize how many distinct symbols ended up in the cache vs how many we tried.
    cached_symbols = sum(1 for s in universe if get_cached_dates(s))
    print(
        f"  wrote {n} rows in {dt:.0f}s — {cached_symbols}/{len(universe)} "
        f"symbols have data (the rest are stale snapshot tickers)"
    )

    # 2. Run inception walk-forward for each registered strategy.
    _banner("[2/2] Running inception walk-forward for each strategy")
    for s in STRATEGIES:
        slug = s.spec.slug
        print(f"  >>> {slug}")
        t0 = time.time()
        try:
            rid = inception_walkforward(
                s, train_years=3, test_years=1, step_months=6,
            )
            dt = time.time() - t0
            print(f"      OK  run_id={rid}  ({dt:.0f}s)")
        except Exception as e:
            dt = time.time() - t0
            print(f"      FAILED ({dt:.0f}s): {type(e).__name__}: {e}")

    _banner("Done")
    print("Refresh https://news-dashboard-two-rho.vercel.app/quant to see the")
    print("leaderboard + tiles populated.")


if __name__ == "__main__":
    main()
