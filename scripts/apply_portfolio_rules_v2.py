from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

old_css = ".band-table td:first-child{font-weight:800}.band-table tr:nth-child(2) td:first-child{background:#cfe7ae}.band-table tr:nth-child(3) td:first-child{background:#fff3b0}.band-table tr:nth-child(4) td:first-child{background:#dceafa}.band-table tr:nth-child(5) td:first-child{background:#f3c8c4}.band-table tr:nth-child(6) td:first-child{background:#e79c9c}"
new_css = ".band-table td:first-child{font-weight:800}.band-crazy{background:#e57373!important}.band-expensive{background:#f3c8c4!important}.band-fair-upper{background:#a9c9f5!important}.band-fair{background:#dceafa!important}.band-cheap{background:#dcedbd!important}.band-sale{background:#9fd18b!important}"
s = s.replace(old_css, new_css)

marker = "function renderHoldings(hs){"
helper = "function bandClass(lab){if(lab==='瘋狂價')return 'band-crazy';if(lab==='昂貴價')return 'band-expensive';if(lab==='合理價(上緣)')return 'band-fair-upper';if(lab==='合理價(下緣)'||lab==='合理價')return 'band-fair';if(lab==='便宜價')return 'band-cheap';if(lab==='特價')return 'band-sale';return ''}\n"
if helper not in s:
    s = s.replace(marker, helper + marker)

old_bands = "bands=(h.labels||[]).map((lab,j)=>`<tr><td>${lab}</td><td>${h.v&&h.v[j]!=null?F(h.v[j]):'—'}</td></tr>`).join('')"
new_bands = "bands=(h.labels||[]).map((lab,j)=>`<tr><td class=\"${bandClass(lab)}\">${lab}</td><td>${h.v&&h.v[j]!=null?F(h.v[j]):'—'}</td></tr>`).join('')"
s = s.replace(old_bands, new_bands)

old_summary = "[\"總未實現損益\",(pnl>=0?'+':'')+F(pnl)+' 元']"
new_summary = "[\"總未實現損益\",(pnl>=0?'+':'')+F(pnl)+' 元',pnl>=0?'up':'down']"
s = s.replace(old_summary, new_summary)

old_map = ".map((x,i)=>`<div class=\"card\"><div class=\"label\">${x[0]}</div><div class=\"num\" style=\"font-size:${i===3?'18px':'25px'}\">${x[1]}</div></div>`).join('')"
new_map = ".map((x,i)=>`<div class=\"card\"><div class=\"label\">${x[0]}</div><div class=\"num ${x[2]||''}\" style=\"font-size:${i===3?'18px':'25px'}\">${x[1]}</div></div>`).join('')"
s = s.replace(old_map, new_map)

# Make the cost-basis intention explicit while the backend corporate-action feed is being connected.
s = s.replace("股票資料由 GitHub Actions 每日從證交所官方資料更新；網頁只讀取本站 stocks.json，不再直接跨站查詢。", "股票資料由 GitHub Actions 每日更新。損益：正值紅色、負值綠色。成本均價將採權息事件滾動調整；現金股利另保留原始成本與含息回本成本兩種口徑，避免混淆。")

p.write_text(s, encoding='utf-8')
print('portfolio rules v2 applied')
