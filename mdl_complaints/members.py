"""Extract the MDL's member cases from the master docket.

A master docket accumulates member cases three ways, and all three name the
cases in the *text* of a docket entry:

* ``NOTICE OF POTENTIAL TAG-ALONG`` -- a case proposed for the MDL.
* ``CONDITIONAL TRANSFER ORDER`` -- a tag-along actually transferred in.
* ``XYZ CASES ENTERED`` -- cases filed directly in the transferee district.

Because the case numbers are in the entry descriptions, the whole member list
comes out of the pages already fetched for the complaint scan, at no extra
request cost.  Resolving each member's *caption* does cost requests, so that is
a separate, budgeted step.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from .client import API_ROOT, CourtListenerClient
from .courts import court_id_from_name, courtlistener_id
from .titles import BATCH_SIZE, MAX_PAGES_PER_BATCH, _build_query

#: "Florida Northern District Court (3:26-cv-04417,3:26-cv-04418)"
_COURT_BLOCK_RE = re.compile(r"([A-Z][A-Za-z ]+?) District Court \(([^)]*)\)")
#: "MN/0:26-cv-00123" -- a court code and number joined by a slash.
_SLASH_RE = re.compile(r"\b([A-Z]{2,4})/(\d+:\d{2}-[a-z]{2}-\d+)")
_NUMBER_RE = re.compile(r"\d+:\d{2}-[a-z]{2}-\d+")

#: How an entry introduced a case, most authoritative first.
SOURCE_RANK = {
    "motion-to-transfer": 0,
    "conditional-transfer-order": 1,
    "cases-entered": 2,
    "tag-along": 3,
    "other": 4,
}


def classify_entry(description: str) -> str:
    """Bucket a docket entry by how it brings member cases in."""
    text = (description or "").upper()
    if text.startswith("MOTION TO TRANSFER"):
        return "motion-to-transfer"
    if "CONDITIONAL TRANSFER ORDER" in text:
        return "conditional-transfer-order"
    if text.startswith("XYZ CASES ENTERED"):
        return "cases-entered"
    if "TAG-ALONG" in text or "NOTICE OF RELATED ACTION" in text:
        return "tag-along"
    return "other"


@dataclass
class MemberCase:
    """One case associated with the MDL."""

    court_id: str
    case_number: str
    source: str
    entry_number: int | None
    date_filed: str | None
    title: str = ""
    title_source: str = ""

    @property
    def key(self) -> tuple[str, str]:
        return (self.court_id, self.case_number)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_members(entries: Iterable[dict[str, Any]]) -> list[MemberCase]:
    """Pull every member case out of the master docket's entry descriptions.

    Cases are de-duplicated across entries, keeping the most authoritative
    mention -- a case usually appears first as a tag-along notice and later on
    the transfer order that actually moved it.
    """
    found: dict[tuple[str, str], MemberCase] = {}

    def record(court_id: str, number: str, entry: dict[str, Any], source: str) -> None:
        if not court_id or not number:
            return
        case = MemberCase(
            court_id=court_id,
            case_number=number,
            source=source,
            entry_number=entry.get("entry_number"),
            date_filed=entry.get("date_filed"),
        )
        existing = found.get(case.key)
        if existing is None or SOURCE_RANK[source] < SOURCE_RANK[existing.source]:
            found[case.key] = case

    for entry in entries:
        description = entry.get("description") or ""
        source = classify_entry(description)
        for match in _COURT_BLOCK_RE.finditer(description):
            court_id = court_id_from_name(match.group(1))
            for number in _NUMBER_RE.findall(match.group(2)):
                record(court_id, number, entry, source)
        for match in _SLASH_RE.finditer(description):
            record(courtlistener_id(match.group(1)), match.group(2), entry, source)

    return sorted(found.values(), key=lambda c: (c.court_id, c.case_number))


def resolve_member_titles(
    client: CourtListenerClient,
    members: list[MemberCase],
    *,
    max_requests: int | None = None,
    batch_size: int = BATCH_SIZE,
) -> int:
    """Fill in ``title`` on member cases in place. Returns requests spent.

    Queries are grouped by court and OR-batched, exactly as for complaints.
    ``max_requests`` caps the spend; because every response is cached, a capped
    run can simply be repeated to make further progress.
    """
    by_court: dict[str, list[MemberCase]] = {}
    for member in members:
        if member.court_id and not member.title:
            by_court.setdefault(member.court_id, []).append(member)

    index = {(m.court_id, m.case_number): m for m in members}
    spent = 0

    for court_id, cases in sorted(by_court.items()):
        numbers = [c.case_number for c in cases]
        for start in range(0, len(numbers), batch_size):
            if max_requests is not None and spent >= max_requests:
                return spent
            batch = numbers[start : start + batch_size]
            payload = client.get(
                f"{API_ROOT}/search/",
                {"type": "d", "court": court_id, "q": _build_query(batch)},
            )
            spent += 1
            pages = 0
            while True:
                for result in payload.get("results") or []:
                    if result.get("court_id") != court_id:
                        continue
                    member = index.get((court_id, result.get("docketNumber") or ""))
                    name = (result.get("caseName") or "").strip()
                    if member is not None and name and not member.title:
                        member.title, member.title_source = name, "docket"
                pages += 1
                next_url = payload.get("next")
                if not next_url or pages >= MAX_PAGES_PER_BATCH:
                    break
                if max_requests is not None and spent >= max_requests:
                    return spent
                payload = client.get(next_url)
                spent += 1
    return spent
