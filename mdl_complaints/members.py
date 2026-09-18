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
from .courts import court_id_from_name, courtlistener_id, state_for_court_id
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
    plaintiff: str = ""
    attorneys: str = ""
    firms: str = ""
    docket_id: int | None = None

    @property
    def origin_court(self) -> str:
        """The district the case transferred *from*, if it transferred at all.

        Cases filed directly in the transferee district did not come from
        anywhere, so they have no originating court.
        """
        return "" if self.source == "cases-entered" else self.court_id

    @property
    def origin_state(self) -> str:
        """State of the originating district -- blank for direct-filed cases.

        This is a venue signal, not a residence: an MDL's transferee court
        accepts direct filings from plaintiffs nationwide, so the transferee
        district says nothing about where a direct-filing plaintiff lives.
        """
        return state_for_court_id(self.origin_court)

    @property
    def key(self) -> tuple[str, str]:
        return (self.court_id, self.case_number)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["origin_court"] = self.origin_court
        data["origin_state"] = self.origin_state
        return data


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
    on_progress: Any = None,
) -> int:
    """Fill in ``title`` on member cases in place. Returns requests spent.

    Queries are grouped by court and OR-batched, exactly as for complaints.
    ``max_requests`` caps the spend; because every response is cached, a capped
    run can simply be repeated to make further progress.

    ``on_progress`` is called after each batch so a long run can checkpoint its
    output. Without it a job that is interrupted late loses everything it has
    resolved, even though the responses themselves are cached.
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
            checkpoint = True
            pages = 0
            while True:
                for result in payload.get("results") or []:
                    if result.get("court_id") != court_id:
                        continue
                    member = index.get((court_id, result.get("docketNumber") or ""))
                    if member is None:
                        continue
                    name = (result.get("caseName") or "").strip()
                    if name and not member.title:
                        member.title, member.title_source = name, "docket"
                    # Parties ride along on the same response, so the plaintiff
                    # and counsel cost nothing beyond the title lookup.
                    if not member.plaintiff:
                        member.plaintiff = "; ".join(
                            plaintiffs_from_parties(result.get("party"))
                        )
                    if not member.attorneys:
                        member.attorneys = "; ".join(result.get("attorney") or [])
                    if not member.firms:
                        member.firms = "; ".join(result.get("firm") or [])
                    if member.docket_id is None:
                        member.docket_id = result.get("docket_id")
                pages += 1
                next_url = payload.get("next")
                if not next_url or pages >= MAX_PAGES_PER_BATCH:
                    break
                if max_requests is not None and spent >= max_requests:
                    return spent
                payload = client.get(next_url)
                spent += 1
            if checkpoint and on_progress is not None:
                on_progress(spent)
    return spent


#: Parties common to every case in a products-liability MDL. Matched as whole
#: words so a plaintiff surnamed e.g. "Cole" is not mistaken for a company.
DEFENDANT_KEYWORDS = (
    "PFIZER", "VIATRIS", "PHARMACIA", "UPJOHN", "GREENSTONE", "PRASCO",
)
#: Corporate suffixes; an individual plaintiff never carries one.
_ORG_SUFFIX_RE = re.compile(
    r"\b(INC|LLC|L\.L\.C|LP|LLP|CO|CORP|CORPORATION|COMPANY|LTD|PLC|N\.V|S\.A)\b\.?$",
    re.IGNORECASE,
)


def is_defendant(party: str) -> bool:
    """True when a party name looks like a corporate defendant.

    >>> is_defendant("PFIZER INC")
    True
    >>> is_defendant("GREENSTONE LLC")
    True
    >>> is_defendant("ISABELLE CARRIGAN-BRODA")
    False
    """
    name = (party or "").strip().upper()
    if not name:
        return True
    if any(keyword in name for keyword in DEFENDANT_KEYWORDS):
        return True
    return bool(_ORG_SUFFIX_RE.search(name))


def plaintiffs_from_parties(parties: Iterable[str]) -> list[str]:
    """Keep only the parties that are not corporate defendants.

    >>> plaintiffs_from_parties(["PFIZER INC", "DONNA TONEY", "PHARMACIA LLC"])
    ['DONNA TONEY']
    """
    return [p.strip() for p in parties or [] if p and not is_defendant(p)]
