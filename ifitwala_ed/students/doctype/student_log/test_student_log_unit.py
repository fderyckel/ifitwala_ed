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
