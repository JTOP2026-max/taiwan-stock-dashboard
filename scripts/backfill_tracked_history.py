import json, os, time, math
from datetime import datetime, timedelta, timezone
import requests

ROOT = os.path.dirname(os.path.dirname(__file__))
OUT = os.path.join(ROOT, 'stock_ohlcv.json')
TRACK_FILE = os.path.join(ROOT, 'tracked_history_codes.json')
TZ = timezone(timedelta(hours=8))
S = requests.Session()
S.headers.update({'User-Agent':'Mozilla/5.0 TaiwanStockDashboard/3.3'})
DEFAULT_TRACKED = ['3008','6510','3044','2454','6274','2449']
MONTHS = 14


def num(v):
    try:
        s = str(v if v is not None else '').replace(',', '').replace('+','').strip()
        if not s or s in ('--','---','-'): return None
        x=float(s)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def tracked_codes():
    """Return only explicitly tracked history symbols.

    Do NOT walk every code in stocks.json. That file contains the full market and
    would turn one history run into tens of thousands of HTTP requests, causing
    GitHub Actions to time out before stock_ohlcv.json can be committed.
    """
    codes=set(DEFAULT_TRACKED)
    try:
        with open(TRACK_FILE,encoding='utf-8') as f:
            j=json.load(f)
        items=j.get('codes',j) if isinstance(j,dict) else j
        if isinstance(items,list):
            codes.update(str(x).strip() for x in items if str(x).strip().isdigit())
    except FileNotFoundError:
        pass
    except Exception as e:
        print('tracked_history_codes.json skip',e)

    # Preserve symbols that already have history so existing charts keep updating.
    try:
        with open(OUT,encoding='utf-8') as f:
            old=json.load(f)
        codes.update(str(k) for k in (old.get('stocks') or {}).keys() if str(k).isdigit())
    except Exception:
        pass
    return sorted(codes)


def month_starts(count=MONTHS):
    now=datetime.now(TZ)
    out=[]
    for i in range(count):
        y=now.year; m=now.month-i
        while m<=0:
            y-=1; m+=12
        out.append((y,m))
    return out


def roc_iso(s):
    try:
        a=str(s).strip().split('/')
        if len(a)!=3:return None
        return f'{int(a[0])+1911:04d}-{int(a[1]):02d}-{int(a[2]):02d}'
    except Exception:return None


def fetch_tpex(code):
    rows=[]
    for y,m in month_starts():
        url=f'https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock?date={y:04d}%2F{m:02d}%2F01&code={code}&response=json'
        try:
            r=S.get(url,timeout=15); r.raise_for_status(); j=r.json()
            tables=j.get('tables') or []
            data=(tables[0].get('data') if tables else []) or []
            for a in data:
                if len(a)<7: continue
                date=roc_iso(a[0]); vol=num(a[1]); op=num(a[3]); hi=num(a[4]); lo=num(a[5]); cl=num(a[6])
                if date and cl and cl>0:
                    rows.append({'date':date,'open':op or cl,'high':hi or cl,'low':lo or cl,'close':cl,'volume':vol or 0,'market':'TPEX'})
        except Exception as e: print('TPEX',code,y,m,'skip',e)
        time.sleep(.05)
    return rows


def fetch_twse(code):
    rows=[]
    for y,m in month_starts():
        url=f'https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?response=json&date={y:04d}{m:02d}01&stockNo={code}'
        try:
            r=S.get(url,timeout=15); r.raise_for_status(); j=r.json()
            for a in (j.get('data') or []):
                if len(a)<7: continue
                date=roc_iso(a[0]); vol=num(a[1]); op=num(a[3]); hi=num(a[4]); lo=num(a[5]); cl=num(a[6])
                if date and cl and cl>0:
                    rows.append({'date':date,'open':op or cl,'high':hi or cl,'low':lo or cl,'close':cl,'volume':vol or 0,'market':'TWSE'})
        except Exception as e: print('TWSE',code,y,m,'skip',e)
        time.sleep(.05)
    return rows


def uniq(rows):
    d={}
    for r in rows:
        if r.get('date') and r.get('close'): d[r['date']]=r
    return [d[k] for k in sorted(d)]


def main():
    out={'updated':datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S'),'stocks':{}}
    codes=tracked_codes()
    print('history symbols',len(codes),codes)
    for code in codes:
        rows=fetch_twse(code)
        if len(rows)<20: rows=fetch_tpex(code)
        rows=uniq(rows)[-260:]
        out['stocks'][code]=rows
        print(code,'history rows',len(rows), rows[-1]['market'] if rows else 'NONE')
    with open(OUT+'.tmp','w',encoding='utf-8') as f:
        json.dump(out,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
    os.replace(OUT+'.tmp',OUT)

if __name__=='__main__': main()
