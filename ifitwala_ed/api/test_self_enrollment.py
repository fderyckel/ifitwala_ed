# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import self_enrollment as self_enrollment_api
from ifitwala_ed.schedule.doctype.program_enrollment_request.test_program_enrollment_request import _make_student
from ifitwala_ed.schedule.doctype.program_offering_selection_window.test_program_offering_selection_window import (
    _build_self_enrollment_context,
)


class TestSelfEnrollmentApi(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._guardian_links: list[tuple[str, str]] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        # These links live outside the test's explicit created-doc list and can leak
        # guardian scope across methods when naming series are reused in CI.
        for student_name, guardian_name in reversed(self._guardian_links):
            frappe.db.delete(
                "Student Guardian",
                {
                    "parent": student_name,
                    "parenttype": "Student",
                    "parentfield": "guardians",
                    "guardian": guardian_name,
                },
            )
            frappe.db.delete(
                "Guardian Student",
                {
                    "parent": guardian_name,
                    "parenttype": "Guardian",
                    "student": student_name,
                },
            )
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_guardian_board_lists_authorized_window(self):
        context = _build_self_enrollment_context()
        window = context["window"]
        window.load_students()
        window.prepare_requests()
        window.open_window()
        guardian_user = self._create_guardian_user_for_student(context["student"].name)

        frappe.set_user(guardian_user)
        payload = self_enrollment_api.get_self_enrollment_portal_board()

        self.assertEqual(payload["viewer"]["actor_type"], "Guardian")
        self.assertEqual(len(payload["windows"]), 1)
        self.assertEqual(payload["windows"][0]["selection_window"], window.name)
        self.assertEqual(payload["windows"][0]["students"][0]["student"], context["student"].name)

    def test_guardian_can_save_and_submit_choices(self):
        context = _build_self_enrollment_context(carry_forward_optional=False)
        window = context["window"]
        window.load_students()
        window.prepare_requests()
        window.open_window()
        guardian_user = self._create_guardian_user_for_student(context["student"].name)

        request_name = frappe.db.get_value(
            "Program Enrollment Request",
            {
                "selection_window": window.name,
                "student": context["student"].name,
            },
        )

        frappe.set_user(guardian_user)
        save_payload = self_enrollment_api.save_self_enrollment_choices(
            selection_window=window.name,
            student=context["student"].name,
            courses=[
                {
                    "course": context["optional_course"].name,
                    "applied_basket_group": context["basket_group"].name,
                }
            ],
        )

        request = frappe.get_doc("Program Enrollment Request", request_name)
        request.reload()
        self.assertEqual(request.status, "Draft")
        self.assertEqual(
            {row.course for row in request.courses},
            {context["required_course"].name, context["optional_course"].name},
        )
        optional_row = next(row for row in request.courses if row.course == context["optional_course"].name)
        self.assertEqual(optional_row.applied_basket_group, context["basket_group"].name)
        self.assertEqual(save_payload["permissions"]["can_edit"], 1)

        submit_payload = self_enrollment_api.submit_self_enrollment_choices(
            selection_window=window.name,
            student=context["student"].name,
        )
        request.reload()
        self.assertEqual(request.status, "Submitted")
        self.assertEqual(request.submitted_by, guardian_user)
        self.assertEqual(submit_payload["request"]["status"], "Submitted")
        self.assertEqual(submit_payload["permissions"]["can_edit"], 0)

    def test_guardian_choice_state_uses_family_friendly_validation_message(self):
        context = _build_self_enrollment_context(carry_forward_optional=False)
        window = context["window"]
        window.load_students()
        window.prepare_requests()
        window.open_window()
        guardian_user = self._create_guardian_user_for_student(context["student"].name)

        frappe.set_user(guardian_user)
        payload = self_enrollment_api.get_self_enrollment_choice_state(
            selection_window=window.name,
            student=context["student"].name,
        )

        self.assertEqual(payload["validation"]["status"], "invalid")
        self.assertEqual(payload["validation"]["violations"], [])
        self.assertIn(
            f"Choose at least one course in {context['basket_group'].name}.",
            payload["validation"]["reasons"],
        )

    def test_guardian_save_choices_returns_live_ready_state(self):
        context = _build_self_enrollment_context(carry_forward_optional=False)
        window = context["window"]
        window.load_students()
        window.prepare_requests()
        window.open_window()
        guardian_user = self._create_guardian_user_for_student(context["student"].name)

        frappe.set_user(guardian_user)
        payload = self_enrollment_api.save_self_enrollment_choices(
            selection_window=window.name,
            student=context["student"].name,
            courses=[
                {
                    "course": context["optional_course"].name,
                    "applied_basket_group": context["basket_group"].name,
                }
            ],
        )

        self.assertEqual(payload["request"]["validation_status"], "Not Validated")
        self.assertEqual(payload["validation"]["status"], "ok")
        self.assertTrue(payload["summary"]["ready_for_submit"])
        self.assertEqual(payload["validation"]["reasons"], [])

    def test_guardian_board_keeps_closed_window_visible_after_deadline(self):
        context = _build_self_enrollment_context(carry_forward_optional=False)
        window = context["window"]
        window.load_students()
        window.prepare_requests()
        window.open_window()
        window.close_window()
        guardian_user = self._create_guardian_user_for_student(context["student"].name)

        frappe.set_user(guardian_user)
        payload = self_enrollment_api.get_self_enrollment_portal_board()

        self.assertEqual(len(payload["windows"]), 1)
        self.assertEqual(payload["windows"][0]["status"], "Closed")
        self.assertEqual(payload["windows"][0]["students"][0]["request"]["status"], "Draft")

    def test_student_cannot_probe_other_student_scope(self):
        context = _build_self_enrollment_context()
        window = context["window"]
        window.load_students()
        window.prepare_requests()
        window.open_window()
        other_student = _make_student("Other Probe")

        frappe.set_user(context["student"].student_email)
        with self.assertRaises(frappe.PermissionError):
            self_enrollment_api.get_self_enrollment_choice_state(
                selection_window=window.name,
                student=other_student.name,
            )

    def _create_guardian_user_for_student(self, student_name: str) -> str:
        self._ensure_role("Guardian")
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"guardian-{frappe.generate_hash(length=8)}@example.com",
                "first_name": "Guardian",
                "last_name": "Portal",
                "enabled": 1,
                "user_type": "Website User",
                "roles": [{"role": "Guardian"}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))

        guardian = frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_first_name": "Guardian",
                "guardian_last_name": "Portal",
                "guardian_email": user.name,
                "guardian_mobile_phone": "5550000003",
                "user": user.name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Guardian", guardian.name))

        student = frappe.get_doc("Student", student_name)
        student.append(
            "guardians",
            {
                "guardian": guardian.name,
                "relation": "Mother",
            },
        )
        student.save(ignore_permissions=True)
        self._guardian_links.append((student.name, guardian.name))
        return user.name

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))
