# ifitwala_ed/api/test_focus_student_log.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint

from ifitwala_ed.api.focus import (
    ACTION_STUDENT_LOG_SUBMIT,
    build_focus_item_id,
    get_focus_context,
    submit_student_log_follow_up,
)
from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.tests.factories.users import make_user


class TestFocusStudentLog(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                if doctype == "Student Log":
                    docstatus = cint(frappe.db.get_value(doctype, name, "docstatus") or 0)
                    if docstatus == 1:
                        frappe.get_doc(doctype, name).cancel()
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

    def test_get_focus_context_includes_student_log_time(self):
        student = self._make_student()
        log_type = self._make_student_log_type()
        log = frappe.get_doc(
            {
                "doctype": "Student Log",
                "student": student.name,
                "date": "2026-04-01",
                "time": "10:15:00",
                "log_type": log_type.name,
                "log": "Observed a pastoral concern and recorded the first action taken.",
                "requires_follow_up": 0,
            }
        ).insert(ignore_permissions=True)
        log.submit()
        self._created.append(("Student Log", log.name))

        ctx = get_focus_context(
            reference_doctype="Student Log",
            reference_name=log.name,
            action_type="student_log.follow_up.act.submit",
        )

        self.assertEqual((ctx.get("log") or {}).get("date"), "2026-04-01")
        self.assertEqual((ctx.get("log") or {}).get("time"), "10:15:00")

    def test_submit_student_log_follow_up_allows_assignee_without_follow_up_doctype_role(self):
        fixture = self._make_follow_up_focus_fixture()

        self.assertFalse(
            frappe.has_permission(
                "Student Log Follow Up",
                ptype="create",
                user=fixture["assignee"],
            )
        )

        frappe.set_user(fixture["assignee"])
        result = submit_student_log_follow_up(
            focus_item_id=fixture["focus_item_id"],
            follow_up="Met the family, agreed on the next support steps, and logged the outcome.",
            client_request_id=f"focus-fu-{frappe.generate_hash(length=8)}",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "created")
        self._created.append(("Student Log Follow Up", result["follow_up_name"]))

        follow_up_doc = frappe.get_doc("Student Log Follow Up", result["follow_up_name"])
        self.assertEqual(follow_up_doc.docstatus, 1)
        self.assertEqual(follow_up_doc.student_log, fixture["log_name"])
        self.assertEqual(
            frappe.db.get_value("Student Log", fixture["log_name"], "follow_up_status"),
            "In Progress",
        )
        self.assertFalse(
            frappe.db.exists(
                "ToDo",
                {
                    "reference_type": "Student Log",
                    "reference_name": fixture["log_name"],
                    "status": "Open",
                },
            )
        )

    def test_submit_student_log_follow_up_rejects_reader_who_is_not_current_assignee(self):
        fixture = self._make_follow_up_focus_fixture()
        author_focus_item_id = build_focus_item_id(
            "student_log",
            "Student Log",
            fixture["log_name"],
            ACTION_STUDENT_LOG_SUBMIT,
            fixture["author"],
        )

        frappe.set_user(fixture["author"])
        with self.assertRaises(frappe.PermissionError):
            submit_student_log_follow_up(
                focus_item_id=author_focus_item_id,
                follow_up="Tried to submit from the author account even though the assignment belongs elsewhere.",
            )

        self.assertFalse(
            frappe.db.exists(
                "Student Log Follow Up",
                {"student_log": fixture["log_name"], "docstatus": 1},
            )
        )

    def test_submit_student_log_follow_up_is_idempotent_after_assignment_closes(self):
        fixture = self._make_follow_up_focus_fixture()
        client_request_id = f"focus-fu-{frappe.generate_hash(length=8)}"

        frappe.set_user(fixture["assignee"])
        first = submit_student_log_follow_up(
            focus_item_id=fixture["focus_item_id"],
            follow_up="Called the guardian, updated the student support note, and confirmed the next checkpoint.",
            client_request_id=client_request_id,
        )
        self._created.append(("Student Log Follow Up", first["follow_up_name"]))

        second = submit_student_log_follow_up(
            focus_item_id=fixture["focus_item_id"],
            follow_up="Called the guardian, updated the student support note, and confirmed the next checkpoint.",
            client_request_id=client_request_id,
        )

        self.assertEqual(first["status"], "created")
        self.assertEqual(second["status"], "already_processed")
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["follow_up_name"], second["follow_up_name"])

        submitted_rows = frappe.get_all(
            "Student Log Follow Up",
            filters={"student_log": fixture["log_name"], "docstatus": 1},
            fields=["name"],
        )
        self.assertEqual(len(submitted_rows), 1)

    def _ensure_role(self, user: str, role: str) -> None:
        if not frappe.db.exists("Role", role):
            self.skipTest(f"Missing Role '{role}' in this site.")
        if frappe.db.exists("Has Role", {"parent": user, "role": role}):
            return
        frappe.get_doc(
            {
                "doctype": "Has Role",
                "parent": user,
                "parenttype": "User",
                "parentfield": "roles",
                "role": role,
            }
        ).insert(ignore_permissions=True)

    def _get_or_create_program_root(self):
        if frappe.db.exists("Program", "All Programs"):
            return frappe.get_doc("Program", "All Programs")

        program = frappe.get_doc(
            {
                "doctype": "Program",
                "name": "All Programs",
                "program_name": "All Programs",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Program", program.name))
        return program

    def _make_follow_up_focus_fixture(self) -> dict[str, str]:
        frappe.set_user("Administrator")

        organization = make_organization(prefix="Focus Log Org")
        self._created.append(("Organization", organization.name))

        school = make_school(organization.name, prefix="Focus Log School")
        self._created.append(("School", school.name))

        assignee = make_user()
        self._created.append(("User", assignee.name))
        self._ensure_role(assignee.name, "Instructor")

        author = make_user()
        self._created.append(("User", author.name))

        student = self._make_student()
        log_type = self._make_student_log_type(school=school.name)
        next_step = self._make_student_log_next_step(school=school.name, associated_role="Instructor")
        program = self._get_or_create_program_root()

        log = frappe.get_doc(
            {
                "doctype": "Student Log",
                "student": student.name,
                "date": "2026-04-02",
                "time": "11:30:00",
                "log_type": log_type.name,
                "log": "Staff home focus follow-up coverage fixture.",
                "requires_follow_up": 1,
                "next_step": next_step.name,
                "follow_up_person": assignee.name,
                "program": program.name,
                "school": school.name,
                "visible_to_student": 0,
                "visible_to_guardians": 0,
            }
        ).insert(ignore_permissions=True)
        log.flags.ignore_permissions = True
        log.submit()
        self._created.append(("Student Log", log.name))

        frappe.db.set_value("Student Log", log.name, "owner", author.name, update_modified=False)

        return {
            "author": author.name,
            "assignee": assignee.name,
            "focus_item_id": build_focus_item_id(
                "student_log",
                "Student Log",
                log.name,
                ACTION_STUDENT_LOG_SUBMIT,
                assignee.name,
            ),
            "log_name": log.name,
        }

    def _make_student(self):
        student = frappe.get_doc(
            {
                "doctype": "Student",
                "student_first_name": "Focus",
                "student_last_name": f"Log-{frappe.generate_hash(length=6)}",
                "student_email": f"{frappe.generate_hash(length=8)}@example.com",
            }
        )
        previous_in_migration = bool(getattr(frappe.flags, "in_migration", False))
        frappe.flags.in_migration = True
        try:
            student.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_migration = previous_in_migration
        self._created.append(("Student", student.name))
        return student

    def _make_student_log_type(self, school: str | None = None):
        doc = frappe.get_doc(
            {
                "doctype": "Student Log Type",
                "log_type": f"Focus Test {frappe.generate_hash(length=6)}",
                "school": school,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Log Type", doc.name))
        return doc

    def _make_student_log_next_step(self, *, school: str, associated_role: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Log Next Step",
                "next_step": f"Focus Follow Up {frappe.generate_hash(length=6)}",
                "associated_role": associated_role,
                "school": school,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Log Next Step", doc.name))
        return doc
