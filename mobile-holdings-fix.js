(function(){
  const $=id=>document.getElementById(id);
  const fmt=v=>typeof F==='function'?F(v):(v??'');
  const labels6=['瘋狂價','昂貴價','合理價(上緣)','合理價(下緣)','便宜價','特價'];

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

  function numberOrNull(v){
    const n=Number(String(v??'').replace(/,/g,''));
    return Number.isFinite(n)?n:null;
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
        const price=numberOrNull(row.z) ?? numberOrNull(row.y);
        if(!(price>0)) continue;
        const ref=numberOrNull(row.y);
        const chg=ref?price-ref:0;
        const pc=ref?chg/ref*100:0;
        return {
          code,
          name:row.n||row.nf||code,
          market:market==='tse'?'TWSE':'TPEX',
          price, chg, pc,
          source:'TWSE MIS'
        };
      }catch(e){}
    }
    return null;
  }

  function makeLookup(code,x,live){
    const model=x||{};
    const price=(live&&live.price)||model.price||0;
    const name=(live&&live.name)||model.name||code;
    const market=(live&&live.market)||model.market||'台股';
    const eps=numberOrNull(model.eps);
    const basePE=numberOrNull(model.basePE);
    const vals=Array.isArray(model.values)?model.values:[];
    const bands=Array.isArray(model.peBands)?model.peBands:[];
    return {
      c:code,n:name,desc:`${market}｜${live?'即時/延遲行情':'自動資料'}`,
      p:price,ch:(live&&live.chg)||0,pc:(live&&live.pc)||0,
      s:+($('shares')?.value||0),a:+($('avg')?.value||0),
      e:eps,pe:numberOrNull(model.pe),ref:new Date().toLocaleDateString('zh-TW'),
      refLabel:eps?'近4季EPS':'行情資料',basePE,peBands:bands,
      labels:Array.isArray(model.labels)&&model.labels.length===6?model.labels:labels6,
      v:vals,autoModel:!!(basePE&&eps),historyDays:model.historyDays||0
    };
  }

  window.lookupStock=async function(){
    const c=($('code')?.value||'').trim();
    if(!/^\d{4,6}$/.test(c)){
      if($('lookupStatus')) $('lookupStatus').textContent='請輸入正確股票代碼';
      return false;
    }
    if($('lookupStatus')) $('lookupStatus').textContent=`查詢 ${c} 中…`;

    const db=await loadDB();
    const model=db[c]||null;
    let live=null;
    try{ live=await directMIS(c); }catch(e){}

    if(!live && !model){
      lookupCache=null;
      if($('lookupStatus')) $('lookupStatus').textContent=`找不到 ${c}；請確認代碼或稍後再試。`;
      return false;
    }

    lookupCache=makeLookup(c,model,live);
    if($('name')) $('name').value=lookupCache.n||'';
    if($('price')) $('price').value=fmt(lookupCache.p);
    if($('eps')) $('eps').value=lookupCache.e==null?'—':fmt(lookupCache.e);
    if($('pe60')) $('pe60').value=lookupCache.basePE==null?'累積中':fmt(lookupCache.basePE);

    const source=live?'TWSE MIS 行情':(model?'背景資料庫':'');
    const modelMsg=model&&lookupCache.basePE?`｜估值模型 ${lookupCache.historyDays||0} 日`:'｜估值資料累積中';
    if($('lookupStatus')) $('lookupStatus').textContent=`完成：${c} ${lookupCache.n}｜${source}${modelMsg}｜可直接新增持股`;
    return true;
  };

  window.addHolding=async function(){
    const c=($('code')?.value||'').trim();
    if(!lookupCache || lookupCache.c!==c){
      const ok=await window.lookupStock();
      if(!ok) return;
    }
    let h;
    try{ h=getHoldings(); }catch(e){ h=[]; }
    if(h.some(x=>x.c===lookupCache.c)){
      if($('lookupStatus')) $('lookupStatus').textContent='這檔股票已在持股清單';
      return;
    }
    lookupCache.s=+($('shares')?.value||0);
    lookupCache.a=+($('avg')?.value||0);
    h.push({...lookupCache});
    try{saveHoldings(h)}catch(e){
      if($('lookupStatus')) $('lookupStatus').textContent='瀏覽器無法儲存持股，請確認不是無痕／私密模式。';
      return;
    }
    renderHoldings(h);
    if($('lookupStatus')) $('lookupStatus').textContent='已新增 '+lookupCache.c+' '+lookupCache.n;
    ['code','name','price','eps','pe60','shares','avg'].forEach(id=>{const el=$(id);if(el)el.value='';});
    lookupCache=null;
  };

  function tuneMobile(){
    document.querySelectorAll('button').forEach(b=>{b.type='button';b.style.touchAction='manipulation';});
    const c=$('code');if(c){c.setAttribute('inputmode','numeric');c.setAttribute('autocomplete','off')}
    const s=$('shares');if(s)s.setAttribute('inputmode','decimal');
    const a=$('avg');if(a)a.setAttribute('inputmode','decimal');
    if($('lookupStatus')) $('lookupStatus').textContent='查股優先讀 TWSE MIS 行情；stocks.json 僅負責估值/歷史快取。即使背景資料庫故障，仍可新增持股。';
    const top=document.querySelector('header .top>div:last-child');
    if(top&&!document.getElementById('txoPageLink')){
      const link=document.createElement('a');
      link.id='txoPageLink';link.href='options-journal.html';link.className='btn secondary';
      link.style.cssText='text-decoration:none;margin-left:6px;font-size:12px;opacity:.72';
      link.textContent='結算紀錄';
      top.appendChild(link);
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',tuneMobile);else tuneMobile();
})();