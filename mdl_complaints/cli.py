"""Command line interface.

    python -m mdl_complaints 3140
    python -m mdl_complaints 3140 --format csv > complaints.csv
    python -m mdl_complaints 3140 --download ./pdfs
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from .client import DEFAULT_CACHE_DIR, CourtListenerClient, CourtListenerError
from .core import (
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
        "--format", choices=("table", "json", "csv"), default="table",
        help="output format (default: table)",
    )
    parser.add_argument(
        "--entry-prefix", default=DEFAULT_ENTRY_PREFIX,
        help=f"docket-entry description prefix (default: {DEFAULT_ENTRY_PREFIX!r})",
    )
    parser.add_argument(
        "--max-pages", type=int, default=1,
        help=(
            "entry pages to scan, 20 entries each (default: 1). Motions to "
            "transfer sit at the start of the docket, so one page is normally "
            "enough and costs one request."
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


def _render_table(complaints: list[Complaint]) -> str:
    headers = ["#", "Att", "Court", "Case No.", "Pages", "PDF"]
    rows = [
        [
            str(i),
            str(c.attachment_number or ""),
            c.court_name or c.court_code,
            c.case_number,
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
        docket, entries, complaints, truncated = collect_complaints(
            client,
            canonical,
            entry_prefix=args.entry_prefix,
            max_pages=args.max_pages,
            available_only=args.available_only,
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
        print(
            f"Entries matching {args.entry_prefix!r}: {len(entries)} | "
            f"complaints found: {len(complaints)}"
        )
        print()
        print(_render_table(complaints) if complaints else "No complaints found.")
        if truncated:
            print(
                f"\nNote: stopped after {args.max_pages} page(s) of docket entries; "
                "later motions to transfer may exist. Re-run with --max-pages N.",
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
