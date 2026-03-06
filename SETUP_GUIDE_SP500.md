# 📈 S&P 500 Daily Data Auto-Update — Setup Guide
## JP Trust Learning

---

## สิ่งที่ได้

| แบบ | รายละเอียด | สถานะ |
|-----|-----------|-------|
| **Google Colab** | กด Run All → ดึงข้อมูล + push GitHub อัตโนมัติ | ✅ พร้อมใช้ |
| **GitHub Actions** | รันทุกวันจันทร์-ศุกร์ 07:00 เวลาไทย อัตโนมัติ | ✅ พร้อมใช้ |

---

## 📁 Output Files

ทุกครั้งที่รัน จะ push **2 ไฟล์**:

| ไฟล์ | หน้าที่ |
|------|--------|
| `input_sp500_daily.csv` | ไฟล์หลักสำหรับ downstream ใช้ต่อ (overwrite ทุกครั้ง) |
| `logs/input_sp500_daily_YYYYMMDD_HHMM.csv` | Backup log เก็บประวัติ (สร้างใหม่ทุกครั้ง) |

**ตัวอย่าง:**
```
jptrustlearning/sp500/
├── input_sp500_daily.csv                    ← ไฟล์หลัก (ล่าสุดเสมอ)
└── logs/
    ├── input_sp500_daily_20250224_0700.csv  ← backup วันนี้
    ├── input_sp500_daily_20250223_0700.csv  ← backup เมื่อวาน
    └── ...
```

---

## 📁 Files ที่เกี่ยวข้อง

| ไฟล์ | อยู่ที่ | หน้าที่ |
|------|--------|--------|
| `scripts/update_sp500_daily.py` | GitHub repo | Python script หลักที่ดึงราคา + merge + save |
| `.github/workflows/update_sp500_prices.yml` | GitHub repo | Workflow file สั่ง GitHub Actions ให้รัน script อัตโนมัติ |
| `SP500_Daily_Updater_AutoPush.ipynb` | Google Colab | Notebook สำหรับรันด้วยมือบน Colab |

**หมายเหตุ:** ไฟล์ `update_sp500_prices.yml` ไม่ได้สร้างอัตโนมัติโดย GitHub — ต้องสร้างเองตามขั้นตอนด้านล่าง

---

## ✅ วิธีใช้ Google Colab (พร้อมใช้เลย)

1. เปิด Google Colab → File → Upload Notebook
2. อัพโหลดไฟล์ `SP500_Daily_Updater_AutoPush.ipynb`
3. กด **Runtime → Run All**
4. ระบบจะถาม PAT Token → กรอก PAT Token ของ repo (ดูจาก Project Instructions)
5. รอจนเสร็จ (~30-60 นาที สำหรับ 500+ หุ้น)

**Flow:**
```
Colab → yfinance (ดึงราคา S&P 500) 
      → merge กับ input_sp500_daily.csv เดิม 
      → git push 2 ไฟล์ → GitHub
```

---

## ⚙️ วิธี Setup GitHub Actions (ทำครั้งเดียว)

### ภาพรวม

GitHub Actions จะรันอัตโนมัติทุกวัน โดยใช้ 2 ไฟล์ทำงานร่วมกัน:

```
GitHub Actions (รันตาม schedule)
  │
  ├── .github/workflows/update_sp500_prices.yml   ← บอก GitHub ว่า "จะรันอะไร เมื่อไหร่"
  │     - ตั้ง schedule (cron)
  │     - install Python + dependencies
  │     - เรียก script
  │     - git commit + push ผลลัพธ์
  │
  └── scripts/update_sp500_daily.py                ← ตัว script จริงที่ทำงาน
        - ดึงรายชื่อ S&P 500 จาก Wikipedia
        - อ่าน input_sp500_daily.csv เดิม
        - ดาวน์โหลดราคาใหม่จาก Yahoo Finance
        - merge + deduplicate + save 2 ไฟล์
```

### ขั้นตอนที่ 1: เพิ่ม Secret `SP500_PAT` ใน GitHub

⚠️ **ต้องทำก่อนเป็นอันดับแรก** — ถ้าไม่มี Secret นี้ workflow จะ fail ทันทีตอน git push เพราะไม่มี token ใช้ authenticate

**Error ที่จะเจอถ้าไม่ทำขั้นตอนนี้:**
```
could not read Username for 'https://github.com': terminal prompts disabled
The process '/usr/bin/git' failed with exit code 128
```

**วิธีทำ:**
1. ไปที่ https://github.com/jptrustlearning/sp500/settings/secrets/actions
2. กด **New repository secret**
3. ช่อง Name ใส่: `SP500_PAT`
4. ช่อง Secret ใส่: PAT Token ของ repo (ดูจาก Project Instructions หรือถาม admin)
5. กด **Add secret**

### ขั้นตอนที่ 2: ตรวจสอบว่า Python script อยู่ใน repo แล้ว

ไฟล์ `scripts/update_sp500_daily.py` ถูก push ไว้ใน repo แล้ว ตรวจสอบได้ที่:
https://github.com/jptrustlearning/sp500/blob/main/scripts/update_sp500_daily.py

ถ้าไม่เจอไฟล์นี้ ให้สั่ง Claude สร้างใหม่ได้

### ขั้นตอนที่ 3: สร้าง Workflow file ผ่าน GitHub UI

⚠️ **ต้องสร้างผ่านหน้าเว็บ GitHub โดยตรง** — ไม่สามารถ push ผ่าน `git push` ได้ เพราะ PAT Token ปัจจุบันไม่มีสิทธิ์ `workflow` (GitHub กำหนดว่าการสร้าง/แก้ไขไฟล์ใน `.github/workflows/` ต้องใช้ token ที่มี scope `workflow` เพิ่มเติม)

**วิธีทำ:**
1. ไปที่ https://github.com/jptrustlearning/sp500
2. กด **Add file → Create new file**
3. ช่องชื่อไฟล์ พิมพ์ทีละส่วน: `.github/` → `workflows/` → `update_sp500_prices.yml`
   (พอพิมพ์ `/` GitHub จะสร้างโฟลเดอร์ให้อัตโนมัติ)
4. ในช่องเนื้อหา วาง YAML ด้านล่างนี้ทั้งหมด:

```yaml
name: Daily S&P 500 Update

on:
  schedule:
    # ทุกวันอังคาร-เสาร์ เวลา 00:00 UTC = 07:00 เวลาไทย
    # (อังคาร-เสาร์ UTC = จันทร์-ศุกร์ ตลาด US ปิดแล้ว)
    - cron: '0 0 * * 2-6'
  workflow_dispatch:
    # กด Run workflow ด้วยมือได้จาก Actions tab

jobs:
  update-prices:
    runs-on: ubuntu-latest
    timeout-minutes: 90

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.SP500_PAT }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install yfinance pandas requests beautifulsoup4

      - name: Run S&P 500 price updater
        run: python scripts/update_sp500_daily.py

      - name: Commit and push
        run: |
          git config user.email "jptrustlearning@users.noreply.github.com"
          git config user.name "JP Trust Learning"
          git add input_sp500_daily.csv logs/
          # Only commit if there are changes
          git diff --cached --quiet || (
            TIMESTAMP=$(date -u +"%Y-%m-%d")
            git commit -m "📈 S&P500 daily update — ${TIMESTAMP}"
            git push
          )
```

5. เลื่อนลงล่าง กด **Commit changes**

### ขั้นตอนที่ 4: ทดสอบ

1. ไปที่ https://github.com/jptrustlearning/sp500 → **Actions** tab
2. จะเห็น workflow ชื่อ **"Daily S&P 500 Update"** ทางซ้าย
3. กด **Run workflow** → เลือก branch `main` → กด **Run workflow** อีกครั้ง
4. รอประมาณ 30-60 นาที → ดู log ว่าสำเร็จหรือไม่

**ถ้าสำเร็จ:** จะเห็น ✅ สีเขียว และมี commit ใหม่ใน repo
**ถ้า fail:** ดู log เพื่อหาสาเหตุ → ดูหัวข้อ Troubleshooting ด้านล่าง

---

## 📅 Schedule

```
Cron: 0 0 * * 2-6
= ทุกวันอังคาร-เสาร์ เวลา 00:00 UTC = 07:00 เวลาไทย
```

**ทำไมเป็นอังคาร-เสาร์?** เพราะตลาด US เปิดวันจันทร์-ศุกร์ ข้อมูลราคาจะพร้อมหลังตลาดปิด ซึ่งตรงกับช่วงเช้าวันถัดไปเวลาไทย (อังคาร-เสาร์)

**หมายเหตุ:** สามารถกด **Run workflow** ด้วยมือได้ทุกเมื่อจาก Actions tab (ไม่ต้องรอ schedule)

---

## 📊 ข้อมูลที่ได้

| Column | Description |
|--------|-------------|
| Ticker | สัญลักษณ์หุ้น (e.g., AAPL, MSFT) |
| Date | วันที่ (YYYY-MM-DD) |
| Open | ราคาเปิด |
| High | ราคาสูงสุด |
| Low | ราคาต่ำสุด |
| Close | ราคาปิด |
| Volume | ปริมาณการซื้อขาย |

---

## 🔄 Downstream Usage

ไฟล์ `input_sp500_daily.csv` พร้อมใช้งานต่อได้ทันที:

```python
import pandas as pd

# อ่านข้อมูลจาก GitHub
url = 'https://raw.githubusercontent.com/jptrustlearning/sp500/main/input_sp500_daily.csv'
df = pd.read_csv(url)

# กรองหุ้นที่ต้องการ
aapl = df[df['Ticker'] == 'AAPL']
```

---

## 🔧 Troubleshooting

### ปัญหา: `could not read Username for 'https://github.com'` / exit code 128
**สาเหตุ:** ยังไม่ได้เพิ่ม Secret `SP500_PAT` หรือ token หมดอายุ
**วิธีแก้:** ไปที่ Settings → Secrets → Actions → เพิ่มหรืออัพเดท `SP500_PAT`

### ปัญหา: Workflow ไม่ขึ้นใน Actions tab
**สาเหตุ:** ไฟล์ `.github/workflows/update_sp500_prices.yml` ยังไม่อยู่ใน repo
**วิธีแก้:** สร้างไฟล์ผ่าน GitHub UI ตามขั้นตอนที่ 3 ด้านบน (ต้องสร้างผ่านเว็บ ไม่ใช่ git push)

### ปัญหา: `refusing to allow a Personal Access Token to create or update workflow`
**สาเหตุ:** PAT Token ไม่มีสิทธิ์ `workflow` จึง push ไฟล์ใน `.github/workflows/` ไม่ได้
**วิธีแก้:** สร้าง workflow file ผ่าน GitHub UI โดยตรง (ตามขั้นตอนที่ 3) หรืออัพเดท PAT Token ที่ github.com/settings/tokens ให้มี scope `workflow`

### ปัญหา: ข้อมูลหาย
**วิธีแก้:** ไปดูในโฟลเดอร์ `logs/` จะมี backup ทุกวันที่รัน

### ปัญหา: Rate limit จาก Yahoo Finance
**วิธีแก้:** รอสักครู่แล้วลองใหม่ — script มี rate limiting + retry อยู่แล้ว (รอ 0.5s ทุก 5 ตัว, retry 3 ครั้งต่อ ticker)

### ปัญหา: Git push failed (อื่นๆ)
**วิธีแก้:** ตรวจสอบว่า PAT Token มีสิทธิ์ `repo` ที่ github.com/settings/tokens

---

## 🔑 Credentials

```
Repository : github.com/jptrustlearning/sp500
Username   : jptrustlearning
Email      : jptrustlearning@users.noreply.github.com
PAT Token  : (ดูจาก Project Instructions — ห้ามเก็บ token ในไฟล์บน GitHub)
Secret Name: SP500_PAT (ใน GitHub Actions)
```

**PAT Token ต้องมี scope:**
- `repo` — สำหรับ read/write repo
- `workflow` — สำหรับ push ไฟล์ `.github/workflows/` (ถ้าจะ push ผ่าน git ไม่ใช่ UI)

---

## 📅 VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| **1.0** | **2026-02-24** | Initial: Colab notebook + GitHub Actions setup guide |
| **1.1** | **2026-03-06** | เพิ่มรายละเอียด: workflow file ต้องสร้างผ่าน GitHub UI, Secret SP500_PAT setup, error messages และ troubleshooting จากปัญหาจริง, อธิบาย file structure ชัดเจนขึ้น |

---

*Created by JP TRUST LEARNING*
*S&P 500 Daily Data Auto-Update — Setup Guide v1.1*
