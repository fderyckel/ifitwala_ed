from __future__ import annotations
import __future__

import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from ifitwala_ed.tests.frappe_stubs import stubbed_frappe


@contextmanager
def _student_referral_module():
    frappe_desk = ModuleType("frappe.desk")
    frappe_desk_form = ModuleType("frappe.desk.form")
    frappe_assign_to = ModuleType("frappe.desk.form.assign_to")
    frappe_assign_to.add = lambda *args, **kwargs: None
    frappe_desk.form = frappe_desk_form
    frappe_desk_form.assign_to = frappe_assign_to

    with stubbed_frappe(
        extra_modules={
            "frappe.desk": frappe_desk,
            "frappe.desk.form": frappe_desk_form,
            "frappe.desk.form.assign_to": frappe_assign_to,
        }
    ) as frappe:
        frappe_utils = sys.modules["frappe.utils"]
        frappe_utils.add_to_date = lambda value, **kwargs: value
        frappe_utils.cint = lambda value=0: int(value or 0)
        frappe_utils.getdate = lambda value=None: value
        frappe_utils.now_datetime = lambda: "2026-04-23 09:15:00"
        frappe_utils.nowdate = lambda: "2026-04-23"

        frappe.db.exists = lambda *args, **kwargs: False
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.db.sql = lambda *args, **kwargs: []
        frappe.db.set_value = lambda *args, **kwargs: None
        frappe.new_doc = lambda doctype: None
        frappe.publish_realtime = lambda *args, **kwargs: None
        frappe.log_error = lambda *args, **kwargs: None
        frappe.sendmail = lambda *args, **kwargs: None
        frappe.enqueue = lambda *args, **kwargs: None

        module = ModuleType("ifitwala_ed.students.doctype.student_referral.student_referral")
        module.__file__ = str(Path(__file__).with_name("student_referral.py"))
        module.__package__ = "ifitwala_ed.students.doctype.student_referral"

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


class TestStudentReferralUnit(TestCase):
    def test_open_case_returns_existing_case_without_repairing_referral_mirror(self):
        with _student_referral_module() as (student_referral_module, frappe):
            referral = student_referral_module.StudentReferral.__new__(student_referral_module.StudentReferral)
            referral.name = "SRF-0001"

            frappe.db.get_value = lambda doctype, filters=None, fieldname=None: (
                "RC-0001" if doctype == "Referral Case" else None
            )
            frappe.db.set_value = Mock()

            case_name = referral.open_case()

        self.assertEqual(case_name, "RC-0001")
        frappe.db.set_value.assert_not_called()

    def test_open_case_creates_case_and_stamps_referral_mirror(self):
        with _student_referral_module() as (student_referral_module, frappe):
            referral = student_referral_module.StudentReferral.__new__(student_referral_module.StudentReferral)
            referral.name = "SRF-0002"
            referral.student = "STU-0001"
            referral.program = "PROG-0001"
            referral.academic_year = "AY-2026"
            referral.school = "SCH-0001"
            referral.confidentiality_level = "Sensitive"
            referral.severity = "High"

            case = SimpleNamespace(
                name="RC-NEW-0001",
                referral=None,
                student=None,
                program=None,
                academic_year=None,
                school=None,
                confidentiality_level=None,
                severity=None,
                opened_on=None,
                insert=Mock(),
            )

            frappe.db.get_value = lambda *args, **kwargs: None
            frappe.new_doc = lambda doctype: case
            frappe.db.set_value = Mock()

            case_name = referral.open_case()

        self.assertEqual(case_name, "RC-NEW-0001")
        self.assertEqual(case.referral, "SRF-0002")
        self.assertEqual(case.student, "STU-0001")
        self.assertEqual(case.program, "PROG-0001")
        self.assertEqual(case.academic_year, "AY-2026")
        self.assertEqual(case.school, "SCH-0001")
        self.assertEqual(case.confidentiality_level, "Sensitive")
        self.assertEqual(case.severity, "High")
        self.assertEqual(case.opened_on, "2026-04-23")
        case.insert.assert_called_once_with(ignore_permissions=True)
        frappe.db.set_value.assert_called_once_with(
            "Student Referral",
            "SRF-0002",
            "referral_case",
            "RC-NEW-0001",
            update_modified=False,
        )

    def test_active_enrollment_context_uses_program_offering_school(self):
        captured = {}

        def fake_sql(query, values=None, as_dict=False):
            captured["query"] = query
            captured["values"] = values
            captured["as_dict"] = as_dict
            return [
                SimpleNamespace(
                    name="PE-0001",
                    program="PROG-1",
                    academic_year="AY-2026",
                    school="SCH-OFFERING",
                    within_ay=1,
                    archived_flag=0,
                )
            ]

        with _student_referral_module() as (student_referral_module, frappe):
            referral = student_referral_module.StudentReferral.__new__(student_referral_module.StudentReferral)
            referral.student = "STU-0001"
            referral.date = "2026-04-19"
            referral.get = lambda fieldname: getattr(referral, fieldname, None)
            frappe.db.sql = fake_sql

            context = referral.get_student_active_enrollment("STU-0001", "2026-04-19")

        self.assertEqual(
            context,
            {
                "name": "PE-0001",
                "program": "PROG-1",
                "academic_year": "AY-2026",
                "school": "SCH-OFFERING",
            },
        )
        self.assertEqual(captured["values"], {"student": "STU-0001", "on_date": "2026-04-19"})
        self.assertTrue(captured["as_dict"])
        self.assertIn("LEFT JOIN `tabProgram Offering` po", captured["query"])
        self.assertIn("po.school", captured["query"])
        self.assertNotIn("p.school", captured["query"])
