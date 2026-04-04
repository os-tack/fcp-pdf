"""Image operation handlers — insert, extract, list."""

from __future__ import annotations

import os

import fitz

from fcp_core import OpResult, ParsedOp

from fcp_pdf.server.resolvers import (
    PdfOpContext,
    parse_page_range,
    require_active_page,
    resolve_page_idx,
)


def op_image(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Insert, extract, or list images.

    Syntax:
      image insert PATH [x:N] [y:N] [w:N] [h:N] [on:PAGE]
      image extract [on:PAGE] [pages:RANGE]  — extract images to files
      image list [on:PAGE] [pages:RANGE]     — list embedded images
    """
    if not op.positionals:
        return OpResult(success=False, message="Usage: image insert|extract|list ...")

    action = op.positionals[0].lower()

    if action == "insert":
        return _image_insert(op, ctx)
    elif action == "extract":
        return _image_extract(op, ctx)
    elif action == "list":
        return _image_list(op, ctx)
    else:
        return OpResult(success=False, message=f"Unknown image action: {action!r}. Use: insert, extract, list")


def _image_insert(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Insert an image onto a page."""
    if len(op.positionals) < 2:
        return OpResult(success=False, message="Usage: image insert PATH [x:N] [y:N] [w:N] [h:N] [on:PAGE]")

    path = op.positionals[1]
    if not os.path.isabs(path):
        base = os.path.dirname(ctx.model.file_path) if ctx.model.file_path else os.getcwd()
        path = os.path.join(base, path)

    if not os.path.isfile(path):
        return OpResult(success=False, message=f"Image not found: {path!r}")

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

    # Position and size
    x = float(op.params.get("x", "72"))
    y = float(op.params.get("y", "72"))
    w = op.params.get("w")
    h = op.params.get("h")

    if w and h:
        rect = fitz.Rect(x, y, x + float(w), y + float(h))
    elif w:
        # Auto-height based on aspect ratio
        img = fitz.Pixmap(path)
        aspect = img.height / img.width
        fw = float(w)
        rect = fitz.Rect(x, y, x + fw, y + fw * aspect)
    else:
        # Place at natural size (capped at page width - margins)
        img = fitz.Pixmap(path)
        max_w = page.rect.width - 144  # 1-inch margins
        scale = min(1.0, max_w / img.width)
        fw = img.width * scale
        fh = img.height * scale
        rect = fitz.Rect(x, y, x + fw, y + fh)

    page.insert_image(rect, filename=path)

    return OpResult(
        success=True,
        message=f"Image inserted on page {idx + 1} at ({x:.0f}, {y:.0f})",
        prefix="+",
    )


def _image_extract(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Extract embedded images from pages."""
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
        indices = list(range(len(ctx.doc)))

    # Output directory
    base_dir = os.path.dirname(ctx.model.file_path) if ctx.model.file_path else os.getcwd()
    out_dir = os.path.join(base_dir, "extracted_images")
    os.makedirs(out_dir, exist_ok=True)

    extracted = 0
    for idx in indices:
        page = ctx.doc[idx]
        image_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]
            base_image = ctx.doc.extract_image(xref)
            if base_image:
                ext = base_image["ext"]
                img_bytes = base_image["image"]
                filename = f"page{idx + 1}_img{img_idx + 1}.{ext}"
                filepath = os.path.join(out_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                extracted += 1

    if extracted == 0:
        return OpResult(success=True, message="No images found to extract", prefix="!")

    return OpResult(
        success=True,
        message=f"Extracted {extracted} image(s) to {out_dir}",
        prefix="+",
    )


def _image_list(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """List embedded images across pages."""
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
        images = page.get_images(full=True)
        if images:
            lines.append(f"  Page {idx + 1}: {len(images)} image(s)")
            for i, img in enumerate(images):
                xref, smask, width, height = img[0], img[1], img[2], img[3]
                colorspace = img[5] if len(img) > 5 else "?"
                lines.append(f"    [{i + 1}] {width}x{height} xref={xref} cs={colorspace}")
            total += len(images)

    if not lines:
        return OpResult(success=True, message="No images found", prefix="!")

    lines.insert(0, f"Total: {total} image(s)")
    return OpResult(success=True, message="\n".join(lines), prefix="!")


HANDLERS: dict[str, callable] = {
    "image": op_image,
}
