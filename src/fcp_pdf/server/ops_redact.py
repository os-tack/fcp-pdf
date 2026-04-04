"""Redaction operation handler — permanently remove text from PDFs."""

from __future__ import annotations

import fitz

from fcp_core import OpResult, ParsedOp

from fcp_pdf.server.resolvers import (
    PdfOpContext,
    parse_color,
    parse_page_range,
    require_active_page,
    resolve_page_idx,
)


def op_redact(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Redact (permanently remove) text from pages.

    This is a destructive operation — redacted text is irrecoverably removed
    from the PDF. The redacted area is filled with a solid color (default black).

    Syntax:
      redact "TEXT" [on:PAGE] [pages:RANGE] [fill:#HEX]
    """
    if not op.positionals:
        return OpResult(success=False, message='Usage: redact "TEXT" [on:PAGE] [pages:RANGE] [fill:#HEX]')

    search_text = op.positionals[0]

    fill_color = (0, 0, 0)  # black default
    if "fill" in op.params:
        try:
            fill_color = parse_color(op.params["fill"])
        except ValueError as e:
            return OpResult(success=False, message=str(e))

    # Determine pages
    pages_spec = op.params.get("pages")
    on_ref = op.params.get("on")

    if pages_spec:
        indices = parse_page_range(pages_spec, len(ctx.doc))
        if indices is None:
            return OpResult(success=False, message=f"Invalid page range: {pages_spec!r}")
    elif on_ref:
        idx = resolve_page_idx(on_ref, ctx)
        if idx is None:
            return OpResult(success=False, message=f"Page not found: {on_ref!r}")
        indices = [idx]
    else:
        active = require_active_page(ctx)
        if isinstance(active, str):
            return OpResult(success=False, message=active)
        _, idx = active
        indices = [idx]

    total_redactions = 0
    for idx in indices:
        page = ctx.doc[idx]

        # Search for all instances of the text
        instances = page.search_for(search_text)
        if not instances:
            continue

        for rect in instances:
            page.add_redact_annot(rect, fill=fill_color)
            total_redactions += 1

        # Apply redactions — this permanently removes the content
        page.apply_redactions()

    if total_redactions == 0:
        return OpResult(
            success=False,
            message=f"Text not found: {search_text!r}",
        )

    return OpResult(
        success=True,
        message=f"Redacted {total_redactions} instance(s) of {search_text!r} across {len(indices)} page(s)",
        prefix="-",
    )


HANDLERS: dict[str, callable] = {
    "redact": op_redact,
}
