import json, os, math
from datetime import datetime, timedelta, timezone
import requests

ROOT = os.path.dirname(os.path.dirname(__file__))
STOCKS_PATH = os.path.join(ROOT, 'stocks.json')
HISTORY_PATH = os.path.join(ROOT, 'stock_history.json')
TZ = timezone(timedelta(hours=8))
S = requests.Session()
S.headers.update({'User-Agent':'Mozilla/5.0 TaiwanStockDashboard/3.0'})
MAX_DAYS = 60


def jget(url, timeout=25):
    r = S.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def num(v):
    try:
        if v is None: return None
        s = str(v).replace(',', '').replace('%','').replace('--','').replace('---','').strip()
        if not s: return None
        x = float(s)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def pick(row, aliases):
    if not isinstance(row, dict): return None
    norm = lambda s: str(s).lower().replace(' ','').replace('_','').replace('/','')
    for k, v in row.items():
        kk = norm(k)
        if any(norm(a) == kk or norm(a) in kk for a in aliases):
            if v not in (None, '', '--', '---'): return v
    return None


def twse_current():
    quotes = jget('https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL')
    pe_rows = jget('https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL')
    pe_map = {str(x.get('Code','')).strip(): num(x.get('PEratio')) for x in pe_rows if isinstance(x, dict)}
    out = {}
    for x in quotes if isinstance(quotes, list) else []:
        code = str(x.get('Code','')).strip()
        price = num(x.get('ClosingPrice'))
        if not code or price is None or price <= 0: continue
        pe = pe_map.get(code)
        eps = price / pe if pe and pe > 0 else None
        out[code] = {'code':code,'name':x.get('Name') or code,'market':'TWSE','price':price,'pe':pe,'eps':eps}
    print('TWSE current', len(out))
    return out


def tpex_current():
    quotes = jget('https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes')
    pe_rows = jget('https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis')
    pe_map = {}
    for x in pe_rows if isinstance(pe_rows, list) else []:
        code = str(pick(x, ['SecuritiesCompanyCode','SecuritiesCode','股票代號','證券代號','代號','Code']) or '').strip()
        pe = num(pick(x, ['PriceEarningRatio','PERatio','本益比']))
        if code: pe_map[code] = pe
    out = {}
    for x in quotes if isinstance(quotes, list) else []:
        code = str(pick(x, ['SecuritiesCompanyCode','SecuritiesCode','股票代號','證券代號','代號','Code']) or '').strip()
        name = pick(x, ['CompanyName','SecuritiesName','股票名稱','證券名稱','Name']) or code
        price = num(pick(x, ['Close','ClosingPrice','收盤價','ClosePrice']))
        if not code or price is None or price <= 0: continue
        pe = pe_map.get(code)
        eps = price / pe if pe and pe > 0 else None
        out[code] = {'code':code,'name':str(name).strip(),'market':'TPEX','price':price,'pe':pe,'eps':eps}
    print('TPEx current', len(out), '6274 present', '6274' in out)
    return out


def load_history():
    try:
        with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
            x = json.load(f)
            if isinstance(x, dict) and isinstance(x.get('days'), list): return x
    except Exception as e:
        print('history load fallback', e)
    return {'days': [], 'meta': {}}


def atomic_json(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def update_history(hist, current):
    today = datetime.now(TZ).date().isoformat()
    prices = {code:x['price'] for code,x in current.items() if x.get('price')}
    days = [d for d in hist.get('days', []) if d.get('date') != today]
    days.append({'date':today,'prices':prices})
    hist['days'] = sorted(days, key=lambda d:d.get('date',''))[-MAX_DAYS:]
    hist.setdefault('meta', {})
    hist['meta']['mode'] = 'daily-accumulation'
    hist['meta']['targetDays'] = MAX_DAYS
    hist['meta']['updated'] = datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
    return hist


def build_stocks(current, hist):
    series = {}
    for day in hist.get('days', []):
        for code, price in (day.get('prices') or {}).items():
            if isinstance(price, (int,float)) and price > 0:
                series.setdefault(code, []).append(price)
    ratios = [1.50,1.382,1.20,1.00,0.80,0.618]
    labels = ['瘋狂價','昂貴價','合理價(上緣)','合理價(下緣)','便宜價','特價']
    out = {
        'updated': datetime.now(TZ).strftime('%Y-%m-%d %H:%M'),
        'source':'TWSE + TPEx official data',
        'count':0,'marketCounts':{},'targetDays':MAX_DAYS,'stocks':{}
    }
    for code, x in current.items():
        arr = series.get(code, [])[-MAX_DAYS:]
        avg = sum(arr)/len(arr) if arr else x.get('price')
        eps = x.get('eps')
        base_pe = avg/eps if avg and eps and eps > 0 else None
        pe_bands = [base_pe*r for r in ratios] if base_pe else []
        values = [eps*p for p in pe_bands] if eps and pe_bands else []
        out['stocks'][code] = {
            **x,'avg60':avg,'historyDays':len(arr),'basePE':base_pe,
            'peBands':pe_bands,'labels':labels,'values':values,
            'modelReady':bool(base_pe and len(arr) >= 15),
            'historyTarget':MAX_DAYS,
            'historyStatus':'ready60' if len(arr)>=MAX_DAYS else f'building {len(arr)}/{MAX_DAYS}'
        }
        m = x.get('market','UNKNOWN')
        out['marketCounts'][m] = out['marketCounts'].get(m,0)+1
    out['count'] = len(out['stocks'])
    return out


def main():
    twse = twse_current()
    tpex = tpex_current()
    current = {**twse, **tpex}
    if len(twse) < 500:
        raise RuntimeError(f'TWSE data too small: {len(twse)}')
    if len(tpex) < 100:
        raise RuntimeError(f'TPEx data too small: {len(tpex)}')
    if '6274' not in current:
        raise RuntimeError('TPEx validation failed: 6274 missing')
    hist = update_history(load_history(), current)
    stocks = build_stocks(current, hist)
    if stocks['count'] < 1000:
        raise RuntimeError(f'combined stock count too small: {stocks["count"]}')
    atomic_json(HISTORY_PATH, hist)
    atomic_json(STOCKS_PATH, stocks)
    print('DONE', stocks['count'], stocks['marketCounts'], '6274', stocks['stocks']['6274']['name'], stocks['stocks']['6274']['price'])

if __name__ == '__main__':
    main()
