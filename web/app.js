const input = document.getElementById('input');
const chat = document.getElementById('chat');
const imageInput = document.getElementById('imageInput');
const leadForm = document.getElementById('leadForm');
const success = document.getElementById('success');
const sendBtn = document.getElementById('sendBtn');
const state = { image: null, profile: { product_interest: '', budget: '', use: '' }, session_id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) };

function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c])); }
function addMessage(text, who = 'user') {
  const row = document.createElement('div'); row.className = `message ${who}`; row.style.marginTop = '18px';
  row.innerHTML = who === 'assistant' ? `<div class="avatar">玉</div><div class="bubble">${text}</div>` : `<div class="bubble" style="margin-left:auto;background:#171714;color:#fff;border-radius:18px 4px 18px 18px">${escapeHtml(text)}</div>`;
  chat.appendChild(row); chat.scrollTop = chat.scrollHeight;
}
function inferProfile(text) {
  const p = state.profile;
  const product = text.match(/翡翠|和田玉|手镯|吊坠|戒指|玉牌|手串/); if (product) p.product_interest = product[0];
  const budget = text.match(/(?:预算|大概|约|准备花)\s*([\d,.]+\s*(?:万|元|块))/); if (budget) p.budget = budget[1];
  const use = text.match(/送人|收藏|日常|佩戴/); if (use) p.use = use[0];
}
async function askAI(message) {
  inferProfile(message); sendBtn.disabled = true; sendBtn.textContent = '分析中…';
  try {
    const res = await fetch('/api/chat', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ message, profile: state.profile, session_id: state.session_id, image: state.image }) });
    const data = await res.json(); if (!res.ok) throw new Error(data.error || 'AI 服务暂不可用');
    state.profile = data.profile || state.profile; addMessage(escapeHtml(data.answer).replace(/\n/g, '<br>'), 'assistant');
  } catch (err) { addMessage(`<strong>暂时无法完成 AI 分析。</strong><br>${escapeHtml(err.message)}<br><br>请检查后端服务和 AI_API_KEY 配置。`, 'assistant'); }
  finally { sendBtn.disabled = false; sendBtn.textContent = '发送'; }
}
sendBtn.onclick = () => { const value = input.value.trim(); if (!value) return; addMessage(value); input.value = ''; askAI(value); };
input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendBtn.click(); } });
document.querySelectorAll('.quick button').forEach(b => b.onclick = () => { input.value = b.dataset.q; sendBtn.click(); });
document.getElementById('startBtn').onclick = () => document.getElementById('consultant').scrollIntoView({behavior:'smooth'});
document.getElementById('humanBtn').onclick = () => document.getElementById('lead').scrollIntoView({behavior:'smooth'});
imageInput.onchange = () => { const file = imageInput.files?.[0]; if (!file) return; if (file.size > 8 * 1024 * 1024) { alert('图片不能超过 8MB'); imageInput.value=''; return; } const reader = new FileReader(); reader.onload = () => { state.image = reader.result; state.imageUploaded = true; addMessage(`已上传图片：${file.name}`); askAI('我上传了一张玉石图片，请先做可见特征层面的初步分析，并告诉我还需要哪些信息。'); }; reader.readAsDataURL(file); };
leadForm.onsubmit = async e => { e.preventDefault(); const contact = document.getElementById('contact').value.trim(); if (!contact) return; const lastQuestion = [...chat.querySelectorAll('.message.user .bubble')].pop()?.textContent || ''; const res = await fetch('/api/leads', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name: document.getElementById('name').value.trim(), contact, source:'web', product_interest:state.profile.product_interest, budget:state.profile.budget, user_question:lastQuestion, image_uploaded:Boolean(state.image), ai_summary:'由玉石 AI 顾问会话生成；等待人工跟进。'})}); const data = await res.json(); if (!res.ok) { alert(data.error || '提交失败'); return; } success.classList.add('show'); leadForm.reset(); };
