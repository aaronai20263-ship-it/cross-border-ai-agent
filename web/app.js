const input = document.getElementById('input');
const chat = document.getElementById('chat');
const imageInput = document.getElementById('imageInput');
const leadForm = document.getElementById('leadForm');
const success = document.getElementById('success');
const sendBtn = document.getElementById('sendBtn');

const state = { imageUploaded: false, messages: [], profile: { product_interest: '', budget: '', use: '' } };

function escapeHtml(value) { return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char])); }
function addMessage(text, who = 'user') {
  const row = document.createElement('div'); row.className = `message ${who}`; row.style.marginTop = '18px';
  row.innerHTML = who === 'assistant' ? `<div class="avatar">玉</div><div class="bubble">${text}</div>` : `<div class="bubble" style="margin-left:auto;background:#171714;color:#fff;border-radius:18px 4px 18px 18px">${escapeHtml(text)}</div>`;
  chat.appendChild(row); chat.scrollTop = chat.scrollHeight; state.messages.push({ who, text });
}
function inferProfile(text) {
  if (/翡翠|手镯|吊坠|戒指|和田玉|玉牌|手串/.test(text)) state.profile.product_interest = text.match(/翡翠|手镯|吊坠|戒指|和田玉|玉牌|手串/)?.[0] || '';
  if (/\d[\d,.]*\s*(万|元|块)/.test(text)) state.profile.budget = text.match(/\d[\d,.]*\s*(?:万|元|块)/)?.[0] || '';
  if (/送人|收藏|日常|佩戴|投资/.test(text)) state.profile.use = text.match(/送人|收藏|日常|佩戴|投资/)?.[0] || '';
}
function reply(text) {
  inferProfile(text); let next;
  if (state.imageUploaded) {
    next = `我已经记录了你的图片。基于目前提供的信息，我会先做<strong>可见特征层面的初步分析</strong>，重点看颜色、光泽、透明度表现、纹理、表面状态与明显瑕疵。<br/><br/>但<strong>仅凭普通照片不能确认天然/处理、真伪、内部结构或实验室鉴定结论</strong>。如果你准备实际购买，我会优先帮你找出需要向卖家核实的关键点。`;
  } else if (!state.profile.budget || !state.profile.product_interest) {
    next = `可以。为了让建议真正有用，我先补齐两个关键变量：<strong>你想买什么，以及预算大约多少？</strong><br/><br/>例如：“翡翠手镯，预算 1–2 万，日常佩戴”。如果已经有具体商品，也可以直接上传图片。`;
  } else {
    next = `收到。你的需求是<strong>${escapeHtml(state.profile.product_interest)}</strong>${state.profile.budget ? `，预算约 <strong>${escapeHtml(state.profile.budget)}</strong>` : ''}。<br/><br/>下一步我会从<strong>材质与可见特征 → 品质因素 → 购买风险 → 预算匹配 → 核验清单</strong>来分析，而不是直接给出“真假”或一个武断价格。<br/><br/>如果你有具体商品图片，现在可以上传，我会继续分析。`;
  }
  setTimeout(() => addMessage(next, 'assistant'), 320);
}
sendBtn.onclick = () => { const value = input.value.trim(); if (!value) return; addMessage(value); input.value = ''; reply(value); };
input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendBtn.click(); } });
document.querySelectorAll('.quick button').forEach(button => button.onclick = () => { input.value = button.dataset.q; sendBtn.click(); });
document.getElementById('startBtn').onclick = () => document.getElementById('consultant').scrollIntoView({ behavior: 'smooth' });
document.getElementById('humanBtn').onclick = () => document.getElementById('lead').scrollIntoView({ behavior: 'smooth' });
imageInput.onchange = () => { const file = imageInput.files?.[0]; if (!file) return; state.imageUploaded = true; addMessage(`已上传图片：${file.name}`); reply('image'); };
leadForm.onsubmit = event => { event.preventDefault(); success.classList.add('show'); leadForm.reset(); };
