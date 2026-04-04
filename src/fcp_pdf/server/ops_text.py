"""Text operation handlers — extract and insert text."""

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


def op_text(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Extract text from page(s).

    Syntax:
      text extract [PAGE] [pages:RANGE] [format:plain|blocks|dict]
    """
    if not op.positionals:
        return OpResult(success=False, message="Usage: text extract [PAGE] [pages:RANGE]")

    action = op.positionals[0].lower()

    if action != "extract":
        return OpResult(success=False, message=f"Unknown text action: {action!r}. Use: extract")

    fmt = op.params.get("format", "plain")

    # Determine page range
    pages_spec = op.params.get("pages")
    if pages_spec:
        indices = parse_page_range(pages_spec, len(ctx.doc))
        if indices is None:
            return OpResult(success=False, message=f"Invalid page range: {pages_spec!r}")
    elif len(op.positionals) > 1:
        ref = op.positionals[1]
        idx = resolve_page_idx(ref, ctx)
        if idx is None:
            return OpResult(success=False, message=f"Invalid page reference: {ref!r}")
        indices = [idx]
    else:
        active = require_active_page(ctx)
        if isinstance(active, str):
            return OpResult(success=False, message=active)
        _, idx = active
        indices = [idx]

    results: list[str] = []
    for idx in indices:
        page = ctx.doc[idx]
        if fmt == "blocks":
            blocks = page.get_text("blocks")
            lines = [f"--- Page {idx + 1} ---"]
            for b in blocks:
                x0, y0, x1, y1, text, block_no, block_type = b[:7]
                if block_type == 0:  # text block
                    lines.append(f"  [{block_no}] ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}): {text.strip()}")
            results.append("\n".join(lines))
        elif fmt == "dict":
            d = page.get_text("dict")
            lines = [f"--- Page {idx + 1} ({d['width']:.0f}x{d['height']:.0f}) ---"]
            for block in d.get("blocks", []):
                if block["type"] == 0:  # text
                    for line_info in block.get("lines", []):
                        spans_text = " ".join(s["text"] for s in line_info.get("spans", []))
                        if spans_text.strip():
                            font_info = line_info["spans"][0] if line_info.get("spans") else {}
                            font = font_info.get("font", "?")
                            size = font_info.get("size", 0)
                            lines.append(f"  [{font} {size:.1f}pt] {spans_text.strip()}")
            results.append("\n".join(lines))
        else:
            text = page.get_text().strip()
            if len(indices) > 1:
                results.append(f"--- Page {idx + 1} ---\n{text}")
            else:
                results.append(text)

    body = "\n\n".join(results)
    total_chars = sum(len(r) for r in results)
    return OpResult(
        success=True,
        message=body if total_chars < 8000 else body[:8000] + f"\n... truncated ({total_chars} total chars)",
        prefix="!",
    )


def op_insert_text(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Insert text at a position on a page.

    Syntax:
      insert-text "TEXT" [x:N] [y:N] [font:NAME] [size:N] [color:#HEX] [on:PAGE]
    """
    if not op.positionals:
        return OpResult(success=False, message='Usage: insert-text "TEXT" [x:N] [y:N]')

    text = op.positionals[0]

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

    x = float(op.params.get("x", "72"))   # 1 inch default
    y = float(op.params.get("y", "72"))
    font_name = op.params.get("font", "helv")
    font_size = float(op.params.get("size", "12"))

    color = (0, 0, 0)  # black default
    if "color" in op.params:
        try:
            color = parse_color(op.params["color"])
        except ValueError as e:
            return OpResult(success=False, message=str(e))

    # Map friendly font names to fitz Base14 names
    font_map = {
        "helv": "helv", "helvetica": "helv",
        "times": "tiro", "times-roman": "tiro",
        "courier": "cour",
        "symbol": "symb",
        "zapf": "zadb", "zapfdingbats": "zadb",
    }
    fitz_font = font_map.get(font_name.lower(), font_name)

    point = fitz.Point(x, y)
    rc = page.insert_text(
        point,
        text,
        fontname=fitz_font,
        fontsize=font_size,
        color=color,
    )

    if rc < 0:
        return OpResult(success=False, message="Text insertion failed (text may not fit)")

    return OpResult(
        success=True,
        message=f'Text inserted on page {idx + 1} at ({x:.0f}, {y:.0f})',
        prefix="+",
    )


HANDLERS: dict[str, callable] = {
    "text": op_text,
    "insert-text": op_insert_text,
}
