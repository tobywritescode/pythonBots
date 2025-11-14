# main.py
import os
from datetime import datetime

import pandas as pd

import api_client
from backtester import prepare_data, calculate_indicators, run_backtest
from strategies import MaCrossStrategy
from filters import AdxFilter
from modular_bot.reports import reporting

if __name__ == "__main__":
    # --- Create required directories ---
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.exists('reports'):
        os.makedirs('reports')

    # --- Parameters ---
    # Grouped parameters for easier management and reporting
    backtest_params = {
        "epic": "SPY",
        "start_date": datetime(2025, 1, 1),
        "end_date": datetime(2025, 7, 9),
        "initial_balance": 10000.0
    }

    risk_params = {
        "risk_per_trade_percent": 2.0,
        "risk_reward_ratio": 2.0,
        "trailing_stop_atr_multiplier": 999
    }

    strategy_params = {
        "fast_ma": 20,
        "slow_ma": 50,
        "trend_period": 200
    }

    filter_params = {
        "adx_threshold": 25
    }

    # --- 1. Fetch or Load Data ---
    # Define a unique filename for the cache
    data_filename = (
        f"{backtest_params['epic']}_"
        f"{backtest_params['start_date'].strftime('%Y%m%d')}_"
        f"{backtest_params['end_date'].strftime('%Y%m%d')}.csv"
    )
    data_filepath = os.path.join('data', data_filename)

    if os.path.exists(data_filepath):
        print(f"Loading data from local cache: {data_filepath}")
        df = pd.read_csv(data_filepath, index_col='datetime', parse_dates=True)
    else:
        print("Local cache not found. Fetching data from API...")
        all_candle_data = api_client.fetch_all_data(
            backtest_params['epic'],
            backtest_params['start_date'],
            backtest_params['end_date']
        )
        if not all_candle_data:
            print("\nWARNING: No data fetched. Cannot run backtest.")
            df = pd.DataFrame()
        else:
            df = prepare_data(all_candle_data)
            df.to_csv(data_filepath)
            print(f"Data saved to {data_filepath} for future use.")

    if not df.empty:
        # 2. Calculate indicators
        df_with_indicators = calculate_indicators(
            df,
            fast_ma=strategy_params['fast_ma'],
            slow_ma=strategy_params['slow_ma'],
            long_term_ma=strategy_params['trend_period']
        )

        if not df_with_indicators.empty:
            # 3. Create filter and strategy instances
            print("\n--- Setting up Strategy and Filters ---")
            adx_filter = AdxFilter(adx_threshold=filter_params['adx_threshold'])
            strategy = MaCrossStrategy(
                df_with_indicators,
                fast_ma=strategy_params['fast_ma'],
                slow_ma=strategy_params['slow_ma'],
                trend_period=strategy_params['trend_period'],
                filters=[adx_filter]
            )

            # 4. Generate final signals
            signal_data = strategy.generate_signals()
            df_with_signals = df_with_indicators.join(signal_data)

            # 5. Run the backtest
            print("\n--- Starting Backtest Engine with Risk-Based Sizing ---")
            trade_results = run_backtest(
                df_with_signals,
                backtest_params['epic'],
                backtest_params['initial_balance'],
                risk_per_trade_percent=risk_params['risk_per_trade_percent'],
                risk_reward_ratio=risk_params['risk_reward_ratio'],
                trailing_stop_atr_multiplier=risk_params['trailing_stop_atr_multiplier']
            )

            # 6. Analyze and Report Results
            if trade_results:
                results_df = pd.DataFrame(trade_results)
                # --- Generate Report ---
                report_data = {
                    "backtest_params": backtest_params,
                    "risk_params": risk_params,
                    "strategy": strategy.get_params(),
                    "filters": [f.get_params() for f in strategy.filters],
                    "results_df": results_df
                }
                report_filename = (
                    f"{strategy.get_params()['name']}_{backtest_params['epic']}_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                )
                report_filepath = os.path.join('reports', report_filename)
                reporting.generate_report(report_data, report_filepath)

            else:
                print("\nNo trades were executed during the backtest period.")