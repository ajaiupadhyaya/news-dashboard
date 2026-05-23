"""Strategy registry — one place that knows about every strategy.

Q1a ships with 2 entries. Q1b will append the remaining 7.
"""

from __future__ import annotations

from app.quant.strategies.base import Strategy
from app.quant.strategies.bollinger_breakout import BollingerBreakout
from app.quant.strategies.buy_hold_spy import BuyHoldSPY
from app.quant.strategies.cross_sectional_momentum import CrossSectionalMomentum
from app.quant.strategies.news_sentiment_momentum import NewsSentimentMomentum
from app.quant.strategies.pairs_trading import PairsTrading
from app.quant.strategies.rsi_mean_reversion import RsiMeanReversion
from app.quant.strategies.sma_crossover import SmaCrossover

STRATEGIES: tuple[Strategy, ...] = (
    SmaCrossover(),
    RsiMeanReversion(),
    CrossSectionalMomentum(),
    PairsTrading(),
    BollingerBreakout(),
    NewsSentimentMomentum(),
    BuyHoldSPY(),
)


def get_strategy(slug: str) -> Strategy:
    for s in STRATEGIES:
        if s.spec.slug == slug:
            return s
    raise KeyError(f"Unknown strategy slug: {slug}")


def list_strategy_slugs() -> list[str]:
    """Display order: classics + alpha alphabetically, benchmark last."""
    classics = sorted(
        s.spec.slug for s in STRATEGIES
        if s.spec.category in ("classic", "alpha")
    )
    benchmarks = sorted(
        s.spec.slug for s in STRATEGIES if s.spec.category == "benchmark"
    )
    return classics + benchmarks
