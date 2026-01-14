Below is the **exact Phase-1 task breakdown for Codex**, written as a linear execution plan with **file paths**, **field specs**, **method names**, **acceptance checks**, and **stop conditions**. It assumes Codex has already read `AGENTS_PHASE1_ACCOUNTING.md` (v2).

---

# Phase 1 Task Breakdown (Codex Execution Plan)

## Task 0 — Preconditions / Safety Gates

**Goal:** Ensure Phase 0.1 gates are satisfied before Phase 1 work begins.

### 0.1 Confirm inclusive-tax fix is already merged

* **File:** `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`
* **Check:** posting logic produces balanced GL for:

  * exclusive tax invoices
  * inclusive tax invoices

**Acceptance**

* Trial Balance and voucher GL balance in both cases.

**Stop if**

* inclusive taxes are still over-crediting income.

---

## Task 1 — Add Program Offering linkage to Sales Invoice (header)

### Files to edit

* `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.json`
* `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`

### 1.1 Add field in JSON

Add a new field to Sales Invoice:

* `fieldname`: `program_offering`
* `fieldtype`: `Link`
* `options`: `Program Offering`
* `label`: `Program Offering`
* `insert_after`: choose the closest logical place (near student/account_holder/org fields)
* Optional = `1`

### 1.2 Add server-side validation in `sales_invoice.py`

Implement validation:

* If `self.program_offering` is set:

  * Resolve Program Offering → `school`
  * Resolve School → `organization`
  * Ensure equals `self.organization` (or derived org from Account Holder if that’s your canonical source)

**Acceptance**

* Saving an invoice with program_offering from a different org throws a clear error.

---

## Task 2 — Add Program Offering + charge_source to Sales Invoice Item (line)

### Files to edit

* `ifitwala_ed/accounting/doctype/sales_invoice_item/sales_invoice_item.json`
* `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`

### 2.1 Add fields to Sales Invoice Item JSON

Add:

1. `program_offering`

* Link → Program Offering
* Optional

2. `charge_source`

* Select (required)
* Options (exact, newline-separated):

  * `Program Offering`
  * `Extra`
  * `Manual`

Defaults:

* If you can set `default` in JSON safely, set default = `Extra`

  * (We’ll override in server-side defaulting later if program_offering set)

### 2.2 Sales Invoice validation rules (in parent controller)

In `sales_invoice.py`, in validate():

* For each item row:

  * If `row.charge_source == "Program Offering"`:

    * `row.program_offering` is required
  * If invoice header `self.program_offering` is set and `row.program_offering` is set:

    * require row.program_offering == self.program_offering
  * Allow `Extra/Manual` rows with row.program_offering blank

**Acceptance**

* Tuition lines cannot be saved without program_offering.
* Extra/manual lines can be saved without program_offering.

---

## Task 3 — Defaulting behavior for program_offering and charge_source

### Files to edit

* `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`

### 3.1 Default header program_offering into rows (server-side)

In validate(), before validations:

* If `self.program_offering` is set:

  * For each row:

    * if row.program_offering is empty AND row.charge_source == "Program Offering" OR row.charge_source is empty:

      * set row.program_offering = self.program_offering

### 3.2 Default charge_source

* If row.program_offering is set and row.charge_source empty:

  * set to `Program Offering`
* Else if empty:

  * set to `Extra`

**Acceptance**

* New invoice with header program_offering and blank item charge_source ends up correctly defaulted on save.

---

## Task 4 — Student constraints (schema-based minimal)

### Files to edit

* `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`

### 4.1 Enforce “student belongs to same account holder” (hard check)

Your `student.json` contains `account_holder`. Enforce:

* If row.student is set:

  * fetch Student.account_holder
  * must equal invoice.account_holder
  * else throw clear error

### 4.2 Student org mismatch = warning only (soft check)

If Student has `anchor_school`, resolve school org; if mismatch:

* `frappe.msgprint()` warning (not throw)

**Acceptance**

* Invoice line with student from another payer is blocked.
* Mismatched school/org yields warning but does not block.

---

## Task 5 — Create Program Billing Plan DocType (new)

### Files to create

* `ifitwala_ed/accounting/doctype/program_billing_plan/program_billing_plan.json`
* `ifitwala_ed/accounting/doctype/program_billing_plan/program_billing_plan.py`
* `ifitwala_ed/accounting/doctype/program_billing_plan_component/program_billing_plan_component.json`

### 5.1 program_billing_plan.json (minimum fields)

Create DocType with:

* `organization` (Link → Organization, reqd)
* `program_offering` (Link → Program Offering, reqd)
* `academic_year` (Link → Academic Year, reqd)
* `billing_cadence` (Select: Annual/Term/Monthly, reqd)
* `invoice_grouping_policy` (Select, reqd, default “One invoice per Account Holder per period”)
* `is_active` (Check, default 1)
* Child table `components` (Table → Program Billing Plan Component)

Add unique constraint logic in controller (since JSON unique constraints are limited).

### 5.2 program_billing_plan_component.json (child table)

Fields:

* `billable_offering` (Link → Billable Offering, reqd)
* `qty` (Float, default 1)
* `requires_student` (Check)
* `description_override` (Data/Small Text)

### 5.3 program_billing_plan.py validations

Validate:

* Plan organization matches program_offering → school → org
* Components’ billable_offering.organization matches plan.organization
* Only one active plan per (org, program_offering, academic_year)

**Acceptance**

* Cannot save a plan if a component offering is from another org.
* Cannot have two active plans for same tuple.

---

## Task 6 — Create Billing Schedule DocType (new)

### Files to create

* `ifitwala_ed/accounting/doctype/billing_schedule/billing_schedule.json`
* `ifitwala_ed/accounting/doctype/billing_schedule/billing_schedule.py`
* `ifitwala_ed/accounting/doctype/billing_schedule_row/billing_schedule_row.json`

### 6.1 billing_schedule.json fields

Minimum:

* `organization` (Link → Organization, reqd)
* `program_enrollment` (Link → Program Enrollment, reqd)
* `program_offering` (Link → Program Offering, reqd)
* `billing_plan` (Link → Program Billing Plan, reqd)
* `student` (Link → Student, reqd)
* `account_holder` (Link → Account Holder, reqd)
* `status` (Select: Pending/Invoiced/Adjusted/Cancelled, default Pending)
* Child table `rows` (Table → Billing Schedule Row)

### 6.2 billing_schedule_row.json fields

Minimum:

* `due_date` (Date, reqd)
* `coverage_start` (Date, optional)
* `coverage_end` (Date, optional)
* `expected_amount` (Currency, optional)
* `sales_invoice` (Link → Sales Invoice, read-only)
* `status` (Select: Pending/Invoiced/Cancelled, default Pending)

### 6.3 billing_schedule.py validations

Validate:

* organization matches:

  * account_holder.organization
  * program_offering.school.organization
  * billing_plan.organization
* student.account_holder matches schedule.account_holder
* billing_plan.program_offering matches schedule.program_offering
* billing_schedule.program_enrollment.program_offering matches schedule.program_offering

**Acceptance**

* Schedule cannot be created with inconsistent enrollment/offering/payer.

---

## Task 7 — Implement schedule generation from Program Enrollment (manual action)

### Files to edit/create

* `ifitwala_ed/accounting/doctype/billing_schedule/billing_schedule.py`
* optionally a server utility: `ifitwala_ed/accounting/billing/schedule_generation.py`

### 7.1 Add whitelisted method

Add:

```python
@frappe.whitelist()
def create_billing_schedule(program_enrollment: str, billing_plan: str):
```

Logic:

* Load Program Enrollment
* Load Billing Plan
* Create Billing Schedule with:

  * org (from student.account_holder.organization or school.organization)
  * student
  * account_holder (from Student.account_holder)
  * program_offering (from enrollment.program_offering)
  * program_enrollment
  * billing_plan
* Create schedule rows:

  * Phase 1 minimal: create **one row** due today or next configurable date
  * (Do not implement term/month logic yet unless explicitly required)
* Save draft schedule

**Acceptance**

* One-click schedule creation works for a given enrollment + plan.

---

## Task 8 — Implement invoice generation service (draft only)

### Files to create

* `ifitwala_ed/accounting/billing/invoice_generation.py`

### 8.1 Whitelisted method

```python
@frappe.whitelist()
def generate_draft_invoice(billing_schedule: str, row_ids=None, rates=None):
```

### 8.2 Required behavior

* Load Billing Schedule + selected rows
* If any selected row already has `sales_invoice`, throw (or skip, but must be deterministic; prefer throw)
* Create Sales Invoice draft:

  * organization
  * account_holder
  * program_offering = schedule.program_offering
  * posting_date = today
* For each component in Billing Plan:

  * Require rate provided (rates dict keyed by billable_offering or component rowname)
  * Append Sales Invoice Item:

    * billable_offering
    * qty
    * rate
    * student if requires_student or if schedule.student exists
    * program_offering
    * charge_source = Program Offering
* Save invoice draft
* Update each selected schedule row:

  * sales_invoice = invoice.name
  * status = Invoiced

Return:

* invoice name
* updated rows

**Acceptance**

* Generated invoice is draft and linked to schedule.
* Cannot generate twice for same row.

---

## Task 9 — Wire Billing Schedule button (Desk UI minimal)

### Files to create/edit

* `ifitwala_ed/accounting/doctype/billing_schedule/billing_schedule.js` (create if missing)

Implement:

* Add button “Generate Draft Invoice”
* Prompt for rates (one per billing component)
* Call `generate_draft_invoice(...)`

**Acceptance**

* Accountant can generate a draft invoice from schedule without manual document creation.

---

## Task 10 — Cancellation syncing (invoice ↔ schedule rows)

### Files to edit

* `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`

In `on_cancel`:

* Find Billing Schedule Rows linked to this invoice
* Clear link
* Set status back to Pending

**Acceptance**

* Cancel invoice restores schedule rows to Pending and unlinks invoice.

---

## Task 11 — Smoke test checklist (must be executed)

1. Create Billing Plan
2. Create Program Enrollment (existing)
3. Create Billing Schedule from enrollment + plan
4. Generate draft invoice
5. Submit invoice manually
6. Run Trial Balance & GL
7. Create Payment Entry, allocate
8. Cancel invoice → schedule resets

**Stop if**

* Any step silently fails
* Any GL imbalance appears
* Schedule rows can be double-invoiced

---

## Final Output Expected

* New DocTypes exist and validate
* Billing Schedule supports draft invoice generation
* Invoice lines clearly identify Program Offering vs Extras vs Manual
* Links are traceable:

  * Program Enrollment → Billing Schedule → Sales Invoice
* Cancellation maintains integrity

---
