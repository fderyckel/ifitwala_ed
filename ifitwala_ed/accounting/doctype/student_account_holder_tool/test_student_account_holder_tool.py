import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.accounting.test_support import AccountingTestMixin


class TestStudentAccountHolderTool(AccountingTestMixin, FrappeTestCase):
    def _make_guardian(self, organization, *, financial=1):
        seed = frappe.generate_hash(length=8)
        guardian = frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_first_name": "Billing",
                "guardian_last_name": f"Guardian {seed}",
                "guardian_email": f"billing-guardian-{seed}@example.com",
                "guardian_mobile_phone": "+14155550123",
                "organization": organization,
                "is_financial_guardian": financial,
            }
        )
        guardian.insert(ignore_permissions=True)
        return guardian

    def test_tool_groups_siblings_and_creates_one_account_holder(self):
        organization = self.make_organization("Tool")
        offering = self.make_program_offering(organization.name)
        academic_year = self.get_program_offering_academic_year(offering.name)
        school = frappe.db.get_value("Program Offering", offering.name, "school")
        first_student = self.make_student(organization.name, "", school=school, prefix="Sibling A")
        second_student = self.make_student(organization.name, "", school=school, prefix="Sibling B")
        guardian = self._make_guardian(organization.name, financial=1)
        self.make_program_enrollment(
            organization=organization.name,
            program_offering=offering.name,
            student=first_student.name,
            academic_year=academic_year,
        )
        first_student.reload()

        first_student.append("siblings", {"student": second_student.name})
        first_student.append("guardians", {"guardian": guardian.name, "relation": "Mother", "can_consent": 1})
        first_student.save(ignore_permissions=True)

        tool = frappe.get_doc(
            {
                "doctype": "Student Account Holder Tool",
                "organization": organization.name,
                "program_offering": offering.name,
                "academic_year": academic_year,
            }
        ).insert(ignore_permissions=True)

        load_summary = tool.load_students()
        tool.reload()

        self.assertEqual(load_summary["loaded_count"], 2)
        family_keys = {row.family_group_key for row in tool.students}
        self.assertEqual(len(family_keys), 1)
        self.assertEqual({row.action for row in tool.students}, {"Create New Account Holder"})

        result = tool.create_account_holders()
        first_student.reload()
        second_student.reload()

        self.assertEqual(result["created_count"], 1)
        self.assertEqual(result["linked_count"], 2)
        self.assertTrue(first_student.account_holder)
        self.assertEqual(first_student.account_holder, second_student.account_holder)

    def test_tool_links_missing_sibling_to_existing_family_account_holder(self):
        organization = self.make_organization("Tool Existing AH")
        account_holder = self.make_account_holder(organization.name)
        offering = self.make_program_offering(organization.name)
        academic_year = self.get_program_offering_academic_year(offering.name)
        school = frappe.db.get_value("Program Offering", offering.name, "school")
        first_student = self.make_student(
            organization.name,
            account_holder.name,
            school=school,
            prefix="Existing AH Sibling",
        )
        second_student = self.make_student(organization.name, "", school=school, prefix="Missing AH Sibling")
        self.make_program_enrollment(
            organization=organization.name,
            program_offering=offering.name,
            student=second_student.name,
            academic_year=academic_year,
        )

        first_student.append("siblings", {"student": second_student.name})
        first_student.save(ignore_permissions=True)

        tool = frappe.get_doc(
            {
                "doctype": "Student Account Holder Tool",
                "organization": organization.name,
                "program_offering": offering.name,
                "academic_year": academic_year,
            }
        ).insert(ignore_permissions=True)

        load_summary = tool.load_students()
        tool.reload()

        self.assertEqual(load_summary["loaded_count"], 1)
        self.assertEqual(tool.students[0].action, "Link Existing Account Holder")
        self.assertEqual(tool.students[0].existing_account_holder, account_holder.name)

        result = tool.create_account_holders()
        second_student.reload()

        self.assertEqual(result["created_count"], 0)
        self.assertEqual(result["linked_count"], 1)
        self.assertEqual(second_student.account_holder, account_holder.name)
