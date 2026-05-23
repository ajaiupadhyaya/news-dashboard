"""Strategy base class + result types.

Every strategy is a subclass that implements `generate_signals(bars, params)`
returning a DataFrame of entry/exit flags (or target-weight floats) keyed
by (date, symbol). The engine handles portfolio construction + costs
uniformly so individual strategies stay focused on signal logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


# A parameter grid is a dict of param-name -> list-of-values. The engine
# takes the Cartesian product to generate all combinations for the sweep.
ParamGrid = dict[str, list[Any]]


@dataclass
class StrategyContext:
    """Per-call context passed to `generate_signals`.

    Lets strategies that read auxiliary data (news, FRED, fundamentals)
    receive it without changing the base signature. Q1a strategies don't
    use any of these; populated by Q1b dashboard-integrated strategies.
    """
    news_clusters: pd.DataFrame | None = None
    econ_series: dict[str, pd.Series] = field(default_factory=dict)
    fundamentals: dict[str, dict] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategySpec:
    """Metadata declared by a Strategy subclass."""
    slug: str
    name: str
    category: str                # "classic" | "alpha" | "benchmark"
    universe_kind: str
    inception_date: str
    live_start_date: str
    methodology_blurb: str
    allow_short: bool = False    # only `pairs-trading` will set True


class Strategy(ABC):
    spec: StrategySpec
    sweep_grid: ParamGrid

    @abstractmethod
    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        """Return a DataFrame of target weights, indexed by date with one
        column per symbol. NaN / 0 means flat; positive = long share of
        portfolio; negative = short (only meaningful when allow_short=True).

        Engine convention: weights at row `t` are the **target portfolio at
        the close of day t**, executed on day t's close price.
        """
        ...
