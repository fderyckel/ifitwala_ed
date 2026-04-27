---
title: "Applicant Review Rule: Reviewer Scope Configuration"
slug: applicant-review-rule
category: Admission
doc_order: 8
version: "1.3.1"
last_change_date: "2026-04-27"
summary: "Configure admissions reviewers by organization, school, optional program offering, and target type, including per-file document item review."
seo_title: "Applicant Review Rule: Reviewer Scope Configuration"
seo_description: "Configure admissions reviewers by organization, school, optional program offering, and target type, including per-file document item review."
---

## Contract

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.json`, `ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.py`, `ifitwala_ed/admission/applicant_review_workflow.py`
Test refs: `ifitwala_ed/admission/test_applicant_review_workflow.py`, `ifitwala_ed/api/test_focus_applicant_review.py`

`Applicant Review Rule` defines who must review admissions artifacts for a given institutional scope.

It is configuration, not a task queue. Tasks are materialized later into `Applicant Review Assignment`.

## Permission Matrix

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.py`, `ifitwala_ed/hooks.py`
Test refs: `ifitwala_ed/admission/doctype/applicant_review_rule/test_applicant_review_rule.py`

- `Admission Manager`, `Academic Admin`, and `System Manager` can create and manage rules in their authorized organization/school scope.
- `Admission Officer` can read and report on rules in their authorized organization/school scope.
- System-level users keep the normal administrative bypass.
- Desk list and report views use the same scoped permission hook; sibling school rules are not visible.

## Target Types and Scope

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.json`, `ifitwala_ed/admission/applicant_review_workflow.py`
Test refs: `ifitwala_ed/admission/test_applicant_review_workflow.py`

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

## Reviewer Rows

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_review_rule_reviewer/applicant_review_rule_reviewer.json`, `ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.py`
Test refs: `ifitwala_ed/admission/test_applicant_review_workflow.py`

Reviewer rows live in child table `Applicant Review Rule Reviewer`.

Supported reviewer modes:

- `Role Only`
- `Specific User`

Row invariants:

- `Role Only` requires `reviewer_role` and must keep `reviewer_user` empty
- `Specific User` requires `reviewer_user`
- duplicate effective reviewer actors are rejected

## Rule Resolution and Materialization

Status: Implemented
Code refs: `ifitwala_ed/admission/applicant_review_workflow.py`
Test refs: `ifitwala_ed/admission/test_applicant_review_workflow.py`, `ifitwala_ed/api/test_focus_applicant_review.py`

When assignments are materialized:

1. only active rules in applicant organization/school ancestor scope are considered
2. nearest organization + nearest school + program specificity wins
3. all rules at the same best scope are merged
4. reviewer actors are deduped
5. no matching rule means no assignment is created

Materialization supports submission-level evidence review only. Parent `Applicant Document` rows are aggregate requirement cards and never receive review assignments.

## Focus Integration

Status: Implemented
Code refs: `ifitwala_ed/api/focus_listing.py`, `ifitwala_ed/api/focus_context.py`, `ifitwala_ed/api/focus_actions_applicant_review.py`
Test refs: `ifitwala_ed/api/test_focus_applicant_review.py`

Role-queue behavior:

- open role assignments can be claimed by a reviewer with the required role
- open role assignments can be reassigned to another enabled user with the same role
- once completed, the assignment leaves the open Focus queue

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.json`, `ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.py`, `ifitwala_ed/admission/applicant_review_workflow.py`
Test refs: `ifitwala_ed/admission/test_applicant_review_workflow.py`, `ifitwala_ed/api/test_focus_applicant_review.py`

- `target_type` schema includes `Applicant Document Item`, `Applicant Health Profile`, and `Student Applicant`.
- `document_type` filtering applies only to `Applicant Document Item` evidence rules.
- Rule matching and assignment creation live in `applicant_review_workflow.py`; the rule doctype controller mainly validates configuration coherence.
