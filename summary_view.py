"""summary_view.py — サマリー画面の HTML/CSS/JS（ライト＋オレンジ基調・立体感のあるUI）。

配色（添付カラーコードをベースにオレンジ基調へ再編）:
  背景#FAFAFA / カード#FFFFFF / 罫線#EAEAEA / 本文#1A1A1A / 補助#8A8A8A
  オレンジ #E9965B（濃#C9742F / 淡#F2C4A0）= ブランド/主役・ポジティブ
  ブルー   #82B5F6（濃#3D7BD9）           = 補助・中立データ
  レッド   #D50403                        = アラート専用（減少デルタのみ）
立体感: 多層シャドウ・グラデーション・面塗り・ホバーで浮く・登場アニメ。
KPIの主役は「検索流入」。フィルタ（期間/種別）は JS クライアント側で即時処理。
"""
import json

SUMMARY_HEIGHT = 1430

_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<style>
:root{
  --bg:#FAFAFA; --card:#FFFFFF; --brd:#EAEAEA; --ink:#1A1A1A; --muted:#8A8A8A;
  --or:#E9965B; --orD:#C9742F; --orL:#F2C4A0; --orBg:#FCEEE2;
  --bl:#82B5F6; --blD:#3D7BD9; --alert:#D50403;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{color:var(--ink);
  background:
   radial-gradient(1100px 520px at 85% -10%, #FCE6D5 0%, rgba(252,230,213,0) 55%),
   radial-gradient(820px 420px at -5% 6%, #EAF1FB 0%, rgba(234,241,251,0) 52%),
   linear-gradient(180deg,#FBFBFC,#F4F5F7);
  font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP","Helvetica Neue",sans-serif;
  font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased;}
.wrap{padding:16px 18px 30px;max-width:2100px;margin:0 auto}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.card{background:var(--card);border:1px solid #EFEFEF;border-radius:18px;
  box-shadow:0 1px 2px rgba(20,20,40,.04), 0 10px 30px rgba(20,20,40,.06);
  animation:rise .4s ease both;}
.muted{color:var(--muted)}

/* header */
.head{display:flex;align-items:center;gap:16px;padding:13px 18px;margin-bottom:15px;
  background:linear-gradient(135deg,#FFFFFF, #FFF8F2);}
.avatar{width:46px;height:46px;border-radius:50%;border:2px solid #fff;background:#eee center/cover;
  box-shadow:0 4px 12px rgba(233,150,91,.35)}
.brand .k{font-size:10px;letter-spacing:2.5px;color:var(--orD);font-weight:800}
.brand .n{font-size:20px;font-weight:900;letter-spacing:.3px}
.head .spacer{flex:1}
.pills{display:flex;gap:5px;background:#F4F5F7;padding:5px;border-radius:13px;border:1px solid var(--brd);
  box-shadow:inset 0 1px 2px rgba(0,0,0,.03)}
.pill{padding:8px 14px;border-radius:9px;font-size:13px;color:var(--muted);cursor:pointer;border:none;
  background:transparent;font-weight:800;white-space:nowrap;transition:.15s}
.pill:hover{color:var(--orD);background:#fff}
.pill.on{background:linear-gradient(135deg,#F2A66A,#E9965B);color:#fff;
  box-shadow:0 5px 13px rgba(233,150,91,.5)}
.grp{margin-left:8px}
.chip{display:flex;align-items:center;gap:7px;padding:9px 13px;border-radius:11px;font-size:12px;
  font-weight:800;border:1px solid var(--brd);background:#fff;color:var(--muted);
  box-shadow:0 2px 6px rgba(20,20,40,.05)}
.chip.gear{cursor:pointer}
.chip.live{color:#fff;background:linear-gradient(135deg,#F2A66A,#E9965B);border:none;
  box-shadow:0 5px 13px rgba(233,150,91,.5)}
.dot{width:8px;height:8px;border-radius:50%;background:#fff;animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}

/* kpi */
.kpis{display:grid;grid-template-columns:1.3fr 1fr 1fr 1fr 1fr;gap:14px;margin-bottom:15px}
.kpi{padding:17px 19px;position:relative;overflow:hidden}
.kpi.hero{background:linear-gradient(135deg,#FFF3E9 0%, #FFFFFF 60%);border:1px solid var(--orL);
  box-shadow:0 2px 6px rgba(233,150,91,.18), 0 14px 34px rgba(233,150,91,.18)}
.kpi.hero::after{content:"";position:absolute;right:-30px;top:-30px;width:110px;height:110px;border-radius:50%;
  background:radial-gradient(circle,rgba(233,150,91,.18),rgba(233,150,91,0))}
.kpi .ic{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;font-size:16px;
  margin-bottom:12px;background:#F2F4F6}
.kpi.hero .ic{background:var(--orBg);box-shadow:0 4px 10px rgba(233,150,91,.25)}
.kpi .lab{font-size:12.5px;color:var(--muted);font-weight:800;display:inline-block;margin-bottom:5px}
.kpi .val{font-size:30px;font-weight:900;letter-spacing:.3px;line-height:1.05}
.kpi.hero .val{font-size:38px;background:linear-gradient(135deg,#E9965B,#C9742F);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.kpi .sub{font-size:12px;color:var(--muted);margin-top:6px}
.delta-up{color:var(--orD);font-weight:900}
.delta-down{color:var(--alert);font-weight:900}

/* chart */
.panel{padding:16px 20px;margin-bottom:15px}
.panel .ph{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:4px}
.panel .ph .t{font-size:16px;font-weight:900}
.panel .ph .r{font-size:12.5px;color:var(--muted);font-weight:700}
#chart{position:relative;width:100%;height:380px;margin-top:4px}
#chart svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.tcard{position:absolute;transform:translate(-50%,-100%);cursor:pointer;transition:transform .12s;
  display:flex;flex-direction:column;align-items:center;will-change:transform}
.tcard:hover{transform:translate(-50%,-100%) scale(1.2);z-index:999!important}
.tcard img{width:78px;height:44px;object-fit:cover;border-radius:7px;border:2px solid #fff;
  box-shadow:0 6px 16px rgba(20,20,40,.28)}
.tcard .vc{margin-top:-9px;background:#fff;border:1px solid var(--brd);border-radius:7px;
  font-size:10.5px;font-weight:900;padding:2px 7px;color:var(--orD);white-space:nowrap;
  box-shadow:0 3px 8px rgba(20,20,40,.12)}
.gridline{stroke:var(--brd);stroke-width:1}
.glab{fill:var(--muted);font-size:10.5px}
.xlab{fill:var(--muted);font-size:10.5px;text-anchor:middle}

/* bottom */
.bottom{display:grid;grid-template-columns:1fr 1fr 1.25fr;gap:15px}
.sec-t{font-size:14.5px;font-weight:900;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.sec-t .prov{font-size:11px;color:var(--muted);font-weight:700;margin-left:auto}
.goal .big{font-size:46px;font-weight:900;line-height:1;
  background:linear-gradient(135deg,#E9965B,#C9742F);-webkit-background-clip:text;background-clip:text;color:transparent}
.goal .big small{font-size:19px;color:var(--ink);font-weight:800;margin-left:4px;-webkit-text-fill-color:var(--ink)}
.bar{height:11px;border-radius:7px;background:#F0F1F4;margin:14px 0 8px;overflow:hidden;
  box-shadow:inset 0 1px 3px rgba(0,0,0,.08)}
.bar>span{display:block;height:100%;border-radius:7px;width:0;transition:width 1s cubic-bezier(.2,.8,.2,1);
  background:linear-gradient(90deg,#F2A66A,#E9965B);box-shadow:0 1px 6px rgba(233,150,91,.6)}
.goal .pct{float:right;font-weight:900;color:var(--orD)}
.latest .lv{font-size:38px;font-weight:900;line-height:1}
.latest .lv small{font-size:15px;color:var(--muted);font-weight:800;margin-left:3px}
.latest img{width:100%;border-radius:12px;border:1px solid var(--brd);display:block;
  box-shadow:0 8px 22px rgba(20,20,40,.16)}
.badge{position:absolute;top:10px;right:10px;color:#fff;border-radius:10px;padding:6px 11px;
  font-size:11.5px;font-weight:900;background:linear-gradient(135deg,#F2A66A,#E9965B);
  box-shadow:0 5px 14px rgba(233,150,91,.5)}
.meta{display:flex;gap:14px;color:var(--muted);font-size:12.5px;margin-top:8px;flex-wrap:wrap}
.rank-row{display:flex;align-items:center;gap:11px;padding:8px 4px;border-bottom:1px solid var(--brd);
  transition:background .12s}
.rank-row:hover{background:#FFF7F0}
.rank-row:last-child{border-bottom:none}
.rank-row .no{width:24px;height:24px;flex:none;text-align:center;line-height:24px;font-weight:900;
  color:var(--muted);font-size:13px}
.rank-row.top .no{color:#fff;border-radius:8px;background:linear-gradient(135deg,#F2A66A,#E9965B);
  box-shadow:0 3px 8px rgba(233,150,91,.45)}
.rank-row img{width:62px;height:35px;object-fit:cover;border-radius:7px;border:1px solid var(--brd)}
.rank-row .tt{flex:1;font-size:12.5px;line-height:1.35;overflow:hidden;display:-webkit-box;
  -webkit-line-clamp:2;-webkit-box-orient:vertical}
.rank-row .en{color:var(--muted);font-size:11px;margin-top:2px}
.rank-row .vv{font-weight:900;font-size:14px;white-space:nowrap;color:var(--orD)}
.foot{display:flex;justify-content:space-between;color:var(--muted);font-size:11.5px;margin-top:16px;padding:0 4px}
.foot a{color:var(--orD);cursor:pointer;font-weight:800}

/* スマホ最適化: KPIは2列(主役は全幅)、下段は1列、ヘッダは折返し */
@media (max-width: 820px){
  .wrap{padding:12px 12px 24px}
  .head{flex-wrap:wrap;gap:10px;padding:12px}
  .head .spacer{display:none}
  .pills{flex-wrap:wrap}
  .kpis{grid-template-columns:1fr 1fr;gap:10px}
  .kpi.hero{grid-column:1 / -1}
  .kpi .val{font-size:25px}
  .kpi.hero .val{font-size:31px}
  .bottom{grid-template-columns:1fr;gap:12px}
  #chart{height:300px}
  .tcard img{width:54px;height:30px}
  .tcard .vc{font-size:9.5px;padding:1px 5px}
  .goal .big{font-size:38px}
  .foot{flex-direction:column;gap:4px}
}
</style></head>
<body><div class="wrap">

  <div class="head card">
    <div class="avatar" id="avatar"></div>
    <div class="brand"><div class="k" id="brandK">REALTIME ANALYTICS</div>
      <div class="n" id="cname">—</div></div>
    <div class="spacer"></div>
    <div class="pills" id="rangePills"></div>
    <div class="pills grp" id="typePills"></div>
    <div class="spacer"></div>
    <div class="chip">外部・共有流入を除く</div>
    <div class="chip gear">⚙</div>
    <div class="chip live" id="liveChip"></div>
  </div>

  <div class="kpis" id="kpis"></div>

  <div class="panel card">
    <div class="ph"><div class="t" id="chartTitle">動画パフォーマンス</div>
      <div class="r" id="chartMeta"></div></div>
    <div id="chart"></div>
  </div>

  <div class="bottom">
    <div class="panel card goal">
      <div class="sec-t">目標達成度 <span class="prov">登録者目標（仮）</span></div>
      <div><span class="big" id="goalRemain"></span></div>
      <div class="bar"><span id="goalBar"></span></div>
      <div class="muted" style="font-size:12.5px"><span id="goalText"></span>
        <span class="pct" id="goalPct"></span></div>
    </div>

    <div class="panel card latest">
      <div class="sec-t">最新動画</div>
      <div style="position:relative" id="latestWrap"></div>
    </div>

    <div class="panel card">
      <div class="sec-t"><span id="rankTitle">視聴数ランキング</span></div>
      <div id="ranking"></div>
    </div>
  </div>

  <div class="foot">
    <div id="updated"></div>
    <div>自動更新: 10分間隔（このタブを開いている間）</div>
    <a id="resetBtn">設定リセット</a>
  </div>
</div>

<script>
const DATA = __PAYLOAD__;
const RANGES = [["1週間",7],["2週間",14],["1ヶ月",30],["3ヶ月",90],["6ヶ月",180],["1年",365],["全期間",1e9]];
const TYPES = [["全て","all"],["ロング","long"],["ショート","short"]];
let state = {days:90, type:"all"};

const fmt = n => (n||0).toLocaleString("en-US");
const man = n => n>=10000 ? (n/10000).toFixed(n>=100000?0:1)+"万" : fmt(n);
const daysAgo = ms => Math.floor((Date.now()-ms)/86400000);

function filtered(){
  const cut = Date.now() - state.days*86400000;
  return DATA.videos.filter(v =>
    (state.days>=1e9 || v.published_ms>=cut) &&
    (state.type==="all" || v.type===state.type));
}

function renderHeader(){
  const c=DATA.channel;
  document.getElementById("cname").textContent = c.name;
  document.getElementById("brandK").textContent = `REALTIME ANALYTICS ・ 全${fmt(c.video_count)}本`;
  const av = document.getElementById("avatar");
  if(DATA.latest) av.style.backgroundImage = `url(${DATA.latest.thumb})`;
  const rp = document.getElementById("rangePills");
  rp.innerHTML = RANGES.map(([l,d])=>
    `<button class="pill ${state.days===d?'on':''}" data-d="${d}">${l}</button>`).join("");
  rp.querySelectorAll(".pill").forEach(b=>b.onclick=()=>{state.days=+b.dataset.d;renderAll();});
  const tp = document.getElementById("typePills");
  tp.innerHTML = TYPES.map(([l,t])=>
    `<button class="pill ${state.type===t?'on':''}" data-t="${t}">${l}</button>`).join("");
  tp.querySelectorAll(".pill").forEach(b=>b.onclick=()=>{state.type=b.dataset.t;renderAll();});
  const live=document.getElementById("liveChip");
  if(c.is_live){ live.classList.add("live"); live.innerHTML='<span class="dot"></span> LIVE・10分'; }
  else{ live.classList.remove("live"); live.textContent='日次データ（シート値）'; }
}

function subsDelta(c){
  if(c.subs_status!=="ok") return `<span class="muted">蓄積中（${c.accrue_start||'—'}開始）</span>`;
  const d=c.subs_delta_28d;
  if(d>0) return `<span class="delta-up">▲ +${fmt(d)} / 28日</span>`;
  if(d<0) return `<span class="delta-down">▼ ${fmt(d)} / 28日</span>`;
  return `<span class="muted">±0 / 28日</span>`;
}

function renderKpis(){
  const c = DATA.channel;
  const liveSub = c.is_live ? "ライブ" : "シート値";
  const cards = [
    {hero:1, ic:"🔍", lab:"検索流入（累計）", val:fmt(c.search_inflow), sub:"日次データ（外部除く）"},
    {ic:"▶", lab:"総再生数", val:fmt(c.total_views), sub:liveSub},
    {ic:"👥", lab:"登録者数", val:fmt(c.subscribers)+"人", sub:subsDelta(c)},
    {ic:"👍", lab:"高評価合算", val:fmt(c.likes_sum), sub:liveSub},
    {ic:"💬", lab:"コメント合算", val:fmt(c.comments_sum), sub:liveSub},
  ];
  document.getElementById("kpis").innerHTML = cards.map((k,i)=>
    `<div class="kpi card ${k.hero?'hero':''}" style="animation-delay:${i*.05}s">
       <div class="ic">${k.ic}</div>
       <span class="lab">${k.lab}</span><div class="val">${k.val}</div>
       <div class="sub">${k.sub||"&nbsp;"}</div></div>`).join("");
}

function renderChart(){
  const vids = filtered().slice().sort((a,b)=>a.published_ms-b.published_ms);
  const total = vids.reduce((s,v)=>s+v.views,0);
  document.getElementById("chartTitle").textContent = `${rangeLabel()}の動画パフォーマンス`;
  document.getElementById("chartMeta").textContent = `${vids.length} 本・累計 ${fmt(total)} 回再生`;

  const box = document.getElementById("chart");
  box.innerHTML = "";
  if(!vids.length){ box.innerHTML='<div class="muted" style="padding:40px">対象期間にデータがありません。</div>'; return; }

  const W = box.clientWidth, H = box.clientHeight;
  const padL=52,padR=26,padT=78,padB=26;
  const tmin = vids[0].published_ms, tmax = vids[vids.length-1].published_ms;
  const vmax = Math.max(...vids.map(v=>v.views), 1);
  const X = t => tmax===tmin ? (padL+(W-padL-padR)/2) : padL+(t-tmin)/(tmax-tmin)*(W-padL-padR);
  const Y = v => padT+(1-v/vmax)*(H-padT-padB);
  const baseY = Y(0);

  const ns="http://www.w3.org/2000/svg";
  const svg=document.createElementNS(ns,"svg");
  // 面塗り用グラデ（オレンジ）
  const defs=document.createElementNS(ns,"defs");
  const lg=document.createElementNS(ns,"linearGradient");
  lg.setAttribute("id","og");lg.setAttribute("x1","0");lg.setAttribute("y1","0");
  lg.setAttribute("x2","0");lg.setAttribute("y2","1");
  lg.innerHTML='<stop offset="0%" stop-color="#E9965B" stop-opacity="0.30"/>'+
               '<stop offset="100%" stop-color="#E9965B" stop-opacity="0"/>';
  defs.appendChild(lg);svg.appendChild(defs);

  for(let i=0;i<=4;i++){
    const val=vmax*i/4, y=Y(val);
    const ln=document.createElementNS(ns,"line");
    ln.setAttribute("x1",padL);ln.setAttribute("x2",W-padR);
    ln.setAttribute("y1",y);ln.setAttribute("y2",y);ln.setAttribute("class","gridline");
    svg.appendChild(ln);
    const tx=document.createElementNS(ns,"text");
    tx.setAttribute("x",padL-8);tx.setAttribute("y",y+3);tx.setAttribute("text-anchor","end");
    tx.setAttribute("class","glab");tx.textContent=man(Math.round(val));svg.appendChild(tx);
  }
  const ticks=Math.min(5,vids.length);
  for(let i=0;i<ticks;i++){
    const t = tmin + (tmax-tmin)*(ticks<=1?0:i/(ticks-1));
    const tx=document.createElementNS(ns,"text");
    tx.setAttribute("x",X(t));tx.setAttribute("y",H-6);tx.setAttribute("class","xlab");
    const dt=new Date(t);tx.textContent=`${dt.getMonth()+1}/${dt.getDate()}`;svg.appendChild(tx);
  }
  const pts=vids.map(v=>`${X(v.published_ms)},${Y(v.views)}`).join(" ");
  // 面塗り
  const area=document.createElementNS(ns,"polygon");
  area.setAttribute("points",`${pts} ${X(tmax)},${baseY} ${X(tmin)},${baseY}`);
  area.setAttribute("fill","url(#og)");svg.appendChild(area);
  // 折れ線（主系列＝濃オレンジ）
  const pl=document.createElementNS(ns,"polyline");
  pl.setAttribute("points",pts);pl.setAttribute("fill","none");
  pl.setAttribute("stroke","#C9742F");pl.setAttribute("stroke-width","2.5");
  pl.setAttribute("stroke-linejoin","round");
  pl.setAttribute("style","filter:drop-shadow(0 3px 5px rgba(201,116,47,.35))");
  svg.appendChild(pl);
  vids.forEach(v=>{
    const c=document.createElementNS(ns,"circle");
    c.setAttribute("cx",X(v.published_ms));c.setAttribute("cy",Y(v.views));
    c.setAttribute("r","4");c.setAttribute("fill","#fff");
    c.setAttribute("stroke","#C9742F");c.setAttribute("stroke-width","2.5");svg.appendChild(c);
  });
  box.appendChild(svg);
  const vsorted=vids.slice().sort((a,b)=>a.views-b.views);
  vsorted.forEach((v,i)=>{
    const card=document.createElement("div");
    card.className="tcard";
    card.style.left=X(v.published_ms)+"px";
    card.style.top=(Y(v.views)-6)+"px";
    card.style.zIndex=10+i;card.title=v.title;
    card.innerHTML=`<img src="${v.thumb}" loading="lazy"><div class="vc">${man(v.views)}</div>`;
    card.onclick=()=>window.open(v.url,"_blank");
    box.appendChild(card);
  });
}

function renderGoal(){
  const c=DATA.channel;
  document.getElementById("goalRemain").innerHTML = `あと <span>${fmt(c.remaining)}</span><small>人</small>`;
  setTimeout(()=>{document.getElementById("goalBar").style.width = c.goal_pct+"%";},80);
  document.getElementById("goalText").textContent = `目標 ${fmt(c.goal)}人（仮） ・ 現在 ${fmt(c.subscribers)}人`;
  document.getElementById("goalPct").textContent = c.goal_pct+"%";
}

function renderLatest(){
  const v=DATA.latest, w=document.getElementById("latestWrap");
  if(!v){w.innerHTML='<div class="muted">データなし</div>';return;}
  w.innerHTML=`
    <img src="${v.thumb.replace('mqdefault','hqdefault')}">
    <div class="badge">速度 ${v.velocity_rank}位 / ${v.velocity_pool}</div>
    <div class="lv" style="margin-top:12px">${fmt(v.views)}<small>回</small></div>
    <div class="meta">
      <span>👍 ${fmt(v.likes)}</span><span>💬 ${fmt(v.comments)}</span>
      <span>公開: ${daysAgo(v.published_ms)}日前</span></div>
    <div class="meta"><span>再生速度: <b style="color:var(--orD)">${man(v.velocity)} 回/日</b>（生涯平均）</span></div>
    <div class="meta"><span style="line-height:1.4">${v.title}</span></div>`;
}

function renderRanking(){
  const vids=filtered().slice().sort((a,b)=>b.views-a.views).slice(0,20);
  document.getElementById("rankTitle").textContent=`${rangeLabel()} 視聴数ランキング（${vids.length}本）`;
  document.getElementById("ranking").innerHTML = vids.map((v,i)=>`
    <div class="rank-row ${i<3?'top':''}">
      <div class="no">${i+1}</div>
      <img src="${v.thumb}" loading="lazy">
      <div class="tt">${v.title}
        <div class="en">👍 ${fmt(v.likes)}　💬 ${fmt(v.comments)}${v.episode!=='—'?'　'+v.episode:''}</div></div>
      <div class="vv">${man(v.views)}</div>
    </div>`).join("") || '<div class="muted">対象なし</div>';
}

function rangeLabel(){ return (RANGES.find(r=>r[1]===state.days)||["直近"])[0]; }

function renderAll(){ renderHeader();renderKpis();renderChart();renderGoal();renderLatest();renderRanking();
  const c=DATA.channel;
  document.getElementById("updated").textContent =
    c.is_live ? `最終更新: ${c.updated_at}（ライブ）` : `最終更新: シート値(日次) ${c.updated_at}`; }

document.getElementById("resetBtn").onclick=()=>{state={days:90,type:"all"};renderAll();};
window.addEventListener("resize",renderChart);
renderAll();
</script>
</body></html>"""


def render_summary(payload):
    """payload(dict) を埋め込んだ完全な HTML 文字列を返す。"""
    return _TEMPLATE.replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False))
