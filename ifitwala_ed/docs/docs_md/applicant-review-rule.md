---
title: "Applicant Review Rule: Reviewer Scope Configuration"
slug: applicant-review-rule
category: Admission
doc_order: 8
version: "1.4.0"
last_change_date: "2026-05-21"
summary: "Configure which users or roles review applicant documents, health profiles, and overall applications for a given admissions scope."
seo_title: "Applicant Review Rule: Reviewer Scope Configuration"
seo_description: "Use Applicant Review Rule to configure admissions reviewers by organization, school, program offering, target type, and reviewer mode."
---

## What Is an Applicant Review Rule?

`Applicant Review Rule` defines who should review admissions artifacts for a specific organization, school, optional program offering, and target type.

It is configuration, not a task queue. The actual reviewer work items are created later as [**Applicant Review Assignment**](/docs/en/applicant-review-assignment/) records.

## Why This Matters

- **Review work goes to the right people.** Rules can target specific users or role-based queues.
- **Schools stay isolated.** Scope is based on organization, school, and optional program offering.
- **Different evidence can route differently.** Document item, health profile, and overall application review can have different reviewers.
- **Focus queues stay useful.** Rules materialize assignments only when matching review work exists.

## Before You Create Rules

You should have:

- organization and school scope decided
- target type chosen
- reviewer users or roles ready
- document type chosen when the rule targets a specific Applicant Document Item type
- agreement on whether the reviewer should be a specific person or a role queue

## Fields You Control

| Field or area | What it controls | Why it matters |
|---|---|---|
| Organization | Top-level institutional scope | Prevents sibling organization leakage |
| School | School scope for the review rule | Keeps reviewer assignment school-specific |
| Program Offering | Optional narrower scope | Supports specialized review for a particular offering |
| Target Type | Applicant Document Item, Applicant Health Profile, or Student Applicant | Defines what kind of review the rule creates |
| Document Type | Optional filter for document-item rules | Routes only one kind of evidence when needed |
| Reviewer Mode | Role Only or Specific User | Decides whether work goes to a queue or person |
| Reviewer Rows | Users or roles who should review | Materializes assignment actors |
| Active state | Whether the rule participates in assignment creation | Lets schools pause rules without deleting history |

## How This Fits the Admissions Workflow

<Steps title="Applicant Review Rule flow">
  <Step title="Define review scope">
    Choose organization, school, optional program offering, and target type.
  </Step>
  <Step title="Add reviewers">
    Add role-only or specific-user reviewer rows.
  </Step>
  <Step title="Applicant work triggers review">
    Evidence submission, health declaration, or application submission reaches a review point.
  </Step>
  <Step title="Best matching rules resolve">
    The workflow chooses nearest organization/school scope and program specificity.
  </Step>
  <Step title="Assignments appear">
    Matching reviewers receive Applicant Review Assignment work items.
  </Step>
</Steps>

## Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Administrative bypass |
| `Admission Manager` | Yes | Yes | Yes | Yes | Can manage rules in authorized scope |
| `Academic Admin` | Yes | Yes | Yes | Yes | Can manage rules in authorized scope |
| `Admission Officer` | Yes | No | No | No | Can read/report on rules in authorized scope |

Desk list and report views use the same scoped permission hook. Sibling school rules are not visible. Desk list view does not request the Program Offering linked title field, keeping its query shape aligned with report view.

## Practical Examples

### Transcript review by registrar role

Create a document-item rule scoped to the school and transcript document type, with reviewer mode `Role Only` for the registrar-style role.

### Health review by nurse

Create a health-profile rule for the school with a specific nurse user or Nurse role queue.

### Overall application review

Create a Student Applicant rule for admissions leadership so submitted applications generate overall review assignments.

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Keep rules scoped to the smallest real policy boundary.</Do>
  <Do>Use role queues when any qualified reviewer may claim the work.</Do>
  <Do>Use specific users when the review must go to a named person.</Do>
  <Do>Use document type filters only for Applicant Document Item rules.</Do>
  <Dont>Create broad rules that expose sibling school review work.</Dont>
  <Dont>Expect rules themselves to show as reviewer tasks.</Dont>
  <Dont>Assign duplicate effective reviewer actors in one rule.</Dont>
</DoDont>

## Common Questions

### Does a rule create work immediately?

No. It defines who should review. Assignments are materialized later when matching applicant work appears.

### What target types are implemented?

`Applicant Document Item`, `Applicant Health Profile`, and `Student Applicant`.

### Can parent Applicant Document rows be assigned?

No. Parent Applicant Document rows are aggregate requirement cards. Evidence review assignments target Applicant Document Item.

## Related Docs

<RelatedDocs
  slugs="applicant-review-assignment,student-applicant,applicant-document,applicant-health-profile"
  title="Continue With Related Applicant Review Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-21)

Status: Implemented

Code refs:

- `ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.json`
- `ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.py`
- `ifitwala_ed/admission/doctype/applicant_review_rule_reviewer/applicant_review_rule_reviewer.json`
- `ifitwala_ed/admission/applicant_review_workflow.py`
- `ifitwala_ed/api/focus_listing.py`
- `ifitwala_ed/api/focus_context.py`
- `ifitwala_ed/api/focus_actions_applicant_review.py`
- `ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule_list.js`
- `ifitwala_ed/hooks.py`

Test refs:

- `ifitwala_ed/admission/test_applicant_review_workflow.py`
- `ifitwala_ed/api/test_focus_applicant_review.py`
- `ifitwala_ed/admission/doctype/applicant_review_rule/test_applicant_review_rule.py`

### Target Types and Scope

Required scope fields:

- `organization`
- `school`
- `target_type`

Optional scope field:

- `program_offering`

Implemented target types:

- `Applicant Document Item`
- `Applicant Health Profile`
- `Student Applicant`

`document_type` is optional and only valid when `target_type` is `Applicant Document Item`.

### Reviewer Rows

Reviewer rows live in child table `Applicant Review Rule Reviewer`.

Supported reviewer modes:

- `Role Only`
- `Specific User`

Row invariants:

- `Role Only` requires `reviewer_role` and must keep `reviewer_user` empty.
- `Specific User` requires `reviewer_user`.
- Duplicate effective reviewer actors are rejected.

### Rule Resolution and Materialization

When assignments are materialized:

1. Only active rules in applicant organization/school ancestor scope are considered.
2. Nearest organization + nearest school + program specificity wins.
3. All rules at the same best scope are merged.
4. Reviewer actors are deduped.
5. No matching rule means no assignment is created.

Materialization supports submission-level evidence review only. Parent `Applicant Document` rows are aggregate requirement cards and never receive review assignments.

### Focus Integration

- Open role assignments can be claimed by a reviewer with the required role.
- Open role assignments can be reassigned to another enabled user with the same role.
- Once completed, the assignment leaves the open Focus queue.
- Rule matching and assignment creation live in `applicant_review_workflow.py`; the rule controller mainly validates configuration coherence.
