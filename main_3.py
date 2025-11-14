from datetime import datetime

import pandas as pd

from modular_bot.api_client import fetch_all_data


def main():
    # --- Strategy Parameters ---
    backtest_params = {
        'epic': 'J225',
        'start_date': datetime(2025, 11, 2),  # Start date to "prime" indicators
        'end_date': datetime(2025, 11, 13),  # Your original end date
        'data_filepath': 'data_1m.csv'
    }

    pine_script_inputs = {
        'atr_len': 14,
        'sl_multiplier': 1.0,
        'tp_multiplier': 5.0,
        'breakeven_trigger_R': 1.0,
        'ob_level': 80,
        'os_level': 20,
        'trend_params': {'k': 3, 'd': 3, 'rsi_len': 14, 'stoch_len': 21},
        'short_params': {'k': 3, 'd': 3, 'rsi_len': 14, 'stoch_len': 14},
        'adx_len': 14,
        'adx_threshold': 20
    }

    initial_capital = 1000000

    # --- Phase 1: Get Data ---
    # ... (code is unchanged from your file) ...
    try:
        df_1m = pd.read_csv(backtest_params['data_filepath'], index_col='datetime', parse_dates=True)
        print(f"Successfully loaded 1M data from {backtest_params['data_filepath']}")
    except FileNotFoundError:
        print(f"{backtest_params['data_filepath']} not found. Fetching from API...")
        all_candle_data = fetch_all_data(
            backtest_params['epic'],
            backtest_params['start_date'],
            backtest_params['end_date'],
            resolution="MINUTE"
        )
        if not all_candle_data:
            print("\nWARNING: No data fetched. Cannot run backtest.")
            return

        df_1m = prepare_data(all_candle_data)
        df_1m.to_csv(backtest_params['data_filepath'])
        print(f"Data saved to {backtest_params['data_filepath']} for future use.")

    if df_1m.empty:
        print("No data available to process.")
        return

    df_45m, df_4h = resample_data(df_1m)


def resample_data(df_1m: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Resamples 1-minute OHLCV data to 45-minute and 4-hour timeframes.

    Args:
        df_1m: DataFrame with 1-minute candlestick data.

    Returns:
        A tuple containing two DataFrames: (df_45m, df_4h).
    """
    print("Resampling data to 45M and 4H timeframes...")
    ohlc_agg = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }
    df_45m = df_1m.resample('45T').agg(ohlc_agg).dropna()
    df_4h = df_1m.resample('4H').agg(ohlc_agg).dropna()
    print(f"Resampling complete. 45M shape: {df_45m.shape}, 4H shape: {df_4h.shape}")
    return df_45m, df_4h


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




if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"\n--- Total execution time: {end_time - start_time:.2f} seconds ---")