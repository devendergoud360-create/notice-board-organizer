#!/usr/bin/env python3
"""Generate NoticeBoardOrganizer_Presentation.pptx (14 slides).

Reproducible with only the Python standard library + python-pptx.
Run:  python docs/make_pptx.py
"""

from __future__ import annotations

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

# ---------------------------------------------------------------------------
# Palette — dark navy / teal accents
# ---------------------------------------------------------------------------
NAVY = RGBColor(0x0B, 0x1F, 0x3A)       # primary dark background
NAVY2 = RGBColor(0x12, 0x2C, 0x50)      # lighter navy panels
TEAL = RGBColor(0x1F, 0xC8, 0xB4)       # accent teal
TEAL_D = RGBColor(0x12, 0x8C, 0x7E)     # deep teal
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
OFFWHITE = RGBColor(0xE8, 0xF1, 0xF7)
GREY = RGBColor(0xA9, 0xBD, 0xCC)
AMBER = RGBColor(0xF5, 0xB4, 0x42)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H
BLANK = prs.slide_layouts[6]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def add_slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = NAVY
    return s


def rect(slide, x, y, w, h, color, line=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    shp.shadow.inherit = False
    return shp


def textbox(slide, x, y, w, h):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    return tb, tf


def set_run(r, size, color=WHITE, bold=False, italic=False, font="Calibri"):
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = font


def add_title(slide, kicker, title, accent=TEAL):
    """Standard slide header with kicker line + big title."""
    rect(slide, Inches(0.55), Inches(0.55), Inches(0.16), Inches(0.95), accent)
    tb, tf = textbox(slide, Inches(0.85), Inches(0.45), Inches(11.8), Inches(0.4))
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = kicker.upper()
    set_run(r, 13, GREY, bold=True)
    tb2, tf2 = textbox(slide, Inches(0.85), Inches(0.78), Inches(11.9), Inches(0.85))
    p2 = tf2.paragraphs[0]
    r2 = p2.add_run()
    r2.text = title
    set_run(r2, 32, WHITE, bold=True)
    # rule under header
    rect(slide, Inches(0.85), Inches(1.62), Inches(11.6), Pt(2), NAVY2)


def add_footer(slide, n):
    tb, tf = textbox(slide, Inches(0.55), Inches(7.02), Inches(8), Inches(0.35))
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = "Notice Board Organizer  ·  LocalImpact Challenge #30"
    set_run(r, 10, GREY)
    tb2, tf2 = textbox(slide, Inches(12.0), Inches(7.02), Inches(0.9), Inches(0.35))
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.RIGHT
    r2 = p2.add_run()
    r2.text = str(n)
    set_run(r2, 10, GREY)


def bullets(slide, x, y, w, h, items, size=19, color=OFFWHITE, gap=6, bullet="•"):
    tb, tf = textbox(slide, x, y, w, h)
    first = True
    for it in items:
        if isinstance(it, tuple):
            text, lvl = it
        else:
            text, lvl = it, 0
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(gap)
        p.level = lvl
        prefix = ("    " * lvl) + (bullet + "  " if lvl == 0 else "–  ")
        r = p.add_run()
        r.text = prefix + text
        set_run(r, size - (1 if lvl else 0), color if lvl == 0 else GREY)
    return tb


def panel(slide, x, y, w, h, title, body_items, accent=TEAL, body_size=16):
    rect(slide, x, y, w, h, NAVY2)
    rect(slide, x, y, w, Inches(0.5), accent)
    tb, tf = textbox(slide, x + Inches(0.2), y + Inches(0.06), w - Inches(0.4), Inches(0.4))
    r = tf.paragraphs[0].add_run()
    r.text = title
    set_run(r, 17, NAVY, bold=True)
    bullets(slide, x + Inches(0.22), y + Inches(0.65), w - Inches(0.44),
            h - Inches(0.8), body_items, size=body_size, gap=5)


# ===========================================================================
# Slide 1 — Title
# ===========================================================================
s = add_slide()
rect(s, Inches(0), Inches(0), SLIDE_W, Inches(0.22), TEAL)
rect(s, Inches(0), Inches(7.28), SLIDE_W, Inches(0.22), TEAL)
tb, tf = textbox(s, Inches(0.9), Inches(1.7), Inches(11.5), Inches(1.0))
r = tf.paragraphs[0].add_run()
r.text = "LOCALIMPACT CHALLENGE  ·  PROJECT #30"
set_run(r, 16, TEAL, bold=True)
tb, tf = textbox(s, Inches(0.9), Inches(2.5), Inches(11.6), Inches(2.0))
p = tf.paragraphs[0]
r = p.add_run(); r.text = "Notice Board"
set_run(r, 46, WHITE, bold=True)
p2 = tf.add_paragraph()
r2 = p2.add_run(); r2.text = "Organizer"
set_run(r2, 46, TEAL, bold=True)
tb, tf = textbox(s, Inches(0.9), Inches(4.8), Inches(11), Inches(0.7))
r = tf.paragraphs[0].add_run()
r.text = "A secure, deterministic campus notice system — CLI + local API + novel risk score"
set_run(r, 20, OFFWHITE)
tb, tf = textbox(s, Inches(0.9), Inches(6.2), Inches(11), Inches(0.6))
r = tf.paragraphs[0].add_run()
r.text = "Python 3.10+ standard library  ·  Four-layer architecture  ·  Cross-language parity"
set_run(r, 14, GREY)
add_footer(s, 1)

# ===========================================================================
# Slide 2 — Problem
# ===========================================================================
s = add_slide()
add_title(s, "Why it matters", "Campus notice boards are chaotic")
bullets(s, Inches(0.9), Inches(2.0), Inches(7.2), Inches(4.6), [
    "Paper notices go stale; expiry dates are missed",
    "No quick way to answer “what is overdue?”",
    "No search, no summary, no audit trail",
    "Invalid or malformed entries creep in",
    "Administrators waste time on manual tracking",
], size=20, gap=10)
panel(s, Inches(8.5), Inches(2.0), Inches(3.9), Inches(4.3),
      "Impact", [
          "Missed deadlines",
          "Outdated information",
          "No accountability",
          "Wasted admin effort",
      ], accent=AMBER, body_size=17)
add_footer(s, 2)

# ===========================================================================
# Slide 3 — Objectives
# ===========================================================================
s = add_slide()
add_title(s, "What we set out to build", "Objectives")
bullets(s, Inches(0.9), Inches(2.0), Inches(11.6), Inches(4.8), [
    "Store notices with category, dates, expiry, author and description",
    "Validate every input defensively — types, ranges, categories, dates",
    "Persist reliably to JSON / CSV / SQLite via interchangeable backends",
    "Search, summarise and warn on overdue / expiring notices",
    "Export MD / TXT / CSV and import CSV with row-level error logs",
    "Expose a secure local HTTP API with CSRF, CSP, bearer token, origin checks",
    "Add a novel, explainable, deterministic risk score with Python/JS parity",
], size=19, gap=8)
add_footer(s, 3)

# ===========================================================================
# Slide 4 — Solution Overview
# ===========================================================================
s = add_slide()
add_title(s, "The big picture", "Solution Overview")
panel(s, Inches(0.7), Inches(2.0), Inches(3.8), Inches(4.6), "Domain Engine", [
    "Notice dataclass",
    "Pure logic functions",
    "Strict validators",
    "Risk score algorithm",
], accent=TEAL)
panel(s, Inches(4.7), Inches(2.0), Inches(3.8), Inches(4.6), "Interfaces", [
    "Colour CLI menu",
    "Local HTTP API",
    "Optional browser UI",
    "Shared Command registry",
], accent=TEAL_D)
panel(s, Inches(8.7), Inches(2.0), Inches(3.8), Inches(4.6), "Trust & Data", [
    "Strategy storage backends",
    "Observer event log",
    "CSRF / CSP / bearer",
    "MD / TXT / CSV export",
], accent=AMBER)
add_footer(s, 4)

# ===========================================================================
# Slide 5 — Architecture (four layers)
# ===========================================================================
s = add_slide()
add_title(s, "Separation of concerns", "Architecture — Four Layers")
layers = [
    ("PRESENTATION", "CLI · Browser UI · HTTP API serializer", TEAL),
    ("APPLICATION", "Command registry · Event bus · Security · JSON logger", TEAL_D),
    ("DOMAIN", "Notice entity · Pure logic · Validators · Risk score", AMBER),
    ("PERSISTENCE", "Strategy registry · JSON / CSV / SQLite", GREY),
]
y = Inches(2.05)
for name, desc, col in layers:
    rect(s, Inches(1.0), y, Inches(2.7), Inches(0.95), col)
    tb, tf = textbox(s, Inches(1.1), y + Inches(0.2), Inches(2.5), Inches(0.6))
    r = tf.paragraphs[0].add_run(); r.text = name
    set_run(r, 15, NAVY, bold=True)
    rect(s, Inches(3.7), y, Inches(8.6), Inches(0.95), NAVY2)
    tb, tf = textbox(s, Inches(3.95), y + Inches(0.22), Inches(8.1), Inches(0.6))
    r = tf.paragraphs[0].add_run(); r.text = desc
    set_run(r, 16, OFFWHITE)
    y += Inches(1.15)
add_footer(s, 5)

# ===========================================================================
# Slide 6 — Design Patterns
# ===========================================================================
s = add_slide()
add_title(s, "Proven patterns, clean code", "Design Patterns")
panel(s, Inches(0.7), Inches(2.0), Inches(3.8), Inches(4.6), "Strategy", [
    "Storage backends behind one interface",
    "Registry selects JSON / CSV / SQLite",
    "Add a format without touching callers",
    "One-line register() extension",
], accent=TEAL)
panel(s, Inches(4.7), Inches(2.0), Inches(3.8), Inches(4.6), "Command", [
    "Actions encapsulated as objects",
    "CLI and API dispatch through one registry",
    "No duplicated business logic",
    "Stable action keys",
], accent=TEAL_D)
panel(s, Inches(8.7), Inches(2.0), Inches(3.8), Inches(4.6), "Observer", [
    "Event bus broadcasts mutations",
    "Structured JSON logger subscribes",
    "Auditable events.jsonl trail",
    "Decoupled side effects",
], accent=AMBER)
add_footer(s, 6)

# ===========================================================================
# Slide 7 — Core Features
# ===========================================================================
s = add_slide()
add_title(s, "From brief to working software", "Core Features")
bullets(s, Inches(0.9), Inches(2.0), Inches(5.7), Inches(4.8), [
    "Add / update / delete notices",
    "Strict validation on every field",
    "Corruption-safe JSON persistence",
    "Keyword + category search",
    "Executive summary & analytics",
], size=19, gap=9)
bullets(s, Inches(6.9), Inches(2.0), Inches(5.5), Inches(4.8), [
    "Overdue / expiring threshold warnings",
    "Markdown / TXT / CSV export",
    "Bulk CSV import with error logs",
    "Paginated terminal tables",
    "40-record seeded demo dataset",
], size=19, gap=9, bullet="✓")
add_footer(s, 7)

# ===========================================================================
# Slide 8 — Data & Storage
# ===========================================================================
s = add_slide()
add_title(s, "One record shape, many backends", "Data & Storage")
tb, tf = textbox(s, Inches(0.9), Inches(1.95), Inches(11.5), Inches(0.5))
r = tf.paragraphs[0].add_run()
r.text = "Notice fields: id · title · category · date_posted · expiry_date · status · author · description"
set_run(r, 15, TEAL, bold=True)
panel(s, Inches(0.7), Inches(2.6), Inches(3.8), Inches(3.9), "JSON", [
    "Human-readable array",
    "Atomic tmp + os.replace",
    "Tolerates corruption",
    "Default store",
], accent=TEAL)
panel(s, Inches(4.7), Inches(2.6), Inches(3.8), Inches(3.9), "CSV", [
    "Fixed 8-column order",
    "Load + export + import",
    "Row-level validation",
    "Seed dataset",
], accent=TEAL_D)
panel(s, Inches(8.7), Inches(2.6), Inches(3.8), Inches(3.9), "SQLite", [
    "Relational backend",
    "Same interface",
    "Strategy-selected",
    "Drop-in replacement",
], accent=AMBER)
add_footer(s, 8)

# ===========================================================================
# Slide 9 — Security
# ===========================================================================
s = add_slide()
add_title(s, "Local-first, defence in depth", "Security")
bullets(s, Inches(0.9), Inches(2.0), Inches(6.0), Inches(4.8), [
    "Loopback-only bind (127.0.0.1)",
    "Origin / Referer allow-list",
    "Double-submit CSRF: HttpOnly session + readable token",
    "Optional constant-time bearer token",
    "Static-file whitelist — no path traversal",
], size=18, gap=8)
bullets(s, Inches(7.1), Inches(2.0), Inches(5.4), Inches(4.8), [
    "1 MiB request body limit",
    "Strict CSP + nosniff headers",
    "HTML escaping prevents stored XSS",
    "Events audited in JSONL log",
    "Every mutation revalidated",
], size=18, gap=8, bullet="✓")
add_footer(s, 9)

# ===========================================================================
# Slide 10 — Novel Algorithm (dedicated)
# ===========================================================================
s = add_slide()
add_title(s, "Novel contribution", "Notice Risk & Priority Score", accent=AMBER)
rect(s, Inches(0.75), Inches(1.85), Inches(11.85), Inches(1.5), NAVY2)
tb, tf = textbox(s, Inches(1.0), Inches(2.0), Inches(11.4), Inches(1.2))
p = tf.paragraphs[0]
r = p.add_run(); r.text = "score = clamp01( 0.45·urgency + 0.20·staleness + 0.20·category_weight + 0.15·history_factor )"
set_run(r, 18, TEAL, bold=True)
p2 = tf.add_paragraph()
r2 = p2.add_run(); r2.text = "Rounded to 6 decimals (ROUND_HALF_UP)  ·  always in [0, 1]"
set_run(r2, 14, GREY)
panel(s, Inches(0.7), Inches(3.55), Inches(2.85), Inches(2.9), "Urgency (45%)", [
    "1 − days_to_expiry/30",
    "Overdue ⇒ 1",
], accent=TEAL, body_size=14)
panel(s, Inches(3.68), Inches(3.55), Inches(2.85), Inches(2.9), "Staleness (20%)", [
    "(T − P).days / 90",
    "Clamped to [0,1]",
], accent=TEAL_D, body_size=14)
panel(s, Inches(6.66), Inches(3.55), Inches(2.85), Inches(2.9), "Category (20%)", [
    "FNV-1a 32-bit hash",
    "(hash mod 1000)/1000",
], accent=AMBER, body_size=14)
panel(s, Inches(9.64), Inches(3.55), Inches(2.85), Inches(2.9), "History (15%)", [
    "Prior same-category",
    "overdue ratio, lower ids",
], accent=GREY, body_size=14)
tb, tf = textbox(s, Inches(0.9), Inches(6.6), Inches(11.5), Inches(0.4))
r = tf.paragraphs[0].add_run()
r.text = "Explainable · Deterministic · Dependency-free · Python ↔ JavaScript parity"
set_run(r, 13, TEAL, bold=True)
add_footer(s, 10)

# ===========================================================================
# Slide 11 — Testing & QA
# ===========================================================================
s = add_slide()
add_title(s, "Confidence by construction", "Testing & QA")
panel(s, Inches(0.7), Inches(2.0), Inches(3.8), Inches(4.6), "Unit", [
    "Validators & dates",
    "Status computation",
    "Search / summary / warnings",
    "JSON & CSV round-trips",
], accent=TEAL)
panel(s, Inches(4.7), Inches(2.0), Inches(3.8), Inches(4.6), "Invariants & E2E", [
    "Score bounded [0,1]",
    "Determinism / no order effects",
    "Full API auth matrix",
    "400/401/403/404/413/422",
], accent=TEAL_D)
panel(s, Inches(8.7), Inches(2.0), Inches(3.8), Inches(4.6), "Browser & Parity", [
    "Playwright smoke QA",
    "Zero console errors",
    "XSS escaping verified",
    "Python ↔ JS score diff",
], accent=AMBER)
add_footer(s, 11)

# ===========================================================================
# Slide 12 — Demo Walkthrough
# ===========================================================================
s = add_slide()
add_title(s, "Two-minute guided tour", "Demo Walkthrough")
steps = [
    ("1", "Generate sample data  →  python seed_data.py"),
    ("2", "Launch CLI           →  python main.py   (option 9 loads 40 records)"),
    ("3", "View analytics        →  option 6  (summary + warnings)"),
    ("4", "Add a notice          →  option 1  (strict validation prompts)"),
    ("5", "Export a report       →  option 7  (MD / TXT / CSV)"),
    ("6", "Serve the API         →  /api/health, /api/summary, /api/risk/{id}"),
    ("7", "Restart & reload      →  persistence proven"),
]
y = Inches(2.0)
for num, text in steps:
    rect(s, Inches(0.95), y, Inches(0.55), Inches(0.55), TEAL)
    tb, tf = textbox(s, Inches(0.95), y + Inches(0.08), Inches(0.55), Inches(0.4))
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = num; set_run(r, 16, NAVY, bold=True)
    tb, tf = textbox(s, Inches(1.75), y + Inches(0.05), Inches(10.5), Inches(0.5))
    r = tf.paragraphs[0].add_run(); r.text = text
    set_run(r, 17, OFFWHITE)
    y += Inches(0.68)
add_footer(s, 12)

# ===========================================================================
# Slide 13 — Results & Predictions
# ===========================================================================
s = add_slide()
add_title(s, "What the system delivers", "Results & Predictions")
bullets(s, Inches(0.9), Inches(2.0), Inches(6.0), Inches(4.8), [
    "40 realistic seeded notices, instantly queryable",
    "Overdue notices flagged correctly after restart",
    "Three interchangeable storage backends",
    "Auditable, structured event log",
    "Deterministic scores — no surprises",
], size=18, gap=9)
bullets(s, Inches(7.1), Inches(2.0), Inches(5.4), Inches(4.8), [
    "Drop-in browser UI over the same API",
    "New backends via one registry line",
    "Export to any downstream tool",
    "Reusable scoring engine for other domains",
    "Strong rubric coverage: core + stretch + security",
], size=18, gap=9, bullet="→")
add_footer(s, 13)

# ===========================================================================
# Slide 14 — Q&A
# ===========================================================================
s = add_slide()
rect(s, Inches(0), Inches(0), SLIDE_W, Inches(0.22), TEAL)
tb, tf = textbox(s, Inches(0.9), Inches(2.4), Inches(11.5), Inches(1.2))
r = tf.paragraphs[0].add_run(); r.text = "Questions?"
set_run(r, 48, TEAL, bold=True)
tb, tf = textbox(s, Inches(0.9), Inches(3.8), Inches(11.5), Inches(1.6))
for i, line in enumerate([
    "Notice Board Organizer — LocalImpact Challenge #30",
    "Python stdlib · Four layers · Strategy / Command / Observer",
    "Deterministic risk score with cross-language parity",
]):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    r = p.add_run(); r.text = line
    set_run(r, 18, OFFWHITE)
rect(s, Inches(0), Inches(7.28), SLIDE_W, Inches(0.22), TEAL)
add_footer(s, 14)

# ---------------------------------------------------------------------------
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "NoticeBoardOrganizer_Presentation.pptx")
prs.save(out)
print(f"Saved {out} ({len(prs.slides)} slides)")
