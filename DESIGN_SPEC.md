# S&P 500 Daily Scanner Dashboard — Design Specification

**Project**: JP Trust Learning S&P 500 Daily Scanner
**Platform**: jptrustlearning.com
**Membership Tiers**: Free, Premier, Platinum
**Last Updated**: 2026-03-31
**Status**: Design Phase

---

## 1. Data Inventory

### 1.1 Core Price Data

| File | Rows | Columns | Freshness | Description |
|------|------|---------|-----------|-------------|
| `input_sp500_daily.csv` | ~1,369,490 | 7 | Daily (2015-01-02 to 2026-03-30) | OHLCV daily prices for all ~500 S&P 500 tickers |
| `input_magnificent7_daily.csv` | ~11,000+ | 7 | Daily (2015-01-02 to 2026-03-30) | OHLCV for AAPL, AMZN, GOOGL, META, MSFT, NVDA, TSLA |
| `input_benchmark_daily.csv` | ~8,000+ | 7 | Daily (2015-01-02 to 2026-03-30) | OHLCV for SPY, QQQ, DIA |

**Columns (all three)**: `Ticker, Date, Open, High, Low, Close, Volume`

### 1.2 Scoring & Screening Data

| File | Rows | Key Columns | Freshness |
|------|------|-------------|-----------|
| `output_combined_score_sp500.csv` | 501 (all S&P 500) | 47 columns | 2026-02-24 |
| `output_momentum_sp500.csv` | 501 | 34 columns | 2026-02-22 |
| `output_screening_largecap_sp500.csv` | ~18 stocks | 24 columns | 2026-02-24 |
| `output_screening_smallcap_russell2000.csv` | ~10 stocks | 23 columns | 2026-02-22 |

#### Combined Score Columns (47 total):
```
Rank, Ticker, News_Score_Raw, News_Score_Norm, News_Tier,
Mom_Score, Mom_Score_Norm, Mom_Tier, Mom_Rank,
Combined_Balanced, Combined_Catalyst, Combined_Trend, Combined_Tier,
Conviction_Tag, In_News_Screening,
Company, Sector, Market_Cap,
Ret_1Y_Pct, Ret_6M_Pct, Ret_3M_Pct, Ret_1M_Pct, Ret_1W_Pct,
RSI_Value, MA50, MA200, Price, Golden_Cross, Volatility_Pct,
D1_ReturnRank, D2_VolumeRank, D3_RSI, D4_MA, D5_Volatility,
Penalty_Total, Warning_Flags, Signals,
Catalyst, Has_Deal, Deal_Value, Deal_Partner, Upside_Pct,
Top_Sources, News_Max_Score, Mom_Min_Score, Mom_Max_Score, As_Of_Running
```

#### Momentum Score Columns (34 total):
```
Rank, Ticker, Net_Score_Avg, Gross_Score_Avg,
Net_Score_BD1, Net_Score_BD2, Score_Delta, Tier,
D1_ReturnRank, D2_VolumeRank, D3_RSI, D4_MA, D5_Volatility,
WP_Return_Pct, WP_Volume_Pct,
Ret_1Y_Pct, Ret_6M_Pct, Ret_3M_Pct, Ret_1M_Pct, Ret_1W_Pct,
RSI_Value, MA50, MA200, Price, Golden_Cross, Volatility_Pct,
Penalty_Total, Penalty_Reversal, Penalty_DeathCross, Warning_Flags,
News_Top20, Base_Date_1, Base_Date_2, As_Of_Running
```

#### Screening (Large Cap) Columns:
```
Rank, Symbol, Company, Sector, Market_Cap_Category, Final_Score,
Base_Score, Diversity_Bonus, Catalyst_Bonus, Tier,
Raw_Mentions, Unique_Sources, Unique_Signals, Signals, Top_Sources,
Upside_Pct, Catalyst, Has_Deal, Deal_Value, Deal_Partner,
Regulatory_Status, Screening_Start_Date, Screening_End_Date, As_Of_Running
```

### 1.3 Fundamental Data

| File | Format | Content |
|------|--------|---------|
| `fundamentals/ratios_current.csv` | 1 row per ticker | Trailing P/E, Forward P/E, P/B, ROE, ROA, Debt/Equity, Current Ratio, Quick Ratio, Profit Margin, Operating Margin, Gross Margin, Revenue Growth, Earnings Growth, Trailing EPS, Forward EPS, Market Cap, Enterprise Value, Dividend Yield, Payout Ratio, Beta, Sector, Industry, Most Recent Quarter, Earnings Date |
| `fundamentals/ratios_annual.csv` | 1 row per ticker | Same as above minus quarter-specific fields |
| `fundamentals/ratios_quarterly.csv` | 1 row per ticker | Same structure |
| `fundamentals/income_quarterly.csv` | Ticker/Date/Metric/Value | Basic EPS, Diluted EPS, EBITDA, Gross Profit, Net Income, Operating Income, R&D, Total Expenses, Cost of Revenue |
| `fundamentals/income_annual.csv` | Ticker/Date/Metric/Value | Same metrics, annual |
| `fundamentals/balance_quarterly.csv` | Ticker/Date/Metric/Value | Cash, Current Assets, Current Liabilities, Long Term Debt, Net Debt, Stockholders Equity, Total Assets, Total Debt, Total Liabilities |
| `fundamentals/balance_annual.csv` | Ticker/Date/Metric/Value | Same metrics, annual |
| `fundamentals/cashflow_quarterly.csv` | Ticker/Date/Metric/Value | CapEx, Cash Dividends Paid, Financing CF, Free Cash Flow |
| `fundamentals/cashflow_annual.csv` | Ticker/Date/Metric/Value | Same metrics, annual |
| `fundamentals/last_run_summary.json` | JSON | Last run: 2026-03-20, 1 ticker processed |

**Note**: Fundamentals currently contain data only for AAPL. Needs expansion to all S&P 500 tickers. For MVP, use `ratios_current.csv` columns where available and mark others as "coming soon."

### 1.4 Company Profiles

| File | Rows | Content |
|------|------|---------|
| `all_profiles.csv` | 71 companies | Ticker, Company, Sector, Industry, Brief_Overview (Thai), Detailed_Profile (Thai) |
| `profiles/profile_*.csv` | ~79 individual files | Same format, one file per ticker |

**Key Feature**: Profiles are written entirely in Thai language with detailed investment analysis, including revenue figures, growth rates, competitive analysis, and risk factors.

### 1.5 Existing Dashboard

| File | Description |
|------|-------------|
| `CombinedScore_Dashboard.html` | 800-line single-file HTML dashboard with Chart.js |

**Existing dashboard features**:
- Dark theme (navy/gold color scheme)
- Score Weight slider (News vs Momentum balance)
- Preset buttons: Catalyst-First, Balanced, Trend-First
- Stats grid with summary cards
- Scatter chart: News Score vs Momentum Score
- Tier distribution donut chart
- Filterable stock table with tier badges (Platinum/Gold/Silver/Bronze/Monitor)
- Conviction tags: Double Strong, News Only, Hidden Gem, Momentum Only, Double Weak
- Search box, tier filters, pagination
- Detail overlay with tabs showing score breakdown + company profile
- Loads data from GitHub raw CSV via fetch()
- Mobile responsive

### 1.6 Available Sectors

```
Consumer Discretionary, Consumer Staples, Energy, Financials,
Health Care, Industrials, Information Technology, Materials,
Real Estate, Utilities
```

### 1.7 Tier Distributions

| Combined Tier | Count |
|---------------|-------|
| Platinum | 3 |
| Gold | 4 |
| Silver | 32 |
| Bronze | 262 |
| Monitor | 200 |

| Conviction Tag | Count |
|----------------|-------|
| Momentum Only | 152 |
| Double Weak | 105 |
| Double Strong | 6 |
| News Only | 4 |
| (none) | 234 |

### 1.8 Market Cap Categories

- Mega Cap
- Large Cap

---

## 2. Feature List by Membership Tier

### 2.1 Free Tier (Hook & Educate)

Goal: Show enough value to demonstrate expertise; create desire for premium features.

| Feature | Data Source | Description |
|---------|------------|-------------|
| Daily Price Table | `input_sp500_daily.csv` | Ticker, Company Name, Price, Change%, Volume (latest day) |
| Sector Filter | `all_profiles.csv` / `output_combined_score_sp500.csv` | Dropdown: 10 GICS sectors |
| Ticker Search | All | Search by ticker symbol or company name |
| Basic Sort | Price data | Sort by Price, Change%, Volume |
| Magnificent 7 Summary | `input_magnificent7_daily.csv` | Mini dashboard card showing Mag7 daily performance |
| Market Overview | `input_benchmark_daily.csv` | SPY, QQQ, DIA performance bar |
| Combined Tier Badge | `output_combined_score_sp500.csv` | Show tier (Platinum/Gold/Silver/Bronze/Monitor) as colored badge — visible but not explained |
| Top 5 Movers | `input_sp500_daily.csv` | Top 5 gainers and losers of the day |
| Sector Heatmap (simplified) | Price data + sectors | Simple color-coded sector performance grid |

### 2.2 Premier Tier (Blurred/Locked — visible but inaccessible)

| Feature | Data Source | Description |
|---------|------------|-------------|
| Combined Score | `output_combined_score_sp500.csv` | Combined_Balanced, Combined_Catalyst, Combined_Trend scores |
| Momentum Score | `output_momentum_sp500.csv` | Net_Score_Avg with tier and dimensional breakdown |
| News Score | `output_combined_score_sp500.csv` | News_Score_Raw, News_Score_Norm, News_Tier |
| Signal Indicators | `output_combined_score_sp500.csv` | Signals column (S1-S8) decoded with Thai explanations |
| Conviction Tags | `output_combined_score_sp500.csv` | Double Strong, News Only, Momentum Only, Hidden Gem, Double Weak |
| Return Periods | Both score files | Ret_1Y, Ret_6M, Ret_3M, Ret_1M, Ret_1W with color coding |
| Technical Indicators | Both score files | RSI_Value, MA50, MA200, Golden_Cross, Volatility_Pct |
| Warning Flags | Both score files | Death Cross, Reversal warnings with Thai explanations |
| Score Weight Slider | `output_combined_score_sp500.csv` | Adjustable News/Momentum weighting (from existing dashboard) |
| Advanced Sorting | All score data | Sort by any score metric |
| Advanced Filters | All score data | Filter by tier, conviction tag, sector, market cap |

### 2.3 Platinum Tier (Blurred/Locked — premium feel)

| Feature | Data Source | Description |
|---------|------------|-------------|
| Fundamental Ratios | `fundamentals/ratios_current.csv` | P/E, P/B, ROE, ROA, Debt/Equity, Margins, Dividend Yield, Beta |
| Scoring Cards | Combined + Momentum data | Visual cards showing D1-D5 dimensional scores with color-coded ratings and Thai explanations |
| Deal & Catalyst Info | `output_screening_largecap_sp500.csv` | Has_Deal, Deal_Value, Deal_Partner, Catalyst descriptions |
| Company Profiles (Thai) | `all_profiles.csv` | Full Brief_Overview + Detailed_Profile in Thai |
| Upside Potential | Screening data | Upside_Pct from analyst estimates |
| Source Attribution | Screening data | Top_Sources (Morgan Stanley, Goldman Sachs, etc.) |
| Scatter Plot Analysis | Combined score data | Interactive News vs Momentum scatter chart |
| Detailed Stock Overlay | All data combined | Full stock detail popup with all metrics + profile |
| Export Watchlist | All data | CSV download of filtered results |

---

## 3. Data Mapping — Feature to Data Source

```
Feature                    → Primary File                          → Key Columns
─────────────────────────────────────────────────────────────────────────────────
Price & Change%            → input_sp500_daily.csv                 → Close, (calc Change%)
Volume                     → input_sp500_daily.csv                 → Volume
Company Name               → output_combined_score_sp500.csv       → Company
                           → all_profiles.csv                      → Company
Sector                     → output_combined_score_sp500.csv       → Sector
                           → all_profiles.csv                      → Sector, Industry
Market Cap Category        → output_combined_score_sp500.csv       → Market_Cap
Combined Score             → output_combined_score_sp500.csv       → Combined_Balanced/Catalyst/Trend
Combined Tier              → output_combined_score_sp500.csv       → Combined_Tier
News Score                 → output_combined_score_sp500.csv       → News_Score_Raw, News_Score_Norm, News_Tier
Momentum Score             → output_momentum_sp500.csv             → Net_Score_Avg, Tier
Momentum Dimensions        → output_momentum_sp500.csv             → D1-D5, WP_Return_Pct, WP_Volume_Pct
Return Periods             → output_combined_score_sp500.csv       → Ret_1Y/6M/3M/1M/1W_Pct
                           → output_momentum_sp500.csv             → Same
RSI                        → output_combined_score_sp500.csv       → RSI_Value
Moving Averages            → output_combined_score_sp500.csv       → MA50, MA200, Golden_Cross
Volatility                 → output_combined_score_sp500.csv       → Volatility_Pct
Signals                    → output_combined_score_sp500.csv       → Signals (S1-S8)
Conviction Tag             → output_combined_score_sp500.csv       → Conviction_Tag
Warnings                   → output_combined_score_sp500.csv       → Warning_Flags, Penalty_Total
                           → output_momentum_sp500.csv             → Penalty_Reversal, Penalty_DeathCross
Catalyst / Deals           → output_screening_largecap_sp500.csv   → Catalyst, Has_Deal, Deal_Value, Deal_Partner
                           → output_combined_score_sp500.csv       → Same columns
Upside %                   → output_screening_largecap_sp500.csv   → Upside_Pct
Analyst Sources            → output_screening_largecap_sp500.csv   → Top_Sources
P/E, P/B, ROE, etc.       → fundamentals/ratios_current.csv       → All ratio columns
Dividend Yield             → fundamentals/ratios_current.csv       → Dividend_Yield, Payout_Ratio
Beta                       → fundamentals/ratios_current.csv       → Beta
Company Profile (Thai)     → all_profiles.csv                      → Brief_Overview, Detailed_Profile
Mag7 Performance           → input_magnificent7_daily.csv          → Close, Volume
Benchmark Performance      → input_benchmark_daily.csv             → Close (SPY, QQQ, DIA)
```

---

## 4. Layout Wireframe (Text-Based)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │  [JP TRUST LEARNING Logo - top right]                              │ │
│ │                                                                     │ │
│ │              S&P 500 DAILY SCANNER                                 │ │
│ │          สแกนหุ้น S&P 500 รายวัน                                    │ │
│ │     ──── ✦ animated gold divider ✦ ────                            │ │
│ │          อัปเดตล่าสุด: 30 มี.ค. 2026                                │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─ MARKET OVERVIEW BAR ────────────────────────────────────────────────┐│
│ │  SPY: $631.97 (-0.34%)  │  QQQ: $XXX.XX (+X.XX%)  │  DIA: $XXX.XX │ │
│ │  ─────────────────────────────────────────────────────────────────── │ │
│ │  Magnificent 7:  AAPL ▲1.2%  NVDA ▼0.8%  MSFT ▲0.3%  ...         │ │
│ └──────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│ ┌─ TOP MOVERS CARDS ──────────────────────────────────────────────────┐│
│ │  🟢 Top 5 Gainers          │  🔴 Top 5 Losers                      │ │
│ │  TICKER +X.XX%  $Price     │  TICKER -X.XX%  $Price                │ │
│ │  TICKER +X.XX%  $Price     │  TICKER -X.XX%  $Price                │ │
│ │  ...                        │  ...                                  │ │
│ └──────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│ ┌─ FILTER BAR ────────────────────────────────────────────────────────┐│
│ │  [🔍 ค้นหาหุ้น...]  [Sector ▼]  [Sort By ▼]  [Tier ▼ 🔒]         │ │
│ │  All(500) | Technology | Healthcare | Financials | Energy | ...     │ │
│ └──────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│ ┌─ MAIN STOCK TABLE ──────────────────────────────────────────────────┐│
│ │                                                                      │ │
│ │  FREE COLUMNS              │  PREMIER (blurred)    │ PLATINUM (blur)│ │
│ │  ─────────────────────────  │  ──────────────────   │ ──────────────│ │
│ │  #  Ticker  Price  Chg%    │  Combined  Momentum   │ P/E  Div%    │ │
│ │     Company Volume Tier    │  News Scr  Signals    │ ROE  Beta    │ │
│ │                             │  Ret_1M%   RSI       │ Profile      │ │
│ │  ─────────────────────────  │  ──────────────────   │ ──────────────│ │
│ │  1  NVDA    $189.82 +1.5%  │  ██████  ██████████   │ ████  ████   │ │
│ │     NVIDIA  160M    Plat   │  ████    ██████████   │ ████  ████   │ │
│ │  2  MU      $428.17 +3.4%  │  ██████  ██████████   │ ████  ████   │ │
│ │     Micron  XXM     Plat   │  ████    ██████████   │ ████  ████   │ │
│ │  ...                        │                       │              │ │
│ │                             │                       │              │ │
│ │  ┌─────────────────────────────────────────────────────────────┐   │ │
│ │  │  🔒 ปลดล็อกข้อมูลทั้งหมด — สมัครสมาชิก Premier/Platinum     │   │ │
│ │  │     [สมัครสมาชิก →]  jptrustlearning.com                     │   │ │
│ │  └─────────────────────────────────────────────────────────────┘   │ │
│ │                                                                      │ │
│ │  [◄ Prev]  Page 1 of 25  [Next ►]                                 │ │
│ └──────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│ ┌─ SECTOR HEATMAP (Free — simplified) ────────────────────────────────┐│
│ │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │ │
│ │  │ Technology │ │ Healthcare │ │ Financials │ │  Energy    │       │ │
│ │  │   +1.2%    │ │   -0.3%    │ │   +0.8%    │ │   +2.1%    │       │ │
│ │  │  ██ green  │ │  ██ red    │ │  ██ green  │ │  ██ green  │       │ │
│ │  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │ │
│ │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │ │
│ │  │ Industrials│ │ Materials  │ │ Con. Disc. │ │ Con.Staples│       │ │
│ │  │   +0.5%    │ │   -0.1%    │ │   +0.3%    │ │   +0.2%    │       │ │
│ │  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │ │
│ │  ┌────────────┐ ┌────────────┐                                      │ │
│ │  │ Real Estate│ │ Utilities  │                                      │ │
│ │  │   -0.7%    │ │   +0.4%    │                                      │ │
│ │  └────────────┘ └────────────┘                                      │ │
│ └──────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│ ┌─ SCORING CARDS (Blurred/Locked — Platinum) ─────────────────────────┐│
│ │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                │ │
│ │  │  🔒 BLURRED  │ │  🔒 BLURRED  │ │  🔒 BLURRED  │                │ │
│ │  │  D1: Return  │ │  D2: Volume  │ │  D3: RSI     │                │ │
│ │  │  Score: ████  │ │  Score: ████  │ │  Score: ████  │                │ │
│ │  │  ████████████ │ │  ████████████ │ │  ████████████ │                │ │
│ │  └──────────────┘ └──────────────┘ └──────────────┘                │ │
│ │  ┌──────────────┐ ┌──────────────┐                                  │ │
│ │  │  🔒 BLURRED  │ │  🔒 BLURRED  │    [🔒 สมัครสมาชิก Platinum]    │ │
│ │  │  D4: MA      │ │  D5: Volatil │                                  │ │
│ │  └──────────────┘ └──────────────┘                                  │ │
│ └──────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│ ┌─ FOOTER ────────────────────────────────────────────────────────────┐│
│ │  JP TRUST LEARNING | jptrustlearning.com                            │ │
│ │  ข้อมูลนี้ไม่ใช่คำแนะนำในการลงทุน (Disclaimer in Thai)               │ │
│ │  อัปเดตล่าสุด: 30 มี.ค. 2026 | แหล่งข้อมูล: Yahoo Finance, etc.   │ │
│ └──────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Mobile Layout Adaptations

- Single-column stack for all sections
- Filter bar collapses to horizontal scroll or dropdown modal
- Table shows only Ticker, Price, Change% on mobile; horizontal scroll for more
- Heatmap becomes 2-column grid
- Scoring cards stack vertically
- CTA banner becomes sticky bottom bar on mobile

---

## 5. Competitive Differentiation

### 5.1 Competitor Analysis

#### Finviz
- **Strengths**: Best-in-class heatmap visualization; 60+ free filters; fast visual scanning; sector/industry maps; real-time data (Elite)
- **Weaknesses**: UI deteriorating with updates; aggressive upselling; 15-20 min delayed data on free tier; limited charting; steep learning curve for beginners; English only
- **What they lack**: Educational explanations; multi-dimensional scoring; Thai language; combined news + momentum scoring

#### TradingView
- **Strengths**: 160 screening criteria; 150+ global exchanges; 8,000+ US stocks; tight chart integration; community ecosystem; Pine Script extensibility
- **Weaknesses**: Busy interface; requires Pine Script for custom strategies; weak on fundamental modeling; expensive premium; English-centric
- **What they lack**: Simplified scoring for beginners; Thai language; news-based catalyst scoring; educational tooltips

#### StockAnalysis
- **Strengths**: 299 indicators; fast UI; "Yahoo Finance but better"; excellent free tier; real-time data; clean design
- **Weaknesses**: Limited analytical tools beyond screening; no integrated scoring system; no educational content
- **What they lack**: Combined scoring methodology; Thai language; investment education integration; visual scoring cards

#### Yahoo Finance
- **Strengths**: Massive brand recognition; comprehensive data; free access; portfolio tracking; news integration
- **Weaknesses**: Slow/buggy interface; limited screener filters; no backtesting; delayed data; regional limitations; cluttered with ads
- **What they lack**: Scoring systems; Thai language; educational context; catalyst/deal tracking; momentum analysis

#### Barchart
- **Strengths**: 150+ data points; pre-built screeners (bullish MAs, breakouts, candlestick patterns); email alerts for premium; clean UI
- **Weaknesses**: Many features paywalled; limited free tier; no educational content; English only
- **What they lack**: Combined scoring; Thai language; catalyst/news integration; educational tooltips

#### Wisesheets
- **Strengths**: Spreadsheet integration (Excel/Google Sheets); 20 years historical depth; custom formulas; great for modeling
- **Weaknesses**: Requires spreadsheet knowledge; not a visual dashboard; no real-time screening; niche audience
- **What they lack**: Visual dashboard; Thai language; scoring cards; beginner-friendly interface

### 5.2 Our Unique Advantages

| Advantage | Detail |
|-----------|--------|
| **1. All in Thai (ทั้งหมดเป็นภาษาไทย)** | NO competitor offers Thai-language S&P 500 analysis. Every label, tooltip, description, and company profile in Thai. Unique in the market. |
| **2. Educational Tooltips** | Every metric has a Thai-language tooltip explaining what it means and why it matters. Competitors assume financial literacy. |
| **3. Combined Scoring System** | Proprietary News + Momentum dual-axis scoring that no competitor offers. 5-dimensional momentum breakdown (Return, Volume, RSI, MA, Volatility) is unique. |
| **4. Conviction Tags** | "Double Strong", "Hidden Gem", "Momentum Only" etc. — plain-language signal labels that beginners can understand instantly. |
| **5. Catalyst & Deal Tracking** | Active M&A deals with values, partners, and regulatory status. Most screeners only show price/fundamental data. |
| **6. Thai Company Profiles** | 71+ detailed company profiles written in Thai with investment context — nowhere else available. |
| **7. Designed for Thai Investors** | Timezone, cultural context, educational approach all tailored for Thai retail investors learning US markets. |

---

## 6. "Mass Appeal" Design Principles

### 6.1 Usable in 10 Seconds

- **Instant comprehension**: On page load, user sees Market Overview (SPY/QQQ/DIA), Top Movers, and a clean table
- **No registration wall**: Free tier is fully usable without sign-up
- **Color-coded everything**: Green = positive, Red = negative, Gold = highlighted/premium
- **Tier badges visible**: Even free users see Platinum/Gold/Silver badges, creating curiosity
- **Thai-first**: All UI text in Thai; English only for ticker symbols and standard financial terms

### 6.2 Thai Language Throughout

All UI elements in Thai:
```
"ค้นหาหุ้น..." (Search stocks...)
"กลุ่มอุตสาหกรรม" (Sector)
"เรียงตาม" (Sort by)
"ราคา" (Price)
"เปลี่ยนแปลง" (Change)
"ปริมาณซื้อขาย" (Volume)
"คะแนนรวม" (Combined Score)
"โมเมนตัม" (Momentum)
"สัญญาณ" (Signals)
"สมัครสมาชิก" (Subscribe/Sign up)
"ปลดล็อก" (Unlock)
"ดูเพิ่มเติม" (See more)
"หุ้นขึ้นมากที่สุด" (Top Gainers)
"หุ้นลงมากที่สุด" (Top Losers)
```

### 6.3 Mobile-First Responsive Design

- Breakpoints: 320px (mobile), 768px (tablet), 1024px (desktop), 1500px (max-width)
- Touch-friendly: minimum 44px tap targets
- Swipe-friendly table with horizontal scroll indicators
- Sticky header on scroll
- Bottom CTA bar on mobile for subscription

### 6.4 Educational Tooltips

Every premium metric gets a tooltip (shown on hover/tap) in Thai:
```
RSI (Relative Strength Index):
"ดัชนีความแข็งแกร่งสัมพัทธ์ — วัดว่าหุ้นถูก overbought (>70) หรือ oversold (<30)
ค่าสูง = อาจมีแรงขายออกมาเร็วๆนี้, ค่าต่ำ = อาจมีแรงซื้อเข้ามา"

Golden Cross:
"สัญญาณทองคำ — เกิดเมื่อเส้น MA50 ตัดขึ้นเหนือ MA200
เป็นสัญญาณเชิงบวกที่นักลงทุนสถาบันจับตาดู"

P/E Ratio:
"อัตราส่วนราคาต่อกำไร — บอกว่าคุณจ่ายกี่บาทต่อกำไร 1 บาท
ค่าสูง = ตลาดคาดหวังการเติบโตสูง, ค่าต่ำ = อาจเป็นหุ้นราคาถูก"
```

---

## 7. "Differentiation" Features

### 7.1 Sector Heatmap

- Grid of 10 sectors showing daily performance
- Color intensity maps to magnitude of change (deeper green = bigger gain, deeper red = bigger loss)
- Free tier: shows sector-level performance only
- Premium: click to drill into individual stocks within sector

### 7.2 Scoring Cards (Platinum)

Five dimensional score cards based on existing D1-D5 system:
```
┌─────────────────────────────────────────────┐
│  D1: Return Rank        ████████████░░  18/20  │
│  ผลตอบแทนเทียบกับตลาด                          │
│  [Tooltip: วัดผลตอบแทนของหุ้นเทียบกับหุ้นอื่นๆ]  │
├─────────────────────────────────────────────┤
│  D2: Volume Rank        ██████████████░  19/20  │
│  ปริมาณซื้อขายเทียบกับค่าเฉลี่ย                    │
├─────────────────────────────────────────────┤
│  D3: RSI Score          ████████████████  20/20  │
│  ดัชนี RSI อยู่ในโซนที่เหมาะสม                     │
├─────────────────────────────────────────────┤
│  D4: Moving Average     ████████████████  20/20  │
│  เทรนด์เส้นค่าเฉลี่ยเคลื่อนที่                      │
├─────────────────────────────────────────────┤
│  D5: Volatility         ██████████░░░░░░  14/20  │
│  ระดับความผันผวนของราคา                          │
└─────────────────────────────────────────────┘
```

Color coding: 18-20 = emerald green, 14-17 = gold, 10-13 = orange, 0-9 = red

### 7.3 Signal Indicators

Decode the existing S1-S8 signals into Thai Buy/Hold/Watch badges:

| Signal | Meaning | Thai Label | Badge Color |
|--------|---------|------------|-------------|
| S1 | Zacks #1 Rank / Strong Buy | ซื้อเข้มข้น | Emerald |
| S2 | Undervalued (Simply Wall St) | ราคาต่ำกว่ามูลค่า | Blue |
| S3 | Revenue Beat | รายได้เกินคาด | Emerald |
| S4 | Momentum Leader | ผู้นำโมเมนตัม | Purple |
| S5 | Institutional Pick | สถาบันเลือก | Gold |
| S6 | Earnings Upgrade | ปรับประมาณการขึ้น | Emerald |
| S7 | M&A / Catalyst Event | มีดีลควบรวม/เหตุการณ์สำคัญ | Orange |
| S8 | Multiple Source Consensus | หลายแหล่งเห็นตรงกัน | Gold |

### 7.4 Thai-Language Educational Tooltips

- Every column header has a `?` icon that opens a tooltip
- Tooltips explain the metric in simple Thai
- Include practical examples: "P/E ของ NVDA อยู่ที่ 65 หมายความว่า..."
- Educational approach differentiates from all competitors

### 7.5 Premium Blur + Lock + CTA

```css
/* Blur effect for locked columns */
.premium-locked {
  filter: blur(6px);
  user-select: none;
  pointer-events: none;
  position: relative;
}
.premium-locked::after {
  content: '🔒';
  position: absolute;
  /* centered lock icon */
}
```

- Lock icon (🔒) overlaid on blurred content
- "สมัครสมาชิก" (Subscribe) button with gold styling
- CTA links to jptrustlearning.com membership page
- Blur is applied via CSS only (data not sent to client for locked tiers in production; for static HTML MVP, blur is visual only)

---

## 8. "Member Attraction" Strategy

### 8.1 Free Shows Enough to Hook

- User sees a clean, professional dashboard — better than anything available in Thai
- Daily prices, top movers, sector heatmap are fully functional
- Tier badges (Platinum/Gold/Silver) are visible — user thinks "I want to know WHY this stock is Platinum"
- The blurred columns create curiosity — "What's that score? What do those signals mean?"

### 8.2 Premium Features Visible but Locked

- Combined Score, Momentum Score columns are visible but blurred
- Scoring cards section is visible with lock overlay
- Signal badges show count but not detail (e.g., "5 สัญญาณ" but signals are blurred)
- Company profiles show first 2 lines, then fade to blur
- A gentle, non-aggressive prompt: not a popup wall, but an inline CTA within the table area

### 8.3 Clear CTA Flow

```
User sees blurred column → Hovers/taps → Tooltip: "ข้อมูลสำหรับสมาชิก Premier"
→ Click "สมัครสมาชิก" → Redirects to jptrustlearning.com/membership
```

CTA Button styles:
- Premier: Gold outline button — "สมัคร Premier →"
- Platinum: Solid gold button — "สมัคร Platinum →"
- Both include the gold accent color (#D4AF37)

### 8.4 Periodic Teaser

- Once per session, show a "Stock of the Day" card with FULL premium data unlocked for ONE stock
- This lets free users experience the quality of premium data
- Rotates daily from top-ranked stocks (Platinum/Gold tier)

---

## 9. What We're NOT Building (and Why)

| NOT Building | Reason |
|-------------|--------|
| **Real-time streaming prices** | Our data updates daily via GitHub Actions. Real-time would require WebSocket infrastructure and paid data feeds. Daily scanner is sufficient for our educational audience. |
| **Trading execution / broker integration** | We are an education platform, not a brokerage. Adding trading creates regulatory complexity (SEC, Thai SEC). |
| **Custom screener builder** | Complexity would overwhelm our target audience (Thai learners, not quant traders). Our pre-built scoring system is the value proposition. |
| **Backtesting engine** | Requires significant compute infrastructure. Out of scope for a dashboard. Can be a future Colab notebook feature. |
| **User accounts / login system** | MVP is a static HTML dashboard loaded from GitHub. Authentication would require backend infrastructure. Tier access is managed by which URL/page members can access on jptrustlearning.com. |
| **Portfolio tracker** | Out of scope; would require persistent storage and user accounts. |
| **Historical score comparison** | We only have current snapshots of scores, not historical score series. Would require archiving scores over time. |
| **Options / Derivatives data** | Not in our dataset. Our focus is equity fundamentals + momentum. |
| **Full fundamental financial statements** | Fundamentals data currently only covers AAPL. Until expanded, we show ratios_current only and mark detailed financials as "coming soon." |
| **Pine Script / custom indicators** | We are not TradingView. Our scoring system IS our indicator. |
| **Multi-language toggle** | Thai-only is our differentiation. English speakers have 100+ alternatives. |

---

## 10. Design Theme Specification

### 10.1 Colors

```css
:root {
  /* Background layers */
  --bg-primary: #0a0e27;        /* Dark navy - main background */
  --bg-secondary: #111833;      /* Slightly lighter - cards */
  --bg-tertiary: #1a2040;       /* Card hover / input backgrounds */

  /* Gold accent system */
  --gold-primary: #D4AF37;      /* Primary gold */
  --gold-light: #F5D76E;        /* Light gold for gradients */
  --gold-dim: rgba(212,175,55,.15);  /* Gold background tint */
  --gold-glow: rgba(212,175,55,.3);  /* Gold glow/shadow */

  /* Status colors */
  --emerald: #34D399;           /* Positive / gains / strong */
  --red: #F87171;               /* Negative / losses / weak */
  --blue: #60A5FA;              /* Info / news-related */
  --purple: #A78BFA;            /* Special / hidden gem */
  --orange: #FB923C;            /* Warning / moderate */
  --cyan: #22D3EE;              /* Accent / secondary info */

  /* Text hierarchy */
  --text-primary: #E8E6E1;      /* Main text */
  --text-secondary: #9CA3AF;    /* Secondary text */
  --text-muted: #6B7280;        /* Muted / disabled */

  /* Borders */
  --border-subtle: rgba(255,255,255,.06);
  --border-medium: rgba(255,255,255,.1);
}
```

### 10.2 Typography

```css
/* Thai text */
@import url('https://fonts.googleapis.com/css2?family=Anuphan:wght@300;400;500;600;700&display=swap');

/* Headings */
font-family: 'Anuphan', sans-serif;

/* Body / data */
font-family: 'Anuphan', 'Instrument Sans', sans-serif;

/* Monospace for numbers/tickers */
font-family: 'JetBrains Mono', 'Fira Code', monospace;
```

### 10.3 Animated Gold Divider

```css
.gold-divider {
  height: 2px;
  background: linear-gradient(90deg,
    transparent,
    var(--gold-primary),
    var(--gold-light),
    var(--gold-primary),
    transparent
  );
  background-size: 200% 100%;
  animation: shimmer 3s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
```

### 10.4 JP TRUST LEARNING Logo

- Position: top-right corner of header
- If logo image available: `<img>` tag with max-height 48px
- If no image: text-based "JP TRUST LEARNING" in gold gradient
- On mobile: centered above title

### 10.5 Component Styles

- Cards: `border-radius: 14px`, subtle border, background `--bg-secondary`
- Buttons: `border-radius: 8px`, gold border on hover
- Tables: sticky header, alternating row hover, gold highlight for sorted column
- Badges: pill-shaped (`border-radius: 50px`), color-coded by tier
- Inputs: dark background with gold focus border
- Scrollbars: thin, styled to match theme

---

## 11. Technical Implementation Notes

### 11.1 Architecture

- **Single HTML file** (like existing `CombinedScore_Dashboard.html`)
- **No backend required** — loads CSV data from GitHub raw URLs via `fetch()`
- **Client-side CSV parsing** — use Papa Parse or custom CSV parser
- **Client-side rendering** — vanilla JS, no framework needed
- **Chart.js** for heatmap and any visualizations

### 11.2 Data Loading Strategy

```javascript
// Load from GitHub raw URLs (same pattern as existing dashboard)
const BASE = 'https://raw.githubusercontent.com/{owner}/{repo}/main/';
const FILES = {
  daily:     BASE + 'input_sp500_daily.csv',
  combined:  BASE + 'output_combined_score_sp500.csv',
  momentum:  BASE + 'output_momentum_sp500.csv',
  screening: BASE + 'output_screening_largecap_sp500.csv',
  profiles:  BASE + 'all_profiles.csv',
  mag7:      BASE + 'input_magnificent7_daily.csv',
  benchmark: BASE + 'input_benchmark_daily.csv',
  ratios:    BASE + 'fundamentals/ratios_current.csv',
};
```

**Important**: `input_sp500_daily.csv` is ~63MB. Do NOT load the full file. Strategy:
- For latest price data: load only the last 2 days per ticker (needs a server-side pre-processed file, or use the combined_score file which already has Price column)
- Alternative: Create a lightweight `latest_prices.csv` via GitHub Actions that extracts only the most recent trading day

### 11.3 Tier Access Control (MVP)

For static HTML MVP:
- All data is technically in the HTML/JS
- Premium columns are blurred via CSS
- This is a demo/preview approach
- Production would serve different data payloads per tier via API

### 11.4 Performance Considerations

- Paginate table (20 rows per page, matching existing dashboard)
- Lazy-load charts and scoring cards
- Debounce search/filter inputs
- Use `requestAnimationFrame` for table rendering
- Cache parsed CSV data in memory after first load

---

## 12. File Dependencies Summary

For the Designer_Builder agent to build the dashboard, these files MUST be accessible:

| Priority | File | Purpose | Load Strategy |
|----------|------|---------|---------------|
| Critical | `output_combined_score_sp500.csv` | Main table data: scores, tiers, prices, returns, signals | Full load (~115KB) |
| Critical | `output_momentum_sp500.csv` | Momentum scores and dimensional breakdown | Full load (~105KB) |
| Critical | `all_profiles.csv` | Thai company profiles | Full load (~192KB) |
| High | `output_screening_largecap_sp500.csv` | Catalyst/deal data | Full load (~3KB) |
| High | `input_benchmark_daily.csv` | SPY/QQQ/DIA for market overview | Tail only (last 2 rows per ticker, ~1KB) |
| High | `input_magnificent7_daily.csv` | Mag7 daily performance | Tail only (last 2 rows per ticker, ~1KB) |
| Medium | `fundamentals/ratios_current.csv` | P/E, ROE, Dividend etc. | Full load (~1KB, currently AAPL only) |
| Low | `input_sp500_daily.csv` | Historical prices for daily change calc | DO NOT LOAD (63MB). Use Price from combined_score instead. |

---

*This specification was prepared for the JP Trust Learning S&P 500 Daily Scanner Dashboard project. The Designer_Builder agent should use this document as the single source of truth for building the dashboard.*
