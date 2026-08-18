import json, os, time
from datetime import datetime, timedelta, timezone
import requests

ROOT = os.path.dirname(os.path.dirname(__file__))
STOCKS_PATH = os.path.join(ROOT, 'stocks.json')
HISTORY_PATH = os.path.join(ROOT, 'stock_history.json')
TZ = timezone(timedelta(hours=8))
S = requests.Session()
S.headers.update({'User-Agent':'Mozilla/5.0 TaiwanStockDashboard/1.0'})


def jget(url, params=None, timeout=30):
    r = S.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def num(v):
    try:
        if v is None: return None
        s = str(v).replace(',', '').replace('--','').strip()
        x = float(s)
        return x if x == x else None
    except Exception:
        return None


def twse_current():
    quotes = jget('https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL')
    pe = jget('https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL')
    pe_map = {str(x.get('Code','')).strip(): num(x.get('PEratio')) for x in pe}
    out = {}
    for x in quotes:
        code = str(x.get('Code','')).strip()
        price = num(x.get('ClosingPrice'))
        if not code or price is None or price <= 0: continue
        p = pe_map.get(code)
        eps = (price / p) if p and p > 0 else None
        out[code] = {'code':code,'name':x.get('Name') or code,'market':'TWSE','price':price,'pe':p,'eps':eps}
    return out


def twse_daily_all(d):
    data = jget('https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX', {
        'date': d.strftime('%Y%m%d'), 'type':'ALLBUT0999', 'response':'json'
    })
    rows = {}
    for t in data.get('tables', []):
        fields = t.get('fields') or []
        if '證券代號' in fields and '收盤價' in fields:
            ci, pi = fields.index('證券代號'), fields.index('收盤價')
            ni = fields.index('證券名稱') if '證券名稱' in fields else None
            for r in t.get('data', []):
                try:
                    c = str(r[ci]).strip()
                    p = num(r[pi])
                    if c and p and p > 0:
                        rows[c] = {'price':p, 'name': (r[ni] if ni is not None else c)}
                except Exception:
                    pass
            break
    return rows


def load_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                x = json.load(f)
                if isinstance(x, dict) and 'days' in x: return x
        except Exception:
            pass
    return {'days': []}


def save_json(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def ensure_60_days(hist):
    known = {x.get('date') for x in hist['days']}
    today = datetime.now(TZ).date()
    # Bootstrap only when history is short. One request per calendar day, stop at 60 trading days.
    need = max(0, 60 - len(hist['days']))
    if need:
        d = today
        scanned = 0
        while len(hist['days']) < 60 and scanned < 130:
            ds = d.isoformat()
            if ds not in known and d.weekday() < 5:
                try:
                    rows = twse_daily_all(d)
                    if len(rows) > 300:
                        hist['days'].append({'date':ds,'prices':{k:v['price'] for k,v in rows.items()}})
                        known.add(ds)
                        print('bootstrap', ds, len(rows))
                    time.sleep(0.15)
                except Exception as e:
                    print('skip', ds, e)
            d -= timedelta(days=1)
            scanned += 1
    # Always refresh today's completed session when available.
    ds = today.isoformat()
    try:
        rows = twse_daily_all(today)
        if len(rows) > 300:
            hist['days'] = [x for x in hist['days'] if x.get('date') != ds]
            hist['days'].append({'date':ds,'prices':{k:v['price'] for k,v in rows.items()}})
    except Exception as e:
        print('today history unavailable', e)
    hist['days'] = sorted(hist['days'], key=lambda x:x.get('date',''))[-60:]
    return hist


def build_stocks(current, hist):
    series = {}
    for day in hist.get('days', []):
        for code, price in (day.get('prices') or {}).items():
            series.setdefault(code, []).append(price)
    updated = datetime.now(TZ).strftime('%Y-%m-%d %H:%M')
    out = {'updated': updated, 'source':'TWSE official data', 'count':0, 'stocks':{}}
    ratios = [1.382, 1.20, 1.00, 0.80, 0.618]
    labels = ['昂貴價','合理價(上緣)','合理價(下緣)','便宜價','特價']
    for code, x in current.items():
        arr = [p for p in series.get(code, []) if isinstance(p,(int,float)) and p > 0][-60:]
        avg60 = sum(arr)/len(arr) if arr else None
        eps = x.get('eps')
        base_pe = (avg60/eps) if avg60 and eps and eps > 0 else None
        pe_bands = [base_pe*r for r in ratios] if base_pe else []
        values = [eps*p for p in pe_bands] if eps and pe_bands else []
        out['stocks'][code] = {
            **x,
            'avg60': avg60,
            'historyDays': len(arr),
            'basePE': base_pe,
            'peBands': pe_bands,
            'labels': labels,
            'values': values,
            'modelReady': bool(base_pe and len(arr) >= 20)
        }
    out['count'] = len(out['stocks'])
    return out


def main():
    current = twse_current()
    hist = ensure_60_days(load_history())
    stocks = build_stocks(current, hist)
    save_json(HISTORY_PATH, hist)
    save_json(STOCKS_PATH, stocks)
    print('stocks', stocks['count'], 'history days', len(hist['days']))

if __name__ == '__main__':
    main()
