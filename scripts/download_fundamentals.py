"""
SP500 Fundamental Data Downloader
=================================
ดึงข้อมูล fundamental ของหุ้น S&P 500 จาก yfinance
- Income Statement (Revenue, EPS, Net Income)
- Balance Sheet (Assets, Debt, Equity)
- Cash Flow (FCF, Operating CF)
- Key Ratios (P/E, P/B, ROE, Debt/Equity)

Output: CSV files in fundamentals/ folder
Schedule: Monthly (after earnings season)
Pipeline: แยกจาก daily OHLCV pipeline

Usage:
    python download_fundamentals.py
    python download_fundamentals.py --tickers AAPL,MSFT,NVDA
    python download_fundamentals.py --sp500-csv path/to/sp500_tickers.csv
"""

import yfinance as yf
import pandas as pd
import os
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json

# ============================================================
# CONFIG
# ============================================================
OUTPUT_DIR = Path("fundamentals")
LOG_DIR = Path("fundamentals/logs")
RATE_LIMIT_DELAY = 0.5  # seconds between API calls
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Fields to extract
INCOME_FIELDS = [
    "Total Revenue",
    "Net Income",
    "Gross Profit",
    "Operating Income",
    "EBITDA",
    "Basic EPS",
    "Diluted EPS",
    "Total Expenses",
    "Cost Of Revenue",
    "Research And Development",
]

BALANCE_FIELDS = [
    "Total Assets",
    "Total Liabilities Net Minority Interest",
    "Stockholders Equity",
    "Total Debt",
    "Cash And Cash Equivalents",
    "Net Debt",
    "Current Assets",
    "Current Liabilities",
    "Long Term Debt",
    "Working Capital",
]

CASHFLOW_FIELDS = [
    "Operating Cash Flow",
    "Free Cash Flow",
    "Capital Expenditure",
    "Investing Cash Flow",  # renamed from Investing Activities
    "Financing Cash Flow",  # renamed from Financing Activities
    "Repurchase Of Capital Stock",
    "Cash Dividends Paid",
    "Issuance Of Debt",
    "Repayment Of Debt",
]

RATIO_KEYS = {
    "trailingPE": "Trailing P/E",
    "forwardPE": "Forward P/E",
    "priceToBook": "P/B",
    "pegRatio": "PEG Ratio",
    "returnOnEquity": "ROE",
    "returnOnAssets": "ROA",
    "debtToEquity": "Debt/Equity",
    "currentRatio": "Current Ratio",
    "quickRatio": "Quick Ratio",
    "profitMargins": "Profit Margin",
    "operatingMargins": "Operating Margin",
    "grossMargins": "Gross Margin",
    "revenueGrowth": "Revenue Growth",
    "earningsGrowth": "Earnings Growth",
    "trailingEps": "Trailing EPS",
    "forwardEps": "Forward EPS",
    "marketCap": "Market Cap",
    "enterpriseValue": "Enterprise Value",
    "dividendYield": "Dividend Yield",
    "payoutRatio": "Payout Ratio",
    "beta": "Beta",
    "sector": "Sector",
    "industry": "Industry",
}

# ============================================================
# LOGGING
# ============================================================
def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"fundamentals_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)


# ============================================================
# TICKER LIST
# ============================================================
def get_sp500_tickers(csv_path=None):
    """Get S&P 500 ticker list. Uses Wikipedia as fallback."""
    if csv_path and os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        # Try common column names
        for col in ["Ticker", "ticker", "Symbol", "symbol"]:
            if col in df.columns:
                tickers = df[col].dropna().unique().tolist()
                logging.info(f"Loaded {len(tickers)} tickers from {csv_path}")
                return sorted(tickers)
        # If no matching column, use first column
        tickers = df.iloc[:, 0].dropna().unique().tolist()
        logging.info(f"Loaded {len(tickers)} tickers from {csv_path} (first column)")
        return sorted(tickers)

    # Fallback: download from Wikipedia
    try:
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )
        df = tables[0]
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        logging.info(f"Loaded {len(tickers)} tickers from Wikipedia")
        return sorted(tickers)
    except Exception as e:
        logging.error(f"Failed to get S&P 500 list: {e}")
        return []


# ============================================================
# DATA EXTRACTION
# ============================================================
def safe_extract(df, fields, ticker):
    """Extract specified fields from a yfinance DataFrame (income/balance/cashflow).
    Returns a dict of {field: {date: value}}."""
    if df is None or df.empty:
        return {}

    result = {}
    for field in fields:
        if field in df.index:
            row = df.loc[field]
            result[field] = {
                col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col): (
                    float(val) if pd.notna(val) else None
                )
                for col, val in row.items()
            }
    return result


def extract_ratios(info):
    """Extract key ratios from ticker.info dict."""
    result = {}
    for key, label in RATIO_KEYS.items():
        val = info.get(key)
        if val is not None:
            result[label] = val
    return result


def download_single_ticker(ticker_symbol, logger):
    """Download all fundamental data for a single ticker."""
    for attempt in range(MAX_RETRIES):
        try:
            t = yf.Ticker(ticker_symbol)

            # --- Annual financial statements ---
            income_annual = safe_extract(
                t.income_stmt, INCOME_FIELDS, ticker_symbol
            )
            balance_annual = safe_extract(
                t.balance_sheet, BALANCE_FIELDS, ticker_symbol
            )
            cashflow_annual = safe_extract(
                t.cashflow, CASHFLOW_FIELDS, ticker_symbol
            )

            # --- Quarterly financial statements ---
            income_quarterly = safe_extract(
                t.quarterly_income_stmt, INCOME_FIELDS, ticker_symbol
            )
            balance_quarterly = safe_extract(
                t.quarterly_balance_sheet, BALANCE_FIELDS, ticker_symbol
            )
            cashflow_quarterly = safe_extract(
                t.quarterly_cashflow, CASHFLOW_FIELDS, ticker_symbol
            )

            # --- Key ratios (current snapshot) ---
            try:
                info = t.info or {}
            except Exception:
                info = {}
            ratios = extract_ratios(info)

            return {
                "ticker": ticker_symbol,
                "annual": {
                    "income": income_annual,
                    "balance": balance_annual,
                    "cashflow": cashflow_annual,
                },
                "quarterly": {
                    "income": income_quarterly,
                    "balance": balance_quarterly,
                    "cashflow": cashflow_quarterly,
                },
                "ratios": ratios,
                "download_time": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.warning(
                f"  [{ticker_symbol}] Attempt {attempt+1}/{MAX_RETRIES} failed: {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    logger.error(f"  [{ticker_symbol}] All retries failed")
    return None


# ============================================================
# CSV BUILDERS
# ============================================================
def build_statement_csv(all_data, statement_type, period):
    """Build a long-format CSV from financial statement data.
    Columns: Ticker, Date, Metric, Value
    """
    rows = []
    for data in all_data:
        if data is None:
            continue
        ticker = data["ticker"]
        statements = data.get(period, {}).get(statement_type, {})
        for metric, date_values in statements.items():
            for date, value in date_values.items():
                rows.append(
                    {
                        "Ticker": ticker,
                        "Date": date,
                        "Metric": metric,
                        "Value": value,
                    }
                )
    return pd.DataFrame(rows)


def build_ratios_csv(all_data):
    """Build a wide-format CSV for current ratios.
    Columns: Ticker, ratio1, ratio2, ...
    """
    rows = []
    for data in all_data:
        if data is None:
            continue
        row = {"Ticker": data["ticker"]}
        row.update(data.get("ratios", {}))
        rows.append(row)
    return pd.DataFrame(rows)


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Download S&P 500 fundamental data via yfinance"
    )
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated ticker list (e.g. AAPL,MSFT,NVDA)",
    )
    parser.add_argument(
        "--sp500-csv",
        type=str,
        default=None,
        help="Path to CSV with S&P 500 tickers",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(OUTPUT_DIR),
        help="Output directory for CSV files",
    )
    args = parser.parse_args()

    logger = setup_logging()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Get ticker list ---
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        tickers = get_sp500_tickers(args.sp500_csv)

    if not tickers:
        logger.error("No tickers found. Exiting.")
        sys.exit(1)

    logger.info(f"Starting fundamental download for {len(tickers)} tickers")
    logger.info(f"Output directory: {output_dir}")

    # --- Download ---
    all_data = []
    success = 0
    failed = 0
    failed_tickers = []

    for i, ticker in enumerate(tickers, 1):
        logger.info(f"[{i}/{len(tickers)}] Downloading {ticker}...")
        data = download_single_ticker(ticker, logger)
        if data:
            all_data.append(data)
            success += 1
        else:
            failed += 1
            failed_tickers.append(ticker)

        # Rate limiting
        if i < len(tickers):
            time.sleep(RATE_LIMIT_DELAY)

        # Progress update every 50 tickers
        if i % 50 == 0:
            logger.info(f"  Progress: {i}/{len(tickers)} ({success} ok, {failed} failed)")

    # --- Build CSVs ---
    logger.info("Building CSV files...")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")

    # 1) Annual Income Statement
    df = build_statement_csv(all_data, "income", "annual")
    if not df.empty:
        path = output_dir / "income_annual.csv"
        df.to_csv(path, index=False)
        logger.info(f"  Saved {path} ({len(df)} rows)")

    # 2) Annual Balance Sheet
    df = build_statement_csv(all_data, "balance", "annual")
    if not df.empty:
        path = output_dir / "balance_annual.csv"
        df.to_csv(path, index=False)
        logger.info(f"  Saved {path} ({len(df)} rows)")

    # 3) Annual Cash Flow
    df = build_statement_csv(all_data, "cashflow", "annual")
    if not df.empty:
        path = output_dir / "cashflow_annual.csv"
        df.to_csv(path, index=False)
        logger.info(f"  Saved {path} ({len(df)} rows)")

    # 4) Quarterly Income Statement
    df = build_statement_csv(all_data, "income", "quarterly")
    if not df.empty:
        path = output_dir / "income_quarterly.csv"
        df.to_csv(path, index=False)
        logger.info(f"  Saved {path} ({len(df)} rows)")

    # 5) Quarterly Balance Sheet
    df = build_statement_csv(all_data, "balance", "quarterly")
    if not df.empty:
        path = output_dir / "balance_quarterly.csv"
        df.to_csv(path, index=False)
        logger.info(f"  Saved {path} ({len(df)} rows)")

    # 6) Quarterly Cash Flow
    df = build_statement_csv(all_data, "cashflow", "quarterly")
    if not df.empty:
        path = output_dir / "cashflow_quarterly.csv"
        df.to_csv(path, index=False)
        logger.info(f"  Saved {path} ({len(df)} rows)")

    # 7) Current Ratios (snapshot)
    df = build_ratios_csv(all_data)
    if not df.empty:
        path = output_dir / "ratios_current.csv"
        df.to_csv(path, index=False)
        logger.info(f"  Saved {path} ({len(df)} rows)")

    # --- Summary ---
    summary = {
        "run_date": datetime.now(timezone.utc).isoformat(),
        "total_tickers": len(tickers),
        "success": success,
        "failed": failed,
        "failed_tickers": failed_tickers,
    }
    summary_path = output_dir / "last_run_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info("=" * 50)
    logger.info(f"DONE: {success} success, {failed} failed out of {len(tickers)}")
    if failed_tickers:
        logger.info(f"Failed tickers: {', '.join(failed_tickers[:20])}")
    logger.info("=" * 50)

    # Exit with error code if too many failures
    if failed > len(tickers) * 0.5:
        logger.error("More than 50% failed — possible API issue")
        sys.exit(1)


if __name__ == "__main__":
    main()
