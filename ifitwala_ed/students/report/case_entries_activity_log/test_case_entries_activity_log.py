import importlib
import sys
import types
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch


def _install_frappe_stub():
    class _Dict(dict):
        __getattr__ = dict.get

        def __setattr__(self, key, value):
            self[key] = value

    frappe = sys.modules.get("frappe") or types.ModuleType("frappe")
    frappe._dict = _Dict
    frappe._ = lambda text: text
    frappe.throw = lambda message, *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError(message))
    frappe.ValidationError = type("ValidationError", (Exception,), {})
    frappe.db = types.SimpleNamespace(sql=lambda *args, **kwargs: [], get_value=lambda *args, **kwargs: None)
    frappe.session = _Dict({"user": "test@example.com"})
    frappe.defaults = types.SimpleNamespace(get_user_default=lambda *args, **kwargs: None)
    frappe.get_roles = lambda *_args, **_kwargs: []

    frappe_utils = sys.modules.get("frappe.utils") or types.ModuleType("frappe.utils")
    frappe_utils.formatdate = lambda value, *_args, **_kwargs: str(value or "")
    frappe_utils.get_link_to_form = lambda _doctype, name, label=None: label or name
    frappe_utils.getdate = lambda value=None: datetime.strptime(str(value), "%Y-%m-%d").date() if value else None
    frappe_utils.get_system_timezone = lambda: "UTC"
    frappe_utils.flt = lambda value: float(value or 0)
    frappe_utils.strip_html = lambda value: value or ""
    frappe_utils.escape_html = lambda value: value or ""

    frappe.utils = frappe_utils

    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = frappe_utils


def _install_support_stubs():
    school_settings_utils = types.ModuleType("ifitwala_ed.school_settings.school_settings_utils")
    school_settings_utils.get_allowed_schools = lambda user=None, selected_school=None: []
    sys.modules["ifitwala_ed.school_settings.school_settings_utils"] = school_settings_utils


_install_frappe_stub()
_install_support_stubs()

frappe = sys.modules["frappe"]
case_entries_activity_log = importlib.import_module(
    "ifitwala_ed.students.report.case_entries_activity_log.case_entries_activity_log"
)


class TestCaseEntriesActivityLog(TestCase):
    @patch("ifitwala_ed.students.report.case_entries_activity_log.case_entries_activity_log._guard_roles")
    @patch(
        "ifitwala_ed.students.report.case_entries_activity_log.case_entries_activity_log.frappe.db.sql", return_value=[]
    )
    @patch(
        "ifitwala_ed.students.report.case_entries_activity_log.case_entries_activity_log.get_allowed_schools",
        return_value=["SCH-PARENT", "SCH-CHILD"],
    )
    @patch(
        "ifitwala_ed.students.report.case_entries_activity_log.case_entries_activity_log.frappe.session",
        frappe._dict({"user": "staff@example.com"}),
    )
    def test_execute_uses_descendant_aware_allowed_school_scope(
        self,
        mock_get_allowed_schools,
        mock_sql,
        _mock_guard_roles,
    ):
        case_entries_activity_log.execute({"school": "SCH-PARENT"})

        mock_get_allowed_schools.assert_called_once_with("staff@example.com", "SCH-PARENT")
        query, params = mock_sql.call_args.args[:2]
        self.assertIn("rc.school IN %(school_list)s", query)
        self.assertEqual(params["school_list"], ("SCH-PARENT", "SCH-CHILD"))
