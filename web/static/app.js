'use strict';
// Browser client. All user text is HTML-escaped before insertion.
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
  toast._t = setTimeout(() => { el.hidden = true; }, 2800);
}

function daysInfo(n) {
  const d = n.days_remaining;
  const cls = d < 0 ? 'days-neg' : (d <= 3 ? 'days-low' : '');
  const label = d < 0 ? `${Math.abs(d)}d overdue` : (d === 0 ? 'Today' : `${d}d left`);
  return `<span class="${cls}">${label}</span>`;
}

function renderStats(s, warnCount) {
  const cards = [
    { label: 'Total notices', value: s.total, ico: '▤', cls: '' },
    { label: 'Active', value: s.active, ico: '●', cls: 'green' },
    { label: 'Upcoming', value: s.upcoming, ico: '◷', cls: '' },
    { label: 'Expired', value: s.expired, ico: '✕', cls: 'red' },
    { label: 'Warnings', value: warnCount, ico: '⚠', cls: 'amber' },
  ];
  document.getElementById('stats').innerHTML = cards.map(c => `
    <div class="stat ${c.cls}">
      <div class="stat-label">${esc(c.label)}</div>
      <div class="stat-value">${esc(c.value)}</div>
      <div class="stat-ico">${c.ico}</div>
    </div>`).join('');
}

function setActive(view) {
  document.querySelectorAll('.nav-item').forEach(b =>
    b.classList.toggle('active', b.dataset.view === view));
  const titles = {
    notices: ['All Notices', 'Browse, search and manage every notice in one place.'],
    summary: ['Executive Summary', 'A snapshot of totals, status breakdown and key trends.'],
    warnings: ['Threshold Warnings', 'Notices that are overdue or expiring soon.'],
    rank: ['Risk Ranking', 'Notices ordered by the Notice Risk & Priority Score.'],
  };
  const t = titles[view] || titles.notices;
  document.getElementById('page-title').textContent = t[0];
  document.getElementById('page-sub').textContent = t[1];
}

function renderTable(rows, cols) {
  if (!rows.length) {
    return '<div class="empty"><div class="empty-ico">▤</div><p>No records to display.</p></div>';
  }
  // cols: array of { key, label }.
  const normalized = cols.map(c => typeof c === 'string' ? { key: c, label: c } : c);
  const head = normalized.map(c => `<th>${esc(c.label)}</th>`).join('');
  const body = rows.map(r => `<tr>${normalized.map(c => `<td>${r[c.key] == null ? '' : r[c.key]}</td>`).join('')}</tr>`).join('');
  return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

async function refresh() {
  setActive('notices');
  const data = await api('/api/notices');
  noticesCache = data.notices;
  const sum = await api('/api/summary');
  const warns = await api('/api/warnings');
  renderStats(sum, warns.warnings.length);
  renderWarnBadge(warns.warnings.length);

  const kw = document.getElementById('search').value.trim().toLowerCase();
  const rows = noticesCache.filter(n =>
    !kw || `${n.title} ${n.description} ${n.author}`.toLowerCase().includes(kw));
  document.getElementById('panel').innerHTML =
    `<h2>Notices <span class="count-label">(${rows.length})</span></h2>` +
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
  const s = await api('/api/summary');
  const warns = await api('/api/warnings');
  renderStats(s, warns.warnings.length);
  renderWarnBadge(warns.warnings.length);
  const cats = Object.entries(s.category_counts || {});
  document.getElementById('panel').innerHTML = `<h2>Summary</h2>
    <div class="kv">
      ${[['Total notices', s.total], ['Active', s.active], ['Upcoming', s.upcoming],
         ['Expired', s.expired], ['Overdue', s.overdue], ['Expiring ≤ 7 days', s.expiring_soon],
         ['Avg days remaining', s.avg_days_remaining]]
        .map(([k, v]) => `<div class="kv-item"><div class="kv-key">${esc(k)}</div><div class="kv-val">${esc(v)}</div></div>`).join('')}
    </div>
    <h2 class="section-title">By category</h2>
    ${cats.length ? renderTable(cats.map(([k, v]) => ({ category: esc(k), count: v })), [{ key: 'category', label: 'Category' }, { key: 'count', label: 'Count' }]) : '<p class="muted">No data.</p>'}`;
}

async function warningsView() {
  setActive('warnings');
  const d = await api('/api/warnings');
  renderWarnBadge(d.warnings.length);
  document.getElementById('panel').innerHTML = '<h2>Warnings</h2>' +
    (d.warnings.length ? d.warnings.map(w => `
      <div class="warn-row ${w.message.includes('OVERDUE') ? 'overdue' : ''}">
        <div class="warn-title">#${esc(w.id)} — ${esc(w.title)}</div>
        <div class="warn-msg">${esc(w.message)}</div>
      </div>`).join('') : '<div class="empty"><div class="empty-ico">✓</div><p>No threshold warnings. Everything is on track.</p></div>');
}

async function rankView() {
  setActive('rank');
  const d = await api('/api/rank');
  document.getElementById('panel').innerHTML = '<h2>Risk Ranking</h2>' +
    renderTable(d.ranked.map(r => {
      const pct = Math.round(r.risk_score * 100);
      return {
        id: `<span class="muted">#${r.id}</span>`,
        title: esc(r.title),
        score: `<div class="risk-bar"><div class="risk-track"><div class="risk-fill risk-${pct >= 70 ? 'high' : (pct >= 40 ? 'mid' : 'low')} w-${Math.round(pct / 5) * 5}"></div></div><strong>${r.risk_score.toFixed(6)}</strong></div>`,
      };
    }), [{ key: 'id', label: 'ID' }, { key: 'title', label: 'Title' }, { key: 'score', label: 'Risk score' }]);
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
  document.getElementById('modal').onclick = e => {
    if (e.target.id === 'modal') closeModal();
  };
  document.getElementById('btn-theme').onclick = () => {
    document.body.classList.toggle('light');
  };
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
      toast('Notice added successfully');
      await refresh();
    } catch (err) { toast('Save failed: ' + err.message, true); }
  };

  await refresh();
});
