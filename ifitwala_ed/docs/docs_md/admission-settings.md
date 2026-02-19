---
title: "Admission Settings: SLA and Assignment Controls"
slug: admission-settings
category: Admission
doc_order: 1
summary: "Configure response SLAs, assignment colors, and background SLA checks for the full admissions pipeline."
seo_title: "Admission Settings: SLA and Assignment Controls"
seo_description: "Configure response SLAs, assignment colors, and background SLA checks for the full admissions pipeline."
---

## Admission Settings: SLA and Assignment Controls

## Before You Start (Prerequisites)

- Ensure your admissions team users and roles are in place (`Admission Manager` / `Admission Officer`).
- Confirm you will run admissions through `Inquiry` and/or `Registration of Interest` so SLA settings are actually used.
- Align SLA values and assignment color conventions with operations before enabling checks.

Admission teams move fast, and missed follow-ups are expensive. `Admission Settings` is the control center that keeps Inquiry and Registration workflows time-bound and visible.

<Callout type="tip" title="Why this matters">
When these settings are correct, your team sees at-risk records early instead of discovering misses at the end of the week.
</Callout>

## What You Configure

- **First Contact SLA days**: days from submission to first contact deadline.
- **Follow up SLA Days**: days from assignment to follow-up deadline.
- **SLA Enabled / SLA Check Interval Hours**: operational controls for SLA tracking.
- **Todo Color**: visual color applied to assignment ToDo items created from Inquiry assignment flows.

## Where It Is Used Across the ERP

- [**Inquiry**](/docs/en/inquiry/): default SLA deadlines and list indicators.
- [**Registration of Interest**](/docs/en/registration-of-interest/): same SLA helper is reused.
- Scheduler job: hourly SLA sweep via `ifitwala_ed.admission.admission_utils.check_sla_breaches`.
- Assignment flows: `assign_inquiry` and `reassign_inquiry` use these values for follow-up deadlines and ToDo color.
- Inquiry analytics API uses `followup_sla_days` as upcoming horizon in `ifitwala_ed.api.inquiry.get_dashboard_data`.

## Permission Model

- **Write**: `System Manager`, `Admission Manager`
- **Read-only**: `Admission Officer`, `Academic Admin`

## Lifecycle and Linked Documents

1. Set SLA and assignment settings before admitting your first inquiry batch.
2. Run daily intake in `Inquiry` and `Registration of Interest`; each record uses this configuration.
3. Review breached/at-risk records and adjust team workload from assignment and ToDo indicators.
4. Revisit SLA values at term boundaries so new admissions periods reflect real team capacity.

<Callout type="info" title="When to change settings">
Treat SLA updates as operational policy changes. Confirm with admissions leadership before changing values mid-cycle.
</Callout>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/admission/doctype/admission_settings/admission_settings.json`
- **Controller file**: `ifitwala_ed/admission/doctype/admission_settings/admission_settings.py`
- **Required fields (`reqd=1`)**: none at schema level; controller/workflow rules enforce operational completeness where applicable.
- **Lifecycle hooks in controller**: none (reference/master behavior, or handled by framework defaults).
- **Operational/public methods**: none beyond standard document behavior.

- **DocType**: `Admission Settings` (`ifitwala_ed/admission/doctype/admission_settings/`)
- **Type**: `issingle = 1`
- **Desk surface**:
  - single doctype form under Admission module
  - consumed by assignment and SLA helper code paths
- **Controller**: no custom controller logic (`pass`), behavior is consumed by utility/services code.
- **Key consumers**:
  - `ifitwala_ed/admission/admission_utils.py`
  - `ifitwala_ed/api/inquiry.py`
  - `ifitwala_ed/hooks.py` (scheduler events)

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full single-doctype control |
| `Admission Manager` | Yes | Yes | Yes | Yes | Operational owner of SLA settings |
| `Admission Officer` | Yes | No | No | No | Read-only |
| `Academic Admin` | Yes | No | No | No | Read-only |

## Related Docs

- [**Inquiry**](/docs/en/inquiry/) - operational first-contact workflow
- [**Registration of Interest**](/docs/en/registration-of-interest/) - public lead intake
- [**Student Applicant**](/docs/en/student-applicant/) - downstream admissions lifecycle
