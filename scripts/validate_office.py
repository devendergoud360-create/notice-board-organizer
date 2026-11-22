"""Validate the Office deliverables (run in CI)."""

from docx import Document
from pptx import Presentation

PPTX = "docs/NoticeBoardOrganizer_Presentation.pptx"
DOCX = "docs/NoticeBoardOrganizer_Documentation.docx"

slides = len(Presentation(PPTX).slides)
assert slides == 14, f"expected 14 slides, got {slides}"
doc = Document(DOCX)
headings = [p for p in doc.paragraphs if p.style.name.startswith("Heading")]
assert len(headings) >= 15, f"expected >=15 headings, got {len(headings)}"
print(f"Office deliverables OK: {slides} slides, {len(headings)} headings")
