from typing import List

import numpy as np

from backtester.core.bt_types import Trade


def calculate_risk(trades: List[Trade]) -> dict:
    """
    Compute risk metrics from a list of trades.

    Capital curve starts at 1.0 with compound returns applied per trade.
    max_drawdown is negative (peak-to-trough decline).
    capital_min is the lowest point of the normalized equity curve.
    """
    if not trades:
        return _empty_metrics()

    returns = np.array([t.net_return for t in trades])
    adverse = np.array([t.max_adverse for t in trades])

    # Prepend 1.0 so the peak starts at initial capital, not the first trade result.
    equity = np.concatenate([[1.0], np.cumprod(1 + returns)])
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak

    return {
        "max_drawdown": float(np.min(drawdown)),
        "max_consecutive_loss": _max_consecutive_loss(returns),
        "max_adverse_excursion": float(np.max(adverse)),
        "mean_adverse_excursion": float(np.mean(adverse)),
        "p90_adverse_excursion": float(np.percentile(adverse, 90)),
        "capital_min": float(np.min(equity[1:])),  # exclude starting capital
    }


def _max_consecutive_loss(returns: np.ndarray) -> int:
    max_streak = 0
    streak = 0
    for r in returns:
        if r < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def _empty_metrics() -> dict:
    return {
        "max_drawdown": 0.0,
        "max_consecutive_loss": 0,
        "max_adverse_excursion": 0.0,
        "mean_adverse_excursion": 0.0,
        "p90_adverse_excursion": 0.0,
        "capital_min": 1.0,
    }
