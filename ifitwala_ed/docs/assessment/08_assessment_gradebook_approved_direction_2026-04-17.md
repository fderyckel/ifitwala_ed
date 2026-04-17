# Assessment & Gradebook Approved Direction

Status: Approved product direction / non-canonical until runtime docs are updated
Date: 2026-04-17
Audience: Product and Engineering
Scope: Release visibility, binary/completion audit model, rubric point ownership, collect-work workflow, and next implementation priority

Important note:
- This memo records approved product direction after the assessment audit.
- It does not replace the canonical runtime contracts in `03_gradebook_notes.md`, `04_task_notes.md`, or `07_feedback_annotation_ecosystem_contract.md`.
- When implementation lands, update the canonical runtime docs in the same change.

## Bottom Line

Approved direction:
- Students and guardians share one release state.
- `Binary` and `Completion` move onto the same contribution/audit workflow as other grading modes.
- Rubric descriptors and levels remain globally reusable, but points stay delivery-local.
- `Collect Work` stays inside the same assessment product, with a dedicated evidence inbox view that deep-links into the grading drawer.

The drawer/evidence/feedback baseline is already live.
The next step is not to build another grading surface. It is to harden the current drawer-centered workflow into a premium, evidence-first assessment product.

## Approved Decisions

### 1. One Release State

Decision:
- Students and guardians share the same release state.

Implementation direction:
- Keep one server-owned release flag on `Task Outcome`.
- Keep one explicit release action in the drawer.
- Remove any product drift where audience visibility appears split even though the runtime truth is shared.
- Treat notification targeting as a communications concern, not a separate grade visibility truth.

### 2. Binary / Completion Must Use The Same Audit Contract

Decision:
- `Binary` and `Completion` should not remain outcome-direct write paths.

Implementation direction:
- Keep `Task Outcome.is_complete` as derived official truth for reads, dashboards, and reporting.
- Add contribution-level judgment so completion-style grading produces the same audit trail, stale-evidence behavior, moderation path, and release behavior as points, grades, and rubric rows.
- Do not keep a permanent grading exception where these modes bypass `Task Contribution`.

### 3. Rubric Points Stay Local To The Delivery

Decision:
- Reuse the language of quality globally, but keep scoring consequence local.

Implementation direction:
- Global rubric layer owns criterion names, levels, descriptors, and stable ordering.
- Delivery-local rubric layer owns weight, whether criteria contribute numerically, and selected level -> points mapping.
- Do not make `Assessment Criteria Level` the canonical owner of final numeric points across the platform.

Rationale:
- This matches how strong products reuse rubric language while still allowing assignment-level scoring differences across formative, summative, and standards-aligned work.

### 4. Collect Work Gets An Evidence Inbox, Not A Separate Module

Decision:
- `Collect Work` stays inside the same assessment product.

Implementation direction:
- Keep the gradebook as the overview and official-truth surface.
- Add an evidence-first inbox for collect-work tasks:
  - submitted / missing / late / new-evidence filters
  - version-aware evidence review
  - quick actions
  - next/previous learner flow
  - deep link into the grading drawer for rubric, moderation, and release

## Recommended Next Epic

If one initiative starts next, it should be:

- `Release Contract + Contribution Parity + Evidence Inbox`

Why this should come next:
- The drawer already exists, so the biggest remaining product gain comes from workflow correctness and evidence-first speed.
- It resolves the most important contract issues without reopening architecture.
- It sets the right base for later moderation, annotation, and analytics.

## Suggested Build Sequence

1. Normalize release semantics so one release action owns visibility for both students and guardians.
2. Move `Binary` and `Completion` grading onto contribution-based writes.
3. Add the collect-work evidence inbox on top of the existing drawer/evidence workflow.
4. Add delivery-local rubric point mapping so criteria selection becomes reliable and fast.
5. Extend the drawer into richer moderation, teacher-speed, and feedback-artifact workflows.
