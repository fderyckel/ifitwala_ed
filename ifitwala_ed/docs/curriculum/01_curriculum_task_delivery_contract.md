# Curriculum Planning, Teaching, and Task Delivery Contract (Authoritative)

Status: Canonical current-workspace contract
Code refs: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`, `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.json`, `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.json`, `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
Test refs: `ifitwala_ed/curriculum/doctype/learning_unit/test_learning_unit.py`, `ifitwala_ed/curriculum/doctype/lesson/test_lesson.py`, `ifitwala_ed/curriculum/doctype/lesson_instance/test_lesson_instance.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`

This note is the canonical contract for how planned curriculum, taught curriculum, and assessed work connect in the current workspace.

## Current Intent

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`, `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.json`, `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.json`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
Test refs: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`

- Planned curriculum lives in `Learning Standards`, `Learning Unit`, `Learning Unit Standard Alignment`, `Lesson`, and `Lesson Activity`.
- Taught curriculum lives in `Lesson Instance`.
- Assessed work lives in `Task` and `Task Delivery`.
- `Task` currently anchors to curriculum through `default_course` plus optional `learning_unit` and `lesson`.
- `Task Delivery` currently anchors to teaching context through `student_group` plus optional `lesson_instance`.
- The live schema does not give `Task` or `Task Delivery` a direct field for `Learning Standards` or `Lesson Activity`.
- The live `Learning Unit` schema stores standards alignment as inline child rows (`Learning Unit Standard Alignment`), not as `Link` rows to the standalone `Learning Standards` master.

## Entity Roles

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`, `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.json`, `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
Test refs: None beyond scaffold coverage

- `Learning Standards` is the standalone standards catalog for framework metadata.
- `Learning Unit` is the planned unit container inside a `Course`.
- `Learning Unit Standard Alignment` is the unit-level standards snapshot stored inside `Learning Unit.standards`.
- `Lesson` is the ordered planned teaching segment inside a learning unit.
- `Lesson Activity` is the pedagogical atom inside a lesson.
- `Lesson Instance` is the real taught event for a `Student Group`; it can exist with or without any task.
- `Task` is the reusable learning-work definition; it can point back to a unit or lesson, but it is not the teaching event itself.
- `Task Delivery` is the runtime assignment/collection/assessment event; it can point to a `Lesson Instance`, but it does not own curriculum planning.

## Linkage Rules

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/doctype/task/task.js`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_delivery_service.py`
Test refs: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`

1. `Task` requires `default_course`.
2. `Task.learning_unit` is optional, but when present `task.py` validates that the unit belongs to the same course as the task.
3. `Task.lesson` is optional, but when present `task.py` validates that the lesson belongs to the selected learning unit and course.
4. `Task` has no current field for `lesson_activity` or `lesson_instance`.
5. `Task Delivery` requires `task`, `student_group`, and `delivery_mode`.
6. `Task Delivery.lesson_instance` is the only explicit taught-curriculum link on the live schema.
7. `assessment/task_delivery_service.py::resolve_or_create_lesson_instance()` can create an async `Lesson Instance` when explicit lesson/activity context is supplied, but the current `Task Delivery` schema and delivery APIs do not expose `lesson`, `lesson_activity`, or `instance_type`, so that helper is dormant in the normal documented path.
8. Because of rules 4 and 6, the current authoritative path is:
   planned curriculum -> `Task` (optional unit/lesson anchor) -> `Task Delivery` -> optional `Lesson Instance`.

## Contract Matrix

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`, `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.py`, `ifitwala_ed/curriculum/doctype/lesson/lesson.py`, `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.py`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/api/task.py`, `ifitwala_ed/api/class_hub.py`
Test refs: `ifitwala_ed/curriculum/doctype/learning_unit/test_learning_unit.py`, `ifitwala_ed/curriculum/doctype/lesson/test_lesson.py`, `ifitwala_ed/curriculum/doctype/lesson_instance/test_lesson_instance.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`

| Concern | Current contract | Status | Code refs | Test refs |
|---|---|---|---|---|
| Schema / DocType | Planned layer is `Learning Standards`, `Learning Unit`, `Learning Unit Standard Alignment`, `Lesson`, `Lesson Activity`; taught layer is `Lesson Instance`; assessed linkage is `Task` and `Task Delivery`. | Implemented | `curriculum/doctype/*/*.json`, `assessment/doctype/task/task.json`, `assessment/doctype/task_delivery/task_delivery.json` | Scaffold only for most curriculum doctypes |
| Controller / Workflow logic | Parent-side workflow exists for `Learning Unit`, `Task`, and `Task Delivery`; `Lesson`, `Lesson Activity`, `Learning Standards`, and `Lesson Instance` controllers are empty. | Partial | `curriculum/doctype/learning_unit/learning_unit.py`, `assessment/doctype/task/task.py`, `assessment/doctype/task_delivery/task_delivery.py`, `assessment/task_delivery_service.py` | `assessment/doctype/task_delivery/test_task_delivery.py` |
| API endpoints | No dedicated curriculum CRUD API is present. Task/runtime linkage is exposed through `api/task.py`, `assessment/task_creation_service.py`, and `assessment/task_delivery_service.py`. Class Hub exposes lesson-instance-shaped payloads. | Partial | `api/task.py`, `assessment/task_creation_service.py`, `assessment/task_delivery_service.py`, `api/class_hub.py` | `assessment/test_task_creation_service.py` |
| SPA / Desk surfaces | Desk forms exist for curriculum doctypes. `task.js` filters learning units and lessons by course. `learning_unit.js` exposes lesson list/reorder actions. Class Hub reads `lesson_instance`. | Partial | `assessment/doctype/task/task.js`, `curriculum/doctype/learning_unit/learning_unit.js`, `ui-spa/src/pages/staff/ClassHub.vue` | None |
| Reports / Dashboards / Briefings | Student portfolio and Class Hub can carry lesson-instance or lesson-activity context, but there is no curriculum-to-task analytical contract beyond the existing links. | Partial | `api/student_portfolio.py`, `api/class_hub.py` | None |
| Scheduler / background jobs | No scheduler-owned curriculum linkage jobs are present in the current workspace. | Implemented | None | None |
| Tests | Curriculum doctypes mostly have scaffolds only. Runtime task-delivery behavior has actual coverage. | Partial | `curriculum/doctype/*/test_*.py`, `assessment/doctype/task_delivery/test_task_delivery.py` | Same as code refs |

## Review Guardrails

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.py`, `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.py`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
Test refs: None

- Do not invent a standalone `Learning Unit Standard` DocType. The live workspace has `Learning Standards` plus the child table `Learning Unit Standard Alignment`.
- Do not document `Lesson Activity` as a direct task/task-delivery field. That link does not exist in the current schema.
- Do not document `Lesson Instance` as owning tasks. Its own DocType description explicitly forbids that.
- Keep child-table behavior lightweight. `Lesson Activity` and `Learning Unit Standard Alignment` currently have empty controllers, which matches the repository rule that business logic belongs on parents.

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.js`, `ifitwala_ed/curriculum/doctype/lesson/lesson.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/api/class_hub.py`
Test refs: None

### Current Drift To Preserve In Review

- `learning_unit.js` exposes a reorder-lessons action that calls `ifitwala_ed.curriculum.doctype.lesson.lesson.reorder_lessons`, but the current `lesson.py` does not define `reorder_lessons()`.
- `resolve_or_create_lesson_instance()` supports explicit `lesson` and `lesson_activity` context, but the live `Task Delivery` schema and delivery APIs only expose `lesson_instance`.
- `api/class_hub.py::start_session()` currently returns demo `lesson_instance` data (`LI-DEMO-0001`) instead of creating a persisted `Lesson Instance`.
- `Learning Standards` is present as a catalog DocType, but `Learning Unit.standards` does not currently link to it by field; the alignment rows duplicate framework metadata inline.
