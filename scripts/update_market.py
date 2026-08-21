import json, os, math
from datetime import datetime, timedelta, timezone
import requests

ROOT=os.path.dirname(os.path.dirname(__file__))
MARKET=os.path.join(ROOT,'market.json')
HIST=os.path.join(ROOT,'market_history.json')
CNN_HIST=os.path.join(ROOT,'cnn_fear_greed.json')
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

def parse_pc(target_date):
    try:
        j=jget('https://openapi.taifex.com.tw/v1/PutCallRatio')
        rows=j if isinstance(j,list) else j.get('data',[]) if isinstance(j,dict) else []
        if not rows:return {}

        def row_date(row):
            # TAIFEX has changed the date column label across payload versions.
            # Detect the YYYYMMDD value itself instead of trusting a field name.
            preferred=[]
            other=[]
            for k,v in row.items():
                kk=str(k).lower().replace('_','').replace(' ','')
                (preferred if any(x in kk for x in ('date','日期')) else other).append(v)
            for v in preferred+other:
                s=str(v).strip()
                digits=''.join(ch for ch in s if ch.isdigit())
                if len(digits)>=8:
                    digits=digits[:8]
                    if digits.startswith('20'):
                        try:return datetime.strptime(digits,'%Y%m%d').date()
                        except:pass
            return None

        dated=[(row_date(row),row) for row in rows]
        exact=[row for rd,row in dated if rd==target_date]
        if not exact:
            available=[(rd,row) for rd,row in dated if rd is not None and rd<=target_date]
            if available:
                latest=max(rd for rd,_ in available)
                if latest!=target_date:
                    print('pc date mismatch:',latest,'!=',target_date)
                    return {}
                exact=[row for rd,row in available if rd==latest]
            else:
                # Some TAIFEX payload versions omit a usable date column.
                # Only trust the first (latest) row after the publication window;
                # never do this during the early-morning refresh that caused stale P/C.
                now=datetime.now(TZ)
                safe_fallback=(now.hour>=18) or (target_date<now.date() and now.hour>=10)
                if not safe_fallback:
                    print('pc unavailable: undated payload before publication window')
                    return {}
                print('pc date unavailable; using latest row after publication window')
                exact=[rows[0]]

        r=exact[0]
        def pick(keys):
            for k,v in r.items():
                kk=str(k).lower().replace('/','').replace(' ','')
                if any(x in kk for x in keys):
                    value=num(v)
                    if value is not None:return value
        trade=pick(['putcallvolumeratio','成交量比率','成交比率','volumeratio'])
        oi=pick(['putcalloiratio','未平倉量比率','未平倉比率','oiratio'])
        if trade is not None and trade>10:trade/=100
        if oi is not None and oi>10:oi/=100
        return {'trade':trade,'oi':oi,'date':target_date.isoformat()}
    except Exception as e:
        print('pc unavailable',e)
        return {}

def parse_futures():
    try:
        j=jget('https://openapi.taifex.com.tw/v1/DailyMarketReportFut')
        rows=j if isinstance(j,list) else j.get('data',[]) if isinstance(j,dict) else []
        def norm(k): return str(k).lower().replace('_','').replace(' ','').replace('/','')
        def pick(row,names):
            for k,v in row.items():
                nk=norm(k)
                if any(name in nk for name in names): return v
            return None
        def pick_exact(row,names):
            wanted={norm(name) for name in names}
            for k,v in row.items():
                if norm(k) in wanted:return v
            return None
        def signed(v):
            if v is None:return None
            s=str(v).strip()
            direction=-1 if ('▼' in s or s.startswith('-')) else 1
            s=s.replace('▲','').replace('▼','').replace('%','').replace(',','').strip()
            try:return abs(float(s))*direction
            except:return None
        cand=[]
        for r in rows:
            code=str(pick(r,['contractcode','commodityid','productid','商品代號','契約']) or '').strip().upper()
            name=str(pick(r,['contractname','commodityname','商品名稱']) or '').strip()
            if code!='TX' and '臺股期貨' not in name and 'TAIEXFUTURES' not in name.upper().replace(' ',''):continue
            price=num(pick(r,['closingprice','closeprice','lastprice','最後成交價','收盤價']))
            if price is None or price<=0:continue
            chg=signed(pick(r,['changepercent','漲跌%']))
            raw_change=signed(pick_exact(r,['Change','ChangeValue','漲跌價','漲跌點數']))
            if raw_change is not None:chg=raw_change
            date=str(pick(r,['tradedate','date','交易日期','日期']) or '')
            month=str(pick(r,['contractmonth','deliverymonth','到期月份']) or '')
            session=str(pick(r,['tradingsession','session','交易時段']) or '')
            volume=num(pick(r,['volume','成交量'])) or 0
            night=1 if any(x in session.lower() for x in ['盤後','夜盤','after','night']) else 0
            cand.append((date,night,month,volume,price,chg,session))
        if not cand:return {}
        latest_date=max(x[0] for x in cand)
        same=[x for x in cand if x[0]==latest_date]
        if any(x[1] for x in same):same=[x for x in same if x[1]]
        same.sort(key=lambda x:(x[2] or '999999',-x[3]))
        row=same[0]
        return {'price':row[4],'chg':row[5],'date':row[0],'session':row[6] or ('盤後' if row[1] else '一般')}
    except Exception as e:
        print('futures unavailable',e); return {}


def parse_cnn_fear_greed():
    try:
        r=S.get('https://production.dataviz.cnn.io/index/fearandgreed/graphdata',timeout=30,headers={'Referer':'https://edition.cnn.com/markets/fear-and-greed','Accept':'application/json'})
        r.raise_for_status(); j=r.json(); fg=j.get('fear_and_greed') or {}
        score=num(fg.get('score')); timestamp=fg.get('timestamp'); rating=str(fg.get('rating') or '').strip().lower(); records=[]
        for row in (j.get('fear_and_greed_historical') or {}).get('data') or []:
            x=num(row.get('x')); y=num(row.get('y'))
            if x is None or y is None:continue
            dt=datetime.fromtimestamp(x/1000,timezone.utc).date().isoformat()
            records.append({'date':dt,'score':round(y,2),'rating':str(row.get('rating') or '').strip().lower()})
        if score is not None and timestamp:
            try:current_date=datetime.fromisoformat(str(timestamp).replace('Z','+00:00')).date().isoformat()
            except:current_date=None
            if current_date and not any(x.get('date')==current_date for x in records):records.append({'date':current_date,'score':round(score,2),'rating':rating})
        records=sorted({x['date']:x for x in records}.values(),key=lambda x:x['date'])[-500:]
        return {'score':score,'rating':rating,'timestamp':timestamp,'previousClose':num(fg.get('previous_close')),'previousWeek':num(fg.get('previous_1_week')),'previousMonth':num(fg.get('previous_1_month')),'records':records}
    except Exception as e:
        print('cnn fear & greed unavailable',e); return {}

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
    d,mi=latest_trading_day(); tw=parse_twse(mi); inst=parse_institutions(d); prev=load(MARKET,{})
    cnn=parse_cnn_fear_greed()
    pc=parse_pc(d)
    if not pc and prev.get('date')==d.isoformat():
        old_pc=prev.get('pc',{})
        if old_pc.get('trade') is not None and old_pc.get('oi') is not None:
            pc={'trade':old_pc.get('trade'),'oi':old_pc.get('oi'),'date':d.isoformat()}
            print('pc unavailable; preserving validated same-day values')
    fut=parse_futures()
    idx=tw.get('index') or prev.get('core',{}).get('idx'); chg=tw.get('chg') if tw.get('chg') is not None else prev.get('core',{}).get('chg'); pct=tw.get('pct')
    if pct is None and idx and chg and idx-chg: pct=chg/(idx-chg)*100
    turnover=tw.get('turnover'); vol=(round(turnover/1e12,2) if turnover else prev.get('core',{}).get('volTrillion'))
    breadth={'up':tw.get('up') or prev.get('breadth',{}).get('up'),'down':tw.get('down') or prev.get('breadth',{}).get('down')}
    taiwan_sentiment=sentiment(pc,breadth,inst)
    cnn_score=cnn.get('score') if cnn.get('score') is not None else prev.get('cnnFearGreed',{}).get('score')
    cnn_snapshot={'score':cnn_score,'rating':cnn.get('rating') or prev.get('cnnFearGreed',{}).get('rating'),'timestamp':cnn.get('timestamp') or prev.get('cnnFearGreed',{}).get('timestamp'),'previousClose':cnn.get('previousClose'),'previousWeek':cnn.get('previousWeek'),'previousMonth':cnn.get('previousMonth')}
    fut_price=fut.get('price'); fut_chg=fut.get('chg'); basis=(fut_price-idx) if fut_price is not None and idx is not None else None
    out={'date':d.isoformat(),'updated':datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S'),'core':{'idx':idx,'chg':chg,'pct':pct,'volTrillion':vol,'fut':fut_price,'futChg':fut_chg,'basis':basis},'inst':{'total':inst.get('total'),'foreign':inst.get('foreign'),'trust':inst.get('trust'),'dealer':inst.get('dealer')},'pc':{'trade':pc.get('trade'),'oi':pc.get('oi')},'breadth':breadth,'taiwanSentiment':taiwan_sentiment,'cnnFearGreed':cnn_snapshot,'fearGreed':cnn_score,'sources':{'twse':bool(mi),'institutions':bool(inst),'taifexPC':bool(pc),'taifexFutures':bool(fut),'cnnFearGreed':cnn.get('score') is not None}}
    save(MARKET,out)
    old_cnn=load(CNN_HIST,{'records':[]}); cnn_records=cnn.get('records') or old_cnn.get('records',[])
    save(CNN_HIST,{'updated':out['updated'],'source':'CNN Fear & Greed','records':cnn_records})
    hist=load(HIST,{'records':[]}); recs=[x for x in hist.get('records',[]) if x.get('date')!=out['date']]; recs.append(out); recs=sorted(recs,key=lambda x:x.get('date',''))[-400:]; save(HIST,{'updated':out['updated'],'records':recs}); print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':main()
