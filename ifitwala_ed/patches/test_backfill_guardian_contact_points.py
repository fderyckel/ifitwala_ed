from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillGuardianContactPoints(TestCase):
    def test_execute_backfills_guardians_with_single_student_school(self):
        sync_calls: list[dict] = []
        contact_privacy = types.ModuleType("ifitwala_ed.contacts.contact_privacy")

        def sync_guardian_contact_points(guardian_doc, **kwargs):
            sync_calls.append({"guardian": guardian_doc, **kwargs})
            return ["CCP-EMAIL", "CCP-PHONE"]

        contact_privacy.sync_guardian_contact_points = sync_guardian_contact_points

        with stubbed_frappe(extra_modules={"ifitwala_ed.contacts.contact_privacy": contact_privacy}) as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {
                "Communication Contact Point",
                "Contact Access Log",
                "Guardian",
                "Student",
                "Student Guardian",
            }

            def get_all(doctype, **kwargs):
                if doctype == "Student Guardian":
                    return [
                        {"parent": "STU-1", "guardian": "GRD-1"},
                        {"parent": "STU-2", "guardian": "GRD-1"},
                    ]
                if doctype == "Student":
                    return [
                        {"name": "STU-1", "anchor_school": "SCHOOL-1"},
                        {"name": "STU-2", "anchor_school": "SCHOOL-1"},
                    ]
                if doctype == "Guardian":
                    return [
                        {
                            "name": "GRD-1",
                            "organization": "ORG-1",
                            "guardian_email": "guardian@example.com",
                            "guardian_mobile_phone": "+66812345678",
                        }
                    ]
                return []

            frappe.get_all = get_all
            module = import_fresh("ifitwala_ed.patches.backfill_guardian_contact_points")

            module.execute()

        self.assertEqual(len(sync_calls), 1)
        self.assertEqual(sync_calls[0]["guardian"]["name"], "GRD-1")
        self.assertEqual(sync_calls[0]["school"], "SCHOOL-1")
        self.assertEqual(sync_calls[0]["purpose"], "school_communication")
        self.assertEqual(sync_calls[0]["workflow"], "guardian_contact_point_backfill")

    def test_backfill_processes_guardians_with_multiple_student_schools(self):
        sync_calls: list[dict] = []

        with stubbed_frappe() as frappe:
            frappe.get_all = lambda doctype, **kwargs: {
                "Student Guardian": [
                    {"parent": "STU-1", "guardian": "GRD-1"},
                    {"parent": "STU-2", "guardian": "GRD-1"},
                ],
                "Student": [
                    {"name": "STU-1", "anchor_school": "SCHOOL-1"},
                    {"name": "STU-2", "anchor_school": "SCHOOL-2"},
                ],
                "Guardian": [
                    {
                        "name": "GRD-1",
                        "organization": "ORG-1",
                        "guardian_email": "guardian@example.com",
                        "guardian_mobile_phone": "+66812345678",
                    }
                ],
            }.get(doctype, [])
            module = import_fresh("ifitwala_ed.patches.backfill_guardian_contact_points")

            stats = module.backfill_guardian_contact_points(
                frappe,
                sync_function=lambda guardian_doc, **kwargs: sync_calls.append({"guardian": guardian_doc, **kwargs})
                or ["CCP-EMAIL", "CCP-PHONE"],
            )

        self.assertEqual(stats["guardians_eligible"], 1)
        self.assertEqual(stats["guardian_school_links"], 2)
        self.assertEqual(stats["guardians_processed"], 1)
        self.assertEqual(stats["school_contexts_processed"], 2)
        self.assertEqual(stats["contact_points_synced"], 4)
        self.assertEqual([call["school"] for call in sync_calls], ["SCHOOL-1", "SCHOOL-2"])

    def test_execute_returns_when_required_tables_are_missing(self):
        contact_privacy = types.ModuleType("ifitwala_ed.contacts.contact_privacy")
        contact_privacy.sync_guardian_contact_points = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("sync should not run when required tables are missing")
        )

        with stubbed_frappe(extra_modules={"ifitwala_ed.contacts.contact_privacy": contact_privacy}) as frappe:
            frappe.db.table_exists = lambda doctype: doctype != "Communication Contact Point"
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when required tables are missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_guardian_contact_points")

            module.execute()

    def test_backfill_logs_failures_without_raw_contact_values(self):
        log_entries: list[tuple[str, str]] = []

        with stubbed_frappe() as frappe:
            frappe.get_all = lambda doctype, **kwargs: {
                "Student Guardian": [{"parent": "STU-1", "guardian": "GRD-1"}],
                "Student": [{"name": "STU-1", "anchor_school": "SCHOOL-1"}],
                "Guardian": [
                    {
                        "name": "GRD-1",
                        "organization": "ORG-1",
                        "guardian_email": "guardian@example.com",
                        "guardian_mobile_phone": "+66812345678",
                    }
                ],
            }.get(doctype, [])
            frappe.get_traceback = lambda: "unit traceback"
            frappe.log_error = lambda message, title: log_entries.append((message, title))
            module = import_fresh("ifitwala_ed.patches.backfill_guardian_contact_points")

            stats = module.backfill_guardian_contact_points(
                frappe,
                sync_function=lambda *args, **kwargs: (_ for _ in ()).throw(Exception("sync failed")),
            )

        self.assertEqual(stats["failures"], 1)
        self.assertEqual(log_entries[0][1], "Guardian Contact Point Backfill Failed")
        self.assertIn("guardian=GRD-1", log_entries[0][0])
        self.assertIn("school=SCHOOL-1", log_entries[0][0])
        self.assertNotIn("guardian@example.com", log_entries[0][0])
        self.assertNotIn("+66812345678", log_entries[0][0])
