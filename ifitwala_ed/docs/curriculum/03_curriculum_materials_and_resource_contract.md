# Curriculum Materials And Resource Contract

Status: Canonical current-state contract
Code refs: `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.json`, `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/file_access.py`, `ifitwala_ed/integrations/drive/bridge.py`, `ifitwala_ed/utilities/governed_uploads.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/ui-spa/src/components/planning/PlanningResourcePanel.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/curriculum/doctype/supporting_material/test_supporting_material.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`, `ifitwala_ed/curriculum/test_materials.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

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

The student surface must not require learners to hunt across unrelated pages just to collect the materials for a class.

## File Governance

Status: Implemented
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/integrations/drive/bridge.py`, `ifitwala_ed/utilities/governed_uploads.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/api/test_file_access.py`

File-backed materials use governed upload and governed open flows.

Locked rules:

- `Supporting Material` is the business owner inside Ifitwala_Ed
- Drive remains the file authority
- open/download URLs must be server-resolved
- raw private file paths are not a valid SPA contract
- Ifitwala_Ed owns context, placement, and permission checks
- current supporting-material upload classification uses purpose `academic_report` and binding role `general_reference`; the education-oriented `learning_resource` replacement is proposed in `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`

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
- student LMS resource shelves with governed open URLs

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
