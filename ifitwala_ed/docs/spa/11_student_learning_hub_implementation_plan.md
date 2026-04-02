# Student Hub Implementation Plan

Status: Proposed
Code refs: `ifitwala_ed/docs/spa/10_student_learning_hub_proposal.md`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/Courses.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentPortfolioFeed.vue`, `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`, `ifitwala_ed/ui-spa/src/overlays/OverlayHost.vue`, `ifitwala_ed/ui-spa/src/composables/useOverlayStack.ts`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/api/course_schedule.py`, `ifitwala_ed/api/student_portfolio.py`
Test refs: None

This plan sequences implementation of the Student Hub learning proposal into a few practical phases that can start now without changing the canonical curriculum and task contracts by accident.

## Purpose and sequencing

Status: Proposed
Code refs: `ifitwala_ed/docs/spa/10_student_learning_hub_proposal.md`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
Test refs: None

The implementation order should follow this rule:

1. make the curriculum visible
2. make navigation and next-step selection calm
3. make execution focused
4. then add richer interactivity and interoperability

This avoids a common failure mode where the product ships a task feed and board before it ships the actual learning surface.

Recommended start order:

- Start with contract hardening and aggregated payload design.
- Build the course learning surface before making the board heavily interactive.
- Ship the first `Today` cockpit with more server curation and less student orchestration.
- Add focus, reflection, and progress only after the course route can anchor execution meaningfully.

## Cross-phase guardrails

Status: Proposed
Code refs: `ifitwala_ed/docs/spa/10_student_learning_hub_proposal.md`, `ifitwala_ed/docs/student/portfolio_journal_architecture.md`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/docs_md/lesson-activity.md`, `ifitwala_ed/docs/docs_md/task-delivery.md`
Test refs: None

These rules should apply in every phase:

- Keep the native curriculum model canonical: `Learning Unit -> Lesson -> Lesson Activity`.
- Keep runtime learning state separate from authored curriculum state.
- Do not let personal board state overwrite `Task Delivery`, `Task Submission`, grading, or publication truth.
- Do not surface generic `Student Log` rows on Home under the current contract.
- Keep reflection inside the learning loop, but reuse the existing `student_reflection_entry` and portfolio services.
- Keep low-stakes retrieval checks outside the heavy `Task Delivery` lifecycle unless a later contract explicitly says otherwise.

Marketplace and import/export guardrails:

- Design early phases so a future educator marketplace can package planned curriculum without carrying student runtime state.
- The likely portable boundary for a first marketplace export is the planned layer: `Learning Unit`, `Learning Unit Standard Alignment`, `Lesson`, and `Lesson Activity`.
- Do not assume marketplace export should include `Task Delivery`, `Lesson Instance`, student progress, reflections, portfolio items, checkpoint attempts, or gradebook outcomes.
- Whether `Task` should later become exportable should be treated as a separate approved decision, not assumed in early Hub work.
- The current inline `Learning Unit Standard Alignment` model is more portable than a hard link to a local standards master, but local standards reconciliation still needs an explicit later design.
- Any future marketplace package format, versioning model, file-bundle contract, and import lineage schema require separate approval before implementation.

## Phase 1: Contract hardening and aggregated payload design

Status: Implemented
Code refs: `ifitwala_ed/docs/spa/10_student_learning_hub_proposal.md`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/ui-spa/src/router/index.ts`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/lib/services/student/studentLearningHubService.ts`, `ifitwala_ed/ui-spa/src/types/contracts/student_hub/get_student_hub_home.ts`, `ifitwala_ed/ui-spa/src/types/contracts/student_hub/get_student_course_detail.ts`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/api/course_schedule.py`
Test refs: `ifitwala_ed/api/test_courses.py`, `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`

Goal: lock the delivery contract before UI expansion.

Scope:

- Define one aggregated student-home payload contract and one aggregated course-detail payload contract.
- Define the deep-link resolution rule using the live curriculum anchors that already exist: `Course`, optional `Learning Unit`, optional `Lesson`, and optional `Lesson Instance`.
- Explicitly keep `Lesson Activity` as a rendered curriculum object, not a task-delivery field, because that direct link does not exist in the live schema.
- Define the first reflection-entry trigger points using the current reflection architecture.
- Define the focus-mode entry and exit contract at the proposal level before implementation.
- Explicitly document that generic `Student Log` rows stay off Home.

Execution notes:

- Backend now exposes one aggregated endpoint for Home and one for Course Detail.
- SPA now consumes those aggregated payloads through a dedicated student-Hub service layer.
- Route-level deep-link query anchors are now explicit on `student-course-detail`.
- Backend contract tests and SPA service tests were added with the implementation, although runtime execution is still tooling-limited in this workspace.

Exit criteria:

- Course Detail can be built from one aggregated payload.
- Home can be built from one aggregated payload.
- Deep-link behavior is documented against the live curriculum/task contract.

## Phase 2: Read-only course learning surface

Status: Implemented
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/lib/studentCourseDetail.ts`, `ifitwala_ed/ui-spa/src/pages/student/Courses.vue`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/docs/docs_md/learning-unit.md`, `ifitwala_ed/docs/docs_md/lesson.md`, `ifitwala_ed/docs/docs_md/lesson-activity.md`, `ifitwala_ed/docs/docs_md/task.md`
Test refs: `ifitwala_ed/ui-spa/src/lib/__tests__/studentCourseDetail.test.ts`

Goal: make `My Courses` the real LMS surface before the planning layer becomes the primary student experience.

Scope:

- Upgrade `CourseDetail.vue` from placeholder to structured course view.
- Render ordered `Learning Unit`, `Lesson`, and `Lesson Activity` sequences.
- Show embedded task context inside the relevant lesson flow.
- Support deep-link landing into the correct course section when the student enters from Home.
- Keep the first release read-only for progress and completion state.

Execution notes:

- `CourseDetail.vue` now uses one active-unit and active-lesson view instead of a flat curriculum dump.
- The student can navigate through a route-driven course map of units and lessons without creating new workflow state.
- Course map navigation now docks as a side rail from `lg` breakpoints onward, and mobile starts collapsed behind an explicit `Show Outline` action to reduce vertical scroll debt.
- Unit navigation now uses a single-expanded accordion pattern (active unit expanded by default) so students are not forced through a full unit+lesson dump before reaching lesson content.
- Linked work is now rendered inline at course, unit, and lesson level using the existing `Task` and `Task Delivery` contract.
- Teacher framing is limited to live schema fields already present today: unit overview, essential understanding, misconceptions, lesson type, lesson date, duration, and due-work context.
- This phase remains read-only; progress state, resume state, and execution overlays stay in later phases.

Exit criteria:

- A student can open a course and understand what unit, lesson, and activity comes next.
- A task or route anchor can land inside the relevant course context.
- The course page works even when `Lesson Instance` context is absent.

## Phase 3: Today cockpit and server-curated work board

Status: Implemented
Code refs: `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/Courses.vue`, `ifitwala_ed/ui-spa/src/types/contracts/student_hub/get_student_hub_home.ts`, `ifitwala_ed/ui-spa/src/types/contracts/student_hub/get_student_courses_data.ts`, `ifitwala_ed/api/course_schedule.py`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/docs/docs_md/task-delivery.md`, `ifitwala_ed/docs/docs_md/task-outcome.md`
Test refs: `ifitwala_ed/api/test_courses.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/Courses.test.ts`

Goal: turn Home into a calm daily routing surface without requiring strong self-management up front.

Scope:

- Add the top orientation strip for current or next class.
- Add a compact `My Work Board`.
- Add the dated learning timeline under the board.
- Keep `Soon` and `Later` server-curated from canonical dated records.
- Route every execution action back into course context rather than into context-free task shells.

Execution notes:

- Student Home now uses one aggregated payload for top orientation, board lanes, and timeline days.
- The first shipping cut favors system curation over manual orchestration.
- `Now / Soon / Later / Done` are currently server-curated from `Task Delivery` and `Task Outcome` truth, with no persistent student lane-move state yet.
- Student agency is intentionally light in this phase: continue work from the top strip, choose from `Now`, or open the dated timeline into course context.
- The board remains a planning layer, not a second grading system.
- Student shell now includes a route-aware secondary context sidebar for non-course student routes, so each main student area exposes local shortcuts without adding extra top-level navigation churn.
- Student course cards and the Home fallback course CTA now expose one server-owned learning-space readiness state before navigation:
  - `ready`
  - `shared_plan_only`
  - `awaiting_class_assignment`
  - `awaiting_class_plan`
- Entry surfaces now show the reason inline and only keep navigation active when the learning space is actually openable. This prevents students from clicking into a known unavailable course shell just to discover that it is not ready.

Exit criteria:

- Home answers what is happening now, what matters next, and where the student should continue.
- The board reduces decision load instead of increasing it.
- The student can move from Home into the right course context in one action.

## Phase 4: Focus, reflection, and progress loop

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/overlays/OverlayHost.vue`, `ifitwala_ed/ui-spa/src/composables/useOverlayStack.ts`, `ifitwala_ed/ui-spa/src/pages/student/StudentPortfolioFeed.vue`, `ifitwala_ed/ui-spa/src/components/portfolio/PortfolioFeedSurface.vue`, `ifitwala_ed/api/student_portfolio.py`, `ifitwala_ed/docs/student/portfolio_journal_architecture.md`
Test refs: None

Goal: turn the Hub from a planner into a real learning loop.

Scope:

- Add durable resume and progress state for lesson and activity continuation after explicit contract approval.
- Add a true focus execution surface anchored to course and lesson context.
- Add reflection prompts inside lesson and task completion flow.
- Add portfolio-promotion prompts when real evidence already exists.
- Add light completion feedback that rewards closure without introducing heavy gamification.

Execution notes:

- Focus mode should launch from resolved course context and preserve a clear return path to the full course page.
- Reflection should reuse the existing reflection and portfolio services, not create a second evidence system.
- If a durable student planning-state contract is approved later, this is the earliest sensible phase to add estimates, subtasks, and a personally managed `Now`.

Exit criteria:

- Students can continue where they left off.
- Students can enter a reduced-distraction execution mode from real course context.
- Reflection and portfolio capture happen inside the lesson loop, not only in a separate navigation silo.

## Phase 5: Interactive activity model, interoperability, and marketplace foundation

Status: Proposed
Code refs: `ifitwala_ed/docs/spa/10_student_learning_hub_proposal.md`, `ifitwala_ed/docs/docs_md/lesson-activity.md`, `ifitwala_ed/docs/docs_md/lesson-instance.md`, `ifitwala_ed/docs/docs_md/task-delivery.md`, `ifitwala_ed/docs/student/portfolio_journal_architecture.md`
Test refs: None

Goal: add richer lesson behavior without breaking native curriculum ownership or future portability.

Scope:

- Add native interactive activity modes such as reading, video, and low-stakes checks.
- Add lightweight checkpoint state that is separate from `Task Delivery`.
- Add cmi5-first launch and import architecture after explicit approval.
- Add SCORM compatibility only as a compatibility layer, not as the product model.
- Define the first marketplace-ready curriculum export/import boundary at the planned curriculum layer after explicit approval.

Marketplace readiness outcomes for this phase:

- Export/import should treat planned curriculum as the portable asset and student runtime as local state.
- The first marketplace-ready boundary should center on `Learning Unit` packages with their lessons and lesson activities.
- Imported packages should adapt into Ifitwala_ed's native curriculum structure rather than replace it.
- Package review, versioning, asset bundling, conflict resolution, and local course attachment all need explicit documented contracts before coding.

Exit criteria:

- The Hub supports native interactive lesson flow.
- External content compatibility does not become the canonical UX.
- Future marketplace work is unblocked by early architectural shortcuts.

## Delivery gates

Status: Proposed
Code refs: `ifitwala_ed/docs/spa/10_student_learning_hub_proposal.md`, `ifitwala_ed/docs/concurrency_01_proposal.md`, `ifitwala_ed/docs/concurrency_02_proposal.md`, `ifitwala_ed/docs/high_concurrency_03.md`
Test refs: None

Recommended delivery gates:

- Do not start heavy Home-board interaction work before Phase 1 payload contracts are approved.
- Do not ship focus mode before Phase 2 deep-linking into course context works cleanly.
- Do not add durable personal planning state without an explicit schema and contract decision.
- Do not add checkpoint state by reusing `Task Delivery`.
- Do not begin marketplace import/export implementation until the package boundary and file-governance rules are documented and approved.

Recommended implementation order for engineering:

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5

Parallelizable work after Phase 1:

- Course-detail backend aggregation and frontend rendering
- Home payload assembly and timeline rendering
- Reflection-entry integration design
- Focus-mode interaction design
