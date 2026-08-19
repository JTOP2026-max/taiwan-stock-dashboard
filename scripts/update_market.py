import json, os, math
from datetime import datetime, timedelta, timezone
import requests

ROOT=os.path.dirname(os.path.dirname(__file__))
MARKET=os.path.join(ROOT,'market.json')
HIST=os.path.join(ROOT,'market_history.json')
TZ=timezone(timedelta(hours=8))
S=requests.Session(); S.headers.update({'User-Agent':'Mozilla/5.0 TaiwanStockDashboard/2.1'})

def num(v):
    try:
        if v is None:return None
        s=str(v).replace(',','').replace('%','').replace('--','').strip()
        if not s:return None
        x=float(s); return x if math.isfinite(x) else None
    except:return None

def jget(url,params=None,timeout=30):
    r=S.get(url,params=params,timeout=timeout); r.raise_for_status(); return r.json()

def load(path,default):
    try:
        with open(path,'r',encoding='utf-8') as f:return json.load(f)
    except:return default

def save(path,obj):
    with open(path,'w',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)

def latest_trading_day():
    d=datetime.now(TZ).date()
    for _ in range(8):
        if d.weekday()<5:
            try:
                j=jget('https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX',{'date':d.strftime('%Y%m%d'),'type':'ALLBUT0999','response':'json'})
                if j.get('stat')=='OK' and j.get('tables'): return d,j
            except: pass
        d-=timedelta(days=1)
    return datetime.now(TZ).date(),{}

def parse_twse(mi):
    out={'index':None,'chg':None,'pct':None,'turnover':None,'up':None,'down':None}; up=down=0
    for t in mi.get('tables',[]):
        fields=t.get('fields') or []; data=t.get('data') or []
        if '指數' in fields and ('收盤指數' in fields or '收盤價' in fields):
            for r in data:
                if any('發行量加權股價指數' in str(x) for x in r):
                    def val(name): return num(r[fields.index(name)]) if name in fields and fields.index(name)<len(r) else None
                    out['index']=val('收盤指數') or val('收盤價')
                    raw_chg=val('漲跌點數')
                    raw_pct=val('漲跌百分比') if '漲跌百分比' in fields else val('漲跌百分比(%)')
                    sign=''
                    for sign_name in ('漲跌(+/-)','漲跌'):
                        if sign_name in fields and fields.index(sign_name)<len(r):
                            sign=str(r[fields.index(sign_name)]).lower()
                            break
                    direction=-1 if ('-' in sign or 'green' in sign) else 1
                    out['chg']=(abs(raw_chg)*direction) if raw_chg is not None else None
                    out['pct']=(abs(raw_pct)*direction) if raw_pct is not None else None
        if '證券代號' in fields and '收盤價' in fields:
            sign_i=fields.index('漲跌(+/-)') if '漲跌(+/-)' in fields else None; amt_i=fields.index('成交金額') if '成交金額' in fields else None; total=0.0
            for r in data:
                if amt_i is not None and amt_i<len(r): total+=num(r[amt_i]) or 0
                if sign_i is not None and sign_i<len(r):
                    s=str(r[sign_i]).strip()
                    if '+' in s: up+=1
                    elif '-' in s: down+=1
            if total>0: out['turnover']=total
    out['up']=up or None; out['down']=down or None; return out

def parse_institutions(d):
    try:
        j=jget('https://www.twse.com.tw/rwd/zh/fund/BFI82U',{'dayDate':d.strftime('%Y%m%d'),'type':'day','response':'json'})
        fields=j.get('fields') or []; data=j.get('data') or []
        if not fields or not data:return {}
        diff_i=next((i for i,f in enumerate(fields) if '買賣差額' in str(f) or '買賣超' in str(f)),None)
        if diff_i is None:return {}
        foreign=trust=dealer=total=None
        for r in data:
            if not r or diff_i>=len(r): continue
            name=str(r[0]).replace(' ',''); v=num(r[diff_i])
            if v is None:continue
            if name=='合計': total=v
            elif '外資及陸資' in name and '外資自營商' not in name: foreign=v
            elif '投信' in name: trust=(trust or 0)+v
            elif '自營商' in name: dealer=(dealer or 0)+v
        if total is None:
            vals=[x for x in (foreign,trust,dealer) if x is not None]; total=sum(vals) if vals else None
        if foreign is None and total is not None:
            foreign=total-(trust or 0)-(dealer or 0)
        return {k:(v/1e8 if v is not None else None) for k,v in {'total':total,'foreign':foreign,'trust':trust,'dealer':dealer}.items()}
    except Exception as e:
        print('institution unavailable',e); return {}

def parse_pc():
    try:
        j=jget('https://openapi.taifex.com.tw/v1/PutCallRatio'); rows=j if isinstance(j,list) else j.get('data',[]) if isinstance(j,dict) else []
        if not rows:return {}
        r=rows[0]
        def pick(keys):
            for k,v in r.items():
                kk=str(k).lower().replace('/','').replace(' ','')
                if any(x in kk for x in keys):
                    n=num(v)
                    if n is not None:return n
        trade=pick(['putcallvolumeratio','成交量比率','成交比率','volumeratio']); oi=pick(['putcalloiratio','未平倉量比率','未平倉比率','oiratio'])
        if trade and trade>10: trade/=100
        if oi and oi>10: oi/=100
        return {'trade':trade,'oi':oi}
    except Exception as e:
        print('pc unavailable',e); return {}

def parse_futures():
    try:
        j=jget('https://openapi.taifex.com.tw/v1/DailyMarketReportFut'); rows=j if isinstance(j,list) else j.get('data',[]) if isinstance(j,dict) else []
        cand=[]
        for r in rows:
            text=' '.join(str(v) for v in r.values())
            # Prefer TX/臺股期貨; keep rows with a valid close.
            if '臺股期貨' in text or 'TAIEX Futures' in text or any(str(v).strip()=='TX' for v in r.values()):
                price=chg=None
                for k,v in r.items():
                    kk=str(k).lower()
                    if price is None and any(x in kk for x in ['closingprice','close','收盤價']): price=num(v)
                    if chg is None and any(x in kk for x in ['change','漲跌']): chg=num(v)
                if price is not None: cand.append((r,price,chg))
        if not cand:return {}
        r,price,chg=cand[0]
        return {'price':price,'chg':chg}
    except Exception as e:
        print('futures unavailable',e); return {}

def sentiment(pc,breadth,inst):
    score=50.0; oi=pc.get('oi'); trade=pc.get('trade')
    if oi is not None: score += max(-18,min(18,(oi-1.0)*45))
    if trade is not None: score += max(-8,min(8,(trade-1.0)*20))
    u=breadth.get('up'); d=breadth.get('down')
    if u is not None and d is not None and u+d>0: score += ((u-d)/(u+d))*18
    f=inst.get('foreign')
    if f is not None: score += max(-10,min(10,f/80))
    return round(max(0,min(100,score)))

def main():
    d,mi=latest_trading_day(); tw=parse_twse(mi); inst=parse_institutions(d); pc=parse_pc(); fut=parse_futures(); prev=load(MARKET,{})
    idx=tw.get('index') or prev.get('core',{}).get('idx'); chg=tw.get('chg') if tw.get('chg') is not None else prev.get('core',{}).get('chg'); pct=tw.get('pct')
    if pct is None and idx and chg and idx-chg: pct=chg/(idx-chg)*100
    turnover=tw.get('turnover'); vol=(round(turnover/1e12,2) if turnover else prev.get('core',{}).get('volTrillion'))
    breadth={'up':tw.get('up') or prev.get('breadth',{}).get('up'),'down':tw.get('down') or prev.get('breadth',{}).get('down')}; fg=sentiment(pc,breadth,inst)
    fut_price=fut.get('price') or prev.get('core',{}).get('fut'); fut_chg=fut.get('chg') if fut.get('chg') is not None else prev.get('core',{}).get('futChg'); basis=(fut_price-idx) if fut_price is not None and idx is not None else None
    out={'date':d.isoformat(),'updated':datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S'),'core':{'idx':idx,'chg':chg,'pct':pct,'volTrillion':vol,'fut':fut_price,'futChg':fut_chg,'basis':basis},'inst':{'total':inst.get('total'),'foreign':inst.get('foreign'),'trust':inst.get('trust'),'dealer':inst.get('dealer')},'pc':{'trade':pc.get('trade'),'oi':pc.get('oi')},'breadth':breadth,'fearGreed':fg,'sources':{'twse':bool(mi),'institutions':bool(inst),'taifexPC':bool(pc),'taifexFutures':bool(fut)}}
    save(MARKET,out); hist=load(HIST,{'records':[]}); recs=[x for x in hist.get('records',[]) if x.get('date')!=out['date']]; recs.append(out); recs=sorted(recs,key=lambda x:x.get('date',''))[-400:]; save(HIST,{'updated':out['updated'],'records':recs}); print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':main()
