#!/usr/bin/env python3
"""
Mini S&P 500 — Last 14 Trading Days Slicer
JP Trust Learning

Purpose:
  input_sp500_daily.csv (~66 MB, ~1.4M rows since 2015) is too heavy for
  the News page Market Movers sparkline (which only needs the last few days).

  This script reads input_sp500_daily.csv and writes a much smaller
  mini_sp500_last14days.csv containing only the rows from the last 14
  unique trading dates in the dataset. Output is typically ~300–500 KB.

Trim logic:
  1. Read all rows from input_sp500_daily.csv
  2. Collect unique dates and sort descending
  3. Take the top 14 unique dates (=14 trading days, holiday-safe)
  4. Filter rows whose Date is in those 14 dates
  5. Sort by Ticker (asc) then Date (asc) for downstream parsing
  6. Write mini_sp500_last14days.csv (same column schema as input)
"""

import os
import sys
import pandas as pd

INPUT_CSV  = 'input_sp500_daily.csv'
OUTPUT_CSV = 'mini_sp500_last14days.csv'
DAYS       = 14


def main() -> int:
    if not os.path.exists(INPUT_CSV):
        print(f'❌ Input file not found: {INPUT_CSV}', file=sys.stderr)
        return 1

    in_size_mb = os.path.getsize(INPUT_CSV) / (1024 * 1024)
    print(f'📥 Reading {INPUT_CSV} ({in_size_mb:.1f} MB)...')

    # Only load the columns we need to keep memory low.
    df = pd.read_csv(
        INPUT_CSV,
        usecols=['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'],
        dtype={'Ticker': 'string', 'Date': 'string'},
    )
    print(f'   total rows: {len(df):,}')

    # Take the last N unique trading dates (string sort works because YYYY-MM-DD).
    unique_dates = sorted(df['Date'].dropna().unique(), reverse=True)
    if not unique_dates:
        print('❌ No valid dates found in CSV', file=sys.stderr)
        return 1

    keep_dates = set(unique_dates[:DAYS])
    print(f'   unique dates total: {len(unique_dates):,}')
    print(f'   keeping last {len(keep_dates)} dates: '
          f'{min(keep_dates)} → {max(keep_dates)}')

    mini = df[df['Date'].isin(keep_dates)].copy()
    mini.sort_values(['Ticker', 'Date'], inplace=True, kind='stable')
    mini.reset_index(drop=True, inplace=True)

    mini.to_csv(OUTPUT_CSV, index=False)

    out_size_kb = os.path.getsize(OUTPUT_CSV) / 1024
    reduction   = (1 - out_size_kb / 1024 / in_size_mb) * 100
    print(f'📤 Wrote {OUTPUT_CSV}: {len(mini):,} rows · {out_size_kb:.0f} KB '
          f'({reduction:.1f}% smaller)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
