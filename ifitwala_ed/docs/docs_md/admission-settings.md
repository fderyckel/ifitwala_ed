---
title: "Admission Settings: Admissions SLA and Assignment Policy"
slug: admission-settings
category: Admission
doc_order: 1
version: "1.5.1"
last_change_date: "2026-04-23"
summary: "Define admissions SLA windows, assignment task color defaults, admissions-portal family/access toggles, and the admissions-to-enrollment auto-hydration policy."
seo_title: "Admission Settings: Admissions SLA and Assignment Policy"
seo_description: "Define admissions SLA windows, assignment task color defaults, and admissions-portal guardian section visibility."
---

## Before You Start (Prerequisites)

- Ensure admissions staff users exist with the right roles (`Admission Manager`, `Admission Officer`).
- Confirm your admissions intake flow is using [**Inquiry**](/docs/en/inquiry/), because these settings are consumed from Inquiry services.
- Align SLA day windows and assignment color conventions with operations leadership before changing values in production.

`Admission Settings` is a Single DocType that stores operational defaults for admissions SLA deadlines, assignment ToDo styling, admissions portal surface toggles, family-workspace access mode, and the admissions-to-enrollment auto-hydration policy.

## Authoritative Contract

[[fig:fig-1 size=auto]]

This doctype owns eight configuration fields:

- `first_contact_sla_days`: days from inquiry submission to first-contact due date.
- `followup_sla_days`: days from assignment to follow-up due date.
- `todo_color`: color used when creating assignment ToDo rows from admissions assignment actions.
- `sla_enabled`: boolean setting stored in the doc.
- `sla_check_interval_hours`: integer setting stored in the doc.
- `show_guardians_in_admissions_profile`: boolean toggle to show/hide guardian intake rows in `/admissions/profile`.
- `admissions_access_mode`: select setting controlling whether `/admissions` runs as `Single Applicant Workspace` or `Family Workspace`.
- `auto_hydrate_enrollment_request_after_promotion`: boolean toggle controlling whether promotion auto-creates a draft `Program Enrollment Request` from an accepted `Applicant Enrollment Plan`.

## How to Read the Two SLAs

- `first_contact_sla_days` and `followup_sla_days` are measured from different anchor events, so one is not required to be greater/less than the other.
- `first_contact_due_on` is anchored to inquiry submission time (`submitted_at`) and seeded by `set_inquiry_deadlines`; legacy missing values are remediated through the one-shot patch `ifitwala_ed.patches.backfill_inquiry_first_contact_due_dates`.
- `followup_due_on` is anchored to assignment time and is set on `assign_inquiry` / `reassign_inquiry`.
- In `Assigned` state, SLA status evaluation can consider both due dates; whichever deadline is sooner can drive overdue/due-today status.

### Worked Example (Concrete Dates)

Assume:
- `first_contact_sla_days = 3`
- `followup_sla_days = 2`
- Inquiry submitted on `2026-03-04`
- Inquiry assigned on `2026-03-06`

Then:
- `first_contact_due_on = 2026-03-07` (submission + 3 days)
- `followup_due_on = 2026-03-08` (assignment + 2 days)

This shows why `followup_sla_days` does not need to be less than `first_contact_sla_days`: the due dates depend on different start points.

## Non-Negotiable Invariants

1. `Admission Settings` is `issingle = 1`; there is one authoritative settings record per site.
2. First-contact and follow-up SLA dates are derived from these settings in admissions utility flows, not from per-user preferences.
3. Assignment ToDo color falls back to `"blue"` when `todo_color` is empty during assignment/reassignment calls.
4. Current scheduler execution is hourly via hooks; `sla_enabled` and `sla_check_interval_hours` are currently stored settings and are not used to gate or reschedule that hook path.
5. Guardian intake in admissions portal profile is controlled by `show_guardians_in_admissions_profile`; when disabled, applicant portal profile payload omits editable guardian rows.
6. `admissions_access_mode` is the authoritative site contract for admissions login resolution:
   - `Single Applicant Workspace`: login requires `Admissions Applicant` + exactly one `Student Applicant.applicant_user`.
   - `Family Workspace`: login can use `Admissions Family` + explicit consenting applicant guardian linkage to one or more applicants.
7. Enrollment-request hydration remains request-only and post-student; this setting controls timing, not contract shape.

## Where It Is Used Across the ERP

- [**Inquiry**](/docs/en/inquiry/):
  - `set_inquiry_deadlines` seeds `first_contact_due_on` using `first_contact_sla_days`.
  - `assign_inquiry` / `reassign_inquiry` set `followup_due_on` from `followup_sla_days` and ToDo color from `todo_color`.
- [**Student Applicant**](/docs/en/student-applicant/):
  - admissions family/applicant portal access mode is resolved from `admissions_access_mode`.
  - `promote_to_student()` reads `auto_hydrate_enrollment_request_after_promotion` to decide whether to auto-hydrate a draft request from the accepted applicant plan.
- [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/):
  - accepted plans can stay staff-reviewed/manual or auto-hydrate immediately after promotion based on this setting.
- Scheduler:
  - `ifitwala_ed.admission.scheduled_jobs.run_hourly_sla_sweep` is registered in `hooks.py` hourly events.
  - Sweep logic in `check_sla_breaches` is column-aware, recomputes SLA status, and caches run summary at `admissions:sla_sweep:last_run`.
  - Existing sites backfill missing `Inquiry.first_contact_due_on` values through the one-shot patch `ifitwala_ed.patches.backfill_inquiry_first_contact_due_dates`.
- Inquiry dashboard analytics:
  - `ifitwala_ed.api.inquiry.get_dashboard_data` uses `followup_sla_days` as the upcoming-horizon window.

## Permission Model

- **Write**: `System Manager`, `Admission Manager`
- **Read-only**: `Admission Officer`, `Academic Admin`

## Lifecycle and Operations Flow

1. Configure SLA day windows and `todo_color`.
2. Intake and assign inquiries; utility methods apply these defaults when deadlines and assignments are created.
3. Let hourly scheduler recompute SLA statuses and maintain overdue/due-today/upcoming/on-track states.
4. Monitor dashboard and list indicators, then adjust settings only as an intentional policy change.

<Callout type="info" title="When to change settings">
Treat SLA value updates as policy changes. Mid-cycle edits can shift operational expectations for newly calculated deadlines and dashboard horizons.
</Callout>

## Related Docs

<RelatedDocs
  slugs="inquiry,student-applicant,applicant-review-assignment"
  title="Related Admissions Operations Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-04-23)

- **DocType schema file**: `ifitwala_ed/admission/doctype/admission_settings/admission_settings.json`
- **Controller file**: `ifitwala_ed/admission/doctype/admission_settings/admission_settings.py`
- **Desk script file**: `ifitwala_ed/admission/doctype/admission_settings/admission_settings.js`
- **Required fields (`reqd=1`)**: none.
- **Lifecycle hooks in controller**: none (`AdmissionSettings(Document)` with `pass` only).
- **Operational/public methods on this doctype**: none.

- **DocType**: `Admission Settings` (`issingle = 1`)
- **Field contract**:
  - `first_contact_sla_days` (`Int`, default `1`)
  - `followup_sla_days` (`Int`, default `7`)
  - `todo_color` (`Color`)
  - `sla_enabled` (`Check`, default `0`)
  - `sla_check_interval_hours` (`Int`)
- `show_guardians_in_admissions_profile` (`Check`, default `0`)
- `admissions_access_mode` (`Select`, default `Single Applicant Workspace`)
- `auto_hydrate_enrollment_request_after_promotion` (`Check`, default `1`)
- **Runtime consumers**:
  - `ifitwala_ed/admission/admission_utils.py`
    - `_get_first_contact_sla_days_default`
    - `set_inquiry_deadlines`
    - `assign_inquiry`
    - `reassign_inquiry`
    - `check_sla_breaches`
  - `ifitwala_ed/patches/backfill_inquiry_first_contact_due_dates.py`
    - one-shot remediation for legacy missing `first_contact_due_on` values
  - `ifitwala_ed/api/inquiry.py`
    - `get_dashboard_data` reads `followup_sla_days` for upcoming horizon
  - `ifitwala_ed/api/admissions_portal.py`
    - family/applicant access resolution and invite mode are gated by `admissions_access_mode`
    - `_guardians_feature_enabled` controls whether `/admissions/profile` payload exposes guardian intake rows
    - `update_applicant_profile` applies guardian rows only when the setting is enabled
  - `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
    - `_maybe_auto_hydrate_enrollment_request_after_promotion` gates draft request hydration from accepted applicant plans
  - `ifitwala_ed/hooks.py`
    - hourly scheduler entrypoint: `ifitwala_ed.admission.scheduled_jobs.run_hourly_sla_sweep`
- **Operational nuance**:
  - Current scheduler registration is static hourly from `hooks.py`; no code path currently reads `sla_enabled` or `sla_check_interval_hours` to enable/disable or retime scheduler execution.

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full single-doctype control |
| `Admission Manager` | Yes | Yes | Yes | Yes | Operational owner |
| `Admission Officer` | Yes | No | No | No | Read-only |
| `Academic Admin` | Yes | No | No | No | Read-only |
