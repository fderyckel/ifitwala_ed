# Professional Development Governance (HR Domain)

## Scope and Status

This document is the canonical Phase 1 contract for Professional Development (PD) in `ifitwala_ed`.

- Runtime scope: Desk governance + staff SPA (`My Growth`) + backend lifecycle APIs
- Authority: HR workflow, school-tree scope, Academic Year boundary, and PD-scoped accounting encumbrance
- Out of scope in Phase 1:
  - substitute booking automation
  - compliance catalog / expiry engine
  - sharing-back enforcement
  - recommendation generation and delayed impact analytics

PD is implemented as a closed-loop HR workflow, not as a reimbursement form and not as a generic LMS tracker.

## Canonical Time and Scope Model

Every PD workflow object is scoped by:

- `employee`
- `organization`
- `school`
- `academic_year`

Accounting legality remains:

- `organization`
- `fiscal_year`

Locked rules:

- `Academic Year` is the educational boundary for request, record, outcome, and budget governance.
- `Fiscal Year` is the posting legality boundary for encumbrance reserve and liquidation entries.
- `school` must belong to `organization`.
- `academic_year.school` must equal the document `school`.
- archived academic years cannot accept new PD requests.

## Phase 1 DocTypes

### Strategic / policy

- `Professional Development Theme`

### Budget and finance

- `Professional Development Budget`
- `Professional Development Encumbrance`

### Lifecycle

- `Professional Development Request`
- `Professional Development Record`
- `Professional Development Outcome`

### Data-only child tables

- `Professional Development Request Cost`
- `Professional Development Audit Entry`
- `Professional Development Outcome Evidence`

Child tables remain data-only. All workflow, validation, booking, and accounting logic belongs in parent controllers and services.

## HR Settings Contract

`HR Settings` owns the Phase 1 PD policy switches:

- `pd_budget_mode`
- `pd_approval_routing`
- `pd_auto_approve_threshold`
- `pd_require_completion_evidence`
- `pd_require_liquidation_reflection`
- `pd_year_close_policy`

These settings are global policy controls for the current site and do not replace document-level scope validation.

## Professional Development Theme

`Professional Development Theme` is the strategy/alignment reference.

Locked fields:

- `theme_name`
- `organization`
- `school` (optional school-specific override; blank means organization-wide)
- `description`
- `is_active`

## Professional Development Budget

Phase 1 uses one budget document per reservable pool line. This keeps reservation locking doc-scoped and avoids a generic budget engine.

Locked fields:

- `organization`
- `school`
- `academic_year`
- `budget_mode`
- `pool_label`
- `professional_development_theme` (optional)
- optional targeting dimensions:
  - `employee`
  - `department`
  - `program`
- finance configuration:
  - `encumbrance_account`
  - `expense_account`
  - `clearing_account`
- amounts:
  - `budget_amount`
  - `reserved_amount`
  - `liquidated_amount`
  - `available_amount`
- `is_active`

Budget invariants:

- `available_amount = budget_amount - reserved_amount - liquidated_amount`
- reservation and liquidation operate under row lock
- inactive budgets cannot accept new reservations
- budget scope must match the request scope exactly on `organization`, `school`, and `academic_year`

Mode-specific intent:

- `School Pool`: no employee/department/program targeting required
- `Employee Allowance`: `employee` required
- `Department Pool`: `department` required
- `Program Pool`: `program` required
- `Hybrid`: pool may optionally target employee, department, or program

## Professional Development Request

`Professional Development Request` is the mandatory staging object.

Locked identity and linkage fields:

- `employee`
- `organization`
- `school`
- `academic_year`
- `professional_development_budget`
- `professional_development_theme`
- `pgp_plan`
- `pgp_goal`

Locked intent fields:

- `title`
- `professional_development_type`
- `provider_name`
- `location`
- `start_datetime`
- `end_datetime`
- `absence_days`
- `requires_substitute`
- `learning_outcomes`
- `sharing_commitment`

Locked system fields:

- `status`
- `estimated_total`
- `validation_status`
- `budget_snapshot_json`
- `validation_snapshot_json`
- `requires_override`
- `override_approved`
- `override_reason`
- `override_by`
- `override_on`
- `submitted_by`
- `submitted_on`
- `decision_by`
- `decision_on`
- `professional_development_record`
- `professional_development_encumbrance`

Request statuses:

- `Draft`
- `Submitted`
- `Under Review`
- `Approved`
- `Rejected`
- `Cancelled`

Request invariants:

- `estimated_total` is derived from `Professional Development Request Cost`
- duplicate active requests are blocked for the same `(employee, academic_year, title, start_datetime)`
- gate statuses (`Submitted`, `Under Review`, `Approved`) must carry frozen budget and validation snapshots
- if the frozen validation snapshot is blocked, `override_reason` and `override_approved` are required before approval
- approval never edits committed truth in place; it materializes record, reservation, and availability

## Professional Development Record

`Professional Development Record` is the committed operational truth created from an approved request.

Locked fields:

- `professional_development_request`
- `employee`
- `organization`
- `school`
- `academic_year`
- `professional_development_budget`
- `professional_development_theme`
- `title`
- `professional_development_type`
- `provider_name`
- `location`
- `start_datetime`
- `end_datetime`
- `estimated_total`
- `status`
- `employee_booking`
- `professional_development_encumbrance`
- `professional_development_outcome`
- `actual_total`

Record statuses:

- `Planned`
- `Attended`
- `Completed`
- `Cancelled`
- `Liquidated`

Record invariants:

- approval creates or updates exactly one record per request
- approved/planned records materialize one blocking `Employee Booking`
- cancelling a planned/completed record releases booking and budget reservation
- liquidation is terminal for Phase 1

## Professional Development Outcome

`Professional Development Outcome` captures completion evidence and actual spend.

Locked fields:

- `professional_development_record`
- `employee`
- `organization`
- `school`
- `academic_year`
- `completion_date`
- `reflection`
- `actual_total`
- `liquidation_ready`

Evidence is stored in `Professional Development Outcome Evidence`.

## Professional Development Encumbrance

`Professional Development Encumbrance` is the PD-scoped accounting companion.

Locked fields:

- `organization`
- `school`
- `academic_year`
- `professional_development_budget`
- `professional_development_request`
- `professional_development_record`
- `posting_date`
- `liquidation_date`
- `fiscal_year`
- `liquidation_fiscal_year`
- `encumbrance_account`
- `expense_account`
- `clearing_account`
- `encumbered_amount`
- `liquidated_amount`
- `released_amount`
- `variance_amount`
- `status`

Statuses:

- `Draft`
- `Reserved`
- `Released`
- `Liquidated`

Accounting invariants:

- reserve validates posting date against `Fiscal Year`, `Accounts Settings.lock_until_date`, and `Accounting Period`
- reserve posts balanced GL entries with `organization` and `school` dimensions
- release reverses only the reserve voucher
- liquidation reverses reserve first, then posts actual expense separately
- this is a PD-scoped finance slice, not a generic accounting budget engine

## Employee Booking Integration

PD does not create `Leave Application`.

Phase 1 uses `Employee Booking` as staff availability truth:

- `booking_type = Professional Development`
- one booking per committed record
- overlap validation uses the canonical employee-booking conflict helper
- cancellation removes the booking deterministically by source reference

## Portal / SPA Contract

Staff portal uses one bounded bootstrap endpoint for `My Growth`.

Phase 1 board payload includes:

- current viewer
- active requests
- upcoming and open records
- completion backlog
- requestable themes and budgets in scope
- expiring items only when Phase 1 data actually exists
- summary metrics for:
  - open requests
  - upcoming PD
  - completion backlog
  - available personal/scope budget preview

Mutation endpoints are domain-specific:

- submit request
- decide request
- cancel request
- complete record
- liquidate record

## Permissions and Tenancy Model

Server-side scope is mandatory.

### Scoped administrative roles

- `System Manager`
- `HR Manager`
- `HR User`
- `Academic Admin`

### Finance visibility role

- `Accounts Manager`
- `Accounts User`

### Employee self-service

- employees may create and manage only their own PD requests and outcomes through the portal/API contract
- employees may read only their own request/record/outcome documents
- sibling-school visibility is forbidden

Organization scope and school-tree scope must both pass when a document is school-scoped.

## Academic Year Closure Contract

Phase 1 forbids silent carryover.

Open PD documents at year close must be handled explicitly according to `HR Settings.pd_year_close_policy`:

- `Cancel Open Requests`: cancel open requests and open records for the target AY scope
- `Require Manual Carry Forward`: block silent closure and require explicit roll-forward action before archival

Archiving the academic year must not silently preserve open PD operational truth.

## Phase 1 Non-Negotiables

- no direct write from request into final PD truth without approval
- no silent retroactive edits to frozen validation or budget snapshots
- no leave-domain overload for PD absence
- no generic cost-center abstraction
- no global cross-school visibility
