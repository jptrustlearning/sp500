#!/usr/bin/env python3
"""
MACRO BACKFILL 1995-2000 from FRED — ONE-TIME SCRIPT (NEW, additive)
JP Trust Learning

Extends the macro-regime inputs (WTI, GOLD, USDJPY) back to 1995 so the
hist1996 lab's defensive overlay can compute Delta-6M and APPLY from ~mid-1996
instead of Aug-2001. Yahoo's CL=F / GC=F futures don't exist before ~2000, so
the pre-2001 segment is sourced from FRED spot series (free, no API key):

    WTI    -> DCOILWTICO        (Cushing WTI spot, $/bbl, daily, 1986+)
    GOLD   -> GOLDAMGBD228NLBM  (LBMA Gold AM fixing, USD/oz; fallback PM)
    USDJPY -> DEXJPUS           (JPY per USD, daily, 1971+)

DOES NOT TOUCH any existing script or workflow. It only APPENDS 1995-2000 rows
(disjoint from the existing 2001+ Yahoo data) into the existing CSVs:
    input_commodities_daily.csv   (adds WTI, GOLD rows)
    input_jpy_daily.csv           (adds USDJPY rows)

SEAM HANDLING (important): FRED spot and Yahoo futures sit at slightly different
price LEVELS. A raw join would make the Delta-6M that straddles 2001-01 spurious.
So each FRED segment is RESCALED by (yahoo_first_close / fred_last_value) at the
seam -> the series joins continuously, and Delta-6M (a ratio) stays clean across
the boundary. The macro filter only reads Close, so O=H=L=C=value, Volume=0.

Run once via GitHub Actions workflow_dispatch.
"""

import urllib.request
import pandas as pd
import os
import time
from datetime import datetime

FRED_START = '1995-01-01'
FRED_END = '2000-12-31'           # disjoint from existing Yahoo data (2001-01-02+)
SEAM_AFTER = '2001-01-01'         # first existing Yahoo row used to compute scale

# (label, target_csv, [fred series id candidates], round_decimals)
JOBS = [
    ('WTI',    'input_commodities_daily.csv', ['DCOILWTICO'],                       2),
    ('GOLD',   'input_commodities_daily.csv', ['GOLDAMGBD228NLBM', 'GOLDPMGBD228NLBM'], 2),
    ('USDJPY', 'input_jpy_daily.csv',         ['DEXJPUS'],                          4),
]


def fetch_fred(series_id):
    url = (f'https://fred.stlouisfed.org/graph/fredgraph.csv'
           f'?id={series_id}&cosd={FRED_START}&coed={FRED_END}')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    for attempt in range(3):
        try:
            text = urllib.request.urlopen(req, timeout=60).read().decode('utf-8')
            break
        except Exception as e:
            print(f'    fetch retry {attempt+1}/3 failed: {e}')
            if attempt == 2:
                return []
            time.sleep(3)
    lines = text.strip().splitlines()
    out = []
    for line in lines[1:]:                      # skip header (DATE,<id> or observation_date,<id>)
        parts = line.split(',')
        if len(parts) < 2:
            continue
        d, v = parts[0].strip(), parts[1].strip()
        if v in ('.', '', 'NA', 'nan', 'NaN'):  # FRED missing-value marker
            continue
        try:
            out.append((d, float(v)))
        except ValueError:
            continue
    return out


def yahoo_first_close(csv_path, label):
    """Earliest existing (Yahoo) Close for `label` on/after the seam date."""
    df = pd.read_csv(csv_path)
    sub = df[(df['Ticker'] == label) & (df['Date'] >= SEAM_AFTER)].sort_values('Date')
    if sub.empty:
        return None, df
    return float(sub.iloc[0]['Close']), df


if __name__ == '__main__':
    print('=' * 64)
    print('MACRO FRED BACKFILL 1995-2000 (WTI / GOLD / USDJPY) — ONE-TIME')
    print(f'FRED window: {FRED_START} -> {FRED_END} | seam @ {SEAM_AFTER}')
    print('Additive only — existing 2001+ data untouched.')
    print('=' * 64)

    # group new rows by target CSV so each file is written once
    new_by_file = {}
    summary = []

    for label, csv_path, series_ids, ndp in JOBS:
        print(f'\n--- {label}  ({csv_path}) ---')
        if not os.path.exists(csv_path):
            print(f'  ERROR: {csv_path} not found'); raise SystemExit(1)

        # fetch FRED (with fallbacks)
        data, used = [], None
        for sid in series_ids:
            print(f'  fetching FRED {sid} ...')
            data = fetch_fred(sid)
            print(f'    got {len(data)} rows')
            if len(data) >= 100:
                used = sid; break

        if len(data) < 100:
            print(f'  ERROR: {label} returned too few rows ({len(data)}) — refusing to merge garbage')
            raise SystemExit(1)

        fred_first, fred_last = data[0], data[-1]
        # seam scale vs existing Yahoo
        yclose, df_existing = yahoo_first_close(csv_path, label)
        if yclose is None:
            print(f'  ERROR: no existing Yahoo {label} row >= {SEAM_AFTER} to anchor scale')
            raise SystemExit(1)
        scale = yclose / fred_last[1]
        print(f'  FRED range {fred_first[0]} -> {fred_last[0]} (used {used})')
        print(f'  seam: FRED last {fred_last[0]}={fred_last[1]:.4f}  Yahoo first {label}={yclose:.4f}'
              f'  -> scale x{scale:.5f}')

        rows = []
        for d, v in data:
            price = round(v * scale, ndp)
            rows.append({'Ticker': label, 'Date': d, 'Open': price, 'High': price,
                         'Low': price, 'Close': price, 'Volume': 0})
        new_by_file.setdefault(csv_path, []).extend(rows)
        summary.append((label, used, len(rows), fred_first[0], fred_last[0], scale))

    # merge + write each affected file once (append-only, dedupe keep-last)
    print('\n=== writing files ===')
    os.makedirs('logs', exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    for csv_path, rows in new_by_file.items():
        df_existing = pd.read_csv(csv_path)
        df_new = pd.DataFrame(rows)[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        before = len(df_existing)
        df_all = pd.concat([df_existing, df_new], ignore_index=True)
        df_all['Volume'] = df_all['Volume'].fillna(0).astype('int64')
        df_all = df_all.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
        df_all = df_all.sort_values(['Ticker', 'Date']).reset_index(drop=True)
        df_all.to_csv(csv_path, index=False)
        df_all.to_csv(os.path.join('logs', f'{os.path.basename(csv_path)[:-4]}_fred1996_{ts}.csv'), index=False)
        print(f'  {csv_path}: {before} -> {len(df_all)} rows (+{len(df_all)-before})')

    print('\n=== summary ===')
    for label, used, n, d0, d1, sc in summary:
        print(f'  {label:7s} +{n:4d} rows  {d0} -> {d1}  (FRED {used}, scale x{sc:.4f})')
    print('\nDONE — macro inputs now reach 1995; overlay can compute from ~mid-1996.')
    print('No HTML change needed (same Ticker labels WTI/GOLD/USDJPY).')
    print('=' * 64)
