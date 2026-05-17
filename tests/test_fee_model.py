import pytest
from backtester.core.fee_model import FeeModel


def test_round_trip_defaults():
    fee = FeeModel()
    assert fee.round_trip == pytest.approx(0.002)


def test_round_trip_with_slippage():
    fee = FeeModel(taker_fee=0.001, slippage_estimate=0.0005)
    assert fee.round_trip == pytest.approx(0.003)


def test_apply_reduces_positive_return():
    fee = FeeModel()
    assert fee.apply(0.02) == pytest.approx(0.018)


def test_apply_worsens_loss():
    fee = FeeModel()
    assert fee.apply(-0.01) == pytest.approx(-0.012)


def test_apply_zero_return_results_in_loss():
    fee = FeeModel()
    assert fee.apply(0.0) == pytest.approx(-0.002)
