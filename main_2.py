# run_backtest.py
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
import time
import os
import matplotlib.pyplot as plt
import mplfinance as mpf

# --- Import your broker/data functions ---
from modular_bot.api_client import fetch_all_data
from modular_bot.backtester import prepare_data


# --- Phase 1: Data Acquisition & Resampling ---
def resample_data(df_1m):
    """Resamples 1M OHLCV data into 45M and 4H timeframes."""
    # ... (code is unchanged from your file) ...
    if df_1m.empty:
        print("Cannot resample empty DataFrame.")
        return pd.DataFrame(), pd.DataFrame()

    print(f"Resampling 1M data (start: {df_1m.index.min()}, end: {df_1m.index.max()})...")

    # Define aggregation rules
    agg_rules = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }

    if df_1m.index.tz is None:
        try:
            df_1m.index = df_1m.index.tz_localize('UTC')
            print("Localized 1M index to UTC for resampling.")
        except Exception as e:
            print(f"Could not localize index, proceeding as-is. Error: {e}")

    # Resample to 45-minute
    df_45m = df_1m.resample('45min', label='right', closed='right').agg(agg_rules).dropna()

    # Resample to 4-hour
    df_4h = df_1m.resample('4H', label='right', closed='right').agg(agg_rules).dropna()

    print(f"Resampling complete. 45M bars: {len(df_45m)}, 4H bars: {len(df_4h)}")
    return df_45m, df_4h


# --- Phase 2: Indicator Calculation ---
def calculate_indicators(df_4h, df_45m, trend_params, short_params, atr_len, adx_len):
    """
    Calculates StochRSI, ATR, and ADX indicators.
    """
    # ... (code is unchanged from your file) ...
    print("Calculating indicators...")

    # Calculate 4-Hour Trend StochRSI
    stoch_rsi_4h = ta.stochrsi(
        df_4h['close'],
        length=trend_params['stoch_len'],
        rsi_length=trend_params['rsi_len'],
        k=trend_params['k'],
        d=trend_params['d']
    )
    if stoch_rsi_4h is not None and not stoch_rsi_4h.empty:
        df_4h['trend_srsi_k'] = stoch_rsi_4h[
            f'STOCHRSIk_{trend_params['stoch_len']}_{trend_params['rsi_len']}_{trend_params['k']}_{trend_params['d']}']
        df_4h['trend_srsi_d'] = stoch_rsi_4h[
            f'STOCHRSId_{trend_params['stoch_len']}_{trend_params['rsi_len']}_{trend_params['k']}_{trend_params['d']}']
    else:
        df_4h['trend_srsi_k'] = np.nan
        df_4h['trend_srsi_d'] = np.nan

    # Calculate 45-Minute Short StochRSI
    stoch_rsi_45m = ta.stochrsi(
        df_45m['close'],
        length=short_params['stoch_len'],
        rsi_length=short_params['rsi_len'],
        k=short_params['k'],
        d=short_params['d']
    )
    if stoch_rsi_45m is not None and not stoch_rsi_45m.empty:
        df_45m['short_srsi_k'] = stoch_rsi_45m[
            f'STOCHRSIk_{short_params['stoch_len']}_{short_params['rsi_len']}_{short_params['k']}_{short_params['d']}']
        df_45m['short_srsi_d'] = stoch_rsi_45m[
            f'STOCHRSId_{short_params['stoch_len']}_{short_params['rsi_len']}_{short_params['k']}_{short_params['d']}']
    else:
        df_45m['short_srsi_k'] = np.nan
        df_45m['short_srsi_d'] = np.nan

    # Calculate 45M ATR
    df_45m['atr'] = ta.atr(df_45m['high'], df_45m['low'], df_45m['close'], length=atr_len)

    # Calculate 4-Hour ADX
    adx_4h = ta.adx(df_4h['high'], df_4h['low'], df_4h['close'], length=adx_len)
    if adx_4h is not None and not adx_4h.empty:
        df_4h['adx'] = adx_4h[f'ADX_{adx_len}']
    else:
        df_4h['adx'] = np.nan

    print("Indicator calculation complete.")
    return df_4h, df_45m


# --- Phase 3: Backtest Loop ---

def run_backtest_loop(df, params):
    """
    Runs the main event-driven backtest.
    'df' is the master 1-minute DataFrame with all indicator data merged.
    """
    print("Starting backtest loop...")

    # --- State variables ---
    trade_bias = 0

    # Anchors
    lowest_price_during_setup = float('inf')
    temp_anchor_low_timestamp = None
    confirmed_anchor_low_timestamp = None

    highest_price_during_setup = float('-inf')
    temp_anchor_high_timestamp = None
    confirmed_anchor_high_timestamp = None

    # --- AVWAP: REMOVED ROLLING SUM VARIABLES ---
    avwap_low = np.nan
    avwap_high = np.nan

    # Position
    position = 0
    entry_price = 0.0
    stop_loss_price = 0.0
    take_profit_price = 0.0
    entry_timestamp = None

    entry_avwap = np.nan
    entry_trend_srsi_k = np.nan
    entry_short_srsi_k = np.nan
    entry_adx = np.nan

    # Break-Even State
    breakeven_trigger_price = 0.0
    breakeven_stop_activated = False

    trades = []

    df_prev = df.shift(1)

    # --- MAIN LOOP ---
    for row, prev_row in zip(df.itertuples(), df_prev.itertuples()):

        # ==============================================================================
        # STEP 1: UPDATE INDICATORS & STATE
        # ==============================================================================

        # --- 1a. Update Bias (4-Hour Logic) ---
        if (prev_row.trend_srsi_k < params['os_level'] and
                row.trend_srsi_k >= params['os_level'] and
                row.adx > params['adx_threshold']):
            trade_bias = 1

        elif prev_row.trend_srsi_k < params['ob_level'] and row.trend_srsi_k >= params['ob_level']:
            if trade_bias == 1: trade_bias = 0

        if (prev_row.trend_srsi_k > params['ob_level'] and
                row.trend_srsi_k <= params['ob_level'] and
                row.adx > params['adx_threshold']):
            trade_bias = -1

        elif prev_row.trend_srsi_k > params['os_level'] and row.trend_srsi_k <= params['os_level']:
            if trade_bias == -1: trade_bias = 0

        # --- 1b. Update Setup & Anchors (45-Minute Logic) ---
        is_long_setup = (trade_bias == 1 and row.short_srsi_k < params['os_level'])
        is_short_setup = (trade_bias == -1 and row.short_srsi_k > params['ob_level'])

        if (is_long_setup and (prev_row.short_srsi_k >= params['os_level'])):
            lowest_price_during_setup = row.low
            temp_anchor_low_timestamp = row.Index
        if (is_short_setup and (prev_row.short_srsi_k <= params['ob_level'])):
            highest_price_during_setup = row.high
            temp_anchor_high_timestamp = row.Index

        if is_long_setup:
            if row.low < lowest_price_during_setup:
                lowest_price_during_setup = row.low
                temp_anchor_low_timestamp = row.Index
        if is_short_setup:
            if row.high > highest_price_during_setup:
                highest_price_during_setup = row.high
                temp_anchor_high_timestamp = row.Index

        # --- Anchor Confirmation ---
        if (prev_row.short_srsi_k < params['os_level'] and row.short_srsi_k >= params[
            'os_level']) and trade_bias == 1 and temp_anchor_low_timestamp:
            confirmed_anchor_low_timestamp = temp_anchor_low_timestamp
            lowest_price_during_setup = float('inf')
            # --- ROLLING SUMS REMOVED ---

        if (prev_row.short_srsi_k > params['ob_level'] and row.short_srsi_k <= params[
            'ob_level']) and trade_bias == -1 and temp_anchor_high_timestamp:
            confirmed_anchor_high_timestamp = temp_anchor_high_timestamp
            highest_price_during_setup = float('-inf')
            # --- ROLLING SUMS REMOVED ---

        # --- 1c. Update AVWAP (Cumulative Calculation) ---
        # --- LOGIC ENTIRELY REBUILT ---
        long_avwap_active = False
        short_avwap_active = False

        # Reset AVWAP values for this bar
        avwap_low = np.nan
        avwap_high = np.nan

        if confirmed_anchor_low_timestamp and (
                not confirmed_anchor_high_timestamp or confirmed_anchor_low_timestamp > confirmed_anchor_high_timestamp):
            long_avwap_active = True
            # This is the new, correct calculation
            if row.Index >= confirmed_anchor_low_timestamp:
                try:
                    # Slice the dataframe from the anchor to the current bar
                    avwap_slice = df.loc[confirmed_anchor_low_timestamp:row.Index]
                    # Calculate cumulative (Price * Volume)
                    pv = (avwap_slice['low'] * avwap_slice['volume']).sum()
                    # Calculate cumulative Volume
                    vol_sum = avwap_slice['volume'].sum()
                    # Calculate the true AVWAP
                    avwap_low = pv / vol_sum if vol_sum > 0 else np.nan
                except Exception as e:
                    # This can happen if timestamps are misaligned, but should be rare
                    print(f"Warning: AVWAP slice failed at {row.Index}. {e}")
                    avwap_low = np.nan

        if confirmed_anchor_high_timestamp and (
                not confirmed_anchor_low_timestamp or confirmed_anchor_high_timestamp > confirmed_anchor_low_timestamp):
            short_avwap_active = True
            if row.Index >= confirmed_anchor_high_timestamp:
                try:
                    # Slice the dataframe from the anchor to the current bar
                    avwap_slice = df.loc[confirmed_anchor_high_timestamp:row.Index]
                    # Calculate cumulative (Price * Volume)
                    pv = (avwap_slice['high'] * avwap_slice['volume']).sum()
                    # Calculate cumulative Volume
                    vol_sum = avwap_slice['volume'].sum()
                    # Calculate the true AVWAP
                    avwap_high = pv / vol_sum if vol_sum > 0 else np.nan
                except Exception as e:
                    print(f"Warning: AVWAP slice failed at {row.Index}. {e}")
                    avwap_high = np.nan

        # ==============================================================================
        # STEP 2: CHECK EXITS (Existing Positions)
        # ==============================================================================
        if position == 1:

            if not breakeven_stop_activated:
                if row.high >= breakeven_trigger_price:
                    stop_loss_price = entry_price
                    breakeven_stop_activated = True

            if row.low <= stop_loss_price:
                trades.append(('Long', entry_timestamp, row.Index, entry_price, stop_loss_price,
                               stop_loss_price, take_profit_price, confirmed_anchor_low_timestamp, 'low',
                               entry_avwap, entry_trend_srsi_k, entry_short_srsi_k, entry_adx))
                position = 0
                continue

            elif row.high >= take_profit_price:
                trades.append(('Long', entry_timestamp, row.Index, entry_price, take_profit_price,
                               stop_loss_price, take_profit_price, confirmed_anchor_low_timestamp, 'low',
                               entry_avwap, entry_trend_srsi_k, entry_short_srsi_k, entry_adx))
                position = 0
                continue

            # This exit logic now uses the correctly calculated avwap_low
            elif not pd.isna(avwap_low) and row.close < avwap_low:
                trades.append(('Long', entry_timestamp, row.Index, entry_price, row.close,
                               stop_loss_price, take_profit_price, confirmed_anchor_low_timestamp, 'low',
                               entry_avwap, entry_trend_srsi_k, entry_short_srsi_k, entry_adx))
                position = 0
                continue

        elif position == -1:

            if not breakeven_stop_activated:
                if row.low <= breakeven_trigger_price:
                    stop_loss_price = entry_price
                    breakeven_stop_activated = True

            if row.high >= stop_loss_price:
                trades.append(('Short', entry_timestamp, row.Index, entry_price, stop_loss_price,
                               stop_loss_price, take_profit_price, confirmed_anchor_high_timestamp, 'high',
                               entry_avwap, entry_trend_srsi_k, entry_short_srsi_k, entry_adx))
                position = 0
                continue

            elif row.low <= take_profit_price:
                trades.append(('Short', entry_timestamp, row.Index, entry_price, take_profit_price,
                               stop_loss_price, take_profit_price, confirmed_anchor_high_timestamp, 'high',
                               entry_avwap, entry_trend_srsi_k, entry_short_srsi_k, entry_adx))
                position = 0
                continue

            # This exit logic now uses the correctly calculated avwap_high
            elif not pd.isna(avwap_high) and row.close > avwap_high:
                trades.append(('Short', entry_timestamp, row.Index, entry_price, row.close,
                               stop_loss_price, take_profit_price, confirmed_anchor_high_timestamp, 'high',
                               entry_avwap, entry_trend_srsi_k, entry_short_srsi_k, entry_adx))
                position = 0
                continue

        # ==============================================================================
        # STEP 3: CHECK ENTRIES (New Positions)
        # ==============================================================================
        # This logic is now fed the correct AVWAP value
        if position == 0 and not pd.isna(row.atr):

            if long_avwap_active and not pd.isna(avwap_low):
                if row.low <= avwap_low <= row.high:
                    position = 1
                    entry_price = avwap_low
                    stop_distance = row.atr * params['sl_multiplier']
                    stop_loss_price = entry_price - stop_distance
                    take_profit_price = entry_price + (stop_distance * params['tp_multiplier'])
                    entry_timestamp = row.Index

                    entry_avwap = avwap_low
                    entry_trend_srsi_k = row.trend_srsi_k
                    entry_short_srsi_k = row.short_srsi_k
                    entry_adx = row.adx

                    breakeven_trigger_price = entry_price + (stop_distance * params['breakeven_trigger_R'])
                    breakeven_stop_activated = False

            elif short_avwap_active and not pd.isna(avwap_high):
                if row.low <= avwap_high <= row.high:
                    position = -1
                    entry_price = avwap_high
                    stop_distance = row.atr * params['sl_multiplier']
                    stop_loss_price = entry_price + stop_distance
                    take_profit_price = entry_price - (stop_distance * params['tp_multiplier'])
                    entry_timestamp = row.Index

                    entry_avwap = avwap_high
                    entry_trend_srsi_k = row.trend_srsi_k
                    entry_short_srsi_k = row.short_srsi_k
                    entry_adx = row.adx

                    breakeven_trigger_price = entry_price - (stop_distance * params['breakeven_trigger_R'])
                    breakeven_stop_activated = False

    print(f"Backtest loop complete. Found {len(trades)} trades.")
    return trades


# --- Phase 4: Performance Analysis & Charting ---
def generate_trade_chart(trade_data, full_df, trade_number, context_bars=50, post_bars=20):
    """Generates and saves a candlestick chart for a single trade."""

    try:
        # ... (code is unchanged from your file) ...
        (trade_type, entry_time, exit_time, entry_price, exit_price,
         sl_price, tp_price, anchor_time, avwap_type,
         entry_avwap, entry_trend_k, entry_short_k, entry_adx) = trade_data

        entry_idx = full_df.index.get_loc(entry_time)
        exit_idx = full_df.index.get_loc(exit_time)

        start_idx = max(0, entry_idx - context_bars)
        end_idx = min(len(full_df), exit_idx + post_bars)

        plot_df = full_df.iloc[start_idx:end_idx].copy()

        if plot_df.empty:
            print(f"  Skipping Trade {trade_number}: No data in slice.")
            return

        # --- Re-calculate AVWAP for plotting (now matches backtest logic) ---
        sum_pv = 0.0
        sum_vol = 0.0
        avwap_series = []
        price_col = 'low' if avwap_type == 'low' else 'high'

        # This logic is slow but correct for plotting
        full_slice_df = full_df.loc[anchor_time:plot_df.index[-1]]

        for row in plot_df.itertuples():
            if row.Index < anchor_time:
                avwap_series.append(np.nan)
            else:
                # Get the slice from anchor to *this* row
                current_slice = full_slice_df.loc[anchor_time:row.Index]
                pv = (current_slice[price_col] * current_slice['volume']).sum()
                vol_sum = current_slice['volume'].sum()
                avwap_series.append(pv / vol_sum if vol_sum > 0 else np.nan)

        plot_df['avwap'] = avwap_series

        add_plots = []

        add_plots.append(mpf.make_addplot(plot_df['avwap'], color='blue', width=0.7))

        sl_line = [sl_price] * len(plot_df)
        tp_line = [tp_price] * len(plot_df)
        add_plots.append(mpf.make_addplot(sl_line, color='red', linestyle='--', width=0.7))
        add_plots.append(mpf.make_addplot(tp_line, color='green', linestyle='--', width=0.7))

        entry_marker = [np.nan] * len(plot_df)
        exit_marker = [np.nan] * len(plot_df)

        entry_marker_idx = plot_df.index.get_loc(entry_time)
        exit_marker_idx = plot_df.index.get_loc(exit_time)

        entry_marker[entry_marker_idx] = entry_price * 0.998 if trade_type == 'Long' else entry_price * 1.002
        exit_marker[exit_marker_idx] = exit_price * 1.002 if trade_type == 'Long' else exit_price * 0.998

        add_plots.append(mpf.make_addplot(entry_marker, type='scatter', marker='^' if trade_type == 'Long' else 'v',
                                          color='green' if trade_type == 'Long' else 'red', markersize=100))
        add_plots.append(mpf.make_addplot(exit_marker, type='scatter', marker='x', color='black', markersize=100))

        chart_title = f"Trade {trade_number}: {trade_type} | Entry: {entry_time.strftime('%Y-%m-%d %H:%M')}"
        chart_file = f"./charts/trade_{trade_number:04d}.png"

        mpf.plot(
            plot_df,
            type='candle',
            style='yahoo',
            title=chart_title,
            ylabel='Price',
            addplot=add_plots,
            figsize=(15, 7),
            volume=True,
            panel_ratios=(3, 1),
            savefig=chart_file
        )
        plt.close('all')

    except Exception as e:
        print(f"  ERROR generating chart for Trade {trade_number}: {e}")


def analyze_and_plot_results(trades, initial_capital, df_master):
    """
    Calculates and prints performance statistics, saves a CSV log, and generates charts.
    """
    # ... (code is unchanged from your file) ...
    if not trades:
        print("No trades were executed.")
        return

    if not os.path.exists('./charts'):
        os.makedirs('./charts')
        print("Created './charts' directory for trade plots.")

    new_columns = [
        'Type', 'EntryTime', 'ExitTime', 'EntryPrice', 'ExitPrice',
        'StopLoss', 'TakeProfit', 'AnchorTime', 'AVWAPType',
        'EntryAVWAP', 'EntryTrendSRSI_K', 'EntryShortSRSI_K', 'EntryADX'
    ]
    trade_df = pd.DataFrame(trades, columns=new_columns)

    csv_filename = 'trades_log.csv'
    try:
        trade_df.to_csv(csv_filename, index=False)
        print(f"\nSuccessfully saved trade log to {csv_filename}")
    except Exception as e:
        print(f"\nERROR: Could not save trade log to CSV. {e}")

    # print(f"\nGenerating {len(trade_df)} trade charts...")
    # for i, trade_row in enumerate(trade_df.itertuples(index=False)):
    #     if i < 100:
    #         print(f"  Generating chart for trade {i + 1}...")
    #         generate_trade_chart(trade_row, df_master, i + 1)
    #     elif i == 100:
    #         print("  ... (skipping remaining chart generation to save time) ...")

    print("Chart generation complete.")

    trade_df['P&L'] = np.where(trade_df['Type'] == 'Long',
                               trade_df['ExitPrice'] - trade_df['EntryPrice'],
                               trade_df['EntryPrice'] - trade_df['ExitPrice'])

    gross_profit = trade_df[trade_df['P&L'] > 0]['P&L'].sum()
    gross_loss = abs(trade_df[trade_df['P&L'] < 0]['P&L'].sum())

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
    total_net_pnl = trade_df['P&L'].sum()

    wins = trade_df[trade_df['P&L'] > 0]
    losses = trade_df[trade_df['P&L'] < 0]

    win_rate = (len(wins) / len(trade_df)) * 100 if len(trade_df) > 0 else 0
    avg_win = wins['P&L'].mean()
    avg_loss = abs(losses['P&L'].mean())

    avg_rr = avg_win / avg_loss if avg_loss > 0 else np.inf

    print("\n--- Backtest Results ---")
    print(f"Total Trades:       {len(trade_df)}")
    print(f"Win Rate:           {win_rate:.2f}%")
    print(f"Total Net P&L:      {total_net_pnl:.2f} (points)")
    print(f"Profit Factor:      {profit_factor:.3f}")
    print(f"Avg. Win / Avg. Loss: {avg_rr:.2f} : 1")
    print(f"Average Win:        {avg_win:.2f}")
    print(f"Average Loss:       {avg_loss:.2f}")


# --- Main Execution ---

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

    # --- Phase 1b: Resample ---
    df_45m, df_4h = resample_data(df_1m)

    # --- Phase 2: Calculate Indicators ---
    df_4h, df_45m = calculate_indicators(
        df_4h,
        df_45m,
        pine_script_inputs['trend_params'],
        pine_script_inputs['short_params'],
        pine_script_inputs['atr_len'],
        pine_script_inputs['adx_len']
    )

    # --- Phase 3: Merge Data & Run Backtest ---
    print("Merging dataframes for backtest loop...")

    df_4h_ffilled = df_4h.reindex(df_1m.index, method='ffill')
    df_45m_ffilled = df_45m.reindex(df_1m.index, method='ffill')

    df_master = df_1m.join(df_4h_ffilled, rsuffix='_4h')
    df_master = df_master.join(df_45m_ffilled, rsuffix='_45m')

    df_master.dropna(inplace=True)

    if df_master.empty:
        print("Master DataFrame is empty. Check data alignment or 'start_date' (may need more warm-up data).")
        return

    print(f"Master DataFrame created. Shape: {df_master.shape}. Running backtest...")

    trades = run_backtest_loop(df_master, pine_script_inputs)

    # --- Phase 4: Analyze Results ---
    analyze_and_plot_results(trades, initial_capital, df_master)


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"\n--- Total execution time: {end_time - start_time:.2f} seconds ---")