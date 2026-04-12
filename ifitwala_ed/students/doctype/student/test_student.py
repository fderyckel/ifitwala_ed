# ifitwala_ed/students/doctype/student/test_student.py
# Copyright (c) 2024, fdR and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.students.doctype.student.student import (
    get_family_address_link_proposal,
    get_student_crm_summary,
    link_family_address,
)


class TestStudent(FrappeTestCase):
    def _student_payload(self) -> dict:
        seed = frappe.generate_hash(length=8)
        return {
            "doctype": "Student",
            "student_first_name": "Test",
            "student_last_name": f"Student{seed}",
            "student_email": f"student-{seed}@example.com",
        }

    def _make_imported_student(self):
        prev_import = getattr(frappe.flags, "in_import", False)
        frappe.flags.in_import = True
        try:
            doc = frappe.get_doc(self._student_payload())
            doc.allow_direct_creation = 1
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_import = prev_import
        return doc

    def _make_guardian(self, *, email: str | None = None):
        seed = frappe.generate_hash(length=8)
        phone_suffix = "".join(str(ord(ch) % 10) for ch in seed[:6])
        guardian = frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_first_name": "Guardian",
                "guardian_last_name": seed,
                "guardian_email": email or f"guardian-{seed}@example.com",
                "guardian_mobile_phone": f"+1415{phone_suffix}",
            }
        ).insert(ignore_permissions=True)
        return guardian

    def _make_address(self, *, link_doctype: str, link_name: str, prefix: str):
        meta = frappe.get_meta("Address")
        links_field = meta.get_field("links")
        self.assertIsNotNone(links_field)
        country_name = frappe.get_all("Country", fields=["name"], limit=1)
        resolved_country = (country_name[0].get("name") if country_name else None) or "Thailand"

        address_seed = frappe.generate_hash(length=6)
        payload = {"doctype": "Address"}
        for fieldname, value in {
            "address_title": f"{prefix} {address_seed}",
            "address_type": "Billing",
            "address_line1": "1 Test Street",
            "city": "Bangkok",
            "country": resolved_country,
            "pincode": "10110",
        }.items():
            if meta.get_field(fieldname):
                payload[fieldname] = value

        address = frappe.get_doc(payload)
        address.append(links_field.fieldname, {"link_doctype": link_doctype, "link_name": link_name})
        address.insert(ignore_permissions=True)
        return address

    def test_direct_creation_is_blocked_without_applicant_or_import_context(self):
        doc = frappe.get_doc(self._student_payload())
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_import_context_allows_direct_creation(self):
        prev_import = getattr(frappe.flags, "in_import", False)
        frappe.flags.in_import = True
        try:
            doc = frappe.get_doc(self._student_payload())
            doc.allow_direct_creation = 1
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_import = prev_import

        self.assertTrue(bool(doc.name))

    def test_import_context_requires_allow_direct_creation(self):
        prev_import = getattr(frappe.flags, "in_import", False)
        frappe.flags.in_import = True
        try:
            doc = frappe.get_doc(self._student_payload())
            with self.assertRaises(frappe.ValidationError):
                doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_import = prev_import

    def test_update_after_migration_insert_without_allow_direct_creation_is_allowed(self):
        prev_migration = getattr(frappe.flags, "in_migration", False)
        frappe.flags.in_migration = True
        try:
            doc = frappe.get_doc(self._student_payload())
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_migration = prev_migration

        doc.student_preferred_name = "Updated Name"
        doc.save(ignore_permissions=True)
        self.assertEqual(doc.student_preferred_name, "Updated Name")

    def test_get_student_crm_summary_returns_contact_and_student_address(self):
        student = self._make_imported_student()
        address = self._make_address(link_doctype="Student", link_name=student.name, prefix="Student Address")

        summary = get_student_crm_summary(student.name)

        contact_name = frappe.db.get_value(
            "Dynamic Link",
            {"parenttype": "Contact", "link_doctype": "Student", "link_name": student.name},
            "parent",
        )
        self.assertEqual(summary.get("contact"), contact_name)
        self.assertEqual(summary.get("addresses"), [address.name])
        self.assertEqual(int(summary.get("address_count") or 0), 1)

    def test_family_address_proposal_skips_related_records_with_existing_address(self):
        student = self._make_imported_student()
        sibling = self._make_imported_student()
        guardian = self._make_guardian()

        student.append("guardians", {"guardian": guardian.name, "relation": "Mother", "can_consent": 1})
        student.append("siblings", {"student": sibling.name})
        student.save(ignore_permissions=True)

        student_address = self._make_address(link_doctype="Student", link_name=student.name, prefix="Home")
        self._make_address(link_doctype="Student", link_name=sibling.name, prefix="Sibling Existing")

        proposal = get_family_address_link_proposal(student.name, student_address.name)

        self.assertEqual([row["guardian"] for row in proposal.get("eligible_guardians") or []], [guardian.name])
        self.assertEqual(proposal.get("eligible_siblings") or [], [])
        self.assertEqual([row["student"] for row in proposal.get("skipped_siblings") or []], [sibling.name])

    def test_link_family_address_links_only_selected_family_records(self):
        student = self._make_imported_student()
        sibling = self._make_imported_student()
        guardian = self._make_guardian()

        student.append("guardians", {"guardian": guardian.name, "relation": "Father", "can_consent": 1})
        student.append("siblings", {"student": sibling.name})
        student.save(ignore_permissions=True)

        student_address = self._make_address(link_doctype="Student", link_name=student.name, prefix="Family Home")

        result = link_family_address(
            student.name,
            student_address.name,
            guardians=[guardian.name],
            siblings=[sibling.name],
        )

        self.assertEqual(result.get("linked_guardians"), [guardian.name])
        self.assertEqual(result.get("linked_siblings"), [sibling.name])
        self.assertTrue(
            frappe.db.exists(
                "Dynamic Link",
                {
                    "parenttype": "Address",
                    "parent": student_address.name,
                    "link_doctype": "Guardian",
                    "link_name": guardian.name,
                },
            )
        )
        self.assertTrue(
            frappe.db.exists(
                "Dynamic Link",
                {
                    "parenttype": "Address",
                    "parent": student_address.name,
                    "link_doctype": "Student",
                    "link_name": sibling.name,
                },
            )
        )
