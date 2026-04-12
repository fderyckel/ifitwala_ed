---
title: "Supporting Material: Reusable Learning Material"
slug: supporting-material
category: Curriculum
doc_order: 8
version: "1.1.0"
last_change_date: "2026-04-13"
summary: "Store reusable supporting files and links that students open alongside units, sessions, and tasks without turning planning content into a file library."
seo_title: "Supporting Material: Reusable Learning Material"
seo_description: "Store reusable supporting files and links that students open alongside units, sessions, and tasks without turning planning content into a file library."
---

## Supporting Material: Reusable Learning Material

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`, `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.py`, `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/integrations/drive/materials.py`, `ifitwala_ed/api/materials.py`
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`

`Supporting Material` is the reusable object for separately openable learning materials. It is not the planning body and it is not the task submission layer.

Current workspace note: v1 supports governed file-backed materials and reusable reference links. Session prompts and curriculum rich text stay on their planning records.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`, `ifitwala_ed/curriculum/materials.py`
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`

- Resolve the authoritative `Course` first.
- Decide whether the item is a governed file or a reusable reference link.
- Use unit or class-session content instead when the teacher is writing instructional text or sequencing the session itself.

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

## Permission Matrix

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`, `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.py`, `ifitwala_ed/curriculum/materials.py`
Test refs: `ifitwala_ed/curriculum/test_materials.py`, `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Global administrative access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Global academic access |
| `Instructor` | Yes | Yes | Yes | Yes | Limited by taught-course or class anchor scope |
| `Curriculum Coordinator` | Yes | Yes | Yes | No | Write applies to program-scoped shared curriculum materials anchored to `Course Plan` and `Unit Plan`; class-owned anchors remain instructor/class-scoped |
| `Accreditation Visitor` | No | No | No | No | Not in the live supporting-material runtime access contract |

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`

- [**Material Placement**](/docs/en/material-placement/)
- [**Task**](/docs/en/task/)
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
- Desk read/list visibility is course-scoped through permission hooks.
- `Academic Admin` can manage supporting materials across curriculum scope.
- `Curriculum Coordinator` can manage supporting materials for program-scoped shared curriculum on `Course Plan` and `Unit Plan`; they do not gain class-owned material write access just from coordinator scope.
- Session instructions, activity prompts, and curriculum rich text are not modeled as `Supporting Material`.

### Current Constraints To Preserve In Review

- Do not turn this doctype into a curriculum-text container.
- Do not bypass Drive governance for file materials.
- Do not expose raw private file paths from this doctype.
