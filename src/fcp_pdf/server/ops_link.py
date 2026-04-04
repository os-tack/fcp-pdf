"""Link operation handlers — add and list hyperlinks and internal page links."""

from __future__ import annotations

import fitz

from fcp_core import OpResult, ParsedOp

from fcp_pdf.server.resolvers import (
    PdfOpContext,
    parse_page_range,
    require_active_page,
    resolve_page_idx,
)


def op_link(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Add or list links on pages.

    Syntax:
      link add [on:PAGE] [x:N] [y:N] [w:N] [h:N] [uri:URL]
      link add [on:PAGE] [x:N] [y:N] [w:N] [h:N] [page:N]  — internal link
      link list [on:PAGE] [pages:RANGE]
    """
    if not op.positionals:
        return OpResult(success=False, message="Usage: link add|list ...")

    action = op.positionals[0].lower()

    if action == "add":
        return _link_add(op, ctx)
    elif action == "list":
        return _link_list(op, ctx)
    else:
        return OpResult(success=False, message=f"Unknown link action: {action!r}. Use: add, list")


def _link_add(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Add a link annotation."""
    # Resolve target page
    on_ref = op.params.get("on")
    if on_ref:
        idx = resolve_page_idx(on_ref, ctx)
        if idx is None:
            return OpResult(success=False, message=f"Page not found: {on_ref!r}")
    else:
        active = require_active_page(ctx)
        if isinstance(active, str):
            return OpResult(success=False, message=active)
        _, idx = active

    page = ctx.doc[idx]

    x = float(op.params.get("x", "72"))
    y = float(op.params.get("y", "72"))
    w = float(op.params.get("w", "100"))
    h = float(op.params.get("h", "20"))
    rect = fitz.Rect(x, y, x + w, y + h)

    uri = op.params.get("uri")
    target_page = op.params.get("page")

    if uri:
        link = {"kind": fitz.LINK_URI, "from": rect, "uri": uri}
        page.insert_link(link)
        return OpResult(
            success=True,
            message=f"URI link added on page {idx + 1}: {uri}",
            prefix="+",
        )
    elif target_page:
        try:
            target = int(target_page) - 1
        except ValueError:
            return OpResult(success=False, message=f"Invalid target page: {target_page!r}")
        if target < 0 or target >= len(ctx.doc):
            return OpResult(success=False, message=f"Target page out of range: {target_page}")

        link = {
            "kind": fitz.LINK_GOTO,
            "from": rect,
            "page": target,
            "to": fitz.Point(0, 0),
        }
        page.insert_link(link)
        return OpResult(
            success=True,
            message=f"Internal link added on page {idx + 1} → page {target + 1}",
            prefix="+",
        )
    else:
        return OpResult(success=False, message="Specify uri:URL for web link or page:N for internal link")


def _link_list(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """List all links on page(s)."""
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
        indices = list(range(len(ctx.doc)))

    lines: list[str] = []
    total = 0
    for idx in indices:
        page = ctx.doc[idx]
        links = page.get_links()
        if links:
            lines.append(f"  Page {idx + 1}: {len(links)} link(s)")
            for i, link in enumerate(links):
                kind = link.get("kind", -1)
                rect = link.get("from", fitz.Rect())
                if kind == fitz.LINK_URI:
                    uri = link.get("uri", "")
                    lines.append(f"    [{i + 1}] URI: {uri}")
                elif kind == fitz.LINK_GOTO:
                    target = link.get("page", -1)
                    lines.append(f"    [{i + 1}] → page {target + 1}")
                elif kind == fitz.LINK_NAMED:
                    name = link.get("name", "?")
                    lines.append(f"    [{i + 1}] Named: {name}")
                else:
                    lines.append(f"    [{i + 1}] type={kind}")
            total += len(links)

    if not lines:
        return OpResult(success=True, message="No links found", prefix="!")

    lines.insert(0, f"Total: {total} link(s)")
    return OpResult(success=True, message="\n".join(lines), prefix="!")


HANDLERS: dict[str, callable] = {
    "link": op_link,
}
