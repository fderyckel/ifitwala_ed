from __future__ import annotations

import types
from types import SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillInquiryFirstContactDueDates(TestCase):
    def test_execute_backfills_missing_due_dates_using_submitted_at_or_creation_fallback(self):
        admission_utils = types.ModuleType("ifitwala_ed.admission.admission_utils")

        def set_inquiry_deadlines(doc):
            if not getattr(doc, "first_contact_due_on", None):
                doc.first_contact_due_on = f"due:{getattr(doc, 'submitted_at', None)}"

        admission_utils.set_inquiry_deadlines = set_inquiry_deadlines

        inquiry_docs = {
            "INQ-SUBMITTED": SimpleNamespace(
                name="INQ-SUBMITTED",
                submitted_at="2026-02-01",
                creation="2026-02-01",
                first_contact_due_on=None,
            ),
            "INQ-CREATION": SimpleNamespace(
                name="INQ-CREATION",
                submitted_at=None,
                creation="2026-02-05",
                first_contact_due_on=None,
            ),
            "INQ-ALREADY": SimpleNamespace(
                name="INQ-ALREADY",
                submitted_at="2026-02-07",
                creation="2026-02-07",
                first_contact_due_on="due:2026-02-07",
            ),
        }
        updates: list[tuple[str, str, str, str, bool]] = []

        with stubbed_frappe(extra_modules={"ifitwala_ed.admission.admission_utils": admission_utils}) as frappe:
            frappe.db.table_exists = lambda doctype: doctype == "Inquiry"
            frappe.get_all = lambda doctype, filters=None, fields=None, limit=None: [
                {"name": "INQ-SUBMITTED", "submitted_at": "2026-02-01", "creation": "2026-02-01"},
                {"name": "INQ-CREATION", "submitted_at": None, "creation": "2026-02-05"},
                {"name": "INQ-ALREADY", "submitted_at": "2026-02-07", "creation": "2026-02-07"},
            ]
            frappe.get_doc = lambda doctype, name: inquiry_docs[name]
            frappe.db.set_value = lambda doctype, name, fieldname, value, update_modified=False: updates.append(
                (doctype, name, fieldname, value, update_modified)
            )
            module = import_fresh("ifitwala_ed.patches.backfill_inquiry_first_contact_due_dates")

            module.execute()

        self.assertEqual(
            updates,
            [
                ("Inquiry", "INQ-SUBMITTED", "first_contact_due_on", "due:2026-02-01", False),
                ("Inquiry", "INQ-CREATION", "first_contact_due_on", "due:2026-02-05", False),
            ],
        )

    def test_execute_returns_when_inquiry_table_is_missing(self):
        admission_utils = types.ModuleType("ifitwala_ed.admission.admission_utils")
        admission_utils.set_inquiry_deadlines = lambda doc: None

        with stubbed_frappe(extra_modules={"ifitwala_ed.admission.admission_utils": admission_utils}) as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when Inquiry table is missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_inquiry_first_contact_due_dates")

            module.execute()
