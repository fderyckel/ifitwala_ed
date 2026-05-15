# Educator-Centered Curriculum Replatform Plan

Status: Canonical current-state cleanup and governance note
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/curriculum/03_curriculum_materials_and_resource_contract.md`, `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`, `ifitwala_ed/docs/enrollment/07_year_rollover_architecture.md`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/task.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_task.py`, `ifitwala_ed/assessment/test_task_creation_service.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

This note tracks the remaining governance cleanup after the curriculum replatform moved live runtime away from the old lesson stack and onto:

- `Course Plan`
- `Unit Plan`
- `Class Teaching Plan`
- `Class Session`
- reusable `Task`
- class-scoped `Task Delivery`

It is not a brainstorm file. It documents the cleanup rules the repository now follows.

## Current Baseline

Status: Implemented
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

Current runtime truth:

- shared curriculum lives in `Course Plan` and `Unit Plan`
- class-owned teaching lives in `Class Teaching Plan` and `Class Session`
- assigned work lives in reusable `Task` plus class-owned `Task Delivery`
- student learning surfaces now read the replatformed class/session spine directly

The old `Lesson`, `Lesson Activity`, and `Lesson Instance` tree is not the live curriculum runtime.

## Governed Year-To-Year Persistence

Status: Implemented as governance rule with Desk-side handover flow
Code refs: `ifitwala_ed/api/task.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/docs/enrollment/07_year_rollover_architecture.md`
Test refs: `ifitwala_ed/api/test_task.py`, `ifitwala_ed/assessment/test_task_creation_service.py`

Year-to-year reuse follows this rule set:

- governed shared assets may be reused across years:
  - `Course Plan`
  - `Unit Plan`
  - course-library reusable `Task`
  - explicit shared/common-assessment baselines when those exist
- class-owned runtime does not silently roll forward:
  - `Class Teaching Plan`
  - `Class Session`
  - class-local resources
  - class-authored assigned-work deliveries
- a teacher may still reuse their own historical task definitions for the same course
- cross-teacher reuse for the same course still requires explicit course-library sharing

This repository now implements a bounded Desk-side curriculum handover flow from `Course Plan`, plus a checklist-assisted bulk handover action on `End of Year Checklist`. That handover creates a draft next-year `Course Plan`, duplicates governed `Unit Plan` rows, reuses shared material placements on the new anchors, and leaves class-owned runtime untouched.

## Enrollment Rollover Boundary

Status: Locked
Code refs: `ifitwala_ed/docs/enrollment/07_year_rollover_architecture.md`
Test refs: `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`, `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`

Enrollment rollover and curriculum reuse are related but separate.

- enrollment rollover moves students into the next academic-year offering context
- it does not currently clone curriculum, class plans, or class sessions
- do not document class-runtime reuse as if it is already part of `Program Enrollment Tool`, `Program Offering Selection Window`, or `End of Year Checklist`

## Legacy Cleanup Status

Status: Partial
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/curriculum/README.md`, `../ifitwala_drive/ifitwala_drive/ifitwala_drive/doctype/drive_binding/drive_binding.py`, `../ifitwala_drive/ifitwala_drive/patches/retire_legacy_lesson_binding_roles.py`
Test refs: `../ifitwala_drive/ifitwala_drive/tests/test_drive_binding_doctype.py`, `../ifitwala_drive/ifitwala_drive/tests/test_retire_legacy_lesson_binding_roles_patch.py`

Completed cleanup:

- canonical contracts now use `Class Session` instead of `Lesson Instance` for live runtime language
- student LMS and class-planning docs now point to the replatformed curriculum spine
- retired lesson-era `Drive Binding` roles are no longer part of the live governed-file contract; legacy rows are normalized through a one-shot Drive patch instead of being preserved in runtime schema/validation
- broken documentation reference for this note has been restored

Remaining real gaps:

- there is still no dedicated promotion workflow from class-originated work into governed shared/common-assessment baseline space
- `Learning Standards` is still a catalog master while unit/runtime publication and reporting rely on different layers
- curriculum workspace and Desk affordances still expose broad masters, so product guidance must continue to prefer the SPA planning flows where they exist

## Decision Rule For Future Changes

Status: Locked
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`
Test refs: None

Any future change should be rejected if it does any of the following:

- reintroduces the lesson tree as runtime truth
- silently promotes class-local edits back into shared curriculum
- implies enrollment rollover already clones curriculum runtime
- creates a second student LMS tree for reflection, tasks, or session work

## Related Docs

Status: Canonical map
Code refs: None
Test refs: None

- `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
- `ifitwala_ed/docs/curriculum/03_curriculum_materials_and_resource_contract.md`
- `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`
- `ifitwala_ed/docs/enrollment/07_year_rollover_architecture.md`
- `ifitwala_ed/docs/student/portfolio_journal_architecture.md`
