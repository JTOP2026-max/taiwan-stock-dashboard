(function(){
  const DB_URL='stocks.json';
  const SYNC_MS=60000;
  const MIGRATION_KEY='tw_quote_sync_migrated_20260821';
  let syncing=false, dbCache=null, dbLoadedAt=0;
  const num=v=>{const n=Number(String(v??'').replace(/,/g,''));return Number.isFinite(n)?n:null};
  const nowText=()=>new Date().toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});

  async function loadDB(force=false){
    if(!force&&dbCache&&Date.now()-dbLoadedAt<60000)return dbCache;
    try{
      const r=await fetch(DB_URL+'?ts='+Date.now(),{cache:'no-store'});
      if(!r.ok)throw new Error('stocks '+r.status);
      const j=await r.json();dbCache=j.stocks||{};dbLoadedAt=Date.now();return dbCache;
    }catch(e){return dbCache||{}}
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
        return {price,prev,ch,pc,open:num(row.o),high:num(row.h),low:num(row.l),name:row.n||row.nf||'',time:row.t||'',date:row.d||'',source:'TWSE MIS 最新成交'};
      }catch(e){}
    }
    return null;
  }

  function dbQuote(code,db){
    const x=db?.[code];if(!x||!(num(x.price)>0))return null;
    return {price:num(x.price),prev:null,ch:null,pc:null,name:x.name||'',time:'',date:'',source:(x.market==='TPEX'?'TPEx':'TWSE')+' 官方盤後資料'};
  }

  function migrateLegacyLocks(hs){
    if(localStorage.getItem(MIGRATION_KEY))return false;
    let changed=false;
    for(const h of hs){
      if(h&&h.manualPrice===true){h.manualPrice=false;changed=true;}
      if(h&&h.priceLocked==null)h.priceLocked=false;
    }
    try{localStorage.setItem(MIGRATION_KEY,'1')}catch(e){}
    return changed;
  }

  async function syncHoldings(force=false){
    if(syncing||typeof window.getHoldings!=='function'||typeof window.saveHoldings!=='function')return;
    syncing=true;
    try{
      const hs=window.getHoldings();if(!Array.isArray(hs)||!hs.length)return;
      let changed=migrateLegacyLocks(hs), db=await loadDB(force), ok=0;
      for(const h of hs){
        if(!h?.c||h.priceLocked===true)continue;
        let q=await misQuote(String(h.c));
        if(!q)q=dbQuote(String(h.c),db);
        if(!q?.price)continue;
        ok++;
        const old=Number(h.p), next=Number(q.price);
        if(old!==next)changed=true;
        h.p=next;
        if(q.name)h.n=q.name;
        if(q.prev!=null){h.prev=q.prev;h.ch=q.ch||0;h.pc=q.pc||0;}
        h.open=q.open??h.open;h.high=q.high??h.high;h.low=q.low??h.low;
        h.quoteTime=q.time||nowText();h.quoteDate=q.date||'';h.quoteSource=q.source;
        h.manualPrice=false;
      }
      if(changed)window.saveHoldings(hs);
      if(typeof window.renderHoldings==='function')window.renderHoldings(hs);
      const st=document.getElementById('lookupStatus');
      if(st&&ok)st.textContent=`持股行情已同步 ${ok}/${hs.length} 檔｜${nowText()}｜MIS 優先，官方盤後資料備援`;
    }catch(e){console.warn('holding quote sync failed',e)}finally{syncing=false}
  }

  // Existing saved holdings used manualPrice as a permanent lock. Replace that with an explicit priceLocked flag.
  const oldEdit=window.editHoldingValue;
  if(typeof oldEdit==='function'){
    window.editHoldingValue=function(i,key,val){
      const r=oldEdit(i,key,val);
      if(key==='p'){
        try{const hs=window.getHoldings();if(hs[i]){hs[i].priceLocked=true;hs[i].manualPrice=false;window.saveHoldings(hs);if(typeof window.renderHoldings==='function')window.renderHoldings(hs)}}catch(e){}
      }
      return r;
    };
  }
  const oldRestore=window.restoreAutoPrice;
  window.restoreAutoPrice=function(i){
    try{const hs=window.getHoldings();if(hs[i]){hs[i].priceLocked=false;hs[i].manualPrice=false;window.saveHoldings(hs)}}catch(e){}
    if(typeof oldRestore==='function')oldRestore(i);
    setTimeout(()=>syncHoldings(true),50);
  };
  window.syncHoldingQuotes=()=>syncHoldings(true);

  function start(){setTimeout(()=>syncHoldings(true),900);setInterval(()=>syncHoldings(false),SYNC_MS);document.addEventListener('visibilitychange',()=>{if(!document.hidden)syncHoldings(true)});window.addEventListener('focus',()=>syncHoldings(true));}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
