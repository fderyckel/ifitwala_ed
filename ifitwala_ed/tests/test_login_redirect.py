# ifitwala_ed/tests/test_login_redirect.py
import frappe
from frappe.tests.utils import FrappeTestCase
from ifitwala_ed.api.users import redirect_user_to_entry_portal

class TestLoginRedirect(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.create_test_users()

    def create_test_users(self):
        # Create a Student user
        self.student = "test_student@example.com"
        if not frappe.db.exists("User", self.student):
            user = frappe.new_doc("User")
            user.email = self.student
            user.first_name = "Test"
            user.last_name = "Student"
            user.enabled = 1
            user.save()
            user.add_roles("Student")
        
        # Create a Staff user
        self.staff = "test_staff@example.com"
        if not frappe.db.exists("User", self.staff):
            user = frappe.new_doc("User")
            user.email = self.staff
            user.first_name = "Test"
            user.last_name = "Staff"
            user.enabled = 1
            user.save()
            user.add_roles("Employee", "Teacher")
            
            # Create active Employee record
            if not frappe.db.exists("Employee", {"user_id": self.staff}):
                emp = frappe.new_doc("Employee")
                emp.first_name = "Test"
                emp.last_name = "Staff"
                emp.user_id = self.staff
                emp.status = "Active"
                emp.employment_status = "Active"
                # Mock mandatory fields if any...
                emp.save(ignore_permissions=True)

    def test_student_redirect(self):
        frappe.set_user(self.student)
        
        # Clear response
        frappe.local.response = {}
        
        # Run redirect
        redirect_user_to_entry_portal()
        
        # Check response
        self.assertEqual(frappe.local.response.get("home_page"), "/portal/student")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/student")
        
        # Verify DB was NOT written (home_page should remain empty or default)
        db_home_page = frappe.db.get_value("User", self.student, "home_page")
        self.assertNotEqual(db_home_page, "/portal/student", "Should not persist home_page to DB")

    def test_staff_redirect(self):
        frappe.set_user(self.staff)
        
        frappe.local.response = {}
        redirect_user_to_entry_portal()
        
        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

    def tearDown(self):
        frappe.set_user("Administrator")
