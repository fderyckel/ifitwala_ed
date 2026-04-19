from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _Dict(dict):
    __getattr__ = dict.get

    def __setattr__(self, key, value):
        self[key] = value


@contextmanager
def _case_entries_activity_log_module():
    school_settings_utils = ModuleType("ifitwala_ed.school_settings.school_settings_utils")
    school_settings_utils.get_allowed_schools = lambda user=None, selected_school=None: []

    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.formatdate = lambda value, *_args, **_kwargs: str(value or "")
    frappe_utils.get_link_to_form = lambda _doctype, name, label=None: label or name
    frappe_utils.getdate = lambda value=None: datetime.strptime(str(value), "%Y-%m-%d").date() if value else None
    frappe_utils.get_system_timezone = lambda: "UTC"
    frappe_utils.flt = lambda value: float(value or 0)
    frappe_utils.strip_html = lambda value: value or ""
    frappe_utils.escape_html = lambda value: value or ""

    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "ifitwala_ed.school_settings.school_settings_utils": school_settings_utils,
        }
    ) as frappe:
        frappe._dict = _Dict
        frappe.db.sql = lambda *args, **kwargs: []
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.session = _Dict({"user": "test@example.com"})
        frappe.defaults = SimpleNamespace(get_user_default=lambda *args, **kwargs: None)
        frappe.get_roles = lambda *_args, **_kwargs: []
        yield import_fresh("ifitwala_ed.students.report.case_entries_activity_log.case_entries_activity_log")


class TestCaseEntriesActivityLog(TestCase):
    def test_execute_uses_descendant_aware_allowed_school_scope(self):
        with (
            _case_entries_activity_log_module() as module,
            patch.object(module, "_guard_roles"),
            patch.object(module.frappe.db, "sql", return_value=[]) as mock_sql,
            patch.object(
                module, "get_allowed_schools", return_value=["SCH-PARENT", "SCH-CHILD"]
            ) as mock_get_allowed_schools,
            patch.object(module.frappe, "session", module.frappe._dict({"user": "staff@example.com"})),
        ):
            module.execute({"school": "SCH-PARENT"})

        mock_get_allowed_schools.assert_called_once_with("staff@example.com", "SCH-PARENT")
        query, params = mock_sql.call_args.args[:2]
        self.assertIn("rc.school IN %(school_list)s", query)
        self.assertEqual(params["school_list"], ("SCH-PARENT", "SCH-CHILD"))
