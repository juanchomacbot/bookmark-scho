# Smart PDF Bookmark Injector

A Shiny for Python web app that injects a precise, hierarchy-aware bookmark outline into any PDF file. Unlike tools that only link to the top of a page, it uses **PyMuPDF** to locate each heading's exact vertical position and creates a bookmark that scrolls the reader to that precise line.

---

## Features

- Upload any PDF and a JSON outline — no scripting required.
- Two-pass text search: exact match first, then a Unicode-normalized fallback that handles curly apostrophes, em dashes, ligatures, and other encoding mismatches between the JSON source and the PDF.
- Configurable header/footer exclusion margin (in points) to prevent running page headers from hijacking bookmark targets.
- TOC bypass: when a heading appears more than once (e.g. in a printed Table of Contents), the bookmark links to the last occurrence, which is always the real section body.
- Per-heading processing log shown in the UI.
- One-click download of the bookmarked PDF.
- Built-in "How to Get JSON" tab with instructions for extracting an outline from the Google Scholar PDF reader.

---

## Project Structure

```
.
├── app.py                  # Shiny app — UI, server logic, PDF processing
├── json_indications.md     # Instructions displayed in the second app tab
├── requirements.txt        # Pinned runtime dependencies
├── pyproject.toml          # Package metadata (Python >= 3.12.13)
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
pip install -r requirements.txt
```

**3. Run the app**

```bash
shiny run app.py
```

Then open `http://localhost:8000` in your browser.

---

## Usage

### Step 1 — Prepare the JSON outline

The app expects a JSON file that is a list of objects, each with two keys:

| Key | Type | Description |
|---|---|---|
| `title` | string | Exact heading text as it appears in the PDF |
| `level` | integer | Hierarchy depth (1 = main heading, 2 = sub-heading, …) |

```json
[
    { "title": "1. Introduction", "level": 1 },
    { "title": "1.1 Background",  "level": 2 },
    { "title": "2. Methodology",  "level": 1 }
]
```

See the **"How to Get JSON"** tab in the app for a step-by-step guide on extracting this outline automatically from the Google Scholar PDF reader using a browser console script.

### Step 2 — Upload and process

1. Upload the PDF under **"1. Choose PDF file"**.
2. Upload the JSON outline under **"2. Choose JSON outline file"**.
3. Adjust **"Header / footer exclusion margin"** if needed (default 30 pt works for most web-saved PDFs; increase it if running headers are still matched).
4. Click **"Apply Bookmarks"**.
5. Review the processing log, then click **"Download Bookmarked PDF"**.

---

## How the Search Works

For each heading the app performs two passes per page:

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

- **Scanned / image PDFs** — the script requires selectable text. Run OCR first (e.g. with `ocrmypdf`) if your PDF is image-only.
- **Heavily fragmented text** — some PDF exporters split a single heading across many tiny text spans. If a heading consistently fails to match, try shortening the `title` value in your JSON to the first unambiguous words.

---

## Dependencies

| Package | Purpose |
|---|---|
| `shiny` | Web application framework |
| `pymupdf` | PDF text search and bookmark injection (imported as `fitz`) |
