from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

css='.editable-price{width:96px;padding:4px 6px;border:1px solid #9fb0c3;border-radius:6px;text-align:center;font:inherit;background:#fff}.auto-price-btn{margin-top:4px;border:0;background:#eef3fb;color:#345;padding:3px 6px;border-radius:5px;font-size:11px;cursor:pointer}.manual-tag{font-size:10px;color:#b54708;display:block;margin-top:2px}'
if css not in s:
    s=s.replace('.stock-table th,.pe-table th,.band-table th{background:#f6f7f9}.codecell{background:var(--yellow);font-weight:800}.meaningcell{background:var(--lightblue);font-weight:900;font-size:19px}.costcell{background:#fff6c5}',
                '.stock-table th,.pe-table th,.band-table th{background:#f6f7f9}.codecell{background:var(--yellow);font-weight:800}.meaningcell{background:var(--lightblue);font-weight:900;font-size:19px}.costcell{background:#fff6c5}'+css)

anchor="function resetHoldings(){saveHoldings(JSON.parse(JSON.stringify(fallback.h)));renderHoldings(getHoldings());refreshHoldingsFromDB()}"
insert="""function updateHoldingPrice(i,v){let n=Number(v);if(!Number.isFinite(n)||n<=0)return;let h=getHoldings();if(!h[i])return;h[i].p=n;h[i].manualPrice=true;saveHoldings(h);renderHoldings(h)}
function resumeAutoPrice(i){let h=getHoldings();if(!h[i])return;h[i].manualPrice=false;let q=stockDB[h[i].c];if(q&&q.price)h[i].p=q.price;saveHoldings(h);renderHoldings(h)}
"""
if 'function updateHoldingPrice' not in s and anchor in s:
    s=s.replace(anchor,anchor+'\n'+insert)

old="let y={...x,p:q.price??x.p,pe:q.pe??x.pe};"
new="let y={...x,p:(x.manualPrice?x.p:(q.price??x.p)),pe:q.pe??x.pe};"
s=s.replace(old,new)

oldcell='<tr><td class="codecell">${h.c}</td><td>${h.n}</td><td>${F(h.p)}</td></tr>'
newcell='<tr><td class="codecell">${h.c}</td><td>${h.n}</td><td><input class="editable-price" type="number" step="0.01" value="${h.p??\'\'}" onchange="updateHoldingPrice(${i},this.value)">${h.manualPrice?\'<span class="manual-tag">手動價格</span><button class="auto-price-btn" onclick="resumeAutoPrice(\'+i+\')">恢復自動價</button>\':\'<span class="small">自動價，可直接改</span>\'}</td></tr>'
if oldcell not in s:
    raise SystemExit('target price cell not found')
s=s.replace(oldcell,newcell)

status_old='股票資料由 GitHub Actions 每日更新。損益：正值紅色、負值綠色。成本均價將採權息事件滾動調整；現金股利另保留原始成本與含息回本成本兩種口徑，避免混淆。'
status_new='股票資料由 GitHub Actions 每日更新。持股卡片的「股價」可直接點擊輸入；手動修改後會保留，不被每日自動行情覆蓋，並可按「恢復自動價」。損益：正值紅色、負值綠色。'
s=s.replace(status_old,status_new)

p.write_text(s,encoding='utf-8')
print('patched editable holding price')
