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




# =============================================================================
# Rotation mini — last ~300 trading days, Close+Volume only
# Used by: sector-rotation.html (JP Trust Sector & Theme Rotation Tracker)
# Includes SPY (from input_benchmark_daily.csv) and GOLD/WTI
# (from input_commodities_daily.csv) as reference series.
# =============================================================================

ROTATION_OUTPUT = 'mini_sp500_rotation.csv'
ROTATION_DAYS   = 300
BENCHMARK_CSV   = 'input_benchmark_daily.csv'
COMMODITIES_CSV = 'input_commodities_daily.csv'


def build_rotation_mini() -> int:
    if not os.path.exists(INPUT_CSV):
        print(f'❌ [rotation] Input file not found: {INPUT_CSV}', file=sys.stderr)
        return 1

    df = pd.read_csv(
        INPUT_CSV,
        usecols=['Ticker', 'Date', 'Close', 'Volume'],
        dtype={'Ticker': 'string', 'Date': 'string'},
    )

    frames = [df]

    # SPY benchmark
    if os.path.exists(BENCHMARK_CSV):
        b = pd.read_csv(
            BENCHMARK_CSV,
            usecols=['Ticker', 'Date', 'Close', 'Volume'],
            dtype={'Ticker': 'string', 'Date': 'string'},
        )
        frames.append(b[b['Ticker'] == 'SPY'])
    else:
        print(f'⚠️ [rotation] {BENCHMARK_CSV} not found — SPY missing')

    # GOLD / WTI reference
    if os.path.exists(COMMODITIES_CSV):
        c = pd.read_csv(
            COMMODITIES_CSV,
            usecols=['Ticker', 'Date', 'Close', 'Volume'],
            dtype={'Ticker': 'string', 'Date': 'string'},
        )
        frames.append(c[c['Ticker'].isin(['GOLD', 'WTI'])])
    else:
        print(f'⚠️ [rotation] {COMMODITIES_CSV} not found — GOLD/WTI missing')

    allrows = pd.concat(frames, ignore_index=True)

    unique_dates = sorted(allrows['Date'].dropna().unique(), reverse=True)
    keep_dates = set(unique_dates[:ROTATION_DAYS])
    mini = allrows[allrows['Date'].isin(keep_dates)].copy()

    mini['Close'] = pd.to_numeric(mini['Close'], errors='coerce').round(4)
    mini['Volume'] = pd.to_numeric(mini['Volume'], errors='coerce').fillna(0).astype('int64')
    mini.dropna(subset=['Close'], inplace=True)
    mini.sort_values(['Ticker', 'Date'], inplace=True, kind='stable')
    mini.reset_index(drop=True, inplace=True)

    mini.to_csv(ROTATION_OUTPUT, index=False, lineterminator='\n')

    out_size_mb = os.path.getsize(ROTATION_OUTPUT) / (1024 * 1024)
    print(f'📤 [rotation] Wrote {ROTATION_OUTPUT}: {len(mini):,} rows · '
          f'{out_size_mb:.1f} MB · {min(keep_dates)} → {max(keep_dates)}')
    return 0


if __name__ == '__main__':
    rc = main()
    rc2 = build_rotation_mini()
    sys.exit(rc or rc2)
