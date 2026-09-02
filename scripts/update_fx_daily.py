#!/usr/bin/env python3
"""
FX Daily Price Updater (EURUSD / GBPUSD / AUDUSD / USDCAD + DXY) — GitHub Actions
JP Trust Learning · B16 (Sep 2026)

Same flow as scripts/update_jpy_daily.py, generalised to several tickers in one
file (Ticker column), plus hardening learned from auditing the USDJPY file:

  * Yahoo FX "daily" bars are NOT New-York-close bars. Empirically (checked
    against MT5 broker H1 for USDJPY + EURUSD, 2015→2026):
      - Close on row D  ≈ price at 00:00 UTC of D   (= 07:00 Bangkok, D)
      - High/Low of row D ≈ range of [00:00 UTC D-1 → 00:00 UTC D]
      - Open on row D ≈ Close of the same row (96% within 0.05 JPY) — it is a
        snapshot, NOT the session open.  Do not use Open; use previous Close.
    This is fine for the percentile grid (levels move 4–12 pips vs NY close,
    the monthly-frozen grid tolerates ~250 pips of DXY drift) but do not
    expect the file to match a broker's D1 chart by eye — the date is shifted.
  * Yahoo occasionally emits Saturday/Sunday rows and bad prints
    (USDJPY 2015→: 37 rows >0.3% off, max ~1%).  We drop weekend rows and
    flag |day-over-day| > 3% in the log (kept, not dropped — Brexit-type days
    are real).
  * Yahoo sometimes corrects a bar days later.  The JPY script only fetches
    last_date+1 → never sees corrections.  Here we re-fetch a trailing
    REFETCH_DAYS window every run and keep the latest values (keep='last').
  * No per-run copies in logs/ — git history of the CSV is the backup
    (the gold/btc repos accumulated 1,500 zero-byte files that way).

Yahoo symbols → stored Ticker label:
  EURUSD=X → EURUSD    GBPUSD=X → GBPUSD    AUDUSD=X → AUDUSD
  CAD=X    → USDCAD    DX-Y.NYB → DXY (ICE US Dollar Index, cash)
(USDJPY stays in input_jpy_daily.csv — not duplicated here.)

Output: input_fx_daily.csv — Ticker, Date, Open, High, Low, Close, Volume
        (same schema as input_jpy_daily.csv / input_benchmark_daily.csv)
"""

import os
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

# =============================================================================
# CONFIG
# =============================================================================
CSV_FILE = 'input_fx_daily.csv'
FALLBACK_START = '2003-01-01'   # Yahoo FX pairs start ~2003-12; DXY earlier
REFETCH_DAYS = 10               # re-download this many trailing days each run
FLAG_PCT = 3.0                  # warn if |Close/prevClose - 1| > this (%)

# yahoo_symbol -> (label, decimals)
TICKERS = {
    'EURUSD=X': ('EURUSD', 5),
    'GBPUSD=X': ('GBPUSD', 5),
    'AUDUSD=X': ('AUDUSD', 5),
    'CAD=X':    ('USDCAD', 5),
    'DX-Y.NYB': ('DXY',    3),
}
COLS = ['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']


# =============================================================================
# FUNCTIONS
# =============================================================================

def download_fx(yahoo_symbol, label, decimals, start_date, end_date, retry_count=3):
    """Download daily bars for one symbol and normalise to our schema."""
    for attempt in range(retry_count):
        try:
            df = yf.Ticker(yahoo_symbol).history(
                start=start_date, end=end_date, interval='1d', auto_adjust=False)
            if df is None or df.empty:
                return None
            df = df.reset_index()
            if 'Date' not in df.columns:            # yfinance sometimes names it Datetime
                df = df.rename(columns={df.columns[0]: 'Date'})
            df['Date'] = pd.to_datetime(df['Date'])
            if getattr(df['Date'].dt, 'tz', None) is not None:
                df['Date'] = df['Date'].dt.tz_localize(None)
            df['Date'] = df['Date'].dt.normalize()
            df['Ticker'] = label
            df = df.dropna(subset=['High', 'Low', 'Close'])
            df['Open'] = df['Open'].fillna(df['Close'])
            for c in ['Open', 'High', 'Low', 'Close']:
                df[c] = df[c].astype(float).round(decimals)
            df['Volume'] = pd.to_numeric(df.get('Volume', 0), errors='coerce').fillna(0).astype('int64')
            return df[COLS]
        except Exception as e:  # noqa: BLE001
            print(f'  ⚠️ Attempt {attempt + 1} failed for {yahoo_symbol}: {e}')
            if attempt == retry_count - 1:
                return None
            time.sleep(2)
    return None


def validate(df_all):
    """Drop weekend rows / impossible bars, flag big jumps. Returns (df, n_dropped)."""
    n0 = len(df_all)
    wk = df_all['Date'].dt.weekday
    weekend = wk >= 5
    if weekend.any():
        for _, r in df_all[weekend].iterrows():
            print(f'  🗑️ drop weekend row {r.Ticker} {r.Date.date()} close {r.Close}')
    df_all = df_all[~weekend]
    bad_bar = (df_all['High'] < df_all['Low']) | (df_all['Close'] <= 0)
    if bad_bar.any():
        for _, r in df_all[bad_bar].iterrows():
            print(f'  🗑️ drop impossible bar {r.Ticker} {r.Date.date()} H{r.High} L{r.Low} C{r.Close}')
    df_all = df_all[~bad_bar]
    return df_all.copy(), n0 - len(df_all)


def flag_jumps(df_all, only_after=None):
    """Print rows whose day-over-day close move exceeds FLAG_PCT (kept in data)."""
    flagged = 0
    for label, g in df_all.groupby('Ticker'):
        g = g.sort_values('Date')
        pct = (g['Close'] / g['Close'].shift(1) - 1).abs() * 100
        m = pct > FLAG_PCT
        if only_after is not None:
            m &= g['Date'] >= only_after
        for d, p, c in zip(g.loc[m, 'Date'], pct[m], g.loc[m, 'Close']):
            print(f'  🚩 {label} {d.date()} moved {p:.2f}% (close {c}) — check vs broker; kept')
            flagged += 1
    return flagged


# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    print('=' * 60)
    print('💱 FX Daily Updater — JP Trust Learning')
    print(f'📌 {", ".join(f"{k}→{v[0]}" for k, v in TICKERS.items())}')
    print('=' * 60)

    if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
        df_existing = pd.read_csv(CSV_FILE)
        df_existing['Date'] = pd.to_datetime(df_existing['Date'])
        print(f'📂 Existing: {len(df_existing):,} rows · '
              f'{df_existing["Date"].min().date()} → {df_existing["Date"].max().date()}')
    else:
        df_existing = pd.DataFrame(columns=COLS)
        df_existing['Date'] = pd.to_datetime(df_existing['Date'])
        print('📂 No existing file — initial backfill')

    # Yahoo's `end` is exclusive → end=today returns rows up to the bar labelled
    # yesterday (same as the JPY pipeline).  A bar's values can still be revised
    # by Yahoo for a few days, hence the trailing re-fetch below.
    end_date = datetime.now().strftime('%Y-%m-%d')

    frames = []
    for yahoo_symbol, (label, decimals) in TICKERS.items():
        prev = df_existing[df_existing['Ticker'] == label]
        if len(prev):
            last = prev['Date'].max()
            start_date = (last - timedelta(days=REFETCH_DAYS)).strftime('%Y-%m-%d')
            mode = f'incremental (last {last.date()}, re-fetch {REFETCH_DAYS}d)'
        else:
            start_date = FALLBACK_START
            mode = f'backfill from {FALLBACK_START}'
        print(f'\n🔄 {label:6} ({yahoo_symbol}): {start_date} → {end_date} · {mode}')
        df_new = download_fx(yahoo_symbol, label, decimals, start_date, end_date)
        if df_new is None or df_new.empty:
            print('   ℹ️ no rows returned')
            continue
        print(f'   📊 {len(df_new):,} rows · {df_new["Date"].min().date()} → {df_new["Date"].max().date()}')
        frames.append(df_new)

    if not frames:
        print('\nℹ️  Nothing downloaded (holiday / Yahoo down) — no changes')
        sys.exit(0)

    df_all = pd.concat([df_existing] + frames, ignore_index=True)
    df_all['Date'] = pd.to_datetime(df_all['Date'])
    # keep='last' → freshly downloaded values win over stored ones (absorbs Yahoo revisions)
    df_all = df_all.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
    df_all, dropped = validate(df_all)
    df_all = df_all.sort_values(['Ticker', 'Date']).reset_index(drop=True)

    cutoff = df_all['Date'].max() - timedelta(days=REFETCH_DAYS + 5)
    print('\n🔍 validation')
    n_flag = flag_jumps(df_all, only_after=cutoff)
    print(f'   dropped {dropped} rows · flagged {n_flag} jumps >{FLAG_PCT}% in the recent window')

    # Diff vs existing (informational)
    if len(df_existing):
        old = df_existing.set_index(['Ticker', 'Date'])['Close']
        new = df_all.set_index(['Ticker', 'Date'])['Close']
        common = old.index.intersection(new.index)
        changed = (old.loc[common] != new.loc[common]).sum()
        added = len(new) - len(common)
        print(f'   {added} new rows · {changed} existing closes revised by Yahoo')

    df_out = df_all.copy()
    df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')
    df_out.to_csv(CSV_FILE, index=False)
    print(f'\n💾 Saved: {CSV_FILE} ({os.path.getsize(CSV_FILE) / 1024:.1f} KB)')

    for label, g in df_all.groupby('Ticker'):
        print(f'   {label:6} {len(g):5,} rows · {g["Date"].min().date()} → {g["Date"].max().date()} · last close {g["Close"].iloc[-1]}')

    print('\n' + '=' * 60)
    print('🎉 DONE!')
    print('=' * 60)
