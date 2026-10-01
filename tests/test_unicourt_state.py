"""Offline tests for unicourt_state: no network, no credentials.

The PDF tests need pypdf and are skipped without it.
"""

from __future__ import annotations

import contextlib
import json
import os
import stat
import re
from datetime import date, timedelta
import csv
import functools
import io
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unicourt_state import cli, documents  # noqa: E402
from unicourt_state import client as client_mod  # noqa: E402
from unicourt_state import credentials as credentials_mod  # noqa: E402
from unicourt_state import search as search_mod  # noqa: E402
from unicourt_state.status import Status  # noqa: E402
from unicourt_state.plaintiffs import (  # noqa: E402
    parse_plaintiffs,
    plaintiffs_from_caption,
    plaintiffs_from_cover_sheet,
    split_names,
)
from unicourt_state.search import build_query  # noqa: E402

try:
    import pypdf  # noqa: F401

    HAVE_PYPDF = True
except Exception:  # broken system installs can raise more than ImportError
    HAVE_PYPDF = False


def make_pdf(lines: list[str]) -> bytes:
    """A one-page PDF with one text line per entry (Helvetica, top to bottom)."""
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    ops = ["BT", "/F1 11 Tf", "14 TL", "54 760 Td"]
    for line in lines:
        ops.append(f"({esc(line)}) Tj T*")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
              % (len(objects) + 1, xref))
    return out.getvalue()


def doc(doc_id, name, price=0, repository="COURT_SOURCE", description=None, filed="2025-01-02"):
    return {
        "object": "CaseDocument",
        "caseDocumentId": doc_id,
        "name": name,
        "description": description,
        "documentFiledDate": f"{filed}T00:00:00-08:00",
        "pages": 2,
        "price": price,
        "repository": repository,
        "availabilityStatusAtCourtSource": "NO_KNOWN_ISSUE",
    }


# -- query --------------------------------------------------------------------

class BuildQueryTests(unittest.TestCase):
    def test_single_party_with_court_id(self):
        q = build_query(["Pfizer Inc"], court_id="CORTabc")
        self.assertEqual(q, '(Party:(name:"Pfizer Inc")) AND (Court:(courtId:"CORTabc"))')

    def test_all_is_the_default_and_any_is_or(self):
        q = build_query(["Pfizer", "Pharmacia"], court_name="X Court", role="defendant")
        self.assertIn(') AND (Party:', q)                 # default: every party (AND)
        self.assertNotIn(" OR ", q)
        self.assertIn('(PartyRole:(name:"defendant"))', q)
        self.assertIn('(Court:(name:"X Court"))', q)
        for match in ("any", "or"):
            self.assertIn(") OR (Party:", build_query(["Pfizer", "Pharmacia"], court_id="C", match=match))
        self.assertEqual(build_query(["A", "B"], court_id="C", match="and"),
                         build_query(["A", "B"], court_id="C", match="all"))

    def test_jurisdiction_and_court_type_scope(self):
        q = build_query(["Pfizer"], state="New York", court_type="state")
        self.assertEqual(q, '(Party:(name:"Pfizer")) AND (Court:(type:"State")) '
                            'AND (JurisdictionGeo:(state:"New York"))')
        q = build_query(["Pfizer"], state="Florida", county="Charlotte", court_type="federal")
        self.assertIn('(JurisdictionGeo:(state:"Florida" AND county:"Charlotte"))', q)
        self.assertIn('(Court:(type:"Federal"))', q)
        q = build_query(["Pfizer"], court_id="CORT1", court_type="state")  # scopes combine
        self.assertIn('(Court:(courtId:"CORT1")) AND (Court:(type:"State"))', q)

    def test_scope_validation(self):
        with self.assertRaises(ValueError):
            build_query(["A"])                                  # no scope at all
        with self.assertRaises(ValueError):
            build_query(["A"], county="Kings")                  # county without state
        with self.assertRaises(ValueError):
            build_query(["A"], court_type="tribal")
        self.assertTrue(build_query(["A"], court_type="state"))  # court type alone is a scope

    def test_cli_parses_scope_and_match(self):
        args = cli.build_parser().parse_args(
            ["search", "--state", "New York", "--court-type", "Federal", "--party", "A", "--party", "B"])
        self.assertEqual((args.state, args.court_type, args.match, args.court_id), ("New York", "federal", "all", None))

    def test_dates(self):
        q = build_query(["A"], court_id="C", filed_from="2024-01-01")
        self.assertTrue(q.endswith("filedDate:[2024-01-01T00:00:00 TO *]"))

    def test_quotes_are_neutralised(self):
        q = build_query(['Acme "Best" Co'], court_id="C")
        self.assertIn('name:"Acme  Best  Co"', q)

    def test_validation(self):
        with self.assertRaises(ValueError):
            build_query([], court_id="C")
        with self.assertRaises(ValueError):
            build_query(["x" * 2000], court_id="C")


# -- document choice -------------------------------------------------------------

class DocumentChoiceTests(unittest.TestCase):
    def test_similarity(self):
        sim = documents.phrase_similarity
        self.assertEqual(sim("Civil Case Cover Sheet", "civil case cover sheet"), 1.0)
        self.assertEqual(sim("COMPLAINT FOR DAMAGES", "complaint"), 1.0)
        self.assertGreater(sim("Civil Covr Sheet", "civil cover sheet"), 0.8)
        self.assertLess(sim("Summons", "complaint"), 0.5)

    def test_excluded_lookalikes(self):
        for name in ("Answer to Complaint", "Cross-Complaint", "Notice of Removal",
                     "Proof of Service of Summons and Complaint"):
            self.assertLess(documents.score_document(doc("D", name), "complaint"), 0.8, name)

    def test_is_free(self):
        self.assertTrue(documents.is_free(doc("D", "x", price=0)))
        self.assertTrue(documents.is_free(doc("D", "x", price=0.0)))
        self.assertFalse(documents.is_free(doc("D", "x", price=0.1)))
        self.assertFalse(documents.is_free(doc("D", "x", price=None)))
        # already in UniCourt's store but still priced: not free
        self.assertFalse(documents.is_free(doc("D", "x", price=0.2, repository="UNICOURT")))

    def _attempts(self, docs, include_paid=False, order=documents.DEFAULT_ORDER):
        matches = documents.match_all(docs, order)
        return [c.doc["caseDocumentId"] for c in documents.attempts(matches, order, include_paid)]

    def test_attempts_prefer_cover_sheet_then_complaint(self):
        docs = [doc("C1", "Complaint for Damages"), doc("S1", "Civil Case Cover Sheet"), doc("M1", "Summons")]
        self.assertEqual(self._attempts(docs), ["S1", "C1"])

    def test_priced_documents_need_include_paid_and_come_after_free(self):
        docs = [doc("S1", "Civil Cover Sheet", price=0.5), doc("C1", "Complaint", price=0)]
        self.assertEqual(self._attempts(docs), ["C1"])
        self.assertEqual(self._attempts(docs, include_paid=True), ["C1", "S1"])

    def test_unknown_price_and_sealed_never_attempted(self):
        sealed = {**doc("C2", "Complaint", price=0), "availabilityStatusAtCourtSource": "SEALED"}
        docs = [doc("C1", "Complaint", price=None), sealed]
        self.assertEqual(self._attempts(docs, include_paid=True), [])

    def test_earliest_filed_wins_ties(self):
        docs = [doc("C2", "Complaint", filed="2025-06-01"), doc("C1", "Complaint", filed="2025-01-01")]
        self.assertEqual(self._attempts(docs, order=["complaint"]), ["C1"])

    def test_paid_document_is_not_supported_and_never_ordered(self):
        paid = doc("D1", "Complaint", price=1.5, repository="UNICOURT")
        client = FakeClient({("GET", "caseDocument/D1"): paid})
        with self.assertRaises(documents.PaidDownloadNotSupported) as ctx:
            documents.obtain_file_url(client, paid)
        self.assertIn("not supported", str(ctx.exception))
        self.assertEqual(client.calls, [])  # refused before any request

    def test_obtain_refuses_priced_document(self):
        with self.assertRaises(documents.PaidDownloadNotSupported):
            documents.obtain_file_url(FakeClient({}), doc("D", "x", price=1))

    def test_obtain_orders_court_document_and_polls(self):
        client = FakeClient({
            ("GET", "caseDocument/D1"): doc("D1", "Complaint"),
            ("PUT", "caseDocumentOrder"): {"status": "IN_PROGRESS", "caseDocumentOrderCallbackId": "CB1"},
            ("GET", "caseDocumentOrder/callbacks/CB1"): [
                {"status": "IN_PROGRESS", "caseDocumentOrderCallbackId": "CB1"},
                {"status": "COMPLETE", "caseDocumentOrderCallbackId": "CB1",
                 "file": {"fileUrl": "https://files/x.pdf"}},
            ],
        })
        with mock.patch.object(documents.time, "sleep"):
            url = documents.obtain_file_url(client, doc("D1", "Complaint"), poll_seconds=0)
        self.assertEqual(url, "https://files/x.pdf")
        put = client.calls[1]
        self.assertEqual(put[0:2], ("PUT", "caseDocumentOrder"))
        self.assertFalse(put[2]["reOrder"])
        self.assertFalse(put[2]["isPreviewOnly"])

    def test_obtain_downloads_stored_document_directly(self):
        client = FakeClient({
            ("GET", "caseDocument/D1"): doc("D1", "Complaint", repository="UNICOURT"),
            ("GET", "caseDocumentDownload/D1"): {"fileUrl": "https://files/y.pdf"},
        })
        url = documents.obtain_file_url(client, doc("D1", "Complaint", repository="UNICOURT"))
        self.assertEqual(url, "https://files/y.pdf")
        self.assertEqual([c[0] for c in client.calls], ["GET", "GET"])

    def test_is_free_rejects_unreadable_prices(self):
        for price in ("free", "", True, [0]):
            self.assertFalse(documents.is_free(doc("D", "x", price=price)), price)
        self.assertTrue(documents.is_free(doc("D", "x", price="0")))

    def test_price_change_before_order_blocks_it(self):
        # listed as free, but the fresh copy now carries a price
        client = FakeClient({("GET", "caseDocument/D1"): doc("D1", "Complaint", price=0.4)})
        with self.assertRaises(documents.PaidDownloadNotSupported):
            documents.obtain_file_url(client, doc("D1", "Complaint", price=0))
        self.assertEqual([(c[0], c[1]) for c in client.calls], [("GET", "caseDocument/D1")])

    def test_unconfirmable_price_blocks_order(self):
        client = FakeClient({})  # caseDocument lookup fails
        client._serve = mock.Mock(side_effect=documents.UniCourtError(500, "UN500"))
        with self.assertRaises(documents.DocumentUnavailable):
            documents.obtain_file_url(client, doc("D1", "Complaint", price=0))

    def test_failed_order_raises(self):
        client = FakeClient({("GET", "caseDocument/D"): doc("D", "Complaint"),
                             ("PUT", "caseDocumentOrder"): {
            "status": "FAILURE", "caseDocumentOrderCallbackId": "CB",
            "exception": {"message": "DELAYED_AT_THE_COURT_SOURCE", "details": "slow"}}})
        with self.assertRaises(documents.DocumentUnavailable):
            documents.obtain_file_url(client, doc("D", "Complaint"))


# -- plaintiff parsing ----------------------------------------------------------

CA_COMPLAINT = """\
1 JOHN LAWYER (SBN 123456)
2 LAWYER LLP
3 100 Main Street, Suite 200
4 Attorneys for Plaintiffs
5
SUPERIOR COURT OF THE STATE OF CALIFORNIA
FOR THE COUNTY OF LOS ANGELES
6 JANE DOE, an individual; and MARIA
7 GARCIA, individually and as successor in interest to Jose Garcia,
8 Plaintiffs, Case No.: 25STCV01234
9 v. COMPLAINT FOR DAMAGES
10 PFIZER INC., a Delaware corporation; and DOES 1 through 50,
11 Defendants.
"""

NY_COMPLAINT = """\
SUPREME COURT OF THE STATE OF NEW YORK
COUNTY OF KINGS
ROBERT SMITH and LINDA SMITH, Index No. 500123/2025
Plaintiffs,
-against-
ACME CORP.,
Defendant.
"""

TX_PETITION = """\
CAUSE NO. 2025-12345
IN THE DISTRICT COURT OF HARRIS COUNTY, TEXAS
ANGELA BROWN, Plaintiff, v. ACME CORP., Defendant
PLAINTIFF'S ORIGINAL PETITION
"""

TX_COVER_SHEET = """\
CIVIL CASE INFORMATION SHEET
CAUSE NUMBER (FOR CLERK USE ONLY): COURT (FOR CLERK USE ONLY):
STYLED Angela Brown v. Acme Corp.
Plaintiff(s)/Petitioner(s):
Angela Brown
Defendant(s)/Respondent(s):
Acme Corp.
"""

FL_COVER_SHEET = """\
FORM 1.997. CIVIL COVER SHEET
IN THE CIRCUIT COURT OF THE ELEVENTH JUDICIAL CIRCUIT
IN AND FOR MIAMI-DADE COUNTY, FLORIDA
Plaintiff
Carlos Rivera
Ana Rivera
vs.
Defendant
Acme Corp.
"""

CA_COVER_SHEET = """\
CM-010
CASE NAME: Jane Doe, et al. v. Pfizer Inc.
CIVIL CASE COVER SHEET
"""


class PlaintiffParsingTests(unittest.TestCase):
    def test_california_caption(self):
        self.assertEqual(plaintiffs_from_caption(CA_COMPLAINT), ["JANE DOE", "MARIA GARCIA"])

    def test_new_york_caption(self):
        self.assertEqual(plaintiffs_from_caption(NY_COMPLAINT), ["ROBERT SMITH", "LINDA SMITH"])

    def test_inline_caption(self):
        self.assertEqual(plaintiffs_from_caption(TX_PETITION), ["ANGELA BROWN"])

    def test_texas_cover_sheet(self):
        self.assertEqual(plaintiffs_from_cover_sheet(TX_COVER_SHEET), ["Angela Brown"])

    def test_florida_cover_sheet(self):
        self.assertEqual(plaintiffs_from_cover_sheet(FL_COVER_SHEET), ["Carlos Rivera", "Ana Rivera"])

    def test_cover_sheet_case_name_fallback(self):
        self.assertEqual(plaintiffs_from_cover_sheet(CA_COVER_SHEET), ["Jane Doe"])

    def test_cover_sheet_falls_back_to_caption(self):
        names, method = parse_plaintiffs(NY_COMPLAINT, "civil-cover-sheet")
        self.assertEqual((names, method), (["ROBERT SMITH", "LINDA SMITH"], "caption"))

    def test_nothing_found(self):
        self.assertEqual(parse_plaintiffs("Exhibit A\nInvoice total 42", "complaint"), ([], ""))

    def test_split_names_drops_descriptors(self):
        self.assertEqual(
            split_names("JOHN ROE, a minor, by and through his guardian ad litem MARY ROE; "
                        "PAT LEE, an individual"),
            ["JOHN ROE", "PAT LEE"],
        )


# -- end-to-end run with a fake API ------------------------------------------------

class FakeClient:
    """Routes (method, path) to canned responses; lists are served in turn."""

    def __init__(self, routes, files=None):
        self.routes = routes
        self.files = files or {}
        self.calls = []
        self.params = []
        self.requests_made = 0
        self.rate_limited = 0
        self.limiter = SimpleNamespace(waited=0.0)

    def _serve(self, method, path, body=None, params=None):
        self.calls.append((method, path, body))
        self.params.append(params)
        self.requests_made += 1
        route = re.sub(r"^/workspace/[^/]+/", "", path.split("?")[0])  # nextPageAPI links are absolute
        value = self.routes[(method, route)]
        if callable(value):  # dynamic route: gets the query parameters
            query = dict(urllib.parse.parse_qsl(path.split("?", 1)[1])) if "?" in path else {}
            return value({**query, **(params or {})})
        if isinstance(value, list):
            return value.pop(0) if len(value) > 1 else value[0]
        return value

    def get(self, path, params=None):
        return self._serve("GET", path, params=params)

    def put(self, path, body):
        return self._serve("PUT", path, body)

    # the real pagination logic, run against the fake routes
    paginate = client_mod.UniCourtClient.paginate
    iter_pages = client_mod.UniCourtClient.iter_pages

    def fetch_file(self, url, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.files[url])
        return len(self.files[url])


CASE = {
    "caseId": "CASEtest0000000001",
    "caseNumber": "25STCV01234",
    "caseName": "Jane Doe, et al. vs Pfizer Inc.",
    "filedDate": "2025-01-02T00:00:00+00:00",
    "court": {"name": "Los Angeles County Superior Court", "type": "State"},
}


def write_cases(tmp, rows, header="case_id,case_number,case_name,court,filed_date"):
    path = Path(tmp) / "cases.csv"
    lines = [header] + [",".join(r) for r in rows]
    path.write_text("\n".join(lines) + "\n")
    return path


class GetComplaintsBase(unittest.TestCase):
    """Runs cmd_get_complaints against a FakeClient serving several cases."""

    def _client(self, docs_by_case, files=None, orders=None):
        routes = {}
        for case_id, docs in docs_by_case.items():
            routes[("GET", f"case/{case_id}/documents")] = {"caseDocumentArray": docs}
            for d in docs:
                routes[("GET", f"caseDocument/{d['caseDocumentId']}")] = d
                routes[("GET", f"caseDocumentDownload/{d['caseDocumentId']}")] = {
                    "fileUrl": f"https://f/{d['caseDocumentId']}.pdf"}
        client = FakeClient(routes, files or {})
        if orders is not None:  # PUT caseDocumentOrder completes at once with the doc's file
            def serve(method, path, body=None, _orig=client._serve):
                if method == "PUT":
                    client.calls.append((method, path, body))
                    orders.append(body["caseDocumentId"])
                    return {"status": "COMPLETE", "caseDocumentOrderCallbackId": "CB",
                            "file": {"fileUrl": f"https://f/{body['caseDocumentId']}.pdf"}}
                return _orig(method, path, body)
            client._serve = serve
        return client

    def _args(self, tmp, cases_csv, **kw):
        base = dict(input_file=cases_csv, dry_run=False, include_paid=False, budget=None,
                    doc_types="civil-cover-sheet,complaint", threshold=0.8, limit=0,
                    out=str(Path(tmp) / "documents.csv"),
                    plaintiffs_out=str(Path(tmp) / "plaintiffs.csv"),
                    pdf_dir=str(Path(tmp) / "pdfs"), yes=True, priority="level2",
                    workers=3, token="t", workspace="w", verbose=False)
        base.update(kw)
        return SimpleNamespace(**base)

    def _run(self, client, args, ask=None):
        err = io.StringIO()
        patches = [mock.patch.object(cli, "_client", return_value=client), redirect_stderr(err)]
        if ask is not None:
            patches.append(mock.patch.object(cli, "_ask_terminal", side_effect=ask))
        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            cli.cmd_get_complaints(args)

        def read(path):
            if not Path(path).exists():
                return None
            with open(path) as fh:
                return list(csv.DictReader(fh))
        return read(args.out), read(args.plaintiffs_out), err.getvalue()


class CaseListTests(unittest.TestCase):
    def _search(self, tmp, fmt="auto", out=None):
        client = FakeClient({("GET", "caseSearch"): {"caseSearchResultArray": [CASE], "totalCount": 7}})
        args = SimpleNamespace(court_id="C", court_name=None, party=["Pfizer"], match="any",
                               state=None, county=None, court_type=None,
                               role=None, filed_from=None, filed_to=None, limit=1, format=fmt,
                               out=out, token="t", workspace="w", verbose=False)
        stdout, err = io.StringIO(), io.StringIO()
        with mock.patch.object(cli, "_client", return_value=client), redirect_stderr(err), \
                redirect_stdout(stdout):
            cli.cmd_search(args)
        return stdout.getvalue(), err.getvalue()

    def test_search_out_writes_a_case_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "cases.csv"
            _, err = self._search(tmp, out=str(out))
            with out.open() as fh:
                cases = cli.read_cases(fh)
        self.assertIn("1 of 7 matching case(s)", err)
        self.assertEqual(cases[0]["caseId"], CASE["caseId"])
        self.assertEqual(cases[0]["caseNumber"], "25STCV01234")
        self.assertEqual(cases[0]["court"]["name"], "Los Angeles County Superior Court")

    def test_piped_search_output_is_a_case_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout, _ = self._search(tmp)  # captured stdout is not a terminal -> CSV
        cases = cli.read_cases(io.StringIO(stdout))
        self.assertEqual([c["caseId"] for c in cases], [CASE["caseId"]])
        with tempfile.TemporaryDirectory() as tmp:
            table, _ = self._search(tmp, fmt="table")
        self.assertTrue(table.startswith("25STCV01234  2025-01-02"))

    def test_get_complaints_reads_stdin_pipe(self):
        piped = "case_id,case_number\nCASE1,25-1\n"
        args = SimpleNamespace(input_file=None)
        with mock.patch.object(cli.sys, "stdin", io.StringIO(piped)):
            cases = cli._load_cases(args)
        self.assertEqual([(c["caseId"], c["caseNumber"]) for c in cases], [("CASE1", "25-1")])

    def test_read_cases_accepts_minimal_and_edited_lists(self):
        text = "caseId\nCASEa\n\nCASEb\nCASEa\n"
        self.assertEqual([c["caseId"] for c in cli.read_cases(io.StringIO(text))], ["CASEa", "CASEb"])
        with self.assertRaises(SystemExit):
            cli.read_cases(io.StringIO("number\nx\n"))


class OptionTests(unittest.TestCase):
    def test_include_paid_requires_budget_and_vice_versa(self):
        for extra in (["--include-paid"], ["--budget", "10"]):
            with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                cli.cmd_get_complaints(cli.build_parser().parse_args(
                    ["get-complaints", "-i", "x.csv", *extra]))

    def test_budget_parsing(self):
        args = cli.build_parser().parse_args(
            ["get-complaints", "-i", "x.csv", "--include-paid", "--budget", "$1,250.50"])
        self.assertEqual(args.budget, Decimal("1250.50"))
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            cli.build_parser().parse_args(["get-complaints", "--budget", "-5"])


class DryRunTests(GetComplaintsBase):
    DOCS = {
        "CASE1": [doc("S1", "Civil Case Cover Sheet", price=0), doc("C1", "Complaint", price=1.2),
                  doc("X1", "Notice of Hearing", price=0)],
        "CASE2": [doc("C2", "Complaint for Damages", price=2.5), doc("M2", "Summons", price=0)],
        "CASE3": [doc("C3", "Original Petition", price=0)],
        "CASE4": [doc("M4", "Summons", price=0)],
        "CASE5": [doc("C5", "Complaint", price=None)],
        "CASE6": [],
    }

    def _dry(self, **kw):
        client = self._client(self.DOCS)
        with tempfile.TemporaryDirectory() as tmp:
            cases = write_cases(tmp, [[c, "", "", "", ""] for c in self.DOCS])
            inventory, plaintiffs, err = self._run(client, self._args(tmp, cases, dry_run=True, **kw))
        return client, inventory, plaintiffs, err

    def test_inventory_lists_every_document_with_price_and_action(self):
        client, inventory, plaintiffs, err = self._dry()
        rows = {(r["case_id"], r["case_document_id"]): r for r in inventory}
        self.assertEqual(len(inventory), 9)  # 8 documents + 1 placeholder for the empty case
        self.assertEqual(rows[("CASE1", "S1")]["action"], "download")
        self.assertEqual(rows[("CASE1", "C1")]["action"], "paid-skip")
        self.assertEqual(rows[("CASE1", "C1")]["price"], "1.2")
        self.assertEqual(rows[("CASE1", "X1")]["action"], "")          # not a wanted type
        self.assertEqual(rows[("CASE1", "X1")]["matched_type"], "")
        self.assertEqual(rows[("CASE3", "C3")]["action"], "download")
        self.assertEqual(rows[("CASE5", "C5")]["action"], "unknown-price")
        self.assertEqual(rows[("CASE6", "")]["action"], "no-documents")
        self.assertIsNone(plaintiffs)
        self.assertFalse(any(c[0] == "PUT" or c[1].startswith("caseDocument") for c in client.calls))

    def test_summary(self):
        _, _, _, err = self._dry()
        self.assertIn("Summary for 6 case(s), 8 document(s) listed (dry run", err)
        self.assertIn("paid    2 ($3.70)", err)
        self.assertIn("Cases with a free document: 2", err)
        self.assertIn("Cases with only paid documents: 1 (cheapest document per case: $2.50 in total)", err)
        self.assertIn("Cases with nothing usable: 3", err)
        self.assertIn("Paid documents are not downloaded (downloading them is not supported)", err)

    def test_dry_run_with_budget_plans_purchases_in_case_order(self):
        _, inventory, _, err = self._dry(include_paid=True, budget=Decimal("2"))
        rows = {(r["case_id"], r["case_document_id"]): r["action"] for r in inventory}
        self.assertEqual(rows[("CASE1", "S1")], "download")
        self.assertEqual(rows[("CASE1", "C1")], "buy-fallback")   # free cover sheet comes first
        self.assertEqual(rows[("CASE2", "C2")], "over-budget")    # $2.50 > $2.00
        self.assertIn("Paid documents, budget $2.00: planned 0 for $0.00; over budget 1", err)
        self.assertIn("plan only: downloading paid documents is not supported", err)
        _, inventory, _, err = self._dry(include_paid=True, budget=Decimal("3"))
        self.assertIn(("CASE2", "C2", "buy"), {(r["case_id"], r["case_document_id"], r["action"]) for r in inventory})
        self.assertIn("planned 1 for $2.50", err)

    def test_free_fallback_is_marked(self):
        docs = {"CASE1": [doc("S1", "Civil Cover Sheet", price=0), doc("C1", "Complaint", price=0)]}
        with tempfile.TemporaryDirectory() as tmp:
            cases = write_cases(tmp, [["CASE1", "", "", "", ""]])
            inventory, _, _ = self._run(self._client(docs), self._args(tmp, cases, dry_run=True))
        self.assertEqual([r["action"] for r in inventory], ["download", "fallback"])


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class DownloadTests(GetComplaintsBase):
    def test_cover_sheet_gives_plaintiffs(self):
        docs = {"CASE1": [doc("S1", "Civil Cover Sheet", repository="UNICOURT"),
                          doc("C1", "Complaint", repository="UNICOURT")]}
        files = {"https://f/S1.pdf": make_pdf(TX_COVER_SHEET.splitlines())}
        with tempfile.TemporaryDirectory() as tmp:
            cases = write_cases(tmp, [["CASE1", "2025-1", "Brown v. Acme", "Harris", "2025-01-02"]])
            inventory, rows, err = self._run(self._client(docs, files), self._args(tmp, cases))
        self.assertEqual([r["plaintiff"] for r in rows], ["Angela Brown"])
        self.assertEqual(rows[0]["case_number"], "2025-1")
        by_id = {r["case_document_id"]: r for r in inventory}
        self.assertEqual((by_id["S1"]["result"], by_id["S1"]["plaintiffs_found"]), ("downloaded", "1"))
        self.assertEqual(by_id["C1"]["result"], "")  # fallback not needed
        self.assertIn("PDFs downloaded: 1; plaintiffs found: 1 in 1 case(s)", err)

    def test_falls_back_to_complaint_when_cover_sheet_has_no_names(self):
        docs = {"CASE1": [doc("S1", "Civil Cover Sheet", repository="UNICOURT"),
                          doc("C1", "Complaint for Damages", repository="UNICOURT")]}
        files = {"https://f/S1.pdf": make_pdf(["CIVIL COVER SHEET", "Check one box"]),
                 "https://f/C1.pdf": make_pdf(NY_COMPLAINT.splitlines())}
        with tempfile.TemporaryDirectory() as tmp:
            cases = write_cases(tmp, [["CASE1", "", "", "", ""]])
            _, rows, _ = self._run(self._client(docs, files), self._args(tmp, cases))
        self.assertEqual([r["plaintiff"] for r in rows], ["ROBERT SMITH", "LINDA SMITH"])

    def test_paid_documents_are_never_fetched(self):
        docs = {"CASE1": [doc("S1", "Civil Cover Sheet", price=0.5), doc("C1", "Complaint", price=3)]}
        client = self._client(docs)
        with tempfile.TemporaryDirectory() as tmp:
            cases = write_cases(tmp, [["CASE1", "", "", "", ""]])
            _, rows, _ = self._run(client, self._args(tmp, cases))
        self.assertEqual(rows[0]["status"], "no-free-document")
        self.assertFalse(any(c[0] == "PUT" or c[1].startswith("caseDocument") for c in client.calls))

    def test_include_paid_without_dry_run_is_not_supported(self):
        docs = {"CASE1": [doc("C1", "Complaint", price=1.5)]}
        client = self._client(docs)
        with tempfile.TemporaryDirectory() as tmp:
            cases = write_cases(tmp, [["CASE1", "", "", "", ""]])
            with self.assertRaises(SystemExit) as ctx:
                self._run(client, self._args(tmp, cases, include_paid=True, budget=Decimal("10")))
        self.assertIn("Downloading paid documents is not supported", str(ctx.exception.code))
        self.assertEqual(client.calls, [])  # stopped before any API call

    def test_main_reports_paid_error_cleanly(self):
        err = io.StringIO()
        with mock.patch.object(cli, "cmd_get_complaints",
                               side_effect=documents.PaidDownloadNotSupported("(x: $1)")), \
                redirect_stderr(err):
            code = cli.main(["get-complaints", "-i", "x.csv"])
        self.assertEqual(code, 2)
        self.assertIn("Error: Downloading paid documents is not supported", err.getvalue())

    def test_declined_and_no_terminal_download_nothing(self):
        docs = {"CASE1": [doc("S1", "Civil Cover Sheet", repository="UNICOURT")]}
        for answer in ("n", None):  # None: no terminal to ask
            client = self._client(docs)
            with tempfile.TemporaryDirectory() as tmp:
                cases = write_cases(tmp, [["CASE1", "", "", "", ""]])
                inventory, rows, _ = self._run(client, self._args(tmp, cases, yes=False),
                                               ask=lambda prompt, a=answer: a)
            self.assertEqual(rows[0]["status"], "declined")
            self.assertEqual(inventory[0]["result"], "declined")
            self.assertFalse(any(c[1].startswith("caseDocument") for c in client.calls))


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class ParallelTests(GetComplaintsBase):
    def test_many_cases_in_parallel_keep_case_order_and_report_status(self):
        n = 8
        docs = {f"CASE{i}": [doc(f"C{i}", "Complaint", repository="UNICOURT")] for i in range(n)}
        files = {f"https://f/C{i}.pdf": make_pdf(NY_COMPLAINT.splitlines()) for i in range(n)}
        with tempfile.TemporaryDirectory() as tmp:
            cases = write_cases(tmp, [[c, f"N{c}", "", "", ""] for c in docs])
            inventory, rows, err = self._run(self._client(docs, files), self._args(tmp, cases, workers=4))
        self.assertEqual([r["case_id"] for r in rows], [c for c in docs for _ in (0, 1)])
        self.assertTrue(all(r["status"] == "ok" for r in rows))
        self.assertEqual({r["result"] for r in inventory}, {"downloaded"})
        self.assertIn("[Listing documents: 8/8 cases", err)
        self.assertIn("[Downloading: 8/8 cases | 0 active | 8 PDFs, 16 plaintiffs", err)
        self.assertIn("NCASE3  saved", err)

    def test_court_order_status_is_reported(self):
        docs = {"CASE1": [doc("C1", "Complaint", repository="COURT_SOURCE")]}
        files = {"https://f/C1.pdf": make_pdf(NY_COMPLAINT.splitlines())}
        client = self._client(docs, files)
        client.routes[("PUT", "caseDocumentOrder")] = {"status": "IN_PROGRESS", "caseDocumentOrderCallbackId": "CB1"}
        client.routes[("GET", "caseDocumentOrder/callbacks/CB1")] = [
            {"status": "IN_PROGRESS", "caseDocumentOrderCallbackId": "CB1"},
            {"status": "COMPLETE", "caseDocumentOrderCallbackId": "CB1", "file": {"fileUrl": "https://f/C1.pdf"}},
        ]
        fast = functools.partial(documents.obtain_file_url, poll_seconds=0)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(documents, "obtain_file_url", fast):
            cases = write_cases(tmp, [["CASE1", "25-1", "", "", ""]])
            _, rows, err = self._run(client, self._args(tmp, cases))
        self.assertEqual(rows[0]["status"], "ok")
        self.assertIn("25-1  complaint order IN_PROGRESS", err)
        self.assertIn("25-1  complaint order COMPLETE", err)
        self.assertEqual(err.count("order IN_PROGRESS"), 1)  # logged on change, not every poll


class StatusAndStopTests(unittest.TestCase):
    def test_status_log_and_final_line_without_terminal(self):
        out = io.StringIO()
        status = Status(stream=out, live=False, quiet_interval=3600).start("Downloading", 3)
        status.add(active=1)
        status.log("  25-1  saved x.pdf")
        status.add(active=-1, done=1, pdfs=1, plaintiffs=2)
        status.finish()
        text = out.getvalue()
        self.assertIn("  25-1  saved x.pdf\n", text)
        self.assertIn("[Downloading: 1/3 cases | 0 active | 1 PDFs, 2 plaintiffs | 0m00s]", text)
        self.assertNotIn("\r", text)  # no live redraws when not a terminal

    def test_live_status_redraws_in_place(self):
        out = io.StringIO()
        status = Status(stream=out, live=True, interval=3600).start("Listing documents", 2)
        status.log("event")
        status.finish()
        self.assertIn("\r\033[K", out.getvalue())
        self.assertTrue(out.getvalue().endswith("[Listing documents: 0/2 cases | 0 active | 0m00s]\n"))

    def test_stop_interrupts_waiting_on_an_order(self):
        import threading
        client = FakeClient({
            ("GET", "caseDocument/D1"): doc("D1", "Complaint"),
            ("PUT", "caseDocumentOrder"): {"status": "IN_PROGRESS", "caseDocumentOrderCallbackId": "CB1"},
        })
        stop = threading.Event()
        stop.set()
        with self.assertRaises(documents.DocumentUnavailable) as ctx:
            documents.obtain_file_url(client, doc("D1", "Complaint"), poll_seconds=3600, stop=stop)
        self.assertIn("interrupted", str(ctx.exception))

    def test_workers_range(self):
        args = cli.build_parser().parse_args(["get-complaints", "-i", "x.csv", "--workers", "0"])
        with self.assertRaises(SystemExit):
            cli.cmd_get_complaints(args)


class RateLimitTests(unittest.TestCase):
    def test_thirty_per_five_seconds_with_a_fake_clock(self):
        now = [0.0]
        slept = []

        def sleep(seconds):
            slept.append(seconds)
            now[0] += seconds

        limiter = client_mod.RateLimiter(clock=lambda: now[0], sleep=sleep)
        for _ in range(30):
            limiter.acquire()
        self.assertEqual(slept, [])          # the first 30 go straight through
        now[0] = 1.0
        limiter.acquire()                     # the 31st waits for the window to roll
        self.assertEqual(now[0], 5.0)
        self.assertAlmostEqual(limiter.waited, 4.0)

    def test_window_holds_across_threads(self):
        import threading
        limiter = client_mod.RateLimiter(calls=5, period=0.3)
        stamps, lock = [], threading.Lock()

        def worker():
            for _ in range(5):
                limiter.acquire()
                with lock:
                    stamps.append(time.monotonic())

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        stamps.sort()
        self.assertEqual(len(stamps), 20)
        for i in range(len(stamps) - 5):  # never 6 requests inside one window
            self.assertGreaterEqual(stamps[i + 5] - stamps[i], 0.3 - 0.01)

    def test_pause_holds_everyone_back(self):
        now = [10.0]
        limiter = client_mod.RateLimiter(clock=lambda: now[0],
                                         sleep=lambda s: now.__setitem__(0, now[0] + s))
        limiter.pause(5)
        limiter.acquire()
        self.assertEqual(now[0], 15.0)

    def _client_with_responses(self, responses):
        """A real UniCourtClient whose urlopen replays (status, headers) responses."""
        now = [0.0]
        limiter = client_mod.RateLimiter(clock=lambda: now[0],
                                         sleep=lambda s: now.__setitem__(0, now[0] + s))
        api = client_mod.UniCourtClient("tok", "wk1", root="https://api.test", limiter=limiter)
        calls = []

        def urlopen(req, timeout=None, context=None):
            calls.append(now[0])
            status, headers, *body = responses.pop(0)
            if status == 200:
                resp = mock.MagicMock()
                resp.__enter__.return_value.read.return_value = b'{"ok": true}'
                return resp
            raise urllib.error.HTTPError(req.full_url, status, "error",
                                         headers, io.BytesIO(body[0] if body else b"{}"))
        return api, urlopen, calls, now

    def test_429_pauses_for_retry_after_then_succeeds(self):
        import email.message
        hdrs = email.message.Message()
        hdrs["Retry-After"] = "3"
        api, urlopen, calls, now = self._client_with_responses([(429, hdrs), (200, None)])
        with mock.patch.object(client_mod.urllib.request, "urlopen", urlopen):
            self.assertEqual(api.get("caseSearch"), {"ok": True})
        self.assertEqual(calls, [0.0, 3.0])  # retried after Retry-After, via the limiter
        self.assertEqual((api.rate_limited, api.requests_made), (1, 2))

    def test_documented_rate_limit_bodies_are_recognised(self):
        import email.message
        bodies = [b'{"object": "Exception", "code": "UN429", "message": "TOO_MANY_REQUESTS", '
                  b'"details": "Too Many Requests."}',
                  b'{"message": "Too Many Requests"}']
        for body in bodies:
            # whatever the status code, the body alone marks it as rate limited
            api, urlopen, calls, now = self._client_with_responses(
                [(400, email.message.Message(), body), (200, None)])
            with mock.patch.object(client_mod.urllib.request, "urlopen", urlopen):
                self.assertEqual(api.get("caseSearch"), {"ok": True})
            self.assertEqual(api.rate_limited, 1, body)

    def test_other_errors_are_not_treated_as_rate_limits(self):
        import email.message
        api, urlopen, calls, now = self._client_with_responses(
            [(400, email.message.Message(), b'{"code": "UN400", "message": "INVALID_INPUT"}')])
        with mock.patch.object(client_mod.urllib.request, "urlopen", urlopen):
            with self.assertRaises(client_mod.UniCourtError) as ctx:
                api.get("caseSearch")
        self.assertEqual((ctx.exception.code, api.rate_limited), ("UN400", 0))

    def test_429_without_header_waits_a_full_window_and_gives_up_eventually(self):
        import email.message
        responses = [(429, email.message.Message()) for _ in range(client_mod.RATE_LIMITED_RETRIES + 1)]
        api, urlopen, calls, now = self._client_with_responses(responses)
        with mock.patch.object(client_mod.urllib.request, "urlopen", urlopen), \
                mock.patch.object(client_mod.time, "sleep"):
            with self.assertRaises(client_mod.UniCourtError) as ctx:
                api.get("caseSearch")
        self.assertEqual(ctx.exception.status, 429)
        self.assertEqual(calls[1] - calls[0], 5.0)
        self.assertEqual(len(calls), client_mod.RATE_LIMITED_RETRIES + 1)


class PaginationTests(unittest.TestCase):
    def test_follows_next_page_and_sends_page_number(self):
        client = FakeClient({("GET", "case/X/documents"): lambda q: {
            "1": {"caseDocumentArray": [{"n": 1}, {"n": 2}], "totalCount": 3, "totalPages": 2,
                  "nextPageAPI": "/workspace/w/case/X/documents?pageNumber=2"},
            "2": {"caseDocumentArray": [{"n": 3}], "nextPageAPI": None},
        }[str(q["pageNumber"])]})
        meta = {}
        items = list(client.paginate("case/X/documents", "caseDocumentArray", {"sortBy": "x"}, meta=meta))
        self.assertEqual([i["n"] for i in items], [1, 2, 3])
        self.assertEqual(client.params[0], {"pageNumber": 1, "sortBy": "x"})
        self.assertEqual((meta["totalCount"], meta["totalPages"]), (3, 2))

    def test_reads_data_property_and_stops_on_empty_page(self):
        pages = [{"data": [{"n": 1}], "nextPageAPI": "/x?pageNumber=2"},
                 {"data": [], "nextPageAPI": "/x?pageNumber=3"},  # past the end: empty, not an error
                 {"data": [{"n": 99}], "nextPageAPI": None}]
        client = FakeClient({("GET", "x"): pages, ("GET", "/x"): pages})
        self.assertEqual([i["n"] for i in client.paginate("x", "caseSearchResultArray")], [1])
        self.assertEqual(len(client.calls), 2)

    def test_find_courts_sends_page_number(self):
        client = FakeClient({("GET", "masterData/court"): {"courtArray": [{"courtId": "C1"}]}})
        search_mod.find_courts(client, "Los Angeles")
        self.assertEqual(client.params[0]["pageNumber"], 1)


class SearchSplitTests(unittest.TestCase):
    """caseSearch over a simulated index: 10 per page, cap patched down to 20."""

    RANGE = re.compile(r"filedDate:\[(\S+) TO (\S+)\]")

    def _index(self, cases):
        def handler(q):
            m = self.RANGE.search(q["q"])
            lo = m.group(1)[:10] if m and m.group(1) != "*" else "0000-00-00"
            hi = m.group(2)[:10] if m and m.group(2) != "*" else "9999-99-99"
            hits = sorted((c for c in cases if lo <= c["filedDate"][:10] <= hi),
                          key=lambda c: c["filedDate"], reverse=q.get("order", "desc") == "desc")
            page = int(q["pageNumber"])
            hits_page = hits[(page - 1) * 10: page * 10] if page <= 2 else []  # 2 pages = cap of 20
            more = page < min(2, (len(hits) + 9) // 10)
            nxt = "caseSearch?" + urllib.parse.urlencode({**q, "pageNumber": page + 1}) if more else None
            return {"caseSearchResultArray": hits_page, "totalCount": len(hits), "nextPageAPI": nxt}
        return FakeClient({("GET", "caseSearch"): handler})

    @staticmethod
    def _cases(n, start=date(2024, 1, 1), per_day=1):
        return [{"caseId": f"C{i}", "filedDate": f"{start + timedelta(days=i // per_day)}T00:00:00+00:00"}
                for i in range(n)]

    def _search(self, client, **kw):
        make = lambda f, t: search_mod.build_query(["Acme"], court_id="CX", filed_from=f, filed_to=t)  # noqa: E731
        notes, meta = [], {}
        with mock.patch.object(search_mod, "CASE_SEARCH_CAP", 20):
            found = list(search_mod.search_cases(client, make, meta=meta, note=notes.append, **kw))
        return found, notes, meta

    def test_under_the_cap_is_one_query(self):
        found, notes, meta = self._search(self._index(self._cases(15)))
        self.assertEqual(len(found), 15)
        self.assertEqual((notes, meta["totalCount"]), ([], 15))

    def test_over_the_cap_splits_by_date_and_finds_everything(self):
        cases = self._cases(55)
        found, notes, meta = self._search(self._index(cases))
        self.assertEqual(sorted(c["caseId"] for c in found), sorted(c["caseId"] for c in cases))
        self.assertEqual(len(found), len({c["caseId"] for c in found}))  # no duplicates
        self.assertEqual(meta["totalCount"], 55)
        self.assertTrue(any("splitting at" in n for n in notes))
        dates = [c["filedDate"] for c in found]
        self.assertEqual(dates, sorted(dates, reverse=True))  # still newest first

    def test_split_respects_given_dates_and_limit(self):
        found, _, _ = self._search(self._index(self._cases(55)),
                                   filed_from="2024-01-11", filed_to="2024-02-09", limit=25)
        self.assertEqual(len(found), 25)
        self.assertTrue(all("2024-01-11" <= c["filedDate"][:10] <= "2024-02-09" for c in found))

    def test_one_day_over_the_cap_warns_and_returns_the_cap(self):
        found, notes, _ = self._search(self._index(self._cases(30, per_day=30)))
        self.assertEqual(len(found), 20)
        self.assertTrue(any("cannot be split further" in n for n in notes))


class CredentialsTests(unittest.TestCase):
    ROOT = "https://deep-api.unicourt.com"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "conf" / "unicourt" / "credentials.json"
        self.env = mock.patch.dict(os.environ, {"UNICOURT_CREDENTIALS_FILE": str(self.path)}, clear=False)
        self.env.start()
        for var in ("UNICOURT_TOKEN", "UNICOURT_WORKSPACE", "UNICOURT_CLIENT_ID",
                    "UNICOURT_CLIENT_SECRET", "UNICOURT_API_ROOT"):
            os.environ.pop(var, None)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def _entry(self, ws="wk1", token="tok-" + "x" * 30, client="client-1", token_id="WT1"):
        return {"api_root": self.ROOT, "workspace_id": ws, "token_id": token_id, "access_token": token,
                "client_id_sha256": credentials_mod.client_fingerprint(client), "created": "2026-10-01T00:00:00+00:00"}

    def _args(self, **kw):
        return SimpleNamespace(**{"token": None, "workspace": None, "verbose": False, **kw})

    def test_store_is_private_and_holds_no_secret(self):
        store = credentials_mod.TokenStore()
        store.save(self._entry())
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        text = self.path.read_text()
        self.assertNotIn("client-1", text)          # only a hash of the client id
        self.assertNotIn("secret", text.lower())
        self.assertEqual(store.find(self.ROOT)["workspace_id"], "wk1")
        self.assertIsNone(store.find(self.ROOT, client_id="someone-else"))

    def test_loose_permissions_are_tightened(self):
        store = credentials_mod.TokenStore(warn=lambda m: None)
        store.save(self._entry())
        os.chmod(self.path, 0o644)
        warnings = []
        credentials_mod.TokenStore(warn=warnings.append).find(self.ROOT)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertTrue(warnings and "Tightened permissions" in warnings[0])

    def test_several_workspaces_need_a_choice(self):
        store = credentials_mod.TokenStore()
        store.save(self._entry("wk1"))
        store.save(self._entry("wk2", token_id="WT2"))
        with self.assertRaises(SystemExit):
            store.find(self.ROOT)
        self.assertEqual(store.find(self.ROOT, "wk2")["token_id"], "WT2")
        store.remove(self.ROOT, "wk1")
        self.assertEqual(store.find(self.ROOT)["workspace_id"], "wk2")

    def test_first_run_creates_and_stores_a_token_then_reuses_it(self):
        os.environ.update(UNICOURT_WORKSPACE="wk1", UNICOURT_CLIENT_ID="client-1",
                          UNICOURT_CLIENT_SECRET="s3cret-value")
        made = []

        def fake_generate(api, client_id, secret, workspace):
            made.append((client_id, secret, workspace))
            return self._entry(workspace, client=client_id)

        with mock.patch.object(credentials_mod, "generate", side_effect=fake_generate), \
                redirect_stderr(io.StringIO()):
            first = cli._client(self._args())
            os.environ.pop("UNICOURT_WORKSPACE")          # later runs need neither the
            os.environ.pop("UNICOURT_CLIENT_SECRET")      # workspace nor the secret
            second = cli._client(self._args())
        self.assertEqual(made, [("client-1", "s3cret-value", "wk1")])  # created once
        self.assertEqual((first.token, second.token, second.workspace_id), (first.token, first.token, "wk1"))
        self.assertNotIn("s3cret-value", self.path.read_text())

    def test_explicit_token_wins_and_needs_a_workspace(self):
        with self.assertRaises(SystemExit):
            cli._client(self._args(token="explicit"))
        api = cli._client(self._args(token="explicit", workspace="wk9"))
        self.assertEqual((api.token, api.workspace_id), ("explicit", "wk9"))
        self.assertFalse(self.path.exists())

    def test_no_credentials_and_no_terminal_explains_what_to_set(self):
        with mock.patch.object(cli, "_ask_terminal", return_value=None), \
                mock.patch.object(cli.getpass, "getpass", side_effect=EOFError), \
                self.assertRaises(SystemExit) as ctx:
            cli._client(self._args())
        self.assertIn("UNICOURT_CLIENT_ID", str(ctx.exception))

    def test_workspace_is_looked_up_when_not_given(self):
        os.environ.update(UNICOURT_CLIENT_ID="client-1", UNICOURT_CLIENT_SECRET="s3cret")
        found = {"workspaceId": "deep01", "workspaceType": "DEEP", "workspaceName": "DEEP"}
        with mock.patch.object(credentials_mod, "discover_workspace", return_value=found) as discover, \
                mock.patch.object(credentials_mod, "generate",
                                  side_effect=lambda api, c, sec, ws: self._entry(ws, client=c)) as generate, \
                redirect_stderr(io.StringIO()) as err:
            api = cli._client(self._args())
        self.assertEqual(api.workspace_id, "deep01")
        self.assertEqual(generate.call_args[0][3], "deep01")
        self.assertEqual(discover.call_count, 1)
        self.assertIn("Using workspace deep01 (DEEP: DEEP)", err.getvalue())

    def test_rejected_token_is_replaced_once_and_stored(self):
        credentials_mod.TokenStore().save(self._entry(token="old-token-" + "x" * 20))
        os.environ.update(UNICOURT_CLIENT_ID="client-1", UNICOURT_CLIENT_SECRET="s3cret")
        with mock.patch.object(credentials_mod, "generate",
                               return_value=self._entry(token="new-token-" + "y" * 20, token_id="WT2")), \
                redirect_stderr(io.StringIO()):
            api = cli._client(self._args())
            sent = []

            def urlopen(req, timeout=None, context=None):
                sent.append(req.get_header("Authorization"))
                if len(sent) == 1:
                    raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {},
                                                 io.BytesIO(b'{"message": "Unauthorized"}'))
                resp = mock.MagicMock()
                resp.__enter__.return_value.read.return_value = b'{"ok": true}'
                return resp

            with mock.patch.object(client_mod.urllib.request, "urlopen", urlopen):
                self.assertEqual(api.get("caseSearch"), {"ok": True})
        self.assertEqual(sent, ["Bearer old-token-" + "x" * 20, "Bearer new-token-" + "y" * 20])
        self.assertEqual(credentials_mod.TokenStore().find(self.ROOT)["token_id"], "WT2")

    def test_token_command_never_prints_the_token(self):
        credentials_mod.TokenStore().save(self._entry(token="tok-SECRETPART-" + "z" * 20))
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            cli.cmd_token(SimpleNamespace(workspace=None, refresh=False, revoke=False, verbose=False))
        self.assertIn("WT1", out.getvalue())
        self.assertNotIn("SECRETPART", out.getvalue())

    def test_generate_and_revoke_send_the_documented_bodies(self):
        calls = []

        class Api:
            root = self.ROOT

            def request(self, method, path, auth=True, body=None, **kw):
                calls.append((method, path, auth, body))
                return {"workspaceId": "wk1", "workspaceTokenId": "WT7", "accessToken": "A" * 40}

        entry = credentials_mod.generate(Api(), "client-1", "s3cret", "wk1")
        credentials_mod.revoke(Api(), "client-1", "s3cret", entry)
        self.assertEqual(calls[0], ("POST", "/generateNewWorkspaceToken", False,
                                    {"clientId": "client-1", "clientSecret": "s3cret", "workspaceId": "wk1"}))
        self.assertEqual(calls[1], ("PUT", "/invalidateWorkspaceToken", False,
                                    {"clientId": "client-1", "clientSecret": "s3cret",
                                     "workspaceId": "wk1", "workspaceTokenId": "WT7"}))
        self.assertNotIn("clientSecret", json.dumps(entry))

    def test_ten_token_limit_explains_what_to_do(self):
        class Api:
            root = self.ROOT

            def request(self, *a, **kw):
                raise client_mod.UniCourtError(403, "UN203", "LIMIT_REACHED", "max 10")

        with self.assertRaises(SystemExit) as ctx:
            credentials_mod.generate(Api(), "c", "s", "wk1")
        self.assertIn("maximum of 10 tokens", str(ctx.exception))

    class _DiscoveryApi:
        """Fake UniCourt for discover_workspace: records calls, serves canned answers."""

        def __init__(self, calls, token_response, workspaces=(), fail_list=False):
            self.calls, self.token_response = calls, token_response
            self.workspaces, self.fail_list = list(workspaces), fail_list

        def request(self, method, path, auth=True, body=None, **kw):
            self.calls.append((method, path, body))
            return self.token_response if path == "/generateNewToken" else {"object": "Success"}

        def paginate(self, path, array_key, params=None, **kw):
            self.calls.append(("GET", path, None))
            if self.fail_list:
                raise client_mod.UniCourtError(500, "UN500")
            return iter(self.workspaces)

    def _discover(self, token_response, workspaces=(), fail_list=False):
        calls = []
        make_api = lambda token: self._DiscoveryApi(calls, token_response, workspaces, fail_list)  # noqa: E731
        try:
            return credentials_mod.discover_workspace(make_api, "client-1", "s3cret"), calls
        except BaseException as exc:
            exc.calls = calls
            raise

    def test_discover_uses_deep_workspace_from_the_token_response(self):
        deep = {"workspaceId": "7zlq3xbp", "workspaceType": "DEEP", "workspaceName": "DEEP"}
        found, calls = self._discover({"accessToken": "acct", "tokenId": "T1", "deepWorkspace": deep})
        self.assertEqual(found["workspaceId"], "7zlq3xbp")
        self.assertEqual([c[1] for c in calls], ["/generateNewToken", "/invalidateToken"])  # no listing needed
        self.assertEqual(calls[-1][2], {"clientId": "client-1", "clientSecret": "s3cret", "tokenId": "T1"})

    def test_discover_lists_workspaces_and_prefers_deep(self):
        workspaces = [{"workspaceId": "u1", "workspaceType": "USER"},
                      {"workspaceId": "d1", "workspaceType": "DEEP"},
                      {"workspaceId": "s1", "workspaceType": "SHARED"}]
        found, calls = self._discover({"accessToken": "acct", "tokenId": "T1"}, workspaces)
        self.assertEqual(found["workspaceId"], "d1")
        self.assertEqual([c[1] for c in calls], ["/generateNewToken", "/workspaces", "/invalidateToken"])

    def test_discover_single_workspace_without_deep(self):
        found, _ = self._discover({"accessToken": "a", "tokenId": "T1"}, [{"workspaceId": "only", "workspaceType": "SHARED"}])
        self.assertEqual(found["workspaceId"], "only")

    def test_discover_ambiguous_lists_choices_and_still_revokes(self):
        workspaces = [{"workspaceId": "s1", "workspaceType": "SHARED", "workspaceName": "Team A"},
                      {"workspaceId": "s2", "workspaceType": "SHARED", "workspaceName": "Team B"}]
        with self.assertRaises(SystemExit) as ctx:
            self._discover({"accessToken": "a", "tokenId": "T1"}, workspaces)
        self.assertIn("s1", str(ctx.exception.code))
        self.assertIn("Team B", str(ctx.exception.code))
        self.assertEqual(ctx.exception.calls[-1][1], "/invalidateToken")

    def test_discover_revokes_the_account_token_even_when_listing_fails(self):
        with self.assertRaises(client_mod.UniCourtError) as ctx:
            self._discover({"accessToken": "a", "tokenId": "T1"}, fail_list=True)
        self.assertEqual(ctx.exception.calls[-1][1], "/invalidateToken")

    def test_revoke_and_refresh(self):
        store = credentials_mod.TokenStore()
        store.save(self._entry())
        os.environ.update(UNICOURT_CLIENT_ID="client-1", UNICOURT_CLIENT_SECRET="s3cret")
        revoked = []
        with mock.patch.object(credentials_mod, "revoke", side_effect=lambda api, c, s, e: revoked.append(e["token_id"])), \
                mock.patch.object(credentials_mod, "generate", return_value=self._entry(token_id="WT2")), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            cli.cmd_token(SimpleNamespace(workspace=None, refresh=True, revoke=False, verbose=False))
            self.assertEqual((revoked, store.find(self.ROOT)["token_id"]), (["WT1"], "WT2"))
            cli.cmd_token(SimpleNamespace(workspace=None, refresh=False, revoke=True, verbose=False))
        self.assertEqual(revoked, ["WT1", "WT2"])
        self.assertIsNone(store.find(self.ROOT))


if __name__ == "__main__":
    unittest.main()
