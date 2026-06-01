import json
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _billing_run_module(*, run_rows=None, offering_rows=None):
    account_holder_utils = ModuleType("ifitwala_ed.accounting.account_holder_utils")
    account_holder_utils.get_school_organization = lambda *args, **kwargs: None

    receivables = ModuleType("ifitwala_ed.accounting.receivables")
    receivables.money = lambda value=0: value or 0

    calls = []
    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.accounting.account_holder_utils": account_holder_utils,
            "ifitwala_ed.accounting.receivables": receivables,
        }
    ) as frappe:
        frappe.parse_json = lambda value: json.loads(value) if isinstance(value, str) else value

        def get_list(doctype, **kwargs):
            calls.append(("get_list", doctype, kwargs))
            return list(run_rows or [])

        def get_all(doctype, **kwargs):
            calls.append(("get_all", doctype, kwargs))
            return list(offering_rows or [])

        frappe.get_list = get_list
        frappe.get_all = get_all
        yield import_fresh("ifitwala_ed.accounting.doctype.billing_run.billing_run"), calls


class TestBillingRunListView(TestCase):
    def test_form_hydrates_context_when_billing_plan_is_selected(self):
        script = Path(__file__).with_name("billing_run.js").read_text()

        self.assertIn("get_billing_plan_context", script)
        self.assertIn("hydrate_context_from_billing_plan(frm)", script)
        self.assertIn("billing_plan(frm)", script)
        self.assertIn("organization: context.organization", script)
        self.assertIn("program_offering: context.program_offering", script)
        self.assertIn("academic_year: context.academic_year", script)

    def test_list_view_strips_generated_program_offering_title_join(self):
        script = Path(__file__).with_name("billing_run_list.js").read_text()

        self.assertRegex(script, r"frappe\.listview_settings\[['\"]Billing Run['\"]\]")
        self.assertIn("program_offering.offering_title as program_offering_offering_title", script)
        self.assertIn("delete listview.link_field_title_fields.program_offering", script)
        self.assertIn("get_program_offering_title_map_for_billing_runs", script)
        self.assertIn("hydrate_program_offering_titles(listview)", script)
        self.assertIn("program_offering(value, _df, doc)", script)

    def test_title_lookup_is_scoped_to_readable_billing_run_rows(self):
        with _billing_run_module(
            run_rows=[{"name": "BRUN-1", "program_offering": "PRO-OFF-1"}],
            offering_rows=[{"name": "PRO-OFF-1", "offering_title": "Grade 6 Tuition 2026"}],
        ) as (billing_run, calls):
            title_map = billing_run.get_program_offering_title_map_for_billing_runs(["BRUN-1", "BRUN-HIDDEN"])

        self.assertEqual(
            title_map,
            {
                "BRUN-1": {
                    "program_offering": "PRO-OFF-1",
                    "offering_title": "Grade 6 Tuition 2026",
                }
            },
        )
        self.assertEqual(calls[0][0], "get_list")
        self.assertEqual(calls[0][1], "Billing Run")
        self.assertEqual(calls[0][2]["filters"], {"name": ["in", ["BRUN-1", "BRUN-HIDDEN"]]})
        self.assertEqual(calls[0][2]["limit"], 2)
        self.assertEqual(calls[1][0], "get_all")
        self.assertEqual(calls[1][1], "Program Offering")
        self.assertEqual(calls[1][2]["filters"], {"name": ["in", ["PRO-OFF-1"]]})
