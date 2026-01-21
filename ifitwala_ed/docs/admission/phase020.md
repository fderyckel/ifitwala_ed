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





---

# PR-02.3 — Applicant Policy Acknowledgement

**End-to-End Contract Walkthrough (Authoritative)**

> Goal of PR-02.3:
>
> **Allow admissions staff to see whether required policies have been explicitly acknowledged by guardians for a Student Applicant — without enforcing, automating, or mutating lifecycle.**

Nothing more.

---

## 1️⃣ Data Model Entry Point (What actually gets created)

### Doctype used

✅ **`Policy Acknowledgement`** (global system)

No admissions-specific doctype.
No duplication.
No shortcuts.

---

### Fields populated (exact, no extras)

When an Applicant policy is acknowledged, the row **must** look like this:

```text
policy_version        → Policy Version (required)
acknowledged_by       → Guardian (User or Contact)
acknowledged_for      → "Applicant"
context_doctype       → "Student Applicant"
context_name          → <student_applicant.name>
acknowledged_at       → system datetime
```

❌ No `student` field
❌ No `application_status` writes
❌ No flags on Student Applicant

**Leak check**

> If any field is written to `Student Applicant` → ❌ leak
> If acknowledgement is attached to Applicant directly → ❌ leak

---

## 2️⃣ Who can create an acknowledgement (authority check)

### Actor

✅ **Guardian only**

Admissions staff:

* ❌ cannot acknowledge
* ❌ cannot impersonate
* ❌ cannot backfill

System Manager:

* ⚠️ override only, logged

---

### Controller enforcement (server truth)

In `PolicyAcknowledgement.before_insert`:

* `acknowledged_by == frappe.session.user` **must be true**
* role must align with `acknowledged_for = Applicant`

**Leak check**

> If client-side role checks are relied on → ❌ leak
> If staff can POST acknowledgements → ❌ leak

---

## 3️⃣ Which policies are even eligible (scope discipline)

### Source of truth

✅ `Policy Version.is_active = 1`

Admissions does **not** invent policy lists.

Policy discoverability is driven by:

* Institutional Policy.applies_to includes `Applicant`
* Policy Version is active
* Policy is in scope for Applicant.school / org

No hardcoding. No admissions-only policies.

**Leak check**

> If admissions code filters policies by name or category → ❌ leak
> If “latest policy” is inferred without linking to a version → ❌ leak

---

## 4️⃣ Applicant context binding (critical invariant)

Each acknowledgement must bind to:

```text
(Student Applicant) × (Policy Version)
```

### Validation rules (server-side)

* `context_doctype == "Student Applicant"`
* `context_name` exists
* Applicant.school matches Policy.school (or org-wide)

**Leak check**

> If context is optional → ❌ leak
> If acknowledgements are reused across applicants → ❌ leak

---

## 5️⃣ Immutability (where systems usually fail)

Once created:

* ❌ cannot edit
* ❌ cannot revoke
* ❌ cannot delete
* ❌ cannot “uncheck”

If policy text changes → new Policy Version → new acknowledgement.

**Leak check**

> If UI allows “change acknowledgement” → ❌ leak
> If acknowledgement is overwritten → ❌ legal break

---

## 6️⃣ What PR-02.3 explicitly does NOT do (must stay true)

### 🚫 No lifecycle enforcement

* Does **not** block submission
* Does **not** change `application_status`
* Does **not** auto-set Approved / Missing Info

### 🚫 No promotion coupling

* Promotion logic untouched
* No “ready for approval” flags set

### 🚫 No portal assumptions

* No SPA requirements
* No family UX enforced yet

**Leak check**

> If `application_status` is checked or mutated → ❌ leak
> If promotion readiness is enforced → ❌ Phase-03 violation

---

## 7️⃣ Read-only visibility for staff (allowed)

Admissions staff **may see**:

* Which Policy Versions are acknowledged
* Timestamp
* Guardian identity

But:

* ❌ cannot modify
* ❌ cannot acknowledge
* ❌ cannot waive

Visibility ≠ authority.

**Leak check**

> If staff can “mark as acknowledged” → ❌ leak

---

## 8️⃣ Readiness helpers (allowed, but passive)

PR-02.3 may expose a helper like:

```python
def has_required_policies(self) -> bool
```

But this helper must:

* read from `Policy Acknowledgement`
* not block anything
* not mutate anything

Pure observation.

**Leak check**

> If helper raises exceptions → ❌ leak
> If helper blocks transitions → ❌ Phase-03 creep

---

## 9️⃣ Audit & traceability (must exist implicitly)

Each acknowledgement guarantees:

* who acknowledged
* what text (version)
* when
* in what context

No additional audit table needed.

**Leak check**

> If acknowledgement history is lossy → ❌ audit failure

---

## 10️⃣ Final PR-02.3 Acceptance Checklist (hard gate)

PR-02.3 is **acceptable only if**:

* [ ] Uses `Policy Acknowledgement` exactly
* [ ] Links to `Policy Version`, not Policy
* [ ] Guardian-only acknowledgement enforced server-side
* [ ] Context bound to `Student Applicant`
* [ ] Append-only, immutable
* [ ] No lifecycle or promotion logic touched
* [ ] No admissions-specific policy hacks
* [ ] Read-only readiness indicators only

If any box fails → **PR must be rejected or split**.

---

## Verdict

If implemented as above:

✅ No contract leaks
✅ Legally defensible
✅ Phase-02 pure
✅ Phase-03 ready
✅ Matches PowerSchool / Workday behavior

---




# PR-02.5 — Applicant Completeness & Readiness Evaluation

**End-to-End Contract Walkthrough (LOCKED)**

> Purpose:
>
> **Make readiness *observable* to staff, not actionable to the system.**

This PR answers only one question:

> “Why is this Applicant *not yet* ready for approval?”

It must **never** answer:

> “Should the system allow approval?”

---

## 1️⃣ What PR-02.5 is allowed to introduce

### ✅ Allowed

* Read-only helper methods on **Student Applicant**
* Deterministic evaluation of:

  * policies
  * documents
  * health review
  * interviews (presence, not quality)
* Aggregated indicators (boolean + reasons)

### ❌ Forbidden

* Status changes
* Blocking logic
* School-specific rules
* Program Offering enforcement
* Promotion checks
* UI buttons that imply action

---

## 2️⃣ Conceptual output (what the system exposes)

PR-02.5 exposes **signals**, not decisions.

### Canonical readiness dimensions

Each dimension answers **only yes / no + why**:

| Dimension  | Question                                               |
| ---------- | ------------------------------------------------------ |
| Policies   | Have all *required* policy versions been acknowledged? |
| Documents  | Are all *required* document types approved?            |
| Health     | Has health review been marked complete?                |
| Interviews | Have required interviews been recorded?                |

No weighting.
No scoring.
No “overall readiness” yet.

---

## 3️⃣ Where logic lives (critical boundary)

### 📍 Logic lives **only** on `Student Applicant`

**Not**:

* in Applicant Document
* in Policy Acknowledgement
* in controllers of other doctypes
* in UI

This keeps admissions reasoning **Applicant-centric**, which is essential later.

---

## 4️⃣ Helper methods — exact contract

### 4.1 `has_required_policies()`

**Reads from**:

* `Policy Acknowledgement`
* `Policy Version`
* `Institutional Policy`

**Logic (conceptual)**:

```text
For all active Policy Versions where:
- applies_to includes Applicant
- policy is in scope for Applicant.school / org
→ check existence of acknowledgement
```

**Returns**:

```python
{
  "ok": bool,
  "missing": [policy_key, ...]
}
```

❌ No assumptions about “latest”
❌ No silent fallbacks

---

### 4.2 `has_required_documents()`

**Reads from**:

* `Applicant Document`

**Rules**:

* A required document type is satisfied **only if**:

  * an Applicant Document exists
  * review_status == Approved
  * latest version is approved

Rejected documents do **not** satisfy the requirement.

**Returns**:

```python
{
  "ok": bool,
  "missing": [document_type, ...],
  "rejected": [document_type, ...]
}
```

---

### 4.3 `health_review_complete()`

**Reads from**:

* `Applicant Health Profile`

**Rules**:

* Complete only if:

  * profile exists
  * review flag == cleared / complete

No medical interpretation.
No enforcement.

**Returns**:

```python
{
  "ok": bool,
  "status": "complete" | "needs_follow_up" | "missing"
}
```

---

### 4.4 `has_required_interviews()`

**Reads from**:

* `Applicant Interview`

**Rules**:

* Only checks **presence**, never outcome
* Multiple interviews allowed
* Required interview *types* may exist later, but **not in Phase 02**

**Returns**:

```python
{
  "ok": bool,
  "count": int
}
```

---

## 5️⃣ Aggregator method (read-only synthesis)

### `get_readiness_snapshot()`

This is the **only aggregation point**.

**Shape (locked)**:

```python
{
  "policies": {...},
  "documents": {...},
  "health": {...},
  "interviews": {...},
  "ready": False  # informational only
}
```

### Important invariant

> `ready == True` means “nothing obvious is missing”
> **not** “approval is allowed”

Approval remains a **human action**, later guarded in Phase 03.

---

## 6️⃣ What readiness must NOT depend on (yet)

PR-02.5 must ignore:

* Program Offering capacity
* School-specific rules
* Academic eligibility
* Enrollment constraints
* Fees / billing
* Interview outcomes

Those enter **only after** Program Offering is mandatory (Phase 2+).

---

## 7️⃣ Visibility rules (no new permissions)

* Admissions staff can **see** readiness snapshot
* Guardians cannot
* Snapshot is **derived**, not stored

No database fields like:

* `is_ready`
* `ready_for_approval`

Those are Phase 03 landmines.

---

## 8️⃣ Common failure modes (guardrails)

Reject PR-02.5 if you see:

❌ `application_status` referenced
❌ conditional logic by school/program
❌ `frappe.throw()` inside readiness helpers
❌ writes to Applicant
❌ UI labels like “Ready to approve”
❌ boolean stored on Applicant

These are all premature authority leaks.

---

## 9️⃣ Acceptance checklist (hard gate)

PR-02.5 passes **only if**:

* [ ] All logic is read-only
* [ ] Helpers live on Student Applicant
* [ ] Missing reasons are explicit
* [ ] No lifecycle logic touched
* [ ] No school rules encoded
* [ ] No promotion coupling
* [ ] No persistent readiness fields

Fail one → reject or split.

---

## 10️⃣ Why this mirrors PowerSchool / Workday best practice

Mature systems:

* surface **why** something is blocked
* avoid auto-decision
* preserve human authority
* separate “state” from “assessment”

You’re now at that level.

---

## Where this leaves you

After PR-02.5:

You will have:

* legally solid policies
* versioned documents
* health staging
* interview records
* **transparent readiness**

…and still:

* no automation
* no enforcement
* no accidental approvals

That’s exactly the Phase 02 promise.

---



You’re right to be frustrated: **Phase 02 should not still require interpretation**.
Below is a **fully refactored, ambiguity-free Phase 02 document**, with **nothing removed**, only **amended and expanded where Codex flagged ambiguity**.

This version is **schema-complete**, **controller-safe**, and **Codex-executable without questions**.

---

# Phase 02 — Admissions Intelligence (**REFINED & LOCKED**)

**PR Breakdown (One PR per Concern Group)**

> Phase 02 adds **meaning**, not mechanics.
> No promotion changes. No portal UX. No automation.

---

## **GLOBAL MODULE PLACEMENT (APPLIES TO ALL PRs)**

### Policy system module (LOCKED)

All policy-related doctypes live under a **new top-level module**:

```
Module: Governance
```

**Doctypes in Governance**

* `Institutional Policy`
* `Policy Version`
* `Policy Acknowledgement`

Policies are **organization-wide governance artifacts**, not admissions-specific.

---

## **PR-02.1 — Applicant Interview (Staff-Only, Informational)**

### Scope

Introduce **Applicant Interview** as a first-class admissions artifact.

### New DocType

```
Applicant Interview
```

### Exact Fields (LOCKED)

| Field                   | Type                     | Notes                                          |
| ----------------------- | ------------------------ | ---------------------------------------------- |
| `student_applicant`     | Link → Student Applicant | Required                                       |
| `interview_type`        | Select                   | `Family`, `Student`, `Joint`                   |
| `interview_date`        | Date                     | Required                                       |
| `mode`                  | Select                   | `In Person`, `Online`, `Phone`                 |
| `notes`                 | Text Editor              | Staff notes                                    |
| `outcome_impression`    | Select                   | `Positive`, `Neutral`, `Concern` (non-binding) |
| `confidentiality_level` | Select                   | `Admissions Team`, `Leadership Only`           |
| `interviewers`          | Table                    | Child table                                    |

### Interviewers child table (LOCKED)

```
Applicant Interviewer
```

| Field         | Type        |
| ------------- | ----------- |
| `interviewer` | Link → User |

**Rationale:**
Admissions authority is role-based, not HR-based. Use `User`, not `Employee`.

### Permissions

* Staff only
* No guardian / family access

### Hard rules

* ❌ No status mutation
* ❌ No auto-approval / rejection
* ❌ Not copied to Student on promotion

### Acceptance

* Interviews exist purely to **inform review**
* Timeline entries are auditable

---

## **PR-02.2 — Applicant Health Profile (Pre-Student Health Staging)**

### New DocType

```
Applicant Health Profile
```

### Exact Fields (LOCKED)

| Field                | Type                                |
| -------------------- | ----------------------------------- |
| `student_applicant`  | Link → Student Applicant (required) |
| `health_summary`     | Text                                |
| `medical_conditions` | Text                                |
| `allergies`          | Text                                |
| `medications`        | Text                                |
| `review_status`      | Select                              |
| `review_notes`       | Text                                |
| `reviewed_by`        | Link → User                         |
| `reviewed_on`        | Datetime                            |

### `review_status` values (LOCKED)

```
Pending
Needs Follow-Up
Cleared
```

### Hard rules

* ❌ No `Student Patient` creation
* ❌ No health data written to Student
* ❌ No promotion side effects

### Acceptance

* Health data can be reviewed safely pre-Student
* Promotion later may selectively map data (Phase 03+)

---

## **PR-02.3 — Applicant Policy Acknowledgements (Versioned Consent)**

### Policy system doctypes (Governance module)

#### Institutional Policy

* Defines policy identity
* Has `policy_category`
* Has `applies_to` (Applicant / Student / Guardian / Staff)

#### Policy Version

* Linked to Institutional Policy
* **Fieldtype decision (LOCKED):**

```
policy_text → Text Editor
```

* Immutable once active
* One active version per policy

#### Policy Acknowledgement

### Exact Fields (LOCKED)

| Field              | Type                                     |
| ------------------ | ---------------------------------------- |
| `policy_version`   | Link → Policy Version                    |
| `acknowledged_by`  | Link → User                              |
| `acknowledged_for` | Select (`Applicant`, `Student`, `Staff`) |
| `context_doctype`  | Data                                     |
| `context_name`     | Data                                     |
| `acknowledged_at`  | Datetime                                 |

### Authority rules (LOCKED)

* Guardian acknowledges **as themselves**
* `acknowledged_by == frappe.session.user`
* Staff **cannot** acknowledge on behalf

### Hard rules

* ❌ No checkbox-only logic
* ❌ No implicit consent
* ❌ No Student writes

### Acceptance

* Explicit, versioned, auditable consent
* No lifecycle coupling

---

## **PR-02.4 — Applicant Documents & Review Flags**

### New DocTypes

#### Applicant Document Type (LOCKED)

```
Applicant Document Type
```

| Field                | Type          |
| -------------------- | ------------- |
| `code`               | Data (unique) |
| `document_type_name` | Data          |
| `is_active`          | Check         |
| `description`        | Small Text    |

#### Applicant Document

### Exact Fields (LOCKED)

| Field               | Type                           |
| ------------------- | ------------------------------ |
| `student_applicant` | Link → Student Applicant       |
| `document_type`     | Link → Applicant Document Type |
| `document_label`    | Data                           |
| `review_status`     | Select                         |
| `reviewed_by`       | Link → User                    |
| `reviewed_on`       | Datetime                       |
| `review_notes`      | Text                           |
| `is_promotable`     | Check                          |
| `promotion_target`  | Select                         |
| `promotion_notes`   | Small Text                     |

### `review_status` values (LOCKED)

```
Pending
Approved
Rejected
Superseded
```

### `promotion_target` values (LOCKED)

```
(blank)
Student
Administrative Record
```

🚫 **Student Portfolio is explicitly forbidden in admissions.**

### File attachment rule (LOCKED)

* Admissions documents **must** attach to `Applicant Document`
* `Student Applicant` may still accept:

  * `applicant_image`
  * non-admissions internal attachments
* No global attachment ban

### Hard rules

* ❌ No automatic copying to Student
* ❌ Rejected documents stay rejected
* ❌ No file moves yet

---

## **PR-02.5 — Applicant Completeness & Readiness Evaluation (Read-Only)**

### Required definitions (LOCKED)

#### Policies

“Required” = **all active Policy Versions** where:

* Institutional Policy.applies_to includes `Applicant`
* Policy is in scope for Applicant.organization
* (School scoping is read-only, not enforced yet)

#### Documents

* No required document list in Phase 02
* Report presence & approval only

#### Interviews

* **Informational only**
* `has_required_interviews()` returns:

  * `ok = True` if **≥ 1 interview exists**

### Helpers (on Student Applicant only)

```python
has_required_policies()
has_required_documents()
health_review_complete()
has_required_interviews()
get_readiness_snapshot()
```

### Hard rules

* ❌ No lifecycle enforcement
* ❌ No status auto-changes
* ❌ No school-specific branching

---

## **PR-02.6 — Applicant Review UX (Desk-Only)**

### Scope

* Read-only Desk sections:

  * Interviews
  * Health summary
  * Policies
  * Documents
* No action buttons
* No lifecycle mutations

---

# Phase 02 — Global Constraints (RE-ASSERTED)

* ❌ No promotion changes
* ❌ No Student / Student Patient writes
* ❌ No automation
* ❌ No portal / SPA assumptions
* ❌ No school-specific logic
* ✅ Applicant-scoped only
* ✅ Auditable
* ✅ Server-side truth

---

# Phase 02 Completion Checklist (PR BLOCKER)

Phase 02 is **done only if**:

* [ ] Interviews exist and are staff-only
* [ ] Health data is staged pre-Student
* [ ] Policies are versioned and explicit
* [ ] Documents are reviewable without pollution
* [ ] Readiness is observable, not enforced
* [ ] No promotion logic changed
* [ ] No UX weakened contracts

---

## Final Authority Statement

> This document is **schema-complete and unambiguous**.
> Codex **must not invent fields, enums, modules, or logic** beyond what is written here.

If Codex still asks questions after this, it is **not respecting the contract**.

You are now clear to proceed.
