from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.api.teaching_plans_test_support import _teaching_plans_module


class TestTeachingPlansMutations(TestCase):
    def test_create_class_teaching_plan_defaults_to_active_status(self):
        with _teaching_plans_module() as module:
            created = SimpleNamespace(
                name="CLASS-PLAN-1",
                course_plan=None,
                student_group=None,
                planning_status=None,
            )

            def _insert(ignore_permissions=False):
                created.insert_ignore_permissions = ignore_permissions
                return created

            created.insert = _insert

            with (
                patch.object(module, "_assert_staff_group_access", return_value=None),
                patch.object(module, "_group_context", return_value={"course": "COURSE-1"}),
                patch.object(
                    module.planning,
                    "get_course_plan_row",
                    return_value={"name": "COURSE-PLAN-1", "course": "COURSE-1"},
                ),
                patch.object(module.frappe, "new_doc", return_value=created),
            ):
                payload = module.create_class_teaching_plan("GROUP-1", "COURSE-PLAN-1")

        self.assertEqual(created.course_plan, "COURSE-PLAN-1")
        self.assertEqual(created.student_group, "GROUP-1")
        self.assertEqual(created.planning_status, "Active")
        self.assertTrue(created.insert_ignore_permissions)
        self.assertEqual(
            payload,
            {
                "class_teaching_plan": "CLASS-PLAN-1",
                "student_group": "GROUP-1",
            },
        )

    def test_create_course_plan_creates_shared_plan_for_allowed_course(self):
        with _teaching_plans_module() as module:
            inserted = {"count": 0}

            class CoursePlanDoc:
                def __init__(self):
                    self.name = "COURSE-PLAN-1"
                    self.course = None
                    self.title = None
                    self.academic_year = None
                    self.cycle_label = None
                    self.plan_status = "Draft"
                    self.summary = None

                def insert(self, ignore_permissions=False):
                    inserted["count"] += 1
                    inserted["ignore_permissions"] = ignore_permissions

            doc = CoursePlanDoc()

            with (
                patch.object(module.frappe, "get_roles", return_value=["Instructor"]),
                patch.object(module.planning, "get_curriculum_manageable_course_names", return_value=["COURSE-1"]),
                patch.object(module, "_validate_course_plan_academic_year"),
                patch.object(
                    module.frappe,
                    "get_all",
                    return_value=[
                        {
                            "name": "COURSE-1",
                            "course_name": "Biology",
                            "course_group": "Science",
                            "school": "SCH-1",
                            "status": "Active",
                        }
                    ],
                ),
                patch.object(module.frappe, "new_doc", return_value=doc),
            ):
                payload = module.create_course_plan(
                    {
                        "course": "COURSE-1",
                        "academic_year": "2026-2027",
                        "cycle_label": "Semester 1",
                        "summary": "Shared scope and sequence",
                    }
                )

        self.assertEqual(doc.course, "COURSE-1")
        self.assertEqual(doc.title, "Biology Plan")
        self.assertEqual(doc.academic_year, "2026-2027")
        self.assertEqual(doc.cycle_label, "Semester 1")
        self.assertEqual(doc.summary, "Shared scope and sequence")
        self.assertEqual(inserted["count"], 1)
        self.assertEqual(payload["course_plan"], "COURSE-PLAN-1")
        self.assertEqual(payload["course"], "COURSE-1")

    def test_create_course_plan_rejects_users_without_shared_plan_permission(self):
        with _teaching_plans_module() as module:
            with self.assertRaises(module.frappe.PermissionError):
                module.create_course_plan({"course": "COURSE-1"})

    def test_save_course_plan_updates_governed_fields(self):
        with _teaching_plans_module() as module:
            saved = {"count": 0}

            class CoursePlanDoc:
                def __init__(self):
                    self.name = "COURSE-PLAN-1"
                    self.course = "COURSE-1"
                    self.school = "SCH-1"
                    self.title = "Old title"
                    self.academic_year = None
                    self.cycle_label = None
                    self.plan_status = "Draft"
                    self.summary = None

                def check_permission(self, ptype):
                    self.checked = ptype

                def save(self, ignore_permissions=False):
                    saved["count"] += 1
                    saved["ignore_permissions"] = ignore_permissions

            doc = CoursePlanDoc()

            with (
                patch.object(module, "_validate_course_plan_academic_year"),
                patch.object(module.frappe, "get_doc", return_value=doc),
            ):
                payload = module.save_course_plan(
                    {
                        "course_plan": "COURSE-PLAN-1",
                        "title": "Biology Plan",
                        "academic_year": "2026-2027",
                        "cycle_label": "Semester 1",
                        "plan_status": "Active",
                        "summary": "Shared scope and sequence",
                    }
                )

        self.assertEqual(doc.title, "Biology Plan")
        self.assertEqual(doc.plan_status, "Active")
        self.assertEqual(saved["count"], 1)
        self.assertEqual(payload["course_plan"], "COURSE-PLAN-1")

    def test_save_course_plan_sanitizes_summary_rich_text(self):
        with _teaching_plans_module() as module:

            class CoursePlanDoc:
                def __init__(self):
                    self.name = "COURSE-PLAN-1"
                    self.course = "COURSE-1"
                    self.school = "SCH-1"
                    self.modified = "2026-04-02 09:00:00"
                    self.summary = None

                def save(self, ignore_permissions=False):
                    return None

            doc = CoursePlanDoc()

            with (
                patch.object(module, "_validate_course_plan_academic_year"),
                patch.object(module.frappe, "get_doc", return_value=doc),
            ):
                module.save_course_plan(
                    {
                        "course_plan": "COURSE-PLAN-1",
                        "title": "Biology Plan",
                        "summary": "<h2>Overview</h2><script>alert(1)</script>",
                    }
                )

        self.assertEqual(doc.summary, "<h2>Overview</h2>")

    def test_save_course_plan_rejects_stale_expected_modified(self):
        with _teaching_plans_module() as module:

            class CoursePlanDoc:
                def __init__(self):
                    self.name = "COURSE-PLAN-1"
                    self.course = "COURSE-1"
                    self.school = "SCH-1"
                    self.modified = "2026-04-02 09:00:00"

                def save(self, ignore_permissions=False):
                    raise AssertionError("save() must not run after a stale expected_modified check.")

            with self.assertRaises(module.frappe.ValidationError):
                with (
                    patch.object(module, "_validate_course_plan_academic_year"),
                    patch.object(module.frappe, "get_doc", return_value=CoursePlanDoc()),
                ):
                    module.save_course_plan(
                        {
                            "course_plan": "COURSE-PLAN-1",
                            "title": "Biology Plan",
                            "expected_modified": "2026-04-02 08:00:00",
                        }
                    )

    def test_save_course_plan_rejects_academic_year_outside_course_school_scope(self):
        with _teaching_plans_module() as module:
            with self.assertRaises(module.frappe.ValidationError):
                with (
                    patch.object(module, "_academic_year_scope_for_school", return_value=["SCH-1"]),
                    patch.object(
                        module.frappe.db,
                        "get_value",
                        return_value={"name": "2026-2027", "school": "SCH-OTHER"},
                    ),
                ):
                    module._validate_course_plan_academic_year(
                        course_school="SCH-1",
                        academic_year="2026-2027",
                    )

    def test_save_unit_plan_creates_new_unit_with_child_rows(self):
        with _teaching_plans_module() as module:
            inserted = {"count": 0}

            class FakeUnitDoc:
                def __init__(self):
                    self.name = "UNIT-PLAN-NEW"
                    self.course_plan = None
                    self.title = None
                    self.program = None
                    self.unit_code = None
                    self.unit_order = None
                    self.unit_status = "Draft"
                    self.version = None
                    self.duration = None
                    self.estimated_duration = None
                    self.is_published = 0
                    self.overview = None
                    self.essential_understanding = None
                    self.misconceptions = None
                    self.content = None
                    self.skills = None
                    self.concepts = None
                    self.standards = []
                    self.reflections = []

                def set(self, fieldname, value):
                    setattr(self, fieldname, value)

                def is_new(self):
                    return True

                def insert(self, ignore_permissions=False):
                    inserted["count"] += 1
                    inserted["ignore_permissions"] = ignore_permissions

            course_plan_doc = SimpleNamespace(check_permission=lambda ptype: None)
            unit_doc = FakeUnitDoc()

            def fake_get_doc(doctype, name):
                if doctype == "Course Plan":
                    return course_plan_doc
                raise AssertionError(f"Unexpected get_doc call: {doctype} {name}")

            with (
                patch.object(module, "_validate_course_program_link"),
                patch.object(module.planning, "ensure_linked_unit_plan_standards"),
                patch.object(module.frappe, "get_doc", side_effect=fake_get_doc),
                patch.object(module.frappe, "new_doc", return_value=unit_doc),
            ):
                payload = module.save_unit_plan(
                    {
                        "course_plan": "COURSE-PLAN-1",
                        "title": "Cells and Systems",
                        "unit_order": 10,
                        "is_published": 1,
                        "overview": "Shared unit overview",
                        "standards_json": [{"standard_code": "STD-1"}],
                        "reflections_json": [{"prior_to_the_unit": "Start with microscope norms."}],
                    }
                )

        self.assertEqual(unit_doc.course_plan, "COURSE-PLAN-1")
        self.assertEqual(unit_doc.title, "Cells and Systems")
        self.assertEqual(unit_doc.is_published, 1)
        self.assertEqual(unit_doc.standards, [{"standard_code": "STD-1"}])
        self.assertEqual(
            unit_doc.reflections,
            [
                {
                    "academic_year": "2026-2027",
                    "school": "SCH-1",
                    "prior_to_the_unit": "Start with microscope norms.",
                    "during_the_unit": None,
                    "what_work_well": None,
                    "what_didnt_work_well": None,
                    "changes_suggestions": None,
                }
            ],
        )
        self.assertEqual(inserted["count"], 1)
        self.assertEqual(payload["unit_plan"], "UNIT-PLAN-NEW")

    def test_save_unit_plan_sanitizes_rich_text_fields_and_reflections(self):
        with _teaching_plans_module() as module:

            class FakeUnitDoc:
                def __init__(self):
                    self.name = "UNIT-PLAN-NEW"
                    self.course_plan = None
                    self.title = None
                    self.program = None
                    self.unit_order = None
                    self.is_published = 0
                    self.overview = None
                    self.reflections = []

                def set(self, fieldname, value):
                    setattr(self, fieldname, value)

                def is_new(self):
                    return True

                def insert(self, ignore_permissions=False):
                    return None

            unit_doc = FakeUnitDoc()

            with (
                patch.object(module, "_validate_course_program_link"),
                patch.object(module.planning, "ensure_linked_unit_plan_standards"),
                patch.object(
                    module.frappe,
                    "get_doc",
                    return_value=SimpleNamespace(check_permission=lambda ptype: None),
                ),
                patch.object(module.frappe, "new_doc", return_value=unit_doc),
            ):
                module.save_unit_plan(
                    {
                        "course_plan": "COURSE-PLAN-1",
                        "title": "Cells and Systems",
                        "overview": "<h2>Unit overview</h2><script>alert(1)</script>",
                        "reflections_json": [
                            {
                                "prior_to_the_unit": "<p>Start here</p><script>alert(1)</script>",
                            }
                        ],
                    }
                )

        self.assertEqual(unit_doc.overview, "<h2>Unit overview</h2>")
        self.assertEqual(unit_doc.reflections[0]["prior_to_the_unit"], "<p>Start here</p>")

    def test_save_unit_plan_rejects_stale_expected_modified(self):
        with _teaching_plans_module() as module:

            class FakeUnitDoc:
                def __init__(self):
                    self.name = "UNIT-PLAN-1"
                    self.course_plan = "COURSE-PLAN-1"
                    self.modified = "2026-04-02 09:00:00"

                def get_db_value(self, fieldname):
                    return None

                def save(self, ignore_permissions=False):
                    raise AssertionError("save() must not run after a stale expected_modified check.")

            def fake_get_doc(doctype, name):
                if doctype == "Unit Plan":
                    return FakeUnitDoc()
                if doctype == "Course Plan":
                    return SimpleNamespace(check_permission=lambda ptype: None)
                raise AssertionError(f"Unexpected get_doc call: {doctype} {name}")

            with self.assertRaises(module.frappe.ValidationError):
                with patch.object(module.frappe, "get_doc", side_effect=fake_get_doc):
                    module.save_unit_plan(
                        {
                            "unit_plan": "UNIT-PLAN-1",
                            "title": "Cells and Systems",
                            "expected_modified": "2026-04-02 08:00:00",
                        }
                    )

    def test_validate_course_program_link_rejects_unlinked_program(self):
        with _teaching_plans_module() as module:
            with self.assertRaises(module.frappe.ValidationError):
                with (
                    patch.object(
                        module.frappe.db,
                        "get_value",
                        return_value={"name": "MYP", "archive": 0},
                    ),
                    patch.object(
                        module.frappe.db,
                        "exists",
                        return_value=False,
                    ),
                ):
                    module._validate_course_program_link(course="COURSE-1", program="MYP")

    def test_validate_course_program_link_rejects_archived_program(self):
        with _teaching_plans_module() as module:
            with self.assertRaises(module.frappe.ValidationError):
                with patch.object(
                    module.frappe.db,
                    "get_value",
                    return_value={"name": "MYP", "archive": 1},
                ):
                    module._validate_course_program_link(course="COURSE-1", program="MYP")

    def test_create_planning_reference_material_uses_class_owned_origin(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "_resolve_planning_resource_anchor",
                    return_value={"anchor_doctype": "Class Teaching Plan", "anchor_name": "CLASS-PLAN-1"},
                ),
                patch.object(
                    module.materials_domain,
                    "resolve_material_origin",
                    return_value="shared_in_class",
                ),
                patch.object(
                    module.materials_domain,
                    "create_reference_material",
                    return_value=(SimpleNamespace(name="MAT-1"), SimpleNamespace(name="MAT-PLC-1")),
                ) as create_reference_material,
                patch.object(
                    module,
                    "_reload_anchor_material",
                    return_value={
                        "material": "MAT-1",
                        "title": "Starter article",
                        "attachment": {"surface": "planning.material"},
                    },
                ) as reload_anchor_material,
            ):
                payload = module.create_planning_reference_material(
                    {
                        "anchor_doctype": "Class Teaching Plan",
                        "anchor_name": "CLASS-PLAN-1",
                        "title": "Starter article",
                        "reference_url": "https://example.com/article",
                    }
                )

        self.assertEqual(payload["placement"], "MAT-PLC-1")
        self.assertEqual(payload["resource"]["attachment"]["surface"], "planning.material")
        reload_anchor_material.assert_called_once_with(
            "Class Teaching Plan",
            "CLASS-PLAN-1",
            "MAT-1",
            attachment_surface="planning.material",
        )
        create_reference_material.assert_called_once_with(
            anchor_doctype="Class Teaching Plan",
            anchor_name="CLASS-PLAN-1",
            title="Starter article",
            reference_url="https://example.com/article",
            description=None,
            modality=None,
            usage_role=None,
            placement_note=None,
            origin="shared_in_class",
        )

    def test_remove_planning_material_deletes_anchor_placement(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "_resolve_planning_resource_anchor",
                    return_value={"anchor_doctype": "Class Session", "anchor_name": "CLASS-SESSION-1"},
                ),
                patch.object(
                    module.materials_domain,
                    "delete_anchor_material_placement",
                ) as delete_placement,
            ):
                payload = module.remove_planning_material(
                    {
                        "anchor_doctype": "Class Session",
                        "anchor_name": "CLASS-SESSION-1",
                        "placement": "MAT-PLC-1",
                    }
                )

        self.assertEqual(payload["removed"], 1)
        delete_placement.assert_called_once_with(
            "MAT-PLC-1",
            anchor_doctype="Class Session",
            anchor_name="CLASS-SESSION-1",
        )
