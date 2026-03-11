---
title: "Basket Group: Enrollment Basket Requirement Vocabulary"
slug: basket-group
category: Enrollment
doc_order: 2
version: "1.1.0"
last_change_date: "2026-03-11"
summary: "Define named basket requirement groups used by Program, Program Offering, Applicant Enrollment Plan, Program Enrollment Request, and Program Enrollment."
seo_title: "Basket Group: Enrollment Basket Requirement Vocabulary"
seo_description: "Define named basket requirement groups used across program planning, offering setup, applicant choices, and enrollment transactions."
---

## Basket Group: Enrollment Basket Requirement Vocabulary

`Basket Group` is the canonical master for enrollment basket semantics.

It is not course taxonomy. Course taxonomy stays on `Course.course_group`. `Basket Group` is used only for requirement families, choice families, and resolved basket assignments.

In staff forms, basket-related fields are labeled `Basket Group (Enrollment)`, and the program/offering mapping tables appear as `Enrollment Basket Memberships`.

## Before You Start (Prerequisites)

- Decide the basket vocabulary your school uses, for example `Group 3 Humanities`, `Group 4 Sciences`, or `Arts Elective Pool`.
- Create linked [**Program**](/docs/en/program/) and [**Program Offering**](/docs/en/program-offering/) records after the master groups exist if you want operators to pick from a clean list.

## Why It Matters

- Separates basket and choice semantics from course taxonomy.
- Supports one course belonging to zero, one, or many basket groups.
- Gives requests and enrollments a stable vocabulary for `applied_basket_group` and `credited_basket_group`.

## Where It Is Used Across the ERP

- `Program.course_basket_groups`
- `Program Offering.offering_course_basket_groups`
- `Program Offering Enrollment Rule.basket_group`
- `Applicant Enrollment Plan Course.applied_basket_group`
- `Program Enrollment Request Course.applied_basket_group`
- `Program Enrollment Course.credited_basket_group`

## Worked Examples

### Example 1: IB ESS

- Basket groups:
  - `Group 3 Humanities`
  - `Group 4 Sciences`
- Course memberships:
  - `ESS -> Group 3 Humanities`
  - `ESS -> Group 4 Sciences`

Result: the same course may appear in more than one requirement family, but request and enrollment rows still store which group it actually counted against.

## Related Docs

- [**Program**](/docs/en/program/)
- [**Program Offering**](/docs/en/program-offering/)
- [**Program Enrollment Request**](/docs/en/program-enrollment-request/)
- [**Program Enrollment**](/docs/en/program-enrollment/)
- [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/)

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/basket_group/basket_group.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/basket_group/basket_group.py`
- **Required fields (`reqd=1`)**:
  - `basket_group_name` (`Data`)
- **Lifecycle hooks in controller**: none
- **Operational/public methods**: none

- **DocType**: `Basket Group` (`ifitwala_ed/schedule/doctype/basket_group/`)
- **Autoname**: `field:basket_group_name`
- **Supporting child tables**:
  - `Program Course Basket Group`
  - `Program Offering Course Basket Group`

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Assistant` | Yes | No | No | No |
| `Schedule Maker` | Yes | No | No | No |
| `Instructor` | Yes | No | No | No |
