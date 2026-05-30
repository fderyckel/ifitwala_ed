import json
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _program_billing_plan_module(*, plan_rows=None, offering_rows=None):
    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.flt = lambda value=0, precision=None: float(value or 0)

    account_holder_utils = ModuleType("ifitwala_ed.accounting.account_holder_utils")
    account_holder_utils.get_school_organization = lambda *args, **kwargs: None

    calls = []
    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "ifitwala_ed.accounting.account_holder_utils": account_holder_utils,
        }
    ) as frappe:
        frappe.parse_json = lambda value: json.loads(value) if isinstance(value, str) else value

        def get_list(doctype, **kwargs):
            calls.append(("get_list", doctype, kwargs))
            return list(plan_rows or [])

        def get_all(doctype, **kwargs):
            calls.append(("get_all", doctype, kwargs))
            return list(offering_rows or [])

        frappe.get_list = get_list
        frappe.get_all = get_all
        yield import_fresh("ifitwala_ed.accounting.doctype.program_billing_plan.program_billing_plan"), calls


class TestProgramBillingPlanListView(TestCase):
    def test_list_view_strips_generated_program_offering_title_join(self):
        script = Path(__file__).with_name("program_billing_plan_list.js").read_text()

        self.assertRegex(script, r"frappe\.listview_settings\[['\"]Program Billing Plan['\"]\]")
        self.assertIn("program_offering.offering_title as program_offering_offering_title", script)
        self.assertIn("delete listview.link_field_title_fields.program_offering", script)
        self.assertIn("get_program_offering_title_map_for_billing_plans", script)
        self.assertIn("hydrate_program_offering_titles(listview)", script)
        self.assertIn("program_offering(value, _df, doc)", script)

    def test_title_lookup_is_scoped_to_readable_billing_plan_rows(self):
        with _program_billing_plan_module(
            plan_rows=[{"name": "PBP-1", "program_offering": "PRO-OFF-1"}],
            offering_rows=[{"name": "PRO-OFF-1", "offering_title": "Grade 6 Tuition 2026"}],
        ) as (program_billing_plan, calls):
            title_map = program_billing_plan.get_program_offering_title_map_for_billing_plans(["PBP-1", "PBP-HIDDEN"])

        self.assertEqual(
            title_map,
            {
                "PBP-1": {
                    "program_offering": "PRO-OFF-1",
                    "offering_title": "Grade 6 Tuition 2026",
                }
            },
        )
        self.assertEqual(calls[0][0], "get_list")
        self.assertEqual(calls[0][1], "Program Billing Plan")
        self.assertEqual(calls[0][2]["filters"], {"name": ["in", ["PBP-1", "PBP-HIDDEN"]]})
        self.assertEqual(calls[0][2]["limit"], 2)
        self.assertEqual(calls[1][0], "get_all")
        self.assertEqual(calls[1][1], "Program Offering")
        self.assertEqual(calls[1][2]["filters"], {"name": ["in", ["PRO-OFF-1"]]})
