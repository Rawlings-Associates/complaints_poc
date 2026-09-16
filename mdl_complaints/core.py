"""Domain logic: master docket number -> complaints under a motion to transfer.

An MDL is created by a motion to transfer filed with the JPML.  That motion
carries the member-case complaints as numbered attachments, so the complaints
are reachable without touching the member dockets at all.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .client import CourtListenerClient
from .courts import expand_court_code

JPML_COURT_ID = "jpml"
STORAGE_ROOT = "https://storage.courtlistener.com"
COURTLISTENER_ROOT = "https://www.courtlistener.com"

DEFAULT_ENTRY_PREFIX = "MOTION TO TRANSFER"

#: Attachment descriptions look like ``Complaint CAN 3:24-6875`` or
#: ``Complaint NDCA 3:24-cv-08746``.
_COMPLAINT_RE = re.compile(
    r"^complaints?\b[\s:.-]*(?P<court>[A-Z]{2,5})?\s*"
    r"(?P<case>\d+:\d+-[\w-]+)?",
    re.IGNORECASE,
)
#: office:year-[type-]number, where the type is often omitted by the JPML.
_CASE_RE = re.compile(
    r"^(?P<office>\d+):(?P<year>\d+)-(?:(?P<type>[a-z]{2})-)?(?P<number>\d+)$",
    re.IGNORECASE,
)
_MDL_DIGITS_RE = re.compile(r"(\d{2,5})")


class DocketNotFound(RuntimeError):
    pass


def normalize_mdl_number(raw: str) -> str:
    """Normalise user input into the exact string CourtListener stores.

    ``docket_number`` is an exact-match field on the API and there is no
    ``icontains`` lookup, so ``3140`` or ``md 3140`` silently return zero
    results.  Everything is funnelled through the canonical ``MDL No. 3140``.

    >>> normalize_mdl_number("3140")
    'MDL No. 3140'
    >>> normalize_mdl_number("md 3140")
    'MDL No. 3140'
    >>> normalize_mdl_number("  MDL-3140 ")
    'MDL No. 3140'
    """
    if raw is None:
        raise ValueError("MDL number is required")
    match = _MDL_DIGITS_RE.search(str(raw))
    if not match:
        raise ValueError(f"Could not find an MDL number in {raw!r}")
    return f"MDL No. {match.group(1)}"


@dataclass
class Complaint:
    """One member-case complaint attached to a motion to transfer."""

    mdl_number: str
    entry_number: int | None
    entry_date_filed: str | None
    attachment_number: int | None
    description: str
    court_code: str
    court_name: str
    case_number: str
    case_number_normalized: str
    page_count: int | None
    is_available: bool
    document_id: int
    pdf_url: str
    courtlistener_url: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _pdf_url(doc: dict[str, Any]) -> str:
    """Best available PDF link, preferring CourtListener's own storage."""
    local = doc.get("filepath_local")
    if local:
        return f"{STORAGE_ROOT}/{local}"
    return doc.get("filepath_ia") or ""


def normalize_case_number(case_number: str) -> str:
    """Canonicalise a member-case number so the same case matches across motions.

    The JPML drops the ``cv`` and leading zeros in some descriptions, so
    ``3:24-6875`` and ``3:24-cv-06875`` are the same case written two ways.

    >>> normalize_case_number("3:24-6875")
    '3:24-cv-06875'
    >>> normalize_case_number("1:24-cv-02105")
    '1:24-cv-02105'
    >>> normalize_case_number("")
    ''
    """
    match = _CASE_RE.match((case_number or "").strip())
    if not match:
        return case_number or ""
    case_type = (match.group("type") or "cv").lower()
    return (
        f"{match.group('office')}:{match.group('year')}-"
        f"{case_type}-{int(match.group('number')):05d}"
    )


def parse_complaint_description(text: str) -> tuple[str, str]:
    """Pull ``(court_code, case_number)`` out of an attachment description.

    >>> parse_complaint_description("Complaint CAN 3:24-6875")
    ('CAN', '3:24-6875')
    >>> parse_complaint_description("Complaint NDCA 3:24-cv-08746")
    ('NDCA', '3:24-cv-08746')
    >>> parse_complaint_description("Complaint")
    ('', '')
    """
    match = _COMPLAINT_RE.match(text or "")
    if not match:
        return "", ""
    return (match.group("court") or "").upper(), match.group("case") or ""


def is_complaint(doc: dict[str, Any]) -> bool:
    """True for attachments that are member-case complaints.

    ``document_type`` 2 means attachment; type 1 is the motion itself, which is
    never a complaint.
    """
    if doc.get("document_type") != 2:
        return False
    return bool(re.match(r"^\s*complaints?\b", doc.get("description") or "", re.I))


def find_docket(
    client: CourtListenerClient, mdl_number: str, court: str = JPML_COURT_ID
) -> dict[str, Any]:
    """Resolve an MDL number to its JPML docket. Costs one request."""
    canonical = normalize_mdl_number(mdl_number)
    payload = client.dockets(court=court, docket_number=canonical)
    results = payload.get("results") or []
    if not results:
        raise DocketNotFound(
            f"No {court} docket found for {canonical!r}. "
            "The MDL may not exist or may not be in CourtListener."
        )
    return results[0]


def fetch_entries(
    client: CourtListenerClient,
    docket_id: int,
    *,
    max_pages: int = 1,
    oldest_first: bool = True,
) -> tuple[list[dict[str, Any]], bool]:
    """Return ``(entries, truncated)``, oldest first by default.

    Ordering is what keeps this cheap: the motion that creates an MDL is entry
    1, so ascending order puts it on the first page.  The API default is
    newest-first, which on a mature docket means paging through hundreds of
    entries to reach the very thing we want.

    ``truncated`` reports that more pages exist but were not fetched, so the
    caller can tell "no more motions" apart from "stopped looking".
    """
    params: dict[str, Any] = {"docket": docket_id}
    if oldest_first:
        params["order_by"] = "date_filed"
    payload = client.docket_entries(**params)
    entries: list[dict[str, Any]] = []
    pages = 0
    while True:
        entries.extend(payload.get("results") or [])
        pages += 1
        next_url = payload.get("next")
        if not next_url:
            return entries, False
        if pages >= max_pages:
            return entries, True
        payload = client.get(next_url)


def collect_complaints(
    client: CourtListenerClient,
    mdl_number: str,
    *,
    entry_prefix: str = DEFAULT_ENTRY_PREFIX,
    max_pages: int = 1,
    available_only: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[Complaint], bool]:
    """Return ``(docket, matching_entries, complaints, truncated)``.

    Two requests in the normal case: one to resolve the docket, one for the
    first page of entries.
    """
    docket = find_docket(client, mdl_number)
    prefix = entry_prefix.strip().upper()

    matching: list[dict[str, Any]] = []
    complaints: list[Complaint] = []
    seen: set[int] = set()

    entries, truncated = fetch_entries(client, docket["id"], max_pages=max_pages)
    for entry in entries:
        description = (entry.get("description") or "").strip()
        if not description.upper().startswith(prefix):
            continue
        matching.append(entry)
        for doc in entry.get("recap_documents") or []:
            if not is_complaint(doc):
                continue
            if available_only and not doc.get("is_available"):
                continue
            if doc["id"] in seen:
                continue
            seen.add(doc["id"])
            code, case_number = parse_complaint_description(doc.get("description") or "")
            absolute = doc.get("absolute_url") or ""
            complaints.append(
                Complaint(
                    mdl_number=docket.get("docket_number", ""),
                    entry_number=entry.get("entry_number"),
                    entry_date_filed=entry.get("date_filed"),
                    attachment_number=doc.get("attachment_number"),
                    description=(doc.get("description") or "").strip(),
                    court_code=code,
                    court_name=expand_court_code(code),
                    case_number=case_number,
                    case_number_normalized=normalize_case_number(case_number),
                    page_count=doc.get("page_count"),
                    is_available=bool(doc.get("is_available")),
                    document_id=doc["id"],
                    pdf_url=_pdf_url(doc),
                    courtlistener_url=(
                        f"{COURTLISTENER_ROOT}{absolute}" if absolute else ""
                    ),
                )
            )

    complaints.sort(key=lambda c: (c.entry_number or 0, c.attachment_number or 0))
    return docket, matching, complaints, truncated
