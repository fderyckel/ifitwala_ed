---
title: "Assessment Scheme: Term Reporting Calculation Policy"
slug: assessment-scheme
category: Assessment
doc_order: 2
version: "1.0.1"
last_change_date: "2026-04-25"
summary: "Define how a school, program, or course counts assessment evidence when producing term results."
seo_title: "Assessment Scheme: Term Reporting Calculation Policy"
seo_description: "Define weighted categories, total points, task weights, criteria-based reporting, or manual-final assessment policies for term reports."
---

## Assessment Scheme: Term Reporting Calculation Policy

## Before You Start (Prerequisites)

- Define stable `Assessment Category` records first if the scheme uses category weighting.
- Create the `Grade Scale` that should convert numeric scores into report symbols.
- Decide the simplest calculation method educators and families can understand before adding weights.
- Prefer one visible method per school/program/course scope; use task weights only when teachers can explain why some tasks count more.

`Assessment Scheme` is the policy layer between day-to-day assessment evidence and official term reporting. It lets a school keep calculation rules explicit without putting formula logic on individual tasks.

## Where It Is Used Across the ERP

- [**Reporting Cycle**](/docs/en/reporting-cycle/) can select a default scheme and snapshots resolved scheme definitions during recalculation.
- [**Task Delivery**](/docs/en/task-delivery/) supplies `assessment_category` and optional `reporting_weight` evidence data that scheme methods may use. The staff task overlay reads the resolved scheme before showing category or weight controls.
- [**Course Term Result**](/docs/en/course-term-result/) stores the final result and component breakdown produced from the scheme.

## Lifecycle and Linked Documents

1. Create the scheme for the relevant school scope.
2. Choose one calculation method: weighted categories, total points, weighted tasks, category/task hybrid, criteria-based, or manual final.
3. Add category rows only when the calculation method needs category policy.
4. Mark the scheme `Active` when it is ready for reporting.
5. Run Reporting Cycle recalculation to snapshot and apply the resolved scheme.

## Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Instructor` | Yes | No | No | No |
| `Academic Staff` | Yes | No | No | No |

## Related Docs

<RelatedDocs
  slugs="assessment-category,reporting-cycle,course-term-result,task-delivery,grade-scale"
  title="Related Docs"
/>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/assessment_scheme/assessment_scheme.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/assessment_scheme/assessment_scheme.py`
- **Child table**: `Assessment Scheme Category`
- **Required fields (`reqd=1`)**:
  - `scheme_name`
  - `school`
  - `calculation_method`
- **Calculation methods**:
  - `Weighted Categories`
  - `Total Points`
  - `Weighted Tasks`
  - `Category + Task Weight Hybrid`
  - `Criteria-Based`
  - `Manual Final`
- **Validation rules**:
  - duplicate category rows are blocked
  - category weights cannot be negative
  - category-based final-grade weights must total 100%
  - only one active scheme may exist for the same exact scope
- **Runtime resolver**:
  - `assessment/term_reporting.py` resolves the most specific active scheme by school/year/program/course, with the Reporting Cycle scheme as the default/tie-breaker
  - `api/task.py::get_assessment_setup_for_delivery()` exposes the resolved scheme controls to task setup without duplicating scheme logic in the SPA
  - child table controllers stay empty; validation belongs to the parent `Assessment Scheme`
- **Desk client script**:
  - hides category rows when the selected method does not use category policy
  - shows an active-final category weight total for category-based methods so setup drift is visible before save
