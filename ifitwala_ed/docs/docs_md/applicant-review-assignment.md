---
title: "Applicant Review Assignment: Materialized Review Work Item"
slug: applicant-review-assignment
category: Admission
doc_order: 9
version: "1.0.0"
last_change_date: "2026-02-23"
summary: "System-generated admissions review assignments powering Focus actions and reviewer audit summary."
seo_title: "Applicant Review Assignment: Materialized Review Work Item"
seo_description: "System-generated admissions review assignments powering Focus actions and reviewer audit summary."
---

## Applicant Review Assignment: Materialized Review Work Item

`Applicant Review Assignment` is system-created and drives reviewer actions.

This doctype is not the primary user surface.

## Targets

Each assignment references one target:

- `Applicant Document`
- `Applicant Health Profile`
- `Student Applicant` (overall application review)

## Assignment Actor Contract

Exactly one actor must be set:

- `assigned_to_user`, or
- `assigned_to_role`

Open-assignment uniqueness is enforced per `(target_type, target_name, assignee)`.

## Lifecycle

- `Open` → reviewer can act in Focus.
- `Done` → decision captured, item disappears from Focus.
- `Cancelled` → reserved for operational cleanup.

For repeat cycles (health re-declare, resubmitted application), completed assignments are reopened instead of duplicated.

## Decisions

Decision set depends on target type.

- Applicant Document: `Approved`, `Needs Follow-Up`, `Rejected`
- Applicant Health Profile: `Cleared`, `Needs Follow-Up`
- Student Applicant: `Recommend Admit`, `Recommend Waitlist`, `Recommend Reject`, `Needs Follow-Up`

Document decision mapping to `Applicant Document.review_status`:

- `Approved` → `Approved`
- `Rejected` → `Rejected`
- `Needs Follow-Up` → `Pending`

## Focus Integration

Open assignments generate Focus items with action type:

- `applicant_review.assignment.decide`

Submission endpoint:

- `ifitwala_ed.api.focus.submit_applicant_review_assignment`

## Audit/Reporting

Completed assignments are aggregated into Desk `Student Applicant.review_assignments_summary`.
