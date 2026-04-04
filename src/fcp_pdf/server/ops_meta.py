"""Metadata operation handlers — get/set document metadata."""

from __future__ import annotations

from fcp_core import OpResult, ParsedOp

from fcp_pdf.server.resolvers import PdfOpContext


def op_meta(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Get or set document metadata.

    Syntax:
      meta get
      meta set [title:TEXT] [author:TEXT] [subject:TEXT] [keywords:TEXT] [creator:TEXT] [producer:TEXT]
    """
    if not op.positionals:
        return OpResult(success=False, message="Usage: meta get|set [title:TEXT] [author:TEXT] ...")

    action = op.positionals[0].lower()

    if action == "get":
        return _meta_get(ctx)
    elif action == "set":
        return _meta_set(op, ctx)
    else:
        return OpResult(success=False, message=f"Unknown meta action: {action!r}. Use: get, set")


def _meta_get(ctx: PdfOpContext) -> OpResult:
    """Display document metadata."""
    meta = ctx.doc.metadata

    lines: list[str] = []
    field_map = [
        ("Title", "title"),
        ("Author", "author"),
        ("Subject", "subject"),
        ("Keywords", "keywords"),
        ("Creator", "creator"),
        ("Producer", "producer"),
        ("Created", "creationDate"),
        ("Modified", "modDate"),
        ("Format", "format"),
        ("Encryption", "encryption"),
    ]

    for label, key in field_map:
        val = meta.get(key, "")
        if val:
            lines.append(f"  {label}: {val}")

    if not lines:
        return OpResult(success=True, message="No metadata set", prefix="!")

    return OpResult(success=True, message="\n".join(lines), prefix="!")


def _meta_set(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Set document metadata fields."""
    meta = ctx.doc.metadata.copy()

    settable = ["title", "author", "subject", "keywords", "creator", "producer"]
    updated: list[str] = []

    for field in settable:
        if field in op.params:
            meta[field] = op.params[field]
            updated.append(field)

    if not updated:
        return OpResult(
            success=False,
            message="No metadata fields specified. Use: title, author, subject, keywords, creator, producer",
        )

    ctx.doc.set_metadata(meta)

    # Also update model title if title was set
    if "title" in op.params:
        ctx.model.title = op.params["title"]

    return OpResult(
        success=True,
        message=f"Metadata updated: {', '.join(updated)}",
        prefix="*",
    )


HANDLERS: dict[str, callable] = {
    "meta": op_meta,
}
