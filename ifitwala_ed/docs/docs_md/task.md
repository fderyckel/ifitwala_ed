---
title: "Task: The Reusable Learning and Assessment Blueprint"
slug: task
category: Assessment
doc_order: 4
summary: "Author reusable learning tasks once, then deliver them to groups with the right grading mode, evidence expectations, and rubric strategy."
---

# Task: The Reusable Learning and Assessment Blueprint

`Task` is the design layer for learning work. It defines intent, instructions, and default assessment behavior, but it is not yet assigned to a class. That separation keeps teaching flexible and prevents accidental data duplication.

<Callout type="tip" title="Teacher workflow benefit">
Teachers can reuse a strong task design across cohorts and terms, while each delivery still keeps its own historical outcomes.
</Callout>

## Where It Is Used Across the ERP

- [**Task Delivery**](/docs/en/task-delivery/) references Task as the assignable source.
- [**Task Rubric Version**](/docs/en/task-rubric-version/) snapshots criteria from Task at delivery time.
- [**Task Outcome**](/docs/en/task-outcome/), [**Task Submission**](/docs/en/task-submission/), and [**Task Contribution**](/docs/en/task-contribution/) inherit context from delivery/task.
- Staff Portal:
  - `/staff/home` opens `create-task` overlay via global overlay stack.
  - Overlay component: `ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`.
  - Overlay host routing: `ui-spa/src/overlays/OverlayHost.vue` + `ui-spa/src/composables/useOverlayStack.ts`.
- Class Hub overlays (task-adjacent quick flows):
  - `class-hub-task-review`
  - `class-hub-quick-evidence`
  - `class-hub-quick-cfu`
- Task planning API endpoints (`ifitwala_ed/api/task.py`):
  - `search_tasks`
  - `get_task_for_delivery`
  - `create_task_delivery`
- Staff analytics resurfacing:
  - `ui-spa/src/pages/staff/analytics/StudentOverview.vue` task cards/charts
  - `ifitwala_ed/api/student_overview_dashboard.py` (`_task_rows`) currently reads legacy `Task` + `Task Student` structures
- Morning briefing resurfacing:
  - `ifitwala_ed/api/morning_brief.py` `get_pending_grading_tasks` reads `Task` due/publish status
- Desk Workspaces:
  - `Curriculum` workspace
  - `Admin` workspace

## Technical Notes (IT)

- **DocType**: `Task` (`ifitwala_ed/assessment/doctype/task/`)
- **Title field**: `title`
- **Child tables**:
  - `attachments` (`Attached Document`)
  - `task_criteria` (`Task Template Criterion`)
- **Key links**:
  - `learning_unit`, `lesson`, `default_course`, `default_grade_scale`
- **Controller invariants** (`task.py`):
  - curriculum alignment guard: lesson/unit/course must be coherent
  - duplicate criteria guard in `task_criteria`
  - grading default enforcement by `default_delivery_mode` / `default_grading_mode`
  - trash guard: Task cannot be deleted once used by a Task Delivery
- **Desk client script** (`task.js`):
  - filtered selectors for `learning_unit` and `lesson` based on course context
  - resets stale curriculum links when course changes
  - delivery-mode-based clearing of grading defaults
- **Creation surface integration**:
  - Create Task + Delivery wizard in staff portal overlay
  - orchestration service `assessment/task_creation_service.py` supports single-transaction creation flow
- **Reports/analytics note**:
  - no dedicated Query/Script report object currently references `Task` directly
  - analytics is delivered through SPA/API surfaces instead

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Instructor` | Yes | Yes | Yes | Yes |
| `Academic Staff` | Yes | No | No | No |

## Authoritative References

- `ifitwala_ed/docs/assessment/01_assessment_notes.md`
- `ifitwala_ed/docs/assessment/02_curriculum_relationship_notes.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`

## Related Docs

- [**Task Delivery**](/docs/en/task-delivery/)
- [**Task Outcome**](/docs/en/task-outcome/)
- [**Assessment Criteria**](/docs/en/assessment-criteria/)
- [**Grade Scale**](/docs/en/grade-scale/)
