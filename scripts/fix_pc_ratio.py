import json, math, os, re
from datetime import datetime
from html.parser import HTMLParser
import requests

ROOT=os.path.dirname(os.path.dirname(__file__))
MARKET=os.path.join(ROOT,'market.json')
HISTORY=os.path.join(ROOT,'market_history.json')
API='https://openapi.taifex.com.tw/v1/PutCallRatio'
PAGE='https://www.taifex.com.tw/cht/3/pcRatio'
HEADERS={'User-Agent':'Mozilla/5.0 TaiwanStockDashboard/2.3'}


def num(v):
    try:
        if v is None:return None
        s=str(v).replace(',','').replace('%','').strip()
        if not s or s in ('--','-','null','None'):return None
        x=float(s);return x if math.isfinite(x) else None
    except:return None


def norm(k):return re.sub(r'[\s_/%()（）-]+','',str(k)).lower()


def row_date(row):
    vals=[]
    for k,v in row.items():
        if 'date' in norm(k) or '日期' in str(k):vals.insert(0,v)
        else:vals.append(v)
    for v in vals:
        digits=''.join(ch for ch in str(v) if ch.isdigit())
        if len(digits)>=8 and digits[:4]=='2026':
            try:return datetime.strptime(digits[:8],'%Y%m%d').date().isoformat()
            except:pass
    return None


def pick(row, tests):
    for k,v in row.items():
        nk=norm(k)
        if any(t(nk,str(k)) for t in tests):
            x=num(v)
            if x is not None:return x
    return None


def api_ratios(target):
    r=requests.get(API,timeout=30,headers=HEADERS);r.raise_for_status();data=r.json()
    rows=data if isinstance(data,list) else data.get('data',[]) if isinstance(data,dict) else []
    row=next((x for x in rows if row_date(x)==target),None)
    if not row:return None
    trade=pick(row,[lambda k,raw:('putcall' in k and 'ratio' in k and ('volume' in k or '成交' in raw)),lambda k,raw:'買賣權成交量比率' in raw or '賣買權成交量比率' in raw])
    oi=pick(row,[lambda k,raw:('putcall' in k and 'ratio' in k and ('oi' in k or 'openinterest' in k or '未平倉' in raw)),lambda k,raw:'買賣權未平倉量比率' in raw or '賣買權未平倉量比率' in raw])
    if trade is None:
        pv=pick(row,[lambda k,raw:'賣權成交量' in raw and '比率' not in raw or ('putvolume' in k and 'ratio' not in k)])
        cv=pick(row,[lambda k,raw:'買權成交量' in raw and '比率' not in raw or ('callvolume' in k and 'ratio' not in k)])
        if pv is not None and cv not in (None,0):trade=pv/cv
    if oi is None:
        po=pick(row,[lambda k,raw:'賣權未平倉量' in raw and '比率' not in raw or (('putoi' in k or 'putopeninterest' in k) and 'ratio' not in k)])
        co=pick(row,[lambda k,raw:'買權未平倉量' in raw and '比率' not in raw or (('calloi' in k or 'callopeninterest' in k) and 'ratio' not in k)])
        if po is not None and co not in (None,0):oi=po/co
    if trade is not None and trade>10:trade/=100
    if oi is not None and oi>10:oi/=100
    return (trade,oi) if trade is not None and oi is not None else None


class TableParser(HTMLParser):
    def __init__(self):super().__init__();self.in_td=False;self.cell='';self.row=[];self.rows=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('td','th'):self.in_td=True;self.cell=''
    def handle_data(self,data):
        if self.in_td:self.cell+=data
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.in_td:
            self.row.append(' '.join(self.cell.split()));self.in_td=False
        elif tag=='tr' and self.row:
            self.rows.append(self.row);self.row=[]


def page_ratios(target):
    d=datetime.strptime(target,'%Y-%m-%d');slash=f'{d.year}/{d.month}/{d.day}'
    r=requests.get(PAGE,timeout=30,headers=HEADERS,params={'queryStartDate':slash,'queryEndDate':slash});r.raise_for_status()
    p=TableParser();p.feed(r.text)
    for row in p.rows:
        if not row:continue
        rd=row[0].replace(' ','')
        if rd not in (slash,target,target.replace('-','/')):continue
        # Expected: 日期, 賣權成交量, 買權成交量, 成交比率%, 賣權OI, 買權OI, OI比率%
        if len(row)>=7:
            trade=num(row[3]);oi=num(row[6])
            if trade is not None and oi is not None:return trade/100.0,oi/100.0
    return None


def main():
    with open(MARKET,'r',encoding='utf-8') as f:market=json.load(f)
    target=market.get('date')
    ratios=None
    try:ratios=api_ratios(target)
    except Exception as e:print('TAIFEX OpenAPI failed:',e)
    if not ratios:
        try:ratios=page_ratios(target)
        except Exception as e:print('TAIFEX webpage fallback failed:',e)
    if not ratios:raise RuntimeError(f'No exact TAIFEX P/C data for {target}')
    trade,oi=ratios
    market['pc']={'trade':round(trade,4),'oi':round(oi,4),'date':target}
    market.setdefault('sources',{})['taifexPC']=True
    with open(MARKET,'w',encoding='utf-8') as f:json.dump(market,f,ensure_ascii=False,indent=2)
    try:
        with open(HISTORY,'r',encoding='utf-8') as f:hist=json.load(f)
        rows=hist if isinstance(hist,list) else hist.get('records',hist.get('days',[])) if isinstance(hist,dict) else []
        found=False
        for h in rows:
            if h.get('date')==target:
                h['pc']=market['pc'];h.setdefault('sources',{})['taifexPC']=True;found=True;break
        if found:
            with open(HISTORY,'w',encoding='utf-8') as f:json.dump(hist,f,ensure_ascii=False,indent=2)
    except Exception as e:print('history update skipped:',e)
    print(f'P/C updated for {target}: trade={trade:.4f}, oi={oi:.4f}')

if __name__=='__main__':main()
