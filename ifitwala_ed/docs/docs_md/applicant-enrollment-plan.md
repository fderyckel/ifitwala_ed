---
title: "Applicant Enrollment Plan: Admissions to Enrollment Bridge"
slug: applicant-enrollment-plan
category: Admission
doc_order: 5
version: "1.2.2"
last_change_date: "2026-05-20"
summary: "Stage placement, offer, deposit terms, family response, and pre-request basket choices before student promotion, then hydrate the real Program Enrollment Request without duplicating admissions truth."
seo_title: "Applicant Enrollment Plan: Admissions to Enrollment Bridge"
seo_description: "Use Applicant Enrollment Plan to manage committee-ready placement, offer deposits, applicant basket choices, and real Program Enrollment Request hydration after promotion."
---

## Applicant Enrollment Plan: Admissions to Enrollment Bridge

`Applicant Enrollment Plan` is the pre-student bridge between `Student Applicant` and the real [**Program Enrollment Request**](/docs/en/program-enrollment-request/).

It lets admissions and academic staff agree the offered placement, send a family-facing offer in `/admissions`, capture pre-request course intent, and carry accepted intent forward into enrollment without retyping the same academic-year and offering data.

<Callout type="warning" title="Boundary rule">
This is not the real enrollment transaction. The committed enrollment path still remains `Student -> Program Enrollment Request -> Program Enrollment`.
</Callout>

## Before You Start (Prerequisites)

- Create the source [**Student Applicant**](/docs/en/student-applicant/) first.
- Create target [**Program Offering**](/docs/en/program-offering/) and its offering courses.
- Ensure the applicant is already at internal admissions status `Approved` before staff move the plan into committee-approved and offer states.
- Decide whether [**Admission Settings**](/docs/en/admission-settings/) should auto-hydrate the post-promotion request.

## What This Record Owns

- applicant-linked placement planning
- intended `academic_year`
- intended `term` when used
- intended `program`
- intended `program_offering`
- optional planned course basket
- course-row snapshots for `required`, `applied_basket_group`, and `choice_rank`
- committee notes
- offer status, timestamps, expiry, and message
- admissions deposit terms, deposit invoice link, and deposit override approval state
- hydration provenance to the resulting `Program Enrollment Request`

## What It Does Not Own

- the canonical admissions lifecycle status
- committed enrollment truth
- enrollment validation snapshots
- enrollment-request override approvals
- direct `Program Enrollment` creation

## Lifecycle States

| Status | Runtime meaning |
|---|---|
| `Draft` | Staff is preparing the placement plan |
| `Ready for Committee` | Plan is ready for committee review |
| `Committee Approved` | Placement and offer package approved internally |
| `Offer Sent` | Family-facing offer is open in the admissions portal |
| `Offer Accepted` | Applicant user accepted the offer in portal |
| `Offer Declined` | Applicant user declined the offer in portal |
| `Offer Expired` | Staff closed the offer after expiry |
| `Hydrated` | Real `Program Enrollment Request` has been created |
| `Cancelled` | Plan was intentionally closed |
| `Superseded` | A newer plan replaced this one |

## Operational Flow

1. Staff opens `Manage Enrollment Plan` from the `Student Applicant` Desk form.
2. Staff completes year, offering, and optional course intent.
3. Planned course rows sync `required` from the offering.
4. Optional rows may carry `applied_basket_group` and `choice_rank`.
5. Staff marks the plan ready for committee, records committee approval, and sends the offer.
6. If the offering includes optional basket choices, the applicant user completes them inside `/admissions/course-choices`.
7. The applicant user responds to the offer inside `/admissions/status`.
8. If the accepted offer requires a deposit, staff generate the draft deposit invoice and finance records payment in accounting.
9. Promotion to `Student` is allowed only when the latest plan is `Offer Accepted` or already `Hydrated`; if deposit-before-promotion is enabled, the required deposit must also be paid.
10. After promotion, the system can auto-hydrate or staff can manually hydrate the real [**Program Enrollment Request**](/docs/en/program-enrollment-request/).

## Hydration Rules

- Hydration is server-owned.
- Hydration is idempotent: if the plan already points to a live request, the same request is returned.
- The request is created only after `Student` exists.
- Course seeding order is:
  1. explicit AEP planned courses
  2. required `Program Offering Course` rows missing from the explicit plan
- The generated request stays `Draft`; validation and approval still happen on the real request.

## Portal Behavior

- Offer acceptance and decline happen only in the authenticated admissions portal.
- The portal status page shows the latest offer package from the applicant's latest plan.
- If the offering exposes optional basket choices, the portal shows them on `/admissions/course-choices` using `Basket Group` semantics from the selected `Program Offering`.
- Required offering courses stay visible as locked reference rows; only optional selections and required multi-group basket resolution are editable by the applicant.
- Offer acceptance is server-gated until required basket selections are complete.
- Repeated accept or decline clicks are safe; the server returns the already-recorded outcome instead of creating duplicate state.
- If a selected course belongs to more than one basket group, the accepted-plan course row must keep an explicit `applied_basket_group` before hydration can complete.
- When a deposit invoice exists, `/admissions/status` may show the deposit summary read-only. The portal does not collect payment or submit invoices.

## Deposit Rules

- Deposit defaults are configured in [**Admission Settings**](/docs/en/admission-settings/) by organization and optional school.
- A default deposit on an accepted plan can generate one draft `Sales Invoice` for finance review.
- Manual changes to deposit terms become a `Manual Override` and require both academic and finance approval before invoice generation.
- The draft invoice bridge is idempotent: if a deposit invoice already exists, the existing invoice is returned.
- When `require_deposit_before_promotion` is enabled, promotion is blocked until the required deposit is paid.
- This bridge is not a checkout or payment-plan engine; accounting still owns invoice submission and payment recording.

## Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Admission Manager` | Yes | Yes | Yes | Yes |
| `Admission Officer` | Yes | Yes | Yes | No |
| `Academic Admin` | Yes | Yes | Yes | No |
| `Curriculum Coordinator` | Yes | Yes | Yes | No |
| `Academic Staff` | Yes | No | No | No |

## Related Docs

<RelatedDocs
  slugs="student-applicant,program-offering,basket-group,program-enrollment-request,admission-settings,student-enrollment-playbook"
  title="Related Admissions and Enrollment Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-20)

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
  - `update_portal_choices`
  - `approve_deposit_academic_override`
  - `approve_deposit_finance_override`
  - `reject_deposit_override`
  - `generate_deposit_invoice`
  - module whitelisted: `get_or_create_applicant_enrollment_plan`
  - module whitelisted: `hydrate_program_enrollment_request_from_applicant_plan`
  - module helper: `get_applicant_enrollment_choice_state`
  - module helper: `generate_deposit_invoice_from_offer`

- **DocType**: `Applicant Enrollment Plan` (`ifitwala_ed/admission/doctype/applicant_enrollment_plan/`)
- **Autoname**: `format:AEP-{YYYY}-{####}`
- **Planned course snapshot fields**:
  - `required`
  - `applied_basket_group`
  - `choice_rank`
- **Controller guarantees**:
  - sync `organization`, `school`, and promoted `student` from the linked applicant
  - enforce one active non-terminal plan per applicant
  - require `academic_year` + `program_offering` before review, offer, accepted, and hydrated states
  - require applicant `Approved` before committee-approved, offer, accepted, and hydrated states
  - normalize duplicate planned courses away
  - sync `required` from offering semantics
  - block invalid basket-group choices
  - single-group optional rows auto-fill `applied_basket_group`
  - multi-group optional rows require explicit `applied_basket_group` in `Offer Accepted` and `Hydrated`
  - reject hydration without a student or seedable basket
  - apply school-default deposit terms when available
  - require academic and finance approval before invoicing manual deposit overrides
  - create at most one draft deposit invoice per accepted plan
- **Portal/runtime integration**:
  - latest-plan lookup powers `/admissions/status`
  - latest-plan basket-choice payload powers `/admissions/course-choices`
  - `get_applicant_enrollment_choices` / `update_applicant_enrollment_choices` run through `ifitwala_ed/api/admissions_portal.py`
  - `accept_enrollment_offer` / `decline_enrollment_offer` call plan methods through `ifitwala_ed/api/admissions_portal.py`
  - accepted-offer deposit summary is serialized read-only into `/admissions/status`
  - `StudentApplicant.promote_to_student()` validates latest-plan eligibility and can auto-hydrate via Admission Settings
- **Request provenance written to PER**:
  - `source_student_applicant`
  - `source_applicant_enrollment_plan`
