---
title: "Admissions Cockpit: Applicant Progress and Blockers"
slug: admission-cockpit
category: Admission
doc_order: 3
version: "1.1.0"
last_change_date: "2026-05-21"
summary: "Monitor active applicants, blockers, assignments, messages, offers, deposits, and enrollment-plan actions from one staff cockpit."
seo_title: "Admissions Cockpit: Applicant Progress and Blockers"
seo_description: "Use Admissions Cockpit to monitor active applicants by stage, filter admissions scope, review blockers, open applicant workspaces, and run offer, deposit, and enrollment-plan actions."
---

## What Is the Admissions Cockpit?

`Admissions Cockpit` is the staff command surface for active applications. It gives admissions teams one applicant-centered view of progress, blockers, assignments, unread applicant replies, interview status, offer state, and deposit readiness.

Families and applicants do not use this page. They use the authenticated `/admissions` portal. The cockpit is for staff who need to decide what to open next, what is blocked, and where the team is falling behind.

<Callout type="info" title="Why Ifitwala Ed is different">
The cockpit brings readiness, review work, messages, interviews, offers, deposits, and enrollment-plan actions into the same applicant board. Staff can move from "what is blocked?" to "open the right workspace" without losing the applicant context.
</Callout>

## Why This Matters

- **Admissions teams see the whole active pipeline.** Applicants are grouped by stage instead of buried in separate lists.
- **Blockers are visible before staff open records.** Missing documents, policies, health clearance, deposits, and reviewer gaps surface early.
- **Staff can start from their own work.** `My Assignments Only` is the default working view.
- **Actions stay close to context.** Staff can schedule interviews, open messages, review recommendations, send offers, hydrate requests, and generate deposit invoices from the applicant card when allowed.
- **Server rules still protect the workflow.** The cockpit shows actions, but downstream Student Applicant, Applicant Enrollment Plan, and finance rules own final eligibility.

## Before You Use the Cockpit

You should have:

- admissions staff with the correct admissions role and scoped access
- [**Admission Settings**](/docs/en/admission-settings/) configured for SLA, offer, hydration, or deposit behavior
- [**Student Applicant**](/docs/en/student-applicant/) records as the applicant record of truth
- required [**Applicant Document Type**](/docs/en/applicant-document-type/), health, policy, recommendation, and [**Applicant Interview**](/docs/en/applicant-interview/) workflows configured before relying on readiness signals
- [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/) configured before using offer, deposit, or enrollment-request actions

Open it from:

- `/hub/staff/admission-cockpit`
- `/staff/admission-cockpit`

## What Staff See

| Area | What it shows | Why it matters |
|---|---|---|
| Filters | Organization, School, and My Assignments Only | Keeps the board scoped to the team or school being reviewed |
| KPI tiles | Active applications, blocked, ready for decision, accepted pending promotion, open assignments, unread replies | Gives managers a quick operational pulse |
| Top Admission Blockers | Missing policies, document requirements, health not cleared, profile incomplete, no reviewer, deposit not ready | Shows what is slowing applicants down |
| Applicant board | Preparation, Submitted, Review, Accepted lanes | Lets staff scan the pipeline by stage |
| Applicant cards | Name, status, school, offering, readiness pills, interview summary, messages, blockers, plan/deposit state | Helps staff choose the next action without opening every record |

## How This Fits the Admissions Workflow

<Steps title="Daily cockpit workflow">
  <Step title="Start with your assignments">
    Use `My Assignments Only` to clear your own review and follow-up work first.
  </Step>
  <Step title="Scan blockers">
    Use blocker chips to focus on one type of missing work, such as documents, health, policies, or deposit readiness.
  </Step>
  <Step title="Open applicant context">
    Open the applicant workspace or Desk record from the card so evidence, messages, and review status stay together.
  </Step>
  <Step title="Run eligible actions">
    Schedule interviews, open recommendation review, send offers, hydrate enrollment requests, or generate deposit invoices only when the card shows the action is available.
  </Step>
  <Step title="Widen the view">
    After urgent assigned work is handled, widen filters to review team throughput across schools or stages.
  </Step>
</Steps>

## Permission Matrix

The cockpit is a staff operations page. It does not grant permission to bypass downstream document, approval, offer, deposit, or finance rules.

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

## Practical Examples

### Morning admissions standup

An Admissions Manager opens the cockpit, checks blocked counts, scans top blockers, and assigns the team to clear health, document, or policy blockers before new outreach begins.

### My assignments first

An Admission Officer starts with `My Assignments Only`, opens applicants with unread replies or pending review tasks, then clears the next action from the applicant workspace.

### Offer and deposit review

For accepted applicants, the cockpit shows whether the Applicant Enrollment Plan can send an offer, hydrate a request, or generate a draft deposit invoice. Finance still owns invoice submission and payment recording.

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use the cockpit to find and open the next applicant action quickly.</Do>
  <Do>Keep organization and school filters aligned with the team you are reviewing.</Do>
  <Do>Use blocker chips to focus the board on one problem type at a time.</Do>
  <Do>Use applicant workspace links for evidence so applicant context stays intact.</Do>
  <Dont>Treat the cockpit as a replacement for server-side approval, promotion, or finance rules.</Dont>
  <Dont>Manually bypass readiness, deposit, or offer requirements because a card looks close to complete.</Dont>
  <Dont>Use internal notes for applicant-facing instructions.</Dont>
</DoDont>

## Common Questions

### Why are rejected or promoted applicants missing?

Terminal statuses are excluded from the default cockpit payload. Rejected, withdrawn, and promoted applicants are not part of the normal active staff board unless terminal statuses are explicitly requested.

### Can the cockpit approve an applicant by itself?

No. Cockpit actions call downstream workflows, but Student Applicant, Applicant Enrollment Plan, and finance rules still enforce eligibility.

### Are internal notes visible to applicants?

No. Internal notes in the applicant case thread are staff-only. Applicant-visible replies must be written as applicant-facing messages.

### Does deposit invoice generation collect payment?

No. Deposit invoice generation creates or returns the draft invoice bridge owned by Applicant Enrollment Plan logic. Accounting still owns submission and payment recording.

## Related Docs

<RelatedDocs
  slugs="inquiry,student-applicant,applicant-enrollment-plan,applicant-document-type,applicant-document,applicant-health-profile,applicant-interview,applicant-review-assignment,admission-settings"
  title="Continue With Related Admission Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-21)

- **Staff URL**: `/hub/staff/admission-cockpit` in the deployed hub shell.
- **SPA route**: `/staff/admission-cockpit`, route name `staff-admission-cockpit`.
- **Route file**: `ifitwala_ed/ui-spa/src/router/index.ts`
- **SPA page**: `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`
- **Service map**: `ifitwala_ed/ui-spa/src/lib/admission.ts`
- **Backend API**: `ifitwala_ed/api/admission_cockpit.py`
- **Test refs**:
  - `ifitwala_ed/api/test_admission_cockpit.py`
  - `ifitwala_ed/ui-spa/src/pages/staff/__tests__/AdmissionsCockpit.test.ts`

### Payload and Actions

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
- **Default page payload**: `assigned_to_me = 1`, `limit = 120`
- **Backend limit bounds**: minimum `1`, maximum `250`
- **Role gate**: admissions roles plus `Academic Admin`, `System Manager`, and `Administrator`
- **Cache contract**: Redis cache prefix `admissions:cockpit:v2:` with 120-second TTL; cockpit action endpoints invalidate the admissions cockpit cache after mutation

### Stage and Blocker Contract

- **Default terminal exclusions**: `Rejected`, `Withdrawn`, and `Promoted`
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

### Data Sources and Integrations

- Applicant card sources include Student Applicant fields, readiness snapshot, Applicant Review Assignment rows, admissions case thread summaries, Applicant Interview summaries, Applicant Enrollment Plan state, recommendation state, health state, policy state, document state, and deposit state.
- Workspace integrations:
  - applicant workspace overlay: `admissions-workspace`
  - interview schedule overlay: `admissions-interview-schedule`
  - case communication thread uses Student Applicant context
- Analytics note: the page uses `analytics-shell`, `FiltersBar`, and `KpiRow`, but the implemented component lives under `ui-spa/src/pages/staff/admissions/` because it is an admissions cockpit with workflow actions, not a pure chart analytics route.
