TS.renderNav = function(){
  const nav = document.getElementById('nav');
  nav.innerHTML = TS.pages.map(([id,label])=>`<button class="nav-btn ${TS.state.page===id?'active':''}" data-page="${id}">${label}</button>`).join('');
  nav.querySelectorAll('button').forEach(b=>b.onclick=()=>{TS.state.page=b.dataset.page;TS.render();});
};
TS.renderKpis = function(summary){
  const p = summary?.portfolio || {};
  document.getElementById('kpis').innerHTML = [
    ['Cases', p.case_count ?? '—'],
    ['Requested', TS.money(p.total_requested_hkd)],
    ['Scored', p.scored_cases ?? '—'],
    ['Audit chain', summary?.audit_chain?.valid ? 'valid' : '—']
  ].map(([a,b])=>`<div class="kpi"><span>${a}</span><b>${b}</b></div>`).join('');
};
TS.render = function(){ TS.renderNav(); const fn = TS[`page_${TS.state.page}`] || TS.page_dashboard; fn(); };
