"""Operation context and reference resolution for PDF verbs."""

from __future__ import annotations

from dataclasses import dataclass

import fitz

from fcp_pdf.model.snapshot import PdfModel


@dataclass
class PdfOpContext:
    """Context passed to every verb handler."""

    doc: fitz.Document
    model: PdfModel

    @property
    def active_page(self) -> fitz.Page | None:
        idx = self.model.active_page
        if 0 <= idx < len(self.doc):
            return self.doc[idx]
        return None

    @property
    def active_page_idx(self) -> int:
        return self.model.active_page

    @property
    def page_count(self) -> int:
        return len(self.doc)


def resolve_page_idx(ref: str, ctx: PdfOpContext) -> int | None:
    """Resolve a page reference to a 0-based index.

    Accepts:
      - 1-based number: "1", "5"
      - Keywords: "active", "last", "first"
    """
    ref = ref.strip().lower()
    if ref in ("active", "current"):
        return ctx.model.active_page
    if ref == "last":
        return len(ctx.doc) - 1 if len(ctx.doc) > 0 else None
    if ref == "first":
        return 0 if len(ctx.doc) > 0 else None
    try:
        n = int(ref)
        if 1 <= n <= len(ctx.doc):
            return n - 1
        return None
    except ValueError:
        return None


def parse_page_range(spec: str, page_count: int) -> list[int] | None:
    """Parse a page range spec into 0-based indices.

    Formats:
      "3"       -> [2]
      "1-5"     -> [0,1,2,3,4]
      "1,3,5"   -> [0,2,4]
      "1-3,7-9" -> [0,1,2,6,7,8]
      "all"     -> [0..page_count-1]
    """
    spec = spec.strip().lower()
    if spec == "all":
        return list(range(page_count))

    indices: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            try:
                start = int(start_s.strip())
                end = int(end_s.strip())
            except ValueError:
                return None
            if start < 1 or end < 1 or start > page_count or end > page_count:
                return None
            if start <= end:
                indices.extend(range(start - 1, end))
            else:
                indices.extend(range(start - 1, end - 2, -1))
        else:
            try:
                n = int(part)
            except ValueError:
                return None
            if n < 1 or n > page_count:
                return None
            indices.append(n - 1)

    return indices


def require_active_page(ctx: PdfOpContext) -> tuple[fitz.Page, int] | str:
    """Get the active page or return an error message."""
    page = ctx.active_page
    if page is None:
        return "No active page. Use 'page add' first."
    return page, ctx.active_page_idx


def parse_color(hex_str: str) -> tuple[float, float, float]:
    """Parse a hex color string to RGB floats (0.0-1.0)."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    if len(hex_str) != 6:
        raise ValueError(f"Invalid color: #{hex_str}")
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return (r, g, b)
