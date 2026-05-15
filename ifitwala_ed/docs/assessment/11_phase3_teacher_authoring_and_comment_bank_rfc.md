# Ifitwala_Ed — Phase 3 Teacher Authoring And Comment-Bank RFC

Status: **Implemented execution RFC / non-authoritative after runtime docs update**
Audience: Product, Engineering, UX, and coding agents
Scope: Phase 3 teacher authoring, minimal comment bank, rubric-linked feedback authoring, and curriculum-aware relevance inside the existing assessment drawer
Last updated: 2026-04-19

Important note:

- This RFC turns the approved Phase 3 direction into an execution-ready implementation plan.
- It does **not** approve final schema names, field names, endpoint names, or permission changes by itself.
- If implementation lands, update `03_gradebook_notes.md`, `04_task_notes.md`, and `07_feedback_annotation_ecosystem_contract.md` in the same change.
- This RFC extends the Phase 2 runtime introduced by `09_feedback_records_and_publication_rfc.md`.

Related docs:

- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`
- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`
- `ifitwala_ed/docs/assessment/09_feedback_records_and_publication_rfc.md`
- `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
- `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`
- `ifitwala_ed/docs/docs_md/assessment-criteria.md`
- `ifitwala_ed/docs/docs_md/course-plan.md`
- `ifitwala_ed/docs/docs_md/task.md`

---

## 0. Bottom Line

Phase 3 should make the gradebook drawer fast enough for daily grading work.

That means:

- finish the teacher authoring workflow on top of the existing feedback workspace
- add a minimal, assessment-owned comment bank
- reuse curriculum, task, and rubric metadata only to **seed relevance**
- keep feedback authoring inside the gradebook drawer instead of creating a second review or planning surface

The product outcome is not "more annotation types."
The product outcome is: faster, more structured, rubric-aware feedback authoring with less repetitive typing.

---

## 1. Current Baseline

Status: **Implemented baseline**

Code refs:

- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/gradebook_writes.py`
- `ifitwala_ed/assessment/task_feedback_service.py`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookPdfWorkspace.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/gradebook/feedback_workspace.ts`

Test refs:

- `ifitwala_ed/api/test_gradebook.py`
- `ifitwala_ed/assessment/test_task_feedback_service.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`

Phase 2 already provides:

- one bounded drawer bootstrap
- one version-bound `Task Feedback Workspace` per outcome and selected submission version
- structured anchored feedback items with `point`, `rect`, `page`, `text_quote`, and `path` families in the service contract
- explicit feedback and grade visibility state in the drawer runtime
- a governed `pdf.js` drawer workspace with page navigation, zoom, and draft point / area / page anchors

Phase 3 now adds:

- teacher-speed reusable comments
- quick insertion from a bounded drawer comment bank
- item-level authoring for each feedback item's intent, criterion linkage, and workflow state
- personal / course / task relevance for reusable comments

Phase 3 still does **not** provide the student-facing navigator or reply loop.

---

## 2. Phase 3 Goal And Non-Goals

Status: **Planned**

### Goal

Make teacher feedback authoring fast, structured, rubric-aware, and integrated with the current curriculum and assessment runtime.

### Non-goals

Phase 3 does **not**:

- move feedback authoring into `CoursePlanWorkspace.vue`
- change reporting ownership away from `Task Outcome` and `Task Outcome Criterion`
- introduce student replies or the student feedback navigator
- introduce broad cross-teacher or whole-school comment sharing by default
- replace the current task-creation, rubric, or curriculum authoring flows
- make OCR hardening the main delivery of this phase

---

## 3. Product Boundary For Phase 3

Status: **Locked for implementation**

Code refs:

- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookPdfWorkspace.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`
- `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`

Phase 3 owns:

- teacher feedback authoring in the gradebook drawer
- feedback summary authoring
- anchored feedback item authoring
- minimal reusable comment insertion and promotion
- rubric-linked feedback authoring shortcuts

Phase 3 does **not** move grading or feedback work into:

- `CoursePlanWorkspace.vue`
- `CoursePlanQuizBanksSection.vue`
- a standalone document-review page
- a separate comment-bank management app

Curriculum remains upstream context.
Assessment remains the feedback and grading runtime.

---

## 4. Integration Map Across Existing Components

Status: **Planned integration contract**

### 4.1 Assessment runtime owners

The following remain the runtime owners for teacher feedback work:

- `ifitwala_ed/api/gradebook_reads.py`
  bounded drawer bootstrap
- `ifitwala_ed/api/gradebook_writes.py`
  named feedback and grading mutations
- `ifitwala_ed/assessment/task_feedback_service.py`
  feedback workspace and anchored item normalization
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`
  summary and publication authoring shell
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookPdfWorkspace.vue`
  anchored PDF authoring surface

### 4.2 Curriculum and planning context providers

The following remain upstream context providers only:

- `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`
  governed course planning shell
- `ifitwala_ed/ui-spa/src/components/planning/course-plan-workspace/CoursePlanQuizBanksSection.vue`
  shared quiz-bank authoring and assignment launch
- `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`
  task and delivery creation, including criteria setup
- `ifitwala_ed/api/task.py`
  course criteria and task criteria read helpers
- `ifitwala_ed/assessment/task_creation_service.py`
  task and delivery criteria defaults

### 4.3 Curriculum truth and rubric truth

The following remain the truth owners for criteria and rubric setup:

- `Assessment Criteria`
- `Course Assessment Criteria`
- `Task Template Criterion`
- task-local delivery rubric strategy

Feedback records may link to these objects.
They must not replace them.

---

## 5. Recommended Phase 3 Output

Status: **Planned**

By the end of Phase 3, a teacher should be able to:

1. open the existing gradebook drawer
2. review a selected submission version
3. create or select an anchored feedback item
4. link it to the appropriate criterion when relevant
5. insert a reusable comment in one or two actions
6. edit that comment in place
7. promote a useful one-off comment into the personal comment bank
8. save one bounded feedback draft without leaving the drawer

That is the minimum successful outcome for this phase.

---

## 6. Phase 3 Sub-Phases

Status: **Planned rollout**

### 6.1 Phase 3a — Complete the teacher authoring UI

Primary files:

- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookPdfWorkspace.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/gradebook/feedback_workspace.ts`

Deliver:

- item-level editor for:
  - note body
  - intent
  - linked `assessment_criteria`
  - workflow state
- tighter selection sync between the PDF overlay and right-side feedback list
- criterion-aware editing flow that uses the existing delivery rubric rows already present in the drawer
- explicit save-state feedback so authoring changes never fail silently

Design rule:

- summary authoring and anchored item authoring stay in one drawer workflow
- the drawer remains the only rich authoring surface

Acceptance gate:

- a teacher can fully author a version-bound feedback draft from the drawer without resorting to raw JSON or placeholder item state

### 6.2 Phase 3b — Minimal comment bank

Primary files and modules:

- new assessment-owned comment-bank service and schema, name to be approved
- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/gradebook_writes.py`
- `ifitwala_ed/ui-spa/src/lib/services/gradebook/gradebookService.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/gradebook/get_drawer.ts`

Deliver:

- teacher-owned reusable comment entries
- optional relevance to:
  - course
  - task
  - `assessment_criteria`
- optional default intent on each reusable comment
- active and archived state
- ability to insert a reusable comment into the selected feedback item
- ability to promote a one-off anchored note into the teacher's reusable bank

Hard scope rule:

- first version is **teacher-owned first**
- do not start with broad course-team sharing unless explicitly approved

Design rule:

- the bank is a productivity layer over the feedback workspace
- it is not curriculum truth and not rubric truth

Acceptance gate:

- a teacher can reuse a criterion-relevant quick comment from the drawer in at most two actions

### 6.3 Phase 3c — Curriculum and task relevance wiring

Primary files and modules:

- `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`
- `ifitwala_ed/api/task.py`
- `ifitwala_ed/assessment/task_creation_service.py`
- `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/staff_teaching/get_staff_course_plan_surface.ts`

Deliver:

- comment-bank suggestion relevance seeded from existing runtime context:
  - course
  - task
  - `unit_plan` when present
  - delivery rubric criteria
- no new curriculum feedback editor
- no second planning-time comment workflow

Recommended interpretation:

- curriculum and task metadata influence **which reusable comments are suggested**
- they do not become the owner of reusable feedback content

Acceptance gate:

- the drawer can surface better reusable comments because it already knows the course, task, and criteria context

### 6.4 Phase 3d — Docs and tests

Primary files:

- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`
- `ifitwala_ed/docs/assessment/09_feedback_records_and_publication_rfc.md`
- relevant API and SPA tests

Deliver:

- runtime docs updated to reflect shipped comment-bank behavior
- targeted backend tests for:
  - drawer read-model reuse
  - comment-bank filtering and permissions
  - promotion of ad hoc note to reusable comment
- targeted SPA tests for:
  - item editing
  - insertion from bank
  - criterion-aware suggestion filtering

Acceptance gate:

- docs and code say the same thing about how teacher authoring now works

---

## 7. Comment-Bank Domain Guidance

Status: **Planned**

This RFC intentionally avoids approving final schema names, but it does lock the first-version shape.

First-version comment-bank entries should support:

- owner teacher
- reusable body text
- default feedback intent
- optional course relevance
- optional task relevance
- optional `assessment_criteria` relevance
- archived or active state

First-version entries should **not** require:

- team moderation
- nested folders
- rubric-weight ownership
- institution-wide libraries
- student-visible publication state

Server-side rules:

- filtering and visibility stay server-owned
- teacher-only scope is the default
- course or task relevance only narrows suggestions; it does not widen unauthorized visibility

---

## 8. Drawer Read-Model Change

Status: **Planned**

Code refs:

- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/ui-spa/src/types/contracts/gradebook/get_drawer.ts`

The drawer should remain one bounded read model.

Recommended addition:

- a `comment_bank` block returned together with `feedback_workspace`

That block should already be scoped server-side by:

- current teacher
- current course
- current task
- current delivery rubric context

Do **not** add:

- per-item client fetches
- PDF-viewer fetches for comment suggestions
- separate curriculum read calls from the drawer just to find reusable comments

This must stay aligned with the repo-wide hot-path and bounded-bootstrap rules.

---

## 9. UI Contract For The Drawer

Status: **Planned**

### 9.1 In `GradebookPdfWorkspace.vue`

Add:

- selected-item editing affordances beyond note text alone
- insert-from-bank action near the selected feedback item
- promote-to-bank action on anchored drafts
- criterion indicator on anchored items where applicable

Keep:

- governed `pdf.js` rendering
- selected-submission-version binding
- point / area / page anchored authoring

Do not:

- turn the PDF workspace into a second full-page app
- add a large general-purpose annotation toolbar

### 9.2 In `GradebookStudentDrawer.vue`

Add:

- bounded comment-bank panel or picker within the Evidence workflow
- tighter coordination between rubric rows and selected feedback item editing
- explicit teacher guidance when a criterion-linked reusable comment is available

Keep:

- summary authoring
- version-aware feedback workspace ownership
- official-result and publication controls outside the PDF canvas

---

## 10. Curriculum Integration Rules

Status: **Locked for Phase 3**

Code refs:

- `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
- `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`
- `ifitwala_ed/ui-spa/src/components/planning/course-plan-workspace/CoursePlanQuizBanksSection.vue`
- `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`

Rules:

1. `CoursePlanWorkspace.vue` remains the governed curriculum workspace.
2. `CoursePlanQuizBanksSection.vue` remains a planning and assignment-launch surface.
3. `CreateTaskDeliveryOverlay.vue` remains the canonical task and delivery handoff path from curriculum into assessment.
4. Course-plan, unit-plan, quiz-bank, and task metadata may shape feedback suggestion relevance.
5. They must not become a second feedback-authoring system.

Implication:

- if a teacher wants to author or reuse feedback during grading, that happens in the gradebook drawer
- if a teacher wants to define curriculum, quizzes, or task criteria defaults, that happens in the curriculum and task flows

---

## 11. Rubric And Criteria Integration Rules

Status: **Locked for Phase 3**

Code refs:

- `ifitwala_ed/docs/docs_md/assessment-criteria.md`
- `ifitwala_ed/api/task.py`
- `ifitwala_ed/assessment/task_creation_service.py`
- `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`

Rules:

1. `Assessment Criteria` remain reusable curriculum truth.
2. `Task Template Criterion` and delivery rubric strategy remain the assignment-side rubric setup.
3. Feedback items may link to criteria for evidence context.
4. Reusable comments may also be tagged to criteria for better suggestions.
5. Reusable comments must not become the owner of criterion weighting, levels, or official outcome values.

Design implication:

- criterion-linked quick comments are allowed
- criterion-defined grading truth remains elsewhere

---

## 12. Permissions And Multi-Tenant Rules

Status: **Planned**

Rules:

- comment-bank visibility is evaluated server-side
- teacher-owned entries default to the current teacher only
- course/task relevance cannot widen access beyond the teacher's own permission scope
- sibling course and school bleed is forbidden

Before any shared-bank behavior is added later, the implementation must define:

- who may create shared entries
- who may edit them
- who sees them by default
- how tenant and course isolation is enforced

That is not Phase 3 default behavior.

---

## 13. Suggested Implementation Order

Status: **Planned**

1. Finish the item authoring UI in the gradebook drawer.
2. Add the minimal assessment-owned comment-bank domain and read/write service.
3. Extend the bounded drawer payload with scoped reusable comments.
4. Wire insert and promote flows in the drawer UI.
5. Add criterion-aware and task-aware relevance based on existing task and curriculum context.
6. Update docs and tests together.

This order matters because:

- it preserves the drawer as the single authoring surface
- it avoids curriculum drift
- it keeps the first productivity win close to the current teacher workflow

---

## 14. Acceptance Criteria

Status: **Planned**

Phase 3 should be considered successful only if all of the following are true:

- teachers can reuse a relevant comment without leaving the drawer
- teachers can promote a one-off note into the bank from the drawer
- anchored feedback and summary authoring still save through one bounded feedback draft path
- criterion-linked authoring stays aligned to the delivery rubric already in the drawer
- no new curriculum-side grading workflow is created
- reporting truth remains owned by `Task Outcome` and `Task Outcome Criterion`
- drawer reads remain bounded and do not degrade into request waterfalls

---

## 15. Main Risks

Status: **Planned risk register**

### Risk 1 — Workflow drift

If comment banks become a separate workspace, teachers will be forced to context-switch and the gradebook drawer will stop being the single authoring surface.

### Risk 2 — Truth drift

If reusable comments start carrying rubric truth or reporting meaning, the product will blur feedback with official result ownership.

### Risk 3 — Permission drift

If shared comment visibility is introduced too early, course-team or tenant isolation may leak.

### Risk 4 — Hot-path regression

If the drawer loads reusable comments through separate client fetches, the page will regress into waterfalls.

### Risk 5 — Curriculum drift

If course-plan or quiz-bank authoring starts carrying live grading behavior, curriculum planning and assessment runtime will be muddled again.

---

## 16. Open Decisions Requiring Explicit Approval

Status: **Pending**

1. Final schema and endpoint names for the minimal comment-bank layer
2. Whether first-version entries may optionally be shared with the course team, or whether teacher-owned only is the strict launch rule
3. Whether summary snippets belong in the first comment-bank version, or whether Phase 3 should only support anchored-item reusable comments

Until those decisions are approved, implementation should treat this RFC as the execution map, not as field-level approval.
