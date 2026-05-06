#!/usr/bin/env python3
"""
S&P 500 Backfill — 2021-12-31 ONLY (one-time fix)
JP Trust Learning

Background: input_sp500_daily.csv is missing all 493 ticker rows for 2021-12-31.
Dec 31, 2021 was a Friday — NYSE was OPEN as the final trading day of 2021
(S&P 500 closed at 4,766.18, -0.26%). The original Yahoo Finance pull pipeline
glitched specifically for that date; benchmark CSV (SPY/QQQ/DIA) has the data
fine, only the SP500 universe is missing.

This script:
1. Reads existing CSV
2. Aborts if 2021-12-31 already populated (idempotent)
3. Identifies the universe = tickers that had data on 2021-12-30 (the day before
   the gap) — this is the most accurate "S&P 500 on Dec 31, 2021" universe
4. Fetches Dec 31, 2021 OHLCV for each ticker via yfinance (auto_adjust=True
   to match existing CSV's adjusted-price convention)
5. Inserts rows into CSV, sorts by Ticker+Date, writes back

Run via workflow_dispatch on .github/workflows/backfill_sp500_20211231.yml.
After successful run, this script + workflow can be deleted.
"""

import yfinance as yf
import pandas as pd
import time
import sys

# =============================================================================
# CONFIG
# =============================================================================
CSV_FILE = 'input_sp500_daily.csv'
TARGET_DATE = '2021-12-31'
REFERENCE_DATE = '2021-12-30'   # day before gap → use as universe source

# yfinance fetch range — narrow window around target to be safe with timezone/DST
FETCH_START = '2021-12-30'
FETCH_END = '2022-01-04'        # exclusive end → covers Dec 30, 31 + Jan 3


# =============================================================================
# MAIN
# =============================================================================
def main():
    print('=' * 60)
    print(f'📊 SP500 backfill — {TARGET_DATE} (single-day fix)')
    print('=' * 60)

    # --- Read existing CSV ---
    print(f'📂 Reading {CSV_FILE} ...')
    df = pd.read_csv(CSV_FILE)
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    print(f'   {len(df):,} rows · {df["Ticker"].nunique()} unique tickers')

    # --- Idempotency check ---
    existing = df[df['Date'] == TARGET_DATE]
    if len(existing) > 0:
        print(f'⚠️  {TARGET_DATE} already has {len(existing)} rows — aborting (no-op)')
        return 0

    # --- Universe: tickers with data on the day before the gap ---
    ref = df[df['Date'] == REFERENCE_DATE]
    if len(ref) == 0:
        print(f'❌ No data found for reference date {REFERENCE_DATE} — cannot determine universe')
        return 1

    tickers = sorted(ref['Ticker'].unique().tolist())
    print(f'📋 Universe = {len(tickers)} tickers (had data on {REFERENCE_DATE})')

    # --- Fetch each ticker individually (matches existing daily script pattern) ---
    new_rows = []
    failures = []
    for i, t in enumerate(tickers):
        if (i + 1) % 50 == 0:
            print(f'   ... {i + 1}/{len(tickers)}  (got {len(new_rows)}, failed {len(failures)})')
        try:
            stock = yf.Ticker(t)
            hist = stock.history(
                start=FETCH_START,
                end=FETCH_END,
                interval='1d',
                auto_adjust=True,   # match existing CSV's adjusted-price convention
            )
            if hist.empty:
                failures.append((t, 'empty'))
                continue

            hist = hist.reset_index()
            if hist['Date'].dt.tz is not None:
                hist['Date'] = hist['Date'].dt.tz_localize(None)
            hist['DateStr'] = hist['Date'].dt.strftime('%Y-%m-%d')

            row = hist[hist['DateStr'] == TARGET_DATE]
            if row.empty:
                failures.append((t, f'no row for {TARGET_DATE}'))
                continue

            r = row.iloc[0]
            # Sanity: skip rows with missing/NaN price data
            if pd.isna(r['Close']) or float(r['Close']) <= 0:
                failures.append((t, f'invalid Close={r["Close"]}'))
                continue

            new_rows.append({
                'Ticker': t,
                'Date': TARGET_DATE,
                'Open':   round(float(r['Open']), 2),
                'High':   round(float(r['High']), 2),
                'Low':    round(float(r['Low']), 2),
                'Close':  round(float(r['Close']), 2),
                'Volume': int(r['Volume']) if not pd.isna(r['Volume']) else 0,
            })
        except Exception as e:
            failures.append((t, str(e)[:50]))

    print()
    print(f'✓  Got {len(new_rows)} rows · ✗  Failed {len(failures)}')
    if failures:
        print(f'   First 20 failures: {failures[:20]}')

    if not new_rows:
        print('❌ No data fetched — aborting (CSV unchanged)')
        return 1

    # --- Insert + sort + write ---
    new_df = pd.DataFrame(new_rows)
    combined = pd.concat([df, new_df], ignore_index=True)
    combined = combined.sort_values(['Ticker', 'Date']).reset_index(drop=True)
    combined.to_csv(CSV_FILE, index=False)

    print()
    print(f'💾 Wrote {len(combined):,} total rows to {CSV_FILE}')
    print(f'   ({len(new_rows)} new rows added for {TARGET_DATE})')
    print('✅ Done')

    # --- Spot-check: print 3 sample rows ---
    print()
    print(f'📍 Sample rows for {TARGET_DATE}:')
    sample = combined[combined['Date'] == TARGET_DATE].head(3)
    print(sample.to_string(index=False))

    return 0


if __name__ == '__main__':
    sys.exit(main())
