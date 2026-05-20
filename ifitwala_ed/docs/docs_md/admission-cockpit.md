---
title: "Admissions Cockpit: Applicant Progress and Blockers"
slug: admission-cockpit
category: Admission
doc_order: 3
version: "1.0.0"
last_change_date: "2026-05-20"
summary: "Monitor active applicants, blockers, assignments, messages, offers, deposits, and enrollment-plan actions from one staff cockpit."
seo_title: "Admissions Cockpit: Applicant Progress and Blockers"
seo_description: "Use Admissions Cockpit to monitor active applicants by stage, filter admissions scope, review blockers, open applicant workspaces, and run offer, deposit, and enrollment-plan actions."
---

## Before You Start (Prerequisites)

- Ensure admissions staff users have the correct admissions role and scoped access.
- Configure [**Admission Settings**](/docs/en/admission-settings/) before using SLA, offer, hydration, or deposit workflows.
- Create and maintain [**Student Applicant**](/docs/en/student-applicant/) records as the applicant record of truth.
- Configure required [**Applicant Document Type**](/docs/en/applicant-document-type/), [**Applicant Interview**](/docs/en/applicant-interview/), health, policy, and recommendation workflows before relying on readiness signals.
- Configure [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/) before using offer, deposit, or enrollment-request actions.

Admissions Cockpit is the staff-facing command surface for active applications. It gives admissions teams one applicant-centered view of progress, blockers, assignments, unread applicant replies, interview status, offer state, and deposit readiness.

## Where To Open It

Open the cockpit from the staff hub:

- Production-style path: `/hub/staff/admission-cockpit`
- SPA route path: `/staff/admission-cockpit`

The page is designed for staff operations. Families and applicants use the authenticated admissions portal instead.

## What It Solves

- Shows active applicants by stage without forcing staff to open every record one by one.
- Highlights the most common blockers across the current filter scope.
- Keeps application readiness visible across profile, documents, recommendations, policies, and health.
- Shows open review assignments and makes "My Assignments Only" the default working view.
- Brings messages, interview scheduling, recommendation review, enrollment-plan actions, and deposit actions closer to the applicant card.
- Helps staff move from "what is blocked?" to "what should I open next?" without losing applicant context.

<Callout type="tip" title="Best daily use">
Start with `My Assignments Only`, clear urgent blockers, then widen the scope to all applicants when reviewing team throughput.
</Callout>

## What Staff See

The cockpit has four main areas:

1. **Filters**
   - `Organization`
   - `School`
   - `My Assignments Only`
2. **KPI tiles**
   - Active Applications
   - Blocked
   - Ready for Decision
   - Accepted Pending Promotion
   - My Open Assignments
   - Unread Applicant Replies
3. **Top Admission Blockers**
   - Missing Policies
   - Requirements Awaiting Submission
   - Requirements Needing Attention
   - Health Not Cleared
   - Profile Incomplete
   - No Reviewer Assigned
   - Deposit Not Ready
4. **Applicant board**
   - Preparation
   - Submitted
   - Review
   - Accepted

Each applicant card can show the applicant name, application status, school, program offering, readiness pills, interview summary, unread communication count, top blockers, enrollment-plan state, and deposit state.

## Applicant Stages

| Staff board lane | Typical applicant statuses shown there |
|---|---|
| Preparation | `Draft`, `Invited`, `In Progress`, `Missing Info` |
| Submitted | `Submitted` |
| Review | `Under Review`, plus ready applicants awaiting decision |
| Accepted | Approved applicants waiting for promotion/enrollment bridge completion |

Terminal statuses are not part of the normal staff view. Rejected, withdrawn, and promoted applicants are excluded from the default cockpit payload.

## Common Staff Actions

From the cockpit, staff can:

- Create a new inquiry when the user has admissions inquiry creation access.
- Refresh the cockpit data.
- Open the applicant workspace from the applicant name.
- Schedule an interview for an applicant.
- Open or send applicant case communication.
- Open the Student Applicant Desk record.
- Review pending recommendations.
- Open the latest interview workspace.
- Open blockers directly in the applicant workspace when the blocker points to applicant evidence.
- Send an enrollment offer when the Applicant Enrollment Plan is ready for that action.
- Hydrate a Program Enrollment Request from an eligible Applicant Enrollment Plan.
- Generate a draft deposit invoice when deposit terms are ready and invoicing is allowed.
- Open the Applicant Enrollment Plan, Program Enrollment Request, or Sales Invoice when available.

<Callout type="warning" title="Do not bypass readiness">
The cockpit shows next actions, but server-side Student Applicant, Applicant Enrollment Plan, and deposit rules still own final eligibility. If an action is blocked, resolve the displayed blocker instead of manually changing statuses.
</Callout>

## Messages and Internal Notes

The `Message` action opens the applicant case thread for that Student Applicant. Staff can send an applicant-visible reply or mark the message as an internal note.

Internal notes are not visible to the applicant. Use them for staff coordination only.

## Enrollment Plan and Deposit Actions

When an applicant has an Applicant Enrollment Plan, the cockpit can show:

- plan name and status
- offer expiry date
- whether the offer can be sent
- whether a Program Enrollment Request can be hydrated
- whether a deposit is required
- deposit amount, due date, invoice, invoice status, paid amount, outstanding amount, overdue state, and override-approval state

Deposit invoice generation creates or returns the draft invoice bridge owned by Applicant Enrollment Plan logic. It is not a payment collection flow. Finance still owns invoice submission and payment recording.

## Operational Guardrails

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use the cockpit to find and open the next applicant action quickly.</Do>
  <Do>Keep organization and school filters aligned with the admissions team you are reviewing.</Do>
  <Do>Use blocker chips to focus the board on one type of missing work at a time.</Do>
  <Do>Use applicant workspace links for document, recommendation, health, and review evidence so the applicant context stays intact.</Do>
  <Do>Use the enrollment-plan buttons only when the card shows the action is available.</Do>
  <Dont>Treat the cockpit as a replacement for server-side approval, promotion, or finance rules.</Dont>
  <Dont>Manually bypass readiness, deposit, or offer requirements because a card looks close to complete.</Dont>
  <Dont>Use internal notes for applicant-facing instructions.</Dont>
</DoDont>

## Permission Matrix

| Role | Access Cockpit | Run Cockpit Actions | Notes |
|---|---|---|---|
| `System Manager` | Yes | Yes | Full operational access |
| `Administrator` | Yes | Yes | Full operational access |
| `Admission Manager` | Yes | Yes | Admissions operational owner |
| `Admission Officer` | Yes | Yes | Admissions operator |
| `Academic Admin` | Yes | Limited by downstream document/action permissions | Can access cockpit view; downstream actions still enforce their own rules |
| `Academic Staff` | No by this cockpit role gate | No | Academic review may happen through assignment/focus surfaces instead |
| `Admissions Applicant` | No | No | Uses `/admissions` portal |
| `Admissions Family` | No | No | Uses `/admissions` family workspace where enabled |

## Related Docs

<RelatedDocs
  slugs="inquiry,student-applicant,applicant-enrollment-plan,applicant-document-type,applicant-document,applicant-health-profile,applicant-interview,applicant-review-assignment,admission-settings"
  title="Continue With Related Admission Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-20)

- **Staff URL**: `/hub/staff/admission-cockpit` in the deployed hub shell.
- **SPA route**: `/staff/admission-cockpit`, route name `staff-admission-cockpit`.
- **Route file**: `ifitwala_ed/ui-spa/src/router/index.ts`
- **SPA page**: `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`
- **Service map**: `ifitwala_ed/ui-spa/src/lib/admission.ts`
- **Backend API**: `ifitwala_ed/api/admission_cockpit.py`
- **Test refs**:
  - `ifitwala_ed/api/test_admission_cockpit.py`
  - `ifitwala_ed/ui-spa/src/pages/staff/__tests__/AdmissionsCockpit.test.ts`

- **Main payload endpoint**: `ifitwala_ed.api.admission_cockpit.get_admissions_cockpit_data`
- **Action endpoints**:
  - `send_admissions_cockpit_offer(applicant_enrollment_plan)`
  - `hydrate_admissions_cockpit_request(applicant_enrollment_plan)`
  - `generate_admissions_cockpit_deposit_invoice(applicant_enrollment_plan)`
- **Main filters contract**:
  - `organization`
  - `school`
  - `assigned_to_me`
  - `include_terminal`
  - `application_statuses`
  - `limit`
- **Default page payload**: `assigned_to_me = 1`, `limit = 120`.
- **Backend limit bounds**: minimum `1`, maximum `250`; assigned-to-me prefetch can read a larger bounded candidate set before trimming to the requested limit.
- **Role gate**: admissions roles plus `Academic Admin`, `System Manager`, and `Administrator`.
- **Default terminal exclusions**: `Rejected`, `Withdrawn`, and `Promoted` are excluded unless terminal statuses are explicitly requested.
- **Backend stage IDs**:
  - `draft`
  - `in_progress`
  - `submitted`
  - `under_review`
  - `awaiting_decision`
  - `accepted_pending_promotion`
- **Displayed board lanes**:
  - `Preparation` combines backend `in_progress` and `draft`
  - `Submitted`
  - `Review` combines backend `awaiting_decision` and `under_review`
  - `Accepted` shows `accepted_pending_promotion`
- **Blocker kinds**:
  - `missing_policies`
  - `missing_documents`
  - `documents_unapproved`
  - `health_not_cleared`
  - `profile_incomplete`
  - `no_reviewer_assigned`
  - `deposit_not_ready`
- **Response sections**:
  - `config`
  - `counts`
  - `blockers`
  - `columns`
  - `generated_at`
- **Cache contract**: Redis cache prefix `admissions:cockpit:v2:` with 120-second TTL; cockpit action endpoints invalidate the admissions cockpit cache after mutation.
- **Applicant card sources**: Student Applicant fields, readiness snapshot, Applicant Review Assignment rows, admissions case thread summaries, Applicant Interview summaries, Applicant Enrollment Plan state, recommendation state, health state, policy state, document state, and deposit state.
- **Workspace integrations**:
  - applicant workspace overlay: `admissions-workspace`
  - interview schedule overlay: `admissions-interview-schedule`
  - case communication thread uses Student Applicant context
- **Analytics note**: The page uses `analytics-shell`, `FiltersBar`, and `KpiRow`, but the implemented component lives under `ui-spa/src/pages/staff/admissions/` because it is an admissions cockpit with workflow actions, not a pure chart analytics route under `ui-spa/src/pages/staff/analytics/`.
