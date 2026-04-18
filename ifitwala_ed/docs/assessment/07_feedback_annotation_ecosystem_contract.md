# Ifitwala_Ed — Assessment Feedback & Annotation Ecosystem Contract

Status: **Authoritative feature contract**
Scope: Gradebook drawer feedback workflow, submission evidence review, returned feedback artifacts, and student-facing released feedback surfaces
Audience: Product, Engineering, UX, and coding agents
Last updated: 2026-04-18

This document is the canonical product and architecture contract for feedback and annotation work in assessment.
It does not replace the task runtime contract in `04_task_notes.md`.
It defines how feedback and annotation must fit that runtime.

Related docs:
- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`
- `ifitwala_ed/docs/assessment/09_feedback_records_and_publication_rfc.md`
- `ifitwala_ed/docs/files_and_policies/files_01_architecture_notes.md`
- `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_08_cross_portal_governed_attachment_preview_contract.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`
- `ifitwala_drive/ifitwala_drive/docs/02_system_architecture.md`
- `ifitwala_drive/ifitwala_drive/docs/04_coupling_with_ifiwala_ed.md`
- `ifitwala_drive/ifitwala_drive/docs/05_optionC_design_lock.md`
- `ifitwala_drive/ifitwala_drive/docs/06_api_contracts.md`
- `ifitwala_drive/ifitwala_drive/docs/21_cross_portal_governed_attachment_preview_contract.md`

---

## 0. Bottom Line

Ifitwala_Ed must build a **feedback workflow for assessed work**, not a generic PDF markup tool.

The product center is:

- anchored feedback on submission evidence
- rubric-linked judgment
- prioritized summary/feedforward
- controlled release
- student response and revision

PDF annotation is one evidence-review and anchoring surface inside that workflow.
It is not the source of truth.
Annotation is the teacher-facing feature.
OCR is supporting infrastructure for unreadable or scanned PDFs.

---

## 1. Locked Product Decisions

Status: **Phase 0 locked**

Code refs:
- `ifitwala_ed/api/gradebook.py`
- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/assessment/task_submission_service.py`
- `ifitwala_ed/assessment/task_outcome_service.py`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/Gradebook.vue`

Test refs:
- `ifitwala_ed/api/test_gradebook.py`
- `ifitwala_ed/api/test_task_submission.py`
- `ifitwala_ed/assessment/test_task_submission_service.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`

The following decisions are non-negotiable for this feature family:

1. Teacher work happens inside the existing Gradebook page and Grading Drawer flow.
   Do not create a parallel document-review page as the main grading surface.
2. Original student submission evidence remains immutable.
   Annotation and feedback must not overwrite learner evidence.
3. Structured feedback is the future source of truth.
   Painted or flattened PDF marks are derivative artifacts, not canonical runtime truth.
4. Release of feedback and release of grades are product-level concepts that must remain explicit and auditable.
5. Student- and guardian-visible evidence and feedback must resolve through Ed-owned, surface-authorized routes.
   The SPA must never guess raw private paths or bypass workflow permission checks.
6. Accessibility and OCR are platform rules for this feature family.
   They are not optional polish once annotation becomes a default workflow.
7. AI-generated student-visible feedback is out of scope unless the workflow keeps a teacher approval step before publication.
8. The first serious teacher authoring version must include a minimal comment bank.
   Reusable comments and quickmarks are part of core teacher productivity, not late polish.
9. Reporting and transcript truth remain owned by `Task Outcome` and `Task Outcome Criterion`.
   Feedback records, replies, and feedback artifacts must not become reporting inputs.
10. The future feedback domain must stay inside the assessment boundary.
    Do not create a parallel mini-platform detached from gradebook, submissions, and outcomes.

---

## 2. Canonical Runtime Layers

Status: **Locked architecture**

Code refs:
- `ifitwala_ed/docs/assessment/04_task_notes.md`
- `ifitwala_ed/assessment/doctype/task_submission/task_submission.json`
- `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.json`
- `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.json`

The ecosystem must be reasoned about in four layers:

| Layer | Runtime owner | Meaning |
| --- | --- | --- |
| Immutable submission evidence | `Task Submission` and governed file attachments | what the learner submitted and when |
| Structured feedback records | future dedicated feedback domain adjacent to task runtime | anchored comments, summary, priorities, replies, publication state |
| Derived feedback artifact | governed `assessment_feedback` file artifact | returned annotated PDF, rubric sheet, or feedback export |
| Official grade and rubric outcome | `Task Outcome` and `Task Outcome Criterion` | official institutional truth |

Rules:

- `Task Outcome` remains the official grading/result layer.
- `Task Submission` remains append-only evidence.
- A future structured feedback domain must stay adjacent to the task runtime, not fused into `Task Outcome`.
- A derived feedback artifact may reference evidence and structured feedback, but it must not become the grading source of truth.

---

## 3. Teacher Surface Contract

Status: **Phase 0 locked, Phase 1 required**

Code refs:
- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/Gradebook.vue`
- `ifitwala_ed/api/gradebook_reads.py`

The teacher surface contract is:

- Gradebook grid or roster list for scanning
- Grading Drawer for detailed work

The drawer is the only rich workspace for:

- evidence review
- rubric and comment authoring
- official result inspection
- compare and moderation context
- release actions

The grid or student list may show status, badges, and one-glance summaries.
It must not become a second rich grading UI that competes with the drawer.

---

## 4. Evidence And File Governance Contract

Status: **Implemented baseline**

Code refs:
- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/api/file_access.py`
- `ifitwala_ed/assessment/task_submission_service.py`
- `ifitwala_ed/docs/files_and_policies/files_01_architecture_notes.md`
- `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`

Test refs:
- `ifitwala_ed/api/test_task_submission.py`
- `ifitwala_ed/api/test_gradebook.py`
- `ifitwala_ed/api/test_file_access.py`

Current governed contract that feedback and annotation work must preserve:

- submission evidence uses `assessment_submission`
- returned or marked artifacts use `assessment_feedback`
- all governed file writes go through the Ifitwala_drive boundary, not direct business-logic `File.insert()` paths
- file actions resolve to stable Ed-owned `preview_url`, `open_url`, and `download_url` values when available
- submission version history stays bounded in gradebook/evidence surfaces
- file transport and permission checks remain server-owned

The SPA may render previews and actions from the returned DTO.
It must never derive file URLs from storage paths or raw `file_url`.
Ifitwala_Ed remains the workflow and portal-authorization authority.
Ifitwala_drive remains the governed file-platform authority for upload sessions, versions, canonical references, preview derivatives, and short-lived grants.

For Ed-owned staff, student, and guardian surfaces:

- the SPA must not call Drive grant APIs directly
- Ed-owned routes authorize the business surface first, then call Drive to issue the grant or redirect
- preview and download behavior must stay aligned with the cross-portal governed preview contract

---

## 5. Publication Matrix And Reporting Boundary

Status: **Phase 0 locked, not yet implemented in runtime**

Code refs:
- `ifitwala_ed/api/outcome_publish.py`
- `ifitwala_ed/api/gradebook_writes.py`
- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`

The feedback ecosystem must separate **what is released** from **to whom it is released**.

Release channels:

| Channel | Allowed audience reach | Notes |
| --- | --- | --- |
| Feedback | `none`, `student`, `student_and_guardian` | supports feedback-first release |
| Grade / rubric outcome | `none`, `student`, `student_and_guardian` | may lag feedback release |

Rules:

- `student_and_guardian` always implies student visibility first.
- Guardian visibility must never exceed student visibility for the same release channel.
- Feedback may be released before grade.
- Grade may remain hidden while feedback is visible.
- Either release channel may be released independently.
- Product-preferred shortcuts are `release feedback` and `release both`; grade-only release remains an explicit action rather than the default shortcut.
- Student and guardian surfaces must render only the channels released to that audience.
- The current `Task Outcome.is_published` model is legacy baseline behavior only.
  It must not be treated as the final release contract for feedback work.

Reporting boundary:

- Official academic truth for reporting remains `Task Outcome` and `Task Outcome Criterion`.
- Structured feedback, anchored comments, replies, acknowledgements, and derived feedback artifacts are pedagogical workflow data, not reporting truth.
- Release state governs portal visibility and workflow timing.
  It does not redefine reporting ownership.

---

## 6. Feedback Version Binding And Artifact Invariants

Status: **Phase 0 locked, not yet implemented in runtime**

Code refs:
- `ifitwala_ed/docs/assessment/04_task_notes.md`
- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/assessment/task_submission_service.py`

Every feedback object must bind to one selected evidence version.

Rules:

- Each feedback record binds to exactly one `Task Outcome`.
- Each anchored feedback record also binds to one selected `Task Submission` version, or to an explicit teacher-created evidence stub when no learner upload exists.
- Anchors resolve only inside that selected evidence version.
- Resubmission creates a new evidence version; prior feedback remains historical, but becomes stale for current review unless a teacher explicitly carries it forward.
- Derived feedback artifacts bind to one evidence version and one feedback publication snapshot.
- Original learner evidence remains immutable.
- Replacing a returned feedback artifact creates a new governed feedback artifact/version; it does not mutate the learner submission.

---

## 7. Annotation, Comment Bank, And OCR Contract

Status: **Phase 0 locked, not yet implemented in runtime**

Code refs:
- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`

The annotation product must be implemented as three coordinated layers:

1. annotation workspace in the gradebook drawer
2. structured feedback records inside the assessment boundary
3. OCR and accessibility support for low-quality evidence

Teacher-facing annotation minimum:

- text highlight with anchored comment for text-readable PDFs
- point comment
- area comment
- page comment
- optional ink/freehand for handwritten or diagram-heavy work

Teacher productivity minimum:

- minimal comment bank or quickmarks in the first serious authoring version
- scoped reusable comments at least by assignment or course
- insertion from the drawer without leaving the grading flow
- first-version default scope is teacher-owned entries with optional course or assignment relevance; broader shared banks come later

Structured feedback record minimum:

- feedback items, summary records, and reply history remain first-class assessment records
- conversation history must not collapse into one opaque message blob
- each reply/message keeps author, timestamp, visibility/workflow state, and parent thread identity

Annotation payload discipline:

- anchor/body payloads may use JSON-capable storage, but the contract must define explicit shapes per annotation kind rather than one untyped catch-all blob
- minimum anchor families are text quote, point, rect/area, and path/ink
- text-readable anchors should preserve page, normalized rect coordinates, quote text, and selector offsets when available
- ink/path payloads must persist committed normalized stroke points plus width/style metadata, not raw pointer-move streams
- payloads should be kind-discriminated or versioned so validation and later migrations stay tractable

Readability and OCR rules:

- Text-readable PDFs support text highlight, search, copyable snippets, and quote-based anchoring.
- Non-readable PDFs must be detected before rich text annotation is treated as available.
- Until OCR or repair exists, unreadable PDFs may use reduced annotation mode:
  - area comments
  - page comments
  - ink
- reduced-mode comments still create structured feedback records with coarse anchors; they must not exist only as flattened artifact marks
- the default OCR path is asynchronous enhancement after readability detection, not a synchronous review blocker
- Do not roll out annotation as if every PDF is text-readable.

Hot-path write discipline:

- autosave may improve UX, but the server contract remains named, bounded mutations
- debounce draft/comment saves rather than treating each keystroke as an immediate authoritative write
- never write one DB row or document save per pointer move
- ink writes should commit on stroke end or bounded idle windows
- payloads and writes must stay outcome/version/page scoped so the drawer remains concurrency-safe

Stylus and device constraint:

- ink is supportive, not foundational
- highlight/comment and typed summary flows must remain first-class without stylus support
- Safari/iPad pointer quirks, inconsistent pressure, and palm-rejection noise must not define the core review path

Accessibility minimum:

- keyboard-first review and navigation
- non-color-only meaning for states and badges
- screen-reader legible comment and summary structure
- clear jump behavior between feedback navigator and document anchors

Student-facing feedback UX minimum:

- released feedback should foreground a concise synthesis with strengths, improvements, and next steps
- student-visible navigation should focus threads and context, not dump a flat wall of disjoint comments
- annotations support the summary; they do not replace synthesis

---

## 8. Phase 1 Implementation Contract

Status: **Implemented baseline in this change**

Code refs:
- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/gradebook.py`
- `ifitwala_ed/ui-spa/src/lib/services/gradebook/gradebookService.ts`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/Gradebook.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`

Test refs:
- `ifitwala_ed/api/test_gradebook.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`

Phase 1 means the following is live:

1. The teacher stays on the Gradebook page.
2. Task View opens one student at a time in a right-side grading drawer.
3. The drawer uses one bounded bootstrap call for:
   - delivery policy
   - student identity
   - outcome state
   - latest submission summary
   - selected submission evidence
   - submission version list
   - current teacher contribution context
   - moderation history
   - allowed actions
4. The Evidence tab reads one selected submission plus bounded version summaries, not a per-file waterfall.
5. Submission attachments continue to use governed preview/open actions resolved by Ed.
6. The drawer may save marking through existing gradebook mutation routes, but it must not invent client-side official truth.

Phase 1 does **not** mean the structured feedback domain is complete.
It is the drawer-first evidence and grading foundation.
It also does **not** mean the release model is solved beyond the current legacy `is_published` baseline.

---

## 9. Next Implementation Sequence

Status: **Locked sequencing from current baseline**

From the current drawer/evidence baseline, the next implementation sequence is:

1. structured feedback records and publication states inside the assessment boundary
2. annotation authoring workflow plus minimal comment bank and readability detection/fallback
3. student feedback navigator plus reply and clarification loop
4. OCR hardening, derived artifacts/export, and feedback analytics

See `09_feedback_records_and_publication_rfc.md` for the non-authoritative implementation RFC that translates this sequence into a Phase 2 design.

The following remain out of current-baseline scope until those phases ship:

- student-visible annotation navigation
- revision planning and acted-on tracking
- derived annotated PDF generation
- full OCR gate enforcement
- AI-assisted comment generation

---

## 10. Technical Notes (IT)

Status: **Current implementation boundary**

Code refs:
- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/docs/high_concurrency_contract.md`

Test refs:
- `ifitwala_ed/api/test_gradebook.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`

- The Phase 1 drawer bootstrap must stay bounded and outcome-scoped.
- Evidence review should reuse the existing selected-submission serialization path rather than inventing a new file-preview endpoint.
- Task list or roster reads may remain separate from drawer bootstrap as long as the drawer itself does not fan out into multiple dependent requests.
- The current release model in `Task Outcome.is_published` remains a baseline implementation detail, not the final feedback-release contract.
- Future feedback records should be introduced adjacent to the task runtime and keyed by outcome plus evidence version, rather than hidden inside `Task Contribution`.
