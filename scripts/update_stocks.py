import json, os, time, math
from datetime import datetime, timedelta, timezone
import requests

ROOT = os.path.dirname(os.path.dirname(__file__))
STOCKS_PATH = os.path.join(ROOT, 'stocks.json')
HISTORY_PATH = os.path.join(ROOT, 'stock_history.json')
TZ = timezone(timedelta(hours=8))
S = requests.Session()
S.headers.update({'User-Agent':'Mozilla/5.0 TaiwanStockDashboard/2.1'})


def jget(url, params=None, timeout=35):
    r = S.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def num(v):
    try:
        if v is None: return None
        s = str(v).replace(',', '').replace('--','').replace('---','').replace('%','').strip()
        if not s: return None
        x = float(s)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def pick(row, aliases):
    if not isinstance(row, dict): return None
    for k, v in row.items():
        kk = str(k).lower().replace(' ', '').replace('_','').replace('/','')
        if any(a.lower().replace(' ','').replace('_','').replace('/','') in kk for a in aliases):
            if v not in (None, '', '--', '---'): return v
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


def tpex_current():
    quotes = jget('https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes')
    perows = jget('https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis')
    pe_map = {}
    for x in perows if isinstance(perows, list) else []:
        code = str(pick(x, ['SecuritiesCompanyCode','SecuritiesCode','股票代號','代號','Code']) or '').strip()
        p = num(pick(x, ['PriceEarningRatio','PERatio','本益比']))
        if code: pe_map[code] = p
    out = {}
    for x in quotes if isinstance(quotes, list) else []:
        code = str(pick(x, ['SecuritiesCompanyCode','SecuritiesCode','股票代號','代號','Code']) or '').strip()
        name = pick(x, ['CompanyName','SecuritiesName','股票名稱','證券名稱','Name']) or code
        price = num(pick(x, ['Close','ClosingPrice','收盤價','ClosePrice']))
        if not code or price is None or price <= 0: continue
        p = pe_map.get(code)
        eps = (price / p) if p and p > 0 else None
        out[code] = {'code':code,'name':str(name).strip(),'market':'TPEX','price':price,'pe':p,'eps':eps}
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
                    c = str(r[ci]).strip(); p = num(r[pi])
                    if c and p and p > 0: rows[c] = {'price':p,'name':r[ni] if ni is not None else c}
                except Exception: pass
            break
    return rows


def parse_tpex_rows(obj):
    rows = {}
    def consume(item):
        if isinstance(item, dict):
            code = str(pick(item, ['SecuritiesCompanyCode','SecuritiesCode','股票代號','證券代號','代號','Code']) or '').strip()
            price = num(pick(item, ['Close','ClosingPrice','收盤價','ClosePrice']))
            name = pick(item, ['CompanyName','SecuritiesName','股票名稱','證券名稱','Name']) or code
            if code and price and price > 0: rows[code] = {'price':price,'name':str(name).strip()}
            for v in item.values():
                if isinstance(v, (dict,list)): consume(v)
        elif isinstance(item, list):
            for v in item: consume(v)
    consume(obj)
    return rows


def tpex_daily_all(d):
    # New TPEx website JSON endpoint; fallback to legacy endpoint for compatibility.
    urls = [
      ('https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes', {'date':d.strftime('%Y/%m/%d'),'id':'','response':'json'}),
      ('https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php', {'l':'zh-tw','o':'json','d':f'{d.year-1911}/{d.month:02d}/{d.day:02d}','s':'0,asc,0'})
    ]
    for url, params in urls:
        try:
            obj = jget(url, params=params)
            rows = parse_tpex_rows(obj)
            if len(rows) > 100: return rows
        except Exception as e:
            print('tpex daily endpoint failed', d.isoformat(), url, e)
    return {}


def load_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                x = json.load(f)
                if isinstance(x, dict) and 'days' in x: return x
        except Exception: pass
    return {'days': [], 'meta':{}}


def save_json(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def ensure_60_days(hist):
    hist.setdefault('meta', {})
    known = {x.get('date') for x in hist['days']}
    today = datetime.now(TZ).date()
    if len(hist['days']) < 60:
        d = today; scanned = 0
        while len(hist['days']) < 60 and scanned < 130:
            ds = d.isoformat()
            if ds not in known and d.weekday() < 5:
                try:
                    rows = twse_daily_all(d)
                    if len(rows) > 300:
                        hist['days'].append({'date':ds,'prices':{k:v['price'] for k,v in rows.items()}})
                        known.add(ds); print('TWSE bootstrap', ds, len(rows))
                    time.sleep(0.12)
                except Exception as e: print('TWSE skip', ds, e)
            d -= timedelta(days=1); scanned += 1

    # One-time TPEx backfill into the same 60 trading-day records.
    if not hist['meta'].get('tpexBackfilled'):
        ok = 0
        for day in sorted(hist['days'], key=lambda x:x.get('date','')):
            try:
                d = datetime.strptime(day['date'], '%Y-%m-%d').date()
                rows = tpex_daily_all(d)
                if len(rows) > 100:
                    day.setdefault('prices', {}).update({k:v['price'] for k,v in rows.items()})
                    ok += 1; print('TPEx backfill', day['date'], len(rows))
                time.sleep(0.12)
            except Exception as e: print('TPEx skip', day.get('date'), e)
        if ok >= max(10, len(hist['days'])//2): hist['meta']['tpexBackfilled'] = True
        hist['meta']['tpexBackfillDays'] = ok

    # Refresh today's completed session from both markets.
    ds = today.isoformat(); merged = {}
    try:
        rows = twse_daily_all(today); merged.update({k:v['price'] for k,v in rows.items()})
    except Exception as e: print('today TWSE unavailable', e)
    try:
        rows = tpex_daily_all(today); merged.update({k:v['price'] for k,v in rows.items()})
    except Exception as e: print('today TPEx unavailable', e)
    if len(merged) > 300:
        hist['days'] = [x for x in hist['days'] if x.get('date') != ds]
        hist['days'].append({'date':ds,'prices':merged})
    hist['days'] = sorted(hist['days'], key=lambda x:x.get('date',''))[-60:]
    return hist


def build_stocks(current, hist):
    series = {}
    for day in hist.get('days', []):
        for code, price in (day.get('prices') or {}).items():
            if isinstance(price,(int,float)) and price > 0: series.setdefault(code, []).append(price)
    updated = datetime.now(TZ).strftime('%Y-%m-%d %H:%M')
    out = {'updated':updated,'source':'TWSE + TPEx official data','count':0,'marketCounts':{},'stocks':{}}
    ratios = [1.50,1.382,1.20,1.00,0.80,0.618]
    labels = ['瘋狂價','昂貴價','合理價(上緣)','合理價(下緣)','便宜價','特價']
    for code,x in current.items():
        arr = series.get(code, [])[-60:]; avg60 = sum(arr)/len(arr) if arr else None
        eps=x.get('eps'); base_pe=(avg60/eps) if avg60 and eps and eps>0 else None
        pe_bands=[base_pe*r for r in ratios] if base_pe else []; values=[eps*p for p in pe_bands] if eps and pe_bands else []
        out['stocks'][code]={**x,'avg60':avg60,'historyDays':len(arr),'basePE':base_pe,'peBands':pe_bands,'labels':labels,'values':values,'modelReady':bool(base_pe and len(arr)>=20)}
        m=x.get('market','UNKNOWN'); out['marketCounts'][m]=out['marketCounts'].get(m,0)+1
    out['count']=len(out['stocks']); return out


def main():
    twse = twse_current()
    try: tpex = tpex_current()
    except Exception as e:
        print('TPEx current unavailable', e); tpex = {}
    current = {**twse, **tpex}
    hist = ensure_60_days(load_history())
    stocks = build_stocks(current, hist)
    save_json(HISTORY_PATH, hist); save_json(STOCKS_PATH, stocks)
    print('stocks',stocks['count'],stocks.get('marketCounts'),'history days',len(hist['days']))

if __name__ == '__main__': main()
