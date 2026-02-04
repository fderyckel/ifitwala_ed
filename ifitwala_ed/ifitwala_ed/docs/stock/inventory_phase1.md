# inventory_phase1.md
Ifitwala_Ed — Inventory Phase 1A (Codex Execution Plan)
This file is the authoritative “what to create” + file paths + controllers checklist.

Indentation: tabs for shared code.
No child table logic.
All mutations occur in parent doc controllers on submit.

---

## 1) Files/paths to create (exact)

### A) Module folder
Create folder:
- `ifitwala_ed/stock/` (if not already)
- `ifitwala_ed/stock/inventory/` (new)

### B) DocTypes (create these folders + files)
1) Inventory Item
- `ifitwala_ed/stock/doctype/inventory_item/inventory_item.json`
- `ifitwala_ed/stock/doctype/inventory_item/inventory_item.py`
- `ifitwala_ed/stock/doctype/inventory_item/inventory_item.js` (optional, minimal client)

2) Inventory Unit
- `ifitwala_ed/stock/doctype/inventory_unit/inventory_unit.json`
- `ifitwala_ed/stock/doctype/inventory_unit/inventory_unit.py`
- `ifitwala_ed/stock/doctype/inventory_unit/inventory_unit.js` (optional)

3) Inventory Ledger Entry
- `ifitwala_ed/stock/doctype/inventory_ledger_entry/inventory_ledger_entry.json`
- `ifitwala_ed/stock/doctype/inventory_ledger_entry/inventory_ledger_entry.py`

4) Inventory Transfer + child
- `ifitwala_ed/stock/doctype/inventory_transfer/inventory_transfer.json`
- `ifitwala_ed/stock/doctype/inventory_transfer/inventory_transfer.py`
- `ifitwala_ed/stock/doctype/inventory_transfer_item/inventory_transfer_item.json`
- (NO controller for child)

5) Inventory Issue + child
- `ifitwala_ed/stock/doctype/inventory_issue/inventory_issue.json`
- `ifitwala_ed/stock/doctype/inventory_issue/inventory_issue.py`
- `ifitwala_ed/stock/doctype/inventory_issue_item/inventory_issue_item.json`
- (NO controller for child)

6) Inventory Return + child
- `ifitwala_ed/stock/doctype/inventory_return/inventory_return.json`
- `ifitwala_ed/stock/doctype/inventory_return/inventory_return.py`
- `ifitwala_ed/stock/doctype/inventory_return_item/inventory_return_item.json`
- (NO controller for child)

7) Inventory Incident
- `ifitwala_ed/stock/doctype/inventory_incident/inventory_incident.json`
- `ifitwala_ed/stock/doctype/inventory_incident/inventory_incident.py`

8) Inventory Repair Ticket
- `ifitwala_ed/stock/doctype/inventory_repair_ticket/inventory_repair_ticket.json`
- `ifitwala_ed/stock/doctype/inventory_repair_ticket/inventory_repair_ticket.py`

### C) Shared server utilities (new)
Create:
- `ifitwala_ed/stock/inventory/inventory_utils.py`
- `ifitwala_ed/stock/inventory/inventory_ledger.py`
- `ifitwala_ed/stock/inventory/inventory_validations.py`

### D) Bulk endpoints (whitelisted)
Create:
- `ifitwala_ed/api/inventory.py`

Contains:
- `bulk_issue(payload)`
- `bulk_return(payload)`
Both must reuse the same validation/mutation helpers as the doctypes.

### E) Reports
Create report files (Script Reports or Query Reports; choose Script for permission logic):
- `ifitwala_ed/stock/report/inventory_units_by_location/inventory_units_by_location.py`
- `ifitwala_ed/stock/report/inventory_units_by_location/inventory_units_by_location.js`
- `ifitwala_ed/stock/report/inventory_issued_by_employee/inventory_issued_by_employee.py`
- `ifitwala_ed/stock/report/inventory_issued_by_employee/inventory_issued_by_employee.js`
- `ifitwala_ed/stock/report/inventory_issued_by_student/inventory_issued_by_student.py`
- `ifitwala_ed/stock/report/inventory_issued_by_student/inventory_issued_by_student.js`
- `ifitwala_ed/stock/report/inventory_issued_by_guardian/inventory_issued_by_guardian.py`
- `ifitwala_ed/stock/report/inventory_issued_by_guardian/inventory_issued_by_guardian.js`
- `ifitwala_ed/stock/report/inventory_overdue_issues/inventory_overdue_issues.py`
- `ifitwala_ed/stock/report/inventory_overdue_issues/inventory_overdue_issues.js`
- `ifitwala_ed/stock/report/inventory_repair_queue/inventory_repair_queue.py`
- `ifitwala_ed/stock/report/inventory_repair_queue/inventory_repair_queue.js`

---

## 2) Controllers to implement (exact responsibilities)

### Inventory Unit controller (`inventory_unit.py`)
Implement `validate()`:
- Enforce custody invariant: exactly one custodian set
- If linked item.has_serial_no=1, require serial_no
- Enforce uniqueness on asset_tag/serial_no via doctype uniqueness + fallback validate check

No ledger writes.

---

### Inventory Ledger Entry controller (`inventory_ledger_entry.py`)
Implement `validate()`:
- Block manual edits:
  - if not doc.is_new(): throw
- Block deletes via permissions (and optionally `on_trash` throw)

Ledger created only via helper `inventory_ledger.create_entries(...)`.

---

### Inventory Transfer controller (`inventory_transfer.py`)
Implement:
- `validate()`:
  - from_location != to_location
  - validate each row against hard-fail rules
- `on_submit()`:
  - call shared validator
  - call shared ledger writer
  - update Inventory Unit custody for serial rows
- `on_cancel()`:
  - Phase 1: disallow cancel (HF) OR write reversal ledger (choose one and document)
  - Default Phase 1: HF on cancel to keep audit simple

---

### Inventory Issue controller (`inventory_issue.py`)
Implement:
- `validate()`:
  - enforce issued_to_type + exact one issued_to_*
  - validate each row (serial/consumable rules)
  - acknowledgment consistency rules (if terms_accepted)
- `on_submit()`:
  - write ledger entries
  - update Inventory Unit custody/status for serial rows
- `on_cancel()`:
  - Phase 1 default: HF on cancel

---

### Inventory Return controller (`inventory_return.py`)
Implement:
- `validate()`:
  - enforce returned_from_type + exact one returned_from_*
  - validate each row (custody match, status match)
- `on_submit()`:
  - write ledger entries
  - update Inventory Unit custody/status for serial rows
- `on_cancel()`:
  - Phase 1 default: HF on cancel

---

### Inventory Incident controller (`inventory_incident.py`)
Implement:
- `validate()`:
  - incident_type required
  - suggested_amount defaults from item.standard_rate if missing
- `on_submit()`:
  - if incident_type=Lost: set unit.status="Lost"
  - if incident_type=Damaged: set unit.condition="Damaged" (optional) and keep status
  - do not create accounting docs

---

### Inventory Repair Ticket controller (`inventory_repair_ticket.py`)
Implement:
- `validate()`:
  - block if unit.status in {Lost, Retired}
- `on_submit()` or `after_insert()` (choose one; prefer on_submit):
  - set unit.status="Under Repair"
- Add method `close_ticket()` (whitelisted or workflow event):
  - set ticket status Closed
  - if unit has a location custodian → unit.status="Available"

---

## 3) Shared helper contracts (must exist)

### inventory_validations.py
Must expose:
- `validate_issue(doc)`
- `validate_return(doc)`
- `validate_transfer(doc)`
- `validate_unit_custody(unit_doc_or_fields)`
All implement the Hard-Fail Matrix from inventory_notes.md.

### inventory_ledger.py
Must expose:
- `make_ledger_entries(voucher_type, voucher_name, posting_datetime, rows)`
Rows are normalized dicts:
- inventory_item
- inventory_unit (optional)
- from_location / to_location
- qty_change
- remarks

Must:
- insert in bulk (one DB round-trip)
- throw if no rows

### inventory_utils.py
Must expose:
- `resolve_issued_to(doc)` → returns {type, name} for issued_to
- `resolve_returned_from(doc)` → returns {type, name}
- `set_unit_custody(unit_name, custody_fields)` → bulk-safe helper
- `assert_unit_in_location(unit_name, location)`
- `assert_unit_held_by(unit_name, custodian_type, custodian_name)`

---

## 4) Bulk endpoints (Codex must implement)

### `ifitwala_ed/api/inventory.py`
Whitelisted:
- `bulk_issue(payload)`
- `bulk_return(payload)`

Payload rules:
- Flat payload (no `{payload: ...}` wrapper)
- Must accept keyword args or parse JSON string (match your canonical API shape)

Bulk must:
- validate inputs strictly
- reuse the same validation + mutation helpers as doctype controllers
- support up to N=500 rows (batch insert ledger entries)

---

## 5) Phase 1 acceptance criteria (must pass)

1. Can create Inventory Items and Units
2. Can issue serial units to:
   - Employee
   - Student
   - Guardian
   - Location
3. Can return serial units from those custodians to a Location
4. Can transfer serial units between Locations
5. Can issue/return consumables by qty (no unit)
6. Ledger entries exist for every submit action
7. Reports produce correct lists
8. Hard-fail matrix enforced (no illegal transitions)
9. Bulk issue/return works with the same invariants

---

## 6) Phase 1 explicit hard choices

### Cancel behavior
Default Phase 1:
- Disallow cancel for Transfer/Issue/Return (HF)
Rationale: prevents ledger reversal complexity in v1.

If you later want cancel support:
- Implement reversal ledger entries (ERPNext style).

---

## 7) What Codex must NOT do

- Do not create any child doctype controllers
- Do not write accounting entries or invoices
- Do not store stock balances as fields (derive from ledger)
- Do not infer Account Holder from Guardian automatically
- Do not allow editing/deleting ledger entries

---
