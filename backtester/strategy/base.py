from abc import ABC, abstractmethod
from typing import List

import pandas as pd

from backtester.core.bt_types import Signal


class Strategy(ABC):
    """
    Interface every strategy must implement.

    The framework guarantees:
    - fit() receives ONLY training data.
    - generate_signals() receives test data with no future returns.
    - The strategy NEVER sees test data during fit().
    """

    @abstractmethod
    def name(self) -> str:
        """Unique strategy name used in reports."""

    @abstractmethod
    def warmup_periods(self) -> int:
        """
        Number of candles required before the first valid signal.
        The framework discards these candles from the start of train
        before calling fit(), ensuring calibration uses clean data only.
        """

    @abstractmethod
    def holding_periods(self) -> int:
        """Number of candles to hold after entry."""

    @abstractmethod
    def fit(self, train_data: pd.DataFrame) -> None:
        """
        Calibrate strategy parameters using ONLY training data.
        Called once per walk-forward window before generate_signals().
        """

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        Generate entry signals for each candle in `data`.
        Parameters must come from the last `fit()` call.

        CONTRACT (not enforced by the framework):
        When generating a signal for the candle at timestamp T, the strategy
        MUST NOT use information from candles at timestamps > T. Common violations:
          - `data['col'].shift(-k)` — looks k candles into the future.
          - `data['col'].rolling(N).mean().shift(-N)` — future-windowed rolling.
          - Iterating `data` in reverse and propagating state forward.

        The framework cannot detect these. The strategy author is responsible.
        A canonical self-check: the signals produced for `data.iloc[:k]` should
        be identical (at indices < k) to the signals produced for `data.iloc[:k+m]`.
        """
