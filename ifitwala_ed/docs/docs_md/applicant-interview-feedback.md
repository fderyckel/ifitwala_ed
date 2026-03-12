---
title: "Applicant Interview Feedback: Per-Interviewer Notes"
slug: applicant-interview-feedback
category: Admission
doc_order: 9
version: "1.2.0"
last_change_date: "2026-03-12"
summary: "Store the only canonical interviewer-opinion record per interviewer per admissions interview, avoiding collisions on any shared event note."
seo_title: "Applicant Interview Feedback"
seo_description: "Per-interviewer admissions interview feedback linked to Applicant Interview with Draft/Submitted status and row-level access control."
---

## Purpose

`Applicant Interview Feedback` stores structured notes per interviewer for one `Applicant Interview`.

This is the only canonical store for interviewer opinion. It prevents multi-interviewer collisions on one shared text field and enables clear accountability by user and timestamp.

## Core Model

- `applicant_interview` -> `Applicant Interview` (required)
- `student_applicant` -> `Student Applicant` (auto-synced from interview)
- `interviewer_user` -> `User` (required, one row per interviewer)
- `feedback_status` -> `Draft` or `Submitted`
- `submitted_on` (set when status becomes `Submitted`)
- Structured fields:
  - `strengths`
  - `concerns`
  - `shared_values`
  - `other_notes`
  - `recommendation`

## Invariants

- Unique pair: `(applicant_interview, interviewer_user)`.
- Non-privileged users can only create/edit their own row.
- User must be listed in `Applicant Interview.interviewers` to access/edit.
- Downgrade `Submitted -> Draft` is blocked for non-privileged users.
- Parent `Applicant Interview` fields are not used to store panel opinion or a combined interview judgment.

## SPA Usage

Used by `AdmissionsWorkspaceOverlay` opened from `StaffHome` calendar when the clicked `School Event` references `Applicant Interview`.

Workspace APIs:
- `get_interview_workspace(interview=...)`
- `save_my_interview_feedback(...)`

## Related Docs

- [**Applicant Interview**](/docs/en/applicant-interview/)
- [**Student Applicant**](/docs/en/student-applicant/)

## Technical Notes (IT)

- **DocType schema**: `ifitwala_ed/admission/doctype/applicant_interview_feedback/applicant_interview_feedback.json`
- **Controller**: `ifitwala_ed/admission/doctype/applicant_interview_feedback/applicant_interview_feedback.py`
- **Unique/index setup**: `on_doctype_update()`
- **Permission hooks**:
  - `get_permission_query_conditions(...)`
  - `has_permission(...)`
- **Scope contract**:
  - staff roles (`Admission Officer`, `Admission Manager`, `Academic Admin`, `System Manager`) are scoped by applicant organization/school visibility
  - non-privileged interviewers can access only their own row and only when listed on the interview
  - no cross-panel opinion merge is stored at the interview-event level
