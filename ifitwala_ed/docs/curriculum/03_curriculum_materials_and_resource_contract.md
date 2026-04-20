# Curriculum Materials And Resource Contract

Status: Canonical current-state contract
Code refs: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.json`, `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/file_access.py`, `ifitwala_ed/integrations/drive/bridge.py`, `ifitwala_ed/utilities/governed_uploads.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/ui-spa/src/components/planning/PlanningResourcePanel.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`, `ifitwala_ed/curriculum/test_materials.py`, `ifitwala_ed/api/test_materials.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/ui-spa/src/components/tasks/__tests__/CreateTaskDeliveryOverlay.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

This is the canonical contract for reusable learning materials and resource sharing inside the curriculum stack.

Materials are part of curriculum delivery. They are no longer documented as a separate subsystem outside `docs/curriculum`.

## Core Boundary

Status: Locked
Code refs: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.json`, `ifitwala_ed/assessment/doctype/task/task.json`
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

The learning stack is split into three different things:

- curriculum and session content
- reusable supporting materials
- assigned work

Decision rule:

- authored teaching flow belongs in the curriculum or session objects
- separately openable supporting items belong in materials
- student work belongs in `Task` and `Task Delivery`

Materials are not a dump zone for lesson text, discussion prompts, or missing planning structure.

## Domain Model

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.json`, `ifitwala_ed/curriculum/materials.py`
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`, `ifitwala_ed/curriculum/test_materials.py`

### Supporting Material

Reusable material record.

Current supported types:

- `File`
- `Reference Link`

### Material Placement

Contextual share record that decides where a material appears.

Current allowed anchors:

- `Course Plan`
- `Unit Plan`
- `Class Teaching Plan`
- `Class Session`
- `Task`

Current origin rules:

- `curriculum` for `Course Plan` and `Unit Plan`
- `shared_in_class` for `Class Teaching Plan` and `Class Session`
- `task` for `Task`

## Placement And Removal Rules

Status: Implemented
Code refs: `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`, `ifitwala_ed/curriculum/test_materials.py`, `ifitwala_ed/api/test_teaching_plans.py`

- A material is reusable.
- A placement is the share into one curriculum or assigned-work context.
- Removing a share deletes the placement, not the underlying material.
- The authoritative course for a placement is resolved from the anchor, not guessed by the client.
- Duplicate placement of the same material onto the same anchor is rejected.

Product rule:

- class-shared materials must attach to a real `Class Teaching Plan` or `Class Session`
- task materials must attach to `Task`
- there is no standalone session-only or class-only materials library outside these anchors

## Authoring Workflow

Status: Implemented
Code refs: `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/ui-spa/src/components/planning/PlanningResourcePanel.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/assessment/test_task_creation_service.py`

Staff add materials where they already work:

- task creation overlay for task-scoped materials
- course-plan workspace for shared course-plan and unit resources
- class-planning workspace for class-wide and session-specific resources
- file-upload authoring on those surfaces must show inline upload feedback while the browser is preparing/sending the selected file and must keep a visible finishing state until the governed response returns

Current staff preview behavior:

- governed file materials in the task creation overlay now expose `thumbnail_url` only when a ready `thumb` derivative exists, alongside stable `preview_url` routes for richer preview/open behavior
- governed file materials on the course-plan and class-planning workspaces now expose stable `thumbnail_url` routes for inline image cards plus stable `preview_url` routes for richer preview/open behavior
- those current material rows now also carry an additive nested `attachment_preview` block with the shared cross-surface preview DTO
- those planning workspaces now consume that nested preview DTO through the shared display-only SPA attachment preview card
- the task creation overlay now lets teachers queue governed task attachments while writing the task itself, then persists those queued attachments automatically during the create action so the workflow still feels like one compose step
- that governed task-attachment flow is currently restricted to PDF and image uploads (`pdf`, `jpg`, `jpeg`, `png`, `webp`) plus reference links
- the task creation overlay now renders current task attachments through the shared SPA attachment preview card instead of a task-specific preview fragment
- those workspaces render inline image previews from `thumbnail_url`, render inline PDF first-page cards from `thumbnail_url` when the smaller `pdf_card` derivative is ready, fall back to the governed `preview_url` inline when the card preview is absent or the thumbnail route cannot be delivered, and keep `preview_url` as the richer PDF preview action
- `open_url` remains the explicit original-file action and compatibility baseline

This is the current source-of-truth workflow. Do not push teachers back into a generic Desk library as the primary authoring path.

## Student LMS Visibility

Status: Implemented
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

The student learning space currently exposes materials in these buckets:

- course-plan shared resources
- class-owned resources
- unit resources
- session resources
- task materials

Resolution rule:

- class-owned resources resolve first
- shared plan resources are fallback context
- task materials travel with assigned work

Current student preview behavior:

- `CourseDetail.vue` uses optional `thumbnail_url` for inline governed image cards and stable Ed-owned `preview_url` routes for richer preview/open behavior
- those resource rows now also carry an additive nested `attachment_preview` block with the shared cross-surface preview DTO
- `CourseDetail.vue` now consumes that nested preview DTO through the shared display-only SPA attachment preview card
- session resources plus unit, class, and shared course resource shelves now render inline image thumbnails from `thumbnail_url`, use `thumbnail_url` for PDF first-page card previews when the `pdf_card` derivative is ready, fall back to `preview_url` inline when needed, and keep `preview_url` as the richer PDF preview action
- task-linked materials now render directly inside the assigned-work brief with preview and download actions so students can read the task and access its attachments in one place

The student surface must not require learners to hunt across unrelated pages just to collect the materials for a class.

## File Governance

Status: Implemented
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/integrations/drive/bridge.py`, `ifitwala_ed/utilities/governed_uploads.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/api/test_file_access.py`

File-backed materials use governed upload and governed open flows.

Locked rules:

- `Supporting Material` is the business owner inside Ifitwala_Ed
- Drive remains the file authority
- preview routes for file-backed materials must remain Ed-owned stable action routes, not raw file paths or cached grant URLs
- open/download URLs must be server-resolved
- raw private file paths are not a valid SPA contract
- Ifitwala_Ed owns context, placement, and permission checks
- current supporting-material upload classification uses purpose `learning_resource`; the binding role remains `general_reference` in the current compatibility rollout so existing Drive binding semantics do not drift

## Permissions And Scope

Status: Implemented
Code refs: `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.py`, `ifitwala_ed/api/file_access.py`
Test refs: `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`, `ifitwala_ed/api/test_file_access.py`

- Students only read materials reachable through permitted curriculum or assigned-work anchors.
- Teachers manage materials only on anchors they can manage.
- Shared-plan visibility must not leak class-owned notes or resources.
- File access must enforce the same scope rules as the material placement itself.

## Current Status And Gaps

Status: Partial
Code refs: `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_file_access.py`

Implemented now:

- task-scoped link and file materials
- shared course-plan and unit resource authoring
- class-wide and session-specific resource authoring
- student LMS resource shelves with governed preview/open URLs and inline image or compact PDF preview where available

Not implemented now:

- existing-file picker from Drive
- a separate browse-first materials workspace replacing the current context-first flow

## Related Docs

Status: Canonical map
Code refs: None
Test refs: None

- `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
- `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`

## Technical Notes (IT)

Status: Canonical
Code refs: `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/file_access.py`
Test refs: `ifitwala_ed/curriculum/test_materials.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_file_access.py`

- `Supporting Material` is the reusable record. `Material Placement` is the contextual share.
- `resolve_anchor_context`, `resolve_material_origin`, and the placement permission helpers in `ifitwala_ed/curriculum/materials.py` are the canonical ownership math. Do not reimplement anchor rules ad hoc in endpoints or SPA code.
- `api/materials.py` owns task-scoped material mutations. `api/teaching_plans.py` owns planning-surface resource mutations.
- Any new material surface must define whether it is class-owned, shared-plan-owned, or task-owned before code is written.
