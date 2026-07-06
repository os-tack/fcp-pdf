# fcp-pdf

MCP server for semantic PDF operations.

## What It Does

fcp-pdf lets LLMs read, edit, and generate PDF files by describing document intent -- pages, text, annotations, bookmarks, watermarks, redactions -- instead of driving a low-level PDF library call by call. It exposes 13 verbs (`page`, `text`, `insert-text`, `annotate`, `bookmark`, `merge`, `split`, `meta`, `watermark`, `image`, `redact`, `link`, plus `compose`) and renders them into standard `.pdf` files. Built on the [FCP](https://github.com/os-tack/fcp) framework, powered by [PyMuPDF](https://pymupdf.readthedocs.io/) (`fitz`) for serialization.

The `compose` verb is a small document-generation sub-DSL: it accumulates structured content (headings, paragraphs, tables, lists, callouts, cover pages, columns) into a buffer, then `compose render` paginates it with text reflow, page breaks, headers/footers, and auto-generated bookmarks, using one of five built-in themes (`corporate`, `modern`, `minimal`, `executive`, `ocean`).

## Quick Example

```
pdf_session('new "Invoice"')

pdf([
    'page add',
    'insert-text "INVOICE" x:72 y:72 size:24 font:helv-bold',
    'insert-text "Date: 2026-01-15" x:72 y:110 size:12',
    'annotate rect on:1 x:60 y:60 w:475 h:70 color:#1a1a2e',
    'bookmark add "Invoice" page:1',
])

pdf_session('save as:./invoice.pdf')
```

Or generate a themed multi-page report with `compose`:

```
pdf_session('new "Q4 Report"')

pdf([
    'compose config paper:letter theme:modern footer:"Page {page} of {pages}"',
    'compose heading "Q4 Revenue Report" level:1',
    'compose paragraph "Revenue grew 38% YoY driven by **enterprise expansion**."',
    'compose table "Metric" "Q3" "Q4" "Delta"',
    'compose row "Revenue" "$1.3M" "$1.8M" "+38%"',
    'compose list "Enterprise ARR crossed $1M" "Launched APAC region"',
    'compose render',
])

pdf_session('save as:./q4_report.pdf')
```

### Available MCP Tools

| Tool | Purpose |
|------|---------|
| `pdf(ops)` | Batch mutations -- pages, text, annotations, bookmarks, merges, watermarks, images, redaction, links, compose |
| `pdf_query(q)` | Inspect the document -- structure (`plan`/`status`), page detail (`describe`), full-text search (`find`), `toc`, `fonts`, `annots` |
| `pdf_session(action)` | Lifecycle -- new, open, save, checkpoint, undo, redo |
| `pdf_help()` | Full reference card |

## Installation

Requires Python >= 3.11.

```bash
pip install fcp-pdf
```

### MCP Client Configuration

```json
{
  "mcpServers": {
    "pdf": {
      "command": "uv",
      "args": ["run", "python", "-m", "fcp_pdf"]
    }
  }
}
```

## Architecture

3-layer architecture:

```
MCP Server (Intent Layer)
  Parses op strings, dispatches to verb handlers
        |
Semantic Model
  PdfModel wraps a fitz.Document, byte-snapshot undo/redo
        |
Serialization (PyMuPDF / fitz)
  Semantic model -> .pdf binary output
```

Key features:

- **Pages** -- add, remove, move, rotate, copy, activate
- **Text** -- extraction (plain/blocks/dict) and free-form insertion
- **Annotations** -- highlight, underline, strikeout, sticky notes, shapes
- **Bookmarks** -- table of contents management
- **Merge / split** -- combine or extract page ranges across documents
- **Metadata** -- title, author, subject, keywords, creator, producer
- **Watermarks** -- rotated, opacity-controlled text overlays
- **Images** -- insert, extract, list
- **Redaction** -- permanently remove text from pages
- **Links** -- hyperlinks and internal page links
- **Compose** -- themed document layout engine with automatic pagination and bookmarks
- **Undo/redo** -- full document snapshots with event sourcing

## Development

```bash
uv sync --dev        # install deps
uv run pytest        # run tests
uv run fcp-pdf        # start MCP server
```

## License

MIT
