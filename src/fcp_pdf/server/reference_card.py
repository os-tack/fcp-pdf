"""Extra reference card sections for PDF help."""

from __future__ import annotations

EXTRA_SECTIONS: dict[str, str] = {
    "Page References": (
        "Pages can be referenced by:\n"
        "  - 1-based number: 1, 2, 3\n"
        "  - Keywords: active, first, last\n"
    ),
    "Page Ranges": (
        "Range formats:\n"
        "  3       — single page\n"
        "  1-5     — pages 1 through 5\n"
        "  1,3,5   — specific pages\n"
        "  1-3,7-9 — mixed ranges\n"
        "  all     — every page\n"
    ),
    "Page Sizes": (
        "Default page size is US Letter (612x792 points = 8.5x11 inches).\n"
        "Common sizes:\n"
        "  Letter:  width:612 height:792\n"
        "  A4:      width:595 height:842\n"
        "  Legal:   width:612 height:1008\n"
        "  Tabloid: width:792 height:1224\n"
    ),
    "Coordinates": (
        "PDF coordinates are in points (1/72 inch), origin at top-left.\n"
        "  72pt  = 1 inch\n"
        "  595pt = A4 width\n"
        "  612pt = Letter width\n"
    ),
    "Fonts": (
        "Built-in PDF fonts (Base14):\n"
        "  helv (Helvetica), times (Times Roman), cour (Courier)\n"
        "  symbol, zapf (ZapfDingbats)\n"
        "Bold/italic variants: helv-bold, helv-oblique, times-bold, etc.\n"
    ),
    "Colors": (
        "Hex format: #FF0000, #00FF00, F0F (3-char shorthand)\n"
        "Default colors by context:\n"
        "  Text: black (#000000)\n"
        "  Highlight: yellow (#FFFF00)\n"
        "  Watermark: light gray (#CCCCCC)\n"
        "  Redaction fill: black (#000000)\n"
    ),
    "Queries": (
        "pdf_query commands:\n"
        "  plan / map       — full document structure overview\n"
        "  status           — quick summary (pages, text, images)\n"
        "  describe N       — detailed view of page N\n"
        "  find TEXT         — search text across all pages\n"
        "  toc / bookmarks  — table of contents\n"
        "  fonts [N]        — list fonts (optionally for page N)\n"
        "  annots           — list all annotations\n"
    ),
    "Response Prefixes": (
        "+ created  * modified  - removed  ! info/error  @ bulk\n"
    ),
    "Compose (Layout Engine)": (
        "The compose verb accumulates structured content into a buffer,\n"
        "then renders it with automatic text reflow and pagination.\n"
        "\n"
        "Content blocks:\n"
        "  heading    — H1-H4, auto-numbered with numbering:on\n"
        "  paragraph  — reflowed text with **bold**, *italic*, `code`, ~~strike~~\n"
        "  table/row  — tables with themed headers (compose table → compose row)\n"
        "  list       — bullet list from positional args\n"
        "  ordered-list — numbered list\n"
        "  cover      — title page with subtitle, author, date\n"
        "  callout    — info/warning/success/error alert boxes\n"
        "  badge      — inline colored label\n"
        "  highlight  — accent-background text block\n"
        "  blockquote — indented styled quote\n"
        "  code       — monospace code block\n"
        "  image      — embedded image with optional caption\n"
        "  columns    — side-by-side column layout\n"
        "  toc        — auto-generate table of contents from headings\n"
        "  rule       — horizontal divider\n"
        "  spacer     — vertical whitespace\n"
        "  pagebreak  — force new page\n"
        "  raw        — inject raw HTML\n"
        "\n"
        "Config:\n"
        "  paper:letter|a4|legal  margin:72  font:Helvetica  size:11\n"
        "  theme:corporate|modern|minimal|executive|ocean\n"
        "  numbering:on  header:\"Title\"  footer:\"Page {page}\"\n"
        "\n"
        "Lifecycle: compose config → compose content → compose render\n"
        "Render auto-generates PDF bookmarks from headings.\n"
    ),
    "Themes": (
        "Named color themes coordinate all visual elements:\n"
        "  corporate  — dark navy headings, professional tables\n"
        "  modern     — indigo accents, clean lines\n"
        "  minimal    — grayscale, understated\n"
        "  executive  — slate + red accents, boardroom ready\n"
        "  ocean      — blue palette, fresh and open\n"
        "\n"
        "Each theme sets: heading/body colors, table header bg/fg,\n"
        "callout colors (info/warning/success/error), accent tints,\n"
        "blockquote/code/rule colors.\n"
        "\n"
        "Set via: compose config theme:modern\n"
    ),
    "Example Workflow": (
        "  # Open an existing PDF\n"
        "  pdf_session('open ./report.pdf')\n"
        "  pdf_query('plan')  # see structure\n"
        "  pdf_query('find revenue')  # search\n"
        "  pdf(['text extract pages:1-3'])  # read content\n"
        "\n"
        "  # Create a new PDF\n"
        "  pdf_session('new \"Invoice\"')\n"
        "  pdf([\n"
        "    'page add',\n"
        '    \'insert-text "INVOICE" x:72 y:72 size:24 font:helv\',\n'
        '    \'insert-text "Date: 2024-01-15" x:72 y:110 size:12\',\n'
        "  ])\n"
        "\n"
        "  # Annotate and redact\n"
        "  pdf(['annotate highlight text:\"confidential\"'])\n"
        "  pdf(['redact \"SSN: 123-45-6789\" fill:#000'])\n"
        "\n"
        "  # Merge and split\n"
        "  pdf(['merge ./appendix.pdf'])\n"
        "  pdf(['split ./pages_1_5.pdf pages:1-5'])\n"
        "\n"
        "  # Watermark and save\n"
        "  pdf(['watermark \"DRAFT\" opacity:0.2 angle:45'])\n"
        "  pdf_session('save as:./final.pdf')\n"
        "\n"
        "  # --- Compose: build a complex document ---\n"
        "  pdf_session('new \"Q4 Report\"')\n"
        "  pdf([\n"
        '    \'compose config paper:letter margin:72 font:Helvetica footer:"Page {page} of {pages}"\',\n'
        '    \'compose heading "Q4 Revenue Report" level:1\',\n'
        "    'compose paragraph \"Revenue grew 38% YoY driven by **enterprise expansion** and *new market entry*.\"',\n"
        "    'compose spacer height:8',\n"
        '    \'compose table "Metric" "Q3" "Q4" "Delta"\',\n'
        '    \'compose row "Revenue" "$1.3M" "$1.8M" "+38%"\',\n'
        '    \'compose row "Customers" "142" "198" "+39%"\',\n'
        '    \'compose row "NPS" "72" "81" "+9"\',\n'
        "    'compose heading \"Key Highlights\" level:2',\n"
        "    'compose list \"Enterprise ARR crossed $1M\" \"Launched APAC region\" \"Net retention at 128%\"',\n"
        "    'compose pagebreak',\n"
        "    'compose heading \"Appendix\" level:2',\n"
        "    'compose paragraph \"Detailed metrics available in the data warehouse.\"',\n"
        "    'compose render',\n"
        "  ])\n"
        "  pdf_session('save as:./q4_report.pdf')\n"
    ),
}
