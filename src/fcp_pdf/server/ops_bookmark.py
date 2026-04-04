"""Bookmark / TOC operation handlers."""

from __future__ import annotations

from fcp_core import OpResult, ParsedOp

from fcp_pdf.server.resolvers import PdfOpContext


def op_bookmark(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Manage document bookmarks (table of contents).

    Syntax:
      bookmark add TITLE [page:N] [level:N]
      bookmark remove TITLE
      bookmark list
    """
    if not op.positionals:
        return OpResult(success=False, message="Usage: bookmark add|remove|list [TITLE] [page:N] [level:N]")

    action = op.positionals[0].lower()

    if action == "list":
        return _bookmark_list(ctx)
    elif action == "add":
        return _bookmark_add(op, ctx)
    elif action == "remove":
        return _bookmark_remove(op, ctx)
    else:
        return OpResult(success=False, message=f"Unknown bookmark action: {action!r}. Use: add, remove, list")


def _bookmark_list(ctx: PdfOpContext) -> OpResult:
    """List all bookmarks."""
    toc = ctx.doc.get_toc()
    if not toc:
        return OpResult(success=True, message="No bookmarks", prefix="!")

    lines: list[str] = []
    for level, title, page in toc:
        indent = "  " * (level - 1)
        lines.append(f"{indent}{title} → page {page}")

    return OpResult(success=True, message="\n".join(lines), prefix="!")


def _bookmark_add(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Add a bookmark entry."""
    if len(op.positionals) < 2:
        return OpResult(success=False, message='Usage: bookmark add "TITLE" [page:N] [level:N]')

    title = op.positionals[1]
    page = int(op.params.get("page", str(ctx.model.active_page + 1)))
    level = int(op.params.get("level", "1"))

    toc = ctx.doc.get_toc()
    toc.append([level, title, page])
    ctx.doc.set_toc(toc)

    return OpResult(
        success=True,
        message=f'Bookmark added: "{title}" → page {page} (level {level})',
        prefix="+",
    )


def _bookmark_remove(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Remove a bookmark by title."""
    if len(op.positionals) < 2:
        return OpResult(success=False, message='Usage: bookmark remove "TITLE"')

    title = op.positionals[1]
    toc = ctx.doc.get_toc()
    original_len = len(toc)
    toc = [entry for entry in toc if entry[1] != title]

    if len(toc) == original_len:
        return OpResult(success=False, message=f"Bookmark not found: {title!r}")

    ctx.doc.set_toc(toc)
    removed = original_len - len(toc)
    return OpResult(
        success=True,
        message=f'Bookmark "{title}" removed ({removed} entries)',
        prefix="-",
    )


HANDLERS: dict[str, callable] = {
    "bookmark": op_bookmark,
}
