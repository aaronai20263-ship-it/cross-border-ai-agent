async function load() {
  const [s, l] = await Promise.all([fetch('/api/admin/summary'), fetch('/api/admin/leads')]);
  if (!s.ok || !l.ok) throw new Error('Admin API unavailable');
  const summary = await s.json(); const data = await l.json();
  document.getElementById('stats').innerHTML = `<article><span>TODAY</span><h3>${summary.today_consultations}</h3><p>今日咨询人数</p></article><article><span>LEADS</span><h3>${summary.new_leads}</h3><p>今日新增客户</p></article><article><span>QUALIFIED</span><h3>${summary.qualified_leads}</h3><p>高意向客户</p></article>`;
  document.querySelector('#leads tbody').innerHTML = data.leads.map(x => `<tr><td>${new Date(x.created_at).toLocaleString()}</td><td>${esc(x.name)}</td><td>${esc(x.contact)}</td><td>${esc(x.product_interest)}</td><td>${esc(x.budget)}</td><td>${esc(x.lead_status)}</td></tr>`).join('');
}
function esc(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c])); }
load().catch(e => { document.getElementById('stats').innerHTML = `<p>${esc(e.message)}</p>`; });
