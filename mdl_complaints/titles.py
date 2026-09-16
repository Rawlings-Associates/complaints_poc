"""Resolve member-case titles (captions) for complaints.

A complaint attachment is described only as ``Complaint CAN 3:24-6875`` -- the
case caption lives on the member docket, not on the JPML docket.  Titles are
therefore looked up through the search endpoint.

Two things keep the request count down:

* Queries are **grouped by court**.  Docket numbers are not unique across
  courts -- ``1:24-cv-01831`` matches eight different districts -- so an
  ungrouped query returns mostly noise and spills over many result pages.
* Within a court, numbers are **OR-batched** into a single query.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Iterable

from .client import API_ROOT, CourtListenerClient
from .courts import courtlistener_id

#: Numbers per query. Kept modest so a court's results fit on one page.
BATCH_SIZE = 15
MAX_PAGES_PER_BATCH = 3

#: Complaint PDFs carry a signature block reading "Attorneys for Plaintiff
#: <name>". Checked against 26 known-good docket titles it agreed 16 times and
#: contradicted none, so it is a safe fallback -- but only a fallback, since it
#: yields the plaintiff rather than a full caption.
_PLAINTIFF_RE = re.compile(
    r"Attorneys?\s+for\s+Plaintiffs?\s+"
    r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){0,3})"
)
#: Only the first pages hold the caption; the rest is the body of the complaint.
_TEXT_WINDOW = 20_000


def plaintiff_from_complaint_text(text: str) -> str:
    """Best-effort plaintiff name from a complaint PDF's OCR text.

    Returns ``""`` when nothing matches, so the caller can leave the title
    blank instead of guessing.

    >>> plaintiff_from_complaint_text("Attorneys for Plaintiff Jamie Grubensky")
    'Jamie Grubensky'
    >>> plaintiff_from_complaint_text("no signature block here")
    ''
    """
    match = _PLAINTIFF_RE.search((text or "")[:_TEXT_WINDOW])
    return match.group(1).strip() if match else ""


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _build_query(case_numbers: Iterable[str]) -> str:
    quoted = " OR ".join(f'"{number}"' for number in case_numbers)
    return f"docketNumber:({quoted})"


def resolve_titles(
    client: CourtListenerClient,
    complaints: list[Any],
    *,
    max_requests: int | None = None,
) -> dict[tuple[str, str], str]:
    """Return ``{(court_id, normalized_case_number): case_name}``.

    Unresolvable complaints are simply absent from the mapping; the caller
    leaves those titles blank rather than guessing.
    """
    wanted: dict[str, set[str]] = defaultdict(set)
    for complaint in complaints:
        court_id = courtlistener_id(complaint.court_code)
        if court_id and complaint.case_number_normalized:
            wanted[court_id].add(complaint.case_number_normalized)

    titles: dict[tuple[str, str], str] = {}
    requests_made = 0

    for court_id, numbers in sorted(wanted.items()):
        for batch in _chunks(sorted(numbers), BATCH_SIZE):
            if max_requests is not None and requests_made >= max_requests:
                return titles
            url = f"{API_ROOT}/search/"
            params = {"type": "d", "court": court_id, "q": _build_query(batch)}
            payload = client.get(url, params)
            requests_made += 1

            pages = 0
            while True:
                for result in payload.get("results") or []:
                    _record(result, court_id, batch, titles)
                pages += 1
                next_url = payload.get("next")
                if not next_url or pages >= MAX_PAGES_PER_BATCH:
                    break
                if max_requests is not None and requests_made >= max_requests:
                    return titles
                payload = client.get(next_url)
                requests_made += 1

    return titles


def _record(
    result: dict[str, Any],
    court_id: str,
    batch: list[str],
    titles: dict[tuple[str, str], str],
) -> None:
    """Keep a search hit only if it is the court and case we asked about."""
    from .core import normalize_case_number

    if result.get("court_id") != court_id:
        return
    number = normalize_case_number(result.get("docketNumber") or "")
    if number not in batch:
        return
    name = (result.get("caseName") or "").strip()
    if name:
        titles.setdefault((court_id, number), name)
