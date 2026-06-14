TS.loadCases = async function(){ const data = await TS.api('/cases'); TS.state.cases=data.cases; TS.state.latestRisk=data.latest_risk||{}; TS.state.nextActions=data.next_actions||{}; return data; };
TS.selectCase = async function(id){ TS.state.selectedCaseId=Number(id); TS.state.passport=await TS.api(`/cases/${id}/passport`); TS.state.page='passport'; TS.render(); };
TS.page_cases = async function(){
  const content=document.getElementById('content'); content.innerHTML=`<div class="panel"><h2>Case Queue</h2><div class="toolbar"><button class="primary" id="reloadCases">Reload queue</button><button id="goPortfolio">Open portfolio desk</button></div><div id="caseRows">Loading...</div></div>`;
  document.getElementById('reloadCases').onclick=()=>TS.page_cases();
  document.getElementById('goPortfolio').onclick=()=>{TS.state.page='portfolio';TS.render();};
  try{ const data=await TS.loadCases();
    const rows=[`<div class="row header"><div>Case</div><div>Route</div><div>Exposure</div><div>Status</div><div>Risk</div><div>Next action</div></div>`];
    for(const c of data.cases){ const r=data.latest_risk[c.id]; const n=data.next_actions[c.id]; rows.push(`<div class="row" data-id="${c.id}"><div><b>${c.case_ref}</b><br><span class="small muted">${c.sme_name}</span></div><div>${c.origin_country} → ${c.destination_country}<br><span class="small muted">${c.goods_description}</span></div><div>${TS.money(c.requested_financing_hkd)}<br><span class="small muted">invoice ${TS.money(c.invoice_amount_hkd)}</span></div><div>${TS.pill(c.status)}</div><div>${r?TS.pill(`${r.category} • ${r.score}`,r.category):TS.pill('UNSCORED')}</div><div>${n?`<b>${n.label}</b><p class="small muted">${n.reason}</p>`:'—'}</div></div>`); }
    document.getElementById('caseRows').innerHTML=rows.join(''); document.querySelectorAll('.row[data-id]').forEach(r=>r.onclick=()=>TS.selectCase(r.dataset.id));
  }catch(e){ document.getElementById('caseRows').innerHTML=`<code>${TS.safe(e.message)}</code>`; }
};
