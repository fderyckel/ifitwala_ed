# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

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
def _student_log_follow_up_module():
    frappe_desk = ModuleType("frappe.desk")
    frappe_desk_form = ModuleType("frappe.desk.form")
    frappe_assign_to = ModuleType("frappe.desk.form.assign_to")
    frappe_assign_to.remove = lambda *args, **kwargs: None
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
        frappe.utils = frappe_utils
        frappe_utils.today = lambda: "2026-04-23"
        frappe_utils.get_fullname = lambda user: user
        frappe_utils.get_link_to_form = lambda doctype, name: f"/app/{doctype}/{name}"
        frappe_utils.strip_html = lambda value: value or ""

        frappe.session = SimpleNamespace(user="unit.test@example.com")
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.db.set_value = lambda *args, **kwargs: None
        frappe.get_all = lambda *args, **kwargs: []
        frappe.get_doc = lambda *args, **kwargs: None
        frappe.publish_realtime = lambda *args, **kwargs: None

        module = ModuleType("ifitwala_ed.students.doctype.student_log_follow_up.student_log_follow_up")
        module.__file__ = str(Path(__file__).with_name("student_log_follow_up.py"))
        module.__package__ = "ifitwala_ed.students.doctype.student_log_follow_up"
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


class TestStudentLogFollowUpUnit(TestCase):
    def test_close_open_todos_uses_native_assign_remove_api(self):
        with _student_log_follow_up_module() as (student_log_follow_up_module, _):
            doc = student_log_follow_up_module.StudentLogFollowUp.__new__(
                student_log_follow_up_module.StudentLogFollowUp
            )

            with (
                patch.object(
                    student_log_follow_up_module.frappe,
                    "get_all",
                    return_value=[
                        {"name": "TODO-1", "allocated_to": "assignee@example.com"},
                        {"name": "TODO-2", "allocated_to": "backup@example.com"},
                    ],
                ),
                patch.object(student_log_follow_up_module, "assign_remove") as assign_remove,
                patch.object(student_log_follow_up_module.frappe.db, "set_value") as set_value,
            ):
                doc._close_open_todos_for_log("LOG-0001")

        self.assertEqual(
            assign_remove.call_args_list,
            [
                call("Student Log", "LOG-0001", "assignee@example.com"),
                call("Student Log", "LOG-0001", "backup@example.com"),
            ],
        )
        set_value.assert_not_called()
