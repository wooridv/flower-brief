const dataPath=document.body.dataset.briefingPath||'data/latest.json';
const esc=(s='')=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const legacyStory=s=>s.summary?s:{...s,shortTitle:s.title,date:'',country:'',sourceName:s.source_name||'',sourceUrl:s.source_url||'',imageUrl:s.image||'',summary:s.core||'',whyItMatters:s.why||'',background:'관련 산업 동향을 원문에서 확인하세요.',technology:s.tech||'',marketOutlook:'시장 흐름을 지속적으로 확인해야 합니다.',keywords:[]};
const normalized=d=>({...d,stories:(d.stories||[]).map(legacyStory),flowerWatch:d.flowerWatch||[],mostImportantChange:d.mostImportantChange||d.summary,attentionPoints:d.attentionPoints||[]});
const pathBase=dataPath.includes('../../')?'../../':dataPath.includes('../')?'../':'';

function fallbackFor(category=''){
  const c=category.toLowerCase();
  if(/화훼|절화|품종|flori|breed/.test(c))return'floriculture.svg';
  if(/스마트|온실|green|시설/.test(c))return'greenhouse.svg';
  if(/시장|유통|수출|market/.test(c))return'market.svg';
  return'technology.svg';
}
function imageFor(story){return story.imageUrl?esc(story.imageUrl):`${pathBase}assets/fallback/${fallbackFor(story.category)}`}
function storyCard(s,i){
  const fallback=`${pathBase}assets/fallback/${fallbackFor(s.category)}`;
  return `<article class="story"><div class="story-visual"><img src="${imageFor(s)}" alt="${esc(s.title)}" loading="lazy" onerror="this.onerror=null;this.src='${fallback}'"><div class="story-number">0${i+1}</div><div class="story-tag">${esc(s.category)}</div></div><div class="story-content"><div class="story-meta">${esc(s.date)} · ${esc(s.country)}</div><h2>${esc(s.title)}</h2><p class="story-lead">${esc(s.summary)}</p><div class="mini-block"><b>왜 중요한가</b><p>${esc(s.whyItMatters)}</p></div><div class="mini-block"><b>새로운 기술·제품·서비스</b><p>${esc(s.technology)}</p></div><div class="mini-block"><b>시장 변화 및 전망</b><p>${esc(s.marketOutlook)}</p></div><a class="source-link" target="_blank" rel="noopener noreferrer" href="${esc(s.sourceUrl)}">원문 보기 → ${esc(s.sourceName)}</a></div></article>`;
}
function renderFlowerWatch(items){
  if(!items.length)return;
  document.getElementById('flowerWatchSection').hidden=false;
  document.getElementById('flowerWatch').innerHTML=items.map(x=>`<article class="flower-watch-card"><small>${esc(x.flower)}</small><h3>${esc(x.variety||'품종 동향')}</h3><strong>${esc(x.signal)}</strong><p>${esc(x.evidence)}</p><a href="${esc(x.sourceUrl)}" target="_blank" rel="noopener noreferrer">근거 보기 · ${esc(x.sourceName)}</a></article>`).join('');
}
async function loadBriefing(){
  const r=await fetch(dataPath,{cache:'no-store'});if(!r.ok)throw Error('브리핑을 불러오지 못했습니다.');
  const d=normalized(await r.json());document.title=`${d.date} | 농업·화훼·원예 브리핑`;
  for(const id of ['briefingDate','footerDate'])document.getElementById(id).textContent=d.date;
  document.getElementById('briefingSummary').textContent=d.summary;document.getElementById('signal').textContent=d.signal;
  renderFlowerWatch(d.flowerWatch);document.getElementById('stories').innerHTML=d.stories.map(storyCard).join('');observeStories();
}
function observeStories(){if(!('IntersectionObserver'in window)){document.querySelectorAll('.story').forEach(x=>x.classList.add('show'));return}const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('show');io.unobserve(e.target)}}),{threshold:.12});document.querySelectorAll('.story').forEach(x=>io.observe(x))}
async function loadArchive(){try{const base=pathBase;const r=await fetch(`${base}data/archive.json`,{cache:'no-store'});const xs=await r.json();const q=document.getElementById('archiveList');q.innerHTML=xs.map(x=>`<a class="archive-item" href="${base}briefing/${esc(x.date)}/"><strong>${esc(x.title)}</strong><span>${esc(x.date)} · ${esc(x.signal)}</span></a>`).join('');if(document.querySelector('main').dataset.archivePage==='true')renderArchivePage(xs,base)}catch(e){console.warn('Archive unavailable',e)}}
function renderArchivePage(items,base){document.getElementById('stories').innerHTML=`<section class="archive-page"><div class="eyebrow">BROWSE</div><h2>전체 브리핑</h2><input id="archiveSearch" class="archive-search" placeholder="제목·시그널 검색"><div id="archiveResults"></div></section>`;const out=document.getElementById('archiveResults');const paint=filter=>out.innerHTML=items.filter(x=>JSON.stringify(x).toLowerCase().includes(filter.toLowerCase())).map(x=>`<a class="archive-result" href="${base}briefing/${x.date}/"><small>${esc(x.date)}</small><h3>${esc(x.title)}</h3><p>${esc(x.signal)}</p><span>${x.headlines.map(esc).join(' · ')}</span></a>`).join('')||'<p>검색 결과가 없습니다.</p>';paint('');document.getElementById('archiveSearch').oninput=e=>paint(e.target.value)}
const drawer=document.getElementById('archive'),overlay=document.getElementById('overlay');document.getElementById('archiveBtn').onclick=()=>{drawer.classList.add('open');overlay.classList.add('open')};document.getElementById('closeArchive').onclick=overlay.onclick=()=>{drawer.classList.remove('open');overlay.classList.remove('open')};
loadBriefing().catch(e=>document.querySelector('main').innerHTML=`<div class="error"><h2>${esc(e.message)}</h2><p>해당 날짜의 브리핑 파일이 아직 없습니다.</p></div>`);loadArchive();
