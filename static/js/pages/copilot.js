TS.page_copilot = async function(){
  const content=document.getElementById('content');
  if(!TS.state.selectedCaseId){content.innerHTML='<div class="panel"><h2>Copilot Brief</h2><p>Select a case first.</p></div>';return;}
  content.innerHTML='<div class="panel"><h2>Banker Copilot Brief</h2><p class="muted">Deterministic assistant: no external LLM call, no hidden data transfer. It converts the Risk Passport into a judge-friendly credit workflow.</p><div id="copilotBody">Loading...</div></div>';
  try{
    const c=await TS.api(`/cases/${TS.state.selectedCaseId}/copilot`);
    const m=await TS.api(`/cases/${TS.state.selectedCaseId}/credit-memo`);
    document.getElementById('copilotBody').innerHTML=`
      <div class="two">
        <div class="card"><h3>Executive summary</h3><p>${c.executive_summary}</p><div class="notice ACTION"><b>Next best action:</b> ${c.next_best_action}</div><h3>Decision position</h3><p>${c.decision_position}</p></div>
        <div class="card"><h3>Credit memo</h3><p>${TS.pill(m.proposed_decision)}</p><p><b>Recommended:</b> ${TS.money(m.recommended_amount_hkd)}</p>${m.sections.map(s=>`<div class="field"><span>${s.title}</span><p>${s.body}</p></div>`).join('')}</div>
      </div>
      <div class="three">
        <div class="card"><h3>Top risk drivers</h3><ul>${c.top_risk_drivers.map(x=>`<li>${x}</li>`).join('')}</ul></div>
        <div class="card"><h3>Required controls</h3><ul>${c.required_controls.map(x=>`<li>${x}</li>`).join('')}</ul></div>
        <div class="card"><h3>Banker questions</h3><ul>${c.banker_questions.map(x=>`<li>${x}</li>`).join('')}</ul></div>
      </div>
      <div class="card"><h3>Objection handling for judges</h3>${c.objection_handling.map(o=>`<div class="field"><span>${o.objection}</span><b>${o.response}</b></div>`).join('')}</div>
      <div class="card"><h3>Demo script</h3>${c.demo_script.map((x,i)=>`<div class="timeline-row"><b>${i+1}. ${x}</b></div>`).join('')}</div>`;
  }catch(e){document.getElementById('copilotBody').innerHTML=`<code>${TS.safe(e.message)}</code>`;}
};
