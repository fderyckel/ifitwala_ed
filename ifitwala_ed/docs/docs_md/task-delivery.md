---
title: "Task Delivery: Turning a Task into a Real Teaching Event"
slug: task-delivery
category: Assessment
doc_order: 5
summary: "Assign a task to a specific student group with dates, grading mode, and evidence rules, then generate student outcomes at scale."
seo_title: "Task Delivery: Turning a Task into a Real Teaching Event"
seo_description: "Assign a task to a specific student group with dates, grading mode, and evidence rules, then generate student outcomes at scale."
---

## Task Delivery: Turning a Task into a Real Teaching Event

## Before You Start (Prerequisites)

- Create the `Task` first.
- Create the `Student Group` first (with roster aligned to the teaching context).
- Prepare grading setup first (`Grade Scale`, and criteria readiness if using criteria grading mode).

`Task Delivery` is where a reusable task becomes real: for this group, in this context, on these dates, with these evidence and grading rules.

<Callout type="warning" title="Important invariant">
Once a delivery has outcomes/evidence, grading configuration is intentionally locked to protect historical integrity.
</Callout>

## Where It Is Used Across the ERP

- Created from [**Task**](/docs/en/task/) planning flows.
- Parent context for [**Task Outcome**](/docs/en/task-outcome/) rows (one per student).
- Referenced by [**Task Submission**](/docs/en/task-submission/) and [**Task Contribution**](/docs/en/task-contribution/).
- Rubric snapshot source for [**Task Rubric Version**](/docs/en/task-rubric-version/) when criteria grading is used.
- Staff portal + grading UX:
  - `/staff/gradebook` task list and grading context
  - Class Hub task review/evidence overlays (`class-hub-task-review`, `class-hub-quick-evidence`, `class-hub-quick-cfu`)
- Guardian-facing timelines:
  - `ifitwala_ed.api.guardian_home.get_guardian_home_snapshot` builds due-task and upcoming-assessment chips from Task Delivery dates/status.
- Student reflections and portfolio linkage:
  - `Student Reflection Entry` can reference Task Delivery.

## Technical Notes (IT)

- **DocType**: `Task Delivery` (`ifitwala_ed/assessment/doctype/task_delivery/`)
- **Autoname**: `TDL-{YYYY}-{#####}`
- **Key links**:
  - `task`, `student_group`, `grade_scale`, `rubric_version`, `course`, `academic_year`, `school`, `lesson_instance`
- **Lifecycle behavior** (`task_delivery.py`):
  - `before_validate`:
    - requires task + group
    - stamps denormalized context from group
    - validates task/course alignment
    - optionally resolves/creates lesson instance context
  - `validate`:
    - delivery mode coherence (`Assign Only`, `Collect Work`, `Assess`)
    - date validation (`available_from <= due_date <= lock_date`)
    - grading/rubric requirements for assess mode
    - group submission hard-block (paused)
    - immutability checks when submitted/outcomes exist
  - `on_submit`:
    - optional rubric snapshot generation for criteria grading
    - bulk outcome creation for all eligible students
  - `on_cancel`:
    - blocked once evidence exists
    - otherwise removes linked Task Outcomes
- **Service dependencies**:
  - `assessment/task_delivery_service.py` (`get_delivery_context`, `bulk_create_outcomes`, lesson-instance resolution)
- **Desk client script**: currently stub-only (`task_delivery.js`)
- **Architecture guarantees (embedded from assessment doctrine)**:
  - delivery snapshots assessment behavior for historical stability
  - criteria deliveries snapshot rubric rows so later task edits do not rewrite history
  - one delivery can lead to many outcomes, but each student still gets exactly one official outcome row for that delivery

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Instructor` | Yes | Yes | Yes | Yes |

## Related Docs

- [**Task**](/docs/en/task/)
- [**Task Outcome**](/docs/en/task-outcome/)
- [**Task Rubric Version**](/docs/en/task-rubric-version/)
- [**Task Submission**](/docs/en/task-submission/)
