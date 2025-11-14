# backtester.py
import pandas as pd
import numpy as np


def print_trade_summary(trade_info):
    """Prints a formatted summary of a single trade to the console."""
    result_color = "\033[92m" if trade_info['pnl'] > 0 else "\033[91m"
    end_color = "\033[0m"
    result = "WIN" if trade_info['pnl'] > 0 else "LOSS"

    summary = f"""
------------------------------------------------------------------
TRADE CLOSED: {trade_info['date'].strftime('%Y-%m-%d')} | {trade_info['epic']}
- **Result**:      {result_color}{result}{end_color} ({trade_info['direction']})
- **P&L**:         {result_color}£{trade_info['pnl']:.2f}{end_color}
- **Units Traded**: {trade_info['units']:.4f}
- **Entry**:       {trade_info['entry_price']:.5f} at {trade_info['entry_time'].strftime('%H:%M:%S')}
- **Exit**:        {trade_info['exit_price']:.5f} at {trade_info['exit_time'].strftime('%H:%M:%S')}
- **Initial SL**:  {trade_info['initial_stop_loss']:.5f}
- **Take Profit**: {trade_info['take_profit']:.5f}
------------------------------------------------------------------"""
    print(summary)


def prepare_data(price_list):
    """Converts the raw list of candle objects into a clean DataFrame."""
    if not price_list: return pd.DataFrame()
    df = pd.DataFrame(price_list)
    df['datetime'] = pd.to_datetime(df['snapshotTimeUTC'])
    df.set_index('datetime', inplace=True)
    df = df[~df.index.duplicated(keep='first')]
    df['open'] = df['openPrice'].apply(lambda p: p['bid'])
    df['high'] = df['highPrice'].apply(lambda p: p['bid'])
    df['low'] = df['lowPrice'].apply(lambda p: p['bid'])
    df['close'] = df['closePrice'].apply(lambda p: p['bid'])
    volume_field = 'lastTradedVolume'

    if volume_field in df.columns:
        df['volume'] = pd.to_numeric(df[volume_field])
        print(f"Successfully extracted volume from '{volume_field}'.")
    else:
        print(f"WARNING: Volume field '{volume_field}' not found!")
        print("Please check DEBUG output for the correct field name and update the 'volume_field' variable.")
        print("VWAP calculation will fail without volume.")
        df['volume'] = 0

    print(f"Data prepared. Date range: {df.index.min()} to {df.index.max()}")

    final_cols = ['open', 'high', 'low', 'close', 'volume']
    df = df[final_cols]

    df.dropna(inplace=True)
    return df


def _calculate_atr(df, period=14):
    """Helper to calculate ATR."""
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def calculate_indicators(df, fast_ma=20, slow_ma=50, long_term_ma=200, adx_period=14):
    """Calculates EMA, ATR, and ADX indicators."""
    print(f"Calculating indicators: EMA({fast_ma}, {slow_ma}, {long_term_ma}), ADX({adx_period}), ATR(14)...")
    df[f'EMA_{fast_ma}'] = df['close'].ewm(span=fast_ma, adjust=False).mean()
    df[f'EMA_{slow_ma}'] = df['close'].ewm(span=slow_ma, adjust=False).mean()
    df[f'EMA_{long_term_ma}'] = df['close'].ewm(span=long_term_ma, adjust=False).mean()
    df['ATRr_14'] = _calculate_atr(df, period=14)
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


def run_backtest(df_with_signals, epic, initial_balance, risk_per_trade_percent=2.0, risk_reward_ratio=1.5,
                 trailing_stop_atr_multiplier=2.5):
    """
    Backtesting engine with risk-based position sizing.
    """
    all_trades = []
    current_balance = initial_balance
    in_trade = False
    trade_details = {}

    for candle in df_with_signals.itertuples():
        if in_trade:
            exit_price = 0
            if trade_details['direction'] == 'LONG':
                new_trailing_stop = candle.high - (candle.ATRr_14 * trailing_stop_atr_multiplier)
                trade_details['current_stop_loss'] = max(trade_details['current_stop_loss'], new_trailing_stop)
                if candle.high >= trade_details['take_profit']:
                    exit_price = trade_details['take_profit']
                elif candle.low <= trade_details['current_stop_loss']:
                    exit_price = trade_details['current_stop_loss']
            else:  # SHORT
                new_trailing_stop = candle.low + (candle.ATRr_14 * trailing_stop_atr_multiplier)
                trade_details['current_stop_loss'] = min(trade_details['current_stop_loss'], new_trailing_stop)
                if candle.low <= trade_details['take_profit']:
                    exit_price = trade_details['take_profit']
                elif candle.high >= trade_details['current_stop_loss']:
                    exit_price = trade_details['current_stop_loss']

            if exit_price > 0:
                in_trade = False
                price_change = (exit_price - trade_details['entry_price']) if trade_details[
                                                                                  'direction'] == 'LONG' else (
                            trade_details['entry_price'] - exit_price)
                pnl = price_change * trade_details['units']
                current_balance += pnl
                trade_details.update({'exit_time': candle.Index, 'exit_price': exit_price, 'pnl': pnl})
                all_trades.append(trade_details.copy())
                print_trade_summary(trade_details)
                trade_details = {}

        if not in_trade and candle.signal != 0:
            in_trade = True
            entry_price = candle.close
            initial_stop_loss = candle.stop_loss_price
            direction = 'LONG' if candle.signal == 1 else 'SHORT'

            risk_per_unit = abs(entry_price - initial_stop_loss)
            if risk_per_unit == 0:
                in_trade = False
                continue

            # --- Position Sizing Calculation ---
            monetary_risk = current_balance * (risk_per_trade_percent / 100.0)
            units_to_trade = monetary_risk / risk_per_unit

            take_profit_distance = risk_per_unit * risk_reward_ratio
            take_profit = entry_price + take_profit_distance if direction == 'LONG' else entry_price - take_profit_distance

            trade_details = {
                'epic': epic, 'date': candle.Index.date(), 'entry_time': candle.Index,
                'entry_price': entry_price, 'direction': direction,
                'initial_stop_loss': initial_stop_loss,
                'current_stop_loss': initial_stop_loss,
                'take_profit': take_profit,
                'units': units_to_trade
            }

    return all_trades
