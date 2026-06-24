import json
import re
import tempfile
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF
from shiny import App, reactive, render, ui

# Read instructions once at startup so the UI stays static
_INSTRUCTIONS_MD = Path("json_indications.md").read_text(encoding="utf-8")

# --- UI Definition ---
app_ui = ui.page_fluid(
    ui.panel_title("Smart PDF Bookmark Injector"),
    ui.navset_tab(
        ui.nav_panel(
            "Tool",
            ui.layout_sidebar(
                ui.sidebar(
            ui.h5("Upload Files"),
            ui.input_file(
                "pdf_file",
                "1. Choose PDF file",
                accept=[".pdf"],
            ),
            ui.input_file(
                "json_file",
                "2. Choose JSON outline file",
                accept=[".json", ".JSON"],
            ),
            ui.markdown(
                "_JSON must be a list of objects with `title` (string) and `level` (integer) keys._"
            ),
            ui.hr(),
            ui.h5("Options"),
            ui.input_numeric(
                "margin_pt",
                "Header / footer exclusion margin (pt)",
                value=30,
                min=0,
                max=200,
                step=5,
            ),
            ui.markdown(
                "_Matches within this distance from the top or bottom edge of each "
                "page are ignored. Increase if running headers/footers are still "
                "being picked up._"
            ),
            ui.hr(),
            ui.input_action_button(
                "process_btn",
                "Apply Bookmarks",
                class_="btn-primary w-100",
            ),
            ui.hr(),
            ui.download_button(
                "download_btn",
                "Download Bookmarked PDF",
                class_="btn-success w-100",
            ),
                    width=320,
                ),
                ui.card(
                    ui.card_header("Processing Log"),
                    ui.output_text_verbatim("log_output", placeholder=True),
                ),
            ),
        ),
        ui.nav_panel(
            "How to Get JSON",
            ui.card(
                ui.card_body(ui.markdown(_INSTRUCTIONS_MD)),
            ),
        ),
    ),
)


# --- Server Logic ---
def server(input, output, session):
    _result_path: reactive.Value[Path | None] = reactive.Value(None)
    _log_messages: reactive.Value[list[str]] = reactive.Value([])

    @reactive.effect
    @reactive.event(input.process_btn)
    def _on_process():
        pdf_info = input.pdf_file()
        json_info = input.json_file()

        if not pdf_info:
            _log_messages.set(["❌ Error: Please upload a PDF file."])
            _result_path.set(None)
            return

        if not json_info:
            _log_messages.set(["❌ Error: Please upload a JSON outline file."])
            _result_path.set(None)
            return

        try:
            with open(json_info[0]["datapath"]) as f:
                outline_data = json.load(f)
        except json.JSONDecodeError as exc:
            _log_messages.set([f"❌ JSON parse error: {exc}"])
            _result_path.set(None)
            return

        if not isinstance(outline_data, list):
            _log_messages.set(
                ["❌ Error: JSON must be an array of objects with 'title' and 'level' keys."]
            )
            _result_path.set(None)
            return

        margin_pt = float(input.margin_pt() or 0)
        output_file = Path(tempfile.mktemp(suffix=".pdf"))
        messages, success = _apply_smart_bookmarks(
            pdf_info[0]["datapath"], str(output_file), outline_data, margin_pt
        )

        _log_messages.set(messages)
        _result_path.set(output_file if success else None)

    @output
    @render.text
    def log_output() -> str:
        msgs = _log_messages.get()
        if not msgs:
            return "Upload a PDF and a JSON outline file, then click 'Apply Bookmarks'."
        return "\n".join(msgs)

    @render.download(filename="bookmarked_output.pdf")
    def download_btn():
        path = _result_path.get()
        if path is None or not path.exists():
            return
        with open(path, "rb") as f:
            yield f.read()


# --- Text Normalization ---

# All Unicode codepoints that should map to a plain ASCII apostrophe.
# Using explicit sets avoids source-file encoding ambiguity (e.g. U+2019 vs
# U+02BC look identical in many editors but behave differently in regexes).
_APOSTROPHES: frozenset[str] = frozenset(
    "'"  # APOSTROPHE (straight)
    "`"  # GRAVE ACCENT
    "´"  # ACUTE ACCENT
    "ʹ"  # MODIFIER LETTER PRIME
    "ʻ"  # MODIFIER LETTER TURNED COMMA
    "ʼ"  # MODIFIER LETTER APOSTROPHE  (ʼ – used in JSON)
    "ʽ"  # MODIFIER LETTER REVERSED COMMA
    "ˈ"  # MODIFIER LETTER VERTICAL LINE
    "‘"  # LEFT SINGLE QUOTATION MARK
    "’"  # RIGHT SINGLE QUOTATION MARK  ('' – used in PDF)
    "‚"  # SINGLE LOW-9 QUOTATION MARK
    "‛"  # SINGLE HIGH-REVERSED-9 QUOTATION MARK
    "′"  # PRIME
    "‵"  # REVERSED PRIME
    "＇"  # FULLWIDTH APOSTROPHE
)

_DASHES: frozenset[str] = frozenset(
    "‐"  # HYPHEN
    "‑"  # NON-BREAKING HYPHEN
    "‒"  # FIGURE DASH
    "–"  # EN DASH
    "—"  # EM DASH
    "―"  # HORIZONTAL BAR
    "−"  # MINUS SIGN
    "﹘"  # SMALL EM DASH
    "﹣"  # SMALL HYPHEN-MINUS
    "－"  # FULLWIDTH HYPHEN-MINUS
)


def _normalize(text: str) -> str:
    """
    Flatten text for fuzzy comparison: Unicode decomposition, explicit
    punctuation substitution via codepoint sets, diacritic removal,
    collapsed whitespace, lowercase. Used only for matching — never written
    to the output.
    """
    # Compatibility decomposition expands ligatures, superscripts, etc.
    text = unicodedata.normalize("NFKD", text)
    # Drop combining diacritical marks left by NFKD
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Unify all apostrophe/single-quote variants to straight apostrophe
    text = "".join("'" if c in _APOSTROPHES else c for c in text)
    # Unify all dash/hyphen variants to ASCII hyphen
    text = "".join("-" if c in _DASHES else c for c in text)
    return re.sub(r"\s+", " ", text).strip().lower()


# --- Core Processing Functions ---
def _search_page(page, search_query: str, margin_pt: float) -> float | None:
    """
    Return the y0 coordinate of the best match on the page, or None.
    Matches within margin_pt of the top or bottom edge are ignored so that
    running headers and footers never win over real section headings.

    Pass 1 — exact PyMuPDF search.
    Pass 2 — normalized block-text fallback for Unicode mismatches.
    """
    page_height = page.rect.height

    def _in_content_zone(y0: float) -> bool:
        return margin_pt < y0 < (page_height - margin_pt)

    # Pass 1: fast native search; keep only hits inside the content zone
    for inst in page.search_for(search_query):
        if _in_content_zone(inst.y0):
            return inst.y0

    # Pass 2: per-block normalized comparison, same zone filter
    # get_text("blocks") → (x0, y0, x1, y1, text, block_no, block_type)
    norm_query = _normalize(search_query)
    for block in page.get_text("blocks"):
        if block[6] != 0:  # skip image/non-text blocks
            continue
        if _in_content_zone(block[1]) and norm_query in _normalize(block[4]):
            return block[1]

    return None


def _apply_smart_bookmarks(
    input_pdf: str,
    output_pdf: str,
    outline_data: list[dict],
    margin_pt: float = 30.0,
) -> tuple[list[str], bool]:
    """
    Search each heading in outline_data within the PDF, build a bookmark list
    with exact page + Y-coordinate destinations, and save to output_pdf.
    Returns (log_messages, success).
    """
    messages: list[str] = []
    toc: list = []

    try:
        doc = fitz.open(input_pdf)

        for item in outline_data:
            title: str = item.get("title", "")
            level: int = item.get("level", 1)

            if not title:
                messages.append("⚠️  Skipped: an item is missing the 'title' key.")
                continue

            # Truncate to 35 chars so long titles that wrap across lines still match
            search_query = title[:35]
            matches: list[dict] = []

            for page_num in range(len(doc)):
                y = _search_page(doc[page_num], search_query, margin_pt)
                if y is not None:
                    matches.append({"page": page_num + 1, "y": y})

            if matches:
                # Last occurrence skips any printed Table-of-Contents entries
                best = matches[-1]
                toc.append([
                    level,
                    title,
                    best["page"],
                    {"kind": fitz.LINK_GOTO, "to": fitz.Point(0, best["y"])},
                ])
                messages.append(f"✅ Linked: '{search_query}...' → Page {best['page']}")
            else:
                messages.append(f"❌ Not found in PDF: '{title}'")

        doc.set_toc(toc)
        doc.save(output_pdf)
        doc.close()
        messages.append(f"\n✅ Done — {len(toc)} bookmark(s) applied.")
        return messages, True

    except Exception as exc:  # noqa: BLE001
        messages.append(f"❌ Fatal error: {exc}")
        return messages, False


app = App(app_ui, server)
