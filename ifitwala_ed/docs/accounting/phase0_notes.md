# Ifitwala Ed — Accounting Phase 0 Implementation Plan

> **Scope**: Desk-only (no portal). Double-entry accounting. Accountant-grade correctness.
> **Reference**: `accounting_notes.md` (canonical architecture lock).
> **Method**: Incremental, verifiable steps. Each step must be validated before proceeding.

---

## How to Use This Document

* This plan is designed to be executed **step-by-step by a coding agent**.
* **Do not batch steps**. Each step must be completed, tested, and signed off.
* No UI polish. No portal. Frappe Desk only.
* Every step ends with **clear final outcomes** and **validation scenarios**.

---

## ERPNext v15 Alignment Notes (Locked)

* Baseline ERPNext version: v15 (accounting module only).
* ERPNext Company doctype is used as Organization (same doctype, education naming).
* Account Holder is the education-tailored replacement for ERPNext Customer (legal counterparty).
* Phase 0 explicitly includes ERPNext core accounting doctypes: Account, GL Entry, Journal Entry, Payment Entry.
* Manufacturing / production modules are explicitly out of scope.

---

## ERPNext v15 Doctype Mapping (Phase 0)

| Ifitwala Doctype / Concept | ERPNext v15 Doctype | Notes |
| --- | --- | --- |
| Organization (legal entity) | Company | Same doctype; surfaced as Organization. |
| Accounting Settings (org-level) | Accounts Settings | Org-level defaults. |
| Chart of Accounts Template | Chart of Accounts Importer + Chart template JSON files | Templates live under `erpnext/accounts/doctype/account/chart_of_accounts`. |
| Account | Account | ERPNext account tree. |
| GL Entry | GL Entry | Ledger row. |
| Journal Entry | Journal Entry | Manual accounting entry. |
| Account Holder | Customer | Legal debtor / A/R party. |
| Student Invoice | Sales Invoice | Education-tailored naming. |
| Student Invoice Line | Sales Invoice Item | Invoice line table. |
| Payment Entry | Payment Entry | Receipts and allocations. |
| Payment Allocation | Payment Entry Reference | Invoice allocation rows. |
| Tax Template | Sales Taxes and Charges Template | Sales tax template. |
| Tax Line | Sales Taxes and Charges | Child table for tax lines. |
| Tax Category | Tax Category | Tax classification. |
| Billable Offering | Item + Item Price; Subscription Plan/Subscription (recurring) | Single education abstraction. |
| Accounting Period | Accounting Period | Period locks. |
| Apply Advance Tool | Payment Reconciliation | Manual allocation tool alignment. |

---

## Step 0 — Project Setup & Safety Rails

### Objective

Establish the accounting module structure and ensure architectural guardrails are in place **before any financial logic is written**.

### Deliverables

* `ifitwala_ed/accounting/` module created

  * `doctype/`
  * `utils/`
  * `reports/`
* `accounting_notes.md` committed and treated as canonical
* One Organization-level Accounting Settings doctype (name TBD)

### Final Outcomes

* Accounting module loads cleanly
* No assumptions of single organization
* Central place for org-level accounting defaults exists

### Validation & Checks

* Bench migrate runs cleanly
* Importing `ifitwala_ed.accounting` does not error
* Only System Manager can edit Accounting Settings

### Edge Cases to Test

* Multi-organization site: module loads for each org
* Permissions: non-admin cannot edit accounting settings

---

## Step 1 — Chart of Accounts Skeleton (Organization-first)

### Objective

Create a **minimal but ERPNext-aligned Chart of Accounts** that can support all Phase 0 postings.

### Deliverables

* Account doctype (lean ERPNext-style)
* `GL Entry` doctype (core ledger row)
* `Journal Entry` doctype (manual accounting entry)
* Parent/child account hierarchy
* Account types (Asset, Liability, Income, Expense, Equity)
* Organization-level default accounts:

  * Accounts Receivable
  * Cash
  * Bank
  * Advances / Unearned Revenue (liability)
  * Tax Payable

### Final Outcomes

* Each Organization has its own independent COA
* Posting is impossible to group accounts
* COA is future-safe for payroll, inventory, assets

### Validation & Checks

* Cannot post to group accounts
* Cannot create circular account hierarchies
* Accounts strictly scoped to Organization

### Edge Cases to Test

1. Two organizations with identical account names but different trees
2. Attempt to post using an account from another org
3. Trial Balance on empty ledger returns zeros

---

## Step 2 — Account Holder (Legal Counterparty)

### Objective

Lock the **legal debtor model** used for all receivables and payments.

### Deliverables

* `Account Holder` doctype

  * Organization
  * Account type (Individual / Joint / Organization)
  * Legal / display name
  * Status
* Student ↔ Account Holder relationship

### Final Outcomes

* Every student has **exactly one primary Account Holder**
* One Account Holder can be linked to many students
* All A/R truth is anchored on Account Holder

### Notes

* ERPNext counterpart: Customer (education-tailored naming).
* Student is the beneficiary; Account Holder is the legal debtor.

### Validation & Checks

* Student cannot have two active primary account holders
* Account Holder and Student must belong to same Organization

### Edge Cases to Test

1. One family paying for 3 students
2. Adult learner as own Account Holder
3. Joint Account Holder (two guardians)
4. Attempt to delete Account Holder with downstream links

---

## Step 3 — Tax Baseline (Simple but Real)

### Objective

Support **basic but correct tax handling**, aligned with accounting practice.

### Deliverables

* `Tax Template` doctype

  * Tax lines (rate, account, inclusive flag)
* `Tax Category` doctype
* Offering → Tax Category resolution

### Final Outcomes

* Inclusive and exclusive tax models supported
* Tax amounts post to liability accounts
* No hard-coded tax logic

### Validation & Checks

* Inclusive tax backs out correctly
* Exclusive tax adds correctly
* Tax account must be liability

### Edge Cases to Test

1. Inclusive tax invoice
2. Exclusive tax invoice
3. Multiple tax lines
4. Zero-rated tax category

---

## Step 4 — Billable Offering (Unified Billing Model)

### Objective

Unify all billable items (tuition, services, trips, shop) under one abstraction.

### Deliverables

* `Billable Offering` doctype

  * Offering type
  * Linked reference (Program / Activity / Trip, optional)
  * Default income account
  * Tax category
  * Pricing mode

### Final Outcomes

* No special-casing by pedagogical type
* Every billed line maps cleanly to income and tax

### Validation & Checks

* Income account required and non-group
* Offering org matches account org

### Edge Cases to Test

1. Program tuition offering
2. Lunch per-unit offering
3. Bus subscription offering
4. Trip one-off offering

---

## Step 5 — Student Invoice (Core Billing Document)

### Objective

Create the **primary revenue document** with immutable posting behavior.

### Deliverables

* `Sales Invoice` doctype (education-tailored student invoice)
* Draft → Submit lifecycle
* GL posting on submit

### Final Outcomes

* Submitted invoice posts balanced GL entries
* Invoice becomes immutable after submit
* Student attribution is analytic only

### Validation & Checks

* Dr Accounts Receivable (Account Holder)
* Cr Income accounts (per line)
* Cr Tax Payable

### Edge Cases to Test

1. Multi-line invoice with different offerings
2. Invoice for multiple students
3. Inclusive tax invoice
4. Cancelled invoice reverses GL
5. Back-dated invoice into locked period

---

## Step 6 — Payment Entry (Allocations, Advances)

### Objective

Accept money **without corrupting accounting truth**.

### Deliverables

* `Payment Entry` doctype
* Allocation child table
* Advance (liability) handling

### Final Outcomes

* No negative A/R balances
* Overpayments become liabilities
* Prepayments supported

### Validation & Checks

* Allocations cannot exceed outstanding
* Payments scoped to Account Holder

### Edge Cases to Test

1. Partial payment
2. One payment → many invoices
3. Overpayment → advance
4. Prepayment without invoice

---

## Step 7 — Apply Advance Tool (Desk Utility)

### Objective

Allow accountants to manually apply advances to invoices.

### Deliverables

* Desk action or utility
* Controlled GL posting

### Final Outcomes

* Advances reduce outstanding invoices correctly
* No silent ledger mutation

### Edge Cases to Test

1. Partial advance application
2. Full advance application
3. Attempt over-application

---

## Step 8 — Core Reports (Trust Layer)

### Objective

Prove the system is trustworthy.

### Deliverables

* Account Holder Statement
* Aged Receivables
* Student Attribution View
* Trial Balance
* General Ledger

### Final Outcomes

* Reports reconcile with GL
* Accountants can audit balances

### Edge Cases to Test

1. Trial Balance always zero-sum
2. A/R totals match statements
3. Tax payable matches invoices

---

## Step 9 — Period Locks & Permissions

### Objective

Prevent accidental or silent corruption.

### Deliverables

* Accounting Period doctype
* Lock-until-date per Organization
* Role-based permissions

### Final Outcomes

* Past periods protected
* Only authorized users can submit/cancel

### Edge Cases to Test

1. Post into locked period
2. Cancel in locked period
3. Unauthorized submission attempt

---

## Completion Criteria for Phase 0

Phase 0 is considered complete when:

* Trial Balance reconciles
* Invoices, payments, advances work end-to-end
* Account Holder balances are correct
* Accountants can audit without manual fixes
* No shortcuts block Phase 1 (payroll, inventory, assets)

---

## Explicit Anti-Patterns (Do Not Implement)

* Editing submitted invoices
* Negative Accounts Receivable balances
* Hard-coded school billing logic
* Portal workflows in Phase 0

---

## Next Phase (Not Implemented Here)

* Automated revenue recognition
* Payroll & payables
* Inventory and asset lifecycle
* Online payment gateways
* Consolidated multi-org reporting
