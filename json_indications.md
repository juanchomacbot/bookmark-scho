# Instructions

The **Smart PDF Bookmark Injector** turns a Google Scholar outline into real,
clickable bookmarks baked into your local PDF. This page walks you through the
whole process, from extracting the outline to downloading the finished PDF.

> 🎬 **Prefer to watch?** A short video demonstration is available here:
> **[youtu.be/9tQK_rzlnx0](https://youtu.be/9tQK_rzlnx0)**

## How it works (the big picture)

The app needs two files: your **PDF** and a **JSON outline** that describes the
section titles, their hierarchy level, and the page each one is on. You get the
JSON from Google Scholar with a one-time browser script (Part A below), then
upload both files here and click **Apply Bookmarks** (Part B). The output is the
same PDF with a proper navigable bookmark tree.

The whole flow is three stages:

1. **Get the outline JSON** from the Google Scholar PDF reader (Part A).
2. **Upload the PDF and the JSON** into the **Tool** tab (Part B).
3. **Apply Bookmarks and download** the bookmarked PDF (Part B).

---

# Part A — Extract the outline as JSON

This extracts the automatically generated outline from a PDF viewed in Google
Scholar. The script captures each section's **title**, its heading **level**, and
the **page** it lives on, then downloads a ready-to-use `outline.json`.

## Step 1: Open the PDF and Developer Tools

1. Open your target PDF in the browser using the Google Scholar PDF reader.
2. Ensure the left-hand sidebar containing the outline is visible.
3. Right-click anywhere on the page and select **Inspect** (or press `Cmd+Option+I` on Mac / `Ctrl+Shift+I` on Windows).
4. Navigate to the **Console** tab at the top of the Developer Tools panel.

## Step 2: Switch the Console Context (Crucial Step)

Google Scholar loads the PDF viewer inside an isolated `iframe` (a window within the main webpage). If you run scripts in the main window, they will fail to find the outline.

1. Look at the top-left corner of the Console tab. You will see a dropdown menu that usually defaults to **`top ▼`**.
2. Click this dropdown.
3. Search for and select the iframe that contains the reader (it is usually named **`reader.html`** or lists the Google Scholar extension).

> **Note:** If you skip this step, the script below will return an empty `[]` array.

## Step 3: Run the Extraction Script

Once your console is in the correct `reader.html` context, copy the following JavaScript code, paste it into the console, and press **Enter**.

The script clicks through every outline entry to read which page each one lands on, so **the reader will visibly scroll through the document for ~30–60 seconds**. Let it finish without clicking anything; when it's done, `outline.json` downloads automatically.

> If Chrome blocks the paste with a warning, type `allow pasting` in the console and press Enter, then paste the script again.

```javascript
(async () => {
  const titles = [...document.querySelectorAll('.gsr-section-title')];
  if (!titles.length) {
    console.warn('No .gsr-section-title found — are you in the reader.html frame?');
    return;
  }

  // The reader's page-number box: the only non-checkbox input holding a plain
  // integer (the zoom box shows e.g. "122%", so it is skipped).
  const pageBox = [...document.querySelectorAll('input')]
    .find(i => i.type !== 'checkbox' && i.type !== 'radio' && /^\d+$/.test(i.value));

  // After clicking a heading, wait until the page box stops changing, then read it.
  const readPage = async () => {
    if (!pageBox) return null;
    let last = null, stable = 0;
    for (let i = 0; i < 40; i++) {
      await new Promise(r => setTimeout(r, 80));
      const v = pageBox.value;
      if (v === last) { if (++stable >= 2) break; } else { last = v; stable = 0; }
    }
    return /^\d+$/.test(last || '') ? parseInt(last, 10) : null;
  };

  const outline = [];
  for (const link of titles) {
    const title = link.innerText.trim();
    if (!title) continue;

    // Depth = how many gsr-subsections wrappers sit above this heading.
    let level = 1, parent = link.parentElement;
    while (parent) {
      if (parent.classList && parent.classList.contains('gsr-subsections')) level++;
      parent = parent.parentElement;
    }

    link.click();                  // navigate the reader to this section
    const page = await readPage();  // its page number lands in the page box
    outline.push(page ? { title, level, page } : { title, level });
  }

  // Download outline.json directly — no copy/paste needed.
  const blob = new Blob([JSON.stringify(outline, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'outline.json';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);

  const withPage = outline.filter(o => o.page).length;
  console.log(`Done: ${outline.length} sections (${withPage} with page). Downloaded outline.json.`);
})();
```

When the script finishes, your browser downloads a file named **`outline.json`**
(check your Downloads folder). It looks like this:

```json
[
    {
        "title": "1. Introduction to the Topic",
        "level": 1,
        "page": 3
    },
    {
        "title": "1.1 Background Context",
        "level": 2,
        "page": 4
    }
]
```

The `page` field tells the app exactly which page each heading is on, so it jumps straight there instead of searching the whole PDF. (If the reader couldn't report a page for some entry, that entry simply omits `page` and the app falls back to searching for it — nothing breaks.)

---

# Part B — Apply the bookmarks in this app

Now switch to the **Tool** tab and use the sidebar on the left:

## Step 4: Upload your two files

1. Under **"1. Choose PDF file"**, select the same PDF you read in Google Scholar.
2. Under **"2. Choose JSON outline file"**, select the `outline.json` you just downloaded.

## Step 5: Adjust the option (optional)

- **Header / footer exclusion margin (pt)** — matches found within this distance
  from the top or bottom edge of each page are ignored, so running headers and
  footers don't get picked up instead of the real heading. The default of **30**
  works for most documents. Increase it if a header/footer is still being matched.

## Step 6: Apply and download

1. Click **Apply Bookmarks**. The **Processing Log** on the right shows each
   heading as it is linked (`✅ Linked: ...`) or reported as not found
   (`❌ Not found ...`), ending with a count of bookmarks applied.
2. Click **Download Bookmarked PDF** to save the result. Open it in any PDF
   reader and the bookmark panel will show your navigable outline.

> **Tip:** If some headings show as "Not found", the title text in the JSON may
> not match the selectable text in the PDF exactly. The app already handles
> common Unicode differences (curly quotes, dashes, ligatures) and falls back to
> the page hint when text can't be matched, so most entries still land correctly.
