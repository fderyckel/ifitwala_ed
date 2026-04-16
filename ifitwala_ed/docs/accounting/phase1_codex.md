# Ifitwala Ed — Phase 1 Execution Companion

## Status

Implemented companion note
Canonical contract: `ifitwala_ed/docs/accounting/phase1_notes.md`

This file is a file-map and implementation checklist for the Phase 1 billing architecture. It does not override the canonical contract.

## 1. Core File Map

### Billing plan setup

- `ifitwala_ed/accounting/doctype/program_billing_plan/program_billing_plan.json`
- `ifitwala_ed/accounting/doctype/program_billing_plan/program_billing_plan.py`
- `ifitwala_ed/accounting/doctype/program_billing_plan/program_billing_plan.js`
- `ifitwala_ed/accounting/doctype/program_billing_plan_component/program_billing_plan_component.json`

### Derived billing state

- `ifitwala_ed/accounting/doctype/billing_schedule/billing_schedule.json`
- `ifitwala_ed/accounting/doctype/billing_schedule/billing_schedule.py`
- `ifitwala_ed/accounting/doctype/billing_schedule/billing_schedule.js`
- `ifitwala_ed/accounting/doctype/billing_schedule_row/billing_schedule_row.json`

### Batch control

- `ifitwala_ed/accounting/doctype/billing_run/billing_run.json`
- `ifitwala_ed/accounting/doctype/billing_run/billing_run.py`
- `ifitwala_ed/accounting/doctype/billing_run/billing_run.js`
- `ifitwala_ed/accounting/doctype/billing_run_item/billing_run_item.json`

### Services

- `ifitwala_ed/accounting/billing/schedule_generation.py`
- `ifitwala_ed/accounting/billing/invoice_generation.py`

### Existing accounting reuse

- `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`
- `ifitwala_ed/accounting/receivables.py`
- `ifitwala_ed/accounting/test_support.py`

## 2. Locked Implementation Decisions

- `Billable Offering` remains the global fee/accounting catalog.
- `Program Billing Plan Component.default_rate` is the approved program-local price source for bulk generation.
- `Billing Schedule` is derived from `Program Enrollment`; it is not manually curated as a second enrollment ledger.
- `Billing Run` is the operator-facing batch object for “generate all draft invoices for this program”.
- Generated invoices are grouped by `Account Holder + period_key`.
- Generated invoices remain draft and still pass the normal `Sales Invoice` validation path.

## 3. Required User-Facing Actions

- On `Program Billing Plan`: `Generate Billing Schedules`
- On `Billing Schedule`: `Generate Draft Invoice`
- On `Billing Run`: `Generate Draft Invoices`

No CLI-only workflow is acceptable for the normal accounting path.

## 4. Required Integrity Hooks

- Schedule generation must be idempotent for pending rows.
- Billing-run generation must skip rows already linked to a `Sales Invoice`.
- `Sales Invoice.on_cancel` must reset linked billing rows.
- Deleting a generated draft invoice must also reset linked billing rows.

## 5. Minimum Test Coverage

- duplicate active billing plan is blocked
- schedule generation derives rows from enrollment and cadence
- bulk run groups sibling students on one invoice when they share an `Account Holder`
- invoice cancel resets billing rows to `Pending`

## 6. Explicit Non-Goals

- no global pricing engine
- no automatic invoice submission
- no GL outside `Sales Invoice`
- no account mapping on billing-plan components
