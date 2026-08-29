(function(){
  const DB_URL='stocks.json';
  const PROXY_URL='https://taiwan-stock-quote-proxy.safecar7249.workers.dev';
  const SYNC_MS=30000;
  const MIGRATION_KEY='tw_quote_sync_migrated_20260821';
  let syncing=false, dbCache=null, dbLoadedAt=0, dbUpdated='';
  const num=v=>{const n=Number(String(v??'').replace(/,/g,''));return Number.isFinite(n)?n:null};
  const nowText=()=>new Date().toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});

  async function loadDB(force=false){
    if(!force&&dbCache&&Date.now()-dbLoadedAt<60000)return dbCache;
    try{
      const r=await fetch(DB_URL+'?ts='+Date.now(),{cache:'no-store'});
      if(!r.ok)throw new Error('stocks '+r.status);
      const j=await r.json();dbCache=j.stocks||{};dbUpdated=j.updated||'';dbLoadedAt=Date.now();return dbCache;
    }catch(e){return dbCache||{}}
  }

  async function proxyQuote(code){
    if(!PROXY_URL)return null;
    try{
      const u=`${PROXY_URL.replace(/\/$/,'')}/quote?code=${encodeURIComponent(code)}&_=${Date.now()}`;
      const r=await fetch(u,{cache:'no-store'});if(!r.ok)return null;
      const q=await r.json();if(!q?.ok||!(num(q.price)>0))return null;
      return {price:num(q.price),prev:num(q.prev),ch:num(q.chg),pc:num(q.pct),open:num(q.open),high:num(q.high),low:num(q.low),name:q.name||'',time:q.time||'',date:q.date||'',source:q.source||'Cloudflare 行情代理',kind:'live-proxy'};
    }catch(e){return null}
  }

  async function misQuote(code){
    for(const market of ['tse','otc']){
      try{
        const u=`https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=${market}_${encodeURIComponent(code)}.tw&json=1&delay=0&_=${Date.now()}`;
        const r=await fetch(u,{cache:'no-store'});if(!r.ok)continue;
        const j=await r.json(), row=Array.isArray(j.msgArray)?j.msgArray.find(x=>String(x.c||'')===String(code)):null;
        if(!row)continue;
        const price=num(row.z), prev=num(row.y);
        if(!(price>0))continue;
        const ch=prev!=null?price-prev:0, pc=prev?ch/prev*100:0;
        return {price,prev,ch,pc,open:num(row.o),high:num(row.h),low:num(row.l),name:row.n||row.nf||'',time:row.t||'',date:row.d||'',source:'TWSE MIS 最新成交（瀏覽器備援）',kind:'live-direct'};
      }catch(e){}
    }
    return null;
  }

  function dbQuote(code,db){
    const x=db?.[code];if(!x||!(num(x.price)>0))return null;
    return {price:num(x.price),prev:null,ch:null,pc:null,name:x.name||'',time:'',date:dbUpdated||'',source:(x.market==='TPEX'?'TPEx':'TWSE')+' 官方盤後資料（非即時）',kind:'close'};
  }

  function migrateLegacyLocks(hs){
    if(localStorage.getItem(MIGRATION_KEY))return false;
    let changed=false;
    for(const h of hs){if(h&&h.manualPrice===true){h.manualPrice=false;changed=true;}if(h&&h.priceLocked==null)h.priceLocked=false;}
    try{localStorage.setItem(MIGRATION_KEY,'1')}catch(e){}
    return changed;
  }

  async function syncHoldings(force=false){
    if(syncing||typeof window.getHoldings!=='function'||typeof window.saveHoldings!=='function')return;
    syncing=true;
    try{
      const hs=window.getHoldings();if(!Array.isArray(hs)||!hs.length)return;
      let changed=migrateLegacyLocks(hs), db=await loadDB(force), ok=0, proxyCount=0, directCount=0;
      for(const h of hs){
        if(!h?.c||h.priceLocked===true)continue;
        let q=await proxyQuote(String(h.c));
        if(!q)q=await misQuote(String(h.c));
        if(!q)q=dbQuote(String(h.c),db);
        if(!q?.price)continue;
        ok++;if(q.kind==='live-proxy')proxyCount++;if(q.kind==='live-direct')directCount++;
        const old=Number(h.p), next=Number(q.price);if(old!==next)changed=true;
        h.p=next;if(q.name)h.n=q.name;if(q.prev!=null){h.prev=q.prev;h.ch=q.ch||0;h.pc=q.pc||0;}
        h.open=q.open??h.open;h.high=q.high??h.high;h.low=q.low??h.low;
        h.quoteTime=q.time||'';h.quoteDate=q.date||'';h.quoteSource=q.source;h.quoteKind=q.kind||'';h.manualPrice=false;
      }
      if(changed)window.saveHoldings(hs);if(typeof window.renderHoldings==='function')window.renderHoldings(hs);
      const st=document.getElementById('lookupStatus');
      if(st&&ok){const closeCount=ok-proxyCount-directCount;st.textContent=`持股行情已同步 ${ok}/${hs.length} 檔｜${nowText()}｜代理 ${proxyCount}、直連 ${directCount}、盤後備援 ${closeCount}｜每30秒刷新`;}
    }catch(e){console.warn('holding quote sync failed',e)}finally{syncing=false}
  }

  const oldEdit=window.editHoldingValue;
  if(typeof oldEdit==='function')window.editHoldingValue=function(i,key,val){const r=oldEdit(i,key,val);if(key==='p'){try{const hs=window.getHoldings();if(hs[i]){hs[i].priceLocked=true;hs[i].manualPrice=false;window.saveHoldings(hs);if(typeof window.renderHoldings==='function')window.renderHoldings(hs)}}catch(e){}}return r;};
  const oldRestore=window.restoreAutoPrice;
  window.restoreAutoPrice=function(i){try{const hs=window.getHoldings();if(hs[i]){hs[i].priceLocked=false;hs[i].manualPrice=false;window.saveHoldings(hs)}}catch(e){}if(typeof oldRestore==='function')oldRestore(i);setTimeout(()=>syncHoldings(true),50);};
  window.syncHoldingQuotes=()=>syncHoldings(true);

  function loadMarketStructure(){if(document.querySelector('script[data-market-structure]'))return;const s=document.createElement('script');s.src='market-structure.js?v=20260825a';s.async=false;s.dataset.marketStructure='1';document.head.appendChild(s);}
  function loadPeScale(){if(document.querySelector('script[data-pe-scale]'))return;const s=document.createElement('script');s.src='pe-scale-ui.js?v=20260826b';s.async=false;s.dataset.peScale='1';document.head.appendChild(s);}
  function start(){loadMarketStructure();loadPeScale();setTimeout(()=>syncHoldings(true),900);setInterval(()=>syncHoldings(false),SYNC_MS);document.addEventListener('visibilitychange',()=>{if(!document.hidden)syncHoldings(true)});window.addEventListener('focus',()=>syncHoldings(true));}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
