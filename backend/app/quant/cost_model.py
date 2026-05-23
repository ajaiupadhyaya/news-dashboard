"""Uniform cost model used by both the backtest engine and the (future)
forward-step runner — keeps the two paths numerically consistent.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    commission: float = 0.0          # dollars per fill
    slippage_bps: float = 5.0        # basis points, per side
    allow_short: bool = False

    def to_dict(self) -> dict:
        return {
            "commission": self.commission,
            "slippage_bps": self.slippage_bps,
            "allow_short": self.allow_short,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CostModel":
        return cls(
            commission=float(d.get("commission", 0.0)),
            slippage_bps=float(d.get("slippage_bps", 5.0)),
            allow_short=bool(d.get("allow_short", False)),
        )


def apply_slippage(price: float, *, side: str, slippage_bps: float) -> float:
    """Push price adverse-to-trader by `slippage_bps` basis points.

    buys / covers fill above mid; sells / shorts fill below mid.
    """
    if slippage_bps == 0:
        return price
    mult = slippage_bps / 10_000.0
    if side in ("buy", "cover"):
        return round(price * (1 + mult), 6)
    if side in ("sell", "short"):
        return round(price * (1 - mult), 6)
    raise ValueError(f"Unknown side: {side}")


def target_qty_from_weight(*, weight: float, equity: float, price: float) -> int:
    """Convert a target portfolio weight into an integer share quantity.

    Negative weights produce negative quantities (short positions).
    Zero or invalid price returns 0 to avoid division errors.
    """
    if price <= 0 or equity <= 0:
        return 0
    raw = (weight * equity) / price
    return int(raw) if raw >= 0 else -int(-raw)
