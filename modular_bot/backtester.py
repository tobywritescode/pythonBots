# backtester.py
import pandas as pd


# pandas_ta dependency removed to resolve environment conflicts

def print_trade_summary(trade_info):
    """
    Prints a formatted summary of a single trade to the console.
    """
    result_color = "\033[92m" if trade_info['result'] == 'WIN' else "\033[91m"
    end_color = "\033[0m"

    summary = f"""
------------------------------------------------------------------
TRADE CLOSED: {trade_info['date'].strftime('%Y-%m-%d')} | {trade_info['epic']}
- **Result**:      {result_color}{trade_info['result']}{end_color} ({trade_info['direction']})
- **P&L**:         {result_color}£{trade_info['pnl']:.2f}{end_color}
- **Risk/Reward**: {trade_info['rr_ratio']:.2f}
- **Entry**:       {trade_info['entry_price']:.5f} at {trade_info['entry_time'].strftime('%H:%M:%S')}
- **Exit**:        {trade_info['exit_price']:.5f} at {trade_info['exit_time'].strftime('%H:%M:%S')}
- **Stop Loss**:   {trade_info['stop_loss']:.5f}
- **Take Profit**: {trade_info['take_profit']:.5f}
------------------------------------------------------------------"""
    print(summary)


def prepare_data(price_list):
    """
    Converts the raw list of candle objects into a clean DataFrame.
    """
    if not price_list:
        return pd.DataFrame()
    df = pd.DataFrame(price_list)
    df['datetime'] = pd.to_datetime(df['snapshotTimeUTC'])
    df.set_index('datetime', inplace=True)
    df = df[~df.index.duplicated(keep='first')]
    # Flatten the price dicts into separate columns
    df['open'] = df['openPrice'].apply(lambda p: p['bid'])
    df['high'] = df['highPrice'].apply(lambda p: p['bid'])
    df['low'] = df['lowPrice'].apply(lambda p: p['bid'])
    df['close'] = df['closePrice'].apply(lambda p: p['bid'])
    print(f"Data prepared. Date range: {df.index.min()} to {df.index.max()}")
    return df


def _calculate_atr(df, period=14):
    """Helper to calculate ATR."""
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def calculate_indicators(df, fast_ma=20, slow_ma=50, adx_period=14):
    """
    Calculates EMA, ATR, and ADX indicators without external libraries.
    """
    print(f"Calculating indicators: EMA({fast_ma}, {slow_ma}), ADX({adx_period}), ATR(14)...")

    # EMA Calculations
    df[f'EMA_{fast_ma}'] = df['close'].ewm(span=fast_ma, adjust=False).mean()
    df[f'EMA_{slow_ma}'] = df['close'].ewm(span=slow_ma, adjust=False).mean()

    # ATR Calculation
    df['ATRr_14'] = _calculate_atr(df, period=14)

    # ADX Calculation
    plus_dm = (df['high'] - df['high'].shift()).where(
        (df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']), 0)
    minus_dm = (df['low'].shift() - df['low']).where(
        (df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()), 0)

    plus_di = 100 * (plus_dm.ewm(alpha=1 / adx_period, adjust=False).mean() / df['ATRr_14'])
    minus_di = 100 * (minus_dm.ewm(alpha=1 / adx_period, adjust=False).mean() / df['ATRr_14'])

    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    df[f'ADX_{adx_period}'] = dx.ewm(alpha=1 / adx_period, adjust=False).mean()

    df.dropna(inplace=True)
    print("Indicators calculated and NaN rows dropped.")
    return df


def run_backtest(df_with_signals, epic, risk_reward_ratio, initial_balance, position_size_per_trade):
    """
    A generic backtesting engine that executes trades based on a 'signal' column.
    """
    all_trades = []
    current_balance = initial_balance
    in_trade = False
    trade_details = {}

    for candle in df_with_signals.itertuples():
        if in_trade:
            exit_price = 0
            result = None

            if trade_details['direction'] == 'LONG':
                if candle.low <= trade_details['stop_loss']:
                    result = 'LOSS'
                    exit_price = trade_details['stop_loss']
                elif candle.high >= trade_details['take_profit']:
                    result = 'WIN'
                    exit_price = trade_details['take_profit']

            elif trade_details['direction'] == 'SHORT':
                if candle.high >= trade_details['stop_loss']:
                    result = 'LOSS'
                    exit_price = trade_details['stop_loss']
                elif candle.low <= trade_details['take_profit']:
                    result = 'WIN'
                    exit_price = trade_details['take_profit']

            if result:
                in_trade = False
                stop_distance = abs(trade_details['entry_price'] - trade_details['stop_loss'])
                monetary_risk = ((stop_distance / trade_details['entry_price']) * position_size_per_trade) if \
                trade_details['entry_price'] != 0 else 0
                pnl = (monetary_risk * risk_reward_ratio) if result == 'WIN' else -monetary_risk
                current_balance += pnl

                trade_details.update({
                    'result': result, 'exit_time': candle.Index, 'exit_price': exit_price,
                    'pnl': pnl, 'rr_ratio': risk_reward_ratio
                })

                all_trades.append(trade_details.copy())
                print_trade_summary(trade_details)
                trade_details = {}

        if not in_trade and candle.signal != 0:
            in_trade = True
            entry_price = candle.close
            stop_loss = candle.stop_loss_price
            risk_per_unit = abs(entry_price - stop_loss)

            if risk_per_unit == 0:
                in_trade = False
                continue

            take_profit_distance = risk_per_unit * risk_reward_ratio
            direction = 'LONG' if candle.signal == 1 else 'SHORT'

            if direction == 'LONG':
                take_profit = entry_price + take_profit_distance
            else:
                take_profit = entry_price - take_profit_distance

            trade_details = {
                'epic': epic, 'date': candle.Index.date(), 'entry_time': candle.Index,
                'entry_price': entry_price, 'direction': direction, 'stop_loss': stop_loss,
                'take_profit': take_profit, 'position_size': position_size_per_trade
            }

    return all_trades
