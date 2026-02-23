---
title: "Applicant Review Rule: Reviewer Scope Configuration"
slug: applicant-review-rule
category: Admission
doc_order: 8
version: "1.0.0"
last_change_date: "2026-02-23"
summary: "Configure admissions review assignees by organization, school, optional program offering, and target type."
seo_title: "Applicant Review Rule: Reviewer Scope Configuration"
seo_description: "Configure admissions review assignees by organization, school, optional program offering, and target type."
---

## Applicant Review Rule: Reviewer Scope Configuration

`Applicant Review Rule` defines who must review admissions artifacts for a given institutional scope.

## Scope Model

- `organization` is required.
- `school` is required.
- `program_offering` is optional for program-specific rules.
- `target_type` is required and must be one of:
  - `Applicant Document`
  - `Applicant Health Profile`
  - `Student Applicant`
- `document_type` is optional and only valid when `target_type = Applicant Document`.

## Reviewer Rows

Use child table `Applicant Review Rule Reviewer`.

Each row must set exactly one of:

- `reviewer_role`
- `reviewer_user`

Duplicate reviewer rows are rejected.

## Rule Resolution Contract

When assignments are materialized:

1. Only active rules in applicant organization/school ancestor scope are considered.
2. Most-specific scope is selected by nearest organization + nearest school + program specificity.
3. All matching rules at the same most-specific scope are merged.
4. Reviewer rows are deduped by `(reviewer_user, reviewer_role)`.
5. If no rule matches, no assignment is created.

## Permissions

Rule management is limited to:

- `Admission Manager`
- `Academic Admin`
- `System Manager`
