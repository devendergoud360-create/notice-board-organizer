'use strict';
// NoticeBoard Command Center — browser client.
// All user text is HTML-escaped. No inline styles (strict CSP compliant).
let csrf = '';
let noticesCache = [];
let searchTimer = null;

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}

async function ensureCsrf() {
  await fetch('/api/csrf', { credentials: 'same-origin' });
  const m = document.cookie.match(/(?:^|;\s*)nbo_csrf=([^;]+)/);
  csrf = m ? decodeURIComponent(m[1]) : '';
}

async function api(path, options = {}) {
  options.credentials = 'same-origin';
  options.headers = Object.assign({}, options.headers || {});
  if (options.method && options.method !== 'GET') {
    options.headers['X-CSRF-Token'] = csrf;
    options.headers['Content-Type'] = 'application/json';
  }
  const r = await fetch(path, options);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

function toast(message, isError = false) {
  const el = document.getElementById('toast');
  el.textContent = message;
  el.className = 'toast' + (isError ? ' error' : '');
  el.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { el.hidden = true; }, 3000);
}

function daysInfo(n) {
  const d = n.days_remaining;
  const cls = d < 0 ? 'days-neg' : (d <= 3 ? 'days-low' : '');
  const label = d < 0 ? `${Math.abs(d)}d overdue` : (d === 0 ? 'Due today' : `${d}d left`);
  return `<span class="${cls}">${label}</span>`;
}

function renderStats(s, warnCount) {
  const cards = [
    { label: 'Total notices', value: s.total, ico: '▦', foot: 'Across all categories', cls: '' },
    { label: 'Active now', value: s.active, ico: '●', foot: 'Due today', cls: 'green' },
    { label: 'Upcoming', value: s.upcoming, ico: '◷', foot: 'Scheduled ahead', cls: 'violet' },
    { label: 'Expired', value: s.expired, ico: '✕', foot: 'Need attention', cls: 'red' },
    { label: 'Warnings', value: warnCount, ico: '⚡', foot: 'Overdue or due ≤ 3d', cls: 'amber' },
  ];
  document.getElementById('stats').innerHTML = cards.map(c => `
    <div class="stat ${c.cls}">
      <div class="stat-top"><span class="stat-label">${esc(c.label)}</span><span class="stat-ico">${c.ico}</span></div>
      <div class="stat-value">${esc(c.value)}</div>
      <div class="stat-foot">${esc(c.foot)}</div>
    </div>`).join('');
  document.getElementById('nav-count').textContent = s.total;
}

function renderMiniChart(s) {
  const cats = Object.values(s.category_counts || {});
  const max = Math.max(1, ...cats);
  document.getElementById('mini-chart').innerHTML =
    cats.slice(0, 12).map(v => `<i class="w-${Math.round(v / max * 100 / 5) * 5}"></i>`).join('');
  // height via CSS class (no inline styles): reuse width classes won't set height;
  // use a dedicated set of height classes instead.
  document.querySelectorAll('#mini-chart i').forEach((el, i) => {
    const v = cats[i] || 0;
    const pct = Math.round(v / max * 100 / 10) * 10;
    el.className = `h-${pct}`;
  });
}

function setActive(view) {
  document.querySelectorAll('.nav-item').forEach(b =>
    b.classList.toggle('active', b.dataset.view === view));
  const meta = {
    notices: ['OVERVIEW / NOTICES', 'All Notices', 'Every notice, beautifully organized and always in sync.'],
    summary: ['INSIGHTS / ANALYTICS', 'Analytics', 'A living picture of your notice board at a glance.'],
    warnings: ['ALERTS / WARNINGS', 'Warnings', 'The urgent things — surfaced before they become problems.'],
    rank: ['INTELLIGENCE / RISK RADAR', 'Risk Radar', 'Notices ranked by the Notice Risk & Priority Score.'],
  };
  const m = meta[view] || meta.notices;
  document.getElementById('page-eyebrow').textContent = m[0];
  document.getElementById('page-title').textContent = m[1];
  document.getElementById('page-sub').textContent = m[2];
}

function renderTable(rows, cols, start = 0) {
  if (!rows.length) {
    return '<div class="empty"><div class="empty-ico">✧</div><p>Nothing here yet — clean slate.</p></div>';
  }
  const head = cols.map(c => `<th>${esc(c.label)}</th>`).join('');
  const body = rows.map((r, i) => `<tr>${cols.map(c =>
    `<td>${r[c.key] == null ? '' : r[c.key]}</td>`).join('')}</tr>`).join('');
  return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

async function refresh() {
  setActive('notices');
  const data = await api('/api/notices');
  noticesCache = data.notices;
  const [sum, warns] = await Promise.all([api('/api/summary'), api('/api/warnings')]);
  renderStats(sum, warns.warnings.length);
  renderMiniChart(sum);
  renderWarnBadge(warns.warnings.length);

  const kw = document.getElementById('search').value.trim().toLowerCase();
  const rows = noticesCache.filter(n =>
    !kw || `${n.title} ${n.description} ${n.author}`.toLowerCase().includes(kw));
  document.getElementById('panel').innerHTML =
    `<div class="panel-head"><h2>Notice directory <span class="count-label">${rows.length} records</span></h2></div>` +
    renderTable(rows.map(n => ({
      id: `<span class="muted">#${n.id}</span>`,
      title: `<div class="title-cell">${esc(n.title)}<div class="sub-cell">by ${esc(n.author)}</div></div>`,
      category: `<span class="pill category">${esc(n.category)}</span>`,
      posted: esc(n.date_posted),
      expiry: esc(n.expiry_date),
      days: daysInfo(n),
      status: `<span class="pill ${n.status}">${esc(n.status)}</span>`,
    })), [
      { key: 'id', label: 'ID' }, { key: 'title', label: 'Title' },
      { key: 'category', label: 'Category' }, { key: 'posted', label: 'Posted' },
      { key: 'expiry', label: 'Expires' }, { key: 'days', label: 'Remaining' },
      { key: 'status', label: 'Status' },
    ]);
}

function renderWarnBadge(count) {
  const b = document.getElementById('warn-count');
  b.textContent = count;
  b.hidden = count === 0;
}

async function summaryView() {
  setActive('summary');
  const [s, warns] = await Promise.all([api('/api/summary'), api('/api/warnings')]);
  renderStats(s, warns.warnings.length);
  renderWarnBadge(warns.warnings.length);
  const cats = Object.entries(s.category_counts || {});
  const maxCat = Math.max(1, ...cats.map(([, v]) => v));

  document.getElementById('panel').innerHTML = `
    <div class="panel-head"><h2>Analytics overview</h2></div>
    <div class="analytics-grid">
      <div class="chart-card">
        <div class="chart-title">Status distribution</div>
        <div class="legend">
          ${[['Active', s.active, '#3ddc97'], ['Upcoming', s.upcoming, '#6c8cff'], ['Expired', s.expired, '#ff6b81']]
            .map(([k, v, c]) => `<div class="legend-row"><span class="legend-dot dot-${k.toLowerCase()}"></span><span>${k}</span><span class="legend-val">${v}</span></div>`).join('')}
        </div>
        <div class="kv">
          ${[['Total', s.total], ['Overdue', s.overdue], ['Expiring ≤ 7d', s.expiring_soon], ['Avg days left', s.avg_days_remaining]]
            .map(([k, v]) => `<div class="kv-item"><div class="kv-key">${k}</div><div class="kv-val">${v}</div></div>`).join('')}
        </div>
      </div>
      <div class="chart-card">
        <div class="chart-title">Notices by category</div>
        ${cats.map(([k, v]) => `
          <div class="bar-row">
            <div class="bar-label"><span>${esc(k)}</span><strong>${v}</strong></div>
            <div class="bar-track"><div class="bar-fill w-${Math.max(5, Math.round(v / maxCat * 100 / 5) * 5)}"></div></div>
          </div>`).join('')}
      </div>
    </div>`;
}

async function warningsView() {
  setActive('warnings');
  const d = await api('/api/warnings');
  renderWarnBadge(d.warnings.length);
  document.getElementById('panel').innerHTML =
    `<div class="panel-head"><h2>Threshold alerts <span class="count-label">${d.warnings.length} active</span></h2></div>` +
    (d.warnings.length ? d.warnings.map(w => {
      const overdue = w.message.includes('OVERDUE');
      return `<div class="warn-row ${overdue ? 'overdue' : ''}">
        <span class="warn-ico">${overdue ? '⛔' : '⏳'}</span>
        <div><div class="warn-title">${esc(w.title)} <span class="muted">#${esc(w.id)}</span></div>
        <div class="warn-msg">${esc(w.message)}</div></div>
        <span class="warn-tag">${overdue ? 'OVERDUE' : 'DUE SOON'}</span>
      </div>`;
    }).join('') : '<div class="empty"><div class="empty-ico">✓</div><p>All clear — no notices need attention.</p></div>');
}

async function rankView() {
  setActive('rank');
  const d = await api('/api/rank');
  const medals = ['🥇', '🥈', '🥉'];
  document.getElementById('panel').innerHTML =
    `<div class="panel-head"><h2>Risk leaderboard</h2></div>` +
    renderTable(d.ranked.map((r, i) => {
      const pct = Math.round(r.risk_score * 100);
      const lvl = pct >= 70 ? 'high' : (pct >= 40 ? 'mid' : 'low');
      return {
        rank: `<span class="rank-medal">${medals[i] || `#${i + 1}`}</span>`,
        title: esc(r.title),
        score: `<div class="risk-bar"><div class="risk-track"><div class="risk-fill risk-${lvl} w-${Math.round(pct / 5) * 5}"></div></div><span class="risk-score-val">${r.risk_score.toFixed(6)}</span></div>`,
      };
    }), [{ key: 'rank', label: '#' }, { key: 'title', label: 'Notice' }, { key: 'score', label: 'Risk score' }]);
}

function openModal() { document.getElementById('modal').hidden = false; }
function closeModal() { document.getElementById('modal').hidden = true; }

document.addEventListener('DOMContentLoaded', async () => {
  await ensureCsrf();
  document.getElementById('btn-refresh').onclick = refresh;
  document.getElementById('btn-summary').onclick = summaryView;
  document.getElementById('btn-warnings').onclick = warningsView;
  document.getElementById('btn-rank').onclick = rankView;
  document.getElementById('btn-add').onclick = openModal;
  document.getElementById('btn-close-modal').onclick = closeModal;
  document.getElementById('btn-cancel').onclick = closeModal;
  document.getElementById('modal').onclick = e => { if (e.target.id === 'modal') closeModal(); };
  document.getElementById('btn-theme').onclick = () => document.body.classList.toggle('light');
  document.getElementById('search').addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(refresh, 180);
  });

  const f = document.getElementById('add-form');
  f.date_posted.value = new Date().toISOString().slice(0, 10);
  f.expiry_date.value = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
  f.onsubmit = async e => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(f).entries());
    try {
      await api('/api/notices', { method: 'POST', body: JSON.stringify(body) });
      f.reset();
      closeModal();
      toast('Notice published — nice work!');
      await refresh();
    } catch (err) { toast('Could not publish: ' + err.message, true); }
  };
  await refresh();
});
