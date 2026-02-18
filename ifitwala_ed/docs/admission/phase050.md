Part A

# Phase 5 — UX Invariants (Non-Negotiable)

## Implementation Status (2026-02-18)

* Implemented: Admissions Applicant doctype permissions (Student Applicant, Applicant Document, Applicant Health Profile, Policy Acknowledgement).
* Implemented: Portal status mapping includes `Withdrawn` with read-only reason support.
* Implemented: admissions applicants are redirected to `/admissions` and blocked from staff/student/guardian portal surfaces by route policy.
* Implemented: formalized DTO/type contracts in SPA code (`NextAction`, `CompletionState`, `ApplicantPolicy`).

**Scope:** Applicant & Staff Admissions UX
**Authority:** Subordinate to Admissions Governance Contracts and Phase 1–3 server logic
**Purpose:** Prevent UX from becoming a source of truth

---

## Core Principle

> UX is an interface, never an authority.
> Removing the UI must not change what is true.

---

## 1. UX May Do

UX MAY:

* Read Applicant and sub-domain data
* Display computed completeness and readiness
* Guide users through required steps
* Gate visibility based on server-provided state
* Submit data through explicit server methods
* Render historical, immutable records

---

## 2. UX Must NEVER Do

UX MUST NOT:

* Mutate Applicant status directly
* Infer or recompute business logic client-side
* Create local “draft truth” that diverges from server
* Rename, move, or delete files
* Implicitly reopen or resubmit applications
* Trigger promotion or simulate its effects
* Bypass governance, permissions, or scope rules

---

## 3. UX Failure Semantics

If UX encounters:

* missing data
* conflicting state
* blocked actions
* failed server validations

Then UX MUST:

* surface the failure explicitly
* explain why the action is blocked
* provide no silent fallback or auto-fix

---

## 4. File Handling (Preview)

UX treats files as **legal artifacts**, not UI assets.

* Upload ≠ acceptance
* Acceptance ≠ promotion
* Promotion ≠ visibility

File lifecycle is governed server-side only.

---

## 5. Governance Alignment

Any UX requirement that cannot be met
without changing contracts or server behavior MUST:

1. Stop implementation
2. Escalate to governance review
3. Be resolved before UX continues

---

**Violation of this document constitutes architectural drift.**




Part B


# Phase 5 — Applicant Portal Surface Map

This document maps **canonical admissions objects**
to **portal-visible UX surfaces**.

UX renders truth. It does not invent it.

---

## 1. Root Object

### Student Applicant (Read / Conditional Write)

Portal binds to **exactly one object**:

* Student Applicant

Families NEVER see or touch:

* Student
* Student Patient
* Internal admissions records

---

## 2. Portal Sections (Read / Write Matrix)

| Portal Section | Backing Object | Family Action |
|---------------|---------------|---------------|
| Applicant Overview | Student Applicant | Read |
| Personal Details | Student Applicant | Write (until submission) |
| Guardians | Applicant Guardian | Write |
| Health Information | Applicant Health Profile | Write |
| Documents | Applicant Document | Upload only |
| Policy Acknowledgements | Applicant Policy Ack | Accept only |
| Communications | Admissions Communication | Read |
| Submission | Student Applicant | Explicit submit |

---

## 3. Status → UX Gating

UX visibility and editability are driven by:

* `application_status`
* server-computed flags (e.g. is_editable, is_submitted)

UX MUST NOT infer state transitions.

---

## 4. Read-Only Transitions

Once:

* Application is submitted
* Or status changes to non-editable

UX MUST:

* render sections read-only
* explain why editing is locked
* avoid “disabled but unexplained” UI

---

## 5. Promotion Boundary

After promotion:

* Applicant becomes read-only forever
* Portal access is revoked or frozen (school-defined)
* No Student data is exposed in the Applicant portal

---

## 6. Error & Blocking States

When requirements are unmet:

* UX shows missing items
* UX does not guess priorities
* UX does not auto-resolve

All blocking rules originate server-side.

---




Part C


## Admissions UX Contract (Phase 5)

This section defines how **staged admissions files**
must be surfaced in UX without violating legal or architectural constraints.

---

### 1. File Lifecycle (Admissions Context)

Applicant files exist in **three states**:

1. Uploaded (family action)
2. Reviewed (staff action)
3. Finalized (promotion outcome)

UX MUST reflect these states explicitly.

---

### 2. UX State Mapping

| Server Truth | UX Representation |
|-------------|------------------|
| Uploaded | “Uploaded – pending review” |
| Accepted | “Accepted” |
| Rejected | “Rejected” |
| Finalized (post-promotion) | “Final record” |

UX MUST NOT rename or reframe these states.

---

### 3. UX Permissions

Families may:

* upload files
* view review status
* see rejection reasons if shared

Families may NOT:

* delete files
* replace rejected files unless reopened
* rename files
* see internal-only documents

---

### 4. Promotion Effect (UX)

Upon promotion:

* Accepted files become owned by Student
* Applicant retains historical reference only
* UX must reflect that files are no longer editable

No visual illusion of duplication is allowed.

---

### 5. GDPR Alignment

UX must not expose:

* file paths
* storage locations
* internal file IDs

Erasure and retention are server-governed only.

---
