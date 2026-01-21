# Phase 02 — Admissions Intelligence

**PR Breakdown (One PR per Concern Group)**

> Phase 02 adds **meaning**, not mechanics.
> No promotion changes. No portal UX. No automation.

---

## **PR-02.1 — Applicant Interview (Staff-Only, Informational)**

### Scope

Introduce **Applicant Interview** as a first-class admissions artifact.

### Changes

* New DocType: `Applicant Interview`
* Fields (conceptual, not UX-driven):

  * `student_applicant` (Link, required)
  * `interview_type` (Family / Student / Joint)
  * `interviewers` (multi staff)
  * `date`, `mode`
  * `notes`
  * `outcome_impression` (non-binding)
  * `confidentiality_level`
* Permissions:

  * Staff only
  * No family access
* Multiple interviews per Applicant allowed

### Hard rules

* ❌ No status mutation
* ❌ No auto-approval / rejection
* ❌ Not copied to Student on promotion

### Acceptance

* Interviews exist purely to **inform review**
* Timeline entries are auditable

---

## **PR-02.2 — Applicant Health Profile (Pre-Student Health Staging)**

### Scope

Create a **pre-student health container** without touching `Student Patient`.

### Changes

* New DocType: `Applicant Health Profile`
* Linked to `Student Applicant`
* Family-editable (until Submitted)
* Staff review flags:

  * complete / needs follow-up / cleared
* No medical enforcement yet

### Hard rules

* ❌ No `Student Patient` creation
* ❌ No health data written to Student
* ❌ No promotion side effects

### Acceptance

* Health data can be reviewed safely pre-student
* Promotion later can selectively map data

---

## **PR-02.3 — Applicant Policy Acknowledgements (Versioned Consent)**

### Scope

Track **explicit, versioned consent** required for approval.

### Changes

* New DocType: `Applicant Policy Acknowledgement`
* Linked to:

  * `Student Applicant`
  * Policy version (static reference)
* Fields:

  * acknowledged_at
  * acknowledged_by (guardian)
* Immutable once acknowledged

### Hard rules

* ❌ No “checkbox only” logic
* ❌ No implicit consent
* ❌ No Student writes

### Acceptance

* Approval can later assert “policy X vY acknowledged”
* Legal traceability guaranteed

---

## **PR-02.4 — Applicant Documents & Review Flags**

### Scope

Enable document intake **without polluting Student records**.

### Changes

* New DocType: `Applicant Document`
* Linked to `Student Applicant`
* Fields:

  * document_type
  * file
  * review_status (pending / approved / rejected)
  * staff_notes
* Multiple documents per type allowed

### Hard rules

* ❌ No automatic copying to Student
* ❌ Rejected documents stay rejected
* ❌ No file moves yet (Phase 3)

### Acceptance

* Staff can review completeness meaningfully
* Rejections do not leak into canonical records

---

## **PR-02.5 — Applicant Completeness & Readiness Evaluation (Read-Only Logic)**

### Scope

Provide **deterministic readiness checks** without enforcing transitions yet.

### Changes

* Computed helpers on `Student Applicant`:

  * has_required_interviews()
  * has_required_policies()
  * has_required_documents()
  * health_review_complete()
* Read-only indicators only (no blocking yet)

### Hard rules

* ❌ No lifecycle enforcement
* ❌ No status auto-changes
* ❌ No school-specific branching (Phase 1.5 later)

### Acceptance

* Staff can *see* why an Applicant isn’t ready
* No automation creep

---

## **PR-02.6 — Applicant Review UX (Desk-Only, Optional)**

> Optional but recommended if staff need visibility.

### Scope

Minimal Desk affordances to **review**, not decide.

### Changes

* Sectioned views on Applicant:

  * Interviews
  * Health summary
  * Policies
  * Documents
* Read-only aggregates
* No buttons that mutate status

### Hard rules

* ❌ No portal
* ❌ No approvals
* ❌ No promotion triggers

### Acceptance

* Staff can review without exporting data
* UX does not encode logic

---

# Phase 02 — Global Constraints (Apply to ALL PRs)

* ❌ No promotion changes

* ❌ No Student / Student Patient writes

* ❌ No automation

* ❌ No portal / SPA assumptions

* ❌ No school-specific logic (Phase 1.5 first)

* ✅ All data is Applicant-scoped

* ✅ All mutations are auditable

* ✅ All logic is server-side

---

# Phase 02 Completion Checklist (PR Blocker)

Phase 02 is **done** only if:

* [ ] Interviews exist and are staff-only
* [ ] Health data is staged pre-Student
* [ ] Policies are versioned and explicit
* [ ] Documents are reviewable without pollution
* [ ] Applicant readiness is *observable*, not enforced
* [ ] No promotion logic changed
* [ ] No UX weakened contracts

If any box fails → Phase 02 is incomplete.

---




Below is the **Applicant Document – Doctype Contract (v1)**.
This is written as a **canonical contract**, not implementation chatter.

---

# Applicant Document — Doctype Contract (Phase 02)

## 1. Purpose (non-negotiable)

`Applicant Document` is the **semantic owner of all admission-related files**.

It exists to:

* Attach meaning to uploaded files (what this document *is*)
* Control review, approval, and rejection
* Gate promotion to Student records
* Decouple admissions logic from raw File handling

**No admissions file should be attached directly to `Student Applicant`.**

---

## 2. Position in the Admissions Model

```
Inquiry
  ↓
Student Applicant
  ↓
Applicant Document  ←── FILES LIVE HERE
  ↓
(Student promotion – Phase 03)
```

* One `Student Applicant` → many `Applicant Document`
* One `Applicant Document` → many `File` (versioned)

---

## 3. Core Invariants

These rules define correctness.

1. Every uploaded admissions file **must** be attached to an `Applicant Document`
2. An `Applicant Document` represents **one logical document type**
3. Files under one Applicant Document form a **versioned slot**
4. Promotion eligibility is decided **here**, not in File utilities
5. Rejected documents are **never deleted automatically**

---

## 4. Fields (authoritative)

### 4.1 Identity & Linking

| Field               | Type                     | Notes                                     |
| ------------------- | ------------------------ | ----------------------------------------- |
| `student_applicant` | Link → Student Applicant | **Required**, immutable after insert      |
| `document_type`     | Link / Select            | e.g. Passport, Transcript, Recommendation |
| `document_label`    | Data                     | Human-friendly name (optional override)   |

---

### 4.2 Review & Status

| Field           | Type        | Notes                                           |
| --------------- | ----------- | ----------------------------------------------- |
| `review_status` | Select      | `Pending`, `Approved`, `Rejected`, `Superseded` |
| `reviewed_by`   | Link → User | Set on approval/rejection                       |
| `reviewed_on`   | Datetime    | System-managed                                  |
| `review_notes`  | Text        | Staff-only                                      |

**Defaults**

* `review_status = Pending`

---

### 4.3 Promotion Control (Phase-aware)

| Field              | Type       | Notes                                |
| ------------------ | ---------- | ------------------------------------ |
| `is_promotable`    | Check      | Computed or rule-driven              |
| `promotion_target` | Select     | `Student`, `Student Portfolio`, etc. |
| `promotion_notes`  | Small Text | Why / how this document promotes     |

> `is_promotable` **must never** be manually checked without review.

---

### 4.4 File Slot Semantics (derived, not user-editable)

These are **not form fields**, but conceptual bindings:

* One Applicant Document = one **logical file slot**
* Slot key:

  ```
  (Student Applicant, document_type)
  ```

---

## 5. File Attachment Rules

### 5.1 Where files attach

* `File.attached_to_doctype = "Applicant Document"`
* `File.attached_to_name = applicant_document.name`

Direct attachment to `Student Applicant` is **invalid** (UI + server validation).

---

### 5.2 Routing contract (mandatory)

`Applicant Document` **must implement**:

```python
def get_file_routing_context(self, file_doc) -> dict
```

#### Required return keys

```python
{
  "root_folder": "Home/Admissions",
  "subfolder": "Applicant/<APPLICANT_ID>/Documents/<DOCUMENT_TYPE>",
  "file_category": "Admissions Applicant Document",
  "logical_key": "<DOCUMENT_TYPE>"
}
```

This enables:

* Correct folder placement
* Correct versioning
* Clean separation of concerns

---

## 6. Versioning Rules

* Versioning is **always enabled** for Applicant Documents
* Every upload creates a new version
* Only one file per slot is marked `custom_is_latest = 1`
* Rejected documents may still have newer versions uploaded

**No file is ever overwritten in-place.**

---

## 7. Validation Rules

### 7.1 On insert

* `student_applicant` is required
* `document_type` is required
* Enforce uniqueness:

  ```
  (student_applicant, document_type) must be unique
  ```

  → Multiple files = versions, not multiple rows

---

### 7.2 On delete

* Deletion is **restricted**
* Only allowed when:

  * No files attached, OR
  * System Manager override

Otherwise: soft-fail with explanation.

---

## 8. Permissions (policy-level)

### 8.1 Who can upload files

* Academic Admin
* Admissions Officer (future role)
* System Manager

### 8.2 Who can approve/reject

* Academic Admin
* System Manager

### 8.3 Applicant / Guardian

* **No access** in Phase 02
* Portal exposure is Phase 04+

---

## 9. Promotion Contract (Phase 03 dependency)

`Applicant Document` is the **only source of truth** for promotion.

Promotion logic must:

1. Check `review_status == Approved`
2. Check `is_promotable == 1`
3. Promote **latest version only**
4. Copy or re-link file (never destructive move)
5. Preserve Applicant-side history

No implicit promotion. Ever.

---

## 10. Explicit Non-Goals (for discipline)

This doctype does **not**:

* Decide *when* promotion happens
* Create Student records
* Send notifications
* Enforce curriculum-specific requirements

It provides **clean, auditable state** only.

---

## 11. Phase Compatibility

| Phase    | Status                          |
| -------- | ------------------------------- |
| Phase 02 | **Required**                    |
| Phase 03 | Promotion gate                  |
| Phase 04 | Guardian / applicant upload UI  |
| Phase 05 | Analytics & completeness checks |

---

## Final judgment

This contract:

* Fits your existing file architecture
* Avoids logic leakage into utilities
* Scales to complex admissions policies
* Survives real-world school imports and audits

