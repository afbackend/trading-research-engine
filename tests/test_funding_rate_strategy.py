import pandas as pd
import pytest

from backtester.core.bt_types import Direction
from backtester.strategy.examples.funding_rate import FundingRateStrategy


def _make_data(funding_rates: list, include_ohlc: bool = True) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(funding_rates), freq="4h")
    data = {"funding_rate": funding_rates}
    if include_ohlc:
        data.update({
            "open": [100.0] * len(funding_rates),
            "high": [105.0] * len(funding_rates),
            "low":  [95.0]  * len(funding_rates),
            "close":[101.0] * len(funding_rates),
        })
    return pd.DataFrame(data, index=idx)


# --- fit and threshold calibration ---

def test_fit_calibrates_threshold_at_90th_percentile():
    rates = list(range(100))  # 0..99, abs same
    strategy = FundingRateStrategy(percentile=0.90)
    strategy.fit(_make_data(rates))
    import numpy as np
    expected = float(pd.Series([abs(r) for r in rates]).quantile(0.90))
    assert strategy._threshold == pytest.approx(expected)


def test_fit_uses_configured_percentile():
    rates = list(range(100))
    s50 = FundingRateStrategy(percentile=0.50)
    s95 = FundingRateStrategy(percentile=0.95)
    s50.fit(_make_data(rates))
    s95.fit(_make_data(rates))
    assert s50._threshold < s95._threshold


def test_threshold_is_inf_before_fit():
    strategy = FundingRateStrategy()
    assert strategy._threshold == float("inf")


# --- signal generation ---

def test_high_positive_funding_generates_short():
    strategy = FundingRateStrategy(percentile=0.90)
    strategy.fit(_make_data([0.01] * 100))  # threshold ≈ 0.01
    # Signal above threshold
    data = _make_data([0.02])
    signals = strategy.generate_signals(data)
    assert len(signals) == 1
    assert signals[0].direction == Direction.SHORT


def test_high_negative_funding_generates_long():
    strategy = FundingRateStrategy(percentile=0.90)
    strategy.fit(_make_data([0.01] * 100))
    data = _make_data([-0.02])
    signals = strategy.generate_signals(data)
    assert len(signals) == 1
    assert signals[0].direction == Direction.LONG


def test_moderate_funding_generates_no_signal():
    strategy = FundingRateStrategy(percentile=0.90)
    strategy.fit(_make_data([0.01] * 100))
    # threshold ≈ 0.01; 0.005 is below
    data = _make_data([0.005])
    signals = strategy.generate_signals(data)
    assert signals == []


def test_no_signals_before_fit():
    strategy = FundingRateStrategy()
    # threshold = inf → nothing exceeds it
    data = _make_data([999.0, -999.0])
    signals = strategy.generate_signals(data)
    assert signals == []


def test_multiple_candles_produces_multiple_signals():
    strategy = FundingRateStrategy(percentile=0.90)
    strategy.fit(_make_data([0.01] * 100))
    data = _make_data([0.02, 0.005, -0.02, 0.03])
    signals = strategy.generate_signals(data)
    # 0.02 → SHORT, 0.005 → none, -0.02 → LONG, 0.03 → SHORT
    assert len(signals) == 3
    assert signals[0].direction == Direction.SHORT
    assert signals[1].direction == Direction.LONG
    assert signals[2].direction == Direction.SHORT


# --- missing column ---

def test_missing_funding_rate_column_raises_in_generate_signals():
    strategy = FundingRateStrategy()
    strategy._threshold = 0.01
    data = _make_data([0.02], include_ohlc=True)
    data = data.drop(columns=["funding_rate"])
    with pytest.raises(ValueError, match="funding_rate"):
        strategy.generate_signals(data)


def test_missing_funding_rate_column_raises_in_fit():
    strategy = FundingRateStrategy()
    data = _make_data([0.01] * 100, include_ohlc=True)
    data = data.drop(columns=["funding_rate"])
    with pytest.raises(ValueError, match="funding_rate"):
        strategy.fit(data)


# --- interface compliance ---

def test_strategy_name():
    assert FundingRateStrategy().name() == "funding_rate"


def test_warmup_and_holding():
    s = FundingRateStrategy()
    assert s.warmup_periods() == 50
    assert s.holding_periods() == 4
