#!/usr/bin/env python3
"""
VIX Daily Price Updater — GitHub Actions Version
JP Trust Learning

Downloads daily data for CBOE Volatility Index (^VIX)
Output format matches input_benchmark_daily.csv exactly:
  Ticker, Date, Open, High, Low, Close, Volume

Note: VIX is an index (not a tradable ETF), so Volume is always 0.

Output Files:
  - input_vix_daily.csv (overwrite)
  - logs/input_vix_daily_YYYYMMDD_HHMM.csv (backup)
"""

import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime, timedelta

# =============================================================================
# CONFIG
# =============================================================================
CSV_FILE = 'input_vix_daily.csv'
LOG_FOLDER = 'logs'
FALLBACK_START = '2015-01-01'

# VIX index — stored as "VIX" in Ticker column for downstream compatibility
YF_SYMBOL = '^VIX'
TICKER_LABEL = 'VIX'

# =============================================================================
# FUNCTIONS
# =============================================================================

def download_vix_data(start_date, end_date, retry_count=3):
    """Download daily VIX data"""
    for attempt in range(retry_count):
        try:
            idx = yf.Ticker(YF_SYMBOL)
            df = idx.history(start=start_date, end=end_date, interval='1d')

            if df.empty:
                return None

            df = df.reset_index()
            df['Ticker'] = TICKER_LABEL

            # Handle timezone
            if df['Date'].dt.tz is not None:
                df['Date'] = df['Date'].dt.tz_localize(None)

            df = df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

            # Round prices (VIX has 2 decimal precision)
            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = df[col].round(2)
            df['Volume'] = df['Volume'].fillna(0).astype(int)

            return df

        except Exception as e:
            print(f'  ⚠️ Attempt {attempt+1} failed: {e}')
            if attempt == retry_count - 1:
                return None
            time.sleep(2)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    print('=' * 60)
    print('📊 VIX Daily Updater — JP Trust Learning')
    print(f'📌 Symbol: {YF_SYMBOL} (stored as "{TICKER_LABEL}")')
    print('=' * 60)

    # Create logs folder
    os.makedirs(LOG_FOLDER, exist_ok=True)

    # Read existing data
    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        df_existing['Date'] = pd.to_datetime(df_existing['Date'])
        if len(df_existing) > 0 and pd.notna(df_existing['Date'].max()):
            last_date = df_existing['Date'].max()
            start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f'📂 Existing: {len(df_existing):,} rows')
            print(f'📅 Last date: {last_date.date()}')
        else:
            start_date = FALLBACK_START
            print(f'📂 Existing file is empty — starting from {FALLBACK_START}')
    else:
        df_existing = pd.DataFrame(columns=['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        start_date = FALLBACK_START
        print(f'📂 No existing file — starting from {FALLBACK_START}')

    end_date = datetime.now().strftime('%Y-%m-%d')
    print(f'\n🔄 Fetching: {start_date} → {end_date}')

    # Download
    print(f'\n📥 Downloading {YF_SYMBOL}...')
    df_new = download_vix_data(start_date, end_date)

    # Merge and save
    if df_new is not None and not df_new.empty:
        new_count = len(df_new)
        print(f'  ✅ {TICKER_LABEL}: {new_count} rows')
        print(f'\n📊 Downloaded {new_count:,} new rows')

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
        log_filename = f'input_vix_daily_{timestamp}.csv'
        log_path = os.path.join(LOG_FOLDER, log_filename)
        df_out.to_csv(log_path, index=False)
        print(f'💾 Saved: {LOG_FOLDER}/{log_filename}')

        print(f'\n📊 Total: {len(df_all):,} rows')
        print(f'📅 Range: {df_all["Date"].min().date()} → {df_all["Date"].max().date()}')
        print(f'\n✅ VIX downloaded successfully!')

    else:
        print('\nℹ️  No new data available (market closed / holiday / already up to date)')

    print('\n' + '=' * 60)
    print('🎉 DONE!')
    print('=' * 60)
