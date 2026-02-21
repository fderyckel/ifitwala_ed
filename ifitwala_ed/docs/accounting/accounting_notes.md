# Ifitwala Ed — Accounting Architecture Notes (Phase 0)

## Status

**Architecture lock — accounting best‑practice first.**

This document defines the **non‑negotiable accounting primitives and rules** for Ifitwala Ed. It is intentionally conservative, accountant‑friendly, and aligned with international accounting practice and ERPNext patterns. Pedagogical or UX concerns do not override accounting correctness.

This file is the canonical reference and will be updated incrementally as decisions are locked.

### ERPNext Baseline & Scope (Locked)

* Baseline ERPNext version: v15 (accounting module only).
* ERPNext Company doctype is used as Organization (same doctype, education naming).
* Manufacturing / production modules are explicitly out of scope for education accounting.

### ERPNext v15 Doctype Mapping (Accounting)

| Ifitwala Doctype / Concept | ERPNext v15 Doctype | Notes |
| --- | --- | --- |
| Organization (legal entity) | Company | Same doctype; surfaced as Organization. |
| Accounting Settings (org-level) | Accounts Settings | Org-level defaults. |
| Chart of Accounts Template | Chart of Accounts Importer + chart template JSON/Python files | Templates live under `ifitwala_ed/accounting/doctype/account/chart_of_accounts`. Current packaged default is `standard_chart_of_accounts` (English); additional templates can be added later in the same module. |
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

---

## 6. Billing Cadence (Supported Structures)

The system must structurally support:

* Application fees (one‑off)
* Registration / enrollment / capital fees (one‑off)
* Term‑based tuition billing
* Recurring subscriptions (monthly, term, annual)
* Usage‑based subscriptions (e.g. lunches per month)
* Ad‑hoc charges

Operational policy is configurable per Organization.

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

No silent mutation of posted entries.

---

## 13. Reporting (Phase 0)

Operational:

* Account Holder statement
* Student financial attribution view
* Aged receivables

Accounting:

* General Ledger
* Trial Balance
* Income by Offering / Program

---

## 14. Non‑Goals (Phase 0)

* Manufacturing / production modules
* Payroll processing
* Inventory valuation
* Automated revenue schedules
* Multi‑currency
* Consolidation across organizations

---

## 15. Forward Compatibility

This architecture explicitly keeps doors open for:

* Payroll
* Inventory & asset tracking (IT devices, book loans)
* Automated revenue recognition
* Consolidated reporting

No Phase‑0 shortcuts may block these paths.

---

## 16. Open for Future Locking

* Credit allocation automation vs manual
* Capital fee accounting defaults
* Recognition schedule automation
* Online payment gateway integration

(These are intentionally not locked yet.)
