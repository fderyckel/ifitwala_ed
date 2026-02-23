Got it. Below is a **much more detailed, operational Phase 1 note**, written as a **build contract**.
This is meant to be readable by **humans** *and* executable by **coding agents** without interpretation.

You can drop this verbatim as:

```
docs/accounting/phase1_notes.md
```

No fluff. No ambiguity.

---

# Ifitwala Ed — Accounting Phase 1 Notes

## Program Billing Structures & Deterministic Invoice Generation

**Status:** LOCKED DESIGN
**Depends on:**

* Phase 0 (ledger, payments, reconciliation)
* Phase 0.1 (tax posting correction + Program Offering linkage)

**Audience:**

* Core ERP developers
* Accounting logic agents
* Reviewers / auditors

---

## 0. Phase 1 Objective (Non-Negotiable)

Phase 1 introduces **billing structure**, not accounting shortcuts.

By the end of Phase 1, the system must be able to answer, deterministically and audibly:

* *What should be billed?*
* *When should it be billed?*
* *Which Program Offering caused this invoice to exist?*

All without:

* auto-submitting invoices
* silent GL posting
* student-level A/R
* revenue recognition logic

---

## 1. Canonical Objects (Reconfirmed)

These objects already exist and MUST NOT be repurposed.

| Object               | Role                                          |
| -------------------- | --------------------------------------------- |
| `Sales Invoice`      | Legal accounting document                     |
| `Sales Invoice Item` | Atomic charge line                            |
| `Account Holder`     | Legal debtor                                  |
| `Student`            | Beneficiary / analytic only                   |
| `Billable Offering`  | Chargeable service (maps to income + tax)     |
| `Program Offering`   | Educational context (program + school + year) |

---

## 2. New Objects Introduced in Phase 1

### 2.1 Program Billing Plan (NEW)

**File(s)**

```
ifitwala_ed/accounting/doctype/program_billing_plan/
├─ program_billing_plan.json
├─ program_billing_plan.py
```

**Purpose**
Defines *how a specific Program Offering is billed*.

**Fields (minimum)**

* `organization` (Link → Organization, required)
* `program_offering` (Link → Program Offering, required, unique per org)
* `academic_year` (Link → Academic Year, required)
* `billing_cadence` (Select):

  * Annual
  * Term
  * Monthly
* `invoice_grouping_policy` (Select):

  * One invoice per Account Holder per period (default)
* `is_active` (Check)

**Rules**

* One active Billing Plan per Program Offering per Academic Year.
* No pricing logic here.
* No accounting logic here.
* No invoice creation here.

---

### 2.2 Program Billing Component (Child Table)

**File(s)**

```
ifitwala_ed/accounting/doctype/program_billing_plan_component/
├─ program_billing_plan_component.json
```

**Fields**

* `billable_offering` (Link → Billable Offering, required)
* `qty` (Float, default = 1)
* `requires_student` (Check)
* `description_override` (Data, optional)

**Rules**

* This table defines *what tuition is made of*.
* No rate stored here (Phase 1 still collects rate at invoice generation).

---

### 2.3 Billing Schedule (NEW, derived object)

**File(s)**

```
ifitwala_ed/accounting/doctype/billing_schedule/
├─ billing_schedule.json
├─ billing_schedule.py
```

**Purpose**
Represents *expected billing events* for a Program Enrollment.

**Fields**

* `organization` (Link → Organization)
* `program_enrollment` (Link → Program Enrollment)
* `program_offering` (Link → Program Offering)
* `billing_plan` (Link → Program Billing Plan)
* `student` (Link → Student)
* `account_holder` (Link → Account Holder)
* `status` (Select):

  * Pending
  * Invoiced
  * Adjusted
  * Cancelled

---

### 2.4 Billing Schedule Row (Child Table)

**File(s)**

```
ifitwala_ed/accounting/doctype/billing_schedule_row/
├─ billing_schedule_row.json
```

**Fields**

* `due_date` (Date)
* `coverage_start` (Date)
* `coverage_end` (Date)
* `expected_amount` (Currency, informational)
* `sales_invoice` (Link → Sales Invoice, read-only)
* `status` (Select: Pending / Invoiced / Cancelled)

**Rules**

* Billing Schedule rows do NOT post accounting entries.
* They are expectations only.

---

## 3. Invoice Generation (Core Phase 1 Mechanism)

### 3.1 Entry Point (MANDATORY MANUAL FIRST)

**Action**

* Button: **“Generate Draft Invoice”**

**Location**

* Billing Schedule
* (Optionally) Program Enrollment form

**Server Method**

```
ifitwala_ed/accounting/billing/invoice_generation.py
```

**Method signature (example)**

```python
def generate_draft_invoice(billing_schedule, schedule_row_ids=None):
```

---

### 3.2 Invoice Creation Rules (LOCKED)

The method MUST:

1. Create a **Draft Sales Invoice**

2. Set:

   * `organization`
   * `account_holder`
   * `program_offering`
   * `posting_date = today`

3. For each Billing Component:

   * Create a Sales Invoice Item with:

     * `billable_offering`
     * `qty`
     * `rate` (prompted / provided)
     * `student` (if required)
     * `program_offering`
     * `charge_source = Program Offering`

4. Link:

   * `billing_schedule_row.sales_invoice = invoice.name`

5. Set Billing Schedule Row status → `Invoiced`

**Hard constraints**

* Never auto-submit
* Never bypass Sales Invoice validation
* Never write GL directly

---

## 4. Sales Invoice Changes Required for Phase 1

### 4.1 Header Fields (Additions)

**File**

```
ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.json
```

Add:

* `program_offering` (Link → Program Offering)

### 4.2 Item Fields (Additions)

**File**

```
ifitwala_ed/accounting/doctype/sales_invoice_item/sales_invoice_item.json
```

Add:

* `program_offering` (Link → Program Offering)
* `charge_source` (Select):

  * Program Offering
  * Extra
  * Manual

---

### 4.3 Validation Logic (Server-side only)

**File**

```
ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py
```

Add validations:

* If invoice has `program_offering`:

  * Program Offering must belong to same Organization as invoice.
* If item has `charge_source = Program Offering`:

  * `program_offering` is required.
* If item has `student`:

  * student must belong to invoice organization.

No client-side enforcement.

---

## 5. Extras Handling (Explicit)

Extras remain **Billable Offerings**, not special cases.

Examples:

* Bus subscription
* Lunch subscription
* Uniform
* Trip fee

**How they appear**

* Sales Invoice Item
* `charge_source = Extra`
* `program_offering` optional
* `student` optional but recommended

Extras never bypass Sales Invoice.

---

## 6. Explicit Prohibitions (Phase 1)

The following are FORBIDDEN in Phase 1:

* Auto-submitting invoices
* Generating invoices without a Billing Schedule
* Posting GL outside Sales Invoice
* Editing submitted invoices
* Student as party
* Revenue recognition automation
* Usage-based billing

Violating any of the above breaks Phase 1.

---

## 7. Testing Checklist (Mandatory)

Before Phase 1 is considered complete:

* Tuition invoice generated from Billing Schedule
* Invoice links back to Program Offering
* Invoice links back to Billing Schedule Row
* Mixed invoice (tuition + extra) works
* Inclusive & exclusive tax invoices both balance
* Trial Balance balances
* Cancelling invoice resets Billing Schedule Row

---

## 8. Phase 1 Completion Gate

Phase 1 is complete ONLY if:

* Billing is structured
* Invoice origin is traceable
* Accounting invariants hold
* Phase 2 can be built without refactoring Phase 0/1

---

## 9. Phase 2 Boundary (Explicit)

Phase 1 intentionally does NOT include:

* Revenue schedules
* Deferred income
* Subscriptions
* Payment gateways
* Parent portal billing
* Multi-currency

---

### Final lock statement

> **Phase 1 does not optimize speed.
> Phase 1 optimizes correctness, traceability, and future safety.**

---




## 1️⃣ What your actual schemas tell us (important confirmations)

### Program Offering

From `program_offering.json`

*Facts that matter for accounting:*

* Program Offering **does NOT link to Organization directly**
* It links to **School**
* Therefore **Organization must be resolved via School**
* Program Offering is already the **canonical academic unit** for enrollment

✅ This confirms our design choice:
**Program Offering is the correct anchor for tuition billing context**
but **must never carry accounting logic**.

---

### Student

From `student.json`

Key facts:

* Student has:

  * `account_holder` (required)
  * `anchor_school` (optional but present)
* Student **does not link to Organization directly**

✅ Therefore:

* **Account Holder = legal debtor**
* **Student = analytic dimension**
* Organization resolution must be:

  * Invoice → Account Holder → Organization
  * Student consistency checks are *secondary*

This validates Phase-1 rule:
👉 **enforce Account Holder / Organization strictly**
👉 **student/org alignment = soft check only**

---

### Program Enrollment

From `program_enrollment.json`

Key facts:

* Program Enrollment already links:

  * `student`
  * `program`
  * `program_offering` (required)
  * `school`
  * `academic_year`
* This is the **perfect source** for Billing Schedule generation

✅ Confirms:

* Billing Schedule **must be derived from Program Enrollment**
* No ambiguity about which Program Offering applies
* Academic Year is already present (good for future proration)

---

### Billable Offering

From `billable_offering.json`

Critical confirmations:

* Billable Offering already contains:

  * `organization`
  * `income_account`
  * `tax_category`
  * `pricing_mode`
* **No rate fields** (important!)

✅ Therefore:

* Rates **must be supplied at invoice generation time**
* Phase-1 must **not invent pricing logic**
* Billable Offering is **exactly** the right abstraction for:

  * tuition
  * extras (bus, lunch, uniform, etc.)

This strongly validates your earlier instinct.

---

## 2️⃣ Corrections & clarifications to Phase-1 decisions

These are **important and final**.

### A. `charge_source` options (final)

**Keep all three**:

```
Program Offering
Extra
Manual
```

Why:

* `Program Offering` → tuition derived from enrollment
* `Extra` → bus, lunch, uniform, trip, etc. (still structured)
* `Manual` → accountant-only corrections (must exist)

❌ Do NOT reduce to Program Offering + blank
That would destroy audit clarity later.

---

### B. Manual Invoice UI (final decision)

Yes — **manual invoice action must collect**:

For each line:

* `billable_offering` (required)
* `qty` (default 1)
* `rate` (required)
* `student` (optional)
* `program_offering` (optional unless charge_source = Program Offering)

And **never infer rate**.

This aligns perfectly with Billable Offering lacking prices.

---

### C. Organization enforcement (important nuance)

**Phase 1 rule (balanced, safe):**

1. **Always enforce**:

   * Invoice.Organization == BillableOffering.organization
   * Invoice.Organization == AccountHolder.organization

2. **Program Offering enforcement**:

   * Resolve ProgramOffering → School → Organization
   * Must match Invoice.Organization

3. **Student enforcement**:

   * Soft check only:

     * warn if Student.anchor_school org mismatches
     * do **not** block invoice

This avoids false negatives in multi-school households.

---

## 3️⃣ Phase-1 Coding Instruction File (v2 – FINAL)

Below is the **revised, schema-aware, Codex-ready instruction file**.
You can **replace the previous one** with this.

---

# `AGENTS_PHASE1_ACCOUNTING.md`

## Ifitwala Ed — Phase 1 Billing & Invoicing (Authoritative)

---

## 0. Scope Lock (Read First)

You are implementing **Phase 1 only**.

Phase 1 introduces:

* Program Billing Plan
* Billing Schedule derived from Program Enrollment
* Deterministic **draft** Sales Invoice generation
* Program Offering linkage on invoices and lines

Phase 1 explicitly does **NOT** include:

* auto-submission
* GL posting outside Sales Invoice
* pricing engines
* ERPNext Item / Stock
* revenue recognition
* installment automation

If unsure: **stop and ask**.

---

## 1. Accounting Invariants (Non-Negotiable)

1. **Sales Invoice is the only GL-posting document**
2. **Billing Schedule never touches GL**
3. **Invoices generated are always DRAFT**
4. **Account Holder is the legal debtor**
5. **Student is analytic only**
6. **Program Offering is contextual, not accounting**
7. **Billable Offering is the only object that defines:**

   * income account
   * tax category
8. **Rates are always provided at invoice creation**
9. **Inclusive tax correctness must be preserved**

---

## 2. New Data Concepts (Phase 1)

### 2.1 Program Billing Plan

Template defining **what is billable** for a Program Offering.

* Linked to:

  * Organization
  * Program Offering
  * Academic Year
* Contains components:

  * Billable Offering
  * Quantity rule (static for Phase 1)

No prices. No GL.

---

### 2.2 Billing Schedule

Concrete, per-student, per-enrollment billing plan.

Derived from:

* Program Enrollment
* Program Billing Plan

Contains rows with:

* due_date
* expected_amount (informational)
* status: Pending / Invoiced
* linked Sales Invoice (once generated)

---

## 3. `charge_source` (Final)

Sales Invoice Item must include:

```
Program Offering
Extra
Manual
```

Rules:

* If `program_offering` is set → default `Program Offering`
* Else → default `Extra`
* `Manual` is accountant-only

---

## 4. Allowed File Modifications

### Modify

```
accounting/doctype/sales_invoice/sales_invoice.json
accounting/doctype/sales_invoice/sales_invoice.py
accounting/doctype/sales_invoice_item/sales_invoice_item.json
```

### Create (exact paths)

```
accounting/doctype/program_billing_plan/*
accounting/doctype/program_billing_plan_component/*
accounting/doctype/billing_schedule/*
accounting/doctype/billing_schedule_row/*
accounting/billing/invoice_generation.py
```

No other files may be touched.

---

## 5. Sales Invoice Validation Rules (Server-Side Only)

### Organization resolution

* Invoice.organization = AccountHolder.organization
* BillableOffering.organization must match
* ProgramOffering → School → Organization must match

### Program Offering rules

* If any line has `charge_source = Program Offering`:

  * line.program_offering is required
* If invoice.program_offering is set:

  * all Program Offering lines must match it

### Student rules

* Student is optional
* If set:

  * must belong to same Account Holder
  * org mismatch = warning only

---

## 6. Invoice Generation Service

### File

```
accounting/billing/invoice_generation.py
```

### Required method

```python
@frappe.whitelist()
def generate_draft_invoice(
    billing_schedule: str,
    row_ids: list[str] | None = None,
    rates: dict[str, float] | None = None
)
```

### Behavior

1. Load Billing Schedule
2. Validate not already invoiced
3. Create **draft** Sales Invoice
4. For each selected row:

   * create Sales Invoice Item
   * require rate input
   * set:

     * billable_offering
     * qty
     * rate
     * student
     * program_offering
     * charge_source
5. Save invoice (docstatus = 0)
6. Link invoice back to schedule rows
7. Return invoice name + affected rows

No submission. Ever.

---

## 7. Cancellation Handling

On Sales Invoice `on_cancel`:

* For linked Billing Schedule rows:

  * clear `sales_invoice`
  * set status back to `Pending`

No orphaned schedules allowed.

---

## 8. Manual Invoice Entry (Desk)

Manual invoices:

* May include any `charge_source`
* Must always collect rate
* Must still pass all org + offering validations

No shortcuts.

---

## 9. Definition of Done

Phase 1 is complete when:

* Billing Schedule generates draft invoices
* Program Offering is traceable from enrollment → invoice
* Trial Balance balances (tax-inclusive & exclusive)
* Cancellation restores schedule integrity
* No GL outside Sales Invoice

---

## 10. Forbidden Actions

Do NOT:

* add price fields to Billable Offering
* infer rates
* auto-submit invoices
* touch GL Entry
* introduce ERPNext Items
* add client-side accounting logic

---

## Final note (important)

This Phase 1 design is **clean, conservative, and future-proof**:

* It respects ERPNext accounting invariants
* It aligns perfectly with your education domain
* It leaves room for Phase 2 pricing without refactors
