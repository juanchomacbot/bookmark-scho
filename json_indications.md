# How to Extract a Google Scholar Outline as JSON

This guide explains how to extract the automatically generated outline from a PDF viewed in Google Scholar. The extracted JSON data can then be uploaded to the **Smart PDF Bookmark Injector** web app to bake the bookmarks directly into your local PDF file.

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

```javascript
let outlineData = [];

document.querySelectorAll('.gsr-section-title').forEach(link => {
    let title = link.innerText.trim();
    if (!title) return;
    
    // Calculate if it is an H1, H2, etc., by counting its parent subsections
    let level = 1;
    let parent = link.parentElement;
    while (parent) {
        if (parent.classList && parent.classList.contains('gsr-subsections')) {
            level++;
        }
        parent = parent.parentElement;
    }
    
    outlineData.push({ title: title, level: level });
});

console.log("Extraction successful! Copy the JSON array below:\n\n");
console.log(JSON.stringify(outlineData, null, 4));

```

## Step 4: Copy the JSON Output

The console will instantly print a beautifully formatted JSON array that looks like this:

```json
[
    {
        "title": "1. Introduction to the Topic",
        "level": 1
    },
    {
        "title": "1.1 Background Context",
        "level": 2
    }
]

```

Highlight the entire array (including the opening `[` and closing `]`), then save it to a `.json` file. Upload that file in the **Tool** tab under **"2. Choose JSON outline file"** and click **Apply Bookmarks**.