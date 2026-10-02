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
from .titles import plaintiff_from_complaint_text, resolve_titles

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
#: A court and case number anywhere in a description, e.g. the mislabelled
#: ``Exhibit A Docket Sheet & Complaint - FLN/3:24-00624``.
_EMBEDDED_CASE_RE = re.compile(
    r"\b(?P<court>[A-Z]{2,5})\s*[/ ]\s*(?P<case>\d+:\d+-[\w-]*\d)"
)


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
    """One document from the MDL docket.

    Normally a member-case complaint attached to a motion to transfer; with
    ``all_documents`` it can be any document, and ``labelled_complaint`` says
    whether the docket itself called it a complaint.
    """

    mdl_number: str
    entry_number: int | None
    entry_date_filed: str | None
    attachment_number: int | None
    description: str
    court_code: str
    court_name: str
    case_number: str
    case_number_normalized: str
    title: str
    title_source: str
    page_count: int | None
    is_available: bool
    document_id: int
    pdf_url: str
    courtlistener_url: str
    labelled_complaint: bool = True

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


def parse_document_description(text: str) -> tuple[str, str]:
    """Like :func:`parse_complaint_description`, for any document.

    Complaints are often filed under another label, so a court and case number
    found anywhere in the description is used when the label is not
    ``Complaint ...``.

    >>> parse_document_description("Complaint CAN 3:24-6875")
    ('CAN', '3:24-6875')
    >>> parse_document_description("Exhibit A Docket Sheet & Complaint - FLN/3:24-00624")
    ('FLN', '3:24-00624')
    >>> parse_document_description("Proof of Service")
    ('', '')
    """
    code, case_number = parse_complaint_description(text)
    if case_number:
        return code, case_number
    match = _EMBEDDED_CASE_RE.search(text or "")
    if not match:
        return code, ""
    return match.group("court"), match.group("case")


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
    max_pages: int = 0,
    oldest_first: bool = True,
) -> tuple[list[dict[str, Any]], bool]:
    """Return ``(entries, truncated)``, oldest first by default.

    Ordering is what keeps this cheap: the motion that creates an MDL is entry
    1, so ascending order puts it on the first page.  The API default is
    newest-first, which on a mature docket means paging through hundreds of
    entries to reach the very thing we want.

    ``max_pages`` of 0 fetches every page.  ``truncated`` reports that more
    pages exist but were not fetched, so the caller can tell "nothing more to
    find" apart from "stopped looking".
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
        if max_pages and pages >= max_pages:
            return entries, True
        payload = client.get(next_url)


def collect_complaints(
    client: CourtListenerClient,
    mdl_number: str,
    *,
    entry_prefix: str | None = None,
    max_pages: int = 0,
    available_only: bool = False,
    with_titles: bool = True,
    pdf_fallback: bool = True,
    all_documents: bool = False,
    doc_match: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[Complaint], bool]:
    """Return ``(docket, matching_entries, complaints, truncated)``.

    ``entry_prefix`` of ``None`` scans every docket entry; pass
    ``"MOTION TO TRANSFER"`` to narrow to the motions that created the MDL.
    ``max_pages`` of 0 means "all pages".

    Complaints are often mislabelled (``Exhibit A Docket Sheet & Complaint``),
    so ``all_documents`` keeps every document -- main filings and attachments
    alike -- rather than only those described as ``Complaint``.
    ``doc_match`` keeps documents whose description matches that regular
    expression (case-insensitive), whatever their label.
    """
    docket = find_docket(client, mdl_number)
    prefix = (entry_prefix or "").strip().upper()
    pattern = re.compile(doc_match, re.IGNORECASE) if doc_match else None

    matching: list[dict[str, Any]] = []
    complaints: list[Complaint] = []
    seen: set[int] = set()
    # The OCR text is already in the payload, so the PDF fallback is free.
    texts: dict[int, str] = {}

    entries, truncated = fetch_entries(client, docket["id"], max_pages=max_pages)
    for entry in entries:
        description = (entry.get("description") or "").strip()
        if prefix and not description.upper().startswith(prefix):
            continue
        matching.append(entry)
        for doc in entry.get("recap_documents") or []:
            labelled = is_complaint(doc)
            # The main filing has no description of its own; the entry's is it.
            label = (doc.get("description") or "").strip() or description
            if pattern:
                if not pattern.search(label):
                    continue
            elif not (all_documents or labelled):
                continue
            if available_only and not doc.get("is_available"):
                continue
            if doc["id"] in seen:
                continue
            seen.add(doc["id"])
            texts[doc["id"]] = doc.get("plain_text") or ""
            if labelled:
                code, case_number = parse_complaint_description(label)
            else:
                code, case_number = parse_document_description(
                    doc.get("description") or ""
                )
            absolute = doc.get("absolute_url") or ""
            complaints.append(
                Complaint(
                    mdl_number=docket.get("docket_number", ""),
                    entry_number=entry.get("entry_number"),
                    entry_date_filed=entry.get("date_filed"),
                    attachment_number=doc.get("attachment_number"),
                    description=label,
                    court_code=code,
                    court_name=expand_court_code(code),
                    case_number=case_number,
                    case_number_normalized=normalize_case_number(case_number),
                    title="",
                    title_source="",
                    page_count=doc.get("page_count"),
                    is_available=bool(doc.get("is_available")),
                    document_id=doc["id"],
                    pdf_url=_pdf_url(doc),
                    courtlistener_url=(
                        f"{COURTLISTENER_ROOT}{absolute}" if absolute else ""
                    ),
                    labelled_complaint=labelled,
                )
            )

    if with_titles and complaints:
        _attach_titles(client, complaints, texts, use_pdf_fallback=pdf_fallback)

    complaints.sort(key=lambda c: (c.entry_number or 0, c.attachment_number or 0))
    return docket, matching, complaints, truncated


def collect_members(
    client: CourtListenerClient,
    mdl_number: str,
    *,
    max_pages: int = 0,
) -> tuple[dict[str, Any], list[Any], bool]:
    """Return ``(docket, member_cases, truncated)`` for an MDL number.

    The member list is parsed from entry descriptions, so this costs the same
    two-plus requests as the complaint scan and no more.
    """
    from .members import extract_members

    docket = find_docket(client, mdl_number)
    entries, truncated = fetch_entries(client, docket["id"], max_pages=max_pages)
    return docket, extract_members(entries), truncated


def _attach_titles(
    client: CourtListenerClient,
    complaints: list[Complaint],
    texts: dict[int, str],
    *,
    use_pdf_fallback: bool = True,
) -> None:
    """Fill in ``title``/``title_source`` in place.

    The member docket is authoritative.  Only where it has nothing do we fall
    back to the complaint PDF, and the source is recorded either way so a
    derived title is never mistaken for a looked-up one.
    """
    from .courts import courtlistener_id

    titles = resolve_titles(client, complaints)
    for complaint in complaints:
        key = (courtlistener_id(complaint.court_code), complaint.case_number_normalized)
        name = titles.get(key, "")
        if name:
            complaint.title, complaint.title_source = name, "docket"
            continue
        if use_pdf_fallback:
            plaintiff = plaintiff_from_complaint_text(texts.get(complaint.document_id, ""))
            if plaintiff:
                complaint.title, complaint.title_source = plaintiff, "complaint-pdf"
