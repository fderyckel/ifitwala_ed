---
title: "Assessment Category: Classifying Learning Work Clearly"
slug: assessment-category
category: Assessment
doc_order: 1
summary: "Define meaningful assessment buckets (Formative, Summative, Project, etc.) so teaching teams, analytics, and reporting speak the same language."
---

# Assessment Category: Classifying Learning Work Clearly

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

## Technical Notes (IT)

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
