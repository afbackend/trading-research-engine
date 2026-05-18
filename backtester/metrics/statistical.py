from typing import List

import numpy as np
from scipy import stats

from backtester.core.bt_types import Trade

_P_VALUE_THRESHOLD = 0.05


def calculate_statistical(
    trades: List[Trade],
    p_threshold: float = _P_VALUE_THRESHOLD,
) -> dict:
    """
    One-tailed t-test: H1 mean(net_return) > 0.

    Returns conservative defaults (p=1.0, not significant) when there
    are fewer than 2 trades or when std is zero.
    """
    n = len(trades)

    if n < 2:
        return _default_metrics(n)

    returns = np.array([t.net_return for t in trades])
    std = float(np.std(returns, ddof=1))

    if std == 0.0:
        return _default_metrics(n)

    result = stats.ttest_1samp(returns, popmean=0.0, alternative="greater")
    t_stat = float(result.statistic)
    p_value = float(result.pvalue)

    sem = std / np.sqrt(n)
    ci = stats.t.interval(0.95, df=n - 1, loc=float(np.mean(returns)), scale=sem)

    return {
        "t_statistic": t_stat,
        "p_value": p_value,
        "is_significant": p_value < p_threshold,
        "confidence_interval_95": (float(ci[0]), float(ci[1])),
        "n_trades": n,
        "degrees_of_freedom": n - 1,
    }


def _default_metrics(n: int) -> dict:
    return {
        "t_statistic": 0.0,
        "p_value": 1.0,
        "is_significant": False,
        "confidence_interval_95": (0.0, 0.0),
        "n_trades": n,
        "degrees_of_freedom": max(0, n - 1),
    }
