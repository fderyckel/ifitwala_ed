---
title: "Applicant Interview Feedback: Per-Interviewer Notes"
slug: applicant-interview-feedback
category: Admission
doc_order: 9
version: "1.5.0"
last_change_date: "2026-05-28"
summary: "Capture each interviewer's structured notes and recommendation for one admissions interview without overwriting other panel members."
seo_title: "Applicant Interview Feedback"
seo_description: "Use Applicant Interview Feedback for per-interviewer admissions notes linked to Applicant Interview with Draft/Submitted status and row-level access control."
---

## What Is Applicant Interview Feedback?

`Applicant Interview Feedback` is one interviewer's structured notes for one [**Applicant Interview**](/docs/en/applicant-interview/).

It is the only canonical place for interviewer opinion. The parent interview stores the event; feedback rows store what each interviewer thought, recommended, or flagged.

## Why This Matters

- **Every interviewer has their own accountable row.**
- **Notes do not collide in one shared text field.**
- **Draft and submitted feedback states are clear.**
- **Applicant interview summaries can show feedback completion.**
- **Panel opinions stay traceable by interviewer user and timestamp.**

## Before You Write Feedback

You must be listed as an interviewer on the parent Applicant Interview to write or submit feedback.

On Desk, listed interviewers can use `Open My Feedback` from the parent interview. In the SPA workspace, the interface presents this as `Interview Notes` so staff do not need to think about the separate storage row. Scoped admissions users, counselors, academic admins, and the note owner can read saved notes when the workspace exposes them, but they do not get the editor unless they are assigned interviewers.

## Information You Manage

| Field | What it controls | Why it matters |
|---|---|---|
| Applicant Interview | Interview event this feedback belongs to | Keeps opinion attached to the right event |
| Student Applicant | Applicant being reviewed | Auto-synced from the interview |
| Interviewer User | Person responsible for this feedback | Enforces one row per interviewer |
| Feedback status | Draft or Submitted | Shows whether notes are final |
| Submitted on | Timestamp when submitted | Supports accountability |
| Strengths / concerns / shared values / other notes | Structured feedback areas | Keeps review comments organized |
| Recommendation | Interviewer's recommendation | Supports admissions decision context |

## How This Fits the Admissions Workflow

<Steps title="Interview feedback flow">
  <Step title="Open interview workspace">
    Open the interview from Staff calendar, Admissions Cockpit, or the parent interview form.
  </Step>
  <Step title="Write personal notes">
    Each interviewer writes their own structured notes instead of sharing one parent field.
  </Step>
  <Step title="Save draft or submit">
    Drafts can be revised. Submitted rows are treated as completed feedback.
  </Step>
  <Step title="Surface completion">
    Applicant summaries show feedback completion from submitted feedback rows.
  </Step>
</Steps>

## Permission Matrix

| Role / Actor | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | No | No | No | Scoped administrative read access; feedback submission remains interviewer-owned |
| `Academic Admin` | Yes | No | No | No | Scoped to applicant organization/school visibility |
| `Admission Manager` | Yes | No | No | No | Scoped to applicant organization/school visibility |
| `Admission Officer` | Yes | No | No | No | Scoped to applicant organization/school visibility |
| `Counselor` | Yes | No | No | No | Read-only within school scope |
| Listed interviewer | Yes | Yes | Yes | No | Own feedback row only; must be listed on the interview |
| `Curriculum Coordinator` | No broad access | No broad access | No broad access | No | Can act only when listed as interviewer |

## Practical Examples

### Two-person panel

Two interviewers attend the same applicant interview. Each submits their own feedback row, so their recommendations remain separate and attributable.

### Draft before final submission

An interviewer saves notes as Draft immediately after the meeting, then submits once the recommendation is complete.

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use your own feedback row for your own notes and recommendation.</Do>
  <Do>Submit feedback when your notes are final.</Do>
  <Dont>Store panel opinion in the parent Applicant Interview notes field.</Dont>
  <Dont>Overwrite another interviewer's feedback.</Dont>
</DoDont>

## Common Questions

### Can non-privileged users edit someone else's feedback?

No. Non-privileged interviewers can access only their own row and only when listed on the interview.

### Can submitted feedback go back to draft?

Downgrade from `Submitted` to `Draft` is blocked for non-privileged users.

## Related Docs

<RelatedDocs
  slugs="applicant-interview,student-applicant"
  title="Continue With Related Interview Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-21)

- **DocType schema**: `ifitwala_ed/admission/doctype/applicant_interview_feedback/applicant_interview_feedback.json`
- **Controller**: `ifitwala_ed/admission/doctype/applicant_interview_feedback/applicant_interview_feedback.py`
- **Unique/index setup**: `on_doctype_update()`
- **Permission hooks**:
  - `get_permission_query_conditions(...)`
  - `has_permission(...)`

### Invariants

- Unique pair: `(applicant_interview, interviewer_user)`.
- `student_applicant` is auto-synced from interview.
- Non-privileged users can only create/edit their own row.
- User must be listed in `Applicant Interview.interviewers` to create/edit.
- Scoped admissions users, counselors, academic admins, and the note owner can read saved notes without receiving edit controls.
- Downgrade `Submitted -> Draft` is blocked for non-privileged users.
- Parent `Applicant Interview` fields are not used to store panel opinion or a combined interview judgment.

### Surface Usage

- Used by `AdmissionsWorkspaceOverlay` opened from Staff calendar or Admissions Cockpit.
- The SPA hides the editable note form unless the current user is assigned to the interview.
- Read-only note cards remain visible to scoped admissions, counselor, academic admin, and note-owner readers.
- Desk `Open My Feedback` opens the current user's existing feedback row or starts a prefilled draft.
- Workspace APIs:
  - `get_interview_workspace(interview=...)`
  - `save_my_interview_feedback(...)`
