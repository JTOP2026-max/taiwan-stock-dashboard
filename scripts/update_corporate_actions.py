import json
import re
import hashlib
from datetime import datetime, timedelta, timezone
import requests

TZ = timezone(timedelta(hours=8))
OUT = 'corporate_actions.json'
EVENT_OUT = 'company_events.json'
S = requests.Session()
S.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36','Accept':'application/json,text/plain,*/*','Referer':'https://openapi.twse.com.tw/','Accept-Language':'zh-TW,zh;q=0.9,en;q=0.8'})


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
    try:
        if re.fullmatch(r'\d{7,8}', s):
            y = int(s[:-4]); md = s[-4:]
            y = y + 1911 if y < 1911 else y
            return f'{y:04d}-{int(md[:2]):02d}-{int(md[2:]):02d}'
        if '年' in s:
            y, rest = s.split('年',1)
            m, d = rest.replace('日','').split('月',1)
            y = int(y); y = y + 1911 if y < 1911 else y
            return f'{y:04d}-{int(m):02d}-{int(d):02d}'
        p = s.replace('.','/').replace('-','/').split('/')
        if len(p) >= 3 and all(x.strip().isdigit() for x in p[:3]):
            y = int(p[0]); y = y + 1911 if y < 1911 else y
            return f'{y:04d}-{int(p[1]):02d}-{int(p[2]):02d}'
    except Exception:
        pass
    return ''


def extract_event_date(text, fallback=''):
    text = str(text or '')
    patterns = [
        r'(?:法人說明會|法說會|召開日期|日期|基準日|停止交易日|恢復交易日)[^\d]{0,20}(\d{2,4}[./-]\d{1,2}[./-]\d{1,2})',
        r'(\d{2,4}[./-]\d{1,2}[./-]\d{1,2})'
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            d = roc_to_iso(m.group(1))
            if d: return d
    return roc_to_iso(fallback)


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
        if bonus > 1: bonus = bonus / 10.0
        cash=num(first(row,['CashDividend','CashDividendPerShare','現金股利','息值']))
        if bonus <= 0 and cash <= 0: continue
        name=str(first(row,['CompanyName','Name','名稱','公司名稱']) or '').strip()
        out.append({'id':f'TPEX-{code}-{date}-{bonus:.8f}-{cash:.8f}','market':'TPEX','code':code,'name':name,'exDate':date,'stockRatio':bonus,'cashDividend':cash,'type':'權息'})
    return out


def twse_dividend_policies():
    url='https://openapi.twse.com.tw/v1/opendata/t187ap45_L'
    data=S.get(url,timeout=30).json()
    latest={}
    for row in data if isinstance(data,list) else []:
        code=str(row.get('公司代號','')).strip()
        if not code or not re.fullmatch(r'\d{4,6}',code): continue
        cash=sum(num(row.get(k)) for k in [
            '股東配發-盈餘分配之現金股利(元/股)',
            '股東配發-法定盈餘公積發放之現金(元/股)',
            '股東配發-資本公積發放之現金(元/股)'])
        stock=sum(num(row.get(k)) for k in [
            '股東配發-盈餘轉增資配股(元/股)',
            '股東配發-法定盈餘公積轉增資配股(元/股)',
            '股東配發-資本公積轉增資配股(元/股)'])
        board=roc_to_iso(row.get('董事會（擬議）股利分派日'))
        key=(row.get('股利年度',''),row.get('期別',''),board)
        old=latest.get(code)
        if old is None or key>old['_key']:
            latest[code]={'_key':key,'kind':'dividend_policy','code':code,'name':str(row.get('公司名稱','')).strip(),'date':board,'cash':cash,'stock':stock,'title':f"股利政策：現金 {cash:.2f} 元/股、股票 {stock:.2f} 元/股",'status':str(row.get('決議（擬議）進度','')).strip(),'source':'TWSE t187ap45_L'}
    for x in latest.values(): x.pop('_key',None)
    return list(latest.values())


def classify_material(subject, detail):
    text=(subject+' '+detail).replace(' ', '')
    if '法人說明會' in text or '法說會' in text:
        return 'conference'
    if '減資' in text:
        return 'capital_reduction'
    if '增資' in text or '現金增資' in text or '私募' in text:
        return 'capital_increase'
    return ''


def twse_material_events():
    url='https://openapi.twse.com.tw/v1/opendata/t187ap04_L'
    data=S.get(url,timeout=30).json()
    out=[]
    for row in data if isinstance(data,list) else []:
        code=str(row.get('公司代號','')).strip()
        if not code or not re.fullmatch(r'\d{4,6}',code): continue
        subject=str(first(row,['主旨 ','主旨']) or '').strip()
        detail=str(row.get('說明','') or '')
        kind=classify_material(subject,detail)
        if not kind: continue
        date=extract_event_date(subject+'\n'+detail, row.get('事實發生日') or row.get('發言日期'))
        pub=roc_to_iso(row.get('發言日期'))
        sig=hashlib.sha1(subject.encode('utf-8')).hexdigest()[:10]
        ident=f"TWSE-MOPS-{code}-{kind}-{date or pub}-{sig}"
        out.append({'id':ident,'kind':kind,'code':code,'name':str(row.get('公司名稱','')).strip(),'date':date or pub,'published':pub,'title':subject[:180],'source':'TWSE t187ap04_L'})
    return out


def load_old_events():
    try:
        with open(EVENT_OUT,encoding='utf-8') as f:
            j=json.load(f)
        return j.get('events',[]) if isinstance(j,dict) else []
    except Exception:
        return []


def main():
    actions=[]; errors=[]
    for fn in (twse_actions,tpex_actions):
        try: actions.extend(fn())
        except Exception as e: errors.append(f'{fn.__name__}: {e}')
    today=datetime.now(TZ).date(); lo=today-timedelta(days=45); hi=today+timedelta(days=370)
    unique={}
    for a in actions:
        try: d=datetime.fromisoformat(a['exDate']).date()
        except Exception: continue
        if lo <= d <= hi: unique[a['id']]=a
    action_list=sorted(unique.values(), key=lambda x:(x['exDate'],x['code']))
    out={'updated':datetime.now(TZ).strftime('%Y-%m-%d %H:%M'),'trackingStart':'2026-08-18','count':len(action_list),'errors':errors,'actions':action_list}
    with open(OUT,'w',encoding='utf-8') as f: json.dump(out,f,ensure_ascii=False,indent=2)

    events=[]
    for a in action_list:
        events.append({'id':'EV-'+a['id'],'kind':'dividend','code':a['code'],'name':a.get('name',''),'date':a['exDate'],'cash':a.get('cashDividend',0),'stock':a.get('stockRatio',0),'title':f"除權息：現金 {a.get('cashDividend',0):.2f} 元/股、配股率 {a.get('stockRatio',0)*100:.2f}%",'source':a.get('market','')})
    for fn in (twse_dividend_policies, twse_material_events):
        try: events.extend(fn())
        except Exception as e: errors.append(f'{fn.__name__}: {e}')
    for e in load_old_events():
        if e.get('kind') not in ('conference','capital_increase','capital_reduction'): continue
        try: d=datetime.fromisoformat(e.get('date','')).date()
        except Exception: continue
        if d >= today-timedelta(days=7): events.append(e)
    dedup={}
    for e in events:
        code=str(e.get('code','')).strip(); kind=e.get('kind',''); date=e.get('date','')
        if not code or not kind: continue
        key=e.get('id') or f'{code}-{kind}-{date}-{e.get("title","")[:40]}'
        dedup[key]=e
    final=[]
    for e in dedup.values():
        if e.get('kind')=='dividend_policy': final.append(e); continue
        try: d=datetime.fromisoformat(e.get('date','')).date()
        except Exception: continue
        if today-timedelta(days=7) <= d <= today+timedelta(days=370): final.append(e)
    final.sort(key=lambda x:(x.get('date') or '9999-12-31',x.get('code',''),x.get('kind','')))
    evt={'updated':datetime.now(TZ).strftime('%Y-%m-%d %H:%M'),'count':len(final),'errors':errors,'events':final}
    with open(EVENT_OUT,'w',encoding='utf-8') as f: json.dump(evt,f,ensure_ascii=False,indent=2)
    print('corporate actions',out['count'],'events',evt['count'],'errors',errors)

if __name__=='__main__': main()
