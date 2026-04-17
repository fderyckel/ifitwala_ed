# Ifitwala_Ed — Assessment Feedback & Annotation Ecosystem Contract

Status: **Authoritative feature contract**
Scope: Gradebook drawer feedback workflow, submission evidence review, returned feedback artifacts, and student-facing released feedback surfaces
Audience: Product, Engineering, UX, and coding agents
Last updated: 2026-04-17

This document is the canonical product and architecture contract for feedback and annotation work in assessment.
It does not replace the task runtime contract in `04_task_notes.md`.
It defines how feedback and annotation must fit that runtime.

Related docs:
- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`
- `ifitwala_ed/docs/files_and_policies/files_01_architecture_notes.md`
- `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_08_cross_portal_governed_attachment_preview_contract.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`

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
- file actions resolve to stable Ed-owned `preview_url`, `open_url`, and `download_url` values when available
- submission version history stays bounded in gradebook/evidence surfaces
- file transport and permission checks remain server-owned

The SPA may render previews and actions from the returned DTO.
It must never derive file URLs from storage paths or raw `file_url`.

---

## 5. Phase 1 Implementation Contract

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

---

## 6. Explicitly Deferred Beyond Phase 1

Status: **Locked out of this implementation**

The following items are intentionally not treated as implemented by Phase 1:

- a dedicated structured feedback doctype/domain for anchored comments and summary
- independent feedback release and grade release states
- student reply and clarification workflows
- revision planning and acted-on tracking
- derived annotated PDF generation
- OCR gate enforcement
- student-visible annotation navigation
- AI-assisted comment generation

If these move forward, update this contract and the task/runtime docs together.

---

## 7. Accessibility And OCR Rule

Status: **Required product rule, not yet implemented in task runtime**

When annotation becomes a first-class authoring workflow, the platform must support:

- machine-readable PDF text or explicit OCR gating
- keyboard-first review and navigation
- non-color-only status meaning
- screen-reader legible comment and summary structure
- governed student-facing routes for released feedback artifacts

Until that work exists in code, the docs must continue to describe it as required future enforcement, not live runtime truth.

---

## 8. Technical Notes (IT)

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
