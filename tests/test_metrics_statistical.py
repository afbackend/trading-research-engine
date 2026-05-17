import pytest
import pandas as pd
from scipy import stats

from backtester.core.bt_types import Direction, Trade
from backtester.metrics.statistical import calculate_statistical


def make_trade(net_return: float, days_offset: int = 0) -> Trade:
    base = pd.Timestamp("2024-01-01")
    gross = net_return + 0.002
    return Trade(
        entry_time=base + pd.Timedelta(days=days_offset),
        exit_time=base + pd.Timedelta(days=days_offset + 1),
        direction=Direction.LONG,
        entry_price=100.0,
        exit_price=100.0 * (1 + gross),
        gross_return=gross,
        fee=0.002,
        net_return=net_return,
        holding_candles=4,
        max_adverse=0.0,
    )


# --- defaults (n < 2 or std == 0) ---

def test_empty_returns_defaults():
    m = calculate_statistical([])
    assert m["p_value"] == pytest.approx(1.0)
    assert m["t_statistic"] == pytest.approx(0.0)
    assert m["is_significant"] is False
    assert m["n_trades"] == 0
    assert m["degrees_of_freedom"] == 0
    assert m["confidence_interval_95"] == (0.0, 0.0)


def test_single_trade_returns_defaults():
    m = calculate_statistical([make_trade(0.05)])
    assert m["p_value"] == pytest.approx(1.0)
    assert m["is_significant"] is False
    assert m["n_trades"] == 1
    assert m["degrees_of_freedom"] == 0


def test_zero_std_returns_defaults():
    trades = [make_trade(0.01, i) for i in range(5)]
    m = calculate_statistical(trades)
    assert m["p_value"] == pytest.approx(1.0)
    assert m["is_significant"] is False


# --- significance ---

def test_strongly_positive_returns_are_significant():
    trades = [make_trade(0.05, i) for i in range(20)]
    trades += [make_trade(-0.001, i) for i in range(20, 25)]
    m = calculate_statistical(trades)
    assert m["is_significant"] is True
    assert m["p_value"] < 0.05
    assert m["t_statistic"] > 0


def test_negative_mean_is_not_significant():
    trades = [make_trade(-0.02, i) for i in range(20)]
    trades += [make_trade(0.001, i) for i in range(20, 22)]
    m = calculate_statistical(trades)
    assert m["is_significant"] is False
    assert m["p_value"] > 0.5


def test_custom_p_threshold():
    trades = [make_trade(0.05, i) for i in range(30)]
    trades += [make_trade(-0.005, i) for i in range(30, 35)]
    m_strict = calculate_statistical(trades, p_threshold=0.01)
    m_loose = calculate_statistical(trades, p_threshold=0.10)
    assert m_strict["is_significant"] is True
    assert m_loose["is_significant"] is True


# --- one-tailed vs two-tailed ---

def test_one_tailed_p_value_is_half_of_two_tailed():
    trades = [make_trade(0.02, i) for i in range(10)]
    trades += [make_trade(-0.005, i) for i in range(10, 15)]
    m = calculate_statistical(trades)
    returns = [t.net_return for t in trades]
    two_tailed = stats.ttest_1samp(returns, popmean=0.0).pvalue
    assert m["p_value"] == pytest.approx(two_tailed / 2, rel=1e-6)


# --- fields ---

def test_n_trades_and_dof():
    trades = [make_trade(0.01, i) for i in range(7)] + [make_trade(-0.005, i) for i in range(7, 10)]
    m = calculate_statistical(trades)
    assert m["n_trades"] == 10
    assert m["degrees_of_freedom"] == 9


def test_t_statistic_sign_matches_mean():
    positive_trades = [make_trade(0.02, i) for i in range(5)] + [make_trade(-0.001, i) for i in range(5, 8)]
    m = calculate_statistical(positive_trades)
    assert m["t_statistic"] > 0


# --- confidence interval ---

def test_confidence_interval_is_tuple_of_two_floats():
    trades = [make_trade(0.01, i) for i in range(5)] + [make_trade(-0.01, i) for i in range(5, 8)]
    m = calculate_statistical(trades)
    ci = m["confidence_interval_95"]
    assert isinstance(ci, tuple)
    assert len(ci) == 2
    assert ci[0] < ci[1]


def test_confidence_interval_contains_mean_for_positive_returns():
    trades = [make_trade(0.03, i) for i in range(10)] + [make_trade(-0.005, i) for i in range(10, 13)]
    m = calculate_statistical(trades)
    mean = sum(t.net_return for t in trades) / len(trades)
    ci = m["confidence_interval_95"]
    assert ci[0] <= mean <= ci[1]
