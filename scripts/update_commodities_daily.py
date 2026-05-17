#!/usr/bin/env python3
"""
Commodities & Macro-Proxy ETF Daily Price Updater — GitHub Actions Version
JP Trust Learning

Downloads daily price data for commodity futures and macro-proxy ETFs:
  - WTI crude oil    (Yahoo: CL=F → stored as 'WTI',  since 2001)
  - Gold             (Yahoo: GC=F → stored as 'GOLD', since 2001)
  - FXY              (Yahoo: FXY  → stored as 'FXY',  since 2007)
                     CurrencyShares Japanese Yen Trust — proxy for JPY strength
  - USL              (Yahoo: USL  → stored as 'USL',  since 2007)
                     United States 12-Month Oil Fund — 12M-spread WTI ETF
                     (less contango decay than USO)
  - USO              (Yahoo: USO  → stored as 'USO',  since 2006)
                     United States Oil Fund — front-month WTI ETF (most liquid)
  - GLD              (Yahoo: GLD  → stored as 'GLD',  since 2004)
                     SPDR Gold Shares — most-liquid gold ETF
  - SGOV             (Yahoo: SGOV → stored as 'SGOV', since May 2020)
                     iShares 0-3 Month Treasury Bond ETF — cash-equivalent
                     (modern, low expense ratio, very tight tracking)
  - BIL              (Yahoo: BIL  → stored as 'BIL',  since 2007)
                     SPDR 1-3 Month T-Bill ETF — cash-equivalent fallback
                     for the pre-2020 period when SGOV didn't exist

Auto-detects mode PER TICKER: initial backfill from 2001 (or each ticker's
inception date, whichever is later) if missing from CSV, else incremental
update from that ticker's last date + 1.

Output format matches input_benchmark_daily.csv:
  Ticker, Date, Open, High, Low, Close, Volume

Output Files:
  - input_commodities_daily.csv (overwrite)
  - logs/input_commodities_daily_YYYYMMDD_HHMM.csv (backup)
"""

import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime, timedelta

# =============================================================================
# CONFIG
# =============================================================================
CSV_FILE = 'input_commodities_daily.csv'
LOG_FOLDER = 'logs'
FALLBACK_START = '2001-01-01'

# (Yahoo ticker, CSV label)
TICKERS = [
    ('CL=F', 'WTI'),    # WTI crude oil front-month futures (since 2001)
    ('GC=F', 'GOLD'),   # Gold front-month futures (since 2001)
    ('FXY',  'FXY'),    # Invesco CurrencyShares Japanese Yen Trust ETF — proxy for JPY strength (since 2007)
    ('USL',  'USL'),    # United States 12-Month Oil Fund — 12M-spread WTI ETF, less contango decay than USO (since 2007)
    ('USO',  'USO'),    # United States Oil Fund — front-month WTI ETF, most-liquid oil ETF (since 2006)
    ('GLD',  'GLD'),    # SPDR Gold Shares — most-liquid gold ETF (since 2004)
    ('SGOV', 'SGOV'),   # iShares 0-3 Month Treasury Bond ETF — modern cash-equivalent (since May 2020)
    ('BIL',  'BIL'),    # SPDR 1-3 Month T-Bill ETF — cash-equivalent fallback for pre-2020 (since 2007)
]

# =============================================================================
# FUNCTIONS
# =============================================================================

def download_commodity_data(yahoo_ticker, label, start_date, end_date, retry_count=3):
    """Download daily commodity data and normalize to OHLCV format."""
    for attempt in range(retry_count):
        try:
            stock = yf.Ticker(yahoo_ticker)
            df = stock.history(start=start_date, end=end_date, interval='1d', auto_adjust=False)

            if df.empty:
                return None

            df = df.reset_index()
            df['Ticker'] = label

            if df['Date'].dt.tz is not None:
                df['Date'] = df['Date'].dt.tz_localize(None)

            df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
            df = df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = df[col].round(2)
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
    print('🛢️🥇💴 Commodities + Macro ETFs Daily Updater — JP Trust Learning')
    print(f'📌 Tickers: {", ".join([f"{y}→{l}" for y, l in TICKERS])}')
    print('=' * 60)

    os.makedirs(LOG_FOLDER, exist_ok=True)

    # Load existing
    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        df_existing['Date'] = pd.to_datetime(df_existing['Date'])
        print(f'📂 Existing: {len(df_existing):,} rows, tickers: {sorted(df_existing["Ticker"].unique().tolist())}')
    else:
        df_existing = pd.DataFrame(columns=['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        print(f'📂 No existing file — initial backfill from {FALLBACK_START}')

    end_date = datetime.now().strftime('%Y-%m-%d')

    # Fetch each ticker individually — each may have different last date
    all_new_data = []
    success_count = 0
    failed = []

    for yahoo_ticker, label in TICKERS:
        # Determine start date per ticker (allows late-added ticker to backfill while existing ones do incremental)
        if len(df_existing) > 0 and label in df_existing['Ticker'].unique():
            last_date = df_existing[df_existing['Ticker'] == label]['Date'].max()
            start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
            mode = f'incremental from {start_date}'
        else:
            start_date = FALLBACK_START
            mode = f'INITIAL backfill from {start_date}'

        print(f'\n📥 {label} ({yahoo_ticker}) — {mode} → {end_date}')

        # Skip if start_date is already past end_date (already up to date)
        if start_date > end_date:
            print(f'  ℹ️  Already up to date')
            success_count += 1
            continue

        df = download_commodity_data(yahoo_ticker, label, start_date, end_date)

        if df is not None and not df.empty:
            all_new_data.append(df)
            success_count += 1
            print(f'  ✅ {len(df):,} new rows ({df["Date"].min().date()} → {df["Date"].max().date()})')
        else:
            failed.append(label)
            print(f'  ❌ no data')

        time.sleep(0.5)

    if not all_new_data:
        print('\nℹ️  No new data — already up to date')
        if failed:
            print(f'⚠️ Failed: {", ".join(failed)}')
        print('\n' + '=' * 60)
        print('🎉 DONE (no changes)')
        print('=' * 60)
        exit(0)

    # Merge
    df_new = pd.concat(all_new_data, ignore_index=True)
    df_all = pd.concat([df_existing, df_new], ignore_index=True)
    df_all['Date'] = pd.to_datetime(df_all['Date'])
    df_all = df_all.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
    df_all = df_all.sort_values(['Ticker', 'Date']).reset_index(drop=True)

    df_out = df_all.copy()
    df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')

    df_out.to_csv(CSV_FILE, index=False)
    size_kb = os.path.getsize(CSV_FILE) / 1024
    print(f'\n💾 Saved: {CSV_FILE} ({size_kb:.1f} KB)')

    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    log_filename = f'input_commodities_daily_{timestamp}.csv'
    log_path = os.path.join(LOG_FOLDER, log_filename)
    df_out.to_csv(log_path, index=False)
    print(f'💾 Saved: {LOG_FOLDER}/{log_filename}')

    print(f'\n📊 Total: {len(df_all):,} rows')
    for t in sorted(df_all['Ticker'].unique()):
        sub = df_all[df_all['Ticker'] == t]
        print(f'   {t}: {len(sub):,} rows ({sub["Date"].min().date()} → {sub["Date"].max().date()})')

    if failed:
        print(f'\n⚠️ Failed: {", ".join(failed)}')

    print('\n' + '=' * 60)
    print('🎉 DONE!')
    print('=' * 60)
