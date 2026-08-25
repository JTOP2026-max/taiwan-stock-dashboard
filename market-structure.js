(function(){
  if(window.__v5MarketStructure) return;
  window.__v5MarketStructure=true;

  const RED='#df1f26', GREEN='#16834b', AMBER='#b7791f', TEXT='#182230';
  const num=v=>{const x=Number(v);return Number.isFinite(x)?x:null};
  const avg=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
  const changePct=(a,b)=>a!=null&&b?((a/b)-1)*100:null;
  const fmt=(v,d=1)=>v==null?'—':Number(v).toLocaleString('zh-TW',{minimumFractionDigits:d,maximumFractionDigits:d});
  const signed=(v,d=0)=>v==null?'—':`${v>0?'+':''}${fmt(v,d)}`;

  function ensureCSS(){
    if(document.getElementById('v5MarketStructureCSS')) return;
    const s=document.createElement('style');
    s.id='v5MarketStructureCSS';
    s.textContent=`
      .v5-ms-head{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px}
      .v5-ms-badge{font-size:11px;color:#667085;background:#f1f5f9;border-radius:999px;padding:4px 8px;white-space:nowrap}
      .v5-ms-title{font-size:24px;font-weight:900;line-height:1.25;margin:4px 0 9px}
      .v5-ms-chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 11px}
      .v5-ms-chip{font-size:11px;background:#f8fafc;border:1px solid #e4eaf1;border-radius:999px;padding:5px 8px;color:#475467}
      .v5-ms-reason{font-size:13px;line-height:1.7;color:#344054}
      .v5-ms-watch{margin-top:10px;border-top:1px solid #e7ebf0;padding-top:9px;font-size:13px;line-height:1.65;color:#344054}
      .v5-ms-watch b{color:#182230}
      @media(max-width:820px){.v5-ms-title{font-size:22px}.v5-ms-reason,.v5-ms-watch{font-size:14px}.v5-ms-chip{font-size:12px}}
    `;
    document.head.appendChild(s);
  }

  function classify(cur,history){
    const rows=(Array.isArray(history?.records)?history.records:[])
      .filter(r=>r&&r.date&&num(r.core?.idx)!=null)
      .sort((a,b)=>String(a.date).localeCompare(String(b.date)));
    const byDate=new Map(rows.map(r=>[r.date,r]));
    if(cur?.date) byDate.set(cur.date,cur);
    const all=[...byDate.values()].sort((a,b)=>String(a.date).localeCompare(String(b.date)));
    const recent20=all.slice(-20), recent10=all.slice(-10), recent5=all.slice(-5);

    const idx=num(cur?.core?.idx), dayPct=num(cur?.core?.pct);
    const vols20=recent20.map(r=>num(r.core?.volTrillion)).filter(v=>v!=null&&v>0);
    const vols5=recent5.map(r=>num(r.core?.volTrillion)).filter(v=>v!=null&&v>0);
    const vol5=avg(vols5), vol20=avg(vols20), volRatio=vol5!=null&&vol20?vol5/vol20:null;
    const idxs10=recent10.map(r=>num(r.core?.idx)).filter(v=>v!=null);
    const range10=idxs10.length>=3&&idxs10.at(-1)?(Math.max(...idxs10)-Math.min(...idxs10))/idxs10.at(-1)*100:null;
    const old5=all.length>=6?num(all.at(-6)?.core?.idx):null;
    const trend5=changePct(idx,old5);
    const ma20=avg(recent20.map(r=>num(r.core?.idx)).filter(v=>v!=null));
    const up=num(cur?.breadth?.up), down=num(cur?.breadth?.down);
    const breadth=up!=null&&down!=null&&up+down>0?up/(up+down):null;
    const foreign=num(cur?.inst?.foreign), pc=num(cur?.pc?.oi);
    const sideways=range10!=null&&range10<=3.0&&trend5!=null&&Math.abs(trend5)<=1.8;

    let title='盤勢中性｜等待訊號', color=TEXT;
    let reason='量價、騰落與法人訊號尚未形成明確一致方向。';
    let watch='觀察是否出現帶量突破、量縮止穩，或騰落家數明顯改善。';

    if(idx!=null&&ma20!=null&&idx<ma20&&dayPct!=null&&dayPct<=-.7&&volRatio!=null&&volRatio>=1.03&&(foreign==null||foreign<0)){
      title='放量轉弱｜風險升高'; color=GREEN;
      reason=`指數位於20日平均之下，今日下跌且量能高於近期平均${foreign!=null?`，外資 ${signed(foreign,0)} 億`:''}。`;
      watch='留意短期支撐、成交量是否續增，以及外資賣壓是否延續。';
    }else if(dayPct!=null&&dayPct>.35&&breadth!=null&&breadth>=.57&&(volRatio==null||volRatio>=.93)){
      title='量價結構健康｜多頭擴散'; color=RED;
      reason=`指數上漲 ${signed(dayPct,2)}%，上漲家數占 ${(breadth*100).toFixed(0)}%，漲勢有擴散。`;
      watch='留意量能能否維持，以及強勢族群是否持續擴散而非集中少數權值股。';
    }else if(dayPct!=null&&dayPct>0&&breadth!=null&&breadth<.49){
      title='權值撐盤｜結構分歧'; color=AMBER;
      reason=`指數收紅，但上漲家數占比僅 ${(breadth*100).toFixed(0)}%（${fmt(up,0)} 漲／${fmt(down,0)} 跌），盤面擴散不足。`;
      watch='留意騰落家數能否回升；若指數續漲但多數個股走弱，代表分歧仍在擴大。';
    }else if(sideways&&volRatio!=null&&volRatio<.9){
      title='量縮盤整｜等待方向'; color=AMBER;
      reason=`近10日震盪區間約 ${fmt(range10,1)}%，近5日變動 ${signed(trend5,1)}%，5日均量僅約20日均量 ${(volRatio*100).toFixed(0)}%。`;
      watch='重點看區間上緣／下緣，以及突破時是否同步放量。';
    }else if(trend5!=null&&trend5>.8&&volRatio!=null&&volRatio<.88){
      title='量縮上漲｜動能降溫'; color=AMBER;
      reason=`近5日指數仍上漲 ${signed(trend5,1)}%，但5日均量只有20日均量 ${(volRatio*100).toFixed(0)}%，量價不同步。`;
      watch='留意後續是否補量，若價格續創高但量能持續縮，需注意背離。';
    }else if(sideways){
      title='區間盤整｜多空拉鋸'; color=TEXT;
      reason=`近10日震盪約 ${fmt(range10,1)}%，近5日變動 ${signed(trend5,1)}%，尚未脫離整理區。`;
      watch='觀察區間突破方向、成交量，以及突破後能否連續守住。';
    }else if(dayPct!=null&&dayPct<0&&trend5!=null&&trend5>0&&volRatio!=null&&volRatio<.92){
      title='量縮拉回｜整理觀察'; color=AMBER;
      reason=`近5日仍上漲 ${signed(trend5,1)}%，今日回檔但量能低於20日均量。`;
      watch='留意支撐是否守住；若後續轉為放量下跌，盤勢判讀會轉弱。';
    }else if(trend5!=null&&trend5>0&&breadth!=null&&breadth>=.52){
      title='震盪偏多｜結構尚可'; color=RED;
      reason=`近5日指數 ${signed(trend5,1)}%，上漲家數占 ${(breadth*100).toFixed(0)}%。`;
      watch='留意量能與騰落家數是否同步改善，確認多頭不是只靠少數族群。';
    }else if(breadth!=null&&breadth<.45){
      title='盤面偏弱｜個股壓力較大'; color=GREEN;
      reason=`上漲家數僅占 ${(breadth*100).toFixed(0)}%（${fmt(up,0)} 漲／${fmt(down,0)} 跌）${foreign!=null?`，外資 ${signed(foreign,0)} 億`:''}。`;
      watch='留意跌家數是否持續擴大，以及指數是否跌破近期支撐。';
    }

    const chips=[];
    if(volRatio!=null) chips.push(`5日量／20日量 ${(volRatio*100).toFixed(0)}%`);
    if(range10!=null) chips.push(`10日區間 ${fmt(range10,1)}%`);
    if(breadth!=null) chips.push(`上漲占比 ${(breadth*100).toFixed(0)}%`);
    if(foreign!=null) chips.push(`外資 ${signed(foreign,0)}億`);
    if(pc!=null) chips.push(`P/C ${fmt(pc,2)}`);
    return {title,color,reason,watch,chips,date:cur?.date||''};
  }

  async function render(){
    const box=document.getElementById('breadth');
    if(!box) return;
    ensureCSS();
    let cur=null,hist={};
    try{
      const [a,b]=await Promise.all([
        fetch('market.json?ts='+Date.now(),{cache:'no-store'}),
        fetch('market_history.json?ts='+Date.now(),{cache:'no-store'})
      ]);
      if(a.ok) cur=await a.json();
      if(b.ok) hist=await b.json();
    }catch(e){}
    if(!cur) return;
    const cards=[...box.children].filter(x=>x.classList&&x.classList.contains('card'));
    const target=cards.at(-1);
    if(!target) return;
    const a=classify(cur,hist);
    target.innerHTML=`<div class="v5-ms-head"><div class="label">市場結構｜盤後自動判讀</div><span class="v5-ms-badge">${a.date?a.date+' 盤後':'每日盤後'}</span></div><div class="v5-ms-title" style="color:${a.color}">${a.title}</div><div class="v5-ms-chips">${a.chips.map(x=>`<span class="v5-ms-chip">${x}</span>`).join('')}</div><div class="v5-ms-reason">${a.reason}</div><div class="v5-ms-watch"><b>觀察重點：</b>${a.watch}</div>`;
  }

  function start(){setTimeout(render,600);setTimeout(render,1800);}
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start); else start();
  window.addEventListener('market-data-updated',()=>setTimeout(render,150));
})();
