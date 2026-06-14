TS.page_llm = async function(){
  const content = document.getElementById('content');

  if(!TS.state.selectedCaseId){
    content.innerHTML = '<div class="panel"><h2>Real LLM Copilot</h2><p>Select a case first.</p></div>';
    return;
  }

  content.innerHTML = `
    <div class="panel">
      <h2>V8 Real LLM Case Copilot</h2>
      <p class="muted">
        This page calls a real local Ollama LLM through the FastAPI backend.
        Answers are grounded in the selected case, risk passport, documents, fraud graph, compliance checks, and evidence bundle.
      </p>

      <div class="two">
        <div class="card">
          <h3>Ask the case</h3>
          <p class="muted">Try: “Should BOCHK approve this case?” or “What conditions should the banker require?”</p>
          <textarea id="llmQuestion" rows="5">Should BOCHK approve this case and what conditions should the banker require?</textarea>
          <button id="llmAskBtn" class="primary">Ask real LLM</button>
        </div>

        <div class="card">
          <h3>Credit memo</h3>
          <p class="muted">Generate a banker-grade memo from the selected Risk Passport.</p>
          <button id="llmMemoBtn">Generate LLM credit memo</button>
          <p class="muted">First answer may take 30–120 seconds on CPU.</p>
        </div>
      </div>

      <div class="card">
        <h3>LLM output</h3>
        <div id="llmMeta" class="notice ACTION">No LLM call yet.</div>
        <pre id="llmOutput">Ask a question or generate a memo.</pre>
      </div>
    </div>
  `;

  const show = (data) => {
    document.getElementById('llmMeta').innerHTML = `
      <b>Mode:</b> ${TS.safe(data.mode)} |
      <b>Provider:</b> ${TS.safe(data.provider || '—')} |
      <b>Model:</b> ${TS.safe(data.model || '—')}
    `;
    document.getElementById('llmOutput').textContent = data.answer || JSON.stringify(data, null, 2);
  };

  document.getElementById('llmAskBtn').onclick = async () => {
    document.getElementById('llmOutput').textContent = 'Calling local LLM...';
    const body = new URLSearchParams();
    body.append('question', document.getElementById('llmQuestion').value);
    const data = await TS.api(`/llm/cases/${TS.state.selectedCaseId}/chat`, {method:'POST', body});
    show(data);
  };

  document.getElementById('llmMemoBtn').onclick = async () => {
    document.getElementById('llmOutput').textContent = 'Generating LLM credit memo...';
    const data = await TS.api(`/llm/cases/${TS.state.selectedCaseId}/credit-memo`);
    show(data);
  };
};
