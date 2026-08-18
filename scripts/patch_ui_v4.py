from pathlib import Path

root = Path(__file__).resolve().parents[1]
idx = root / 'index.html'
stock_py = root / 'scripts' / 'update_stocks.py'

s = idx.read_text(encoding='utf-8')

# Editable-cell styling.
needle = ".stock-table th,.pe-table th,.band-table th{background:#f6f7f9}.codecell{background:var(--yellow);font-weight:800}.meaningcell{background:var(--lightblue);font-weight:900;font-size:19px}.costcell{background:#fff6c5}"
replacement = needle + ".inline-edit{width:100%;min-width:70px;border:1px solid #b8c4d2;border-radius:6px;padding:5px 6px;text-align:center;background:#fff;font:inherit}.inline-edit:focus{outline:2px solid #9fc2f2;border-color:#5f91d8}.price-edit{font-weight:800}.shares-edit{background:#fff}.avg-edit{background:#fff6c5}"
if needle in s and '.inline-edit{' not in s:
    s = s.replace(needle, replacement, 1)

# Ensure all six valuation colors are explicit.
old_colors = ".band-table td:first-child{font-weight:800}.band-crazy{background:#e57373!important}.band-expensive{background:#f3c8c4!important}.band-fair-upper{background:#a9c9f5!important}.band-fair{background:#dceafa!important}.band-cheap{background:#dcedbd!important}.band-sale{background:#9fd18b!important}"
new_colors = ".band-table td:first-child{font-weight:800}.band-crazy{background:#e57373!important}.band-expensive{background:#f3c8c4!important}.band-fair-upper{background:#8fb8ef!important}.band-fair{background:#dceafa!important}.band-cheap{background:#dcedbd!important}.band-sale{background:#8fcf7b!important}"
s = s.replace(old_colors, new_colors)

# Convert old 5-band fallback holdings to six bands.
s = s.replace('labels:[\"昂貴價\",\"合理價(上緣)\",\"合理價(下緣)\",\"便宜價\",\"特價\"],v:[6675.4,5796.3,4830.2,3864.2,2985.1]', 'labels:[\"瘋狂價\",\"昂貴價\",\"合理價(上緣)\",\"合理價(下緣)\",\"便宜價\",\"特價\"],v:[7245.3,6675.4,5796.3,4830.2,3864.2,2985.1]')
s = s.replace('labels:[\"昂貴價\",\"合理價(上緣)\",\"合理價(下緣)\",\"便宜價\",\"特價\"],v:[5346.8,4642.7,3868.9,3095.1,2391]', 'labels:[\"瘋狂價\",\"昂貴價\",\"合理價(上緣)\",\"合理價(下緣)\",\"便宜價\",\"特價\"],v:[5803.1,5346.8,4642.7,3868.9,3095.1,2391]')
s = s.replace('mults:[1.5,1.25,1,.75,.5],labels:[\"瘋狂價\",\"昂貴價\",\"合理價\",\"便宜價\",\"特價\"],v:[792,660,528,396,264]', 'mults:[1.5,1.25,1.0,0.9,0.75,0.5],labels:[\"瘋狂價\",\"昂貴價\",\"合理價(上緣)\",\"合理價(下緣)\",\"便宜價\",\"特價\"],v:[792,660,528,475.2,396,264]')
s = s.replace('labels:[\"昂貴價\",\"合理價(上緣)\",\"合理價(下緣)\",\"便宜價\",\"特價\"],v:[5315.8,4615.8,3846.5,3077.2,2377.1]', 'labels:[\"瘋狂價\",\"昂貴價\",\"合理價(上緣)\",\"合理價(下緣)\",\"便宜價\",\"特價\"],v:[5769.9,5315.8,4615.8,3846.5,3077.2,2377.1]')

# Default lookup labels if stock JSON has not updated yet.
s = s.replace('let labels=x.labels||[\"昂貴價\",\"合理價(上緣)\",\"合理價(下緣)\",\"便宜價\",\"特價\"]', 'let labels=x.labels||[\"瘋狂價\",\"昂貴價\",\"合理價(上緣)\",\"合理價(下緣)\",\"便宜價\",\"特價\"]')

# Add edit helpers immediately before delete function.
anchor = "function delHolding(i){let h=getHoldings();if(confirm('確定刪除 '+h[i].c+' '+h[i].n+'？')){h.splice(i,1);saveHoldings(h);renderHoldings(h)}}"
helpers = "function editHoldingValue(i,key,val){let n=Number(String(val).replace(/,/g,''));if(!Number.isFinite(n)||n<0){renderHoldings(getHoldings());return}let h=getHoldings();if(!h[i])return;h[i][key]=n;if(key==='p'){h[i].manualPrice=true}saveHoldings(h);renderHoldings(h)}\nfunction restoreAutoPrice(i){let h=getHoldings(),x=h[i],q=x&&stockDB[x.c];if(!x||!q||q.price==null)return;x.p=q.price;x.manualPrice=false;saveHoldings(h);renderHoldings(h)}\n" + anchor
if anchor in s and 'function editHoldingValue(' not in s:
    s = s.replace(anchor, helpers, 1)

# Do not overwrite manually keyed price during daily DB refresh.
s = s.replace("let y={...x,p:q.price??x.p,pe:q.pe??x.pe};", "let y={...x,p:x.manualPrice?x.p:(q.price??x.p),pe:q.pe??x.pe};")

# Replace table display cells with directly editable inputs.
s = s.replace('<td>${F(h.p)}</td></tr><tr><th>持有股數</th><th>成本均價</th><th>成本</th></tr><tr><td>${F(h.s)}</td><td class=\"costcell\">${F(h.a)}</td><td>${F(cost)}</td>', '<td><input class=\"inline-edit price-edit\" type=\"number\" step=\"0.01\" value=\"${h.p??0}\" onchange=\"editHoldingValue(${i},\\\'p\\\',this.value)\" title=\"可直接輸入股價\"></td></tr><tr><th>持有股數</th><th>成本均價</th><th>成本</th></tr><tr><td><input class=\"inline-edit shares-edit\" type=\"number\" step=\"1\" value=\"${h.s??0}\" onchange=\"editHoldingValue(${i},\\\'s\\\',this.value)\" title=\"可直接輸入持有股數\"></td><td class=\"costcell\"><input class=\"inline-edit avg-edit\" type=\"number\" step=\"0.01\" value=\"${h.a??0}\" onchange=\"editHoldingValue(${i},\\\'a\\\',this.value)\" title=\"可直接輸入成本均價\"></td><td>${F(cost)}</td>')

# Assign color class by meaning, rather than row position.
old_bands = "bands=(h.labels||[]).map((lab,j)=>`<tr><td>${lab}</td><td>${h.v&&h.v[j]!=null?F(h.v[j]):'—'}</td></tr>`).join('')"
new_bands = "bands=(h.labels||[]).map((lab,j)=>{let cls=lab.includes('瘋狂')?'band-crazy':lab.includes('昂貴')?'band-expensive':lab.includes('上緣')?'band-fair-upper':lab.includes('下緣')||lab==='合理價'?'band-fair':lab.includes('便宜')?'band-cheap':lab.includes('特價')?'band-sale':'';return `<tr><td class=\"${cls}\">${lab}</td><td>${h.v&&h.v[j]!=null?F(h.v[j]):'—'}</td></tr>`}).join('')"
s = s.replace(old_bands, new_bands)

# Footer marker for manual price restore.
old_footer = "<span class=\"small\">${h.autoModel===false?'估值模型：自訂／預估 EPS':'估值模型：每日自動更新'}${h.historyDays?'｜歷史 '+h.historyDays+' 日':''}</span><button class=\"danger\" onclick=\"delHolding(${i})\">刪除／汰弱</button>"
new_footer = "<span class=\"small\">${h.autoModel===false?'估值模型：自訂／預估 EPS':'估值模型：每日自動更新'}${h.historyDays?'｜歷史 '+h.historyDays+' 日':''}${h.manualPrice?'｜手動股價':''}</span><span>${h.manualPrice?`<button class=\"btn secondary\" style=\"padding:5px 8px;margin-right:6px\" onclick=\"restoreAutoPrice(${i})\">恢復自動價</button>`:''}<button class=\"danger\" onclick=\"delHolding(${i})\">刪除／汰弱</button></span>"
s = s.replace(old_footer, new_footer)

# Price meaning supports six levels.
old_pm = "function priceMeaning(h){if(!h.v||h.v.length<5)return'尚未設定';let a=[...h.v].sort((x,y)=>x-y);if(h.p<=a[0])return'特價';if(h.p<=a[1])return'便宜價';if(h.p<=a[3])return'合理價';return'昂貴價'}"
new_pm = "function priceMeaning(h){if(!h.v||h.v.length<5)return'尚未設定';let a=[...h.v].filter(Number.isFinite).sort((x,y)=>x-y);if(a.length<5)return'尚未設定';if(h.p<=a[0])return'特價';if(h.p<=a[1])return'便宜價';if(a.length>=6){if(h.p<=a[2])return'合理價(下緣)';if(h.p<=a[3])return'合理價(上緣)';if(h.p<=a[4])return'昂貴價';return'瘋狂價'}if(h.p<=a[3])return'合理價';return'昂貴價'}"
s = s.replace(old_pm, new_pm)

# Clarify direct editing in UI status.
s = s.replace('成本均價將採權息事件滾動調整；現金股利另保留原始成本與含息回本成本兩種口徑，避免混淆。', '股價、持有股數、成本均價都可直接點欄位輸入並立即重算。成本均價後續仍可由權息事件自動滾動調整。')

idx.write_text(s, encoding='utf-8')

# Backend: every auto stock now emits six valuation levels, including crazy price.
p = stock_py.read_text(encoding='utf-8')
p = p.replace("ratios = [1.382, 1.20, 1.00, 0.80, 0.618]", "ratios = [1.50, 1.382, 1.20, 1.00, 0.80, 0.618]")
p = p.replace("labels = ['昂貴價','合理價(上緣)','合理價(下緣)','便宜價','特價']", "labels = ['瘋狂價','昂貴價','合理價(上緣)','合理價(下緣)','便宜價','特價']")
stock_py.write_text(p, encoding='utf-8')
print('patched index.html and update_stocks.py')
