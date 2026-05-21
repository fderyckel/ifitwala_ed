---
title: "Admission Settings: Your Admissions Policy Control Panel"
slug: admission-settings
category: Admission
doc_order: 1
version: "1.6.0"
last_change_date: "2026-05-21"
summary: "Set the admissions response rhythm, portal access mode, guardian visibility, applicant-to-enrollment handoff, and deposit policy from one shared control panel."
seo_title: "Admission Settings: Your Admissions Policy Control Panel"
seo_description: "Use Admission Settings to configure admissions SLA expectations, portal access mode, guardian visibility, enrollment-request handoff, and deposit policy."
---

## What Are Admission Settings?

`Admission Settings` is the control panel for how your admissions team responds to families, manages follow-up work, opens the admissions portal, and moves accepted applicants toward enrollment.

Most staff will not change these settings every day. But everyone in admissions benefits when they are clear: officers know how quickly to respond, managers know what the team is measuring, families get the right portal experience, and finance-sensitive steps like deposits are handled before promotion.

![admission settings form](docs://fig1){data-size="auto"}

<Callout type="info" title="Why Ifitwala Ed is different">
Admission Settings connects the whole admissions journey: inquiry response, staff task visibility, applicant/family portal access, offer deposits, and the final handoff into enrollment. Instead of scattering those choices across disconnected tools, Ifitwala Ed keeps the policy in one place and applies it consistently where staff already work.
</Callout>

## Why This Matters

- **No inquiry should disappear.** SLA settings help teams see which families need first contact or follow-up.
- **Admissions work gets visible ownership.** Assignment settings make admissions tasks easier to recognize in staff ToDo lists.
- **Your portal can match your real admissions model.** Schools can choose an individual applicant workspace or a family workspace.
- **Guardian data collection stays intentional.** You decide whether guardians appear in the admissions profile workflow.
- **Accepted applicants move forward with less manual handoff.** If enabled, accepted applicant plans can prepare the next enrollment request step after promotion.
- **Deposit policy is respected before promotion.** If a required deposit must be paid first, the system can block premature promotion.

## Before You Change These Settings

Admission Settings are operational policy settings, not personal preferences. Review them with the people who own admissions flow, applicant communication, and deposit policy.

You should have:

- admissions staff users with the right roles, usually `Admission Manager` and `Admission Officer`
- your admissions intake flow using [**Inquiry**](/docs/en/inquiry/)
- clear internal expectations for first contact and follow-up timing
- agreement on whether applicants should use a single-applicant or family admissions workspace
- finance alignment before enabling required-deposit promotion blocks

<Callout type="warning" title="Treat changes as policy changes">
Changing SLA days or deposit behavior during an active admissions cycle can change staff expectations and applicant readiness decisions. Make changes deliberately, and tell the admissions team what changed.
</Callout>

## Settings You Control

| Setting | What it controls | Why it matters |
|---|---|---|
| First contact SLA | How many days the team has to make first contact after an inquiry is submitted | Helps new families receive timely attention |
| Follow-up SLA | How many days the assigned owner has for the next follow-up after assignment | Keeps assigned admissions work from going stale |
| Assignment ToDo color | The color used for admissions assignment tasks | Makes admissions follow-up easier to spot in staff task lists |
| SLA enabled / check interval | Stored SLA configuration values | The live SLA sweep currently runs hourly; IT details are at the bottom of this page |
| Show guardians in admissions profile | Whether editable guardian rows appear in the applicant portal profile | Lets schools decide how much family data is collected during admissions |
| Admissions access mode | Whether `/admissions` behaves as a single-applicant workspace or a family workspace | Shapes how applicants and families log in and manage applications |
| Auto-create enrollment request after promotion | Whether an accepted applicant plan can prepare a draft Program Enrollment Request after student promotion | Reduces manual handoff between admissions and enrollment |
| Deposit defaults | School-approved default deposit terms for accepted applicant offers | Keeps admissions offers aligned with finance policy |
| Require deposit before promotion | Whether promotion is blocked until a required admissions deposit is paid | Prevents accepted applicants from moving into enrollment before required payment is complete |

<Callout type="tip" title="Start simple">
For a new school demo or pilot, set clear SLA days first, choose the portal access mode, and leave deposit enforcement off until the offer and finance workflow is ready.
</Callout>

## How This Fits the Admissions Flow

<Steps title="Admission Settings in the admissions journey">
  <Step title="Inquiry arrives">
    A family submits an inquiry or a staff member records a lead. Admission Settings provide the first-contact expectation.
  </Step>
  <Step title="Staff assigns follow-up">
    When an inquiry is assigned or reassigned, the follow-up SLA and ToDo color help the owner see what needs attention.
  </Step>
  <Step title="Applicant uses the portal">
    The admissions access mode decides whether the applicant works alone or through a family workspace. Guardian visibility controls whether guardian rows appear in the admissions profile.
  </Step>
  <Step title="Offer and deposit policy apply">
    Accepted applicant plans can use deposit defaults, and schools can require a paid deposit before promotion when that is the policy.
  </Step>
  <Step title="Admissions hands off to enrollment">
    After promotion, Ifitwala Ed can prepare the draft enrollment request from the accepted applicant plan when auto-hydration is enabled.
  </Step>
</Steps>

## Permission Matrix

Admission Officers and Academic Admins can read Admission Settings so they understand the operating rules. System Managers and Admission Managers can change them.

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full single-settings control |
| `Admission Manager` | Yes | Yes | Yes | Yes | Admissions policy owner |
| `Admission Officer` | Yes | No | No | No | Can see expectations, cannot change policy |
| `Academic Admin` | Yes | No | No | No | Read-only policy visibility |

## Practical Examples

### Fast-response admissions team

A school wants every new family contacted within one working rhythm and every assigned follow-up handled quickly. Set a short first-contact SLA and a follow-up SLA that matches the team's daily routine.

Example:

- Inquiry submitted on `2026-03-04`
- First contact SLA is `3` days
- Inquiry assigned on `2026-03-06`
- Follow-up SLA is `2` days

Then:

- First contact is due on `2026-03-07`
- Assigned follow-up is due on `2026-03-08`

These two deadlines start from different moments. The first-contact SLA starts when the inquiry arrives; the follow-up SLA starts when someone is assigned.

### Family workspace admissions model

A school that works mostly with parents may prefer `Family Workspace`, so one consenting family login can manage more than one applicant. A school that works applicant-by-applicant may prefer `Single Applicant Workspace`.

### Deposit required before enrollment

If the school requires an admissions deposit before an accepted applicant becomes a student, enable the deposit requirement only after deposit defaults and finance ownership are ready. The setting protects the promotion step; it does not collect payment by itself.

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Review SLA windows before each admissions season.</Do>
  <Do>Align deposit settings with finance before enforcing promotion blocks.</Do>
  <Do>Choose the portal access mode that matches how families actually apply.</Do>
  <Do>Tell admissions staff when policy settings change mid-cycle.</Do>
  <Dont>Change SLA days casually during an active campaign.</Dont>
  <Dont>Enable family workspace until guardian identity and consent workflows are ready.</Dont>
  <Dont>Treat deposit settings as a full payment-plan setup.</Dont>
  <Dont>Assume read-only staff can change these settings.</Dont>
</DoDont>

## Common Questions

### Should the follow-up SLA always be shorter than the first-contact SLA?

Not necessarily. They measure different things. First contact starts from inquiry submission. Follow-up starts from assignment or reassignment. A shorter follow-up SLA can still produce a later due date if the inquiry was assigned later.

### Will changing SLA days update every old inquiry?

No. Treat SLA changes as policy changes for operational expectations going forward. Existing records may already have deadline values based on the settings that were active when those workflow moments happened.

### Does requiring a deposit collect the money?

No. Deposit settings control the admissions deposit bridge and promotion block. Finance workflows still own invoice submission, payment recording, and financial reconciliation.

### Who should own Admission Settings?

Usually the Admissions Manager owns the values, with input from school leadership and finance when deposit policy is involved. Admission Officers should understand the settings, but they should not normally change them.

### Which portal mode should we choose?

Use `Single Applicant Workspace` when each applicant should log in and manage their own application. Use `Family Workspace` when guardians need a family-centered view across one or more applicants.

## Related Docs

<RelatedDocs
  slugs="inquiry,admission-cockpit,student-applicant,applicant-enrollment-plan,applicant-review-assignment"
  title="Continue With Related Admissions Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-21)

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
  - `deposit_defaults` (`Table` -> `Admission Deposit Default`)
  - `require_deposit_before_promotion` (`Check`, default `0`)
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
    - promotion checks `require_deposit_before_promotion` when the accepted applicant plan requires a deposit
  - `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`
    - applies `deposit_defaults` to accepted plans and exposes deposit invoice generation
  - `ifitwala_ed/hooks.py`
    - hourly scheduler entrypoint: `ifitwala_ed.admission.scheduled_jobs.run_hourly_sla_sweep`
- **Operational invariants**:
  - `Admission Settings` is `issingle = 1`; there is one authoritative settings record per site.
  - First-contact and follow-up SLA dates are derived from these settings in admissions utility flows, not from per-user preferences.
  - Assignment ToDo color falls back to `"blue"` when `todo_color` is empty during assignment/reassignment calls.
  - Current scheduler registration is static hourly from `hooks.py`; no code path currently reads `sla_enabled` or `sla_check_interval_hours` to enable/disable or retime scheduler execution.
  - `show_guardians_in_admissions_profile` controls whether applicant portal profile payloads expose editable guardian rows.
  - `admissions_access_mode` is the authoritative site contract for admissions login resolution:
    - `Single Applicant Workspace`: login requires `Admissions Applicant` + exactly one `Student Applicant.applicant_user`.
    - `Family Workspace`: login can use `Admissions Family` + explicit consenting applicant guardian linkage to one or more applicants.
  - Enrollment-request hydration remains request-only and post-student; `auto_hydrate_enrollment_request_after_promotion` controls timing, not contract shape.
  - Deposit settings control the admissions deposit bridge only. They do not create full payment plans, collect payment, or create committed enrollment.
- **SLA date behavior**:
  - `first_contact_due_on` is anchored to inquiry submission time (`submitted_at`) and seeded by `set_inquiry_deadlines`.
  - `followup_due_on` is anchored to assignment time and is set on `assign_inquiry` / `reassign_inquiry`.
  - In `Assigned` state, SLA status evaluation can consider both due dates; whichever deadline is sooner can drive overdue/due-today status.
  - Sweep logic in `check_sla_breaches` is column-aware, recomputes SLA status, and caches run summary at `admissions:sla_sweep:last_run`.
