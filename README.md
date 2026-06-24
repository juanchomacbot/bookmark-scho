# Smart PDF Bookmark Injector

A Shiny for Python web app that injects a precise, hierarchy-aware bookmark outline into any PDF file. Unlike tools that only link to the top of a page, it uses **PyMuPDF** to locate each heading's exact vertical position and creates a bookmark that scrolls the reader to that precise line.

---

## Features

- Upload any PDF and a JSON outline — no scripting required.
- **Page-aware fast path:** when the outline carries an optional 1-based `page` for a heading (captured by the Google Scholar console script), the app jumps straight to that page instead of scanning the whole PDF — faster and immune to printed-Table-of-Contents false positives.
- Two-pass text search: exact match first, then a Unicode-normalized fallback that handles curly apostrophes, em dashes, ligatures, and other encoding mismatches between the JSON source and the PDF.
- Graceful degradation: headings rendered as images (no selectable text) still land on the correct page via the outline's page hint; outlines with no page hint fall back to a full-document search that links to the last occurrence of the heading.
- Configurable header/footer exclusion margin (in points) to prevent running page headers from hijacking bookmark targets.
- Per-heading processing log shown in the UI, distinguishing each match path.
- One-click download of the bookmarked PDF.
- Built-in "How to Get JSON" tab with instructions for extracting an outline from the Google Scholar PDF reader.
- "jut" brand styling (Bootswatch Lux + Nunito Sans, vendored for offline use).

---

## Project Structure

```
.
├── app.py                  # Shiny app — UI, server logic, PDF processing
├── json_indications.md     # Instructions + console script, rendered in the "How to Get JSON" tab
├── tests/                  # pytest suite (conftest builds tiny PDFs on the fly)
├── www/                    # Brand assets: estilos-jut.css, icono-jut.svg, vendored fonts
├── requirements.txt        # Pinned runtime dependencies
├── requirements-dev.txt    # Runtime deps + pytest
├── pyproject.toml          # Package metadata (Python >= 3.12.13) + pytest config
├── CLAUDE.md               # Guidance for Claude Code
└── .venv/                  # Virtual environment (not committed)
```

---

## Setup

**1. Create and activate a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

**2. Install dependencies**

```bash
pip install -r requirements.txt          # runtime only
pip install -r requirements-dev.txt      # adds pytest for development
```

**3. Run the app**

```bash
shiny run app.py
```

Then open `http://localhost:8000` in your browser.

**4. Run the tests**

```bash
pytest
```

---

## Usage

### Step 1 — Prepare the JSON outline

The app expects a JSON file that is a list of objects, each with the following keys:

| Key | Type | Required | Description |
|---|---|---|---|
| `title` | string | yes | Heading text as it appears in the PDF (the first 35 chars are used for the search query) |
| `level` | integer | yes | Hierarchy depth (1 = main heading, 2 = sub-heading, …) |
| `page` | integer | no | 1-based page the heading lives on; lets the app jump straight there instead of searching the whole PDF |

```json
[
    { "title": "1. Introduction", "level": 1, "page": 1 },
    { "title": "1.1 Background",  "level": 2, "page": 2 },
    { "title": "2. Methodology",  "level": 1, "page": 5 }
]
```

The `page` key is optional: outlines without it (e.g. older `{title, level}` files) still work via the full-document search, so nothing breaks. See the **"How to Get JSON"** tab in the app for a step-by-step guide on extracting this outline automatically from the Google Scholar PDF reader using a browser console script — that script captures the `page` for you.

### Step 2 — Upload and process

1. Upload the PDF under **"1. Choose PDF file"**.
2. Upload the JSON outline under **"2. Choose JSON outline file"**.
3. Adjust **"Header / footer exclusion margin"** if needed (default 30 pt works for most web-saved PDFs; increase it if running headers are still matched).
4. Click **"Apply Bookmarks"**.
5. Review the processing log, then click **"Download Bookmarked PDF"**.

---

## How the Search Works

For each heading the app resolves a `(page, y-coordinate)` destination through up to three tiers:

1. **Tier 1 — page-hint fast path.** If the item has a valid `page`, the app searches only that page (via `_search_page`). A hit there is unambiguous and gives the exact Y, so the rest of the document is skipped.
2. **Tier 2 — full-document scan.** Used when there is no page hint, or the hinted page didn't match. Every page is searched and the **last** matching occurrence is chosen, which skips any printed Table-of-Contents entries and lands on the real section body.
3. **Tier 3 — top-of-page fallback.** If the heading text isn't selectable anywhere (e.g. it's rendered as an image) but a valid `page` hint exists, the app trusts the hint and links to the top of that page.

Within a page, `_search_page` itself runs two passes:

1. **Exact search** — PyMuPDF's native `page.search_for()`. Fast and precise.
2. **Normalized fallback** — If the exact search misses (e.g. the JSON has a curly apostrophe `ʼ` U+02BC but the PDF stores a right single quotation mark `'` U+2019), both strings are normalized before comparison:
   - Unicode NFKD decomposition.
   - All apostrophe/single-quote variants → `'`.
   - All dash/hyphen variants → `-`.
   - Combining diacritics removed.
   - Whitespace collapsed, lowercased.

Matches within the configured margin of the top or bottom page edge are discarded, ensuring running headers and footers never override the real section heading.

---

## Limitations

- **Scanned / image PDFs** — text matching requires selectable text. With a `page` hint the bookmark still lands on the correct page (Tier 3), but to target the exact line, run OCR first (e.g. with `ocrmypdf`).
- **Heavily fragmented text** — some PDF exporters split a single heading across many tiny text spans. If a heading consistently fails to match, try shortening the `title` value in your JSON to the first unambiguous words.

---

## Dependencies

| Package | Purpose |
|---|---|
| `shiny` | Web application framework |
| `shinyswatch` | Bootswatch Lux theme for the "jut" brand styling |
| `pymupdf` | PDF text search and bookmark injection (imported as `fitz`) |
| `pytest` | Test runner (development only) |
