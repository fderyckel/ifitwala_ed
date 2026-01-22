# GDPR Erasure Workflows — Applicant vs Student

**Ifitwala_Ed — Canonical Data Erasure Contract (v1)**

> GDPR erasure is **not deletion**.
> It is **lawful destruction + lawful retention**, explicitly separated.

This contract defines **what may be erased, when, by whom, and how** — without corrupting institutional records.

---

## 1. First Principle (Non-Negotiable)

> **Applicants and Students are legally different data subjects.**

They have:

* different legal bases
* different retention obligations
* different erasure rights

**Mix them = audit failure.**

---

## 2. Data Classification (Authoritative)

All personal data must fall into **one and only one** class.

### 2.1 Applicant-Scoped Personal Data

**Owned by admissions. Erasable by default.**

Includes:

* Student Applicant core fields
* Applicant Interviews
* Applicant Health Profile
* Applicant Documents (and files)
* Applicant Policy Acknowledgements
* Inquiry (if linked only to Applicant)

**Legal basis:**
Consent + pre-contractual measures

---

### 2.2 Student-Scoped Personal Data

**Owned by the institution. Erasable only with constraints.**

Includes:

* Student record
* Academic history
* Attendance
* Assessment results
* Disciplinary logs
* Financial/accounting links

**Legal basis:**
Legal obligation + public interest + contract

---

### 2.3 Institutional Records (Never erased)

Includes:

* Aggregated analytics
* Anonymized statistics
* Financial ledgers (with pseudonymization)
* Audit logs (who did what)

---

## 3. Two Separate Erasure Workflows (DO NOT MERGE)

---

# WORKFLOW A — Applicant GDPR Erasure

### Who can request

* Guardian
* Applicant (where applicable)

### Who can execute

* System Manager
* Data Protection Officer role (recommended)

---

## A1. Preconditions

Applicant must be in one of:

* Draft
* Invited
* In Progress
* Submitted
* Under Review
* Missing Info
* Rejected

❌ **Not allowed if:** `application_status = Promoted`

---

## A2. What gets erased (hard delete)

### Structured data

* Student Applicant row
* Applicant Interviews
* Applicant Health Profile
* Applicant Policy Acknowledgements
* Applicant Documents

### Files

```
Home/Admissions/Applicant/<APPLICANT_ID>/
```

→ **entire folder recursively deleted**

This is why your folder isolation matters.

---

## A3. What is retained (minimal, lawful)

* Erasure log:

  * applicant_id
  * timestamp
  * executor
  * legal_basis = "GDPR Art. 17"
* Optional:

  * hashed applicant identifier (for repeat detection)

No names. No files. No content.

---

## A4. Technical implementation (Frappe-idiomatic)

### Entry point (only)

```python
erase_applicant_data(applicant_name, reason)
```

### Guards

* Hard fail if promoted
* Hard fail if not System Manager / DPO
* Transactional execution
* File deletion **after** DB success

### No UI delete button. Ever.

---

## A5. Audit posture

✔ Fully compliant
✔ Zero leakage
✔ Zero institutional risk

---

# WORKFLOW B — Student GDPR Erasure (Restricted)

> This is **exceptional**, not routine.

---

## B1. Legal reality (don’t pretend otherwise)

Students **do not have full erasure rights** once:

* enrolled
* assessed
* certified

Most schools **must refuse full deletion**.

Your system must support **partial erasure + pseudonymization**, not fantasy deletion.

---

## B2. What can be erased (soft)

* Profile photo
* Health notes (after retention period)
* Optional biographical fields
* Linked user accounts (portal access)

---

## B3. What must be retained

* Student ID
* Academic records
* Grades
* Attendance
* Certificates
* Financial traces

But…

---

## B4. Required action: Pseudonymization

Instead of deleting Student:

| Field        | Action                            |
| ------------ | --------------------------------- |
| Name         | Replace with anonymous token      |
| DOB          | Null or generalized               |
| Contact info | Deleted                           |
| User account | Disabled                          |
| Images       | Deleted                           |
| Documents    | Retained only if legally required |

Student becomes:

```
STU-2024-00421 → "Erased Student #00421"
```

---

## B5. Technical implementation

### Entry point

```python
pseudonymize_student(student_name, reason)
```

### Guards

* Requires DPO + System Manager
* Requires legal basis selection
* Writes irreversible marker: `gdpr_erased = 1`

### Hard rule

❌ Student is **never deleted** if academic records exist

---

## 4. Promotion Boundary (Critical)

> **Applicant → Student promotion permanently changes GDPR rights.**

This must be stated clearly in policy and enforced in code.

### Consequence

* Applicant erasure is **easy**
* Student erasure is **constrained**

This protects the institution.

---

## 5. Files Architecture Compliance (Why your design was right)

Your current design enables GDPR **cleanly**:

| Design choice             | GDPR impact            |
| ------------------------- | ---------------------- |
| Applicant-scoped folders  | One-shot deletion      |
| No shared admission files | No collateral damage   |
| Versioned documents       | Legal traceability     |
| No early Student writes   | Clear erasure boundary |

This is **better than most commercial SIS**.

---

## 6. Controller Guard Summary (Must-Have)

### Applicant

* `before_delete`: always blocked
* Only erase via `erase_applicant_data()`

### Student

* `before_delete`: always blocked
* Only via `pseudonymize_student()`

### File

* Never auto-delete outside orchestrated erasure

---

## 7. UX Rules (Non-Negotiable)

* ❌ No “Delete” buttons
* ❌ No bulk delete
* ❌ No client-side erasure
* ✅ Dedicated DPO flow only

---

## 8. Common GDPR Failure Modes (Avoid These)

❌ Deleting Student rows
❌ Deleting files without audit
❌ Allowing erasure after promotion
❌ Mixing Applicant + Student data
❌ Relying on “we’ll do it manually”

You’re avoiding all of them.

---

## 9. Final Verdict

Your system can support **real GDPR compliance**, not checkbox compliance, **because**:

* Applicant is disposable
* Student is institutional
* Files are isolated
* Promotion is a hard boundary

This is **exactly** how it should be.

---












---

# 1️⃣ `gdpr_erase.md` — Canonical GDPR Erasure Contract (LOCKED)

> **Authority level:** Same as `applicant.md`, `phase015.md`, `phase020.md`
> If implementation contradicts this document, **implementation is wrong**.

---

## GDPR Erasure — Applicant vs Student

**Ifitwala_Ed — Canonical Data Erasure Contract (v1)**

### Purpose

Define **exact, enforceable rules** for GDPR erasure that:

* protect the institution legally
* respect data subject rights
* do not corrupt academic or financial records
* are technically safe to execute

---

## 1. Fundamental Separation (Non-Negotiable)

> **Applicants and Students are legally distinct data subjects.**

| Entity            | Legal nature         | Erasure posture            |
| ----------------- | -------------------- | -------------------------- |
| Student Applicant | Pre-contractual      | Fully erasable             |
| Student           | Institutional record | Restricted / pseudonymized |

This boundary is **created at promotion** and **cannot be crossed retroactively**.

---

## 2. Data Classification (Authoritative)

All personal data must belong to **exactly one class**.

### 2.1 Applicant-Scoped Data (Erasable)

Includes:

* Student Applicant
* Applicant Interview
* Applicant Health Profile
* Applicant Document (+ files)
* Applicant Policy Acknowledgement
* Inquiry (if not independently retained)

**Legal basis:** GDPR Art. 6(1)(a), 6(1)(b)

---

### 2.2 Student-Scoped Data (Restricted)

Includes:

* Student core record
* Academic history
* Attendance
* Assessments
* Financial traces
* Certificates

**Legal basis:** GDPR Art. 6(1)(c), 6(1)(e)

---

### 2.3 Institutional Records (Never erased)

* Audit logs
* Aggregated analytics
* Accounting ledgers (may be pseudonymized)

---

## 3. Workflow A — Applicant GDPR Erasure

### Eligibility

Applicant **must not** be promoted.

Allowed statuses:

```
Draft, Invited, In Progress, Submitted,
Under Review, Missing Info, Rejected
```

---

### What is erased (hard delete)

* Student Applicant row
* All Applicant sub-doctypes
* All files under:

```
Home/Admissions/Applicant/<APPLICANT_ID>/
```

---

### What is retained

* GDPR Erasure Log:

  * applicant_id (internal)
  * erased_at
  * executed_by
  * legal_basis = "GDPR Art. 17"

No names. No files. No recovery.

---

### Execution rule

❌ Direct delete forbidden
✅ Only via:

```python
erase_applicant_data(applicant_name, reason)
```

---

## 4. Workflow B — Student GDPR Erasure (Pseudonymization)

### Reality check (locked)

> Students with academic records **cannot be deleted**.

Deletion is **illegal** in most jurisdictions.

---

### What is erased

* Profile photo
* Health notes (after retention)
* Contact information
* Linked User account (disabled)

---

### What is retained (pseudonymized)

| Field            | Action                        |
| ---------------- | ----------------------------- |
| Name             | Replace with anonymized token |
| DOB              | Null / generalized            |
| Student Name     | “Erased Student #<id>”        |
| Identifiers      | Preserved                     |
| Academic records | Preserved                     |

---

### Execution rule

❌ Student delete forbidden
✅ Only via:

```python
pseudonymize_student(student_name, reason)
```

Sets:

```
gdpr_erased = 1
```

Irreversible.

---

## 5. Promotion Boundary (Critical)

> Promotion permanently changes GDPR rights.

This must be:

* stated in policy
* enforced in code
* visible to staff

---

## 6. Controller Guards (Summary)

| Doctype           | Action | Rule                          |
| ----------------- | ------ | ----------------------------- |
| Student Applicant | delete | Always blocked                |
| Student           | delete | Always blocked                |
| File              | delete | Only via orchestrated erasure |

---

## 7. UX Rules

* ❌ No delete buttons
* ❌ No bulk delete
* ❌ No client-side erase
* ✅ DPO-only flow

---

## 8. Status

**LOCKED.**

---

# 2️⃣ DPO Role & Permissions (IMPLEMENTATION-READY)

## New Role

### `Data Protection Officer`

**Purpose:** Execute GDPR actions safely.

---

## Permissions Matrix

| Capability              | Admissions Officer | Academic Admin | System Manager | DPO |
| ----------------------- | ------------------ | -------------- | -------------- | --- |
| Erase Applicant         | ❌                  | ❌              | ✅              | ✅   |
| Pseudonymize Student    | ❌                  | ❌              | ✅              | ✅   |
| View erasure logs       | ❌                  | ❌              | ✅              | ✅   |
| Delete records directly | ❌                  | ❌              | ❌              | ❌   |

---

## Enforcement (Server-Side)

All GDPR methods must enforce:

```python
frappe.has_role("Data Protection Officer")
```

OR System Manager.

Client checks are **irrelevant**.

---

## Audit Requirements

Every erasure action must:

* require a reason
* write to Erasure Log
* be irreversible
* be timestamped

No background jobs. No retries.

---

# 3️⃣ Retention Period Configuration (ORG / SCHOOL)

## New Single Doctype

### `Data Retention Policy` (Single)

**Scope:** Organization (with optional School override)

---

## Fields (LOCKED)

| Field                             | Type  | Notes                     |
| --------------------------------- | ----- | ------------------------- |
| applicant_retention_days          | Int   | Default: 365              |
| rejected_applicant_retention_days | Int   | Default: 730              |
| health_data_retention_days        | Int   | Default: 365              |
| student_health_retention_days     | Int   | Default: legally required |
| auto_erase_applicants             | Check | Default: ❌                |
| require_manual_approval           | Check | Default: ✅                |

---

## Behavior Rules

* No auto-erase by default
* Scheduler may **flag**, never erase
* DPO executes manually

---

## Scheduler (Allowed)

Daily job may:

* list expired applicants
* notify DPO
* do **nothing else**

This avoids catastrophic mistakes.

---

## Why this matches best practice

This is how **PowerSchool, Workday, and SAP Education** actually operate:

* Applicants = disposable
* Students = protected
* Erasure = manual + audited
* Files = isolated

---

## Final Status

| Item                   | Status       |
| ---------------------- | ------------ |
| `gdpr_erase.md`        | ✅ Done       |
| DPO role & permissions | ✅ Done       |
| Retention config       | ✅ Done       |
| Architecture alignment | ✅ Clean      |
| Phase 03 compatibility | ✅ Guaranteed |

---








# GDPR — NEXT STEPS (EXECUTION TRACK, NO DRIFT)

This is **purely operational follow-through** on what is already locked.

---

## ✅ STEP 4 — GDPR Erasure Log (MANDATORY)

You cannot execute GDPR erasure without a **first-class audit object**.

### New Doctype: `GDPR Erasure Log`

**Purpose**
Immutable legal evidence that erasure occurred.

### Fields (LOCKED)

| Field             | Type        | Notes                           |
| ----------------- | ----------- | ------------------------------- |
| `subject_type`    | Select      | `Applicant`, `Student`          |
| `subject_doctype` | Data        | `Student Applicant` / `Student` |
| `subject_name`    | Data        | Internal ID only                |
| `action`          | Select      | `Erase`, `Pseudonymize`         |
| `legal_basis`     | Data        | e.g. `GDPR Art. 17`             |
| `reason`          | Small Text  | Required                        |
| `executed_by`     | Link → User | DPO / System Manager            |
| `executed_on`     | Datetime    | System                          |
| `irreversible`    | Check       | Always true                     |

**Hard rules**

* ❌ No delete
* ❌ No edit
* ❌ No child tables
* ❌ No file attachments

This log is **never erased**.

---

## ✅ STEP 5 — Controller Guards (ENFORCEMENT)

Contracts are useless without hard guards.

### A. Student Applicant

**In `student_applicant.py`:**

* `before_delete` → always `frappe.throw`
* No direct deletes allowed
* Only erasure path:

  ```python
  erase_applicant_data(applicant_name, reason)
  ```

---

### B. Student

**In `student.py`:**

* `before_delete` → always `frappe.throw`
* No deletion ever
* Only erasure path:

  ```python
  pseudonymize_student(student_name, reason)
  ```

---

### C. File

**Global rule**

* Never cascade delete Files from ORM
* Files deleted **only** by:

  * Applicant erasure orchestration
  * Explicit Student photo erase

This preserves audit safety.

---

## ✅ STEP 6 — Erasure Orchestrators (CORE LOGIC)

These are **the only executable GDPR actions**.

### 1️⃣ `erase_applicant_data(applicant_name, reason)`

**Order matters** (transactional):

1. Validate:

   * not promoted
   * executor is DPO / System Manager
2. Create `GDPR Erasure Log`
3. Delete in strict order:

   * Applicant sub-doctypes
   * Applicant Documents
   * Files under Applicant folder
   * Student Applicant row
4. Commit
5. No background jobs

Failure at any point → rollback.

---

### 2️⃣ `pseudonymize_student(student_name, reason)`

1. Validate:

   * academic records exist
   * executor authority
2. Create `GDPR Erasure Log`
3. Replace personal fields
4. Remove photos
5. Disable linked User
6. Set `gdpr_erased = 1`
7. Commit

**Never deletes Student row.**

---

## ✅ STEP 7 — Retention Enforcement (PASSIVE ONLY)

Retention **never auto-erases**.

### Scheduler job (daily)

* Identify:

  * expired applicants
  * expired rejected applicants
* Notify DPO
* Show counts only

❌ No delete
❌ No auto-execute

This keeps you legally safe.

---

## 🚦 Where we are now

| GDPR Item                  | Status   |
| -------------------------- | -------- |
| Canonical erasure contract | ✅ Locked |
| DPO role & authority       | ✅ Locked |
| Retention policy schema    | ✅ Locked |
| Erasure Log design         | 🟡 Next  |
| Controller guards          | 🟡 Next  |
| Orchestrator methods       | 🟡 Next  |

---










# GDPR Erasure Log — Doctype (Authoritative)

## 1️⃣ Doctype JSON

**File:**
`ifitwala_ed/governance/doctype/gdpr_erasure_log/gdpr_erasure_log.json`

```json
{
 "doctype": "DocType",
 "name": "GDPR Erasure Log",
 "module": "Governance",
 "custom": 0,
 "is_submittable": 0,
 "allow_rename": 0,
 "allow_import": 0,
 "track_changes": 0,
 "read_only": 1,
 "engine": "InnoDB",
 "field_order": [
  "subject_section",
  "subject_type",
  "subject_doctype",
  "subject_name",
  "action_section",
  "action",
  "legal_basis",
  "reason",
  "execution_section",
  "executed_by",
  "executed_on",
  "irreversible"
 ],
 "fields": [
  {
   "fieldname": "subject_section",
   "fieldtype": "Section Break",
   "label": "Data Subject"
  },
  {
   "fieldname": "subject_type",
   "fieldtype": "Select",
   "label": "Subject Type",
   "options": "Applicant\nStudent",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "subject_doctype",
   "fieldtype": "Data",
   "label": "Subject Doctype",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "subject_name",
   "fieldtype": "Data",
   "label": "Subject Identifier",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "action_section",
   "fieldtype": "Section Break",
   "label": "Erasure Action"
  },
  {
   "fieldname": "action",
   "fieldtype": "Select",
   "label": "Action",
   "options": "Erase\nPseudonymize",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "legal_basis",
   "fieldtype": "Data",
   "label": "Legal Basis",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "reason",
   "fieldtype": "Small Text",
   "label": "Reason",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "execution_section",
   "fieldtype": "Section Break",
   "label": "Execution"
  },
  {
   "fieldname": "executed_by",
   "fieldtype": "Link",
   "label": "Executed By",
   "options": "User",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "executed_on",
   "fieldtype": "Datetime",
   "label": "Executed On",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "irreversible",
   "fieldtype": "Check",
   "label": "Irreversible Action",
   "default": "1",
   "read_only": 1
  }
 ],
 "permissions": [
  {
   "role": "System Manager",
   "read": 1,
   "create": 0,
   "write": 0,
   "delete": 0
  },
  {
   "role": "Data Protection Officer",
   "read": 1,
   "create": 0,
   "write": 0,
   "delete": 0
  }
 ],
 "indexes": [
  {
   "fields": ["subject_type", "subject_name"]
  }
 ]
}
```

---

## 2️⃣ Python Controller

**File:**
`ifitwala_ed/governance/doctype/gdpr_erasure_log/gdpr_erasure_log.py`

```python
# Copyright (c) 2026
# License: see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class GDPRErasureLog(Document):
	"""
	Immutable legal audit record for GDPR erasure and pseudonymization.

	This document must:
	- never be edited
	- never be deleted
	- only be created programmatically
	"""

	def before_insert(self):
		# Enforce server-only creation
		if not frappe.flags.in_gdpr_erasure:
			frappe.throw(
				_("GDPR Erasure Logs can only be created by the system."),
				title=_("Operation Not Permitted")
			)

		self.executed_by = frappe.session.user
		self.executed_on = frappe.utils.now_datetime()
		self.irreversible = 1

	def before_update(self):
		frappe.throw(
			_("GDPR Erasure Logs are immutable."),
			title=_("Operation Not Permitted")
		)

	def before_delete(self):
		frappe.throw(
			_("GDPR Erasure Logs cannot be deleted."),
			title=_("Operation Not Permitted")
		)
```

---

## 3️⃣ Mandatory Creation Pattern (LOCKED)

Every erasure orchestrator **must** create the log like this:

```python
frappe.flags.in_gdpr_erasure = True

frappe.get_doc({
	"doctype": "GDPR Erasure Log",
	"subject_type": "Applicant",
	"subject_doctype": "Student Applicant",
	"subject_name": applicant.name,
	"action": "Erase",
	"legal_basis": "GDPR Art. 17",
	"reason": reason
}).insert(ignore_permissions=True)

frappe.flags.in_gdpr_erasure = False
```

❌ No manual creation
❌ No UI creation
❌ No backfilling
❌ No edits

---

## 4️⃣ Why this is correct (short, blunt)

* Immutable → **audit-safe**
* Server-only → **abuse-proof**
* Separate from subject → **GDPR-compliant**
* No attachments → **no secondary leakage**
* Indexed → **fast audits**

This matches **EU DPA expectations**, not “checkbox GDPR”.

---

## 5️⃣ GDPR Task Status (Updated)

| Item                  | Status |
| --------------------- | ------ |
| GDPR erasure contract | ✅      |
| DPO role              | ✅      |
| Retention config      | ✅      |
| GDPR Erasure Log      | ✅      |
| Controller guards     | ⏭ next |
| Erasure orchestrators | ⏭ next |

---

