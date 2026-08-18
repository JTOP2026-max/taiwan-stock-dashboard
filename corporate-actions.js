(()=>{
const TRACKING_START='2026-08-18';
const safeNum=x=>Number.isFinite(Number(x))?Number(x):0;
function migrateHolding(h){
  if(h.origShares==null)h.origShares=safeNum(h.s);
  if(h.origAvg==null)h.origAvg=safeNum(h.a);
  if(h.origCost==null)h.origCost=h.origShares*h.origAvg;
  if(h.adjustedCost==null)h.adjustedCost=safeNum(h.a)*safeNum(h.s);
  if(h.cashReceived==null)h.cashReceived=0;
  if(h.stockSharesAdded==null)h.stockSharesAdded=0;
  if(!Array.isArray(h.processedActions))h.processedActions=[];
  if(!h.corpActionTrackingStart)h.corpActionTrackingStart=TRACKING_START;
  return h;
}
function applyOne(h,a){
  if(a.code!==h.c)return false;
  if(a.exDate < (h.corpActionTrackingStart||TRACKING_START))return false;
  if((h.processedActions||[]).includes(a.id))return false;
  let shares=safeNum(h.s), cost=safeNum(h.adjustedCost);
  const cash=safeNum(a.cashDividend), ratio=safeNum(a.stockRatio);
  if(cash>0){const got=shares*cash;h.cashReceived=safeNum(h.cashReceived)+got;cost=Math.max(0,cost-got);}
  if(ratio>0){const add=shares*ratio;h.stockSharesAdded=safeNum(h.stockSharesAdded)+add;shares+=add;}
  h.s=shares;h.adjustedCost=cost;h.a=shares>0?cost/shares:0;
  h.processedActions.push(a.id);h.lastCorpAction=a;
  return true;
}
function addCorpInfo(){
  const hs=typeof getHoldings==='function'?getHoldings():[];
  document.querySelectorAll('.holding-card').forEach((card,i)=>{
    const h=hs[i]; if(!h)return;
    let box=card.querySelector('.corp-info');
    if(!box){box=document.createElement('div');box.className='corp-info';box.style.cssText='padding:8px 10px;background:#f8fafc;border-top:1px solid #e1e6ec;font-size:12px;color:#475467;line-height:1.7';card.appendChild(box);}
    const last=h.lastCorpAction?`｜最近權息 ${h.lastCorpAction.exDate} ${h.lastCorpAction.cashDividend?`現金 ${Number(h.lastCorpAction.cashDividend).toFixed(2)}元/股 `:''}${h.lastCorpAction.stockRatio?`配股率 ${(Number(h.lastCorpAction.stockRatio)*100).toFixed(2)}%`:''}`:'';
    box.innerHTML=`原始成本均價 <b>${F(h.origAvg)}</b>｜含權息回本成本 <b>${F(h.a)}</b>｜累計現金股利 <b>${F(h.cashReceived)}</b> 元｜配股增加 <b>${F(h.stockSharesAdded)}</b> 股${last}<br><span style="color:#98a2b3">自 ${h.corpActionTrackingStart||TRACKING_START} 起自動套用；實際入帳股數／稅費以券商資料為準。</span>`;
  });
}
async function run(){
  if(typeof getHoldings!=='function'||typeof saveHoldings!=='function')return;
  let hs=getHoldings().map(migrateHolding),changed=false;
  try{
    const r=await fetch('corporate_actions.json?ts='+Date.now(),{cache:'no-store'});
    if(r.ok){const j=await r.json();for(const h of hs){for(const a of (j.actions||[])){if(applyOne(h,a))changed=true;}}}
  }catch(e){console.warn('corporate actions unavailable',e)}
  if(changed||hs.some(h=>h.origAvg==null)){saveHoldings(hs)}else saveHoldings(hs);
  if(typeof renderHoldings==='function')renderHoldings(hs);
  setTimeout(addCorpInfo,0);
}
const oldRender=window.renderHoldings;
if(typeof oldRender==='function'){
  window.renderHoldings=function(hs){oldRender(hs);setTimeout(addCorpInfo,0)};
}
window.addEventListener('load',run);
setTimeout(run,300);
})();
