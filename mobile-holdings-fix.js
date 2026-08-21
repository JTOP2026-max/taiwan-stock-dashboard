(function(){
  const $=id=>document.getElementById(id);
  const fmt=v=>typeof F==='function'?F(v):(v??'');
  const labels6=['瘋狂價','昂貴價','合理價(上緣)','合理價(下緣)','便宜價','特價'];
  const SETTINGS_KEY='tw_stock_dashboard_holding_settings_v1';
  const DEFAULT_SETTINGS={feeRate:0.1425,taxRate:0.3,financingRate:2.6,dailyUpdate:true};

  function numberOrNull(v){
    const n=Number(String(v??'').replace(/,/g,''));
    return Number.isFinite(n)?n:null;
  }
  function normalizeTime(v){
    if(!v) return '';
    const s=String(v).trim();
    return s.length>=5?s:'';
  }
  function loadSettings(){
    try{return {...DEFAULT_SETTINGS,...JSON.parse(localStorage.getItem(SETTINGS_KEY)||'{}')}}catch(e){return {...DEFAULT_SETTINGS}}
  }
  function saveSettings(s){
    try{localStorage.setItem(SETTINGS_KEY,JSON.stringify(s));return true}catch(e){return false}
  }
  function trendClass(v){return v>0?'quote-up':v<0?'quote-down':'quote-flat'}
  function trendText(ch,pc){
    ch=Number(ch||0);pc=Number(pc||0);
    if(ch>0)return `▲ ${fmt(Math.abs(ch))} (${Math.abs(pc).toFixed(2)}%)`;
    if(ch<0)return `▼ ${fmt(Math.abs(ch))} (${Math.abs(pc).toFixed(2)}%)`;
    return '平盤';
  }

  async function loadDB(){
    try{
      if(typeof stockDB!=='undefined' && stockDB && Object.keys(stockDB).length) return stockDB;
      const r=await fetch('stocks.json?ts='+Date.now(),{cache:'no-store'});
      if(!r.ok) return {};
      const j=await r.json();
      if(typeof stockDB!=='undefined') stockDB=j.stocks||{};
      return j.stocks||{};
    }catch(e){ return {}; }
  }

  async function directMIS(code){
    const markets=['tse','otc'];
    for(const market of markets){
      try{
        const url=`https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=${market}_${code}.tw&json=1&delay=0&_=${Date.now()}`;
        const r=await fetch(url,{cache:'no-store',mode:'cors'});
        if(!r.ok) continue;
        const j=await r.json();
        const row=Array.isArray(j.msgArray)&&j.msgArray[0];
        if(!row || String(row.c||'')!==code) continue;
        const price=numberOrNull(row.z);
        if(!(price>0)) continue;
        const prev=numberOrNull(row.y);
        const chg=prev?price-prev:0;
        const pc=prev?chg/prev*100:0;
        return {code,name:row.n||row.nf||code,market:market==='tse'?'TWSE':'TPEX',price,chg,pc,prev,
          open:numberOrNull(row.o),high:numberOrNull(row.h),low:numberOrNull(row.l),
          quoteTime:normalizeTime(row.t),quoteDate:String(row.d||''),source:'TWSE MIS 最新成交',kind:'live'};
      }catch(e){}
    }
    return null;
  }

  async function officialClose(code){
    try{
      const r=await fetch('https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes',{cache:'no-store'});
      if(r.ok){
        const arr=await r.json();
        if(Array.isArray(arr)){
          const row=arr.find(x=>String(x.SecuritiesCompanyCode||x.SecuritiesCode||x.Code||'').trim()===code);
          if(row){
            const price=numberOrNull(row.Close ?? row.ClosingPrice ?? row.ClosePrice);
            const prev=numberOrNull(row.PreviousClose ?? row.ReferencePrice ?? row.RefPrice);
            if(price>0){
              const chg=prev?price-prev:0, pc=prev?chg/prev*100:0;
              return {code,name:row.CompanyName||row.SecuritiesName||row.Name||code,market:'TPEX',price,prev,chg,pc,
                open:numberOrNull(row.Open),high:numberOrNull(row.High),low:numberOrNull(row.Low),source:'TPEx 官方收盤',kind:'close'};
            }
          }
        }
      }
    }catch(e){}
    try{
      const r=await fetch('https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL',{cache:'no-store'});
      if(r.ok){
        const arr=await r.json();
        if(Array.isArray(arr)){
          const row=arr.find(x=>String(x.Code||'').trim()===code);
          if(row){
            const price=numberOrNull(row.ClosingPrice), prev=numberOrNull(row.MonthlyAveragePrice);
            if(price>0) return {code,name:row.Name||code,market:'TWSE',price,prev:null,chg:0,pc:0,
              open:numberOrNull(row.OpeningPrice),high:numberOrNull(row.HighestPrice),low:numberOrNull(row.LowestPrice),source:'TWSE 官方收盤',kind:'close'};
          }
        }
      }
    }catch(e){}
    return null;
  }

  async function getBestQuote(code){
    const live=await directMIS(code);
    if(live) return live;
    return await officialClose(code);
  }

  function makeLookup(code,x,quote){
    const model=x||{}, price=(quote&&quote.price)||model.price||0;
    const name=(quote&&quote.name)||model.name||code, market=(quote&&quote.market)||model.market||'台股';
    const eps=numberOrNull(model.eps), basePE=numberOrNull(model.basePE);
    return {c:code,n:name,desc:`${market}｜${quote?quote.source:'自動資料'}`,p:price,ch:(quote&&quote.chg)||0,pc:(quote&&quote.pc)||0,
      prev:quote&&quote.prev,open:quote&&quote.open,high:quote&&quote.high,low:quote&&quote.low,
      quoteKind:quote&&quote.kind,quoteTime:quote&&quote.quoteTime,quoteSource:quote&&quote.source,
      s:+($('shares')?.value||0),a:+($('avg')?.value||0),e:eps,pe:numberOrNull(model.pe),ref:new Date().toLocaleDateString('zh-TW'),
      refLabel:eps?'近4季EPS':'行情資料',basePE,peBands:Array.isArray(model.peBands)?model.peBands:[],
      labels:Array.isArray(model.labels)&&model.labels.length===6?model.labels:labels6,v:Array.isArray(model.values)?model.values:[],
      autoModel:!!(basePE&&eps),historyDays:model.historyDays||0};
  }

  window.lookupStock=async function(){
    const c=($('code')?.value||'').trim();
    if(!/^\d{4,6}$/.test(c)){if($('lookupStatus'))$('lookupStatus').textContent='請輸入正確股票代碼';return false}
    if($('lookupStatus')) $('lookupStatus').textContent=`查詢 ${c} 中…`;
    const db=await loadDB(), model=db[c]||null;
    let quote=null; try{quote=await getBestQuote(c)}catch(e){}
    if(!quote&&!model){lookupCache=null;if($('lookupStatus'))$('lookupStatus').textContent=`找不到 ${c}；請確認代碼或稍後再試。`;return false}
    lookupCache=makeLookup(c,model,quote);
    if($('name')) $('name').value=lookupCache.n||'';
    if($('price')) $('price').value=fmt(lookupCache.p);
    if($('eps')) $('eps').value=lookupCache.e==null?'—':fmt(lookupCache.e);
    if($('pe60')) $('pe60').value=lookupCache.basePE==null?'累積中':fmt(lookupCache.basePE);
    const source=quote?quote.source:(model?'背景資料庫':''), t=quote&&quote.quoteTime?` ${quote.quoteTime}`:'';
    const modelMsg=model&&lookupCache.basePE?`｜估值模型 ${lookupCache.historyDays||0} 日`:'｜估值資料累積中';
    if($('lookupStatus')) $('lookupStatus').textContent=`完成：${c} ${lookupCache.n}｜${source}${t}${modelMsg}｜可直接新增持股`;
    return true;
  };

  window.addHolding=async function(){
    const c=($('code')?.value||'').trim();
    if(!lookupCache||lookupCache.c!==c){const ok=await window.lookupStock();if(!ok)return}
    let h;try{h=getHoldings()}catch(e){h=[]}
    if(h.some(x=>x.c===lookupCache.c)){if($('lookupStatus'))$('lookupStatus').textContent='這檔股票已在持股清單';return}
    lookupCache.s=+($('shares')?.value||0);lookupCache.a=+($('avg')?.value||0);h.push({...lookupCache});
    try{saveHoldings(h)}catch(e){if($('lookupStatus'))$('lookupStatus').textContent='瀏覽器無法儲存持股，請確認不是無痕／私密模式。';return}
    renderHoldings(h);if($('lookupStatus'))$('lookupStatus').textContent='已新增 '+lookupCache.c+' '+lookupCache.n;
    ['code','name','price','eps','pe60','shares','avg'].forEach(id=>{const el=$(id);if(el)el.value=''});lookupCache=null;
  };

  function injectStyle(){
    if(document.getElementById('holdingPolishStyle'))return;
    const s=document.createElement('style');s.id='holdingPolishStyle';s.textContent=`
      .holding-card{border:1px solid #d9e2ef!important;border-radius:16px!important;box-shadow:0 8px 24px rgba(20,55,95,.08)!important;background:linear-gradient(180deg,#fff 0%,#fcfdff 100%)!important}
      .holding-title{background:linear-gradient(90deg,#f7fbff,#eef5ff)!important;color:#183153!important;font-weight:900!important;letter-spacing:.3px!important}
      .stock-table th,.pe-table th,.band-table th{background:#f7f9fc!important;color:#334155!important}
      .price-edit{font-weight:900!important;font-size:16px!important;border-radius:8px!important}
      .quote-up{color:#df1f26!important}.quote-down{color:#16834b!important}.quote-flat{color:#111827!important}
      .quote-badge{display:inline-flex;align-items:center;gap:5px;margin-top:5px;padding:3px 8px;border-radius:999px;font-size:11px;font-weight:800;background:#f4f7fb;border:1px solid #e3e9f1}
      .quote-meta{font-size:11px;color:#64748b;margin-top:4px;line-height:1.5}
      .holding-settings{margin:12px 0 16px;padding:14px 16px;border:1px solid #dce6f3;border-radius:14px;background:linear-gradient(180deg,#ffffff,#f9fcff);box-shadow:0 5px 16px rgba(20,55,95,.05)}
      .holding-settings-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}.holding-settings-title{font-weight:900;color:#16834b}
      .holding-settings-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;align-items:end}.holding-settings label{font-size:12px;color:#475569;font-weight:700;display:block;margin-bottom:5px}
      .holding-settings input{width:100%;padding:8px 9px;border:1px solid #cfd9e6;border-radius:8px;background:#fff;text-align:center}.setting-switch{display:flex;align-items:center;gap:8px;height:36px}.setting-switch input{width:auto}
      .save-setting{background:#16a34a;color:#fff;border:0;border-radius:8px;padding:9px 14px;font-weight:900;cursor:pointer}.setting-note{font-size:11px;color:#64748b;margin-top:7px}
      .meaningcell{background:linear-gradient(180deg,#eaf3ff,#dceafa)!important;color:#1e3a5f!important}
      @media(max-width:900px){.holding-settings-grid{grid-template-columns:1fr 1fr}.holding-settings{overflow:hidden}}
    `;document.head.appendChild(s);
  }

  function ensureSettingsPanel(){
    if(document.getElementById('holdingSettingsPanel'))return;
    const anchor=document.getElementById('holdings');if(!anchor)return;
    const st=loadSettings(), box=document.createElement('section');box.id='holdingSettingsPanel';box.className='holding-settings';
    box.innerHTML=`<div class="holding-settings-head"><div class="holding-settings-title">♻ 持股設定</div><div class="small">修改後會套用到持股估值顯示</div></div>
      <div class="holding-settings-grid">
        <div><label>交易手續費率 (%)</label><input id="settingFee" type="number" step="0.0001" value="${st.feeRate}"></div>
        <div><label>交易稅率 (%)</label><input id="settingTax" type="number" step="0.01" value="${st.taxRate}"></div>
        <div><label>融資利率／年 (%)</label><input id="settingFinancing" type="number" step="0.1" value="${st.financingRate}"></div>
        <div><label>每日更新</label><div class="setting-switch"><input id="settingDaily" type="checkbox" ${st.dailyUpdate?'checked':''}><span>${st.dailyUpdate?'開啟':'關閉'}</span></div></div>
        <div></div><div><button id="saveHoldingSettings" class="save-setting">💾 儲存設定</button></div>
      </div><div class="setting-note">預設手續費 0.1425%、交易稅 0.3%、融資利率 2.6%。後續可再接入券商實際折扣與融資條件。</div>`;
    anchor.parentNode.insertBefore(box,anchor);
    const daily=$('settingDaily');if(daily)daily.addEventListener('change',()=>{daily.nextElementSibling.textContent=daily.checked?'開啟':'關閉'});
    const save=$('saveHoldingSettings');if(save)save.addEventListener('click',()=>{
      const n={feeRate:+($('settingFee').value||0),taxRate:+($('settingTax').value||0),financingRate:+($('settingFinancing').value||0),dailyUpdate:!!$('settingDaily').checked};
      saveSettings(n);save.textContent='✓ 已儲存';setTimeout(()=>save.textContent='💾 儲存設定',1200);
    });
  }

  function decorateHoldingCards(hs){
    const cards=[...document.querySelectorAll('.holding-card')];
    cards.forEach((card,i)=>{
      const h=hs&&hs[i];if(!h)return;
      const cls=trendClass(Number(h.ch||0));
      const price=card.querySelector('.price-edit');if(price){price.classList.remove('quote-up','quote-down','quote-flat');price.classList.add(cls)}
      const meaning=card.querySelector('.meaningcell');if(meaning){
        const old=meaning.querySelector('.quote-extra');if(old)old.remove();
        const extra=document.createElement('div');extra.className='quote-extra';
        extra.innerHTML=`<div class="quote-badge ${cls}">${trendText(h.ch,h.pc)}</div><div class="quote-meta">${h.quoteSource||h.desc||'行情資料'}${h.quoteTime?'｜'+h.quoteTime:''}${h.prev?`<br>昨收 ${fmt(h.prev)}`:''}${h.open?`｜開 ${fmt(h.open)}`:''}${h.high?`｜高 ${fmt(h.high)}`:''}${h.low?`｜低 ${fmt(h.low)}`:''}</div>`;
        meaning.appendChild(extra);
      }
    });
  }

  const originalRender=window.renderHoldings;
  if(typeof originalRender==='function'){
    window.renderHoldings=function(hs){const r=originalRender(hs);try{decorateHoldingCards(hs)}catch(e){}return r};
  }

  async function refreshExistingHoldings(){
    const settings=loadSettings();if(!settings.dailyUpdate)return;
    let hs=[];try{hs=getHoldings()}catch(e){return}
    if(!Array.isArray(hs)||!hs.length)return;
    let changed=false;
    for(const h of hs){
      if(!h||!h.c||h.manualPrice)continue;
      try{
        const q=await getBestQuote(String(h.c));
        if(q&&q.price>0){
          if(q.price!==h.p||q.chg!==h.ch||q.pc!==h.pc)changed=true;
          h.p=q.price;h.ch=q.chg||0;h.pc=q.pc||0;h.prev=q.prev||null;h.open=q.open||null;h.high=q.high||null;h.low=q.low||null;
          h.quoteKind=q.kind;h.quoteTime=q.quoteTime||'';h.quoteSource=q.source||'';
        }
      }catch(e){}
    }
    try{if(changed)saveHoldings(hs);renderHoldings(hs)}catch(e){}
  }

  function tuneMobile(){
    injectStyle();ensureSettingsPanel();
    document.querySelectorAll('button').forEach(b=>{b.type='button';b.style.touchAction='manipulation'});
    const c=$('code');if(c){c.setAttribute('inputmode','numeric');c.setAttribute('autocomplete','off')}
    const s=$('shares');if(s)s.setAttribute('inputmode','decimal');const a=$('avg');if(a)a.setAttribute('inputmode','decimal');
    if($('lookupStatus'))$('lookupStatus').textContent='行情優先讀 MIS 最新成交；無成交價時改讀 TWSE/TPEx 官方收盤。股價：紅漲、綠跌、黑平盤。';
    const top=document.querySelector('header .top>div:last-child');
    if(top&&!document.getElementById('txoPageLink')){const link=document.createElement('a');link.id='txoPageLink';link.href='options-journal.html';link.className='btn secondary';link.style.cssText='text-decoration:none;margin-left:6px;font-size:12px;opacity:.72';link.textContent='結算紀錄';top.appendChild(link)}
    try{decorateHoldingCards(getHoldings())}catch(e){}
    setTimeout(refreshExistingHoldings,700);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',tuneMobile);else tuneMobile();
})();