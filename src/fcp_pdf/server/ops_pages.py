"""Page operation handlers — add, remove, move, rotate, copy, activate."""

from __future__ import annotations

import fitz

from fcp_core import OpResult, ParsedOp

from fcp_pdf.server.resolvers import (
    PdfOpContext,
    parse_page_range,
    resolve_page_idx,
)


def op_page(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Manage pages.

    Syntax:
      page add [at:N] [count:N] [width:W] [height:H]
      page remove N|RANGE
      page move FROM to:TO
      page rotate N|RANGE angle:90|180|270
      page copy N [at:N]
      page activate N
    """
    if not op.positionals:
        return OpResult(success=False, message="Usage: page add|remove|move|rotate|copy|activate [N]")

    action = op.positionals[0].lower()
    rest = op.positionals[1:]

    if action == "add":
        return _page_add(rest, op.params, ctx)
    elif action == "remove":
        return _page_remove(rest, op.params, ctx)
    elif action == "move":
        return _page_move(rest, op.params, ctx)
    elif action == "rotate":
        return _page_rotate(rest, op.params, ctx)
    elif action == "copy":
        return _page_copy(rest, op.params, ctx)
    elif action == "activate":
        return _page_activate(rest, op.params, ctx)
    else:
        return OpResult(success=False, message=f"Unknown page action: {action!r}. Use: add, remove, move, rotate, copy, activate")


def _page_add(rest: list[str], params: dict[str, str], ctx: PdfOpContext) -> OpResult:
    """Add blank page(s)."""
    count = int(params.get("count", "1"))
    at = params.get("at")

    # Page dimensions — default to letter size
    width = float(params.get("width", "612"))  # 8.5" in points
    height = float(params.get("height", "792"))  # 11" in points

    insert_after = -1  # append
    if at:
        idx = resolve_page_idx(at, ctx)
        if idx is None:
            return OpResult(success=False, message=f"Invalid page reference: {at!r}")
        insert_after = idx - 1  # insert before the target

    for i in range(count):
        pos = insert_after + i if insert_after >= 0 else -1
        ctx.doc.new_page(pno=pos, width=width, height=height)

    # Activate the first new page
    if insert_after >= 0:
        ctx.model.active_page = insert_after
    else:
        ctx.model.active_page = len(ctx.doc) - count

    if count == 1:
        return OpResult(success=True, message=f"Page added (page {ctx.model.active_page + 1})", prefix="+")
    return OpResult(success=True, message=f"{count} pages added", prefix="+")


def _page_remove(rest: list[str], params: dict[str, str], ctx: PdfOpContext) -> OpResult:
    """Remove page(s)."""
    if not rest:
        return OpResult(success=False, message="Usage: page remove N|RANGE")

    spec = rest[0]
    indices = parse_page_range(spec, len(ctx.doc))
    if indices is None:
        return OpResult(success=False, message=f"Invalid page range: {spec!r}")

    # Remove in reverse order to keep indices stable
    for idx in sorted(set(indices), reverse=True):
        ctx.doc.delete_page(idx)

    # Clamp active page
    if len(ctx.doc) == 0:
        ctx.model.active_page = 0
    elif ctx.model.active_page >= len(ctx.doc):
        ctx.model.active_page = len(ctx.doc) - 1

    removed = len(set(indices))
    if removed == 1:
        return OpResult(success=True, message=f"Page {indices[0] + 1} removed", prefix="-")
    return OpResult(success=True, message=f"{removed} pages removed", prefix="-")


def _page_move(rest: list[str], params: dict[str, str], ctx: PdfOpContext) -> OpResult:
    """Move a page to a new position."""
    if not rest:
        return OpResult(success=False, message="Usage: page move N to:N")

    from_ref = rest[0]
    to_ref = params.get("to")
    if not to_ref:
        return OpResult(success=False, message="Usage: page move N to:N (missing 'to' param)")

    from_idx = resolve_page_idx(from_ref, ctx)
    to_idx = resolve_page_idx(to_ref, ctx)
    if from_idx is None:
        return OpResult(success=False, message=f"Invalid source page: {from_ref!r}")
    if to_idx is None:
        return OpResult(success=False, message=f"Invalid target page: {to_ref!r}")

    ctx.doc.move_page(from_idx, to_idx)
    ctx.model.active_page = to_idx
    return OpResult(success=True, message=f"Page {from_idx + 1} moved to position {to_idx + 1}", prefix="*")


def _page_rotate(rest: list[str], params: dict[str, str], ctx: PdfOpContext) -> OpResult:
    """Rotate page(s)."""
    if not rest:
        return OpResult(success=False, message="Usage: page rotate N|RANGE angle:90|180|270")

    spec = rest[0]
    angle = int(params.get("angle", "90"))
    if angle not in (0, 90, 180, 270, -90, -180, -270):
        return OpResult(success=False, message=f"Invalid angle: {angle}. Use 90, 180, or 270")

    indices = parse_page_range(spec, len(ctx.doc))
    if indices is None:
        return OpResult(success=False, message=f"Invalid page range: {spec!r}")

    for idx in indices:
        page = ctx.doc[idx]
        page.set_rotation((page.rotation + angle) % 360)

    count = len(set(indices))
    if count == 1:
        return OpResult(success=True, message=f"Page {indices[0] + 1} rotated {angle} degrees", prefix="*")
    return OpResult(success=True, message=f"{count} pages rotated {angle} degrees", prefix="*")


def _page_copy(rest: list[str], params: dict[str, str], ctx: PdfOpContext) -> OpResult:
    """Copy a page within the document."""
    if not rest:
        return OpResult(success=False, message="Usage: page copy N [at:N]")

    src_ref = rest[0]
    src_idx = resolve_page_idx(src_ref, ctx)
    if src_idx is None:
        return OpResult(success=False, message=f"Invalid source page: {src_ref!r}")

    at = params.get("at")
    dest = -1  # append
    if at:
        dest_idx = resolve_page_idx(at, ctx)
        if dest_idx is None:
            return OpResult(success=False, message=f"Invalid target position: {at!r}")
        dest = dest_idx

    ctx.doc.copy_page(src_idx, dest)
    new_idx = dest if dest >= 0 else len(ctx.doc) - 1
    ctx.model.active_page = new_idx
    return OpResult(success=True, message=f"Page {src_idx + 1} copied to position {new_idx + 1}", prefix="+")


def _page_activate(rest: list[str], params: dict[str, str], ctx: PdfOpContext) -> OpResult:
    """Set the active page."""
    if not rest:
        return OpResult(success=False, message="Usage: page activate N")

    ref = rest[0]
    idx = resolve_page_idx(ref, ctx)
    if idx is None:
        return OpResult(success=False, message=f"Invalid page reference: {ref!r}")

    ctx.model.active_page = idx
    return OpResult(success=True, message=f"Active page: {idx + 1}", prefix="*")


HANDLERS: dict[str, callable] = {
    "page": op_page,
}
