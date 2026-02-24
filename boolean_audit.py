#!/usr/bin/env python3
"""
🔒 Boolean Audit v1.0 — MANDATORY before every git push
ตรวจ boolean values ใน CSV และ Dashboard HTML ให้ตรง contract

Usage: python3 boolean_audit.py
Exit code 0 = PASS, 1 = FAIL
"""

import csv
import glob
import re
import sys
import os

PASS = True  # global tracker

# ══════════════════════════════════════════════════════════
# BOOLEAN CONTRACT — กฎตายตัว
# ══════════════════════════════════════════════════════════

# Define expected values for each boolean column per CSV pattern
# Key = column name, Value = set of allowed string values
BOOLEAN_CONTRACTS = {
    "output_combined_score_sp500*.csv": {
        "Golden_Cross":       {"True", "False"},
        "In_News_Screening":  {"TRUE", "FALSE"},
        "Has_Deal":           {"TRUE", "FALSE", ""},  # empty allowed for non-news stocks
    },
    "output_momentum_sp500*.csv": {
        "Golden_Cross":       {"True", "False"},
    },
    "output_screening_largecap_sp500*.csv": {
        "Has_Deal":           {"TRUE", "FALSE"},
    },
    "output_screening_smallcap_russell2000*.csv": {
        "Has_Deal":           {"TRUE", "FALSE"},
    },
}

# Dashboard strict comparison patterns that should NOT exist
# These are case-sensitive JS comparisons that will break on case mismatch
DASHBOARD_BAD_PATTERNS = [
    r"===\s*['\"]True['\"]",
    r"===\s*['\"]False['\"]",
    r"===\s*['\"]TRUE['\"]",
    r"===\s*['\"]FALSE['\"]",
    r"!==\s*['\"]True['\"]",
    r"!==\s*['\"]False['\"]",
    r"!==\s*['\"]TRUE['\"]",
    r"!==\s*['\"]FALSE['\"]",
]

# Exclude these patterns (they're fine — using toLowerCase)
DASHBOARD_OK_PATTERNS = [
    r"\.toLowerCase\(\)\s*===",
    r"\.toLowerCase\(\)\s*!==",
    r"\.toUpperCase\(\)\s*===",
    r"\.toUpperCase\(\)\s*!==",
]


def audit_csv():
    """Part 1: Audit all CSV files against boolean contract."""
    global PASS
    print("=" * 60)
    print("PART 1: CSV BOOLEAN AUDIT")
    print("=" * 60)

    any_csv_found = False

    for pattern, columns in BOOLEAN_CONTRACTS.items():
        files = sorted(glob.glob(pattern))
        if not files:
            continue

        for filepath in files:
            any_csv_found = True
            print(f"\n📄 {filepath}")

            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                print("   ⚠️  Empty file — skipping")
                continue

            for col, allowed in columns.items():
                if col not in rows[0]:
                    print(f"   ⚠️  Column '{col}' not found — skipping")
                    continue

                # Count values
                value_counts = {}
                violations = []
                for i, row in enumerate(rows):
                    val = row[col].strip()
                    value_counts[val] = value_counts.get(val, 0) + 1
                    if val not in allowed:
                        violations.append((i + 2, val))  # +2 for header + 0-index

                # Report
                print(f"\n   Column: {col}")
                print(f"   Allowed: {allowed}")
                print(f"   Values found:")
                for val, count in sorted(value_counts.items(), key=lambda x: -x[1]):
                    marker = "✅" if val in allowed else "❌"
                    display_val = repr(val) if val == "" else val
                    print(f"      {marker} {display_val}: {count}")

                if violations:
                    PASS = False
                    print(f"   ❌ FAIL — {len(violations)} violations found!")
                    # Show first 5 violations
                    for row_num, val in violations[:5]:
                        print(f"      Row {row_num}: got '{val}'")
                    if len(violations) > 5:
                        print(f"      ... and {len(violations) - 5} more")
                else:
                    print(f"   ✅ PASS")

    if not any_csv_found:
        print("\n   ⚠️  No CSV files matched any pattern — nothing to audit")


def audit_dashboards():
    """Part 2: Audit Dashboard HTML files for strict boolean comparisons."""
    global PASS
    print("\n" + "=" * 60)
    print("PART 2: DASHBOARD BOOLEAN AUDIT")
    print("=" * 60)

    html_files = sorted(glob.glob("*.html"))
    if not html_files:
        print("\n   ⚠️  No HTML files found — skipping")
        return

    for filepath in html_files:
        print(f"\n📄 {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        issues = []
        for line_num, line in enumerate(lines, 1):
            # Skip lines that use toLowerCase/toUpperCase (these are safe)
            if any(re.search(ok, line) for ok in DASHBOARD_OK_PATTERNS):
                continue

            for bad_pattern in DASHBOARD_BAD_PATTERNS:
                matches = list(re.finditer(bad_pattern, line))
                for m in matches:
                    # Double-check it's not preceded by toLowerCase on same line
                    before = line[:m.start()]
                    if '.toLowerCase()' in before or '.toUpperCase()' in before:
                        continue
                    issues.append((line_num, m.group(), line.strip()[:120]))

        if issues:
            PASS = False
            print(f"   ❌ FAIL — {len(issues)} strict boolean comparison(s) found!")
            for line_num, match, context in issues:
                print(f"      Line {line_num}: {match}")
                print(f"        → {context}")
            print(f"\n   FIX: Use .toLowerCase() === 'true' instead of === 'True'")
            print(f"   Example: String(d.Golden_Cross).toLowerCase() === 'true'")
        else:
            print(f"   ✅ PASS — No strict boolean comparisons found")


def main():
    global PASS

    print("🔒 BOOLEAN AUDIT v1.0")
    print(f"   Directory: {os.getcwd()}")
    print()

    audit_csv()
    audit_dashboards()

    # ── Final Verdict ──
    print("\n" + "=" * 60)
    if PASS:
        print("✅ ALL BOOLEAN CHECKS PASSED — Safe to push")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ BOOLEAN AUDIT FAILED — ห้าม push จนกว่าจะแก้!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
