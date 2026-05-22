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


def rsi(prices: list[float], period: int = 14) -> list[float | None]:
    """Wilder's Relative Strength Index, aligned to `prices`.

    The first `period` entries are None (not enough price changes yet).
    100.0 when there are no losses in the window, 0.0 when no gains.
    """
    n = len(prices)
    out: list[float | None] = [None] * n
    if n <= period:
        return out

    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, n):
        delta = prices[i] - prices[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    def _rsi(avg_gain: float, avg_loss: float) -> float:
        if avg_loss == 0.0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100.0 - 100.0 / (1.0 + rs), 4)

    # gains[k] is the change into prices[k + 1]; the first average covers
    # gains[0:period] -> the first RSI value aligns to prices[period].
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out[period] = _rsi(avg_gain, avg_loss)
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        out[i] = _rsi(avg_gain, avg_loss)
    return out


def _ema(values: list[float], period: int) -> list[float]:
    """Exponential moving average, seeded with the first value."""
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1.0 - k))
    return out


def macd(prices: list[float], fast: int = 12, slow: int = 26,
         signal: int = 9) -> dict[str, list[float | None]]:
    """MACD line, signal line, and histogram, each aligned to `prices`.

    Entries before the slow EMA has filled (`slow - 1`) are None. Returns a
    dict with keys "macd", "signal", "histogram".
    """
    n = len(prices)
    empty: list[float | None] = [None] * n
    if n < slow:
        return {"macd": empty[:], "signal": empty[:], "histogram": empty[:]}

    ema_fast = _ema(prices, fast)
    ema_slow = _ema(prices, slow)
    macd_line: list[float | None] = [None] * n
    for i in range(slow - 1, n):
        macd_line[i] = round(ema_fast[i] - ema_slow[i], 4)

    defined = [m for m in macd_line if m is not None]
    sig = _ema(defined, signal)
    signal_line: list[float | None] = [None] * n
    histogram: list[float | None] = [None] * n
    for offset, i in enumerate(range(slow - 1, n)):
        signal_line[i] = round(sig[offset], 4)
        histogram[i] = round((macd_line[i] or 0.0) - sig[offset], 4)
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


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
