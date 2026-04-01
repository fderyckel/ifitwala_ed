from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _teaching_plans_module():
    student_groups_api = ModuleType("ifitwala_ed.api.student_groups")
    student_groups_api.TRIAGE_ROLES = set()
    student_groups_api._instructor_group_names = lambda user: []

    file_access_api = ModuleType("ifitwala_ed.api.file_access")
    file_access_api.resolve_academic_file_open_url = lambda **kwargs: "/open/resource"

    materials_domain = ModuleType("ifitwala_ed.curriculum.materials")
    materials_domain.MATERIAL_TYPE_FILE = "File"
    materials_domain.MATERIAL_CLASS_OWNED_ANCHORS = {"Class Teaching Plan", "Class Session"}
    materials_domain.list_materials_for_anchors = lambda anchor_refs: {}
    materials_domain.resolve_anchor_context = lambda anchor_doctype, anchor_name: {
        "anchor_doctype": anchor_doctype,
        "anchor_name": anchor_name,
        "student_group": "GROUP-1",
    }
    materials_domain.resolve_material_origin = lambda anchor_doctype: "shared_in_class"
    materials_domain.create_reference_material = lambda **kwargs: (
        SimpleNamespace(name="MAT-1"),
        SimpleNamespace(name="MAT-PLC-1"),
    )
    materials_domain.create_file_material_record = lambda **kwargs: SimpleNamespace(name="MAT-1")
    materials_domain.create_material_placement = lambda **kwargs: SimpleNamespace(name="MAT-PLC-1")
    materials_domain.delete_anchor_material_placement = lambda *args, **kwargs: None

    planning_domain = ModuleType("ifitwala_ed.curriculum.planning")
    planning_domain.normalize_text = lambda value: str(value or "").strip()
    planning_domain.normalize_long_text = lambda value: value
    planning_domain.normalize_flag = lambda value: 1 if str(value or "").strip() in {"1", "True", "true"} else 0
    planning_domain.get_course_plan_row = lambda course_plan: {
        "name": course_plan,
        "title": course_plan,
        "course": "COURSE-1",
        "school": "SCH-1",
        "academic_year": "2026-2027",
    }
    planning_domain.get_student_group_row = lambda student_group: {"name": student_group, "course": "COURSE-1"}
    planning_domain.get_unit_plan_rows = lambda course_plan: []
    planning_domain.replace_session_activities = lambda doc, activities: None
    planning_domain.replace_unit_plan_standards = lambda doc, rows: doc.set("standards", rows)
    planning_domain.replace_unit_plan_reflections = lambda doc, rows, course_plan_row=None: doc.set("reflections", rows)

    governed_uploads = ModuleType("ifitwala_ed.utilities.governed_uploads")
    governed_uploads.upload_supporting_material_file = lambda material: None

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.api.student_groups": student_groups_api,
            "ifitwala_ed.api.file_access": file_access_api,
            "ifitwala_ed.curriculum.materials": materials_domain,
            "ifitwala_ed.curriculum.planning": planning_domain,
            "ifitwala_ed.utilities.governed_uploads": governed_uploads,
        }
    ) as frappe:
        frappe.db.sql = lambda *args, **kwargs: []
        frappe.db.exists = lambda *args, **kwargs: False
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.get_all = lambda *args, **kwargs: []
        frappe.get_list = lambda *args, **kwargs: []
        yield import_fresh("ifitwala_ed.api.teaching_plans")


class TestTeachingPlansApi(TestCase):
    def test_build_unit_lookup_includes_shared_and_class_reflections_for_staff(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module.planning,
                    "get_unit_plan_rows",
                    return_value=[
                        {
                            "name": "UNIT-1",
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "overview": "Shared unit overview",
                            "essential_understanding": "Systems work together.",
                            "content": "Cells",
                            "skills": "Observe",
                            "concepts": "Systems",
                        }
                    ],
                ),
                patch.object(
                    module.frappe,
                    "get_all",
                    side_effect=[
                        [
                            {
                                "parent": "UNIT-1",
                                "standard_code": "STD-1",
                                "standard_description": "Explain how cells function.",
                                "coverage_level": "Introduced",
                            }
                        ],
                        [
                            {
                                "parent": "UNIT-1",
                                "academic_year": "2026-2027",
                                "prior_to_the_unit": "Shared reflection",
                            }
                        ],
                    ],
                ),
                patch.object(
                    module.frappe.db,
                    "sql",
                    return_value=[
                        {
                            "unit_plan": "UNIT-1",
                            "class_teaching_plan": "CLASS-PLAN-1",
                            "class_teaching_plan_title": "Biology A",
                            "student_group": "GROUP-1",
                            "academic_year": "2026-2027",
                            "student_group_name": "Biology A",
                            "student_group_abbreviation": "BIO-A",
                            "prior_to_the_unit": "Students needed microscope norms.",
                            "during_the_unit": "More modeling helped.",
                            "what_work_well": "Lab rotations",
                            "what_didnt_work_well": None,
                            "changes_suggestions": "Add more annotation examples.",
                        }
                    ],
                ),
            ):
                lookup = module._build_unit_lookup("COURSE-PLAN-1", audience="staff")

        self.assertEqual(lookup["UNIT-1"]["standards"][0]["standard_code"], "STD-1")
        self.assertEqual(lookup["UNIT-1"]["shared_reflections"][0]["prior_to_the_unit"], "Shared reflection")
        self.assertEqual(lookup["UNIT-1"]["class_reflections"][0]["class_label"], "Biology A")
        self.assertEqual(
            lookup["UNIT-1"]["class_reflections"][0]["changes_suggestions"],
            "Add more annotation examples.",
        )

    def test_serialize_backbone_units_hides_staff_only_reflections_from_students(self):
        with _teaching_plans_module() as module:
            with patch.object(
                module.frappe,
                "get_all",
                return_value=[
                    {
                        "unit_plan": "UNIT-1",
                        "unit_title": "Cells and Systems",
                        "unit_order": 10,
                        "governed_required": 1,
                        "pacing_status": "In Progress",
                        "teacher_focus": "Precision",
                        "pacing_note": "Slow down for lab setup",
                        "prior_to_the_unit": "Teacher-only",
                        "during_the_unit": "Teacher-only",
                        "what_work_well": "Teacher-only",
                        "what_didnt_work_well": "Teacher-only",
                        "changes_suggestions": "Teacher-only",
                    }
                ],
            ):
                payload = module._serialize_backbone_units(
                    "CLASS-PLAN-1",
                    {
                        "UNIT-1": {
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "overview": "Shared unit overview",
                            "essential_understanding": "Systems work together.",
                            "content": "Cells",
                            "skills": "Observe",
                            "concepts": "Systems",
                            "misconceptions": "Teacher-only misconception note",
                            "standards": [{"standard_code": "STD-1"}],
                            "shared_reflections": [{"prior_to_the_unit": "Teacher-only"}],
                            "class_reflections": [{"class_label": "Biology A"}],
                        }
                    },
                    audience="student",
                )

        self.assertEqual(payload[0]["overview"], "Shared unit overview")
        self.assertEqual(payload[0]["standards"][0]["standard_code"], "STD-1")
        self.assertNotIn("misconceptions", payload[0])
        self.assertNotIn("shared_reflections", payload[0])
        self.assertNotIn("class_reflections", payload[0])

    def test_build_staff_bundle_without_selected_plan_returns_empty_curriculum(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "_resolve_staff_plan",
                    return_value=(
                        {
                            "name": "GROUP-1",
                            "student_group_name": "Biology A",
                            "course": "COURSE-1",
                            "academic_year": "2025-2026",
                        },
                        [{"name": "COURSE-PLAN-1", "title": "Semester 1", "plan_status": "Active"}],
                        [],
                        None,
                    ),
                ),
                patch.object(module, "now_datetime") as now_datetime,
            ):
                now_datetime.return_value.isoformat.return_value = "2026-03-31 10:00:00"
                payload = module._build_staff_bundle("GROUP-1")

        self.assertIsNone(payload["teaching_plan"])
        self.assertEqual(payload["curriculum"]["units"], [])
        self.assertEqual(payload["curriculum"]["session_count"], 0)

    def test_fetch_class_sessions_hides_teacher_fields_for_students(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module.frappe,
                    "get_all",
                    return_value=[
                        {
                            "name": "CLASS-SESSION-1",
                            "title": "Evidence walk",
                            "unit_plan": "UNIT-1",
                            "session_status": "Planned",
                            "session_date": None,
                            "sequence_index": 10,
                            "learning_goal": "Use evidence",
                            "teacher_note": "Teacher-only",
                        }
                    ],
                ),
                patch.object(
                    module.frappe.db,
                    "sql",
                    return_value=[
                        {
                            "parent": "CLASS-SESSION-1",
                            "title": "Observe",
                            "activity_type": "Discuss",
                            "estimated_minutes": 15,
                            "sequence_index": 10,
                            "student_direction": "Take notes.",
                            "teacher_prompt": "Push for precision.",
                            "resource_note": "Notebook needed.",
                            "idx": 1,
                        }
                    ],
                ),
            ):
                payload = module._fetch_class_sessions("CLASS-PLAN-1", audience="student")

        self.assertEqual(len(payload), 1)
        self.assertNotIn("teacher_note", payload[0])
        self.assertNotIn("teacher_prompt", payload[0]["activities"][0])
        self.assertEqual(payload[0]["activities"][0]["student_direction"], "Take notes.")

    def test_resolve_student_plan_reads_only_active_class_plans(self):
        with _teaching_plans_module() as module:
            with patch.object(
                module.frappe,
                "get_all",
                return_value=[
                    {
                        "name": "CLASS-PLAN-1",
                        "title": "Biology A",
                        "course_plan": "COURSE-PLAN-1",
                        "planning_status": "Active",
                        "team_note": None,
                    }
                ],
            ) as get_all:
                selected_group, class_plan_row = module._resolve_student_plan(
                    "COURSE-1",
                    [{"student_group": "GROUP-1", "label": "Biology A"}],
                    "GROUP-1",
                )

        self.assertEqual(selected_group, "GROUP-1")
        self.assertEqual(class_plan_row["name"], "CLASS-PLAN-1")
        self.assertEqual(get_all.call_args.kwargs["filters"]["planning_status"], "Active")

    def test_build_staff_course_plan_bundle_includes_selected_unit_and_resources(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "_resolve_planning_resource_anchor",
                    return_value={
                        "anchor_doctype": "Course Plan",
                        "anchor_name": "COURSE-PLAN-1",
                        "can_manage_resources": 1,
                    },
                ),
                patch.object(
                    module.planning,
                    "get_course_plan_row",
                    return_value={
                        "name": "COURSE-PLAN-1",
                        "title": "Biology Plan",
                        "course": "COURSE-1",
                        "school": "SCH-1",
                        "academic_year": "2026-2027",
                        "cycle_label": "Semester 1",
                        "plan_status": "Active",
                    },
                ),
                patch.object(
                    module.planning,
                    "get_unit_plan_rows",
                    return_value=[
                        {
                            "name": "UNIT-1",
                            "title": "Cells and Systems",
                            "unit_order": 10,
                        }
                    ],
                ),
                patch.object(
                    module,
                    "_build_unit_lookup",
                    return_value={
                        "UNIT-1": {
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "standards": [],
                            "shared_reflections": [],
                            "class_reflections": [],
                        }
                    },
                ),
                patch.object(
                    module,
                    "_fetch_material_map",
                    return_value={
                        ("Course Plan", "COURSE-PLAN-1"): [{"material": "MAT-COURSE", "title": "Scope and sequence"}],
                        ("Unit Plan", "UNIT-1"): [{"material": "MAT-UNIT", "title": "Lab handout"}],
                    },
                ),
                patch.object(
                    module.frappe,
                    "get_doc",
                    return_value=SimpleNamespace(
                        name="COURSE-PLAN-1",
                        summary="Shared course summary",
                        check_permission=lambda ptype: None,
                    ),
                ),
                patch.object(
                    module.frappe.db,
                    "get_value",
                    return_value={"course_name": "Biology", "course_group": "Science"},
                ),
            ):
                payload = module._build_staff_course_plan_bundle("COURSE-PLAN-1")

        self.assertEqual(payload["resolved"]["unit_plan"], "UNIT-1")
        self.assertEqual(payload["course_plan"]["can_manage_resources"], 1)
        self.assertEqual(payload["resources"]["course_plan_resources"][0]["title"], "Scope and sequence")
        self.assertEqual(payload["curriculum"]["units"][0]["shared_resources"][0]["title"], "Lab handout")

    def test_list_staff_course_plans_serializes_manage_flag(self):
        with _teaching_plans_module() as module:
            rows = [
                {
                    "name": "COURSE-PLAN-1",
                    "title": "Biology Plan",
                    "course": "COURSE-1",
                    "school": "SCH-1",
                    "academic_year": "2026-2027",
                    "cycle_label": "Semester 1",
                    "plan_status": "Active",
                },
                {
                    "name": "COURSE-PLAN-2",
                    "title": "Biology Plan B",
                    "course": "COURSE-2",
                    "school": "SCH-1",
                    "academic_year": "2026-2027",
                    "cycle_label": "Semester 2",
                    "plan_status": "Draft",
                },
            ]

            def fake_get_doc(doctype, name):
                if name == "COURSE-PLAN-1":
                    return SimpleNamespace(check_permission=lambda ptype: None)

                def deny(_ptype):
                    raise module.frappe.PermissionError("blocked")

                return SimpleNamespace(check_permission=deny)

            with (
                patch.object(module.frappe, "get_list", return_value=rows),
                patch.object(
                    module.frappe,
                    "get_all",
                    return_value=[
                        {"name": "COURSE-1", "course_name": "Biology", "course_group": "Science"},
                        {"name": "COURSE-2", "course_name": "Biology B", "course_group": "Science"},
                    ],
                ),
                patch.object(module.frappe, "get_doc", side_effect=fake_get_doc),
            ):
                payload = module.list_staff_course_plans()

        self.assertEqual(len(payload["course_plans"]), 2)
        self.assertEqual(payload["course_plans"][0]["can_manage_resources"], 1)
        self.assertEqual(payload["course_plans"][1]["can_manage_resources"], 0)

    def test_save_course_plan_updates_governed_fields(self):
        with _teaching_plans_module() as module:
            saved = {"count": 0}

            class CoursePlanDoc:
                def __init__(self):
                    self.name = "COURSE-PLAN-1"
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

            with patch.object(module.frappe, "get_doc", return_value=doc):
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
        self.assertEqual(unit_doc.reflections, [{"prior_to_the_unit": "Start with microscope norms."}])
        self.assertEqual(inserted["count"], 1)
        self.assertEqual(payload["unit_plan"], "UNIT-PLAN-NEW")

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
                    return_value={"material": "MAT-1", "title": "Starter article"},
                ),
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
