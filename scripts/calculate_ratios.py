"""
SP500 Calculated Ratios Pipeline
=================================
คำนวณ financial ratios 29+ ตัวจาก raw data ใน fundamentals/ folder
แยกจาก ratios ที่ดึงตรงจาก yfinance (ratios_current/quarterly/annual.csv)

Input:  fundamentals/income_annual.csv, balance_annual.csv, cashflow_annual.csv
        fundamentals/income_quarterly.csv, balance_quarterly.csv, cashflow_quarterly.csv
        fundamentals/ratios_current.csv  (สำหรับ market data: Market Cap, EV, Price)

Output: fundamentals/calculated_ratios_annual.csv   (append, dedup Ticker+FiscalDate)
        fundamentals/calculated_ratios_quarterly.csv (append, dedup Ticker+FiscalDate)
        fundamentals/calculated_ratios_current.csv   (overwrite — latest snapshot)

Design:
  - ทุก ratio มี registry (RATIO_REGISTRY) → เพิ่ม ratio ใหม่ง่าย
  - แต่ละ ratio เป็น function รับ dict ของ metrics → return float | None
  - Graceful: ถ้าข้อมูลไม่ครบ → None (ไม่ error)

Usage:
    python calculate_ratios.py
    python calculate_ratios.py --input-dir ../fundamentals --output-dir ../fundamentals
"""

import pandas as pd
import numpy as np
import os
import sys
import logging
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable, Dict, List, Any

# ============================================================
# CONFIG
# ============================================================
DEFAULT_DIR = Path("fundamentals")
LOG_DIR = Path("fundamentals/logs")

# ============================================================
# LOGGING
# ============================================================
def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"calc_ratios_{timestamp}.log"

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
# RATIO CALCULATION FUNCTIONS
# ============================================================
# Each function receives a dict of metric_name → value
# Returns float or None if data insufficient

def _safe_div(a, b):
    """Safe division: returns None if denominator is 0 or either is None."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def _safe_sub(a, b):
    """Safe subtraction."""
    if a is None or b is None:
        return None
    return a - b


# --- Profitability Ratios ---

def calc_gross_margin(m: dict) -> Optional[float]:
    """Gross Margin = Gross Profit / Revenue"""
    return _safe_div(m.get("Gross Profit"), m.get("Total Revenue"))


def calc_operating_margin(m: dict) -> Optional[float]:
    """Operating Margin = Operating Income / Revenue"""
    return _safe_div(m.get("Operating Income"), m.get("Total Revenue"))


def calc_net_margin(m: dict) -> Optional[float]:
    """Net Margin = Net Income / Revenue"""
    return _safe_div(m.get("Net Income"), m.get("Total Revenue"))


def calc_ebitda_margin(m: dict) -> Optional[float]:
    """EBITDA Margin = EBITDA / Revenue"""
    return _safe_div(m.get("EBITDA"), m.get("Total Revenue"))


def calc_fcf_margin(m: dict) -> Optional[float]:
    """FCF Margin = Free Cash Flow / Revenue"""
    return _safe_div(m.get("Free Cash Flow"), m.get("Total Revenue"))


def calc_roe(m: dict) -> Optional[float]:
    """Return on Equity = Net Income / Stockholders Equity"""
    return _safe_div(m.get("Net Income"), m.get("Stockholders Equity"))


def calc_roa(m: dict) -> Optional[float]:
    """Return on Assets = Net Income / Total Assets"""
    return _safe_div(m.get("Net Income"), m.get("Total Assets"))


def calc_roic(m: dict) -> Optional[float]:
    """ROIC = NOPAT / Invested Capital
    NOPAT = Operating Income × (1 - Tax Rate)
    Tax Rate = Tax Provision / Pretax Income
    Invested Capital = Total Debt + Stockholders Equity - Cash
    """
    op_income = m.get("Operating Income")
    tax = m.get("Tax Provision")
    pretax = m.get("Pretax Income")
    invested = m.get("Invested Capital")

    # Fallback: calculate Invested Capital if not directly available
    if invested is None:
        debt = m.get("Total Debt")
        equity = m.get("Stockholders Equity")
        cash = m.get("Cash And Cash Equivalents")
        if debt is not None and equity is not None:
            invested = debt + equity - (cash or 0)

    if op_income is None or invested is None or invested == 0:
        return None

    # Tax rate
    if pretax and pretax != 0 and tax is not None:
        tax_rate = tax / pretax
        tax_rate = max(0, min(tax_rate, 1))  # clamp 0-1
    else:
        tax_rate = 0.21  # fallback US corporate rate

    nopat = op_income * (1 - tax_rate)
    return nopat / invested


def calc_roce(m: dict) -> Optional[float]:
    """ROCE = EBIT / Capital Employed
    Capital Employed = Total Assets - Current Liabilities
    """
    ebit = m.get("EBIT") or m.get("Operating Income")
    assets = m.get("Total Assets")
    cl = m.get("Current Liabilities")
    if ebit is None or assets is None or cl is None:
        return None
    cap_employed = assets - cl
    return _safe_div(ebit, cap_employed)


# --- Valuation Ratios (need Market Cap / Price) ---

def calc_pe_ratio(m: dict) -> Optional[float]:
    """P/E = Market Cap / Net Income"""
    return _safe_div(m.get("Market Cap"), m.get("Net Income"))


def calc_ps_ratio(m: dict) -> Optional[float]:
    """P/S = Market Cap / Revenue"""
    return _safe_div(m.get("Market Cap"), m.get("Total Revenue"))


def calc_pb_ratio(m: dict) -> Optional[float]:
    """P/B = Market Cap / Book Value (Stockholders Equity)"""
    return _safe_div(m.get("Market Cap"), m.get("Stockholders Equity"))


def calc_pfcf_ratio(m: dict) -> Optional[float]:
    """P/FCF = Market Cap / Free Cash Flow"""
    return _safe_div(m.get("Market Cap"), m.get("Free Cash Flow"))


def calc_ev_ebitda(m: dict) -> Optional[float]:
    """EV/EBITDA = Enterprise Value / EBITDA"""
    return _safe_div(m.get("Enterprise Value"), m.get("EBITDA"))


def calc_ev_revenue(m: dict) -> Optional[float]:
    """EV/Revenue = Enterprise Value / Revenue"""
    return _safe_div(m.get("Enterprise Value"), m.get("Total Revenue"))


def calc_ev_fcf(m: dict) -> Optional[float]:
    """EV/FCF = Enterprise Value / Free Cash Flow"""
    return _safe_div(m.get("Enterprise Value"), m.get("Free Cash Flow"))


def calc_earnings_yield(m: dict) -> Optional[float]:
    """Earnings Yield = Net Income / Market Cap (inverse P/E)"""
    return _safe_div(m.get("Net Income"), m.get("Market Cap"))


# --- Leverage & Solvency ---

def calc_debt_to_equity(m: dict) -> Optional[float]:
    """Debt/Equity = Total Debt / Stockholders Equity"""
    return _safe_div(m.get("Total Debt"), m.get("Stockholders Equity"))


def calc_debt_to_assets(m: dict) -> Optional[float]:
    """Debt/Assets = Total Debt / Total Assets"""
    return _safe_div(m.get("Total Debt"), m.get("Total Assets"))


def calc_net_debt_to_ebitda(m: dict) -> Optional[float]:
    """Net Debt / EBITDA"""
    return _safe_div(m.get("Net Debt"), m.get("EBITDA"))


def calc_interest_coverage(m: dict) -> Optional[float]:
    """Interest Coverage = EBIT / Interest Expense"""
    ebit = m.get("EBIT") or m.get("Operating Income")
    interest = m.get("Interest Expense")
    if interest is not None and interest < 0:
        interest = abs(interest)  # yfinance sometimes gives negative
    return _safe_div(ebit, interest)


def calc_current_ratio(m: dict) -> Optional[float]:
    """Current Ratio = Current Assets / Current Liabilities"""
    return _safe_div(m.get("Current Assets"), m.get("Current Liabilities"))


def calc_quick_ratio(m: dict) -> Optional[float]:
    """Quick Ratio = (Current Assets - Inventory) / Current Liabilities"""
    ca = m.get("Current Assets")
    inv = m.get("Inventory") or 0
    cl = m.get("Current Liabilities")
    if ca is None or cl is None or cl == 0:
        return None
    return (ca - inv) / cl


# --- Efficiency ---

def calc_asset_turnover(m: dict) -> Optional[float]:
    """Asset Turnover = Revenue / Total Assets"""
    return _safe_div(m.get("Total Revenue"), m.get("Total Assets"))


def calc_receivables_turnover(m: dict) -> Optional[float]:
    """Receivables Turnover = Revenue / Accounts Receivable"""
    return _safe_div(m.get("Total Revenue"), m.get("Accounts Receivable"))


def calc_cash_conversion_cycle(m: dict) -> Optional[float]:
    """Cash Conversion Cycle = DIO + DSO - DPO
    DIO = (Inventory / COGS) × 365
    DSO = (Accounts Receivable / Revenue) × 365
    DPO = (Accounts Payable / COGS) × 365
    """
    revenue = m.get("Total Revenue")
    cogs = m.get("Cost Of Revenue")
    ar = m.get("Accounts Receivable")
    inv = m.get("Inventory")
    ap = m.get("Accounts Payable")

    if revenue is None or cogs is None or cogs == 0:
        return None
    if ar is None and inv is None and ap is None:
        return None

    dio = (inv / cogs * 365) if inv and cogs else 0
    dso = (ar / revenue * 365) if ar and revenue else 0
    dpo = (ap / cogs * 365) if ap and cogs else 0

    return dio + dso - dpo


# --- Cash Flow Quality ---

def calc_cash_conversion_ratio(m: dict) -> Optional[float]:
    """Cash Conversion Ratio = Operating Cash Flow / Net Income"""
    return _safe_div(m.get("Operating Cash Flow"), m.get("Net Income"))


def calc_capex_to_revenue(m: dict) -> Optional[float]:
    """CapEx/Revenue = Capital Expenditure / Revenue"""
    capex = m.get("Capital Expenditure")
    if capex is not None and capex < 0:
        capex = abs(capex)
    return _safe_div(capex, m.get("Total Revenue"))


def calc_sbc_to_revenue(m: dict) -> Optional[float]:
    """SBC/Revenue = Stock Based Compensation / Revenue"""
    return _safe_div(m.get("Stock Based Compensation"), m.get("Total Revenue"))


# ============================================================
# RATIO REGISTRY — เพิ่ม ratio ใหม่ที่นี่
# ============================================================
# Format: (output_column_name, calc_function, category)
# category ใช้สำหรับ grouping ใน output

RATIO_REGISTRY: List[tuple] = [
    # --- Profitability (9) ---
    ("Gross Margin (calc)",         calc_gross_margin,         "Profitability"),
    ("Operating Margin (calc)",     calc_operating_margin,     "Profitability"),
    ("Net Margin (calc)",           calc_net_margin,           "Profitability"),
    ("EBITDA Margin (calc)",        calc_ebitda_margin,        "Profitability"),
    ("FCF Margin (calc)",           calc_fcf_margin,           "Profitability"),
    ("ROE (calc)",                  calc_roe,                  "Profitability"),
    ("ROA (calc)",                  calc_roa,                  "Profitability"),
    ("ROIC (calc)",                 calc_roic,                 "Profitability"),
    ("ROCE (calc)",                 calc_roce,                 "Profitability"),

    # --- Valuation (8) ---
    ("P/E (calc)",                  calc_pe_ratio,             "Valuation"),
    ("P/S (calc)",                  calc_ps_ratio,             "Valuation"),
    ("P/B (calc)",                  calc_pb_ratio,             "Valuation"),
    ("P/FCF (calc)",                calc_pfcf_ratio,           "Valuation"),
    ("EV/EBITDA (calc)",            calc_ev_ebitda,            "Valuation"),
    ("EV/Revenue (calc)",           calc_ev_revenue,           "Valuation"),
    ("EV/FCF (calc)",               calc_ev_fcf,               "Valuation"),
    ("Earnings Yield (calc)",       calc_earnings_yield,       "Valuation"),

    # --- Leverage & Solvency (5) ---
    ("Debt/Equity (calc)",          calc_debt_to_equity,       "Leverage"),
    ("Debt/Assets (calc)",          calc_debt_to_assets,       "Leverage"),
    ("Net Debt/EBITDA (calc)",      calc_net_debt_to_ebitda,   "Leverage"),
    ("Interest Coverage (calc)",    calc_interest_coverage,    "Leverage"),
    ("Current Ratio (calc)",        calc_current_ratio,        "Leverage"),
    ("Quick Ratio (calc)",          calc_quick_ratio,          "Leverage"),

    # --- Efficiency (3) ---
    ("Asset Turnover (calc)",       calc_asset_turnover,       "Efficiency"),
    ("Receivables Turnover (calc)", calc_receivables_turnover, "Efficiency"),
    ("Cash Conversion Cycle (calc)",calc_cash_conversion_cycle,"Efficiency"),

    # --- Cash Flow Quality (3) ---
    ("Cash Conversion Ratio (calc)", calc_cash_conversion_ratio, "CashFlow"),
    ("CapEx/Revenue (calc)",         calc_capex_to_revenue,      "CashFlow"),
    ("SBC/Revenue (calc)",           calc_sbc_to_revenue,        "CashFlow"),
]


# ============================================================
# DATA LOADING — pivot long-format CSVs to wide per Ticker+Date
# ============================================================
def load_statement_wide(csv_path: Path) -> pd.DataFrame:
    """Load a long-format statement CSV (Ticker, Date, Metric, Value)
    and pivot to wide: index=(Ticker, Date), columns=Metric values.
    """
    if not csv_path.exists():
        logging.warning(f"File not found: {csv_path}")
        return pd.DataFrame()

    df = pd.read_csv(csv_path)
    if df.empty:
        return pd.DataFrame()

    # Dedup: keep last occurrence per (Ticker, Date, Metric)
    df = df.drop_duplicates(subset=["Ticker", "Date", "Metric"], keep="last")

    # Pivot
    wide = df.pivot_table(
        index=["Ticker", "Date"],
        columns="Metric",
        values="Value",
        aggfunc="last",
    )
    wide.columns.name = None
    wide = wide.reset_index()
    return wide


def load_ratios_current(csv_path: Path) -> pd.DataFrame:
    """Load ratios_current.csv for market data (Market Cap, EV, etc.)."""
    if not csv_path.exists():
        logging.warning(f"File not found: {csv_path}")
        return pd.DataFrame()
    return pd.read_csv(csv_path)


def merge_statements(income: pd.DataFrame, balance: pd.DataFrame,
                     cashflow: pd.DataFrame) -> pd.DataFrame:
    """Merge 3 wide-format statement DataFrames on (Ticker, Date)."""
    if income.empty and balance.empty and cashflow.empty:
        return pd.DataFrame()

    # Start with whichever is non-empty
    dfs = [df for df in [income, balance, cashflow] if not df.empty]
    merged = dfs[0]
    for df in dfs[1:]:
        merged = merged.merge(df, on=["Ticker", "Date"], how="outer",
                              suffixes=("", "_dup"))
        # Drop duplicate columns
        dup_cols = [c for c in merged.columns if c.endswith("_dup")]
        merged = merged.drop(columns=dup_cols)

    return merged


def attach_market_data(stmt_df: pd.DataFrame,
                       ratios_current: pd.DataFrame) -> pd.DataFrame:
    """Attach Market Cap and Enterprise Value from ratios_current
    to each row by Ticker. (Current snapshot applied to all periods.)
    """
    if ratios_current.empty or stmt_df.empty:
        return stmt_df

    market_cols = ["Ticker", "Market Cap", "Enterprise Value"]
    available = [c for c in market_cols if c in ratios_current.columns]
    if len(available) <= 1:  # only Ticker
        return stmt_df

    market = ratios_current[available].drop_duplicates(subset=["Ticker"])

    return stmt_df.merge(market, on="Ticker", how="left")


# ============================================================
# RATIO CALCULATION ENGINE
# ============================================================
def calculate_all_ratios(merged_df: pd.DataFrame,
                         logger: logging.Logger) -> pd.DataFrame:
    """Calculate all registered ratios for each (Ticker, Date) row.
    Returns a DataFrame with Ticker, FiscalDate, + all ratio columns.
    """
    if merged_df.empty:
        return pd.DataFrame()

    results = []
    for _, row in merged_df.iterrows():
        m = row.to_dict()
        result_row = {
            "Ticker": m.get("Ticker"),
            "FiscalDate": m.get("Date"),
        }
        for col_name, calc_fn, category in RATIO_REGISTRY:
            try:
                val = calc_fn(m)
                # Round to 6 decimal places
                if val is not None and not np.isnan(val) and not np.isinf(val):
                    result_row[col_name] = round(val, 6)
                else:
                    result_row[col_name] = None
            except Exception as e:
                result_row[col_name] = None

        results.append(result_row)

    df = pd.DataFrame(results)

    # Drop rows where ALL ratio columns are None
    ratio_cols = [name for name, _, _ in RATIO_REGISTRY]
    df = df.dropna(subset=ratio_cols, how="all")

    return df


# ============================================================
# MERGE WITH EXISTING (append, dedup)
# ============================================================
def merge_append(new_df: pd.DataFrame, csv_path: Path,
                 key_cols: list) -> pd.DataFrame:
    """Append new data to existing CSV, dedup by key_cols.
    For duplicates: prefer new data (updated calculations).
    """
    if not csv_path.exists():
        return new_df

    try:
        existing = pd.read_csv(csv_path)
        combined = pd.concat([existing, new_df], ignore_index=True)
        # Keep last (= new data wins)
        combined = combined.drop_duplicates(subset=key_cols, keep="last")
        combined = combined.sort_values(key_cols).reset_index(drop=True)
        return combined
    except Exception as e:
        logging.warning(f"Could not merge with {csv_path}: {e}")
        return new_df


# ============================================================
# CURRENT SNAPSHOT — calculate from latest fiscal date per ticker
# ============================================================
def build_current_snapshot(annual_df: pd.DataFrame,
                           quarterly_df: pd.DataFrame) -> pd.DataFrame:
    """Build current snapshot: for each ticker, use latest available data.
    Priority: quarterly (most recent) > annual.
    """
    frames = []
    if not quarterly_df.empty:
        # Get latest quarter per ticker
        q = quarterly_df.sort_values("FiscalDate", ascending=False)
        q = q.drop_duplicates(subset=["Ticker"], keep="first")
        q["Source"] = "quarterly"
        frames.append(q)

    if not annual_df.empty:
        a = annual_df.sort_values("FiscalDate", ascending=False)
        a = a.drop_duplicates(subset=["Ticker"], keep="first")
        a["Source"] = "annual"
        frames.append(a)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    # Prefer quarterly over annual for same ticker
    combined["_priority"] = combined["Source"].map({"quarterly": 0, "annual": 1})
    combined = combined.sort_values(["Ticker", "_priority"])
    combined = combined.drop_duplicates(subset=["Ticker"], keep="first")
    combined = combined.drop(columns=["_priority"])
    combined = combined.sort_values("Ticker").reset_index(drop=True)

    return combined


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Calculate financial ratios from raw fundamental data"
    )
    parser.add_argument(
        "--input-dir", type=str, default=str(DEFAULT_DIR),
        help="Directory containing raw fundamental CSVs"
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory (default: same as input-dir)"
    )
    args = parser.parse_args()

    logger = setup_logging()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir) if args.output_dir else input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("SP500 Calculated Ratios Pipeline")
    logger.info(f"Input:  {input_dir}")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Ratios: {len(RATIO_REGISTRY)} registered")
    logger.info("=" * 60)

    # --- Load raw data ---
    logger.info("Loading raw financial statement CSVs...")

    inc_annual = load_statement_wide(input_dir / "income_annual.csv")
    bal_annual = load_statement_wide(input_dir / "balance_annual.csv")
    cf_annual  = load_statement_wide(input_dir / "cashflow_annual.csv")

    inc_qtr = load_statement_wide(input_dir / "income_quarterly.csv")
    bal_qtr = load_statement_wide(input_dir / "balance_quarterly.csv")
    cf_qtr  = load_statement_wide(input_dir / "cashflow_quarterly.csv")

    ratios_current = load_ratios_current(input_dir / "ratios_current.csv")

    logger.info(f"  Annual  — Income: {len(inc_annual)}, Balance: {len(bal_annual)}, CashFlow: {len(cf_annual)}")
    logger.info(f"  Quarter — Income: {len(inc_qtr)}, Balance: {len(bal_qtr)}, CashFlow: {len(cf_qtr)}")
    logger.info(f"  Ratios Current: {len(ratios_current)} tickers")

    # --- Merge statements ---
    logger.info("Merging statements...")
    annual_merged = merge_statements(inc_annual, bal_annual, cf_annual)
    qtr_merged = merge_statements(inc_qtr, bal_qtr, cf_qtr)

    # Attach market data for valuation ratios
    annual_merged = attach_market_data(annual_merged, ratios_current)
    qtr_merged = attach_market_data(qtr_merged, ratios_current)

    logger.info(f"  Annual merged:    {len(annual_merged)} rows")
    logger.info(f"  Quarterly merged: {len(qtr_merged)} rows")

    # --- Calculate ratios ---
    logger.info("Calculating ratios...")

    calc_annual = calculate_all_ratios(annual_merged, logger)
    calc_qtr = calculate_all_ratios(qtr_merged, logger)

    logger.info(f"  Annual calculated:    {len(calc_annual)} rows")
    logger.info(f"  Quarterly calculated: {len(calc_qtr)} rows")

    # --- Save: Annual (append) ---
    if not calc_annual.empty:
        path = output_dir / "calculated_ratios_annual.csv"
        df = merge_append(calc_annual, path, ["Ticker", "FiscalDate"])
        df.to_csv(path, index=False)
        logger.info(f"  Saved {path} ({len(df)} rows) [append]")

    # --- Save: Quarterly (append) ---
    if not calc_qtr.empty:
        path = output_dir / "calculated_ratios_quarterly.csv"
        df = merge_append(calc_qtr, path, ["Ticker", "FiscalDate"])
        df.to_csv(path, index=False)
        logger.info(f"  Saved {path} ({len(df)} rows) [append]")

    # --- Save: Current snapshot (overwrite) ---
    current = build_current_snapshot(calc_annual, calc_qtr)
    if not current.empty:
        path = output_dir / "calculated_ratios_current.csv"
        current.to_csv(path, index=False)
        logger.info(f"  Saved {path} ({len(current)} rows) [overwrite]")

    # --- Summary stats ---
    ratio_cols = [name for name, _, _ in RATIO_REGISTRY]
    coverage = {}
    if not calc_annual.empty:
        for col in ratio_cols:
            if col in calc_annual.columns:
                pct = calc_annual[col].notna().mean() * 100
                coverage[col] = f"{pct:.1f}%"

    summary = {
        "run_date": datetime.now(timezone.utc).isoformat(),
        "ratios_count": len(RATIO_REGISTRY),
        "annual_rows": len(calc_annual) if not calc_annual.empty else 0,
        "quarterly_rows": len(calc_qtr) if not calc_qtr.empty else 0,
        "current_rows": len(current) if not current.empty else 0,
        "annual_coverage": coverage,
        "ratio_list": [name for name, _, _ in RATIO_REGISTRY],
    }

    summary_path = output_dir / "calc_ratios_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"  Summary: {summary_path}")

    # Print coverage highlights
    logger.info("")
    logger.info("Coverage highlights (annual):")
    for name, pct in sorted(coverage.items(), key=lambda x: x[1], reverse=True)[:10]:
        logger.info(f"  {name}: {pct}")

    logger.info("")
    logger.info("=" * 60)
    logger.info("DONE — Calculated ratios pipeline complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
