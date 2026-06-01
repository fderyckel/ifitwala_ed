from pathlib import Path
from unittest import TestCase


class TestStudentAccountHolderToolListView(TestCase):
    def test_list_view_strips_generated_program_offering_title_join(self):
        script = Path(__file__).with_name("student_account_holder_tool_list.js").read_text()

        self.assertRegex(script, r"frappe\.listview_settings\[['\"]Student Account Holder Tool['\"]\]")
        self.assertIn("program_offering.offering_title as program_offering_offering_title", script)
        self.assertIn("delete listview.link_field_title_fields.program_offering", script)

    def test_form_calls_module_level_whitelisted_methods(self):
        script = Path(__file__).with_name("student_account_holder_tool.js").read_text()

        self.assertIn(
            "ifitwala_ed.accounting.doctype.student_account_holder_tool.student_account_holder_tool.load_students",
            script,
        )
        self.assertIn(
            "ifitwala_ed.accounting.doctype.student_account_holder_tool.student_account_holder_tool.create_account_holders",
            script,
        )
        self.assertIn("args: { name: frm.doc.name }", script)

    def test_module_exposes_button_command_wrappers(self):
        module = Path(__file__).with_name("student_account_holder_tool.py").read_text()

        self.assertIn("def load_students(name: str | None = None, doc=None)", module)
        self.assertIn("def create_account_holders(name: str | None = None, doc=None)", module)
        self.assertIn("def _get_tool_doc_for_action", module)
