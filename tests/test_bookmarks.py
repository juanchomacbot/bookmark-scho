"""Tests for the bookmark injection logic in app.py.

Covers the text-normalization helper, the per-page margin-aware search, and the
three-tier page-resolution strategy in _apply_smart_bookmarks.
"""

import fitz
import pytest

from app import _apply_smart_bookmarks, _normalize, _search_page
from tests.conftest import read_toc


# --- _normalize ------------------------------------------------------------

def test_normalize_folds_curly_apostrophe():
    # Curly apostrophe (PDF) and straight apostrophe (JSON) must compare equal.
    assert _normalize("don’t") == _normalize("don't")


def test_normalize_folds_dashes():
    # En dash, em dash and hyphen all collapse to ASCII hyphen.
    assert _normalize("a–b") == _normalize("a-b") == _normalize("a—b")


def test_normalize_expands_ligatures_and_lowercases():
    assert _normalize("Oﬃce") == "office"  # "ﬃ" ligature -> "ffi"


def test_normalize_collapses_whitespace():
    assert _normalize("  Hello   World  ") == "hello world"


# --- _search_page ----------------------------------------------------------

def _single_page(build_pdf, text, y):
    doc = fitz.open(build_pdf([[(text, y)]]))
    return doc, doc[0]


def test_search_page_finds_heading_in_content_zone(build_pdf):
    doc, page = _single_page(build_pdf, "Methods", 400)
    y = _search_page(page, "Methods", margin_pt=30.0)
    doc.close()
    assert y is not None
    assert 380 < y < 400  # near the inserted baseline


def test_search_page_ignores_text_in_top_margin(build_pdf):
    # A running header near the very top must be excluded by the margin filter.
    doc, page = _single_page(build_pdf, "Running Header", 12)
    y = _search_page(page, "Running Header", margin_pt=30.0)
    doc.close()
    assert y is None


def test_search_page_unicode_fallback(build_pdf):
    # PDF has an accented "é"; the query is plain ASCII. PyMuPDF's exact search
    # (Pass 1) is accent-sensitive and misses, so the normalized Pass 2 must catch it.
    doc, page = _single_page(build_pdf, "Café Notes", 300)
    y = _search_page(page, "Cafe Notes", margin_pt=30.0)
    doc.close()
    assert y is not None


def test_search_page_returns_none_when_absent(build_pdf):
    doc, page = _single_page(build_pdf, "Introduction", 300)
    y = _search_page(page, "Conclusion", margin_pt=30.0)
    doc.close()
    assert y is None


# --- _apply_smart_bookmarks: the three tiers -------------------------------

@pytest.fixture
def doc_path(build_pdf):
    # 3-page document with one distinct heading per page.
    return build_pdf(
        [
            [("Introduction", 120)],
            [("Methods", 160)],
            [("Results", 220)],
        ]
    )


def test_tier1_correct_page_hint_gives_exact_y(doc_path, tmp_path):
    out = str(tmp_path / "out.pdf")
    msgs, ok = _apply_smart_bookmarks(
        doc_path, out, [{"title": "Introduction", "level": 1, "page": 1}]
    )
    assert ok
    (entry,) = read_toc(out)
    assert entry["page"] == 1
    assert 100 < entry["y"] < 120  # exact heading Y, not a top-of-page fallback
    assert any("page from outline" in m and "top of page" not in m for m in msgs)


def test_tier2_wrong_page_hint_is_corrected(doc_path, tmp_path):
    # Hint says page 3 but "Methods" is really on page 2: full scan must correct it.
    out = str(tmp_path / "out.pdf")
    _, ok = _apply_smart_bookmarks(
        doc_path, out, [{"title": "Methods", "level": 1, "page": 3}]
    )
    assert ok
    (entry,) = read_toc(out)
    assert entry["page"] == 2


def test_tier2_no_page_hint_uses_legacy_search(doc_path, tmp_path):
    out = str(tmp_path / "out.pdf")
    _, ok = _apply_smart_bookmarks(doc_path, out, [{"title": "Results", "level": 1}])
    assert ok
    (entry,) = read_toc(out)
    assert entry["page"] == 3


def test_tier3_absent_text_lands_on_top_of_hinted_page(doc_path, tmp_path):
    out = str(tmp_path / "out.pdf")
    msgs, ok = _apply_smart_bookmarks(
        doc_path, out, [{"title": "Ghost Heading", "level": 1, "page": 2}]
    )
    assert ok
    (entry,) = read_toc(out)
    assert entry["page"] == 2
    assert entry["y"] == 30.0  # default margin -> top of page
    assert any("top of page" in m for m in msgs)


def test_invalid_page_hint_falls_through_to_search(doc_path, tmp_path):
    # Out-of-range page is ignored; the text is still found by the scan.
    out = str(tmp_path / "out.pdf")
    _, ok = _apply_smart_bookmarks(
        doc_path, out, [{"title": "Methods", "level": 1, "page": 999}]
    )
    assert ok
    (entry,) = read_toc(out)
    assert entry["page"] == 2


def test_unfound_heading_without_hint_is_reported(doc_path, tmp_path):
    out = str(tmp_path / "out.pdf")
    msgs, ok = _apply_smart_bookmarks(doc_path, out, [{"title": "Nowhere", "level": 1}])
    assert ok
    assert read_toc(out) == []  # nothing bookmarked
    assert any("Not found" in m for m in msgs)


def test_backward_compatible_old_format(doc_path, tmp_path):
    # Old {title, level} outlines (no page key) keep working unchanged.
    out = str(tmp_path / "out.pdf")
    outline = [
        {"title": "Introduction", "level": 1},
        {"title": "Methods", "level": 2},
        {"title": "Results", "level": 2},
    ]
    _, ok = _apply_smart_bookmarks(doc_path, out, outline)
    assert ok
    toc = read_toc(out)
    assert [e["page"] for e in toc] == [1, 2, 3]
    assert [e["level"] for e in toc] == [1, 2, 2]
