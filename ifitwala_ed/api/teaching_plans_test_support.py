from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from types import ModuleType, SimpleNamespace

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


@contextmanager
def _teaching_plans_module():
    student_groups_api = ModuleType("ifitwala_ed.api.student_groups")
    student_groups_api.TRIAGE_ROLES = set()
    student_groups_api._instructor_group_names = lambda user: []

    file_access_api = ModuleType("ifitwala_ed.api.file_access")
    file_access_api.get_academic_file_thumbnail_ready_map = lambda file_names: {
        file_name: True for file_name in file_names or []
    }
    file_access_api.resolve_academic_file_open_url = lambda **kwargs: "/open/resource"
    file_access_api.resolve_academic_file_preview_url = lambda **kwargs: "/preview/resource"
    file_access_api.resolve_academic_file_thumbnail_url = lambda **kwargs: "/thumbnail/resource"

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
    materials_domain._get_coordinator_course_names = lambda user: []

    planning_domain = ModuleType("ifitwala_ed.curriculum.planning")
    planning_domain.normalize_text = lambda value: str(value or "").strip()
    planning_domain.normalize_long_text = lambda value: value
    planning_domain.normalize_rich_text = lambda value, *, allow_headings_from="h2": (
        str(value or "").replace("<script>alert(1)</script>", "").strip() or None
    )
    planning_domain.normalize_flag = lambda value: 1 if str(value or "").strip() in {"1", "True", "true"} else 0
    planning_domain.normalize_record_modified = lambda value: str(value or "").strip()

    def _assert_record_modified_matches(*, expected_modified, current_modified, section_label):
        if expected_modified is None:
            return
        if str(expected_modified or "").strip() == str(current_modified or "").strip():
            return
        raise StubValidationError(f"{section_label} was updated by another user.")

    planning_domain.assert_record_modified_matches = _assert_record_modified_matches
    planning_domain.user_has_global_curriculum_access = lambda user, roles=None: False
    planning_domain.get_instructor_course_names = lambda user: []
    planning_domain.get_coordinator_course_names = lambda user: []
    planning_domain.get_curriculum_manageable_course_names = lambda user, roles=None: []
    planning_domain.user_can_read_course_curriculum = lambda user, course, roles=None: False
    planning_domain.user_can_manage_course_curriculum = lambda user, course, roles=None: False
    planning_domain.assert_can_read_course_curriculum = lambda user, course, roles=None, action_label=None: None
    planning_domain.assert_can_manage_course_curriculum = lambda user, course, roles=None, action_label=None: None
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
    planning_domain.ensure_linked_unit_plan_standards = lambda doc: None

    def _create_student_group_class_delivery(student_group, *, course_plan=None, activate=1):
        doc = frappe.new_doc("Class Teaching Plan")
        doc.student_group = student_group
        doc.course_plan = course_plan
        doc.planning_status = "Active" if planning_domain.normalize_flag(activate) else "Draft"
        doc.insert(ignore_permissions=True)
        return {"class_teaching_plan": doc.name}

    planning_domain.create_student_group_class_delivery = _create_student_group_class_delivery

    def _replace_unit_plan_reflections(doc, rows, course_plan_row=None):
        defaults = course_plan_row or {}
        doc.set(
            "reflections",
            [
                {
                    **(row or {}),
                    "academic_year": (row or {}).get("academic_year") or defaults.get("academic_year"),
                    "school": (row or {}).get("school") or defaults.get("school"),
                    "prior_to_the_unit": planning_domain.normalize_rich_text((row or {}).get("prior_to_the_unit")),
                    "during_the_unit": planning_domain.normalize_rich_text((row or {}).get("during_the_unit")),
                    "what_work_well": planning_domain.normalize_rich_text((row or {}).get("what_work_well")),
                    "what_didnt_work_well": planning_domain.normalize_rich_text(
                        (row or {}).get("what_didnt_work_well")
                    ),
                    "changes_suggestions": planning_domain.normalize_rich_text((row or {}).get("changes_suggestions")),
                }
                for row in rows or []
            ],
        )

    planning_domain.replace_unit_plan_reflections = _replace_unit_plan_reflections

    governed_uploads = ModuleType("ifitwala_ed.utilities.governed_uploads")
    governed_uploads.upload_supporting_material_file = lambda material: None

    quiz_service = ModuleType("ifitwala_ed.assessment.quiz_service")
    quiz_service.get_student_delivery_state_map = lambda **kwargs: {}

    school_settings_utils = ModuleType("ifitwala_ed.school_settings.school_settings_utils")
    school_settings_utils.resolve_school_calendars_for_window = lambda school, start_date, end_date: []

    schedule_utils = ModuleType("ifitwala_ed.schedule.schedule_utils")
    schedule_utils.get_calendar_holiday_set = lambda calendar_name: set()
    schedule_utils.get_weekend_days_for_calendar = lambda calendar_name: [0, 6]

    student_communications_api = ModuleType("ifitwala_ed.api.student_communications")
    student_communications_api.get_student_course_communication_summary = lambda *args, **kwargs: {
        "total_count": 0,
        "unread_count": 0,
        "high_priority_count": 0,
        "has_high_priority": 0,
        "latest_publish_at": None,
    }

    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.get_datetime = lambda value: (
        value
        if isinstance(value, datetime)
        else datetime.combine(value, datetime.min.time())
        if isinstance(value, date)
        else datetime.fromisoformat(str(value))
    )
    frappe_utils.getdate = lambda value: value if isinstance(value, date) else datetime.fromisoformat(str(value)).date()
    frappe_utils.now_datetime = lambda: "2026-04-07 10:30:00"
    frappe_utils.strip_html = lambda value: str(value or "").replace("<p>", "").replace("</p>", "")

    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "ifitwala_ed.api.student_groups": student_groups_api,
            "ifitwala_ed.api.file_access": file_access_api,
            "ifitwala_ed.api.student_communications": student_communications_api,
            "ifitwala_ed.curriculum.materials": materials_domain,
            "ifitwala_ed.curriculum.planning": planning_domain,
            "ifitwala_ed.assessment.quiz_service": quiz_service,
            "ifitwala_ed.school_settings.school_settings_utils": school_settings_utils,
            "ifitwala_ed.schedule.schedule_utils": schedule_utils,
            "ifitwala_ed.utilities.governed_uploads": governed_uploads,
        }
    ) as frappe:
        frappe.db.sql = lambda *args, **kwargs: []
        frappe.db.exists = lambda *args, **kwargs: False
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.delete_doc = lambda *args, **kwargs: None
        frappe.get_all = lambda *args, **kwargs: []
        frappe.get_list = lambda *args, **kwargs: []
        yield import_fresh("ifitwala_ed.api.teaching_plans")
