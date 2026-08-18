import json
from datetime import datetime, timedelta, timezone
import requests

TZ = timezone(timedelta(hours=8))
OUT = 'corporate_actions.json'
S = requests.Session()
S.headers.update({'User-Agent':'Mozilla/5.0 TaiwanStockDashboard/1.0'})


def num(v):
    try:
        if v is None: return 0.0
        s = str(v).replace(',', '').strip()
        if not s or '待公告' in s or s in ('--','N/A','-'): return 0.0
        return float(s)
    except Exception:
        return 0.0


def roc_to_iso(s):
    s = str(s or '').strip()
    # TWSE text: 115年08月18日
    try:
        if '年' in s:
            y, rest = s.split('年',1)
            m, d = rest.replace('日','').split('月',1)
            return f"{int(y)+1911:04d}-{int(m):02d}-{int(d):02d}"
        # TPEx may use 115/08/18
        p = s.replace('.','/').split('/')
        if len(p) >= 3:
            y = int(p[0]); y = y + 1911 if y < 1911 else y
            return f"{y:04d}-{int(p[1]):02d}-{int(p[2]):02d}"
    except Exception:
        pass
    return ''


def twse_actions():
    url = 'https://www.twse.com.tw/exchangeReport/TWT48U'
    j = S.get(url, params={'response':'json'}, timeout=30).json()
    fields = j.get('fields') or []
    rows = j.get('data') or []
    out=[]
    for r in rows:
        row = {fields[i]: r[i] for i in range(min(len(fields),len(r)))}
        code = str(row.get('股票代號','')).strip()
        date = roc_to_iso(row.get('除權除息日期'))
        if not code or not date: continue
        bonus = num(row.get('無償配股率'))
        cash = num(row.get('現金股利'))
        if bonus <= 0 and cash <= 0: continue
        out.append({'id':f'TWSE-{code}-{date}-{bonus:.8f}-{cash:.8f}','market':'TWSE','code':code,'name':str(row.get('名稱','')).strip(),'exDate':date,'stockRatio':bonus,'cashDividend':cash,'type':str(row.get('除權息','')).strip()})
    return out


def first(d, keys):
    for k in keys:
        if k in d and d[k] not in (None,''): return d[k]
    return None


def tpex_actions():
    url='https://www.tpex.org.tw/openapi/v1/tpex_exright_prepost'
    data=S.get(url,timeout=30).json()
    out=[]
    for row in data if isinstance(data,list) else []:
        code=str(first(row,['SecuritiesCompanyCode','Code','股票代號','公司代號']) or '').strip()
        date=roc_to_iso(first(row,['Date','ExDate','除權除息日期','資料日期']))
        if not code or not date: continue
        bonus=num(first(row,['FreeStockDividendRate','StockDividendRate','無償配股率','股票股利']))
        # If an API expresses stock dividend as NTD/share rather than ratio, convert using NT$10 par convention only when clearly > 1.
        if bonus > 1: bonus = bonus / 10.0
        cash=num(first(row,['CashDividend','CashDividendPerShare','現金股利','息值']))
        if bonus <= 0 and cash <= 0: continue
        name=str(first(row,['CompanyName','Name','名稱','公司名稱']) or '').strip()
        out.append({'id':f'TPEX-{code}-{date}-{bonus:.8f}-{cash:.8f}','market':'TPEX','code':code,'name':name,'exDate':date,'stockRatio':bonus,'cashDividend':cash,'type':'權息'})
    return out


def main():
    actions=[]; errors=[]
    for fn in (twse_actions,tpex_actions):
        try: actions.extend(fn())
        except Exception as e: errors.append(str(e))
    # de-dupe and retain a practical recent/future window
    today=datetime.now(TZ).date(); lo=today-timedelta(days=45); hi=today+timedelta(days=370)
    unique={}
    for a in actions:
        try: d=datetime.fromisoformat(a['exDate']).date()
        except Exception: continue
        if lo <= d <= hi: unique[a['id']]=a
    out={'updated':datetime.now(TZ).strftime('%Y-%m-%d %H:%M'),'trackingStart':'2026-08-18','count':len(unique),'errors':errors,'actions':sorted(unique.values(), key=lambda x:(x['exDate'],x['code']))}
    with open(OUT,'w',encoding='utf-8') as f: json.dump(out,f,ensure_ascii=False,indent=2)
    print('corporate actions',out['count'],'errors',errors)

if __name__=='__main__': main()
