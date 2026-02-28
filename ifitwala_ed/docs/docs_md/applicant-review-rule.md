---
title: "Applicant Review Rule: Reviewer Scope Configuration"
slug: applicant-review-rule
category: Admission
doc_order: 8
version: "1.1.1"
last_change_date: "2026-02-28"
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

Each row must set `reviewer_mode`:

- `Role Only`
- `Specific User`

Row rules:

- `Role Only` requires `reviewer_role` and must keep `reviewer_user` empty.
- `Specific User` requires `reviewer_user`; `reviewer_role` is optional but recommended.
- If `Specific User` includes a `reviewer_role`, the selected user must have that role.
- Duplicate reviewer actors are rejected.

UI behavior:

- In the `reviewers` child table, `reviewer_role` can be selected by users with `Applicant Review Rule` write access, even if they do not have direct `Role` read permission.
- In the `reviewers` child table, `reviewer_user` link options are filtered by `reviewer_role` when a role is selected.
- If no role is selected, `reviewer_user` shows the standard enabled-user query.

## Rule Resolution Contract

When assignments are materialized:

1. Only active rules in applicant organization/school ancestor scope are considered.
2. Most-specific scope is selected by nearest organization + nearest school + program specificity.
3. All matching rules at the same most-specific scope are merged.
4. Reviewer rows are deduped by effective assignment actor (specific user or role queue).
5. If no rule matches, no assignment is created.

## Focus Overlay Behavior (Role Queue)

When a rule row is `Role Only`, materialized `Applicant Review Assignment` remains role-assigned (`assigned_to_role`).

From Focus overlay, a role holder can:

- **Take ownership** (claim): convert open assignment to `assigned_to_user = current user`.
- **Assign** to another enabled user with the same role: convert open assignment to `assigned_to_user = selected user`.

## Permissions

Rule management is limited to:

- `Admission Manager`
- `Academic Admin`
- `System Manager`
