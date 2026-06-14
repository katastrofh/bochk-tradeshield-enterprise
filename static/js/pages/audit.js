TS.page_audit = async function(){
  const content=document.getElementById('content');
  content.innerHTML='<div class="panel"><h2>Audit & Governance</h2><div class="toolbar"><button id="auditCsv">Download audit CSV</button></div><div id="auditBody">Loading...</div></div>';
  document.getElementById('auditCsv').onclick=()=>TS.downloadFile('/exports/audit.csv','tradeshield_audit.csv').catch(e=>alert(e.message));
  try{
    const a=await TS.api('/audit'); const m=await TS.api('/governance/model-registry');
    document.getElementById('auditBody').innerHTML=`<div class="two"><div class="card"><h3>Audit chain</h3><p>Valid: <b>${a.chain.valid}</b></p><p class="small muted">Latest hash: ${a.chain.latest_hash||'—'}</p>${a.events.slice(0,20).map(ev=>`<div class="audit-item"><b>${ev.event_type}</b><p>${ev.event_summary}</p><code>${ev.event_hash}</code></div>`).join('')}</div><div class="card"><h3>Model registry</h3>${m.map(x=>`<div class="field"><span>${x.model_name} • ${x.version}</span><b>${x.owner}</b><p class="small muted">${x.validation_status}</p><p class="small muted">${x.limitations}</p></div>`).join('')}</div></div>`;
  }catch(e){document.getElementById('auditBody').innerHTML=`<code>${TS.safe(e.message)}</code>`;}
};
