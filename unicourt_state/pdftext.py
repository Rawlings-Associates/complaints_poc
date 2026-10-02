"""Turn a downloaded PDF into plain text an agent (or a person) can read.

No names are parsed here. Every state and court lays its forms out
differently, so the CLI hands over the text and leaves reading it to the
caller. Pages are extracted in pypdf's layout mode, which keeps table rows
(such as an attached list of plaintiffs) on one line; long runs of spaces are
shortened to a three-space gap so columns stay apart without the padding.

A scanned page has no text layer and yields nothing (OCR is out of scope);
it is marked as such rather than guessed at.
"""

from __future__ import annotations

import re
from pathlib import Path

NO_TEXT = "[no text layer on this page: scanned?]"
_GAP = re.compile(r" {3,}")


def read_pages(path: Path) -> list[str]:
    """The text of every page, one string per page ('' for a page without text)."""
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - depends on the environment
        raise SystemExit("pypdf is required to read PDFs: pip install pypdf") from None
    return [_page_text(page) for page in PdfReader(str(path)).pages]


def _page_text(page) -> str:
    try:
        raw = page.extract_text(extraction_mode="layout")
    except Exception:  # layout mode trips on some fonts; plain mode still reads them
        raw = page.extract_text() or ""
    lines = (_GAP.sub("   ", line.strip()) for line in raw.splitlines())
    return "\n".join(line for line in lines if line)


def format_pages(pages: list[str]) -> str:
    """All pages as one text, each under a ``=== Page N of M ===`` line."""
    total = len(pages)
    return "\n\n".join(f"=== Page {n} of {total} ===\n{text or NO_TEXT}"
                       for n, text in enumerate(pages, 1))
