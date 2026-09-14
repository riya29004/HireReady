/* ============================================================
   HireReady - progress.js
   Location: static/js/progress.js
   Renders the progress report using /api/progress
   ============================================================ */

'use strict';

let currentDays = 7;
let showAllDoubtsState = false;
let latestProgressData = null;

document.addEventListener('DOMContentLoaded', () => {
  // Changed: hide Recent Doubts and Subject Coverage sections from the progress page as requested.
  const doubtLog = document.getElementById('doubtLogList');
  if (doubtLog) {
    const card = doubtLog.closest('.section-card');
    if (card) card.style.display = 'none';
  }
  const coverageGrid = document.getElementById('coverageGrid');
  if (coverageGrid) {
    const card = coverageGrid.closest('.section-card');
    if (card) card.style.display = 'none';
  }

  loadProgress(currentDays);
});

function setRange(btn, days) {
  document.querySelectorAll('.range-tab').forEach(tab => tab.classList.remove('active'));
  btn.classList.add('active');
  currentDays = days;
  loadProgress(days);
}

function toggleAllDoubts() {
  showAllDoubtsState = !showAllDoubtsState;
  renderRecentDoubts(latestProgressData?.recent_doubts || []);
}

async function loadProgress(days) {
  try {
    const res = await fetch(`/api/progress?days=${days}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    if (data.error) throw new Error(data.error);

    latestProgressData = data;
    renderProgress(data, days);
  } catch (err) {
    renderLoadError(err.message);
  }
}

function renderProgress(data, days) {
  renderStats(data, days);
  renderHeatmap(data.activity || [], days);
  renderSubjectBars(data.subject_doubts || {});
  renderScoreHistory(data.score_history || []);
  renderGapList(data.gap_topics || []);
  renderRecentDoubts(data.recent_doubts || []);
  renderCoverage(data.coverage || {});
  renderStrengthPie(data.strength_rows || []);
  renderDifficultyBars(data.strength_rows || [], data.subject_doubts || {});
  renderStrengthTable(data.strength_rows || []);
}

function renderStats(data, days) {
  document.getElementById('statTotalDoubts').textContent = data.total_doubts ?? 0;
  document.getElementById('statInterviews').textContent = data.interviews_done ?? 0;
  document.getElementById('statStreak').textContent = data.streak ?? 0;

  const estimatedMinutes = (data.total_doubts || 0) * 10;
  document.getElementById('statStudyTime').textContent = formatMinutes(estimatedMinutes);
  document.getElementById('statStudyTimeSub').textContent =
    `${Math.max(1, Math.round(estimatedMinutes / Math.max(days, 1)))} min avg per day`;

  document.getElementById('statAvgScore').textContent =
    `Avg score: ${Number(data.avg_score || 0).toFixed(1)}`;
  document.getElementById('statStreakSub').textContent =
    (data.streak || 0) > 0 ? `You're on a ${data.streak}-day run` : 'Start a fresh streak today';
  document.getElementById('statDoubtsChange').textContent = `Last ${days} days`;
}

function renderHeatmap(activity, days) {
  const wrap = document.getElementById('heatmapWrap');
  wrap.innerHTML = '';
  document.getElementById('heatmapRange').textContent = `Last ${days} days`;

  const maxCount = Math.max(1, ...activity.map(item => Number(item.count || 0)));

  activity.forEach(item => {
    const col = document.createElement('div');
    col.className = 'hm-col';

    const day = document.createElement('div');
    day.className = 'hm-day';
    day.title = `${item.date}: ${item.count || 0} activity`;
    day.dataset.level = String(getHeatLevel(Number(item.count || 0), maxCount));

    const label = document.createElement('div');
    label.className = 'sh-bar-label';
    label.textContent = shortDate(item.date);

    col.appendChild(day);
    col.appendChild(label);
    wrap.appendChild(col);
  });
}

function renderSubjectBars(subjectCounts) {
  const root = document.getElementById('subjectBars');
  root.innerHTML = '';

  const meta = {
    dsa:  { label: 'DSA', icon: '🧩', cls: 'sb-dsa' },
    dbms: { label: 'DBMS', icon: '🗄️', cls: 'sb-dbms' },
    os:   { label: 'OS', icon: '💻', cls: 'sb-os' },
    cn:   { label: 'CN', icon: '🌐', cls: 'sb-cn' },
  };

  const maxCount = Math.max(1, ...Object.values(subjectCounts).map(v => Number(v || 0)));

  Object.entries(meta).forEach(([key, cfg]) => {
    const count = Number(subjectCounts[key] || 0);
    const item = document.createElement('div');
    item.className = 'sb-item';
    item.innerHTML = `
      <div class="sb-header">
        <div class="sb-label"><span class="sb-icon">${cfg.icon}</span>${cfg.label}</div>
        <div class="sb-count">${count} doubt${count === 1 ? '' : 's'}</div>
      </div>
      <div class="sb-track">
        <div class="sb-fill ${cfg.cls}" style="width:0%"></div>
      </div>
    `;
    root.appendChild(item);

    setTimeout(() => {
      const fill = item.querySelector('.sb-fill');
      if (fill) fill.style.width = `${(count / maxCount) * 100}%`;
    }, 50);
  });
}

function renderScoreHistory(history) {
  const chart = document.getElementById('scoreHistoryChart');
  const list = document.getElementById('scoreHistoryList');
  chart.innerHTML = '';
  list.innerHTML = '';

  if (!history.length) {
    list.innerHTML = '<div class="topics-empty">No interview history yet.</div>';
    return;
  }

  history.forEach((item, index) => {
    const score = Number(item.score || 0);
    const wrap = document.createElement('div');
    wrap.className = 'sh-bar-wrap';
    wrap.innerHTML = `
      <div class="sh-bar" style="height:0%" title="${score.toFixed(1)}/10"></div>
      <div class="sh-bar-label">${shortDate(item.date || '')}</div>
    `;
    chart.appendChild(wrap);

    setTimeout(() => {
      const bar = wrap.querySelector('.sh-bar');
      if (bar) bar.style.height = `${Math.max(8, score * 10)}%`;
    }, 80 + index * 40);

    const cls = score >= 7 ? 'hi' : score >= 4 ? 'mid' : 'lo';
    const row = document.createElement('div');
    row.className = 'sh-row';
    row.innerHTML = `
      <div class="sh-score ${cls}">${score.toFixed(1)}</div>
      <div class="sh-subjects">${escHtml(item.subjects || 'Interview')}</div>
      <div class="sh-date">${escHtml(item.date || '')}</div>
    `;
    list.appendChild(row);
  });
}

function renderGapList(gaps) {
  const root = document.getElementById('gapList');
  root.innerHTML = '';

  if (!gaps.length) {
    root.innerHTML = '<div class="topics-empty">No weak topics detected yet.</div>';
    return;
  }

  gaps.forEach((gap, index) => {
    const severity = gap.severity || 'low';
    const width = Math.max(6, Number(gap.pct || 0));
    const interviewCount = Number(gap.interview_count || 0);
    const doubtCount = Number(gap.doubt_count || 0);
    const evidenceLabel = interviewCount > 0
      ? `${interviewCount} interview${interviewCount === 1 ? '' : 's'}`
      : `${doubtCount} doubt${doubtCount === 1 ? '' : 's'}`;
    const item = document.createElement('div');
    item.className = 'gap-item';
    item.innerHTML = `
      <div class="gap-item-top">
        <div class="gap-topic">${escHtml(gap.name || 'Topic')}</div>
        <div class="gap-severity sev-${severity}">${escHtml(severity)}</div>
      </div>
      <div class="gap-meta">
        <span class="gap-tag">${escHtml((gap.subject || '').toUpperCase())}</span>
        <span>Score ${Number(gap.score || 0).toFixed(1)}</span>
        ${interviewCount > 0 ? `<span>Avg interview ${Number(gap.avg_interview_score || 0).toFixed(1)}/10</span>` : ''}
      </div>
      <div class="gap-bar-row">
        <div class="gap-bar-track">
          <div class="gap-bar-fill fill-${severity}" style="width:0%"></div>
        </div>
        <div class="gap-count">${evidenceLabel}</div>
      </div>
    `;
    root.appendChild(item);

    setTimeout(() => {
      const fill = item.querySelector('.gap-bar-fill');
      if (fill) fill.style.width = `${width}%`;
    }, 80 + index * 40);
  });
}

function renderRecentDoubts(doubts) {
  const root = document.getElementById('doubtLogList');
  const toggle = document.getElementById('showAllDoubts');
  if (!root || !toggle) return;
  root.innerHTML = '';

  if (!doubts.length) {
    root.innerHTML = '<div class="topics-empty">No recent doubts yet.</div>';
    toggle.textContent = 'Show all';
    return;
  }

  doubts.forEach((item, index) => {
    const row = document.createElement('div');
    row.className = 'dl-item';
    if (!showAllDoubtsState && index >= 5) row.classList.add('hidden');
    row.innerHTML = `
      <div class="dl-tag">${escHtml(item.subject || '')}</div>
      <div class="dl-text">${escHtml(item.question || '')}</div>
      <div class="dl-time">${escHtml(item.time_ago || '')}</div>
    `;
    root.appendChild(row);
  });

  toggle.textContent = showAllDoubtsState ? 'Show less' : 'Show all';
}

function renderCoverage(coverage) {
  const root = document.getElementById('coverageGrid');
  if (!root) return;
  root.innerHTML = '';

  const meta = {
    dsa: '🧩',
    dbms: '🗄️',
    os: '💻',
    cn: '🌐',
  };

  Object.entries(meta).forEach(([subject, icon]) => {
    const item = coverage[subject] || { pct: 0, label: 'No data yet' };
    const card = document.createElement('div');
    card.className = 'cov-item';
    card.innerHTML = `
      <div class="cov-header">
        <div class="cov-icon">${icon}</div>
        <div class="cov-name">${subject.toUpperCase()}</div>
        <div class="cov-pct">${Number(item.pct || 0)}%</div>
      </div>
      <div class="cov-bar-track">
        <div class="cov-bar-fill" style="width:0%;background:var(--accent)"></div>
      </div>
      <div class="cov-sub">${escHtml(item.label || 'No data yet')}</div>
    `;
    root.appendChild(card);

    setTimeout(() => {
      const fill = card.querySelector('.cov-bar-fill');
      if (fill) fill.style.width = `${Number(item.pct || 0)}%`;
    }, 80);
  });
}

function renderStrengthTable(rows) {
  const root = document.getElementById('strengthTableWrap');
  if (!root) return;

  if (!rows.length) {
    root.innerHTML = '<div class="strength-empty">No subject strength data yet. Ask doubts or complete mock interviews to build this table.</div>';
    return;
  }

  root.innerHTML = `
    <div class="strength-table-wrap">
      <table class="strength-table">
        <thead>
          <tr>
            <th>Subject</th>
            <th>Topic</th>
            <th>Recent Doubts</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map(row => `
            <tr>
              <td>${escHtml(row.subject || '')}</td>
              <td>${escHtml(row.topic || '')}</td>
              <td class="mono">${Number(row.recent_doubts || 0)}</td>
              <td>${renderStrengthBadge(row.status || 'Learning')}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function renderStrengthBadge(status) {
  const normalized = String(status || '').toLowerCase().replace(/\s+/g, '-');
  return `<span class="strength-badge strength-${normalized}">${escHtml(status)}</span>`;
}

function renderStrengthPie(rows) {
  const root = document.getElementById('strengthPieWrap');
  if (!root) return;

  if (!rows.length) {
    root.innerHTML = '<div class="strength-empty">No strength distribution data yet.</div>';
    return;
  }

  const counts = {
    Strong: 0,
    Learning: 0,
    Weak: 0,
    'Very Weak': 0,
  };
  rows.forEach(row => {
    const status = row.status || 'Learning';
    if (counts[status] !== undefined) counts[status] += 1;
  });

  const total = Object.values(counts).reduce((sum, value) => sum + value, 0) || 1;
  const circumference = 2 * Math.PI * 42;
  const segments = [
    { key: 'Strong', cls: 'seg-strong' },
    { key: 'Learning', cls: 'seg-learning' },
    { key: 'Weak', cls: 'seg-weak' },
    { key: 'Very Weak', cls: 'seg-very-weak' },
  ];

  let offset = 0;
  const circles = segments.map(segment => {
    const pct = counts[segment.key] / total;
    const dash = pct * circumference;
    const circle = `
      <circle
        class="strength-pie-segment ${segment.cls}"
        cx="60" cy="60" r="42"
        stroke-dasharray="${dash} ${circumference - dash}"
        stroke-dashoffset="${-offset}"
      ></circle>
    `;
    offset += dash;
    return circle;
  }).join('');

  root.innerHTML = `
    <div class="strength-pie-wrap">
      <div style="position:relative;">
        <svg class="strength-pie-svg" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
          <circle class="strength-pie-bg" cx="60" cy="60" r="42"></circle>
          ${circles}
        </svg>
        <div class="strength-pie-center" style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;">
          <div class="big">${total}</div>
          <div class="sub">Tracked Topics</div>
        </div>
      </div>
      <div class="strength-pie-legend">
        ${segments.map(segment => {
          const percent = Math.round((counts[segment.key] / total) * 100);
          const legendClass = `dot-${segment.key.toLowerCase().replace(/\s+/g, '-')}`;
          return `
            <div class="pie-legend-item">
              <span class="pie-legend-dot ${legendClass}"></span>
              <span>${segment.key} ${percent}%</span>
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `;
}

function renderDifficultyBars(rows, subjectDoubts) {
  const root = document.getElementById('difficultyBarWrap');
  if (!root) return;

  const subjects = [
    { key: 'DSA', label: 'DSA' },
    { key: 'DBMS', label: 'DBMS' },
    { key: 'OS', label: 'OS' },
    { key: 'CN', label: 'Networks' },
  ];

  const severityWeights = {
    Strong: 15,
    Learning: 35,
    Weak: 60,
    'Very Weak': 80,
  };

  const difficultyMap = {};
  subjects.forEach(subject => {
    const subjectRows = rows.filter(row => String(row.subject || '').toUpperCase() === subject.key);
    const avgStatusScore = subjectRows.length
      ? subjectRows.reduce((sum, row) => sum + (severityWeights[row.status] ?? 35), 0) / subjectRows.length
      : 20;

    const doubtBoost = Math.min(20, Number(subjectDoubts[String(subject.key).toLowerCase()] || 0) * 3);
    difficultyMap[subject.key] = Math.min(100, Math.round(avgStatusScore + doubtBoost));
  });

  const maxValue = Math.max(1, ...Object.values(difficultyMap));

  root.innerHTML = `
    <div class="difficulty-chart">
      <div class="difficulty-bars">
        ${subjects.map(subject => {
          const value = difficultyMap[subject.key] || 0;
          const height = Math.max(12, (value / maxValue) * 220);
          return `
            <div class="difficulty-col">
              <div class="difficulty-value">${value}</div>
              <div class="difficulty-bar" style="height:${height}px"></div>
              <div class="difficulty-label">${subject.label}</div>
            </div>
          `;
        }).join('')}
      </div>
      <div class="difficulty-legend">
        <span class="difficulty-legend-swatch"></span>
        <span>Difficulty Score</span>
      </div>
    </div>
  `;
}

function renderLoadError(message) {
  document.getElementById('statTotalDoubts').textContent = '—';
  document.getElementById('statInterviews').textContent = '—';
  document.getElementById('statStreak').textContent = '—';
  document.getElementById('statStudyTime').textContent = '—';
  document.getElementById('statDoubtsChange').textContent = `Could not load: ${message}`;
  document.getElementById('heatmapWrap').innerHTML = '<div class="topics-empty">Could not load progress data.</div>';
  document.getElementById('subjectBars').innerHTML = '';
  document.getElementById('scoreHistoryList').innerHTML = '';
  document.getElementById('gapList').innerHTML = '';
  const doubtLogList = document.getElementById('doubtLogList');
  if (doubtLogList) doubtLogList.innerHTML = '';
  const coverageGrid = document.getElementById('coverageGrid');
  if (coverageGrid) coverageGrid.innerHTML = '';
  const strengthPieWrap = document.getElementById('strengthPieWrap');
  if (strengthPieWrap) strengthPieWrap.innerHTML = '';
  const difficultyBarWrap = document.getElementById('difficultyBarWrap');
  if (difficultyBarWrap) difficultyBarWrap.innerHTML = '';
  const strengthTableWrap = document.getElementById('strengthTableWrap');
  if (strengthTableWrap) strengthTableWrap.innerHTML = '';
}

function getHeatLevel(count, maxCount) {
  if (count <= 0) return 0;
  const ratio = count / maxCount;
  if (ratio < 0.25) return 1;
  if (ratio < 0.5) return 2;
  if (ratio < 0.75) return 3;
  return 4;
}

function formatMinutes(minutes) {
  const mins = Number(minutes || 0);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  const rem = mins % 60;
  return rem ? `${hours}h ${rem}m` : `${hours}h`;
}

function shortDate(value) {
  return String(value || '').slice(0, 6);
}

function escHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
