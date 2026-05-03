from __future__ import annotations
import __future__

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ifitwala_ed.tests.frappe_stubs import stubbed_frappe


@contextmanager
def _student_module():
    frappe_desk = ModuleType("frappe.desk")
    frappe_desk_form = ModuleType("frappe.desk.form")
    frappe_desk_linked_with = ModuleType("frappe.desk.form.linked_with")
    frappe_desk_linked_with.get_linked_doctypes = lambda *args, **kwargs: {}
    frappe_desk.form = frappe_desk_form
    frappe_desk_form.linked_with = frappe_desk_linked_with

    account_holder_utils = ModuleType("ifitwala_ed.accounting.account_holder_utils")
    account_holder_utils.validate_account_holder_for_student = lambda doc: None

    policy_utils = ModuleType("ifitwala_ed.governance.policy_utils")
    policy_utils.MEDIA_CONSENT_POLICY_KEY = "media_consent"
    policy_utils.has_applicant_policy_acknowledgement = lambda **kwargs: False

    drive_authority = ModuleType("ifitwala_ed.integrations.drive.authority")
    drive_authority.is_governed_file = lambda *args, **kwargs: False

    employee_utils = ModuleType("ifitwala_ed.utilities.employee_utils")
    employee_utils.get_user_visible_schools = lambda user=None: []

    student_utils = ModuleType("ifitwala_ed.utilities.student_utils")
    student_utils.format_student_age = lambda date_of_birth: "12 years" if date_of_birth else ""

    with stubbed_frappe(
        extra_modules={
            "frappe.desk": frappe_desk,
            "frappe.desk.form": frappe_desk_form,
            "frappe.desk.form.linked_with": frappe_desk_linked_with,
            "ifitwala_ed.accounting.account_holder_utils": account_holder_utils,
            "ifitwala_ed.governance.policy_utils": policy_utils,
            "ifitwala_ed.integrations.drive.authority": drive_authority,
            "ifitwala_ed.utilities.employee_utils": employee_utils,
            "ifitwala_ed.utilities.student_utils": student_utils,
        }
    ) as frappe:
        frappe_utils = sys.modules["frappe.utils"]
        frappe_utils.get_files_path = lambda *args, **kwargs: "/tmp"
        frappe_utils.get_link_to_form = lambda doctype, name: f"{doctype}:{name}"
        frappe_utils.getdate = lambda value=None: value
        frappe_utils.today = lambda: "2026-04-23"
        frappe_utils.validate_email_address = lambda value, throw=False: value

        frappe.flags = SimpleNamespace(from_applicant_promotion=False)
        frappe.msgprint = lambda *args, **kwargs: None
        frappe.log_error = lambda *args, **kwargs: None
        frappe.db.exists = lambda *args, **kwargs: False
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.db.escape = lambda value, percent=True: f"'{value}'"
        frappe.db.sql = lambda *args, **kwargs: []
        frappe.get_doc = lambda *args, **kwargs: None

        module = ModuleType("ifitwala_ed.students.doctype.student.student")
        module.__file__ = str(Path(__file__).with_name("student.py"))
        module.__package__ = "ifitwala_ed.students.doctype.student"

        source = Path(module.__file__).read_text(encoding="utf-8")
        code = compile(
            source,
            module.__file__,
            "exec",
            flags=__future__.annotations.compiler_flag,
            dont_inherit=True,
        )
        exec(code, module.__dict__)

        yield module, frappe


class TestStudentUnit(TestCase):
    def test_student_metadata_restricts_dob_and_exposes_derived_age(self):
        payload = json.loads(Path(__file__).with_name("student.json").read_text(encoding="utf-8"))
        fields = {field["fieldname"]: field for field in payload["fields"] if field.get("fieldname")}

        self.assertEqual(fields["student_date_of_birth"].get("permlevel"), 2)
        self.assertNotIn("in_filter", fields["student_date_of_birth"])
        self.assertNotIn("in_preview", fields["student_date_of_birth"])
        self.assertEqual(fields["student_age"].get("fieldtype"), "Data")
        self.assertEqual(fields["student_age"].get("is_virtual"), 1)
        self.assertEqual(fields["student_age"].get("read_only"), 1)

        dob_read_roles = {
            row.get("role")
            for row in payload["permissions"]
            if row.get("permlevel") == 2 and row.get("read")
        }
        self.assertEqual(dob_read_roles, {"Academic Admin", "System Manager"})

    def test_student_sibling_metadata_uses_age_not_dob(self):
        payload = json.loads(
            Path(__file__).parents[1].joinpath("student_sibling", "student_sibling.json").read_text(encoding="utf-8")
        )
        fields = {field["fieldname"]: field for field in payload["fields"] if field.get("fieldname")}

        self.assertIn("sibling_age", fields)
        self.assertNotIn("sibling_date_of_birth", fields)
        self.assertIn("sibling_age", payload["field_order"])
        self.assertNotIn("sibling_date_of_birth", payload["field_order"])
        self.assertEqual(fields["sibling_age"].get("read_only"), 1)

    def test_permission_query_conditions_scope_academic_assistant_to_visible_schools(self):
        with _student_module() as (student_module, frappe):
            with (
                patch.object(frappe, "get_roles", return_value=["Academic Assistant"]),
                patch.object(student_module, "get_user_visible_schools", return_value=["SCH-ROOT", "SCH-CHILD"]),
            ):
                condition = student_module.get_permission_query_conditions("assistant@example.com")

        self.assertEqual(condition, "`tabStudent`.`anchor_school` IN ('SCH-ROOT', 'SCH-CHILD')")

    def test_permission_query_conditions_scope_instructor_to_active_student_groups(self):
        with _student_module() as (student_module, frappe):
            with patch.object(frappe, "get_roles", return_value=["Instructor", "Academic Staff"]):
                condition = student_module.get_permission_query_conditions("teacher@example.com")

        self.assertIn("FROM `tabStudent Group Student` sgs", condition)
        self.assertIn("sgs.student = `tabStudent`.`name`", condition)
        self.assertIn("IFNULL(`tabStudent`.`enabled`, 1) = 1", condition)
        self.assertIn("COALESCE(sgs.active, 1) = 1", condition)
        self.assertIn("IFNULL(sg.status, 'Active') = 'Active'", condition)
        self.assertNotIn("anchor_school", condition)

    def test_has_permission_rejects_instructor_student_outside_group_scope(self):
        with _student_module() as (student_module, frappe):
            student = SimpleNamespace(name="STU-0001", anchor_school="SCH-ROOT")
            with patch.object(frappe, "get_roles", return_value=["Instructor", "Academic Staff"]):
                allowed = student_module.has_permission(student, ptype="read", user="teacher@example.com")

        self.assertFalse(allowed)

    def test_has_permission_allows_school_scoped_admin_inside_visible_school(self):
        with _student_module() as (student_module, frappe):
            allowed_doc = SimpleNamespace(name="STU-0001", anchor_school="SCH-CHILD")
            blocked_doc = SimpleNamespace(name="STU-0002", anchor_school="SCH-SIBLING")
            with (
                patch.object(frappe, "get_roles", return_value=["Academic Admin"]),
                patch.object(student_module, "get_user_visible_schools", return_value=["SCH-ROOT", "SCH-CHILD"]),
            ):
                allowed = student_module.has_permission(allowed_doc, ptype="read", user="admin@example.com")
                blocked = student_module.has_permission(blocked_doc, ptype="read", user="admin@example.com")

        self.assertTrue(allowed)
        self.assertFalse(blocked)

    def test_has_permission_does_not_upgrade_academic_staff_to_write(self):
        with _student_module() as (student_module, frappe):
            student = SimpleNamespace(name="STU-0001", anchor_school="SCH-CHILD")
            with (
                patch.object(frappe, "get_roles", return_value=["Academic Staff"]),
                patch.object(student_module, "get_user_visible_schools", return_value=["SCH-CHILD"]),
            ):
                allowed = student_module.has_permission(student, ptype="write", user="staff@example.com")

        self.assertFalse(allowed)

    def test_after_insert_for_applicant_promotion_still_materializes_contact_binding(self):
        with _student_module() as (student_module, frappe):
            frappe.flags.from_applicant_promotion = True
            student = student_module.Student.__new__(student_module.Student)

            with (
                patch.object(student, "create_student_user") as create_student_user,
                patch.object(student, "create_student_patient") as create_student_patient,
                patch.object(student, "ensure_contact_and_link") as ensure_contact_and_link,
            ):
                student.after_insert()

        create_student_user.assert_not_called()
        create_student_patient.assert_not_called()
        ensure_contact_and_link.assert_called_once_with()

    def test_on_update_no_longer_repairs_missing_contact_binding(self):
        with _student_module() as module_context:
            student_module = module_context[0]
            student = student_module.Student.__new__(student_module.Student)

            with (
                patch.object(student, "ensure_contact_and_link") as ensure_contact_and_link,
                patch.object(student, "update_student_enabled_status") as update_student_enabled_status,
                patch.object(student, "sync_student_contact_image") as sync_student_contact_image,
                patch.object(student, "sync_reciprocal_siblings") as sync_reciprocal_siblings,
            ):
                student.on_update()

        ensure_contact_and_link.assert_not_called()
        update_student_enabled_status.assert_called_once_with()
        sync_student_contact_image.assert_called_once_with()
        sync_reciprocal_siblings.assert_called_once_with()

    def test_ensure_contact_and_link_creates_contact_without_requiring_user(self):
        with _student_module() as (student_module, frappe):
            student = student_module.Student.__new__(student_module.Student)
            student.name = "STU-0001"
            student.student_email = "student@example.com"
            student.student_first_name = "Test"
            student.student_preferred_name = ""
            student.student_last_name = "Student"
            student.student_image = "/files/student.png"

            created_payloads: list[dict] = []
            contact = SimpleNamespace(
                name="CONTACT-0001",
                flags=SimpleNamespace(ignore_permissions=False),
                email_id=None,
                insert=Mock(),
                append=Mock(),
                save=Mock(),
            )

            frappe.db.exists = lambda doctype, filters=None: False

            def _get_value(doctype, filters=None, fieldname=None):
                if doctype == "Dynamic Link":
                    return None
                if doctype == "Contact":
                    return None
                if doctype == "Contact Email":
                    return None
                return None

            frappe.db.get_value = _get_value
            frappe.get_doc = lambda payload, *args: created_payloads.append(payload) or contact

            student.ensure_contact_and_link()

        self.assertEqual(created_payloads[0]["doctype"], "Contact")
        self.assertNotIn("user", created_payloads[0])
        self.assertEqual(contact.email_id, "student@example.com")
        contact.insert.assert_called_once_with()
        contact.append.assert_called_once_with("links", {"link_doctype": "Student", "link_name": "STU-0001"})
        contact.save.assert_called_once_with(ignore_permissions=True)

    def test_ensure_contact_and_link_reuses_primary_email_contact_before_creating_new_one(self):
        with _student_module() as (student_module, frappe):
            student = student_module.Student.__new__(student_module.Student)
            student.name = "STU-0002"
            student.student_email = "student@example.com"
            student.student_first_name = "Test"
            student.student_preferred_name = ""
            student.student_last_name = "Student"
            student.student_image = None

            existing_contact = SimpleNamespace(
                name="CONTACT-EXISTING",
                append=Mock(),
                save=Mock(),
            )

            frappe.db.exists = lambda doctype, filters=None: False

            def _get_value(doctype, filters=None, fieldname=None):
                if doctype == "Dynamic Link":
                    return None
                if doctype == "Contact":
                    return None
                if doctype == "Contact Email":
                    return "CONTACT-EXISTING"
                return None

            frappe.db.get_value = _get_value

            def _get_doc(doctype_or_payload, name=None):
                if doctype_or_payload == "Contact" and name == "CONTACT-EXISTING":
                    return existing_contact
                raise AssertionError(f"unexpected get_doc call: {doctype_or_payload!r}, {name!r}")

            frappe.get_doc = _get_doc

            student.ensure_contact_and_link()

        existing_contact.append.assert_called_once_with("links", {"link_doctype": "Student", "link_name": "STU-0002"})
        existing_contact.save.assert_called_once_with(ignore_permissions=True)
