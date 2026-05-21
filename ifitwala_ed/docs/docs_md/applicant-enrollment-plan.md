---
title: "Applicant Enrollment Plan: Admissions to Enrollment Bridge"
slug: applicant-enrollment-plan
category: Admission
doc_order: 5
version: "1.3.0"
last_change_date: "2026-05-21"
summary: "Plan placement, offer, deposit terms, family response, and pre-request course choices before promotion, then hydrate the real Program Enrollment Request."
seo_title: "Applicant Enrollment Plan: Admissions to Enrollment Bridge"
seo_description: "Use Applicant Enrollment Plan to manage committee-ready placement, offer deposits, applicant basket choices, and real Program Enrollment Request hydration after promotion."
---

## What Is an Applicant Enrollment Plan?

`Applicant Enrollment Plan` is the bridge between an approved [**Student Applicant**](/docs/en/student-applicant/) and the real [**Program Enrollment Request**](/docs/en/program-enrollment-request/).

It lets admissions and academic staff agree on the offered placement, send a family-facing offer in `/admissions`, collect pre-request course intent, manage deposit terms, and carry accepted intent forward after promotion without retyping the same academic-year and offering data.

<Callout type="warning" title="Boundary rule">
This is not the committed enrollment transaction. The committed path remains `Student -> Program Enrollment Request -> Program Enrollment`.
</Callout>

## Why This Matters

- **Admissions and academics can agree before enrollment.** The plan captures intended year, program, offering, and course choices while the person is still an applicant.
- **Families can respond to offers in the portal.** Offer acceptance and decline happen in `/admissions`.
- **Optional course choices are captured early.** Basket choices can be collected before the real enrollment request exists.
- **Deposits stay connected to the offer.** Deposit defaults, manual overrides, invoice links, and paid-state checks live with the accepted plan.
- **Enrollment request creation stays clean.** Hydration creates the real Program Enrollment Request only after the Student exists.

## Before You Create or Use a Plan

You should have:

- the source [**Student Applicant**](/docs/en/student-applicant/)
- target [**Program Offering**](/docs/en/program-offering/) and offering courses
- applicant status `Approved` before committee-approved, offer, accepted, and hydrated states
- [**Admission Settings**](/docs/en/admission-settings/) configured if the school auto-hydrates requests or requires deposit before promotion
- finance agreement before generating deposit invoices or approving manual deposit overrides

## Information You Manage

| Area | What it controls | Why it matters |
|---|---|---|
| Applicant link | The Student Applicant this plan belongs to | Keeps placement planning tied to the admissions record |
| Academic year and term | Intended enrollment period | Seeds the future request |
| Program and offering | Intended program placement | Connects admissions offer to real offering structure |
| Planned courses | Required and optional course intent | Carries course choices into the future request |
| Basket group and rank | Optional selection semantics | Protects choice rules when offerings include baskets |
| Committee status | Internal review and approval of the offer package | Separates staff approval from family response |
| Offer status | Sent, accepted, declined, expired, hydrated, or closed | Shows where the family-facing offer stands |
| Deposit terms | Required deposit, amount, due date, invoice, and override state | Aligns admissions offer with finance policy |
| Hydration link | Resulting Program Enrollment Request | Provides traceability into enrollment |

## How This Fits the Admissions Workflow

<Steps title="Applicant Enrollment Plan flow">
  <Step title="Prepare placement">
    Staff open Manage Enrollment Plan from Student Applicant and complete year, offering, and optional course intent.
  </Step>
  <Step title="Review internally">
    Staff mark the plan ready for committee, record committee approval, and prepare the offer package.
  </Step>
  <Step title="Send offer">
    The family sees the latest offer package in `/admissions/status`.
  </Step>
  <Step title="Collect choices">
    If the offering has optional basket choices, the applicant completes them in `/admissions/course-choices`.
  </Step>
  <Step title="Resolve deposit">
    Staff generate a draft deposit invoice when terms are ready; finance owns invoice submission and payment recording.
  </Step>
  <Step title="Hydrate after promotion">
    Once the applicant is promoted to Student, the accepted plan can hydrate a draft Program Enrollment Request.
  </Step>
</Steps>

## Permission Matrix

Applicant Enrollment Plan is shared by admissions and academic planning roles. Read-only academic staff can see plans but do not edit them.

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full control |
| `Admission Manager` | Yes | Yes | Yes | Yes | Admissions offer owner |
| `Admission Officer` | Yes | Yes | Yes | No | Admissions operator |
| `Academic Admin` | Yes | Yes | Yes | No | Academic planning owner |
| `Curriculum Coordinator` | Yes | Yes | Yes | No | Course/offering planning support |
| `Academic Staff` | Yes | No | No | No | Read-only |

## Practical Examples

### Accepted applicant with a simple placement

The applicant is approved for Grade 6 in a specific Program Offering. Staff prepare the plan, approve it internally, send the offer, and the family accepts. After promotion, the plan can hydrate the Program Enrollment Request.

### Optional course choices

The offering includes elective baskets. The plan shows required courses as locked reference rows and lets the applicant choose eligible optional courses in the portal before hydration.

### Deposit before promotion

The accepted offer requires a deposit. Staff generate the draft invoice, finance records payment, and promotion is allowed only after the required deposit is paid when Admission Settings enforce that policy.

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use the latest active plan as the offer source for the applicant.</Do>
  <Do>Confirm academic year and program offering before committee approval.</Do>
  <Do>Let families complete required basket choices before accepting the offer.</Do>
  <Do>Coordinate deposit overrides with both academic and finance approval.</Do>
  <Dont>Treat Applicant Enrollment Plan as the committed enrollment record.</Dont>
  <Dont>Create Program Enrollment directly from admissions.</Dont>
  <Dont>Use deposit settings as a checkout or payment-plan engine.</Dont>
</DoDont>

## Common Questions

### Is this the real enrollment request?

No. It is the applicant-stage bridge. The real request is Program Enrollment Request and is created only after the Student exists.

### Can hydration run twice?

Hydration is idempotent. If the plan already points to a live request, the same request is returned.

### Can the portal collect payment?

No. The portal may show deposit summary read-only. Accounting owns invoice submission and payment recording.

### Who owns offer acceptance?

Applicant Enrollment Plan owns the family-facing offer states: `Offer Sent`, `Offer Accepted`, and `Offer Declined`.

## Related Docs

<RelatedDocs
  slugs="student-applicant,admission-cockpit,program-offering,basket-group,program-enrollment-request,admission-settings,student-enrollment-playbook"
  title="Continue With Related Admissions and Enrollment Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-21)

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

### Lifecycle States

| Status | Runtime meaning |
|---|---|
| `Draft` | Staff is preparing the placement plan |
| `Ready for Committee` | Plan is ready for committee review |
| `Committee Approved` | Placement and offer package approved internally |
| `Offer Sent` | Family-facing offer is open in the admissions portal |
| `Offer Accepted` | Applicant user accepted the offer in portal |
| `Offer Declined` | Applicant user declined the offer in portal |
| `Offer Expired` | Staff closed the offer after expiry |
| `Hydrated` | Real Program Enrollment Request has been created |
| `Cancelled` | Plan was intentionally closed |
| `Superseded` | A newer plan replaced this one |

### Controller Guarantees

- **DocType**: `Applicant Enrollment Plan` (`ifitwala_ed/admission/doctype/applicant_enrollment_plan/`)
- **Autoname**: `format:AEP-{YYYY}-{####}`
- Planned course snapshot fields:
  - `required`
  - `applied_basket_group`
  - `choice_rank`
- Controller guarantees:
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

### Hydration Rules

- Hydration is server-owned.
- Hydration is idempotent.
- The request is created only after `Student` exists.
- Course seeding order:
  1. explicit AEP planned courses
  2. required `Program Offering Course` rows missing from the explicit plan
- The generated request stays `Draft`; validation and approval still happen on the real request.

### Portal and Deposit Runtime

- Latest-plan lookup powers `/admissions/status`.
- Latest-plan basket-choice payload powers `/admissions/course-choices`.
- `get_applicant_enrollment_choices` / `update_applicant_enrollment_choices` run through `ifitwala_ed/api/admissions_portal.py`.
- `accept_enrollment_offer` / `decline_enrollment_offer` call plan methods through `ifitwala_ed/api/admissions_portal.py`.
- Accepted-offer deposit summary is serialized read-only into `/admissions/status`.
- Deposit defaults are configured in Admission Settings by organization and optional school.
- Manual deposit term changes become `Manual Override` and require academic and finance approval before invoice generation.
- Draft invoice bridge is idempotent.
- When `require_deposit_before_promotion` is enabled, promotion is blocked until the required deposit is paid.

### Request Provenance Written to PER

- `source_student_applicant`
- `source_applicant_enrollment_plan`
