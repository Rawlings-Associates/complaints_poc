"""Pick a case's documents by name similarity, and fetch only free ones."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from .client import UniCourtClient, UniCourtError

# Document types in the order they are tried. Each has phrases a matching
# document name resembles, and words that mean "a different document that
# mentions this one" (an answer to a complaint is not a complaint).
DOC_TYPES: dict[str, dict[str, list[str]]] = {
    "civil-cover-sheet": {
        "phrases": [
            "civil cover sheet",
            "civil case cover sheet",
            "cover sheet",
            "civil case information sheet",
            "case information sheet",
            "case information statement",
            "civil action cover sheet",
        ],
        "exclude": ["addendum instructions", "instructions"],
    },
    "complaint": {
        "phrases": [
            "complaint",
            "complaint for damages",
            "amended complaint",
            "petition",
            "original petition",
            "plaintiffs original petition",
        ],
        "exclude": [
            "answer", "cross", "response", "reply", "motion", "demurrer",
            "opposition", "notice", "summons", "proof", "service", "exhibit",
            "memorandum", "order", "stipulation", "cover sheet", "withdraw",
            "removal", "dismiss",
        ],
    },
}

# Only the cover sheet by default; ask for complaints with --doc-types.
DEFAULT_ORDER = ("civil-cover-sheet",)
DEFAULT_THRESHOLD = 0.8


def normalize(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def phrase_similarity(text: str, phrase: str) -> float:
    """How closely ``text`` resembles ``phrase``, from 0 to 1.

    A whole-word containment is a full match ("Complaint for Damages" contains
    "complaint"). Otherwise the best of a character-level ratio (catches typos
    and OCR noise such as "Civil Covr Sheet") and the share of the phrase's
    words present in the text.
    """
    text, phrase = normalize(text), normalize(phrase)
    if not text or not phrase:
        return 0.0
    if re.search(rf"\b{re.escape(phrase)}\b", text):
        return 1.0
    ratio = SequenceMatcher(None, text, phrase).ratio()
    words = phrase.split()
    overlap = sum(1 for w in words if w in text.split()) / len(words)
    return max(ratio, 0.9 * overlap)


def score_document(doc: dict[str, Any], doc_type: str) -> float:
    spec = DOC_TYPES[doc_type]
    best = 0.0
    for field in ("name", "description"):
        text = normalize(doc.get(field))
        if not text:
            continue
        if any(re.search(rf"\b{re.escape(w)}", text) for w in spec["exclude"]):
            continue
        best = max(best, *(phrase_similarity(text, p) for p in spec["phrases"]))
    return best


def price_of(doc: dict[str, Any]) -> Decimal | None:
    """The document's price, or None when it is missing or unreadable."""
    price = doc.get("price")
    if price is None or isinstance(price, bool):
        return None
    try:
        value = Decimal(str(price))
    except (InvalidOperation, ValueError):
        return None
    return value if value.is_finite() and value >= 0 else None


def is_free(doc: dict[str, Any]) -> bool:
    """Free means an explicit price of zero. A missing or unreadable price is not free."""
    return price_of(doc) == 0


def is_sealed(doc: dict[str, Any]) -> bool:
    return doc.get("availabilityStatusAtCourtSource") == "SEALED"


@dataclass
class Candidate:
    """A case document whose name matched one of the wanted document types.

    ``doc_type`` is the ``DOC_TYPES`` key it matched (e.g. ``"complaint"``),
    ``score`` is its name similarity to that type (0-1, at least the
    threshold), and ``doc`` is the raw ``CaseDocument`` from the API. A
    candidate is only a match by name: whether it is downloaded still depends
    on ``free`` and on the user's confirmation.
    """

    doc_type: str
    score: float
    doc: dict[str, Any]

    @property
    def free(self) -> bool:
        return is_free(self.doc)

    @property
    def price(self) -> Decimal | None:
        return price_of(self.doc)

    @property
    def label(self) -> str:
        parts = [self.doc.get("name"), self.doc.get("description")]
        return " / ".join(p for p in parts if p) or self.doc.get("caseDocumentId", "?")


def rank(
    docs: Iterable[dict[str, Any]], doc_type: str, threshold: float = DEFAULT_THRESHOLD
) -> list[Candidate]:
    """Matching documents, best first; ties go to the earliest filed."""
    found = [
        Candidate(doc_type, s, d)
        for d in docs
        if (s := score_document(d, doc_type)) >= threshold
    ]
    found.sort(key=lambda c: (-c.score, c.doc.get("documentFiledDate") or ""))
    return found


def attempts(
    matches: dict[str, list[Candidate]], order: Iterable[str], include_paid: bool = False
) -> list[Candidate]:
    """The documents to try for one case, in order, until one gives readable text.

    Free documents come first (the best free match of each type, in type
    order). With ``include_paid``, the best priced match of each type that has
    no free match follows. Sealed documents and unknown prices never qualify.
    """
    order = list(order)
    free, paid = [], []
    for doc_type in order:
        usable = [c for c in matches.get(doc_type, []) if not is_sealed(c.doc)]
        free_here = [c for c in usable if c.free]
        if free_here:
            free.append(free_here[0])
        elif include_paid:
            priced = [c for c in usable if c.price is not None and c.price > 0]
            if priced:
                paid.append(priced[0])
    return free + paid


def match_all(
    docs: list[dict[str, Any]], order: Iterable[str], threshold: float = DEFAULT_THRESHOLD
) -> dict[str, list[Candidate]]:
    """Matches of each type, best first. A document counts for its first type only."""
    taken: set[str] = set()
    result: dict[str, list[Candidate]] = {}
    for doc_type in order:
        found = [c for c in rank(docs, doc_type, threshold)
                 if c.doc.get("caseDocumentId") not in taken]
        taken.update(c.doc.get("caseDocumentId") for c in found)
        result[doc_type] = found
    return result


def list_documents(client: UniCourtClient, case_id: str) -> list[dict[str, Any]]:
    params = {"sortBy": "oldest to latest"}  # 100 documents per page
    return list(client.paginate(f"case/{case_id}/documents", "caseDocumentArray", params))


PAID_NOT_SUPPORTED = (
    "Downloading paid documents is not supported. Only free documents (price 0) "
    "can be downloaded; use --dry-run with --include-paid --budget to plan and price paid ones."
)


class PaidDownloadNotSupported(RuntimeError):
    """Raised for any attempt to fetch a document that is not free."""

    def __init__(self, detail: str = ""):
        super().__init__(f"{PAID_NOT_SUPPORTED} {detail}".strip())


class DocumentUnavailable(RuntimeError):
    """The document could not be obtained (order failed, sealed, timed out)."""


def obtain_file_url(
    client: UniCourtClient,
    doc: dict[str, Any],
    priority: str = "level2",
    poll_seconds: float = 10,
    timeout_seconds: float = 1800,
    on_status=None,
    stop=None,
) -> str:
    """Signed URL for a free document.

    This is the only function that orders or downloads a document, and it
    fetches free documents only: anything with a price other than 0, or no
    readable price, raises ``PaidDownloadNotSupported``. The price is checked
    twice: on the listed document, then on a fresh copy fetched just before
    acting, so a stale listing cannot lead to a charge.

    A free document already in UniCourt's store downloads directly. One that
    is still at the court is ordered (``reOrder`` false, so nothing is fetched
    twice), polled until complete, then downloaded. ``stop`` (a
    ``threading.Event``) ends the wait early when the run is interrupted.
    """
    if not is_free(doc):
        raise PaidDownloadNotSupported(f"(listed price: {doc.get('price')!r})")
    doc = verify_free(client, doc["caseDocumentId"])
    doc_id = doc["caseDocumentId"]
    price = price_of(doc)

    if price == 0 and doc.get("repository") == "UNICOURT":
        return _download_url(client, doc_id)

    callback = client.put(
        "caseDocumentOrder",
        {
            "caseDocumentId": doc_id,
            "isPreviewOnly": False,
            "reOrder": False,
            "priorityLevel": priority,
            "notifyOnDelay": False,
        },
    )
    callback_id = callback.get("caseDocumentOrderCallbackId")
    deadline = time.monotonic() + timeout_seconds
    wait = poll_seconds
    while True:
        status = callback.get("status")
        if on_status:
            on_status(status)
        if status == "COMPLETE":
            url = (callback.get("file") or {}).get("fileUrl")
            return url or _download_url(client, doc_id)
        if status in ("FAILURE", "MANUAL"):
            exc = callback.get("exception") or {}
            raise DocumentUnavailable(
                f"order {callback_id} ended {status}: {exc.get('message', '')} {exc.get('details', '')}".strip()
            )
        if not callback_id or time.monotonic() > deadline:
            raise DocumentUnavailable(f"order {callback_id} still {status} after {timeout_seconds:.0f}s")
        if stop is None:
            time.sleep(wait)
        elif stop.wait(wait):
            raise DocumentUnavailable(f"order {callback_id} left {status}: run interrupted")
        wait = min(wait * 1.5, 60)
        callback = client.get(f"caseDocumentOrder/callbacks/{callback_id}")


def verify_free(client: UniCourtClient, doc_id: str) -> dict[str, Any]:
    """Re-read the document; refuse unless it is still free and not sealed."""
    try:
        fresh = client.get(f"caseDocument/{doc_id}")
    except UniCourtError as exc:
        raise DocumentUnavailable(f"could not confirm the price: {exc}") from None
    if not is_free(fresh):
        raise PaidDownloadNotSupported(f"(current price: {fresh.get('price')!r})")
    if is_sealed(fresh):
        raise DocumentUnavailable("document is sealed")
    return {**fresh, "caseDocumentId": fresh.get("caseDocumentId") or doc_id}


def _download_url(client: UniCourtClient, doc_id: str) -> str:
    try:
        result = client.get(f"caseDocumentDownload/{doc_id}")
    except UniCourtError as exc:
        raise DocumentUnavailable(str(exc)) from None
    url = result.get("fileUrl")
    if not url:
        exc = result.get("exception") or {}
        raise DocumentUnavailable(f"no download URL: {exc.get('message', '')} {exc.get('details', '')}".strip())
    return url


def pdf_filename(case: dict[str, Any], cand: Candidate) -> str:
    case_no = re.sub(r"[^A-Za-z0-9._-]+", "_", case.get("caseNumber") or case.get("caseId", "case"))
    return f"{case_no}_{cand.doc_type}_{cand.doc['caseDocumentId']}.pdf"


def download(client: UniCourtClient, url: str, dest_dir: Path, filename: str) -> Path:
    dest = dest_dir / filename
    client.fetch_file(url, dest)
    return dest
