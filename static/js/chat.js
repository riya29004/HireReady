// /* ============================================================
//    HireReady — chat.js
//    Location: static/js/chat.js
//    Depends on: CHAT_CONFIG (defined inline per page)
//    ============================================================ */

// /* ── State ── */
// let conversationHistory = [];   // [{role, content}] — full history sent to API
// let questionCount  = 0;
// let sessionStart   = Date.now();
// let isWaiting      = false;
// let sessionTimer   = null;
// let topicsTracked  = new Set();

// /* ── DOM refs (resolved after DOMContentLoaded) ── */
// let chatMessages, typingIndicator, userInput,
//     sendBtn, topicsList, questionCountEl, sessionTimeEl;


// /* ============================================================
//    INIT
//    ============================================================ */
// document.addEventListener('DOMContentLoaded', () => {

//   chatMessages    = document.getElementById('chatMessages');
//   typingIndicator = document.getElementById('typingIndicator');
//   userInput       = document.getElementById('userInput');
//   sendBtn         = document.getElementById('sendBtn');
//   topicsList      = document.getElementById('topicsList');
//   questionCountEl = document.getElementById('questionCount');
//   sessionTimeEl   = document.getElementById('sessionTime');

//   // Stamp welcome message time
//   const welcomeTime = document.getElementById('welcomeTime');
//   if (welcomeTime) welcomeTime.textContent = now();

//   // Session timer — update every minute
//   sessionTimer = setInterval(updateSessionTime, 60_000);
// });


// /* ============================================================
//    SEND MESSAGE
//    ============================================================ */
// async function sendMessage() {
//   if (isWaiting) return;

//   const text = userInput.value.trim();
//   if (!text) return;

//   // Append user bubble
//   appendUserMessage(text);
//   userInput.value = '';
//   autoResize(userInput);

//   // Update history
//   conversationHistory.push({ role: 'user', content: text });
//   questionCount++;
//   if (questionCountEl) questionCountEl.textContent = questionCount;

//   // Show typing
//   setWaiting(true);

//   try {
//     const res = await fetch(CHAT_CONFIG.apiEndpoint, {
//       method:  'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify({
//         subject: CHAT_CONFIG.subject,
//         history: conversationHistory
//       })
//     });

//     if (!res.ok) throw new Error(`HTTP ${res.status}`);
//     const data = await res.json();

//     const reply = data.reply || 'Sorry, I could not generate a response. Please try again.';
//     conversationHistory.push({ role: 'assistant', content: reply });

//     appendAgentMessage(reply);
//     extractTopics(text);       // tag topics from user's question

//   } catch (err) {
//     appendAgentMessage(
//       `⚠️ I'm having trouble connecting right now. Please check your network and try again.\n\n*Error: ${err.message}*`
//     );
//   } finally {
//     setWaiting(false);
//   }
// }


// /* ============================================================
//    RENDER HELPERS
//    ============================================================ */

// function appendUserMessage(text) {
//   const row = document.createElement('div');
//   row.className = 'msg-row msg-user';
//   row.innerHTML = `
//     <div class="msg-bubble user-bubble">
//       <div class="msg-content"><p>${escHtml(text)}</p></div>
//     </div>
//     <div class="msg-avatar user-msg-avatar">${getUserInitial()}</div>
//   `;
//   chatMessages.appendChild(row);
//   scrollToBottom();
// }

// function appendAgentMessage(text) {
//   const row = document.createElement('div');
//   row.className = 'msg-row msg-agent';
//   row.innerHTML = `
//     <div class="msg-avatar agent-avatar ${CHAT_CONFIG.subject}-avatar">${CHAT_CONFIG.agentAvatar}</div>
//     <div class="msg-bubble agent-bubble">
//       <div class="msg-header">
//         <span class="msg-sender">${CHAT_CONFIG.agentName}</span>
//         <span class="msg-time">${now()}</span>
//       </div>
//       <div class="msg-content">${renderMarkdown(text)}</div>
//     </div>
//   `;
//   chatMessages.appendChild(row);
//   scrollToBottom();
// }

// /* Minimal markdown renderer — handles bold, italic, code, pre, lists */
// function renderMarkdown(text) {
//   // Escape HTML first on raw text
//   let html = text
//     // code blocks (``` ... ```)
//     .replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
//       `<pre><code class="lang-${lang || 'text'}">${escHtml(code.trim())}</code></pre>`)
//     // inline code
//     .replace(/`([^`]+)`/g, (_, c) => `<code>${escHtml(c)}</code>`)
//     // bold
//     .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
//     // italic
//     .replace(/\*(.+?)\*/g, '<em>$1</em>')
//     // headers (## and ###)
//     .replace(/^### (.+)$/gm, '<h4 style="margin:10px 0 4px;font-size:0.88rem;">$1</h4>')
//     .replace(/^## (.+)$/gm,  '<h3 style="margin:12px 0 6px;font-size:0.95rem;">$1</h3>')
//     // unordered list items
//     .replace(/^[-*] (.+)$/gm, '<li style="margin:3px 0;padding-left:4px;">$1</li>')
//     // numbered list
//     .replace(/^\d+\. (.+)$/gm, '<li style="margin:3px 0;padding-left:4px;">$1</li>')
//     // line breaks
//     .replace(/\n\n/g, '</p><p style="margin-top:8px;">')
//     .replace(/\n/g, '<br>');

//   // Wrap loose <li> in <ul>
//   html = html.replace(/(<li[\s\S]*?<\/li>)/g, m => {
//     if (!m.startsWith('<ul>')) return `<ul style="margin:6px 0 6px 16px;padding:0;">${m}</ul>`;
//     return m;
//   });

//   return `<p>${html}</p>`;
// }

// /* HTML escape */
// function escHtml(str) {
//   return str
//     .replace(/&/g, '&amp;')
//     .replace(/</g, '&lt;')
//     .replace(/>/g, '&gt;')
//     .replace(/"/g, '&quot;');
// }


// /* ============================================================
//    TYPING STATE
//    ============================================================ */
// function setWaiting(state) {
//   isWaiting = state;
//   if (sendBtn) sendBtn.disabled = state;
//   if (typingIndicator) typingIndicator.classList.toggle('show', state);
//   scrollToBottom();
// }


// /* ============================================================
//    CLEAR CHAT
//    ============================================================ */
// function clearChat() {
//   if (!confirm('Clear this conversation?')) return;
//   conversationHistory = [];
//   questionCount  = 0;
//   topicsTracked  = new Set();
//   sessionStart   = Date.now();
//   if (questionCountEl) questionCountEl.textContent = '0';
//   if (sessionTimeEl)   sessionTimeEl.textContent   = '0m';
//   if (topicsList) topicsList.innerHTML = '<div class="topics-empty">Topics you ask about will appear here.</div>';

//   // Remove all messages except the first welcome one
//   const allRows = chatMessages.querySelectorAll('.msg-row');
//   allRows.forEach((row, i) => { if (i > 0) row.remove(); });
// }


// /* ============================================================
//    QUICK PROMPTS
//    ============================================================ */
// function quickPrompt(btn) {
//   if (isWaiting) return;
//   userInput.value = btn.textContent.trim();
//   autoResize(userInput);
//   sendMessage();
// }


// /* ============================================================
//    TOPICS TRACKER
//    ── Lightweight keyword extraction from user questions
//    ============================================================ */
// const TOPIC_KEYWORDS = {
//   dsa: ['array','linked list','stack','queue','tree','graph','heap','hash','sort','search',
//         'dynamic programming','dp','recursion','backtracking','greedy','complexity','big o',
//         'binary search','bfs','dfs','trie','segment tree','sliding window','two pointer',
//         'dijkstra','bellman','floyd','topological','mst','kruskal','prim'],
//   dbms:['sql','join','query','normalisation','normalization','acid','transaction','index',
//         'indexing','schema','primary key','foreign key','er diagram','relation','view',
//         '1nf','2nf','3nf','bcnf','deadlock','lock','isolation','commit','rollback','trigger',
//         'stored procedure','nosql','mongodb'],
//   os:  ['process','thread','deadlock','semaphore','mutex','scheduling','paging','segmentation',
//         'virtual memory','cache','inode','file system','interrupt','system call','context switch',
//         'pcb','round robin','fcfs','sjf','priority','thrashing','page fault','memory'],
//   cn:  ['tcp','udp','ip','http','https','dns','osi','model','layer','routing','protocol',
//         'subnet','handshake','socket','port','firewall','ssl','tls','packet','frame','arp',
//         'icmp','bandwidth','latency','congestion','flow control']
// };

// function extractTopics(userText) {
//   const lower = userText.toLowerCase();
//   const keywords = TOPIC_KEYWORDS[CHAT_CONFIG.subject] || [];
//   keywords.forEach(kw => {
//     if (lower.includes(kw) && !topicsTracked.has(kw)) {
//       topicsTracked.add(kw);
//       addTopicTag(kw);
//     }
//   });
// }

// function addTopicTag(topic) {
//   const empty = topicsList.querySelector('.topics-empty');
//   if (empty) empty.remove();

//   const tag = document.createElement('div');
//   tag.className = 'topic-tag';
//   tag.innerHTML = `<span>📌</span> ${capitalise(topic)}`;
//   topicsList.appendChild(tag);
// }


// /* ============================================================
//    UTILITIES
//    ============================================================ */

// function scrollToBottom() {
//   requestAnimationFrame(() => {
//     chatMessages.scrollTop = chatMessages.scrollHeight;
//   });
// }

// function now() {
//   return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
// }

// function updateSessionTime() {
//   if (!sessionTimeEl) return;
//   const mins = Math.floor((Date.now() - sessionStart) / 60_000);
//   sessionTimeEl.textContent = mins < 60 ? `${mins}m` : `${Math.floor(mins/60)}h ${mins%60}m`;
// }

// function getUserInitial() {
//   const name = document.querySelector('.user-name')?.textContent?.trim();
//   return (name || 'U')[0].toUpperCase();
// }

// function capitalise(str) {
//   return str.charAt(0).toUpperCase() + str.slice(1);
// }

// /* Auto-resize textarea */
// function autoResize(el) {
//   el.style.height = 'auto';
//   el.style.height = Math.min(el.scrollHeight, 160) + 'px';
// }

// /* Enter to send, Shift+Enter for newline */
// function handleKey(e) {
//   if (e.key === 'Enter' && !e.shiftKey) {
//     e.preventDefault();
//     sendMessage();
//   }
// }


/* ============================================================
   HireReady — chat.js
   Location: static/js/chat.js

   IMPORTANT: Each subject HTML page must define CHAT_CONFIG
   before this script loads. Example for dsa.html:

   <script>
     const CHAT_CONFIG = {
       subject:      'dsa',
       agentName:    'DSA Agent',
       agentAvatar:  '🧩',
       apiEndpoint:  '/api/chat',
     };
   </script>
   <script src="/static/js/chat.js"></script>
   ============================================================ */

/* ── State ── */
let conversationHistory = [];
let questionCount  = 0;
let sessionStart   = Date.now();
let isWaiting      = false;
let sessionTimer   = null;
let topicsTracked  = new Set();

/* ── DOM refs ── */
let chatMessages, typingIndicator, userInput,
    sendBtn, topicsList, questionCountEl, sessionTimeEl;


/* ============================================================
   INIT
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {

  chatMessages    = document.getElementById('chatMessages');
  typingIndicator = document.getElementById('typingIndicator');
  userInput       = document.getElementById('userInput');
  sendBtn         = document.getElementById('sendBtn');
  topicsList      = document.getElementById('topicsList');
  questionCountEl = document.getElementById('questionCount');
  sessionTimeEl   = document.getElementById('sessionTime');

  const welcomeTime = document.getElementById('welcomeTime');
  if (welcomeTime) welcomeTime.textContent = now();

  sessionTimer = setInterval(updateSessionTime, 60_000);
});


/* ============================================================
   SEND MESSAGE
   ============================================================ */
async function sendMessage() {
  if (isWaiting) return;

  const text = userInput.value.trim();
  if (!text) return;

  appendUserMessage(text);
  userInput.value = '';
  autoResize(userInput);

  conversationHistory.push({ role: 'user', content: text });
  questionCount++;
  if (questionCountEl) questionCountEl.textContent = questionCount;

  setWaiting(true);

  try {
    const res = await fetch(CHAT_CONFIG.apiEndpoint, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        subject: CHAT_CONFIG.subject,
        history: conversationHistory
      })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const reply = data.reply || 'Sorry, I could not generate a response. Please try again.';
    conversationHistory.push({ role: 'assistant', content: reply });

    appendAgentMessage(reply);
    extractTopics(text);

  } catch (err) {
    appendAgentMessage(
      `⚠️ I'm having trouble connecting right now. Please check your network and try again.\n\n*Error: ${err.message}*`
    );
  } finally {
    setWaiting(false);
  }
}


/* ============================================================
   RENDER HELPERS
   ============================================================ */

function appendUserMessage(text) {
  const row = document.createElement('div');
  row.className = 'msg-row msg-user';
  row.innerHTML = `
    <div class="msg-bubble user-bubble">
      <div class="msg-content"><p>${escHtml(text)}</p></div>
    </div>
    <div class="msg-avatar user-msg-avatar">${getUserInitial()}</div>
  `;
  chatMessages.appendChild(row);
  scrollToBottom();
}

function appendAgentMessage(text) {
  const row = document.createElement('div');
  row.className = 'msg-row msg-agent';
  row.innerHTML = `
    <div class="msg-avatar agent-avatar ${CHAT_CONFIG.subject}-avatar">${CHAT_CONFIG.agentAvatar}</div>
    <div class="msg-bubble agent-bubble">
      <div class="msg-header">
        <span class="msg-sender">${CHAT_CONFIG.agentName}</span>
        <span class="msg-time">${now()}</span>
      </div>
      <div class="msg-content">${renderMarkdown(text)}</div>
    </div>
  `;
  chatMessages.appendChild(row);
  scrollToBottom();
}

function renderMarkdown(text) {
  let html = text
    .replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
      `<pre><code class="lang-${lang || 'text'}">${escHtml(code.trim())}</code></pre>`)
    .replace(/`([^`]+)`/g,     (_, c) => `<code>${escHtml(c)}</code>`)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,     '<em>$1</em>')
    .replace(/^### (.+)$/gm,   '<h4 style="margin:10px 0 4px;font-size:0.88rem;">$1</h4>')
    .replace(/^## (.+)$/gm,    '<h3 style="margin:12px 0 6px;font-size:0.95rem;">$1</h3>')
    .replace(/^[-*] (.+)$/gm,  '<li style="margin:3px 0;padding-left:4px;">$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li style="margin:3px 0;padding-left:4px;">$1</li>')
    .replace(/\n\n/g, '</p><p style="margin-top:8px;">')
    .replace(/\n/g,   '<br>');

  html = html.replace(/(<li[\s\S]*?<\/li>)/g, m => {
    if (!m.startsWith('<ul>')) return `<ul style="margin:6px 0 6px 16px;padding:0;">${m}</ul>`;
    return m;
  });

  return `<p>${html}</p>`;
}

function escHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}


/* ============================================================
   TYPING STATE
   ============================================================ */
function setWaiting(state) {
  isWaiting = state;
  if (sendBtn) sendBtn.disabled = state;
  if (typingIndicator) typingIndicator.classList.toggle('show', state);
  scrollToBottom();
}


/* ============================================================
   CLEAR CHAT
   ============================================================ */
function clearChat() {
  if (!confirm('Clear this conversation?')) return;
  conversationHistory = [];
  questionCount  = 0;
  topicsTracked  = new Set();
  sessionStart   = Date.now();
  if (questionCountEl) questionCountEl.textContent = '0';
  if (sessionTimeEl)   sessionTimeEl.textContent   = '0m';
  if (topicsList) topicsList.innerHTML = '<div class="topics-empty">Topics you ask about will appear here.</div>';

  const allRows = chatMessages.querySelectorAll('.msg-row');
  allRows.forEach((row, i) => { if (i > 0) row.remove(); });
}


/* ============================================================
   QUICK PROMPTS
   ============================================================ */
function quickPrompt(btn) {
  if (isWaiting) return;
  userInput.value = btn.textContent.trim();
  autoResize(userInput);
  sendMessage();
}


/* ============================================================
   TOPICS TRACKER
   ============================================================ */
const TOPIC_KEYWORDS = {
  dsa:  ['array','linked list','stack','queue','tree','graph','heap','hash','sort','search',
         'dynamic programming','dp','recursion','backtracking','greedy','complexity','big o',
         'binary search','bfs','dfs','trie','segment tree','sliding window','two pointer',
         'dijkstra','bellman','floyd','topological','mst','kruskal','prim'],
  dbms: ['sql','join','query','normalisation','normalization','acid','transaction','index',
         'indexing','schema','primary key','foreign key','er diagram','relation','view',
         '1nf','2nf','3nf','bcnf','deadlock','lock','isolation','commit','rollback','trigger',
         'stored procedure','nosql','mongodb'],
  os:   ['process','thread','deadlock','semaphore','mutex','scheduling','paging','segmentation',
         'virtual memory','cache','inode','file system','interrupt','system call','context switch',
         'pcb','round robin','fcfs','sjf','priority','thrashing','page fault','memory'],
  cn:   ['tcp','udp','ip','http','https','dns','osi','model','layer','routing','protocol',
         'subnet','handshake','socket','port','firewall','ssl','tls','packet','frame','arp',
         'icmp','bandwidth','latency','congestion','flow control'],
};

function extractTopics(userText) {
  const lower    = userText.toLowerCase();
  const keywords = TOPIC_KEYWORDS[CHAT_CONFIG.subject] || [];
  keywords.forEach(kw => {
    if (lower.includes(kw) && !topicsTracked.has(kw)) {
      topicsTracked.add(kw);
      addTopicTag(kw);
    }
  });
}

function addTopicTag(topic) {
  const empty = topicsList.querySelector('.topics-empty');
  if (empty) empty.remove();

  const tag = document.createElement('div');
  tag.className = 'topic-tag';
  tag.innerHTML = `<span>📌</span> ${capitalise(topic)}`;
  topicsList.appendChild(tag);
}


/* ============================================================
   UTILITIES
   ============================================================ */

function scrollToBottom() {
  requestAnimationFrame(() => {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  });
}

function now() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function updateSessionTime() {
  if (!sessionTimeEl) return;
  const mins = Math.floor((Date.now() - sessionStart) / 60_000);
  sessionTimeEl.textContent = mins < 60 ? `${mins}m` : `${Math.floor(mins/60)}h ${mins%60}m`;
}

function getUserInitial() {
  const name = document.querySelector('.user-name')?.textContent?.trim();
  return (name || 'U')[0].toUpperCase();
}

function capitalise(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}