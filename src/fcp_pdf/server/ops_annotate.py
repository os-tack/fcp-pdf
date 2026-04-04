"""Annotation operation handlers — highlight, underline, strikeout, note, shapes."""

from __future__ import annotations

import fitz

from fcp_core import OpResult, ParsedOp

from fcp_pdf.server.resolvers import (
    PdfOpContext,
    parse_color,
    require_active_page,
    resolve_page_idx,
)


def op_annotate(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Add annotations to a page.

    Syntax:
      annotate highlight text:"TEXT" [on:PAGE] [color:#HEX]
      annotate underline text:"TEXT" [on:PAGE] [color:#HEX]
      annotate strikeout text:"TEXT" [on:PAGE] [color:#HEX]
      annotate note [x:N] [y:N] [content:"TEXT"] [on:PAGE] [color:#HEX]
      annotate rect [x:N] [y:N] [w:N] [h:N] [on:PAGE] [color:#HEX]
      annotate circle [x:N] [y:N] [w:N] [h:N] [on:PAGE] [color:#HEX]
      annotate line [x:N] [y:N] [x1:N] [y1:N] [on:PAGE] [color:#HEX]
      annotate freetext "TEXT" [x:N] [y:N] [w:N] [h:N] [on:PAGE] [size:N] [color:#HEX]
    """
    if not op.positionals:
        return OpResult(
            success=False,
            message="Usage: annotate highlight|underline|strikeout|note|rect|circle|line|freetext ...",
        )

    action = op.positionals[0].lower()

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

    color = (1.0, 1.0, 0.0)  # yellow default
    if "color" in op.params:
        try:
            color = parse_color(op.params["color"])
        except ValueError as e:
            return OpResult(success=False, message=str(e))

    if action in ("highlight", "underline", "strikeout"):
        return _text_markup(action, op, page, idx, color)
    elif action == "note":
        return _sticky_note(op, page, idx, color)
    elif action == "rect":
        return _rect_annot(op, page, idx, color)
    elif action == "circle":
        return _circle_annot(op, page, idx, color)
    elif action == "line":
        return _line_annot(op, page, idx, color)
    elif action == "freetext":
        return _freetext_annot(op, page, idx, color)
    else:
        return OpResult(
            success=False,
            message=f"Unknown annotation type: {action!r}. Use: highlight, underline, strikeout, note, rect, circle, line, freetext",
        )


def _text_markup(
    action: str, op: ParsedOp, page: fitz.Page, page_idx: int, color: tuple[float, float, float]
) -> OpResult:
    """Apply text markup (highlight/underline/strikeout) by searching for text."""
    search_text = op.params.get("text", "")
    if not search_text and len(op.positionals) > 1:
        search_text = op.positionals[1]
    if not search_text:
        return OpResult(success=False, message=f'Usage: annotate {action} text:"TEXT"')

    quads = page.search_for(search_text, quads=True)
    if not quads:
        return OpResult(success=False, message=f"Text not found on page {page_idx + 1}: {search_text!r}")

    if action == "highlight":
        annot = page.add_highlight_annot(quads)
    elif action == "underline":
        annot = page.add_underline_annot(quads)
    elif action == "strikeout":
        annot = page.add_strikeout_annot(quads)
    else:
        return OpResult(success=False, message=f"Unknown markup: {action}")

    annot.set_colors(stroke=color)
    annot.update()

    return OpResult(
        success=True,
        message=f"{action.capitalize()} applied to {len(quads)} instance(s) of {search_text!r} on page {page_idx + 1}",
        prefix="+",
    )


def _sticky_note(
    op: ParsedOp, page: fitz.Page, page_idx: int, color: tuple[float, float, float]
) -> OpResult:
    """Add a sticky note annotation."""
    x = float(op.params.get("x", "72"))
    y = float(op.params.get("y", "72"))
    content = op.params.get("content", "")
    if not content and len(op.positionals) > 1:
        content = " ".join(op.positionals[1:])
    if not content:
        return OpResult(success=False, message='Usage: annotate note [x:N] [y:N] content:"TEXT"')

    point = fitz.Point(x, y)
    annot = page.add_text_annot(point, content)
    annot.set_colors(stroke=color)
    annot.update()

    return OpResult(
        success=True,
        message=f"Note added on page {page_idx + 1} at ({x:.0f}, {y:.0f})",
        prefix="+",
    )


def _rect_annot(
    op: ParsedOp, page: fitz.Page, page_idx: int, color: tuple[float, float, float]
) -> OpResult:
    """Add a rectangle annotation."""
    x = float(op.params.get("x", "72"))
    y = float(op.params.get("y", "72"))
    w = float(op.params.get("w", "100"))
    h = float(op.params.get("h", "50"))

    rect = fitz.Rect(x, y, x + w, y + h)
    annot = page.add_rect_annot(rect)
    annot.set_colors(stroke=color)
    annot.set_border(width=1.5)
    annot.update()

    return OpResult(
        success=True,
        message=f"Rectangle annotation added on page {page_idx + 1}",
        prefix="+",
    )


def _circle_annot(
    op: ParsedOp, page: fitz.Page, page_idx: int, color: tuple[float, float, float]
) -> OpResult:
    """Add a circle/ellipse annotation."""
    x = float(op.params.get("x", "72"))
    y = float(op.params.get("y", "72"))
    w = float(op.params.get("w", "100"))
    h = float(op.params.get("h", "100"))

    rect = fitz.Rect(x, y, x + w, y + h)
    annot = page.add_circle_annot(rect)
    annot.set_colors(stroke=color)
    annot.set_border(width=1.5)
    annot.update()

    return OpResult(
        success=True,
        message=f"Circle annotation added on page {page_idx + 1}",
        prefix="+",
    )


def _line_annot(
    op: ParsedOp, page: fitz.Page, page_idx: int, color: tuple[float, float, float]
) -> OpResult:
    """Add a line annotation."""
    x = float(op.params.get("x", "72"))
    y = float(op.params.get("y", "72"))
    x1 = float(op.params.get("x1", "200"))
    y1 = float(op.params.get("y1", "200"))

    p1 = fitz.Point(x, y)
    p2 = fitz.Point(x1, y1)
    annot = page.add_line_annot(p1, p2)
    annot.set_colors(stroke=color)
    annot.set_border(width=1.5)
    annot.update()

    return OpResult(
        success=True,
        message=f"Line annotation added on page {page_idx + 1}",
        prefix="+",
    )


def _freetext_annot(
    op: ParsedOp, page: fitz.Page, page_idx: int, color: tuple[float, float, float]
) -> OpResult:
    """Add a free text annotation (text box on the page)."""
    text = ""
    if len(op.positionals) > 1:
        text = op.positionals[1]
    text = text or op.params.get("content", "")
    if not text:
        return OpResult(success=False, message='Usage: annotate freetext "TEXT" [x:N] [y:N] [w:N] [h:N]')

    x = float(op.params.get("x", "72"))
    y = float(op.params.get("y", "72"))
    w = float(op.params.get("w", "200"))
    h = float(op.params.get("h", "50"))
    font_size = float(op.params.get("size", "12"))

    rect = fitz.Rect(x, y, x + w, y + h)
    annot = page.add_freetext_annot(
        rect,
        text,
        fontsize=font_size,
        text_color=color,
    )
    annot.update()

    return OpResult(
        success=True,
        message=f"Free text annotation added on page {page_idx + 1}",
        prefix="+",
    )


HANDLERS: dict[str, callable] = {
    "annotate": op_annotate,
}
