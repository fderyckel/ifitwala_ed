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
    frappe_utils.getdate = lambda value=None: value
    frappe_utils.today = lambda: "2026-01-01"

    frappe.utils = frappe_utils

    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = frappe_utils


def _install_support_stubs():
    fiscal_year_utils = types.ModuleType("ifitwala_ed.accounting.fiscal_year_utils")
    fiscal_year_utils.fill_date_range_from_fiscal_year = lambda filters, from_key="from_date", to_key="to_date": (
        None,
        None,
    )
    sys.modules["ifitwala_ed.accounting.fiscal_year_utils"] = fiscal_year_utils


_install_frappe_stub()
_install_support_stubs()

aged_receivables = importlib.import_module("ifitwala_ed.accounting.report.aged_receivables.aged_receivables")


class TestAgedReceivables(TestCase):
    @patch("ifitwala_ed.accounting.report.aged_receivables.aged_receivables.frappe.db.sql", return_value=[])
    @patch(
        "ifitwala_ed.accounting.report.aged_receivables.aged_receivables.fill_date_range_from_fiscal_year",
        return_value=(None, None),
    )
    def test_execute_keeps_exact_match_invoice_item_school_filter(
        self,
        _mock_dates,
        mock_sql,
    ):
        aged_receivables.execute({"organization": "ORG-1", "school": "SCH-PARENT"})

        query, params = mock_sql.call_args.args[:2]
        self.assertIn("sii.school = %(school)s", query)
        self.assertEqual(params["school"], "SCH-PARENT")
