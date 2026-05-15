# inventory_notes.md
Ifitwala_Ed — Inventory (Phase 1)
ERPNext-inspired, Ifitwala-native (Location + Account Holder aware)

This document is the authoritative functional spec for Phase 1.
It includes locked invariants and the hard-fail validation matrix.

---

## 0) Goal

Cover ~90% of real school inventory use cases for:
- Lending to Teachers/Staff (Employee)
- Lending to Students (Student)
- Lending to Parents/Guardians (Guardian)
- Classroom / room custody (Location)
- Serial-level tracking (laptops, textbooks, devices)
- Bulk issuance & return (class sets, 1:1 devices)
- Barcode workflows (scan item tags + scan borrower)
- Basic condition/status tracking + repair stub
- Incident capture for loss/damage (accounting handled separately)

Not in Phase 1:
- Procurement, suppliers, receiving
- Depreciation, capitalization, asset valuation
- Library catalog features (ISBN, reservations, fines)
- Automatic invoices / accounting postings

---

## 1) Locked principles (non-negotiable)

1. Custody ≠ Financial responsibility ≠ Relationship
2. “Where” is always `Location` (NestedSet tree)
3. `Account Holder` is never a custodian
4. Inventory never auto-posts accounting entries
5. Ledger is append-only; edits/deletes are blocked
6. All logic lives in parent transaction controllers (no child controllers)
7. Bulk tools must reuse the same validation+mutation paths as single actions
8. No silent failures: throw on invalid inputs, missing context, and illegal transitions
9. Time handling must use Frappe site timezone

---

## 2) Canonical doctypes used (existing)

Custody targets:
- Employee
- Student (has `account_holder` required)
- Guardian
- Location (NestedSet tree)

Financial responsibility:
- Account Holder (resolved by accounting, inventory only provides facts)

---

## 3) Inventory data model (Phase 1 doctypes)

### 3.1 Inventory Item (catalog)
Represents an item type, not a physical unit.

Required fields:
- item_name (Data, unique)
- item_code (Data, unique, optional)
- has_serial_no (Check, default 0)
- is_consumable (Check, default 0)
- default_uom (Data, default "Nos")
- standard_rate (Currency, optional but recommended)
- barcode (Data, optional) — for scan workflows
- active (Check, default 1)

Rules:
- If has_serial_no=1, issuing must be by Inventory Unit (serial) only.
- If is_consumable=1, issuance is quantity-based and return is typically not required.

---

### 3.2 Inventory Unit (physical unit / serial)
Represents one physical unit (one laptop, one book copy, one iPad).

Required fields:
- inventory_item (Link Inventory Item)
- serial_no (Data, unique; required if item.has_serial_no)
- asset_tag (Data, unique, optional) — printed barcode/tag identifier
- status (Select):
  - Available
  - Issued
  - Under Repair
  - Lost
  - Retired
- condition (Select):
  - New
  - Good
  - Worn
  - Damaged
- current_location (Link Location) — always set when not issued to a person
- current_employee (Link Employee) — optional
- current_student (Link Student) — optional
- current_guardian (Link Guardian) — optional

Custody invariant:
- Exactly ONE of {current_location, current_employee, current_student, current_guardian} must be set.

---

### 3.3 Inventory Ledger Entry (append-only)
Single source of truth for movement history.

Fields:
- posting_datetime (Datetime)
- inventory_item (Link Inventory Item)
- inventory_unit (Link Inventory Unit, optional)
- from_location (Link Location, optional)
- to_location (Link Location, optional)
- qty_change (Float) — for non-serial/consumable movements
- voucher_type (Data)
- voucher_name (Data)
- remarks (Small Text)

Rules:
- Created only by transaction controllers.
- Never edited or deleted (hard fail if attempted).

---

## 4) Transactions (Phase 1 doctypes)

All transactions follow ERPNext pattern:
- Draft → Submitted
- on_submit writes ledger and mutates Inventory Unit custody/status.
- No side effects on save; only on submit.

### 4.1 Inventory Transfer (Location → Location)
Purpose: move items/units between Locations.

Header fields:
- from_location (Link Location, reqd)
- to_location (Link Location, reqd)
- posting_datetime (Datetime, default now)

Child table: Inventory Transfer Item
- inventory_item (Link Inventory Item, reqd)
- inventory_unit (Link Inventory Unit, optional)
- qty (Float, default 1)

Rules:
- If inventory_unit is set, qty must be 1 and item must match unit’s item.
- If item.has_serial_no=1, inventory_unit is required (no qty-only transfers).

Effects on submit:
- Ledger entry per row
- If serial: move unit’s custody to current_location=to_location, clear other custody fields
- If qty-only: ledger records qty movement (future balance reports derived from ledger)

---

### 4.2 Inventory Issue (Location → Custodian)
Purpose: check-out / lend to Employee/Student/Guardian/Location.

Header fields:
- issue_from_location (Link Location, reqd)
- issued_to_type (Select: Employee / Student / Guardian / Location, reqd)
- issued_to_employee (Link Employee)
- issued_to_student (Link Student)
- issued_to_guardian (Link Guardian)
- issued_to_location (Link Location)
- expected_return_date (Date, optional)
- terms_accepted (Check, default 0)
- accepted_by_name (Data, optional)
- accepted_on (Datetime, optional)
- acknowledgment_attachment (Attach, optional)
- notes (Small Text, optional)

Child table: Inventory Issue Item
- inventory_item (Link Inventory Item, reqd)
- inventory_unit (Link Inventory Unit, optional)
- qty (Float, default 1)
- condition_out (Select: New / Good / Worn / Damaged, optional)
- remarks (Small Text, optional)

Rules:
- Exactly one of issued_to_* must be set based on issued_to_type.
- If inventory_item.has_serial_no=1 → inventory_unit is required and qty must be 1.
- If inventory_item.is_consumable=1 → inventory_unit must be empty and qty > 0.
- If issuing a serial unit:
  - unit.status must be Available
  - unit.current_location must equal issue_from_location
- If issuing to Location:
  - custody becomes that Location (useful for classroom sets)

Effects on submit:
- Ledger entry per row (voucher_type="Inventory Issue")
- For serial units:
  - clear all custody fields
  - set the correct current_* field
  - set status="Issued"
  - update condition if condition_out provided
- For consumable qty:
  - ledger records qty out of issue_from_location

---

### 4.3 Inventory Return (Custodian → Location)
Purpose: check-in / return.

Header fields:
- return_to_location (Link Location, reqd)
- returned_from_type (Select: Employee / Student / Guardian / Location, reqd)
- returned_from_employee (Link Employee)
- returned_from_student (Link Student)
- returned_from_guardian (Link Guardian)
- returned_from_location (Link Location)
- posting_datetime (Datetime, default now)
- notes (Small Text, optional)

Child table: Inventory Return Item
- inventory_item (Link Inventory Item, reqd)
- inventory_unit (Link Inventory Unit, optional)
- qty (Float, default 1)
- condition_in (Select: New / Good / Worn / Damaged, optional)
- remarks (Small Text, optional)

Rules:
- Exactly one returned_from_* must be set based on returned_from_type.
- If returning serial unit:
  - unit.status must be Issued or Under Repair (if closing repair loop)
  - unit must currently be held by that custodian (strict match)
- If returning consumable qty:
  - qty must be > 0; return increases stock at return_to_location

Effects on submit:
- Ledger entry per row (voucher_type="Inventory Return")
- For serial units:
  - clear custody fields
  - set current_location=return_to_location
  - status="Available" (unless explicitly set to Under Repair via Repair Ticket)
  - update condition if condition_in provided
- For consumables:
  - ledger records qty into return_to_location

---

## 5) Repairs & incidents (Phase 1 minimal)

### 5.1 Inventory Repair Ticket (stub)
Purpose: capture repairs without building a full maintenance module.

Fields:
- inventory_unit (Link Inventory Unit, reqd)
- issue_summary (Data, reqd)
- status (Select: Open / In Progress / Closed, default Open)
- opened_on (Datetime)
- closed_on (Datetime, optional)
- notes (Text, optional)

Rules:
- On submit/open: unit.status must become "Under Repair"
- On close: unit.status returns to "Available" (if unit is in a Location custody)

---

### 5.2 Inventory Incident
Purpose: record loss/damage/unreturned as facts (no billing).

Fields:
- inventory_unit (Link Inventory Unit, reqd)
- incident_type (Select: Lost / Damaged / Unreturned, reqd)
- incident_date (Date, default today)
- notes (Text)
- suggested_amount (Currency, optional; default from item.standard_rate)
- linked_voucher_type / linked_voucher_name (optional)

Rules:
- If incident_type="Lost": unit.status must become "Lost"
- If incident_type="Retired": use separate workflow later (not in Phase 1)

---

## 6) Reports (Phase 1 must-have)

All reports must be ledger-derived and/or Inventory Unit state derived.

1. Inventory Units by Location (current state)
2. Issued Units by Employee
3. Issued Units by Student
4. Issued Units by Guardian
5. Overdue Issues (expected_return_date < today)
6. Unit assignment history (from vouchers + ledger)
7. Classroom set snapshot (Location custody + counts)
8. Repair queue (units Under Repair)

---

## 7) Hard-fail validation matrix (Phase 1)

Legend:
- HF = hard fail (frappe.throw)
- WARN = warning (msgprint) allowed to proceed (avoid for now; Phase 1 uses HF unless stated)
- OK = allowed

### A) Custody & identity
1. Inventory Unit custody fields set to 0 or >1 → HF
2. Issue: issued_to_type set but matching issued_to_* empty → HF
3. Issue: more than one issued_to_* filled → HF
4. Return: returned_from_type set but matching returned_from_* empty → HF
5. Return: more than one returned_from_* filled → HF

### B) Serial rules
6. Item.has_serial_no=1 and issue row has no inventory_unit → HF
7. Item.has_serial_no=1 and qty != 1 → HF
8. Issue serial unit whose unit.status != Available → HF
9. Issue serial unit whose current_location != issue_from_location → HF
10. Transfer serial unit without inventory_unit → HF
11. Transfer serial unit with qty != 1 → HF

### C) Consumable/qty rules
12. Item.is_consumable=1 and row has inventory_unit → HF
13. Item.is_consumable=1 and qty <= 0 → HF
14. Return consumable qty <= 0 → HF

### D) Return integrity
15. Return serial unit where unit is not currently held by returned_from_* custodian → HF
16. Return serial unit where unit.status not in {Issued, Under Repair} → HF
17. Return to_location missing → HF

### E) Location validity
18. Transfer where from_location == to_location → HF
19. Issue where issue_from_location missing → HF
20. Transfer where from_location missing or to_location missing → HF

### F) Ledger invariants
21. Any attempt to edit/delete Inventory Ledger Entry via UI or server → HF
22. Transaction submit must create at least one ledger entry → HF
23. Ledger rows must have voucher_type + voucher_name → HF

### G) Repair/incident invariants
24. Repair Ticket open while unit.status in {Lost, Retired} → HF
25. Incident Lost sets unit.status="Lost" unless already Retired → HF
26. Incident for unit already Lost + incident_type=Lost again → HF (duplicate)

### H) Acknowledgment (optional enforcement)
27. If terms_accepted=1 then accepted_by_name and accepted_on required → HF
28. If acknowledgment_attachment provided but terms_accepted=0 → HF (keep consistent)

---

## 8) Notes on guardian borrowing (explicit policy)

- Guardians can borrow items directly.
- Inventory does not require a `related_student` because guardians can have multiple children.
- If accounting needs a student context, accounting can request it or enforce it at billing time.
- Inventory preserves custody facts; it does not decide billing logic.

---
