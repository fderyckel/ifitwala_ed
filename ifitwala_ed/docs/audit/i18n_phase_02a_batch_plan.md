# Phase 2a Triage And Batch Plan

## 1. Purpose

This file translates the completed Phase 1 audit into execution order and implementation boundaries without changing application code.

## 2. Source Summary

- Real audit path used: `ifitwala_ed/docs/audit/phase_01_i18n_audit.md`
- Files scanned: 1385
- Candidate user-facing strings: 6257
- Unwrapped strings: 2114
- Unsafe interpolation cases: 873
- Normalization groups: 5
- Overall Phase 1 exit decision: `READY FOR PHASE 2 WITH RISKS`

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
- Bucket B counts come from the audit's unsafe-interpolation section.
- Bucket A/C/D counts come from the unwrapped-string section after removing rows that overlap with interpolation-risk findings.
- Python Bucket D includes the explicit uncertain set plus a very small manually triaged subset of diagnostic dialog-title rows that should not be wrapped blindly.

| Surface | Bucket A | Bucket B | Bucket C | Bucket D | Notes |
| ------- | -------- | -------- | -------- | -------- | ----- |
| Python backend | 67 | 787 | 1 | 5 | Dominated by `python_format_chain`; the safe subset is mostly permission, access, and plain validation messages. |
| Desk JS / classic client scripts | 36 | 15 | 0 | 4 | Most ambiguity comes from config labels that may be business truth rather than visible UI text. |
| Vue SPA | 1739 | 13 | 185 | 0 | Largest translation-debt surface by far; most work is raw template copy and component props, with normalization pressure concentrated in loading/empty/error states. |
| templates / website | 32 | 41 | 2 | 0 | Public pages are smaller in count but higher-risk because copy is public-facing and mixed with raw HTML/JS. |
| reports / print-facing UI | 11 | 17 | 1 | 0 | Small volume, but many report strings share interpolation-risk patterns and should not be mixed into Batch 1. |

## 5. Batch Strategy

- One surface at a time.
- One bucket at a time.
- No mixed PRs across unrelated surfaces.
- Interpolation fixes handled separately from safe wrapping.
- Vue starts with one pilot page only.
- Batch 1 stays Python-only and excludes every string that is normalization-sensitive, interpolation-sensitive, or classification-sensitive.

## 6. First Recommended Execution Batch

## Batch 1 Scope

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

1. Phase 2b Batch 1 — Python backend, Bucket A only
2. Phase 2c — Python interpolation-risk fixes
3. Phase 2d — Desk JS safe mechanical pass
4. Phase 2e — one Vue pilot page
5. Phase 2f — remaining Vue/shared components
6. Phase 2g — templates / website / report surfaces
7. Phase 2h — extraction/catalog generation

No audit evidence justifies changing that order. The Python unsafe-pattern load is materially larger than the safe Python subset, so separating Batch 1 from Phase 2c remains the right control.

## 9. Readiness Decision

PHASE 2B READY WITH RISKS

- The audit is complete enough to isolate a small Python-only Bucket A batch without re-triaging the full repo.
- The safe Python subset is real but much smaller than the raw backend findings list because many lines are interpolation-risk or technically phrased.
- Normalization is not fully frozen for empty states and submit-failure wording, so Batch 1 must continue to exclude Bucket C strings.
- The main operational risk is accidental inclusion of parameter-name or diagnostic strings that look user-facing at first glance.
- Keeping Batch 1 file-scoped and partial-file where needed is safer than widening scope to all backend rows.

## Next Agent Task Recommendation

Phase 2b — Batch 1: wrap safe Python server-side user-facing strings only
