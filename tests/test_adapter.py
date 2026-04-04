"""Tests for PdfAdapter — full lifecycle tests."""

from __future__ import annotations

import os
import tempfile

import fitz
import pytest

from fcp_core import EventLog, parse_op
from fcp_pdf.adapter import PdfAdapter
from fcp_pdf.model.snapshot import PdfModel, SnapshotEvent


@pytest.fixture
def adapter():
    return PdfAdapter()


@pytest.fixture
def model(adapter):
    return adapter.create_empty("Test", {})


@pytest.fixture
def log():
    return EventLog()


@pytest.fixture
def model_with_pages(adapter, model, log):
    """Model with 3 pages of content."""
    for i in range(3):
        op = parse_op(f"page add")
        adapter.dispatch_op(op, model, log)
    # Add text to page 1
    op = parse_op('insert-text "Hello World" x:72 y:100 on:1')
    adapter.dispatch_op(op, model, log)
    return model


# -- Session lifecycle --

class TestSessionLifecycle:
    def test_create_empty(self, adapter):
        model = adapter.create_empty("My Doc", {})
        assert model.title == "My Doc"
        assert len(model.doc) == 0

    def test_serialize_deserialize(self, adapter, model_with_pages):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            adapter.serialize(model_with_pages, path)
            assert os.path.isfile(path)

            loaded = adapter.deserialize(path)
            assert len(loaded.doc) == 3
            assert loaded.file_path == path
        finally:
            os.unlink(path)

    def test_digest(self, adapter, model_with_pages):
        digest = adapter.get_digest(model_with_pages)
        assert "Pages: 3" in digest
        assert "Active: page" in digest


# -- Page operations --

class TestPageOps:
    def test_add_page(self, adapter, model, log):
        op = parse_op("page add")
        result = adapter.dispatch_op(op, model, log)
        assert result.success
        assert len(model.doc) == 1

    def test_add_multiple_pages(self, adapter, model, log):
        op = parse_op("page add count:5")
        result = adapter.dispatch_op(op, model, log)
        assert result.success
        assert len(model.doc) == 5

    def test_remove_page(self, adapter, model_with_pages, log):
        assert len(model_with_pages.doc) == 3
        op = parse_op("page remove 2")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert len(model_with_pages.doc) == 2

    def test_rotate_page(self, adapter, model_with_pages, log):
        op = parse_op("page rotate 1 angle:90")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert model_with_pages.doc[0].rotation == 90

    def test_copy_page(self, adapter, model_with_pages, log):
        op = parse_op("page copy 1")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert len(model_with_pages.doc) == 4

    def test_activate_page(self, adapter, model_with_pages, log):
        op = parse_op("page activate 3")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert model_with_pages.active_page == 2

    def test_move_page(self, adapter, model_with_pages, log):
        op = parse_op("page move 1 to:3")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

    def test_remove_range(self, adapter, model_with_pages, log):
        op = parse_op("page remove 1-2")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert len(model_with_pages.doc) == 1


# -- Text operations --

class TestTextOps:
    def test_insert_text(self, adapter, model_with_pages, log):
        op = parse_op('insert-text "Test text" x:100 y:200 on:1')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert "inserted" in result.message.lower()

    def test_extract_text(self, adapter, model_with_pages, log):
        op = parse_op("text extract 1")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert "Hello World" in result.message

    def test_extract_text_blocks(self, adapter, model_with_pages, log):
        op = parse_op("text extract 1 format:blocks")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

    def test_extract_text_dict(self, adapter, model_with_pages, log):
        op = parse_op("text extract 1 format:dict")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success


# -- Annotation operations --

class TestAnnotationOps:
    def test_highlight(self, adapter, model_with_pages, log):
        op = parse_op('annotate highlight text:"Hello" on:1')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert "highlight" in result.message.lower()

    def test_underline(self, adapter, model_with_pages, log):
        op = parse_op('annotate underline text:"Hello" on:1')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

    def test_strikeout(self, adapter, model_with_pages, log):
        op = parse_op('annotate strikeout text:"Hello" on:1')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

    def test_sticky_note(self, adapter, model_with_pages, log):
        op = parse_op('annotate note x:100 y:100 content:"Review this" on:1')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert "note" in result.message.lower()

    def test_rect_annotation(self, adapter, model_with_pages, log):
        op = parse_op("annotate rect x:50 y:50 w:200 h:100 on:1 color:#FF0000")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

    def test_circle_annotation(self, adapter, model_with_pages, log):
        op = parse_op("annotate circle x:100 y:100 w:80 h:80 on:1")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

    def test_line_annotation(self, adapter, model_with_pages, log):
        op = parse_op("annotate line x:10 y:10 x1:200 y1:200 on:1")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

    def test_freetext_annotation(self, adapter, model_with_pages, log):
        op = parse_op('annotate freetext "Important!" x:72 y:300 w:200 h:30 on:1')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

    def test_text_not_found(self, adapter, model_with_pages, log):
        op = parse_op('annotate highlight text:"nonexistent" on:1')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert not result.success


# -- Bookmark operations --

class TestBookmarkOps:
    def test_add_bookmark(self, adapter, model_with_pages, log):
        op = parse_op('bookmark add "Chapter 1" page:1 level:1')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

    def test_list_bookmarks(self, adapter, model_with_pages, log):
        # Add then list
        adapter.dispatch_op(parse_op('bookmark add "Ch1" page:1'), model_with_pages, log)
        adapter.dispatch_op(parse_op('bookmark add "Ch2" page:2'), model_with_pages, log)

        op = parse_op("bookmark list")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert "Ch1" in result.message
        assert "Ch2" in result.message

    def test_remove_bookmark(self, adapter, model_with_pages, log):
        adapter.dispatch_op(parse_op('bookmark add "ToRemove" page:1'), model_with_pages, log)
        op = parse_op('bookmark remove "ToRemove"')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert "removed" in result.message.lower()


# -- Metadata operations --

class TestMetaOps:
    def test_set_metadata(self, adapter, model_with_pages, log):
        op = parse_op('meta set title:"My Report" author:"Test Author"')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

    def test_get_metadata(self, adapter, model_with_pages, log):
        adapter.dispatch_op(
            parse_op('meta set title:"My Report" author:"Test Author"'),
            model_with_pages, log,
        )
        op = parse_op("meta get")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert "My Report" in result.message


# -- Merge / Split --

class TestMergeSplit:
    def test_split_and_merge(self, adapter, model_with_pages, log):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            split_path = f.name
        try:
            # Split pages 1-2
            op = parse_op(f'split "{split_path}" pages:1-2')
            result = adapter.dispatch_op(op, model_with_pages, log)
            assert result.success
            assert os.path.isfile(split_path)

            # Verify split file has 2 pages
            check = fitz.open(split_path)
            assert len(check) == 2
            check.close()

            # Merge back
            op = parse_op(f'merge "{split_path}"')
            result = adapter.dispatch_op(op, model_with_pages, log)
            assert result.success
            assert len(model_with_pages.doc) == 5  # 3 + 2
        finally:
            os.unlink(split_path)


# -- Redact --

class TestRedact:
    def test_redact_text(self, adapter, model_with_pages, log):
        op = parse_op('redact "Hello" on:1')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

        # Verify text is gone
        text = model_with_pages.doc[0].get_text()
        assert "Hello" not in text


# -- Link operations --

class TestLinkOps:
    def test_add_uri_link(self, adapter, model_with_pages, log):
        op = parse_op('link add on:1 x:72 y:72 w:100 h:20 uri:https://example.com')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

    def test_add_internal_link(self, adapter, model_with_pages, log):
        op = parse_op("link add on:1 x:72 y:150 w:100 h:20 page:2")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success

    def test_list_links(self, adapter, model_with_pages, log):
        # Add a link first
        adapter.dispatch_op(
            parse_op('link add on:1 x:72 y:72 w:100 h:20 uri:https://example.com'),
            model_with_pages, log,
        )
        op = parse_op("link list on:1")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert "example.com" in result.message


# -- Image operations --

class TestImageOps:
    def test_list_images_empty(self, adapter, model_with_pages, log):
        op = parse_op("image list")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert "no images" in result.message.lower()

    def test_insert_image(self, adapter, model_with_pages, log):
        # Create a small test image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img_path = f.name
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100), 1)
            pix.set_rect(pix.irect, (255, 0, 0, 255))  # red square (RGBA)
            pix.save(img_path)
        try:
            op = parse_op(f'image insert "{img_path}" on:1 x:72 y:200 w:100 h:100')
            result = adapter.dispatch_op(op, model_with_pages, log)
            assert result.success

            # Verify image is embedded
            images = model_with_pages.doc[0].get_images()
            assert len(images) >= 1
        finally:
            os.unlink(img_path)


# -- Undo / Redo --

class TestUndoRedo:
    def test_snapshot_round_trip(self, model_with_pages):
        original_count = len(model_with_pages.doc)
        snap = model_with_pages.snapshot()

        # Mutate
        model_with_pages.doc.new_page()
        assert len(model_with_pages.doc) == original_count + 1

        # Restore
        model_with_pages.restore(snap)
        assert len(model_with_pages.doc) == original_count

    def test_undo_via_adapter(self, adapter, model, log):
        # Add a page
        op = parse_op("page add")
        adapter.dispatch_op(op, model, log)
        assert len(model.doc) == 1
        assert len(log) == 1

        # Undo
        events = log.undo(1)
        assert len(events) == 1
        adapter.reverse_event(events[0], model)
        assert len(model.doc) == 0

        # Redo
        events = log.redo(1)
        assert len(events) == 1
        adapter.replay_event(events[0], model)
        assert len(model.doc) == 1


# -- Query dispatch --

class TestQueries:
    def test_query_plan(self, adapter, model_with_pages):
        result = adapter.dispatch_query("plan", model_with_pages)
        assert "Pages: 3" in result
        assert "Page 1" in result

    def test_query_status(self, adapter, model_with_pages):
        result = adapter.dispatch_query("status", model_with_pages)
        assert "Pages: 3" in result

    def test_query_describe(self, adapter, model_with_pages):
        result = adapter.dispatch_query("describe 1", model_with_pages)
        assert "Page 1" in result

    def test_query_find(self, adapter, model_with_pages):
        result = adapter.dispatch_query("find Hello", model_with_pages)
        assert "Page 1" in result

    def test_query_find_no_match(self, adapter, model_with_pages):
        result = adapter.dispatch_query("find xyznonexistent", model_with_pages)
        assert "No matches" in result

    def test_query_toc(self, adapter, model_with_pages, log):
        adapter.dispatch_op(
            parse_op('bookmark add "Intro" page:1'), model_with_pages, log
        )
        result = adapter.dispatch_query("toc", model_with_pages)
        assert "Intro" in result

    def test_query_fonts(self, adapter, model_with_pages):
        result = adapter.dispatch_query("fonts", model_with_pages)
        # Should list helv since we inserted text
        assert "helv" in result.lower() or "Helvetica" in result or "No fonts" in result

    def test_query_annots_empty(self, adapter, model_with_pages):
        result = adapter.dispatch_query("annots", model_with_pages)
        assert "No annotations" in result or "annotation" in result.lower()

    def test_query_unknown(self, adapter, model_with_pages):
        result = adapter.dispatch_query("bogus", model_with_pages)
        assert "Unknown query" in result


# -- Watermark --

class TestWatermark:
    def test_watermark_all_pages(self, adapter, model_with_pages, log):
        op = parse_op('watermark "DRAFT" size:48 opacity:0.2 angle:45')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert "3 page(s)" in result.message

    def test_watermark_specific_pages(self, adapter, model_with_pages, log):
        op = parse_op('watermark "CONFIDENTIAL" pages:1-2')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert result.success
        assert "2 page(s)" in result.message


# -- Error handling --

class TestErrorHandling:
    def test_unknown_verb(self, adapter, model_with_pages, log):
        op = parse_op("bogus whatever")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert not result.success
        assert "Unknown verb" in result.message

    def test_page_out_of_range(self, adapter, model_with_pages, log):
        op = parse_op("page activate 99")
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert not result.success

    def test_empty_doc_text_extract(self, adapter, model, log):
        op = parse_op("text extract")
        result = adapter.dispatch_op(op, model, log)
        assert not result.success
        assert "no active page" in result.message.lower() or "No active" in result.message

    def test_merge_file_not_found(self, adapter, model_with_pages, log):
        op = parse_op('merge "/tmp/nonexistent_abc123.pdf"')
        result = adapter.dispatch_op(op, model_with_pages, log)
        assert not result.success


# -- Resolvers --

class TestResolvers:
    def test_parse_page_range(self):
        from fcp_pdf.server.resolvers import parse_page_range

        assert parse_page_range("1", 10) == [0]
        assert parse_page_range("1-3", 10) == [0, 1, 2]
        assert parse_page_range("1,3,5", 10) == [0, 2, 4]
        assert parse_page_range("1-3,7-9", 10) == [0, 1, 2, 6, 7, 8]
        assert parse_page_range("all", 5) == [0, 1, 2, 3, 4]
        assert parse_page_range("99", 10) is None
        assert parse_page_range("abc", 10) is None

    def test_parse_color(self):
        from fcp_pdf.server.resolvers import parse_color

        r, g, b = parse_color("#FF0000")
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(0.0)

        r, g, b = parse_color("F00")
        assert r == pytest.approx(1.0)

        with pytest.raises(ValueError):
            parse_color("ZZZZ")
