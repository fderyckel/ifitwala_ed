# Phase 5b — OCR And Readability Hardening RFC

Status: Planned Phase 5b implementation RFC
Audience: Product, Engineering, coding agents
Scope: OCR/readability hardening for governed assessment submission evidence
Last updated: 2026-04-23

Related docs:

- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`
- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`
- `ifitwala_ed/docs/assessment/12_phase4_student_feedback_navigator_and_reply_rfc.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_08_cross_portal_governed_attachment_preview_contract.md`
- `../ifitwala_drive/ifitwala_drive/docs/06_api_contracts.md`

---

## 0. Bottom line

Phase 5b should harden OCR and text-readability for governed `assessment_submission` evidence without changing the primary document-surface rule:

- the in-product reading surface remains immutable `assessment_submission` evidence
- OCR/readability is supporting infrastructure that upgrades the evidence surface when text-readable derivatives become available
- unreadable or scanned PDFs must still remain reviewable through reduced-mode fallback; OCR must not become a blocking gate for all staff or student reading

The implementation should extend the existing `annotation_readiness` contract instead of inventing a second OCR-only read model.

---

## 1. Why this phase exists

Current runtime already has:

- server-owned `annotation_readiness` on selected submission evidence
- governed PDF viewing in the staff drawer
- released-feedback document context in the student navigator
- reduced-mode fallback when preview/readability is limited

Current runtime does **not** yet have a hardened readability lifecycle.

Today the system mainly infers safe review mode from governed preview metadata such as `preview_status`. That is enough for Phase 1b and Phase 4 baseline behavior, but it is not strong enough for:

- reliable text anchoring
- safe jump-to-quote navigation
- search within scanned/image-heavy PDFs
- platform-wide decisions about when rich annotation should be enabled
- future analytics about evidence quality and feedback uptake

Phase 5b exists to make that layer explicit, bounded, and concurrency-safe.

---

## 2. Product outcome

After Phase 5b:

- teachers should immediately know whether a selected submission supports rich text-aware review or only reduced review
- students should see the same clarity in the released-feedback document context without being dropped into broken quote navigation
- unreadable/scanned PDFs should remain usable through point / area / page context and open-source-PDF fallback
- OCR/readability improvement should happen asynchronously and upgrade the same evidence surface later without mutating the original submission

This phase is about **clarity and trust**, not about adding another tool.

---

## 3. Canonical file and surface rules

These rules are already locked elsewhere and remain non-negotiable here:

1. Primary in-product evidence surface:
   immutable `assessment_submission`
2. Optional derivative returned/exported surface:
   governed `assessment_feedback`
3. OCR/readability work:
   supporting derivative/state work for submission evidence, not a second source of truth
4. Student navigator:
   still defaults to immutable submission evidence plus structured overlays
5. Guardian detail:
   remains text-first unless a separately authorized file DTO is explicitly designed later

Phase 5b must not reopen the document-surface decision already locked in Phase 4.

---

## 4. Current runtime baseline to preserve

Current baseline is already implemented in:

- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookPdfWorkspace.vue`
- `ifitwala_ed/ui-spa/src/components/assessment/ReleasedFeedbackPdfViewer.vue`

Current behaviors that must remain:

- server returns one selected submission payload with bounded attachment rows
- attachment rows use stable Ed-owned `open_url`, `preview_url`, and additive `attachment_preview`
- `annotation_readiness` stays the server-owned summary of what the surface can safely do with the selected evidence
- unreadable or partially ready PDFs still allow reduced-mode review rather than a dead end
- the SPA must not infer file readability by guessing from MIME, extension, or front-end parsing alone

Phase 5b extends this baseline; it does not replace it.

---

## 5. Proposed runtime direction

### 5.1 Extend `annotation_readiness`, do not fork it

The current `annotation_readiness` block should remain the canonical surface contract for evidence review readiness.

Phase 5b should extend that block to distinguish more clearly between:

- preview delivery readiness
- text readability state
- OCR upgrade progress
- safe capabilities the current surface may enable

The important design rule is:

> one evidence readiness contract per selected submission version, not one preview contract plus one OCR contract plus one UI-only inference layer

### 5.2 Two independent but related concerns

Phase 5b should model these as separate concerns inside the same readiness contract:

1. **Preview/renderability**
   Can the surface render/open a governed preview today?
2. **Text readability**
   Can the surface safely treat the evidence as text-addressable?

Those concerns are related, but they are not the same.

A PDF can be:

- preview-ready but not text-readable
- text-readable but still waiting on a richer preview derivative
- neither preview-ready nor text-readable

### 5.3 Capability-first UX

The UI should not reason from raw OCR states.
It should reason from a small capability summary computed server-side.

For example:

- rich text anchoring available
- quote-based jump available
- reduced comment mode only
- open-source-PDF fallback only

This keeps the UI simpler and reduces cognitive load.

---

## 6. Proposed readiness model

Status: Proposed contract refinement, not yet implemented

Phase 5b should keep existing top-level fields such as:

- `mode`
- `reason_code`
- `title`
- `message`
- `attachment_row_name`
- `attachment_file_name`
- `preview_status`
- `preview_url`
- `open_url`

And add a planned substructure for richer decisions, conceptually:

- `preview`
  current preview state for the selected governed evidence
- `text_readability`
  whether the selected evidence is text-addressable today
- `upgrade`
  whether an OCR/readability improvement job is pending, failed, or complete
- `capabilities`
  what the current surface may safely enable

This RFC deliberately locks the shape conceptually first.
Final concrete field names should be chosen only when implementation begins.

### 6.1 Minimum conceptual states

Preview concern should distinguish:

- ready
- pending
- failed
- unsupported
- not_applicable

Text readability concern should distinguish:

- ready
- pending
- failed
- unsupported
- not_applicable

Upgrade concern should distinguish:

- none_needed
- queued
- processing
- failed
- completed

Capabilities should at least answer:

- can_render_document
- can_use_text_anchor
- can_search_text
- can_jump_to_quote
- can_use_reduced_mode

### 6.2 UX-facing reduction

Even if the server tracks richer state internally, the teacher and student UX should still collapse this into a small number of understandable modes:

- rich review
- reduced review
- open-only fallback
- not applicable

The user should never have to parse a queue state machine.

---

## 7. Staff drawer behavior

### 7.1 Gradebook drawer remains the teacher surface

No separate OCR workspace should be created.

The existing gradebook Evidence tab remains the owner of:

- document context
- current readiness summary
- annotation affordance availability
- reduced-mode guidance

### 7.2 Staff UX rules

When evidence is text-readable:

- text-aware annotation affordances may be enabled later
- rich text anchoring can be trusted
- quote-based navigation may be surfaced

When evidence is preview-ready but not text-readable:

- point / area / page comments remain available
- reduced-mode explanation should say clearly that the source PDF is readable as a document but not as text-addressable evidence
- the drawer should not pretend that highlight/text-quote tools are available

When evidence is still processing:

- current reduced-mode fallback remains valid
- the UI may tell the teacher that readability upgrades are pending
- review must still continue through the current source PDF and structured feedback panel

When evidence fails upgrade:

- the teacher should see an actionable explanation
- no silent downgrade
- reduced-mode fallback remains available where the source file itself can still be opened

---

## 8. Student navigator behavior

### 8.1 Student surface stays summary-first

The student still lands in:

1. summary
2. priorities
3. rubric snapshot
4. feedback list
5. document context

Phase 5b must not invert that ordering.

### 8.2 Student document behavior

When evidence is text-readable:

- jump-to-anchor and quote-based context can be trusted

When evidence is only preview/open-ready:

- student still sees the document context pane
- anchored note navigation should degrade gracefully to page/region context where possible
- the document block should explain that some comments are positioned visually rather than text-linked

When evidence is not safely renderable:

- student remains able to consume released summary, priorities, rubric snapshot, and comment list
- the document block degrades to stable open/download actions where allowed

### 8.3 Guardian behavior

No change from the Phase 4 lock:

- guardian detail remains text-first
- no reuse of the student document contract
- any future guardian file access must resolve its own surface-authorized DTO

---

## 9. Drive and async boundary

### 9.1 Drive remains the binary authority

Ed should not perform OCR storage governance itself.

Drive remains responsible for:

- governed versions
- derivative generation/storage
- preview/readability-related derivative lifecycle where applicable

Ed remains responsible for:

- business-surface authorization
- readiness interpretation
- workflow meaning
- portal/staff DTO assembly

### 9.2 OCR/readability must stay off the request path

This is a hard concurrency rule.

Phase 5b must not:

- run OCR inline during submission reads
- trigger heavy repair work from every page open
- let staff/student page loads block on OCR completion

Instead:

- queue readability upgrade work asynchronously
- normalize queue labels to valid runtime queues
- keep the current selected-submission read bounded and cache-safe
- let the UI read current readiness state without polling loops

### 9.3 Mutation ownership

Upgrade jobs should be triggered only from explicit ownership points, for example:

- at governed finalize when a new submission PDF version arrives
- from an explicit server-side repair/requeue command owned by the assessment/file boundary

They must not be spawned ad hoc from multiple surfaces.

---

## 10. Read-model boundaries

Phase 5b should extend only existing bounded reads:

- selected submission evidence in drawer reads
- released feedback detail document context for students

It should not create:

- a second OCR dashboard payload
- a separate PDF-readiness waterfall from the SPA
- client-side OCR state probing

If a richer readiness block is added, it should arrive inside the existing selected submission / document payloads.

---

## 11. Tests and acceptance gates

Before implementation is considered done, the following acceptance gates should hold.

### 11.1 Backend

- selected submission payload distinguishes preview readiness from text readability
- unreadable PDFs still produce a valid reduced-mode readiness contract
- text-readable PDFs produce a richer readiness contract without changing immutable submission semantics
- guardian released-feedback detail still does not leak document DTOs
- all governed file actions continue using Ed-owned routes and shared `attachment_preview` semantics

### 11.2 SPA

- staff drawer shows the correct readiness message and permitted toolset for each state
- student navigator document pane degrades cleanly for unreadable/open-only cases
- no client-only inference decides that text anchoring is available

### 11.3 Concurrency

- no OCR work is started inline from hot read endpoints
- no polling loop is introduced just to watch OCR completion
- queue selection remains runtime-valid and documented

---

## 12. Explicit non-goals for Phase 5b

Phase 5b should **not** also try to deliver:

- analytics over OCR/readability outcomes
- a guardian document viewer
- AI-generated text repair or comment generation
- making derived `assessment_feedback` artifacts the default student document surface
- a second standalone “document repair” app

Those are later concerns.

---

## 13. Recommended implementation sequence

1. Lock the runtime contract extension on `annotation_readiness`.
2. Add backend readiness resolution and async upgrade ownership.
3. Expose the extended readiness state through existing drawer and released-feedback reads.
4. Update the staff drawer PDF workspace and student document viewer to honor the refined capability contract.
5. Add focused backend and SPA tests for readable, pending, failed, and reduced-mode paths.

---

## 14. Technical Notes (IT)

Status: Planned Phase 5b refinement

Code refs:

- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/released_feedback.py`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookPdfWorkspace.vue`
- `ifitwala_ed/ui-spa/src/components/assessment/ReleasedFeedbackPdfViewer.vue`
- `ifitwala_ed/integrations/drive/workflow_specs.py`
- `ifitwala_ed/integrations/drive/tasks.py`

Existing tests to extend:

- `ifitwala_ed/api/test_gradebook.py`
- `ifitwala_ed/api/test_released_feedback.py`
- `ifitwala_ed/api/test_task_submission.py`
- `ifitwala_ed/api/test_task_submission_unit.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`
- `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentReleasedFeedbackDetail.test.ts`
