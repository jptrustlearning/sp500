# 🔒 Boolean Audit Instructions — MANDATORY Before Every CSV Push
## JP TRUST LEARNING — ป้องกัน Boolean Mismatch ระหว่าง CSV ↔ Dashboard

---

## ⚠️ ปัญหาที่เกิดซ้ำ 3 ครั้ง (22-24 Feb 2026)

**Root Cause:** Python สร้าง CSV ด้วยค่า boolean ที่ไม่ตรงกับที่ Dashboard JavaScript คาดหวัง

| ครั้งที่ | วันที่ | ไฟล์ที่มีปัญหา | CSV เขียน | Dashboard เช็ค | ผลลัพธ์ |
|---------|--------|----------------|-----------|---------------|---------|
| 1 | 22 Feb | Gold Momentum | `TRUE` | `=== 'True'` | Golden Cross แสดง No หมด |
| 2 | 23 Feb | Combined Score | `TRUE` | `=== 'True'` | Golden Cross แสดง No หมด |
| 3 | 24 Feb | Combined Score | `TRUE` | `=== 'True'` | Golden Cross แสดง No หมด |

**ทำไมผิดซ้ำ:**
- Python `bool(True)` → pandas เขียน `True` แต่ `.str.upper()` แปลงเป็น `TRUE`
- Dashboard JS ใช้ strict equality `=== 'True'` ไม่ match กับ `TRUE`
- ไม่มี automated check → ผิดซ้ำทุกครั้งที่รัน

---

## 📋 BOOLEAN CONTRACT — กฎตายตัว

### CSV ต้องเขียนค่า boolean ดังนี้:

| Column | ค่าที่ถูกต้อง | ห้ามใช้ |
|--------|-------------|---------|
| `Golden_Cross` | `True` / `False` | ~~TRUE~~ ~~FALSE~~ ~~true~~ ~~false~~ ~~1~~ ~~0~~ |
| `In_News_Screening` | `TRUE` / `FALSE` | ~~True~~ ~~true~~ ~~1~~ ~~0~~ |
| `Has_Deal` | `TRUE` / `FALSE` | ~~True~~ ~~true~~ ~~1~~ ~~0~~ |

### Dashboard ต้องเช็คแบบ case-insensitive:

```javascript
// ✅ ถูก — รับได้ทุก case
String(d.Golden_Cross).toLowerCase() === 'true'
String(d.In_News_Screening).toLowerCase() === 'true'
String(d.Has_Deal).toLowerCase() === 'true'

// ❌ ผิด — strict match จะพังเมื่อ case ไม่ตรง
d.Golden_Cross === 'True'
d.In_News_Screening === 'TRUE'
```

---

## 🛡️ MANDATORY AUDIT PROCESS

### ก่อน `git push` ทุกครั้ง ต้องรัน:

```bash
cd /home/claude/sp500
python3 boolean_audit.py
```

### Audit ตรวจ 2 ส่วน:

**Part 1 — CSV Audit:**
- อ่านทุก CSV ที่จะ push
- ตรวจทุก boolean column ว่าค่าตรงตาม contract
- แสดง value counts ของแต่ละ column
- ❌ FAIL ถ้าเจอค่าที่ไม่ตรง contract

**Part 2 — Dashboard Audit:**
- Scan ทุก `.html` ในร repo
- หา pattern `=== 'True'`, `=== 'TRUE'`, `=== 'False'`, `=== 'FALSE'`
- ❌ FAIL ถ้าเจอ strict boolean comparison (ต้องใช้ `.toLowerCase()`)

### ผลลัพธ์:

```
✅ ALL BOOLEAN CHECKS PASSED — Safe to push
   หรือ
❌ BOOLEAN AUDIT FAILED — ห้าม push จนกว่าจะแก้
```

---

## 🔧 PYTHON SCRIPT — boolean_audit.py

ไฟล์อยู่ที่: `sp500/boolean_audit.py`

รันได้เดี่ยวๆ หรือเรียกจาก script อื่นก่อน push:

```python
import subprocess
result = subprocess.run(['python3', 'boolean_audit.py'], capture_output=True, text=True)
if result.returncode != 0:
    print("❌ AUDIT FAILED — aborting push")
    sys.exit(1)
```

---

## 📐 CHECKLIST สำหรับ Claude (ทุกครั้งที่สร้าง/แก้ CSV)

```
□ 1. Golden_Cross → ใช้ .str.capitalize() ได้ True/False — ห้าม .str.upper()
□ 2. In_News_Screening → ใช้ .map({True: 'TRUE', False: 'FALSE'}) 
□ 3. Has_Deal → ตรวจให้เป็น TRUE/FALSE (ตัวใหญ่)
□ 4. รัน python3 boolean_audit.py ก่อน git push
□ 5. Audit PASSED แล้วเท่านั้นถึง push
```

---

## ⚠️ COMMON PITFALLS — สิ่งที่ต้องระวัง

1. **ห้าม `.str.upper()` กับ Golden_Cross** — Dashboard เดิมเช็ค `'True'` ไม่ใช่ `'TRUE'`
2. **Pandas boolean → string** — `df['col'] = df['col'].astype(bool)` แล้ว `.to_csv()` จะเขียน `True`/`False` ซึ่งอาจไม่ตรงกับ Dashboard
3. **fillna** — `fillna(False)` ได้ Python bool, ต้อง map เป็น string ก่อน save
4. **CSV round-trip** — อ่าน CSV กลับมา boolean กลายเป็น string `'True'` ไม่ใช่ `True` (Python bool)
5. **Dashboard แก้แล้วต้อง push** — ถ้าแก้ HTML ให้ case-insensitive แล้ว ต้อง push HTML ด้วย

---

## 📅 VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial: Boolean contract, audit script, mandatory pre-push check |

---

*Created by JP TRUST LEARNING*
*Boolean Audit Instructions v1.0 — February 2026*
