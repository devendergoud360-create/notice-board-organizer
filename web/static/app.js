'use strict';
// Browser client. All user text is HTML-escaped before insertion.
let csrf = '';

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

function table(rows, cols) {
  if (!rows.length) return '<p>No records.</p>';
  const head = cols.map(c => `<th>${esc(c)}</th>`).join('');
  const body = rows.map(r => '<tr>' + cols.map(c => `<td>${esc(r[c])}</td>`).join('') + '</tr>').join('');
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

async function refresh() {
  const data = await api('/api/notices');
  document.getElementById('panel').innerHTML =
    `<h2>Notices (${data.notices.length})</h2>` +
    table(data.notices, ['id','title','category','expiry_date','status']);
}

async function summary() {
  const s = await api('/api/summary');
  document.getElementById('panel').innerHTML = '<h2>Summary</h2><table><tbody>' +
    Object.entries(s).map(([k,v]) =>
      `<tr><th>${esc(k)}</th><td>${esc(typeof v === 'object' ? JSON.stringify(v) : v)}</td></tr>`
    ).join('') + '</tbody></table>';
}

async function warnings() {
  const d = await api('/api/warnings');
  document.getElementById('panel').innerHTML = '<h2>Warnings</h2>' +
    (d.warnings.length ? d.warnings.map(w =>
      `<p class="warn">#${esc(w.id)} ${esc(w.title)}: ${esc(w.message)}</p>`).join('')
      : '<p>No warnings.</p>');
}

async function rank() {
  const d = await api('/api/rank');
  document.getElementById('panel').innerHTML = '<h2>Risk Ranking</h2>' +
    table(d.ranked.map(r => ({id:r.id, title:r.title, risk_score:r.risk_score.toFixed(6)})),
          ['id','title','risk_score']);
}

document.addEventListener('DOMContentLoaded', async () => {
  await ensureCsrf();
  document.getElementById('btn-refresh').onclick = refresh;
  document.getElementById('btn-summary').onclick = summary;
  document.getElementById('btn-warnings').onclick = warnings;
  document.getElementById('btn-rank').onclick = rank;
  document.getElementById('add-form').hidden = false;
  document.getElementById('add-form').onsubmit = async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const body = Object.fromEntries(f.entries());
    try {
      await api('/api/notices', { method:'POST', body:JSON.stringify(body) });
      e.target.reset();
      await refresh();
    } catch (err) { alert('Save failed: ' + err.message); }
  };
  await refresh();
});
