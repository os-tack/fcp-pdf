"""Byte-snapshot undo/redo for PyMuPDF documents.

SnapshotEvent captures before/after states as bytes.
fitz documents serialize/deserialize via doc.tobytes()/fitz.open(stream=...).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import fitz


@dataclass
class SnapshotEvent:
    """Event type for byte-snapshot undo/redo."""

    type: str = "snapshot"
    before: bytes = field(default=b"", repr=False)
    after: bytes = field(default=b"", repr=False)
    summary: str = ""


class PdfModel:
    """Thin wrapper around fitz.Document for in-place undo/redo.

    The session dispatcher holds a reference to this object.
    reverse_event/replay_event replace self.doc in place so
    the session reference stays valid.
    """

    def __init__(self, title: str = "Untitled", doc: fitz.Document | None = None):
        self.title = title
        self.doc: fitz.Document = doc or fitz.open()
        self.file_path: str | None = None
        self.active_page: int = 0

    def snapshot(self) -> bytes:
        """Take a byte snapshot of the current document state."""
        if len(self.doc) == 0:
            # PyMuPDF can't serialize zero-page docs — return sentinel
            return b""
        return self.doc.tobytes(deflate=True, garbage=3)

    def restore(self, data: bytes) -> None:
        """Replace the document from snapshot bytes (in-place for undo/redo)."""
        self.doc.close()
        if data == b"":
            # Restore to empty doc
            self.doc = fitz.open()
        else:
            self.doc = fitz.open(stream=data, filetype="pdf")
