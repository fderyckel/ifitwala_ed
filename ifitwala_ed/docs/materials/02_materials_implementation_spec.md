## Materials Implementation Spec

Status: Canonical implementation spec
Code refs: `ifitwala_ed/api/courses.py`, `ifitwala_ed/api/file_access.py`, `ifitwala_ed/integrations/drive/bridge.py`, `ifitwala_ed/utilities/governed_uploads.py`
Test refs: `ifitwala_ed/api/test_courses.py`, `ifitwala_ed/api/test_file_access.py`

This document defines the implementation contract for the v1 materials slice.

## Scope

Status: Locked for v1
Code refs: None
Test refs: None

Implemented in v1:

- reusable `Supporting Material` domain object
- contextual `Material Placement`
- task-overlay authoring for reference links and governed file uploads
- student LMS materials shelf in course detail
- Drive-safe open/download URLs for file-backed materials

Not implemented in v1:

- Drive existing-file picker
- Class Hub quick-share
- dedicated lesson/unit materials authoring UI beyond direct Desk record access

## Domain Model

Status: Locked
Code refs: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.json`
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

### Supporting Material

Canonical reusable object.

Required core fields:

- `title`
- `course`
- `material_type`

Supported v1 material types:

- `File`
- `Reference Link`

Canonical attributes:

- title
- course
- canonical description
- modality
- file reference for governed uploads
- external reference URL
- archived state

### Material Placement

Contextual share record.

Required core fields:

- `supporting_material`
- `course`
- `anchor_doctype`
- `anchor_name`
- `origin`

Placement responsibilities:

- where students see the material
- why it appears there
- usage role
- teacher note
- ordering

Allowed v1 anchors:

- `Course`
- `Learning Unit`
- `Lesson`
- `Task`

## Validation Rules

Status: Locked
Code refs: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.py`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.py`
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

- Lesson content and lesson-activity links are not auto-converted into materials.
- File materials must resolve to a governed `File` attached to `Supporting Material`.
- File materials must also have an active governed `Drive Binding`.
- Link materials must carry a valid reference URL.
- Placement course must match both the material course and the anchor course.
- Duplicate placement of the same material onto the same anchor is rejected.

## Drive Integration

Status: Locked
Code refs: `ifitwala_ed/integrations/drive/bridge.py`, `ifitwala_ed/integrations/drive/materials.py`, `ifitwala_ed/utilities/governed_uploads.py`
Test refs: `ifitwala_ed/utilities/test_governed_uploads_task_flows.py`

File-backed materials use the governed Drive upload flow with:

- `Supporting Material` as the authoritative business owner
- `Supporting Material` as the attached doctype
- organization and school derived from the material course
- `general_reference` as the Drive binding role

The v1 implementation uses Drive upload sessions and finalize through the existing bridge rather than inventing a second file workflow.

## File Access Contract

Status: Locked
Code refs: `ifitwala_ed/api/file_access.py`
Test refs: `ifitwala_ed/api/test_file_access.py`

File-backed material opens use `download_academic_file` with `context_doctype = Supporting Material`.

Server-side access must allow:

- students enrolled in the course
- instructors with teaching scope on the course
- academic admins and system managers
- curriculum coordinators with read scope through coordinated programs

File access must not depend on raw private URLs.

## Desk Visibility Contract

Status: Locked
Code refs: `ifitwala_ed/hooks.py`, `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.py`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.py`
Test refs: `ifitwala_ed/curriculum/test_materials.py`, `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

Desk visibility for `Supporting Material` and `Material Placement` must be course-scoped.

- Academic admins and system managers have full access.
- Instructors can read and manage materials for courses they teach.
- Curriculum coordinators can read materials for courses in coordinated programs, but not manage them by default.
- List visibility uses `permission_query_conditions`.
- Doc-level enforcement uses `has_permission`.

## Task Overlay Contract

Status: Locked
Code refs: `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/api/materials.py`
Test refs: `ifitwala_ed/assessment/test_task_creation_service.py`

After task creation succeeds, the overlay remains in a post-create materials stage.

The overlay must support:

- add reference-link material to the new task
- upload governed file material to the new task
- list already-added task materials
- finish without adding materials

The task is created first because governed file upload requires a saved business owner and the material placement requires a saved task anchor.

## Student Course Detail Contract

Status: Locked
Code refs: `ifitwala_ed/api/courses.py`, `ifitwala_ed/ui-spa/src/types/contracts/student_hub/get_student_course_detail.ts`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_courses.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

`get_student_course_detail` remains the single bounded bootstrap for the LMS course view.

The response is extended with a materials collection containing:

- canonical material fields
- secure open URL
- all visible placements in the course

The SPA computes the active materials shelf from:

- course context
- active unit
- active lesson
- task anchors visible in that lesson or unit context

## Compatibility Rule

Status: Locked
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task/task.py`
Test refs: None

Existing `Task.attachments` remain a legacy compatibility surface.

The new materials workflow does not depend on `Task.attachments` as the authoritative file owner for new material files.

## Removal Rule

Status: Locked
Code refs: `ifitwala_ed/api/materials.py`, `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.py`
Test refs: `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

- Removing a task, lesson, unit, or course share deletes the placement only.
- The underlying material remains available for reuse until explicitly archived or deleted.
- A material with active placements cannot be hard-deleted.

## Delivery Status

Status: Partial
Code refs: `ifitwala_ed/api/materials.py`, `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.py`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_courses.py`, `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

V1 is considered complete when:

- teachers can add file and link materials from the task overlay
- students can open those materials from the course LMS
- governed file reads remain permission-safe
- docs and code stay aligned on the lesson vs materials boundary
