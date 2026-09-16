"""Offline tests. These run entirely from saved fixtures - no API requests."""

from __future__ import annotations

import doctest
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mdl_complaints import core, courts, members as members_mod, titles  # noqa: E402
from mdl_complaints.core import (  # noqa: E402
    collect_complaints,
    is_complaint,
    normalize_case_number,
    normalize_mdl_number,
    parse_complaint_description,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_tests(loader, tests, ignore):
    """Run the module doctests as part of the suite."""
    tests.addTests(doctest.DocTestSuite(core))
    tests.addTests(doctest.DocTestSuite(courts))
    tests.addTests(doctest.DocTestSuite(titles))
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

    def get(self, url, params=None):
        if "/search/" in url:
            self.calls.append(f"search:{(params or {}).get('court')}")
            return {"results": self.search_results}
        self.calls.append(f"get:{url}")
        return {"results": []}

    #: Overridden by the title tests; empty means "nothing resolves".
    search_results: list = []


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
            collect_complaints(
                self.client, "3140",
                entry_prefix="MOTION TO TRANSFER", with_titles=False,
            )
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

    def test_motions_only_lookup_costs_two_requests(self):
        client = FakeClient()
        collect_complaints(
            client, "3140", entry_prefix="MOTION TO TRANSFER",
            max_pages=1, with_titles=False,
        )
        self.assertEqual(
            client.calls, ["dockets:MDL No. 3140", "entries:date_filed"]
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
            FakeClient(), "3140", entry_prefix="MOTION TO TRANSFER",
            available_only=True, with_titles=False,
        )
        self.assertTrue(all(c.is_available for c in available))
        self.assertLessEqual(len(available), len(self.complaints))

    def test_unknown_mdl_raises(self):
        with self.assertRaises(core.DocketNotFound):
            collect_complaints(FakeClient(), "9999", with_titles=False)


class TestFullDocketScope(unittest.TestCase):
    """With no entry prefix the tool collects complaints from every entry."""

    def test_scanning_all_entries_is_a_superset_of_the_motions(self):
        _, _, motions, _ = collect_complaints(
            FakeClient(), "3140",
            entry_prefix="MOTION TO TRANSFER", with_titles=False,
        )
        _, entries, everything, _ = collect_complaints(
            FakeClient(), "3140", with_titles=False,
        )
        motion_ids = {c.document_id for c in motions}
        all_ids = {c.document_id for c in everything}
        self.assertTrue(motion_ids.issubset(all_ids))
        self.assertEqual(len(entries), 20)  # every entry on the fixture page


class TestCourtlistenerIds(unittest.TestCase):
    def test_both_conventions_map_to_the_same_court_id(self):
        self.assertEqual(courts.courtlistener_id("CAN"), "cand")
        self.assertEqual(courts.courtlistener_id("NDCA"), "cand")
        self.assertEqual(courts.courtlistener_id("INS"), "insd")
        self.assertEqual(courts.courtlistener_id("NV"), "nvd")

    def test_unknown_code_has_no_id(self):
        self.assertEqual(courts.courtlistener_id("QQQ"), "")


class TestTitleResolution(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        _, _, self.complaints, _ = collect_complaints(
            self.client, "3140",
            entry_prefix="MOTION TO TRANSFER", with_titles=False,
        )

    def test_groups_queries_by_court(self):
        client = FakeClient()
        titles.resolve_titles(client, self.complaints)
        courts_queried = [c for c in client.calls if c.startswith("search:")]
        # 28 complaints across 8 districts -> one query per district, not per case.
        self.assertEqual(len(courts_queried), 8)
        self.assertIn("search:cand", courts_queried)

    def test_ignores_hits_from_the_wrong_court(self):
        client = FakeClient()
        # Same docket number, different district: must not be used as a title.
        client.search_results = [
            {"court_id": "njd", "docketNumber": "3:24-cv-06875",
             "caseName": "WRONG COURT CASE"},
        ]
        resolved = titles.resolve_titles(client, self.complaints)
        self.assertEqual(resolved, {})

    def test_matches_on_court_and_normalized_number(self):
        client = FakeClient()
        client.search_results = [
            {"court_id": "cand", "docketNumber": "3:24-cv-06875",
             "caseName": "Schmidt v. Pfizer Inc."},
        ]
        resolved = titles.resolve_titles(client, self.complaints)
        self.assertEqual(
            resolved[("cand", "3:24-cv-06875")], "Schmidt v. Pfizer Inc."
        )

    def test_respects_a_request_budget(self):
        client = FakeClient()
        titles.resolve_titles(client, self.complaints, max_requests=2)
        self.assertEqual(
            len([c for c in client.calls if c.startswith("search:")]), 2
        )


class TestPdfTitleFallback(unittest.TestCase):
    """The PDF fallback is free (the OCR text is already in the payload)."""

    def test_extracts_plaintiff_from_signature_block(self):
        self.assertEqual(
            titles.plaintiff_from_complaint_text(
                "ONDERLAW, LLC\nAttorneys for Plaintiff Jamie Grubensky\n"
            ),
            "Jamie Grubensky",
        )

    def test_returns_blank_rather_than_guessing(self):
        self.assertEqual(titles.plaintiff_from_complaint_text("nothing here"), "")
        self.assertEqual(titles.plaintiff_from_complaint_text(""), "")

    def test_ignores_text_far_past_the_caption(self):
        padding = "x" * 30_000
        self.assertEqual(
            titles.plaintiff_from_complaint_text(
                padding + "Attorneys for Plaintiff Late Match"
            ),
            "",
        )

    def test_docket_title_wins_over_the_pdf(self):
        client = FakeClient()
        client.search_results = [
            {"court_id": "cand", "docketNumber": "3:24-cv-06875",
             "caseName": "Schmidt v. Pfizer Inc."},
        ]
        _, _, complaints, _ = collect_complaints(
            client, "3140", entry_prefix="MOTION TO TRANSFER",
        )
        schmidt = next(c for c in complaints if c.case_number == "3:24-6875")
        self.assertEqual(schmidt.title, "Schmidt v. Pfizer Inc.")
        self.assertEqual(schmidt.title_source, "docket")

    def test_pdf_fallback_is_labelled_as_such(self):
        client = FakeClient()
        _, _, complaints, _ = collect_complaints(
            client, "3140", entry_prefix="MOTION TO TRANSFER",
        )
        # No search results, so anything with a title came from a PDF.
        for complaint in complaints:
            if complaint.title:
                self.assertEqual(complaint.title_source, "complaint-pdf")

    def test_fallback_can_be_disabled(self):
        _, _, complaints, _ = collect_complaints(
            FakeClient(), "3140", entry_prefix="MOTION TO TRANSFER",
            pdf_fallback=False,
        )
        self.assertTrue(all(not c.title for c in complaints))


class TestMemberExtraction(unittest.TestCase):
    """Member cases are parsed from entry text, so extraction costs no requests."""

    def _entry(self, number, description):
        return {
            "entry_number": number,
            "date_filed": "2025-01-01",
            "description": description,
        }

    def test_parses_spelled_out_court_blocks(self):
        found = members_mod.extract_members([
            self._entry(1, "XYZ CASES ENTERED -- 2 related action(s) -- "
                           "Florida Northern District Court "
                           "(3:25-cv-00108,3:25-cv-00144)"),
        ])
        self.assertEqual(
            [(m.court_id, m.case_number) for m in found],
            [("flnd", "3:25-cv-00108"), ("flnd", "3:25-cv-00144")],
        )
        self.assertTrue(all(m.source == "cases-entered" for m in found))

    def test_parses_slash_style_references(self):
        found = members_mod.extract_members([
            self._entry(9, "CONDITIONAL TRANSFER ORDER FINALIZED (CTO-3) "
                           "re: pldg. ( 287 in MDL No. 3140, 1 in "
                           "MN/0:26-cv-00123)"),
        ])
        self.assertEqual(found[0].court_id, "mnd")
        self.assertEqual(found[0].case_number, "0:26-cv-00123")
        self.assertEqual(found[0].source, "conditional-transfer-order")

    def test_deduplicates_and_keeps_the_most_authoritative_source(self):
        # The same case appears first as a tag-along, later on a transfer order.
        found = members_mod.extract_members([
            self._entry(5, "NOTICE OF POTENTIAL TAG-ALONG -- "
                           "Minnesota District Court (0:26-cv-00123)"),
            self._entry(9, "CONDITIONAL TRANSFER ORDER FILED TODAY -- "
                           "Minnesota District Court (0:26-cv-00123)"),
        ])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].source, "conditional-transfer-order")

    def test_ignores_unmappable_courts(self):
        found = members_mod.extract_members([
            self._entry(1, "Atlantis Eastern District Court (1:25-cv-00001)"),
        ])
        self.assertEqual(found, [])

    def test_classifies_entry_kinds(self):
        classify = members_mod.classify_entry
        self.assertEqual(classify("MOTION TO TRANSFER (INITIAL)"), "motion-to-transfer")
        self.assertEqual(
            classify("CONDITIONAL TRANSFER ORDER FILED TODAY (CTO-1)"),
            "conditional-transfer-order",
        )
        self.assertEqual(classify("XYZ CASES ENTERED -- 3 actions"), "cases-entered")
        self.assertEqual(classify("NOTICE OF POTENTIAL TAG-ALONG"), "tag-along")
        self.assertEqual(classify("NOTICE OF APPEARANCE"), "other")


class TestMemberTitleResolution(unittest.TestCase):
    def setUp(self):
        self.members = members_mod.extract_members([{
            "entry_number": 1, "date_filed": "2025-01-01",
            "description": "XYZ CASES ENTERED -- Florida Northern District "
                           "Court (3:25-cv-00108,3:25-cv-00144)",
        }])

    def test_fills_titles_from_search_hits(self):
        client = FakeClient()
        client.search_results = [
            {"court_id": "flnd", "docketNumber": "3:25-cv-00108",
             "caseName": "SUTTON v. PFIZER INC"},
        ]
        spent = members_mod.resolve_member_titles(client, self.members)
        self.assertEqual(spent, 1)
        self.assertEqual(self.members[0].title, "SUTTON v. PFIZER INC")
        self.assertEqual(self.members[0].title_source, "docket")
        self.assertEqual(self.members[1].title, "")  # no hit, left blank

    def test_budget_caps_spending(self):
        many = members_mod.extract_members([{
            "entry_number": 1, "date_filed": "2025-01-01",
            "description": "XYZ CASES ENTERED -- Florida Northern District Court ("
                           + ",".join(f"3:25-cv-{n:05d}" for n in range(1, 60)) + ")",
        }])
        client = FakeClient()
        spent = members_mod.resolve_member_titles(client, many, max_requests=2)
        self.assertEqual(spent, 2)

    def test_wrong_court_hits_are_ignored(self):
        client = FakeClient()
        client.search_results = [
            {"court_id": "njd", "docketNumber": "3:25-cv-00108",
             "caseName": "SOME OTHER CASE"},
        ]
        members_mod.resolve_member_titles(client, self.members)
        self.assertTrue(all(not m.title for m in self.members))


class TestCaseNumberNormalization(unittest.TestCase):
    def test_jpml_shorthand_matches_full_form(self):
        self.assertEqual(
            normalize_case_number("3:24-6875"), normalize_case_number("3:24-cv-06875")
        )

    def test_leaves_unparseable_input_alone(self):
        self.assertEqual(normalize_case_number("not-a-case"), "not-a-case")


if __name__ == "__main__":
    unittest.main(verbosity=2)
