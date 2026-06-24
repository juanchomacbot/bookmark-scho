# Plan: Smarter Scholar extraction — capture page number + auto-download JSON

## Context

Today the workflow has two friction points:

1. **Lossy hand-off.** The console script only emits `{title, level}`. The Python app
   (`app.py`) then re-discovers *where* each heading lives by fuzzy-searching the entire
   PDF for the title text — an expensive, error-prone step guarded by the "last
   occurrence" + margin heuristics (`_apply_smart_bookmarks`, `_search_page`). The
   Scholar reader already knows which page each section is on; we throw that away.
2. **Manual JSON file.** The user must highlight console output, copy it, paste into an
   editor, and save a `.json` by hand (`json_indications.md` Steps 3–4).

Goal: have the console script (a) capture the **page number** of each heading and
(b) **download** the JSON directly. Python then uses the page to scope its Y-search to
the correct page instead of guessing across all pages. Per the user's decisions:
**page-number precision is enough** (Python still finds the exact Y line within that
page), and we settle the exact DOM source via a **diagnostic round-trip first**.

The Scholar reader is a pdf.js-based Chrome extension; `.gsr-section-title` are the
clickable sidebar headings. Their text already matches real PDF text (that's why the
current search works). We need to learn what page-destination data those elements carry.

## Step 0 — Branch

Create and switch to a feature branch off `main` (e.g. `feature/scholar-page-capture`)
before any edits. All work lands there; `main` stays untouched. No commits/pushes unless
the user asks.

## Step 1 — Diagnostic snippet (run first, drives Step 2)

Before writing final extraction code, have the user run this in the **`reader.html`**
console context and paste back the output. It reveals where (if anywhere) the page
destination is stored, so Step 2 targets the real attribute instead of guessing.

```javascript
const els = document.querySelectorAll('.gsr-section-title');
console.log('count:', els.length, '| PDFViewerApplication:', typeof window.PDFViewerApplication);
console.log('rendered pages:', document.querySelectorAll('.page[data-page-number]').length);
[...els].slice(0, 3).forEach((el, i) => {
  console.log(`\n--- #${i}: ${el.innerText.trim().slice(0, 60)} ---`);
  console.log('tag/class:', el.tagName, el.className);
  console.log('attrs:', [...el.attributes].map(a => `${a.name}=${a.value}`));
  console.log('dataset:', JSON.stringify(el.dataset));
  console.log('href:', el.getAttribute('href'), '| closest a:', el.closest('a')?.getAttribute('href'));
  console.log('own props:', Object.getOwnPropertyNames(el).filter(k => !(k in HTMLElement.prototype)));
  let p = el.parentElement, d = 0;
  while (p && d < 5) { if (Object.keys(p.dataset || {}).length) console.log('ancestor', d, 'dataset:', JSON.stringify(p.dataset)); p = p.parentElement; d++; }
});
```

**Branch on what it shows:**
- **Static destination found** (a `data-*`, an `href="#page=N"`, or an attached pdf.js
  dest object) → read the page directly per element. Preferred: no side effects.
- **Nothing static, but `window.PDFViewerApplication` exists** → fallback method:
  programmatically `click()` each section title, `await` a short delay, read
  `PDFViewerApplication.pdfViewer.currentPageNumber`, record it, restore scroll. Authoritative
  (uses Scholar's own navigation) but async and scrolls the doc.
- **Neither** → emit `{title, level}` only (page omitted); Python keeps current behavior.
  No regression.

## Step 2 — New extraction + auto-download script (`json_indications.md`)

Replace the script block (currently `json_indications.md` lines 26–49). Keep the existing
`level`-by-counting-`gsr-subsections` logic. Add, per the Step-1 branch, a 1-based `page`
field (omit it when unavailable). Then **download instead of `console.log`**:

```javascript
const blob = new Blob([JSON.stringify(outlineData, null, 2)], { type: 'application/json' });
const a = document.createElement('a');
a.href = URL.createObjectURL(blob);
a.download = 'outline.json';
document.body.appendChild(a); a.click(); a.remove();
URL.revokeObjectURL(a.href);
console.log(`Downloaded outline.json with ${outlineData.length} sections.`);
```

Output shape becomes `{ "title": "...", "level": 1, "page": 5 }` (`page` optional). The
1-based page matches Python's existing `page_num + 1` convention.

## Step 3 — Use the page number in `app.py`

In `_apply_smart_bookmarks` (the per-item loop, `app.py:246–274`):
- Read optional `page = item.get("page")`.
- **If `page` is a valid int in range:** call `_search_page(doc[page-1], search_query, margin_pt)`
  on that one page. If it returns a Y, use `(page, y)`. If it returns `None` (heading text
  mismatch), still bookmark that page near its top (e.g. `y = margin_pt`) so the link lands
  on the correct page — a strict improvement over a wrong-page guess.
- **If `page` is absent/invalid:** keep the current full-document scan + `matches[-1]`
  heuristic exactly as-is (backward compatible with old `{title, level}` JSON).

`_search_page` (`app.py:198`) is reused unchanged. Add a short log line distinguishing
"Linked via page N (from outline)" vs the legacy "searched" path so the user can see the
new fast path working. No change to `doc.set_toc` / TOC tuple construction.

## Step 4 — Docs & UI copy

- **`json_indications.md`:** update Steps 3–4 — the script now *downloads* `outline.json`,
  so replace the copy/highlight/save instructions with "a file named `outline.json`
  downloads automatically; upload it in the Tool tab." Update the sample JSON to include
  `page`.
- **`app.py` sidebar hint** (`app.py:32–34`) and **`CLAUDE.md`** JSON-format section:
  document the new optional `page` key (integer, 1-based) and that it lets the app skip the
  cross-page search.

## Critical files
- `json_indications.md` — diagnostic snippet, new extraction + download script, Steps 3–4, sample.
- `app.py` — `_apply_smart_bookmarks` page-aware branch (`:246–274`); sidebar hint (`:32–34`).
- `CLAUDE.md` — JSON input format note.

## Verification
1. **Diagnostic:** user runs Step-1 snippet in the `reader.html` console; confirm which
   branch applies from the pasted output.
2. **Download:** run the final script; confirm `outline.json` downloads and contains
   `page` values that match where headings actually appear in the reader.
3. **App, new path:** `shiny run app.py`; upload the PDF + new JSON; confirm log shows
   "via page N" lines and bookmarks jump to the correct pages — including a heading whose
   text Scholar paraphrased (should still land on the right page via the top-of-page
   fallback).
4. **Backward compat:** upload an old `{title, level}` JSON; confirm the legacy
   full-search path still works unchanged.
