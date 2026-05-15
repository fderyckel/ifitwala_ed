# Phase 2a Normalization Decisions

## 1. Purpose

This file locks canonical English decisions before translation wrapping begins, so Phase 2 implementation does not normalize wording ad hoc while touching code.

## 2. Source

These decisions were derived from the completed Phase 1 audit at `ifitwala_ed/docs/audit/phase_01_i18n_audit.md`.

## 3. Decision Table

| Group ID | Variant Strings Found | Recommended Canonical English | Keep Distinct Cases | Rationale | Decision Status |
| -------- | --------------------- | ----------------------------- | ------------------- | --------- | --------------- |
| NORM-01 | Could not load family finance.; Unable to load admissions portal; Could not load guardian home snapshot.; Couldn't open this policy; Unable to load organization chart context. | Unable to load {resource}. | `Unable to open {resource}.`; `Unable to save {resource}.`; `Unable to submit {resource}.` | Load-failure copy should use one verb family for the same failure mode. | ready |
| NORM-02 | Loading request...; Loading family finance...; Loading academic load analytics...; Loading calendar…; Loading your application… | Loading {resource}… | `Refreshing preview…`; `Load more`; `Loading context...` when it is an action-specific control label rather than a passive page state | Loading states should use one punctuation and sentence pattern across surfaces. | ready |
| NORM-03 | No stories published yet.; No published schools are available yet.; No active selection windows; No requests yet.; Nothing urgent right now.; Nothing scheduled in this range | No {resource} available for this view. | `No deadline`; `No location`; `No category`; `No follow-up recorded`; `No scheduled blocks` | Empty-state copy is the largest wording family in the audit, but some variants describe field absence rather than true zero-state UX. | needs_human_review |
| NORM-04 | Back to Home; Back to Family Snapshot; Back to Staff Home; Back to Courses; Back to Applicant; Back to Selection Board | Back to {destination} | `Back`; `Close`; `Return to` if a future surface uses materially different interaction semantics | Back-navigation labels should follow one pattern while preserving the destination noun. | ready |
| NORM-05 | Could not submit request.; Unable to submit recommendation.; Request could not be submitted.; Could not submit booking.; Could not submit course selection. | Unable to submit {resource}. | `Unable to save {resource}.`; `Unable to acknowledge {resource}.`; `Unable to approve {resource}.`; `Unable to complete {resource}.` | Submission failures should not mix passive and active voice, but workflow verbs still need to stay distinct. | needs_human_review |

## 4. High-Risk Language Notes

- Workflow verbs must stay distinct where business meaning differs: `save`, `submit`, `approve`, `acknowledge`, `complete`, `archive`, and `publish` are not interchangeable in this ERP.
- Permission language must stay consistent by meaning: `sign in`, `do not have permission`, `do not have access`, and `not permitted` reflect different states and should not be casually merged.
- Institutional nouns should remain stable across phases: `Organization`, `School`, `Academic Year`, `Student Group`, `Guardian`, `Program Offering`, `Class Hub`, `Enrollment Analytics`, and `Student Overview`.
- Technical parameter names found in some backend messages such as `student_group`, `lesson_instance`, `signals_json`, and `assignment_lane` should not be normalized into UX copy without separate review; these are triage risks, not normalization wins.
- Status-like wording in admissions and policy workflows should remain aligned with product truth. In particular, `Draft`, `Submitted`, `In Review`, `Approved`, `Rejected`, `Accepted`, `Acknowledged`, and `Signed` should not be simplified unless the owning workflow contract says so.

## 5. Normalization Freeze Recommendation

NORMALIZATION READY WITH RISKS

- NORM-01, NORM-02, and NORM-04 are sufficiently defined to support implementation.
- NORM-03 still needs a human pass to separate true empty states from field-absence wording.
- NORM-05 is close, but workflow verbs around submit/save/acknowledge/approve still need strict guardrails during implementation.
- The highest-risk vocabulary is concentrated in ERP workflow semantics, not generic UI chrome.
- Phase 2b can start safely if it excludes all strings that fall under the two `needs_human_review` groups.
