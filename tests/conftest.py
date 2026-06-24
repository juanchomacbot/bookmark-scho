"""Shared pytest fixtures and helpers for the bookmark tests.

These build tiny in-memory PDFs with PyMuPDF so the suite is fast and needs no
binary fixtures checked into the repo.
"""

import fitz
import pytest


@pytest.fixture
def build_pdf(tmp_path):
    """Return a factory that writes a PDF and gives back its path.

    Usage:
        path = build_pdf([
            [("Introduction", 120)],          # page 1: text at y=120
            [("Methods", 160), ("Notes", 400)],  # page 2: two strings
        ])

    Each page is a list of ``(text, y)`` tuples; text is inserted at x=72 with
    its baseline at the given y (PDF points from the top).
    """

    def _build(pages, name="sample.pdf"):
        doc = fitz.open()
        for entries in pages:
            page = doc.new_page()
            for text, y in entries:
                page.insert_text((72, y), text)
        out = tmp_path / name
        doc.save(str(out))
        doc.close()
        return str(out)

    return _build


def read_toc(pdf_path):
    """Return the saved TOC as a list of dicts: level, title, page, y."""
    doc = fitz.open(pdf_path)
    result = []
    for entry in doc.get_toc(simple=False):
        level, title, page = entry[0], entry[1], entry[2]
        dest = entry[3] if len(entry) > 3 and isinstance(entry[3], dict) else {}
        point = dest.get("to")
        result.append(
            {
                "level": level,
                "title": title,
                "page": page,
                "y": round(point.y, 1) if point is not None else None,
            }
        )
    doc.close()
    return result
