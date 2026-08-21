(function(){
  const $=id=>document.getElementById(id);
  const RED='#df1f26', GREEN='#16834b', BLUE='#2166d1', MUTED='#667085', LINE='#dfe5ec';
  const fmt=(v,d=2)=>Number.isFinite(Number(v))?Number(v).toLocaleString('zh-TW',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';

  function pcLabel(v){
    if(!Number.isFinite(v)) return ['資料待更新',MUTED];
    if(v<0.7) return ['極度偏空',GREEN];
    if(v<1.0) return ['偏空',GREEN];
    if(v<=1.2) return ['正常範圍','#182230'];
    if(v<=1.35) return ['偏多',RED];
    if(v<=1.45) return ['偏多注意',RED];
    return ['最後的煙火・戒慎貪婪',RED];
  }
  function fgLabel(v){
    if(!Number.isFinite(v)) return ['資料待更新',MUTED];
    if(v<30) return ['市場恐懼',GREEN];
    if(v<50) return ['市場溫和',GREEN];
    if(v<66) return ['市場樂觀',RED];
    if(v<80) return ['市場樂觀追價',RED];
    return ['市場無腦多・小心最後煙火',RED];
  }
  function pctToAngle(p){ return -90 + Math.max(0,Math.min(1,p))*180; }
  function needle(angle){
    const a=angle*Math.PI/180, cx=150, cy=125, len=83;
    const x=cx+Math.cos(a)*len, y=cy+Math.sin(a)*len;
    return `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="#111827" stroke-width="5" stroke-linecap="round"/><circle cx="${cx}" cy="${cy}" r="9" fill="#111827"/><circle cx="${cx}" cy="${cy}" r="4" fill="#fff"/>`;
  }
  function gaugeSVG(type,value){
    let p=0, segs='';
    if(type==='pc'){
      p=(Math.max(.5,Math.min(1.6,value??1.05))-.5)/1.1;
      segs=`<path d="M55 125 A95 95 0 0 1 82.8 57.8" fill="none" stroke="#15945a" stroke-width="24"/>
      <path d="M82.8 57.8 A95 95 0 0 1 116.8 36.0" fill="none" stroke="#7bcf3f" stroke-width="24"/>
      <path d="M116.8 36.0 A95 95 0 0 1 161.0 30.6" fill="none" stroke="#55a8ef" stroke-width="24"/>
      <path d="M161.0 30.6 A95 95 0 0 1 205.8 48.1" fill="none" stroke="#f5c542" stroke-width="24"/>
      <path d="M205.8 48.1 A95 95 0 0 1 232.3 77.5" fill="none" stroke="#f58220" stroke-width="24"/>
      <path d="M232.3 77.5 A95 95 0 0 1 245 125" fill="none" stroke="#e11d2e" stroke-width="24"/>`;
    }else{
      p=Math.max(0,Math.min(100,value??50))/100;
      segs=`<path d="M55 125 A95 95 0 0 1 88.5 52.1" fill="none" stroke="#15945a" stroke-width="24"/>
      <path d="M88.5 52.1 A95 95 0 0 1 136.0 31.0" fill="none" stroke="#7bcf3f" stroke-width="24"/>
      <path d="M136.0 31.0 A95 95 0 0 1 181.0 35.2" fill="none" stroke="#f5c542" stroke-width="24"/>
      <path d="M181.0 35.2 A95 95 0 0 1 224.0 67.0" fill="none" stroke="#f58220" stroke-width="24"/>
      <path d="M224.0 67.0 A95 95 0 0 1 245 125" fill="none" stroke="#e11d2e" stroke-width="24"/>`;
    }
    return `<svg class="tech-gauge-svg" viewBox="0 0 300 155" aria-hidden="true">${segs}${needle(pctToAngle(p))}</svg>`;
  }
  function pcLegend(){return `<div class="tech-legend"><span><i style="background:#15945a"></i>&lt;0.7 極度偏空</span><span><i style="background:#7bcf3f"></i>0.7–1.0 偏空</span><span><i style="background:#55a8ef"></i>1.0–1.2 正常</span><span><i style="background:#f5c542"></i>1.2–1.35 偏多</span><span><i style="background:#f58220"></i>1.36–1.45 注意</span><span><i style="background:#e11d2e"></i>&gt;1.45 最後煙火</span></div>`}
  function fgLegend(){return `<div class="tech-legend"><span><i style="background:#15945a"></i>0–30 恐懼</span><span><i style="background:#7bcf3f"></i>30–50 溫和</span><span><i style="background:#f5c542"></i>50–65 樂觀</span><span><i style="background:#f58220"></i>66–79 追價</span><span><i style="background:#e11d2e"></i>≥80 無腦多</span></div>`}
  function card(title,type,value,sub,updated){
    const lab=type==='pc'?pcLabel(value):fgLabel(value), isPC=type==='pc';
    return `<div class="card sentiment-tech-card"><div class="tech-head"><b>${title}</b><span>${updated||'盤後資料'}</span></div><div class="tech-main"><div class="tech-gauge-wrap">${gaugeSVG(type,value)}<div class="tech-value" style="color:${lab[1]}">${isPC?fmt(value,2):fmt(value,2)+'/100'}</div><div class="tech-state" style="color:${lab[1]}">${lab[0]}</div></div><div class="tech-side">${sub}</div></div>${isPC?pcLegend():fgLegend()}</div>`;
  }
  function css(){
    if(document.getElementById('sentimentTechCSS'))return;
    const s=document.createElement('style');s.id='sentimentTechCSS';s.textContent=`
    #sent{grid-template-columns:1fr 2fr 2fr;align-items:stretch}
    .sentiment-tech-card{position:relative;overflow:hidden;background:linear-gradient(145deg,#fff 0%,#fbfdff 100%);border:1px solid #d7e2ef;box-shadow:0 10px 28px rgba(31,65,114,.08)}
    .sentiment-tech-card:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 90% 12%,rgba(33,102,209,.07),transparent 30%);pointer-events:none}
    .tech-head{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px}.tech-head b{font-size:15px}.tech-head span{font-size:11px;color:${MUTED};padding:4px 7px;border-radius:999px;background:#f1f5f9}
    .tech-main{display:grid;grid-template-columns:minmax(220px,1.25fr) minmax(120px,.75fr);gap:10px;align-items:center}.tech-gauge-wrap{text-align:center}.tech-gauge-svg{width:100%;max-width:320px;filter:drop-shadow(0 5px 8px rgba(33,102,209,.08))}.tech-value{font-size:31px;font-weight:900;line-height:1;margin-top:-16px}.tech-state{font-weight:900;margin-top:6px}.tech-side{font-size:13px;line-height:1.9;color:#344054}.tech-side b{font-size:16px}.tech-legend{display:grid;grid-template-columns:repeat(3,1fr);gap:5px 9px;border-top:1px solid #edf2f7;padding-top:9px;margin-top:10px;font-size:10px;color:#475467}.tech-legend span{white-space:nowrap}.tech-legend i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}
    @media(max-width:1100px){#sent{grid-template-columns:1fr 1fr}.sentiment-tech-card:first-child{grid-column:1/-1}}
    @media(max-width:820px){#sent{grid-template-columns:1fr}.sentiment-tech-card:first-child{grid-column:auto}.tech-main{grid-template-columns:1fr}.tech-side{text-align:center}.tech-legend{grid-template-columns:1fr 1fr}}
    `;document.head.appendChild(s);
  }
  async function render(){
    const sent=$('sent'); if(!sent)return;
    css();
    let d={}; try{const r=await fetch('market.json?ts='+Date.now(),{cache:'no-store'});if(r.ok)d=await r.json();}catch(e){}
    const pc=d.pc||{}, cnn=d.cnnFearGreed||{};
    const children=[...sent.children];
    const inst=children[0]?children[0].outerHTML:'<div class="card"><div class="label">三大法人</div><div class="small">資料載入中</div></div>';
    const pcv=Number.isFinite(Number(pc.oi))?Number(pc.oi):NaN;
    const cnv=Number.isFinite(Number(cnn.score))?Number(cnn.score):NaN;
    const pcSub=`<div>成交比 <b style="color:${Number(pc.trade)>=1.2?RED:Number(pc.trade)<1?GREEN:'#182230'}">${fmt(pc.trade,2)}</b></div><div>未平倉比 <b style="color:${Number(pc.oi)>1.2?RED:Number(pc.oi)<1?GREEN:'#182230'}">${fmt(pc.oi,2)}</b></div><div class="small">偏多＝紅字｜偏空＝綠字</div>`;
    const cnSub=`<div>市場情緒</div><div><b style="color:${fgLabel(cnv)[1]}">${fgLabel(cnv)[0]}</b></div><div class="small">CNN 美股情緒・每日盤後</div>`;
    sent.innerHTML=inst+card('P/C Ratio（每日盤後）','pc',pcv,pcSub,d.date?d.date+' 盤後':'等待盤後資料')+card('CNN Fear & Greed（美股・每日盤後）','fg',cnv,cnSub,d.date?d.date+' 盤後':'等待盤後資料');
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(render,350));else setTimeout(render,350);
  window.addEventListener('market-data-updated',render);
})();
(function(){
  function loadRichHoldings(){
    if(document.querySelector('script[data-rich-holdings]')) return;
    const s=document.createElement('script');
    s.src='rich-holdings-ui.js?v=20260821d';
    s.async=false;
    s.dataset.richHoldings='1';
    document.head.appendChild(s);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',loadRichHoldings); else loadRichHoldings();
})();
