---
title: "Student Insight Note: Living Context for Learner Support"
slug: student-insight-note
category: Students
doc_order: 3
version: "1.0.0"
last_change_date: "2026-05-28"
summary: "Capture time-aware notes about student learning needs, access needs, strengths, interests, achievements, and relationship starters without freezing a child in place."
seo_title: "Student Insight Note: Living Context for Learner Support"
seo_description: "Use Student Insight Notes in Ifitwala Ed to share reviewable, visibility-scoped learner context with teachers and support staff."
---

## What is a Student Insight Note?

A **Student Insight Note** is a short, reviewable note that helps staff understand a student as a learner and person.

Use it for context that may change over time:
- learning support and access needs
- wellbeing context
- strengths and interests
- hobbies, activities, achievements, and relationship starters
- family-provided context carried forward from admissions

Student Insight Notes are intentionally different from permanent Student fields. They can be reviewed, marked active, moved to needs review, or archived when the information is no longer current.

## Where Staff See Notes

Teacher-visible notes appear beside the student name in staff workflows such as attendance and gradebook. Staff can open the note indicator without leaving the current page.

On the Student Desk record, use **View > Student Insight Notes** to open all notes linked to that student.

## Fields Explained

| Field | What It's For | Tips |
|---|---|---|
| **Student** | The learner the note belongs to | Required |
| **Category** | The kind of context | Learning Support, Access, Wellbeing, Strength, Interest, Achievement, or Relationship Starter |
| **Summary** | The actual note | Keep it clear, respectful, and useful for staff action |
| **Source** | Where the information came from | Family, Admissions, Teacher, Counselor, Learning Support, or System |
| **Effective From** | When the note starts being relevant | Defaults to today |
| **Review On** | When staff should check if it is still true | Especially useful for interests, supports, and wellbeing context |
| **Status** | Current lifecycle state | Active, Needs Review, or Archived |
| **Visibility** | Who should see the note in staff context | Choose the narrowest audience that can act on the context |

## Admissions Promotion

When an applicant is promoted to a Student, family-provided profile context can create Student Insight Notes automatically.

Learning support details are visible to Learning Support, wellbeing details to Counselor, and classroom-friendly access, strengths, interests, relationship starters, and achievements to Teachers.

## Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full access |
| `Academic Admin` | Yes* | Yes* | Yes | Yes | School-scoped academic oversight |
| `Academic Assistant` | Yes* | Yes* | Yes | No | School-scoped academic support |
| `Admission Manager` | Yes* | Yes* | Yes | No | Admissions/admin visibility |
| `Admission Officer` | Yes* | Yes* | Yes | No | Admissions/admin visibility |
| `Learning Support` | Yes* | Yes* | Yes | No | Teacher and Learning Support notes in visible student scope |
| `Counselor` | Yes* | Yes* | Yes | No | Teacher and Counselor notes in visible student scope |
| `Academic Staff` | Yes* | Yes* | Yes | No | Teacher-visible notes for students in scope |
| `Instructor` | Yes* | Yes* | Yes | No | Teacher-visible notes for assigned students |
| `Accreditation Visitor` | Yes* | No | No | No | Read-only when scope permits |

*Access is scoped by student visibility and note visibility. Archived notes are not shown in attendance and gradebook indicators.

## Related Docs

<RelatedDocs
  slugs="student,student-applicant,student-log"
  title="Continue With Student Context Docs"
/>

## Technical Notes (IT)

- **DocType**: `Student Insight Note` - Located in Students module
- **Autoname**: `SIN-{YYYY}-{####}` format
- **Status model**: `Active`, `Needs Review`, `Archived`
- **Visibility model**: `Teachers`, `Learning Support`, `Counselor`, `Admissions/Admin`
- **Promotion bridge**: `StudentApplicant.promote_to_student()` calls `create_student_insight_notes_from_applicant(...)`
- **Hot-path reads**: attendance and gradebook use bounded summary payloads from `build_student_insight_summaries(...)`; the SPA does not fetch insight notes per row
