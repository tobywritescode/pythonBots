# main.py

from datetime import datetime, time
import pandas as pd

# Import our custom modules
import api_client
from backtester import prepare_data, calculate_indicators, run_backtest
from strategies import MaCrossStrategy, OrbStrategy  # Import the specific strategy you want to test

if __name__ == "__main__":
    # --- Parameters ---
    EPIC = "SPY"
    BACKTEST_START_DATE = datetime(2025, 1, 1)
    BACKTEST_END_DATE = datetime(2025, 7, 9)
    RR_RATIO = 1.5
    SESSION_UTC_TIME = time(13, 30)
    INITIAL_BALANCE = 1000.0
    POSITION_SIZE = 1000.0

    # 1. Fetch data using our API client
    print(f"Fetching data for {EPIC}...")
    all_candle_data = api_client.fetch_all_data(EPIC, BACKTEST_START_DATE, BACKTEST_END_DATE)

    # 2. Prepare the base DataFrame
    df = prepare_data(all_candle_data)

    if not df.empty:
        # 3. Calculate technical indicators
        df_with_indicators = calculate_indicators(df)

        # 4. Initialize the desired strategy
        strategy = MaCrossStrategy(df_with_indicators, fast_ma=20, slow_ma=50)
        # print(f"Initializing ORB Strategy for {SESSION_UTC_TIME} UTC open.")
        # strategy = OrbStrategy(df_with_indicators, session_open_time=SESSION_UTC_TIME)

        # 5. Generate signals from the strategy
        signal_data = strategy.generate_signals()
        df_with_signals = df_with_indicators.join(signal_data)

        # 6. Run the backtest engine with the data and signals
        print("\n--- Starting Backtest Engine ---")
        trade_results = run_backtest(df_with_signals, EPIC, RR_RATIO, INITIAL_BALANCE, POSITION_SIZE)

        # 7. Analyze final results
        results_df = pd.DataFrame(trade_results)
        if not results_df.empty:
            net_pnl = results_df['pnl'].sum()
            win_rate = len(results_df[results_df['pnl'] > 0]) / len(results_df) * 100

            print("\n--- 💰 FINAL BACKTEST SUMMARY 💰 ---")
            print(f"Total Trades: {len(results_df)}")
            print(f"Win Rate: {win_rate:.2f}%")
            print(f"Net P&L: £{net_pnl:.2f}")
            print("--------------------------------------\n")
        else:
            print("\nNo trades were executed during the backtest period.")