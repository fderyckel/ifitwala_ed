# Ifitwala_Ed Quiz Capacity Proposal

Status: Proposal only, non-canonical until approved
Code refs: `ifitwala_ed/api/courses.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/types/contracts/student_hub/get_student_course_detail.ts`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/assessment/04_task_notes.md`, `ifitwala_ed/docs/high_concurrency_03.md`
Test refs: `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`, `ifitwala_ed/curriculum/doctype/lesson/test_lesson.py`, `ifitwala_ed/curriculum/doctype/lesson_instance/test_lesson_instance.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`
Date: 2026-03-13

## Executive Summary

Status: Proposal
Code refs: `ifitwala_ed/api/courses.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/docs/assessment/04_task_notes.md`
Test refs: `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`

Recommendation: add a native quiz capability on top of the existing `Task` -> `Task Delivery` -> `Task Outcome` architecture, and integrate it into the current student hub course flow instead of introducing a second LMS runtime.

This is the best fit for the current workspace because:

- `/hub/student` already has a single aggregated course detail flow that renders `Learning Unit` -> `Lesson` -> `Lesson Activity` plus linked work.
- The assessment architecture is already locked around `Task`, `Task Delivery`, `Task Outcome`, `Task Submission`, and `Task Contribution`.
- External Moodle or Canvas embedding would split identity, routing, attempt state, and grade truth across two systems.
- Frappe LMS shows the right simplicity baseline for quizzes, while Moodle and Canvas show the deeper controls worth adopting selectively.

The recommended product direction is:

1. Keep `Task` / `Task Delivery` / `Task Outcome` as the official grading and reporting path.
2. Support both non-assessed practice quizzes and officially assessed quizzes.
3. Add a quiz-specific authoring and attempt layer below the current task/delivery/outcome path.
4. Integrate quiz launch, continue, and review directly into the existing student course detail surfaces.
5. Treat answer secrecy, idempotency, and concurrency as hard requirements from day one.

## Current Workspace Constraints

Status: Implemented current state
Code refs: `ifitwala_ed/api/courses.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
Test refs: `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`

- `get_student_course_detail()` already returns one aggregated student payload for course, units, lessons, lesson activities, linked tasks, and task deliveries.
- `CourseDetail.vue` already renders unit-level, lesson-level, and lesson-activity-level learning flow inside the student hub.
- `Lesson Activity` is a child table and currently supports `Reading`, `Video`, `Link`, `Discussion`, and `Interactive`. There is no live quiz-specific activity contract yet.
- `Task` already supports `task_type = Quiz`, but that is only classification today; there is no native question bank, randomized delivery, timed attempt, or auto-grading engine.
- `Task` can currently anchor to `Learning Unit` and `Lesson`, but not directly to `Lesson Activity`.
- `Task Delivery` can currently anchor to `Lesson Instance`, but not directly to `Lesson Activity`.

Implication: true quiz integration at the lesson-activity level is not available in the current contract and would require explicit approval for schema, API, and SPA changes.

## Benchmark Takeaways

Status: Proposal inputs
Code refs: None (external benchmark section)
Test refs: None

What to borrow from each benchmark:

- Frappe LMS: keep quiz authoring simple and product-friendly; its public README describes quizzes with single-choice, multiple-choice, and open-ended questions.
- Moodle: question banks, random questions from categories, time limits, multiple attempts, review controls, safe-exam style restrictions, and pre-created attempts for large synchronous starts.
- Canvas New Quizzes: item banks, random sets from banks, multiple attempts with score policy, waiting periods, build-on-last-attempt behavior, outcome alignment, and session/IP-aware controls.

What not to copy blindly:

- Do not introduce a second gradebook or second student navigation tree.
- Do not let the client assemble quiz correctness from generic CRUD calls.
- Do not adopt high-friction teacher forms that fight the product-manager mandate in this repository.

## Product Recommendation

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/docs/assessment/03_gradebook_notes.md`, `ifitwala_ed/docs/assessment/04_task_notes.md`
Test refs: None

### Recommendation

Build a native quiz layer that plugs into the existing assessment spine:

- authoring stays attached to the current curriculum and task model
- runtime delivery stays attached to `Task Delivery`
- official result stays attached to `Task Outcome`
- quiz attempts and item-level responses live in a quiz-specific runtime layer beneath delivery/outcome

This preserves one canonical institutional truth for:

- permissions
- grading
- analytics
- reporting
- student hub navigation

### Quiz Modes

The product should explicitly support more than one quiz mode:

- Practice quiz: formative, learner-facing, immediate feedback, retry-friendly, and excluded from official gradebook/reporting by default.
- Checked formative quiz: low-stakes, may show score/progress to student and teacher, but should still be configurable not to contribute to official reporting.
- Assessed quiz: contributes to the existing official assessment path through `Task Delivery` and `Task Outcome`.

Product rule: quiz does not automatically mean graded.

### Why not make Moodle or Canvas the primary runtime?

Because that would create avoidable drift in:

- authentication and session scope
- student navigation out of `/hub/student`
- grade publication timing
- retry/pass-threshold policy
- teacher authoring workflow
- operational support and auditability

### Why not copy Frappe LMS directly?

Because the current repository already has a locked assessment architecture and student hub route model. The right move is to adopt the good quiz patterns, not a parallel LMS stack.

## Proposed User Experience

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/api/courses.py`
Test refs: None

### Student Hub Integration

Inside the existing course detail experience:

- course, unit, and lesson cards show quiz badges and status counts
- lesson activity cards can render a quiz call-to-action when that activity is configured as quiz-backed
- the student sees `Start Quiz`, `Continue Attempt`, `Retry`, `View Result`, or `Awaiting Manual Review`
- active attempts open in a dedicated quiz player route inside the SPA, then return cleanly to the course context

Recommended route behavior:

- keep navigation base-less and inside the SPA router
- deep-link back to course, learning unit, lesson, and if approved, lesson activity context

### Teacher Authoring

Recommended teacher flow:

1. Create quiz-backed work from the current course/unit/lesson workflow, not from a detached admin list.
2. Reuse the current `Task` authoring and delivery concepts for assignment timing and grading policy.
3. Open a dedicated quiz builder for question pools, timing, attempts, and pass-threshold rules.
4. Allow creation from:
   - course level
   - learning unit level
   - lesson level
   - lesson activity level, but only after explicit contract approval

### Grading Flow

- auto-gradable questions score immediately on submit
- manually graded questions move the result into a pending review state
- the official released score still lands in the existing outcome path
- retry-until-threshold rules are enforced server-side, not by the client

### Practice Flow

- practice quizzes should support immediate per-question or end-of-attempt feedback
- practice quizzes should support high retry counts or unlimited retries when policy allows
- practice quizzes should support mastery thresholds without forcing an official gradebook entry
- practice quiz analytics can inform teachers, but must not be mistaken for released official results

## Capability Scope

Status: Proposed
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
Test refs: None

### Phase 1 Capability Set

Support in the first approved implementation:

- non-assessed practice quizzes
- officially assessed quizzes
- single-choice
- multiple-answer
- true/false
- short written answer with exact or normalized-match grading
- long written answer requiring manual grading
- random question selection from a reusable question bank or bank category
- question and choice shuffling
- time-limited attempts
- maximum attempts
- waiting period between attempts
- best-score policy for retries
- required mastery percentage to mark the quiz complete
- retry until threshold when policy allows it

### Result Policies

The first slice should support at least these result policies:

- Practice only: store attempt/completion/progress data, but no official released grade.
- Practice with mastery target: allow repeat until threshold, mark completion when threshold is met, but still keep it out of official reporting unless explicitly configured otherwise.
- Assessed: release an official score/result into the existing outcome path.

### Phase 2 Capability Set

Add after the first production slice is stable:

- matching
- ordering
- numeric/range questions
- fill-in-the-blank with multiple accepted patterns
- formula/calculated questions
- accommodation rules for extra time and attempt overrides
- proctoring or safe-exam integrations where justified

### Explicit Product Rule

Do not block the first release on every question type. Ship the high-volume school cases first:

- single-choice
- multiple-answer
- true/false
- short answer
- essay
- question banks
- retries
- timers

## Security Model

Status: Proposed hard requirement
Code refs: `ifitwala_ed/docs/high_concurrency_03.md`, `ifitwala_ed/docs/assessment/04_task_notes.md`
Test refs: None

The security bar must assume students inspect:

- browser HTML
- network payloads
- console logs
- cached responses
- predictable URLs

### Non-Negotiable Controls

- Correct answers, scoring keys, distractor correctness, and pass/fail logic must never be included in the initial student quiz payload.
- Correctness metadata must never be rendered into hidden HTML, `data-*` attributes, or client-side stores just because the UI "doesn't show it".
- Production client code must not log quiz payloads, responses, or review data to the console.
- Review payloads after submission must be regenerated server-side according to a release policy; do not reuse the live attempt payload and merely hide fields with CSS or client branching.
- All quiz actions must use named workflow endpoints such as start, save response, submit attempt, continue attempt, and review attempt; no student-facing generic CRUD.
- Attempt access must be server-authorized against the current student and delivery scope on every request.
- Randomization seeds and selected question sets must be owned by the server.
- Rich text question content and feedback must be sanitized before storage and before rendering.
- Response endpoints should return `Cache-Control: no-store` for active attempt payloads.

### Direct URL and Scope Defense

Frappe LMS has had a public advisory for students reaching quiz forms by direct URL. This proposal should treat that as a design warning:

- route secrecy is not permission
- client gating is not permission
- only server-side authorization is permission

### Anti-Cheating Controls Worth Supporting

- one question per page for high-stakes mode
- optional delayed release of correct answers and explanations
- optional IP-range restriction for controlled assessments
- multi-session detection and audit trail for sensitive quizzes

## High-Concurrency Design

Status: Proposed hard requirement
Code refs: `ifitwala_ed/api/courses.py`, `ifitwala_ed/docs/concurrency_01_proposal.md`, `ifitwala_ed/docs/concurrency_02_proposal.md`, `ifitwala_ed/docs/high_concurrency_03.md`
Test refs: None

The quiz engine should follow the repository's concurrency rules from the start.

### Read Path

- keep the current aggregated student course detail endpoint pattern
- add quiz status summaries to the existing course payload rather than creating request waterfalls
- fetch only the active attempt page or active question block in the quiz player, not the entire answer key or full bank
- cache immutable published quiz-definition snapshots and question-bank metadata in Redis with explicit invalidation

### Write Path

- starting an attempt must be idempotent
- saving a response must be idempotent
- submitting an attempt must be idempotent
- lock scope must stay narrow; avoid rewriting large parent documents for every answer save
- manual grading fan-out, analytics recomputation, notifications, and release jobs should leave the request and run in workers

### Large Synchronous Exam Protection

For scheduled high-volume starts, borrow the Moodle idea of pre-created attempts:

- prebuild attempt shells and randomized question manifests before the open time
- do this in quiet hours or via background workers
- keep the open-window request path small: authenticate, attach the prebuilt manifest, serve the first page

### Observability

- log start/save/submit processed/skipped/failed counts
- keep per-quiz run summaries in logs or cache
- alert on overlap, queue backlog, and unusually slow attempt submission

## Data and Workflow Shape

Status: Proposed
Code refs: `ifitwala_ed/docs/assessment/04_task_notes.md`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
Test refs: None

This proposal intentionally avoids freezing exact new fieldnames before approval, but the required persisted concepts are:

- a quiz definition model
- a reusable question bank model
- question versions or immutable published snapshots
- an attempt model per student and delivery
- an attempt-item or response model for each presented question

Recommended invariant:

- `Task Delivery` remains the assignable object
- `Task Outcome` remains the official result object
- quiz-specific runtime records are subordinate to delivery/outcome, never a replacement for them

Recommended result boundary:

- practice quiz attempts may persist learner progress and completion signals without becoming official released grades
- only assessed quiz configurations should feed the official grade/reporting path by default

This avoids a second reporting pipeline and keeps gradebook parity.

## Contract Matrix

Status: Proposed
Code refs: `ifitwala_ed/api/courses.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
Test refs: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`

| Concern | Current contract | Proposed contract | Approval needed |
|---|---|---|---|
| Schema / DocType | `Task` can classify a row as `Quiz` but there is no native quiz engine or lesson-activity quiz link. | Add approval-gated persisted quiz definition, question bank, attempt, and response models; add explicit result-policy support for practice vs assessed quizzes; add an explicit lesson-activity integration contract if activity-level launch is required. | Yes |
| Controller / workflow logic | Assessment truth flows through `Task Delivery` and `Task Outcome`. | Keep that truth path; add quiz-specific workflow endpoints and services for start/save/submit/review, with server-owned distinction between practice and assessed outcomes. | Yes |
| API endpoints | `get_student_course_detail()` aggregates course, unit, lesson, activity, and linked task data. | Extend the student hub payload with quiz summaries; add dedicated quiz-player endpoints with server-owned authorization and release policy. | Yes |
| SPA / student surfaces | `CourseDetail.vue` renders units, lessons, activities, and linked work. | Add quiz badges, activity-level quiz cards, a dedicated quiz player route, and result/retry states inside the student hub. | Yes |
| Reports / gradebook | Current reporting trusts the task/outcome model. | Keep official quiz grades flowing into the existing outcome/reporting pipeline; do not add a separate quiz gradebook. | Yes |
| Scheduler / background jobs | No quiz-specific workload exists. | Add bounded background jobs for pre-creating attempts, releasing results, analytics, and notifications where needed. | Yes |
| Tests | No end-to-end quiz path exists. | Add backend endpoint tests, attempt idempotency tests, payload secrecy tests, student hub contract tests, and concurrency-oriented submission tests. | Yes |

## Decision Options

Status: Proposed evaluation
Code refs: `ifitwala_ed/docs/assessment/04_task_notes.md`, `ifitwala_ed/api/courses.py`
Test refs: None

### Option A: External Moodle or Canvas as the primary quiz runtime

Pros

- mature feature set immediately
- broad question-type coverage
- known exam controls

Cons

- splits the student experience out of the current hub
- duplicates grade and permission logic
- raises identity, sync, and reporting drift risk

Blind spots

- operational complexity of two systems
- unclear ownership of grade publication timing

Risks

- long-term product fragmentation
- support burden and inconsistent student UX

### Option B: Directly adopt Frappe LMS quiz runtime

Pros

- close ecosystem fit
- simpler product model than Moodle

Cons

- still creates a parallel LMS runtime next to the current task/outcome architecture
- does not automatically fit the current lesson/activity/student-hub contract

Blind spots

- migration and contract overlap with the existing assessment spine

Risks

- dual assessment models inside one product

### Option C: Native quiz capability on top of current task delivery and outcome flow

Pros

- preserves one canonical grade/reporting path
- fits the current `/hub/student` course experience
- aligns with current repository rules on server-owned invariants
- cleanly supports practice quizzes that do not become official grades by default

Cons

- higher implementation cost than embedding an external tool
- requires approval-gated schema and API work

Blind spots

- exact authoring UX shape still needs a product decision
- question-versioning policy needs explicit design before implementation

Risks

- under-scoping security and concurrency would create a fragile first release

Recommended option: C

## Approval Gates and Likely Implementation Surface

Status: Proposed next step
Code refs: `ifitwala_ed/api/courses.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/types/contracts/student_hub/get_student_course_detail.ts`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
Test refs: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`

If this proposal is approved, the first implementation planning pass should focus on these existing files:

- `ifitwala_ed/api/courses.py`
- `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/student_hub/get_student_course_detail.ts`
- `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`
- `ifitwala_ed/assessment/doctype/task/task.json`
- `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`

And on new approval-gated quiz-specific models, services, APIs, and tests that are not yet present in the workspace.

Recommended first delivery slice after approval:

1. lesson-level quiz launch in student hub
2. explicit practice-vs-assessed quiz policy
3. question bank with random draw
4. single-choice, multiple-answer, true/false, short answer, essay
5. timed attempts and attempt caps
6. retry-until-threshold
7. strict answer-secrecy tests
8. idempotent start/save/submit tests

Activity-level linking should be a second contract step unless product insists it must ship in the first slice.

## External References

Status: Benchmark sources
Code refs: None
Test refs: None

- Frappe LMS README: [GitHub - frappe/lms](https://github.com/frappe/lms)
- Moodle Quiz activity: [MoodleDocs - Quiz activity](https://docs.moodle.org/en/Quiz_activity)
- Moodle Quiz settings: [MoodleDocs - Quiz settings](https://docs.moodle.org/en/Quiz_settings)
- Moodle Question banks: [MoodleDocs - Question banks](https://docs.moodle.org/500/en/Question_banks)
- Canvas New Quizzes overview: [Instructure - Create a quiz using New Quizzes](https://community.instructure.com/en/kb/articles/661046-how-do-i-create-a-quiz-using-new-quizzes)
- Canvas New Quizzes settings: [Instructure - Manage settings for a quiz in New Quizzes](https://community.instructure.com/en/kb/articles/661070-how-do-i-manage-settings-for-a-quiz-in-new-quizzes)
- Canvas item banks and random sets: [Instructure - Add all items or a random set from an item bank](https://community.instructure.com/en/kb/articles/661082-how-do-i-add-all-items-or-a-random-set-from-an-item-bank-to-a-quiz-in-new-quizzes)
- Frappe LMS security overview: [GitHub - frappe/lms security](https://github.com/frappe/lms/security)
