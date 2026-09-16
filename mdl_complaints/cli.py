"""Command line interface.

    python -m mdl_complaints 3140
    python -m mdl_complaints 3140 --format csv > complaints.csv
    python -m mdl_complaints 3140 --download ./pdfs
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from .client import DEFAULT_CACHE_DIR, CourtListenerClient, CourtListenerError
from .members import resolve_member_titles
from .titles import BATCH_SIZE
from .core import (
    collect_members,
    DEFAULT_ENTRY_PREFIX,
    Complaint,
    DocketNotFound,
    collect_complaints,
    normalize_mdl_number,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdl-complaints",
        description=(
            "Given an MDL master docket number, list the complaints attached "
            "to its motion(s) to transfer."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Accepts 3140, 'md 3140', 'MDL 3140' or 'MDL No. 3140'.\n"
            "Responses are cached, so re-runs normally cost zero API requests."
        ),
    )
    parser.add_argument("mdl", help="MDL master docket number, e.g. 3140")
    parser.add_argument(
        "--members", action="store_true",
        help=(
            "list the MDL's member cases (tag-alongs, transfer orders and "
            "cases filed directly in the transferee district) instead of the "
            "complaints attached to the motions"
        ),
    )
    parser.add_argument(
        "--resolve-names", action="store_true",
        help="look up member-case captions (costs roughly one request per 15 cases)",
    )
    parser.add_argument(
        "--budget", type=int, default=None, metavar="N",
        help=(
            "cap the requests spent resolving names. Responses are cached, so "
            "re-running a capped job continues where it left off"
        ),
    )
    parser.add_argument(
        "--court", metavar="ID",
        help="only cases from this CourtListener court id, e.g. flnd",
    )
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="only the first N results",
    )
    parser.add_argument(
        "--format", choices=("table", "json", "csv"), default="table",
        help="output format (default: table)",
    )
    parser.add_argument(
        "--entry-prefix", default=None,
        help=(
            "only entries whose description starts with this, e.g. "
            f"{DEFAULT_ENTRY_PREFIX!r}. Default: scan every entry."
        ),
    )
    parser.add_argument(
        "--motions-only", action="store_true",
        help=f"shorthand for --entry-prefix {DEFAULT_ENTRY_PREFIX!r}",
    )
    parser.add_argument(
        "--max-pages", type=int, default=0,
        help="entry pages to scan, 20 entries each (default: 0 = all pages)",
    )
    parser.add_argument(
        "--no-titles", action="store_true",
        help="skip member-case title lookup (saves about one request per court)",
    )
    parser.add_argument(
        "--no-pdf-titles", action="store_true",
        help=(
            "do not fall back to the complaint PDF for titles the member "
            "docket could not supply (the fallback costs no extra requests)"
        ),
    )
    parser.add_argument(
        "--available-only", action="store_true",
        help="only complaints whose PDF is available in RECAP",
    )
    parser.add_argument(
        "--download", metavar="DIR",
        help="also download the complaint PDFs into DIR",
    )
    parser.add_argument(
        "--rate", type=int, default=10,
        help="max API requests per minute (default: 10)",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="bypass the on-disk cache",
    )
    parser.add_argument(
        "--cache-dir", default=str(DEFAULT_CACHE_DIR),
        help=f"cache location (default: {DEFAULT_CACHE_DIR})",
    )
    parser.add_argument("--token", help="API token (default: $COURTLISTENER_API_KEY)")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="log requests and cache hits",
    )
    return parser


def _render_table(complaints: list[Complaint], title_width: int = 46) -> str:
    headers = ["#", "Entry", "Court", "Case No.", "Title", "Pg", "PDF"]
    rows = [
        [
            str(i),
            f"{c.entry_number or ''}-{c.attachment_number or ''}",
            c.court_name or c.court_code,
            c.case_number,
            _clip(c.title, title_width) + ("*" if c.title_source == "complaint-pdf" else ""),
            str(c.page_count or ""),
            "yes" if c.is_available else "no",
        ]
        for i, c in enumerate(complaints, 1)
    ]
    widths = [
        max(len(h), *(len(r[col]) for r in rows)) if rows else len(h)
        for col, h in enumerate(headers)
    ]
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)).rstrip()
    out = [line, "  ".join("-" * w for w in widths)]
    for row in rows:
        out.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
    return "\n".join(out)


def _clip(text: str, width: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= width else text[: width - 1] + "\u2026"


def _render_members(members: list, title_width: int = 52) -> str:
    headers = ["#", "Court", "Case No.", "Title", "Source"]
    rows = [
        [str(i), m.court_id, m.case_number, _clip(m.title, title_width), m.source]
        for i, m in enumerate(members, 1)
    ]
    widths = [
        max(len(h), *(len(r[col]) for r in rows)) if rows else len(h)
        for col, h in enumerate(headers)
    ]
    out = [
        "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)).rstrip(),
        "  ".join("-" * w for w in widths),
    ]
    for row in rows:
        out.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(row)).rstrip())
    return "\n".join(out)


def _write_rows_csv(rows: list, fields: list[str], stream) -> None:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow(row.as_dict())


def _run_members(args, client, canonical) -> int:
    docket, members, truncated = collect_members(
        client, canonical, max_pages=args.max_pages
    )
    if args.court:
        members = [m for m in members if m.court_id == args.court]

    spent = 0
    if args.resolve_names:
        target = members[: args.limit] if args.limit else members
        spent = resolve_member_titles(client, target, max_requests=args.budget)

    if args.limit:
        members = members[: args.limit]

    resolved = sum(1 for m in members if m.title)
    if args.format == "json":
        json.dump(
            {
                "mdl_number": docket.get("docket_number"),
                "case_name": docket.get("case_name"),
                "docket_id": docket.get("id"),
                "member_count": len(members),
                "titles_resolved": resolved,
                "truncated": truncated,
                "members": [m.as_dict() for m in members],
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    elif args.format == "csv":
        _write_rows_csv(
            members,
            ["court_id", "case_number", "source", "entry_number", "date_filed",
             "title", "title_source"],
            sys.stdout,
        )
    else:
        print(f"{docket.get('docket_number')} - {docket.get('case_name')}")
        by_court = Counter(m.court_id for m in members)
        print(
            f"Member cases: {len(members)} across {len(by_court)} court(s) | "
            f"titles resolved: {resolved}/{len(members)}"
        )
        print()
        print(_render_members(members) if members else "No member cases found.")
        if not args.resolve_names and members:
            remaining = -(-sum(1 for m in members if not m.title) // BATCH_SIZE)
            print(
                f"\nTitles not looked up. --resolve-names would cost about "
                f"{remaining} request(s); add --budget N to cap it.",
                file=sys.stderr,
            )

    if spent:
        print(f"[names] {spent} request(s) spent resolving captions", file=sys.stderr)
    return 0


def _write_csv(complaints: list[Complaint], stream) -> None:
    fields = list(Complaint.__dataclass_fields__)
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for complaint in complaints:
        writer.writerow(complaint.as_dict())


def _download(complaints: list[Complaint], directory: str, verbose: bool) -> int:
    """Fetch the PDFs. These come from the storage host, not the rate-limited API."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    saved = 0
    for complaint in complaints:
        if not complaint.pdf_url:
            continue
        slug = (complaint.case_number or str(complaint.document_id)).replace(":", "-")
        path = target / f"{complaint.court_code or 'court'}_{slug}.pdf"
        if path.exists():
            if verbose:
                print(f"  [skip] {path.name} already downloaded", file=sys.stderr)
            saved += 1
            continue
        try:
            request = urllib.request.Request(
                complaint.pdf_url, headers={"User-Agent": "mdl-complaints-poc/0.1"}
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                path.write_bytes(response.read())
            saved += 1
            if verbose:
                print(f"  [saved] {path.name}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 - one bad PDF must not abort the run
            print(f"  [warn] {complaint.description}: {exc}", file=sys.stderr)
        time.sleep(0.5)
    return saved


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.motions_only and not args.entry_prefix:
        args.entry_prefix = DEFAULT_ENTRY_PREFIX

    try:
        canonical = normalize_mdl_number(args.mdl)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        client = CourtListenerClient(
            token=args.token,
            cache_dir=Path(args.cache_dir),
            use_cache=not args.no_cache,
            max_calls=args.rate,
            verbose=args.verbose,
        )
        if args.members:
            result = _run_members(args, client, canonical)
            print(
                f"\n[api] {client.request_count} request(s), "
                f"{client.cache_hits} cache hit(s), "
                f"{client.bucket.remaining()}/{args.rate} left in this minute",
                file=sys.stderr,
            )
            return result
        docket, entries, complaints, truncated = collect_complaints(
            client,
            canonical,
            entry_prefix=args.entry_prefix,
            max_pages=args.max_pages,
            available_only=args.available_only,
            with_titles=not args.no_titles,
            pdf_fallback=not args.no_pdf_titles,
        )
    except DocketNotFound as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except CourtListenerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        json.dump(
            {
                "mdl_number": docket.get("docket_number"),
                "case_name": docket.get("case_name"),
                "docket_id": docket.get("id"),
                "date_filed": docket.get("date_filed"),
                "matching_entries": len(entries),
                "complaint_count": len(complaints),
                "truncated": truncated,
                "complaints": [c.as_dict() for c in complaints],
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    elif args.format == "csv":
        _write_csv(complaints, sys.stdout)
    else:
        print(f"{docket.get('docket_number')} - {docket.get('case_name')}")
        print(
            f"Docket {docket.get('id')} | filed {docket.get('date_filed')} | "
            f"https://www.courtlistener.com{docket.get('absolute_url', '')}"
        )
        scope = (
            f"entries starting {args.entry_prefix!r}"
            if args.entry_prefix else "all docket entries"
        )
        resolved = sum(1 for c in complaints if c.title)
        derived = sum(1 for c in complaints if c.title_source == "complaint-pdf")
        print(
            f"Scope: {scope} | matching entries: {len(entries)} | "
            f"complaints: {len(complaints)} | titles: {resolved}/{len(complaints)}"
        )
        print()
        print(_render_table(complaints) if complaints else "No complaints found.")
        if derived:
            print(
                f"\n* {derived} title(s) taken from the complaint PDF "
                "(plaintiff only) because the member docket had none."
            )
        if truncated:
            print(
                f"\nNote: stopped after {args.max_pages} page(s) of docket entries; "
                "more entries exist. Re-run with --max-pages 0 for all.",
                file=sys.stderr,
            )

    if args.download:
        saved = _download(complaints, args.download, args.verbose)
        print(f"\nDownloaded {saved}/{len(complaints)} PDFs to {args.download}",
              file=sys.stderr)

    print(
        f"\n[api] {client.request_count} request(s), {client.cache_hits} cache hit(s), "
        f"{client.bucket.remaining()}/{args.rate} left in this minute",
        file=sys.stderr,
    )
    return 0
