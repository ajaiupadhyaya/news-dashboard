import statistics
from math import sqrt


def simple_returns(prices: list[float]) -> list[float]:
    out: list[float] = []
    for i in range(1, len(prices)):
        prev = prices[i - 1]
        out.append((prices[i] - prev) / prev if prev else 0.0)
    return out


def momentum(prices: list[float], periods: int) -> float:
    """Total return over the last `periods` steps. 0.0 if history too short."""
    if len(prices) <= periods:
        return 0.0
    base = prices[-periods - 1]
    return (prices[-1] / base) - 1.0 if base else 0.0


def annualized_volatility(returns: list[float], periods_per_year: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    return statistics.stdev(returns) * sqrt(periods_per_year)


def sma(prices: list[float], window: int) -> list[float | None]:
    """Simple moving average aligned to `prices`; None until the window fills."""
    out: list[float | None] = []
    for i in range(len(prices)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(round(sum(prices[i + 1 - window: i + 1]) / window, 4))
    return out


def downsample(values: list[float], target: int) -> list[float]:
    """Evenly sample `values` down to `target` points, keeping both endpoints."""
    if target <= 1 or len(values) <= target:
        return list(values)
    step = (len(values) - 1) / (target - 1)
    return [values[round(i * step)] for i in range(target)]


def breadth(changes: list[float]) -> dict:
    advancers = sum(1 for c in changes if c > 0)
    decliners = sum(1 for c in changes if c < 0)
    unchanged = sum(1 for c in changes if c == 0)
    ratio = advancers / decliners if decliners else float(advancers)
    return {
        "advancers": advancers,
        "decliners": decliners,
        "unchanged": unchanged,
        "advance_decline_ratio": round(ratio, 4),
    }
