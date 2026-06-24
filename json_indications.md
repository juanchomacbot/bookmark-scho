# How to Extract a Google Scholar Outline as JSON

This guide explains how to extract the automatically generated outline from a PDF viewed in Google Scholar. The script captures each section's **title**, its heading **level**, and the **page** it lives on, then downloads a ready-to-use `outline.json`. Upload that file to the **Smart PDF Bookmark Injector** web app to bake the bookmarks directly into your local PDF file.

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

## Step 4: Upload the Downloaded File

When the script finishes, your browser downloads a file named **`outline.json`** (check your Downloads folder). It looks like this:

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

Go to the **Tool** tab, upload `outline.json` under **"2. Choose JSON outline file"**, and click **Apply Bookmarks**.
