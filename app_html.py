# -*- coding: utf-8 -*-
"""화훼 절화 경매 대시보드 SPA(정적). data/index.json, data/<date>.json 을 읽어 렌더."""

SPA_HTML = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>화훼 절화 경매 브리핑</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<style>
:root{
  --bg:#f5f3ef; --panel:#ffffff; --panel2:#faf8f5; --line:#e9e3da; --line2:#f0ebe3;
  --tx:#221f1b; --mut:#8b8378; --faint:#b6afa2;
  --accent:#e7568c; --accent2:#f4a0c0; --accentSoft:#fde9f1;
  --up:#e23b52; --down:#2f74d0; --neu:#9a9086;
  --mapMin:#f3ead0; --mapMax:#c62f6a; --shadow:0 1px 2px rgba(0,0,0,.04),0 8px 24px rgba(60,40,30,.06);
}
@media(prefers-color-scheme:dark){:root{
  --bg:#151310; --panel:#201d19; --panel2:#1a1713; --line:#332e27; --line2:#26221c;
  --tx:#efe9df; --mut:#a89f92; --faint:#6f665a;
  --accent:#ff77a9; --accent2:#c85a86; --accentSoft:#331b26;
  --up:#ff6b7d; --down:#66a6ff; --neu:#8a8074;
  --mapMin:#3a2f1f; --mapMax:#ff77a9; --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--bg);color:var(--tx);
  font-family:Pretendard,-apple-system,BlinkMacSystemFont,"Malgun Gothic",sans-serif;
  font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased;padding-bottom:40px}
.wrap{max-width:1000px;margin:0 auto;padding:0 16px}
a{color:var(--accent);text-decoration:none}

/* topbar */
.top{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 82%,transparent);
  backdrop-filter:saturate(1.4) blur(10px);border-bottom:1px solid var(--line)}
.top .wrap{display:flex;align-items:center;gap:10px;height:58px}
.brand{font-weight:800;letter-spacing:-.02em;font-size:17px;display:flex;align-items:center;gap:7px;white-space:nowrap}
.brand .dot{width:9px;height:9px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 4px var(--accentSoft)}
.spacer{flex:1}
.datenav{display:flex;align-items:center;gap:6px}
.iconbtn{width:34px;height:34px;border:1px solid var(--line);background:var(--panel);border-radius:10px;
  color:var(--tx);font-size:15px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:.15s}
.iconbtn:hover{border-color:var(--accent);color:var(--accent)}
.iconbtn:disabled{opacity:.35;cursor:default}
select#dsel{appearance:none;border:1px solid var(--line);background:var(--panel);color:var(--tx);
  border-radius:10px;padding:7px 30px 7px 12px;font:inherit;font-weight:600;cursor:pointer;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'><path d='M2 4l4 4 4-4' fill='none' stroke='%238b8378' stroke-width='1.6'/></svg>");
  background-repeat:no-repeat;background-position:right 10px center}
.reallink{font-size:13px;color:var(--mut);border:1px solid var(--line);padding:7px 11px;border-radius:10px;white-space:nowrap;transition:.15s}
.reallink:hover{border-color:var(--accent);color:var(--accent)}

/* hero */
.hero{margin:22px 0 8px;display:flex;flex-wrap:wrap;align-items:flex-end;gap:14px 26px}
.hero .day{font-size:14px;color:var(--mut);font-weight:600}
.hero .big{font-size:40px;font-weight:800;letter-spacing:-.03em;line-height:1.05}
.hero .big .unit{font-size:20px;color:var(--mut);font-weight:700;margin-left:3px}
.badge{display:inline-flex;align-items:center;gap:5px;font-weight:700;font-size:14px;padding:5px 11px;border-radius:999px}
.badge.up{color:var(--up);background:color-mix(in srgb,var(--up) 12%,transparent)}
.badge.down{color:var(--down);background:color-mix(in srgb,var(--down) 12%,transparent)}
.badge.neu{color:var(--neu);background:var(--line2)}
.kpis{display:flex;gap:26px;margin-left:auto}
.kpi .k{font-size:12px;color:var(--mut)}
.kpi .v{font-size:20px;font-weight:800;letter-spacing:-.02em}
.subline{color:var(--mut);font-size:12.5px;margin:2px 0 18px}

/* cards / grid */
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:760px){.grid{grid-template-columns:1fr}.kpis{margin-left:0;width:100%}.hero .big{font-size:34px}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:var(--shadow)}
.card h3{margin:0 0 4px;font-size:15px;font-weight:800;letter-spacing:-.01em}
.card .hint{color:var(--mut);font-size:12px;margin:0 0 14px}

/* share bars */
.bars{display:flex;flex-direction:column;gap:11px}
.bar .row1{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px;gap:8px}
.bar .nm{font-weight:700;font-size:14px}
.bar .vl{font-size:12.5px;color:var(--mut);font-variant-numeric:tabular-nums;white-space:nowrap}
.bar .vl b{color:var(--tx);font-weight:800}
.bar .delta{margin-left:6px;font-weight:700}
.bar .delta.up{color:var(--up)} .bar .delta.down{color:var(--down)} .bar .delta.neu{color:var(--neu)}
.track{height:10px;background:var(--line2);border-radius:6px;overflow:hidden}
.fill{height:100%;width:0;border-radius:6px;background:linear-gradient(90deg,var(--accent2),var(--accent));
  transition:width .9s cubic-bezier(.22,1,.36,1)}
.fill.reg{background:linear-gradient(90deg,#f2c14e,#e7568c)}
.bar.clk{cursor:pointer;border-radius:8px;padding:4px 6px;margin:-4px -6px;transition:background .15s}
.bar.clk:hover{background:var(--line2)}
.bar.clk.sel{background:var(--accentSoft)}
.bar.clk.sel .nm{color:var(--accent)}
#regdetail h3 .rg{color:var(--accent)}
.rgtag{display:inline-block;font-size:11px;color:var(--mut);border:1px solid var(--line);border-radius:6px;padding:1px 6px;margin-left:6px;vertical-align:middle}
.rpill{display:inline-block;font-weight:700;font-size:12.5px;padding:3px 9px;border-radius:8px;cursor:pointer;border:1px solid var(--line);transition:.15s}
.rpill.hi{color:var(--up);background:color-mix(in srgb,var(--up) 8%,transparent)}
.rpill.lo{color:var(--down);background:color-mix(in srgb,var(--down) 8%,transparent)}
.rpill:hover{border-color:var(--accent)}

/* map */
.mapwrap{display:grid;grid-template-columns:1.05fr .95fr;gap:10px;align-items:center}
@media(max-width:520px){.mapwrap{grid-template-columns:1fr}}
#map{width:100%;height:300px}
#map path{stroke:var(--panel);stroke-width:.8;cursor:pointer;transition:fill .8s cubic-bezier(.22,1,.36,1),opacity .15s}
#map path:hover{opacity:.82}
.legend{display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--mut);margin-top:6px}
.legbar{height:8px;flex:1;border-radius:5px;background:linear-gradient(90deg,var(--mapMin),var(--mapMax))}
.tip{position:fixed;pointer-events:none;background:var(--tx);color:var(--bg);font-size:12px;font-weight:600;
  padding:6px 9px;border-radius:8px;opacity:0;transition:opacity .12s;z-index:50;white-space:nowrap}

/* chips */
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{display:inline-flex;align-items:center;gap:6px;padding:7px 12px;border-radius:12px;font-size:13.5px;font-weight:700;
  border:1px solid var(--line);background:var(--panel2)}
.chip .p{font-weight:800}
.chip.up{color:var(--up);border-color:color-mix(in srgb,var(--up) 30%,var(--line))}
.chip.down{color:var(--down);border-color:color-mix(in srgb,var(--down) 30%,var(--line))}
.chip .nm{color:var(--tx)}

/* tables */
.tblcard{margin-top:16px}
.toolbar{display:flex;gap:10px;align-items:center;margin:2px 0 12px;flex-wrap:wrap}
#q{flex:1;min-width:180px;padding:10px 13px;border:1px solid var(--line);border-radius:12px;background:var(--panel2);color:var(--tx);font:inherit}
#q:focus{outline:none;border-color:var(--accent)}
.tblscroll{overflow:auto;max-height:65vh;-webkit-overflow-scrolling:touch;border:1px solid var(--line);border-radius:14px}
table{width:100%;border-collapse:collapse;font-size:13px;background:var(--panel)}
th,td{padding:9px 12px;text-align:left;white-space:nowrap}
thead th{position:sticky;top:0;z-index:2;background:var(--panel2);color:var(--mut);font-weight:700;font-size:12px;box-shadow:inset 0 -1px 0 var(--line)}
tbody tr{border-bottom:1px solid var(--line2)}
tbody tr:last-child{border-bottom:none}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
td.nm{font-weight:700}
.up{color:var(--up);font-weight:700}.down{color:var(--down);font-weight:700}.neu{color:var(--neu)}
.sect-h{display:flex;align-items:baseline;justify-content:space-between;margin:26px 2px 12px}
.sect-h h2{font-size:17px;font-weight:800;letter-spacing:-.02em;margin:0}
.sect-h .m{font-size:12px;color:var(--mut)}
footer{margin-top:30px;color:var(--mut);font-size:12px;text-align:center;line-height:1.7}
.loading{padding:60px 0;text-align:center;color:var(--mut)}
.spin{width:26px;height:26px;border:3px solid var(--line);border-top-color:var(--accent);border-radius:50%;
  margin:0 auto 12px;animation:sp .8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
</style>
<!--EMBED-->
</head>
<body>
<div class="top"><div class="wrap">
  <div class="brand"><span class="dot"></span>절화 경매 브리핑</div>
  <div class="spacer"></div>
  <div class="datenav">
    <button class="iconbtn" id="prev" title="이전 경매일">‹</button>
    <select id="dsel"></select>
    <button class="iconbtn" id="next" title="다음 경매일">›</button>
  </div>
  <a class="reallink" id="reallink" href="https://flower.at.or.kr/real/real2.do" target="_blank" rel="noopener">실시간 상세 ↗</a>
</div></div>

<div class="wrap">
  <div id="app"><div class="loading"><div class="spin"></div>데이터 불러오는 중…</div></div>
</div>
<div class="tip" id="tip"></div>

<script>
const WON=n=>{n=+n||0;if(n>=1e8)return (n/1e8).toFixed(2)+'억';if(n>=1e4)return (n/1e4).toFixed(1)+'만';return Math.round(n).toLocaleString('ko-KR');};
const INT=n=>Math.round(+n||0).toLocaleString('ko-KR');
const SGN=p=>p==null?'신규':(p>=0?'+'+p.toFixed(1)+'%':p.toFixed(1)+'%');
const CLS=p=>p==null?'neu':(p>0?'up':(p<0?'down':'neu'));
const ARR=p=>p==null?'':(p>0?'▲':(p<0?'▼':'–'));
const REGION_LONG={'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천','광주광역시':'광주','대전광역시':'대전','울산광역시':'울산','세종특별자치시':'세종','경기도':'경기','강원도':'강원','강원특별자치도':'강원','충청북도':'충북','충청남도':'충남','전라북도':'전북','전북특별자치도':'전북','전라남도':'전남','경상북도':'경북','경상남도':'경남','제주특별자치도':'제주','제주도':'제주'};

let INDEX=null, GEO=null, CUR=null, CACHE={}, CURP=null, SELREG=null;

async function boot(){
  if(window.__EMBED){ INDEX=window.__EMBED.index; }
  else { try{ INDEX=await (await fetch('data/index.json',{cache:'no-store'})).json(); }
  catch(e){ document.getElementById('app').innerHTML='<div class="loading">데이터가 아직 없습니다.</div>'; return; } }
  const sel=document.getElementById('dsel');
  sel.innerHTML=INDEX.dates.map(d=>`<option value="${d.date}">${d.date} (${d.weekday})</option>`).join('');
  sel.onchange=()=>load(sel.value);
  document.getElementById('prev').onclick=()=>step(1);
  document.getElementById('next').onclick=()=>step(-1);
  // 지도 데이터(실패해도 나머지는 정상)
  loadGeo();
  load(INDEX.latest||INDEX.dates[0].date);
}
function step(dir){
  const i=INDEX.dates.findIndex(d=>d.date===CUR);
  const j=i+dir; if(j<0||j>=INDEX.dates.length)return;
  document.getElementById('dsel').value=INDEX.dates[j].date; load(INDEX.dates[j].date);
}
async function loadGeo(){
  if(window.__EMBED){ GEO=window.__EMBED.geo||null; }
  else { try{ GEO=await (await fetch('korea_provinces.geojson')).json(); }
  catch(e){ try{ GEO=await (await fetch('https://cdn.jsdelivr.net/gh/southkorea/southkorea-maps@master/kostat/2018/json/skorea-provinces-2018-geo.json')).json(); }catch(e2){ GEO=null; } } }
  if(GEO && CUR && CACHE[CUR]) drawMap(CACHE[CUR]);  // 지도 늦게 도착 시 재드로우
}
async function load(date){
  CUR=date;
  const i=INDEX.dates.findIndex(d=>d.date===date);
  document.getElementById('prev').disabled=(i>=INDEX.dates.length-1);
  document.getElementById('next').disabled=(i<=0);
  document.getElementById('dsel').value=date;
  let p=CACHE[date];
  if(!p){ p=window.__EMBED ? window.__EMBED.dates[date] : await (await fetch('data/'+date+'.json',{cache:'no-store'})).json(); CACHE[date]=p; }
  render(p);
}

function render(p){
  const t=p.total, prev=INDEX.dates.find((d,ix)=>ix>INDEX.dates.findIndex(x=>x.date===p.date));
  const app=document.getElementById('app');
  const topItems=p.items.slice(0,10);
  const maxShare=Math.max(...topItems.map(x=>x.share),1);
  const regs=p.regions||[];
  const maxReg=Math.max(...regs.map(r=>r.share),1);

  app.innerHTML=`
  <div class="hero">
    <div>
      <div class="day">${p.date} (${p.weekday}) 경매${prev?` · 직전 ${prev.date}(${prev.weekday}) 대비`:''}</div>
      <div class="big"><span id="cup">0</span></div>
    </div>
    <div>${badge(t.amtChange)}</div>
    <div class="kpis">
      <div class="kpi"><div class="k">총 물량</div><div class="v">${INT(t.qty)}<span style="font-size:12px;color:var(--mut)"> 속</span></div></div>
      <div class="kpi"><div class="k">거래 품목</div><div class="v">${t.items}<span style="font-size:12px;color:var(--mut)"> 종</span></div></div>
      <div class="kpi"><div class="k">산지</div><div class="v">${regs.length||'-'}<span style="font-size:12px;color:var(--mut)"> 지역</span></div></div>
    </div>
  </div>
  <div class="subline">양재동 aT화훼공판장 전자경매 정산가 · 단가 원/속(수수료 미포함)</div>

  <div class="grid">
    <div class="card">
      <h3>많이 나간 품목 <span style="color:var(--accent)">TOP 10</span></h3>
      <p class="hint">거래액 점유율 · 막대 = 비중, 우측 = 거래액·전 경매 대비</p>
      <div class="bars" id="itembars">${topItems.map(it=>barRow(it,maxShare,false)).join('')}</div>
    </div>
    <div class="card">
      <h3>산지별 반입 <span style="color:var(--accent)">지역 분포</span></h3>
      <p class="hint">물량 기준 · 색이 진할수록 반입량 많음</p>
      <div class="mapwrap">
        <div><svg id="map" viewBox="0 0 300 300" preserveAspectRatio="xMidYMid meet"></svg>
          <div class="legend"><span>적음</span><span class="legbar"></span><span>많음</span></div></div>
        <div class="bars" id="regbars">${regs.slice(0,8).map(r=>regRow(r,maxReg)).join('')||'<div class="hint">지역 데이터 없음</div>'}</div>
      </div>
      ${regs.length?'<p class="hint" style="margin:12px 0 0">👆 지도 또는 지역을 클릭하면 그 지역 품목별 내역이 아래에 표시됩니다</p>':''}
    </div>
  </div>

  ${regs.length?'<div id="regdetail" class="card" style="margin-top:16px"></div>':''}

  <div class="sect-h"><h2>가격 등락</h2><span class="m">주요 품목(거래액 300만원+) · 직전 경매 대비</span></div>
  <div class="grid">
    <div class="card"><h3 style="color:var(--up)">📈 상승 TOP</h3><div class="chips" style="margin-top:12px">${(p.risers||[]).map(chip).join('')||'<span class="hint">해당 없음</span>'}</div></div>
    <div class="card"><h3 style="color:var(--down)">📉 하락 TOP</h3><div class="chips" style="margin-top:12px">${(p.fallers||[]).map(chip).join('')||'<span class="hint">해당 없음</span>'}</div></div>
  </div>

  ${(p.itemRegionPrice&&p.itemRegionPrice.length)?`
  <div class="sect-h"><h2>품목별 산지 최고·최저가</h2><span class="m">지역별 평균 낙찰단가 비교 · 실시간 경매 기준 · 산지 클릭 가능</span></div>
  <div class="tblscroll">
    <table><thead><tr><th>품목</th><th>🔺 최고가 산지</th><th class="num">최고 평균단가</th><th>🔻 최저가 산지</th><th class="num">최저 평균단가</th><th class="num">격차</th></tr></thead>
    <tbody>${p.itemRegionPrice.map(r=>`<tr><td class="nm">${esc(r.name)}</td><td><span class="rpill hi" data-region="${esc(r.hi.region)}">${esc(r.hi.region)}</span></td><td class="num up">${INT(r.hi.price)}원</td><td><span class="rpill lo" data-region="${esc(r.lo.region)}">${esc(r.lo.region)}</span></td><td class="num down">${INT(r.lo.price)}원</td><td class="num">+${r.gapPct}%</td></tr>`).join('')}</tbody></table>
  </div>`:''}

  <div class="sect-h"><h2>품목 요약</h2><span class="m">${p.items.length}개 품목 · 거래액순</span></div>
  <div class="tblscroll">
    <table><thead><tr><th>품목</th><th class="num">평균단가</th><th class="num">전대비</th><th class="num">물량(속)</th><th class="num">거래액</th><th class="num">비중</th></tr></thead>
    <tbody>${p.items.map(it=>`<tr><td class="nm">${esc(it.name)}</td><td class="num">${INT(it.wavg)}</td><td class="num ${CLS(it.change)}">${it.change==null?'신규':SGN(it.change)}</td><td class="num">${INT(it.qty)}</td><td class="num">${WON(it.amt)}</td><td class="num">${it.share}%</td></tr>`).join('')}</tbody></table>
  </div>

  <div class="sect-h"><h2>전체 세부</h2><span class="m">품종·등급별 · 검색 가능</span></div>
  <div class="toolbar"><input id="q" type="search" placeholder="🔍 품목·품종·등급 검색 (예: 백합, 옐로우윈, 특2)"><span class="m" id="qn"></span></div>
  <div class="tblscroll">
    <table id="dtable"><thead><tr><th>품목</th><th>품종</th><th>등급</th><th class="num">평균</th><th class="num">최고</th><th class="num">최저</th><th class="num">물량</th><th class="num">거래액</th></tr></thead>
    <tbody>${p.detail.map(r=>`<tr><td class="nm">${esc(r.pum)}</td><td>${esc(r.good)}</td><td>${esc(r.lv)}</td><td class="num">${INT(r.avg)}</td><td class="num">${INT(r.max)}</td><td class="num">${INT(r.min)}</td><td class="num">${INT(r.qty)}</td><td class="num">${WON(r.amt)}</td></tr>`).join('')}</tbody></table>
  </div>

  <footer>
    데이터 출처: <a href="https://flower.at.or.kr/real/real2.do" target="_blank" rel="noopener">aT 화훼유통정보시스템 실시간 경매현황 ↗</a><br>
    더 자세한 내용(공판장·품종별 실시간)은 위 링크에서 확인하세요 · 생성 ${INDEX.generated||''}
  </footer>`;

  CURP=p;
  countUp(document.getElementById('cup'), t.amt);
  requestAnimationFrame(()=>{ document.querySelectorAll('.fill').forEach(f=>{ f.style.width=f.dataset.w+'%'; }); });
  drawMap(p);
  wireSearch(p);
  // 지역 막대 클릭 → 상세
  document.querySelectorAll('#regbars .bar.clk').forEach(b=>{ b.onclick=()=>selectRegion(b.dataset.region); });
  // 최고/최저가 표의 산지 pill 클릭 → 해당 지역 상세로 이동
  document.querySelectorAll('.rpill[data-region]').forEach(el=>{ el.onclick=()=>{ selectRegion(el.dataset.region); const rd=document.getElementById('regdetail'); if(rd)rd.scrollIntoView({behavior:'smooth',block:'center'}); }; });
  if(regs.length){ const keep=(SELREG&&regs.find(r=>r.name===SELREG))?SELREG:regs[0].name; selectRegion(keep); }
}

function badge(ch){
  if(ch==null)return '<span class="badge neu">비교 기준</span>';
  const c=ch>0?'up':(ch<0?'down':'neu');
  return `<span class="badge ${c}">${ARR(ch)} ${Math.abs(ch).toFixed(1)}% <span style="opacity:.7;font-weight:600">전 경매 대비</span></span>`;
}
function barRow(it,mx,reg){
  const w=Math.max(2, it.share/mx*100);
  const d=it.change==null?'':`<span class="delta ${CLS(it.change)}">${ARR(it.change)}${Math.abs(it.change).toFixed(1)}%</span>`;
  return `<div class="bar"><div class="row1"><span class="nm">${esc(it.name)}</span>
    <span class="vl"><b>${WON(it.amt)}원</b> · ${it.share}%${d}</span></div>
    <div class="track"><div class="fill" data-w="${w}"></div></div></div>`;
}
function regRow(r,mx){
  const w=Math.max(2, r.share/mx*100);
  return `<div class="bar clk" data-region="${esc(r.name)}"><div class="row1"><span class="nm">${esc(r.name)}</span>
    <span class="vl"><b>${INT(r.qty)}속</b> · ${r.share}%</span></div>
    <div class="track"><div class="fill reg" data-w="${w}"></div></div></div>`;
}
function itemRegBar(it,mx){
  const w=Math.max(2, it.qty/mx*100);
  return `<div class="bar"><div class="row1"><span class="nm">${esc(it.name)}</span>
    <span class="vl"><b>${INT(it.qty)}속</b> · ${it.share}% · 평균 ${INT(it.avg)}원</span></div>
    <div class="track"><div class="fill" data-w="${w}"></div></div></div>`;
}
function selectRegion(name){
  const p=CURP; if(!p)return; SELREG=name;
  const r=(p.regions||[]).find(x=>x.name===name);
  const el=document.getElementById('regdetail'); if(!el)return;
  if(!r||!r.items||!r.items.length){ el.innerHTML='<p class="hint">해당 지역 상세 데이터가 없습니다.</p>'; return; }
  const mx=Math.max(...r.items.map(i=>i.qty),1);
  el.innerHTML=`<h3>📍 <span class="rg">${esc(name)}</span> 산지 품목별 내역 <span class="rgtag">${INT(r.qty)}속 · ${WON(r.amt)}원 · ${r.share}%</span></h3>
    <p class="hint">이 지역에서 반입된 품목(물량 기준 상위 ${Math.min(r.items.length,12)}종)</p>
    <div class="bars">${r.items.slice(0,12).map(i=>itemRegBar(i,mx)).join('')}</div>`;
  requestAnimationFrame(()=>{ el.querySelectorAll('.fill').forEach(f=>{f.style.width=f.dataset.w+'%';}); });
  // 막대 하이라이트
  document.querySelectorAll('#regbars .bar').forEach(b=>b.classList.toggle('sel', b.dataset.region===name));
  highlightMap(name);
}
function highlightMap(name){
  if(!window.__MAPSEL)return;
  window.__MAPSEL.attr('stroke',f=>{const s=REGION_LONG[f.properties.name]||f.properties.name;return s===name?'var(--accent)':'var(--panel)';})
    .attr('stroke-width',f=>{const s=REGION_LONG[f.properties.name]||f.properties.name;return s===name?2.2:0.8;});
}
function chip(r){
  return `<span class="chip ${CLS(r.change)}"><span class="nm">${esc(r.name)}</span> <span class="p">${SGN(r.change)}</span>
    <span style="color:var(--mut);font-weight:600">${INT(r.wavg)}원</span></span>`;
}

function drawMap(p){
  const svg=d3.select('#map'); svg.selectAll('*').remove();
  if(!GEO||!p.regions||!p.regions.length){ document.querySelector('.mapwrap').style.gridTemplateColumns='1fr'; document.getElementById('map').style.display='none'; return; }
  document.getElementById('map').style.display='';
  const byName={}; p.regions.forEach(r=>byName[r.name]=r);
  const mx=Math.max(...p.regions.map(r=>r.qty),1);
  const W=300,H=300;
  const proj=d3.geoMercator().fitSize([W,H],GEO);
  const path=d3.geoPath(proj);
  const cssMin=getComputedStyle(document.documentElement).getPropertyValue('--mapMin').trim();
  const cssMax=getComputedStyle(document.documentElement).getPropertyValue('--mapMax').trim();
  const scale=d3.scaleSequential(t=>d3.interpolate(cssMin,cssMax)(t)).domain([0,1]);
  const tip=document.getElementById('tip');
  const paths=svg.attr('viewBox',`0 0 ${W} ${H}`).selectAll('path').data(GEO.features).enter().append('path')
    .attr('d',path)
    .attr('fill','var(--line2)')
    .style('cursor','pointer')
    .on('mousemove',(ev,f)=>{const s=REGION_LONG[f.properties.name]||f.properties.name;const r=byName[s];
      tip.style.opacity=1;tip.style.left=(ev.clientX+12)+'px';tip.style.top=(ev.clientY+12)+'px';
      tip.textContent=r?`${s} · ${INT(r.qty)}속 (${r.share}%) · 클릭`:`${s} · 반입 없음`;})
    .on('mouseleave',()=>tip.style.opacity=0)
    .on('click',(ev,f)=>{const s=REGION_LONG[f.properties.name]||f.properties.name;if(byName[s])selectRegion(s);});
  window.__MAPSEL=paths;
  paths.transition().duration(800)
    .attr('fill',f=>{const s=REGION_LONG[f.properties.name]||f.properties.name;const r=byName[s];return r?scale(Math.pow(r.qty/mx,0.7)):'var(--line2)';});
  if(SELREG)highlightMap(SELREG);
}

function wireSearch(p){
  const q=document.getElementById('q'), qn=document.getElementById('qn');
  const rows=[...document.querySelectorAll('#dtable tbody tr')];
  const upd=()=>{const s=q.value.trim();let n=0;rows.forEach(r=>{const hit=!s||r.textContent.indexOf(s)>=0;r.style.display=hit?'':'none';if(hit)n++;});qn.textContent=s?`${n}건`:`${rows.length}건`;};
  q.oninput=upd; upd();
}
function countUp(el,target){
  const dur=900,t0=performance.now();
  function fr(t){const k=Math.min(1,(t-t0)/dur);const e=1-Math.pow(1-k,3);const v=target*e;
    el.innerHTML=WON(v)+'<span class="unit">원</span>';if(k<1)requestAnimationFrame(fr);}
  requestAnimationFrame(fr);
}
function esc(s){return String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
boot();
</script>
</body>
</html>
"""
