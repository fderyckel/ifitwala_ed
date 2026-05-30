from pathlib import Path
from unittest import TestCase


class TestProgramBillingPlanListView(TestCase):
    def test_list_view_strips_generated_program_offering_title_join(self):
        script = Path(__file__).with_name("program_billing_plan_list.js").read_text()

        self.assertRegex(script, r"frappe\.listview_settings\[['\"]Program Billing Plan['\"]\]")
        self.assertIn("program_offering.offering_title as program_offering_offering_title", script)
        self.assertIn("delete listview.link_field_title_fields.program_offering", script)
