# -*- coding: utf-8 -*-
"""gen_sector_latest.py — สร้าง sector-latest.json (ไฟล์ย่อสำหรับแถบค้นหาหุ้นบนหน้าแรก public)

พอร์ตตรงจาก compute() ใน pages/sector-rotation.html — ต้องได้ quadrant ตรงกับหน้า dashboard เป๊ะ
ที่มาข้อมูล: sp500/mini_sp500_rotation.csv  (Ticker,Date,Close,Volume)

usage: python3 gen_sector_latest.py <rotation.csv> <out.json>
"""
import csv, json, sys, math
from datetime import date

W_RS, W_MOM, TAIL = 14, 8, 8
NAN = float('nan')

THEMES = [
 ('Mag 7',                  'AAPL MSFT NVDA AMZN GOOGL META TSLA', 'MAGS'),
 ('Semiconductors',         'NVDA AMD AVGO QCOM TXN INTC MRVL ADI NXPI ON MCHP', 'SMH · SOXX'),
 ('Semi Equip & Memory',    'MU AMAT LRCX KLAC WDC STX SNDK TER', 'SMH'),
 ('Software',               'MSFT ORCL CRM ADBE NOW PLTR INTU SNPS CDNS ADSK WDAY IBM', 'IGV · XSW'),
 ('Cybersecurity',          'CRWD PANW FTNT GEN', 'CIBR · HACK · BUG'),
 ('AI Infra & Data Center', 'VRT ANET SMCI DELL ETN GEV CIEN', 'AIQ · DTCR · GRID'),
 ('Fintech & Payments',     'V MA PYPL AXP COF FISV GPN FIS', 'IPAY · FINX'),
 ('Crypto-linked',          'COIN HOOD XYZ', 'IBIT · DAPP'),
 ('Banks & Brokers',        'JPM BAC WFC C GS MS SCHW PNC USB TFC BK', 'KBWB · KBE · IAI'),
 ('Defense',                'LMT RTX NOC GD LHX HWM AXON HII TDG', 'ITA · XAR · PPA'),
 ('Homebuilders',           'DHI LEN PHM NVR MAS BLDR', 'ITB · XHB'),
 ('Travel & Airlines',      'BKNG ABNB MAR HLT DAL UAL LUV RCL CCL NCLH EXPE', 'JETS · PEJ'),
 ('Pharma & Managed Care',  'LLY JNJ MRK ABBV PFE BMY UNH CVS CI ELV HUM CNC MOH ZTS', 'IHE · XLV'),
 ('Biotech Large',          'AMGN GILD VRTX REGN BIIB MRNA INCY', 'IBB · XBI'),
 ('MedTech',                'ISRG SYK MDT BSX EW GEHC ABT DHR TMO IDXX', 'IHI'),
 ('Energy',                 'XOM CVX COP SLB EOG PSX MPC VLO OXY HAL BKR FANG', 'XLE · XOP · OIH'),
 ('Utilities & Power',      'NEE DUK SO VST CEG D AEP EXC SRE PEG NRG', 'XLU · GRID'),
 ('Staples',                'PG KO PEP COST WMT PM MO CL KMB GIS KHC MDLZ', 'XLP'),
 ('REITs',                  'PLD AMT EQIX WELL SPG O PSA CCI DLR VICI', 'XLRE · VNQ'),
 ('Materials',              'LIN SHW APD ECL FCX NUE DOW DD ALB NEM', 'XLB'),
 ('Industrials',            'CAT DE HON GE EMR PH UNP UPS CSX NSC ITW MMM', 'XLI'),
 ('Media & Telecom',        'NFLX DIS CMCSA TMUS VZ T CHTR TTD', 'XLC'),
 ('Consumer & Retail',      'HD LOW NKE MCD SBUX TJX ORLY AZO CMG ROST TGT LULU', 'XLY · XRT'),
 ('Insurance',              'PGR CB TRV AIG ALL MET PRU AFL', 'IAK · KIE'),
]


def iso_key(s):
    y, m, d = (int(x) for x in s.split('-'))
    yy, ww, _ = date(y, m, d).isocalendar()
    return '%d-%d' % (yy, ww)


def week_boundaries(dates):
    b, prev = [], None
    for i, ds in enumerate(dates):
        k = iso_key(ds)
        if k != prev and prev is not None:
            b[-1] = i - 1
        if k != prev:
            b.append(i); prev = k
        else:
            b[-1] = i
    return b


def sma(arr, w, i):
    if i + 1 < w:
        return NAN
    s = 0.0
    for k in range(i - w + 1, i + 1):
        if math.isnan(arr[k]):
            return NAN
        s += arr[k]
    return s / w


def load(path):
    dset, rows = set(), []
    with open(path, newline='', encoding='utf-8') as fh:
        rd = csv.reader(fh)
        next(rd, None)
        for p in rd:
            if len(p) < 4:
                continue
            rows.append(p); dset.add(p[1])
    dates = sorted(dset)
    didx = {d: i for i, d in enumerate(dates)}
    N = len(dates)
    series = {}
    for p in rows:
        s = series.get(p[0])
        if s is None:
            s = ([NAN] * N, [0.0] * N); series[p[0]] = s
        i = didx[p[1]]
        s[0][i] = float(p[2]); s[1][i] = float(p[3] or 0)
    return dates, series


def compact(s):
    c, v = [], []
    for i in range(len(s[0])):
        if not math.isnan(s[0][i]):
            c.append(s[0][i]); v.append(s[1][i])
    return c, v


def ret_n(c, n):
    L = len(c)
    return None if L <= n else (c[L - 1] / c[L - 1 - n] - 1) * 100


def main(src, out):
    dates, series = load(src)
    bidx = week_boundaries(dates)
    W = len(bidx)

    def weekly_of(t):
        s = series.get(t)
        if s is None:
            return None
        o = [NAN] * W; last = NAN; bi = 0
        for i in range(len(s[0])):
            if not math.isnan(s[0][i]):
                last = s[0][i]
            if bi < W and i == bidx[bi]:
                o[bi] = last; bi += 1
        return o

    spy_w = weekly_of('SPY')
    spy_c, _ = compact(series['SPY'])
    spy = {k: ret_n(spy_c, n) for k, n in (('r1d', 1), ('r1m', 21), ('r3m', 63))}

    out_groups, tick_map = [], {}
    for gi, (name, tk, etf) in enumerate(THEMES):
        members = tk.split(' ')
        cps = [(t, compact(series[t])) for t in members if t in series]

        R = {}
        for k, n in (('r1d', 1), ('r1w', 5), ('r1m', 21), ('r3m', 63)):
            vs = [x for x in (ret_n(c, n) for _, (c, _v) in cps) if x is not None]
            R[k] = sum(vs) / len(vs) if vs else None

        ab = []
        for _, (c, _v) in cps:
            if len(c) >= 21:
                ab.append(c[-1] > sum(c[-20:]) / 20)
        breadth = (sum(1 for x in ab if x) / len(ab) * 100) if ab else None

        dv = []
        for _, (c, v) in cps:
            if len(c) >= 20:
                a5 = sum(c[i] * v[i] for i in range(len(c) - 5, len(c))) / 5
                a20 = sum(c[i] * v[i] for i in range(len(c) - 20, len(c))) / 20
                if a20 > 0:
                    dv.append(a5 / a20)
        dvol = sum(dv) / len(dv) if dv else None

        quad, tail = 'lag', None
        wcs = []
        for t in members:
            w = weekly_of(t)
            if not w or math.isnan(w[0]):
                continue
            if sum(1 for x in w if math.isnan(x)) <= 2:
                wcs.append(w)
        if len(wcs) >= 2 and spy_w:
            idx = [NAN] * W
            for i in range(W):
                s, n = 0.0, 0
                for w in wcs:
                    if not math.isnan(w[i]) and not math.isnan(w[0]):
                        s += w[i] / w[0]; n += 1
                idx[i] = s / n if n else NAN
            rs = [100 * idx[i] / spy_w[i] * spy_w[0] for i in range(W)]
            rr = [NAN] * W; rm = [NAN] * W
            for i in range(W):
                m = sma(rs, W_RS, i); rr[i] = NAN if math.isnan(m) else 100 * rs[i] / m
            for i in range(W):
                m = sma(rr, W_MOM, i); rm[i] = NAN if math.isnan(m) else 100 * rr[i] / m
            pts = [(rr[i], rm[i]) for i in range(W) if not math.isnan(rr[i]) and not math.isnan(rm[i])]
            if len(pts) >= 2:
                tail = [[round(x, 3), round(y, 3)] for x, y in pts[-TAIL:]]
                hx, hy = pts[-1]
                quad = ('lead' if hy >= 100 else 'weak') if hx >= 100 else ('improv' if hy >= 100 else 'lag')

        g = {'n': name, 'etf': etf, 'q': quad,
             'r1m': None if R['r1m'] is None else round(R['r1m'], 2),
             'r3m': None if R['r3m'] is None else round(R['r3m'], 2),
             'vs': None if (R['r1m'] is None or spy['r1m'] is None) else round(R['r1m'] - spy['r1m'], 2),
             'breadth': None if breadth is None else round(breadth),
             'dvol': None if dvol is None else round(dvol, 2),
             'tail': tail, 'tk': members}
        out_groups.append(g)
        for t in members:
            tick_map.setdefault(t, []).append(gi)

    ticks = {}
    for t in sorted(tick_map):
        if t not in series:
            continue
        c, _v = compact(series[t])
        spark = c[-20:]
        lo, hi = min(spark), max(spark)
        rng = (hi - lo) or 1.0
        ticks[t] = {
            'g': tick_map[t],
            'd': None if ret_n(c, 1) is None else round(ret_n(c, 1), 2),
            'm': None if ret_n(c, 21) is None else round(ret_n(c, 21), 2),
            'q': None if ret_n(c, 63) is None else round(ret_n(c, 63), 2),
            's': [round((x - lo) / rng * 100) for x in spark],
        }

    doc = {'as_of': dates[-1], 'spy': {k: (None if v is None else round(v, 2)) for k, v in spy.items()},
           'groups': out_groups, 'ticks': ticks}
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(',', ':'))
    print('as_of', doc['as_of'], '| groups', len(out_groups), '| tickers', len(ticks))
    for g in out_groups:
        print('  %-24s %-7s r1m %7s  vs %7s  breadth %3s  dvol %s' %
              (g['n'], g['q'], g['r1m'], g['vs'], g['breadth'], g['dvol']))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
