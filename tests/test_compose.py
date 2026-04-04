"""Tests for the compose layout engine."""

from __future__ import annotations

import os
import tempfile

import fitz
import pytest

from fcp_core import EventLog, parse_op
from fcp_pdf.adapter import PdfAdapter
from fcp_pdf.model.snapshot import PdfModel


@pytest.fixture
def adapter():
    return PdfAdapter()


@pytest.fixture
def model(adapter):
    return adapter.create_empty("Test", {})


@pytest.fixture
def log():
    return EventLog()


def _dispatch(adapter, model, log, cmd: str):
    """Helper to dispatch a single command."""
    op = parse_op(cmd)
    return adapter.dispatch_op(op, model, log)


# -- Basic content accumulation --

class TestComposeContent:
    def test_heading(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose heading "Introduction" level:1')
        assert r.success
        assert "H1" in r.message

    def test_heading_level2(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose heading "Details" level:2')
        assert r.success
        assert "H2" in r.message

    def test_paragraph(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose paragraph "This is body text."')
        assert r.success
        assert "Paragraph" in r.message

    def test_paragraph_with_formatting(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose paragraph "Text with **bold** and *italic*" align:center size:14')
        assert r.success

    def test_rule(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose rule")
        assert r.success

    def test_spacer(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose spacer height:24")
        assert r.success
        assert "24" in r.message

    def test_blockquote(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose blockquote "A wise quote."')
        assert r.success

    def test_code_block(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose code "def hello():\n    print(42)" lang:python')
        assert r.success

    def test_pagebreak(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose pagebreak")
        assert r.success

    def test_columns(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose columns "Left side" "Right side"')
        assert r.success
        assert "2-column" in r.message

    def test_list_unordered(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose list "Alpha" "Beta" "Gamma"')
        assert r.success
        assert "3 items" in r.message

    def test_list_ordered(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose ordered-list "First" "Second" "Third"')
        assert r.success
        assert "Ordered" in r.message


# -- Table building --

class TestComposeTable:
    def test_table_with_rows(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose table "Name" "Score"')
        assert r.success
        assert "2 columns" in r.message

        r = _dispatch(adapter, model, log, 'compose row "Alice" "95"')
        assert r.success
        assert "Row 1" in r.message

        r = _dispatch(adapter, model, log, 'compose row "Bob" "87"')
        assert r.success
        assert "Row 2" in r.message

    def test_row_without_table(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose row "X" "Y"')
        assert not r.success
        assert "No table" in r.message

    def test_table_with_caption(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose table "A" "B" caption:"Test Results"')
        assert r.success


# -- Config --

class TestComposeConfig:
    def test_config_paper(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose config paper:a4 margin:54")
        assert r.success
        assert "a4" in r.message
        assert "54" in r.message

    def test_config_font(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose config font:Times size:12 line-height:1.6")
        assert r.success

    def test_config_header_footer(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose config header:"Report" footer:"Page {page}"')
        assert r.success
        assert "header set" in r.message
        assert "footer set" in r.message

    def test_config_no_options(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose config")
        assert not r.success


# -- Status --

class TestComposeStatus:
    def test_status_empty(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose status")
        assert r.success
        assert "empty" in r.message.lower()

    def test_status_with_content(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose heading "Title"')
        _dispatch(adapter, model, log, 'compose paragraph "Body text"')
        _dispatch(adapter, model, log, 'compose table "A" "B"')
        _dispatch(adapter, model, log, 'compose row "1" "2"')
        _dispatch(adapter, model, log, 'compose list "X" "Y"')

        r = _dispatch(adapter, model, log, "compose status")
        assert r.success
        assert "Blocks: 4" in r.message  # heading, paragraph, table, list
        assert "H1" in r.message
        assert "Table" in r.message


# -- Clear --

class TestComposeClear:
    def test_clear(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose heading "Title"')
        _dispatch(adapter, model, log, 'compose paragraph "Content"')

        r = _dispatch(adapter, model, log, "compose clear")
        assert r.success

        r = _dispatch(adapter, model, log, "compose status")
        assert "empty" in r.message.lower()


# -- Render --

class TestComposeRender:
    def test_render_simple(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose heading "Test Document"')
        _dispatch(adapter, model, log, 'compose paragraph "This is the first paragraph of the document."')
        _dispatch(adapter, model, log, 'compose paragraph "This is the second paragraph."')

        r = _dispatch(adapter, model, log, "compose render")
        assert r.success
        assert "1 page" in r.message
        assert len(model.doc) == 1

        # Verify text is in the PDF
        text = model.doc[0].get_text()
        assert "Test Document" in text
        # PyMuPDF may render "fi" as the ﬁ ligature
        assert "rst paragraph" in text

    def test_render_clears_buffer(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose paragraph "Content"')
        _dispatch(adapter, model, log, "compose render")

        r = _dispatch(adapter, model, log, "compose status")
        assert "empty" in r.message.lower()

    def test_render_empty_buffer(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose render")
        assert not r.success
        assert "empty" in r.message.lower()

    def test_render_with_table(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose heading "Report"')
        _dispatch(adapter, model, log, 'compose table "Metric" "Value"')
        _dispatch(adapter, model, log, 'compose row "Revenue" "$1M"')
        _dispatch(adapter, model, log, 'compose row "Profit" "$200K"')
        _dispatch(adapter, model, log, "compose render")

        assert len(model.doc) >= 1
        text = model.doc[0].get_text()
        assert "Report" in text
        assert "Revenue" in text

    def test_render_with_list(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose list "Alpha" "Beta" "Gamma"')
        _dispatch(adapter, model, log, "compose render")

        text = model.doc[0].get_text()
        assert "Alpha" in text

    def test_render_multipage(self, adapter, model, log):
        """Enough content to force multiple pages."""
        _dispatch(adapter, model, log, 'compose heading "Big Document"')
        for i in range(50):
            _dispatch(adapter, model, log, f'compose paragraph "Paragraph {i+1}: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam."')
        _dispatch(adapter, model, log, "compose render")

        assert len(model.doc) >= 2, f"Expected multi-page, got {len(model.doc)}"

    def test_render_with_pagebreak(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose paragraph "Page 1 content"')
        _dispatch(adapter, model, log, "compose pagebreak")
        _dispatch(adapter, model, log, 'compose paragraph "Page 2 content"')
        _dispatch(adapter, model, log, "compose render")

        assert len(model.doc) >= 2

    def test_render_a4(self, adapter, model, log):
        _dispatch(adapter, model, log, "compose config paper:a4")
        _dispatch(adapter, model, log, 'compose paragraph "A4 document"')
        _dispatch(adapter, model, log, "compose render")

        page = model.doc[0]
        # A4 is 595x842
        assert abs(page.rect.width - 595) < 5
        assert abs(page.rect.height - 842) < 5

    def test_render_with_header_footer(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose config header:"ACME Corp" footer:"Page {page} of {pages}"')
        _dispatch(adapter, model, log, 'compose paragraph "Document body"')
        _dispatch(adapter, model, log, "compose render")

        text = model.doc[0].get_text()
        assert "ACME Corp" in text
        assert "Page 1 of 1" in text

    def test_render_at_position(self, adapter, model, log):
        """Render into middle of existing document."""
        # Create 2 existing pages
        _dispatch(adapter, model, log, "page add")
        _dispatch(adapter, model, log, "page add")
        assert len(model.doc) == 2

        # Compose and render at position 1 (before page 2)
        _dispatch(adapter, model, log, 'compose paragraph "Inserted content"')
        r = _dispatch(adapter, model, log, "compose render at:2")
        assert r.success
        assert len(model.doc) == 3

    def test_render_preserves_existing_pages(self, adapter, model, log):
        """Rendering doesn't destroy existing content."""
        _dispatch(adapter, model, log, "page add")
        _dispatch(adapter, model, log, 'insert-text "Existing text" x:72 y:100 on:1')
        assert len(model.doc) == 1

        _dispatch(adapter, model, log, 'compose paragraph "New content"')
        _dispatch(adapter, model, log, "compose render")

        assert len(model.doc) == 2
        # Original page still has its text
        assert "Existing text" in model.doc[0].get_text()
        # New page has composed content
        assert "New content" in model.doc[1].get_text()

    def test_render_and_save(self, adapter, model, log):
        """Full lifecycle: compose → render → save → reload."""
        _dispatch(adapter, model, log, 'compose heading "Saved Document"')
        _dispatch(adapter, model, log, 'compose paragraph "This document was composed and saved."')
        _dispatch(adapter, model, log, 'compose table "Col A" "Col B"')
        _dispatch(adapter, model, log, 'compose row "R1A" "R1B"')
        _dispatch(adapter, model, log, "compose render")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            adapter.serialize(model, path)
            assert os.path.isfile(path)

            loaded = adapter.deserialize(path)
            text = loaded.doc[0].get_text()
            assert "Saved Document" in text
            assert "R1A" in text
        finally:
            os.unlink(path)


# -- HTML generation --

class TestComposeHTML:
    def test_inline_formatting(self, adapter, model, log):
        from fcp_pdf.server.ops_compose import _inline_format
        assert "<b>bold</b>" in _inline_format("**bold**")
        assert "<i>italic</i>" in _inline_format("*italic*")
        assert "<code>code</code>" in _inline_format("`code`")
        assert "<s>strike</s>" in _inline_format("~~strike~~")

    def test_html_escaping(self, adapter, model, log):
        from fcp_pdf.server.ops_compose import _escape
        assert _escape("<script>") == "&lt;script&gt;"
        assert _escape("A & B") == "A &amp; B"

    def test_to_html_produces_valid_output(self, adapter, model, log):
        from fcp_pdf.server.ops_compose import _get_buffer, _ContentBlock
        from fcp_pdf.server.resolvers import PdfOpContext

        ctx = PdfOpContext(doc=model.doc, model=model)
        buf = _get_buffer(ctx)

        buf.add(_ContentBlock(kind="heading", data={"text": "Title", "level": 1}))
        buf.add(_ContentBlock(kind="paragraph", data={"text": "Hello **world**"}))
        buf.add(_ContentBlock(kind="table", data={"headers": ["A", "B"], "rows": [["1", "2"]]}))
        buf.add(_ContentBlock(kind="list", data={"items": ["x", "y"], "ordered": False}))
        buf.add(_ContentBlock(kind="rule", data={}))

        html, css = buf.to_html()
        assert "<h1>" in html
        assert "<p>" in html
        assert "<table>" in html
        assert "<ul>" in html
        assert "<hr/>" in html
        assert "font-family" in css


# -- Complex document --

class TestComposeComplexDocument:
    def test_full_report(self, adapter, model, log):
        """Build a realistic multi-section report."""
        cmds = [
            'compose config paper:letter margin:72 footer:"Page {page}"',
            'compose heading "Annual Report 2024" level:1',
            'compose paragraph "Prepared by the Finance Team on January 15, 2025."',
            'compose rule',
            'compose heading "Executive Summary" level:2',
            'compose paragraph "FY2024 was a **transformative year** for the organization. Revenue grew *38%* year-over-year, driven by enterprise expansion and strategic partnerships."',
            'compose spacer height:8',
            'compose heading "Financial Overview" level:2',
            'compose table "Metric" "FY2023" "FY2024" "Change"',
            'compose row "Revenue" "$12.4M" "$17.1M" "+38%"',
            'compose row "Gross Margin" "68%" "72%" "+4pp"',
            'compose row "Operating Income" "$1.2M" "$3.4M" "+183%"',
            'compose row "Headcount" "86" "124" "+44%"',
            'compose heading "Strategic Priorities" level:2',
            'compose list "Expand enterprise sales team to 30 AEs" "Launch self-serve product tier" "Enter European market (UK, DE, FR)" "Achieve SOC 2 Type II certification"',
            'compose heading "Risks" level:2',
            'compose ordered-list "Market downturn affecting enterprise budgets" "Key person dependency in engineering" "Competitive pressure from incumbents"',
            'compose blockquote "The best way to predict the future is to create it."',
            'compose pagebreak',
            'compose heading "Appendix" level:2',
            'compose paragraph "Detailed financial statements are available upon request."',
            'compose code "SELECT SUM(revenue) FROM orders WHERE fiscal_year = 2024 GROUP BY quarter"',
            "compose render",
        ]

        for cmd in cmds:
            r = _dispatch(adapter, model, log, cmd)
            assert r.success, f"Failed: {cmd} → {r.message}"

        # Should produce at least 2 pages (we have a pagebreak)
        assert len(model.doc) >= 2

        # Verify key content
        all_text = ""
        for i in range(len(model.doc)):
            all_text += model.doc[i].get_text()

        assert "Annual Report 2024" in all_text
        assert "Revenue" in all_text
        assert "$17.1M" in all_text
        assert "enterprise sales" in all_text.lower() or "Enterprise" in all_text
        assert "Appendix" in all_text

        # Verify footer
        assert "Page 1" in model.doc[0].get_text()


# -- Error handling --

class TestComposeErrors:
    def test_unknown_action(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose bogus")
        assert not r.success

    def test_heading_no_text(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose heading")
        assert not r.success

    def test_paragraph_no_text(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose paragraph")
        assert not r.success

    def test_blockquote_no_text(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose blockquote")
        assert not r.success

    def test_code_no_text(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose code")
        assert not r.success

    def test_list_no_items(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose list")
        assert not r.success

    def test_columns_no_content(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose columns")
        assert not r.success

    def test_image_not_found(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose image "/tmp/nonexistent_xyz123.png"')
        assert not r.success

    def test_cover_no_title(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose cover")
        assert not r.success

    def test_callout_no_text(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose callout")
        assert not r.success

    def test_callout_bad_level(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose callout "Text" level:bogus')
        assert not r.success

    def test_badge_no_text(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose badge")
        assert not r.success

    def test_highlight_no_text(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose highlight")
        assert not r.success


# -- Themes --

class TestThemes:
    def test_set_theme(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose config theme:modern")
        assert r.success
        assert "modern" in r.message

    def test_set_theme_executive(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose config theme:executive")
        assert r.success

    def test_unknown_theme(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose config theme:nonexistent")
        assert not r.success
        assert "Available" in r.message

    def test_theme_affects_css(self, adapter, model, log):
        from fcp_pdf.server.ops_compose import _get_buffer
        from fcp_pdf.server.resolvers import PdfOpContext

        ctx = PdfOpContext(doc=model.doc, model=model)
        buf = _get_buffer(ctx)

        # Default theme
        _, css_default = buf.to_html()

        # Switch to ocean
        _dispatch(adapter, model, log, "compose config theme:ocean")
        buf = _get_buffer(ctx)
        _, css_ocean = buf.to_html()

        # CSS should differ (different colors)
        assert css_default != css_ocean
        assert "#023e8a" in css_ocean  # ocean heading color

    def test_all_themes_render(self, adapter, log):
        """Each theme should produce valid output."""
        from fcp_pdf.lib.themes import list_themes
        for theme_name in list_themes():
            m = adapter.create_empty(f"Test-{theme_name}", {})
            _dispatch(adapter, m, log, f"compose config theme:{theme_name}")
            _dispatch(adapter, m, log, 'compose heading "Title"')
            _dispatch(adapter, m, log, 'compose paragraph "Body text"')
            r = _dispatch(adapter, m, log, "compose render")
            assert r.success, f"Theme {theme_name} failed to render: {r.message}"


# -- Cover page --

class TestCoverPage:
    def test_cover_basic(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose cover "Annual Report"')
        assert r.success

    def test_cover_full(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose cover "Annual Report" subtitle:"Fiscal Year 2024" author:"Finance Team" date:"January 2025"')
        assert r.success
        assert "Annual Report" in r.message

    def test_cover_renders(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose cover "My Document" subtitle:"A Subtitle"')
        _dispatch(adapter, model, log, 'compose heading "Chapter 1"')
        _dispatch(adapter, model, log, 'compose paragraph "Content here."')
        r = _dispatch(adapter, model, log, "compose render")
        assert r.success
        assert len(model.doc) >= 2  # cover page + content page

        # Cover page should have the title
        cover_text = model.doc[0].get_text()
        assert "My Document" in cover_text


# -- Callout boxes --

class TestCallouts:
    def test_callout_info(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose callout "Check the docs." level:info title:"Note"')
        _dispatch(adapter, model, log, "compose render")
        text = model.doc[0].get_text()
        assert "Note" in text

    def test_callout_warning(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose callout "Danger ahead." level:warning')
        assert r.success

    def test_callout_success(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose callout "All tests passed." level:success title:"Success"')
        assert r.success

    def test_callout_error(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose callout "Build failed." level:error title:"Error"')
        assert r.success

    def test_all_callout_types_render(self, adapter, model, log):
        for level in ("info", "warning", "success", "error"):
            _dispatch(adapter, model, log, f'compose callout "Message for {level}" level:{level} title:"{level.upper()}"')
        r = _dispatch(adapter, model, log, "compose render")
        assert r.success


# -- Badges and highlights --

class TestBadgesHighlights:
    def test_badge(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose badge "NEW"')
        assert r.success

    def test_badge_custom_color(self, adapter, model, log):
        r = _dispatch(adapter, model, log, 'compose badge "BETA" color:#ffffff bg:#ff6600')
        assert r.success

    def test_highlight(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose highlight "This is an important callout paragraph."')
        r = _dispatch(adapter, model, log, "compose render")
        assert r.success


# -- Section numbering --

class TestNumbering:
    def test_numbering_on(self, adapter, model, log):
        _dispatch(adapter, model, log, "compose config numbering:on")
        _dispatch(adapter, model, log, 'compose heading "Introduction" level:1')
        _dispatch(adapter, model, log, 'compose heading "Background" level:2')
        _dispatch(adapter, model, log, 'compose heading "Methods" level:2')
        _dispatch(adapter, model, log, 'compose heading "Results" level:1')
        _dispatch(adapter, model, log, 'compose paragraph "Content."')
        r = _dispatch(adapter, model, log, "compose render")
        assert r.success

        text = model.doc[0].get_text()
        assert "1 Introduction" in text
        assert "1.1 Background" in text
        assert "1.2 Methods" in text
        assert "2 Results" in text


# -- Auto TOC --

class TestAutoTOC:
    def test_toc_generation(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose heading "Chapter 1" level:1')
        _dispatch(adapter, model, log, 'compose heading "Section 1.1" level:2')
        _dispatch(adapter, model, log, 'compose heading "Chapter 2" level:1')

        r = _dispatch(adapter, model, log, "compose toc")
        assert r.success
        assert "3 entries" in r.message

    def test_toc_empty(self, adapter, model, log):
        r = _dispatch(adapter, model, log, "compose toc")
        assert not r.success


# -- Auto bookmarks --

class TestAutoBookmarks:
    def test_bookmarks_from_render(self, adapter, model, log):
        _dispatch(adapter, model, log, 'compose heading "Chapter One" level:1')
        _dispatch(adapter, model, log, 'compose paragraph "Content."')
        _dispatch(adapter, model, log, 'compose heading "Chapter Two" level:1')
        _dispatch(adapter, model, log, 'compose paragraph "More content."')
        _dispatch(adapter, model, log, "compose render")

        toc = model.doc.get_toc()
        titles = [entry[1] for entry in toc]
        assert "Chapter One" in titles
        assert "Chapter Two" in titles


# -- Professional document --

class TestProfessionalDocument:
    def test_executive_report(self, adapter, model, log):
        """Full professional document with all features."""
        cmds = [
            "compose config theme:executive numbering:on paper:letter footer:\"Confidential — Page {page} of {pages}\"",
            'compose cover "Strategic Plan 2025" subtitle:"Board of Directors Presentation" author:"Office of the CEO" date:"March 2025"',
            'compose heading "Executive Summary" level:1',
            'compose callout "This document contains forward-looking statements subject to risks and uncertainties." level:warning title:"Disclaimer"',
            'compose paragraph "The 2025 strategic plan focuses on three pillars: **growth**, *operational excellence*, and `digital transformation`."',
            'compose heading "Financial Targets" level:2',
            'compose table "Metric" "2024 Actual" "2025 Target" "Growth"',
            'compose row "Revenue" "$18.2M" "$25.0M" "+37%"',
            'compose row "EBITDA" "$4.1M" "$6.5M" "+59%"',
            'compose row "Headcount" "124" "175" "+41%"',
            'compose heading "Strategic Initiatives" level:2',
            'compose ordered-list "Launch enterprise platform v2.0 (Q2)" "Expand to 3 EU markets (Q3)" "Achieve FedRAMP authorization (Q4)" "Acquire complementary SaaS tool (Q4)"',
            'compose callout "All initiatives have been reviewed and approved by the executive committee." level:success title:"Status"',
            'compose heading "Risk Assessment" level:2',
            'compose callout "Macro-economic headwinds may impact enterprise buying cycles in H2." level:error title:"High Risk"',
            'compose list "FX exposure from EU expansion" "Integration risk from M&A" "Talent retention in competitive market"',
            'compose highlight "Net risk score: MODERATE — mitigation plans in place for all Tier 1 risks."',
            'compose pagebreak',
            'compose heading "Appendix" level:1',
            'compose heading "Data Sources" level:2',
            'compose paragraph "Financial projections based on bottom-up model validated by external auditor."',
            'compose columns "Contact: strategy@acme.com" "Classification: Confidential"',
            "compose render",
        ]

        for cmd in cmds:
            r = _dispatch(adapter, model, log, cmd)
            assert r.success, f"Failed: {cmd} → {r.message}"

        assert len(model.doc) >= 3  # cover + content + appendix

        # Check bookmarks were generated
        toc = model.doc.get_toc()
        titles = [e[1] for e in toc]
        assert "Executive Summary" in titles or "1 Executive Summary" in titles

        # Save and verify round-trip
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            adapter.serialize(model, path)
            loaded = adapter.deserialize(path)
            assert len(loaded.doc) == len(model.doc)
        finally:
            os.unlink(path)
