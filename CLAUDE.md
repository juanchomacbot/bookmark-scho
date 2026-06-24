# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
shiny run app.py
# App available at http://localhost:8000
```

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

## JSON input format

```json
[
  { "title": "1. Introduction", "level": 1 },
  { "title": "1.1 Background",  "level": 2 }
]
```

`title` must match selectable text in the PDF (first 35 chars are used for the search query). `level` is 1-based hierarchy depth.

## Static content

`json_indications.md` is read once at startup and rendered as Markdown in the "How to Get JSON" tab. It contains the browser console script users run against the Google Scholar PDF reader to extract an outline.
