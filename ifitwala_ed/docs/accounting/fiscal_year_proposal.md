# Ifitwala Ed — Fiscal Year Proposal

This document proposes how Ifitwala Ed should introduce `Fiscal Year` as the legal accounting-year authority while preserving the existing separation between education operations and finance operations.

---

## 1. Problem Statement

Status: Proposed
Code refs: `ifitwala_ed/accounting/ledger_utils.py`, `ifitwala_ed/accounting/doctype/accounting_period/accounting_period.json`, `ifitwala_ed/accounting/doctype/accounts_settings/accounts_settings.json`, `ifitwala_ed/docs/accounting/accounting_notes.md`, `ifitwala_ed/docs/enrollment/academic_year_architecture.md`
Test refs: `ifitwala_ed/accounting/doctype/sales_invoice/test_sales_invoice.py`, `ifitwala_ed/accounting/doctype/payment_entry/test_payment_entry.py`, `ifitwala_ed/accounting/doctype/payment_reconciliation/test_payment_reconciliation.py`, `ifitwala_ed/accounting/doctype/journal_entry/test_journal_entry.py`

Current repo state:

- `Academic Year` is the institutional time container for enrollment, scheduling, reporting cycles, and academic closure.
- `Accounting Period` already exists and is used as a date-bounded transaction lock surface.
- `Accounts Settings.lock_until_date` adds an organization-wide posting lock date.
- No `Fiscal Year` DocType currently exists in the workspace.
- Current accounting validation accepts a posting date if it is not locked; it does not resolve or enforce a legal accounting year.

This is the contract gap:

- educational operations are already dissociated from academic year,
- but accounting still lacks an explicit fiscal-year authority for legal reporting, defaults, and period governance.

---

## 2. ERPNext Reference Contract

Status: Proposed
Code refs: `https://raw.githubusercontent.com/frappe/erpnext/develop/erpnext/accounts/doctype/fiscal_year/fiscal_year.json`, `https://raw.githubusercontent.com/frappe/erpnext/develop/erpnext/accounts/doctype/fiscal_year/fiscal_year.py`, `https://raw.githubusercontent.com/frappe/erpnext/develop/erpnext/accounts/doctype/fiscal_year_company/fiscal_year_company.json`, `https://raw.githubusercontent.com/frappe/erpnext/develop/erpnext/accounts/utils.py`, `https://raw.githubusercontent.com/frappe/erpnext/develop/erpnext/accounts/doctype/accounting_period/accounting_period.json`
Test refs: None

ERPNext v16 distinguishes the concepts as follows:

- `Fiscal Year` is a setup authority with:
  - year name
  - start date
  - end date
  - disabled flag
  - short/long year support
  - company scoping via child rows
- fiscal-year overlap is validated against the company scope, not just globally by date
- fiscal years are cached and resolved by `company + transaction date`
- `Accounting Period` remains a narrower transaction-control layer with:
  - company
  - start/end dates
  - disabled flag
  - per-document closing behavior
  - optional exempted role

ERPNext therefore treats:

- fiscal year = accounting-year authority
- accounting period = transaction restriction/closing window

This proposal mirrors that separation for Ifitwala Ed.

---

## 3. Proposed Contract for Ifitwala Ed

Status: Proposed
Code refs: `ifitwala_ed/accounting/ledger_utils.py`, `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`, `ifitwala_ed/accounting/doctype/payment_entry/payment_entry.py`, `ifitwala_ed/accounting/doctype/payment_reconciliation/payment_reconciliation.py`, `ifitwala_ed/accounting/doctype/journal_entry/journal_entry.py`, `ifitwala_ed/accounting/report/general_ledger/general_ledger.py`, `ifitwala_ed/accounting/report/trial_balance/trial_balance.py`, `ifitwala_ed/accounting/report/account_holder_statement/account_holder_statement.py`, `ifitwala_ed/accounting/report/aged_receivables/aged_receivables.py`, `ifitwala_ed/accounting/report/student_attribution/student_attribution.py`
Test refs: None

### 3.1 Time-domain authority

The system must recognize three distinct time domains:

1. `Academic Year`
   - school-scoped educational container
   - drives enrollment, scheduling, attendance, and assessment/reporting workflows

2. `Fiscal Year`
   - organization-scoped legal accounting year
   - drives posting validity, financial statements, and accounting defaults/reporting shortcuts

3. `Accounting Period`
   - organization-scoped transaction control layer inside the accounting domain
   - used for partial closing/locking of posting windows

`Academic Year` must never be used to infer accounting legality.

### 3.2 New setup object

Introduce a new setup DocType:

- `Fiscal Year`

Proposed minimum fields, modeled on ERPNext:

- `year` / fiscal year label
- `year_start_date`
- `year_end_date`
- `disabled`
- `is_short_year`
- `auto_created` if automatic carry-forward is later approved
- organization-scoping child table, ERPNext-style, using `Organization` instead of `Company`

Proposal choice:

- require explicit organization scoping rows in Ifitwala Ed instead of allowing implicit tenant-global fiscal years

Reason:

- Ifitwala Ed is multi-tenant and permission-sensitive
- explicit legal-entity scope is safer than silent global applicability

### 3.3 Posting validation

For every accounting document with `organization + posting_date`, the server must resolve exactly one active fiscal year.

Applies to:

- `Sales Invoice`
- `Payment Entry`
- `Payment Reconciliation`
- `Journal Entry`
- any later accounting voucher with legal posting effect

Validation contract:

- if no active fiscal year matches the posting date for the organization, block submission/save where posting legality is enforced
- if multiple active fiscal years overlap for the same organization scope, block setup and require correction
- after fiscal-year validation passes, existing `lock_until_date` and `Accounting Period` checks still apply

Ordering:

1. resolve fiscal year
2. check hard organization lock date
3. check closed accounting period

### 3.4 Reporting contract

Accounting reports should support fiscal-year shortcuts in addition to explicit date ranges.

Affected reports:

- General Ledger
- Trial Balance
- Account Holder Statement
- Aged Receivables
- Student Attribution

Report behavior:

- selecting a fiscal year resolves a concrete date range from `year_start_date` to `year_end_date`
- manual `from_date` / `to_date` remains supported
- academic-year filters, where present on educational reports, remain independent and must not be re-used for finance reports

### 3.5 Current `Accounting Period`

Current `Accounting Period` should be retained, not replaced.

Proposed role after fiscal year is introduced:

- keep it as the transaction restriction surface
- continue to validate date overlap per organization
- optionally evolve later toward ERPNext-style document-specific closure if explicitly approved

This proposal does not require `Accounting Period` to become the fiscal-year master.

---

## 4. Contract Matrix

Status: Proposed
Code refs: `ifitwala_ed/accounting/doctype/accounting_period/accounting_period.json`, `ifitwala_ed/accounting/ledger_utils.py`, `ifitwala_ed/accounting/report/general_ledger/general_ledger.py`, `ifitwala_ed/docs/accounting/accounting_notes.md`, `ifitwala_ed/docs/enrollment/academic_year_architecture.md`
Test refs: `ifitwala_ed/accounting/doctype/sales_invoice/test_sales_invoice.py`, `ifitwala_ed/accounting/doctype/payment_entry/test_payment_entry.py`, `ifitwala_ed/accounting/doctype/payment_reconciliation/test_payment_reconciliation.py`, `ifitwala_ed/accounting/doctype/journal_entry/test_journal_entry.py`

| Surface | Current State | Proposed State | Status |
| --- | --- | --- | --- |
| Schema / DocType | `Accounting Period` exists; no `Fiscal Year` DocType exists | Add `Fiscal Year` plus organization-scoping child table; retain `Accounting Period` | Planned |
| Controller / Workflow logic | `validate_posting_date()` checks `lock_until_date` and closed accounting periods only | Resolve active fiscal year first, then apply existing lock checks | Planned |
| API endpoints | no dedicated fiscal-year resolution helper in app accounting layer | add shared fiscal-year resolver/helper for accounting validators and reports | Planned |
| SPA / Desk surfaces | users enter `posting_date`; no fiscal-year setup or chooser | add Desk setup for fiscal years and fiscal-year report shortcuts; no academic-year leakage into finance forms | Planned |
| Reports / Dashboards / Briefings | accounting reports rely on explicit date filters | add fiscal-year quick filters resolving to date ranges | Planned |
| Scheduler / background jobs | none for fiscal-year lifecycle | optional later auto-create next fiscal year, only if explicitly approved | Planned |
| Tests | accounting tests exercise posting dates and lock behavior without fiscal-year assertions | add fiscal-year overlap, missing-year, report filter, and posting-validator regressions | Planned |
| Docs | docs acknowledge `Accounting Period`; fiscal-year contract absent | docs explicitly separate academic year, fiscal year, and accounting period | Planned |

Unknown rows: None

---

## 5. Rationale Before Behavior Change

Status: Proposed
Code refs: `ifitwala_ed/docs/accounting/accounting_notes.md`, `ifitwala_ed/docs/enrollment/academic_year_architecture.md`
Test refs: None

Pros

- matches ERPNext's accounting model closely enough to reduce conceptual drift
- gives finance users a legal-year authority separate from school-year operations
- keeps current `Accounting Period` investment intact
- improves report ergonomics without forcing academic-year logic into finance

Cons

- adds one more setup object for finance teams
- requires migration/backfill decisions for organizations with historical postings
- creates a temporary mixed state until validators and reports are updated

Blind spots

- this proposal does not yet define a book-closing voucher workflow
- this proposal does not yet define whether fiscal year should be stored as an immutable snapshot on vouchers and GL Entry
- this proposal does not yet define auto-creation policy for next fiscal year

Risks

- historical data may exist outside any newly configured fiscal year
- overlap mistakes in setup can create ambiguous posting validity if not blocked hard
- report parity can drift if some reports add fiscal-year shortcuts and others do not

---

## 6. Proposed Implementation Sequence

Status: Proposed
Code refs: `ifitwala_ed/accounting/ledger_utils.py`, `ifitwala_ed/accounting/report/general_ledger/general_ledger.py`, `ifitwala_ed/accounting/report/trial_balance/trial_balance.py`
Test refs: None

1. Add `Fiscal Year` schema and organization scope rows.
2. Add a shared resolver utility for `organization + posting_date -> fiscal year`.
3. Update posting validators to require a matching active fiscal year before lock checks.
4. Add Desk/report filters for fiscal year on finance reports.
5. Add regression tests for setup overlap, posting rejection, and report filter expansion.

Non-goal for this proposal:

- no academic object should be renamed or repurposed
- no accounting correctness should rely on client-side defaults
- no silent inference from `Academic Year`
