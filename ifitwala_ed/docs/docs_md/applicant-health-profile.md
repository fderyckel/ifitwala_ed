---
title: "Applicant Health Profile: Health Disclosure and Clearance"
slug: applicant-health-profile
category: Admission
doc_order: 7
version: "2.5.0"
last_change_date: "2026-05-21"
summary: "Capture applicant health disclosure, vaccination proof, family/staff edits, review status, and health clearance for admissions readiness."
seo_title: "Applicant Health Profile: Health Disclosure and Clearance"
seo_description: "Use Applicant Health Profile to collect applicant health details, vaccination proof, family declarations, and staff clearance for admissions decisions."
---

## What Is an Applicant Health Profile?

`Applicant Health Profile` stores health and safeguarding information needed during admissions review. It gives families a structured place to provide health details, and gives staff a clear review status before approval when health clearance is required.

When a school requires health clearance before approval, this profile becomes part of Student Applicant readiness. If the school does not require health clearance, it can still provide useful context for admissions and onboarding.

<Callout type="info" title="Why Ifitwala Ed is different">
Health review is connected to the applicant journey without turning private health data into a loose attachment. Families can declare details in the portal, proof files use governed upload paths, and staff review state feeds readiness only when the school policy requires it.
</Callout>

## Why This Matters

- **Families can provide sensitive details in context.** Health disclosure happens inside the admissions portal where applicable.
- **Staff review is explicit.** Profiles move through `Pending`, `Needs Follow-Up`, and `Cleared`.
- **Readiness respects school policy.** Student Applicant approval is blocked by health only when the applicant school requires health clearance.
- **Vaccination proof stays governed.** Uploads follow the admissions Drive-governed file path.
- **Promotion can carry health data forward.** On promotion, health fields and vaccination rows can become Student Patient records.

## Before You Use Health Profiles

You should have:

- the [**Student Applicant**](/docs/en/student-applicant/) record
- internal review expectations for `Pending`, `Needs Follow-Up`, and `Cleared`
- applicant portal access/linkage set up if family-side editing is used
- school policy decided for whether health clearance is required before approval

## Information You Manage

| Area | What it controls | Why it matters |
|---|---|---|
| Student Applicant | Applicant linked to the health profile | Keeps health disclosure in the admissions context |
| Blood group and allergy fields | Basic health indicators and details | Helps staff understand immediate health considerations |
| Condition fields | Asthma through vision and other condition details | Captures specific health disclosures |
| Diet and medical history | Diet requirements, surgery/hospitalization, other notes | Supports safeguarding and onboarding context |
| Vaccination rows | Vaccine name, date, proof, and notes | Keeps vaccination evidence organized |
| Declaration fields | Family/applicant confirmation that health details are complete | Triggers review assignment materialization when completed |
| Review status and notes | Staff outcome and follow-up need | Feeds readiness when health clearance is required |

## How This Fits the Admissions Workflow

<Steps title="Applicant Health lifecycle">
  <Step title="Create profile">
    Create health profile context as an applicant enters active review.
  </Step>
  <Step title="Capture details">
    Families or staff add health details and vaccination proof while edits are allowed.
  </Step>
  <Step title="Declare complete">
    When family declaration becomes complete, matching review rules can materialize reviewer assignments.
  </Step>
  <Step title="Review">
    Staff reviewers move the profile to `Cleared` or `Needs Follow-Up`.
  </Step>
  <Step title="Gate approval when required">
    If the school requires health clearance, Student Applicant readiness waits for `Cleared`.
  </Step>
  <Step title="Promote">
    On promotion, health fields and vaccination rows are copied into Student Patient / Student Patient Vaccination.
  </Step>
</Steps>

## Permission Matrix

Health data is sensitive. Family/applicant edits are limited by applicant linkage and status; staff access is scoped by applicant visibility.

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Scoped to applicant visibility |
| `Admission Manager` | Yes | Yes | Yes | Yes | Scoped to applicant visibility |
| `Admission Officer` | Yes | Yes | Yes | Yes | Scoped to applicant visibility |
| `Nurse` | Yes | Yes | Yes | Yes | Staff review role |
| `Guardian` | Yes | Yes | Yes | No | Legacy role permission; linked-guardian rows only |
| `Admissions Applicant` | Yes | Yes | Yes | No | Own applicant rows only |
| `Admissions Family` | Yes | Yes | Yes | No | Family workspace only; explicit guardian linkage required |

Runtime rules:

- family/applicant editing requires valid linkage and permitted applicant status
- admissions/academic staff are applicant organization/school scoped
- assigned reviewers with open Applicant Review Assignment get read-only applicant folder access
- review fields are staff-only
- terminal applicant states `Rejected` and `Promoted` are read-only

## Practical Examples

### Health required before approval

The school enables health clearance as an approval requirement. The applicant profile remains blocked until the health profile is reviewed and marked `Cleared`.

### Needs follow-up

A family declares an allergy or missing vaccination proof. Staff set review status to `Needs Follow-Up`, and the applicant can resolve the missing or unclear information while editing is allowed.

### Vaccination proof

Families upload proof through the admissions portal. The file is handled through the governed Drive path and linked back through canonical file URLs.

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Keep reviewer outcomes explicit: Pending, Needs Follow-Up, or Cleared.</Do>
  <Do>Use governed vaccination-proof uploads and canonical file URLs.</Do>
  <Do>Explain health blockers clearly to families when follow-up is needed.</Do>
  <Dont>Approve applicants while required health review is unresolved.</Dont>
  <Dont>Allow family-side edits after locked applicant states.</Dont>
  <Dont>Store vaccination proof through ad-hoc file paths.</Dont>
</DoDont>

## Common Questions

### Does every applicant need health clearance?

Only when the applicant school has health clearance required for approval. Otherwise, the profile can still store useful health context without blocking approval readiness.

### Who can update review status?

Review fields are staff-only for admissions staff, academic admin, System Manager, and Nurse roles according to scope and runtime rules.

### Can assigned reviewers see supporting applicant context?

Yes. An assigned reviewer with an open Applicant Review Assignment can inspect the applicant folder read-only while the review assignment remains open.

## Related Docs

<RelatedDocs
  slugs="student-applicant,applicant-interview,applicant-document"
  title="Continue With Related Applicant Review Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-21)

- **DocType schema file**: `ifitwala_ed/admission/doctype/applicant_health_profile/applicant_health_profile.json`
- **Controller file**: `ifitwala_ed/admission/doctype/applicant_health_profile/applicant_health_profile.py`
- **Required fields (`reqd=1`)**:
  - `student_applicant` (`Link` -> `Student Applicant`)
- **Lifecycle hooks in controller**: `validate`
- **Operational/public methods**: none beyond standard document behavior
- **Autoname**: `hash`
- **Primary link**: `student_applicant` -> `Student Applicant`, immutable once set

### Review and Upload Contract

- Review states:
  - `Pending`
  - `Needs Follow-Up`
  - `Cleared`
- Admissions portal APIs in `ifitwala_ed/api/admissions_portal.py`:
  - `get_applicant_health`
  - `update_applicant_health`
  - `upload_applicant_health_vaccination_proof`
- SPA page: `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantHealth.vue`
- Governed vaccination-proof upload delegate: `ifitwala_ed.admission.admissions_portal.upload_applicant_health_vaccination_proof` -> `ifitwala_drive.api.admissions.upload_applicant_health_vaccination_proof`
- Declaration-complete transition (`applicant_health_declared_complete: 0 -> 1`) materializes reviewer assignments.
- Reviewer metadata is stamped when moving to review outcomes.
- Promotion handoff is consumed by `Student Applicant.promote_to_student`.
- Family workspace access is resolved through `Admissions Family` plus explicit applicant guardian linkage.
