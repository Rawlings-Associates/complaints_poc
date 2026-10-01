"""Per-case document plans, the paid-download budget, and the run summary.

The same plan drives ``--dry-run`` and a real run, so a dry run shows exactly
what a real run would try, buy and skip.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable

from . import documents as docs_mod
from .documents import Candidate, is_sealed, price_of

CASE_FIELDS = ["case_id", "case_number", "case_name", "court", "filed_date"]

INVENTORY_FIELDS = CASE_FIELDS + [
    "case_document_id", "document_name", "document_description", "document_filed_date",
    "pages", "price", "repository", "availability", "preview_available",
    "matched_type", "match_score", "action", "result", "pdf_path",
    "plaintiffs_found",
]

# The planned action for a document.
ACTIONS = {
    "download": "free; downloaded",
    "fallback": "free; downloaded only if the documents before it yield no plaintiffs",
    "buy": "priced; within --budget (planning only: paid downloads are not supported)",
    "buy-fallback": "priced; needed only if the documents before it yield no plaintiffs (planning only)",
    "over-budget": "priced; would exceed --budget",
    "paid-skip": "priced; not downloaded (paid downloads are not supported)",
    "unknown-price": "no price given; never fetched",
    "sealed": "sealed; never fetched",
    "alternative": "a weaker match of a type already covered; not fetched",
    "": "not a document type being looked for",
    "no-documents": "the case lists no documents",
}


class Budget:
    """Running total of paid downloads against an optional cap."""

    def __init__(self, limit: Decimal | None = None):
        self.limit = limit
        self.used = Decimal(0)
        self.count = 0

    @property
    def remaining(self) -> Decimal:
        return max(self.limit - self.used, Decimal(0)) if self.limit is not None else Decimal(0)

    def allows(self, price: Decimal | None) -> bool:
        if price is None:
            return False
        return price == 0 or (self.limit is not None and self.used + price <= self.limit)

    def charge(self, price: Decimal | None) -> None:
        if price:
            self.used += price
            self.count += 1


def case_record(case: dict[str, Any]) -> dict[str, str]:
    return {
        "case_id": case.get("caseId", ""),
        "case_number": case.get("caseNumber", ""),
        "case_name": case.get("caseName") or "",
        "court": (case.get("court") or {}).get("name", ""),
        "filed_date": (case.get("filedDate") or "")[:10],
    }


def document_row(case: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
    price = price_of(doc)
    return {
        **case_record(case),
        "case_document_id": doc.get("caseDocumentId", ""),
        "document_name": doc.get("name") or "",
        "document_description": doc.get("description") or "",
        "document_filed_date": (doc.get("documentFiledDate") or "")[:10],
        "pages": doc.get("pages") if doc.get("pages") is not None else "",
        "price": "" if price is None else str(price),
        "repository": doc.get("repository") or "",
        "availability": doc.get("availabilityStatusAtCourtSource") or "",
        "preview_available": doc.get("isPreviewAvailable", ""),
        "matched_type": "", "match_score": "", "action": "", "result": "",
        "pdf_path": "", "plaintiffs_found": "",
    }


@dataclass
class CasePlan:
    case: dict[str, Any]
    rows: list[dict[str, Any]]
    matches: dict[str, list[Candidate]]
    tries: list[tuple[Candidate, dict[str, Any]]] = field(default_factory=list)


def plan_case(
    case: dict[str, Any],
    documents: list[dict[str, Any]],
    order: Iterable[str],
    threshold: float,
    include_paid: bool,
    budget: Budget,
) -> CasePlan:
    """Inventory every document of the case and decide what to try.

    ``budget`` is the planning budget: planned purchases are charged to it in
    case order, so later cases see what earlier ones would spend.
    """
    order = list(order)
    matches = docs_mod.match_all(documents, order, threshold)
    rows = [document_row(case, d) for d in documents]
    if not rows:
        rows = [{**document_row(case, {}), "action": "no-documents"}]
        return CasePlan(case, rows, matches)
    by_id = {r["case_document_id"]: r for r in rows}

    for cands in matches.values():
        for cand in cands:
            row = by_id[cand.doc.get("caseDocumentId", "")]
            row["matched_type"] = cand.doc_type
            row["match_score"] = f"{cand.score:.2f}"
            if is_sealed(cand.doc):
                row["action"] = "sealed"
            elif cand.price is None:
                row["action"] = "unknown-price"
            elif cand.price > 0 and not include_paid:
                row["action"] = "paid-skip"
            else:
                row["action"] = "alternative"

    tries = []
    have_primary = False
    for cand in docs_mod.attempts(matches, order, include_paid):
        row = by_id[cand.doc["caseDocumentId"]]
        if cand.free:
            row["action"] = "fallback" if have_primary else "download"
            have_primary = True
        elif have_primary:
            row["action"] = "buy-fallback"
        elif budget.allows(cand.price):
            row["action"] = "buy"
            budget.charge(cand.price)
            have_primary = True
        else:
            row["action"] = "over-budget"
        tries.append((cand, row))
    return CasePlan(case, rows, matches, tries)


# -- summary ---------------------------------------------------------------------

def _chosen(cands: list[Candidate]) -> Candidate | None:
    """The document that stands for a type in a case: best free, else best match."""
    free = [c for c in cands if c.free and not is_sealed(c.doc)]
    return free[0] if free else (cands[0] if cands else None)


def summarize(
    plans: list[CasePlan],
    order: list[str],
    dry_run: bool,
    include_paid: bool,
    planned: Budget,
    plaintiff_rows: list[dict[str, Any]] | None = None,
) -> str:
    note = " (dry run: nothing was ordered or downloaded)" if dry_run else ""
    docs_listed = sum(1 for p in plans for r in p.rows if r["case_document_id"])
    lines = [f"Summary for {len(plans)} case(s), {docs_listed} document(s) listed{note}:"]

    width = max(len(t) for t in order)
    for doc_type in order:
        chosen = [_chosen(p.matches.get(doc_type, [])) for p in plans]
        found = [c for c in chosen if c]
        free = [c for c in found if c.free and not is_sealed(c.doc)]
        sealed = [c for c in found if is_sealed(c.doc)]
        unknown = [c for c in found if c.price is None and not is_sealed(c.doc)]
        paid = [c for c in found if c.price and not is_sealed(c.doc)]
        total = sum((c.price for c in paid), Decimal(0))
        lines.append(
            f"  {doc_type:<{width}}  found {len(found):>4} | free {len(free):>4} | "
            f"paid {len(paid):>4} (${total:,.2f}) | price unknown {len(unknown)} | "
            f"sealed {len(sealed)} | none {len(chosen) - len(found)}"
        )

    free_cases = paid_cases = 0
    cheapest = Decimal(0)
    for p in plans:
        chosen = [c for c in (_chosen(p.matches.get(t, [])) for t in order) if c]
        if any(c.free and not is_sealed(c.doc) for c in chosen):
            free_cases += 1
        else:
            prices = [c.price for c in chosen if c.price and not is_sealed(c.doc)]
            if prices:
                paid_cases += 1
                cheapest += min(prices)
    lines.append(f"  Cases with a free document: {free_cases}")
    lines.append(f"  Cases with only paid documents: {paid_cases} "
                 f"(cheapest document per case: ${cheapest:,.2f} in total)")
    lines.append(f"  Cases with nothing usable: {len(plans) - free_cases - paid_cases}")

    if include_paid:
        over = sum(1 for p in plans for r in p.rows if r["action"] == "over-budget")
        lines.append(f"  Paid documents, budget ${planned.limit:,.2f}: planned {planned.count} "
                     f"for ${planned.used:,.2f}; over budget {over} "
                     "(plan only: downloading paid documents is not supported)")
    else:
        lines.append("  Paid documents are not downloaded (downloading them is not supported).")

    if plaintiff_rows is not None:
        downloaded = sum(1 for p in plans for r in p.rows if r["result"] == "downloaded")
        ok = [r for r in plaintiff_rows if r["status"] == "ok"]
        lines.append(f"  PDFs downloaded: {downloaded}; plaintiffs found: {len(ok)} "
                     f"in {len({r['case_id'] for r in ok})} case(s)")
        other: dict[str, int] = {}
        for r in plaintiff_rows:
            if r["status"] != "ok":
                other[r["status"]] = other.get(r["status"], 0) + 1
        if other:
            lines.append("  Cases without plaintiffs: "
                         + ", ".join(f"{k} {v}" for k, v in sorted(other.items())))
    lines.append("  Prices are what UniCourt reports for each document at the court/source; "
                 "UniCourt's own charges, if any, are not included.")
    return "\n".join(lines)
