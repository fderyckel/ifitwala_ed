# Ifitwala Ed Finance Note: Full Fee Cycle

This note describes the fee workflow that is present in the current workspace. It is written for school finance teams, so it separates what is implemented now from what is only documented as a future billing design.

## 1. Operating Model

Status: Implemented
Code refs: `ifitwala_ed/docs/accounting/accounting_notes.md`, `ifitwala_ed/accounting/doctype/account_holder/account_holder.json`, `ifitwala_ed/students/doctype/student/student.json`
Test refs: `ifitwala_ed/accounting/doctype/sales_invoice/test_sales_invoice.py`, `ifitwala_ed/accounting/doctype/payment_entry/test_payment_entry.py`, `ifitwala_ed/accounting/doctype/payment_reconciliation/test_payment_reconciliation.py`

The payer in Ifitwala Ed is the `Account Holder`, not the student. This is the central accounting rule.

- `Organization` is the legal accounting entity.
- `School` is operational context; it is not the debtor.
- `Student` is the beneficiary and is used for line attribution and reporting.
- `Account Holder` is the legal debtor. One account holder can pay for one or more students.

Practical meaning for finance:

- Invoices are raised to the `Account Holder`.
- Payments are received from the `Account Holder`.
- Outstanding balances, advances, and statements are tracked per `Account Holder`.
- Students should appear on invoice lines when the charge relates to a specific student, but students are not the A/R party.

Important clarification: there is no dedicated `Fee Category` DocType in the current workspace. The closest live setup objects are:

- `Billable Offering` for the chargeable item itself
- `Tax Category` for tax classification
- `Sales Taxes and Charges Template` for actual tax rows

## 2. Fee Setup Before Billing

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/accounts_settings/accounts_settings.json`, `ifitwala_ed/accounting/doctype/billable_offering/billable_offering.json`, `ifitwala_ed/accounting/doctype/billable_offering/billable_offering.py`, `ifitwala_ed/accounting/doctype/tax_category/tax_category.json`, `ifitwala_ed/accounting/doctype/sales_taxes_and_charges_template/sales_taxes_and_charges_template.json`, `ifitwala_ed/accounting/doctype/payment_terms_template/payment_terms_template.json`
Test refs: `ifitwala_ed/accounting/doctype/sales_invoice/test_sales_invoice.py`, `ifitwala_ed/accounting/doctype/payment_request/test_payment_request.py`

Before a school can charge families, finance needs the accounting setup in place.

### 2.1 Organization accounting settings

Each organization needs `Accounts Settings` with at least:

- default receivable account
- default advance / unearned revenue account
- optionally default cash and bank accounts
- optionally default tax payable account
- optionally a lock-until date for accounting periods

These defaults drive posting and payment behavior.

Current accounting-year status:

- the live workspace does not yet define a dedicated `Fiscal Year` DocType
- posting legality is currently enforced by `posting_date`, `Accounts Settings.lock_until_date`, and closed `Accounting Period` ranges
- the planned direction is to add `Fiscal Year` above those controls so finance can manage legal accounting years independently of `Academic Year`

### 2.2 Create the payer record

Create an `Account Holder` for the person or entity that will be invoiced. The record stores:

- organization
- account holder name
- holder type
- status
- primary email / phone

Then make sure the relevant `Student` record links to that same `Account Holder`.

### 2.3 Create the charge definitions

Fees are configured as `Billable Offering` records. This is the live fee catalog.

Each billable offering defines:

- organization
- offering type: `Program`, `Service Subscription`, `One-off Fee`, or `Product`
- optional linked type/reference
- default income account
- optional tax category
- pricing mode: `Fixed`, `Per Term`, `Per Unit`, or `Subscription`

If a school wants separate fee buckets such as tuition, registration, trip, lunch, or bus, that is done by creating separate `Billable Offering` records. The system does not currently provide a separate fee-head or fee-category master.

### 2.4 Configure tax treatment

If tax applies:

1. Create a `Tax Category` if needed.
2. Create a `Sales Taxes and Charges Template` for the organization.
3. Add the tax rows to that template.
4. Select the template on the invoice when billing.

### 2.5 Configure payment timing

If the school wants installments rather than one due date, finance can create a `Payment Terms Template`.

Each template defines:

- term name
- invoice portion %
- due days after invoice date

When selected on a `Sales Invoice`, the template generates the invoice payment schedule automatically.

## 3. Creating and Issuing the Invoice

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.json`, `ifitwala_ed/accounting/doctype/sales_invoice_item/sales_invoice_item.json`, `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`, `ifitwala_ed/accounting/doctype/sales_invoice_payment_schedule/sales_invoice_payment_schedule.json`, `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`, `ifitwala_ed/api/activity_booking.py`
Test refs: `ifitwala_ed/accounting/doctype/sales_invoice/test_sales_invoice.py`

The live billing document is `Sales Invoice`.

### 3.1 What finance enters on the invoice header

At minimum:

- `Account Holder`
- `Organization`
- `Posting Date`

Important separation:

- `Posting Date` is accounting time and must eventually resolve through `Fiscal Year` + `Accounting Period`
- `Program Offering` and student context are academic/billing context and must not be used as fiscal-year proxies

Optional but important:

- `Due Date`
- `Payment Terms Template`
- `Program Offering` when the invoice is tied to a specific program/activity context
- `Tax Template`
- remarks

### 3.2 What finance enters on each invoice line

Each `Sales Invoice Item` can contain:

- `Billable Offering`
- optional `Program Offering`
- read-only `School` / `Program` analytics context
- `Charge Source`: `Program Offering`, `Extra`, or `Manual`
- description
- optional student
- qty
- rate
- income account

How this works in practice:

- Tuition/program lines normally use `Charge Source = Program Offering`.
- Add-on charges such as extras can use `Charge Source = Extra`.
- Fully manual lines can use `Charge Source = Manual`, but then finance must provide the income account directly.

### 3.3 Validations finance will hit

On save/submit, the server enforces the accounting rules:

- the account holder must belong to the same organization as the invoice
- any program offering on the invoice or line must belong to the same organization
- a `Program Offering` charge requires program context
- the billable offering must belong to the same organization and cannot be disabled
- for `Program` billable offerings, a student is required on the line
- the student must belong to the same organization
- the student account holder must match the invoice account holder
- the income account must belong to the organization and must be a real posting income account

### 3.4 What happens when the invoice is submitted

Submission posts GL entries:

- Debit `Accounts Receivable` against the `Account Holder`
- Credit income accounts per line
- Credit tax liability if tax applies

The invoice becomes the formal receivable and `outstanding_amount` is set from the grand total.

Additional runtime behavior now supported:

- invoice `status` is maintained automatically
- installment schedules are generated from payment terms
- school/program/student dimensions are written through for analytics
- credit notes and debit notes can be created from the invoice form

### 3.5 How the payer is actually invoiced

In the current workspace, invoicing is Desk-first.

- Finance creates the `Sales Invoice` in Desk.
- The document supports standard print/email actions through Desk permissions.
- Finance can create a linked `Payment Request` directly from the invoice.
- Finance can create linked `Credit Note` and `Debit Note` drafts directly from the invoice.

There is one implemented server-side draft-invoice shortcut: paid activity booking can create a draft tuition invoice tied to a `Program Offering`. That is a specific workflow, not the general school-fee engine.

## 4. Receiving Payment

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/payment_entry/payment_entry.json`, `ifitwala_ed/accounting/doctype/payment_entry/payment_entry.py`
Test refs: `ifitwala_ed/accounting/doctype/payment_entry/test_payment_entry.py`

Payments are recorded through `Payment Entry`.

Finance enters:

- organization
- account holder (`party`)
- posting date
- cash/bank account in `Paid To`
- paid amount
- optional invoice references
- remarks

What the system does:

- checks the payment belongs to the same organization as the account holder
- checks referenced invoices are submitted
- checks referenced invoices belong to the same account holder
- blocks allocations above invoice outstanding
- blocks total allocations above paid amount
- updates invoice payment schedules and invoice status after allocation
- keeps `unallocated_amount` precision-safe instead of leaving rounding residue on the receipt

Posting result on submit:

- Debit bank/cash
- Credit A/R for allocated amounts
- Credit advance liability for any unallocated remainder

That means overpayments and prepayments are not lost. They stay as advance/unearned amounts instead of creating a negative receivable.

## 5. Applying Advances Later

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/payment_reconciliation/payment_reconciliation.json`, `ifitwala_ed/accounting/doctype/payment_reconciliation/payment_reconciliation.py`
Test refs: `ifitwala_ed/accounting/doctype/payment_reconciliation/test_payment_reconciliation.py`

If a family paid before an invoice existed, or overpaid earlier, finance uses `Payment Reconciliation`.

This document:

- selects the organization and account holder
- lists allocations to submitted invoices
- requires the finance user to choose the source `Payment Entry` for each allocation
- checks there is enough available advance balance
- reduces invoice outstanding amounts
- consumes the stored advance balance from the selected payment entries

Accounting effect on submit:

- Debit advance liability
- Credit A/R

Operationally, this is the step that turns an existing credit balance into settlement of a real invoice.

## 6. Follow-Up and Collections

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/payment_request/payment_request.json`, `ifitwala_ed/accounting/doctype/dunning_notice/dunning_notice.json`, `ifitwala_ed/accounting/doctype/statement_of_accounts_run/statement_of_accounts_run.json`, `ifitwala_ed/accounting/report/aged_receivables/aged_receivables.py`, `ifitwala_ed/accounting/report/account_holder_statement/account_holder_statement.py`, `ifitwala_ed/accounting/report/student_attribution/student_attribution.py`, `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice_list.js`
Test refs: `ifitwala_ed/accounting/doctype/payment_request/test_payment_request.py`, `ifitwala_ed/accounting/doctype/dunning_notice/test_dunning_notice.py`, `ifitwala_ed/accounting/doctype/statement_of_accounts_run/test_statement_of_accounts_run.py`

The follow-up layer now combines reports with dedicated Desk workflow objects.

### 6.1 Main follow-up tools available now

- `Aged Receivables`: shows open submitted invoices with aging buckets
- `Account Holder Statement`: shows the running GL balance for the payer
- `Student Attribution`: shows which student/billable offering each submitted invoice line relates to
- `Sales Invoice` list filters and invoice drill-down for individual cases
- `Payment Request`: tracks invoice-level payment outreach
- `Dunning Notice`: groups overdue invoices into a collection notice
- `Statement Of Accounts Run`: creates a finance work queue for statement processing

### 6.2 What finance can do with those tools

- identify overdue invoices by account holder
- create and track payment requests from invoices or dunning notices
- prepare dunning batches for overdue balances
- process statement runs for one or many account holders
- send statements or copies of invoices manually
- see sibling/family balances at the payer level
- understand which student or offering caused the charge

### 6.3 What is not implemented as a dedicated workflow

I did not find a custom finance collection workflow for:

- automated reminder cadences
- promise-to-pay tracking
- dispute/follow-up tasking
- parent-facing fee statement/payment portal for general school billing

So the follow-up process today is best understood as:

1. raise invoice
2. monitor open balances through reports
3. contact payer manually using the invoice/statement outputs
4. record payment or apply advance when money arrives

## 7. Current End-to-End Fee Cycle

Status: Implemented
Code refs: `ifitwala_ed/accounting/doctype/billable_offering/billable_offering.json`, `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`, `ifitwala_ed/accounting/doctype/payment_entry/payment_entry.py`, `ifitwala_ed/accounting/doctype/payment_reconciliation/payment_reconciliation.py`, `ifitwala_ed/accounting/doctype/payment_request/payment_request.py`, `ifitwala_ed/accounting/doctype/dunning_notice/dunning_notice.py`, `ifitwala_ed/accounting/doctype/statement_of_accounts_run/statement_of_accounts_run.py`
Test refs: `ifitwala_ed/accounting/doctype/sales_invoice/test_sales_invoice.py`, `ifitwala_ed/accounting/doctype/payment_entry/test_payment_entry.py`, `ifitwala_ed/accounting/doctype/payment_reconciliation/test_payment_reconciliation.py`, `ifitwala_ed/accounting/doctype/payment_request/test_payment_request.py`, `ifitwala_ed/accounting/doctype/dunning_notice/test_dunning_notice.py`, `ifitwala_ed/accounting/doctype/statement_of_accounts_run/test_statement_of_accounts_run.py`

For a school finance team, the current full cycle is:

1. Set up the organization’s accounting defaults.
2. Create the `Account Holder` who will legally pay.
3. Link the student to that account holder.
4. Create `Billable Offering` records for each fee type the school charges.
5. Create tax categories/templates if tax is needed.
6. Create a `Payment Terms Template` if the fee should be paid in installments.
7. Create a `Sales Invoice` to the account holder.
8. Add line items for the relevant student and billable offering.
9. Submit the invoice so the receivable posts to the ledger.
10. Create a `Payment Request`, `Dunning Notice`, or `Statement Of Accounts Run` when finance starts follow-up.
11. Monitor outstanding balances through `Aged Receivables`, `Account Holder Statement`, and invoice status.
12. Record incoming money through `Payment Entry`.
13. If money was received in advance, use `Payment Reconciliation` later to apply it to invoices.
14. If the charge must be reduced or reversed, create a linked `Credit Note` or `Debit Note`.

That is the production fee cycle currently supported in this repository.

## 8. Planned Billing Automation Not Yet Live

Status: Planned
Code refs: `ifitwala_ed/docs/accounting/phase1_notes.md`, `ifitwala_ed/docs/accounting/phase1_codex.md`
Test refs: None

The repository also contains a Phase 1 billing design, but it is not the current live workflow.

Planned objects include:

- `Program Billing Plan`
- `Billing Schedule`
- deterministic draft invoice generation from billing schedules

That planned design would make recurring tuition billing more structured, but finance should not assume those objects or automations are available until the corresponding code exists.

## 9. Contract Matrix

Status: Implemented for current fee cycle; Planned for schedule-based automation
Code refs: `ifitwala_ed/accounting/doctype/billable_offering/billable_offering.json`, `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`, `ifitwala_ed/accounting/doctype/payment_entry/payment_entry.py`, `ifitwala_ed/accounting/doctype/payment_reconciliation/payment_reconciliation.py`, `ifitwala_ed/accounting/report/aged_receivables/aged_receivables.py`, `ifitwala_ed/docs/accounting/phase1_notes.md`
Test refs: `ifitwala_ed/accounting/doctype/sales_invoice/test_sales_invoice.py`, `ifitwala_ed/accounting/doctype/payment_entry/test_payment_entry.py`, `ifitwala_ed/accounting/doctype/payment_reconciliation/test_payment_reconciliation.py`

| Area | Current state | Canonical object/path |
| --- | --- | --- |
| Fee catalog / setup | Implemented | `Billable Offering` |
| Payer master | Implemented | `Account Holder` |
| Student linkage | Implemented | `Student.account_holder` |
| Tax grouping | Implemented | `Tax Category` + `Sales Taxes and Charges Template` |
| Invoice document | Implemented | `Sales Invoice` |
| Installment schedules | Implemented | `Payment Terms Template` + `Sales Invoice Payment Schedule` |
| Invoice line attribution | Implemented | `Sales Invoice Item` |
| Invoice collection status | Implemented | `Sales Invoice.status` |
| Receipt entry | Implemented | `Payment Entry` |
| Advance application | Implemented | `Payment Reconciliation` |
| Payment requests | Implemented | `Payment Request` |
| Dunning workflow | Implemented | `Dunning Notice` |
| Statement processing run | Implemented | `Statement Of Accounts Run` |
| Follow-up reporting | Implemented | Aged receivables, statements, student attribution |
| Automated fee schedule / recurring billing engine | Planned | `phase1_notes.md` design only |
| Automated multi-channel collections dispatch | Not found in current workspace | None |
