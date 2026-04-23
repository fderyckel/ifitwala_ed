# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.curriculum import materials as materials_domain
from ifitwala_ed.curriculum.doctype.course_plan.course_plan import (
    ACTIVATION_MODE_ACADEMIC_YEAR_START,
    activate_due_course_plan_rollovers,
    create_rollover_course_plan,
)
from ifitwala_ed.tests.factories.organization import make_organization, make_school


class TestCoursePlan(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.organization = make_organization(prefix="Course Plan Org")
        self.school = make_school(self.organization.name, prefix="Course Plan School")
        self.course = frappe.get_doc(
            {
                "doctype": "Course",
                "course_name": f"Biology {frappe.generate_hash(length=6)}",
                "school": self.school.name,
            }
        ).insert(ignore_permissions=True)

    def test_rollover_creation_duplicates_units_and_shared_materials(self):
        source_ay = self._make_academic_year("2025-2026", "2025-08-01", "2026-06-30")
        target_ay = self._make_academic_year("2026-2027", "2026-08-01", "2027-06-30")
        standard = frappe.get_doc(
            {
                "doctype": "Learning Standards",
                "framework_name": "NGSS",
                "strand": "Life Science",
                "standard_code": f"LS-{frappe.generate_hash(length=5)}",
                "standard_description": "Model how cells function in living systems.",
                "alignment_type": "Knowledge",
            }
        ).insert(ignore_permissions=True)

        source_plan = frappe.get_doc(
            {
                "doctype": "Course Plan",
                "title": f"Biology Plan {frappe.generate_hash(length=4)}",
                "course": self.course.name,
                "academic_year": source_ay.name,
                "plan_status": "Active",
                "summary": "<p>Shared scope and sequence.</p>",
            }
        ).insert(ignore_permissions=True)
        source_unit = frappe.get_doc(
            {
                "doctype": "Unit Plan",
                "course_plan": source_plan.name,
                "title": f"Cells {frappe.generate_hash(length=4)}",
                "unit_status": "Active",
                "duration": "4",
                "is_published": 1,
                "overview": "<p>Students investigate the structure and function of cells.</p>",
                "standards": [
                    {
                        "learning_standard": standard.name,
                        "coverage_level": "Introduced",
                        "alignment_strength": "Exact",
                    }
                ],
                "reflections": [
                    {
                        "academic_year": source_ay.name,
                        "school": self.school.name,
                        "what_work_well": "<p>Lab sequence landed well.</p>",
                    }
                ],
            }
        ).insert(ignore_permissions=True)

        materials_domain.create_reference_material(
            anchor_doctype="Course Plan",
            anchor_name=source_plan.name,
            title="Course Overview Slides",
            reference_url="https://example.com/course-overview",
        )
        materials_domain.create_reference_material(
            anchor_doctype="Unit Plan",
            anchor_name=source_unit.name,
            title="Microscope Notes",
            reference_url="https://example.com/microscope-notes",
        )

        payload = create_rollover_course_plan(
            course_plan=source_plan.name,
            target_academic_year=target_ay.name,
            activation_mode=ACTIVATION_MODE_ACADEMIC_YEAR_START,
            copy_plan_resources=1,
            copy_unit_resources=1,
        )

        target_plan = frappe.get_doc("Course Plan", payload["course_plan"])
        target_units = frappe.get_all(
            "Unit Plan",
            filters={"course_plan": target_plan.name},
            fields=["name", "unit_status", "is_published"],
            limit=0,
        )
        self.assertEqual(target_plan.plan_status, "Draft")
        self.assertEqual(target_plan.activation_mode, ACTIVATION_MODE_ACADEMIC_YEAR_START)
        self.assertEqual(target_plan.rollover_source_course_plan, source_plan.name)
        self.assertEqual(payload["units_created"], 1)
        self.assertEqual(payload["plan_resources_copied"], 1)
        self.assertEqual(payload["unit_resources_copied"], 1)
        self.assertEqual(len(target_units), 1)
        self.assertEqual(target_units[0]["unit_status"], "Draft")
        self.assertEqual(target_units[0]["is_published"], 0)

        target_unit = frappe.get_doc("Unit Plan", target_units[0]["name"])
        self.assertEqual(len(target_unit.standards), 1)
        self.assertEqual(target_unit.standards[0].learning_standard, standard.name)
        self.assertEqual(len(target_unit.reflections), 0)
        self.assertEqual(
            frappe.db.count("Material Placement", {"anchor_doctype": "Course Plan", "anchor_name": target_plan.name}),
            1,
        )
        self.assertEqual(
            frappe.db.count("Material Placement", {"anchor_doctype": "Unit Plan", "anchor_name": target_unit.name}),
            1,
        )

    def test_only_one_active_course_plan_allowed_per_course_and_academic_year(self):
        academic_year = self._make_academic_year("2026-2027", "2026-08-01", "2027-06-30")
        frappe.get_doc(
            {
                "doctype": "Course Plan",
                "title": f"Primary Plan {frappe.generate_hash(length=4)}",
                "course": self.course.name,
                "academic_year": academic_year.name,
                "plan_status": "Active",
            }
        ).insert(ignore_permissions=True)

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Course Plan",
                    "title": f"Duplicate Plan {frappe.generate_hash(length=4)}",
                    "course": self.course.name,
                    "academic_year": academic_year.name,
                    "plan_status": "Active",
                }
            ).insert(ignore_permissions=True)

    def test_daily_activation_sweep_activates_due_rollover_plans_only(self):
        due_ay = self._make_academic_year("2026-2027", "2020-08-01", "2021-06-30")
        future_ay = self._make_academic_year("2027-2028", "2999-08-01", "3000-06-30")
        due_plan = frappe.get_doc(
            {
                "doctype": "Course Plan",
                "title": f"Due Plan {frappe.generate_hash(length=4)}",
                "course": self.course.name,
                "academic_year": due_ay.name,
                "plan_status": "Draft",
                "activation_mode": ACTIVATION_MODE_ACADEMIC_YEAR_START,
            }
        ).insert(ignore_permissions=True)
        future_plan = frappe.get_doc(
            {
                "doctype": "Course Plan",
                "title": f"Future Plan {frappe.generate_hash(length=4)}",
                "course": self.course.name,
                "academic_year": future_ay.name,
                "plan_status": "Draft",
                "activation_mode": ACTIVATION_MODE_ACADEMIC_YEAR_START,
            }
        ).insert(ignore_permissions=True)

        summary = activate_due_course_plan_rollovers()

        self.assertEqual(summary["activated_count"], 1)
        self.assertEqual(frappe.db.get_value("Course Plan", due_plan.name, "plan_status"), "Active")
        self.assertEqual(frappe.db.get_value("Course Plan", future_plan.name, "plan_status"), "Draft")

    def _make_academic_year(self, academic_year_name: str, start_date: str, end_date: str):
        return frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": academic_year_name,
                "school": self.school.name,
                "year_start_date": start_date,
                "year_end_date": end_date,
                "archived": 0,
                "visible_to_admission": 1,
            }
        ).insert(ignore_permissions=True)
