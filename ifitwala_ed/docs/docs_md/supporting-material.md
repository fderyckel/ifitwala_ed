---
title: "Supporting Material: Reusable Learning Material"
slug: supporting-material
category: Curriculum
doc_order: 8
version: "1.0.3"
last_change_date: "2026-04-01"
summary: "Store reusable supporting files and links that students open alongside lessons and tasks without turning lesson content into a file library."
seo_title: "Supporting Material: Reusable Learning Material"
seo_description: "Store reusable supporting files and links that students open alongside lessons and tasks without turning lesson content into a file library."
---

## Supporting Material: Reusable Learning Material

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`, `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.py`, `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/integrations/drive/materials.py`, `ifitwala_ed/api/materials.py`
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`

`Supporting Material` is the reusable object for separately openable learning materials. It is not the lesson body and it is not the task submission layer.

Current workspace note: v1 supports governed file-backed materials and reusable reference links. Lesson and lesson-activity content remain the textbook-like authored flow.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`, `ifitwala_ed/curriculum/materials.py`
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`

- Resolve the authoritative `Course` first.
- Decide whether the item is a governed file or a reusable reference link.
- Use lesson content instead when the teacher is writing instructional text or sequencing the lesson itself.

## Where It Is Used Across The ERP

Status: Partial
Code refs: `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_courses.py`, `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`

- Shared into curriculum contexts through [**Material Placement**](/docs/en/material-placement/).
- Added from the task overlay through `ifitwala_ed.api.materials`.
- Aggregated into the student course LMS through `get_student_course_detail`.
- File-backed materials use Drive-governed upload and open flows.

## Lifecycle And Linked Documents

Status: Partial
Code refs: `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/integrations/drive/materials.py`, `ifitwala_ed/utilities/governed_uploads.py`
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`, `ifitwala_ed/utilities/test_governed_uploads_task_flows.py`

1. Create the reusable material object.
2. For file materials, upload the governed file onto the saved material owner.
3. Share the material into one or more contexts using `Material Placement`.
4. Students open the material from the LMS shelf or task context.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`

- [**Material Placement**](/docs/en/material-placement/)
- [**Task**](/docs/en/task/)
- [**Lesson Activity**](/docs/en/lesson-activity/)
- [**Unit Plan**](/docs/en/unit-plan/)

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`, `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.py`, `ifitwala_ed/integrations/drive/materials.py`, `ifitwala_ed/hooks.py`, `ifitwala_ed/curriculum/materials.py`
Test refs: `ifitwala_ed/curriculum/test_materials.py`, `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`, `ifitwala_ed/utilities/test_governed_uploads_task_flows.py`

### Schema And Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.py`
- **Material types**:
  - `File`
  - `Reference Link`

### Current Contract

- `Supporting Material` is reusable and course-scoped.
- File-backed materials store the authoritative `File` link on the material itself, not on `Task.attachments`.
- File-backed materials require a governed `Drive Binding` with `general_reference`.
- Desk read/list visibility is course-scoped through permission hooks, and curriculum coordinators are read-only by default.
- Lesson text, discussion prompts, and in-flow lesson links are not modeled as `Supporting Material`.

### Current Constraints To Preserve In Review

- Do not turn this doctype into a lesson-text container.
- Do not bypass Drive governance for file materials.
- Do not expose raw private file paths from this doctype.
