import pandas as pd
import pytest
from strategies import MaCrossStrategy
from filters import AdxFilter


@pytest.fixture
def sample_market_data():
    """
    Creates a sample DataFrame for testing.
    - Long Crossover at '10:45'.
    - Price is ABOVE the 200-period MA (EMA_20) at '10:45', so it's a valid uptrend.
    """
    data = {
        'open': [100, 101, 102, 103, 104, 105],
        'high': [101, 102, 103, 104, 105, 106],
        'low': [99, 100, 101, 102, 103, 104],
        'close': [101, 101, 101, 102, 103, 105],  # Close at 102 during signal
        'EMA_5': [100, 100, 101, 102, 103, 104],  # Fast MA
        'EMA_10': [101, 101, 101, 101, 102, 103],  # Slow MA
        'EMA_20': [100, 100, 100, 100, 101, 101],  # Long-term MA (using 20 for simplicity)
        'ATRr_14': [1, 1, 1, 1, 1, 1],  # ATR value
        'ADX_14': [20, 22, 24, 26, 28, 20]  # ADX value
    }
    df = pd.DataFrame(data, index=pd.to_datetime(
        ['2025-01-01 10:00', '2025-01-01 10:15', '2025-01-01 10:30', '2025-01-01 10:45', '2025-01-01 11:00',
         '2025-01-01 11:15']))
    return df


def test_ma_cross_signal_with_trend_and_adx_filter(sample_market_data):
    """
    Tests that a signal is generated when crossover, trend, and ADX conditions are met.
    """
    # Arrange
    adx_filter = AdxFilter(adx_threshold=25)
    strategy = MaCrossStrategy(
        sample_market_data,
        fast_ma=5,
        slow_ma=10,
        trend_period=20,  # Using 20 as our long-term MA for this test
        filters=[adx_filter]
    )

    # Act
    signals_df = strategy.generate_signals()

    # Assert
    # At '10:45', crossover happens, close(102) > EMA_20(100), and ADX(26) > 25. Signal should be 1.
    assert signals_df.loc['2025-01-01 10:45:00']['signal'] == 1


def test_ma_cross_signal_blocked_by_trend_filter(sample_market_data):
    """
    Tests that a signal is blocked if it goes against the long-term trend,
    even if crossover and ADX conditions are met.
    """
    # Arrange
    adx_filter = AdxFilter(adx_threshold=25)
    # Modify the data so the price is below the long-term trend MA
    data_copy = sample_market_data.copy()
    data_copy.loc['2025-01-01 10:45:00', 'EMA_20'] = 103

    strategy = MaCrossStrategy(
        data_copy,
        fast_ma=5,
        slow_ma=10,
        trend_period=20,
        filters=[adx_filter]
    )

    # Act
    signals_df = strategy.generate_signals()

    # Assert
    # At '10:45', crossover and ADX are fine, but close(102) is NOT > EMA_20(103). Signal should be 0.
    assert signals_df.loc['2025-01-01 10:45:00']['signal'] == 0


def test_ma_cross_signal_blocked_by_adx_filter(sample_market_data):
    """
    Tests that a signal is blocked if ADX is too low,
    even if crossover and trend conditions are met.
    """
    # Arrange
    # Set the ADX threshold high enough to block the signal
    adx_filter = AdxFilter(adx_threshold=27)
    strategy = MaCrossStrategy(
        sample_market_data,
        fast_ma=5,
        slow_ma=10,
        trend_period=20,
        filters=[adx_filter]
    )

    # Act
    signals_df = strategy.generate_signals()

    # Assert
    # At '10:45', crossover and trend are fine, but ADX(26) is NOT > 27. Signal should be 0.
    assert signals_df.loc['2025-01-01 10:45:00']['signal'] == 0