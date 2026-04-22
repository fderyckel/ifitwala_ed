from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _portal_module():
    image_helper_state = {"student": [], "guardian": []}

    admission_utils = ModuleType("ifitwala_ed.admission.admission_utils")
    admission_utils.ADMISSIONS_ROLES = set()

    guardian_communications = ModuleType("ifitwala_ed.api.guardian_communications")
    guardian_communications.get_guardian_portal_communication_unread_count = lambda: 0

    student_communications = ModuleType("ifitwala_ed.api.student_communications")
    student_communications.get_student_portal_communication_unread_count = lambda: 0

    attendance = ModuleType("ifitwala_ed.api.attendance")
    attendance.ADMIN_ROLES = set()
    attendance.COUNSELOR_ROLES = set()
    attendance.INSTRUCTOR_ROLES = set()

    def _analytics_module(attribute_name: str):
        module = ModuleType(attribute_name)
        setattr(module, "ALLOWED_ANALYTICS_ROLES", set())
        return module

    enrollment_analytics = _analytics_module("ifitwala_ed.api.enrollment_analytics")
    inquiry = _analytics_module("ifitwala_ed.api.inquiry")
    room_utilization = ModuleType("ifitwala_ed.api.room_utilization")
    room_utilization.ANALYTICS_ROLES = set()
    student_demographics = _analytics_module("ifitwala_ed.api.student_demographics_dashboard")
    student_log_dashboard = _analytics_module("ifitwala_ed.api.student_log_dashboard")
    student_overview_roles = ModuleType("ifitwala_ed.api.student_overview_roles")
    student_overview_roles.ALLOWED_STAFF_ROLES = set()
    users = ModuleType("ifitwala_ed.api.users")
    users.STAFF_ROLES = set()

    org_communication_quick_create = ModuleType("ifitwala_ed.api.org_communication_quick_create")
    org_communication_quick_create.get_org_communication_quick_create_capability = lambda user=None: {}

    policy_signature = ModuleType("ifitwala_ed.api.policy_signature")
    policy_signature.POLICY_LIBRARY_ROLES = set()
    policy_signature.POLICY_SIGNATURE_ANALYTICS_ROLES = set()
    policy_signature.POLICY_SIGNATURE_MANAGER_ROLES = set()

    image_utils = ModuleType("ifitwala_ed.utilities.image_utils")

    def get_preferred_student_avatar_url(
        student_name,
        *,
        original_url=None,
    ):
        image_helper_state["student"].append(
            {
                "student_name": student_name,
                "original_url": original_url,
            }
        )
        return "/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-THUMB&context_doctype=Student&context_name=STU-0001&derivative_role=thumb"

    def get_preferred_guardian_avatar_url(
        guardian_name,
        *,
        original_url=None,
    ):
        image_helper_state["guardian"].append(
            {
                "guardian_name": guardian_name,
                "original_url": original_url,
            }
        )
        return "/api/method/ifitwala_ed.api.file_access.download_guardian_file?file=FILE-THUMB&context_doctype=Guardian&context_name=GRD-0001&derivative_role=thumb"

    image_utils.get_preferred_student_avatar_url = get_preferred_student_avatar_url
    image_utils.get_preferred_guardian_avatar_url = get_preferred_guardian_avatar_url

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.admission.admission_utils": admission_utils,
            "ifitwala_ed.api.guardian_communications": guardian_communications,
            "ifitwala_ed.api.student_communications": student_communications,
            "ifitwala_ed.api.attendance": attendance,
            "ifitwala_ed.api.enrollment_analytics": enrollment_analytics,
            "ifitwala_ed.api.inquiry": inquiry,
            "ifitwala_ed.api.org_communication_quick_create": org_communication_quick_create,
            "ifitwala_ed.api.policy_signature": policy_signature,
            "ifitwala_ed.api.room_utilization": room_utilization,
            "ifitwala_ed.api.student_demographics_dashboard": student_demographics,
            "ifitwala_ed.api.student_log_dashboard": student_log_dashboard,
            "ifitwala_ed.api.student_overview_roles": student_overview_roles,
            "ifitwala_ed.api.users": users,
            "ifitwala_ed.utilities.image_utils": image_utils,
        }
    ) as frappe:
        frappe.as_json = lambda value: value
        frappe.cache = lambda: SimpleNamespace(
            get_value=lambda key: None,
            set_value=lambda key, value, expires_in_sec=None: None,
            delete_value=lambda key: None,
        )
        yield import_fresh("ifitwala_ed.api.portal"), frappe, image_helper_state


class TestPortalUnit(TestCase):
    def test_get_guardian_portal_identity_uses_derivative_only_avatar_url(self):
        with _portal_module() as (portal, frappe, image_helper_state):
            frappe.session = SimpleNamespace(user="guardian@example.com")

            def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False, **kwargs):
                del kwargs
                if doctype == "User":
                    return {
                        "name": "guardian@example.com",
                        "first_name": "Mina",
                        "full_name": "Mina Dar",
                        "email": "guardian@example.com",
                    }
                if doctype == "Guardian":
                    return {
                        "name": "GRD-0001",
                        "guardian_full_name": "Mina Dar",
                        "guardian_first_name": "Mina",
                        "guardian_last_name": "Dar",
                        "guardian_image": "/private/files/guardian-original.png",
                    }
                raise AssertionError(f"Unexpected get_value call: {doctype} {filters} {fieldname} {as_dict}")

            frappe.db.get_value = fake_get_value

            payload = portal.get_guardian_portal_identity()

        self.assertEqual(payload["guardian"], "GRD-0001")
        self.assertIn("derivative_role=thumb", payload["image_url"])
        self.assertEqual(
            image_helper_state["guardian"],
            [
                {
                    "guardian_name": "GRD-0001",
                    "original_url": "/private/files/guardian-original.png",
                }
            ],
        )

    def test_get_student_portal_identity_uses_derivative_only_avatar_url(self):
        cache_writes = []

        with _portal_module() as (portal, frappe, image_helper_state):
            frappe.session = SimpleNamespace(user="student@example.com")
            frappe.cache = lambda: SimpleNamespace(
                get_value=lambda key: None,
                set_value=lambda key, value, expires_in_sec=None: cache_writes.append(
                    {"key": key, "value": value, "expires_in_sec": expires_in_sec}
                ),
            )

            def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False, **kwargs):
                del kwargs
                if doctype == "User":
                    return {
                        "name": "student@example.com",
                        "first_name": "Amina",
                        "full_name": "Amina Example",
                    }
                if doctype == "Student":
                    return {
                        "name": "STU-0001",
                        "student_preferred_name": "Amina",
                        "student_first_name": "Amina",
                        "student_full_name": "Amina Example",
                        "student_image": "/private/files/student-original.png",
                    }
                raise AssertionError(f"Unexpected get_value call: {doctype} {filters} {fieldname} {as_dict}")

            frappe.db.get_value = fake_get_value

            payload = portal.get_student_portal_identity()

        self.assertEqual(payload["student"], "STU-0001")
        self.assertIn("derivative_role=thumb", payload["image_url"])
        self.assertEqual(
            image_helper_state["student"],
            [
                {
                    "student_name": "STU-0001",
                    "original_url": "/private/files/student-original.png",
                }
            ],
        )
        self.assertEqual(len(cache_writes), 1)
        self.assertIn("student_portal:identity:v4:student@example.com", cache_writes[0]["key"])

    def test_invalidate_student_portal_identity_cache_deletes_scoped_student_user_key(self):
        deleted_keys = []

        with _portal_module() as (portal, frappe, _image_helper_state):
            frappe.db.get_value = lambda doctype, name_or_filters, fieldname=None, **kwargs: (
                "student@example.com"
                if doctype == "Student" and name_or_filters == "STU-0001" and fieldname == "student_email"
                else None
            )
            frappe.cache = lambda: SimpleNamespace(
                get_value=lambda key: None,
                set_value=lambda key, value, expires_in_sec=None: None,
                delete_value=lambda key: deleted_keys.append(key),
            )

            portal.invalidate_student_portal_identity_cache(student="STU-0001")

        self.assertEqual(
            deleted_keys,
            ["student_portal:identity:v4:student@example.com"],
        )
