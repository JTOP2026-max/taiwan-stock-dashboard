const cors={
  'Access-Control-Allow-Origin':'*',
  'Access-Control-Allow-Methods':'GET,OPTIONS',
  'Access-Control-Allow-Headers':'Content-Type',
  'Cache-Control':'no-store'
};
const num=v=>{const n=Number(String(v??'').replace(/,/g,''));return Number.isFinite(n)?n:null};
async function getMis(code){
  for(const market of ['tse','otc']){
    const u=`https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=${market}_${encodeURIComponent(code)}.tw&json=1&delay=0&_=${Date.now()}`;
    try{
      const r=await fetch(u,{headers:{'User-Agent':'Mozilla/5.0','Referer':'https://mis.twse.com.tw/'},cf:{cacheTtl:0,cacheEverything:false}});
      if(!r.ok)continue;
      const j=await r.json();
      const row=Array.isArray(j.msgArray)?j.msgArray.find(x=>String(x.c||'')===String(code)):null;
      if(!row)continue;
      const price=num(row.z),prev=num(row.y);
      if(!(price>0))continue;
      const ch=prev!=null?price-prev:0,pc=prev?ch/prev*100:0;
      return {ok:true,code:String(code),market,rowMarket:market,price,prev,chg:ch,pct:pc,open:num(row.o),high:num(row.h),low:num(row.l),name:row.n||row.nf||'',time:row.t||'',date:row.d||'',source:'TWSE MIS via Cloudflare Worker',kind:'live'};
    }catch(e){}
  }
  return null;
}
export default {
  async fetch(request){
    if(request.method==='OPTIONS')return new Response(null,{status:204,headers:cors});
    const url=new URL(request.url);
    if(url.pathname==='/health')return Response.json({ok:true,service:'taiwan-stock-quote-proxy'},{headers:cors});
    if(url.pathname!=='/quote')return Response.json({ok:false,error:'not_found'},{status:404,headers:cors});
    const code=(url.searchParams.get('code')||'').trim();
    if(!/^[0-9A-Za-z]{4,8}$/.test(code))return Response.json({ok:false,error:'invalid_code'},{status:400,headers:cors});
    const q=await getMis(code);
    if(!q)return Response.json({ok:false,code,error:'live_quote_unavailable'},{status:404,headers:cors});
    return Response.json(q,{headers:cors});
  }
};
