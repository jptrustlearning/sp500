#!/usr/bin/env python3
"""
USDJPY Daily Price Updater — GitHub Actions Version
JP Trust Learning

Downloads daily USDJPY exchange rate (how many JPY per 1 USD) from Yahoo Finance.
Auto-detects whether to do initial backfill (since 2001) or incremental update
(from last existing date + 1).

Single ticker: JPY=X (Yahoo's symbol for USDJPY spot)

Output format matches input_benchmark_daily.csv:
  Ticker, Date, Open, High, Low, Close, Volume
(Volume is always 0 for FX spot — Yahoo doesn't report FX volume.)

Output Files:
  - input_jpy_daily.csv (overwrite)
  - logs/input_jpy_daily_YYYYMMDD_HHMM.csv (backup)
"""

import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime, timedelta

# =============================================================================
# CONFIG
# =============================================================================
CSV_FILE = 'input_jpy_daily.csv'
LOG_FOLDER = 'logs'
FALLBACK_START = '2001-01-01'   # Initial backfill start (when CSV is empty / missing)
TICKER_YAHOO = 'JPY=X'          # Yahoo Finance symbol for USDJPY spot
TICKER_LABEL = 'USDJPY'         # How we store it in the CSV Ticker column

# =============================================================================
# FUNCTIONS
# =============================================================================

def download_fx_data(yahoo_ticker, label, start_date, end_date, retry_count=3):
    """Download daily FX data and normalize to OHLCV format."""
    for attempt in range(retry_count):
        try:
            stock = yf.Ticker(yahoo_ticker)
            df = stock.history(start=start_date, end=end_date, interval='1d', auto_adjust=False)

            if df.empty:
                return None

            df = df.reset_index()
            df['Ticker'] = label

            # Strip timezone
            if df['Date'].dt.tz is not None:
                df['Date'] = df['Date'].dt.tz_localize(None)

            # Some FX rows can have NaN — drop them
            df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])

            df = df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

            # Round to 4 decimals (FX rates are typically quoted to 2-4 decimals;
            # SP500 uses 2 but JPY swings tighter so 4 keeps signal)
            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = df[col].round(4)

            # Volume on FX is usually 0 or NaN — cast to int safely
            df['Volume'] = df['Volume'].fillna(0).astype(int)

            return df

        except Exception as e:
            print(f'  ⚠️ Attempt {attempt+1} failed for {yahoo_ticker}: {e}')
            if attempt == retry_count - 1:
                return None
            time.sleep(2)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    print('=' * 60)
    print('💴 USDJPY Daily Updater — JP Trust Learning')
    print(f'📌 Ticker: {TICKER_YAHOO} (stored as "{TICKER_LABEL}")')
    print('=' * 60)

    os.makedirs(LOG_FOLDER, exist_ok=True)

    # Read existing data (if any) to determine fetch window
    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        df_existing['Date'] = pd.to_datetime(df_existing['Date'])
        if len(df_existing) > 0 and pd.notna(df_existing['Date'].max()):
            last_date = df_existing['Date'].max()
            start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f'📂 Existing: {len(df_existing):,} rows')
            print(f'📅 Last date: {last_date.date()} → incremental update')
        else:
            start_date = FALLBACK_START
            print(f'📂 Existing file is empty — initial backfill from {FALLBACK_START}')
    else:
        df_existing = pd.DataFrame(columns=['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        start_date = FALLBACK_START
        print(f'📂 No existing file — initial backfill from {FALLBACK_START}')

    end_date = datetime.now().strftime('%Y-%m-%d')
    print(f'\n🔄 Fetching {TICKER_YAHOO}: {start_date} → {end_date}')

    df_new = download_fx_data(TICKER_YAHOO, TICKER_LABEL, start_date, end_date)

    if df_new is None or df_new.empty:
        print('\nℹ️  No new data available (market closed / holiday / already up to date)')
        print('\n' + '=' * 60)
        print('🎉 DONE (no changes)')
        print('=' * 60)
        exit(0)

    print(f'\n📊 Downloaded {len(df_new):,} new rows')
    print(f'   Range: {df_new["Date"].min().date()} → {df_new["Date"].max().date()}')

    # Merge with existing — keep latest per (Ticker, Date)
    df_all = pd.concat([df_existing, df_new], ignore_index=True)
    df_all['Date'] = pd.to_datetime(df_all['Date'])
    df_all = df_all.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
    df_all = df_all.sort_values(['Ticker', 'Date']).reset_index(drop=True)

    # Output
    df_out = df_all.copy()
    df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')

    df_out.to_csv(CSV_FILE, index=False)
    size_kb = os.path.getsize(CSV_FILE) / 1024
    print(f'\n💾 Saved: {CSV_FILE} ({size_kb:.1f} KB)')

    # Timestamped backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    log_filename = f'input_jpy_daily_{timestamp}.csv'
    log_path = os.path.join(LOG_FOLDER, log_filename)
    df_out.to_csv(log_path, index=False)
    print(f'💾 Saved: {LOG_FOLDER}/{log_filename}')

    print(f'\n📊 Total: {len(df_all):,} rows')
    print(f'📅 Range: {df_all["Date"].min().date()} → {df_all["Date"].max().date()}')

    print('\n' + '=' * 60)
    print('🎉 DONE!')
    print('=' * 60)
