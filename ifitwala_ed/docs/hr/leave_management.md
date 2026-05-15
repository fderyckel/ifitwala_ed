# Leave Management (HR Domain)

Status: Active canonical contract
Code refs:
- `ifitwala_ed/hr/doctype/leave_application/leave_application.py`
- `ifitwala_ed/hr/doctype/leave_allocation/leave_allocation.py`
- `ifitwala_ed/hr/doctype/leave_ledger_entry/leave_ledger_entry.py`
- `ifitwala_ed/hr/leave_permissions.py`
- `ifitwala_ed/hr/utils.py`
- `ifitwala_ed/hooks.py`
Test refs:
- `ifitwala_ed/hr/test_leave_permissions.py`
- `ifitwala_ed/hr/test_leave_utils.py`
- `ifitwala_ed/hr/test_scheduler_dispatch.py`
- `ifitwala_ed/hr/doctype/leave_application/test_leave_application.py`
- `ifitwala_ed/patches/test_backfill_default_leave_types.py`

## Scope and Baseline

This document is the implementation contract for the leave domain integrated into `ifitwala_ed`.

- Upstream baseline: HRMS `develop`
- Upstream snapshot commit: `5a3b657db2b9407f2a03ac78ce8cdf054a53bc1e`
- Temporary vendor snapshot was used during import and then removed after stabilization.
- Runtime scope: Desk + backend only
- Out of scope: portal leave UX and portal leave API flows

## Imported/Added HR Leave DocTypes

### Core leave objects
- `Leave Type`
- `Leave Policy`
- `Leave Policy Detail` (child)
- `Leave Period`
- `Leave Policy Assignment`
- `Leave Allocation`
- `Leave Application`
- `Leave Ledger Entry`
- `Leave Control Panel`
- `Leave Block List`
- `Leave Block List Date` (child)
- `Leave Block List Allow` (child)
- `Compensatory Leave Request`
- `Leave Adjustment`
- `Earned Leave Schedule` (child)

### Deferred/feature-gated object
- `Leave Encashment` (imported, hard-disabled by setting unless explicitly enabled)

### Supporting objects
- `Employee Attendance` (leave-driven staff attendance ledger)
- `HR Settings` (singleton with leave-specific control flags used by this domain)

## Default Leave Type Seed Contract

Fresh installs seed a baseline leave-type catalog through `setup_education()` so HR can start configuring policies without manual doctype setup.

Seeded defaults:

- `Annual Leave`
- `Sick Leave`
- `Personal Leave`
- `School Related Activities`
- `Bereavement Leave`
- `Maternity Leave`
- `Paternity Leave`
- `Family Care Leave`
- `Professional Development Leave`
- `Unpaid Leave`

Seed behavior:

- Only `Unpaid Leave` is created with `is_lwp = 1`
- No default leave allocations, earned-leave behavior, carry-forward rules, encashment rules, or compensatory behavior are preconfigured
- Leave policies remain the canonical place to define entitlement counts and operational rules

Existing-site rollout uses `ifitwala_ed.patches.backfill_default_leave_types` to seed the same defaults idempotently.

## Canonical Schema Mapping Applied

- `company` fields and filters mapped to `organization`
- Employee status checks mapped to `employment_status`
- Employee display/name references mapped to `employee_full_name`
- Employee-level leave approver resolved from `Employee.leave_approver`
- Leave date validations and balance computations anchored on existing Employee + Leave Allocation + Leave Ledger Entry contracts

`school` remains present on some leave records as optional context, but is not used as a holiday resolution source in HR leave flows.

## Holiday Resolution Contract (HR)

HR leave flows use **Staff Calendar only**.

- Primary stored holiday source field: `Employee.current_holiday_lis`
- Holiday row source doctype: `Staff Calendar Holidays`
- No School Calendar fallback is used in HR leave calculations
- When the stored employee link lags behind a recent Staff Calendar change, HR holiday resolution may self-heal to the effective `Staff Calendar` instead of requiring a manual Employee re-save first

This applies to:

- leave-day calculations
- leave balance evaluation where holidays are excluded
- calendar holiday rendering in leave calendar views
- optional leave day validation

If no staff calendar exists for an employee, leave holiday resolution raises an explicit validation exception unless the caller requests non-throw behavior.

### Optional leave source field

`Leave Period.optional_holiday_list` is retained as the source identifier for optional leave day validation.

- Expected source type: Staff Calendar parent id (used against `Staff Calendar Holidays.parent`)
- Validation path: `Leave Application.validate_optional_leave`
- School calendar rows are not considered for optional leave eligibility

## Approval and Workflow Contract

Leave approval is fully controller-owned (no Frappe Workflow records).

`Leave Application.status` transition enforcement is implemented in controller logic with transition guards.

### Status transitions
- `Open` -> `Open|Approved|Rejected|Cancelled`
- `Approved` -> `Approved`
- `Rejected` -> `Rejected`
- `Cancelled` -> `Cancelled`

### Approval authority
Approve/Reject is allowed only for:

1. Assigned `leave_approver`
2. Override roles:
   - `HR User`
   - `HR Manager`
   - `Academic Admin`
   - `System Manager`

Self-approval can be blocked by `HR Settings.prevent_self_leave_approval`.

## Permission and Tenancy Model

Organization-first tenancy is enforced via permission hooks in `ifitwala_ed.hr.leave_permissions`.

### Role scope
- Org-scoped leave roles:
  - `HR User`
  - `HR Manager`
  - `Academic Admin`
  - `System Manager`

### Query scoping behavior
- Org-scoped roles, including `System Manager`, are restricted to the resolved base-organization subtree (`organization` + descendants)
- Non-HR users: restricted to self (`employee` = current employee)
- Sibling organization isolation is enforced by query condition generation and doc-level checks
- The built-in `Administrator` account is not a tenant-scoped role and remains outside this scoped-role contract.

### Leave Encashment access
When `HR Settings.enable_leave_encashment = 0`:

- `leave_encashment_has_permission` returns `False`
- `leave_encashment_pqc` returns `1=0`

Result: Leave Encashment is inaccessible in practice even if the doctype exists.

## Leave Application Side Effects

On submit/cancel, leave application updates:

1. `Leave Ledger Entry` (leave consumption/reversal)
2. `Employee Attendance` (idempotent create/update/cancel)

Attendance updates are keyed by employee/date and linked back to the leave application reference to keep cancellation deterministic.

## Leave Ledger Contract

`Leave Ledger Entry` remains the authoritative leave movement ledger.

- Leave allocations create positive entries
- Leave applications and encashment create consumption entries
- Cancellation removes/reverses ledger impact through controller routines
- Expiry processing keeps `process_expired_allocation` for direct/manual execution, while the scheduler now dispatches chunked background work and respects HR settings feature flags

## Scheduler Contract

Configured daily jobs:

1. `ifitwala_ed.hr.doctype.leave_ledger_entry.leave_ledger_entry.dispatch_process_expired_allocation`
2. `ifitwala_ed.hr.utils.dispatch_allocate_earned_leaves`
3. `ifitwala_ed.hr.utils.dispatch_generate_leave_encashment`

Runtime gating:

- Earned leaves require `HR Settings.enable_earned_leave_scheduler = 1`
- Expiry requires `HR Settings.enable_leave_expiry_scheduler = 1`
- Encashment generation requires both:
  - `HR Settings.enable_leave_encashment = 1`
  - `HR Settings.auto_leave_encashment = 1`

Execution model:

- Daily hooks are dispatcher-only and enqueue chunk workers onto the `long` queue
- Chunk workers re-check live allocation state before mutating ledger data
- Scheduler summaries are written to logs and cache keys for observability
- Direct/manual execution paths remain available for controlled operator actions

Current implementation policy keeps encashment disabled by default pending payroll/account mapping.

## Desk Integration

### HR workspace entries
- `Leave Application`
- `Leave Allocation`
- `Leave Policy Assignment`
- `Leave Control Panel`

### Calendar hooks
- `Leave Application` is registered in `hooks.calendars`

### Dashboard relations
- Leave dashboards reference `Employee Attendance` for leave-attendance traceability
- `Leave Encashment` dashboard exposure is minimized in default HR navigation paths

## Leave Encashment Deferred Policy

Encashment model/controller is retained for compatibility, but production usage is deferred.

Constraints in current phase:

- no payroll rollout dependency in active operations
- no required accounting execution in normal leave flow
- feature-flag gating must stay off unless payroll/account mapping is formally approved

## Invariants and Non-Negotiables

- Parent controllers own business logic; child leave doctypes stay data-only
- No silent leave-action failure: validation failures must raise explicit messages
- Permissions are server-side authoritative
- Organization subtree scope is required for multi-tenant safety
- Staff Calendar is the exclusive HR holiday source

## Known Deferred Items

- Portal leave submission and approval UX
- Payroll/accounting-grade leave encashment enablement
- Broader integration test matrix for high-volume scheduler + policy assignment permutations
