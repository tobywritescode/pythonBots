import json
from datetime import time, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import requests
import config_demo

API_BASE_URL = "https://demo-api-capital.backend-capital.com"  # Demo API URL
API_HEADERS = {
    'X-CAP-API-KEY': config_demo.api_key,
    'Content-Type': 'application/json'
}

xst = ""
cst = ""


def start_session():
    global xst, cst

    payload1 = json.dumps({
        "identifier": config_demo.identifier,
        "password": config_demo.password
    })
    headers1 = {
        'X-CAP-API-KEY': config_demo.api_key,
        'Content-Type': 'application/json'
    }
    response1 = requests.request("POST", config_demo.session_url, headers=headers1, data=payload1)

    if response1.status_code == 200:
        xst = response1.headers['X-SECURITY-TOKEN']
        cst = response1.headers['CST']
        print("started sesh")

# --- 2. Chunked Data Fetching Function ---
def fetch_all_data(epic, start_date, end_date):
    """
    Fetches all 15-minute data in chunks between a start and end date.
    """
    all_prices = []
    current_date = start_date
    start_session()
    print(f"Starting data fetch for {epic} from {start_date.isoformat()} to {end_date.isoformat()}")

    while current_date < end_date:
        # Format URL for the API call
        from_iso = current_date.isoformat()
        url = f"{API_BASE_URL}/api/v1/prices/{epic}?resolution=MINUTE_15&from={from_iso}&max=240"
        SESH_HEADERS = {
            'X-SECURITY-TOKEN': xst,
            'CST': cst
        }
        try:
            # In your real code, you would use your authenticated session
            response = requests.get(url, headers=SESH_HEADERS)
            response.raise_for_status()  # Raises an exception for bad responses (4xx or 5xx)

            data = response.json()
            prices = data.get('prices', [])

            if not prices:
                # No more data available in this range
                print("No more prices returned, ending fetch.")
                break

            all_prices.extend(prices)

            # Get the last timestamp and set it as the start for the next loop
            last_timestamp_str = prices[-1]['snapshotTimeUTC']
            last_timestamp = datetime.fromisoformat(last_timestamp_str.replace('Z', '+00:00'))

            print(f"Fetched {len(prices)} candles. Last timestamp: {last_timestamp.isoformat()}")

            # Move to the next chunk, adding 1 minute to avoid fetching the same candle twice
            current_date = last_timestamp + timedelta(minutes=1)

        except requests.exceptions.RequestException as e:
            print(f"An API error occurred: {e}")
            break

    print(f"Total candles fetched: {len(all_prices)}")
    return all_prices

# def plot_trade(day_candles_df, trade_info):
#     """
#     Generates and displays a Plotly chart for a single trade.
#     """
#     fig = go.Figure()
#
#     # Add Candlestick trace
#     fig.add_trace(go.Candlestick(
#         x=day_candles_df.index,
#         open=day_candles_df['openPrice'].apply(lambda p: p['bid']),
#         high=day_candles_df['highPrice'].apply(lambda p: p['bid']),
#         low=day_candles_df['lowPrice'].apply(lambda p: p['bid']),
#         close=day_candles_df['closePrice'].apply(lambda p: p['bid']),
#         name='Candles'
#     ))
#
#     # Add lines for trading levels
#     fig.add_hline(y=trade_info['range_high'], line_dash="dash", line_color="blue", annotation_text="Range High", annotation_position="bottom right")
#     fig.add_hline(y=trade_info['range_low'], line_dash="dash", line_color="blue", annotation_text="Range Low", annotation_position="bottom right")
#     fig.add_hline(y=trade_info['take_profit'], line_dash="dot", line_color="green", annotation_text="Take Profit", annotation_position="bottom right")
#     fig.add_hline(y=trade_info['stop_loss'], line_dash="dot", line_color="red", annotation_text="Stop Loss", annotation_position="bottom right")
#
#     # Add a vertical line to mark the entry candle
#     fig.add_vline(
#         x=trade_info['entry_time'].isoformat(),
#         line_dash="longdash",
#         line_color="purple"
#     )
#
#     # 2. Add the annotation separately for more control
#     fig.add_annotation(
#         x=trade_info['entry_time'].isoformat(),
#         y=day_candles_df['highPrice'].apply(lambda p: p['bid']).max(),  # Position text at the top
#         yref="y",
#         yshift=10,  # Shift it slightly above the candles
#         text="Entry",
#         showarrow=True,
#         arrowhead=1,
#         arrowcolor="purple"
#     )
#
#     # Update layout and title
#     title_text = (f"{trade_info['epic']} | {trade_info['date'].strftime('%Y-%m-%d')} | "
#                   f"Direction: {trade_info['direction']} | Result: {trade_info['result']}")
#     fig.update_layout(
#         title=title_text,
#         xaxis_title="Time (UTC)",
#         yaxis_title="Price",
#         xaxis_rangeslider_visible=False, # Hides the range slider at the bottom
#         template="plotly_white"
#     )
#
#     fig.show()

def print_trade_summary(trade_info):
    """
    Prints a formatted summary of a single trade to the console.
    """
    # Determine result and color for printing
    result_color = "\033[92m" if trade_info['result'] == 'WIN' else "\033[91m"
    end_color = "\033[0m" # Resets color

    summary = f"""
------------------------------------------------------------------
TRADE FOUND: {trade_info['date'].strftime('%Y-%m-%d')} | {trade_info['epic']}
- **Result**:      {result_color}{trade_info['result']}{end_color} ({trade_info['direction']})
- **P&L**:         {result_color}£{trade_info['pnl']:.2f}{end_color}
- **Range Set**:   at {trade_info['range_time'].strftime('%H:%M:%S')} UTC
- **Range**:       {trade_info['range_low']:.5f} - {trade_info['range_high']:.5f}
- **Setup Risk**:      {trade_info['trade_risk_percent']:.2f}% (Stop distance on a £{trade_info['position_size']:.2f} position)
- **Entry**:       {trade_info['entry_price']:.5f} at {trade_info['entry_time'].strftime('%H:%M:%S')}
- **Stop Loss**:   {trade_info['stop_loss']:.5f}
- **Take Profit**: {trade_info['take_profit']:.5f}
- **Exit**:            at {trade_info['exit_time'].strftime('%H:%M:%S')} UTC
------------------------------------------------------------------"""
    print(summary)

# --- 3. Data Preparation ---
def prepare_data(price_list):
    """
    Converts the raw list of candle objects into a clean DataFrame,
    keeping the necessary OHLC dictionary structure for plotting.
    """
    if not price_list:
        return pd.DataFrame()
    df = pd.DataFrame(price_list)
    df['datetime'] = pd.to_datetime(df['snapshotTimeUTC'])
    df.set_index('datetime', inplace=True)
    df = df[~df.index.duplicated(keep='first')]
    print(f"Data prepared. Date range: {df.index.min()} to {df.index.max()}")
    # We will return the full DataFrame for plotting purposes
    return df


# --- 4. Main Backtesting Logic (Updated) ---
def run_orb_backtest(df, epic, session_open_time, risk_reward_ratio, initial_balance, position_size):
    """
    Runs the ORB strategy with proper trade exit logic and visualizes trades.
    """
    all_trades_summary = []
    current_balance = initial_balance

    # Group candles by day
    for date, day_candles in df.groupby(df.index.date):
        # 1. Identify the Opening Range
        opening_candle_time = datetime.combine(date, session_open_time).replace(tzinfo=day_candles.index.tz)

        # Make sure the opening candle exists for that day
        if opening_candle_time not in day_candles.index:
            continue

        first_candle = day_candles.loc[opening_candle_time]
        range_high = first_candle['highPrice']['bid']
        range_low = first_candle['lowPrice']['bid']

        # Skip days where the opening range is zero (no price movement)
        if range_high == range_low:
            continue

        risk = range_high - range_low
        take_profit_dist = risk * risk_reward_ratio

        trade_initiated = False

        # 2. Look for a breakout on subsequent candles
        for entry_index, entry_candle in day_candles[day_candles.index > opening_candle_time].iterrows():

            # If a trade is already open for the day, break this loop and move to the next day
            if trade_initiated:
                break

            direction = None
            entry_price = 0
            stop_loss = 0
            take_profit = 0

            # Check for Long Breakout
            if entry_candle['highPrice']['bid'] > range_high:
                direction = 'LONG'
                entry_price = range_high
                stop_loss = range_low
                take_profit = range_high + take_profit_dist

            # Check for Short Breakout
            elif entry_candle['lowPrice']['bid'] < range_low:
                direction = 'SHORT'
                entry_price = range_low
                stop_loss = range_high
                take_profit = range_low - take_profit_dist

            # If a breakout occurred, manage the trade
            if direction:
                trade_initiated = True
                exit_time = None
                result = 'INCONCLUSIVE'  # Default result
                pnl = 0

                # 3. Monitor the trade on candles following the entry
                for exit_index, exit_candle in day_candles[day_candles.index > entry_index].iterrows():

                    # Long trade exit conditions
                    if direction == 'LONG':
                        if exit_candle['lowPrice']['bid'] <= stop_loss:
                            result = 'LOSS'
                            exit_time = exit_index
                            break  # Exit found, stop checking candles
                        elif exit_candle['highPrice']['bid'] >= take_profit:
                            result = 'WIN'
                            exit_time = exit_index
                            break  # Exit found, stop checking candles

                    # Short trade exit conditions
                    elif direction == 'SHORT':
                        if exit_candle['highPrice']['bid'] >= stop_loss:
                            result = 'LOSS'
                            exit_time = exit_index
                            break  # Exit found, stop checking candles
                        elif exit_candle['lowPrice']['bid'] <= take_profit:
                            result = 'WIN'
                            exit_time = exit_index
                            break  # Exit found, stop checking candles

                # 4. If a result was determined (WIN/LOSS), calculate P&L and store details
                if result in ['WIN', 'LOSS']:
                    stop_distance = abs(entry_price - stop_loss)
                    trade_risk_percent = (stop_distance / entry_price) * 100
                    monetary_loss = position_size * (trade_risk_percent / 100.0)

                    if result == 'WIN':
                        pnl = monetary_loss * risk_reward_ratio
                    else:  # LOSS
                        pnl = -monetary_loss

                    current_balance += pnl

                    trade_details = {
                        'epic': epic, 'date': date, 'entry_time': entry_index, 'direction': direction,
                        'result': result, 'range_high': range_high, 'range_low': range_low, 'pnl': pnl,
                        'position_size': position_size, 'exit_time': exit_time,
                        'trade_risk_percent': trade_risk_percent,
                        'stop_loss': stop_loss, 'take_profit': take_profit, 'entry_price': entry_price,
                        'range_time': opening_candle_time,
                    }
                    all_trades_summary.append(trade_details)
                    print_trade_summary(trade_details)

    return all_trades_summary


# --- Example Execution ---
if __name__ == "__main__":
    # --- Parameters ---
    EPIC = "SPY"
    BACKTEST_START_DATE = datetime(2025, 1, 1)
    BACKTEST_END_DATE = datetime(2025, 7, 9)
    RR_RATIO = 1.0

    # --- Session to Test (in UTC) ---
    SESSION_UTC_TIME = time(13, 00)  # London Open

    # 1. Fetch all data in chunks
    all_candle_data = fetch_all_data(EPIC, BACKTEST_START_DATE, BACKTEST_END_DATE)

    # 2. Prepare the DataFrame
    df_15m = prepare_data(all_candle_data)

    if not df_15m.empty:
        # 3. Run the backtest
        trade_results = run_orb_backtest(df_15m, EPIC, SESSION_UTC_TIME, RR_RATIO, 100.00, 50)

        # 4. Collate and analyze results
        results_df = pd.DataFrame(trade_results)
        if not results_df.empty:
            net_pnl = results_df['pnl'].sum()
            pnl_color = "\033[92m" if net_pnl > 0 else "\033[91m"
            end_color = "\033[0m"

            win_rate = len(results_df[results_df['pnl'] > 0]) / len(results_df) * 100

            print(f"\n--- 💰 FINAL BACKTEST SUMMARY 💰 ---")
            print(f"Period: {BACKTEST_START_DATE.date()} to {BACKTEST_END_DATE.date()}")
            print(f"Total Trades: {len(results_df)}")
            print(f"Win Rate: {win_rate:.2f}%")
            print(f"Wins: {len(results_df[results_df['pnl'] > 0])} | Losses: {len(results_df[results_df['pnl'] < 0])}")
            print(f"Net P&L: {pnl_color}£{net_pnl:.2f}{end_color}")
            print("--------------------------------------\n")
        else:
            print("\nNo trades were executed during the backtest period.")