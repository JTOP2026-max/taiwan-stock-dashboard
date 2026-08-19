(()=>{
const n=v=>Number.isFinite(Number(v))?Number(v):null;
function set(obj,key,v){if(v!==null&&v!==undefined)obj[key]=v}
function addFreshness(j){
  let el=document.getElementById('marketFreshness');
  if(!el){el=document.createElement('div');el.id='marketFreshness';el.style.cssText='max-width:1500px;margin:8px auto 0;padding:7px 14px;font-size:12px;color:#475467';const m=document.querySelector('main');if(m)m.parentNode.insertBefore(el,m);}
  const s=j.sources||{};
  const status=`TWSE ${s.twse?'✓':'×'}｜法人 ${s.institutions?'✓':'×'}｜P/C ${s.taifexPC?'✓':'×'}｜期貨 ${s.taifexFutures?'✓':'×'}`;
  if(el)el.textContent=`市場資料：${j.date||'—'}｜後端更新 ${j.updated||'—'}｜${status}｜P/C、Fear & Greed 每日盤後更新｜頁面每 5 分鐘自動檢查`;
}
async function runMarket(){
  if(typeof D==='undefined'||typeof render!=='function')return;
  try{
    const r=await fetch('market.json?ts='+Date.now(),{cache:'no-store'}); if(!r.ok)throw Error(r.status);
    const j=await r.json(),c=j.core||{},i=j.inst||{},p=j.pc||{},b=j.breadth||{};
    set(D.core,'idx',n(c.idx)); set(D.core,'chg',n(c.chg)); set(D.core,'pct',n(c.pct));
    if(n(c.volTrillion)!==null)D.core.vol=n(c.volTrillion).toFixed(2)+' 兆';
    D.core.fut=n(c.fut); D.core.futChg=n(c.futChg); D.core.basis=n(c.basis); D.core.futPct=null;
    if(D.core.fut!==null&&D.core.futChg!==null&&D.core.fut-D.core.futChg!==0)D.core.futPct=D.core.futChg/(D.core.fut-D.core.futChg)*100;
    set(D.inst,'t',n(i.total)); set(D.inst,'f',n(i.foreign)); set(D.inst,'tr',n(i.trust)); set(D.inst,'d',n(i.dealer));
    set(D.pc,'trade',n(p.trade)); set(D.pc,'oi',n(p.oi)); set(D.b,'u',n(b.up)); set(D.b,'d',n(b.down)); set(D,'fg',n(j.fearGreed));
    render(); addFreshness(j);
  }catch(e){console.warn('market data unavailable',e)}
}
window.addEventListener('load',runMarket); setTimeout(runMarket,450); setInterval(runMarket,5*60*1000);
})();
