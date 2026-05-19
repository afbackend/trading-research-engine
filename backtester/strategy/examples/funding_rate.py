from typing import List

import pandas as pd

from backtester.core.bt_types import Direction, Signal
from backtester.strategy.base import Strategy


class FundingRateStrategy(Strategy):
    """
    Contrarian strategy based on extreme funding rates.

    Hypothesis (H3 from Sprint 1): extreme positive funding = overcrowded longs →
    mean-reversion SHORT. Extreme negative funding = overcrowded shorts → LONG.

    fit() calibrates the threshold as a percentile of |funding_rate| on train data.
    generate_signals() expects a 'funding_rate' column in the DataFrame.
    """

    def __init__(self, percentile: float = 0.90) -> None:
        self._percentile = percentile
        self._threshold = float("inf")

    def name(self) -> str:
        return "funding_rate"

    def warmup_periods(self) -> int:
        return 50

    def holding_periods(self) -> int:
        return 4

    def fit(self, train_data: pd.DataFrame) -> None:
        self._threshold = float(
            train_data["funding_rate"].abs().quantile(self._percentile)
        )

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        if "funding_rate" not in data.columns:
            raise ValueError(
                "FundingRateStrategy requires a 'funding_rate' column in the DataFrame."
            )

        signals = []
        for ts, row in data.iterrows():
            fr = float(row["funding_rate"])
            if fr > self._threshold:
                signals.append(Signal(timestamp=ts, direction=Direction.SHORT))
            elif fr < -self._threshold:
                signals.append(Signal(timestamp=ts, direction=Direction.LONG))
        return signals
