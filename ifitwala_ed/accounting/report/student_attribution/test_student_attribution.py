import importlib
import sys
import types
from unittest import TestCase
from unittest.mock import patch


def _install_frappe_stub():
    frappe = sys.modules.get("frappe") or types.ModuleType("frappe")
    frappe._ = lambda text: text
    frappe.throw = lambda message, *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError(message))
    frappe.ValidationError = type("ValidationError", (Exception,), {})
    frappe.db = types.SimpleNamespace(sql=lambda *args, **kwargs: [])

    frappe_utils = sys.modules.get("frappe.utils") or types.ModuleType("frappe.utils")
    frappe_utils.flt = lambda value: float(value or 0)

    frappe.utils = frappe_utils

    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = frappe_utils


def _install_support_stubs():
    fiscal_year_utils = types.ModuleType("ifitwala_ed.accounting.fiscal_year_utils")
    fiscal_year_utils.fill_date_range_from_fiscal_year = lambda filters, from_key="from_date", to_key="to_date": (
        None,
        None,
    )
    school_tree = types.ModuleType("ifitwala_ed.utilities.school_tree")
    school_tree.get_descendant_schools = lambda school=None: []
    sys.modules["ifitwala_ed.accounting.fiscal_year_utils"] = fiscal_year_utils
    sys.modules["ifitwala_ed.utilities.school_tree"] = school_tree


_install_frappe_stub()
_install_support_stubs()

student_attribution = importlib.import_module("ifitwala_ed.accounting.report.student_attribution.student_attribution")


class TestStudentAttribution(TestCase):
    @patch("ifitwala_ed.accounting.report.student_attribution.student_attribution.frappe.db.sql", return_value=[])
    @patch(
        "ifitwala_ed.accounting.report.student_attribution.student_attribution.get_descendant_schools",
        return_value=["SCH-PARENT", "SCH-CHILD"],
    )
    @patch(
        "ifitwala_ed.accounting.report.student_attribution.student_attribution.fill_date_range_from_fiscal_year",
        return_value=(None, None),
    )
    def test_execute_uses_descendant_aware_school_filter(
        self,
        _mock_dates,
        _mock_descendants,
        mock_sql,
    ):
        student_attribution.execute({"organization": "ORG-1", "school": "SCH-PARENT"})

        query, params = mock_sql.call_args.args[:2]
        self.assertIn("sii.school IN %(school_list)s", query)
        self.assertEqual(params["school_list"], ("SCH-PARENT", "SCH-CHILD"))
