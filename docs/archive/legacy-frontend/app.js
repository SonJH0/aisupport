const form = document.querySelector('#form');
const input = document.querySelector('#message');
const chatFields = document.querySelector('#chat-fields');
const compareFields = document.querySelector('#compare-fields');
const experience = document.querySelector('#experience');
const job = document.querySelector('#job');
const messages = document.querySelector('#messages');
const image = document.querySelector('#image');
const send = document.querySelector('#send');
const reset = document.querySelector('#reset');
const modes = document.querySelectorAll('[data-mode]');
let history = [];
let mode = 'chat';

function setMode(next) {
  mode = next;
  chatFields.hidden = next === 'compare';
  compareFields.hidden = next !== 'compare';
  input.required = next !== 'compare';
  experience.required = next === 'compare';
  send.textContent = next === 'compare' ? '공고와 경험 비교하기 →' : '질문 보내기 →';
  if (next === 'compare') experience.focus();
  else input.focus();
}

modes.forEach(button => button.addEventListener('click', () => {
  setMode(button.dataset.mode);
  if (button.dataset.text) input.value = button.dataset.text;
}));

function bubble(text, kind) {
  const el = document.createElement('div');
  el.className = 'bubble ' + kind;
  const parts = text.split(/(https?:\/\/[^\s<>]+)/g);
  for (const part of parts) {
    if (/^https?:\/\//i.test(part)) {
      const link = document.createElement('a');
      link.href = part; link.textContent = part; link.target = '_blank'; link.rel = 'noopener noreferrer';
      el.append(link);
    } else el.append(document.createTextNode(part));
  }
  messages.append(el);
}

reset.addEventListener('click', () => {
  history = [];
  messages.replaceChildren();
  input.value = '';
  experience.value = '';
  job.value = '';
  image.value = '';
  setMode('chat');
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  const sendingMode = mode;
  const spec = experience.value.trim();
  const jobText = job.value.trim();
  if (sendingMode === 'compare' && !jobText && !image.files[0]) {
    alert('공고 내용을 입력하거나 공고 이미지를 첨부해 주세요.');
    job.focus();
    return;
  }
  const message = sendingMode === 'compare'
    ? '다음 채용공고와 지원자의 경험을 비교해 주세요. 공고의 각 요건별로 사용자 근거를 인용하여 일치, 정보 부족, 차이로 구분하고, 확인 질문과 우선순위가 있는 보완 행동을 제안하세요. 모르는 내용을 추측하지 마세요.\n\n[지원자의 경험]\n' + spec + '\n\n[채용공고]\n' + (jobText || '첨부된 이미지에서 확인해 주세요.')
    : input.value.trim();
  if (!message) return;
  if (message.length > 10000) { alert('입력 내용이 너무 깁니다. 공고와 경험을 조금 줄여 주세요.'); return; }
  if (image.files[0] && image.files[0].size > 4 * 1024 * 1024) { alert('이미지는 4MB 이하로 선택해 주세요.'); return; }
  bubble(message + (image.files[0] ? '\n[이미지 첨부]' : ''), 'user');
  send.disabled = true;
  reset.disabled = true;
  modes.forEach(button => button.disabled = true);
  send.textContent = '분석 중...';
  try {
    let imageData = null;
    if (image.files[0]) imageData = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(image.files[0]); });
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message, history, image: imageData})
    });
    const result = await res.json();
    if (!res.ok) throw new Error(typeof result.detail === 'string' ? result.detail : '요청을 처리할 수 없습니다.');
    bubble(result.answer, 'assistant');
    if (result.tools?.length) bubble('사용한 도구: ' + result.tools.join(', '), 'tool');
    history.push({role: 'user', content: message}, {role: 'assistant', content: result.answer.slice(0, 10000)});
    history = history.slice(-10);
    input.value = '';
    experience.value = '';
    job.value = '';
    image.value = '';
  } catch (err) {
    bubble(err.message, 'assistant');
  } finally {
    send.disabled = false;
    reset.disabled = false;
    modes.forEach(button => button.disabled = false);
    send.textContent = sendingMode === 'compare' ? '공고와 경험 비교하기 →' : '질문 보내기 →';
  }
});
