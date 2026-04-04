"""Compose — document layout engine backed by fitz.Story.

The compose system accumulates structured content (paragraphs, headings,
tables, lists, rules, images) into a layout buffer. When `compose render`
is called, the buffer is converted to HTML/CSS, fed through fitz.Story,
and paginated into the active document with proper reflow, page breaks,
headers, and footers.

This is the high-level authoring API — where insert-text places glyphs
at absolute coordinates, compose builds documents like a human would.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field

import fitz

from fcp_core import OpResult, ParsedOp

from fcp_pdf.lib.themes import DEFAULT_THEME, Theme, get_theme, list_themes
from fcp_pdf.server.resolvers import PdfOpContext, parse_color


# ---------------------------------------------------------------------------
# Layout buffer — accumulated content before render
# ---------------------------------------------------------------------------

@dataclass
class _LayoutConfig:
    """Page layout configuration."""
    paper: str = "letter"
    margin_top: float = 72
    margin_right: float = 72
    margin_bottom: float = 72
    margin_left: float = 72
    header: str = ""
    footer: str = ""
    font_family: str = "Helvetica, sans-serif"
    font_size: float = 11
    line_height: float = 1.5
    color: str = "#222222"
    theme: Theme = field(default_factory=lambda: DEFAULT_THEME)
    numbering: bool = False


@dataclass
class _ContentBlock:
    """A single block of content in the layout buffer."""
    kind: str  # heading, paragraph, table, list, rule, image, spacer, raw-html, pagebreak, callout, cover, badge
    data: dict = field(default_factory=dict)


class LayoutBuffer:
    """Accumulates content blocks and renders them via Story."""

    def __init__(self) -> None:
        self.config = _LayoutConfig()
        self.blocks: list[_ContentBlock] = []
        self._section_counters = [0, 0, 0, 0]  # H1, H2, H3, H4

    def clear(self) -> None:
        self.blocks.clear()
        self._section_counters = [0, 0, 0, 0]  # H1, H2, H3, H4

    def add(self, block: _ContentBlock) -> None:
        self.blocks.append(block)

    def _section_number(self, level: int) -> str:
        """Generate and return the next section number for a heading level."""
        idx = min(level, 4) - 1
        self._section_counters[idx] += 1
        # Reset lower-level counters
        for i in range(idx + 1, 4):
            self._section_counters[i] = 0
        # Build number string (e.g., "1", "1.2", "1.2.3")
        parts = []
        for i in range(idx + 1):
            parts.append(str(self._section_counters[i]))
        return ".".join(parts)

    def to_html(self) -> tuple[str, str]:
        """Convert accumulated blocks to HTML body + CSS."""
        css = self._build_css()
        body_parts: list[str] = []

        for block in self.blocks:
            body_parts.append(self._render_block(block))

        html = "\n".join(body_parts)
        return html, css

    def _build_css(self) -> str:
        c = self.config
        t = c.theme
        return f"""
body {{
    font-family: {c.font_family};
    font-size: {c.font_size}pt;
    line-height: {c.line_height};
    color: {c.color};
}}
h1 {{ font-size: 22pt; margin-top: 18pt; margin-bottom: 8pt; color: {t.heading}; }}
h2 {{ font-size: 17pt; margin-top: 14pt; margin-bottom: 6pt; color: {t.heading}; }}
h3 {{ font-size: 13pt; margin-top: 10pt; margin-bottom: 4pt; color: {t.subheading}; }}
h4 {{ font-size: {c.font_size}pt; font-weight: bold; margin-top: 8pt; margin-bottom: 4pt; color: {t.subheading}; }}
p {{ margin-top: 0; margin-bottom: 6pt; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 8pt; margin-bottom: 8pt; }}
th {{ background-color: {t.table_header_bg}; color: {t.table_header_fg}; font-weight: bold; padding: 6pt 8pt; border: 1pt solid {t.table_border}; text-align: left; }}
td {{ padding: 5pt 8pt; border: 1pt solid {t.table_border}; }}
tr:nth-child(even) td {{ background-color: {t.table_stripe}; }}
ul, ol {{ margin-top: 4pt; margin-bottom: 8pt; padding-left: 20pt; }}
li {{ margin-bottom: 3pt; }}
hr {{ border: none; border-top: 1pt solid {t.rule}; margin: 12pt 0; }}
blockquote {{ border-left: 3pt solid {t.blockquote_border}; padding-left: 12pt; margin: 8pt 0; color: {t.muted}; font-style: italic; }}
code {{ font-family: Courier; font-size: 10pt; background-color: {t.code_bg}; padding: 1pt 3pt; }}
pre {{ font-family: Courier; font-size: 9pt; background-color: {t.code_bg}; padding: 8pt; margin: 8pt 0; white-space: pre-wrap; }}
a {{ color: {t.accent}; }}
.caption {{ font-size: 9pt; color: {t.muted}; text-align: center; margin-top: 4pt; }}
.muted {{ color: {t.muted}; }}
.accent {{ color: {t.accent}; }}
.callout {{ padding: 10pt 14pt; margin: 8pt 0; border-left: 4pt solid; }}
.callout-info {{ background-color: {t.info_bg}; border-color: {t.info_border}; color: {t.info_fg}; }}
.callout-warning {{ background-color: {t.warning_bg}; border-color: {t.warning_border}; color: {t.warning_fg}; }}
.callout-success {{ background-color: {t.success_bg}; border-color: {t.success_border}; color: {t.success_fg}; }}
.callout-error {{ background-color: {t.error_bg}; border-color: {t.error_border}; color: {t.error_fg}; }}
.callout-title {{ font-weight: bold; margin-bottom: 4pt; }}
.badge {{ font-size: 8pt; padding: 2pt 6pt; font-weight: bold; }}
.cover-title {{ font-size: 36pt; font-weight: bold; color: {t.heading}; }}
.cover-subtitle {{ font-size: 18pt; color: {t.subheading}; margin-top: 8pt; }}
.cover-meta {{ font-size: 11pt; color: {t.muted}; margin-top: 4pt; }}
.highlight {{ background-color: {t.accent_bg}; padding: 8pt 12pt; margin: 6pt 0; }}
"""

    def _render_block(self, block: _ContentBlock) -> str:
        kind = block.kind
        d = block.data

        if kind == "heading":
            level = d.get("level", 1)
            text = _escape(d.get("text", ""))
            # Section numbering
            if self.config.numbering:
                text = f"{self._section_number(level)} {text}"
            tag = f"h{min(level, 4)}"
            align = f' style="text-align:{d["align"]}"' if "align" in d else ""
            return f"<{tag}{align}>{text}</{tag}>"

        elif kind == "cover":
            title = _escape(d.get("title", ""))
            subtitle = _escape(d.get("subtitle", ""))
            author = _escape(d.get("author", ""))
            date = _escape(d.get("date", ""))
            parts = ['<div style="text-align:center;padding-top:200pt">']
            parts.append(f'<p class="cover-title">{title}</p>')
            if subtitle:
                parts.append(f'<p class="cover-subtitle">{subtitle}</p>')
            if author or date:
                parts.append('<div style="height:40pt"></div>')
            if author:
                parts.append(f'<p class="cover-meta">{author}</p>')
            if date:
                parts.append(f'<p class="cover-meta">{date}</p>')
            parts.append("</div>")
            return "\n".join(parts)

        elif kind == "callout":
            level = d.get("level", "info")  # info, warning, success, error
            title = d.get("title", "")
            text = _inline_format(_escape(d.get("text", "")))
            parts = [f'<div class="callout callout-{level}">']
            if title:
                parts.append(f'<p class="callout-title">{_escape(title)}</p>')
            parts.append(f"<p>{text}</p>")
            parts.append("</div>")
            return "\n".join(parts)

        elif kind == "badge":
            text = _escape(d.get("text", ""))
            color = d.get("color", self.config.theme.accent)
            bg = d.get("bg", self.config.theme.accent_bg)
            return f'<span class="badge" style="color:{color};background-color:{bg}">{text}</span>'

        elif kind == "highlight":
            text = _inline_format(_escape(d.get("text", "")))
            return f'<div class="highlight"><p>{text}</p></div>'

        elif kind == "paragraph":
            text = _escape(d.get("text", ""))
            # Convert **bold** and *italic* markdown
            text = _inline_format(text)
            styles: list[str] = []
            if "align" in d:
                styles.append(f"text-align:{d['align']}")
            if "indent" in d:
                styles.append(f"margin-left:{d['indent']}pt")
            if "size" in d:
                styles.append(f"font-size:{d['size']}pt")
            if "color" in d:
                styles.append(f"color:{d['color']}")
            style = f' style="{";".join(styles)}"' if styles else ""
            return f"<p{style}>{text}</p>"

        elif kind == "table":
            headers = d.get("headers", [])
            rows = d.get("rows", [])
            caption = d.get("caption", "")
            parts = ["<table>"]
            if headers:
                parts.append("<tr>" + "".join(f"<th>{_escape(h)}</th>" for h in headers) + "</tr>")
            for row in rows:
                parts.append("<tr>" + "".join(f"<td>{_escape(c)}</td>" for c in row) + "</tr>")
            parts.append("</table>")
            if caption:
                parts.append(f'<p class="caption">{_escape(caption)}</p>')
            return "\n".join(parts)

        elif kind == "list":
            items = d.get("items", [])
            ordered = d.get("ordered", False)
            tag = "ol" if ordered else "ul"
            li_parts = "\n".join(f"<li>{_inline_format(_escape(item))}</li>" for item in items)
            return f"<{tag}>\n{li_parts}\n</{tag}>"

        elif kind == "rule":
            return "<hr/>"

        elif kind == "spacer":
            height = d.get("height", 12)
            return f'<div style="height:{height}pt"></div>'

        elif kind == "blockquote":
            text = _inline_format(_escape(d.get("text", "")))
            return f"<blockquote>{text}</blockquote>"

        elif kind == "code":
            text = _escape(d.get("text", ""))
            lang = d.get("lang", "")
            return f"<pre>{text}</pre>"

        elif kind == "image":
            path = d.get("path", "")
            width = d.get("width", "")
            caption = d.get("caption", "")
            style = f' style="width:{width}"' if width else ""
            parts = [f'<img src="{path}"{style}/>']
            if caption:
                parts.append(f'<p class="caption">{_escape(caption)}</p>')
            return "\n".join(parts)

        elif kind == "pagebreak":
            return '<div style="page-break-before:always"></div>'

        elif kind == "raw-html":
            return d.get("html", "")

        elif kind == "columns":
            cols = d.get("columns", [])
            n = len(cols)
            if n == 0:
                return ""
            col_width = f"{100 // n}%"
            parts = ['<table style="border:none;width:100%"><tr>']
            for col in cols:
                content = _inline_format(_escape(col))
                parts.append(f'<td style="border:none;width:{col_width};vertical-align:top">{content}</td>')
            parts.append("</tr></table>")
            return "\n".join(parts)

        return f"<!-- unknown block: {kind} -->"


def _escape(text: str) -> str:
    """Escape HTML entities."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline_format(text: str) -> str:
    """Convert simple markdown-style inline formatting to HTML.

    Supports **bold**, *italic*, `code`, and ~~strikethrough~~.
    """
    import re
    # Bold: **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Italic: *text*
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    # Code: `text`
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # Strikethrough: ~~text~~
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
    return text


# ---------------------------------------------------------------------------
# Singleton layout buffer (per-session, lives on the model)
# ---------------------------------------------------------------------------

def _get_buffer(ctx: PdfOpContext) -> LayoutBuffer:
    """Get or create the layout buffer on the model."""
    if not hasattr(ctx.model, '_layout_buffer'):
        ctx.model._layout_buffer = LayoutBuffer()
    return ctx.model._layout_buffer


# ---------------------------------------------------------------------------
# Compose verb dispatcher
# ---------------------------------------------------------------------------

def op_compose(op: ParsedOp, ctx: PdfOpContext) -> OpResult:
    """Compose structured document content with automatic layout.

    Content accumulates in a buffer until `compose render` is called,
    which paginates everything into the document with proper reflow.

    Syntax:
      compose heading "TEXT" [level:N]
      compose paragraph "TEXT" [align:left|center|right] [indent:N] [size:N] [color:#HEX]
      compose table [caption:TEXT]                    — start table (follow with data rows)
      compose row "COL1" "COL2" ...                   — add row to current table
      compose list "ITEM1" "ITEM2" ...                — unordered list
      compose ordered-list "ITEM1" "ITEM2" ...        — ordered list
      compose rule                                    — horizontal rule
      compose spacer [height:N]                       — vertical space
      compose blockquote "TEXT"                       — indented quote
      compose code "TEXT" [lang:NAME]                 — code block
      compose image PATH [width:TEXT] [caption:TEXT]  — embed image
      compose pagebreak                               — force page break
      compose columns "COL1" "COL2" ...               — side-by-side columns
      compose config [paper:letter|a4] [margin:N] [font:NAME] [size:N]
      compose status                                  — show buffer contents
      compose clear                                   — clear buffer
      compose render [at:N]                           — render buffer into document
    """
    buf = _get_buffer(ctx)

    if not op.positionals:
        return OpResult(success=False, message="Usage: compose heading|paragraph|table|row|list|rule|render|clear|status ...")

    action = op.positionals[0].lower()
    rest = op.positionals[1:]

    if action == "heading":
        return _compose_heading(rest, op.params, buf)
    elif action == "paragraph":
        return _compose_paragraph(rest, op.params, buf)
    elif action == "table":
        return _compose_table(rest, op.params, buf)
    elif action == "row":
        return _compose_row(rest, op.params, buf)
    elif action == "list":
        return _compose_list(rest, op.params, buf, ordered=False)
    elif action == "ordered-list":
        return _compose_list(rest, op.params, buf, ordered=True)
    elif action == "rule":
        buf.add(_ContentBlock(kind="rule"))
        return OpResult(success=True, message="Rule added", prefix="+")
    elif action == "spacer":
        height = float(op.params.get("height", "12"))
        buf.add(_ContentBlock(kind="spacer", data={"height": height}))
        return OpResult(success=True, message=f"Spacer ({height:.0f}pt) added", prefix="+")
    elif action == "blockquote":
        if not rest:
            return OpResult(success=False, message='Usage: compose blockquote "TEXT"')
        buf.add(_ContentBlock(kind="blockquote", data={"text": rest[0]}))
        return OpResult(success=True, message="Blockquote added", prefix="+")
    elif action == "code":
        if not rest:
            return OpResult(success=False, message='Usage: compose code "TEXT" [lang:NAME]')
        buf.add(_ContentBlock(kind="code", data={"text": rest[0], "lang": op.params.get("lang", "")}))
        return OpResult(success=True, message="Code block added", prefix="+")
    elif action == "image":
        return _compose_image(rest, op.params, buf, ctx)
    elif action == "pagebreak":
        buf.add(_ContentBlock(kind="pagebreak"))
        return OpResult(success=True, message="Page break added", prefix="+")
    elif action == "columns":
        if not rest:
            return OpResult(success=False, message='Usage: compose columns "COL1" "COL2" ...')
        buf.add(_ContentBlock(kind="columns", data={"columns": list(rest)}))
        return OpResult(success=True, message=f"{len(rest)}-column layout added", prefix="+")
    elif action == "cover":
        return _compose_cover(rest, op.params, buf)
    elif action == "callout":
        return _compose_callout(rest, op.params, buf)
    elif action == "badge":
        if not rest:
            return OpResult(success=False, message='Usage: compose badge "TEXT" [color:#HEX] [bg:#HEX]')
        data = {"text": rest[0]}
        if "color" in op.params:
            data["color"] = op.params["color"]
        if "bg" in op.params:
            data["bg"] = op.params["bg"]
        buf.add(_ContentBlock(kind="badge", data=data))
        return OpResult(success=True, message=f"Badge: {rest[0]}", prefix="+")
    elif action == "highlight":
        if not rest:
            return OpResult(success=False, message='Usage: compose highlight "TEXT"')
        buf.add(_ContentBlock(kind="highlight", data={"text": rest[0]}))
        return OpResult(success=True, message="Highlight block added", prefix="+")
    elif action == "toc":
        return _compose_auto_toc(buf, ctx)
    elif action == "config":
        return _compose_config(op.params, buf)
    elif action == "status":
        return _compose_status(buf)
    elif action == "clear":
        buf.clear()
        return OpResult(success=True, message="Layout buffer cleared", prefix="-")
    elif action == "render":
        return _compose_render(op.params, buf, ctx)
    elif action == "raw":
        if not rest:
            return OpResult(success=False, message='Usage: compose raw "<html>..."')
        buf.add(_ContentBlock(kind="raw-html", data={"html": rest[0]}))
        return OpResult(success=True, message="Raw HTML added", prefix="+")
    else:
        return OpResult(
            success=False,
            message=f"Unknown compose action: {action!r}. Use: heading, paragraph, table, row, list, cover, callout, badge, highlight, toc, rule, render, clear, status",
        )


# ---------------------------------------------------------------------------
# Compose sub-commands
# ---------------------------------------------------------------------------

def _compose_heading(rest: list[str], params: dict[str, str], buf: LayoutBuffer) -> OpResult:
    if not rest:
        return OpResult(success=False, message='Usage: compose heading "TEXT" [level:N]')
    text = rest[0]
    level = int(params.get("level", "1"))
    data = {"text": text, "level": level}
    if "align" in params:
        data["align"] = params["align"]
    buf.add(_ContentBlock(kind="heading", data=data))
    return OpResult(success=True, message=f"H{level}: {text[:50]}", prefix="+")


def _compose_paragraph(rest: list[str], params: dict[str, str], buf: LayoutBuffer) -> OpResult:
    if not rest:
        return OpResult(success=False, message='Usage: compose paragraph "TEXT" [align:left|center|right]')
    text = rest[0]
    data: dict = {"text": text}
    for key in ("align", "indent", "size", "color"):
        if key in params:
            data[key] = params[key]
    buf.add(_ContentBlock(kind="paragraph", data=data))
    preview = text[:60] + "..." if len(text) > 60 else text
    return OpResult(success=True, message=f"Paragraph: {preview}", prefix="+")


def _compose_table(rest: list[str], params: dict[str, str], buf: LayoutBuffer) -> OpResult:
    """Start a table. Headers are the positional args. Rows follow via `compose row`."""
    headers = list(rest)
    data: dict = {"headers": headers, "rows": []}
    if "caption" in params:
        data["caption"] = params["caption"]
    buf.add(_ContentBlock(kind="table", data=data))
    if headers:
        return OpResult(success=True, message=f"Table started with {len(headers)} columns: {', '.join(headers)}", prefix="+")
    return OpResult(success=True, message="Table started (headerless)", prefix="+")


def _compose_row(rest: list[str], params: dict[str, str], buf: LayoutBuffer) -> OpResult:
    """Add a row to the most recent table."""
    if not rest:
        return OpResult(success=False, message='Usage: compose row "COL1" "COL2" ...')

    # Find the last table block
    for block in reversed(buf.blocks):
        if block.kind == "table":
            block.data["rows"].append(list(rest))
            row_num = len(block.data["rows"])
            return OpResult(success=True, message=f"Row {row_num} added ({len(rest)} cells)", prefix="+")

    return OpResult(success=False, message="No table started. Use 'compose table' first.")


def _compose_list(rest: list[str], params: dict[str, str], buf: LayoutBuffer, *, ordered: bool) -> OpResult:
    if not rest:
        kind = "ordered-list" if ordered else "list"
        return OpResult(success=False, message=f'Usage: compose {kind} "ITEM1" "ITEM2" ...')
    buf.add(_ContentBlock(kind="list", data={"items": list(rest), "ordered": ordered}))
    return OpResult(success=True, message=f"{'Ordered list' if ordered else 'List'} with {len(rest)} items", prefix="+")


def _compose_image(rest: list[str], params: dict[str, str], buf: LayoutBuffer, ctx: PdfOpContext) -> OpResult:
    if not rest:
        return OpResult(success=False, message='Usage: compose image PATH [width:TEXT] [caption:TEXT]')
    path = rest[0]
    if not os.path.isabs(path):
        base = os.path.dirname(ctx.model.file_path) if ctx.model.file_path else os.getcwd()
        path = os.path.join(base, path)
    if not os.path.isfile(path):
        return OpResult(success=False, message=f"Image not found: {path!r}")
    data = {"path": path}
    if "width" in params:
        data["width"] = params["width"]
    if "caption" in params:
        data["caption"] = params["caption"]
    buf.add(_ContentBlock(kind="image", data=data))
    return OpResult(success=True, message=f"Image added: {os.path.basename(path)}", prefix="+")


def _compose_cover(rest: list[str], params: dict[str, str], buf: LayoutBuffer) -> OpResult:
    """Add a cover/title page."""
    if not rest:
        return OpResult(success=False, message='Usage: compose cover "TITLE" [subtitle:TEXT] [author:TEXT] [date:TEXT]')
    data = {"title": rest[0]}
    for key in ("subtitle", "author", "date"):
        if key in params:
            data[key] = params[key]
    buf.add(_ContentBlock(kind="cover", data=data))
    buf.add(_ContentBlock(kind="pagebreak"))
    return OpResult(success=True, message=f"Cover page: {rest[0][:50]}", prefix="+")


def _compose_callout(rest: list[str], params: dict[str, str], buf: LayoutBuffer) -> OpResult:
    """Add a callout/alert box."""
    if not rest:
        return OpResult(success=False, message='Usage: compose callout "TEXT" [level:info|warning|success|error] [title:TEXT]')
    level = params.get("level", "info")
    if level not in ("info", "warning", "success", "error"):
        return OpResult(success=False, message=f"Unknown callout level: {level!r}. Use: info, warning, success, error")
    data = {"text": rest[0], "level": level}
    if "title" in params:
        data["title"] = params["title"]
    buf.add(_ContentBlock(kind="callout", data=data))
    label = params.get("title", level.upper())
    return OpResult(success=True, message=f"Callout ({level}): {label}", prefix="+")


def _compose_auto_toc(buf: LayoutBuffer, ctx: PdfOpContext) -> OpResult:
    """Generate a table of contents from accumulated headings."""
    headings = [(i, b) for i, b in enumerate(buf.blocks) if b.kind == "heading"]
    if not headings:
        return OpResult(success=False, message="No headings in buffer to generate TOC from")

    # Build a TOC as a series of styled paragraphs
    buf.add(_ContentBlock(kind="heading", data={"text": "Table of Contents", "level": 2}))
    for _, block in headings:
        level = block.data.get("level", 1)
        text = block.data.get("text", "")
        indent = (level - 1) * 20
        buf.add(_ContentBlock(kind="paragraph", data={
            "text": text,
            "indent": str(indent),
            "size": str(max(9, 11 - level)),
        }))
    buf.add(_ContentBlock(kind="pagebreak"))
    return OpResult(success=True, message=f"Table of contents generated ({len(headings)} entries)", prefix="+")


def _compose_config(params: dict[str, str], buf: LayoutBuffer) -> OpResult:
    """Configure page layout."""
    c = buf.config
    updated: list[str] = []

    if "paper" in params:
        c.paper = params["paper"]
        updated.append(f"paper={c.paper}")

    if "margin" in params:
        m = float(params["margin"])
        c.margin_top = c.margin_right = c.margin_bottom = c.margin_left = m
        updated.append(f"margins={m:.0f}pt")

    for side in ("margin-top", "margin-right", "margin-bottom", "margin-left"):
        if side in params:
            setattr(c, side.replace("-", "_"), float(params[side]))
            updated.append(f"{side}={params[side]}pt")

    if "font" in params:
        c.font_family = params["font"]
        updated.append(f"font={c.font_family}")

    if "size" in params:
        c.font_size = float(params["size"])
        updated.append(f"size={c.font_size}pt")

    if "line-height" in params:
        c.line_height = float(params["line-height"])
        updated.append(f"line-height={c.line_height}")

    if "color" in params:
        c.color = params["color"]
        updated.append(f"color={c.color}")

    if "header" in params:
        c.header = params["header"]
        updated.append("header set")

    if "footer" in params:
        c.footer = params["footer"]
        updated.append("footer set")

    if "theme" in params:
        theme = get_theme(params["theme"])
        if theme is None:
            available = ", ".join(list_themes())
            return OpResult(success=False, message=f"Unknown theme: {params['theme']!r}. Available: {available}")
        c.theme = theme
        updated.append(f"theme={theme.name}")

    if "numbering" in params:
        val = params["numbering"].lower()
        c.numbering = val in ("true", "on", "yes", "1")
        updated.append(f"numbering={'on' if c.numbering else 'off'}")

    if not updated:
        return OpResult(success=False, message="No config options specified. Use: paper, margin, font, size, line-height, color, header, footer, theme, numbering")

    return OpResult(success=True, message=f"Layout config: {', '.join(updated)}", prefix="*")


def _compose_status(buf: LayoutBuffer) -> OpResult:
    """Show buffer contents summary."""
    if not buf.blocks:
        return OpResult(success=True, message="Layout buffer is empty", prefix="!")

    c = buf.config
    lines = [
        f"Config: {c.paper}, margins {c.margin_top:.0f}/{c.margin_right:.0f}/{c.margin_bottom:.0f}/{c.margin_left:.0f}pt, {c.font_family} {c.font_size}pt",
        f"Theme: {c.theme.name}" + (", numbering: on" if c.numbering else ""),
        f"Blocks: {len(buf.blocks)}",
        "",
    ]

    for i, block in enumerate(buf.blocks):
        d = block.data
        if block.kind == "heading":
            lines.append(f"  [{i+1}] H{d.get('level',1)}: {d.get('text','')[:60]}")
        elif block.kind == "paragraph":
            text = d.get("text", "")
            lines.append(f"  [{i+1}] P: {text[:60]}{'...' if len(text) > 60 else ''}")
        elif block.kind == "table":
            rows = len(d.get("rows", []))
            cols = len(d.get("headers", []))
            lines.append(f"  [{i+1}] Table: {rows} rows x {cols} cols")
        elif block.kind == "list":
            items = len(d.get("items", []))
            ordered = "OL" if d.get("ordered") else "UL"
            lines.append(f"  [{i+1}] {ordered}: {items} items")
        elif block.kind == "image":
            lines.append(f"  [{i+1}] Image: {os.path.basename(d.get('path',''))}")
        elif block.kind == "pagebreak":
            lines.append(f"  [{i+1}] --- page break ---")
        elif block.kind == "columns":
            lines.append(f"  [{i+1}] Columns: {len(d.get('columns', []))}")
        elif block.kind == "cover":
            lines.append(f"  [{i+1}] Cover: {d.get('title','')[:50]}")
        elif block.kind == "callout":
            lines.append(f"  [{i+1}] Callout ({d.get('level','info')}): {d.get('title', d.get('text','')[:40])}")
        elif block.kind == "badge":
            lines.append(f"  [{i+1}] Badge: {d.get('text','')}")
        elif block.kind == "highlight":
            lines.append(f"  [{i+1}] Highlight: {d.get('text','')[:50]}")
        else:
            lines.append(f"  [{i+1}] {block.kind}")

    return OpResult(success=True, message="\n".join(lines), prefix="!")


def _compose_render(params: dict[str, str], buf: LayoutBuffer, ctx: PdfOpContext) -> OpResult:
    """Render the layout buffer into the document via fitz.Story."""
    if not buf.blocks:
        return OpResult(success=False, message="Layout buffer is empty. Add content first.")

    html_body, css = buf.to_html()

    # Wrap header/footer into the body if configured
    full_html = html_body

    c = buf.config

    try:
        story = fitz.Story(html=full_html, user_css=css)
    except Exception as e:
        return OpResult(success=False, message=f"Story creation failed: {e}")

    # Page dimensions
    try:
        mediabox = fitz.paper_rect(c.paper)
    except Exception:
        mediabox = fitz.paper_rect("letter")

    content_rect = fitz.Rect(
        c.margin_left,
        c.margin_top,
        mediabox.width - c.margin_right,
        mediabox.height - c.margin_bottom,
    )

    # Determine insertion point
    at = params.get("at")
    if at:
        try:
            insert_at = int(at) - 1
        except ValueError:
            return OpResult(success=False, message=f"Invalid page position: {at!r}")
    else:
        insert_at = len(ctx.doc)  # append

    # Render via DocumentWriter to a temporary buffer, then merge
    out_buf = io.BytesIO()
    writer = fitz.DocumentWriter(out_buf)

    page_count = 0
    more = True
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(content_rect)
        story.draw(dev)
        writer.end_page()
        page_count += 1
        if page_count > 500:
            writer.close()
            return OpResult(success=False, message="Render exceeded 500 pages — content too large or infinite loop")

    writer.close()

    # Merge rendered pages into the document
    rendered_doc = fitz.open(stream=out_buf.getvalue(), filetype="pdf")
    ctx.doc.insert_pdf(rendered_doc, start_at=insert_at)
    rendered_doc.close()

    # Add headers and footers on the final pages in the main document
    # (DocumentWriter pages have a flipped coordinate system, so we must
    # write overlays after merging into the main doc)
    if c.header or c.footer:
        for i in range(page_count):
            page_idx = insert_at + i
            if page_idx >= len(ctx.doc):
                break
            page = ctx.doc[page_idx]

            if c.header:
                header_text = c.header.replace("{page}", str(i + 1)).replace("{pages}", str(page_count))
                page.insert_text(
                    fitz.Point(c.margin_left, c.margin_top - 14),
                    header_text,
                    fontname="helv",
                    fontsize=9,
                    color=(0.4, 0.4, 0.4),
                )

            if c.footer:
                footer_text = c.footer.replace("{page}", str(i + 1)).replace("{pages}", str(page_count))
                font = fitz.Font("helv")
                text_width = font.text_length(footer_text, fontsize=9)
                fx = (page.rect.width - text_width) / 2
                fy = page.rect.height - c.margin_bottom + 20
                page.insert_text(
                    fitz.Point(fx, fy),
                    footer_text,
                    fontname="helv",
                    fontsize=9,
                    color=(0.4, 0.4, 0.4),
                )

    # Auto-generate bookmarks from headings
    headings = [b for b in buf.blocks if b.kind == "heading"]
    if headings:
        toc = ctx.doc.get_toc()
        for h in headings:
            level = h.data.get("level", 1)
            title = h.data.get("text", "")
            # Search for the heading text to find which page it landed on
            for pi in range(insert_at, insert_at + page_count):
                if pi < len(ctx.doc):
                    if title in ctx.doc[pi].get_text():
                        toc.append([level, title, pi + 1])
                        break
        try:
            ctx.doc.set_toc(toc)
        except Exception:
            pass  # TOC update is best-effort

    # Activate first new page
    ctx.model.active_page = insert_at

    # Clear buffer after successful render
    buf.clear()

    return OpResult(
        success=True,
        message=f"Rendered {page_count} page(s) into document at position {insert_at + 1}",
        prefix="+",
    )


HANDLERS: dict[str, callable] = {
    "compose": op_compose,
}
