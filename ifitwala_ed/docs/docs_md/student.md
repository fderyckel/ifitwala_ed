---
title: "Student: Canonical Learner Record and Import Rules"
slug: student
category: Students
doc_order: 1
version: "1.0.0"
last_change_date: "2026-03-16"
summary: "Understand when Students are created from admissions versus imported from an existing school, and how to run the Frappe v16 Data Import path safely."
seo_title: "Student: Canonical Learner Record and Import Rules"
seo_description: "Learn the Student creation rules, Data Import setup, import-only bypass flag, and school-scoped onboarding requirements for Frappe v16."
---

## Student: Canonical Learner Record and Import Rules

`Student` is the canonical operational learner record in Ifitwala Ed.

The normal production path is:

`Inquiry -> Student Applicant -> Promotion -> Student`

Direct creation is intentionally restricted so day-to-day operations stay aligned with admissions and enrollment.

<Callout type="warning" title="Canonical path">
In steady state, Students should be created by promoting an approved [**Student Applicant**](/docs/en/student-applicant/). Data Import is an explicit onboarding and migration exception, not the default intake workflow.
</Callout>

## Before You Start (Prerequisites)

- Confirm the target school already exists and you know the exact `School` record to use for `anchor_school`.
- Confirm any linked values used in the sheet already exist, especially `School`, `Student Cohort`, `Student House`, `Language Xtra`, `Country`, and `Account Holder` where applicable.
- Confirm the importing user has Desk access plus `Import` permission on `Student`.
- Prepare clean unique values for `student_email`, `student_id` when used, and the generated `student_full_name` combination.

## How Student Creation Works

There are two supported creation modes in current runtime code:

1. Applicant promotion
2. Explicit import / migration bypass

### 1. Applicant Promotion

This is the canonical path.

- Triggered by `Student Applicant.promote_to_student()`
- Sets `student_applicant`
- Copies applicant profile values into `Student`
- Sets `anchor_school` from the applicant school
- Suppresses Student side effects during the promotion insert itself through `frappe.flags.from_applicant_promotion`

### 2. Data Import / Migration Bypass

This is the exception path used for existing-school onboarding or legacy migration.

- `Student` DocType metadata has `allow_import = 1`
- `Student.before_insert()` checks `frappe.flags.in_import`
- In import context, every inserted row must include `allow_direct_creation = 1`
- Migration and patch contexts are also allowed through `frappe.flags.in_migration` or `frappe.flags.in_patch`

If `allow_direct_creation` is not set to `1` during import, the row is rejected with a validation error.

## Is There a Flag for Existing-School Student Import?

Yes.

The flag is:

- `allow_direct_creation`

Current metadata details:

- field type: `Check`
- default: `0`
- hidden: `1`
- read only: `1`
- purpose: explicit acknowledgement that this row is being created outside the admissions promotion path

This flag is enforced in:

- [student.py](/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/students/doctype/student/student.py)

It exists specifically to support controlled direct creation for import, migration, and audited admin exceptions.

## Frappe v16 Data Import Procedure

This is the verified procedure for the current repo contract.

1. Open `Student` in Desk and use `Menu -> Import`, or open the Frappe Data Import tool and choose `Student`.
2. Select `Insert New Records`.
3. Download the template and include the fields you need for onboarding.
4. Ensure the import file includes `allow_direct_creation` and set it to `1` on every row.
5. Populate the required identity fields:
   - `student_first_name`
   - `student_last_name`
   - `student_email`
6. Populate school-scoped anchors and any verified linked fields:
   - `anchor_school`
   - `cohort` if used
   - `student_house` if used
7. Upload the completed file and run validation before starting import.

What happens on successful import:

- Student records are inserted as direct-creation exceptions
- Student side effects run for imported rows:
  - user creation
  - student patient creation
  - contact linking
  - image/sibling sync on update flows

## Current Permission Setup in This Repo

The Student DocType is import-enabled, but the role matrix matters.

Current `student.json` permissions grant `import` to:

- `Academic Admin`
- `Academic Assistant`

Current `student.json` permissions do **not** grant `import` to:

- `System Manager`

Practical consequence:

- if the importing operator is using an admin account with elevated framework access, they may still be able to run the import
- if you want a non-Administrator sysadmin role to use the Desk import flow consistently, grant `Import` on `Student` in Frappe Role Permissions Manager

Frappe’s permissions model exposes `Import` as a role permission in Role Permissions Manager, and the Data Import tool is the standard UI path for bulk inserts and updates in current Frappe documentation.

## Recommended Import Shape for Existing-School Onboarding

For an existing school migration, treat `Student` import as a school-scoped onboarding sheet, not a global dump.

Recommended minimum columns:

- `student_first_name`
- `student_middle_name`
- `student_last_name`
- `student_preferred_name`
- `student_email`
- `student_date_of_birth`
- `student_gender`
- `student_mobile_number`
- `student_joining_date`
- `student_first_language`
- `student_second_language`
- `student_nationality`
- `student_second_nationality`
- `anchor_school`
- `cohort`
- `student_house`
- `residency_status`
- `enabled`
- `allow_direct_creation`

Recommended values:

- `allow_direct_creation = 1` on every imported row
- `enabled = 1` unless the student should land inactive immediately
- `anchor_school` set explicitly for every row

## Blocking Errors You Should Expect

The import will fail when:

- `allow_direct_creation` is missing or not `1`
- required fields are missing
- unique fields collide (`student_email`, `student_id` when supplied, or derived `student_full_name`)
- linked values do not exist in the target site
- date validation fails, for example birth date after joining date

This is expected. The controller is designed to block silent bad imports.

## Do and Don't

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use Student Applicant promotion for normal admissions-created learners.</Do>
  <Do>Use Data Import only for existing-school onboarding, migration, or other explicit exception flows.</Do>
  <Do>Set `allow_direct_creation = 1` on every imported row.</Do>
  <Do>Keep `anchor_school` explicit on every row to preserve tenant and school scope.</Do>
  <Dont>Assume `System Manager` currently has Student import permission in repo metadata.</Dont>
  <Dont>Use a global mixed-school spreadsheet when importing operational students.</Dont>
  <Dont>Skip link-data preparation and expect import validation to infer missing schools, cohorts, or houses.</Dont>
</DoDont>

## Related Docs

- [**Student Applicant**](/docs/en/student-applicant/)
- [**School**](/docs/en/school/)
- [**Organization**](/docs/en/organization/)
- [**Student Enrollment Playbook**](/docs/en/student-enrollment-playbook/)

## Technical Notes (IT)

### Latest Technical Snapshot (2026-03-16)

- **Primary runtime owners**:
  - `ifitwala_ed/students/doctype/student/student.py`
  - `ifitwala_ed/students/doctype/student/student.json`
  - `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
  - `ifitwala_ed/students/doctype/student/test_student.py`
- **Verified import contract**:
  - DocType metadata enables import with `allow_import = 1`
  - import insert path requires `allow_direct_creation = 1` on each row
  - applicant promotion remains the canonical non-exception creation flow
- **Permission nuance**:
  - repo metadata currently grants Student `import` permission to `Academic Admin` and `Academic Assistant`
  - repo metadata currently does not grant Student `import` permission to `System Manager`
