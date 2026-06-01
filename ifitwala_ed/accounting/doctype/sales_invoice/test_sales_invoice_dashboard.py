import importlib
import sys
import types
import unittest
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def sales_invoice_dashboard_module():
    fake_frappe = types.ModuleType("frappe")
    fake_frappe._ = lambda value: value

    module_name = "ifitwala_ed.accounting.doctype.sales_invoice.sales_invoice_dashboard"
    previous_module = sys.modules.pop(module_name, None)
    with patch.dict(sys.modules, {"frappe": fake_frappe}):
        try:
            yield importlib.import_module(module_name)
        finally:
            sys.modules.pop(module_name, None)
            if previous_module is not None:
                sys.modules[module_name] = previous_module


class TestSalesInvoiceDashboard(unittest.TestCase):
    def test_dashboard_only_lists_standard_countable_links(self):
        with sales_invoice_dashboard_module() as dashboard:
            data = dashboard.get_data()

        items = [item for group in data["transactions"] for item in group["items"]]

        self.assertEqual(items, ["Payment Request", "Sales Invoice"])
        self.assertEqual(data["fieldname"], "sales_invoice")
        self.assertEqual(
            data["non_standard_fieldnames"],
            {
                "Sales Invoice": "against_sales_invoice",
            },
        )
