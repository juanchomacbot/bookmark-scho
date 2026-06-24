# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies (runtime only)
pip install -r requirements.txt

# Install dependencies for development (adds pytest)
pip install -r requirements-dev.txt

# Run the app
shiny run app.py
# App available at http://localhost:8000

# Run the test suite
pytest
```

## Testing (TDD)

This project follows **test-driven development**: write a failing test first, then
the minimal code to pass it, then refactor. Tests live in `tests/` and run with
`pytest` (configured in `pyproject.toml`).

- `tests/conftest.py` — the `build_pdf` fixture writes tiny PDFs with PyMuPDF on the
  fly (no binary fixtures), plus a `read_toc` helper to read back the saved bookmarks.
- `tests/test_bookmarks.py` — covers `_normalize`, `_search_page` (margin exclusion +
  the normalized Pass-2 fallback), and every tier of `_apply_smart_bookmarks`.

**Fixture gotcha:** PyMuPDF's default font cannot embed curly apostrophes, en/em
dashes, or ligatures — `insert_text` replaces them with `·`. To test the Unicode
fallback through a generated PDF, use accented Latin-1 characters (e.g. `é`), which
round-trip correctly. Test `_normalize` directly on Python strings for the other cases.

## Architecture

This is a single-file Shiny for Python web app (`app.py`) with no backend server, database, or build step.

**Data flow:**
1. User uploads a PDF and a JSON outline file via the sidebar
2. Clicking "Apply Bookmarks" triggers `_on_process()`, which calls `_apply_smart_bookmarks()`
3. `_apply_smart_bookmarks()` iterates the outline, calls `_search_page()` per page per heading, collects `(level, title, page, y-coord)` tuples, and writes the TOC via PyMuPDF's `doc.set_toc()`
4. The processed PDF is written to a temp file; the reactive `_result_path` value is set so the download button can serve it

**Two-pass text search (`_search_page`):**
- Pass 1: PyMuPDF `page.search_for()` (exact, fast)
- Pass 2: normalized block-text scan via `_normalize()` — handles Unicode mismatches (curly apostrophes, em dashes, ligatures) between the JSON source and the embedded PDF text

**TOC bypass heuristic:** when a heading matches multiple pages (e.g., it appears in a printed Table of Contents), `_apply_smart_bookmarks` always picks `matches[-1]` — the last occurrence — which is the real section body.

**Margin exclusion:** matches within `margin_pt` of the top or bottom page edge are discarded so running headers/footers never win over the real heading. `margin_pt` is user-configurable via the sidebar `input_numeric` (default 30 pt).

**UI layout:** two tabs (`navset_tab`) — "Tool" (the sidebar + processing log) and "How to Get JSON" (the rendered `json_indications.md`).

**Key constraint:** PyMuPDF is imported as `fitz`; the package name in requirements.txt is `pymupdf`. Runtime requires Python >= 3.12.13 (see pyproject.toml).

## Styling ("jut" brand)

The app uses the **"jut" visual style**: Bootswatch **Lux** + **Nunito Sans** + a teal/near-black accent palette (a port of the `style-jut-1` R/dashboard brand to Shiny for Python).

- Theme: `theme=shinyswatch.theme.lux` on `ui.page_fluid` (hence the `shinyswatch` dependency).
- `www/estilos-jut.css` layers the jut accents on top of Lux and vendors Nunito Sans via `@font-face` so the font works **offline** (the `.ttf` + its OFL license live in `www/fonts/`). `www/icono-jut.svg` is the favicon.
- Static files are served by passing `static_assets=_WWW_DIR` to `App(...)`, which mounts `www/` at the app root — so `href="estilos-jut.css"` and the `@font-face` `url("fonts/…")` resolve. After editing CSS/icons, hard-refresh the browser (they're browser-cached).
- The branded header is a `.jut-header` div (not `ui.panel_title`); the browser-tab title is set via `page_fluid(title=...)`. There is no navbar in this tool, so the source brand's navbar/value-box/DataTables/Leaflet rules were intentionally dropped.

## JSON input format

```json
[
  { "title": "1. Introduction", "level": 1, "page": 1 },
  { "title": "1.1 Background",  "level": 2, "page": 2 }
]
```

`title` must match selectable text in the PDF (first 35 chars are used for the search query). `level` is 1-based hierarchy depth. `page` is optional (1-based): when present, `_apply_smart_bookmarks` scopes the Y-search to that single page (falling back to the top of that page if the heading text doesn't match), skipping the whole-document scan and the `matches[-1]` TOC-bypass heuristic. Outlines without `page` use the legacy full-document scan, so older files keep working.

## Static content

`json_indications.md` is read once at startup and rendered as Markdown in the "How to Get JSON" tab. It contains the browser console script users run against the Google Scholar PDF reader to extract an outline.
