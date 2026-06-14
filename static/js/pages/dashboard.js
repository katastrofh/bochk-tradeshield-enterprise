TS.page_dashboard = async function(){
  const content = document.getElementById('content');
  content.innerHTML = `<div class="panel"><h2>Enterprise Control Tower</h2><p class="muted">V6 is structured like a bank operating layer: portfolio view, case queue, risk passport, copilot brief, decision gates, fraud graph, and audit governance.</p><div id="dashBody">Loading...</div></div>`;
  try{
    const data = await TS.api('/dashboard/summary'); TS.renderKpis(data);
    const cmd = await TS.api('/operations/command-center');
    document.getElementById('dashBody').innerHTML = `
      <div class="two">
        <div class="card"><h3>Operating model</h3>${data.operating_model.map(x=>TS.pill(x)).join(' ')}<div class="notice"><b>V6 fix:</b> downloads use authenticated Bearer requests; model version is aligned; audit CSV is officer-visible for demo.</div></div>
        <div class="card"><h3>Corridor exposure</h3>${data.exposure_by_corridor.map(c=>`<div class="field"><span>${c.corridor}</span><b>${TS.money(c.requested_hkd)} • ${c.cases} cases</b></div>`).join('')}</div>
      </div>
      <div class="card"><h3>Live Command Center</h3>${cmd.queue.map(q=>`<div class="field"><span>${q.case_ref} • ${q.status} • ${q.risk}</span><b>${q.next_action.label}</b><p class="small muted">${q.next_action.reason}</p></div>`).join('')}</div>`;
  }catch(e){ content.innerHTML += `<code>${TS.safe(e.message)}</code>`; }
};
