"""Verb registry for fcp-pdf — defines all verb specs."""

from __future__ import annotations

from fcp_core import VerbSpec

VERBS: list[VerbSpec] = [
    # -- Pages --
    VerbSpec(
        verb="page",
        syntax="page add|remove|move|rotate|copy|activate [N] [at:N] [count:N] [angle:N] [from:N] [to:N]",
        category="pages",
        params=["at", "count", "angle", "from", "to", "width", "height"],
        description="Manage pages: add blank, remove, move, rotate, copy, or activate a page.",
    ),
    # -- Text extraction --
    VerbSpec(
        verb="text",
        syntax="text extract [PAGE] [pages:RANGE] [format:plain|blocks|dict]",
        category="text",
        params=["pages", "format"],
        description="Extract text from page(s). Defaults to active page.",
    ),
    VerbSpec(
        verb="insert-text",
        syntax='insert-text "TEXT" [x:N] [y:N] [font:NAME] [size:N] [color:#HEX] [on:PAGE]',
        category="text",
        params=["x", "y", "font", "size", "color", "on"],
        description="Insert text at a position on a page.",
    ),
    # -- Annotations --
    VerbSpec(
        verb="annotate",
        syntax="annotate highlight|underline|strikeout|note|rect|circle|line [on:PAGE] [x:N] [y:N] [w:N] [h:N] [color:#HEX]",
        category="annotations",
        params=["on", "x", "y", "w", "h", "x1", "y1", "color", "content", "text"],
        description="Add annotations: highlights, underlines, sticky notes, shapes.",
    ),
    # -- Bookmarks / TOC --
    VerbSpec(
        verb="bookmark",
        syntax="bookmark add|remove|list TITLE [page:N] [level:N]",
        category="bookmarks",
        params=["page", "level"],
        description="Manage document bookmarks (table of contents entries).",
    ),
    # -- Merge / Split --
    VerbSpec(
        verb="merge",
        syntax="merge PATH [at:N] [pages:RANGE]",
        category="combine",
        params=["at", "pages"],
        description="Merge another PDF into the current document.",
    ),
    VerbSpec(
        verb="split",
        syntax="split PATH [pages:RANGE]",
        category="combine",
        params=["pages"],
        description="Extract page range to a new PDF file.",
    ),
    # -- Metadata --
    VerbSpec(
        verb="meta",
        syntax="meta get|set [title:TEXT] [author:TEXT] [subject:TEXT] [keywords:TEXT]",
        category="metadata",
        params=["title", "author", "subject", "keywords", "creator", "producer"],
        description="Get or set document metadata (title, author, subject, keywords).",
    ),
    # -- Watermark --
    VerbSpec(
        verb="watermark",
        syntax='watermark "TEXT" [font:NAME] [size:N] [color:#HEX] [opacity:N] [angle:N] [pages:RANGE]',
        category="visual",
        params=["font", "size", "color", "opacity", "angle", "pages"],
        description="Add a text watermark across pages.",
    ),
    # -- Images --
    VerbSpec(
        verb="image",
        syntax="image insert|extract|list PATH [x:N] [y:N] [w:N] [h:N] [on:PAGE] [pages:RANGE]",
        category="images",
        params=["x", "y", "w", "h", "on", "pages"],
        description="Insert images into pages or extract/list images from pages.",
    ),
    # -- Redact --
    VerbSpec(
        verb="redact",
        syntax='redact "TEXT" [on:PAGE] [pages:RANGE] [fill:#HEX]',
        category="security",
        params=["on", "pages", "fill"],
        description="Redact (permanently remove) text from pages.",
    ),
    # -- Links --
    VerbSpec(
        verb="link",
        syntax="link add|list [on:PAGE] [x:N] [y:N] [w:N] [h:N] [uri:URL] [page:N]",
        category="links",
        params=["on", "x", "y", "w", "h", "uri", "page"],
        description="Add or list hyperlinks and internal page links.",
    ),
    # -- Compose (layout engine) --
    VerbSpec(
        verb="compose",
        syntax="compose heading|paragraph|table|row|list|cover|callout|badge|highlight|toc|rule|spacer|blockquote|code|image|pagebreak|columns|config|status|clear|render|raw ...",
        category="compose",
        params=[
            "level", "align", "indent", "size", "color", "lang", "width", "caption",
            "height", "ordered", "paper", "margin", "margin-top", "margin-right",
            "margin-bottom", "margin-left", "font", "line-height", "header", "footer",
            "at", "theme", "numbering", "subtitle", "author", "date", "title", "bg",
        ],
        description=(
            "Document layout engine with themes. Accumulate structured content (headings, paragraphs, "
            "tables, lists, code blocks, callouts, cover pages, images, columns) into a buffer, "
            "then 'compose render' paginates everything with text reflow, page breaks, headers, "
            "footers, and auto-generated bookmarks. Themes: corporate, modern, minimal, executive, ocean."
        ),
    ),
]

VERB_MAP: dict[str, VerbSpec] = {v.verb: v for v in VERBS}
