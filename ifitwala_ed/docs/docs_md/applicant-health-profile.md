---
title: "Applicant Health Profile: Health Disclosure and Clearance"
slug: applicant-health-profile
category: Admission
doc_order: 7
summary: "Capture health details, control family/staff editing by applicant status, and feed readiness for admissions decisions."
seo_title: "Applicant Health Profile: Health Disclosure and Clearance"
seo_description: "Capture health details, control family/staff editing by applicant status, and feed readiness for admissions decisions."
---

## Applicant Health Profile: Health Disclosure and Clearance

## Before You Start (Prerequisites)

- Create the `Student Applicant` record first.
- Decide your internal review process (`Pending`, `Needs Follow-Up`, `Cleared`) before staff start updating rows.
- If family-side editing is used, ensure applicant portal access/linkage is already set up.

`Applicant Health Profile` stores health and safeguarding information needed during admissions review.

## What It Captures

- Health summary
- Medical conditions
- Allergies
- Medications
- Staff review status and notes

## Where It Is Used Across the ERP

- [**Student Applicant**](/docs/en/student-applicant/): readiness checks require a cleared health review.
- Admissions portal APIs:
  - `get_applicant_health`
  - `update_applicant_health`
- Staff review UI: reviewer metadata stamped when moving to review outcomes.
- Admission workspace card: direct operational access.

## Review States

- `Pending`
- `Needs Follow-Up`
- `Cleared`

<Callout type="tip" title="Practical workflow">
Families can provide health details in portal phases where edits are allowed, then staff can move review status to `Cleared` or `Needs Follow-Up`.
</Callout>

## Lifecycle and Linked Documents

1. Create health profile context as soon as an applicant enters active review.
2. Capture family-provided health details and keep entries current through the review window.
3. Staff reviewers move the profile through review outcomes (`Pending`, `Needs Follow-Up`, `Cleared`).
4. Applicant approval readiness depends on the health review state being complete.

<Callout type="warning" title="Admissions decision impact">
Do not move applicants to final approval while health review remains unresolved; readiness checks are designed to prevent this.
</Callout>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/admission/doctype/applicant_health_profile/applicant_health_profile.json`
- **Controller file**: `ifitwala_ed/admission/doctype/applicant_health_profile/applicant_health_profile.py`
- **Required fields (`reqd=1`)**:
  - `student_applicant` (`Link` -> `Student Applicant`)
- **Lifecycle hooks in controller**: `validate`
- **Operational/public methods**: none beyond standard document behavior.

- **DocType**: `Applicant Health Profile` (`ifitwala_ed/admission/doctype/applicant_health_profile/`)
- **Autoname**: `hash`
- **Primary link**: `student_applicant` -> `Student Applicant` (immutable once set)
- **Portal/API surfaces**:
  - endpoints in `ifitwala_ed/api/admissions_portal.py`:
    - `get_applicant_health`
    - `update_applicant_health`
  - SPA page consuming these APIs: `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantHealth.vue`
- **Controller methods**:
  - permission gating by role and applicant status
  - reviewer metadata stamping (`reviewed_by`, `reviewed_on`)

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Staff review role |
| `Admission Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Officer` | Yes | Yes | Yes | Yes | Full Desk access |
| `Guardian` | Yes | Yes | Yes | No | Family-facing write allowed by DocType permissions |

Runtime controller rules:
- Family/applicant editing is allowed only for applicant statuses: `Invited`, `In Progress`, `Missing Info`.
- Review fields are staff-only.
- Terminal applicant states (`Rejected`, `Promoted`) are read-only.

## Reporting

- No dedicated Script/Query Report currently declares this doctype as `ref_doctype`.

## Related Docs

- [**Student Applicant**](/docs/en/student-applicant/) - readiness and decision lifecycle
- [**Applicant Interview**](/docs/en/applicant-interview/) - additional review evidence
- [**Applicant Document**](/docs/en/applicant-document/) - required file evidence
