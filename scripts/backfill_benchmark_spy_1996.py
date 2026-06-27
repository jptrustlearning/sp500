#!/usr/bin/env python3
"""
SPY Historical Backfill 1996-2000 — ONE-TIME SCRIPT
JP Trust Learning

Adds SPY daily data from 1996-01-01 to 2000-12-31 into the production benchmark
CSV (input_benchmark_daily.csv), extending SPY coverage back to 1996.

WHY THIS IS REQUIRED for the hist1996 lab:
  The lab filters its date axis to days where SPY exists:
      state.sortedDates = sortedDates.filter(d => marketData[d] && marketData[d]['SPY'])
  Without SPY for 1996-2000, EVERY 1996-2000 trading day is dropped, and the
  since1996 + delisted stock data becomes invisible. Loading SPY back to 1996
  makes the period exist. (Benchmark CSV is tiny — merge in place, no new file.)

SPY existed since Jan 1993, so 1996-2000 is fully available. No survivorship
issue (single ETF). QQQ (1999) / DIA (1998) are NOT backfilled — only SPY is
used by the date filter and benchmark line.

Run once via GitHub Actions workflow_dispatch.
"""

import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime

CSV_FILE = 'input_benchmark_daily.csv'
LOG_FOLDER = 'logs'
TICKER = 'SPY'
BACKFILL_START = '1996-01-01'
BACKFILL_END = '2000-12-31'   # disjoint from the 2001-2014 SPY backfill


def download_stock_data(ticker, start_date, end_date, retry_count=3):
    for attempt in range(retry_count):
        try:
            df = yf.Ticker(ticker).history(start=start_date, end=end_date,
                                           interval='1d', auto_adjust=True)
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


if __name__ == '__main__':
    print('=' * 60)
    print(f'{TICKER} Historical Backfill 1996-2000 — ONE-TIME')
    print(f'Period: {BACKFILL_START} -> {BACKFILL_END}')
    print(f'Target: {CSV_FILE} (MERGE with existing data)')
    print('=' * 60)

    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        df_existing['Date'] = pd.to_datetime(df_existing['Date'])
        print(f'Existing: {len(df_existing):,} rows '
              f'({df_existing["Date"].min().date()} -> {df_existing["Date"].max().date()})')
        print(f'  Tickers: {sorted(df_existing["Ticker"].unique().tolist())}')
    else:
        print(f'ERROR: {CSV_FILE} not found')
        exit(1)

    print(f'\nDownloading {TICKER} ({BACKFILL_START} -> {BACKFILL_END})...')
    df_spy = download_stock_data(TICKER, BACKFILL_START, BACKFILL_END)
    if df_spy is None or df_spy.empty:
        print(f'ERROR: No data downloaded for {TICKER}')
        exit(1)

    print(f'Downloaded {len(df_spy):,} rows  '
          f'({df_spy["Date"].min().date()} -> {df_spy["Date"].max().date()})')

    df_spy = df_spy[df_spy['Date'] <= pd.Timestamp(BACKFILL_END)]

    df_all = pd.concat([df_spy, df_existing], ignore_index=True)
    df_all['Date'] = pd.to_datetime(df_all['Date'])
    df_all = df_all.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
    df_all = df_all.sort_values(['Ticker', 'Date']).reset_index(drop=True)

    df_out = df_all.copy()
    df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')
    df_out.to_csv(CSV_FILE, index=False)
    size_kb = os.path.getsize(CSV_FILE) / 1024
    print(f'\nSaved: {CSV_FILE} ({size_kb:.1f} KB)')

    os.makedirs(LOG_FOLDER, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    df_out.to_csv(os.path.join(LOG_FOLDER, f'input_benchmark_daily_spy1996_backfill_{ts}.csv'), index=False)

    print(f'\nTotal: {len(df_all):,} rows')
    for t in sorted(df_all['Ticker'].unique().tolist()):
        sub = df_all[df_all['Ticker'] == t]
        print(f'  {t}: {len(sub):,} rows ({sub["Date"].min().date()} -> {sub["Date"].max().date()})')

    print('\n' + '=' * 60)
    print('SPY 1996 BACKFILL DONE — hist1996 lab date axis now reaches 1996.')
    print('=' * 60)
