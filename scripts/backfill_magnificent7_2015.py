#!/usr/bin/env python3
"""
Magnificent 7 Historical Backfill — ONE-TIME SCRIPT
JP Trust Learning

Downloads historical data from 2015-01-01 to 2021-12-31
and merges with existing input_magnificent7_daily.csv (which starts from 2022).

Note: META was Facebook (FB) before June 2022 and GOOGL was traded under
the same ticker. yfinance handles ticker history correctly.

Run once via GitHub Actions workflow_dispatch, then delete.
"""

import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime

# =============================================================================
# CONFIG
# =============================================================================
CSV_FILE = 'input_magnificent7_daily.csv'
LOG_FOLDER = 'logs'
BACKFILL_START = '2015-01-01'
BACKFILL_END = '2021-12-31'

# Magnificent 7 — current tickers
# META: traded as FB before Jun 2022, yfinance META history goes back to 2012
TICKERS = ['AAPL', 'AMZN', 'GOOGL', 'META', 'MSFT', 'NVDA', 'TSLA']

# =============================================================================
# FUNCTIONS
# =============================================================================

def download_stock_data(ticker, start_date, end_date, retry_count=3):
    """Download daily stock data for a single ticker"""
    for attempt in range(retry_count):
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date, interval='1d')

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
            if attempt == retry_count - 1:
                return None
            time.sleep(2)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    print('=' * 60)
    print('📊 Magnificent 7 Historical Backfill — ONE-TIME')
    print(f'📅 Period: {BACKFILL_START} → {BACKFILL_END}')
    print(f'📌 Tickers: {", ".join(TICKERS)}')
    print('=' * 60)

    # Read existing data
    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        df_existing['Date'] = pd.to_datetime(df_existing['Date'])
        print(f'📂 Existing: {len(df_existing):,} rows ({df_existing["Date"].min().date()} → {df_existing["Date"].max().date()})')
    else:
        df_existing = pd.DataFrame(columns=['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        print('📂 No existing file')

    # Download historical data
    all_data = []
    success_count = 0
    failed_tickers = []

    for ticker in TICKERS:
        print(f'\n📥 Downloading {ticker} ({BACKFILL_START} → {BACKFILL_END})...')
        df = download_stock_data(ticker, BACKFILL_START, BACKFILL_END)

        if df is not None and not df.empty:
            all_data.append(df)
            success_count += 1
            print(f'  ✅ {ticker}: {len(df)} rows')
        else:
            failed_tickers.append(ticker)
            print(f'  ❌ {ticker}: no data')

        time.sleep(0.5)

    if not all_data:
        print('❌ No historical data downloaded')
        exit(1)

    df_historical = pd.concat(all_data, ignore_index=True)
    print(f'\n📊 Downloaded {len(df_historical):,} historical rows from {success_count} tickers')

    # Merge: historical + existing
    df_all = pd.concat([df_historical, df_existing], ignore_index=True)
    df_all['Date'] = pd.to_datetime(df_all['Date'])
    df_all = df_all.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
    df_all = df_all.sort_values(['Ticker', 'Date']).reset_index(drop=True)

    # Save
    df_out = df_all.copy()
    df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')

    # Main file
    df_out.to_csv(CSV_FILE, index=False)
    print(f'\n💾 Saved: {CSV_FILE}')

    # Log file
    os.makedirs(LOG_FOLDER, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    log_filename = f'input_magnificent7_daily_backfill_{timestamp}.csv'
    log_path = os.path.join(LOG_FOLDER, log_filename)
    df_out.to_csv(log_path, index=False)
    print(f'💾 Saved: {LOG_FOLDER}/{log_filename}')

    total_tickers = df_all['Ticker'].nunique()
    print(f'\n📊 Total: {len(df_all):,} rows | {total_tickers} tickers')
    print(f'📅 Range: {df_all["Date"].min().date()} → {df_all["Date"].max().date()}')

    if failed_tickers:
        print(f'\n⚠️ Failed: {", ".join(failed_tickers)}')

    print('\n' + '=' * 60)
    print('🎉 BACKFILL DONE!')
    print('=' * 60)
