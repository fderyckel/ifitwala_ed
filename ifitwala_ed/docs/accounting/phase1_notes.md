# Ifitwala Ed — Accounting Phase 1 Notes

## Status

Implemented
Code refs: `ifitwala_ed/accounting/doctype/program_billing_plan/program_billing_plan.py`, `ifitwala_ed/accounting/doctype/billing_schedule/billing_schedule.py`, `ifitwala_ed/accounting/doctype/billing_run/billing_run.py`, `ifitwala_ed/accounting/billing/schedule_generation.py`, `ifitwala_ed/accounting/billing/invoice_generation.py`, `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`
Test refs: `ifitwala_ed/accounting/doctype/program_billing_plan/test_program_billing_plan.py`, `ifitwala_ed/accounting/doctype/billing_schedule/test_billing_schedule.py`, `ifitwala_ed/accounting/doctype/billing_run/test_billing_run.py`

## 0. Objective

Phase 1 adds structured billing for program-based education charges without creating a parallel accounting system.

By the end of Phase 1, the system must answer:

- what should be billed for this `Program Offering`
- which enrolled students are in scope
- which draft invoices were generated for which `Account Holder`
- which billing rows are still pending versus already linked to an invoice

Phase 1 does not move any GL logic outside `Sales Invoice`.

## 1. Canonical Split (Non-Duplication Rule)

| Object | Role | Must not own |
| --- | --- | --- |
| `Billable Offering` | Fee catalog and accounting mapping for one charge type | program-specific enrollment roster, batch state |
| `Program Billing Plan` | Program-specific billing structure for one `Program Offering` + `Academic Year` | tax posting logic, debtor balances |
| `Billing Schedule` | Derived per-enrollment billing state | ledger posting, payment allocation |
| `Billing Run` | Batch control for “generate all draft invoices for this program/period” | fee catalog setup, manual A/R settlement |
| `Sales Invoice` | Legal accounting document and only GL-posting billing document | enrollment-derived schedule generation |

Locked interpretation:

- `Billable Offering` remains the only master that defines income-account and tax-category defaults.
- `Program Billing Plan Component` may store a plan-local `default_rate`; this is allowed because it is program-specific pricing, not a global catalog price.
- `Payment Terms Template` remains the only installment engine. Phase 1 reuses it on generated invoices instead of rebuilding payment schedules elsewhere.

## 2. Existing Objects Reused

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/billable_offering/billable_offering.json`, `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`, `ifitwala_ed/accounting/receivables.py`, `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.json`, `ifitwala_ed/schedule/doctype/program_offering/program_offering.json`
Test refs: `ifitwala_ed/accounting/doctype/sales_invoice/test_sales_invoice.py`

- `Account Holder` remains the legal debtor.
- `Student` remains analytic and line-level attribution only.
- `Program Enrollment` remains the source of truth for who is enrolled in a `Program Offering`.
- `Sales Invoice` and `Sales Invoice Item` remain the billing document model.
- `Payment Terms Template` remains the installment schedule model.

## 3. New Phase 1 Objects

### 3.1 Program Billing Plan

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/program_billing_plan/program_billing_plan.json`, `ifitwala_ed/accounting/doctype/program_billing_plan/program_billing_plan.py`
Test refs: `ifitwala_ed/accounting/doctype/program_billing_plan/test_program_billing_plan.py`

Purpose: define the billable structure for one `Program Offering` in one `Academic Year`.

Minimum fields:

- `organization`
- `program_offering`
- `academic_year`
- `billing_cadence`: `Annual`, `Term`, `Monthly`
- `invoice_grouping_policy`: `One invoice per Account Holder per period`
- `is_active`
- `components`

Rules:

- one active plan per `organization + program_offering + academic_year`
- `program_offering` must resolve to the same `organization`
- `academic_year` must be part of the selected `Program Offering`
- the plan does not post accounting entries

### 3.2 Program Billing Plan Component

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/program_billing_plan_component/program_billing_plan_component.json`
Test refs: `ifitwala_ed/accounting/doctype/program_billing_plan/test_program_billing_plan.py`

Purpose: define one billable component inside the plan.

Fields:

- `billable_offering`
- `qty`
- `default_rate`
- `requires_student`
- `description_override`

Rules:

- `billable_offering.organization` must match the parent plan organization
- `default_rate` is the price source used for bulk draft invoice generation
- `default_rate` is plan-local pricing, not a global fee-catalog price
- `Program` billable offerings must require student attribution

### 3.3 Billing Schedule

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/billing_schedule/billing_schedule.json`, `ifitwala_ed/accounting/doctype/billing_schedule/billing_schedule.py`, `ifitwala_ed/accounting/billing/schedule_generation.py`
Test refs: `ifitwala_ed/accounting/doctype/billing_schedule/test_billing_schedule.py`

Purpose: hold the derived billing state for one `Program Enrollment`.

Header fields:

- `organization`
- `program_enrollment`
- `program_offering`
- `academic_year`
- `billing_plan`
- `student`
- `account_holder`
- `status`
- `rows`

Rules:

- derived from `Program Enrollment`, not manually modeled as an alternative source of truth
- one schedule per `billing_plan + program_enrollment`
- rows may be refreshed from the plan while they are still pending
- linked/invoiced rows are preserved as history

### 3.4 Billing Schedule Row

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/billing_schedule_row/billing_schedule_row.json`
Test refs: `ifitwala_ed/accounting/doctype/billing_schedule/test_billing_schedule.py`, `ifitwala_ed/accounting/doctype/billing_run/test_billing_run.py`

Purpose: represent one component for one billing period for one enrollment.

Fields:

- `plan_component_id`
- `period_key`
- `period_label`
- `billable_offering`
- `qty`
- `rate`
- `requires_student`
- `description`
- `due_date`
- `coverage_start`
- `coverage_end`
- `expected_amount`
- `sales_invoice`
- `billing_run`
- `status`

Rules:

- one row represents one `Program Billing Plan Component x billing period`
- `expected_amount` is informational and derived from `qty x rate`
- rows do not post GL
- `status = Invoiced` means a draft or submitted `Sales Invoice` is already linked and the row must not be regenerated

### 3.5 Billing Run

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/billing_run/billing_run.json`, `ifitwala_ed/accounting/doctype/billing_run/billing_run.py`, `ifitwala_ed/accounting/billing/invoice_generation.py`
Test refs: `ifitwala_ed/accounting/doctype/billing_run/test_billing_run.py`

Purpose: give accounting one explicit batch object for “generate draft invoices for all pending billing rows in this program”.

Fields:

- `organization`
- `program_offering`
- `academic_year`
- `billing_plan`
- `posting_date`
- `due_date_from`
- `due_date_to`
- optional `payment_terms_template`
- `status`
- `processed_on`
- `items`
- read-only run totals

Rules:

- the run resolves exactly one active billing plan
- the run only selects pending schedule rows in the same organization/program/academic-year scope
- the run groups rows by `Account Holder + period_key`
- generated invoices are always draft

### 3.6 Billing Run Item

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/billing_run_item/billing_run_item.json`
Test refs: `ifitwala_ed/accounting/doctype/billing_run/test_billing_run.py`

Purpose: persist the audit trail of invoices created by the run.

Fields:

- `account_holder`
- `period_key`
- `sales_invoice`
- `billing_schedule_count`
- `billing_row_count`
- `grand_total`

## 4. Schedule Generation Rules

Status: Implemented
Code refs: `ifitwala_ed/accounting/billing/schedule_generation.py`
Test refs: `ifitwala_ed/accounting/doctype/billing_schedule/test_billing_schedule.py`

Source of truth:

- generate schedules from `Program Enrollment`
- only enrollments matching the plan `program_offering + academic_year` are in scope
- use `Student.account_holder` to determine the debtor

Cadence rules:

- `Annual`: one period from `Academic Year.year_start_date` to `Academic Year.year_end_date`
- `Term`: one period per `Term` with `term_type = Academic` inside the plan academic year; terms must exist for the offering school or its ancestor scope
- `Monthly`: one period per calendar month segment inside the academic-year date range

Derived-row rules:

- each plan component generates one row per period
- row key = `plan component + period key`
- pending rows are updated in place on schedule refresh
- obsolete pending rows are marked `Cancelled`
- already linked rows are not rewritten

## 5. Invoice Generation Rules

Status: Implemented
Code refs: `ifitwala_ed/accounting/billing/invoice_generation.py`, `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`, `ifitwala_ed/accounting/receivables.py`
Test refs: `ifitwala_ed/accounting/doctype/billing_run/test_billing_run.py`

Single-schedule generation:

- accounting may generate a draft invoice from one `Billing Schedule`
- all selected rows must still be pending

Bulk generation by program:

- accounting creates a `Billing Run`
- the run loads pending schedule rows for the resolved plan
- rows are grouped by `Account Holder + period_key`
- each group creates one draft `Sales Invoice`

Generated invoice behavior:

- `organization`, `account_holder`, and `program_offering` are populated from the schedule/run context
- item rows copy `billable_offering`, `qty`, `rate`, `description`, and student attribution from schedule rows
- `charge_source` is `Program Offering`
- if the run has a `payment_terms_template`, the invoice reuses the existing installment logic in `receivables.py`
- otherwise the invoice `due_date` comes from the billing period row

## 6. Lifecycle And Integrity Rules

Status: Implemented
Code refs: `ifitwala_ed/accounting/billing/invoice_generation.py`, `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`
Test refs: `ifitwala_ed/accounting/doctype/billing_run/test_billing_run.py`

- Cancelling a generated `Sales Invoice` resets linked schedule rows back to `Pending`.
- Deleting a generated draft `Sales Invoice` also resets linked schedule rows.
- Re-running schedule generation does not overwrite linked rows.
- Re-running bulk invoice generation skips already linked rows because the schedule row owns the invoice link.
- All organization checks remain server-side:
  - `Account Holder.organization`
  - `Billable Offering.organization`
  - `Program Offering -> School -> Organization`

## 7. Explicit Prohibitions

- do not add account or tax logic to `Program Billing Plan`
- do not add global price fields to `Billable Offering`
- do not create GL entries from `Billing Schedule` or `Billing Run`
- do not generate student-debtor invoices
- do not bypass `Sales Invoice` validation when generating drafts
- do not collapse multiple billing periods for the same debtor into one invoice unless they share the same `period_key`

## 8. Out Of Scope

Phase 1 still does not include:

- automatic submission of invoices
- online payment gateway settlement
- revenue recognition schedules
- payroll/payables
- inventory or fixed-asset accounting
- family-level “once per account holder” pricing rules outside the per-enrollment model
