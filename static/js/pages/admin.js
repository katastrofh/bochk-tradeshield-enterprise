TS.page_admin = async function(){
 const content=document.getElementById('content');
 content.innerHTML='<div class="panel"><h2>Admin / Debug</h2><p class="muted">Operational diagnostics for judging and debugging.</p><div id="debugBody">Loading...</div></div>';
 try{
  const h=await TS.api('/health'); const s=await TS.api('/debug/seed-status'); const o=await TS.api('/operations/command-center');
  content.querySelector('#debugBody').innerHTML=`<div class="three"><div class="card"><h3>Health</h3><code>${TS.json(h)}</code></div><div class="card"><h3>Seed status</h3><code>${TS.json(s)}</code></div><div class="card"><h3>Command center</h3><code>${TS.json(o)}</code></div></div>`;
 }catch(e){content.querySelector('#debugBody').innerHTML=`<code>${TS.safe(e.message)}</code>`;}
};
