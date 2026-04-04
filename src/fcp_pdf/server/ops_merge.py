"""Merge and split operation handlers."""

from __future__ import annotations

import os

import fitz

from fcp_core import OpResult, ParsedOp

from fcp_pdf.server.resolvers import PdfOpContext, parse_page_range


def op_merge(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Merge another PDF into the current document.

    Syntax:
      merge PATH [at:N] [pages:RANGE]
    """
    if not op.positionals:
        return OpResult(success=False, message="Usage: merge PATH [at:N] [pages:RANGE]")

    path = op.positionals[0]

    if not os.path.isabs(path):
        # Resolve relative to the current doc's directory or cwd
        base = os.path.dirname(ctx.model.file_path) if ctx.model.file_path else os.getcwd()
        path = os.path.join(base, path)

    if not os.path.isfile(path):
        return OpResult(success=False, message=f"File not found: {path!r}")

    try:
        src_doc = fitz.open(path)
    except Exception as e:
        return OpResult(success=False, message=f"Failed to open {path!r}: {e}")

    # Determine which pages from the source
    pages_spec = op.params.get("pages")
    if pages_spec:
        src_pages = parse_page_range(pages_spec, len(src_doc))
        if src_pages is None:
            src_doc.close()
            return OpResult(success=False, message=f"Invalid page range: {pages_spec!r}")
    else:
        src_pages = list(range(len(src_doc)))

    # Determine insertion point
    at_ref = op.params.get("at")
    if at_ref:
        try:
            at_page = int(at_ref) - 1
        except ValueError:
            src_doc.close()
            return OpResult(success=False, message=f"Invalid insertion point: {at_ref!r}")
        start_at = at_page
    else:
        start_at = -1  # append

    # Insert pages
    ctx.doc.insert_pdf(
        src_doc,
        from_page=min(src_pages),
        to_page=max(src_pages),
        start_at=start_at,
    )

    page_count = len(src_pages)
    src_doc.close()

    return OpResult(
        success=True,
        message=f"Merged {page_count} page(s) from {os.path.basename(path)}",
        prefix="+",
    )


def op_split(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Extract page range to a new PDF file.

    Syntax:
      split PATH [pages:RANGE]
    """
    if not op.positionals:
        return OpResult(success=False, message="Usage: split PATH [pages:RANGE]")

    path = op.positionals[0]

    if not os.path.isabs(path):
        base = os.path.dirname(ctx.model.file_path) if ctx.model.file_path else os.getcwd()
        path = os.path.join(base, path)

    # Determine pages
    pages_spec = op.params.get("pages")
    if not pages_spec:
        return OpResult(success=False, message="Usage: split PATH pages:RANGE (e.g. pages:1-5)")

    indices = parse_page_range(pages_spec, len(ctx.doc))
    if indices is None:
        return OpResult(success=False, message=f"Invalid page range: {pages_spec!r}")

    # Create new document with selected pages
    new_doc = fitz.open()
    for idx in indices:
        new_doc.insert_pdf(ctx.doc, from_page=idx, to_page=idx)

    new_doc.save(path)
    page_count = len(indices)
    new_doc.close()

    return OpResult(
        success=True,
        message=f"Split {page_count} page(s) to {os.path.basename(path)}",
        prefix="+",
    )


HANDLERS: dict[str, callable] = {
    "merge": op_merge,
    "split": op_split,
}
