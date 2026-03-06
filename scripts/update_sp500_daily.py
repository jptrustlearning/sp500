#!/usr/bin/env python3
"""
S&P 500 Daily Price Updater — GitHub Actions Version
JP Trust Learning

Replicates the Colab notebook logic:
1. Fetch S&P 500 ticker list from Wikipedia
2. Read existing input_sp500_daily.csv
3. Download new price data from Yahoo Finance
4. Merge + deduplicate + save 2 files:
   - input_sp500_daily.csv (overwrite)
   - logs/input_sp500_daily_YYYYMMDD_HHMM.csv (backup)
"""

import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import time
from datetime import datetime, timedelta

# =============================================================================
# CONFIG
# =============================================================================
CSV_FILE = 'input_sp500_daily.csv'
LOG_FOLDER = 'logs'
FALLBACK_START = '2022-01-01'

# =============================================================================
# Step 1: Get S&P 500 tickers
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
        print('Using backup ticker list...')
        return get_backup_tickers()


def get_backup_tickers():
    """Backup list of major S&P 500 tickers"""
    return [
        'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'GOOG', 'META', 'TSLA', 'AVGO', 'ORCL', 'ADBE',
        'CRM', 'CSCO', 'ACN', 'INTC', 'IBM', 'QCOM', 'TXN', 'AMD', 'NOW', 'INTU',
        'AMAT', 'MU', 'LRCX', 'KLAC', 'SNPS', 'CDNS', 'ADI', 'MRVL', 'PANW', 'ADSK',
        'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'PFE', 'TMO', 'ABT', 'DHR', 'CVS',
        'BMY', 'AMGN', 'GILD', 'MDT', 'ELV', 'CI', 'ISRG', 'VRTX', 'REGN', 'SYK',
        'BRK.B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'SPGI', 'BLK', 'C',
        'SCHW', 'MS', 'AXP', 'CB', 'PNC', 'USB', 'TFC', 'CME', 'ICE', 'AON',
        'AMZN', 'HD', 'NKE', 'MCD', 'LOW', 'SBUX', 'TJX', 'BKNG', 'CMG', 'ORLY',
        'WMT', 'PG', 'KO', 'PEP', 'COST', 'PM', 'MDLZ', 'MO', 'CL', 'STZ',
        'UNP', 'CAT', 'BA', 'HON', 'RTX', 'LMT', 'DE', 'UPS', 'GE', 'ETN',
        'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'MPC', 'VLO', 'PSX', 'OXY', 'WMB',
        'NEE', 'SO', 'DUK', 'SRE', 'AEP', 'EXC', 'XEL', 'ED', 'D', 'PEG',
        'PLD', 'AMT', 'CCI', 'EQIX', 'PSA', 'WELL', 'SPG', 'VICI', 'O', 'DLR',
        'LIN', 'APD', 'SHW', 'ECL', 'DD', 'NEM', 'FCX', 'CTVA', 'DOW', 'PPG',
        'DIS', 'CMCSA', 'NFLX', 'T', 'VZ', 'TMUS', 'CHTR', 'EA', 'TTWO', 'OMC',
    ]


# =============================================================================
# Step 2: Download stock data
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
            if attempt == retry_count - 1:
                print(f'  ❌ {ticker}: {e}')
                return None
            time.sleep(2)


# =============================================================================
# MAIN
# =============================================================================
def main():
    print('=' * 60)
    print('📈 S&P 500 Daily Price Updater — GitHub Actions')
    print('=' * 60)

    # Get tickers
    tickers = get_sp500_tickers()
    print(f'\n📋 Found {len(tickers)} S&P 500 tickers')

    # Create logs folder
    os.makedirs(LOG_FOLDER, exist_ok=True)

    # Read existing data
    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        df_existing['Date'] = pd.to_datetime(df_existing['Date'])
        last_date = df_existing['Date'].max()
        start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
        print(f'📂 Existing: {len(df_existing):,} rows, {df_existing["Ticker"].nunique()} tickers')
        print(f'📅 Last date: {last_date.date()}')
    else:
        df_existing = pd.DataFrame(columns=['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        start_date = FALLBACK_START
        print(f'📂 No existing file — starting from {FALLBACK_START}')

    end_date = datetime.now().strftime('%Y-%m-%d')
    print(f'\n🔄 Fetching: {start_date} → {end_date}')

    # Check if there's anything to fetch
    if start_date >= end_date:
        print('\n✅ Already up to date — nothing to fetch')
        return

    # Download
    all_new_data = []
    success_count = 0
    failed_tickers = []

    print(f'\n📥 Downloading {len(tickers)} tickers...')
    print('-' * 50)

    for i, ticker in enumerate(tickers, 1):
        df = download_stock_data(ticker, start_date, end_date)

        if df is not None and not df.empty:
            all_new_data.append(df)
            success_count += 1
        else:
            failed_tickers.append(ticker)

        # Progress
        if i % 50 == 0 or i == len(tickers):
            pct = (i / len(tickers)) * 100
            print(f'[{i:3d}/{len(tickers)}] {pct:5.1f}% | Success: {success_count} | Failed: {len(failed_tickers)}')

        # Rate limiting
        if i % 5 == 0:
            time.sleep(0.5)

    print('-' * 50)

    if not all_new_data:
        print('\nℹ️  No new data available (market closed / holiday / already up to date)')
        return

    # Merge
    df_new = pd.concat(all_new_data, ignore_index=True)
    new_count = len(df_new)
    print(f'\n📊 Downloaded {new_count:,} new rows from {success_count} tickers')

    df_all = pd.concat([df_existing, df_new], ignore_index=True)
    df_all['Date'] = pd.to_datetime(df_all['Date'])
    df_all = df_all.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
    df_all = df_all.sort_values(['Ticker', 'Date']).reset_index(drop=True)

    # Prepare output
    df_out = df_all.copy()
    df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')

    # File 1: Main file (overwrite)
    df_out.to_csv(CSV_FILE, index=False)
    print(f'\n💾 Saved: {CSV_FILE}')

    # File 2: Log file (timestamped backup)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M')
    log_filename = f'input_sp500_daily_{timestamp}.csv'
    log_path = os.path.join(LOG_FOLDER, log_filename)
    df_out.to_csv(log_path, index=False)
    print(f'💾 Saved: {LOG_FOLDER}/{log_filename}')

    total_tickers = df_all['Ticker'].nunique()
    print(f'\n📊 Total: {len(df_all):,} rows | {total_tickers} tickers')
    print(f'📅 Range: {df_all["Date"].min().date()} → {df_all["Date"].max().date()}')

    # Failed tickers report
    if failed_tickers:
        print(f'\n⚠️ Failed ({len(failed_tickers)}): {", ".join(failed_tickers[:20])}')
        if len(failed_tickers) > 20:
            print(f'   ... and {len(failed_tickers) - 20} more')

    print('\n' + '=' * 60)
    print('🎉 DONE!')
    print('=' * 60)


if __name__ == '__main__':
    main()
