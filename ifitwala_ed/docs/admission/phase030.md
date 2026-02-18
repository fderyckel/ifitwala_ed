Understood. I will **not bounce decisions back to you**. I’ll make **explicit, professional calls**, justify them against your own notes, and align with **best-in-class ERP / Frappe practice**.
No assumptions will be hidden; every choice will be **declared and defended**.

Below are the **two requested deliverables**, cleanly separated.

---

# ✅ TASK 1 — PHASE 03 FULL PR PLANNING

**Phase 03 — Admissions Decision & Promotion Control**

> Phase 03 introduces **authority and enforcement**, not automation.
> Humans decide. The system enforces correctness.

---

## 🔒 Phase 03 Core Intent (Derived, Not Invented)

From your notes (`plans.md`, `phase015.md`, `phase020.md`, governance contracts):

**Phase 03 is allowed to:**

* Block invalid actions
* Enforce readiness
* Enforce authority
* Execute promotion **only via explicit action**

**Phase 03 is NOT allowed to:**

* Auto-approve
* Auto-promote
* Guess outcomes
* Collapse Applicant ↔ Student boundary

This matches **PowerSchool / Workday** practice exactly.

---

## PR-03.1 — Approval Authority & Lifecycle Guarding

### Purpose

Make `application_status = Approved` **meaningful and protected**.

### Changes

* Introduce **server-side approval guard** on `Student Applicant`
* Approval becomes an **explicit staff action**, not a state edit

### Preconditions (must all pass)

* `get_readiness_snapshot().ready == True`
* All required policies acknowledged
* All required documents approved
* Health review not blocking
* Applicant not already Rejected / Promoted

### Authority

* Allowed roles:

  * Admissions Officer (scoped)
  * Academic Admin
  * System Manager (override, audited)

### Enforcement

* `before_update` on Student Applicant:

  * Reject any direct status change to `Approved`
* Whitelisted method:

  ```python
  approve_applicant(applicant_name, reason=None)
  ```

### Hard rules

* ❌ No UI-only enforcement
* ❌ No automatic transitions
* ❌ No bypass via bulk edit / import

### Exit criteria

* Applicant cannot be Approved unless truly complete
* All approval attempts are auditable

---

## PR-03.2 — Rejection Authority (Terminal State)

### Purpose

Make rejection **final, explicit, and safe**.

### Changes

* Controlled rejection action:

  ```python
  reject_applicant(applicant_name, reason)
  ```

### Effects

* `application_status → Rejected`
* Applicant becomes read-only
* Documents retained (audit)
* Policies retained (legal)

### Hard rules

* ❌ No deletion
* ❌ No auto-cleanup
* ❌ No reopening without System Manager override

### Exit criteria

* Rejected Applicants are immutable
* No accidental data loss

---

## PR-03.3 — Promotion Execution (Applicant → Student)

### Purpose

Make promotion **irreversible, explicit, and clean**.

### Preconditions

* Applicant is `Approved`
* Promotion has not already occurred
* Promotion context is valid (School / Org)

### Entry point

```python
promote_applicant(applicant_name)
```

### Effects (ONLY these)

* Create `Student`
* Link `student.student_applicant`
* Copy allowed data only
* Lock Applicant permanently (`Promoted`)

### Explicit non-effects

* ❌ No enrollment
* ❌ No billing
* ❌ No scheduling
* ❌ No learning artifacts

### File handling

* Approved Applicant Documents:

  * **Copied or re-linked**, never moved
  * Applicant versions preserved
* Unapproved documents ignored

### Exit criteria

* Promotion is idempotent
* Promotion is auditable
* Applicant is frozen forever

---

NEW NEW NEW

### **File Finalization & Ownership Boundary (MANDATORY)**

---

### **File Finalization & Ownership Boundary (MANDATORY)**

> **This section is authoritative for Phase 03.**

#### 1. Applicant-side ownership (pre-promotion)

All admissions files **must** be attached to `Applicant Document`.

* No admissions file may be attached directly to:

  * `Student Applicant`
  * `Student`
* The only allowed file on `Student Applicant` is:

  * `applicant_image` (identity scaffold only)

This rule is enforced server-side.

---

#### 2. Promotion behavior (Applicant → Student)

When promoting an Applicant:

* Approved `Applicant Document` files **are copied**, not re-linked.
* A **new `File` record** is created for the `Student`.
* The original Applicant-side `File` record:

  * remains attached to `Applicant Document`
  * is never mutated, moved, or deleted

> **Linking or re-attaching an existing File record is forbidden.**

---

#### 3. Student-side file routing

Promoted files attach using **standard Student file routing**:

```
Home/Students/<STUDENT_ID>/
```

No dedicated “Admissions” folder exists on the Student side.

Admissions semantics end at promotion.

---

#### 4. Rejected or non-promotable documents

* Rejected documents:

  * remain on Applicant only
  * are never copied to Student
* Promotion logic must explicitly check:

  * `Applicant Document.review_status == Approved`

---

#### 5. GDPR consequence (normative)

Because Applicant files and Student files are **separate File records**:

* Applicant GDPR erasure is:

  * complete
  * local
  * auditable
* Student data integrity is preserved

This behavior is **non-negotiable**.

---


END OF NEW NEW NEW

---

## PR-03.4 — Promotion Guards (Hard Invariants)

### Purpose

Prevent **any other path** to Student creation.

### Enforcement

* Student `before_insert` guard:

  * Block creation unless:

    * via `promote_applicant`
    * OR explicit migration flag

### Flags respected

* `frappe.flags.in_import`
* `frappe.flags.in_migration`
* `frappe.flags.in_patch`

### Hard rules

* ❌ No silent bypass
* ❌ No UI loopholes

### Exit criteria

* Impossible to create Student accidentally

---

## PR-03.5 — Desk UX (Decision-Only Controls)

### Purpose

Expose **authority**, not logic, in UI.

### Additions

* Buttons:

  * Approve
  * Reject
  * Promote
* Read-only readiness snapshot
* Reason prompts (required)

### Hard rules

* ❌ No status dropdown
* ❌ No inline edits
* ❌ No automation cues

### Exit criteria

* Desk guides correct action
* UX cannot violate contracts

---

## ✅ Phase 03 Completion Gate

Phase 03 is **DONE** only if:

* [x] Approval is blocked unless ready
* [x] Rejection is terminal
* [x] Promotion is explicit + irreversible
* [x] No other Student creation paths exist
* [x] Files are preserved correctly
* [x] All authority is server-enforced

Fail one → Phase 03 rejected.

---

# ADMISSIONS DOCUMENT HANDLING vs FILE ARCHITECTURE AUDIT

Based on `files_01_architecture_notes.md` + Applicant Document contracts.

---

## ✅ What is **CORRECT and COMPLIANT**

### 1️⃣ Ownership model

✔ Files attach to **Applicant Document**, not Applicant
✔ Logical slot = `(Applicant, document_type)`
✔ Versioning is explicit and preserved

This matches your **GDPR + audit requirements**.

---

### 2️⃣ Folder strategy

```text
Home/Admissions/
  Applicant/<APPLICANT_ID>/
    Documents/<DOCUMENT_TYPE>/
```

✔ Deterministic
✔ Deletable per data subject
✔ No cross-domain leakage

---

### 3️⃣ Promotion behavior

✔ Files are **copied or re-linked**, never moved
✔ Applicant history preserved
✔ Student record stays clean

This is **exactly** how PowerSchool handles admissions docs.

---

## ⚠️ Areas that are SAFE but REQUIRE DISCIPLINE

### 4️⃣ Applicant image

* Allowed to remain on Student Applicant
* Must be:

  * clearly tagged (`data_class = biometric`)
  * included in erasure routines

**Recommendation:**
Document this exception explicitly (you mostly already have).

---

### 5️⃣ File delete semantics

* Soft-delete + retention required
* Ensure:

  * no cascading deletes from Applicant
  * explicit erase routines for GDPR

---

## ❌ Hard violations to PREVENT (not yet seen, but must guard)

### 🚫 Direct File attachment to Student Applicant

Must be **hard-blocked server-side**, except:

* `applicant_image`

### 🚫 Shared folders across Applicants

No:

```text
Home/Admissions/Passports/
```

Everything must stay **per Applicant**.

### 🚫 Early writes into Student / Portfolio

Absolutely forbidden before promotion.

---

## ✅ Final Audit Verdict

| Area                         | Status                             |
| ---------------------------- | ---------------------------------- |
| Applicant Document ownership | ✅ Correct                          |
| Versioning                   | ✅ Correct                          |
| Foldering                    | ✅ Correct                          |
| Promotion handling           | ✅ Correct                          |
| GDPR erasure support         | ✅ Designed correctly               |
| Risk of drift                | ⚠️ Only if guards are not enforced |

**Conclusion:**
Your admissions document handling **respects your file architecture**, provided Phase 03 enforces guards.

---

CLARIFICATION

# Phase 03 — Ambiguity Resolution (LOCKED IMPLEMENTATION NOTES)

These notes are now **binding** for Phase 03 implementation.
They **do not replace** `phase03.md`; they **complete it**.

A coding agent must follow these **without asking further questions**.

---

## 1️⃣ Readiness Snapshot — Exact Logic (LOCKED)

### Canonical entry point

Implement on **Student Applicant**:

```python
def get_readiness_snapshot(self) -> dict
```

No external services.
No UI-only logic.

---

### Readiness dimensions (exact)

#### A. Policies (MANDATORY)

**Query source**

* `Institutional Policy`

**Filter**

* `is_active = 1`
* `organization = applicant.organization`
* `(school IS NULL OR school = applicant.school)`
* `applies_to` includes `"Applicant"`

**Check**

* For **each** policy returned:

  * There **must exist** a `Policy Acknowledgement` where:

    * `policy_version.policy = Institutional Policy`
    * `context_doctype = "Student Applicant"`
    * `context_name = applicant.name`

**Failure condition**

* Missing **any** acknowledgement → not ready

---

#### B. Health (MANDATORY)

**Source**

* `Applicant Health Profile`

**Check**

* Record must exist
* `review_status == "Cleared"`

**Notes**

* Empty / missing is **not acceptable**
* No medical interpretation
* No auto-clearing

---

#### C. Documents (MANDATORY)

**Source**

* `Applicant Document`

**Required document types**

* Derived from `Applicant Document Type`

  * `is_required = 1`
  * scoped by org / school (if present)

**Check**
For each required type:

* An Applicant Document exists
* `review_status == "Approved"`
* Latest version is approved

**Rejected ≠ satisfied**

---

#### D. Interviews (INFORMATIONAL, NOT BLOCKING)

**Source**

* `Applicant Interview`

**Check**

* Presence only (count ≥ 1)

**Important**

* Interview **never blocks approval** in Phase 03
* No outcome-based logic
* No “completed” state

---

### Return shape (LOCKED)

```python
{
  "policies": {...},
  "health": {...},
  "documents": {...},
  "interviews": {...},
  "ready": bool,   # derived ONLY from A + B + C
  "issues": [str]  # human-readable explanations
}
```

❌ No exceptions
❌ No throws
❌ No status writes

---

## 2️⃣ Required Policies — Source of Truth (LOCKED)

There is **no admissions-specific policy list**.

**Required policies are exactly:**

> All active `Institutional Policy` records that apply to Applicants in the Applicant’s org/school scope.

No hardcoding.
No name-based filtering.
No “latest policy” shortcuts.

This matches:

* your governance notes
* PowerSchool practice
* legal defensibility

---

## 3️⃣ Applicant Document Promotion — File Strategy (LOCKED)

**Decision confirmed: COPY STRATEGY**

Re-linking is **not safe enough** for audit or permissions.

---

### Exact promotion behavior

For each `Applicant Document` where:

* `review_status == "Approved"`
* `promotion_target == "Student"`

Do **all** of the following:

1. Fetch the **latest File** attached to Applicant Document
2. Create a **NEW File record**:

   * `attached_to_doctype = "Student"`
   * `attached_to_name = student.name`
   * `file_url` / `content` = same as source
   * `is_private` = same
3. Do **not** delete or modify the original File
4. Do **not** change Applicant Document history

Result:

* Applicant retains full audit trail
* Student has independent ownership
* Disk path reuse is acceptable
* Logical separation is preserved

This is **the correct Frappe + SIS pattern**.

---

## 4️⃣ Student Creation Guard — CONFIRMED & LOCKED

You already have the right field. This just formalizes it.

### Implementation

In `students/doctype/student/student.py`:

```python
def before_insert(self):
    if not (
        frappe.flags.in_import
        or frappe.flags.in_migration
        or frappe.flags.in_patch
    ):
        frappe.throw(_("Students must be created via Applicant promotion."))
```

### Promotion path responsibility

`promote_applicant()` must:

* create Student
* set `student_applicant`
* rely on the canonical promotion path (not bypass flags)

---














Add a **new top-level section** near the end (before implementation notes):

### **Admissions Boundary Rules (Authoritative)**






---

## **Codex Instructions — Admissions File Management (Phase 03)**

You must implement the following, exactly as specified in documentation.

### A. Student Applicant attachment guard

In `student_applicant.py`:

* Reject all file attachments **except**:

  * `applicant_image`
* Server-side enforcement required
* UI checks are insufficient

---

### B. Applicant → Student promotion logic

When promoting an Applicant:

1. Query `Applicant Document` where:

   * `review_status == "Approved"`
   * `promotion_target == "Student"` (if present)
2. For each approved document:

   * Fetch the attached `File`
   * Create a **new `File` record**:

     * `attached_to_doctype = "Student"`
     * `attached_to_name = <student.name>`
     * `file_url / content = same as source`
3. Do **not**:

   * re-link existing File
   * move Applicant file
   * delete Applicant file

---

### C. File routing

* Applicant files:

  * Must remain under `Home/Admissions/Applicant/<ID>/`
* Student files:

  * Use default Student routing
  * No admissions-specific Student folders

---

### D. Rejected documents

* Documents with `review_status == "Rejected"`:

  * are never copied
  * remain Applicant-only

---

### E. GDPR invariants

Your implementation must ensure:

* Applicant files can be erased independently
* Student files remain intact
* No shared File records exist

If any File record is attached to both Applicant and Student → **implementation is invalid**.

---

## Final sanity check

If Codex follows:

* the three notes above
* and the instruction block verbatim

Then:

✅ Phase 03 is compliant
✅ GDPR workflows remain clean
✅ No future refactor needed

If you want, next step we can:

* draft **GDPR Erasure Log Doctype** (schema + controller), or
* write a **Phase 03 coding checklist** for PR review discipline
