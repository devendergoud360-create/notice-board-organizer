# Notice Board Organizer

**LocalImpact Challenge — Project #30 (Campus & Administration)**

A four-layer Python application (CLI + loopback-only HTTP API + browser UI) to store,
validate, search, summarise, and export campus notices — with a novel risk-scoring
algorithm, three interchangeable storage backends, structured event logging, and
web-grade security. Built with the Python standard library only (no runtime deps).

---

## 1. Setup

```bash
# Python 3.10+ ; Node 20+ (Node only for browser QA / parity check)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

python seed_data.py             # generate 40 realistic records (CSV + JSON)
```

No third-party Python packages are required to **run** the app. Test/deliverable
generation needs `python-docx` and `python-pptx`; browser QA needs `playwright`.

## 2. Run

```bash
# Terminal CLI
python main.py                            # JSON storage (default)
python main.py --backend csv              # CSV storage Strategy
python main.py --backend sqlite --log data/events.jsonl

# HTTP API + browser UI (loopback only)
python -m web.server --port 8765
# open http://127.0.0.1:8765

# Optional bearer token
set API_BEARER_TOKEN=secret123 && python -m web.server
```

### CLI flags
| Flag | Meaning |
|------|---------|
| `--backend {json,csv,sqlite}` | Select storage Strategy |
| `--log PATH` | Append structured JSON events to a JSONL file sink |

## 3. Test

```bash
python -m unittest discover -s tests -p 'test_*.py' -v   # 30 tests
python scripts/parity_check.py                           # Python↔JS NRPS parity
node tests/browser_qa.js                                 # Playwright QA (needs npm install)
python -m compileall -q .                                # compile check
```

CI (`.github/workflows/ci.yml`) runs compile check, all 30 tests, parity validation,
Playwright QA, and Office-deliverable validation on every push and PR.

## 4. Architecture

Four layers, documented in `docs/SRS.md`:

| Layer | Contents |
|-------|----------|
| Presentation | `main.py` (CLI), `presentation/` (console input wrappers + report/export presenters), `web/server.py` (HTTP API), `web/static/` (browser UI), `api/index.py` (Vercel edge) |
| Application | `application/facade.py` (use cases), `commands.py` (Command registry), `events.py` (Observer bus + structured JSON logging) |
| Domain | `domain/entities.py`, `domain/services.py`, `domain/validation/` (pure validators), `risk.py` — pure, no I/O |
| Persistence | `persistence/` — Strategy interface + registry with JSON, CSV, SQLite backends |

Design patterns: **Strategy** (interchangeable, registered backends), **Command** (actions as objects in a registry), **Observer** (event bus with console + file subscribers).

## 5. Storage formats

- `data/notices.json` — JSON array of notice objects (default)
- `data/notices.csv` — CSV with header `id,title,category,date_posted,expiry_date,status,author,description`
- `data/notices.db` — SQLite `notices` table
- `data/sample_notices.{json,csv}` — 40 seeded records (normal, boundary, overdue)
- Exports: Markdown, plain-text audit log, CSV (`data/notice_report.*`)

Atomic writes (temp file + `os.replace`) and corrupt-file backup/recovery are built in.

## 6. Novel algorithm — Notice Risk & Priority Score (NRPS)

Deterministic, dependency-free, bounded `[0,1]`, rounded to 6 decimals; full formula
in `docs/SRS.md` §12 and parity implementation in `web/parity/risk.js`.

```
urgency         = clamp01(1 - days_until_expiry/30)     # overdue => 1
staleness       = clamp01(days_since_posted/90)
category_weight = (FNV1a_32(lowercase_category) mod 1000)/1000
history_factor  = 0.5 + 0.5*(prior expired-or-overdue same-category / prior same-category)
score           = clamp01(0.45*u + 0.20*s + 0.20*c + 0.15*h)
```

Cross-language parity is verified in CI across 40 records.

## 7. Security

- Loopback-only bind (`127.0.0.1`)
- Origin checks on state-changing requests
- Double-submit CSRF: HttpOnly session cookie + readable CSRF cookie echoed in `X-CSRF-Token`
- Optional bearer token (`API_BEARER_TOKEN`)
- Static-file whitelist (path traversal blocked)
- 64 KiB request body limit
- Strict Content-Security-Policy and security headers
- HTML escaping of all user text in the browser UI
- Structured JSON event logging (stderr + optional file sink); no operational `print()` in domain/persistence

## 8. Live URLs & repository

- Repository: `https://github.com/CHERRY-TEC/notice-board-organizer`
- Live demo (stable alias): `https://notice-board-organizer.vercel.app` — HTTP 200
- Direct production deployment: `https://notice-board-organizer-grwdp4i1s-cherry-ff88.vercel.app`
- CI: GitHub Actions runs on every push/PR (green on `main`)
- API reference: `docs/API_REFERENCE.md`
- SRS: `docs/SRS.md`

Deployment note: the Vercel deployment is a deliberate target with its own data
layer (per-instance `/tmp` JSON store seeded from `data/sample_notices.json`), reusing
the same domain/application layers. Redeploy with `vercel --prod --yes`. The GitHub
Actions CI is push-triggered and green; Vercel Git auto-deploy connection was not
available in this environment (CLI Git connect requires additional GitHub App
permissions), so production deploys are performed explicitly with the CLI.

## 9. Two-minute demo script

1. `python seed_data.py` then `python main.py` → press **9** to load 40 sample records.
2. Press **1**, enter an invalid category (e.g. `bogus`) → watch validation loop until valid; then add a real notice.
3. Press **6** → summary + threshold warnings; note overdue and expiring-soon flags.
4. Press **7** → export a Markdown report to `data/`.
5. Close and relaunch `python main.py` → records survive restart (persistence proof).
6. Run `python -m web.server` and open the URL → click **Risk Ranking** to show the novel score; `node tests/browser_qa.js` shows zero console errors.

## 10. Deliverables

- `docs/SRS.md`, `docs/API_REFERENCE.md`
- `docs/NoticeBoardOrganizer_Presentation.pptx` (14 slides)
- `docs/NoticeBoardOrganizer_Documentation.docx` (17 sections)
- `.github/workflows/ci.yml`, clean source ZIP
