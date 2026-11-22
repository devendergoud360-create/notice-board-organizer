#!/usr/bin/env python3
"""Generate NoticeBoardOrganizer_Documentation.docx (17 sections).

Reproducible with only the Python standard library + python-docx.
Run:  python docs/make_docx.py
"""

from __future__ import annotations

import os

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
NAVY = RGBColor(0x0B, 0x1F, 0x3A)
TEAL = RGBColor(0x12, 0x8C, 0x7E)
GREY = RGBColor(0x55, 0x5F, 0x6B)
AMBER = RGBColor(0xB8, 0x7A, 0x10)

doc = Document()

# Page setup
for sec in doc.sections:
    sec.top_margin = Inches(0.9)
    sec.bottom_margin = Inches(0.9)
    sec.left_margin = Inches(1.0)
    sec.right_margin = Inches(1.0)

# Base styles
normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(11)
normal.font.color.rgb = RGBColor(0x22, 0x2A, 0x33)
normal.paragraph_format.space_after = Pt(6)

for lvl, size, color in [(1, 20, NAVY), (2, 15, TEAL), (3, 12, NAVY)]:
    st = doc.styles[f"Heading {lvl}"]
    st.font.name = "Calibri"
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = color
    st.paragraph_format.space_before = Pt(12)
    st.paragraph_format.space_after = Pt(6)


def set_cell_bg(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def add_table(headers, rows, widths=None, header_bg="0B1F3A"):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_bg(hdr[i], header_bg)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            r = p.add_run(str(val))
            r.font.size = Pt(9.5)
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return t


def bullet(text, lvl=0):
    p = doc.add_paragraph(style="List Bullet" if lvl == 0 else "List Bullet 2")
    p.add_run(text)
    return p


def para(text, bold=False, italic=False, color=None, size=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.bold = bold
    r.font.italic = italic
    if color:
        r.font.color.rgb = color
    if size:
        r.font.size = Pt(size)
    return p


def code(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.3)
    r = p.add_run(text)
    r.font.name = "Consolas"
    r.font.size = Pt(9)
    r.font.color.rgb = TEAL
    return p


def page_break():
    doc.add_page_break()


# ===========================================================================
# 1. Cover / Title
# ===========================================================================
for _ in range(3):
    doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("LOCALIMPACT CHALLENGE · PROJECT #30")
r.font.size = Pt(14); r.font.bold = True; r.font.color.rgb = TEAL
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Notice Board Organizer")
r.font.size = Pt(36); r.font.bold = True; r.font.color.rgb = NAVY
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Software Documentation & User Guide")
r.font.size = Pt(18); r.font.color.rgb = GREY
for _ in range(4):
    doc.add_paragraph()
for line in [
    "Version 1.0.0  ·  22 November 2026",
    "Python 3.10+ standard library · python-docx · python-pptx",
    "Four-layer architecture · Strategy / Command / Observer · Novel risk score",
]:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(line); r.font.size = Pt(11); r.font.color.rgb = GREY
page_break()


# ===========================================================================
# 2. Executive Summary
# ===========================================================================
doc.add_heading("2. Executive Summary", level=1)
para(
    "The Notice Board Organizer is a hybrid application that transforms a chaotic campus "
    "notice board into a validated, persistent, searchable record system. It faithfully "
    "implements the original problem brief — storing notices with category, posting date, "
    "and expiry date; enforcing strict validation; persisting to JSON and CSV; searching; "
    "summarising; and exporting to Markdown, plain text, and CSV — while adding the web API, "
    "security controls, design patterns, and a novel scoring algorithm demanded by the "
    "evaluation rubric."
)
para(
    "The system is built on a four-layer architecture (presentation, application, domain, "
    "persistence) with interchangeable storage backends behind a Strategy registry, a Command "
    "registry shared by the CLI and API, and an Observer event bus that writes a structured "
    "JSON audit trail. A deterministic Notice Risk & Priority Score ranks each notice in [0,1] "
    "using urgency, staleness, a hashed category weight, and a history-aware factor. Python and "
    "JavaScript implementations are guaranteed to agree to six decimal places."
)
para(
    "Key outcomes: zero third-party runtime dependencies, corruption-safe persistence, "
    "defence-in-depth HTTP security (loopback bind, CSRF double-submit, bearer token, strict "
    "CSP, static whitelist, body-size limit, HTML escaping), and a full testing story from "
    "unit tests through Playwright browser QA to cross-language parity checks."
)


# ===========================================================================
# 3. Problem Context
# ===========================================================================
doc.add_heading("3. Problem Context", level=1)
para(
    "Campus administrators publish many notices — exam schedules, maintenance windows, "
    "deadlines, events. Without a system, notices are posted on paper or ad-hoc documents, "
    "expiry dates are missed, and there is no way to answer simple questions: which notices "
    "are overdue, which expire this week, or what happened to last month's announcements?"
)
para("The original brief called for a beginner-friendly terminal application with:")
for b in [
    "Core logic to store notices with category, date, and expiry status;",
    "Defensive, strict validation of all inputs;",
    "Local persistence to JSON (and CSV) that survives restarts;",
    "Keyword and category search;",
    "An executive summary with totals and averages;",
    "Stretch goals: multi-format export, threshold warnings, bulk CSV import with error logs.",
]:
    bullet(b)
para(
    "The brief also contained contradictions: it demanded a standard-library-only solution "
    "yet mentioned Matplotlib for charts, and described a terminal application while the "
    "rubric expected a web API with security. Section 12 of the SRS documents how these were "
    "resolved with a hybrid design."
)


# ===========================================================================
# 4. Objectives
# ===========================================================================
doc.add_heading("4. Objectives", level=1)
add_table(
    ["#", "Objective", "Outcome"],
    [
        ["1", "Model notices with strict validation", "Notice dataclass + validators"],
        ["2", "Persist reliably across restarts", "Atomic JSON + CSV/SQLite backends"],
        ["3", "Search and summarise", "Keyword/category filter + analytics"],
        ["4", "Warn on overdue / expiring notices", "Threshold warnings"],
        ["5", "Export and import in multiple formats", "MD / TXT / CSV + row-level logs"],
        ["6", "Expose secure local HTTP API", "CSRF, bearer, CSP, origin checks"],
        ["7", "Add explainable deterministic scoring", "Risk score with parity"],
        ["8", "Apply proven design patterns", "Strategy / Command / Observer"],
        ["9", "Prove quality", "Unit, invariant, E2E, Playwright, parity"],
    ],
    widths=[0.5, 4.2, 2.3],
)


# ===========================================================================
# 5. Scope
# ===========================================================================
doc.add_heading("5. Scope", level=1)
para("In scope (core):", bold=True)
for b in [
    "Create, update, delete notices; recompute expiry status on every load;",
    "Strict validation of text, category, dates, and date ordering;",
    "JSON persistence (corruption-safe, atomic) and CSV load/export;",
    "Search by keyword and category; executive summary; threshold warnings.",
]:
    bullet(b)
para("In scope (stretch):", bold=True)
for b in [
    "Markdown / TXT / CSV export; bulk CSV import with row-level error logs;",
    "Optional browser UI; local HTTP API with layered security;",
    "Structured JSON event log; novel risk score with cross-language parity.",
]:
    bullet(b)
para("Out of scope:", bold=True)
for b in [
    "Multi-user accounts, remote network exposure, database servers, external services, "
    "third-party charting libraries (Matplotlib), and native mobile apps.",
]:
    bullet(b)


# ===========================================================================
# 6. Requirements
# ===========================================================================
doc.add_heading("6. Requirements", level=1)
doc.add_heading("6.1 Functional Requirements", level=2)
add_table(
    ["ID", "Requirement", "Brief Mapping"],
    [
        ["FR-1", "Create notice with category/dates/author/description", "Core store"],
        ["FR-2", "Monotonic ID = max+1", "Derived"],
        ["FR-3/4", "Update by id; delete by id", "Core CRUD"],
        ["FR-5", "Recompute status from expiry date vs today", "Expiry status"],
        ["FR-6..10", "Strict validation; re-prompt interactively; structured API errors", "Strict validation"],
        ["FR-11", "Row-level import validation with error logs", "Bulk import"],
        ["FR-12..16", "Atomic JSON, corruption tolerance, CSV field order, backend registry", "Persistence"],
        ["FR-17..19", "Search, summary, threshold warnings", "Search / summary"],
        ["FR-20..22", "MD/TXT/CSV export, import modes", "Multi-format export"],
        ["FR-23..27", "HTTP API, security, patterns, risk score, optional UI", "Rubric"],
    ],
    widths=[0.9, 4.0, 2.1],
)
doc.add_heading("6.2 Non-Functional Requirements", level=2)
add_table(
    ["Category", "Key Requirements"],
    [
        ["Reliability", "Corrupt/missing data tolerated; atomic writes; derived status; JSONL events"],
        ["Security", "Loopback bind; origin check; CSRF double-submit; constant-time bearer; whitelist; 1 MiB cap; strict CSP; HTML escaping"],
        ["Performance", "≤10k notices < 100 ms; O(n) scoring; atomic O(n) save"],
        ["Portability", "Python 3.10+; Windows/macOS/Linux; stdlib only; os.path.join; graceful ANSI"],
        ["Maintainability", "Four layers; pure domain functions; drop-in storage Strategies"],
        ["Determinism", "Byte-identical score and exports; same inputs → same output"],
        ["Usability", "2-minute demo; menu 1–9 + 0; actionable errors"],
        ["Testability", "Unit + invariant + E2E API + Playwright + parity"],
    ],
    widths=[1.7, 5.3],
)


# ===========================================================================
# 7. Architecture & Design
# ===========================================================================
doc.add_heading("7. Architecture & Design", level=1)
para(
    "The system uses four layers with inward-only dependencies. Presentation handles the CLI, "
    "browser UI, and HTTP serialization. Application orchestrates use cases through a Command "
    "registry, an event bus, security middleware, and a structured logger. Domain holds the "
    "Notice entity, pure functions, validators, and the scoring algorithm with no I/O. "
    "Persistence provides interchangeable storage Strategies."
)
add_table(
    ["Layer", "Responsibility", "Typical Modules"],
    [
        ["Presentation", "UI + request/response serialization", "main.py CLI, HTTP handler, optional UI"],
        ["Application", "Use-case dispatch, events, security, logging", "Command registry, event bus, middleware"],
        ["Domain", "Entity, logic, validation, scoring", "models.py, logic.py, validation.py, score module"],
        ["Persistence", "Storage backends", "storage.py registry + JSON/CSV/SQLite"],
    ],
    widths=[1.4, 3.2, 2.4],
)
para("Request flow:", bold=True)
code("Client → Security (origin/CSRF/token/size) → Command registry → Domain → Persistence → Event bus → JSON log → Response")
para(
    "Mermaid diagrams for the layer graph, Strategy class diagram, Command dispatch, Observer "
    "flow, and HTTP sequence are provided in docs/SRS.md §6."
)


# ===========================================================================
# 8. Design Patterns
# ===========================================================================
doc.add_heading("8. Design Patterns", level=1)
doc.add_heading("8.1 Strategy — Storage Registry", level=2)
para(
    "All storage backends implement a common load/save interface and are selected at runtime "
    "by a registry. Adding a new format is a single register() call; callers are unaffected."
)
doc.add_heading("8.2 Command — Action Registry", level=2)
para(
    "Mutations (add, update, delete, import, export) are encapsulated commands dispatched by "
    "a stable key. The CLI menu and API routes share this registry, so both interfaces execute "
    "identical logic with no duplication."
)
doc.add_heading("8.3 Observer — Event Bus", level=2)
para(
    "Domain events are broadcast to subscribers. The structured JSON logger writes one compact "
    "object per line to data/events.jsonl, producing an auditable trail. A warning evaluator and "
    "optional UI refresh can subscribe without coupling to domain code."
)


# ===========================================================================
# 9. Data Model & Storage
# ===========================================================================
doc.add_heading("9. Data Model & Storage", level=1)
add_table(
    ["Field", "Type", "Validation / Notes"],
    [
        ["id", "int", "> 0; assigned max+1; unique"],
        ["title", "str", "trim; 1–120 chars; no control chars"],
        ["category", "str", "lowercase; one of 7 allowed values"],
        ["date_posted", "date", "strict YYYY-MM-DD; P in score"],
        ["expiry_date", "date", "strict YYYY-MM-DD; ≥ posted; E in score"],
        ["status", "str", "Active / Expired / Upcoming; always recomputed"],
        ["author", "str", "trim; ≤120; default Admin"],
        ["description", "str", "trim; ≤120; default empty"],
    ],
    widths=[1.4, 1.2, 4.4],
)
para("Status derivation:", bold=True)
add_table(
    ["Condition", "Status"],
    [["expiry < today", "Expired"], ["expiry == today", "Active"], ["expiry > today", "Upcoming"]],
    widths=[3.2, 3.8],
)
para(
    "Serialization uses ISO date strings. CSV column order: id, title, category, date_posted, "
    "expiry_date, status, author, description. JSON writes are atomic (write tmp then "
    "os.replace) and reads tolerate missing/empty/corrupt files."
)


# ===========================================================================
# 10. API Overview
# ===========================================================================
doc.add_heading("10. API Overview", level=1)
para(
    "The complete reference — with full JSON examples and curl commands for every endpoint — "
    "is docs/API_REFERENCE.md. The endpoint set is summarised below."
)
add_table(
    ["Method", "Path", "Purpose"],
    [
        ["GET", "/api/health", "Health + cookie/CSRF handshake"],
        ["GET", "/api/notices", "List with category/q/sort filters"],
        ["POST", "/api/notices", "Create notice"],
        ["GET", "/api/notices/{id}", "Retrieve one"],
        ["PUT", "/api/notices/{id}", "Update one (partial)"],
        ["DELETE", "/api/notices/{id}", "Delete one"],
        ["GET", "/api/summary", "Executive summary"],
        ["GET", "/api/warnings", "Threshold warnings"],
        ["POST", "/api/export", "Export MD/TXT/CSV"],
        ["POST", "/api/import", "Bulk CSV import"],
        ["GET", "/api/risk/{id}", "Risk score + components"],
        ["GET", "/api/events", "Recent structured events"],
    ],
    widths=[1.1, 2.8, 3.1],
)
para("Error codes: 400, 401, 403, 404, 413, 422, 500 — each with a JSON error envelope.", italic=True)


# ===========================================================================
# 11. Security
# ===========================================================================
doc.add_heading("11. Security", level=1)
para("Defence in depth is applied at multiple independent boundaries:")
add_table(
    ["Control", "Behaviour"],
    [
        ["Loopback bind", "Server listens only on 127.0.0.1"],
        ["Origin/Referer check", "Foreign origins rejected with 403"],
        ["Double-submit CSRF", "HttpOnly session cookie + readable CSRF cookie echoed in X-CSRF-Token; constant-time compare"],
        ["Bearer token", "Optional NOTICE_API_TOKEN via constant-time hmac.compare_digest"],
        ["Static whitelist", "Only approved UI files served; no path traversal"],
        ["Body-size limit", "1 MiB cap → 413"],
        ["Strict CSP", "default-src 'self'; script-src 'self'; object-src 'none'; nosniff"],
        ["HTML escaping", "All user-controlled strings escaped to prevent stored XSS"],
    ],
    widths=[1.8, 5.2],
)


# ===========================================================================
# 12. Novel Algorithm
# ===========================================================================
doc.add_heading("12. Novel Algorithm — Notice Risk & Priority Score", level=1)
para(
    "The score blends four orthogonal signals into a deterministic number in [0,1]. Every term "
    "is inspectable, so the result is fully explainable. The FNV-1a hash is used only to derive "
    "a stable category weight — not to hide information."
)
code("urgency          = 1 if (E-T).days < 0 else clamp01(1 - (E-T).days/30)")
code("staleness        = clamp01((T-P).days/90)")
code("category_weight  = (fnv1a32(utf8(C.lower())) mod 1000)/1000")
code("history_factor   = 0.5 + 0.5 * (overdue same-category lower-id notices / max(1, total same-category lower-id))")
code("score            = clamp01(0.45*urgency + 0.20*staleness + 0.20*category_weight + 0.15*history_factor)")
para("Rounding: 6 decimal places, ROUND_HALF_UP.", bold=True)
para("Weights: urgency 45%, staleness 20%, category 20%, history 15% (sum = 1.00).", bold=True)
para(
    "Boundedness: each term lies in [0,1] and the weights form a convex combination, so the "
    "score is always within [0,1]; clamp01 is a defensive backstop. FNV-1a uses offset basis "
    "2166136261 and prime 16777619, multiplying then XOR-ing each UTF-8 byte mod 2^32."
)
para(
    "History is computed over records with a lower id only, making it independent of roster "
    "order. Python and JavaScript implementations use the same arithmetic, UTF-8 encoding, "
    "and half-up rounding, and are verified byte-identical by a parity test over the 40-record "
    "seed dataset plus edge cases."
)


# ===========================================================================
# 13. Implementation Details
# ===========================================================================
doc.add_heading("13. Implementation Details", level=1)
add_table(
    ["Module", "Responsibility"],
    [
        ["models.py", "Notice dataclass, status computation, serialization"],
        ["validation.py", "Pure validators + interactive prompt loops"],
        ["logic.py", "Search, summary, warnings, id helpers"],
        ["storage.py", "JSON/CSV load/save; corruption tolerance"],
        ["reporting.py", "Tables, summaries, MD/TXT/CSV exports"],
        ["seed_data.py", "40-record realistic dataset generator"],
        ["main.py", "CLI entry point + menu dispatch"],
        ["HTTP/security layer", "API routes, middleware, events, scoring"],
    ],
    widths=[2.2, 4.8],
)
para(
    "Key implementation choices: dataclasses for the entity; pure functions for logic; "
    "atomic file writes; try/except around all I/O; ANSI colours that degrade gracefully; "
    "status always derived rather than trusted; single Command registry for CLI and API."
)


# ===========================================================================
# 14. Testing & Quality Assurance
# ===========================================================================
doc.add_heading("14. Testing & Quality Assurance", level=1)
for h, b in [
    ("Unit tests", "Validators, status, search, summary, warnings, id/delete, JSON/CSV round-trips, exports (test_app.py)."),
    ("Invariant/property tests", "Score bounded [0,1]; determinism; id uniqueness; status consistency; date order; round-trip across backends; export parity; history order-independence."),
    ("End-to-end API tests", "CRUD, filters, summary, warnings; auth matrix 400/401/403/404/413/422; security header assertions."),
    ("Playwright browser QA", "Load UI, add/edit/delete, verify no console errors, XSS escaping, screenshots."),
    ("Cross-language parity", "Feed identical fixtures to Python and JS scorers; assert identical 6-decimal output."),
]:
    doc.add_heading(h, level=2)
    para(b)


# ===========================================================================
# 15. Deployment
# ===========================================================================
doc.add_heading("15. Deployment", level=1)
para("Requirements: Python 3.10+; no third-party runtime packages for the core.")
code("# generate demo data\npython seed_data.py")
code("# run terminal app\npython main.py")
code("# serve local HTTP API\npython main.py --serve 8000")
code("# optional: enable bearer auth\nset NOTICE_API_TOKEN=my-secret")
for b in [
    "Data directory data/ is created automatically;",
    "Static UI assets must be in the whitelist;",
    "For production-style use, keep the loopback bind and terminate TLS at a trusted local proxy if needed;",
    "Windows, macOS, and Linux are supported via os.path.join and graceful ANSI handling.",
]:
    bullet(b)


# ===========================================================================
# 16. User Guide / 2-minute demo
# ===========================================================================
doc.add_heading("16. User Guide / 2-Minute Demo", level=1)
add_table(
    ["Step", "Action", "Expected Result"],
    [
        ["1", "python seed_data.py", "40 CSV + JSON sample records written"],
        ["2", "python main.py", "CLI banner + menu shown"],
        ["3", "Press 9", "40 sample records loaded"],
        ["4", "Press 6", "Summary + overdue/expiring warnings"],
        ["5", "Press 1", "Add a notice via validated prompts"],
        ["6", "Press 7", "Export MD/TXT/CSV to data/"],
        ["7", "Restart app", "Records persist — proves durability"],
        ["8", "GET /api/risk/10", "Score + components returned"],
    ],
    widths=[0.6, 3.0, 3.4],
)
para(
    "Menu map: 1 Add · 2 View · 3 Search · 4 Update · 5 Delete · 6 Summary & warnings · "
    "7 Export · 8 Bulk import · 9 Load sample · 0 Exit."
)


# ===========================================================================
# 17. Conclusion & Future Work
# ===========================================================================
doc.add_heading("17. Conclusion & Future Work", level=1)
para(
    "The Notice Board Organizer delivers a complete, dependency-free solution to the original "
    "brief while satisfying the rubric's architecture, security, and novelty requirements. Its "
    "four-layer design keeps concerns separated, the pattern-driven registries make it "
    "extensible, and the deterministic risk score provides explainable prioritisation with "
    "cross-language parity."
)
para("Future work:", bold=True)
for b in [
    "Polished browser UI with interactive canvas charts (optional, no core dependency impact);",
    "Additional backends (YAML, remote read-only API) via the Strategy registry;",
    "Configurable scoring weights and thresholds exposed via settings;",
    "Scheduled warning digests delivered through the event bus;",
    "Extended parity suite covering more languages.",
]:
    bullet(b)
para("— End of document —", italic=True, color=GREY)


# ---------------------------------------------------------------------------
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "NoticeBoardOrganizer_Documentation.docx")
doc.save(out)
print(f"Saved {out}")
