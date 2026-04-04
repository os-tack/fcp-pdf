"""Named color themes for professional documents.

Each theme defines a coordinated palette that the compose engine
uses for headings, table headers, accents, callouts, and body text.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Theme:
    """A coordinated color palette for document styling."""
    name: str
    # Core
    heading: str        # H1/H2 color
    subheading: str     # H3/H4 color
    body: str           # body text
    muted: str          # captions, footnotes
    # Accents
    accent: str         # primary accent (links, highlights)
    accent_bg: str      # accent background (light tint)
    # Table
    table_header_bg: str
    table_header_fg: str
    table_border: str
    table_stripe: str   # alternating row background
    # Callouts
    info_bg: str
    info_border: str
    info_fg: str
    warning_bg: str
    warning_border: str
    warning_fg: str
    success_bg: str
    success_border: str
    success_fg: str
    error_bg: str
    error_border: str
    error_fg: str
    # Structural
    rule: str           # horizontal rule color
    blockquote_border: str
    code_bg: str


# -- Built-in themes --

CORPORATE = Theme(
    name="corporate",
    heading="#1a1a2e",
    subheading="#16213e",
    body="#2d2d2d",
    muted="#6c757d",
    accent="#0066cc",
    accent_bg="#e8f0fe",
    table_header_bg="#1a1a2e",
    table_header_fg="#ffffff",
    table_border="#d0d0d0",
    table_stripe="#f8f9fa",
    info_bg="#e8f4fd",
    info_border="#0288d1",
    info_fg="#01579b",
    warning_bg="#fff8e1",
    warning_border="#f9a825",
    warning_fg="#e65100",
    success_bg="#e8f5e9",
    success_border="#43a047",
    success_fg="#1b5e20",
    error_bg="#fce4ec",
    error_border="#e53935",
    error_fg="#b71c1c",
    rule="#d0d0d0",
    blockquote_border="#0066cc",
    code_bg="#f5f5f5",
)

MODERN = Theme(
    name="modern",
    heading="#0f172a",
    subheading="#334155",
    body="#374151",
    muted="#9ca3af",
    accent="#6366f1",
    accent_bg="#eef2ff",
    table_header_bg="#6366f1",
    table_header_fg="#ffffff",
    table_border="#e5e7eb",
    table_stripe="#f9fafb",
    info_bg="#eff6ff",
    info_border="#3b82f6",
    info_fg="#1e40af",
    warning_bg="#fffbeb",
    warning_border="#f59e0b",
    warning_fg="#92400e",
    success_bg="#f0fdf4",
    success_border="#22c55e",
    success_fg="#166534",
    error_bg="#fef2f2",
    error_border="#ef4444",
    error_fg="#991b1b",
    rule="#e5e7eb",
    blockquote_border="#6366f1",
    code_bg="#f1f5f9",
)

MINIMAL = Theme(
    name="minimal",
    heading="#111111",
    subheading="#333333",
    body="#222222",
    muted="#888888",
    accent="#111111",
    accent_bg="#f5f5f5",
    table_header_bg="#f0f0f0",
    table_header_fg="#111111",
    table_border="#e0e0e0",
    table_stripe="#fafafa",
    info_bg="#f5f5f5",
    info_border="#999999",
    info_fg="#333333",
    warning_bg="#f5f5f5",
    warning_border="#999999",
    warning_fg="#333333",
    success_bg="#f5f5f5",
    success_border="#999999",
    success_fg="#333333",
    error_bg="#f5f5f5",
    error_border="#999999",
    error_fg="#333333",
    rule="#cccccc",
    blockquote_border="#cccccc",
    code_bg="#f5f5f5",
)

EXECUTIVE = Theme(
    name="executive",
    heading="#1b2838",
    subheading="#2c3e50",
    body="#2c3e50",
    muted="#7f8c8d",
    accent="#c0392b",
    accent_bg="#fdedec",
    table_header_bg="#2c3e50",
    table_header_fg="#ecf0f1",
    table_border="#bdc3c7",
    table_stripe="#f8f9f9",
    info_bg="#eaf2f8",
    info_border="#2980b9",
    info_fg="#1a5276",
    warning_bg="#fef9e7",
    warning_border="#f39c12",
    warning_fg="#7d6608",
    success_bg="#eafaf1",
    success_border="#27ae60",
    success_fg="#1e8449",
    error_bg="#fdedec",
    error_border="#c0392b",
    error_fg="#922b21",
    rule="#bdc3c7",
    blockquote_border="#c0392b",
    code_bg="#f4f6f7",
)

OCEAN = Theme(
    name="ocean",
    heading="#023e8a",
    subheading="#0077b6",
    body="#264653",
    muted="#8ecae6",
    accent="#0096c7",
    accent_bg="#caf0f8",
    table_header_bg="#023e8a",
    table_header_fg="#ffffff",
    table_border="#90e0ef",
    table_stripe="#caf0f8",
    info_bg="#caf0f8",
    info_border="#0077b6",
    info_fg="#023e8a",
    warning_bg="#fff3cd",
    warning_border="#e9c46a",
    warning_fg="#795548",
    success_bg="#d1fae5",
    success_border="#2a9d8f",
    success_fg="#264653",
    error_bg="#fee2e2",
    error_border="#e76f51",
    error_fg="#9b2226",
    rule="#90e0ef",
    blockquote_border="#0077b6",
    code_bg="#edf6f9",
)

THEMES: dict[str, Theme] = {
    "corporate": CORPORATE,
    "modern": MODERN,
    "minimal": MINIMAL,
    "executive": EXECUTIVE,
    "ocean": OCEAN,
}

DEFAULT_THEME = CORPORATE


def get_theme(name: str) -> Theme | None:
    """Look up a theme by name (case-insensitive)."""
    return THEMES.get(name.lower())


def list_themes() -> list[str]:
    """Return available theme names."""
    return sorted(THEMES.keys())
