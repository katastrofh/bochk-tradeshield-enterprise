TS.headers = function(extra={}){ return { ...extra, ...(TS.state.token ? {Authorization:`Bearer ${TS.state.token}`} : {}) }; };
TS.api = async function(path, opts={}){
  const res = await fetch(path, {...opts, headers: TS.headers(opts.headers || {})});
  const text = await res.text();
  let data = null; try { data = text ? JSON.parse(text) : {}; } catch { data = text; }
  if(!res.ok){ throw new Error(typeof data === "string" ? data : (data.detail || JSON.stringify(data))); }
  return data;
};
TS.downloadFile = async function(path, filename){
  const res = await fetch(path, {headers: TS.headers()});
  if(!res.ok){ const txt = await res.text(); throw new Error(txt || `Download failed: ${res.status}`); }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename || 'download'; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(url), 1000);
};
TS.loginAs = async function(email,password){
  const body = new URLSearchParams(); body.append("email", email); body.append("password", password);
  const data = await TS.api('/auth/login',{method:'POST',body});
  TS.state.token = data.access_token; TS.state.user = data; localStorage.setItem('ts_token', data.access_token);
  document.getElementById('currentUser').textContent = data.full_name; document.getElementById('currentRole').textContent = data.role;
  document.getElementById('loginStatus').textContent = `Logged in as ${data.email}`;
  await TS.refreshAll();
};
TS.money = x => x===null||x===undefined ? '—' : `HK$${Number(x).toLocaleString()}`;
TS.pill = (txt, cls='') => `<span class="pill ${cls}">${txt || '—'}</span>`;
TS.safe = x => String(x ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
TS.json = x => TS.safe(JSON.stringify(x, null, 2));
