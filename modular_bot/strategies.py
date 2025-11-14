import pandas as pd
from datetime import datetime, time
# Assuming filters.py is in the same directory
from filters import BaseFilter


class BaseStrategy:
    """A blueprint for all strategy modules, now with filter handling."""

    def __init__(self, df, filters: list[BaseFilter] = None):
        self.df = df.copy()
        self.filters = filters if filters is not None else []

    def _generate_raw_signals(self):
        """
        Generates the core entry signals before any filters are applied.
        This method MUST be implemented by child strategies.
        """
        raise NotImplementedError("You must implement the _generate_raw_signals method!")

    def get_params(self) -> dict:
        """Returns the strategy's parameters as a dictionary for reporting."""
        raise NotImplementedError("You must implement the get_params method!")

    def generate_signals(self):
        """
        Generates the final signals by applying all filters to the raw signals.
        """
        raw_signals_df = self._generate_raw_signals()

        # Start with a baseline condition that is always true
        final_filter = pd.Series(True, index=self.df.index)

        # Apply each filter sequentially
        for f in self.filters:
            final_filter &= f.apply(self.df)

        # A signal is only valid if it occurs when the final filter is True
        raw_signals_df['signal'] = raw_signals_df['signal'].where(final_filter, 0)

        print(f"Generated {len(raw_signals_df[raw_signals_df['signal'] != 0])} final signals after applying filters.")
        return raw_signals_df


class MaCrossStrategy(BaseStrategy):
    """A simple Moving Average Crossover strategy with an added long-term trend filter."""

    def __init__(self, df, fast_ma=20, slow_ma=50, trend_period=200, atr_multiplier=2,
                 filters: list[BaseFilter] = None):
        super().__init__(df, filters)
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.trend_period = trend_period
        self.atr_multiplier = atr_multiplier
        self.fast_ma_col = f'EMA_{self.fast_ma}'
        self.slow_ma_col = f'EMA_{self.slow_ma}'
        self.trend_col = f'EMA_{self.trend_period}'
        self.atr_col = 'ATRr_14'

    def get_params(self) -> dict:
        """Returns the strategy's parameters for reporting."""
        return {
            'name': self.__class__.__name__,
            'fast_ma': self.fast_ma,
            'slow_ma': self.slow_ma,
            'trend_period': self.trend_period,
            'atr_multiplier_for_sl': self.atr_multiplier
        }

    def _generate_raw_signals(self):
        """
        Generates buy (1) and sell (-1) signals based on MA crossover.
        This version now also includes the long-term trend direction as a filter.
        """
        signals_df = pd.DataFrame(index=self.df.index)
        signals_df['signal'] = 0
        signals_df['stop_loss_price'] = 0.0

        # Raw crossover signals
        crossover = (self.df[self.fast_ma_col] > self.df[self.slow_ma_col]) & \
                    (self.df[self.fast_ma_col].shift(1) <= self.df[self.slow_ma_col].shift(1))

        crossunder = (self.df[self.fast_ma_col] < self.df[self.slow_ma_col]) & \
                     (self.df[self.fast_ma_col].shift(1) >= self.df[self.slow_ma_col].shift(1))

        # Directional trend filter conditions
        in_uptrend = self.df['close'] > self.df[self.trend_col]
        in_downtrend = self.df['close'] < self.df[self.trend_col]

        # Combine raw signals with the trend filter
        long_condition = crossover & in_uptrend
        short_condition = crossunder & in_downtrend

        for index, row in self.df[long_condition].iterrows():
            signals_df.loc[index, 'signal'] = 1
            signals_df.loc[index, 'stop_loss_price'] = row['low'] - (row[self.atr_col] * self.atr_multiplier)

        for index, row in self.df[short_condition].iterrows():
            signals_df.loc[index, 'signal'] = -1
            signals_df.loc[index, 'stop_loss_price'] = row['high'] + (row[self.atr_col] * self.atr_multiplier)

        print(f"Generated {len(signals_df[signals_df['signal'] != 0])} raw signals for MA Cross.")
        return signals_df

# --- ORB Strategy remains unchanged as it doesn't use filters yet ---
class OrbStrategy(BaseStrategy):
    """Opening Range Breakout (ORB) Strategy."""

    def __init__(self, df, session_open_time):
        super().__init__(df, filters=None)  # Explicitly no filters for ORB
        self.session_open_time = session_open_time

    def get_params(self) -> dict:
        """Returns the strategy's parameters for reporting."""
        return {
            'name': self.__class__.__name__,
            'session_open_time': self.session_open_time.strftime('%H:%M')
        }

    def _generate_raw_signals(self):
        signals_df = pd.DataFrame(index=self.df.index)
        signals_df['signal'] = 0
        signals_df['stop_loss_price'] = 0.0
        for date, day_candles in self.df.groupby(self.df.index.date):
            opening_candle_time = datetime.combine(date, self.session_open_time).replace(tzinfo=day_candles.index.tz)
            if opening_candle_time not in day_candles.index: continue
            first_candle = day_candles.loc[opening_candle_time]
            range_high, range_low = first_candle['high'], first_candle['low']
            if range_high == range_low: continue
            for idx, candle in day_candles[day_candles.index > opening_candle_time].iterrows():
                if candle['high'] > range_high:
                    signals_df.loc[idx, 'signal'], signals_df.loc[idx, 'stop_loss_price'] = 1, range_low
                    break
                elif candle['low'] < range_low:
                    signals_df.loc[idx, 'signal'], signals_df.loc[idx, 'stop_loss_price'] = -1, range_high
                    break
        return signals_df

    def generate_signals(self):
        # ORB has its own daily logic, so we bypass the standard filter application for now
        raw_signals = self._generate_raw_signals()
        print(f"Generated {len(raw_signals[raw_signals['signal'] != 0])} signals for ORB Strategy.")
        return raw_signals