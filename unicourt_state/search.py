"""Case search: cases naming one or more parties, by court, jurisdiction and court type."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable, Iterable, Iterator, Optional

from .client import UniCourtClient

MAX_QUERY_LENGTH = 2000  # caseSearch rejects longer `q` values

# Case search returns 10 results per page and at most 1,000 pages per query,
# so one query reaches at most 10,000 cases. Larger result sets are split into
# filing-date ranges, as the UniCourt docs recommend.
CASE_SEARCH_PAGE_SIZE = 10
MAX_PAGES = 1000
CASE_SEARCH_CAP = CASE_SEARCH_PAGE_SIZE * MAX_PAGES


def _quote(value: str) -> str:
    """Quote a phrase for a UniCourt keyword expression."""
    return '"' + value.replace("\\", " ").replace('"', " ").strip() + '"'


def party_clause(name: str, role: str | None = None) -> str:
    inner = f"name:{_quote(name)}"
    if role:
        inner += f" AND (PartyRole:(name:{_quote(role)}))"
    return f"(Party:({inner}))"


COURT_TYPES = {"state": "State", "federal": "Federal"}
MATCH_JOINERS = {"all": " AND ", "and": " AND ", "any": " OR ", "or": " OR "}


def build_query(
    parties: Iterable[str],
    court_id: str | None = None,
    court_name: str | None = None,
    match: str = "all",
    role: str | None = None,
    filed_from: str | None = None,
    filed_to: str | None = None,
    state: str | None = None,
    county: str | None = None,
    court_type: str | None = None,
) -> str:
    """Build a caseSearch `q` expression.

    Parties: ``match="all"`` (or ``"and"``, the default) requires every party
    to appear; ``"any"`` (or ``"or"``) finds cases naming at least one.

    Scope, combined with AND; at least one is required so a search is never
    accidentally nationwide:
    - ``court_id`` / ``court_name``: one court.
    - ``state`` (and optionally ``county``): the jurisdiction, as
      ``JurisdictionGeo:(state:"...")``.
    - ``court_type``: ``"state"`` or ``"federal"``, as ``Court:(type:"State")``.
    """
    names = [p.strip() for p in parties if p and p.strip()]
    if not names:
        raise ValueError("at least one party name is required")
    if match not in MATCH_JOINERS:
        raise ValueError("match must be 'all'/'and' or 'any'/'or'")
    if court_type is not None and court_type.lower() not in COURT_TYPES:
        raise ValueError("court type must be 'state' or 'federal'")
    if county and not state:
        raise ValueError("--county needs --state")
    if not (court_id or court_name or state or court_type):
        raise ValueError("give a scope: a court (--court-id/--court-name), a jurisdiction "
                         "(--state), a court type (--court-type), or a combination")

    clauses = [party_clause(n, role) for n in names]
    party_expr = clauses[0] if len(clauses) == 1 else "(" + MATCH_JOINERS[match].join(clauses) + ")"

    scope = []
    if court_id:
        scope.append(f"(Court:(courtId:{_quote(court_id)}))")
    elif court_name:
        scope.append(f"(Court:(name:{_quote(court_name)}))")
    if court_type:
        scope.append(f"(Court:(type:{_quote(COURT_TYPES[court_type.lower()])}))")
    if state:
        geo = f"state:{_quote(state)}"
        if county:
            geo += f" AND county:{_quote(county)}"
        scope.append(f"(JurisdictionGeo:({geo}))")

    parts = [party_expr, *scope]
    if filed_from or filed_to:
        start = f"{filed_from}T00:00:00" if filed_from else "*"
        end = f"{filed_to}T23:59:59" if filed_to else "*"
        parts.append(f"filedDate:[{start} TO {end}]")

    query = " AND ".join(parts)
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError(
            f"query is {len(query)} characters; caseSearch allows {MAX_QUERY_LENGTH}. "
            "Use fewer party names per run."
        )
    return query


QueryFactory = Callable[[Optional[str], Optional[str]], str]  # runtime alias: no `X | None` on 3.9


def _first_page(client: UniCourtClient, query: str, order: str = "desc") -> dict[str, Any]:
    params = {"q": query, "sort": "filedDate", "order": order, "pageNumber": 1}
    return client.get("caseSearch", params)


def _items(page: dict[str, Any]) -> list[dict[str, Any]]:
    items = page.get("caseSearchResultArray")
    return items if items is not None else (page.get("data") or [])


def _filed(page: dict[str, Any]) -> date | None:
    items = _items(page)
    value = (items[0].get("filedDate") or "")[:10] if items else ""
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _day(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def search_cases(
    client: UniCourtClient,
    make_query: QueryFactory,
    filed_from: str | None = None,
    filed_to: str | None = None,
    limit: int | None = None,
    meta: dict[str, Any] | None = None,
    note: Callable[[str], None] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield matching cases, newest filings first.

    ``make_query(filed_from, filed_to)`` builds the ``q`` expression for a
    date range (ISO dates or None). When a query matches more than
    ``CASE_SEARCH_CAP`` cases it is split into filing-date halves, recursively,
    until every range fits; ranges are searched newest first and cases are
    de-duplicated by caseId. ``limit`` of None or 0 means every match;
    ``meta`` receives the overall ``totalCount``.
    """
    note = note or (lambda _msg: None)
    first = _first_page(client, make_query(filed_from, filed_to))
    if meta is not None:
        meta.update({k: v for k, v in first.items() if k not in ("caseSearchResultArray", "data")})
    seen: set[str] = set()
    remaining = limit or None

    for page in _ranges(client, make_query, _day(filed_from), _day(filed_to), first, note):
        for case in client.iter_pages(page, "caseSearchResultArray"):
            case_id = case.get("caseId")
            if case_id in seen:
                continue
            seen.add(case_id)
            yield case
            if remaining is not None:
                remaining -= 1
                if remaining <= 0:
                    return


def _ranges(
    client: UniCourtClient,
    make_query: QueryFactory,
    lo: date | None,
    hi: date | None,
    first: dict[str, Any],
    note: Callable[[str], None],
) -> Iterator[dict[str, Any]]:
    """First pages of date ranges that each fit under the cap, newest first."""
    total = first.get("totalCount") or 0
    if total <= CASE_SEARCH_CAP:
        yield first
        return
    # Bounds found from the data are widened by a day, so a filing whose time
    # zone moves it across midnight is still inside the range.
    if hi is None:
        newest = _filed(first)  # results are newest first
        hi = newest + timedelta(days=1) if newest else None
    if lo is None and hi is not None:
        oldest = _filed(_first_page(client, make_query(None, hi.isoformat()), order="asc"))
        lo = oldest - timedelta(days=1) if oldest else None
    if lo is None or hi is None or lo >= hi:
        note(f"  {total:,} cases match {lo or '?'}..{hi or '?'}, over the {CASE_SEARCH_CAP:,} "
             "a query can return, and the range cannot be split further; "
             f"only the first {CASE_SEARCH_CAP:,} are fetched. Narrow the search.")
        yield first
        return
    mid = lo + (hi - lo) // 2
    note(f"  {total:,} cases match {lo}..{hi}, over the {CASE_SEARCH_CAP:,} per-query cap: "
         f"splitting at {mid}")
    for a, b in ((mid + timedelta(days=1), hi), (lo, mid)):
        page = _first_page(client, make_query(a.isoformat(), b.isoformat()))
        yield from _ranges(client, make_query, a, b, page, note)


def find_courts(client: UniCourtClient, name: str, limit: int = 25) -> list[dict[str, Any]]:
    """Look up courts by name, to get the courtId for a search."""
    params = {"q": f"name:({name.replace(')', ' ').replace('(', ' ')})"}  # pageNumber added by paginate
    return list(client.paginate("masterData/court", "courtArray", params, max_items=limit))
