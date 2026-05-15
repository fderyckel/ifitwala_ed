from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillStudentReferralCaseLinks(TestCase):
    def test_execute_repairs_unambiguous_referral_case_mirrors_only(self):
        updates: list[tuple[str, str, dict[str, str], bool]] = []

        def get_all(doctype: str, **kwargs):
            if doctype == "Referral Case":
                return [
                    {"name": "RC-0001", "referral": "SRF-0001"},
                    {"name": "RC-0002", "referral": "SRF-0002"},
                    {"name": "RC-0003", "referral": "SRF-0003"},
                    {"name": "RC-0004", "referral": "SRF-0003"},
                ]
            if doctype == "Student Referral":
                self.assertEqual(
                    kwargs["filters"],
                    {"name": ["in", ["SRF-0001", "SRF-0002", "SRF-0003"]]},
                )
                return [
                    {"name": "SRF-0001", "referral_case": None},
                    {"name": "SRF-0002", "referral_case": "RC-STALE"},
                    {"name": "SRF-0003", "referral_case": None},
                ]
            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Student Referral", "Referral Case"}
            frappe.get_all = get_all
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: updates.append(
                (doctype, name, values, update_modified)
            )
            module = import_fresh("ifitwala_ed.patches.backfill_student_referral_case_links")

            module.execute()

        self.assertEqual(
            updates,
            [
                ("Student Referral", "SRF-0001", {"referral_case": "RC-0001"}, False),
                ("Student Referral", "SRF-0002", {"referral_case": "RC-0002"}, False),
            ],
        )

    def test_execute_returns_when_required_tables_are_missing(self):
        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when required tables are missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_student_referral_case_links")

            module.execute()
