"""fcp-pdf — PDF File Context Protocol MCP server."""

from __future__ import annotations

from fcp_core.server import create_fcp_server

from fcp_pdf.adapter import PdfAdapter
from fcp_pdf.server.reference_card import EXTRA_SECTIONS
from fcp_pdf.server.verb_registry import VERBS

adapter = PdfAdapter()

mcp = create_fcp_server(
    domain="pdf",
    adapter=adapter,
    verbs=VERBS,
    extra_sections=EXTRA_SECTIONS,
    extensions=["pdf"],
    name="fcp-pdf",
    instructions=(
        "FCP PDF server for reading, manipulating, and creating PDF files. "
        "Use pdf_session to open an existing PDF or create a new one, "
        "pdf to execute operations (page, text, annotate, bookmark, merge, split, meta, watermark, image, redact), "
        "pdf_query to inspect document structure and search content, "
        "and pdf_help for the full verb reference. "
        "Start every interaction with pdf_session."
    ),
)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
