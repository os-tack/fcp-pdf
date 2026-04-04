# fcp-pdf

PDF driver for the File Context Protocol (FCP). Provides semantic PDF operations as an MCP server.

## Architecture

- `src/fcp_pdf/main.py` — MCP server entry point via `create_fcp_server()`
- `src/fcp_pdf/adapter.py` — `PdfAdapter` implementing `FcpDomainAdapter` protocol
- `src/fcp_pdf/model/snapshot.py` — `PdfModel` wrapper around `fitz.Document` with byte-snapshot undo/redo
- `src/fcp_pdf/server/ops_*.py` — verb handlers (pages, text, annotate, bookmark, merge, meta, watermark, image, redact, link)
- `src/fcp_pdf/server/queries.py` — read-only query handlers (plan, status, describe, find, toc, fonts, annots)
- `src/fcp_pdf/server/resolvers.py` — page resolution, range parsing, color parsing
- `src/fcp_pdf/server/verb_registry.py` — verb specs for all operations
- `src/fcp_pdf/server/reference_card.py` — help content

## Key dependencies

- **PyMuPDF** (`pymupdf`/`fitz`) — PDF engine
- **fcp-core** — shared FCP server framework
- **fastmcp** — MCP server transport

## Commands

```bash
uv sync --dev        # install deps
uv run pytest        # run tests
uv run fcp-pdf       # start MCP server
```

## MCP tools exposed

- `pdf(ops)` — execute operations (page, text, insert-text, annotate, bookmark, merge, split, meta, watermark, image, redact, link)
- `pdf_query(q)` — query document state (plan, status, describe, find, toc, fonts, annots)
- `pdf_session(action)` — session lifecycle (new, open, save, checkpoint, undo, redo)
- `pdf_help()` — reference card
