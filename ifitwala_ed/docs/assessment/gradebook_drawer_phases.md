# Ifitwala_Ed — Gradebook Drawer Product Roadmap

Status: **Planned Roadmap / Not a runtime contract until implemented**
Audience: Product, Engineering, UX, and coding agents
Last updated: 2026-04-03

This document turns the Gradebook roadmap into a phased implementation plan that fits the current Ifitwala_Ed assessment architecture.
It is intentionally written for both human planning and coding agents.

Important boundary:

- This file describes **planned product and architecture evolution**.
- It does **not** override current runtime contracts in:
  - `ifitwala_ed/docs/assessment/01_assessment_notes.md`
  - `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
  - `ifitwala_ed/docs/assessment/04_task_notes.md`
- When a phase ships, update the canonical runtime docs above in the same change.

---

## 0. Bottom Line

The next logical product move is to make the Gradebook feel like a **single teacher workspace** where grading, evidence review, comments, moderation, and release all happen in one drawer without doctype exposure.

The architecture should **not** move official grading truth into the SPA.
The drawer should remain a UI surface over the existing contribution/outcome model:

- Teacher edits write **Task Contribution** and **Task Contribution Criterion**
- Official visible results are derived into **Task Outcome** and **Task Outcome Criterion**
- Evidence remains versioned in **Task Submission**
- Task setup and delivery policy remain owned by **Task** and **Task Delivery**

---

## 1. Current Architecture Baseline

Status: **Implemented baseline with UI gaps**

Code refs:

- `ifitwala_ed/api/gradebook.py`
- `ifitwala_ed/assessment/task_creation_service.py`
- `ifitwala_ed/assessment/task_delivery_service.py`
- `ifitwala_ed/assessment/task_contribution_service.py`
- `ifitwala_ed/assessment/task_outcome_service.py`
- `ifitwala_ed/assessment/doctype/task/task.py`
- `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
- `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.py`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/Gradebook.vue`
- `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`

Test refs:

- `ifitwala_ed/api/test_gradebook.py`
- `ifitwala_ed/assessment/test_task_creation_service.py`
- `ifitwala_ed/assessment/test_task_outcome_service.py`
- `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`
- `ifitwala_ed/ui-spa/src/components/tasks/__tests__/CreateTaskDeliveryOverlay.test.ts`

Current model that must remain intact:

| Layer | Owns | Product meaning |
| --- | --- | --- |
| `Task` | reusable task definition, grading defaults, default comment policy, task criteria | what this task is |
| `Task Delivery` | class-scoped assignment instance, deadline policy, grading snapshot, comment policy snapshot, rubric snapshot | this task assigned to this class |
| `Task Outcome` | one row per student x delivery, official status, official score/comment/completion, publication state | official state for one student on one delivery |
| `Task Submission` | versioned student evidence and teacher-created stubs | what was submitted and when |
| `Task Contribution` | teacher/moderator grading input and rubric rows | who marked what |
| `Task Outcome Criterion` | official per-criterion result rows | final criterion-level truth shown to users |

Current UX gaps this roadmap addresses:

- Gradebook grid still carries too much grading interaction inline instead of delegating rich workflows to a drawer.
- Criteria authoring is not yet first-class in the quick task creation overlay.
- Evidence review, comment, rubric marking, status transitions, moderation, and release are not yet unified into one low-friction workflow.
- Bulk grading speed and keyboard-first grading are not yet treated as a product requirement.
- Stale contribution / resubmission review needs a clearer teacher-facing flow.

---

## 2. Product Principles For A Top-Tier Gradebook

Status: **Planned principles**

These principles should guide every phase:

| Principle | Product rationale | Architecture implication |
| --- | --- | --- |
| One teacher workspace | Teachers should grade without opening doctypes or jumping between pages | Build a drawer over `Task Outcome`, `Task Submission`, and `Task Contribution` APIs |
| Mode-aware grading | Binary, Completion, Points, Criteria, and comment-only work must not share one generic form | Keep `Task Delivery.grading_mode` and `allow_feedback` as server-owned UI contract inputs |
| Official truth stays server-side | Prevent client-side drift, invalid totals, and status inconsistencies | SPA may render and stage edits, but official recompute stays in `task_outcome_service.py` |
| Evidence-first review | Teachers should see what changed before deciding whether to remark | Drawer must expose latest submission, prior versions, and stale contribution state |
| Speed at scale | A gradebook used daily must support fast grading across a whole class | Add keyboard navigation, bounded autosave, and one-row drawer transitions without request waterfalls |
| Governed release | Finalization, moderation, and student/guardian visibility must be explicit and auditable | Keep publication and moderation transitions as named API/service operations with permission checks |
| Multi-tenant safety | Teachers and moderators must only see permitted student groups and students | Reuse server-side scope checks already enforced in gradebook APIs and do not move scope math into the SPA |
| Concurrency-safe reads | Gradebook should stay responsive under many concurrent staff users | Prefer bounded aggregated endpoints and follow `ifitwala_ed/docs/high_concurrency_contract.md` |

---

## 3. Phase 1 — Drawer Foundation And Contract Completion

Status: **Recommended next build phase**

### 3.1 Phase Goal

Replace the current “inline controls do everything” gradebook experience with a **Grading Drawer** that gives each student/task row one structured workspace for grading, evidence, comments, visibility, and status.

### 3.2 Why This Phase Comes First

This phase removes the biggest current product friction:

- Teachers need one focused panel per student/task, not a dense in-row editor.
- Criteria grading needs a clean rubric interaction surface.
- Comment policy must stay additive and mode-aware.
- Save/release behavior should be obvious and hard to misuse.

This phase also creates the architectural foundation for later moderation and analytics without moving official grading logic into the client.

### 3.3 Planned Product Scope

| Capability | Expected behavior |
| --- | --- |
| Drawer open from gradebook row/cell | Clicking a student row opens a right-side drawer for that `Task Outcome` |
| My Marking tab | Teacher edits points, completion/binary state, criteria levels, and optional comment according to delivery mode |
| Evidence tab | Teacher reviews latest submission and submission history, including “No digital submission” with stub context |
| Official Result tab | Teacher sees server-derived official score, status, completion state, and per-criterion official rows |
| Visibility controls | Student and guardian visibility are managed from the drawer with explicit state and save feedback |
| Status actions | Allowed status transitions are shown as explicit actions, not hidden behind raw select values |
| Mode-aware comment box | Comment UI appears only when `Task Delivery.allow_feedback = 1`, regardless of grading mode |
| Criteria-first rubric UI | For `Criteria`, rubric levels/comments are the primary controls; `Separate Criteria` does not show an editable total |
| Previous/Next student navigation | Drawer supports moving through students in the selected delivery without closing context |

### 3.4 Architecture Integration

Current objects and services should be reused as follows:

| Drawer concern | Current architecture owner | Notes for implementation |
| --- | --- | --- |
| Student row identity | `Task Outcome` | Drawer should anchor on one outcome id, not on a synthetic client key |
| Current official result | `Task Outcome`, `Task Outcome Criterion` | Read-only official tab must render server-derived state only |
| Teacher draft/save input | `Task Contribution`, `Task Contribution Criterion`, `task_contribution_service.py` | Drawer “My Marking” writes contributions, not direct official field edits |
| Official recompute | `task_outcome_service.py` | Do not recompute totals or grade symbols in Vue |
| Delivery grading policy | `Task Delivery.grading_mode`, `Task Delivery.allow_feedback`, `Task Delivery.rubric_scoring_strategy` | Drawer form shape must be driven by these fields |
| Evidence versions | `Task Submission` | Evidence tab should read submission metadata/content by outcome and version |
| Submission stubs | `task_submission_service.py` through existing contribution flow | If no student submission exists but submission is required, the backend can continue creating a stub when teacher saves a contribution |
| Group and tenant scope | `api/gradebook.py` and canonical scope helpers | All drawer reads/writes must re-check server-side access to the delivery’s student group |

### 3.5 Likely API Shape Change

Do **not** create a client-side request waterfall where the drawer separately fetches outcome, criteria, submission history, official rows, and permissions.
Prefer one bounded drawer bootstrap endpoint under `ifitwala_ed/api/gradebook.py`, with exact route and payload defined in an implementation RFC before coding.

Recommended response composition:

| Response area | Source |
| --- | --- |
| Delivery policy snapshot | `Task Delivery` |
| Student/outcome identity and official scalar fields | `Task Outcome` |
| Official per-criterion rows | `Task Outcome Criterion` |
| Latest teacher-editable contribution draft/context | `Task Contribution` and rubric rows |
| Latest submission and version list summary | `Task Submission` |
| Allowed actions | server-side role/scope checks plus outcome/delivery state |

### 3.6 Guardrails For Coding Agents

- Do not write official totals directly from Vue.
- Do not invent drawer payload fields without first defining the server contract in `api/gradebook.py` and updating docs.
- Do not show comment controls when `allow_feedback = 0`.
- Do not merge `Binary` and `Completion` copy in the UI; they share a boolean storage shape but not teacher-facing labels.
- Do not hide blocked actions silently; every forbidden transition needs an inline reason or toast.
- Do not expose sibling groups or unauthorized students in drawer navigation.

### 3.7 Acceptance Criteria

Phase 1 is done when:

- A teacher can open one student’s grading drawer from the gradebook and complete grading without leaving the page.
- Drawer controls adapt correctly for `Points`, `Completion`, `Binary`, `Criteria`, and comment-only delivery policy.
- Criteria comments and task-level comments remain additive and do not require a rubric level unless a rubric score itself is being saved.
- `Separate Criteria` never shows a user-editable total; `Sum Total` shows server-derived total only.
- Official results shown in the drawer match `Task Outcome` / `Task Outcome Criterion`, not client-local math.
- Student and guardian visibility updates are explicit, permission-checked, and reflected in current outcome state.
- Tests cover all grading modes, comment policy on/off, criteria strategy behavior, visibility updates, and forbidden payload combinations.

---

## 4. Phase 2 — Teacher Speed, Evidence Workflow, And Rubric Authoring

Status: **Planned after Phase 1 drawer foundation**

### 4.1 Phase Goal

Make the gradebook fast enough for real daily use across a whole class and remove the remaining setup gap for criteria-based work.

### 4.2 Why This Phase Comes Second

Once the drawer exists, the next bottlenecks become speed and setup:

- Teachers need to move through many students quickly.
- Rubric creation should not require leaving the normal task setup workflow.
- Resubmissions and stale grading need a clean review path.
- Bulk operations become useful only after the row-level drawer contract is stable.

### 4.3 Planned Product Scope

| Capability | Expected behavior |
| --- | --- |
| Keyboard-first marking | Save, next student, previous student, toggle completion, and level selection support keyboard shortcuts |
| Bulk actions | Set visibility, bulk finalize/release, bulk mark complete, and targeted bulk status transitions where safe |
| Resubmission review | Drawer and grid show “new evidence” and “stale contribution” clearly, with one-click jump to the changed submission |
| Submission history | Teacher can inspect previous versions and compare submission timestamps/content metadata |
| Rubric authoring in task setup | Criteria rows, weights, and scoring strategy can be configured from the task creation/edit workflow |
| Rubric templates | Teachers can reuse saved criteria sets and level definitions where curriculum policy allows |
| Faster criteria marking | One-click level selection, row-level comments, and optional criterion navigation inside drawer |
| Better class scanning | Delivery list and grid surface missing, late, not started, needs review, needs moderation, and released counts |

### 4.4 Architecture Integration

| Capability | Current owner | Integration direction |
| --- | --- | --- |
| Keyboard and next/previous navigation | `Gradebook.vue` and new drawer component | Keep navigation state client-side but outcome reads/writes server-validated |
| Bulk actions | New named endpoints in `api/gradebook.py` plus existing outcome/contribution services | Use bounded batch payloads and enforce per-row permission/scope checks |
| Stale contribution handling | `task_contribution_service.mark_contributions_stale`, `Task Contribution.is_stale`, `Task Submission.version` | Drawer should explain stale state and guide remarking the latest version |
| Criteria authoring | `Task.task_criteria`, `Task.default_rubric_scoring_strategy`, `Task Delivery` snapshot fields | Extend task setup UI without duplicating rubric state in the SPA |
| Rubric templates | likely `Task` template pathways and existing criteria doctypes | Reuse Assessment Criteria and task criteria rows; do not create a second rubric model casually |
| Class scanning counters | `Task Outcome` aggregate reads | Compute counters server-side in bounded queries, not per-row client loops |

### 4.5 High-Concurrency Requirements

Phase 2 is where scalability risk increases.
Follow `ifitwala_ed/docs/high_concurrency_contract.md` explicitly:

- Bulk grade actions must be chunked and idempotent.
- Large class counters should come from bounded indexed queries, not one request per outcome.
- Autosave and row transitions should not trigger uncontrolled refresh fan-out.
- If realtime updates are added, define one ownership model and avoid client-driven polling loops.

### 4.6 Acceptance Criteria

Phase 2 is done when:

- A teacher can grade an entire class mostly from keyboard + next/previous navigation.
- Criteria tasks can be created with rubric rows and strategy from the normal setup workflow without falling back to Desk.
- Resubmissions and stale grading are visible and actionable from the drawer.
- Bulk actions are permission-safe, scoped to the selected delivery/group, and resilient under partial failures.
- Aggregate class status counts render from server-owned counters and remain performant on large groups.
- Tests cover rubric authoring, stale contribution review, keyboard navigation behavior, and bulk action authorization/scope.

---

## 5. Phase 3 — Moderation, Analytics, Reporting Handoff, And Governance

Status: **Planned after Phase 2 speed and setup are stable**

### 5.1 Phase Goal

Turn the Gradebook into a decision-grade operational cockpit with moderation workflows, class analytics, and clean handoff into term reporting.

### 5.2 Why This Phase Comes Third

Moderation and analytics depend on a stable drawer workflow and reliable rubric/task setup.
If these are built too early, the product risks adding complex states before the core marking experience is fast and trusted.

### 5.3 Planned Product Scope

| Capability | Expected behavior |
| --- | --- |
| Compare marking tab | Teacher can compare own contribution, peer review, moderator adjustment, and official result without making the grid noisy |
| Request review | Teacher can request peer review from permitted reviewers on the same student group/course context |
| Formal moderation actions | Send for moderation, approve, adjust, return to grader, and record internal notes where policy allows |
| Release governance | Distinguish draft, finalized, moderated, released, and visible-to-student/guardian states clearly |
| Audit trail | Drawer shows who marked, who moderated, what changed, and when |
| Class analytics | Distribution, missing/late work, low criteria clusters, trend by task type, and students needing intervention |
| Reporting handoff | Make it obvious which gradebook values are live and which reporting outputs are frozen at report-cycle materialization |
| Export / review snapshots | Controlled exports for department review or parent discussion without bypassing permission rules |

### 5.4 Architecture Integration

| Capability | Current owner | Integration direction |
| --- | --- | --- |
| Peer review and moderator marks | `Task Contribution.contribution_type`, `moderation_action`, `task_outcome_service._select_official_contribution` | Compare tab should render contribution layers without changing current official-selection rules unless policy is explicitly updated |
| Release state | `Task Outcome.grading_status`, `Task Outcome.is_published`, `published_on`, `published_by` | Use named server transitions and keep publication side effects server-owned |
| Audit trail | `Task Contribution`, `Task Outcome.modified`, user fields | Present a readable history but do not fabricate provenance from client-side timestamps |
| Analytics | Gradebook/outcome read models plus existing reporting services | Keep analytics queries server-side and permission-scoped; do not calculate reporting policy in Vue |
| Reporting handoff | `ifitwala_ed/assessment/term_reporting.py`, `Course Term Result` pipeline | Gradebook remains mutable operational data; reporting freezes official institutional truth at report-cycle boundaries |

### 5.5 Product Governance Questions To Resolve Before Coding

These decisions should be made explicitly before Phase 3 implementation:

| Question | Why it matters |
| --- | --- |
| Should peer review ever affect official result automatically, or only moderator/self contributions? | Current official selection ignores `Peer Review` as winner |
| Which statuses are user-driven versus system-driven? | Prevent teachers from setting contradictory states manually |
| What is the release policy by school/program/year? | Visibility and moderation rules may differ by institution |
| Should analytics be near-real-time or periodically materialized? | This affects query load, cache strategy, and dashboard freshness |
| What export formats are allowed and who can export? | Prevent accidental leakage of student data across tenant or role boundaries |

### 5.6 Acceptance Criteria

Phase 3 is done when:

- Teachers and moderators can compare marking layers and complete moderation without leaving the gradebook drawer.
- Official result selection, moderation actions, and publication state are transparent and auditable.
- Analytics highlight class-level and criterion-level risk without exposing unauthorized student data.
- Gradebook and term-report boundaries are obvious in the UI and consistent with `term_reporting.py`.
- Exports and review snapshots respect server-side permissions and school/group scope.
- Tests cover moderation transitions, official-result precedence, analytics scope constraints, and report handoff invariants.

---

## 6. Recommended Build Sequence

Status: **Planned sequencing**

This is the recommended engineering order to reduce rework:

| Step | Phase | Why this order |
| --- | --- | --- |
| 1 | Phase 1 | Define drawer UX contract and one bounded drawer bootstrap API |
| 2 | Phase 1 | Build mode-aware “My Marking” tab and server-validated save flow |
| 3 | Phase 1 | Add Evidence and Official Result tabs over existing Submission/Outcome layers |
| 4 | Phase 1 | Add previous/next student navigation and clear visibility/status actions |
| 5 | Phase 2 | Add rubric authoring in task setup so Criteria tasks become first-class end to end |
| 6 | Phase 2 | Add stale submission review, keyboard speed, and safe bulk actions |
| 7 | Phase 3 | Add compare/moderation tabs and named governance transitions |
| 8 | Phase 3 | Add analytics, reporting handoff UI, and scoped export workflows |

Do not skip Step 5 if Criteria grading is expected to be a core product workflow.
A top-tier gradebook cannot rely on a rubric model that teachers cannot author from the normal setup path.

---

## 7. Non-Goals And Anti-Patterns

Status: **Roadmap guardrails**

Do not introduce these patterns while implementing the drawer roadmap:

- Do not create a second official-result model in the SPA.
- Do not let Vue compute rubric totals or grade symbols that should come from `task_outcome_service.py`.
- Do not bypass `Task Contribution` and write official outcome fields directly as the normal grading path.
- Do not duplicate tenant/group scope logic in frontend-only filters.
- Do not build a drawer that requires one API call per tab per student row.
- Do not expose reviewer/moderator comparisons in the main grid if the drawer is the intended comparison surface.
- Do not ship Criteria authoring by inventing ad-hoc client-only rubric objects disconnected from `Task.task_criteria` and Assessment Criteria.

---

## 8. Documentation Update Rule

Status: **Required when phases ship**

When any phase is implemented:

- Update `ifitwala_ed/docs/assessment/03_gradebook_notes.md` if teacher UX flows change.
- Update `ifitwala_ed/docs/assessment/04_task_notes.md` if Task / Delivery / Outcome / Submission / Contribution contracts change.
- Update `ifitwala_ed/docs/assessment/01_assessment_notes.md` if assessment-layer rules change.
- Add code refs and test refs for new APIs/components.
- Mark shipped sections as implemented and leave future phases clearly marked as planned.

This prevents roadmap text from drifting into undocumented runtime behavior.
