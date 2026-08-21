(()=>{
const TRACKING_START='2026-08-18';
const safeNum=x=>Number.isFinite(Number(x))?Number(x):0;
let companyEvents=[];
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
function daysFromToday(iso){if(!iso)return null;const d=new Date(iso+'T00:00:00+08:00');if(Number.isNaN(d.getTime()))return null;const n=new Date(),t=new Date(n.getFullYear(),n.getMonth(),n.getDate());return Math.round((d-t)/86400000)}
function shortDate(iso){if(!iso)return '';const p=iso.split('-');return p.length===3?`${Number(p[1])}/${Number(p[2])}`:iso}
function labelEvent(e){const d=daysFromToday(e.date);if(e.kind==='conference'){if(d===0)return'📣 今日法說';if(d===1)return'📣 明天法說';if(d!=null&&d>1&&d<=7)return`📣 ${d}天後法說`;return`📣 法說 ${shortDate(e.date)}`;}if(e.kind==='dividend'){let x=`💰 除權息 ${shortDate(e.date)}`;if(+e.cash)x+=`｜現金 ${Number(e.cash).toFixed(2)}元`;if(+e.stock)x+=`｜配股 ${(Number(e.stock)*100).toFixed(2)}%`;return x;}if(e.kind==='dividend_policy'){let x='💵 股利政策';if(+e.cash)x+=`｜現金 ${Number(e.cash).toFixed(2)}元`;if(+e.stock)x+=`｜股票 ${Number(e.stock).toFixed(2)}元`;return x;}if(e.kind==='capital_increase')return`➕ 增資${e.date?'｜'+shortDate(e.date):''}`;if(e.kind==='capital_reduction')return`➖ 減資${e.date?'｜'+shortDate(e.date):''}`;return e.title||'重要事件'}
function chipStyle(e){const d=daysFromToday(e.date);if(e.kind==='dividend'||e.kind==='dividend_policy')return'background:#ecfdf3;color:#067647;border-color:#abefc6';if(e.kind==='capital_increase'||e.kind==='capital_reduction')return'background:#f4f3ff;color:#5925dc;border-color:#d9d6fe';if(d===0)return'background:#fff0ef;color:#b42318;border-color:#fecdca';if(d!=null&&d>0&&d<=3)return'background:#fff7e8;color:#b54708;border-color:#fedf89';return'background:#eff6ff;color:#175cd3;border-color:#b2ccff'}
function eventsFor(code){const now=new Date(),cut=new Date(now.getTime()-7*86400000);return companyEvents.filter(e=>String(e.code)===String(code)).filter(e=>!e.date||new Date(e.date+'T23:59:59+08:00')>=cut).sort((a,b)=>(a.date||'9999').localeCompare(b.date||'9999')).slice(0,5)}
function addCorpInfo(){
  const hs=typeof getHoldings==='function'?getHoldings():[];
  document.querySelectorAll('.holding-card').forEach((card,i)=>{
    const h=hs[i]; if(!h)return;
    let eventBox=card.querySelector('.event-radar');
    if(!eventBox){eventBox=document.createElement('div');eventBox.className='event-radar';eventBox.style.cssText='padding:9px 10px;background:#fff;border-top:1px solid #e1e6ec;font-size:12px;color:#344054;line-height:1.7';const footer=card.querySelector('.hold-footer');footer?card.insertBefore(eventBox,footer):card.appendChild(eventBox);}
    const es=eventsFor(h.c);
    eventBox.innerHTML=`<b style="margin-right:8px">📅 近期公司事件</b>${es.length?es.map(e=>`<span title="${String(e.title||'').replace(/\"/g,'&quot;')}" style="display:inline-block;margin:2px 4px 2px 0;padding:3px 7px;border:1px solid;border-radius:999px;font-weight:800;${chipStyle(e)}">${labelEvent(e)}</span>`).join(''):'<span style="color:#98a2b3">近期無重要事件</span>'}`;
    let box=card.querySelector('.corp-info');
    if(!box){box=document.createElement('div');box.className='corp-info';box.style.cssText='padding:8px 10px;background:#f8fafc;border-top:1px solid #e1e6ec;font-size:12px;color:#475467;line-height:1.7';card.appendChild(box);}
    const last=h.lastCorpAction?`｜最近權息 ${h.lastCorpAction.exDate} ${h.lastCorpAction.cashDividend?`現金 ${Number(h.lastCorpAction.cashDividend).toFixed(2)}元/股 `:''}${h.lastCorpAction.stockRatio?`配股率 ${(Number(h.lastCorpAction.stockRatio)*100).toFixed(2)}%`:''}`:'';
    box.innerHTML=`原始成本均價 <b>${F(h.origAvg)}</b>｜含權息回本成本 <b>${F(h.a)}</b>｜累計現金股利 <b>${F(h.cashReceived)}</b> 元｜配股增加 <b>${F(h.stockSharesAdded)}</b> 股${last}<br><span style="color:#98a2b3">自 ${h.corpActionTrackingStart||TRACKING_START} 起自動套用；實際入帳股數／稅費以券商資料為準。</span>`;
  });
}
async function loadEvents(){try{const r=await fetch('company_events.json?ts='+Date.now(),{cache:'no-store'});if(r.ok){const j=await r.json();companyEvents=Array.isArray(j.events)?j.events:[];setTimeout(addCorpInfo,0)}}catch(e){console.warn('company events unavailable',e)}}
async function run(){
  if(typeof getHoldings!=='function'||typeof saveHoldings!=='function')return;
  let hs=getHoldings().map(migrateHolding),changed=false;
  try{const r=await fetch('corporate_actions.json?ts='+Date.now(),{cache:'no-store'});if(r.ok){const j=await r.json();for(const h of hs){for(const a of (j.actions||[])){if(applyOne(h,a))changed=true;}}}}catch(e){console.warn('corporate actions unavailable',e)}
  saveHoldings(hs);if(typeof renderHoldings==='function')renderHoldings(hs);await loadEvents();setTimeout(addCorpInfo,0);
}
const oldRender=window.renderHoldings;
if(typeof oldRender==='function')window.renderHoldings=function(hs){oldRender(hs);setTimeout(addCorpInfo,0)};
window.addEventListener('load',run);setTimeout(run,300);setInterval(loadEvents,30*60*1000);
if(!document.querySelector('script[data-market-loader]')){const s=document.createElement('script');s.src='market-data.js';s.defer=true;s.dataset.marketLoader='1';document.head.appendChild(s);}
function loadDashboardEnhancers(){
  const load=(src,key,onload)=>{if(document.querySelector(`script[data-${key}]`)){if(onload)onload();return}const s=document.createElement('script');s.src=src;s.defer=true;s.dataset[key]='1';if(onload)s.onload=onload;document.body.appendChild(s)};
  load('rich-holdings-ui.js?v=20260821e','richHoldings',()=>load('chart-enhancer.js?v=20260821a','chartEnhancer'));
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(loadDashboardEnhancers,500));else setTimeout(loadDashboardEnhancers,500);
})();
