from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _aged_receivables_module():
    fiscal_year_utils = ModuleType("ifitwala_ed.accounting.fiscal_year_utils")
    fiscal_year_utils.fill_date_range_from_fiscal_year = lambda filters, from_key="from_date", to_key="to_date": (
        None,
        None,
    )

    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.flt = lambda value: float(value or 0)
    frappe_utils.getdate = lambda value=None: value
    frappe_utils.today = lambda: "2026-01-01"

    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "ifitwala_ed.accounting.fiscal_year_utils": fiscal_year_utils,
        }
    ) as frappe:
        frappe.db.sql = lambda *args, **kwargs: []
        yield import_fresh("ifitwala_ed.accounting.report.aged_receivables.aged_receivables")


class TestAgedReceivables(TestCase):
    def test_execute_keeps_exact_match_invoice_item_school_filter(self):
        with (
            _aged_receivables_module() as module,
            patch.object(module.frappe.db, "sql", return_value=[]) as mock_sql,
            patch.object(module, "fill_date_range_from_fiscal_year", return_value=(None, None)),
        ):
            module.execute({"organization": "ORG-1", "school": "SCH-PARENT"})

        query, params = mock_sql.call_args.args[:2]
        self.assertIn("sii.school = %(school)s", query)
        self.assertEqual(params["school"], "SCH-PARENT")
