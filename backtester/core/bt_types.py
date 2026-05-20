from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

import pandas as pd


class Direction(Enum):
    LONG = 1
    SHORT = -1
    NONE = 0


@dataclass
class Signal:
    timestamp: pd.Timestamp
    direction: Direction
    metadata: Dict = field(default_factory=dict)


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: Direction
    entry_price: float
    exit_price: float
    gross_return: float
    fee: float
    net_return: float
    holding_candles: int
    max_adverse: float
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        expected = self.gross_return - self.fee
        if abs(self.net_return - expected) > 1e-10:
            raise ValueError(
                f"net_return ({self.net_return:.6f}) != "
                f"gross_return ({self.gross_return:.6f}) - "
                f"fee ({self.fee:.6f}) = {expected:.6f}"
            )


@dataclass
class BacktestResult:
    trades: List[Trade]
    metrics: Dict
    config: Dict
    is_oos: bool
    signals_generated: int
    signals_executed: int

    @property
    def rejection_rate(self) -> float:
        if self.signals_generated == 0:
            return 0.0
        return 1 - (self.signals_executed / self.signals_generated)

    @property
    def net_returns(self) -> pd.Series:
        return pd.Series([t.net_return for t in self.trades])
