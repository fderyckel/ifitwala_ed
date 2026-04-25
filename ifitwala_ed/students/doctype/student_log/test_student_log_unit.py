from __future__ import annotations
import __future__

import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import call, patch

from ifitwala_ed.tests.frappe_stubs import stubbed_frappe


@contextmanager
def _student_log_module():
    frappe_desk = ModuleType("frappe.desk")
    frappe_desk_form = ModuleType("frappe.desk.form")
    frappe_assign_to = ModuleType("frappe.desk.form.assign_to")
    frappe_assign_to.add = lambda *args, **kwargs: None
    frappe_assign_to.remove = lambda *args, **kwargs: None
    frappe_desk.form = frappe_desk_form
    frappe_desk_form.assign_to = frappe_assign_to

    frappe_utils_nestedset = ModuleType("frappe.utils.nestedset")
    frappe_utils_nestedset.get_descendants_of = lambda *args, **kwargs: []

    with stubbed_frappe(
        extra_modules={
            "frappe.desk": frappe_desk,
            "frappe.desk.form": frappe_desk_form,
            "frappe.desk.form.assign_to": frappe_assign_to,
            "frappe.utils.nestedset": frappe_utils_nestedset,
        }
    ) as frappe:
        frappe_utils = sys.modules["frappe.utils"]
        frappe.utils = frappe_utils
        frappe_utils.cint = lambda value=0: int(value or 0)
        frappe_utils.date_diff = lambda left, right: 0
        frappe_utils.get_datetime = lambda value=None: value
        frappe_utils.add_days = lambda date, days: f"{date}+{days}"
        frappe_utils.today = lambda: "2026-04-19"
        frappe_utils.now_datetime = lambda: "2026-04-19 09:00:00"
        frappe_utils.get_fullname = lambda user: user

        frappe._dict = lambda value=None: SimpleNamespace(**(value or {}))
        frappe.defaults = SimpleNamespace(get_user_default=lambda key, user=None: None)
        frappe.cache = lambda: SimpleNamespace(
            set_value=lambda *args, **kwargs: None,
            get_value=lambda *args, **kwargs: None,
            lock=lambda *args, **kwargs: SimpleNamespace(__enter__=lambda self: self, __exit__=lambda *a: False),
        )
        frappe.as_json = lambda value, **kwargs: str(value)
        frappe.logger = lambda *args, **kwargs: SimpleNamespace(info=lambda *a, **k: None)
        frappe.db.exists = lambda *args, **kwargs: False
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.db.set_value = lambda *args, **kwargs: None
        frappe.db.sql = lambda *args, **kwargs: []
        frappe.get_all = lambda *args, **kwargs: []
        frappe.get_doc = lambda *args, **kwargs: None
        frappe.get_value = lambda *args, **kwargs: None
        frappe.get_roles = lambda user=None: []

        module = ModuleType("ifitwala_ed.students.doctype.student_log.student_log")
        module.__file__ = str(Path(__file__).with_name("student_log.py"))
        module.__package__ = "ifitwala_ed.students.doctype.student_log"

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


class TestStudentLogUnit(TestCase):
    def test_get_user_employee_reads_canonical_employee_fields_only(self):
        with _student_log_module() as (student_log_module, _):
            with (
                patch.object(student_log_module.frappe.db, "has_column", create=True) as has_column,
                patch.object(
                    student_log_module.frappe.db,
                    "get_value",
                    return_value=SimpleNamespace(name="EMP-0001", school="SCH-1"),
                ) as get_value,
            ):
                employee = student_log_module._get_user_employee("staff@example.com")

        has_column.assert_not_called()
        get_value.assert_called_once_with(
            "Employee",
            {"user_id": "staff@example.com"},
            ["name", "school"],
            as_dict=True,
        )
        self.assertEqual(employee.school, "SCH-1")

    def test_get_user_school_anchor_prefers_user_default_then_employee_school(self):
        with _student_log_module() as (student_log_module, _):
            with (
                patch.object(student_log_module.frappe.defaults, "get_user_default", return_value="SCH-DEFAULT"),
                patch.object(student_log_module, "_get_user_employee") as get_user_employee,
            ):
                anchor = student_log_module._get_user_school_anchor("staff@example.com")

            with (
                patch.object(student_log_module.frappe.defaults, "get_user_default", return_value=None),
                patch.object(
                    student_log_module,
                    "_get_user_employee",
                    return_value={"name": "EMP-0001", "school": "SCH-EMP"},
                ) as fallback_employee,
            ):
                employee_anchor = student_log_module._get_user_school_anchor("staff@example.com")

        get_user_employee.assert_not_called()
        fallback_employee.assert_called_once_with("staff@example.com")
        self.assertEqual(anchor, "SCH-DEFAULT")
        self.assertEqual(employee_anchor, "SCH-EMP")

    def test_program_enrollment_context_uses_program_offering_school(self):
        captured = {}

        def fake_sql(query, values=None, as_dict=False):
            captured["query"] = query
            captured["values"] = values
            captured["as_dict"] = as_dict
            return [
                {
                    "program": "PROG-1",
                    "academic_year": "AY-2026",
                    "program_offering": "PO-1",
                    "school": "SCH-OFFERING",
                    "within_ay": 1,
                    "archived_flag": 0,
                    "year_start_date": "2026-01-01",
                    "creation": "2026-04-01 08:00:00",
                }
            ]

        with _student_log_module() as (student_log_module, _):
            with patch.object(student_log_module.frappe.db, "sql", side_effect=fake_sql):
                context = student_log_module._get_program_enrollment_context(
                    "STU-0001",
                    on_date="2026-04-19",
                )

        self.assertEqual(
            context,
            {
                "program": "PROG-1",
                "academic_year": "AY-2026",
                "program_offering": "PO-1",
                "school": "SCH-OFFERING",
            },
        )
        self.assertEqual(captured["values"], {"student": "STU-0001", "on_date": "2026-04-19"})
        self.assertTrue(captured["as_dict"])
        self.assertIn("LEFT JOIN `tabProgram Offering` po", captured["query"])
        self.assertIn("po.school", captured["query"])
        self.assertNotIn("p.school", captured["query"])

    def test_validate_persists_academic_staff_default_when_next_step_has_no_associated_role(self):
        with _student_log_module() as (student_log_module, _):
            doc = student_log_module.StudentLog.__new__(student_log_module.StudentLog)
            doc.requires_follow_up = 1
            doc.next_step = "STEP-1"
            doc.follow_up_role = None
            doc.follow_up_person = None
            doc.follow_up_status = None
            doc.school = "SCH-1"
            doc.name = None
            doc.docstatus = 0
            doc.is_new = lambda: True
            doc._current_assignee = lambda: None
            doc._compute_follow_up_status = lambda: None
            doc._apply_status = lambda *args, **kwargs: None
            doc._ensure_delivery_context = lambda: None
            doc._resolve_school = lambda: "SCH-1"
            doc._assert_amendment_allowed = lambda: None
            doc._assert_core_fields_immutable_after_follow_up = lambda: None
            doc._assert_followup_transition_and_immutability = lambda: None

            with patch.object(student_log_module.frappe, "get_value", return_value=None):
                doc.validate()

        self.assertEqual(doc.follow_up_role, "Academic Staff")

    def test_validate_seeds_delivery_context_for_new_logs_only(self):
        with _student_log_module() as (student_log_module, _):
            doc = student_log_module.StudentLog.__new__(student_log_module.StudentLog)
            doc.requires_follow_up = 0
            doc.next_step = None
            doc.follow_up_person = None
            doc.follow_up_status = None
            doc.student = "STU-0001"
            doc.program = None
            doc.academic_year = None
            doc.program_offering = None
            doc.school = None
            doc.name = None
            doc.docstatus = 0
            doc.is_new = lambda: True
            doc._unassign = lambda: None
            doc._apply_status = lambda *args, **kwargs: None
            doc._assert_amendment_allowed = lambda: None
            doc._assert_core_fields_immutable_after_follow_up = lambda: None
            doc._assert_followup_transition_and_immutability = lambda: None

            def seed_context():
                doc.program = "PROG-1"
                doc.academic_year = "AY-2026"

            with (
                patch.object(doc, "_ensure_delivery_context", side_effect=seed_context) as ensure_delivery_context,
                patch.object(doc, "_resolve_school", return_value="SCH-1") as resolve_school,
            ):
                doc.validate()

        ensure_delivery_context.assert_called_once_with()
        resolve_school.assert_called_once_with()
        self.assertEqual(doc.school, "SCH-1")

    def test_validate_skips_delivery_context_backfill_for_existing_logs(self):
        with _student_log_module() as (student_log_module, _):
            doc = student_log_module.StudentLog.__new__(student_log_module.StudentLog)
            doc.requires_follow_up = 0
            doc.next_step = None
            doc.follow_up_person = None
            doc.follow_up_status = None
            doc.student = "STU-0001"
            doc.program = None
            doc.academic_year = None
            doc.program_offering = None
            doc.school = None
            doc.name = "LOG-0001"
            doc.docstatus = 0
            doc.is_new = lambda: False
            doc._unassign = lambda: None
            doc._apply_status = lambda *args, **kwargs: None
            doc._assert_amendment_allowed = lambda: None
            doc._assert_core_fields_immutable_after_follow_up = lambda: None
            doc._assert_followup_transition_and_immutability = lambda: None

            with (
                patch.object(doc, "_ensure_delivery_context") as ensure_delivery_context,
                patch.object(doc, "_resolve_school", return_value="SCH-1") as resolve_school,
            ):
                doc.validate()

        ensure_delivery_context.assert_not_called()
        resolve_school.assert_not_called()
        self.assertIsNone(doc.school)

    def test_validate_does_not_repair_existing_follow_up_assignments(self):
        with _student_log_module() as (student_log_module, _):
            doc = student_log_module.StudentLog.__new__(student_log_module.StudentLog)
            doc.requires_follow_up = 1
            doc.next_step = "STEP-1"
            doc.follow_up_role = None
            doc.follow_up_person = "selected@example.com"
            doc.follow_up_status = None
            doc.school = "SCH-1"
            doc.name = "LOG-0001"
            doc.docstatus = 1
            doc.is_new = lambda: False
            doc._compute_follow_up_status = lambda: None
            doc._apply_status = lambda *args, **kwargs: None
            doc._ensure_delivery_context = lambda: None
            doc._resolve_school = lambda: "SCH-1"
            doc._assert_amendment_allowed = lambda: None
            doc._assert_core_fields_immutable_after_follow_up = lambda: None
            doc._assert_followup_transition_and_immutability = lambda: None

            def fake_exists(doctype, filters=None):
                if doctype == "Student Log Follow Up":
                    return False
                if doctype == "Has Role":
                    return True
                raise AssertionError(f"Unexpected exists lookup: {doctype!r}")

            with (
                patch.object(student_log_module.frappe.db, "exists", side_effect=fake_exists),
                patch.object(doc, "_assign_to") as assign_to,
                patch.object(doc, "_unassign") as unassign,
            ):
                doc.validate()

        assign_to.assert_not_called()
        unassign.assert_not_called()
        self.assertEqual(doc.follow_up_person, "selected@example.com")

    def test_assign_follow_up_uses_persisted_role_without_repairing_it(self):
        with _student_log_module() as (student_log_module, frappe):
            inserted_todos = []

            class _FakeToDo:
                def __init__(self, payload):
                    self.payload = payload

                def insert(self, ignore_permissions=False):
                    inserted_todos.append((self.payload, ignore_permissions))
                    return self

            def fake_db_get_value(doctype, filters=None, fieldname=None, as_dict=False):
                if doctype == "Student Log":
                    return SimpleNamespace(
                        name="LOG-0001",
                        owner="author@example.com",
                        school="SCH-1",
                        student_name="Focus Student",
                        follow_up_status=None,
                        follow_up_role="Counselor",
                        next_step="STEP-1",
                    )
                if doctype == "ToDo":
                    return None
                raise AssertionError(f"Unexpected get_value lookup: {doctype!r}")

            def fake_get_roles(user=None):
                if user == "assignee@example.com":
                    return ["Counselor"]
                return ["Academic Admin"]

            with (
                patch.object(student_log_module.frappe.defaults, "get_user_default", return_value="SCH-1"),
                patch.object(student_log_module.frappe.db, "get_value", side_effect=fake_db_get_value),
                patch.object(student_log_module.frappe.db, "sql", side_effect=[[(1,)], None]),
                patch.object(student_log_module.frappe, "get_roles", side_effect=fake_get_roles),
                patch.object(student_log_module.frappe, "get_value") as get_value,
                patch.object(student_log_module, "_get_follow_up_due_days", return_value=4),
                patch.object(student_log_module.frappe.utils, "today", return_value="2026-04-19"),
                patch.object(student_log_module.frappe.utils, "add_days", return_value="2026-04-23"),
                patch.object(student_log_module.frappe, "get_doc", side_effect=lambda payload: _FakeToDo(payload)),
                patch.object(student_log_module.frappe.db, "set_value") as set_value,
                patch.object(frappe.session, "user", "admin@example.com"),
            ):
                result = student_log_module.assign_follow_up("LOG-0001", "assignee@example.com")

        self.assertEqual(result["assigned_to"], "assignee@example.com")
        self.assertEqual(result["status"], "Open")
        get_value.assert_not_called()
        self.assertEqual(
            set_value.call_args_list,
            [
                call("Student Log", "LOG-0001", "follow_up_person", "assignee@example.com"),
                call("Student Log", "LOG-0001", "follow_up_status", "Open"),
            ],
        )
        self.assertEqual(inserted_todos[0][0]["allocated_to"], "assignee@example.com")

    def test_unassign_uses_native_assign_remove_api(self):
        with _student_log_module() as (student_log_module, _):
            doc = student_log_module.StudentLog.__new__(student_log_module.StudentLog)
            doc.doctype = "Student Log"
            doc.name = "LOG-0001"
            doc._open_assignees = lambda: ["assignee@example.com", "backup@example.com"]

            with patch.object(student_log_module, "assign_remove") as assign_remove:
                doc._unassign()

        self.assertEqual(
            assign_remove.call_args_list,
            [
                call("Student Log", "LOG-0001", "assignee@example.com"),
                call("Student Log", "LOG-0001", "backup@example.com"),
            ],
        )

    def test_assign_follow_up_blocks_missing_follow_up_role_without_runtime_backfill(self):
        with _student_log_module() as (student_log_module, _):

            def fake_db_get_value(doctype, filters=None, fieldname=None, as_dict=False):
                if doctype == "Student Log":
                    return SimpleNamespace(
                        name="LOG-0002",
                        owner="author@example.com",
                        school="SCH-1",
                        student_name="Focus Student",
                        follow_up_status=None,
                        follow_up_role=None,
                        next_step="STEP-1",
                    )
                if doctype == "Employee":
                    return "SCH-1"
                raise AssertionError(f"Unexpected get_value lookup: {doctype!r}")

            with (
                patch.object(student_log_module.frappe.defaults, "get_user_default", return_value=None),
                patch.object(student_log_module.frappe.db, "get_value", side_effect=fake_db_get_value),
                patch.object(student_log_module.frappe.db, "sql", return_value=[(1,)]),
                patch.object(student_log_module.frappe, "get_value") as get_value,
                patch.object(student_log_module.frappe.db, "set_value") as set_value,
            ):
                with self.assertRaises(student_log_module.frappe.ValidationError):
                    student_log_module.assign_follow_up("LOG-0002", "assignee@example.com")

        get_value.assert_not_called()
        set_value.assert_not_called()
