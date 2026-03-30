---
title: "Course: Catalog Unit for Program and Enrollment Design"
slug: course
category: Curriculum
doc_order: 2
version: "1.3.0"
last_change_date: "2026-03-24"
summary: "Define a reusable catalog course with grade-scale context, assessment categories/criteria, status, and the website publication handoff used by public course marketing surfaces."
seo_title: "Course: Catalog Unit for Program and Enrollment Design"
seo_description: "Define a reusable catalog course with grade-scale context, assessment categories/criteria, and status used by Program and Program Offering enrollment flows."
---

## Course: Catalog Unit for Program and Enrollment Design

`Course` is the catalog-level learning unit that programs and offerings reference. Enrollment logic validates against course identity plus program/offering policies.

In staff forms, the taxonomy field is labeled `Course Group (Catalog)` to distinguish it from enrollment basket terminology.

Public course marketing now uses a separate website-owned publication layer. `Course` remains academic/catalog truth; public course pages are handled through `Course Website Profile` so website storytelling stays separate from instructional delivery.

## Before You Start (Prerequisites)

- Create supporting masters (`Grade Scale`, `Course Group`, shown in forms as `Course Group (Catalog)`, assessment masters) as needed.
- Confirm how the course should behave in scheduling (`term_long`) and reporting exclusions.
- If the course will participate in weighted criteria grading, prepare criterion rows before activation.

## Why It Matters

- `Program` catalog rows and offering rows point to `Course`.
- Program validation allows only `Course.status = Active` in program catalog.
- Enrollment and tooling use course identity for course-level placement in enrollments.
- `Course Group` remains catalog taxonomy only; enrollment basket semantics live on `Basket Group`.
- Public course marketing remains school-scoped and workflow-published through `Course Website Profile`; `Course` itself does not become the public CMS record.

<Callout type="info" title="Assessment weighting rule">
If `assessment_criteria` rows are used, their `criteria_weighting` total must be exactly 100%.
</Callout>

## Where It Is Used Across the ERP

- [**Program**](/docs/en/program/) -> `Program Course.course`
- [**Program Offering**](/docs/en/program-offering/) -> `Program Offering Course.course`
- [**Program Enrollment**](/docs/en/program-enrollment/) -> `Program Enrollment Course.course`
- [**Task**](/docs/en/task/) -> `default_course`
- planned public website course catalog / course detail contract:
- implemented public website course catalog / course detail contract:
  - `ifitwala_ed/docs/website/08_course_catalog_contract.md`
- Enrollment validation and tooling:
  - request validation course basket
  - course add-to-many enrollment tool

## Lifecycle and Linked Documents

1. Create course identity and school/context links.
   On a new Desk form, `school` now prefills from the current user's default school when available; staff can still change or clear it before save.
2. Configure grade-scale fields (`default_grade_scale`, optional `grade_scale` override).
3. Configure `assessment_categories` and `assessment_criteria` rows.
4. Set lifecycle flags (`status`, `term_long`, publish flags).
5. If `is_published = 1` and `school` is set, the system prepares a draft `Course Website Profile`, SEO defaults, curated highlight seed rows from published `Learning Unit` summaries when available, and the school `courses` index page.
6. Add course into one or more programs via catalog mapping.

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Keep `status` accurate (`Active` vs `Discontinued`) because program catalog validation depends on it.</Do>
  <Do>Use `term_long` intentionally so enrollment/course tools can apply proper term defaults.</Do>
  <Dont>Duplicate the same assessment criterion row in one course.</Dont>
  <Dont>Leave weighted criteria totals off 100% when criteria rows are present.</Dont>
</DoDont>

## Worked Examples

### Example 1: Active Course for Enrollment

- `course_name`: `Biology HL`
- `status`: `Active`
- Added to Program catalog and then to Program Offering.
- Students can request/enroll this course through request and tool flows.

### Example 2: Term-Bounded Course

- `term_long = 0`
- During Program Enrollment/Course Enrollment Tool flows, term bounds are defaulted from school AY term boundaries when needed.

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/course/course.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/course/course.py`
- **Required fields (`reqd=1`)**: none at schema level.
- **Lifecycle hooks in controller**: `validate`
- **Lifecycle hooks in controller**: `validate`, `after_insert`, `on_update`
- **Operational/public methods**:
  - `add_course_to_programs(course, programs, mandatory=False)` (whitelisted)
  - `get_programs_without_course(course)` (whitelisted)

- **DocType**: `Course` (`ifitwala_ed/curriculum/doctype/course/`)
- **Autoname**: `field:course_name`
- **Child tables**:
  - `assessment_categories` -> `Course Assessment Category`
  - `assessment_criteria` -> `Course Assessment Criteria`
- **Validation guarantees** (`course.py`):
  - no duplicate criterion links in `assessment_criteria`
  - sum of `criteria_weighting` must equal `100%` (with tolerance)
- **Website publication handoff**:
  - published courses with a `school` prepare `Course Website Profile` defaults through `ifitwala_ed/website/bootstrap.py`
  - public course storytelling, SEO, and workflow state live on `Course Website Profile`
  - public routes are school-scoped: `/schools/{school_slug}/courses` and `/schools/{school_slug}/courses/{course_slug}`

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Academic Assistant` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | No |
| `Academic Staff` | Yes | No | No | No |
| `Instructor` | Yes | No | No | No |
| `Admission Officer` | Yes | No | No | No |
| `Accreditation Visitor` | Yes | No | No | No |

## Related Docs

- [**Program**](/docs/en/program/)
- [**Program Course**](/docs/en/program-course/)
- [**Program Offering Course**](/docs/en/program-offering-course/)
- [**Task**](/docs/en/task/)
