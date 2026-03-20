# SP500 Fundamental Data Pipeline

ดึงข้อมูล Fundamental ของหุ้น S&P 500 จาก **yfinance** อัตโนมัติรายเดือน

> ⚠️ Pipeline นี้ **แยกจาก** daily OHLCV pipeline — ไม่ยุ่งเกี่ยวกัน

---

## 📁 โครงสร้างไฟล์

```
repo/
├── scripts/
│   └── download_fundamentals.py    ← Python script หลัก
├── .github/workflows/
│   └── monthly_fundamentals.yml    ← GitHub Actions (แยกจาก daily)
└── fundamentals/                   ← Output folder
    ├── income_annual.csv           ← Income Statement (Annual)
    ├── income_quarterly.csv        ← Income Statement (Quarterly)
    ├── balance_annual.csv          ← Balance Sheet (Annual)
    ├── balance_quarterly.csv       ← Balance Sheet (Quarterly)
    ├── cashflow_annual.csv         ← Cash Flow (Annual)
    ├── cashflow_quarterly.csv      ← Cash Flow (Quarterly)
    ├── ratios_current.csv          ← Key Ratios (Snapshot)
    ├── last_run_summary.json       ← สรุปผลการรัน
    └── logs/                       ← Log files
```

## 📊 ข้อมูลที่ดึง

### Income Statement
| Metric | คำอธิบาย |
|--------|----------|
| Total Revenue | รายได้รวม |
| Net Income | กำไรสุทธิ |
| Gross Profit | กำไรขั้นต้น |
| Operating Income | กำไรจากการดำเนินงาน |
| EBITDA | กำไรก่อนดอกเบี้ย ภาษี ค่าเสื่อม |
| Basic EPS / Diluted EPS | กำไรต่อหุ้น |

### Balance Sheet
| Metric | คำอธิบาย |
|--------|----------|
| Total Assets | สินทรัพย์รวม |
| Total Debt | หนี้สินรวม |
| Stockholders Equity | ส่วนของผู้ถือหุ้น |
| Cash And Cash Equivalents | เงินสดและเทียบเท่า |
| Net Debt | หนี้สุทธิ |
| Working Capital | เงินทุนหมุนเวียน |

### Cash Flow
| Metric | คำอธิบาย |
|--------|----------|
| Operating Cash Flow | กระแสเงินสดจากการดำเนินงาน |
| Free Cash Flow | กระแสเงินสดอิสระ |
| Capital Expenditure | เงินลงทุนในสินทรัพย์ |

### Key Ratios (Current Snapshot)
P/E, P/B, PEG, ROE, ROA, Debt/Equity, Current Ratio, Profit Margin, Revenue Growth, Beta, Dividend Yield ฯลฯ

## 📐 รูปแบบ CSV

**Financial Statements** (Long format):
```
Ticker,Date,Metric,Value
AAPL,2024-09-28,Total Revenue,391035000000
AAPL,2024-09-28,Net Income,93736000000
MSFT,2024-06-30,Total Revenue,245122000000
```

**Ratios** (Wide format):
```
Ticker,Trailing P/E,P/B,ROE,Debt/Equity,...
AAPL,33.5,52.1,1.57,151.86,...
MSFT,35.2,12.8,0.37,42.15,...
```

## ⏰ Schedule

- **อัตโนมัติ**: วันที่ 20 ของทุกเดือน เวลา 02:00 UTC
- **Manual trigger**: ได้ใน GitHub Actions → "Run workflow"
  - ระบุ tickers เฉพาะได้ เช่น `AAPL,MSFT,NVDA`

## 🚀 วิธีใช้

### รันใน Local / Google Colab
```bash
pip install yfinance pandas

# ดึงทั้ง S&P 500
python scripts/download_fundamentals.py

# ดึงเฉพาะบางตัว
python scripts/download_fundamentals.py --tickers AAPL,MSFT,NVDA

# ระบุ output directory
python scripts/download_fundamentals.py --output-dir ./my_data
```

### ดึงข้อมูลใน Dashboard (PapaParse)
```javascript
const BASE = "https://raw.githubusercontent.com/jptrustlearning/sp500/main/fundamentals";

// ดึง ratios
const ratios = await fetch(`${BASE}/ratios_current.csv`).then(r => r.text());
Papa.parse(ratios, { header: true, complete: (results) => {
    console.log(results.data);
}});

// ดึง income statement
const income = await fetch(`${BASE}/income_annual.csv`).then(r => r.text());
```

## ⚠️ ข้อจำกัด yfinance (Free)

- ข้อมูล financial statements ย้อนหลัง **4-5 ปี** (annual) / **~5 quarters** (quarterly)
- อาจโดน rate limit ถ้าดึงเร็วเกินไป (script มี delay 0.5s)
- บาง ticker อาจไม่มีข้อมูลครบทุก field
- Ratios เป็น **snapshot ปัจจุบัน** ไม่มี historical
