TS.page_ai = async function(){
  const content = document.getElementById('content');

  if(!TS.state.selectedCaseId){
    content.innerHTML = '<div class="panel"><h2>AI Workbench</h2><p>Select a case first.</p></div>';
    return;
  }

  content.innerHTML = `
    <div class="panel">
      <h2>V7 AI Workbench</h2>
      <p class="muted">
        Visible AI layer: Document AI, Explainable Risk AI, GenAI Memo Composer, and Ask-the-Case AI.
        Prototype runs locally with deterministic outputs; production should connect to BOCHK-validated models.
      </p>
      <div id="aiBody">Loading AI outputs...</div>
    </div>
  `;

  try{
    const id = TS.state.selectedCaseId;
    const [docAI, riskAI, memo] = await Promise.all([
      TS.api(`/ai/cases/${id}/document-intelligence`),
      TS.api(`/ai/cases/${id}/risk-explanation`),
      TS.api(`/ai/cases/${id}/genai-memo`)
    ]);

    document.getElementById('aiBody').innerHTML = `
      <div class="three">
        <div class="card">
          <h3>Document AI</h3>
          <p>${TS.pill(docAI.ai_module)}</p>
          <p><b>Confidence:</b> ${docAI.overall_confidence}</p>
          <p><b>Human review:</b> ${docAI.human_review_required ? 'required' : 'not required'}</p>
          <h4>Missing fields</h4>
          <ul>${(docAI.missing_fields || []).map(x=>`<li>${TS.safe(x)}</li>`).join('') || '<li>None</li>'}</ul>
          <h4>Discrepancies</h4>
          <ul>${(docAI.discrepancies || []).map(x=>`<li>${TS.safe(x)}</li>`).join('') || '<li>None</li>'}</ul>
        </div>

        <div class="card">
          <h3>Explainable Risk AI</h3>
          <p>${TS.pill(riskAI.risk_category)}</p>
          <p><b>Score:</b> ${riskAI.risk_score}</p>
          <p><b>Estimated PD:</b> ${riskAI.estimated_default_probability_pct}%</p>
          <p><b>Estimated fraud:</b> ${riskAI.estimated_fraud_probability_pct}%</p>
          <p>${TS.safe(riskAI.plain_english_explanation)}</p>
        </div>

        <div class="card">
          <h3>GenAI Credit Memo</h3>
          <p>${TS.pill(memo.proposed_decision)}</p>
          <p><b>Recommended limit:</b> ${TS.money(memo.recommended_limit_hkd)}</p>
          <p>${TS.safe(memo.executive_summary)}</p>
        </div>
      </div>

      <div class="two">
        <div class="card">
          <h3>Reason codes</h3>
          ${(riskAI.reason_codes || []).map(r=>`
            <div class="field">
              <span>${TS.safe(r.code)} • weight ${r.weight}</span>
              <b>${TS.safe(r.reason)}</b>
            </div>
          `).join('') || '<p>No major reason codes yet.</p>'}
        </div>

        <div class="card">
          <h3>Conditions precedent</h3>
          <ul>${(memo.conditions_precedent || []).map(x=>`<li>${TS.safe(x)}</li>`).join('')}</ul>
          <h3>Banker questions</h3>
          <ul>${(memo.banker_questions || []).map(x=>`<li>${TS.safe(x)}</li>`).join('')}</ul>
        </div>
      </div>

      <div class="card">
        <h3>Ask-the-Case AI</h3>
        <p class="muted">Ask: “Why is this risky?”, “Can we approve?”, “What documents are missing?”, or “Can settlement be released?”</p>
        <div class="ask-row">
          <input id="aiQuestion" value="Why is this case risky?" />
          <button id="aiAskBtn" class="primary">Ask</button>
        </div>
        <div id="aiAnswer" class="notice ACTION">Answer will appear here.</div>
      </div>

      <div class="card">
        <h3>Model governance</h3>
        <pre>${TS.json(riskAI.model_governance)}</pre>
      </div>
    `;

    document.getElementById('aiAskBtn').onclick = async () => {
      const q = document.getElementById('aiQuestion').value;
      const body = new URLSearchParams();
      body.append('question', q);
      const ans = await TS.api(`/ai/cases/${id}/ask`, {method:'POST', body});
      document.getElementById('aiAnswer').innerHTML = `
        <b>Question:</b> ${TS.safe(ans.question)}<br/>
        <b>Answer:</b> ${TS.safe(ans.answer)}<br/>
        <span class="muted">${TS.safe(ans.disclaimer)}</span>
      `;
    };
  }catch(e){
    document.getElementById('aiBody').innerHTML = `<code>${TS.safe(e.message)}</code>`;
  }
};
