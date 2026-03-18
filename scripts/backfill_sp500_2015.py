#!/usr/bin/env python3
"""
S&P 500 Historical Backfill — ONE-TIME SCRIPT
JP Trust Learning

Downloads historical data from 2015-01-01 to 2021-12-31
and merges with existing input_sp500_daily.csv (which starts from 2022).

Run once via GitHub Actions workflow_dispatch, then delete.
"""

import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import time
from datetime import datetime

# =============================================================================
# CONFIG
# =============================================================================
CSV_FILE = 'input_sp500_daily.csv'
LOG_FOLDER = 'logs'
BACKFILL_START = '2015-01-01'
BACKFILL_END = '2021-12-31'

# =============================================================================
# FUNCTIONS
# =============================================================================

def get_sp500_tickers():
    """Fetch current S&P 500 tickers from Wikipedia"""
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'constituents'})

        if not table:
            raise Exception('Table not found')

        tickers = []
        for row in table.find_all('tr')[1:]:
            cells = row.find_all('td')
            if len(cells) > 0:
                ticker = cells[0].text.strip()
                tickers.append(ticker)

        return sorted(tickers)
    except Exception as e:
        print(f'⚠️ Wikipedia fetch failed: {e}')
        return []


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
    print('📊 S&P 500 Historical Backfill — ONE-TIME')
    print(f'📅 Period: {BACKFILL_START} → {BACKFILL_END}')
    print('=' * 60)

    # Get tickers
    tickers = get_sp500_tickers()
    if not tickers:
        print('❌ Failed to get ticker list')
        exit(1)
    print(f'📋 Found {len(tickers)} tickers')

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

    print(f'\n📥 Downloading {len(tickers)} tickers ({BACKFILL_START} → {BACKFILL_END})...')
    print('-' * 50)

    for i, ticker in enumerate(tickers, 1):
        df = download_stock_data(ticker, BACKFILL_START, BACKFILL_END)

        if df is not None and not df.empty:
            all_data.append(df)
            success_count += 1
        else:
            failed_tickers.append(ticker)

        if i % 10 == 0 or i == len(tickers):
            pct = (i / len(tickers)) * 100
            print(f'[{i:3d}/{len(tickers)}] {pct:5.1f}% | Success: {success_count} | Failed: {len(failed_tickers)}')

        if i % 5 == 0:
            time.sleep(0.5)

    print('-' * 50)

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
    log_filename = f'input_sp500_daily_backfill_{timestamp}.csv'
    log_path = os.path.join(LOG_FOLDER, log_filename)
    df_out.to_csv(log_path, index=False)
    print(f'💾 Saved: {LOG_FOLDER}/{log_filename}')

    total_tickers = df_all['Ticker'].nunique()
    print(f'\n📊 Total: {len(df_all):,} rows | {total_tickers} tickers')
    print(f'📅 Range: {df_all["Date"].min().date()} → {df_all["Date"].max().date()}')

    if failed_tickers:
        print(f'\n⚠️ Failed ({len(failed_tickers)}): {", ".join(failed_tickers[:20])}')

    print('\n' + '=' * 60)
    print('🎉 BACKFILL DONE!')
    print('=' * 60)
