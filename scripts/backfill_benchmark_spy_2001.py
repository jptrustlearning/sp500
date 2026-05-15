#!/usr/bin/env python3
"""
SPY Historical Backfill 2001-2014 — ONE-TIME SCRIPT
JP Trust Learning

Adds SPY daily data from 2001-01-01 to 2014-12-31 into the production
benchmark CSV (input_benchmark_daily.csv).

Why merge into production (unlike the SP500 backfill which uses a separate file):
- Benchmark CSV is tiny (~440 KB) → after backfill ~615 KB, well under GitHub's
  100 MB push limit. No need for a separate "since2001" file.
- Single source of truth — hist2001 dashboard fetches the same benchmark URL
  as production, no HTML changes needed.
- Production strategy dashboards filter startYear >= 2015 → pre-2015 SPY rows
  are loaded but ignored in display/ranking. No behavior change.

⚠️ SPY existed since 1993, so no survivorship-bias issue here (single ETF that
still trades today). DIA and QQQ also have pre-2015 data available; this script
intentionally backfills SPY ONLY (the benchmark used by hist2001 backtest).

Run once via GitHub Actions workflow_dispatch.
"""

import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime

# =============================================================================
# CONFIG
# =============================================================================
CSV_FILE = 'input_benchmark_daily.csv'
LOG_FOLDER = 'logs'
TICKER = 'SPY'
BACKFILL_START = '2001-01-01'
BACKFILL_END = '2014-12-31'

# =============================================================================
# FUNCTIONS
# =============================================================================

def download_stock_data(ticker, start_date, end_date, retry_count=3):
    """Download daily stock data for a single ticker."""
    for attempt in range(retry_count):
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date, interval='1d', auto_adjust=True)

            if df.empty:
                return None

            df = df.reset_index()
            df['Ticker'] = ticker

            if df['Date'].dt.tz is not None:
                df['Date'] = df['Date'].dt.tz_localize(None)

            df = df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = df[col].round(2)
            df['Volume'] = df['Volume'].astype(int)

            return df

        except Exception as e:
            print(f'  retry {attempt+1}/{retry_count} failed: {e}')
            if attempt == retry_count - 1:
                return None
            time.sleep(2)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    print('=' * 60)
    print(f'📊 {TICKER} Historical Backfill — ONE-TIME')
    print(f'📅 Period: {BACKFILL_START} → {BACKFILL_END}')
    print(f'💾 Target: {CSV_FILE} (MERGE with existing 2015+ data)')
    print('=' * 60)

    # Read existing benchmark CSV (has SPY/DIA/QQQ from 2015+)
    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        df_existing['Date'] = pd.to_datetime(df_existing['Date'])
        print(f'📂 Existing: {len(df_existing):,} rows ({df_existing["Date"].min().date()} → {df_existing["Date"].max().date()})')
        existing_tickers = sorted(df_existing['Ticker'].unique().tolist())
        print(f'   Tickers: {existing_tickers}')
    else:
        print(f'❌ {CSV_FILE} not found')
        exit(1)

    # Download SPY historical data
    print(f'\n📥 Downloading {TICKER} ({BACKFILL_START} → {BACKFILL_END})...')
    df_spy = download_stock_data(TICKER, BACKFILL_START, BACKFILL_END)

    if df_spy is None or df_spy.empty:
        print(f'❌ No historical data downloaded for {TICKER}')
        exit(1)

    print(f'📊 Downloaded {len(df_spy):,} rows for {TICKER}')
    print(f'   Range: {df_spy["Date"].min().date()} → {df_spy["Date"].max().date()}')

    # Belt-and-suspenders: clip strictly to BACKFILL_END
    end_dt = pd.Timestamp(BACKFILL_END)
    df_spy = df_spy[df_spy['Date'] <= end_dt]

    # Merge: historical SPY (2001-2014) + existing (all tickers 2015+)
    df_all = pd.concat([df_spy, df_existing], ignore_index=True)
    df_all['Date'] = pd.to_datetime(df_all['Date'])
    df_all = df_all.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
    df_all = df_all.sort_values(['Ticker', 'Date']).reset_index(drop=True)

    # Save
    df_out = df_all.copy()
    df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')
    df_out.to_csv(CSV_FILE, index=False)

    size_kb = os.path.getsize(CSV_FILE) / 1024
    print(f'\n💾 Saved: {CSV_FILE} ({size_kb:.1f} KB)')

    # Log file (timestamped backup)
    os.makedirs(LOG_FOLDER, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    log_filename = f'input_benchmark_daily_spy_backfill_{timestamp}.csv'
    log_path = os.path.join(LOG_FOLDER, log_filename)
    df_out.to_csv(log_path, index=False)
    print(f'💾 Saved: {LOG_FOLDER}/{log_filename}')

    # Summary
    print(f'\n📊 Total: {len(df_all):,} rows')
    print(f'📅 Range: {df_all["Date"].min().date()} → {df_all["Date"].max().date()}')
    for t in sorted(df_all['Ticker'].unique().tolist()):
        sub = df_all[df_all['Ticker'] == t]
        print(f'   {t}: {len(sub):,} rows ({sub["Date"].min().date()} → {sub["Date"].max().date()})')

    print('\n' + '=' * 60)
    print('🎉 SPY BACKFILL DONE!')
    print('ℹ️  hist2001 HTML now has SPY benchmark coverage 2001-2026.')
    print('ℹ️  Production strategies unchanged (startYear >= 2015 filter).')
    print('=' * 60)
