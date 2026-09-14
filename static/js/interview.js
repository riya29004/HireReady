/* ============================================================
   HireReady — interview.js
   Location: static/js/interview.js

   Depends on: dashboard.js (toggleTheme, handleLogout, etc.)
   Calls:
     POST /api/interview/generate  → get questions
     POST /api/interview/evaluate  → score each answer
     POST /api/interview/complete  → save session to DB
   ============================================================ */

'use strict';

/* ── Config state (set by setup screen) ── */
let cfg = {
  subjects:   ['dsa','dbms','os','cn'],
  difficulty: 'medium',
  count:      5,
  type:       'mixed',
};

/* ── Session state ── */
let questions      = [];
let currentIndex   = 0;
let scores         = [];
let dbSessionId    = null;   // returned by /api/interview/start
let timerSecs      = 0;
let timerHandle    = null;
let startTimestamp = null;

/* ============================================================
   SETUP CONTROLS
   ============================================================ */

function toggleSubject(btn) {
  const sub = btn.dataset.subject;
  btn.classList.toggle('active');
  if (btn.classList.contains('active')) {
    if (!cfg.subjects.includes(sub)) cfg.subjects.push(sub);
  } else {
    cfg.subjects = cfg.subjects.filter(s => s !== sub);
  }
  // Ensure at least 1 is always selected
  if (cfg.subjects.length === 0) {
    btn.classList.add('active');
    cfg.subjects.push(sub);
  }
}

function setDifficulty(btn) {
  document.querySelectorAll('.iv-diff-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  cfg.difficulty = btn.dataset.level;
}

function setType(btn) {
  document.querySelectorAll('.iv-type-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  cfg.type = btn.dataset.type;
}

function changeCount(delta) {
  cfg.count = Math.min(15, Math.max(3, cfg.count + delta));
  document.getElementById('qCountDisplay').textContent = cfg.count;
}

/* ============================================================
   START INTERVIEW
   ============================================================ */

async function startInterview() {
  const btn    = document.getElementById('startBtn');
  const label  = document.getElementById('startBtnLabel');
  const loader = document.getElementById('startBtnLoader');

  setButtonLoading(btn, label, loader, true);

  try {
    /* 1 — Create DB session (non-fatal if backend not ready) */
    try {
      const sRes = await fetch('/api/interview/start', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ session_type: cfg.type, subjects: cfg.subjects }),
      });
      if (sRes.ok) {
        const sData = await sRes.json();
        dbSessionId = sData.session_id ?? null;
      }
    } catch (_) { /* DB not wired yet — fine */ }

    /* 2 — Generate questions */
    const res = await fetch('/api/interview/generate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        subjects:   cfg.subjects,
        difficulty: cfg.difficulty,
        count:      cfg.count,
        type:       cfg.type,
      }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    if (!data.questions?.length) throw new Error('No questions returned');

    questions    = data.questions;
    currentIndex = 0;
    scores       = [];

    showScreen('screenInterview');
    buildProgressSteps();
    loadQuestion();
    startTimer();

  } catch (err) {
    alert('Could not start interview: ' + err.message + '\n\nMake sure the Flask backend is running and your GROQ_API_KEY is set in .env');
    setButtonLoading(btn, label, loader, false);
  }
}

/* ============================================================
   LOAD QUESTION
   ============================================================ */

function loadQuestion() {
  const q = questions[currentIndex];
  if (!q) return;

  /* Progress */
  updateProgressSteps();
  document.getElementById('progressLabel').textContent =
    `Question ${currentIndex + 1} of ${questions.length}`;

  /* Meta */
  const sub = (q.subject || 'dsa').toLowerCase();
  const tagEl = document.getElementById('qTag');
  tagEl.textContent = sub.toUpperCase();
  tagEl.className   = `iv-q-tag tag-${sub}`;

  const diffEl = document.getElementById('qDiff');
  diffEl.textContent = capitalise(cfg.difficulty);
  diffEl.className   = `iv-q-diff ${cfg.difficulty}`;

  document.getElementById('qNum').textContent  = `Q${currentIndex + 1}`;
  document.getElementById('qText').textContent = q.question;

  /* Reset answer */
  const ta = document.getElementById('answerInput');
  ta.value    = '';
  ta.disabled = false;
  ta.focus();

  /* Reset submit button */
  const submitBtn = document.getElementById('submitBtn');
  setButtonLoading(submitBtn, document.getElementById('submitBtnLabel'),
                   document.getElementById('submitBtnLoader'), false);
  submitBtn.disabled = false;

  /* Hide feedback */
  document.getElementById('feedbackCard').style.display = 'none';

  /* Next button label */
  document.getElementById('nextBtnLabel').textContent =
    currentIndex === questions.length - 1 ? 'See Results →' : 'Next Question →';

  /* Scroll to top of question */
  document.getElementById('qCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ============================================================
   SUBMIT ANSWER
   ============================================================ */

async function submitAnswer() {
  const ta     = document.getElementById('answerInput');
  const answer = ta.value.trim();

  if (!answer) { ta.focus(); ta.classList.add('iv-shake'); setTimeout(() => ta.classList.remove('iv-shake'), 400); return; }

  const submitBtn   = document.getElementById('submitBtn');
  const submitLabel = document.getElementById('submitBtnLabel');
  const submitLoad  = document.getElementById('submitBtnLoader');

  setButtonLoading(submitBtn, submitLabel, submitLoad, true);
  ta.disabled = true;

  const q = questions[currentIndex];

  try {
    const res = await fetch('/api/interview/evaluate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        subject:    q.subject,
        question:   q.question,
        userAnswer: answer,
        difficulty: cfg.difficulty,
        sessionId:  dbSessionId,
      }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    const score = typeof data.score === 'number' ? data.score : 5;
    scores.push({
      subject:     q.subject,
      question:    q.question,
      userAnswer:  answer,
      score:       score,
      feedback:    data.feedback    || '',
      modelAnswer: data.model_answer || '',
    });

    showFeedback(score, data.feedback, data.model_answer);

  } catch (err) {
    /* Graceful degradation — record 5/10 and show error */
    scores.push({ subject: q.subject, question: q.question, userAnswer: answer, score: 5, feedback: '⚠️ Evaluation failed: ' + err.message, modelAnswer: '' });
    showFeedback(5, '⚠️ Could not evaluate your answer (' + err.message + '). Moving on.', '');
  } finally {
    setButtonLoading(submitBtn, submitLabel, submitLoad, false);
  }
}

/* ── Render feedback ── */
function showFeedback(score, feedback, modelAnswer) {
  const pill = document.getElementById('scorePill');
  const sc   = Math.round(score);
  pill.textContent = sc + '/10';
  pill.className   = 'iv-score-pill ' + (sc >= 7 ? 'high' : sc >= 4 ? 'mid' : 'low');

  const labels = { high: '🏆 Great answer!', mid: '👍 Decent — review the model answer', low: '📚 Needs improvement' };
  document.getElementById('feedbackScoreLabel').textContent =
    sc >= 7 ? labels.high : sc >= 4 ? labels.mid : labels.low;

  document.getElementById('feedbackBody').innerHTML    = renderMd(feedback     || '*No feedback available.*');
  document.getElementById('modelAnswerBody').innerHTML = renderMd(modelAnswer  || '*No model answer available.*');

  const card = document.getElementById('feedbackCard');
  card.style.display = 'flex';
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/* ============================================================
   NEXT QUESTION / FINISH
   ============================================================ */

function nextQuestion() {
  if (currentIndex < questions.length - 1) {
    currentIndex++;
    loadQuestion();
  } else {
    finishInterview();
  }
}

async function finishInterview() {
  stopTimer();

  /* Save to DB (non-fatal) */
  try {
    await fetch('/api/interview/complete', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        // Changed: send both key styles so the backend accepts this even if one route expects snake_case.
        session_id: dbSessionId,
        scores:    scores.map(s => s.score),
        sessionId: dbSessionId,
      }),
    });
  } catch (_) { /* DB not wired yet */ }

  showScreen('screenResults');
  renderResults();
}

/* ============================================================
   RESULTS
   ============================================================ */

function renderResults() {
  const total   = scores.reduce((s, q) => s + q.score, 0);
  const avg     = scores.length ? total / scores.length : 0;
  const avgRnd  = Math.round(avg * 10) / 10;

  /* Ring animation */
  document.getElementById('finalScore').textContent = avgRnd.toFixed(1);
  const circumference = 314.16;
  const offset = circumference - (avg / 10) * circumference;
  setTimeout(() => {
    document.getElementById('ringProg').style.strokeDashoffset = offset;
    /* Ring colour based on score */
    const colour = avg >= 7 ? '#4ade80' : avg >= 5 ? '#fbbf24' : '#f87171';
    document.getElementById('ringProg').style.stroke = colour;
  }, 200);

  /* Title */
  const titles = [
    [8,  '🏆 Excellent!',        'You\'re placement-ready. Brilliant performance!'],
    [6,  '👍 Good effort!',      'Almost there — review feedback and practise weak areas.'],
    [4,  '📚 Keep practising',   'You\'ve spotted key gaps. Focus on those topics and try again.'],
    [-1, '💪 Don\'t give up!',   'Everyone starts somewhere. Read the model answers carefully.'],
  ];
  const [, title, tagline] = titles.find(([min]) => avg >= min) || titles[3];
  document.getElementById('resultTitle').textContent   = title;
  document.getElementById('resultTagline').textContent = tagline;

  /* Meta */
  const elapsed = startTimestamp ? Math.round((Date.now() - startTimestamp) / 1000) : 0;
  const mm = String(Math.floor(elapsed / 60)).padStart(2,'0');
  const ss = String(elapsed % 60).padStart(2,'0');
  document.getElementById('scoreMeta').textContent =
    `${scores.length} question${scores.length !== 1 ? 's' : ''} · ${mm}:${ss}`;

  /* Breakdown */
  const list = document.getElementById('breakdownList');
  list.innerHTML = '';
  scores.forEach((s, i) => {
    const sc  = Math.round(s.score);
    const cls = sc >= 7 ? 'high' : sc >= 4 ? 'mid' : 'low';
    const item = document.createElement('div');
    item.className = 'iv-bd-item';
    item.style.animationDelay = (i * 0.07) + 's';
    item.innerHTML = `
      <div class="iv-bd-score ${cls}">${sc}</div>
      <div class="iv-bd-info">
        <div class="iv-bd-q">${escHtml(s.question)}</div>
        <div class="iv-bd-meta">${(s.subject||'').toUpperCase()} · ${capitalise(cfg.difficulty)}</div>
      </div>`;
    list.appendChild(item);
  });

  /* Subject performance */
  const subMap = {};
  scores.forEach(s => {
    const k = (s.subject || 'dsa').toLowerCase();
    if (!subMap[k]) subMap[k] = { total: 0, n: 0 };
    subMap[k].total += s.score;
    subMap[k].n++;
  });

  const colours = { dsa:'#60a5fa', dbms:'#a78bfa', os:'#f472b6', cn:'#2dd4bf' };
  const icons   = { dsa:'🧩', dbms:'🗄️', os:'💻', cn:'🌐' };
  const perfEl  = document.getElementById('subjectPerf');
  perfEl.innerHTML = '';
  Object.entries(subMap).forEach(([sub, val]) => {
    const avg  = val.total / val.n;
    const pct  = (avg / 10) * 100;
    const col  = colours[sub] || 'var(--accent)';
    const item = document.createElement('div');
    item.className = 'iv-sp-item';
    item.innerHTML = `
      <div class="iv-sp-row">
        <div class="iv-sp-name">${icons[sub] || ''} ${sub.toUpperCase()}</div>
        <div class="iv-sp-val">${avg.toFixed(1)}/10 · ${val.n} Q${val.n !== 1 ? 's' : ''}</div>
      </div>
      <div class="iv-sp-track">
        <div class="iv-sp-fill" style="width:0%;background:${col}" data-target="${pct}"></div>
      </div>`;
    perfEl.appendChild(item);
  });
  setTimeout(() => {
    document.querySelectorAll('.iv-sp-fill').forEach(el => {
      el.style.width = el.dataset.target + '%';
    });
  }, 400);
}

/* ============================================================
   RETRY
   ============================================================ */

function retryInterview() {
  stopTimer();
  timerSecs = 0;
  document.getElementById('timerDisplay').textContent = '00:00';
  document.getElementById('ivTimer').style.display    = 'none';
  showScreen('screenSetup');
  /* Re-enable start button */
  const btn = document.getElementById('startBtn');
  btn.disabled = false;
  document.getElementById('startBtnLabel').style.display = 'inline';
  document.getElementById('startBtnLoader').style.display = 'none';
}

/* ============================================================
   TIMER
   ============================================================ */

function startTimer() {
  startTimestamp = Date.now();
  timerSecs      = 0;
  document.getElementById('ivTimer').style.display = 'flex';
  timerHandle = setInterval(() => {
    timerSecs++;
    const m = String(Math.floor(timerSecs / 60)).padStart(2, '0');
    const s = String(timerSecs % 60).padStart(2, '0');
    document.getElementById('timerDisplay').textContent = `${m}:${s}`;
  }, 1000);
}

function stopTimer() {
  clearInterval(timerHandle);
  timerHandle = null;
}

/* ============================================================
   PROGRESS STEPS (dot-rail)
   ============================================================ */

function buildProgressSteps() {
  const wrap = document.getElementById('progressSteps');
  wrap.innerHTML = '';
  questions.forEach((_, i) => {
    const step = document.createElement('div');
    step.className = 'iv-progress-step' + (i === 0 ? ' current' : '');
    step.id = `step-${i}`;
    wrap.appendChild(step);
  });
}

function updateProgressSteps() {
  questions.forEach((_, i) => {
    const el = document.getElementById(`step-${i}`);
    if (!el) return;
    el.className = 'iv-progress-step ' +
      (i < currentIndex ? 'done' : i === currentIndex ? 'current' : '');
  });
}

/* ============================================================
   SCREEN SWITCHER
   ============================================================ */

function showScreen(id) {
  ['screenSetup','screenInterview','screenResults'].forEach(screenId => {
    const el = document.getElementById(screenId);
    if (!el) return;
    el.style.display = screenId === id ? 'block' : 'none';
  });
}

/* ============================================================
   MARKDOWN RENDERER (minimal — handles bold, italic, code, pre, lists)
   ============================================================ */

function renderMd(text) {
  if (!text) return '';
  let html = String(text)
    /* fenced code blocks */
    .replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
      `<pre><code class="lang-${lang||'text'}">${escHtml(code.trim())}</code></pre>`)
    /* inline code */
    .replace(/`([^`\n]+)`/g, (_, c) => `<code>${escHtml(c)}</code>`)
    /* bold */
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    /* italic */
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    /* headings */
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm,  '<h3>$1</h3>')
    /* lists */
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    /* paragraphs */
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');

  /* wrap consecutive <li> in <ul> */
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, m => `<ul>${m}</ul>`);
  return `<p>${html}</p>`;
}

/* ============================================================
   UTILITIES
   ============================================================ */

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function capitalise(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : '';
}

function setButtonLoading(btn, labelEl, loaderEl, loading) {
  btn.disabled            = loading;
  labelEl.style.display   = loading ? 'none'   : 'inline';
  loaderEl.style.display  = loading ? 'inline-flex' : 'none';
}

/* Shake animation for empty answer */
const style = document.createElement('style');
style.textContent = `
  @keyframes ivShake {
    0%,100%{transform:translateX(0)}
    20%{transform:translateX(-6px)}
    40%{transform:translateX(6px)}
    60%{transform:translateX(-4px)}
    80%{transform:translateX(4px)}
  }
  .iv-shake { animation: ivShake 0.35s ease; border-color: #f87171 !important; }
`;
document.head.appendChild(style);
