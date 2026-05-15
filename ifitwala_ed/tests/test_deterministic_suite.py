from __future__ import annotations

import frappe

from ifitwala_ed.tests.base import IfitwalaEdTestSuite
from ifitwala_ed.tests.bootstrap import TEST_GRADE_SCALE

SCENARIO_GRADE_SCALE = "_Test Ifitwala Scenario Grade Scale"


class TestDeterministicSuite(IfitwalaEdTestSuite):
    def test_bootstrap_records_are_available(self):
        self.assertTrue(frappe.db.exists("Organization", self.bootstrap.organization))
        self.assertTrue(frappe.db.exists("School", self.bootstrap.root_school))
        self.assertTrue(frappe.db.exists("School", self.bootstrap.child_school))
        self.assertTrue(frappe.db.exists("Academic Year", self.bootstrap.academic_year))
        self.assertTrue(frappe.db.exists("Term", self.bootstrap.term))
        self.assertEqual(self.bootstrap.grade_scale, TEST_GRADE_SCALE)
        self.assertTrue(frappe.db.exists("Grade Scale", self.bootstrap.grade_scale))

    def test_scenario_records_are_transactional(self):
        self.assertFalse(frappe.db.exists("Grade Scale", SCENARIO_GRADE_SCALE))

        doc = frappe.get_doc(
            {
                "doctype": "Grade Scale",
                "grade_scale_name": SCENARIO_GRADE_SCALE,
                "maximum_grade": 100,
            }
        )
        doc.insert(ignore_permissions=True)

        self.assertTrue(frappe.db.exists("Grade Scale", SCENARIO_GRADE_SCALE))
