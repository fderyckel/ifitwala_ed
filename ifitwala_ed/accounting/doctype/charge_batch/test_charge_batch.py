from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.accounting.charges import charge_generation, source_context
from ifitwala_ed.accounting.charges.charge_generation import generate_draft_invoices_for_charge_batch
from ifitwala_ed.accounting.test_support import AccountingTestMixin


class TestChargeBatch(AccountingTestMixin, FrappeTestCase):
    def test_student_group_context_creates_prefilled_charge_batch(self):
        inserted_payload = {}

        class FakeChargeBatch:
            def __init__(self, payload):
                self.name = "CBAT-TEST"
                self.students = [SimpleNamespace(status="Ready") for row in payload.get("students", [])]
                self.payload = payload

            def insert(self):
                inserted_payload.update(self.payload)

        group = SimpleNamespace(
            name="SG-ACTIVITY",
            school="IIS",
            program_offering=None,
            student_group_name="Weekend Robotics",
            student_group_abbreviation="ROB",
            check_permission=lambda ptype: None,
        )

        def fake_get_doc(doctype, name=None):
            if doctype == "Student Group" and name == "SG-ACTIVITY":
                return group
            if isinstance(doctype, dict) and doctype.get("doctype") == "Charge Batch":
                return FakeChargeBatch(doctype)
            raise AssertionError(f"Unexpected get_doc call: {doctype} {name}")

        with (
            patch("ifitwala_ed.accounting.charges.source_context.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.accounting.charges.source_context.frappe.get_doc", side_effect=fake_get_doc),
            patch("ifitwala_ed.accounting.charges.source_context.get_school_organization", return_value="IEO"),
            patch(
                "ifitwala_ed.accounting.charges.source_context.frappe.get_all",
                return_value=[
                    {"student": "STU-001", "active": 1},
                    {"student": "STU-002", "active": 1},
                    {"student": "STU-002", "active": 1},
                    {"student": "STU-003", "active": 0},
                ],
            ),
        ):
            result = source_context.create_charge_batch_from_context(
                source_doctype="Student Group",
                source_name="SG-ACTIVITY",
                billable_offering="BO-001",
                posting_date="2026-05-30",
                due_date="2026-06-05",
                default_rate=150,
            )

        self.assertEqual(result["charge_batch"], "CBAT-TEST")
        self.assertEqual(inserted_payload["organization"], "IEO")
        self.assertEqual(inserted_payload["source_doctype"], "Student Group")
        self.assertEqual(inserted_payload["source_name"], "SG-ACTIVITY")
        self.assertEqual(inserted_payload["billable_offering"], "BO-001")
        self.assertEqual([row["student"] for row in inserted_payload["students"]], ["STU-001", "STU-002"])

    def test_generates_draft_invoices_grouped_by_account_holder(self):
        org = self.make_organization("Charge Batch")
        income = self.make_account(org.name, "Income", prefix="Trip Income")
        school = self.make_school(org.name)
        account_holder_a = self.make_account_holder(org.name, prefix="Payer A")
        account_holder_b = self.make_account_holder(org.name, prefix="Payer B")
        student_a = self.make_student(org.name, account_holder_a.name, school=school.name, prefix="Sibling A")
        student_b = self.make_student(org.name, account_holder_a.name, school=school.name, prefix="Sibling B")
        student_c = self.make_student(org.name, account_holder_b.name, school=school.name, prefix="Sibling C")
        offering = self.make_billable_offering(
            org.name,
            income.name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
            offering_name="Field Trip",
        )
        self.make_fiscal_year(org.name, year=2026, year_start_date="2026-01-01", year_end_date="2026-12-31")

        batch = frappe.get_doc(
            {
                "doctype": "Charge Batch",
                "organization": org.name,
                "batch_title": f"Field Trip {frappe.generate_hash(length=6)}",
                "source_type": "Trip",
                "billable_offering": offering.name,
                "posting_date": "2026-05-30",
                "due_date": "2026-06-05",
                "default_qty": 1,
                "default_rate": 80,
                "description": "Grade field trip",
                "students": [
                    {"student": student_a.name},
                    {"student": student_b.name},
                    {"student": student_c.name},
                ],
            }
        )
        batch.insert()

        result = generate_draft_invoices_for_charge_batch(batch.name)

        self.assertEqual(result["invoice_count"], 2)
        invoices = {}
        for name in result["invoice_names"]:
            invoice = frappe.get_doc("Sales Invoice", name)
            invoices[invoice.account_holder] = invoice

        self.assertEqual(len(invoices[account_holder_a.name].items), 2)
        self.assertEqual(len(invoices[account_holder_b.name].items), 1)
        self.assertEqual(
            {row.student for row in invoices[account_holder_a.name].items},
            {student_a.name, student_b.name},
        )
        self.assertEqual({row.student for row in invoices[account_holder_b.name].items}, {student_c.name})

        charges = frappe.get_all(
            "Billable Charge",
            filters={"charge_batch": batch.name},
            fields=["student", "account_holder", "status", "sales_invoice"],
            limit=10,
        )
        self.assertEqual({row.status for row in charges}, {"Invoiced"})
        self.assertEqual(
            {row.student: row.account_holder for row in charges},
            {
                student_a.name: account_holder_a.name,
                student_b.name: account_holder_a.name,
                student_c.name: account_holder_b.name,
            },
        )

        invoice_to_delete = invoices[account_holder_a.name]
        frappe.delete_doc("Sales Invoice", invoice_to_delete.name, ignore_permissions=True)

        reset_rows = frappe.get_all(
            "Billable Charge",
            filters={"charge_batch": batch.name, "account_holder": account_holder_a.name},
            fields=["status", "sales_invoice"],
            limit=10,
        )
        self.assertEqual({row.status for row in reset_rows}, {"Pending"})
        self.assertEqual({row.sales_invoice for row in reset_rows}, {None})

    def test_missing_account_holder_blocks_batch_generation(self):
        org = self.make_organization("Charge Block")
        income = self.make_account(org.name, "Income", prefix="Lunch Income")
        school = self.make_school(org.name)
        offering = self.make_billable_offering(
            org.name,
            income.name,
            offering_type="Service Subscription",
            pricing_mode="Fixed",
            offering_name="Lunch",
        )
        self.make_fiscal_year(org.name, year=2026, year_start_date="2026-01-01", year_end_date="2026-12-31")

        student = frappe.get_doc(
            {
                "doctype": "Student",
                "student_first_name": "No",
                "student_last_name": f"Payer {frappe.generate_hash(length=6)}",
                "student_email": f"{frappe.generate_hash(length=8)}@example.com",
                "anchor_school": school.name,
            }
        )
        previous_in_migration = bool(getattr(frappe.flags, "in_migration", False))
        frappe.flags.in_migration = True
        try:
            student.insert()
        finally:
            frappe.flags.in_migration = previous_in_migration

        batch = frappe.get_doc(
            {
                "doctype": "Charge Batch",
                "organization": org.name,
                "batch_title": f"Lunch {frappe.generate_hash(length=6)}",
                "source_type": "Lunch",
                "billable_offering": offering.name,
                "posting_date": "2026-05-30",
                "due_date": "2026-06-05",
                "default_qty": 1,
                "default_rate": 20,
                "description": "Lunch charge",
                "students": [{"student": student.name}],
            }
        )
        batch.insert()

        self.assertEqual(batch.students[0].status, "Blocked")
        self.assertIn("Account Holder", batch.students[0].issue)
        with self.assertRaises(frappe.ValidationError):
            generate_draft_invoices_for_charge_batch(batch.name)

    def test_large_batch_generation_is_enqueued(self):
        org = self.make_organization("Charge Queue")
        income = self.make_account(org.name, "Income", prefix="Trip Queue Income")
        school = self.make_school(org.name)
        account_holder = self.make_account_holder(org.name, prefix="Queue Payer")
        students = [
            self.make_student(org.name, account_holder.name, school=school.name, prefix=f"Queue Student {idx}")
            for idx in range(3)
        ]
        offering = self.make_billable_offering(
            org.name,
            income.name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
            offering_name="Queued Trip",
        )

        batch = frappe.get_doc(
            {
                "doctype": "Charge Batch",
                "organization": org.name,
                "batch_title": f"Queued Trip {frappe.generate_hash(length=6)}",
                "source_type": "Trip",
                "billable_offering": offering.name,
                "posting_date": "2026-05-30",
                "due_date": "2026-06-05",
                "default_qty": 1,
                "default_rate": 80,
                "description": "Queued field trip",
                "students": [{"student": student.name} for student in students],
            }
        )
        batch.insert()

        with (
            patch.object(charge_generation, "CHARGE_BATCH_INVOICE_QUEUE_THRESHOLD", 2),
            patch("ifitwala_ed.accounting.charges.charge_generation.frappe.enqueue") as mocked_enqueue,
        ):
            result = charge_generation.generate_draft_invoices_for_charge_batch_or_enqueue(
                batch.name,
                target_user="accounts@example.com",
            )

        self.assertEqual(result["queued"], 1)
        mocked_enqueue.assert_called_once()
        self.assertEqual(mocked_enqueue.call_args.kwargs["queue"], "long")
        self.assertEqual(mocked_enqueue.call_args.kwargs["charge_batch"], batch.name)
        self.assertTrue(mocked_enqueue.call_args.kwargs["enqueue_after_commit"])

        batch.reload()
        self.assertEqual(batch.invoice_generation_status, "Queued")
