# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/schedule/doctype/end_of_year_checklist/test_end_of_year_checklist.py

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEndofYearChecklist(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []
        seed = frappe.generate_hash(length=4).upper()
        self.org = self._create_org()
        self.root_school = self._create_school(f"Root School {seed}", f"R{seed}", self.org, is_group=1)
        self.child_school = self._create_school(
            f"Child School {seed}",
            f"C{seed}",
            self.org,
            parent=self.root_school,
            is_group=1,
        )
        self.leaf_school = self._create_school(
            f"Leaf School {seed}", f"L{seed}", self.org, parent=self.child_school, is_group=0
        )
        self.sibling_school = self._create_school(
            f"Sibling School {seed}",
            f"S{seed}",
            self.org,
            parent=self.root_school,
            is_group=0,
        )

        self.ay_name = "2025-2026"
        self.root_ay = self._create_academic_year(self.root_school, self.ay_name)
        self.child_ay = self._create_academic_year(self.child_school, self.ay_name)
        self.leaf_ay = self._create_academic_year(self.leaf_school, self.ay_name)
        self.sibling_ay = self._create_academic_year(self.sibling_school, self.ay_name)

        self.root_term = self._create_term(self.root_ay, "Root Term")
        self.child_term = self._create_term(self.child_ay, "Child Term")
        self.leaf_term = self._create_term(self.leaf_ay, "Leaf Term")

        self.program = self._create_program()
        self.root_offering = self._create_program_offering(self.program, self.sibling_school, self.root_ay)
        self.child_offering = self._create_program_offering(self.program, self.leaf_school, self.child_ay)
        self.leaf_offering = self._create_program_offering(self.program, self.leaf_school, self.leaf_ay)

        self.root_student = self._create_student("Root")
        self.child_student = self._create_student("Child")
        self.leaf_student = self._create_student("Leaf")
        self.root_enrollment = self._create_program_enrollment(self.root_student, self.root_offering, self.root_ay)
        self.child_enrollment = self._create_program_enrollment(self.child_student, self.child_offering, self.child_ay)
        self.leaf_enrollment = self._create_program_enrollment(self.leaf_student, self.leaf_offering, self.leaf_ay)

        self.root_group = self._create_student_group(self.root_offering, self.root_ay, "SGR")
        self.child_group = self._create_student_group(self.child_offering, self.child_ay, "SGC")
        self.leaf_group = self._create_student_group(self.leaf_offering, self.leaf_ay, "SGL")

    def tearDown(self):
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_leaf_closure_affects_only_leaf(self):
        checklist = frappe.get_single("End of Year Checklist")
        checklist.school = self.leaf_school
        checklist.academic_year = self.leaf_ay
        checklist.status = "In Progress"
        checklist.save(ignore_permissions=True)

        checklist.archive_academic_year()
        checklist.archive_terms()
        checklist.archive_program_enrollment()
        checklist.archive_student_groups()

        self.assertEqual(frappe.db.get_value("Academic Year", self.leaf_ay, "archived"), 1)
        self.assertEqual(frappe.db.get_value("Academic Year", self.leaf_ay, "visible_to_admission"), 0)
        self.assertEqual(frappe.db.get_value("Academic Year", self.root_ay, "archived"), 0)

        self.assertEqual(frappe.db.get_value("Term", self.leaf_term, "archived"), 1)
        self.assertEqual(frappe.db.get_value("Program Enrollment", self.leaf_enrollment, "archived"), 1)
        self.assertEqual(frappe.db.get_value("Student Group", self.leaf_group, "status"), "Retired")

        self.assertEqual(frappe.db.get_value("Term", self.child_term, "archived"), 0)
        self.assertEqual(frappe.db.get_value("Program Enrollment", self.child_enrollment, "archived"), 0)
        self.assertEqual(frappe.db.get_value("Student Group", self.child_group, "status"), "Active")

    def test_parent_closure_cascades(self):
        checklist = frappe.get_single("End of Year Checklist")
        checklist.school = self.root_school
        checklist.academic_year = self.root_ay
        checklist.status = "In Progress"
        checklist.save(ignore_permissions=True)

        checklist.archive_academic_year()

        self.assertEqual(frappe.db.get_value("Academic Year", self.root_ay, "archived"), 1)
        self.assertEqual(frappe.db.get_value("Academic Year", self.child_ay, "archived"), 1)
        self.assertEqual(frappe.db.get_value("Academic Year", self.leaf_ay, "archived"), 1)

    def test_idempotent_reexecution(self):
        checklist = frappe.get_single("End of Year Checklist")
        checklist.school = self.child_school
        checklist.academic_year = self.child_ay
        checklist.status = "In Progress"
        checklist.save(ignore_permissions=True)

        checklist.archive_program_enrollment()
        checklist.archive_program_enrollment()
        self.assertEqual(frappe.db.get_value("Program Enrollment", self.child_enrollment, "archived"), 1)

    def test_unauthorized_parent_selection_blocked(self):
        user = self._create_user("eoy_user@example.com")
        frappe.defaults.set_user_default("school", self.child_school, user=user)
        frappe.set_user(user)

        checklist = frappe.get_single("End of Year Checklist")
        checklist.school = self.root_school
        checklist.academic_year = self.root_ay
        checklist.status = "In Progress"
        with self.assertRaises(frappe.ValidationError):
            checklist.save(ignore_permissions=True)

        frappe.set_user("Administrator")

    def _create_org(self):
        name = f"Org-{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": name,
                "abbr": name[:6].upper(),
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", doc.name))
        return doc.name

    def _create_school(self, school_name, abbr, organization, parent=None, is_group=0):
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": school_name,
                "abbr": abbr,
                "organization": organization,
                "is_group": 1 if is_group else 0,
                "parent_school": parent,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", doc.name))
        return doc.name

    def _create_academic_year(self, school, academic_year_name):
        doc = frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": academic_year_name,
                "school": school,
                "archived": 0,
                "visible_to_admission": 1,
                "year_start_date": "2025-08-01",
                "year_end_date": "2026-06-30",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Academic Year", doc.name))
        return doc.name

    def _create_term(self, academic_year, term_name):
        doc = frappe.get_doc(
            {
                "doctype": "Term",
                "academic_year": academic_year,
                "term_name": term_name,
                "term_type": "Academic",
                "archived": 0,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Term", doc.name))
        return doc.name

    def _create_program(self):
        name = f"Program-{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Program", doc.name))
        return doc.name

    def _create_program_offering(self, program, school, academic_year):
        doc = frappe.get_doc(
            {
                "doctype": "Program Offering",
                "program": program,
                "school": school,
                "offering_academic_years": [{"academic_year": academic_year}],
                "status": "Active",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Program Offering", doc.name))
        return doc.name

    def _create_student(self, label):
        seed = frappe.generate_hash(length=6)
        prev_import = getattr(frappe.flags, "in_import", False)
        frappe.flags.in_import = True
        try:
            doc = frappe.get_doc(
                {
                    "doctype": "Student",
                    "student_first_name": label,
                    "student_last_name": f"Student{seed}",
                    "student_email": f"{label.lower()}{seed}@example.com",
                }
            ).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_import = prev_import
        self._created.append(("Student", doc.name))
        return doc.name

    def _create_program_enrollment(self, student, program_offering, academic_year):
        doc = frappe.get_doc(
            {
                "doctype": "Program Enrollment",
                "student": student,
                "program_offering": program_offering,
                "academic_year": academic_year,
                "enrollment_date": "2025-09-01",
                "enrollment_source": "Admin",
                "enrollment_override_reason": "EOY checklist test setup",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Program Enrollment", doc.name))
        return doc.name

    def _create_student_group(self, program_offering, academic_year, abbreviation):
        doc = frappe.get_doc(
            {
                "doctype": "Student Group",
                "program_offering": program_offering,
                "academic_year": academic_year,
                "group_based_on": "Pastoral",
                "student_group_abbreviation": abbreviation,
                "status": "Active",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Group", doc.name))
        return doc.name

    def _create_user(self, email):
        if frappe.db.exists("User", email):
            return email
        doc = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Eoy",
                "last_name": "User",
                "enabled": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", doc.name))
        return doc.name
