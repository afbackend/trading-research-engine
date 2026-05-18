import pytest
import pandas as pd

from backtester.core.bt_types import Direction, Trade
from backtester.metrics.risk import calculate_risk


def make_trade(net_return: float, max_adverse: float = 0.0, days_offset: int = 0) -> Trade:
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
        max_adverse=max_adverse,
    )


# --- empty ---

def test_empty_returns_zeros():
    m = calculate_risk([])
    assert m["max_drawdown"] == 0.0
    assert m["max_consecutive_loss"] == 0
    assert m["capital_min"] == 1.0


# --- max_drawdown ---

def test_max_drawdown_all_wins_is_zero():
    trades = [make_trade(0.01, days_offset=i) for i in range(5)]
    assert calculate_risk(trades)["max_drawdown"] == pytest.approx(0.0)


def test_max_drawdown_single_loss():
    # equity: [0.90] → peak: [1.0] → drawdown: [(0.90-1.0)/1.0] = -0.10
    trades = [make_trade(-0.10)]
    assert calculate_risk(trades)["max_drawdown"] == pytest.approx(-0.10)


def test_max_drawdown_recovery():
    # equity: [1.10, 0.99, 1.089] → peak: [1.10, 1.10, 1.10]
    # drawdown: [0, (0.99-1.10)/1.10, ...] = [0, -0.10, ...]
    trades = [make_trade(0.10, days_offset=0),
              make_trade(-0.10, days_offset=1),
              make_trade(0.10, days_offset=2)]
    m = calculate_risk(trades)
    assert m["max_drawdown"] < 0
    assert m["max_drawdown"] == pytest.approx(-0.10, abs=1e-4)


def test_max_drawdown_is_negative():
    trades = [make_trade(0.05, days_offset=0), make_trade(-0.15, days_offset=1)]
    assert calculate_risk(trades)["max_drawdown"] < 0


# --- max_consecutive_loss ---

def test_max_consecutive_loss_all_wins():
    trades = [make_trade(0.01, days_offset=i) for i in range(5)]
    assert calculate_risk(trades)["max_consecutive_loss"] == 0


def test_max_consecutive_loss_all_losses():
    trades = [make_trade(-0.01, days_offset=i) for i in range(4)]
    assert calculate_risk(trades)["max_consecutive_loss"] == 4


def test_max_consecutive_loss_mixed():
    # W L L L W L L → longest streak = 3
    returns = [0.01, -0.01, -0.01, -0.01, 0.01, -0.01, -0.01]
    trades = [make_trade(r, days_offset=i) for i, r in enumerate(returns)]
    assert calculate_risk(trades)["max_consecutive_loss"] == 3


def test_max_consecutive_loss_streak_resets():
    returns = [0.01, -0.01, -0.01, 0.01, -0.01]
    trades = [make_trade(r, days_offset=i) for i, r in enumerate(returns)]
    assert calculate_risk(trades)["max_consecutive_loss"] == 2


# --- MAE ---

def test_max_adverse_excursion():
    trades = [
        make_trade(0.01, max_adverse=0.02, days_offset=0),
        make_trade(0.01, max_adverse=0.05, days_offset=1),
        make_trade(0.01, max_adverse=0.01, days_offset=2),
    ]
    assert calculate_risk(trades)["max_adverse_excursion"] == pytest.approx(0.05)


def test_mean_adverse_excursion():
    trades = [
        make_trade(0.01, max_adverse=0.02, days_offset=0),
        make_trade(0.01, max_adverse=0.04, days_offset=1),
    ]
    assert calculate_risk(trades)["mean_adverse_excursion"] == pytest.approx(0.03)


def test_p90_adverse_excursion():
    trades = [make_trade(0.01, max_adverse=float(i) / 100, days_offset=i)
              for i in range(1, 11)]
    m = calculate_risk(trades)
    assert m["p90_adverse_excursion"] == pytest.approx(0.09, abs=0.01)


# --- capital_min ---

def test_capital_min_all_wins():
    trades = [make_trade(0.10, days_offset=i) for i in range(3)]
    m = calculate_risk(trades)
    assert m["capital_min"] > 1.0


def test_capital_min_all_losses():
    trades = [make_trade(-0.10, days_offset=i) for i in range(3)]
    m = calculate_risk(trades)
    expected = 0.9 ** 3
    assert m["capital_min"] == pytest.approx(expected, rel=1e-4)


def test_capital_min_is_lowest_point():
    # equity goes up then crashes
    trades = [make_trade(0.20, days_offset=0),
              make_trade(-0.50, days_offset=1),
              make_trade(0.30, days_offset=2)]
    m = calculate_risk(trades)
    equity = [1.20, 1.20 * 0.50, 1.20 * 0.50 * 1.30]
    assert m["capital_min"] == pytest.approx(min(equity), rel=1e-4)
