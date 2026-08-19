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

(function(){
  const RECORD_KEY='txo_settlement_journal_v1';
  const SETTINGS_KEY='txo_settlement_settings_v1';
  const defaults={winThreshold:0,stopLoss:15,takeProfit:25};
  let records=read(RECORD_KEY,[]);
  let settings={...defaults,...read(SETTINGS_KEY,{})};
  let editingId=null;
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const n=v=>Number(v)||0;
  const twToday=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  function read(key,fallback){try{const v=JSON.parse(localStorage.getItem(key));return v??fallback}catch(e){return fallback}}
  function write(key,value){localStorage.setItem(key,JSON.stringify(value))}
  function weekday(date){return new Intl.DateTimeFormat('zh-TW',{weekday:'short',timeZone:'Asia/Taipei'}).format(new Date(date+'T12:00:00+08:00'))}
  function isSettlementDay(date){const d=new Date(date+'T12:00:00+08:00').getDay();return d===3||d===5}
  function calc(r){return Math.round((n(r.exitPremium)-n(r.entryPremium))*50*Math.max(1,n(r.contracts))-n(r.costs))}
  function inject(){
    const target=document.getElementById('breadth')?.parentElement;
    const holdingsTitle=[...document.querySelectorAll('.sec')].find(x=>x.textContent.includes('我的持股'));
    if(!target||!holdingsTitle)return;
    const style=document.createElement('style');
    style.textContent=`
      .txo-head{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}
      .txo-live{background:#fff7ed;border:1px solid #fdba74;color:#9a3412;border-radius:999px;padding:5px 10px;font-size:12px;font-weight:900}
      .txo-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin:10px 0}
      .txo-stat{background:#f8fafc;border:1px solid var(--line);border-radius:9px;padding:10px}.txo-stat b{display:block;font-size:22px;margin-top:4px}
      .txo-form{display:grid;grid-template-columns:repeat(6,1fr);gap:8px}.txo-field label{display:block;color:var(--muted);font-size:11px;margin-bottom:4px}.txo-field input,.txo-field select{width:100%;border:1px solid #ccd4de;border-radius:7px;padding:8px;background:#fff}
      .txo-wide{grid-column:span 2}.txo-actions{display:flex;gap:7px;flex-wrap:wrap;margin:10px 0}.txo-table{width:100%;border-collapse:collapse;min-width:1050px}.txo-table th,.txo-table td{border-bottom:1px solid var(--line);padding:8px;text-align:center;font-size:12px}.txo-table th{background:#f6f7f9;color:var(--muted)}
      .txo-settings{background:#f8fafc;border-radius:9px;padding:10px;margin-top:10px}.txo-settings-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;max-width:650px}.txo-settings input{width:100%;padding:7px;border:1px solid #ccd4de;border-radius:7px}
      .txo-empty{text-align:center;color:var(--muted);padding:18px}.txo-note{font-size:12px;color:var(--muted);line-height:1.6}
      @media(max-width:820px){.txo-stats{grid-template-columns:1fr 1fr}.txo-form{grid-template-columns:1fr 1fr}.txo-wide{grid-column:span 2}.txo-settings-grid{grid-template-columns:1fr}.txo-table-wrap{overflow:auto}}
    `;
    document.head.appendChild(style);
    const box=document.createElement('section');
    box.id='txoJournal';
    box.innerHTML=`
      <div class="sec">④ 週三／週五｜台指選擇權結算短沖</div>
      <div class="card">
        <div class="txo-head"><div><b>09:00～09:20 Call／Put 紀錄</b><div class="txo-note" id="txoDayNote"></div></div><span class="txo-live" id="txoDayBadge"></span></div>
        <div class="txo-stats">
          <div class="txo-stat"><span class="label">已平倉筆數</span><b id="txoTrades">0</b></div>
          <div class="txo-stat"><span class="label">勝率</span><b id="txoWinRate">—</b></div>
          <div class="txo-stat"><span class="label">累計淨損益</span><b id="txoPnl">0</b></div>
          <div class="txo-stat"><span class="label">平均每筆</span><b id="txoAvg">0</b></div>
        </div>
        <div id="txoEntryArea">
          <div class="txo-form">
            <div class="txo-field"><label>日期</label><input id="txoDate" type="date"></div>
            <div class="txo-field"><label>商品</label><select id="txoType"><option>CALL</option><option>PUT</option></select></div>
            <div class="txo-field"><label>履約價</label><input id="txoStrike" type="number" step="50" placeholder="44600"></div>
            <div class="txo-field"><label>口數</label><input id="txoContracts" type="number" min="1" value="1"></div>
            <div class="txo-field"><label>進場時間</label><input id="txoEntryTime" type="time" value="09:05"></div>
            <div class="txo-field"><label>出場時間</label><input id="txoExitTime" type="time" value="09:20"></div>
            <div class="txo-field"><label>進場權利金</label><input id="txoEntryPremium" type="number" min="0" step="0.1"></div>
            <div class="txo-field"><label>出場權利金</label><input id="txoExitPremium" type="number" min="0" step="0.1"></div>
            <div class="txo-field"><label>交易成本（元）</label><input id="txoCosts" type="number" min="0" value="0"></div>
            <div class="txo-field"><label>09:00台指期</label><input id="txoFuture" type="number"></div>
            <div class="txo-field"><label>09:00現貨</label><input id="txoSpot" type="number"></div>
            <div class="txo-field txo-wide"><label>進場理由／觀察</label><input id="txoNote" placeholder="突破早盤高點、站上VWAP、台積電同步"></div>
          </div>
          <div class="txo-actions"><button class="btn" id="txoSave">儲存紀錄</button><button class="btn secondary" id="txoCancel" style="display:none">取消修改</button></div>
        </div>
        <div class="txo-table-wrap"><table class="txo-table"><thead><tr><th>日期</th><th>商品</th><th>履約價</th><th>進／出場</th><th>權利金</th><th>口數</th><th>期現價差</th><th>淨損益</th><th>勝負</th><th>備註</th><th>操作</th></tr></thead><tbody id="txoRows"></tbody></table></div>
        <details class="txo-settings"><summary><b>策略設定（勝率、停損停利可在這裡修改）</b></summary>
          <div class="txo-settings-grid">
            <label class="txo-field">勝利門檻（淨利元）<input id="txoWinThreshold" type="number"></label>
            <label class="txo-field">停損提醒（%）<input id="txoStopLoss" type="number" min="1"></label>
            <label class="txo-field">停利提醒（%）<input id="txoTakeProfit" type="number" min="1"></label>
          </div>
          <div class="txo-actions"><button class="btn secondary" id="txoSaveSettings">儲存策略設定</button></div>
          <div class="txo-note">勝率＝淨損益高於勝利門檻的筆數 ÷ 已平倉筆數。淨損益＝（出場權利金－進場權利金）×50元×口數－交易成本。紀錄只存在目前裝置的瀏覽器。</div>
        </details>
      </div>`;
    holdingsTitle.parentNode.insertBefore(box,holdingsTitle);
    const headings=[...document.querySelectorAll('.sec')];
    headings.forEach(h=>{if(h!==box.firstElementChild&&/^[④⑤]/.test(h.textContent)){h.textContent=h.textContent.replace(/^④/,'⑤').replace(/^⑤ 持股估值/,'⑥ 持股估值')}});
    bind();resetForm();renderJournal();
  }
  function el(id){return document.getElementById(id)}
  function formRecord(){
    return {id:editingId||('t'+Date.now()),date:el('txoDate').value,type:el('txoType').value,strike:n(el('txoStrike').value),contracts:Math.max(1,n(el('txoContracts').value)),entryTime:el('txoEntryTime').value,exitTime:el('txoExitTime').value,entryPremium:n(el('txoEntryPremium').value),exitPremium:n(el('txoExitPremium').value),costs:n(el('txoCosts').value),future:n(el('txoFuture').value),spot:n(el('txoSpot').value),note:el('txoNote').value.trim()};
  }
  function saveRecord(){
    const r=formRecord();
    if(!r.date||!r.strike||!r.entryPremium){alert('請至少填寫日期、履約價與進場權利金。');return}
    if(!isSettlementDay(r.date)&&!confirm('這個日期不是週三或週五，仍要儲存嗎？'))return;
    const i=records.findIndex(x=>x.id===r.id);if(i>=0)records[i]=r;else records.unshift(r);
    records.sort((a,b)=>(b.date+b.entryTime).localeCompare(a.date+a.entryTime));write(RECORD_KEY,records);resetForm();renderJournal();
  }
  function resetForm(){
    editingId=null;if(!el('txoDate'))return;
    el('txoDate').value=twToday();el('txoType').value='CALL';el('txoStrike').value='';el('txoContracts').value=1;el('txoEntryTime').value='09:05';el('txoExitTime').value='09:20';el('txoEntryPremium').value='';el('txoExitPremium').value='';el('txoCosts').value=0;el('txoFuture').value='';el('txoSpot').value='';el('txoNote').value='';el('txoSave').textContent='儲存紀錄';el('txoCancel').style.display='none';
  }
  function editRecord(id){
    const r=records.find(x=>x.id===id);if(!r)return;editingId=id;
    ['Date','Type','Strike','Contracts','EntryTime','ExitTime','EntryPremium','ExitPremium','Costs','Future','Spot','Note'].forEach(k=>{const key=k.charAt(0).toLowerCase()+k.slice(1);el('txo'+k).value=r[key]??''});
    el('txoSave').textContent='儲存修改';el('txoCancel').style.display='inline-block';el('txoEntryArea').scrollIntoView({behavior:'smooth',block:'center'});
  }
  function deleteRecord(id){if(confirm('確定刪除這筆交易紀錄？')){records=records.filter(x=>x.id!==id);write(RECORD_KEY,records);renderJournal()}}
  function renderJournal(){
    const today=twToday(),active=isSettlementDay(today);
    el('txoDayBadge').textContent=active?'今天是結算觀察日':'非週三／週五';
    el('txoDayNote').textContent=active?'今天顯示完整輸入區；先確認同一時間期貨、現貨與選擇權報價。':'完整紀錄仍保留；新增區在週三、週五會自動呈現。';
    el('txoEntryArea').style.display=active||editingId?'block':'none';
    const closed=records.filter(r=>n(r.exitPremium)>0),wins=closed.filter(r=>calc(r)>n(settings.winThreshold)),total=closed.reduce((a,r)=>a+calc(r),0),avg=closed.length?Math.round(total/closed.length):0;
    el('txoTrades').textContent=closed.length;el('txoWinRate').textContent=closed.length?(wins.length/closed.length*100).toFixed(1)+'%':'—';
    el('txoPnl').textContent=(total>0?'+':'')+total.toLocaleString()+' 元';el('txoPnl').className=total>0?'up':total<0?'down':'';
    el('txoAvg').textContent=(avg>0?'+':'')+avg.toLocaleString()+' 元';el('txoAvg').className=avg>0?'up':avg<0?'down':'';
    el('txoRows').innerHTML=records.length?records.map(r=>{const pnl=n(r.exitPremium)>0?calc(r):null,basis=n(r.future)&&n(r.spot)?n(r.future)-n(r.spot):null,result=pnl===null?'未平倉':pnl>n(settings.winThreshold)?'勝':'負';return `<tr><td>${esc(r.date)}<br>${weekday(r.date)}</td><td><b>${esc(r.type)}</b></td><td>${n(r.strike).toLocaleString()}</td><td>${esc(r.entryTime)}／${esc(r.exitTime||'—')}</td><td>${n(r.entryPremium)} → ${n(r.exitPremium)||'—'}</td><td>${n(r.contracts)}</td><td>${basis===null?'—':(basis>0?'+':'')+basis.toLocaleString()}</td><td class="${pnl>0?'up':pnl<0?'down':''}">${pnl===null?'—':(pnl>0?'+':'')+pnl.toLocaleString()+' 元'}</td><td><b>${result}</b></td><td title="${esc(r.note)}">${esc((r.note||'—').slice(0,24))}</td><td><button class="btn secondary" data-edit="${r.id}" style="padding:5px 7px">修改</button> <button class="danger" data-delete="${r.id}">刪除</button></td></tr>`}).join(''):'<tr><td colspan="11" class="txo-empty">尚無紀錄；週三或週五完成交易後，請填入進出場資料。</td></tr>';
    el('txoRows').querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>editRecord(b.dataset.edit));
    el('txoRows').querySelectorAll('[data-delete]').forEach(b=>b.onclick=()=>deleteRecord(b.dataset.delete));
    el('txoWinThreshold').value=settings.winThreshold;el('txoStopLoss').value=settings.stopLoss;el('txoTakeProfit').value=settings.takeProfit;
  }
  function bind(){
    el('txoSave').onclick=saveRecord;el('txoCancel').onclick=()=>{resetForm();renderJournal()};
    el('txoSaveSettings').onclick=()=>{settings={winThreshold:n(el('txoWinThreshold').value),stopLoss:n(el('txoStopLoss').value)||15,takeProfit:n(el('txoTakeProfit').value)||25};write(SETTINGS_KEY,settings);renderJournal();alert('策略設定已儲存，勝率已重新計算。')};
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',inject);else inject();
})();