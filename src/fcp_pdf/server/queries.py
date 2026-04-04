"""Read-only query handlers for PDF inspection."""

from __future__ import annotations

from fcp_pdf.model.snapshot import PdfModel


def dispatch_query(query: str, model: PdfModel) -> str:
    """Route a query string to the appropriate handler."""
    parts = query.strip().split(None, 1)
    if not parts:
        return "! Empty query"

    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    handler = QUERY_HANDLERS.get(cmd)
    if handler is None:
        available = ", ".join(sorted(QUERY_HANDLERS.keys()))
        return f"! Unknown query: {cmd!r}. Available: {available}"

    return handler(args, model)


def _query_plan(args: str, model: PdfModel) -> str:
    """Overview of the document structure."""
    doc = model.doc
    lines: list[str] = []
    lines.append(f"Document: {model.title}")
    if model.file_path:
        lines.append(f"File: {model.file_path}")

    lines.append(f"Pages: {len(doc)}")
    lines.append(f"Active: page {model.active_page + 1}")

    # Metadata summary
    meta = doc.metadata
    if meta.get("title"):
        lines.append(f"Title: {meta['title']}")
    if meta.get("author"):
        lines.append(f"Author: {meta['author']}")

    # Encryption
    if doc.is_encrypted:
        lines.append("Encrypted: yes")

    # TOC
    toc = doc.get_toc()
    if toc:
        lines.append(f"Bookmarks: {len(toc)}")

    lines.append("")

    # Page summaries
    for i in range(min(len(doc), 50)):
        page = doc[i]
        marker = " *" if i == model.active_page else ""
        rotation = f" rot={page.rotation}" if page.rotation else ""
        text_len = len(page.get_text())
        images = len(page.get_images())
        links = len(page.get_links())
        annots = 0
        for _ in page.annots():
            annots += 1

        parts_list: list[str] = []
        parts_list.append(f"{page.rect.width:.0f}x{page.rect.height:.0f}")
        if text_len:
            parts_list.append(f"{text_len} chars")
        if images:
            parts_list.append(f"{images} img")
        if links:
            parts_list.append(f"{links} links")
        if annots:
            parts_list.append(f"{annots} annots")
        if rotation:
            parts_list.append(rotation.strip())

        detail = ", ".join(parts_list)
        lines.append(f"  Page {i + 1}{marker}: [{detail}]")

    if len(doc) > 50:
        lines.append(f"  ... +{len(doc) - 50} more pages")

    return "\n".join(lines)


def _query_status(args: str, model: PdfModel) -> str:
    """Quick status summary."""
    doc = model.doc
    total_text = sum(len(doc[i].get_text()) for i in range(len(doc)))
    total_images = sum(len(doc[i].get_images()) for i in range(len(doc)))

    lines = [
        f"Title: {model.title}",
        f"File: {model.file_path or '(unsaved)'}",
        f"Pages: {len(doc)}",
        f"Active: page {model.active_page + 1}",
        f"Total text: {total_text} chars",
        f"Total images: {total_images}",
    ]
    return "\n".join(lines)


def _query_describe(args: str, model: PdfModel) -> str:
    """Describe a specific page in detail."""
    if not args:
        return "! Usage: describe PAGE_NUMBER"

    try:
        page_num = int(args.strip())
    except ValueError:
        return f"! Invalid page number: {args!r}"

    idx = page_num - 1
    if idx < 0 or idx >= len(model.doc):
        return f"! Page {page_num} out of range (1-{len(model.doc)})"

    page = model.doc[idx]
    lines: list[str] = [
        f"Page {page_num}",
        f"  Size: {page.rect.width:.0f} x {page.rect.height:.0f} points",
        f"  Rotation: {page.rotation}",
    ]

    # Text blocks
    blocks = page.get_text("dict").get("blocks", [])
    text_blocks = [b for b in blocks if b["type"] == 0]
    image_blocks = [b for b in blocks if b["type"] == 1]
    lines.append(f"  Text blocks: {len(text_blocks)}")
    lines.append(f"  Image blocks: {len(image_blocks)}")

    # Fonts used
    fonts: set[str] = set()
    for block in text_blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                fonts.add(f"{span.get('font', '?')} {span.get('size', 0):.1f}pt")
    if fonts:
        lines.append(f"  Fonts: {', '.join(sorted(fonts))}")

    # Images
    images = page.get_images(full=True)
    if images:
        lines.append(f"  Embedded images: {len(images)}")
        for i, img in enumerate(images):
            lines.append(f"    [{i + 1}] {img[2]}x{img[3]} xref={img[0]}")

    # Links
    links = page.get_links()
    if links:
        lines.append(f"  Links: {len(links)}")

    # Annotations
    annots = list(page.annots())
    if annots:
        lines.append(f"  Annotations: {len(annots)}")
        for a in annots[:10]:
            lines.append(f"    {a.type[1]}: {a.info.get('content', '')[:50]}")

    # Text preview (first 500 chars)
    text = page.get_text().strip()
    if text:
        preview = text[:500]
        lines.append(f"  Text preview:")
        for tl in preview.split("\n")[:15]:
            if tl.strip():
                lines.append(f"    {tl.strip()}")
        if len(text) > 500:
            lines.append(f"    ... ({len(text)} total chars)")

    return "\n".join(lines)


def _query_find(args: str, model: PdfModel) -> str:
    """Search for text across all pages."""
    if not args:
        return "! Usage: find TEXT"

    needle = args.strip()
    results: list[str] = []

    for i in range(len(model.doc)):
        page = model.doc[i]
        instances = page.search_for(needle)
        if instances:
            # Get surrounding text context
            text = page.get_text()
            lower_text = text.lower()
            lower_needle = needle.lower()
            pos = lower_text.find(lower_needle)
            if pos >= 0:
                start = max(0, pos - 30)
                end = min(len(text), pos + len(needle) + 30)
                context = text[start:end].replace("\n", " ").strip()
                results.append(f"  Page {i + 1} ({len(instances)}x): ...{context}...")
            else:
                results.append(f"  Page {i + 1}: {len(instances)} match(es)")

    if not results:
        return f"No matches for {needle!r}"

    header = f"Found in {len(results)} page(s):"
    if len(results) > 50:
        results = results[:50]
        results.append("  ... truncated")

    return header + "\n" + "\n".join(results)


def _query_toc(args: str, model: PdfModel) -> str:
    """Display the table of contents / bookmarks."""
    toc = model.doc.get_toc()
    if not toc:
        return "No table of contents / bookmarks"

    lines = [f"Table of Contents ({len(toc)} entries):"]
    for level, title, page in toc:
        indent = "  " * level
        lines.append(f"{indent}{title} → page {page}")

    return "\n".join(lines)


def _query_fonts(args: str, model: PdfModel) -> str:
    """List all fonts used in the document."""
    all_fonts: dict[str, set[int]] = {}

    page_range = range(len(model.doc))
    if args.strip():
        try:
            page_num = int(args.strip())
            page_range = range(page_num - 1, page_num)
        except ValueError:
            pass

    for i in page_range:
        page = model.doc[i]
        fonts = page.get_fonts()
        for f in fonts:
            xref, ext, ftype, name = f[0], f[1], f[2], f[3]
            key = f"{name} ({ftype})"
            if key not in all_fonts:
                all_fonts[key] = set()
            all_fonts[key].add(i + 1)

    if not all_fonts:
        return "No fonts found"

    lines = [f"Fonts ({len(all_fonts)} unique):"]
    for font_key in sorted(all_fonts):
        pages = sorted(all_fonts[font_key])
        if len(pages) > 10:
            page_str = f"pages {pages[0]}-{pages[-1]} ({len(pages)} pages)"
        else:
            page_str = f"pages {', '.join(str(p) for p in pages)}"
        lines.append(f"  {font_key}: {page_str}")

    return "\n".join(lines)


def _query_annots(args: str, model: PdfModel) -> str:
    """List annotations across pages."""
    lines: list[str] = []
    total = 0

    for i in range(len(model.doc)):
        page = model.doc[i]
        annots = list(page.annots())
        if annots:
            lines.append(f"  Page {i + 1}: {len(annots)} annotation(s)")
            for a in annots:
                type_name = a.type[1]
                content = a.info.get("content", "")
                rect = a.rect
                detail = f"    {type_name}"
                if content:
                    detail += f': "{content[:50]}"'
                detail += f" at ({rect.x0:.0f},{rect.y0:.0f})"
                lines.append(detail)
            total += len(annots)

    if not lines:
        return "No annotations found"

    lines.insert(0, f"Total: {total} annotation(s)")
    return "\n".join(lines)


QUERY_HANDLERS: dict[str, callable] = {
    "plan": _query_plan,
    "map": _query_plan,
    "status": _query_status,
    "describe": _query_describe,
    "find": _query_find,
    "search": _query_find,
    "toc": _query_toc,
    "bookmarks": _query_toc,
    "fonts": _query_fonts,
    "annots": _query_annots,
    "annotations": _query_annots,
}
