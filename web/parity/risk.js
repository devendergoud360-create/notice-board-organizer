/**
 * Notice Risk & Priority Score (NRPS) - JavaScript parity implementation.
 * MUST remain byte-for-byte semantically identical to risk.py.
 * Used by the cross-language parity check in CI.
 */

const FNV_OFFSET = 2166136261;
const FNV_PRIME = 16777619;
const MASK32 = 0xFFFFFFFF;

const WEIGHT_URGENCY = 0.45;
const WEIGHT_STALENESS = 0.20;
const WEIGHT_CATEGORY = 0.20;
const WEIGHT_HISTORY = 0.15;

function clamp01(value) {
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

function fnv1a32(text) {
  let h = FNV_OFFSET;
  const bytes = Buffer.from(text.toLowerCase(), 'utf-8');
  for (const byte of bytes) {
    h = Math.imul(h, FNV_PRIME) >>> 0;
    h = (h ^ byte) >>> 0;
    h = h & MASK32;
  }
  return h >>> 0;
}

function roundHalfUp(value, places = 6) {
  const factor = Math.pow(10, places);
  // Emulate ROUND_HALF_UP for positive values (score is in [0,1]).
  return Math.floor(value * factor + 0.5) / factor;
}

function daysBetween(a, b) {
  // Both are 'YYYY-MM-DD' strings; compute whole-day difference a - b in UTC.
  const [ay, am, ad] = a.split('-').map(Number);
  const [by, bm, bd] = b.split('-').map(Number);
  const da = Date.UTC(ay, am - 1, ad);
  const db = Date.UTC(by, bm - 1, bd);
  return Math.round((da - db) / 86400000);
}

function urgencyComponent(expiry, today) {
  const days = daysBetween(expiry, today);
  if (days < 0) return 1;
  return clamp01(1 - days / 30);
}

function stalenessComponent(posted, today) {
  return clamp01(daysBetween(today, posted) / 90);
}

function categoryComponent(category) {
  return (fnv1a32(category) % 1000) / 1000;
}

function historyComponent(notice, records, today) {
  const cat = notice.category.toLowerCase();
  const prior = records.filter(
    (r) => r.id < notice.id && r.category.toLowerCase() === cat
  );
  if (prior.length === 0) return 0.5;
  let bad = 0;
  for (const r of prior) {
    const days = daysBetween(r.expiry_date, today);
    if (days < 0 || r.status === 'Expired') bad += 1;
  }
  const ratio = bad / prior.length;
  return 0.5 + 0.5 * ratio;
}

function computeRisk(notice, records, today) {
  const urgency = urgencyComponent(notice.expiry_date, today);
  const staleness = stalenessComponent(notice.date_posted, today);
  const catw = categoryComponent(notice.category);
  const hist = historyComponent(notice, records, today);
  const score =
    WEIGHT_URGENCY * urgency +
    WEIGHT_STALENESS * staleness +
    WEIGHT_CATEGORY * catw +
    WEIGHT_HISTORY * hist;
  return roundHalfUp(clamp01(score), 6);
}

function riskBreakdown(notice, records, today) {
  return {
    notice_id: notice.id,
    urgency: roundHalfUp(urgencyComponent(notice.expiry_date, today), 6),
    staleness: roundHalfUp(stalenessComponent(notice.date_posted, today), 6),
    category_weight: roundHalfUp(categoryComponent(notice.category), 6),
    history_factor: roundHalfUp(historyComponent(notice, records, today), 6),
    risk_score: computeRisk(notice, records, today),
  };
}

module.exports = {
  clamp01, fnv1a32, roundHalfUp,
  urgencyComponent, stalenessComponent, categoryComponent, historyComponent,
  computeRisk, riskBreakdown,
};

if (require.main === module) {
  // Read fixture from stdin: { "today": "...", "records": [...] }
  let input = '';
  process.stdin.setEncoding('utf-8');
  process.stdin.on('data', (chunk) => { input += chunk; });
  process.stdin.on('end', () => {
    const fixture = JSON.parse(input);
    const results = fixture.records.map((n) => ({
      id: n.id,
      score: computeRisk(n, fixture.records, fixture.today),
    }));
    console.log(JSON.stringify(results));
  });
}
