#!/usr/bin/env python3
"""
S&P 500 SURVIVORSHIP REPAIR — delisted/removed constituents (1996-2010)
JP Trust Learning

Reads survivorship_targets.csv (ticker, removed_yyyymm) — companies that were
in the S&P 500 at some point during 1996-2010 but are NOT in the current index
(so the current-list backfills missed them). Downloads their 1996-2010 daily
data from Yahoo and writes input_sp500_delisted_hist.csv (REPLACES file).

Source of the target list: fja05680/sp500 historical components, diffed against
the current constituents list.

=========================== HONEST DATA-CEILING NOTE ==========================
Yahoo Finance routinely PURGES data for companies that went BANKRUPT (the most
important names for a crisis-survival test: Lehman, Enron, WorldCom, WaMu, ...).
Acquired companies (Compaq, Sun, Merrill, Countrywide, ...) usually retain data
up to the acquisition date. So expect PARTIAL recovery (~30-60%), skewed toward
acquired names, NOT bankruptcies. This script measures and logs the real rate.
A complete survivorship fix requires a paid point-in-time price source (CRSP,
Norgate, Sharadar). This recovers what is freely recoverable.
===============================================================================

Output columns: Ticker, Date, Open, High, Low, Close, Volume
Run once via GitHub Actions workflow_dispatch.
"""

import yfinance as yf
import pandas as pd
import os
import time
import csv
from datetime import datetime

# =============================================================================
# CONFIG
# =============================================================================
TARGETS_FILE = 'survivorship_targets.csv'
CSV_FILE = 'input_sp500_delisted_hist.csv'
LOG_FOLDER = 'logs'
FETCH_START = '1996-01-01'
FETCH_END = '2011-01-01'   # a hair past 2010 to capture full window

# A few well-known bankruptcy ticker aliases to try as a fallback (base often
# purged; the Q-suffixed pink-sheet symbol *sometimes* survives on Yahoo).
ALIASES = {
    'LEH': ['LEHMQ'], 'ENE': ['ENRNQ'], 'WCOM': ['WCOEQ', 'MCIP'],
    'WM': ['WAMUQ'], 'FNM': ['FNMA'], 'FRE': ['FMCC'], 'ABK': ['ABKFQ'],
    'CFC': ['CFC'], 'NCC': ['NCC'], 'GM': ['MTLQQ'],
}

# =============================================================================
def load_targets():
    targets = []
    with open(TARGETS_FILE, newline='') as f:
        for row in csv.DictReader(f):
            t = (row.get('ticker') or '').strip()
            if t:
                targets.append((t, (row.get('removed_yyyymm') or '').strip()))
    return targets


def download(ticker):
    """Return a cleaned DataFrame for one ticker, or None if no data."""
    try:
        df = yf.Ticker(ticker).history(start=FETCH_START, end=FETCH_END,
                                       interval='1d', auto_adjust=True)
        if df is None or df.empty:
            return None
        df = df.reset_index()
        if df['Date'].dt.tz is not None:
            df['Date'] = df['Date'].dt.tz_localize(None)
        df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        # clip to window
        df = df[df['Date'] <= pd.Timestamp(FETCH_END)]
        for c in ['Open', 'High', 'Low', 'Close']:
            df[c] = df[c].round(2)
        df['Volume'] = df['Volume'].fillna(0).astype('int64')
        return df if not df.empty else None
    except Exception:
        return None


def fetch_with_aliases(base):
    """Try the base ticker, then known aliases. Returns (df, used_symbol)."""
    df = download(base)
    if df is not None:
        return df, base
    for alt in ALIASES.get(base, []):
        df = download(alt)
        if df is not None:
            return df, alt
    return None, None


# =============================================================================
if __name__ == '__main__':
    print('=' * 64)
    print('S&P 500 SURVIVORSHIP REPAIR — delisted names 1996-2010 (ONE-TIME)')
    print(f'Window: {FETCH_START} -> {FETCH_END}')
    print(f'Target file: {CSV_FILE} (will OVERWRITE)')
    print('Yahoo purges most bankruptcies -> expect PARTIAL recovery. See header.')
    print('=' * 64)

    targets = load_targets()
    if not targets:
        print(f'ERROR: no targets loaded from {TARGETS_FILE}')
        exit(1)
    print(f'Loaded {len(targets)} delisted/removed target tickers\n')

    all_data = []
    recovered = []   # (ticker, used_symbol, n_rows, first, last)
    empty = []
    failed = []

    for i, (base, removed) in enumerate(targets, 1):
        df, used = fetch_with_aliases(base)
        if df is not None and not df.empty:
            df['Ticker'] = base   # store under the canonical (historical) base symbol
            df = df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            all_data.append(df)
            recovered.append((base, used, len(df),
                              df['Date'].min().date(), df['Date'].max().date()))
        else:
            empty.append(base)

        if i % 25 == 0 or i == len(targets):
            pct = i / len(targets) * 100
            print(f'[{i:3d}/{len(targets)}] {pct:5.1f}% | recovered: {len(recovered)} | empty: {len(empty)}')
        if i % 5 == 0:
            time.sleep(0.4)

    print('-' * 64)
    if not all_data:
        print('No delisted data could be recovered from Yahoo (0/%d).' % len(targets))
        print('This is possible if Yahoo has purged all targets. Nothing written.')
        exit(0)

    df_all = pd.concat(all_data, ignore_index=True)
    df_all['Date'] = pd.to_datetime(df_all['Date'])
    df_all = df_all.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
    df_all = df_all.sort_values(['Ticker', 'Date']).reset_index(drop=True)
    df_out = df_all.copy()
    df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')
    df_out.to_csv(CSV_FILE, index=False)

    size_mb = os.path.getsize(CSV_FILE) / (1024 * 1024)
    os.makedirs(LOG_FOLDER, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    df_out.to_csv(os.path.join(LOG_FOLDER, f'input_sp500_delisted_hist_{ts}.csv'), index=False)

    rate = len(recovered) / len(targets) * 100
    print(f'\nRECOVERED {len(recovered)}/{len(targets)} tickers ({rate:.1f}%)  '
          f'| {len(df_all):,} rows | {size_mb:.1f} MB')
    print(f'Range: {df_all["Date"].min().date()} -> {df_all["Date"].max().date()}')

    # how many recovered names actually have data in the dot-com / GFC windows
    dot = df_all[(df_all['Date'] >= '2000-01-01') & (df_all['Date'] <= '2002-12-31')]['Ticker'].nunique()
    gfc = df_all[(df_all['Date'] >= '2007-06-01') & (df_all['Date'] <= '2009-06-30')]['Ticker'].nunique()
    print(f'Names with data during dot-com 2000-2002: {dot}')
    print(f'Names with data during GFC 2007-2009    : {gfc}')

    print('\nSample recovered (first 30):')
    for base, used, n, f0, f1 in recovered[:30]:
        tag = '' if used == base else f' (via {used})'
        print(f'  {base:8s}{tag:14s} {n:5d} rows  {f0} -> {f1}')

    print(f'\nNOT recovered ({len(empty)}) — likely purged bankruptcies / bad symbols:')
    print('  ' + ', '.join(empty[:60]) + (' ...' if len(empty) > 60 else ''))

    print('\n' + '=' * 64)
    print('REPAIR DONE — input_sp500_delisted_hist.csv written.')
    print('Next: HTML appends this file (cloudCsvUrlDelisted) so the backtest')
    print('candidate universe includes these names for the dates they traded.')
    print('Reminder: bankruptcies are largely missing — bias reduced, not erased.')
    print('=' * 64)
