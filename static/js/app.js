TS.refreshAll = async function(){
  try{
    const summary=await TS.api('/dashboard/summary'); TS.renderKpis(summary);
    await TS.loadCases();
    if(TS.state.cases.length && !TS.state.selectedCaseId){
      TS.state.selectedCaseId=TS.state.cases[0].id;
      TS.state.passport=await TS.api(`/cases/${TS.state.selectedCaseId}/passport`);
    }
  }catch(e){ console.warn(e); }
  TS.render();
};
document.addEventListener('DOMContentLoaded',()=>{
  TS.renderNav(); TS.renderKpis(null); TS.render();
  const demo = {officer:['officer@tradeshield.ai','demo12345'],manager:['manager@tradeshield.ai','demo12345'],sme:['sme@tradeshield.ai','demo12345'],admin:['admin@tradeshield.ai','ChangeMe123!']};
  document.querySelectorAll('[data-demo]').forEach(b=>b.onclick=()=>{const [e,p]=demo[b.dataset.demo];document.getElementById('email').value=e;document.getElementById('password').value=p;TS.loginAs(e,p).catch(err=>document.getElementById('loginStatus').textContent=err.message);});
  document.getElementById('loginBtn').onclick=()=>TS.loginAs(document.getElementById('email').value.trim(),document.getElementById('password').value).catch(err=>document.getElementById('loginStatus').textContent=err.message);
  document.getElementById('logoutBtn').onclick=()=>{localStorage.removeItem('ts_token');location.reload();};
  if(TS.state.token){TS.api('/auth/me').then(u=>{TS.state.user=u;document.getElementById('currentUser').textContent=u.full_name;document.getElementById('currentRole').textContent=u.role;document.getElementById('loginStatus').textContent=`Session restored: ${u.email}`;return TS.refreshAll();}).catch(()=>localStorage.removeItem('ts_token'));}
});
