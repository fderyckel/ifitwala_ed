# Ifitwala Ed — Accounting Architecture Notes (Phase 0)

## Status

**Architecture lock — accounting best‑practice first.**

This document defines the **non‑negotiable accounting primitives and rules** for Ifitwala Ed. It is intentionally conservative, accountant‑friendly, and aligned with international accounting practice and ERPNext patterns. Pedagogical or UX concerns do not override accounting correctness.

This file is the canonical reference and will be updated incrementally as decisions are locked.

### ERPNext Baseline & Scope (Locked)

* Baseline ERPNext version: v16 (accounting module only).
* ERPNext Company doctype is used as Organization (same doctype, education naming).
* Manufacturing / production modules are explicitly out of scope for education accounting.

### ERPNext v16 Doctype Mapping (Accounting)

| Ifitwala Doctype / Concept | ERPNext v16 Doctype | Notes |
| --- | --- | --- |
| Organization (legal entity) | Company | Same doctype; surfaced as Organization. |
| Accounting Settings (org-level) | Accounts Settings | Org-level defaults. |
| Fiscal Year | Fiscal Year | Implemented. Legal accounting-year authority, distinct from Academic Year and retained separately from Accounting Period. |
| Chart of Accounts Template | Chart of Accounts Importer + chart template JSON/Python files | Templates live under `ifitwala_ed/accounting/doctype/account/chart_of_accounts`. The packaged default is the ERPNext v16 international `standard_chart_of_accounts` template, and it is auto-installed for each new Organization. |
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
| Accounting Period | Accounting Period | Period locks, not the fiscal-year authority. |

---

## 1. Core Principles (Locked)

1. **Accounting correctness > convenience**

   * This is an accounting module, not an LMS add‑on.
   * All posted data must be auditable, reversible, and accountant‑trustworthy.

2. **Double‑entry from day one**

   * Every financial document posts balanced General Ledger entries.
   * Trial Balance must always reconcile.

3. **Immutability of posted documents**

   * Draft → editable
   * Submitted → immutable
   * Corrections are done via cancellation, credit notes, debit notes, or amendments that preserve audit trail.

4. **Structure before automation**

   * Phase 0 prioritizes correct structure.
   * Automation (revenue schedules, stock valuation, payroll runs) may come later.

---

## 2. Legal & Accounting Reference Model

### 2.1 Organization (Legal Entity)

* **Organization** is the legal accounting entity.
* ERPNext **Company** doctype is used and surfaced as Organization (no separate Organization doctype).
* Owns:

  * Chart of Accounts
  * General Ledger
  * Tax configuration
  * Payroll (future)
  * Inventory & Assets (future)

Schools are **operational units only** and are used for analytical dimensions, not legal accounting truth.

### 2.2 Accounting Time Domains

Ifitwala Ed must keep the accounting and education time domains explicitly separate:

* **Academic Year** is the school-scoped educational container for enrollment, scheduling, attendance, and term reporting.
* **Fiscal Year** is the organization-scoped legal accounting year for financial reporting and posting governance.
* **Accounting Period** is the narrower transaction-control layer used to lock/close posting windows.

Current implemented state:

* `Fiscal Year` is implemented as the legal accounting-year authority per Organization scope.
* `Accounting Period` and `Accounts Settings.lock_until_date` are implemented.
* accounting posting validation now resolves `Fiscal Year` before applying lock-date and closed-period checks.

Locked direction:

* keep `Fiscal Year` modeled on ERPNext v16 semantics
* keep `Accounting Period` as a lock surface, not as the accounting-year master
* never infer accounting legality from `Academic Year`

---

## 3. Account Holder (Locked Concept)

### 3.1 Definition

**Account Holder** is the legal counterparty responsible for payment.
It replaces the notion of "Customer" in education context.
ERPNext counterpart: Customer (legal debtor).

### 3.2 Properties

An Account Holder:

* Is the **A/R counterparty**
* Can represent:

  * A single guardian
  * Two guardians jointly
  * An adult learner
  * A sponsoring organization
* Belongs to exactly one Organization

### 3.3 Cardinality Rules (Locked)

* **Each student has exactly one primary Account Holder**
* **One Account Holder may be responsible for multiple students** (siblings, family accounts)

All invoices, advances, credits, and balances are tracked **per Account Holder**.

---

## 4. Student (Beneficiary)

* Student is the **educational beneficiary**, not the legal debtor.
* Students are used for:

  * Invoice line attribution
  * Reporting
  * Analytics

Student links **must never** replace Account Holder in ledger postings.

---

## 5. Billable Offerings (Unified Model)

All billable items flow through a single abstraction:

### 5.1 Billable Offering

Offering types:

* Program (tuition, extracurricular)
* Service Subscription (bus, lunch)
* One‑off Fee (application, registration, trips, exams)
* Product (uniforms, shop items — scaffold)

Each Offering defines:

* Revenue account (default)
* Tax category / template
* Pricing mode (fixed, per‑term, per‑unit, subscription)

No accounting logic is hard‑coded by pedagogical type.

### 5.2 Phase 1 Billing Structure Boundary

`Billable Offering` is the fee catalog and accounting-mapping layer only.

Phase 1 adds separate program billing objects:

* `Program Billing Plan` composes the relevant billable offerings for one `Program Offering` and `Academic Year`
* `Program Billing Plan Component` stores program-local quantity and default-rate policy
* `Billing Schedule` derives the per-enrollment billing rows
* `Billing Run` batches pending schedule rows into draft invoices grouped by `Account Holder`

Locked boundary:

* keep income-account and tax-category ownership on `Billable Offering`
* keep plan-local pricing on `Program Billing Plan Component`
* keep installment splitting on `Payment Terms Template`
* keep all GL posting inside `Sales Invoice`

---

## 6. Billing Cadence (Supported Structures)

The system must structurally support:

* Application fees (one‑off)
* Registration / enrollment / capital fees (one‑off)
* Term‑based tuition billing
* Installment schedules via payment terms templates
* Recurring subscriptions (monthly, term, annual)
* Usage‑based subscriptions (e.g. lunches per month)
* Ad‑hoc charges

Operational policy is configurable per Organization.

Phase 1 implementation status:

* Annual, Term, and Monthly program billing structures are implemented through `Program Billing Plan`
* Billing schedules are generated from `Program Enrollment`
* Accounting can generate draft invoices in bulk for one `Program Offering` through `Billing Run`

---

## 7. Prepayments, Advances & Unearned Revenue (Locked)

### 7.1 Accounting Rule

Money received **before service delivery** is a **liability**, not income.

### 7.2 Phase‑0 Policy

* All prepayments / excess payments are posted to a **liability account**:

  * e.g. `Unearned Revenue` or `Advances from Account Holders`
* No negative Accounts Receivable balances.

### 7.3 Allocation

* Advances may later be allocated to invoices of the **same Account Holder**.
* Revenue recognition may be **manual** in Phase 0, but structure must exist.

---

## 8. Discounts & Scholarships (Locked Flexibility)

System must support **both** accounting treatments:

1. **Contra‑Income** (default)

   * Discounts reduce income via contra‑income accounts

2. **Expense‑based Aid**

   * Scholarships / bursaries recorded as expenses
   * Tuition income remains gross

Treatment is determined by policy, not hard‑coded behavior.

---

## 9. Tax Handling (Phase‑0 Baseline)

* Item/Offering‑level tax categories
* Tax templates with:

  * Rates
  * Accounts
  * Inclusive / Exclusive flag

### Inclusive vs Exclusive

* Both models must be supported
* Inclusive pricing means:

  * Displayed price is final
  * System backs out tax portion

No complex jurisdiction rules in Phase 0.

---

## 10. Chart of Accounts (ERPNext‑Aligned)

The CoA structure must follow ERPNext conventions closely, even if not fully used yet.

### 10.0 Default provisioning

* Each new Organization automatically receives the packaged default chart of accounts.
* The packaged default is the ERPNext v16 international `standard_chart_of_accounts` template.
* Existing sites that have Organizations with zero `Account` rows are backfilled by a migration patch.
* Existing sites also backfill ERPNext-defined `account_type` values for standard-chart accounts when those values are missing.
* `Account.account_name` keeps the human-facing chart label, but the `Account` docname is qualified with the Organization abbreviation to preserve multi-organization isolation and avoid name collisions across sibling organizations.
* The Chart of Accounts tree is organization-scoped and uses an account-specific tree loader so finance can browse the actual nested chart in Desk.

### 10.1 Minimum Active Accounts (Phase 0)

**Assets**

* Cash
* Bank
* Accounts Receivable

**Liabilities**

* Unearned Revenue / Advances

**Income**

* Tuition & Programs
* Services & Subscriptions
* Events & Trips
* Shop Sales (scaffold)

**Expenses**

* Program Costs
* Transport Costs
* Catering Costs
* Trip Costs
* IT & Equipment

### 10.2 Scaffolded Branches (Phase 1 readiness)

* Accounts Payable
* Payroll Payable
* Tax Payable
* Inventory
* Fixed Assets
* Depreciation

---

## 11. Capital / Registration Fees (Policy‑Driven)

Registration‑related fees are **configured, not assumed**.

Possible treatments per Organization policy:

* Income
* Deferred income
* Deposit / liability
* Capital / reserve account

The system must allow mapping each Offering to the appropriate account.

---

## 12. Posting Semantics (Locked)

### Invoice Submission

* Debit: Accounts Receivable (Account Holder)
* Credit: Income accounts (per line)
* Credit: Tax Payable (if applicable)

### Payment Submission

* Debit: Bank / Cash
* Credit: Accounts Receivable (or Advances if prepayment)

### Credit Note Submission

* Debit: Income accounts (reversal)
* Debit: Tax Payable (reversal, if applicable)
* Credit: Accounts Receivable
* Credit notes reduce the outstanding amount of the source invoice and are linked via adjustment traceability.

### Advance Reconciliation

* Debit: Advances / Unearned Revenue
* Credit: Accounts Receivable
* Reconciliation is tied to an explicit Payment Entry source, not an implicit oldest‑first sweep.

No silent mutation of posted entries.

---

## 13. Receivables Operations (Current)

Receivables operations now include:

* `Payment Terms Template` for installment schedules
* `Sales Invoice Payment Schedule` for per‑invoice due rows
* `Payment Request` for payer outreach tied to a submitted invoice
* `Dunning Notice` for overdue receivable follow‑up
* `Statement Of Accounts Run` for finance statement processing queues
* Linked credit notes and debit notes via `Sales Invoice.adjustment_type`
* Rich invoice statuses:

  * Draft
  * Unpaid
  * Partly Paid
  * Paid
  * Overdue
  * Credit Note
  * Partly Credited
  * Credited
  * Cancelled

Analytical dimensions supported in the current accounting layer:

* School
* Program
* Program Offering
* Student (line / GL analytic context only)

These dimensions are for reporting and operational insight. They do **not** replace Organization or Account Holder as legal accounting anchors.

---

## 14. Reporting (Current)

Operational:

* Account Holder statement
* Student financial attribution view
* Aged receivables
* Payment request register (list view / doctype workflow)
* Dunning notice work queue (list view / doctype workflow)
* Statement processing run queue (list view / doctype workflow)

Accounting:

* General Ledger
* Trial Balance
* Income by Offering / Program
* School / Program filtered ledger reporting

### 14.1 School-Dimension Filter Semantics

- `Trial Balance` keeps exact-match filtering on `GL Entry.school`. Parent-school selection does not roll up descendants because legal accounting reporting remains organization-scoped first.
- `Student Attribution` is descendant-aware on `Sales Invoice Item.school`. Selecting a parent school includes invoice lines from descendant schools in that same branch.
- `Aged Receivables` currently keeps exact-match school filtering through invoice-line existence checks. That remains the current contract until owner docs decide whether the report should stay invoice-level or become line-aware.

---

## 15. Non‑Goals (Phase 0)

* Manufacturing / production modules
* Payroll processing
* Inventory valuation
* Automated revenue recognition schedules
* Multi‑currency
* Consolidation across organizations

---

## 16. Forward Compatibility

This architecture explicitly keeps doors open for:

* Payroll
* Inventory & asset tracking (IT devices, book loans)
* Online payment gateway integration
* Consolidated reporting

No Phase‑0 shortcuts may block these paths.

---

## 17. Open for Future Locking

* Capital fee accounting defaults
* Recognition schedule automation
* Automated collections dispatch (email/SMS/portal)

(These are intentionally not locked yet.)
