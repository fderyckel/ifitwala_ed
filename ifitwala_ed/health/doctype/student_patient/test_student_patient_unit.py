from __future__ import annotations

from types import ModuleType
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _student_patient_modules(calls: list[dict]):
    student_utils = ModuleType("ifitwala_ed.utilities.student_utils")

    def get_basic_student_info(student, *, include_dob=False):
        calls.append({"student": student, "include_dob": include_dob})
        payload = {
            "student_full_name": "Amina Learner",
            "student_age": "12 years, 2 months",
        }
        if include_dob:
            payload["student_date_of_birth"] = "2014-03-02"
        return payload

    student_utils.get_basic_student_info = get_basic_student_info
    return {"ifitwala_ed.utilities.student_utils": student_utils}


class TestStudentPatientUnit(TestCase):
    def test_basic_info_hides_dob_for_non_medical_dob_role(self):
        calls: list[dict] = []
        with stubbed_frappe(extra_modules=_student_patient_modules(calls)) as frappe:
            frappe.has_permission = lambda doctype, ptype: doctype == "Student Patient" and ptype == "read"
            frappe.get_roles = lambda user: ["Academic Assistant"]
            frappe.session.user = "assistant@example.com"

            module = import_fresh("ifitwala_ed.health.doctype.student_patient.student_patient")
            payload = module.get_student_basic_info("STU-0001")

        self.assertEqual(calls, [{"student": "STU-0001", "include_dob": False}])
        self.assertEqual(payload["student_age"], "12 years, 2 months")
        self.assertNotIn("student_date_of_birth", payload)

    def test_basic_info_returns_dob_for_nurse(self):
        calls: list[dict] = []
        with stubbed_frappe(extra_modules=_student_patient_modules(calls)) as frappe:
            frappe.has_permission = lambda doctype, ptype: doctype == "Student Patient" and ptype == "read"
            frappe.get_roles = lambda user: ["Nurse"]
            frappe.session.user = "nurse@example.com"

            module = import_fresh("ifitwala_ed.health.doctype.student_patient.student_patient")
            payload = module.get_student_basic_info("STU-0001")

        self.assertEqual(calls, [{"student": "STU-0001", "include_dob": True}])
        self.assertEqual(payload["student_date_of_birth"], "2014-03-02")
