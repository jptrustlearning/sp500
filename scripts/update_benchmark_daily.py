#!/usr/bin/env python3
"""
Market Benchmark Daily Price Updater — GitHub Actions Version
JP Trust Learning

Downloads daily price data for benchmark ETFs: SPY, QQQ, DIA
Output format matches input_sp500_daily.csv exactly:
  Ticker, Date, Open, High, Low, Close, Volume

Output Files:
  - input_benchmark_daily.csv (overwrite)
  - logs/input_benchmark_daily_YYYYMMDD_HHMM.csv (backup)
"""

import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime, timedelta

# =============================================================================
# CONFIG
# =============================================================================
CSV_FILE = 'input_benchmark_daily.csv'
LOG_FOLDER = 'logs'
FALLBACK_START = '2022-01-01'

# Benchmark ETFs
TICKERS = ['SPY', 'QQQ', 'DIA']

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

            # Handle timezone
            if df['Date'].dt.tz is not None:
                df['Date'] = df['Date'].dt.tz_localize(None)

            df = df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

            # Round prices
            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = df[col].round(2)
            df['Volume'] = df['Volume'].astype(int)

            return df

        except Exception as e:
            print(f'  ⚠️ Attempt {attempt+1} failed for {ticker}: {e}')
            if attempt == retry_count - 1:
                return None
            time.sleep(2)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    print('=' * 60)
    print('📊 Market Benchmark Daily Updater — JP Trust Learning')
    print(f'📌 Tickers: {", ".join(TICKERS)}')
    print('=' * 60)

    # Create logs folder
    os.makedirs(LOG_FOLDER, exist_ok=True)

    # Read existing data
    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        df_existing['Date'] = pd.to_datetime(df_existing['Date'])
        last_date = df_existing['Date'].max()
        start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
        print(f'📂 Existing: {len(df_existing):,} rows')
        print(f'📅 Last date: {last_date.date()}')
    else:
        df_existing = pd.DataFrame(columns=['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        start_date = FALLBACK_START
        print(f'📂 No existing file — starting from {FALLBACK_START}')

    end_date = datetime.now().strftime('%Y-%m-%d')
    print(f'\n🔄 Fetching: {start_date} → {end_date}')

    # Download
    all_new_data = []
    success_count = 0
    failed_tickers = []

    for ticker in TICKERS:
        print(f'\n📥 Downloading {ticker}...')
        df = download_stock_data(ticker, start_date, end_date)

        if df is not None and not df.empty:
            all_new_data.append(df)
            success_count += 1
            print(f'  ✅ {ticker}: {len(df)} rows')
        else:
            failed_tickers.append(ticker)
            print(f'  ❌ {ticker}: no data')

        time.sleep(0.5)

    # Merge and save
    if all_new_data:
        df_new = pd.concat(all_new_data, ignore_index=True)
        new_count = len(df_new)
        print(f'\n📊 Downloaded {new_count:,} new rows from {success_count} tickers')

        # Merge with existing
        df_all = pd.concat([df_existing, df_new], ignore_index=True)
        df_all['Date'] = pd.to_datetime(df_all['Date'])
        df_all = df_all.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
        df_all = df_all.sort_values(['Ticker', 'Date']).reset_index(drop=True)

        # Prepare output
        df_out = df_all.copy()
        df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')

        # File 1: Main file
        df_out.to_csv(CSV_FILE, index=False)
        print(f'\n💾 Saved: {CSV_FILE}')

        # File 2: Log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        log_filename = f'input_benchmark_daily_{timestamp}.csv'
        log_path = os.path.join(LOG_FOLDER, log_filename)
        df_out.to_csv(log_path, index=False)
        print(f'💾 Saved: {LOG_FOLDER}/{log_filename}')

        total_tickers = df_all['Ticker'].nunique()
        print(f'\n📊 Total: {len(df_all):,} rows | {total_tickers} tickers')
        print(f'📅 Range: {df_all["Date"].min().date()} → {df_all["Date"].max().date()}')

    else:
        print('\nℹ️  No new data available (market closed / holiday / already up to date)')

    # Report
    if failed_tickers:
        print(f'\n⚠️ Failed: {", ".join(failed_tickers)}')
    else:
        print(f'\n✅ All {len(TICKERS)} tickers downloaded successfully!')

    print('\n' + '=' * 60)
    print('🎉 DONE!')
    print('=' * 60)
