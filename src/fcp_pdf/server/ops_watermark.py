"""Watermark operation handler."""

from __future__ import annotations

import math

import fitz

from fcp_core import OpResult, ParsedOp

from fcp_pdf.server.resolvers import PdfOpContext, parse_color, parse_page_range


def op_watermark(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Add a text watermark across pages.

    Syntax:
      watermark "TEXT" [font:NAME] [size:N] [color:#HEX] [opacity:N] [angle:N] [pages:RANGE]
    """
    if not op.positionals:
        return OpResult(success=False, message='Usage: watermark "TEXT" [size:N] [color:#HEX] [opacity:N] [angle:N]')

    text = op.positionals[0]
    font_size = float(op.params.get("size", "60"))
    angle = float(op.params.get("angle", "45"))
    opacity = float(op.params.get("opacity", "0.3"))

    color = (0.8, 0.8, 0.8)  # light gray default
    if "color" in op.params:
        try:
            color = parse_color(op.params["color"])
        except ValueError as e:
            return OpResult(success=False, message=str(e))

    # Determine pages
    pages_spec = op.params.get("pages", "all")
    indices = parse_page_range(pages_spec, len(ctx.doc))
    if indices is None:
        return OpResult(success=False, message=f"Invalid page range: {pages_spec!r}")

    for idx in indices:
        page = ctx.doc[idx]
        rect = page.rect

        # Calculate center of page
        cx = rect.width / 2
        cy = rect.height / 2

        # Create text writer for precise control
        tw = fitz.TextWriter(page.rect)
        font = fitz.Font("helv")

        # Measure text width to center it
        text_width = font.text_length(text, fontsize=font_size)
        text_height = font_size

        # Starting point: center the text
        start_x = cx - text_width / 2
        start_y = cy + text_height / 2

        tw.append(
            fitz.Point(start_x, start_y),
            text,
            font=font,
            fontsize=font_size,
        )

        tw.write_text(page, color=color, morph=(fitz.Point(cx, cy), fitz.Matrix(angle)), opacity=opacity)

    return OpResult(
        success=True,
        message=f'Watermark "{text}" applied to {len(indices)} page(s)',
        prefix="*",
    )


HANDLERS: dict[str, callable] = {
    "watermark": op_watermark,
}
