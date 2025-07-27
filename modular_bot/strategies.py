from datetime import datetime


class BaseStrategy:
    """A blueprint for all strategy modules."""
    def __init__(self, df):
        self.df = df.copy()

    def generate_signals(self):
        """
        The core logic of the strategy.
        This method must be implemented by each specific strategy.
        It should return a DataFrame with a 'signal' column.
        """
        raise NotImplementedError("You must implement the generate_signals method!")


class MaCrossStrategy(BaseStrategy):
    """A simple Moving Average Crossover strategy with an ADX regime filter."""

    def __init__(self, df, fast_ma=20, slow_ma=50, atr_multiplier=2, adx_period=14, adx_threshold=25):
        super().__init__(df)
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.atr_multiplier = atr_multiplier
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.fast_ma_col = f'EMA_{self.fast_ma}'
        self.slow_ma_col = f'EMA_{self.slow_ma}'
        self.atr_col = 'ATRr_14'
        self.adx_col = f'ADX_{self.adx_period}'

    def generate_signals(self):
        """
        Generates buy (1) and sell (-1) signals based on MA crossover,
        filtered by ADX for trend strength.
        """
        self.df['signal'] = 0
        self.df['stop_loss_price'] = 0.0

        # Condition 1: Fast MA crosses above Slow MA
        crossover = (self.df[self.fast_ma_col] > self.df[self.slow_ma_col]) & \
                    (self.df[self.fast_ma_col].shift(1) <= self.df[self.slow_ma_col].shift(1))

        # Condition 2: Fast MA crosses below Slow MA
        crossunder = (self.df[self.fast_ma_col] < self.df[self.slow_ma_col]) & \
                     (self.df[self.fast_ma_col].shift(1) >= self.df[self.slow_ma_col].shift(1))

        # Condition 3: ADX is above the threshold, indicating a trend
        trending = self.df[self.adx_col] > self.adx_threshold

        # Combine conditions for final signals
        long_condition = crossover & trending
        short_condition = crossunder & trending

        for index, row in self.df[long_condition].iterrows():
            self.df.loc[index, 'signal'] = 1
            self.df.loc[index, 'stop_loss_price'] = row['low'] - (row[self.atr_col] * self.atr_multiplier)

        for index, row in self.df[short_condition].iterrows():
            self.df.loc[index, 'signal'] = -1
            self.df.loc[index, 'stop_loss_price'] = row['high'] + (row[self.atr_col] * self.atr_multiplier)

        print(f"Generated {len(self.df[self.df['signal'] != 0])} signals for MA Cross w/ ADX Filter.")
        return self.df[['signal', 'stop_loss_price']]

class OrbStrategy(BaseStrategy):
    """
    Opening Range Breakout (ORB) Strategy.
    Generates a signal when the price breaks out of the range defined by an initial candle.
    """

    def __init__(self, df, session_open_time):
        """
        Initializes the ORB Strategy.
        :param df: The DataFrame with price data.
        :param session_open_time: A datetime.time object for the opening candle (e.g., time(13, 0)).
        """
        super().__init__(df)
        self.session_open_time = session_open_time

    def generate_signals(self):
        """
        Identifies the opening range for each day and generates a single breakout signal.
        Returns a DataFrame with 'signal' and 'stop_loss_price' columns.
        """
        print(f"Generating signals for ORB strategy with open time {self.session_open_time}...")
        # Create the columns we will populate
        self.df['signal'] = 0
        self.df['stop_loss_price'] = 0.0

        # Group candles by day to process each day independently
        for date, day_candles in self.df.groupby(self.df.index.date):
            opening_candle_time = datetime.combine(date, self.session_open_time).replace(tzinfo=day_candles.index.tz)

            # Check if the opening candle exists for that day
            if opening_candle_time not in day_candles.index:
                continue

            # Identify the opening range high and low
            first_candle = day_candles.loc[opening_candle_time]
            range_high = first_candle['highPrice']['bid']
            range_low = first_candle['lowPrice']['bid']

            # Skip days with no movement in the opening candle
            if range_high == range_low:
                continue

            # Look for a breakout on subsequent candles within the same day
            for candle_index, candle in day_candles[day_candles.index > opening_candle_time].iterrows():

                # Check for Long Breakout
                if candle['highPrice']['bid'] > range_high:
                    self.df.loc[candle_index, 'signal'] = 1  # Long signal
                    self.df.loc[candle_index, 'stop_loss_price'] = range_low  # Stop is the bottom of the range
                    break  # Found the first breakout for the day, stop looking

                # Check for Short Breakout
                elif candle['lowPrice']['bid'] < range_low:
                    self.df.loc[candle_index, 'signal'] = -1  # Short signal
                    self.df.loc[candle_index, 'stop_loss_price'] = range_high  # Stop is the top of the range
                    break  # Found the first breakout for the day, stop looking

        signals_found = len(self.df[self.df['signal'] != 0])
        print(f"Generated {signals_found} signals.")
        return self.df[['signal', 'stop_loss_price']]
