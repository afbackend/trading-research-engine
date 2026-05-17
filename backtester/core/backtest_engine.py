import logging
from typing import List

import pandas as pd

from backtester.core.bt_types import Direction, Signal, Trade
from backtester.core.fee_model import FeeModel

logger = logging.getLogger(__name__)


_REQUIRED_COLUMNS = {"open", "high", "low", "close"}


def run_backtest(
    data: pd.DataFrame,
    signals: List[Signal],
    holding: int,
    fee_model: FeeModel,
) -> List[Trade]:
    """
    Runs a simple fixed-holding backtest.

    Signal timing:
    - Signal detected at candle close (idx).
    - Entry at open of NEXT candle (idx + 1).
    - Exit at close of candle (idx + 1 + holding).
    - This models the realistic delay: you see the signal after
      the candle closes and can only execute at the next open.

    Overlap handling:
    - Re-entry on the exit candle is NOT allowed. New signal accepted
      only after the exit candle has passed (uses <=).
    - This prevents the physical impossibility of exiting and
      re-entering at the same price print.

    MAE window covers [entry, exit] inclusive.
    - Entry candle is included because entry is at open — high/low
      of that candle can move adversely before close.

    Raises ValueError if data is missing required columns or has an unsorted index.
    """
    missing = _REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"Data is missing required columns: {missing}")

    if not data.index.is_monotonic_increasing:
        raise ValueError("Data index must be sorted chronologically (monotonic increasing)")

    trades: List[Trade] = []
    active_until = -1

    for signal in sorted(signals, key=lambda s: s.timestamp):
        if signal.direction == Direction.NONE:
            continue

        idx = data.index.searchsorted(signal.timestamp)

        if idx >= len(data) or data.index[idx] != signal.timestamp:
            logger.warning("Signal timestamp %s not in data index, skipping", signal.timestamp)
            continue

        if idx <= active_until:
            continue

        entry_idx = idx + 1
        exit_idx = entry_idx + holding

        if exit_idx >= len(data):
            continue

        entry_price = float(data.iloc[entry_idx]["open"])
        exit_price = float(data.iloc[exit_idx]["close"])

        if signal.direction == Direction.LONG:
            gross_return = (exit_price - entry_price) / entry_price
        else:
            gross_return = (entry_price - exit_price) / entry_price

        # MAE starts at entry candle: entry is at open, so intracandle move counts.
        window = data.iloc[entry_idx : exit_idx + 1]
        if signal.direction == Direction.LONG:
            adverse = ((entry_price - window["low"]) / entry_price).clip(lower=0)
        else:
            adverse = ((window["high"] - entry_price) / entry_price).clip(lower=0)

        max_adverse = float(adverse.max()) if not adverse.empty else 0.0

        fee = fee_model.round_trip
        net_return = fee_model.apply(gross_return)

        trades.append(Trade(
            entry_time=data.index[entry_idx],
            exit_time=data.index[exit_idx],
            direction=signal.direction,
            entry_price=entry_price,
            exit_price=exit_price,
            gross_return=gross_return,
            fee=fee,
            net_return=net_return,
            holding_candles=holding,
            max_adverse=max_adverse,
            metadata=signal.metadata.copy(),
        ))

        active_until = exit_idx

    return trades
