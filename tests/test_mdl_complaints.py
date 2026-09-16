"""Offline tests. These run entirely from saved fixtures - no API requests."""

from __future__ import annotations

import doctest
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mdl_complaints import core, courts  # noqa: E402
from mdl_complaints.core import (  # noqa: E402
    collect_complaints,
    is_complaint,
    normalize_mdl_number,
    parse_complaint_description,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_tests(loader, tests, ignore):
    """Run the module doctests as part of the suite."""
    tests.addTests(doctest.DocTestSuite(core))
    tests.addTests(doctest.DocTestSuite(courts))
    return tests


class FakeClient:
    """Stands in for CourtListenerClient, serving fixtures and counting calls."""

    def __init__(self) -> None:
        self.docket = json.loads((FIXTURES / "docket_mdl3140.json").read_text())
        self.entries = json.loads((FIXTURES / "entries_asc_mdl3140.json").read_text())
        self.calls: list[str] = []

    def dockets(self, **params):
        self.calls.append(f"dockets:{params.get('docket_number')}")
        if params.get("docket_number") != "MDL No. 3140":
            return {"results": []}
        return self.docket

    def docket_entries(self, **params):
        self.calls.append(f"entries:{params.get('order_by')}")
        return self.entries

    def get(self, url, params=None):  # pragma: no cover - pagination not hit here
        self.calls.append(f"get:{url}")
        return {"results": []}


class TestNormalizeMdlNumber(unittest.TestCase):
    def test_accepts_common_user_input(self):
        for raw in ("3140", "md 3140", "MDL 3140", "MDL-3140", " mdl no. 3140 ",
                    "MDL No. 3140"):
            with self.subTest(raw=raw):
                self.assertEqual(normalize_mdl_number(raw), "MDL No. 3140")

    def test_rejects_input_without_a_number(self):
        with self.assertRaises(ValueError):
            normalize_mdl_number("no digits here")


class TestParsing(unittest.TestCase):
    def test_parses_court_and_case_number(self):
        self.assertEqual(
            parse_complaint_description("Complaint CAN 3:24-6875"), ("CAN", "3:24-6875")
        )
        self.assertEqual(
            parse_complaint_description("Complaint MA 3:24-30145"), ("MA", "3:24-30145")
        )

    def test_bare_complaint_has_no_metadata(self):
        self.assertEqual(parse_complaint_description("Complaint"), ("", ""))

    def test_is_complaint_requires_attachment_type(self):
        # document_type 1 is the motion itself, never a complaint.
        self.assertFalse(is_complaint({"document_type": 1, "description": "Complaint"}))
        self.assertTrue(is_complaint({"document_type": 2, "description": "Complaint X"}))
        self.assertFalse(is_complaint({"document_type": 2, "description": "Brief"}))
        self.assertFalse(
            is_complaint({"document_type": 2, "description": "Schedule of Actions"})
        )


class TestCourtCodes(unittest.TestCase):
    def test_expands_known_codes(self):
        self.assertEqual(courts.expand_court_code("CAN"), "California Northern")
        self.assertEqual(courts.expand_court_code("MOW"), "Missouri Western")
        self.assertEqual(courts.expand_court_code("INS"), "Indiana Southern")
        self.assertEqual(courts.expand_court_code("NV"), "Nevada")
        self.assertEqual(courts.expand_court_code("DC"), "District of Columbia")

    def test_unknown_code_passes_through(self):
        self.assertEqual(courts.expand_court_code("QQQ"), "QQQ")


class TestCollectComplaints(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.docket, self.entries, self.complaints, self.truncated = (
            collect_complaints(self.client, "3140")
        )

    def test_finds_complaints_on_initial_and_subsequent_motions(self):
        # Entry 1 (INITIAL MOTION) says "22 Action(s)"; entry 12 (SUBSEQUENT)
        # says "6 Action(s)". Both are motions to transfer, so both count.
        by_entry = {}
        for complaint in self.complaints:
            by_entry.setdefault(complaint.entry_number, []).append(complaint)
        self.assertEqual(len(by_entry[1]), 22)
        self.assertEqual(len(by_entry[12]), 6)
        self.assertEqual(len(self.complaints), 28)

    def test_matches_corrected_motions_that_carry_no_complaints(self):
        # Entries 2-4 are "MOTION TO TRANSFER (CORRECTED)" with no attachments.
        matched = {e.get("entry_number") for e in self.entries}
        self.assertEqual(matched, {1, 2, 3, 4, 12})

    def test_uses_only_two_requests(self):
        self.assertEqual(
            self.client.calls, ["dockets:MDL No. 3140", "entries:date_filed"]
        )

    def test_excludes_non_complaint_attachments(self):
        descriptions = [c.description for c in self.complaints]
        self.assertNotIn("Brief", descriptions)
        self.assertNotIn("Schedule of Actions", descriptions)
        self.assertNotIn("Proof of Service", descriptions)

    def test_complaint_fields_are_populated(self):
        first = self.complaints[0]
        self.assertEqual(first.court_code, "CAN")
        self.assertEqual(first.court_name, "California Northern")
        self.assertEqual(first.case_number, "3:24-6875")
        self.assertEqual(first.entry_number, 1)
        self.assertTrue(first.pdf_url.startswith("https://storage.courtlistener.com/"))
        self.assertTrue(first.courtlistener_url.startswith("https://www.courtlistener.com/"))

    def test_every_complaint_has_a_court_and_case_number(self):
        for complaint in self.complaints:
            with self.subTest(desc=complaint.description):
                self.assertTrue(complaint.court_code)
                self.assertTrue(complaint.case_number)

    def test_handles_both_court_code_conventions(self):
        names = {c.court_code: c.court_name for c in self.complaints}
        self.assertEqual(names["CAN"], "California Northern")   # JPML style
        self.assertEqual(names["NDCA"], "California Northern")  # reporter style

    def test_normalizes_case_numbers_across_conventions(self):
        by_desc = {c.description: c for c in self.complaints}
        self.assertEqual(
            by_desc["Complaint CAN 3:24-6875"].case_number_normalized, "3:24-cv-06875"
        )
        self.assertEqual(
            by_desc["Complaint NDCA 3:24-cv-08746"].case_number_normalized,
            "3:24-cv-08746",
        )

    def test_available_only_filters(self):
        _, _, available, _ = collect_complaints(
            FakeClient(), "3140", available_only=True
        )
        self.assertTrue(all(c.is_available for c in available))
        self.assertLessEqual(len(available), len(self.complaints))

    def test_unknown_mdl_raises(self):
        with self.assertRaises(core.DocketNotFound):
            collect_complaints(FakeClient(), "9999")


if __name__ == "__main__":
    unittest.main(verbosity=2)
