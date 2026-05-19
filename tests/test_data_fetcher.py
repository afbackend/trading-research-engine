from unittest.mock import MagicMock, call, patch

import ccxt
import pandas as pd
import pytest

from backtester.data.fetcher import fetch_ohlcv

# 2024-01-01 00:00 UTC in ms
_T0 = 1704067200000
_4H = 4 * 3600 * 1000


def _candle(ts: int, price: float = 100.0) -> list:
    return [ts, price, price + 5, price - 5, price + 1, 1000.0]


def _mock_exchange(candles_by_call: list):
    """Return a mock exchange whose fetch_ohlcv side_effect follows candles_by_call."""
    ex = MagicMock(spec=ccxt.Exchange)
    ex.fetch_ohlcv.side_effect = candles_by_call
    return ex


# --- basic shape ---

def test_fetch_returns_dataframe(monkeypatch):
    candles = [_candle(_T0), _candle(_T0 + _4H)]
    ex = _mock_exchange([candles, []])
    monkeypatch.setattr(ccxt, "binance", lambda: ex)

    df = fetch_ohlcv("BTC/USDT", "4h", "2024-01-01", "2024-01-02",
                     exchange_id="binance", retry_delay=0)

    assert isinstance(df.index, pd.DatetimeIndex)
    assert set(["open", "high", "low", "close", "volume"]).issubset(df.columns)
    assert len(df) == 2


def test_fetch_returns_sorted_index(monkeypatch):
    # Out-of-order in source — must come back sorted
    candles = [_candle(_T0 + _4H), _candle(_T0)]
    ex = _mock_exchange([candles, []])
    monkeypatch.setattr(ccxt, "binance", lambda: ex)

    df = fetch_ohlcv("BTC/USDT", "4h", "2024-01-01", "2024-01-02",
                     exchange_id="binance", retry_delay=0)

    assert df.index.is_monotonic_increasing


def test_fetch_deduplicates(monkeypatch):
    candles = [_candle(_T0), _candle(_T0)]  # duplicate timestamp
    ex = _mock_exchange([candles, []])
    monkeypatch.setattr(ccxt, "binance", lambda: ex)

    df = fetch_ohlcv("BTC/USDT", "4h", "2024-01-01", "2024-01-02",
                     exchange_id="binance", retry_delay=0)

    assert df.index.is_unique


# --- pagination ---

def test_pagination_fetches_multiple_batches(monkeypatch):
    end_ts = _T0 + 5 * _4H
    batch1 = [_candle(_T0 + i * _4H) for i in range(3)]   # ends before end_ts
    batch2 = [_candle(_T0 + i * _4H) for i in range(3, 6)] # ends at/after end_ts

    ex = _mock_exchange([batch1, batch2])
    monkeypatch.setattr(ccxt, "binance", lambda: ex)

    end_dt = pd.Timestamp(_T0 + 5 * _4H, unit="ms", tz="UTC")
    fetch_ohlcv("BTC/USDT", "4h", "2024-01-01", end_dt,
                exchange_id="binance", retry_delay=0)

    assert ex.fetch_ohlcv.call_count == 2


def test_empty_response_stops_pagination(monkeypatch):
    ex = _mock_exchange([[]])  # first call returns empty
    monkeypatch.setattr(ccxt, "binance", lambda: ex)

    df = fetch_ohlcv("BTC/USDT", "4h", "2024-01-01", "2024-01-02",
                     exchange_id="binance", retry_delay=0)

    assert len(df) == 0
    assert ex.fetch_ohlcv.call_count == 1


# --- retry ---

def test_retry_exhausted_raises(monkeypatch):
    ex = MagicMock(spec=ccxt.Exchange)
    ex.fetch_ohlcv.side_effect = ccxt.NetworkError("timeout")
    monkeypatch.setattr(ccxt, "binance", lambda: ex)

    with pytest.raises(ccxt.NetworkError):
        fetch_ohlcv("BTC/USDT", "4h", "2024-01-01", "2024-01-02",
                    exchange_id="binance", max_retries=2, retry_delay=0)

    assert ex.fetch_ohlcv.call_count == 3  # initial + 2 retries


def test_retry_succeeds_on_second_attempt(monkeypatch):
    candles = [_candle(_T0 + 4 * _4H)]  # one candle past end → stops
    ex = MagicMock(spec=ccxt.Exchange)
    ex.fetch_ohlcv.side_effect = [ccxt.NetworkError("fail"), candles]
    monkeypatch.setattr(ccxt, "binance", lambda: ex)

    end_dt = pd.Timestamp(_T0 + 2 * _4H, unit="ms", tz="UTC")
    df = fetch_ohlcv("BTC/USDT", "4h", "2024-01-01", end_dt,
                     exchange_id="binance", max_retries=2, retry_delay=0)

    assert ex.fetch_ohlcv.call_count == 2
    assert isinstance(df, pd.DataFrame)


# --- validation ---

def test_unknown_exchange_raises_value_error():
    with pytest.raises(ValueError, match="Unknown exchange"):
        fetch_ohlcv("BTC/USDT", "4h", "2024-01-01", "2024-01-02",
                    exchange_id="totally_fake_exchange_xyz")
