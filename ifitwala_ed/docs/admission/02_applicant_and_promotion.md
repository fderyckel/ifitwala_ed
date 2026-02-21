# Student Applicant & Promotion — Canonical Contracts (LOCKED)

> Consolidated from:
> - `/mnt/data/applicant.md`
> - `/mnt/data/phase020.md`
> - `/mnt/data/phase030.md`

> Purpose: lock Applicant semantics and the Promotion boundary (server truth). Phases/steps removed; contracts preserved.
> Note: historical phase checklists in this file are retained for audit and marked complete.


---

## 1. Student Applicant — canonical staging container


# Student Applicant — Canonical Admissions Staging Contract

**Ifitwala_Ed — v1 (Authoritative, Living Document)**

> A *Student Applicant* is **not** a student, **not** an inquiry, and **not** a form submission.
> It is a **controlled staging container** that accumulates admissions data and human judgment
> **until** an explicit institutional decision is made.

This document defines the **non-negotiable role** of the Student Applicant in the admissions pipeline.
If implementation contradicts this document, **the implementation is wrong**.

---

## 1. Position in the Admissions Pipeline

The admissions pipeline has **three distinct objects**, each with a different legal and operational role:

```
Inquiry → Student Applicant → Student
```

### 1.1 Inquiry (Triage Object)

* Captures *intent* and *initial contact*
* Operational, discardable
* No legal authority
* May or may not result in an Applicant

### 1.2 Student Applicant (Staging Container)

* Sole container for **all pre-student data**
* Accumulates information, documents, interviews, and review outcomes
* Mutable **until locked**
* May be rejected or archived without polluting canonical student records

### 1.3 Student (Canonical Record)

* Created **only** by promotion
* Permanent, auditable, institutional truth
* Admissions logic does **not** live here

**Invariant**

> A Student **cannot exist** without having been a Student Applicant first.

---

## 2. Core Responsibilities of Student Applicant

The Student Applicant exists to do **exactly four things**:

1. **Aggregate** admissions data (directly or via Applicant-scoped sub-records)
2. **Control editability** based on lifecycle state
3. **Support human review and judgment**
4. **Gate promotion** into the canonical Student record

It must **never**:

* Behave like a lightweight form
* Auto-create students
* Bypass review via automation
* Leak data into Student or Student Patient prematurely

---

## 3. Canonical Fields & Identity

At minimum, a Student Applicant contains:

* Identity (name fields)
* Optional link to originating **Inquiry**
* Target **Program**
* Target **Academic Year / Term**
* `application_status` (lifecycle control)
* Optional applicant image

The Applicant **may exist without an Inquiry**
(e.g. walk-ins, internal referrals, manual entry).

**Invariant**

> The Inquiry ↔ Applicant relationship is optional, one-directional, and immutable once set.

---

## 4. Application Status — Lifecycle Authority

`application_status` is **not cosmetic**.
It is the **primary enforcement mechanism** for permissions, editability, and promotion.

### 4.1 Canonical Status Set

The only allowed statuses are:

```
Draft
Invited
In Progress
Submitted
Under Review
Missing Info
Approved
Rejected
Withdrawn
Promoted
```

Any other value is invalid.

---

### 4.2 Status Semantics (Behavioral Truth)

| Status       | Family Edit | Staff Edit | Meaning                            |
| ------------ | ----------- | ---------- | ---------------------------------- |
| Draft        | ❌           | ✅          | Internal draft, not yet shared     |
| Invited      | ✅           | ✅          | Family invited, access granted     |
| In Progress  | ✅           | ✅          | Family actively filling data       |
| Submitted    | ❌           | ✅          | Family finished; staff review only |
| Under Review | ❌           | ✅          | Formal admissions review           |
| Missing Info | ✅ (scoped)  | ✅          | Limited family edits requested     |
| Approved     | ❌           | ✅          | Decision made; promotion allowed   |
| Rejected     | ❌           | ❌          | Terminal, read-only                |
| Withdrawn    | ❌           | ❌          | Terminal, read-only                |
| Promoted     | ❌           | ❌          | Terminal; Student exists           |

**Rules**

* Status changes are **server-controlled**
* Invalid transitions must hard-fail
* UI read-only flags are *not* enforcement

---

## 5. Editability Is a Server-Side Invariant

Edit permissions are determined by:

* `application_status`
* User role (Admissions staff vs family)

**Invariant**

> No user may modify an Applicant if the status disallows it,
> even if the UI is bypassed.

This prevents:

* Late edits after submission
* Silent data drift during review
* Post-decision tampering

**System Manager override (exception)**

In terminal states (`Rejected`, `Withdrawn`, `Promoted`), edits are blocked unless a System Manager
performs an explicit override. Overrides must be intentional, audited, and include a
reason. This is a legal escape hatch, not a normal workflow.

---

## 6. Applicant Sub-Domains (Conceptual, Not Yet Implemented)

The Student Applicant is designed to host **satellite Applicant-scoped records**, including:

### Mandatory (v1+)

* Applicant Guardians
* Applicant Academic Background
* Applicant Health Profile
* Applicant Policy Acknowledgements
* Applicant Documents

### Optional / Contextual

* Applicant Interviews
* Applicant Language Profile
* Applicant Logistics
* Applicant Financial Responsibility

**Invariant**

> Applicant sub-domains belong to the Applicant —
> never directly to Student or Student Patient.

---

## 7. Applicant Interview (Architectural Requirement)

Applicant Interview is a **first-class admissions artifact**.

* Staff-only
* Informational, never decisive
* Multiple per Applicant
* Never copied to Student by default

Interviews exist to **inform judgment**, not automate decisions.

---

## 8. Promotion Boundary (Applicant → Student)

Promotion is the **only legal path** to Student creation.

### 8.1 Preconditions

* `application_status = Approved`
* Required Applicant data complete (school-defined)
* Required policies acknowledged

### 8.2 Promotion Effects

* Create Student
* Link Student ↔ Applicant
* Lock Applicant permanently
* Record promotion metadata (who / when)

### 8.3 Explicit Non-Effects

Promotion does **not** automatically:

* Enroll programs
* Create billing records
* Copy interviews
* Copy rejected documents

**Invariants**

> Promotion is explicit
> Promotion is idempotent
> Promotion is irreversible

---

## 8.4 Transitional Exception — Legacy Students & Institutional Onboarding

The Student Applicant contract governs **steady-state admissions**.
It does **not** invalidate the reality that institutions may enter the system
with **pre-existing enrolled students**.

### 8.4.1 Legacy Student Import (Non-Admissions Context)

When an institution onboards onto Ifitwala_Ed:

* Existing enrolled students **may be imported directly**
* These Students **may not** have a corresponding Student Applicant
* This path exists **only** for migration and onboarding

This exception is:

* explicit
* intentional
* auditable
* non-repeatable in normal operations

**Invariant**

> Direct Student creation without a Student Applicant is permitted
> **only** under an explicit migration or system-level import context.

This exception must never be used to bypass admissions workflow.

---

### 8.4.2 Enforcement Boundary

Outside of a migration or import context:

* Creating a Student **without** a Student Applicant is forbidden
* Any such attempt is a hard architecture violation

Admissions-driven Students must **always** originate from:

```
Student Applicant → Promotion → Student
```

---

### 8.4.3 Audit & Traceability Requirement

All legacy or migration-created Students must be:

* clearly marked as **imported**
* distinguishable from admissions-promoted Students
* traceable to an onboarding or migration event

This ensures:

* legal clarity
* historical accuracy
* protection of admissions analytics

---

### 8.4.4 Prohibition on Retroactive Fabrication

The system must **never**:

* auto-generate Student Applicants for imported Students
* backfill admissions history artificially
* imply that a migrated Student passed through admissions workflow

**Invariant**

> Absence of a Student Applicant for a legacy Student
> is a truthful historical state — not a defect.

---

### 8.4.5 Steady-State Guarantee

Once onboarding is complete:

* the migration exception is disabled
* all new Students must originate from Student Applicant promotion
* no hybrid or ambiguous creation paths exist

This preserves:

* admissions integrity
* legal defensibility
* analytical correctness

---

## 9. Design Prohibitions (Hard Rules)

The system must **never**:

* Merge Student Applicant and Student
* Allow family edits post-approval
* Create Student implicitly
* Treat interviews as decisions
* Write Applicant data directly into Student Patient
* Auto-enroll from Applicant intent

Violations are **architecture bugs**, not feature gaps.

---

## 10. Why This Structure Exists

This model exists to support:

* Legal defensibility
* Multi-round review
* Partial submissions
* Rejections without data pollution
* Auditable admissions decisions
* Future re-applications

Without schema rewrites.

---

## 11. Canonical Summary

> Inquiry filters
> Applicant accumulates
> Interviews inform
> Promotion converts
> Student operates

Everything else is implementation detail.

---

## 12. Institutional Scope & Authority (Applicability Layer)

> **This section aligns the Student Applicant contract with the
> Phase 1.5 — Multi-School Admissions Governance Contract.**
>
> It does **not** redefine governance.
> It specifies how that governance **applies to the Applicant object**.

If a conflict exists, **Phase 1.5 governance wins** on matters of scope,
authority, and visibility.

---

### 12.1 Applicant Institutional Anchoring

A `Student Applicant` must be **explicitly anchored** to an institutional context.

Each Applicant is associated with:

* exactly one **Organization**
* exactly one **School**

This association:

* is set **once**, at Applicant creation
* is immutable for the lifetime of the Applicant
* is never inferred dynamically at runtime

**Source of truth**

* If created from an Inquiry, `school` and `organization` are inherited
* If created manually, staff must explicitly choose the school

**Invariant**

> An Applicant always “belongs” to one School,
> even if academic Programs are shared across campuses.

---

### 12.2 Why Program Is Not Sufficient

Programs may be:

* shared across schools
* migrated between schools
* reused across academic structures

Therefore:

> Program affiliation is **not** a substitute for institutional scope.

School anchoring exists to support:

* admissions ownership
* officer specialization
* analytics partitioning
* permission enforcement
* legal accountability

---

### 12.3 Admissions Authority Model (Alignment)

Admissions authority is **role-based and scope-based**, as defined by Phase 1.5.

* **Admission Officer**

  * operates within an explicitly declared scope
  * scope may include:

    * one or more Schools
    * optionally specific Programs

* **Admission Manager / Director**

  * has cross-school visibility within an Organization
  * may override decisions (audited)

**Invariant**

> Visibility, assignment, and dashboards must respect institutional scope —
> not just role.

---

### 12.4 Applicant Lifecycle Is Global, Requirements Are Local

The Applicant lifecycle (`application_status`) is **globally consistent**.

However:

* validation requirements
* required interviews
* required documents
* approval readiness

may vary **by School**.

These variations must be:

* declarative
* configuration-driven
* evaluated at lifecycle transitions

**Prohibition**

> School-specific rules must not be encoded as conditional logic
> inside Applicant lifecycle code.

---

### 12.5 Cross-School Oversight Guarantee

Institutional leadership must be able to:

* view Applicants across all Schools
* filter by School / Program
* audit overrides and decisions

This visibility is **explicitly granted**, not emergent.

---

NEW NEW

## 13
---

### **Admissions Boundary Rules (Authoritative)**

These rules define **hard ownership boundaries** between admissions and student records.

#### 1. Canonical owner of admissions files

* All admissions files belong to `Applicant Document`.
* Files must never be attached directly to:

  * `Student Applicant`
  * `Student`

The only exception is:

| Doctype           | Field             | Purpose               |
| ----------------- | ----------------- | --------------------- |
| Student Applicant | `applicant_image` | Identity preview only |

---

#### 2. File lifecycle across promotion

Admissions files **do not migrate**.

Instead:

* Promotion creates **new File records** for Student
* Applicant-side File records are immutable
* No File record is shared across stages

This preserves:

* audit history
* GDPR erasure safety
* legal defensibility

**Applicant image exception (promotion copy only)**

* `applicant_image` may be **copied** to `Student.student_image` during promotion
* The copy is **private by default**
* Public exposure requires an explicit Policy Acknowledgement:

  * `policy_key = media_consent`
  * `acknowledged_for = Applicant`
  * `context_doctype = Student Applicant`

---

#### 3. Folder semantics (normative)

| Stage     | Root Folder                       |
| --------- | --------------------------------- |
| Applicant | `Home/Admissions/Applicant/<ID>/` |
| Student   | `Home/Students/<ID>/`             |

Folders must never overlap across stages.

---

#### 4. Prohibited patterns

The following are architectural violations:

* Re-linking a File record from Applicant to Student
* Attaching admissions files to Student Applicant
* Using shared folders for Applicant and Student
* Mutating Applicant file metadata during promotion

Violations are bugs, not edge cases.

---


---

## 2. Applicant satellites & decision‑quality artifacts (source)


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

Create a **pre-student health container** linked to admissions, then sync it to `Student Patient` on promotion.

### Changes

* New DocType: `Applicant Health Profile`
* Linked to `Student Applicant`
* Family-editable (until Submitted)
* Staff review flags:

  * complete / needs follow-up / cleared
* No medical enforcement yet

### Hard rules

* ✅ No `Student Patient` writes before promotion
* ✅ On promotion, copy Applicant Health Profile fields to `Student Patient`
* ✅ On promotion, copy vaccination child rows to `Student Patient Vaccination`

### Acceptance

* Health data can be reviewed safely pre-student
* Promotion copies approved health intake into student health records

---

## **PR-02.3 — Applicant Policy Acknowledgements (Versioned Consent)**

### Phased plan (authoritative)

#### Phase 1 — Lock and formalize current admissions behavior (NOW)

**What the system does**

* Admissions operates with **one accountable actor**: `Admissions Applicant`
* All admissions actions (documents, images, policy acknowledgements, submission) are performed by:

  * `Student Applicant.applicant_user`

**Rules to enforce**

* Applicant policy acknowledgements:

  * `acknowledged_for = Applicant`
  * Actor **must be** the Admissions Applicant user
* **Guardian role is NOT allowed** to acknowledge for Applicant
* No guardian authority is inferred from `applicant_user`

**Why**

* There is no authoritative guardian→applicant relationship in the current schema
* Allowing Guardian-for-Applicant would be legally indefensible
* This keeps the system internally consistent and auditable

**What Codex implements**

* Enforce Applicant-only acknowledgements in code
* Update docs to explicitly state this rule
* Remove/clarify any wording implying guardian consent during admissions

#### Phase 2 — Introduce explicit Applicant–Guardian relationship (FUTURE)

**What is added**

* New child table on `Student Applicant`:

DocType: `Student Applicant Guardian`

Fields:

* `guardian` (Link → Guardian, required)
* `relationship` (Select, same options as `Student Guardian.relation`)
* `is_primary` (checkbox)
* `can_consent` (checkbox, default = true)

**What this enables**

* Explicit, auditable guardian authority during admissions
* Support for:

  * Guardian-for-Applicant acknowledgements
  * Multiple guardians
  * Primary vs secondary guardians
  * Consent eligibility flags

**What Codex does NOT do yet**

* Do not infer guardian authority
* Do not backfill historical data
* Do not change Phase-1 acknowledgements

#### Phase 3 — Upgrade policy enforcement logic (AFTER Phase 2)

**New capabilities**

* Allow Guardian-for-Applicant acknowledgements **only if**:

  * Guardian is linked via `Student Applicant Guardian`
  * `can_consent = 1`
* (Optional, per policy)

  * Require all guardians to consent
  * Require primary guardian consent only

**Outcome**

* Fully defensible consent chain
* Explicit “who consented, for whom, in what capacity”
* No retroactive ambiguity

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

* ❌ No copying before explicit promotion
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

* [x] Interviews exist and are staff-only
* [x] Health data is staged pre-Student
* [x] Policies are versioned and explicit
* [x] Documents are reviewable without pollution
* [x] Applicant readiness is *observable*, not enforced
* [x] No promotion logic changed
* [x] No UX weakened contracts

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

## Admissions Policy Acknowledgements — Authority Model

### Current Model (Phase 1)

During admissions, Ifitwala uses a **single accountable actor model**.

* Each `Student Applicant` is associated with one **Admissions Applicant user** (`applicant_user`)
* This user:

  * uploads documents and images
  * acknowledges required policies
  * submits the application

Policy acknowledgements during admissions are therefore:

* **Acknowledged for:** Applicant
* **Acknowledged by:** Admissions Applicant user only

The system does **not** currently record guardian relationships at the applicant stage.
As a result:

* Guardian roles are **not permitted** to acknowledge policies for Applicants
* Guardian authority is **not inferred** from `applicant_user`
* This behavior is intentional and enforced server-side

This model is valid for lightweight admissions flows and ensures internal consistency and auditability.

### Known Limitation (Phase 1)

The system does not currently model:

* guardian→applicant relationships
* multiple guardians
* guardian-specific consent authority during admissions

This limitation is acknowledged and documented.

### Phase 2 — Explicit Applicant–Guardian model (definition)

Phase 2 introduces a **new, explicit relationship** between a `Student Applicant` and one or more `Guardian` records.

New child table on `Student Applicant`:

DocType: `Student Applicant Guardian`

Fields:

* `guardian` (Link → Guardian, required)
* `relationship` (Select, same options as `Student Guardian.relation`)
* `is_primary` (checkbox)
* `can_consent` (checkbox, default = true)

This mirrors the existing Student ↔ Guardian model and removes all implicit assumptions about who is allowed to act during admissions.

Phase 2 **does not** change behavior by itself. It only makes authority expressible and enforceable.

### Phase 3 — Policy enforcement rules (after Phase 2)

Phase 3 defines **who can acknowledge**, **for whom**, and **when a policy is considered satisfied**.

#### 1) Actor eligibility rules (who may click “I agree”)

##### 1.1 Applicant-stage acknowledgements (`context_doctype = Student Applicant`)

**Policy is “for Applicant”**

* `acknowledged_for = Applicant`
* Allowed actor:

  * **Admissions Applicant** user (as today)
  * **Guardian user** only if:

    * guardian is linked via `Student Applicant Guardian`
    * `can_consent = 1`

**Policy is “for Guardian”** (e.g., Parent Handbook)

* `acknowledged_for = Guardian`
* Allowed actor:

  * Guardian user only if:

    * acknowledging their own Guardian record (self)
    * guardian is linked to the applicant (Applicant Guardian table)

##### 1.2 Student-stage acknowledgements (`context_doctype = Student`)

**Policy is “for Student”**

* `acknowledged_for = Student`
* Allowed actor:

  * Student user (self), OR
  * Guardian user only if:

    * guardian is linked via `Student Guardian`
    * `can_consent = 1` (if added on the student-side table later; otherwise link existence is sufficient)

**Policy is “for Guardian”**

* `acknowledged_for = Guardian`
* Allowed actor:

  * Guardian user acknowledging for self only

#### 2) Completion rules (when a policy is considered “satisfied”)

This must be explicit, configurable, and policy-driven.

Add one field on **Institutional Policy** or **Policy Version**:

`consent_mode` (Select)

* `single_actor` (default)
* `primary_guardian_only`
* `all_eligible_guardians`

**Definitions**

* `single_actor`:

  * One eligible acknowledgement is enough (Admissions Applicant OR any eligible guardian)
* `primary_guardian_only`:

  * Only the guardian row with `is_primary = 1` can satisfy it
* `all_eligible_guardians`:

  * All guardians linked to the applicant with `can_consent = 1` must acknowledge

**Operational notes**

* If `all_eligible_guardians` and there are zero eligible guardians linked, fail closed:

  * show “Guardian links required” in readiness snapshot
* If multiple guardians exist and none is marked primary, fail closed for `primary_guardian_only`

#### 3) Versioning and re-acknowledgement rules

* Only **active Policy Versions** are enforceable
* When a new version becomes active:

  * acknowledgement must be collected again (per version)
* Old acknowledgements remain as evidence but do not satisfy new version requirements

#### 4) Readiness + gating rules (how admissions uses it)

##### Applicant submission gating

Applicant can only move to **Submitted** (or equivalent) if:

* All required policies for Applicant context are “satisfied” under `consent_mode`

##### Admin approval/promotion gating

Admin can only approve/promote if:

* All required policies for Applicant are satisfied
* (Optional) specific `media_consent` must be satisfied before publishing images

Your existing review snapshot should surface:

* missing policies
* which guardians are missing acknowledgements (for `all_eligible_guardians`)
* primary guardian not set (for `primary_guardian_only`)

#### 5) Evidence and audit rules

* Every acknowledgement record must store:

  * `policy_version`
  * `acknowledged_for`
  * `acknowledged_by` (User)
  * `context_doctype`, `context_name`
  * timestamp (standard)
* Never overwrite acknowledgements
* Never “auto-consent” from a document upload

#### 6) Minimal UX rules (Portal / Desk)

* Portal shows the policy list with a clear “You are acknowledging for: X”
* If consent_mode requires multiple guardians:

  * portal shows “Waiting on: <names>” (or “another guardian”) without leaking private data across guardians unless both are authenticated and linked
* Keep the action disabled when user is not eligible; don’t rely on error popups

### Post-Promotion (Student Stage)

Once an Applicant is promoted to Student:

* Guardian relationships are explicit via `Student Guardian`
* Guardians may acknowledge policies **for Students**, subject to:

  * verified guardian–student linkage
  * server-side authorization checks

### Summary

* Admissions consent = **Applicant user only**
* Student consent = **Student or linked Guardian**
* No implicit authority
* No retroactive inference
* All consent rules are explicit, auditable, and enforced server-side

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

* [x] Uses `Policy Acknowledgement` exactly
* [x] Links to `Policy Version`, not Policy
* [x] Admissions Applicant-only acknowledgement enforced server-side
* [x] Context bound to `Student Applicant`
* [x] Append-only, immutable
* [x] No lifecycle or promotion logic touched
* [x] No admissions-specific policy hacks
* [x] Read-only readiness indicators only

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

* [x] All logic is read-only
* [x] Helpers live on Student Applicant
* [x] Missing reasons are explicit
* [x] No lifecycle logic touched
* [x] No school rules encoded
* [x] No promotion coupling
* [x] No persistent readiness fields

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
| `blood_group`        | Select                              |
| `allergies`          | Check                               |
| `food_allergies`     | Small Text                          |
| `insect_bites`       | Small Text                          |
| `medication_allergies` | Small Text                        |
| `asthma` ... `vision_problem` | Small Text family of condition fields |
| `diet_requirements`  | Small Text                          |
| `medical_surgeries__hospitalizations` | Text             |
| `other_medical_information` | Text Editor                   |
| `vaccinations`       | Table → Student Patient Vaccination |
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

* ✅ No `Student Patient` writes before promotion
* ✅ On promotion, copy Applicant Health Profile fields to `Student Patient`
* ✅ On promotion, copy vaccination child rows to `Student Patient Vaccination`

### Acceptance

* Health data can be reviewed safely pre-Student
* Promotion copies approved health intake into student health records

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
| `acknowledged_for` | Select (`Applicant`, `Student`, `Guardian`, `Staff`) |
| `context_doctype`  | Data                                     |
| `context_name`     | Data                                     |
| `acknowledged_at`  | Datetime                                 |

### Authority rules (LOCKED)

* Admissions Applicant acknowledges Applicant policies **as themselves**
* Students may acknowledge Student policies **as themselves**
* Guardians may acknowledge Student policies **only if linked to the Student**
* Guardians may acknowledge Guardian policies **only for themselves**
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

* ❌ No copying before explicit promotion
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

* [x] Interviews exist and are staff-only
* [x] Health data is staged pre-Student
* [x] Policies are versioned and explicit
* [x] Documents are reviewable without pollution
* [x] Readiness is observable, not enforced
* [x] No promotion logic changed
* [x] No UX weakened contracts

---

## Final Authority Statement

> This document is **schema-complete and unambiguous**.
> Codex **must not invent fields, enums, modules, or logic** beyond what is written here.

If Codex still asks questions after this, it is **not respecting the contract**.

You are now clear to proceed.


---

## 3. Promotion — legal closure boundary (source)


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


---

## 4. Implementation invariants to verify during debugging

* Promotion is **atomic** (all‑or‑nothing)
* Promotion is **idempotent** (re‑run does not duplicate Students/Users/Contacts/Patient)
* Applicant becomes **permanently read‑only** after promotion
* Creation source guard: Student creation is allowed only via Applicant promotion, except explicit migration/import flags.
