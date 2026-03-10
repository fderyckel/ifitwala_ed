---
title: "Applicant Enrollment Plan: Admissions to Enrollment Bridge"
slug: applicant-enrollment-plan
category: Admission
doc_order: 5
version: "1.0.0"
last_change_date: "2026-03-10"
summary: "Stage placement, offer, and family response before student promotion, then hydrate the real Program Enrollment Request without duplicating admissions truth."
seo_title: "Applicant Enrollment Plan: Admissions to Enrollment Bridge"
seo_description: "Use Applicant Enrollment Plan to manage committee-ready placement, send offers in the admissions portal, and hydrate a real Program Enrollment Request after promotion."
---

## Applicant Enrollment Plan: Admissions to Enrollment Bridge

`Applicant Enrollment Plan` is the pre-student bridge between `Student Applicant` and the real [**Program Enrollment Request**](/docs/en/program-enrollment-request/).

It lets admissions and academic staff agree the offered placement, send a family-facing offer in `/admissions`, and carry accepted intent forward into enrollment without retyping the same academic-year/offering data.

<Callout type="warning" title="Boundary rule">
This is not the real enrollment transaction. The committed enrollment path still remains `Student -> Program Enrollment Request -> Program Enrollment`.
</Callout>

## Before You Start (Prerequisites)

- Create the source [**Student Applicant**](/docs/en/student-applicant/) first.
- Create target [**Program Offering**](/docs/en/program-offering/) and its offering courses.
- Ensure the applicant is already at internal admissions status `Approved` before staff move the plan into committee-approved / offer states.
- Decide whether [**Admission Settings**](/docs/en/admission-settings/) should auto-hydrate the post-promotion request.

## What This Record Owns

- applicant-linked placement planning
- intended `academic_year`
- intended `term` when used
- intended `program`
- intended `program_offering`
- optional planned course basket
- committee notes
- offer status, timestamps, expiry, and message
- hydration provenance to the resulting `Program Enrollment Request`

## What It Does Not Own

- the canonical admissions lifecycle status
- committed enrollment truth
- enrollment validation snapshots
- override approvals
- direct `Program Enrollment` creation

## Lifecycle States

| Status | Runtime meaning |
|---|---|
| `Draft` | Staff is preparing the placement plan |
| `Ready for Committee` | Plan is ready for committee review |
| `Committee Approved` | Placement/offer package approved internally |
| `Offer Sent` | Family-facing offer is open in the admissions portal |
| `Offer Accepted` | Applicant user accepted the offer in portal |
| `Offer Declined` | Applicant user declined the offer in portal |
| `Offer Expired` | Staff closed the offer after expiry |
| `Hydrated` | Real `Program Enrollment Request` has been created |
| `Cancelled` | Plan was intentionally closed |
| `Superseded` | A newer plan replaced this one |

## Operational Flow

1. Staff opens `Manage Enrollment Plan` from the `Student Applicant` Desk form.
2. Staff completes year/offering/course intent and marks the plan ready for committee.
3. Staff records committee approval and sends the offer.
4. The applicant user responds inside `/admissions/status`.
5. Promotion to `Student` is allowed only when the latest plan is `Offer Accepted` (or already `Hydrated`).
6. After promotion, the system can auto-hydrate or staff can manually hydrate the real [**Program Enrollment Request**](/docs/en/program-enrollment-request/).

## Hydration Rules

- Hydration is server-owned.
- Hydration is idempotent: if the plan already points to a live request, the same request is returned.
- The request is created only after `Student` exists.
- Course seeding order is:
  1. explicit AEP planned courses
  2. required `Program Offering Course` rows
- The generated request stays `Draft`; validation and approval still happen on the real request.

## Portal Behavior

- Offer acceptance and decline happen only in the authenticated admissions portal.
- The portal status page shows the latest offer package from the applicant's latest plan.
- Repeated accept/decline clicks are safe; the server returns the already-recorded outcome instead of creating duplicate state.

## Related Docs

<RelatedDocs
  slugs="student-applicant,program-offering,program-enrollment-request,admission-settings,student-enrollment-playbook"
  title="Related Admissions and Enrollment Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-03-10)

- **DocType schema file**: `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.json`
- **Controller file**: `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`
- **Desk script file**: `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.js`
- **Child table schema**: `ifitwala_ed/admission/doctype/applicant_enrollment_plan_course/applicant_enrollment_plan_course.json`
- **Required fields (`reqd=1`)**:
  - `student_applicant` (`Link` -> `Student Applicant`)
- **Lifecycle hooks in controller**: `validate`
- **Operational/public methods**:
  - `mark_ready_for_committee`
  - `approve_committee`
  - `send_offer`
  - `hydrate_program_enrollment_request`
  - module whitelisted: `get_or_create_applicant_enrollment_plan`
  - module whitelisted: `hydrate_program_enrollment_request_from_applicant_plan`

- **DocType**: `Applicant Enrollment Plan` (`ifitwala_ed/admission/doctype/applicant_enrollment_plan/`)
- **Autoname**: `format:AEP-{YYYY}-{####}`
- **Controller guarantees**:
  - sync `organization`, `school`, and promoted `student` from the linked applicant
  - enforce one active non-terminal plan per applicant
  - require `academic_year` + `program_offering` before review/offer/accepted states
  - require applicant `Approved` before committee-approved / offer / hydrated states
  - normalize duplicate planned courses away
  - reject hydration without a student or seedable basket
- **Portal/runtime integration**:
  - latest-plan lookup powers `/admissions/status`
  - `accept_enrollment_offer` / `decline_enrollment_offer` call plan methods through `ifitwala_ed/api/admissions_portal.py`
  - `StudentApplicant.promote_to_student()` validates latest-plan eligibility and can auto-hydrate via Admission Settings
- **Request provenance written to PER**:
  - `source_student_applicant`
  - `source_applicant_enrollment_plan`

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Admission Manager` | Yes | Yes | Yes | Yes |
| `Admission Officer` | Yes | Yes | Yes | No |
| `Academic Admin` | Yes | Yes | Yes | No |
| `Curriculum Coordinator` | Yes | Yes | Yes | No |
