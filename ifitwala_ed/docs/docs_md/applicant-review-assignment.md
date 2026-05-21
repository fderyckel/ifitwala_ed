---
title: "Applicant Review Assignment: Reviewer Work Item"
slug: applicant-review-assignment
category: Admission
doc_order: 9
version: "1.3.0"
last_change_date: "2026-05-21"
summary: "Route admissions review work to the right reviewer for evidence submissions, health clearance, and overall application recommendations."
seo_title: "Applicant Review Assignment: Reviewer Work Item"
seo_description: "Use Applicant Review Assignment as the system-generated work item for admissions document, health, and overall application review."
---

## What Is an Applicant Review Assignment?

`Applicant Review Assignment` is a system-created work item that tells a reviewer what needs a decision. It is not the evidence record, health profile, or applicant decision itself. It is the task wrapper around review work.

Assignments are created from [**Applicant Review Rule**](/docs/en/applicant-review-rule/) and consumed primarily through Focus or applicant workspace surfaces.

## Why This Matters

- **Review work becomes visible.** Reviewers know what needs a decision.
- **Evidence truth stays in the right record.** Document item decisions update Applicant Document Item and parent document state.
- **Health review stays connected.** Health assignment decisions update Applicant Health Profile review status.
- **Overall application review remains advisory.** Overall recommendations do not mutate Student Applicant status.
- **Assigned reviewers get read-only context.** Reviewers can inspect the applicant folder before deciding.

## Before Review Assignments Are Created

You should have:

- [**Applicant Review Rule**](/docs/en/applicant-review-rule/) configured for the relevant organization/school/target
- submitted evidence, declared health profile, or submitted applicant workflow that should trigger review
- reviewer users or roles ready

## Information It Carries

| Area | What it controls | Why it matters |
|---|---|---|
| Target type | Applicant Document Item, Applicant Health Profile, or Student Applicant | Defines what the reviewer is deciding |
| Target record | The exact item/profile/applicant under review | Keeps review action precise |
| Assignee | One user or one role | Gives review work a clear owner or queue |
| Status | Open, Done, or Cancelled | Controls Focus visibility |
| Decision | Target-specific outcome | Writes back to the correct canonical record |
| Scope fields | Organization, school, program offering | Keeps review access scoped |

## How This Fits the Admissions Workflow

<Steps title="Applicant review assignment flow">
  <Step title="Rules match">
    Active Applicant Review Rules match the applicant scope and target type.
  </Step>
  <Step title="Assignments materialize">
    The workflow creates open assignments for the matched user or role reviewers.
  </Step>
  <Step title="Reviewer inspects context">
    The assigned reviewer gets read-only access to the applicant folder and relevant evidence.
  </Step>
  <Step title="Reviewer submits decision">
    The decision updates the target record where appropriate and marks the assignment done.
  </Step>
</Steps>

## Permission Matrix

| Role / Actor | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Scoped administrative access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Can manage assignments in authorized applicant scope |
| `Admission Manager` | Yes | Yes | Yes | Yes | Can manage assignments in authorized applicant scope |
| Assigned reviewer | Yes | No | No | No | Can read own open or historical assignment in authorized applicant scope |
| Assigned role reviewer | Yes | No | No | No | Can read assignments for one of their roles in authorized applicant scope |
| `Admission Officer` | Conditional | No | No | No | Reads only assignments where they are user or role assignee |

## Practical Examples

### Document item review

An uploaded transcript creates an Applicant Document Item assignment. The reviewer approves, marks needs follow-up, or rejects the item. The parent Applicant Document then resyncs aggregate review state.

### Health clearance

A family marks health declaration complete. The assignment routes to the configured reviewer, whose decision updates Applicant Health Profile review status.

### Overall application recommendation

An overall reviewer recommends admit, waitlist, reject, or needs follow-up. This is advisory and does not directly change Student Applicant application status.

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Configure rules before expecting assignments to appear.</Do>
  <Do>Use Focus for non-admissions reviewer queues.</Do>
  <Do>Review applicant context before submitting a decision.</Do>
  <Dont>Treat assignments as the canonical evidence record.</Dont>
  <Dont>Use Focus document-item actions for admissions-staff evidence review when applicant context is the canonical surface.</Dont>
</DoDont>

## Common Questions

### What can an assignment target?

Exactly one of `Applicant Document Item`, `Applicant Health Profile`, or `Student Applicant`.

### Are parent Applicant Document rows review targets?

No. Parent rows are aggregate requirement cards. Document review assignments target Applicant Document Item.

### Does an overall application decision approve the applicant?

No. Overall application decisions are advisory and do not mutate `Student Applicant.application_status`.

## Related Docs

<RelatedDocs
  slugs="applicant-review-rule,student-applicant,applicant-document,applicant-health-profile"
  title="Continue With Related Applicant Review Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-21)

Status: Implemented

Code refs:

- `ifitwala_ed/admission/doctype/applicant_review_assignment/applicant_review_assignment.json`
- `ifitwala_ed/admission/doctype/applicant_review_assignment/applicant_review_assignment.py`
- `ifitwala_ed/admission/applicant_review_workflow.py`

Test refs:

- `ifitwala_ed/admission/doctype/applicant_review_assignment/test_applicant_review_assignment.py`
- `ifitwala_ed/api/test_focus_applicant_review.py`

### Target and Decision Contract

- Schema supports:
  - `Applicant Document Item`
  - `Applicant Health Profile`
  - `Student Applicant`
- Assignment actor contract: exactly one of `assigned_to_user` or `assigned_to_role`.
- Open-assignment uniqueness is enforced per target + assignee.
- Lifecycle:
  - `Open`
  - `Done`
  - `Cancelled`
- Decision mapping:
  - `Applicant Document Item`: `Approved`, `Needs Follow-Up`, `Rejected`
  - `Applicant Health Profile`: `Cleared`, `Needs Follow-Up`
  - `Student Applicant`: `Recommend Admit`, `Recommend Waitlist`, `Recommend Reject`, `Needs Follow-Up`
- Document item target decisions write `Applicant Document Item.review_status` and resync parent bucket from items.
- Health target decisions write `Applicant Health Profile.review_status`.
- Overall application decisions are advisory.

### User Surfaces

- Focus shows open assignments and supports claim / reassign / submit for non-admissions reviewers and Health / Overall Application review work.
- Open assignments grant read-only applicant-folder access across Student Applicant, Applicant Health Profile, Applicant Document, Applicant Document Item, Recommendation Submission, interview workspace payloads, and governed file downloads for that applicant.
- Admissions roles do not use Focus for Applicant Document Item evidence review; they work from applicant context.
- Admissions cockpit applicant workspace and Desk `Student Applicant.documents_summary` are the canonical admissions-staff evidence review surfaces.
- Desk `Student Applicant.review_assignments_summary` renders completed Health and Overall Application decisions.
- Document reviewer truth is rendered in `Student Applicant.documents_summary`.
- Admissions-workspace users are intentionally blocked from Applicant Document Item Focus actions.
