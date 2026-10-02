"""Command line: find state- or federal-court cases by party, then fetch their filings.

Workflow::

    unicourt search --state "New York" --court-type state --party "Acme" --party "Beta" \
        --limit 0 --out cases.csv          # several parties: all must appear (AND)
    # edit cases.csv down to the cases you care about
    unicourt get-complaints --input-file cases.csv --dry-run --out documents.csv
    unicourt get-complaints --input-file cases.csv            # free documents only
    # texts.jsonl now holds each document's text, for an agent to read the parties from
    unicourt get-complaints --input-file cases.csv --dry-run --include-paid --budget 25

    # or straight from a search:
    unicourt search --state "New York" --court-type state --party "Acme" | unicourt get-complaints --dry-run

Search scope: --state (and --county), --court-type state|federal, and/or one
court (--court-id / --court-name); at least one is required.

Downloading paid documents is not supported: --include-paid only plans and
prices them in a dry run; without --dry-run it stops with an error.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import io
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, TextIO

from . import documents as docs_mod
from . import credentials as creds
from .credentials import mask
from .client import API_ROOT, UniCourtClient, UniCourtError
from .pdftext import format_pages, read_pages
from .plan import CASE_FIELDS, INVENTORY_FIELDS, Budget, CasePlan, case_record, plan_case, summarize
from .search import build_query, find_courts, search_cases
from .status import Status

MAX_WORKERS = 16


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _api_root() -> str:
    return os.environ.get("UNICOURT_API_ROOT", API_ROOT).rstrip("/")  # override for a test server


def _env_credentials() -> tuple[str, str] | None:
    client_id = os.environ.get("UNICOURT_CLIENT_ID", "").strip()
    secret = os.environ.get("UNICOURT_CLIENT_SECRET", "")
    return (client_id, secret) if client_id and secret else None


def _ask_credentials(client_id: str | None = None) -> tuple[str, str]:
    """Client id and secret from the environment, else asked on the terminal."""
    env = _env_credentials()
    if env:
        return env
    client_id = client_id or os.environ.get("UNICOURT_CLIENT_ID", "").strip()
    try:
        if not client_id:
            client_id = (_ask_terminal("UniCourt client ID: ") or "").strip()
        secret = os.environ.get("UNICOURT_CLIENT_SECRET") or getpass.getpass("UniCourt client secret: ")
    except (EOFError, OSError):
        client_id, secret = "", ""
    if not client_id or not secret:
        raise SystemExit("Set UNICOURT_CLIENT_ID and UNICOURT_CLIENT_SECRET (or run in a terminal "
                         "to be asked) so a workspace token can be created.")
    return client_id, secret


def _client(args) -> UniCourtClient:
    """An API client, authenticated in this order:

    1. ``--token`` / ``UNICOURT_TOKEN``: used as given.
    2. A workspace token stored by an earlier run (see credentials.py).
    3. Otherwise one is created from the client ID and secret and stored.

    A stored token that UniCourt rejects (401) is replaced once, when the
    client ID and secret are in the environment.
    """
    root = _api_root()
    workspace = args.workspace or os.environ.get("UNICOURT_WORKSPACE")
    explicit = args.token or os.environ.get("UNICOURT_TOKEN")
    if explicit:
        if not workspace:
            raise SystemExit("A token from --token/UNICOURT_TOKEN also needs --workspace or UNICOURT_WORKSPACE.")
        return UniCourtClient(explicit, workspace, root=root, verbose=args.verbose)

    store = creds.TokenStore(warn=_err)
    env = _env_credentials()
    entry = store.find(root, workspace, env[0] if env else None)
    if entry is None:
        entry = _create_token(store, root, workspace, _ask_credentials(), args.verbose)

    def replace_rejected_token():
        current = _env_credentials()
        if not current:
            _err("The stored token was rejected. Set UNICOURT_CLIENT_ID / UNICOURT_CLIENT_SECRET "
                 "or run `unicourt token --refresh`.")
            return None
        _err("The stored token was rejected (revoked?); creating a new one.")
        return _create_token(store, root, entry["workspace_id"], current, args.verbose)["access_token"]

    return UniCourtClient(entry["access_token"], entry["workspace_id"], root=root,
                          verbose=args.verbose, on_unauthorized=replace_rejected_token)


def _create_token(store, root, workspace, credentials, verbose=False) -> dict[str, Any]:
    """Create and store a workspace token; without a workspace id, look it up first."""
    client_id, secret = credentials
    if not workspace:
        _err("No workspace given: looking up the account's DEEP workspace...")
        found = creds.discover_workspace(
            lambda token: UniCourtClient(token, "", root=root, verbose=verbose),
            client_id, secret, note=_err)
        workspace = found["workspaceId"]
        _err(f"Using workspace {workspace} ({found.get('workspaceType', '?')}: "
             f"{found.get('workspaceName', '')}).")
    api = UniCourtClient("", workspace, root=root, verbose=verbose)
    entry = creds.generate(api, client_id, secret, workspace)
    store.save(entry)
    _err(f"Created a workspace token for {entry['workspace_id']} and stored it in {store.path} "
         "(readable only by you).")
    return entry


def _money(value: str) -> Decimal:
    try:
        amount = Decimal(value.replace("$", "").replace(",", "").strip())
    except InvalidOperation:
        raise argparse.ArgumentTypeError(f"not an amount: {value!r}") from None
    if not amount.is_finite() or amount < 0:
        raise argparse.ArgumentTypeError("the budget must be zero or more")
    return amount


def _add_auth(p: argparse.ArgumentParser) -> None:
    p.add_argument("--token", help="use this token instead of the stored one (default: $UNICOURT_TOKEN)")
    p.add_argument("--workspace", help="workspace id (default: $UNICOURT_WORKSPACE, or the stored one)")
    p.add_argument("-v", "--verbose", action="store_true", help="log requests to stderr")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="unicourt",
        description="Find cases by party in a state, county, court type (state or federal) "
        "or court, then price or download their cover sheets / complaints and save their text "
        "for an agent to read.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("token", help="create, show, refresh or revoke the stored workspace token")
    p.add_argument("--workspace", help="workspace id (default: $UNICOURT_WORKSPACE, the stored one, "
                   "or the account's DEEP workspace, looked up)")
    action = p.add_mutually_exclusive_group()
    action.add_argument("--refresh", action="store_true",
                        help="create a new token, then revoke the old one with UniCourt")
    action.add_argument("--revoke", action="store_true",
                        help="revoke the stored token with UniCourt and delete it locally")
    p.add_argument("-v", "--verbose", action="store_true", help="log requests to stderr")

    p = sub.add_parser("courts", help="look up a courtId by name")
    p.add_argument("name")
    _add_auth(p)

    p = sub.add_parser("search", help="find cases by party; CSV output can feed get-complaints")
    scope = p.add_argument_group("scope (at least one; they combine with AND)")
    court = scope.add_mutually_exclusive_group()
    court.add_argument("--court-id", help="one court, by UniCourt courtId (see the `courts` command)")
    court.add_argument("--court-name", help="one court, by exact name, e.g. 'Los Angeles County Superior Court'")
    scope.add_argument("--state", metavar="NAME",
                       help="jurisdiction: a state, by full name, e.g. 'New York'")
    scope.add_argument("--county", metavar="NAME",
                       help="jurisdiction: a county within --state, e.g. 'Kings'")
    scope.add_argument("--court-type", choices=("state", "federal"), type=str.lower,
                       help="only state courts or only federal courts")
    p.add_argument("--party", action="append", required=True, metavar="NAME",
                   help="party name; repeat for several parties")
    p.add_argument("--match", choices=("all", "and", "any", "or"), default="all",
                   help="several parties: all/and = every party must appear (default); "
                   "any/or = at least one")
    p.add_argument("--role", help="only match the parties in this role, e.g. defendant")
    p.add_argument("--filed-from", metavar="YYYY-MM-DD")
    p.add_argument("--filed-to", metavar="YYYY-MM-DD")
    p.add_argument("--limit", type=int, default=100,
                   help="maximum cases to return, 0 = all (default: %(default)s)")
    p.add_argument("--format", choices=("auto", "table", "csv"), default="auto",
                   help="stdout format; auto = table in a terminal, CSV when piped (default)")
    p.add_argument("--out", metavar="CASES.csv", help="also save the cases to this CSV")
    _add_auth(p)

    p = sub.add_parser(
        "get-complaints",
        help="for each listed case, pick the relevant documents; price them (--dry-run) "
        "or download them and save their text",
    )
    p.add_argument("-i", "--input-file", type=Path, metavar="CASES.csv",
                   help="case list with a case_id column; default: read CSV from stdin (a pipe)")
    p.add_argument("--dry-run", action="store_true",
                   help="plan and price only; nothing is ordered or downloaded")
    p.add_argument("--include-paid", action="store_true",
                   help="plan priced documents too, within --budget (dry run only: "
                   "downloading paid documents is not supported)")
    p.add_argument("--budget", type=_money, metavar="AMOUNT",
                   help="maximum total spend to plan for paid documents, e.g. 25 or 25.00")
    p.add_argument("--doc-types", default=",".join(docs_mod.DEFAULT_ORDER),
                   help="document types to look for, in order of preference (default: %(default)s)")
    p.add_argument("--threshold", type=float, default=docs_mod.DEFAULT_THRESHOLD,
                   help="minimum name similarity, 0-1 (default: %(default)s)")
    p.add_argument("--limit", type=int, default=0,
                   help="only the first N cases of the list, 0 = all (default: 0)")
    p.add_argument("--out", default="documents.csv",
                   help="every document of every case with price, match and action "
                   "(default: %(default)s)")
    p.add_argument("--text-out", default="texts.jsonl",
                   help="one JSON line per case document with its full text, or the reason "
                   "a case has none; written when not a dry run (default: %(default)s)")
    p.add_argument("--pdf-dir", default="pdfs", help="where PDFs are saved (default: %(default)s)")
    p.add_argument("--yes", action="store_true", help="download without asking (use after testing)")
    p.add_argument("--workers", type=int, default=4,
                   help=f"cases processed in parallel, 1-{MAX_WORKERS} (default: %(default)s)")
    p.add_argument("--priority", choices=("level1", "level2", "level5"), default="level2",
                   help="order priority; timeouts 5 min / 30 min / 24 h (default: %(default)s)")
    _add_auth(p)

    p = sub.add_parser(
        "get-documents",
        help="download chosen documents by case_document_id (e.g. rows picked from documents.csv) "
        "and save their text",
    )
    p.add_argument("-i", "--input-file", type=Path, metavar="DOCS.csv",
                   help="documents to fetch, with a case_document_id column (documents.csv rows "
                   "work as they are); default: read CSV from stdin (a pipe)")
    p.add_argument("--dry-run", action="store_true",
                   help="show what would be fetched; no API calls, nothing downloaded")
    p.add_argument("--text-out", default="texts_documents.jsonl",
                   help="one JSON line per document with its full text, or why it has none "
                   "(default: %(default)s)")
    p.add_argument("--pdf-dir", default="pdfs",
                   help="where PDFs are saved; a PDF already there is reused (default: %(default)s)")
    p.add_argument("--yes", action="store_true", help="download without asking (use after testing)")
    p.add_argument("--workers", type=int, default=4,
                   help=f"documents fetched in parallel, 1-{MAX_WORKERS} (default: %(default)s)")
    p.add_argument("--priority", choices=("level1", "level2", "level5"), default="level2",
                   help="order priority; timeouts 5 min / 30 min / 24 h (default: %(default)s)")
    _add_auth(p)

    p = sub.add_parser("extract", help="print the text of a PDF already on disk, page by page")
    p.add_argument("pdf", type=Path)
    return parser


# -- shared helpers ------------------------------------------------------------

def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        _csv_to(fh, rows, fields)


def _csv_to(fh: TextIO, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)


def _case_line(case: dict[str, Any]) -> str:
    court = (case.get("court") or {}).get("name", "")
    filed = (case.get("filedDate") or "")[:10]
    return f"{case.get('caseNumber')}  {filed}  {case.get('caseName')}  [{court}]  {case.get('caseId')}"


def _api_usage(client: UniCourtClient) -> str:
    text = f"{client.requests_made} API request(s)"
    if client.limiter.waited >= 1:
        text += f", {client.limiter.waited:.0f}s spent waiting for the rate limit"
    if client.rate_limited:
        text += f", {client.rate_limited} rate-limited (429) and retried"
    return text


def _doc_types(value: str) -> list[str]:
    order = [t.strip() for t in value.split(",") if t.strip()]
    unknown = [t for t in order if t not in docs_mod.DOC_TYPES]
    if unknown or not order:
        raise SystemExit(f"unknown document type(s): {', '.join(unknown) or value!r}; "
                         f"choose from {', '.join(docs_mod.DOC_TYPES)}")
    return order


def _ask_terminal(prompt: str) -> str | None:
    """Read an answer from the user's terminal, even when stdin is a pipe."""
    if sys.stdin.isatty():
        return input(prompt)
    try:
        with open("/dev/tty") as tty:
            sys.stderr.write(prompt)
            sys.stderr.flush()
            return tty.readline()
    except OSError:
        return None


class Confirmer:
    """Ask before downloading a case's documents: y(es), n(o), a(ll remaining), q(uit)."""

    def __init__(self, assume_yes: bool, ask=None):
        self.all = assume_yes
        self.quit = False
        self.ask = ask or _ask_terminal

    def __call__(self, prompt: str) -> bool:
        if self.all:
            return True
        if self.quit:
            return False
        answer = self.ask(f"{prompt} [y/N/a/q] ")
        if answer is None:
            _err("No terminal to confirm downloads: pass --yes to download without asking.")
            self.quit = True
            return False
        answer = answer.strip().lower()
        if answer == "a":
            self.all = True
        if answer == "q":
            self.quit = True
        return answer in ("y", "yes", "a")


# -- commands -------------------------------------------------------------------

def cmd_token(args) -> int:
    """Manage the stored workspace token. The token itself is never printed."""
    root = _api_root()
    store = creds.TokenStore(warn=_err)
    workspace = args.workspace or os.environ.get("UNICOURT_WORKSPACE")
    entry = store.find(root, workspace)

    if args.revoke or args.refresh:
        if entry is None:
            raise SystemExit(f"No stored token for {workspace or root} in {store.path}.")
        credentials = _ask_credentials()
        if args.refresh:
            entry_new = _create_token(store, root, entry["workspace_id"], credentials, args.verbose)
        api = UniCourtClient("", entry["workspace_id"], root=root, verbose=args.verbose)
        try:
            creds.revoke(api, *credentials, entry)
            _err(f"Revoked token {entry['token_id']} with UniCourt.")
        except UniCourtError as exc:
            _err(f"Could not revoke token {entry['token_id']} with UniCourt: {exc}")
            if args.revoke:
                return 2  # keep the local copy so the revoke can be retried
        if args.revoke:
            store.remove(root, entry["workspace_id"])
            _err(f"Deleted it from {store.path}.")
            return 0
        entry = entry_new
    elif entry is None:
        entry = _create_token(store, root, workspace, _ask_credentials(), args.verbose)

    print(f"Stored token:  {mask(entry['access_token'])} (token id {entry['token_id']})")
    print(f"Workspace:     {entry['workspace_id']}")
    print(f"Created:       {entry['created']}")
    print(f"API root:      {entry['api_root']}")
    print(f"File:          {store.path}")
    return 0


def cmd_courts(args) -> int:
    client = _client(args)
    for court in find_courts(client, args.name):
        print(f"{court.get('courtId')}  {court.get('type', ''):<8} {court.get('name')}"
              f"  [{court.get('system', '')}]")
    return 0


def cmd_search(args) -> int:
    client = _client(args)
    def make_query(filed_from, filed_to):
        return build_query(
            args.party, court_id=args.court_id, court_name=args.court_name, match=args.match,
            role=args.role, filed_from=filed_from, filed_to=filed_to,
            state=args.state, county=args.county, court_type=args.court_type,
        )

    _err(f"q = {make_query(args.filed_from, args.filed_to)}")
    as_csv = args.format == "csv" or (args.format == "auto" and not sys.stdout.isatty())
    meta: dict[str, Any] = {}
    cases = []
    for case in search_cases(client, make_query, args.filed_from, args.filed_to,
                             limit=args.limit, meta=meta, note=_err):
        cases.append(case)
        if not as_csv:
            print(_case_line(case))
    if as_csv:
        _csv_to(sys.stdout, (case_record(c) for c in cases), CASE_FIELDS)
    _err(f"{len(cases)} of {meta.get('totalCount', len(cases))} matching case(s)")
    if args.out:
        _write_csv(Path(args.out), (case_record(c) for c in cases), CASE_FIELDS)
        _err(f"Saved {args.out}. Edit it, then: unicourt get-complaints --input-file {args.out} --dry-run")
    return 0


def read_cases(fh: TextIO, source: str = "input") -> list[dict[str, Any]]:
    """Load a case list. Only case_id is required; other columns are for display."""
    reader = csv.DictReader(fh)
    fields = {f.strip().lower(): f for f in reader.fieldnames or []}
    id_col = fields.get("case_id") or fields.get("caseid")
    if not id_col:
        raise SystemExit(f"{source} needs a case_id column (as written by `unicourt search`)")

    def col(row, name):
        key = fields.get(name)
        return (row.get(key) or "").strip() if key else ""

    cases, seen = [], set()
    for row in reader:
        case_id = (row.get(id_col) or "").strip()
        if not case_id or case_id in seen:
            continue
        seen.add(case_id)
        cases.append({
            "caseId": case_id,
            "caseNumber": col(row, "case_number"),
            "caseName": col(row, "case_name"),
            "court": {"name": col(row, "court"), "type": col(row, "court_type")},
            "courtLocation": {"stateName": col(row, "state")},
            "filedDate": col(row, "filed_date"),
        })
    return cases


def _load_cases(args) -> list[dict[str, Any]]:
    if args.input_file and str(args.input_file) != "-":
        with args.input_file.open(newline="", encoding="utf-8-sig") as fh:
            return read_cases(fh, str(args.input_file))
    if sys.stdin.isatty():
        raise SystemExit("Give a case list with --input-file CASES.csv, or pipe one in: "
                         "unicourt search ... | unicourt get-complaints --dry-run")
    return read_cases(io.StringIO(sys.stdin.read()), "stdin")


def _text_record(case, cand=None, status="", path="", pages=None):
    """One line of the text JSONL: a document's text, or why the case has none.

    ``status`` is ``ok`` (text extracted), ``no-text-layer`` (downloaded, but a
    scan), ``text-extraction-failed``, or a reason nothing was downloaded.
    """
    pages = pages or []
    return {
        **case_record(case),
        "document_type": cand.doc_type if cand else "",
        "document_name": cand.label if cand else "",
        "case_document_id": cand.doc.get("caseDocumentId", "") if cand else "",
        "price": cand.doc.get("price", "") if cand else "",
        "pdf_path": str(path), "status": status,
        "page_count": len(pages), "pages_with_text": sum(1 for p in pages if p),
        "text": format_pages(pages) if pages else "",
    }


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _tag(case: dict[str, Any]) -> str:
    return case.get("caseNumber") or case.get("caseId", "?")


def run_parallel(items, work, workers: int, status: Status, stop: threading.Event, on_result=None):
    """Run ``work(index, item)`` on a thread pool, calling ``on_result`` in this thread.

    Ctrl-C sets ``stop`` (workers check it, and order polling wakes on it),
    cancels queued items and waits for running ones to wind down.
    """
    pool = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="unicourt")
    try:
        futures = [pool.submit(work, i, item) for i, item in enumerate(items)]
        for future in as_completed(futures):
            result = future.result()
            if on_result:
                on_result(result)
    except KeyboardInterrupt:
        stop.set()
        status.log("Interrupted: finishing the requests in flight, starting no new ones...")
        pool.shutdown(wait=True, cancel_futures=True)
        raise
    finally:
        pool.shutdown(wait=True)


def fetch_case(client, plan: CasePlan, args, status: Status, stop: threading.Event) -> list[dict[str, Any]]:
    """Try the planned free documents in order until one gives text (runs in a worker).

    Returns a text record for every document downloaded (a scan included, so
    the agent sees it was tried), or one record saying why there is none.
    """
    case, tag = plan.case, _tag(plan.case)
    outcome = ""
    records: list[dict[str, Any]] = []
    for cand, row in plan.tries:
        if stop.is_set():
            outcome = outcome or "interrupted"
            break
        if not cand.free:  # plans for a real run hold free documents only
            raise docs_mod.PaidDownloadNotSupported(f"({cand.label}: ${cand.price})")
        status.log(f"  {tag}  fetching {cand.doc_type} '{cand.label}'")
        waiting = {"on": False, "last": None}

        def on_order(state, waiting=waiting, cand=cand):
            if state != waiting["last"]:
                status.log(f"  {tag}  {cand.doc_type} order {state}")
                waiting["last"] = state
            if state in ("IN_PROGRESS", "DELAYED") and not waiting["on"]:
                waiting["on"] = True
                status.add(ordering=1)

        try:
            url = docs_mod.obtain_file_url(client, cand.doc, priority=args.priority,
                                           on_status=on_order, stop=stop)
            path = docs_mod.download(client, url, Path(args.pdf_dir), docs_mod.pdf_filename(case, cand))
        except docs_mod.PaidDownloadNotSupported as exc:  # the price changed since the listing
            status.log(f"  {tag}  {exc}")
            row["result"], outcome = "paid-not-supported", "paid-not-supported"
            continue
        except (docs_mod.DocumentUnavailable, UniCourtError, OSError) as exc:
            status.log(f"  {tag}  could not fetch {cand.doc_type}: {exc}")
            status.add(failed=1)
            row["result"], outcome = "failed", "download-failed"
            continue
        finally:
            if waiting["on"]:
                status.add(ordering=-1)
        row["result"], row["pdf_path"] = "downloaded", str(path)
        status.add(pdfs=1)
        try:
            pages = read_pages(path)
        except Exception as exc:  # a damaged PDF must not stop the other cases
            status.log(f"  {tag}  saved {path}, but could not read its text: {exc}")
            records.append(_text_record(case, cand, "text-extraction-failed", path))
            outcome = "text-extraction-failed"
            continue
        with_text = sum(1 for p in pages if p)
        row["text_pages"] = with_text
        if with_text:
            status.add(texts=1)
            status.log(f"  {tag}  saved {path}: text on {with_text} of {len(pages)} page(s)")
            records.append(_text_record(case, cand, "ok", path, pages))
            return records
        status.log(f"  {tag}  saved {path} (no text layer: scanned?)")
        records.append(_text_record(case, cand, "no-text-layer", path, pages))
        outcome = "no-text-layer"
    return records or [_text_record(case, plan.tries[-1][0], outcome or "not-attempted")]


def _gap_records(plan: CasePlan, declined: bool) -> list[dict[str, Any]]:
    """The text record for a case that is not fetched."""
    if not any(plan.matches.values()):
        return [_text_record(plan.case, status="no-matching-document")]
    if not plan.tries:
        return [_text_record(plan.case, status="no-free-document")]
    return [_text_record(plan.case, plan.tries[0][0], "declined" if declined else "not-attempted")]


def cmd_get_complaints(args) -> int:
    if args.include_paid and args.budget is None:
        raise SystemExit("--include-paid needs --budget AMOUNT, the most to spend on paid documents")
    if args.budget is not None and not args.include_paid:
        raise SystemExit("--budget only applies with --include-paid")
    if args.include_paid and not args.dry_run:
        raise SystemExit(f"Error: {docs_mod.PAID_NOT_SUPPORTED}")
    if not 1 <= args.workers <= MAX_WORKERS:
        raise SystemExit(f"--workers must be between 1 and {MAX_WORKERS}")
    order = _doc_types(args.doc_types)
    cases = _load_cases(args)
    if args.limit:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("no cases to process")

    client = _client(args)
    status, stop = Status(), threading.Event()
    out, text_out = Path(args.out), Path(args.text_out)
    mode = "dry run" if args.dry_run else "free documents only"
    _err(f"{len(cases)} case(s) [{mode}], {args.workers} worker(s)")

    # 1. List every case's documents in parallel.
    listed: list[list[dict[str, Any]]] = [[] for _ in cases]

    def list_one(i, case):
        status.add(active=1)
        try:
            return i, docs_mod.list_documents(client, case["caseId"])
        except UniCourtError as exc:
            status.log(f"  {_tag(case)}  could not list documents: {exc}")
            status.add(failed=1)
            return i, []
        finally:
            status.add(active=-1, done=1)

    def store(result):
        listed[result[0]] = result[1]

    status.start("Listing documents", len(cases))
    try:
        run_parallel(cases, list_one, args.workers, status, stop, store)
    finally:
        status.finish()

    # 2. Plan in case order, so budget planning is deterministic.
    planned = Budget(args.budget)
    plans = [plan_case(c, d, order, args.threshold, args.include_paid, planned)
             for c, d in zip(cases, listed)]
    for plan, documents in zip(plans, listed):
        _err(_case_line(plan.case) + f"  ({len(documents)} document(s))")
        for row in plan.rows:
            if row["matched_type"]:
                price = ("free" if row["price"] == "0" else f"${Decimal(row['price']):,.2f}"
                         if row["price"] else "price?")
                _err(f"    {row['matched_type']:<18} {row['action']:<13} {price:<9} {row['document_name']}")
    _write_csv(out, (r for p in plans for r in p.rows), INVENTORY_FIELDS)

    text_records: list[dict[str, Any]] = []
    if not args.dry_run:
        # 3. Confirm per case, here in the main thread, before any download starts.
        confirm = Confirmer(args.yes)
        rows_by_case: dict[int, list[dict[str, Any]]] = {}
        approved: list[tuple[int, CasePlan]] = []
        for i, plan in enumerate(plans):
            if plan.tries and not confirm.quit:
                docs_text = ", then if needed ".join(
                    f"{c.doc_type} '{c.label}'" for c, _ in plan.tries)
                if confirm(f"{_tag(plan.case)} {plan.case.get('caseName') or ''}: "
                           f"download free {docs_text}?"):
                    approved.append((i, plan))
                    continue
                for _, row in plan.tries:
                    row["result"] = "declined"
                rows_by_case[i] = _gap_records(plan, declined=True)
            else:
                rows_by_case[i] = _gap_records(plan, declined=False)

        # 4. Download the approved cases in parallel.
        def checkpoint():
            _write_jsonl(text_out, (r for i in sorted(rows_by_case) for r in rows_by_case[i]))
            _write_csv(out, (r for p in plans for r in p.rows), INVENTORY_FIELDS)

        def fetch_one(_, item):
            i, plan = item
            status.add(active=1)
            try:
                return i, fetch_case(client, plan, args, status, stop)
            finally:
                status.add(active=-1, done=1)

        def collect(result):
            rows_by_case[result[0]] = result[1]
            checkpoint()

        checkpoint()
        if approved:
            status.start("Downloading", len(approved))
            try:
                run_parallel(approved, fetch_one, args.workers, status, stop, collect)
            finally:
                status.finish()
                checkpoint()
        text_records = [r for i in sorted(rows_by_case) for r in rows_by_case[i]]

    _err("")
    _err(summarize(plans, order, args.dry_run, args.include_paid, planned,
                   None if args.dry_run else text_records))
    written = f"{out}" + ("" if args.dry_run else f" and {text_out}")
    _err(f"  Wrote {written}; {_api_usage(client)}.")
    return 0


def read_documents(fh: TextIO, source: str = "input") -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Load chosen documents as (case, document) pairs. Only case_document_id is required.

    Rows of ``documents.csv`` work unchanged: their case columns name the case and
    their price, pages and name columns describe the document.
    """
    reader = csv.DictReader(fh)
    fields = {f.strip().lower(): f for f in reader.fieldnames or []}
    id_col = fields.get("case_document_id") or fields.get("casedocumentid")
    if not id_col:
        raise SystemExit(f"{source} needs a case_document_id column (as in documents.csv)")

    def col(row, name):
        key = fields.get(name)
        return (row.get(key) or "").strip() if key else ""

    pairs, seen = [], set()
    for row in reader:
        doc_id = (row.get(id_col) or "").strip()
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        case = {
            "caseId": col(row, "case_id"),
            "caseNumber": col(row, "case_number"),
            "caseName": col(row, "case_name"),
            "court": {"name": col(row, "court"), "type": col(row, "court_type")},
            "courtLocation": {"stateName": col(row, "state")},
            "filedDate": col(row, "filed_date"),
        }
        price = col(row, "price")
        doc = {
            "caseDocumentId": doc_id,
            "name": col(row, "document_name"),
            "description": col(row, "document_description"),
            "documentFiledDate": col(row, "document_filed_date"),
            "pages": col(row, "pages"),
            "price": price if price else None,
        }
        pairs.append((case, doc))
    return pairs


def _load_documents(args) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    if args.input_file and str(args.input_file) != "-":
        with args.input_file.open(newline="", encoding="utf-8-sig") as fh:
            return read_documents(fh, str(args.input_file))
    if sys.stdin.isatty():
        raise SystemExit("Give the documents with --input-file DOCS.csv (rows of documents.csv), "
                         "or pipe them in")
    return read_documents(io.StringIO(sys.stdin.read()), "stdin")


def _document_filename(case: dict[str, Any], doc: dict[str, Any]) -> str:
    case_no = re.sub(r"[^A-Za-z0-9._-]+", "_", case.get("caseNumber") or case.get("caseId") or "case")
    slug = re.sub(r"[^a-z0-9]+", "-", (doc.get("name") or "document").lower()).strip("-")[:40] or "document"
    return f"{case_no}_{slug}_{doc['caseDocumentId']}.pdf"


def fetch_document(client, case, doc, args, status: Status, stop: threading.Event) -> dict[str, Any]:
    """Download one chosen document and read its text (runs in a worker).

    Only free documents are fetched. A listed price other than 0 is refused
    without an API call; a blank one is left to ``obtain_file_url``, which
    re-reads the document and refuses anything that is not free right now.
    A PDF already in ``--pdf-dir`` is reused, so a stopped run can be repeated.
    """
    cand = docs_mod.Candidate("selected", 1.0, doc)
    tag = f"{_tag(case)} {doc['caseDocumentId']}"
    path = Path(args.pdf_dir) / _document_filename(case, doc)
    if stop.is_set():
        return _text_record(case, cand, "interrupted")
    if path.exists() and path.stat().st_size:
        status.log(f"  {tag}  already on disk: {path}")
        status.add(reused=1)
    else:
        if doc.get("price") is not None and docs_mod.price_of(doc) != 0:
            status.log(f"  {tag}  listed price {doc['price']!r}: {docs_mod.PAID_NOT_SUPPORTED}")
            return _text_record(case, cand, "paid-not-supported")
        status.log(f"  {tag}  fetching '{cand.label}'")
        waiting = {"on": False, "last": None}

        def on_order(state):
            if state != waiting["last"]:
                status.log(f"  {tag}  retrieval {state}")
                waiting["last"] = state
            if state in ("IN_PROGRESS", "DELAYED") and not waiting["on"]:
                waiting["on"] = True
                status.add(ordering=1)

        try:
            url = docs_mod.obtain_file_url(client, {**doc, "price": doc.get("price") or 0},
                                           priority=args.priority, on_status=on_order, stop=stop)
            docs_mod.download(client, url, path.parent, path.name)
        except docs_mod.PaidDownloadNotSupported as exc:
            status.log(f"  {tag}  {exc}")
            return _text_record(case, cand, "paid-not-supported")
        except (docs_mod.DocumentUnavailable, UniCourtError, OSError) as exc:
            status.log(f"  {tag}  could not fetch: {exc}")
            status.add(failed=1)
            return _text_record(case, cand, "download-failed")
        finally:
            if waiting["on"]:
                status.add(ordering=-1)
        status.add(pdfs=1)
    try:
        pages = read_pages(path)
    except Exception as exc:  # a damaged PDF must not stop the other documents
        status.log(f"  {tag}  could not read the text of {path}: {exc}")
        return _text_record(case, cand, "text-extraction-failed", path)
    with_text = sum(1 for p in pages if p)
    if not with_text:
        status.log(f"  {tag}  saved {path} (no text layer: scanned?)")
        return _text_record(case, cand, "no-text-layer", path, pages)
    status.add(texts=1)
    status.log(f"  {tag}  saved {path}: text on {with_text} of {len(pages)} page(s)")
    return _text_record(case, cand, "ok", path, pages)


def cmd_get_documents(args) -> int:
    if not 1 <= args.workers <= MAX_WORKERS:
        raise SystemExit(f"--workers must be between 1 and {MAX_WORKERS}")
    pairs = _load_documents(args)
    if not pairs:
        raise SystemExit("no documents to fetch")
    by_case: dict[str, list[int]] = {}
    for i, (case, _) in enumerate(pairs):
        by_case.setdefault(case["caseId"] or case["caseNumber"], []).append(i)

    def describe(doc):
        price = docs_mod.price_of(doc)
        cost = "price?" if doc.get("price") is None else "free" if price == 0 else f"${price:,.2f}"
        pages = f"{doc['pages']} p." if doc.get("pages") else "? p."
        return f"'{doc.get('name') or doc['caseDocumentId']}' ({pages}, {cost})"

    _err(f"{len(pairs)} document(s) in {len(by_case)} case(s)"
         + (" [dry run: no API calls, nothing downloaded]" if args.dry_run else ""))
    for indices in by_case.values():
        case = pairs[indices[0]][0]
        _err(f"{_tag(case)}  {case.get('caseName') or ''}")
        for i in indices:
            doc = pairs[i][1]
            on_disk = (Path(args.pdf_dir) / _document_filename(case, doc)).exists()
            _err(f"    {doc['caseDocumentId']}  {describe(doc)}" + ("  [on disk]" if on_disk else ""))
    if args.dry_run:
        return 0

    # Confirm per case, before anything is requested.
    confirm = Confirmer(args.yes)
    records: dict[int, dict[str, Any]] = {}
    approved: list[int] = []
    for indices in by_case.values():
        case = pairs[indices[0]][0]
        listing = ", ".join(describe(pairs[i][1]) for i in indices)
        if not confirm.quit and confirm(f"{_tag(case)} {case.get('caseName') or ''}: download {listing}?"):
            approved.extend(indices)
        else:
            for i in indices:
                records[i] = _text_record(pairs[i][0], docs_mod.Candidate("selected", 1.0, pairs[i][1]),
                                          "declined")

    text_out = Path(args.text_out)
    client = _client(args) if approved else None
    status, stop = Status(unit="documents"), threading.Event()

    def checkpoint():
        _write_jsonl(text_out, (records[i] for i in sorted(records)))

    def fetch_one(_, i):
        status.add(active=1)
        try:
            return i, fetch_document(client, *pairs[i], args, status, stop)
        finally:
            status.add(active=-1, done=1)

    def collect(result):
        records[result[0]] = result[1]
        checkpoint()

    checkpoint()
    if approved:
        status.start("Downloading", len(approved))
        try:
            run_parallel(sorted(approved), fetch_one, args.workers, status, stop, collect)
        finally:
            status.finish()
            for i in approved:  # cancelled by Ctrl-C before they started
                records.setdefault(i, _text_record(pairs[i][0], docs_mod.Candidate("selected", 1.0, pairs[i][1]),
                                                   "interrupted"))
            checkpoint()

    counts: dict[str, int] = {}
    for r in records.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    _err("")
    _err(f"Summary for {len(pairs)} document(s) in {len(by_case)} case(s): "
         + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    _err(f"  PDFs downloaded: {status.counts['pdfs']}; reused from {args.pdf_dir}: "
         f"{status.counts['reused']}; with text: {counts.get('ok', 0)}")
    _err(f"  Wrote {text_out}" + (f"; {_api_usage(client)}." if client else "; no API requests."))
    return 0


def cmd_extract(args) -> int:
    pages = read_pages(args.pdf)
    print(format_pages(pages))
    with_text = sum(1 for p in pages if p)
    _err(f"text on {with_text} of {len(pages)} page(s)")
    return 0 if with_text else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler = {
        "token": cmd_token, "courts": cmd_courts, "search": cmd_search,
        "get-complaints": cmd_get_complaints, "get-documents": cmd_get_documents,
        "extract": cmd_extract,
    }[args.command]
    try:
        return handler(args)
    except UniCourtError as exc:
        _err(f"UniCourt API error: {exc}")
        return 2
    except docs_mod.PaidDownloadNotSupported as exc:
        _err(f"Error: {exc}")
        return 2
    except ValueError as exc:
        _err(str(exc))
        return 2
    except KeyboardInterrupt:
        _err("interrupted")
        return 130
