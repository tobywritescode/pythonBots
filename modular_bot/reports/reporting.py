# reporting.py
from datetime import datetime
import pandas as pd

def generate_report(report_data: dict, file_path: str):
    """
    Generates a detailed markdown report from the backtest results and saves it to a file.

    Args:
        report_data (dict): A dictionary containing all data for the report.
        file_path (str): The path to save the markdown file.
    """
    # --- Extract data for convenience ---
    backtest_params = report_data['backtest_params']
    risk_params = report_data['risk_params']
    strategy_details = report_data['strategy']
    filter_details = report_data['filters']
    results_df = report_data['results_df']

    # --- Calculate Final Metrics ---
    initial_balance = backtest_params['initial_balance']
    net_pnl = results_df['pnl'].sum()
    final_balance = initial_balance + net_pnl
    win_rate = len(results_df[results_df['pnl'] > 0]) / len(results_df) * 100 if not results_df.empty else 0
    total_trades = len(results_df)
    pnl_per_trade = net_pnl / total_trades if total_trades > 0 else 0

    # --- Build the Markdown Report String ---
    report_string = f"""
# Backtest Report: {strategy_details['name']} on {backtest_params['epic']}

**Run Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Summary

| Metric              | Value                                   |
|---------------------|-----------------------------------------|
| **Net P&L**         | **£{net_pnl:,.2f}**                      |
| **Final Balance**   | **£{final_balance:,.2f}**                |
| Win Rate            | {win_rate:.2f}%                         |
| Total Trades        | {total_trades}                          |
| Average P&L/Trade   | £{pnl_per_trade:,.2f}                    |
| Initial Balance     | £{initial_balance:,.2f}                  |

---

## Configuration

### Strategy: {strategy_details['name']}
"""
    for key, value in strategy_details.items():
        if key != 'name':
            report_string += f"- **{key.replace('_', ' ').title()}:** {value}\n"

    if filter_details:
        report_string += "\n### Filters Applied\n"
        for f in filter_details:
            report_string += f"#### {f['name']}\n"
            for key, value in f.items():
                if key != 'name':
                    report_string += f"- **{key.replace('_', ' ').title()}:** {value}\n"

    report_string += f"""
### Risk & Backtest Parameters
- **EPIC:** {backtest_params['epic']}
- **Timeframe:** {backtest_params['start_date'].strftime('%Y-%m-%d')} to {backtest_params['end_date'].strftime('%Y-%m-%d')}
- **Risk per Trade:** {risk_params['risk_per_trade_percent']}%
- **Risk/Reward Ratio:** 1:{risk_params['risk_reward_ratio']}
- **Trailing Stop ATRs:** {risk_params['trailing_stop_atr_multiplier']}

---

## Trade Log

"""
    # Convert DataFrame to markdown table
    if not results_df.empty:
        # Format columns for better readability
        log_df = results_df.copy()
        log_df['entry_time'] = log_df['entry_time'].dt.strftime('%Y-%m-%d %H:%M')
        log_df['exit_time'] = log_df['exit_time'].dt.strftime('%Y-%m-%d %H:%M')
        for col in ['pnl', 'entry_price', 'exit_price', 'initial_stop_loss', 'take_profit', 'units']:
            if col in log_df.columns:
                log_df[col] = log_df[col].apply(lambda x: f'{x:,.2f}')

        # Select and rename columns for the report
        log_df = log_df[['direction', 'entry_time', 'entry_price', 'exit_time', 'exit_price', 'pnl']]
        log_df.columns = ['Direction', 'Entry Time', 'Entry Price', 'Exit Time', 'Exit Price', 'P&L (£)']
        report_string += log_df.to_markdown(index=False)
    else:
        report_string += "No trades were executed."

    # --- Write to file ---
    try:
        with open(file_path, 'w') as f:
            f.write(report_string)
        print(f"\n--- 📈 REPORT GENERATED 📈 ---")
        print(f"Successfully saved backtest report to: {file_path}")
        print("--------------------------------\n")
    except IOError as e:
        print(f"Error writing report to file: {e}")
