#!/usr/bin/env python3
"""
MACRO BACKFILL 1995-2000 (WTI / GOLD / USDJPY) — ONE-TIME (mirror-sourced)
JP Trust Learning

Extends the macro-regime inputs back to 1995 so the hist1996 lab's defensive
overlay can apply from ~mid-1996 instead of Aug-2001.

NOTE ON SOURCE: live FRED (fred.stlouisfed.org) blocks/times-out GitHub Actions
runner IPs, so this reads the same FRED series from GitHub raw mirrors (which the
runner can always reach). The underlying numbers are identical public FRED data:
  WTI    DCOILWTICO        <- ReDI-School/python-data-science
  GOLD   GOLDAMGBD228NLBM  <- robintux/Datasets4StackOverFlowQuestions (LBMA AM)
  USDJPY DEXJPUS           <- goodaccoustics/foreignexchange

Additive only — appends 1995-2000 rows disjoint from 2001+ Yahoo data,
splice-rescaled to the Yahoo basis at the 2001 seam. Close-only (O=H=L=C, V=0)
because the macro filter reads Close only. Idempotent (dedupe keep-last).
"""
import urllib.request
import pandas as pd

START, END, SEAM = '1995-01-01', '2000-12-31', '2001-01-01'

JOBS = [
    ('WTI',
     'https://raw.githubusercontent.com/ReDI-School/python-data-science/master/redi/ss_18/week10/DCOILWTICO.csv',
     'input_commodities_daily.csv', 2),
    ('GOLD',
     'https://raw.githubusercontent.com/robintux/Datasets4StackOverFlowQuestions/master/GOLDAMGBD228NLBM_1969-2020.csv',
     'input_commodities_daily.csv', 2),
    ('USDJPY',
     'https://raw.githubusercontent.com/goodaccoustics/foreignexchange/master/Data/DEXJPUS_19710104_20180504.csv',
     'input_jpy_daily.csv', 4),
]


def load_mirror(url):
    txt = urllib.request.urlopen(url, timeout=60).read().decode('utf-8', 'ignore')
    out = []
    for line in txt.splitlines():
        parts = line.split(',')
        if len(parts) < 2 or not parts[0][:1].isdigit():
            continue
        try:
            v = float(parts[1])
        except ValueError:
            continue
        if START <= parts[0] <= END:
            out.append((parts[0], v))
    out.sort()
    return out


if __name__ == '__main__':
    by_file = {}
    for label, url, csvfile, ndp in JOBS:
        fred = load_mirror(url)
        if len(fred) < 100:
            print(f'ERROR: {label} mirror returned {len(fred)} rows'); raise SystemExit(1)
        df = pd.read_csv(csvfile)
        sub = df[(df['Ticker'] == label) & (df['Date'] >= SEAM)].sort_values('Date')
        if sub.empty:
            print(f'ERROR: no existing {label} >= {SEAM}'); raise SystemExit(1)
        yahoo_first = float(sub.iloc[0]['Close'])
        scale = yahoo_first / fred[-1][1]
        if not (0.2 < scale < 5):
            print(f'ERROR: {label} scale {scale:.3f} insane'); raise SystemExit(1)
        rows = [{'Ticker': label, 'Date': d, 'Open': round(v*scale, ndp), 'High': round(v*scale, ndp),
                 'Low': round(v*scale, ndp), 'Close': round(v*scale, ndp), 'Volume': 0} for d, v in fred]
        print(f'{label}: +{len(rows)} rows {fred[0][0]}..{fred[-1][0]}  scale x{scale:.4f}')
        by_file.setdefault(csvfile, []).extend(rows)

    for csvfile, rows in by_file.items():
        df = pd.read_csv(csvfile)
        before = len(df)
        allr = pd.concat([df, pd.DataFrame(rows)[['Ticker','Date','Open','High','Low','Close','Volume']]],
                         ignore_index=True)
        allr['Volume'] = allr['Volume'].fillna(0).astype('int64')
        allr = allr.drop_duplicates(subset=['Ticker','Date'], keep='last').sort_values(['Ticker','Date']).reset_index(drop=True)
        allr.to_csv(csvfile, index=False)
        print(f'{csvfile}: {before} -> {len(allr)} (+{len(allr)-before})')
    print('DONE')
