TS.page_portfolio = async function(){
  const content=document.getElementById('content');
  content.innerHTML=`<div class="panel"><h2>Portfolio Stress Desk</h2><div class="toolbar"><button id="portfolioCsv">Download portfolio CSV</button></div><div id="portfolioBody">Loading...</div></div>`;
  document.getElementById('portfolioCsv').onclick=()=>TS.downloadFile('/exports/portfolio.csv','tradeshield_portfolio.csv').catch(e=>alert(e.message));
  try{
    const p=await TS.api('/portfolio/exposure');
    const s=await TS.api('/portfolio/stress');
    document.getElementById('portfolioBody').innerHTML=`
      <div class="two">
        <div class="card"><h3>Exposure by corridor</h3>${p.corridors.map(c=>`<div class="field"><span>${c.corridor}</span><b>${TS.money(c.requested_hkd)}</b><p class="small muted">${c.cases} cases • high risk ${c.high_risk_cases}</p></div>`).join('')}</div>
        <div class="card"><h3>Stress scenarios</h3>${s.scenarios.map(x=>`<div class="field"><span>${x.name}</span><b>${TS.money(x.stressed_loss_hkd)}</b><p class="small muted">${x.loss_bps_of_exposure} bps of exposure</p></div>`).join('')}</div>
      </div>
      <div class="card"><h3>Risk matrix</h3><div class="table compact"><div class="row header"><div>Case</div><div>SME</div><div>Exposure</div><div>Status</div><div>Risk</div><div>Settlement</div></div>${p.risk_matrix.map(r=>`<div class="row compact-row"><div><b>${r.case_ref}</b></div><div>${r.sme}</div><div>${TS.money(r.requested_hkd)}</div><div>${TS.pill(r.status)}</div><div>${TS.pill(r.risk_category,r.risk_category)}</div><div>${r.settlement_status}</div></div>`).join('')}</div></div>`;
  }catch(e){document.getElementById('portfolioBody').innerHTML=`<code>${TS.safe(e.message)}</code>`;}
};
