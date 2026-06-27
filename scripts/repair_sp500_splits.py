#!/usr/bin/env python3
"""
S&P 500 Split / Reverse-Split Repair  —  JP Trust Learning
============================================================

ปัญหา: update_sp500_daily.py เป็น append-only + yf.Ticker().history() ปรับ
auto_adjust เฉพาะ window ที่ดึงใหม่ → แถวเก่าก่อนวันแตกพาร์/รวมพาร์ ไม่เคยถูกย้อนปรับ
→ เกิดรอยต่อ (discontinuity) ราคา เช่น KLAC 10:1, BKNG 24:1, CVNA 5:1

flow นี้รันแยกจาก pipeline รายวัน (กดเอง รายเดือน ผ่าน workflow_dispatch):

  1. DETECT  — หว่านแหกว้างบน CSV หา single-day discontinuity (forward + reverse)
  2. CONFIRM — ยืนยัน factor "เป๊ะ" จาก yfinance .splits (match ตามวันที่)
               → กรอง crash / spinoff (ที่ไม่มี split record) ออก
               → หรือใช้ --manual overrides.json (กรณีรัน offline / yfinance ดึงไม่ได้)
  3. BACKUP  — คัดลอกของเดิม -> input_sp500_daily_before<YYYYMMDD>_par_ratio.csv
  4. CORRECT — แถว Date < split_date :  OHLC ÷ factor , Volume × factor
               (สูตรเดียวคุมทั้ง forward[factor>1] + reverse[factor<1])

โหมด:
  --dry-run (default) : ทำ 1-2 แล้วพิมพ์ตาราง ไม่เขียนไฟล์
  --apply             : ทำครบ 1-4 (backup + เขียน CSV ใหม่)

idempotent: แก้แล้ว series ต่อเนื่อง รอบหน้าจะไม่ flag ซ้ำ → ไม่มีทาง over-correct
"""

import os
import csv
import sys
import json
import argparse
from datetime import datetime, date, timezone
from collections import defaultdict

# ---------------------------------------------------------------------------
# CONFIG — wide net; yfinance confirmation กรอง false positive ทีหลัง
# ---------------------------------------------------------------------------
DEFAULT_CSV       = 'input_sp500_daily.csv'
PX_DROP_MAX       = 0.75   # ratio ต่ำกว่านี้ = อาจ forward split (ราคาลงแรง)
PX_JUMP_MIN       = 1.33   # ratio สูงกว่านี้ = อาจ reverse split (ราคาเด้งแรง)
DATE_MATCH_DAYS   = 4      # tolerance จับคู่วัน discontinuity กับวัน split ของ yfinance
SCAN_FROM         = '2026-01-01'  # ช่วงที่สแกนหา candidate (เลื่อนได้ด้วย --scan-from)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _d(s):
    return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))


def fmt_price(x):
    """format ราคาแบบ 2 ทศนิยม (ใช้เฉพาะแถวที่ถูกแก้)"""
    return f"{round(x, 2):.2f}"


# ---------------------------------------------------------------------------
# STEP 1 — DETECT candidates
# ---------------------------------------------------------------------------
def detect_candidates(csv_file, scan_from):
    """อ่าน CSV (stream) จัดกลุ่มตาม ticker หา single-day discontinuity"""
    series = defaultdict(list)  # ticker -> [(date, close, volume), ...]
    with open(csv_file, newline='') as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            if len(row) < 7:
                continue
            t, d, _o, _h, _l, c, v = row[:7]
            try:
                series[t].append((d, float(c), float(v)))
            except ValueError:
                continue

    candidates = []  # (ticker, disc_date, prev_close, close, px_ratio, vol_jump)
    for t, rows in series.items():
        rows.sort()
        for i in range(1, len(rows)):
            d, c, v = rows[i]
            pd_, pc, pv = rows[i - 1]
            if d < scan_from or pc <= 0 or c <= 0:
                continue
            ratio = c / pc
            if ratio < PX_DROP_MAX or ratio > PX_JUMP_MIN:
                vj = (v / pv) if pv > 0 else 0.0
                candidates.append((t, d, pc, c, ratio, vj))
    candidates.sort(key=lambda x: x[4])
    return candidates


# ---------------------------------------------------------------------------
# STEP 2 — CONFIRM via yfinance .splits (or manual overrides)
# ---------------------------------------------------------------------------
def load_manual(path):
    """overrides.json รูปแบบ: {"KLAC":[{"date":"2026-06-11","factor":10}], ...}"""
    if not path:
        return {}
    with open(path) as f:
        raw = json.load(f)
    out = defaultdict(list)
    for t, evs in raw.items():
        for e in evs:
            out[t].append((e['date'], float(e['factor'])))
    return out


def confirm_factors(candidates, manual):
    """
    detection เป็นประตูเดียว: แก้เฉพาะ candidate (รอยต่อที่ "ยังมีอยู่จริง") เท่านั้น
    manual แค่ "จ่าย factor" ให้ candidate ที่จับคู่วันได้ ไม่บังคับแก้เอง
    -> idempotent ทุก path (รันซ้ำหลังแก้แล้ว detection ไม่เจอ -> ไม่ทำอะไร)

    boundary การแก้ใช้ "วัน discontinuity (d)" = วันแรกที่ราคาใหม่โผล่ใน CSV
    (แถว Date < d ถูกแก้, แถว d เองคือราคาใหม่ ไม่แตะ)

    คืน (confirmed, review):
      confirmed : ticker -> list[(disc_date, factor)]
      review    : list[(ticker, disc_date, px_ratio, vol_jump, reason)]
    """
    confirmed = defaultdict(list)
    review = []

    try:
        import yfinance as yf
        have_yf, yf_err = True, ''
    except Exception as e:
        have_yf, yf_err = False, str(e)

    _splits_cache = {}

    def yf_splits(t):
        if t not in _splits_cache:
            try:
                _splits_cache[t] = yf.Ticker(t).splits
            except Exception as e:
                _splits_cache[t] = e
        return _splits_cache[t]

    for t, d, pc, c, ratio, vj in candidates:
        factor = None

        # 1) manual override ที่จับคู่วันกับ candidate นี้ (authoritative)
        for md, mf in manual.get(t, []):
            if abs((_d(d) - _d(md)).days) <= DATE_MATCH_DAYS:
                factor = float(mf)
                break

        # 2) ไม่มี manual -> ลอง yfinance .splits
        if factor is None:
            if not have_yf:
                review.append((t, d, ratio, vj, f'no yfinance ({yf_err}) & no manual'))
                continue
            spl = yf_splits(t)
            if isinstance(spl, Exception):
                review.append((t, d, ratio, vj, f'yfinance error: {spl}'))
                continue
            for ts, fac in spl.items():
                sd = ts.strftime('%Y-%m-%d')
                if abs((_d(d) - _d(sd)).days) <= DATE_MATCH_DAYS:
                    factor = float(fac)
                    break
            if factor is None:
                review.append((t, d, ratio, vj, 'no split record near date (crash/spinoff?)'))
                continue

        # sanity: ราคาลง(ratio<1) ต้องคู่กับ forward(factor>1) และกลับกัน
        if factor <= 0 or (ratio < 1) == (factor < 1):
            review.append((t, d, ratio, vj, f'direction mismatch (factor={factor})'))
            continue

        confirmed[t].append((d, factor))

    for t in confirmed:
        confirmed[t] = sorted(set(confirmed[t]))
    return confirmed, review


# ---------------------------------------------------------------------------
# STEP 3+4 — BACKUP + CORRECT (apply only)
# ---------------------------------------------------------------------------
def apply_corrections(csv_file, confirmed):
    """
    เขียน CSV ใหม่ (stream) :
      - แถวที่ไม่ต้องแก้ -> ผ่านบรรทัดดิบเดิม byte-identical (กัน diff เพี้ยน + LF)
      - แถวก่อนวัน split -> OHLC ÷ cumfactor, Volume × cumfactor
    คืน (backup_path, n_rows_changed, per_ticker_counts)
    """
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d')
    backup_path = csv_file.replace('.csv', f'_before{stamp}_par_ratio.csv')

    # 1) BACKUP ก่อนเสมอ
    with open(csv_file, 'rb') as src, open(backup_path, 'wb') as dst:
        dst.write(src.read())

    # 2) CORRECT — เขียนลงไฟล์ชั่วคราวแล้ว replace
    tmp = csv_file + '.tmp'
    changed = 0
    counts = defaultdict(int)
    with open(csv_file, newline='') as fin, open(tmp, 'w', newline='') as fout:
        header = fin.readline()
        fout.write(header)
        for line in fin:
            parts = line.rstrip('\n').split(',')
            if len(parts) < 7:
                fout.write(line)
                continue
            t, d = parts[0], parts[1]
            splits = confirmed.get(t)
            if not splits:
                fout.write(line)        # ticker ไม่มี split -> ดิบเดิม
                continue
            # cumfactor = ผลคูณ factor ของทุก split ที่ "เกิดทีหลังแถวนี้"
            cum = 1.0
            for sd, fac in splits:
                if d < sd:
                    cum *= fac
            if cum == 1.0:
                fout.write(line)        # แถวนี้อยู่หลัง split ทั้งหมด -> ดิบเดิม
                continue
            o, h, l, c, v = float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5]), float(parts[6])
            no = fmt_price(o / cum)
            nh = fmt_price(h / cum)
            nl = fmt_price(l / cum)
            nc = fmt_price(c / cum)
            nv = str(int(round(v * cum)))
            fout.write(f"{t},{d},{no},{nh},{nl},{nc},{nv}\n")
            changed += 1
            counts[t] += 1

    os.replace(tmp, csv_file)
    return backup_path, changed, dict(counts)


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def print_plan(confirmed, review):
    print('\n' + '=' * 70)
    print('CONFIRMED splits (จะถูกแก้):')
    print('-' * 70)
    if not confirmed:
        print('  (ไม่มี)')
    for t in sorted(confirmed):
        for sd, fac in confirmed[t]:
            kind = 'forward' if fac > 1 else 'reverse'
            print(f'  {t:<7} {sd}  factor={fac:<8g} ({kind} split)  '
                  f'-> แถวก่อนวันนี้ OHLC÷{fac:g}, Vol×{fac:g}')
    print('-' * 70)
    print('NEEDS REVIEW (ยืนยันไม่ได้ -> ไม่แตะ ให้เช็คเอง):')
    print('-' * 70)
    if not review:
        print('  (ไม่มี)')
    for t, d, ratio, vj, reason in review:
        print(f'  {t:<7} {d}  px_ratio={ratio:.3f}  vol_jump×{vj:.1f}  | {reason}')
    print('=' * 70)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description='S&P 500 split / reverse-split repair')
    ap.add_argument('--file', default=DEFAULT_CSV, help='CSV ที่จะซ่อม')
    ap.add_argument('--scan-from', default=SCAN_FROM, help='สแกน candidate ตั้งแต่วันนี้ (YYYY-MM-DD)')
    ap.add_argument('--manual', default=None, help='overrides.json (offline / yfinance ดึงไม่ได้)')
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--dry-run', action='store_true', help='(default) แค่ดูแผน ไม่เขียน')
    g.add_argument('--apply', action='store_true', help='backup + เขียน CSV ใหม่')
    args = ap.parse_args()

    apply_mode = args.apply and not args.dry_run
    mode = 'APPLY' if apply_mode else 'DRY-RUN'
    print('=' * 70)
    print(f'📈 SP500 Split Repair — mode: {mode}  | file: {args.file}')
    print('=' * 70)

    if not os.path.exists(args.file):
        print(f'❌ ไม่พบไฟล์: {args.file}')
        sys.exit(1)

    cands = detect_candidates(args.file, args.scan_from)
    print(f'\n🔎 เจอ candidate discontinuity {len(cands)} จุด (ตั้งแต่ {args.scan_from})')
    for t, d, pc, c, ratio, vj in cands:
        print(f'   {t:<7} {d}  {pc:>10.2f} -> {c:>9.2f}  ratio={ratio:.3f}  vol×{vj:.1f}')

    manual = load_manual(args.manual)
    if manual:
        print(f'\n📌 manual overrides: {sum(len(v) for v in manual.values())} รายการ')

    confirmed, review = confirm_factors(cands, manual)
    print_plan(confirmed, review)

    if not apply_mode:
        print('\nℹ️  DRY-RUN — ไม่มีการเขียนไฟล์. รันซ้ำด้วย --apply เพื่อแก้จริง')
        return

    if not confirmed:
        print('\n✅ ไม่มี split ที่ยืนยันได้ -> ไม่ต้องแก้ ไม่สร้าง backup')
        return

    backup_path, changed, counts = apply_corrections(args.file, confirmed)
    print(f'\n💾 BACKUP : {backup_path}')
    print(f'✏️  แก้ไป {changed:,} แถว ใน {len(counts)} ticker:')
    for t in sorted(counts):
        print(f'     {t:<7} {counts[t]:,} แถว')
    print(f'💾 เขียนทับ: {args.file}')
    print('\n🎉 DONE')


if __name__ == '__main__':
    main()
