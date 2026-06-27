#!/usr/bin/env python3
"""
S&P 500 Historical Backfill — ONE-TIME SCRIPT (HIST 1996)
JP Trust Learning

Downloads historical data from 1996-01-01 to 2000-12-31 for current S&P 500
constituents and writes it to input_sp500_daily_since1996.csv (REPLACES file).

WHY A SEPARATE FILE (1996-2000 only):
  - input_sp500_daily_since2001.csv  → 2001-2014
  - input_sp500_daily.csv (production) → 2015+
  This new file holds ONLY 1996-2000 so it does NOT overlap since2001, and so
  each file stays well under GitHub's 100 MB limit. The lab HTML fetches all
  three and concatenates them in-browser.

  Date ranges are disjoint:  [1996-2000] + [2001-2014] + [2015-now]

⚠️ SURVIVORSHIP BIAS — EVEN WORSE THAN 2001:
  Universe = the CURRENT S&P 500 list (Wikipedia). For 1996-2000 this is far
  more biased than 2001-2014 because:
    1. A large share of today's constituents had not yet IPO'd in 1996 — they
       simply have no rows and are dropped (expect a BIG "empty" list).
    2. Every dot-com casualty that was delisted (Pets.com, Webvan, eToys, and
       the many that went to zero) is absent — so a "did it survive dot-com?"
       test will look ROSIER than reality, because the losers were removed from
       the index before they could hurt the backtest.
  Treat results as directional stress-testing only, NOT absolute return claims.

⚠️ MACRO OVERLAY NOTE (read before interpreting the defensive lab):
  The macro regime filter needs WTI (Yahoo CL=F) + GOLD (Yahoo GC=F), both of
  which begin ~2000 on Yahoo, and USDJPY (JPY=X) ~1996. So for 1996-2000 the
  overlay will mostly be inert (no WTI/GOLD Delta-6M => regime null => benign).
  This file unblocks the BASE strategy back to 1996; it does NOT make the
  defensive overlay active pre-2001.

Run once via GitHub Actions workflow_dispatch.
Target file: input_sp500_daily_since1996.csv (REPLACES existing file)
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
CSV_FILE = 'input_sp500_daily_since1996.csv'
LOG_FOLDER = 'logs'
BACKFILL_START = '1996-01-01'
BACKFILL_END = '2000-12-31'   # disjoint from since2001 (which starts 2001-01-01)

# =============================================================================
# FUNCTIONS
# =============================================================================

def get_sp500_tickers():
    """Fetch current S&P 500 tickers from Wikipedia.

    WARNING: this is the *current* list — heavily survivorship-biased for the
    late-1990s. Many tickers below had not IPO'd by 1996.
    """
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
        print(f'WARNING: Wikipedia fetch failed: {e}')
        return []


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
            if attempt == retry_count - 1:
                return None
            time.sleep(2)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    print('=' * 60)
    print('S&P 500 Historical Backfill — HIST 1996 (ONE-TIME)')
    print(f'Period: {BACKFILL_START} -> {BACKFILL_END}')
    print(f'Target: {CSV_FILE} (will OVERWRITE existing file)')
    print('Stores ONLY 1996-2000 (disjoint from since2001 = 2001-2014).')
    print('SURVIVORSHIP-BIASED: only current SP500 constituents.')
    print('=' * 60)

    # Get tickers
    tickers = get_sp500_tickers()
    if not tickers:
        print('ERROR: Failed to get ticker list')
        exit(1)
    print(f'Found {len(tickers)} tickers (current S&P 500)')

    # Download historical data — no merge with existing (overwrite)
    all_data = []
    success_count = 0
    failed_tickers = []
    empty_tickers = []

    print(f'\nDownloading {len(tickers)} tickers ({BACKFILL_START} -> {BACKFILL_END})...')
    print('-' * 60)

    for i, ticker in enumerate(tickers, 1):
        df = download_stock_data(ticker, BACKFILL_START, BACKFILL_END)

        if df is not None and not df.empty:
            all_data.append(df)
            success_count += 1
        elif df is None:
            failed_tickers.append(ticker)
        else:
            empty_tickers.append(ticker)

        if i % 25 == 0 or i == len(tickers):
            pct = (i / len(tickers)) * 100
            print(f'[{i:3d}/{len(tickers)}] {pct:5.1f}% | OK: {success_count} | Fail: {len(failed_tickers)} | Empty: {len(empty_tickers)}')

        if i % 5 == 0:
            time.sleep(0.5)

    print('-' * 60)

    if not all_data:
        print('ERROR: No historical data downloaded')
        exit(1)

    df_historical = pd.concat(all_data, ignore_index=True)
    df_historical['Date'] = pd.to_datetime(df_historical['Date'])

    # Belt-and-suspenders: clip strictly to BACKFILL_END (no overlap with since2001)
    end_dt = pd.Timestamp(BACKFILL_END)
    df_historical = df_historical[df_historical['Date'] <= end_dt]

    df_historical = df_historical.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
    df_historical = df_historical.sort_values(['Ticker', 'Date']).reset_index(drop=True)

    print(f'\nDownloaded {len(df_historical):,} rows from {success_count} tickers (1996-2000 only)')

    # Save — OVERWRITE the file (no merge)
    df_out = df_historical.copy()
    df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')

    df_out.to_csv(CSV_FILE, index=False)

    # Report file size
    size_mb = os.path.getsize(CSV_FILE) / (1024 * 1024)
    print(f'\nSaved: {CSV_FILE} ({size_mb:.1f} MB)')
    if size_mb > 95:
        print(f'WARNING: file is {size_mb:.1f} MB — approaching GitHub 100MB limit')

    # Log file (timestamped backup)
    os.makedirs(LOG_FOLDER, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    log_filename = f'input_sp500_daily_since1996_backfill_{timestamp}.csv'
    log_path = os.path.join(LOG_FOLDER, log_filename)
    df_out.to_csv(log_path, index=False)
    print(f'Saved: {LOG_FOLDER}/{log_filename}')

    total_tickers = df_historical['Ticker'].nunique()
    print(f'\nTotal: {len(df_historical):,} rows | {total_tickers} tickers')
    print(f'Range: {df_historical["Date"].min().date()} -> {df_historical["Date"].max().date()}')

    # How many current constituents actually traded each year (sanity on universe size)
    print('\nDistinct tickers with data per year (universe thinning check):')
    yr = df_historical.copy()
    yr['Year'] = yr['Date'].dt.year
    for y, n in yr.groupby('Year')['Ticker'].nunique().items():
        print(f'  {y}: {n} tickers')

    if failed_tickers:
        print(f'\nNetwork/fetch failures ({len(failed_tickers)}): {", ".join(failed_tickers[:30])}')
    if empty_tickers:
        print(f'\nNo data in 1996-2000 ({len(empty_tickers)}, likely IPO post-2000): {", ".join(empty_tickers[:40])}')

    print('\n' + '=' * 60)
    print('BACKFILL DONE!')
    print('Reminder: dataset is survivorship-biased (worse than 2001) — see header.')
    print('Macro overlay stays inert pre-2001 (no WTI/GOLD on Yahoo before ~2000).')
    print('Next: wire the lab HTML to fetch this file (cloudCsvUrlHist1996).')
    print('=' * 60)
