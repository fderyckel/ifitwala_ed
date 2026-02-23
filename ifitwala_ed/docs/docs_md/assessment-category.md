---
title: "Assessment Category: Classifying Learning Work Clearly"
slug: assessment-category
category: Assessment
doc_order: 1
summary: "Define meaningful assessment buckets (Formative, Summative, Project, etc.) so teaching teams, analytics, and reporting speak the same language."
seo_title: "Assessment Category: Classifying Learning Work Clearly"
seo_description: "Define meaningful assessment buckets (Formative, Summative, Project, etc.) so teaching teams, analytics, and reporting speak the same language."
---

## Assessment Category: Classifying Learning Work Clearly

## Before You Start (Prerequisites)

- Agree the institution-wide assessment taxonomy (for example formative/summative/project) first.
- Create categories before configuring `Course`, `Program`, and `Task` records that reference them.
- Keep naming stable once categories are in active reporting use.

Not every piece of student work should be treated the same. `Assessment Category` gives schools a shared vocabulary for classwork, projects, summatives, and other evidence types so decisions stay consistent across teams.

<Callout type="tip" title="Why this matters">
When categories are clean, your curriculum team can compare like-for-like evidence instead of mixing everything into one noisy score stream.
</Callout>

## Where It Is Used Across the ERP

- [**Course**](/docs/en/course/) via `Course Assessment Category` child rows.
- [**Program**](/docs/en/program/) via `Program Assessment Category` child rows.
- [**Task**](/docs/en/task/) classification and downstream gradebook filtering logic.
- Desk Workspaces:
  - `Curriculum` workspace shortcut (`ifitwala_ed/curriculum/workspace/curriculum/curriculum.json`)
  - `Admin` workspace shortcut (`ifitwala_ed/school_settings/workspace/admin/admin.json`)

## Lifecycle and Linked Documents

1. Define categories first as shared language for assessment design.
2. Attach categories in curriculum setup (`Course` and `Program`) before task rollout.
3. Classify each `Task` using the same vocabulary to keep gradebook and analytics comparable.
4. Review category usage periodically to avoid overlap and duplicate semantics.

<Callout type="info" title="Governance tip">
Treat category names as policy vocabulary, not teacher-specific labels, so reporting remains consistent across years.
</Callout>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/assessment_category/assessment_category.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/assessment_category/assessment_category.py`
- **Required fields (`reqd=1`)**:
  - `category_name` (`Data`)
- **Lifecycle hooks in controller**: none (reference/master behavior, or handled by framework defaults).
- **Operational/public methods**: none beyond standard document behavior.

- **DocType**: `Assessment Category` (`ifitwala_ed/assessment/doctype/assessment_category/`)
- **Autoname**: `field:category_name`
- **Controller**: thin (`pass`) by design; used as a governed master table.
- **Desk UI**:
  - no custom client script behavior beyond default form/list
  - maintained as a reference dataset for curriculum and assessment records
- **Linked child-table ecosystem**:
  - `Course Assessment Category`
  - `Program Assessment Category`
- **Architecture guarantees (embedded from assessment doctrine)**:
  - categories are semantic classification only
  - categories do not compute grades, weights, or numeric outcomes
  - category flags (for example summative/include-in-final) express policy intent, not calculation logic

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Staff` | Yes | No | No | No |
| `Instructor` | Yes | No | No | No |
| `Accreditation Visitor` | Yes | No | No | No |

## Related Docs

- [**Assessment Criteria**](/docs/en/assessment-criteria/) - defines what is measured
- [**Grade Scale**](/docs/en/grade-scale/) - defines how scores become grades
- [**Task**](/docs/en/task/) - where categories are applied in teaching workflows
