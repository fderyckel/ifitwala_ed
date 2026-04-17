# Ifitwala_Ed — Feedback Records And Publication RFC

Status: **Planned implementation RFC / non-authoritative until canonical runtime docs are updated**
Audience: Product, Engineering, UX, and coding agents
Scope: Phase 2 design for structured feedback records, publication states, version binding, drawer integration, annotation readiness, and minimal comment-bank scope
Last updated: 2026-04-17

Important note:

- This RFC translates the canonical assessment contracts into an implementation-ready Phase 2 design.
- It does **not** approve schema names, field names, endpoint names, or cross-module behavior changes by itself.
- If implementation lands, update `03_gradebook_notes.md`, `04_task_notes.md`, and `07_feedback_annotation_ecosystem_contract.md` in the same change.
- This RFC supersedes the older release-visibility direction recorded in `08_assessment_gradebook_approved_direction_2026-04-17.md`.

Related docs:

- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`
- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`
- `ifitwala_ed/docs/assessment/08_assessment_gradebook_approved_direction_2026-04-17.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`

---

## 0. Bottom Line

The next implementation unit should be a **bounded feedback layer inside the assessment boundary**, not a separate platform.

That layer should:

- keep `Task Outcome` and `Task Outcome Criterion` as official academic truth
- keep `Task Contribution` as grading input
- add version-bound structured feedback records adjacent to those models
- add explicit publication state for feedback and grade channels
- keep annotation as one authoring surface over those records, not the source of truth

The goal is to make the drawer capable of real feedback authoring without reopening the grading truth model.

---

## 1. Current Baseline And Why Phase 2 Exists

Status: **Implemented baseline with contract gaps**

Code refs:

- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/gradebook_writes.py`
- `ifitwala_ed/api/outcome_publish.py`
- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`

Test refs:

- `ifitwala_ed/api/test_gradebook.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`

Current workspace reality:

- one bounded drawer bootstrap exists for delivery, student, outcome, selected evidence, version summaries, contribution context, and allowed actions
- evidence is already versioned and governed through Ed-owned preview/open routes
- the current release model still collapses to one `Task Outcome.is_published` state
- there is no first-class feedback record layer yet
- there is no minimal comment bank yet
- there is no annotation-readiness or OCR fallback contract in the live drawer runtime

Why Phase 2 exists:

- the current drawer is a good grading/evidence shell, but not yet a true feedback workspace
- the product now needs explicit feedback ownership, publication rules, and version binding before annotation UI expands

---

## 2. Phase 2 Goals And Non-Goals

Status: **Planned**

Code refs: None yet
Test refs: None yet

Goals:

- define the bounded feedback model inside assessment
- define publication semantics for feedback and grade channels
- define version-binding and stale-feedback behavior
- define how the drawer reads and writes feedback without request waterfalls
- define minimum teacher productivity support through a comment bank
- define annotation readiness and reduced-mode behavior for unreadable PDFs

Non-goals:

- approving final schema names or field names
- approving final endpoint names or payload shapes
- shipping the student feedback navigator in this phase
- shipping full OCR enforcement in this phase
- changing reporting ownership away from `Task Outcome` and `Task Outcome Criterion`

---

## 3. Recommended Assessment-Owned Feedback Model

Status: **Planned target model**

Code refs:

- `ifitwala_ed/docs/assessment/04_task_notes.md`
- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`

Test refs: None yet

The feedback layer should stay inside assessment and should be reasoned about as a small set of conceptual records.

| Conceptual record | Owns | Must know | Must not replace |
| --- | --- | --- | --- |
| Feedback item | one atomic teacher feedback record | outcome, selected evidence version, optional anchor, feedback intent, optional rubric link, visibility/workflow state | `Task Contribution`, `Task Outcome` |
| Feedback summary | overall teacher summary for one review context | strengths, priorities, next steps, summary text, selected evidence version | official outcome truth |
| Feedback response thread | learner or teacher follow-up on one feedback item or summary point | author, timestamp, reply state, acknowledgement or acted-on state | moderation or reporting truth |
| Feedback publication view | release state for feedback and grade channels | channel, audience reach, release timing, audit actor | official score storage |
| Feedback artifact linkage | optional link to returned annotated/exported artifact | governed artifact reference, selected evidence version, publication snapshot | learner submission |

Recommended aggregate boundary:

- one assessment-owned feedback workspace exists per outcome and selected evidence version
- that workspace may contain many feedback items plus one summary
- publication state is adjacent to that workspace, not hidden in the SPA
- replies attach to feedback items or summary points, not to `Task Contribution`

Design rules:

- feedback records must be created and queried inside assessment-scoped services
- feedback records may reference rubric criteria, but they do not become rubric truth
- one teacher action may write both grading input and feedback, but the server must preserve their separate ownership
- feedback records must never be the only place where official score or completion truth lives

---

## 4. Publication Model

Status: **Planned target model**

Code refs:

- `ifitwala_ed/api/outcome_publish.py`
- `ifitwala_ed/api/gradebook_writes.py`
- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`

Test refs: None yet

Phase 2 should replace the current single-bit publish model with two explicit publication channels:

| Channel | Allowed states |
| --- | --- |
| Feedback | hidden, visible to student, visible to student and guardian |
| Grade / rubric outcome | hidden, visible to student, visible to student and guardian |

Invariants:

- guardian visibility never exceeds student visibility for the same channel
- feedback may be visible while grade remains hidden
- release decisions are explicit and reversible until reporting or institutional lock rules prevent reversal
- publication changes must be audit-tracked server-side
- student and guardian surfaces render only what the publication model authorizes for that audience

Teacher-facing implication:

- the drawer should eventually expose distinct actions for releasing or hiding feedback and grade
- the product may still offer a combined “release both” shortcut, but combined release is convenience, not truth

Implementation rule:

- do not overload `grading_status` or similar workflow labels to carry publication truth
- do not keep audience release semantics implicit in notifications or portal heuristics

---

## 5. Version Binding And Stale Feedback Behavior

Status: **Planned target model**

Code refs:

- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/assessment/task_submission_service.py`
- `ifitwala_ed/assessment/task_contribution_service.py`

Test refs:

- `ifitwala_ed/api/test_gradebook.py`

Feedback must bind to the selected evidence version, not float across a learner's submission history.

Rules:

- when a teacher opens a specific submission version in the drawer, new feedback authored in that context binds to that version
- switching the selected version changes the authoring context; it does not silently retarget existing feedback
- when a learner resubmits, prior feedback remains historical and visible in history/audit views
- resubmission marks earlier feedback stale for current review unless a teacher explicitly reuses or carries it forward
- if no learner upload exists, a teacher-created evidence stub may still serve as the bound review context
- any derived feedback artifact must correspond to one evidence version and one publication snapshot

Product implication:

- the drawer should always make the current evidence version obvious before feedback is authored or published
- student-facing released feedback should indicate which submission version it refers to when there is version history

---

## 6. Drawer Read And Write Responsibilities

Status: **Planned target model**

Code refs:

- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/gradebook.py`
- `ifitwala_ed/api/gradebook_writes.py`
- `ifitwala_ed/ui-spa/src/lib/services/gradebook/gradebookService.ts`

Test refs:

- `ifitwala_ed/api/test_gradebook.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`

The drawer should remain the only rich teacher workspace.
Phase 2 should extend the current bounded drawer model instead of introducing a second document-review surface.

Recommended read-model responsibilities:

| Drawer concern | Owner | Notes |
| --- | --- | --- |
| Delivery policy and student identity | current gradebook drawer bootstrap | already live |
| Selected evidence version and governed file actions | current task-submission serialization path | already live |
| Feedback records and summary for selected version | future assessment feedback read layer | add as bounded drawer block |
| Publication state for feedback and grade channels | future publication read layer inside assessment | must be explicit, not inferred |
| Annotation readiness | server-owned readability/OCR status for selected evidence version | do not guess in Vue |
| Comment bank entries relevant to the current teacher context | future comment-bank read layer | keep bounded and scoped |

Recommended mutation responsibilities:

| Mutation category | Owner | Notes |
| --- | --- | --- |
| Save grading input | existing contribution/outcome services | current path remains |
| Save feedback draft | future assessment feedback write layer | separate from official grade truth |
| Change publication state | future named publication operations | separate feedback and grade channels |
| Save or update comment-bank entries | future comment-bank write layer | scoped teacher productivity feature |
| Mark reply / acknowledgement / acted-on state | future feedback response operations | not a reporting write |

Coordination rule:

- if one user action changes both grading input and feedback draft, the server may orchestrate both writes in one named operation or one controlled transactional path
- the client must still treat grading truth and feedback truth as separate concerns

Concurrency rule:

- the drawer remains one bounded bootstrap read plus named mutations
- do not add per-tab waterfalls or client polling loops for feedback blocks

---

## 7. Annotation Readiness And OCR Fallback

Status: **Planned target model**

Code refs:

- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`

Test refs: None yet

Annotation should behave according to server-known readiness of the selected evidence version.

Readiness modes:

| Mode | Teacher capability |
| --- | --- |
| Text-readable | text highlight, anchored comments, search, quote-based anchoring |
| Unreadable but previewable | area comments, page comments, ink, governed preview/open |
| Unavailable / broken preview | clear inline reason, governed fallback action, no fake annotation affordances |

Rules:

- preview availability and annotation readiness are different concerns
- unreadable PDFs should still be previewable when governed file access allows it
- the SPA must not render highlight-based tools before the server marks the evidence readable
- OCR or repair may later upgrade an evidence version from reduced mode to text-readable mode, but the product should not block all review until that happens

---

## 8. Minimal Comment Bank Scope

Status: **Planned target model**

Code refs:

- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`

Test refs: None yet

The first serious teacher authoring version should include a minimal comment bank.

Minimum product expectations:

- teachers can insert reusable comments without leaving the drawer
- comment-bank entries are scoped enough to stay relevant to the current teaching context
- the drawer supports quick insertion into anchored comments, summary text, or general feedback areas where appropriate

Minimum design constraints:

- do not require a large taxonomy or institutional setup before the feature is usable
- do not make comment banks a separate app or detached settings module for day-one use
- do not block feedback authoring when no reusable comments exist

Follow-on enhancements may include richer sharing and conversion workflows, but insertion and small-scope reuse are the minimum for Phase 2/3 teacher adoption.

---

## 9. Security, Scope, And Reporting Constraints

Status: **Locked constraints for implementation**

Code refs:

- `ifitwala_ed/api/gradebook.py`
- `ifitwala_ed/api/gradebook_support.py`
- `ifitwala_ed/docs/nested_scope_contract.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`

Test refs:

- `ifitwala_ed/api/test_gradebook.py`

Constraints:

- all feedback reads and writes must reuse the same group/course/role scope model already enforced for gradebook access
- no student or guardian surface may read feedback or artifacts through raw file paths
- publication state must be enforced server-side, not trusted from SPA UI conditions
- reporting and transcript logic must continue to read official truth only from `Task Outcome` and `Task Outcome Criterion`
- analytics over feedback are allowed later, but they remain secondary read models and do not redefine official truth

---

## 10. Open Decisions Before Schema Or API Approval

Status: **Requires explicit approval**

Code refs: None yet
Test refs: None yet

The following decisions should be made explicitly before schema or endpoint design begins:

1. Whether grade may ever be released without feedback, or whether feedback-first is only a supported path rather than a required policy.
2. Whether the first comment bank is personal-only, course-scoped, assignment-scoped, or some bounded combination of those scopes.
3. Whether reduced-mode ink or area comments must already create full structured anchors in Phase 2, or whether some reduced-mode annotations may stay artifact-only until richer anchoring exists.
4. Whether OCR/repair is automatic for eligible PDFs or a flagged asynchronous enhancement path.

---

## 11. Recommended Implementation Sequence

Status: **Planned**

Code refs:

- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`
- `ifitwala_ed/docs/assessment/gradebook_drawer_phases.md`

Test refs: None yet

Recommended order from the current baseline:

1. Approve this RFC and resolve the open decisions above.
2. Define the bounded drawer feedback read model without final schema naming in code yet.
3. Define the feedback draft and publication mutation contract inside assessment.
4. Add minimal comment-bank read/write support.
5. Add annotation readiness handling and reduced-mode behavior.
6. Add the student feedback navigator and reply loop on top of the same feedback records.

The key sequencing rule is:

- do not build the annotation UI as if release, version binding, and feedback ownership can be decided later

---

## 12. Technical Notes (IT)

Status: **Implementation guidance**

Code refs:

- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/gradebook_writes.py`
- `ifitwala_ed/api/outcome_publish.py`
- `ifitwala_ed/api/task_submission.py`

Test refs:

- `ifitwala_ed/api/test_gradebook.py`

- Keep Phase 2 inside the existing assessment/gradebook boundary.
- Extend the current drawer bootstrap instead of adding a parallel review page bootstrap.
- Preserve Ed-owned file preview/open governance for all evidence and derived feedback artifacts.
- Do not treat this RFC as approval to invent schema or route names without a follow-on approved change.
