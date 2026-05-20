# Phase 2a Triage And Batch Plan

## 1. Purpose

This file translates the completed Phase 1 audit into execution order and implementation boundaries without changing application code.

## 2. Source Summary

- Current audit path used: `.i18n-audit/current.json`
- Current audit generated at: `2026-05-20T10:37:50.753247+00:00`
- Files scanned: 2100
- Findings: 10097
- Warning findings: 1952
- Critical findings: 0
- Normalization-first findings: 328
- Review-needed findings: 1782
- Safe-mechanical findings: 7987
- Current exit decision: `READY FOR CONTROLLED PHASE 2F NON-ADMISSIONS SPA FOLLOW-UP WITH RISKS`

Historical note:

- The earlier Phase 1 audit summary referenced `ifitwala_ed/docs/audit/phase_01_i18n_audit.md`, but that artifact is not currently present in the repository.
- The older Python-first Batch 1 recommendation is superseded by the current audit state: warning-level Python backend findings are now cleared.
- The Admissions Inbox Vue pilot is complete: `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsInbox.vue` has zero current warning findings.
- The Admissions Workspace overlay follow-up is complete: `ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsWorkspaceOverlay.vue` has zero current warning findings.
- The Admissions Cockpit follow-up is complete: `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue` has zero current warning findings.
- The Task Delivery overlay follow-up is complete: `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue` has zero current warning findings.

## 3. Triage Model

All findings are classified into four buckets.

### Bucket A — Safe Mechanical

Definition:
- clearly user-facing
- literal string
- no interpolation problem
- no wording ambiguity
- safe to wrap mechanically later

### Bucket B — Interpolation Risk

Definition:
- user-facing
- currently constructed in a way that makes extraction or translation unsafe
- requires sentence restructuring before wrapping

### Bucket C — Normalization First

Definition:
- wrapping should wait until canonical English is confirmed

### Bucket D — Review Needed

Definition:
- uncertain whether user-facing
- uncertain wrapper choice
- unclear whether text is business truth vs display label

## 4. Classification Output

Notes:
- Current warning findings are safe-mechanical raw user-facing strings in SPA and markup/template surfaces.
- Current Python backend, Desk JS, and metadata findings are informational review debt, not warning-level wrapping debt.
- Review-needed and normalization-first findings must not be wrapped mechanically.

| Surface | Bucket A | Bucket B | Bucket C | Bucket D | Notes |
| ------- | -------- | -------- | -------- | -------- | ----- |
| Python backend | 0 warning / 1 safe warning before cleanup | 0 warning | 42 info | 1741 info | Warning-level backend raw-message debt is cleared; remaining backend findings are dynamic/raw review or wrapped-literal review and need human triage before changes. |
| Desk JS / classic client scripts | 0 warning | 0 warning | 54 info | 14 info | Existing wrapped literals need normalization/review, not broad mechanical wrapping. |
| Vue SPA | 1793 warning | 0 warning | 223 info | 13 info | Largest current warning surface; mostly raw template text and component attributes. |
| templates / website / print markup | 159 warning | 0 warning | 9 info | 14 info | Smaller than SPA but public/print-facing and should follow the SPA pilot rather than mix into it. |
| metadata DocTypes/workspaces/reports/json | 5981 info | 0 warning | 0 | 0 | Catalog extraction should cover these through the Frappe gettext pipeline; do not hand-edit metadata solely for translation convenience. |

## 5. Batch Strategy

- One surface at a time.
- One bucket at a time.
- No mixed PRs across unrelated surfaces.
- Interpolation and dynamic-message fixes handled separately from safe wrapping.
- Vue starts with one pilot page only.
- The Python warning-level safe batch is complete as of the current audit.
- The next implementation batch continues the admissions Vue pilot follow-up and excludes every string that is normalization-sensitive, dynamic-message-sensitive, or classification-sensitive.

## 6. First Recommended Execution Batch

## Superseded Batch 1 Scope

- Python server-side user-facing strings only
- Bucket A only
- no interpolation-risk cases
- no normalization-first cases
- no review-needed cases
- no JS
- no Vue
- no templates
- no reports unless they are pure Python and clearly Bucket A

| File / Module Area | Reason Included | Exclusions / Risks |
| ------------------ | --------------- | ------------------ |
| `ifitwala_ed/accounting/doctype/account_holder/account_holder.py` | Single plain validation sentence: `Organization is required`. Clear user-facing Desk validation copy. | Exclude dynamic organization-context wording from `account_holder_utils.py`; those lines are interpolation-risk. |
| `ifitwala_ed/admission/admission_utils.py` | Two assignment-state validation messages are plain sentences with no dynamic assembly. | Exclude any admissions wording tied to status normalization or dynamic applicant context. |
| `ifitwala_ed/api/enrollment_analytics.py` | Contains straightforward sign-in, permission, and scope-denial messages. These are stable server-owned UX strings. | Exclude any future lines that add dynamic organization/school names or formatted placeholders. |
| `ifitwala_ed/api/inquiry.py` | Safe only for the login and permission messages. | Exclude `Invalid assignment_lane filter.` because it exposes an internal parameter name and belongs in review-needed triage. |
| `ifitwala_ed/api/student_demographics_dashboard.py` | Same safe pattern as other analytics endpoints: sign-in and permission failures only. | Exclude any future filter/detail messages that carry dynamic context. |
| `ifitwala_ed/api/student_log_dashboard.py` | Safe only for the two plain access-control messages. | Exclude `Student Lookup Error`; it reads like a diagnostic title and should stay out of the first batch. |
| `ifitwala_ed/api/student_overview_dashboard.py` | Includes stable sign-in and access-denial sentences with no interpolation. | Exclude any lookup/debug titles or dynamic student-resolution failures if found during implementation. |
| `ifitwala_ed/api/class_hub.py` | Safe only for `Login required` and `Not permitted to access this class.` | Exclude all parameter/payload validation strings such as `student_group`, `lesson_instance`, `signals_json`, `payload_json`, and `students must be a list`. |
| `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.py` | Safe only for `Not permitted to reorder units for this course.` | Exclude `unit_names must be...`, `program is required.`, and payload-oriented messages because they expose internal field names. |
| `ifitwala_ed/school_settings/doctype/school_schedule/school_schedule.py` | Safe only for the plain success messages `School Schedule Days and Blocks have been cleared.` and `School Schedule Blocks have been generated.` | Exclude the interpolated rotation-day success string and the `No School Schedule Days found...` line from Batch 1. |

Current status:

- Superseded by the current audit. Python backend has no warning-level findings after the safe raw `frappe.msgprint(...)` cleanup in `ifitwala_ed/hr/workspace_utils.py`.

## 6.1 Completed Vue Pilot Batch

## Batch 2 Scope

- Vue SPA admissions pilot only
- warning-level `safe_mechanical` findings only
- raw visible template text and display-only attributes only
- no normalization-first findings
- no review-needed findings
- no backend, Desk JS, metadata, templates, website, report, or print markup in the same batch

| File / Surface | Current Warning Count | Reason Included | Exclusions / Risks |
| -------------- | --------------------- | --------------- | ------------------ |
| `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsInbox.vue` | 85 | Admissions is the recommended high-value pilot domain and this is the largest admissions warning file in the current audit. | Exclude workflow statuses, payload keys, route names, and any copy that is classification-sensitive or normalization-sensitive. |

Current status:

- Complete. Current audit reports zero warning findings in `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsInbox.vue`.

## 6.2 Completed Vue Follow-Up Batch

## Batch 3 Scope

- Vue SPA admissions follow-up only
- warning-level `safe_mechanical` findings only
- raw visible template text and display-only attributes only
- no normalization-first findings
- no review-needed findings
- no backend, Desk JS, metadata, templates, website, report, or print markup in the same batch

| File / Surface | Current Warning Count | Reason Included | Exclusions / Risks |
| -------------- | --------------------- | --------------- | ------------------ |
| `ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsWorkspaceOverlay.vue` | 50 | Natural second admissions SPA batch after the inbox page. | Exclude dynamic labels whose source may be server-owned product truth. |

Current status:

- Complete. Current audit reports zero warning findings in `ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsWorkspaceOverlay.vue`.

## 6.3 Completed Vue Follow-Up Batch

## Batch 4 Scope

- Vue SPA admissions follow-up only
- warning-level `safe_mechanical` findings only
- raw visible template text and display-only attributes only
- no normalization-first findings
- no review-needed findings
- no backend, Desk JS, metadata, templates, website, report, or print markup in the same batch

| File / Surface | Current Warning Count | Reason Included | Exclusions / Risks |
| -------------- | --------------------- | --------------- | ------------------ |
| `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue` | 22 | Admissions staff page that can follow after the overlay batch. | Exclude analytics/status copy pending workflow-language review. |

Current status:

- Complete. Current audit reports zero warning findings in `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`.

## 6.4 Completed Vue Follow-Up Batch

## Batch 5 Scope

- Vue SPA non-admissions follow-up only
- warning-level `safe_mechanical` findings only
- raw visible template text and display-only attributes only
- no normalization-first findings
- no review-needed findings
- no backend, Desk JS, metadata, templates, website, report, or print markup in the same batch

| File / Surface | Current Warning Count | Reason Included | Exclusions / Risks |
| -------------- | --------------------- | --------------- | ------------------ |
| `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue` | 97 | Largest current Vue warning file in the audit output. | Read the task/assessment/curriculum feature contract first; exclude workflow statuses, payload keys, route names, and server-owned labels. |

Current status:

- Complete. Current audit reports zero warning findings in `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`.

## 6.5 Current Recommended Execution Batch

## Batch 6 Scope

- Vue SPA non-admissions follow-up only
- warning-level `safe_mechanical` findings only
- raw visible template text and display-only attributes only
- no normalization-first findings
- no review-needed findings
- no backend, Desk JS, metadata, templates, website, report, or print markup in the same batch

| File / Surface | Current Warning Count | Reason Included | Exclusions / Risks |
| -------------- | --------------------- | --------------- | ------------------ |
| `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue` | 89 | Largest current Vue warning file after the task delivery overlay batch. | Read the class planning and curriculum task-delivery contracts first; exclude workflow statuses, payload keys, route names, and server-owned labels. |

## 7. Explicit Exclusions from Batch 1

- f-strings in messages
- concatenated messages
- `.format(...)`-built messages
- computed statuses
- JS dialog strings
- Vue text nodes
- templates and website copy
- report surfaces
- wording under normalization review
- uncertain user-facing cases
- diagnostic or operator-facing titles such as `TRACE`, `SANITIZED`, `LEAKAGE`, `COLLISION`, `MISMATCH`, and similar debug-style labels
- backend strings that expose internal parameter names or payload keys such as `student_group`, `lesson_instance`, `signals_json`, `payload_json`, `assignment_lane`, `unit_names`, `source_doctype`, `source_name`, and `slot_key`

## 8. Proposed Phase Sequence

1. Phase 2b Batch 1 — Python backend warning-level safe raw messages: complete.
2. Phase 2c — one Vue admissions pilot page: complete.
3. Phase 2d — remaining admissions SPA surfaces after pilot review: complete for the workspace overlay.
4. Phase 2e — remaining admissions cockpit SPA page: complete.
5. Phase 2f — remaining Vue/shared components by product surface: in progress; next target is `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`.
6. Phase 2g — templates / website / report / print markup surfaces.
7. Phase 2h — review-needed and normalization-first triage.
8. Phase 2i — extraction/catalog generation.
9. Phase 2j — PO validation and translation automation.

No current audit evidence justifies a broad multi-surface wrapping pass. The warning debt is concentrated in Vue and markup, so the safest next step is a file-scoped Vue follow-up batch.

## 9. Readiness Decision

PHASE 2F READY WITH RISKS

- The audit is complete enough to continue Vue warning cleanup without re-triaging the full repo.
- The current warning debt is dominated by raw Vue template text and display-only attributes.
- Normalization is not fully frozen for empty states and submit-failure wording, so follow-up batches must continue to exclude Bucket C strings.
- The main operational risk is accidentally translating contract values, workflow statuses, route names, payload keys, or server-owned labels.
- Keeping follow-up batches file-scoped is safer than widening to many SPA files at once.

## Next Agent Task Recommendation

Phase 2f — Batch 6: wrap warning-level safe-mechanical strings in `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue` only, after reading the relevant class planning and curriculum contracts.
