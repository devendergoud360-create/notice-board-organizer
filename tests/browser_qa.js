/**
 * Playwright browser QA: loads the live UI, exercises every button, adds a
 * notice via the form, and asserts ZERO console errors / page errors.
 * Run: node tests/browser_qa.js
 */
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..');
const PORT = 8791;
const BASE = `http://127.0.0.1:${PORT}`;

(async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'nbo-qa-'));
  const store = path.join(tmp, 'qa.json');
  // Seed with sample records so the table genuinely renders on first load.
  const seed = require(path.join(ROOT, 'data', 'sample_notices.json'));
  fs.writeFileSync(store, JSON.stringify(seed, null, 2));
  const PY = process.env.PYTHON || 'python';
  const server = spawn(PY, [
    '-m', 'web.server', '--port', String(PORT), '--backend', 'json', '--path', store,
  ], { cwd: ROOT, env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1' } });
  let serverLog = '';
  server.stdout.on('data', (d) => { serverLog += d.toString(); });
  server.stderr.on('data', (d) => { serverLog += d.toString(); });

  // Poll the health endpoint until the server is ready (avoids stdout buffering).
  await new Promise(async (resolve, reject) => {
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline) {
      try {
        const r = await fetch(`${BASE}/api/health`);
        if (r.ok) { resolve(); return; }
      } catch (_) { /* not ready */ }
      await new Promise((r) => setTimeout(r, 200));
    }
    reject(new Error('server did not start. log:\n' + serverLog));
  });

  const browser = await chromium.launch();
  const page = await browser.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', (err) => pageErrors.push(err.message));

  let failures = 0;
  function check(name, condition) {
    if (condition) console.log(`PASS  ${name}`);
    else { console.log(`FAIL  ${name}`); failures++; }
  }

  try {
    const response = await page.goto(BASE, { waitUntil: 'networkidle' });
    check('page returns HTTP 200', response.status() === 200);
    check('title rendered', (await page.title()).includes('NoticeBoard'));
    check('notices table rendered', await page.locator('table').count() >= 1);

    for (const [id, expected] of [
      ['btn-summary', 'Analytics'], ['btn-warnings', 'Threshold alerts'],
      ['btn-rank', 'Risk leaderboard'], ['btn-refresh', 'Notice directory'],
    ]) {
      await page.click('#' + id);
      await page.waitForTimeout(200);
      const text = await page.locator('#panel h2').first().innerText();
      check(`${id} shows ${expected}`, text.includes(expected));
    }

    // Add a notice through the modal form.
    await page.click('#btn-add');
    await page.waitForTimeout(150);
    check('add modal opens', await page.locator('#modal').isVisible());
    const today = new Date().toISOString().slice(0, 10);
    const expiry = new Date(Date.now() + 5 * 86400000).toISOString().slice(0, 10);
    await page.fill('input[name="title"]', 'Browser QA Notice');
    await page.selectOption('select[name="category"]', 'events');
    await page.fill('input[name="date_posted"]', today);
    await page.fill('input[name="expiry_date"]', expiry);
    await page.click('#add-form button[type="submit"]');
    await page.waitForTimeout(400);
    const body = await page.locator('#panel').innerText();
    check('new notice appears after submit', body.includes('Browser QA Notice'));

    check('zero console errors', consoleErrors.length === 0);
    check('zero page errors', pageErrors.length === 0);
    if (consoleErrors.length) console.log('  console:', consoleErrors);
    if (pageErrors.length) console.log('  page:', pageErrors);
  } finally {
    await browser.close();
    server.kill('SIGTERM');
    fs.rmSync(tmp, { recursive: true, force: true });
  }

  console.log(`\nBrowser QA: ${failures === 0 ? 'ALL CHECKS PASSED' : failures + ' FAILURE(S)'}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });
