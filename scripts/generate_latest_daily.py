#!/usr/bin/env python3
"""
Generate latest_daily.csv with the most recent OHLCV data per ticker.
Includes S&P 500, Benchmarks (SPY/QQQ/DIA), and Magnificent 7.
"""
import csv
import os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

INPUT_FILES = [
    os.path.join(BASE_DIR, 'input_sp500_daily.csv'),
    os.path.join(BASE_DIR, 'input_benchmark_daily.csv'),
    os.path.join(BASE_DIR, 'input_magnificent7_daily.csv'),
]

OUTPUT_FILE = os.path.join(BASE_DIR, 'latest_daily.csv')


def load_latest_two_days(filepath):
    """Read CSV, return dict: ticker -> list of (date, open, high, low, close, volume) sorted by date desc."""
    ticker_rows = defaultdict(list)
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.get('Ticker', '').strip()
            date = row.get('Date', '').strip()
            if not ticker or not date:
                continue
            try:
                o = float(row['Open'])
                h = float(row['High'])
                l = float(row['Low'])
                c = float(row['Close'])
                v = int(float(row['Volume']))
            except (ValueError, KeyError):
                continue
            ticker_rows[ticker].append((date, o, h, l, c, v))

    # Keep only the latest 2 dates per ticker for daily change calc
    for ticker in ticker_rows:
        ticker_rows[ticker].sort(key=lambda x: x[0], reverse=True)
        ticker_rows[ticker] = ticker_rows[ticker][:2]

    return ticker_rows


def main():
    all_ticker_data = {}

    for filepath in INPUT_FILES:
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found, skipping.")
            continue
        print(f"Loading {os.path.basename(filepath)}...")
        data = load_latest_two_days(filepath)
        # Merge (later files override if duplicate ticker)
        for ticker, rows in data.items():
            if ticker not in all_ticker_data:
                all_ticker_data[ticker] = rows
            else:
                # Keep the one with the most recent date
                existing_date = all_ticker_data[ticker][0][0]
                new_date = rows[0][0]
                if new_date >= existing_date:
                    all_ticker_data[ticker] = rows

    # Build output rows
    output_rows = []
    for ticker, rows in sorted(all_ticker_data.items()):
        latest = rows[0]  # (date, o, h, l, c, v)
        date, o, h, l, c, v = latest

        # Compute daily change % from previous day's close
        daily_change_pct = 0.0
        if len(rows) >= 2:
            prev_close = rows[1][4]  # previous day's close
            if prev_close > 0:
                daily_change_pct = ((c - prev_close) / prev_close) * 100

        output_rows.append({
            'Ticker': ticker,
            'Date': date,
            'Open': f'{o:.2f}',
            'High': f'{h:.2f}',
            'Low': f'{l:.2f}',
            'Close': f'{c:.2f}',
            'Volume': str(v),
            'Daily_Change_Pct': f'{daily_change_pct:.4f}',
        })

    # Write output
    fieldnames = ['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Daily_Change_Pct']
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Written {len(output_rows)} rows to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
