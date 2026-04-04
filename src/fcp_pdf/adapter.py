"""PdfAdapter — FcpDomainAdapter implementation for PyMuPDF documents.

Bridges fcp-core to PyMuPDF via PdfModel. Handles batch atomicity
and snapshot-based undo/redo.
"""

from __future__ import annotations

import fitz

from fcp_core import EventLog, OpResult, ParsedOp

from fcp_pdf.model.snapshot import PdfModel, SnapshotEvent
from fcp_pdf.server.queries import dispatch_query
from fcp_pdf.server.resolvers import PdfOpContext

# Import all handler dicts
from fcp_pdf.server.ops_pages import HANDLERS as PAGE_HANDLERS
from fcp_pdf.server.ops_text import HANDLERS as TEXT_HANDLERS
from fcp_pdf.server.ops_annotate import HANDLERS as ANNOTATE_HANDLERS
from fcp_pdf.server.ops_bookmark import HANDLERS as BOOKMARK_HANDLERS
from fcp_pdf.server.ops_merge import HANDLERS as MERGE_HANDLERS
from fcp_pdf.server.ops_meta import HANDLERS as META_HANDLERS
from fcp_pdf.server.ops_watermark import HANDLERS as WATERMARK_HANDLERS
from fcp_pdf.server.ops_image import HANDLERS as IMAGE_HANDLERS
from fcp_pdf.server.ops_redact import HANDLERS as REDACT_HANDLERS
from fcp_pdf.server.ops_link import HANDLERS as LINK_HANDLERS
from fcp_pdf.server.ops_compose import HANDLERS as COMPOSE_HANDLERS


class PdfAdapter:
    """FcpDomainAdapter[PdfModel, SnapshotEvent] for PDF operations."""

    def __init__(self) -> None:
        # Merge all verb handlers
        self._handlers: dict[str, callable] = {}
        for h in (
            PAGE_HANDLERS, TEXT_HANDLERS, ANNOTATE_HANDLERS,
            BOOKMARK_HANDLERS, MERGE_HANDLERS, META_HANDLERS,
            WATERMARK_HANDLERS, IMAGE_HANDLERS, REDACT_HANDLERS,
            LINK_HANDLERS, COMPOSE_HANDLERS,
        ):
            self._handlers.update(h)

    # -- FcpDomainAdapter protocol --

    def create_empty(self, title: str, params: dict[str, str]) -> PdfModel:
        """Create a new empty PDF document."""
        doc = fitz.open()
        model = PdfModel(title=title, doc=doc)
        return model

    def serialize(self, model: PdfModel, path: str) -> None:
        """Save PDF to file."""
        model.doc.save(path, garbage=3, deflate=True)
        model.file_path = path

    def deserialize(self, path: str) -> PdfModel:
        """Load PDF from file."""
        doc = fitz.open(path)
        title = path.rsplit("/", 1)[-1]
        model = PdfModel(title=title, doc=doc)
        model.file_path = path
        return model

    def rebuild_indices(self, model: PdfModel) -> None:
        """Rebuild index after undo/redo. Clamp active page."""
        if len(model.doc) == 0:
            model.active_page = 0
        elif model.active_page >= len(model.doc):
            model.active_page = len(model.doc) - 1

    def get_digest(self, model: PdfModel) -> str:
        """Return a compact state fingerprint."""
        doc = model.doc
        page_count = len(doc)
        active = model.active_page + 1

        # Quick stats
        total_images = 0
        total_annots = 0
        for i in range(page_count):
            page = doc[i]
            total_images += len(page.get_images())
            for _ in page.annots():
                total_annots += 1

        parts = [f"Active: page {active}", f"Pages: {page_count}"]
        if total_images:
            parts.append(f"Images: {total_images}")
        if total_annots:
            parts.append(f"Annotations: {total_annots}")

        return ", ".join(parts)

    def dispatch_op(
        self, op: ParsedOp, model: PdfModel, log: EventLog
    ) -> OpResult:
        """Execute a parsed operation on the model."""
        handler = self._handlers.get(op.verb)
        if handler is None:
            from fcp_core import suggest
            s = suggest(op.verb, list(self._handlers.keys()))
            msg = f"Unknown verb: {op.verb!r}"
            if s:
                msg += f"\n  try: {s}"
            return OpResult(success=False, message=msg)

        # Take pre-op snapshot
        before = model.snapshot()

        # Build context
        ctx = PdfOpContext(doc=model.doc, model=model)

        # Dispatch
        try:
            result = handler(op, ctx)
        except NotImplementedError as exc:
            return OpResult(success=False, message=str(exc))
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            return OpResult(success=False, message=f"Error: {exc}")

        if not result.success:
            return result

        # Log snapshot for undo
        after = model.snapshot()
        log.append(SnapshotEvent(before=before, after=after, summary=op.raw))

        return result

    def take_snapshot(self, model: PdfModel) -> bytes:
        """Return byte snapshot for batch rollback."""
        return model.snapshot()

    def restore_snapshot(self, model: PdfModel, snapshot: bytes) -> None:
        """Restore model from snapshot and rebuild indices."""
        model.restore(snapshot)
        self.rebuild_indices(model)

    def dispatch_query(self, query: str, model: PdfModel) -> str:
        """Execute a query against the model."""
        return dispatch_query(query, model)

    def reverse_event(self, event: SnapshotEvent, model: PdfModel) -> None:
        """Undo — restore from before-snapshot."""
        model.restore(event.before)
        self.rebuild_indices(model)

    def replay_event(self, event: SnapshotEvent, model: PdfModel) -> None:
        """Redo — restore from after-snapshot."""
        model.restore(event.after)
        self.rebuild_indices(model)
