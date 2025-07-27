# test_strategies.py
import pandas as pd
import pytest

from modular_bot.strategies import MaCrossStrategy


@pytest.fixture
def sample_market_data_long():
    """
    Creates a sample DataFrame where a long crossover occurs at '10:45'.
    - ADX is high (trending) at '10:45' (26), allowing a signal.
    """
    data = {
        'open': [100, 101, 102, 103, 104, 105],
        'high': [101, 102, 103, 104, 105, 106],
        'low': [99, 100, 101, 102, 103, 104],
        'close': [100, 101, 101, 102, 103, 105],
        'EMA_5': [100, 100, 101, 102, 103, 104],  # Fast MA
        'EMA_10': [101, 101, 101, 101, 102, 103],  # Slow MA
        'ATRr_14': [1, 1, 1, 1, 1, 1],  # ATR value
        'ADX_14': [20, 22, 24, 26, 28, 20]  # ADX value
    }
    df = pd.DataFrame(data, index=pd.to_datetime(
        ['2025-01-01 10:00', '2025-01-01 10:15', '2025-01-01 10:30', '2025-01-01 10:45', '2025-01-01 11:00',
         '2025-01-01 11:15']))
    return df


@pytest.fixture
def sample_market_data_short():
    """
    Creates a sample DataFrame where a short crossover occurs at '10:45'.
    - ADX is high (trending) at '10:45' (26), allowing a signal.
    """
    data = {
        'open': [105, 104, 103, 102, 101, 100],
        'high': [106, 105, 104, 103, 102, 101],
        'low': [104, 103, 102, 101, 100, 99],
        'close': [105, 104, 103, 102, 101, 100],
        'EMA_5': [103, 102, 101, 100, 99, 98],  # Fast MA
        'EMA_10': [101, 101, 101, 101, 100, 99],  # Slow MA
        'ATRr_14': [1, 1, 1, 1, 1, 1],  # ATR value
        'ADX_14': [20, 22, 24, 26, 28, 20]  # ADX value
    }
    df = pd.DataFrame(data, index=pd.to_datetime(
        ['2025-01-01 10:00', '2025-01-01 10:15', '2025-01-01 10:30', '2025-01-01 10:45', '2025-01-01 11:00',
         '2025-01-01 11:15']))
    return df


def test_ma_cross_long_signal_with_adx_filter(sample_market_data_long):
    """
    Tests if a long signal is correctly identified WHEN ADX is above the threshold.
    """
    # Arrange
    strategy = MaCrossStrategy(sample_market_data_long, fast_ma=5, slow_ma=10, adx_threshold=25)

    # Act
    signals_df = strategy.generate_signals()

    # Assert
    # Check that a signal occurred at '10:45' because ADX (26) > 25
    assert signals_df.loc['2025-01-01 10:45:00']['signal'] == 1
    # Check stop loss: low (102) - atr (1) * 2 = 100
    assert signals_df.loc['2025-01-01 10:45:00']['stop_loss_price'] == 100.0


def test_ma_cross_long_signal_is_filtered_by_low_adx(sample_market_data_long):
    """
    Tests that a long signal is IGNORED if ADX is below the threshold.
    """
    # Arrange: Set a high ADX threshold that will filter out the signal
    strategy = MaCrossStrategy(sample_market_data_long, fast_ma=5, slow_ma=10, adx_threshold=27)

    # Act
    signals_df = strategy.generate_signals()

    # Assert
    # Check that NO signal occurred at '10:45' because ADX (26) was not > 27
    assert signals_df['signal'].sum() == 0


def test_ma_cross_short_signal_with_adx_filter(sample_market_data_short):
    """
    Tests if a short signal is correctly identified WHEN ADX is above the threshold.
    """
    # Arrange
    strategy = MaCrossStrategy(sample_market_data_short, fast_ma=5, slow_ma=10, adx_threshold=25)

    # Act
    signals_df = strategy.generate_signals()

    # Assert
    # Check that a signal occurred at '10:45' because ADX (26) > 25
    assert signals_df.loc['2025-01-01 10:45:00']['signal'] == -1
    # Check stop loss: high (103) + atr (1) * 2 = 105
    assert signals_df.loc['2025-01-01 10:45:00']['stop_loss_price'] == 105.0


def test_ma_cross_short_signal_is_filtered_by_low_adx(sample_market_data_short):
    """
    Tests that a short signal is IGNORED if ADX is below the threshold.
    """
    # Arrange: Set a high ADX threshold that will filter out the signal
    strategy = MaCrossStrategy(sample_market_data_short, fast_ma=5, slow_ma=10, adx_threshold=27)

    # Act
    signals_df = strategy.generate_signals()

    # Assert
    # Check that NO signal occurred at '10:45' because ADX (26) was not > 27
    assert signals_df['signal'].sum() == 0
