# Ifitwala_Ed — Phase 4 Student Feedback Navigator And Reply RFC

Status: **Implemented runtime companion / non-authoritative planning history**
Audience: Product, Engineering, UX, and coding agents
Scope: Phase 4 student-facing released feedback navigator, instructor reply/clarification loop, guardian read-only assessment feedback access, and migration away from legacy single-channel outcome release on portal assessment surfaces
Last updated: 2026-04-22

Important note:

- This RFC started as the approved Phase 4 execution plan and now also records the implemented runtime baseline.
- It does **not** approve final schema names, field names, endpoint names, route names, or permission changes by itself.
- `03_gradebook_notes.md` and `07_feedback_annotation_ecosystem_contract.md` have been updated with the current runtime boundary; sections below that still say **Planned** should be read as planning history unless section 1 overrides them.
- This RFC extends the Phase 2 and Phase 3 runtime introduced by `09_feedback_records_and_publication_rfc.md` and `11_phase3_teacher_authoring_and_comment_bank_rfc.md`.

Related docs:

- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`
- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`
- `ifitwala_ed/docs/assessment/09_feedback_records_and_publication_rfc.md`
- `ifitwala_ed/docs/assessment/11_phase3_teacher_authoring_and_comment_bank_rfc.md`
- `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`
- `ifitwala_ed/docs/curriculum/05_student_and_guardian_learning_experience_proposal.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_08_cross_portal_governed_attachment_preview_contract.md`

---

## 0. Bottom Line

Phase 4 should make released assessment feedback usable for learners without turning the product into a second document app.

That means:

- students open a **feedback navigator**, not a naked annotated PDF
- instructors handle student replies and clarifications inside the existing gradebook drawer
- guardians get a bounded, read-only released view only when the publication channel allows it
- student and guardian portals start consuming the assessment-owned feedback and grade publication channels instead of relying only on legacy `Task Outcome.is_published`

The primary product outcome is lower cognitive load for students and faster, cleaner follow-up for instructors.
The primary engineering outcome is one bounded released-feedback read model plus named mutations, with no client waterfalls.

---

## 1. Current Baseline

Status: **Implemented Phase 4 baseline**

Code refs:

- `ifitwala_ed/assessment/task_feedback_service.py`
- `ifitwala_ed/assessment/task_feedback_thread_service.py`
- `ifitwala_ed/api/gradebook.py`
- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/gradebook_writes.py`
- `ifitwala_ed/api/released_feedback.py`
- `ifitwala_ed/api/outcome_publish.py`
- `ifitwala_ed/api/teaching_plans.py`
- `ifitwala_ed/api/courses.py`
- `ifitwala_ed/api/guardian_monitoring.py`
- `ifitwala_ed/ui-spa/src/components/assessment/ReleasedFeedbackNavigator.vue`
- `ifitwala_ed/ui-spa/src/components/assessment/ReleasedFeedbackPdfViewer.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookPdfWorkspace.vue`
- `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
- `ifitwala_ed/ui-spa/src/pages/student/StudentReleasedFeedbackDetail.vue`
- `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianReleasedFeedbackDetail.vue`
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/gradebook/feedback_workspace.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/assessment/released_feedback_detail.ts`

Test refs:

- `ifitwala_ed/api/test_gradebook.py`
- `ifitwala_ed/api/test_released_feedback.py`
- `ifitwala_ed/assessment/test_task_feedback_service.py`
- `ifitwala_ed/assessment/test_task_feedback_thread_service.py`
- `ifitwala_ed/assessment/test_task_feedback_comment_bank_service.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`
- `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`
- `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentQuiz.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts`

Phase 3 already provides:

- one bounded teacher drawer bootstrap
- version-bound `Task Feedback Workspace` records per outcome and selected submission version
- summary fields and structured feedback items
- separate feedback and grade visibility state in the drawer runtime
- a drawer-owned `pdf.js` workspace with draft annotation overlays
- a minimal teacher-owned comment bank

Phase 4 now adds:

- student released-feedback detail routes from course-context work and quiz review
- guardian read-only released-feedback handoff from guardian monitoring
- first-class pinned priorities on the feedback workspace
- first-class reply threads and learner-state tracking
- drawer-first instructor reply and resolve handling
- immutable `assessment_submission` evidence as the default student document surface, with structured overlays layered in the navigator

Current runtime boundaries that still remain after Phase 4:

- the staff drawer still shows the legacy publish/unpublish action alongside the newer channel-state save action
- guardian released-feedback detail is intentionally text-first and does not yet render a guardian document surface
- student reply entry points currently target feedback-item threads; priority and summary reply entry points are not yet exposed in the portal UI
- OCR hardening, derived annotated export artifacts, and feedback analytics remain later phases

---

## 2. Phase 4 Goal And Non-Goals

Status: **Planned**

### Goal

Make released assessment feedback understandable, navigable, and actionable for students while keeping instructor follow-up work inside the existing gradebook drawer.

### Non-goals

Phase 4 does **not**:

- create a separate student PDF-review app
- move instructor follow-up out of the gradebook drawer
- turn guardian surfaces into a second LMS
- move reporting truth away from `Task Outcome` and `Task Outcome Criterion`
- embed full released feedback detail inside the main LMS bootstrap payload
- ship OCR hardening or artifact export as the headline deliverable of this phase

---

## 3. Product And UX Posture

Status: **Locked for planning**

### 3.1 Student UI posture

Student assessment feedback should feel:

- summary-first
- calm
- easy to scan
- easy to act on
- visually premium without becoming visually busy

Rules:

- lead with synthesis before detail
- keep one obvious next action visible at a time
- show short, purposeful labels instead of internal workflow jargon
- avoid walls of comments or table-heavy result layouts
- preserve the current student shell, typography, card surfaces, chips, and route flow instead of inventing a second design language

### 3.2 Instructor UI posture

Instructor Phase 4 work should feel like an extension of the current drawer, not a new moderation inbox.

Rules:

- student replies appear in the same drawer where the instructor authored the feedback
- replies and clarification requests must be triaged in context of the exact released feedback item or summary point
- the drawer should keep the authored feedback, reply state, and released channel state visible together
- no silent “student replied” state; blocked or pending actions need explicit labels

### 3.3 Guardian UI posture

Guardian surfaces remain awareness-first.

Rules:

- guardians can read released assessment feedback only when the publication channel allows it
- guardians do not author replies in this phase
- guardian assessment feedback remains a bounded handoff, not a second full student workflow

---

## 4. Integration Map Across Current Surfaces

Status: **Planned integration contract**

### 4.1 Staff surface stays where it is

Instructor authoring, release changes, and reply handling remain in:

- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookPdfWorkspace.vue`
- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/gradebook_writes.py`
- `ifitwala_ed/assessment/task_feedback_service.py`

Phase 4 extends those surfaces.
It does not add a second instructor review workspace.

### 4.2 Student surface stays course-context-first

Student non-quiz work remains anchored in:

- `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
- `ifitwala_ed/api/teaching_plans.py`
- `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`

Student quiz runtime remains in:

- `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`

Phase 4 should add a course-context assessment feedback handoff from assigned work and released results.
It should not create a disconnected assessment island with no course context.

### 4.3 Guardian surface stays awareness-first

Guardian read models remain anchored in:

- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/api/guardian_monitoring.py`
- `ifitwala_ed/api/guardian_home.py`

Phase 4 should upgrade guardian assessment visibility through those existing surfaces rather than replacing them with a second student-style navigator as the default landing page.

### 4.4 Assessment remains the owner of feedback truth

Phase 4 continues to treat assessment as the source of truth for:

- released summary
- pinned priorities
- anchored feedback items
- reply threads
- publication channel state

Curriculum and LMS surfaces remain consumers and handoff points.
They must not become the source of truth for feedback records or release logic.

### 4.5 Governed file ownership for Phase 4

Phase 4 must reuse the existing governed file split instead of inventing a new assessment file purpose.

Rules:

- immutable learner evidence remains `assessment_submission`
- returned marked or exported feedback files remain `assessment_feedback`
- the student navigator should default to the immutable `assessment_submission` evidence surface when a governed file surface is authorized and available
- released structured feedback is layered onto that evidence context through assessment-owned records
- `assessment_feedback` is an optional derived artifact for download, export, print, or exceptional fallback; it is not the default in-product viewer input

Engineering rule:

- do not make student or guardian feedback reading depend on derived artifact generation before the released feedback can be consumed
- do not collapse evidence and returned-feedback semantics into one portal file contract

---

## 5. Recommended Student Feedback Navigator

Status: **Planned**

The student-facing released-feedback experience should open in this order:

1. overall summary
2. pinned priorities
3. rubric snapshot
4. filterable feedback list
5. document viewer with jump-to-anchor behavior

### 5.1 Required navigator sections

#### Summary block

Must show:

- overall synthesis
- strengths
- improvements
- next steps
- visible submission-version label when multiple versions exist

#### Pinned priorities block

Must show:

- three to five short priority items
- clear “what to do next” phrasing
- jump links into the relevant feedback items or document anchors

Pinned priorities must become first-class feedback data, not be inferred loosely from comment order.

#### Rubric snapshot block

Must show:

- criterion name
- official criterion outcome or level where published
- linked teacher comment where released

The rubric snapshot remains derived from `Task Outcome Criterion`.
It must not redefine rubric truth.

#### Filterable feedback list

Must support lightweight filters by:

- all comments
- strengths
- improvements/issues
- questions
- next steps
- resolved or acknowledged state when applicable later

The list should stay compact and readable.
It should not turn into a giant threaded inbox.

#### Document viewer block

Must:

- remain subordinate to the navigator summary
- open only when evidence/document context exists
- support jump-to-anchor from the feedback list
- support jump-back from the document to the selected feedback entry

The student should never be dropped directly into the document as the first experience.

Default file-surface rule:

- the navigator document surface should render the bound immutable `assessment_submission` evidence by default when that evidence has an authorized governed preview/open surface
- released structured feedback remains the primary product layer and is rendered in navigator UI and overlay/context form, not as flattened document truth
- `assessment_feedback` derived artifacts may be offered as optional returned files or exports, but they are not the primary viewer input for Phase 4
- when no governed submission preview is available, the navigator should remain summary-first and may degrade to metadata-only or explicit open/download actions instead of blocking the released feedback experience

### 5.2 Premium UI rules

The student navigator should preserve the current portal design language:

- card-first sectioning
- clear vertical rhythm
- restrained chip usage
- prominent but not oversized summary typography
- one primary action or focus area per section

Avoid:

- giant tables
- dense moderation-style timelines
- toolbars that feel like staff UI leaked into the portal
- a full-width PDF wall above the synthesis

---

## 6. Instructor Reply And Clarification Loop

Status: **Planned**

Phase 4 should add a bounded dialogue loop on top of the released feedback records.

### 6.1 Student actions

The student should be able to:

- reply to a feedback item
- ask for clarification
- mark a feedback item as understood
- mark a feedback item as acted on

These are pedagogical workflow actions.
They are not reporting writes.

### 6.2 Instructor actions

The instructor should be able to:

- see student replies inside the existing gradebook drawer
- answer in context of the original feedback item or summary point
- mark the thread resolved
- see whether the learner has acknowledged or acted on the item

### 6.3 Thread model rules

Rules:

- replies remain first-class assessment records, not one appended text blob
- each reply keeps author, timestamp, parent thread identity, and workflow state
- replies bind to the same outcome and selected submission version as the released feedback they reference
- instructor reply handling remains drawer-first

### 6.4 UX rules for the reply loop

- replies must be visible in context of the original comment
- the instructor should not need to switch to another page to answer
- the student should not need to hunt across multiple pages to find the teacher response
- if replies are disabled by policy or publication state, the UI must say why

---

## 7. Publication And Release Strategy For Phase 4

Status: **Planned**

Phase 4 is where portal assessment surfaces begin consuming the assessment-owned publication model.

### 7.1 Required release channels

Phase 4 should implement the existing target channel model:

- feedback channel:
  - `hidden`
  - `student`
  - `student_and_guardian`
- grade channel:
  - `hidden`
  - `student`
  - `student_and_guardian`

### 7.2 Transition rule

During the transition:

- staff drawer release controls continue to write the assessment-owned publication state
- legacy `Task Outcome.is_published` may remain as compatibility support for older result surfaces
- new student and guardian feedback navigator surfaces must read the new channel state, not infer visibility only from `is_published`

### 7.3 Product-preferred actions

Preferred instructor shortcuts remain:

- release feedback
- release both

Grade-only release stays explicit but should not dominate the primary teacher flow.

### 7.4 Audience rule

Guardian visibility must never outrun student visibility for the same channel.

---

## 8. Read-Model And Route Strategy

Status: **Planned**

### 8.1 Student route strategy

Phase 4 should keep the student in the course namespace.

Recommended direction:

- assigned work or released-result chips in `CourseDetail.vue` hand off to a dedicated released-feedback detail surface inside the student course flow
- quiz-backed work may hand off from `StudentQuiz.vue` or the same assigned-work route context

Rules:

- keep the student oriented to course and task context
- do not force a global assessment-results page before they can understand one item of feedback

### 8.2 Guardian route strategy

Guardian assessment feedback should route from:

- `GuardianMonitoring.vue`
- and, where useful, `GuardianStudentShell.vue`

The guardian route should open the same released-feedback detail in read-only guardian mode rather than a separate bespoke workflow.

Guardian file-access rule:

- guardian mode must resolve its own surface-authorized file DTO; it must not inherit student-authorized file actions implicitly
- when feedback is guardian-visible but the underlying evidence or artifact file surface is not guardian-authorized, the guardian detail must degrade cleanly to text-only or metadata-only released feedback
- guardian read-only access to a document pane is allowed only when the governed surface explicitly authorizes that file read for guardian context

### 8.3 Read-model shape rule

Phase 4 should use:

- one bounded navigator detail read for one released assessment context
- small indicator fields on LMS/home/guardian summary surfaces

It should **not**:

- dump full feedback detail into `get_student_learning_space()`
- dump full feedback detail into guardian monitoring snapshots
- fetch each comment, thread, or artifact through client waterfalls

File DTO rule:

- the navigator detail payload should reuse the existing governed attachment preview contract and shared `attachment_preview` DTO direction rather than inventing an assessment-only file transport shape
- stable Ed-owned `open_url`, `preview_url`, and `thumbnail_url` actions should remain the file/action contract when present
- additive rollout remains valid: some released assessment contexts may still be open/download-only until richer governed preview routes exist

---

## 9. High-Concurrency And Request-Shape Rules

Status: **Locked planning rule**

Code refs:

- `ifitwala_ed/docs/high_concurrency_contract.md`
- `ifitwala_ed/api/teaching_plans.py`
- `ifitwala_ed/api/courses.py`
- `ifitwala_ed/api/guardian_monitoring.py`

Phase 4 must follow these request-shape rules:

1. Student LMS bootstrap stays bounded.
   Do not inflate `get_student_learning_space()` with full released-feedback detail.
2. Guardian monitoring stays bounded.
   Keep detailed assessment feedback as a handoff, not an inline expansion of all released comments.
3. One detail open should use one bounded read.
   The navigator detail should come from one assessment-owned read model for one released context.
4. No client polling loops for replies.
   Refresh should be user-driven, route-driven, or signal-driven from named mutations.
5. No document/comment waterfall.
   The detail payload should include summary, priorities, comment list, reply thread state, and authorized file/display actions together.
6. File access remains Ed-owned and governed.
   No raw private paths and no direct Drive grant calls from the SPA.
7. The file block must stay purpose-aware.
   Use `assessment_submission` as the default viewer input and keep `assessment_feedback` as optional derived artifact behavior rather than a second source of truth.

Hot-path implication:

- student home, course detail, and guardian monitoring should receive only enough data to decide whether released feedback exists and where to route the user next
- the heavier navigator payload should be loaded only on explicit entry into released assessment feedback

---

## 10. Data And Domain Extensions Required Before Implementation

Status: **Planned**

Phase 4 needs additional assessment-owned records or extensions for:

- pinned priorities as first-class feedback data
- reply threads
- learner acknowledgement and acted-on state
- released navigator detail projection

Rules:

- do not collapse priorities or replies into one generic JSON blob
- keep version binding explicit
- keep publication state separate from reporting truth

This is the main structural gap between the current Phase 3 runtime and the planned Phase 4 UX.

---

## 11. Phase 4 Sub-Phases

Status: **Planned rollout**

### 11.1 Phase 4a — Contract and read-model extension

Deliver:

- lock the student and guardian navigator contract
- add the missing assessment-owned structures for priorities and replies
- add a bounded released-feedback detail read model
- define the transition from legacy `is_published` to channel-aware portal reads

Acceptance gate:

- the contract is precise enough to implement portal reads without inventing fields later

### 11.2 Phase 4b — Student navigator shell

Primary surfaces:

- `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
- student router entries under `ui-spa/src/router/index.ts`
- a new student released-feedback detail surface under the existing student portal shell

Deliver:

- summary-first navigator UI
- priorities block
- rubric snapshot
- filterable feedback list
- document jump behavior

Acceptance gate:

- a student can understand released feedback without starting in the document viewer

### 11.3 Phase 4c — Instructor reply handling in the drawer

Primary surfaces:

- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`
- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/gradebook_writes.py`

Deliver:

- reply visibility in the drawer
- instructor response flow
- thread resolution flow

Acceptance gate:

- the instructor can answer a clarification request without leaving the drawer

### 11.4 Phase 4d — Guardian released-feedback handoff

Primary surfaces:

- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- guardian assessment read models

Deliver:

- read-only guardian handoff into released feedback where publication allows it
- channel-aware rendering that hides unreleased grade or feedback content

Acceptance gate:

- guardian assessment visibility matches channel rules and never exceeds student visibility

### 11.5 Phase 4e — Release migration on portal assessment surfaces

Deliver:

- portal assessment surfaces consume channel-aware release state
- legacy `is_published` dependence is reduced to compatibility paths only

Acceptance gate:

- the student can see feedback without grade when policy allows it

---

## 12. Acceptance Gates For The Whole Phase

Status: **Planned**

Phase 4 is successful when all of the following are true:

1. Students open a released-feedback navigator, not a naked annotated PDF.
2. Students can see released feedback even when grade remains hidden.
3. Instructors can handle clarifications in the existing gradebook drawer.
4. Guardians can read released assessment feedback only when the feedback channel allows it.
5. The student and guardian portals no longer depend solely on legacy `Task Outcome.is_published` for new assessment-feedback visibility.
6. Course detail, guardian monitoring, and related portal shells remain bounded under the high-concurrency contract.
7. Released feedback clearly identifies the submission version it refers to when version history exists.

---

## 13. Main Risks

Status: **Planned risk register**

- **UX drift** if the student navigator becomes a second task app detached from `CourseDetail.vue`.
- **Instructor friction** if reply handling creates a second inbox outside the drawer.
- **Payload bloat** if navigator detail is shoved into LMS or guardian summary bootstraps.
- **Permission leaks** if guardian reads reuse student routes or bypass Ed-owned file access.
- **Data drift** if priorities and replies are stored as opaque blobs with weak structure.
- **Release confusion** if legacy `is_published` and new channel state are mixed without a clear transition contract.

---

## 14. Recommended Next Safe Move

Status: **Ready**

The next safe move after this RFC is a docs-only approval pass on four exact design decisions before schema or API work starts:

1. the student route and surface shape for released assessment feedback
2. the guardian read-only scope and entry point
3. the reply-thread and pinned-priority record shape
4. the transition rule between legacy `Task Outcome.is_published` and the new channel-aware portal reads

After those are approved, implementation should start with the assessment read-model and reply-domain slice, not with portal-only UI scaffolding.
