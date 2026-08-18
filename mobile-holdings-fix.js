(function(){
  const $=id=>document.getElementById(id);
  async function ensureDB(){
    try{
      if(typeof stockDB!=='undefined' && stockDB && Object.keys(stockDB).length) return true;
      const r=await fetch('stocks.json?ts='+Date.now(),{cache:'no-store'});
      if(!r.ok) throw new Error('HTTP '+r.status);
      const j=await r.json();
      stockDB=j.stocks||{};
      return Object.keys(stockDB).length>0;
    }catch(e){
      if($('lookupStatus')) $('lookupStatus').textContent='手機載入股票資料失敗，請重新整理後再試。';
      return false;
    }
  }
  window.lookupStock=async function(){
    const c=($('code')?.value||'').trim();
    if(!/^\d{4,6}$/.test(c)){
      if($('lookupStatus')) $('lookupStatus').textContent='請輸入正確股票代碼';
      return false;
    }
    if(!(await ensureDB())) return false;
    const x=stockDB[c];
    if(!x){
      lookupCache=null;
      if($('lookupStatus')) $('lookupStatus').textContent=`資料庫目前找不到 ${c}`;
      return false;
    }
    const labels=x.labels||['瘋狂價','昂貴價','合理價(上緣)','合理價(下緣)','便宜價','特價'];
    const vals=x.values||[];
    const bands=x.peBands||[];
    lookupCache={c,n:x.name,desc:(x.market||'台股')+'｜自動資料',p:x.price,ch:0,pc:0,s:+($('shares')?.value||0),a:+($('avg')?.value||0),e:x.eps,pe:x.pe,ref:new Date().toLocaleDateString('zh-TW'),refLabel:'近4季EPS',basePE:x.basePE,peBands:bands,labels,v:vals,autoModel:true,historyDays:x.historyDays||0};
    if($('name')) $('name').value=x.name||'';
    if($('price')) $('price').value=typeof F==='function'?F(x.price):(x.price??'');
    if($('eps')) $('eps').value=typeof F==='function'?F(x.eps):(x.eps??'');
    if($('pe60')) $('pe60').value=typeof F==='function'?F(x.basePE):(x.basePE??'');
    if($('lookupStatus')) $('lookupStatus').textContent=`完成：${c} ${x.name}｜可直接按「＋新增持股」`;
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
    try{
      saveHoldings(h);
    }catch(e){
      if($('lookupStatus')) $('lookupStatus').textContent='手機瀏覽器無法儲存持股，請確認不是無痕／私密模式。';
      return;
    }
    renderHoldings(h);
    if($('lookupStatus')) $('lookupStatus').textContent='已新增 '+lookupCache.c+' '+lookupCache.n;
    ['code','name','price','eps','pe60','shares','avg'].forEach(id=>{const el=$(id);if(el)el.value='';});
    lookupCache=null;
  };
  function tuneMobile(){
    document.querySelectorAll('button').forEach(b=>{b.type='button';b.style.touchAction='manipulation';});
    const c=$('code'); if(c){c.setAttribute('inputmode','numeric');c.setAttribute('autocomplete','off');}
    const s=$('shares'); if(s)s.setAttribute('inputmode','decimal');
    const a=$('avg'); if(a)a.setAttribute('inputmode','decimal');
    if($('lookupStatus')) $('lookupStatus').textContent+='｜手機版：輸入代碼、股數、成本後，可直接按「＋新增持股」。';
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',tuneMobile); else tuneMobile();
})();