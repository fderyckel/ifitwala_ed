# Admissions Implementation Plan

**Ifitwala_Ed — Execution Roadmap**

> This plan assumes the **Admissions Canonical Contracts** are locked and authoritative.
>
> In case of conflict:
>
> 1. System-wide governance rules win
> 2. Phase 1.5 — Multi-School Admissions Governance Contract wins on scope & authority
> 3. Object-level contracts (`applicant.md`, etc.) win on semantics
> 4. This document governs **order of execution only**

---

## Phase 0 — Governance Freeze (NO CODE)

**Goal:** Prevent architectural drift before implementation accelerates.

* Freeze Admissions Canonical Contracts as authoritative
* Freeze Phase 1.5 Governance Contract
* Share with all agents / contributors
* Reject PRs that violate any locked contract

**Invariant**

> No execution work may redefine governance or object semantics.

---

## Phase 1 — Pipeline Wiring (Minimal, Structural)

**Goal:** Make the admissions pipeline real, even if empty.

This phase implements **structural truth enforcement only**.
No portals. No satellites. No automation polish.

---

### 1. Inquiry → Invite to Apply

* Server method
* Creates Student Applicant
* Links back to Inquiry
* Writes audit entry

---

### 2. Student Applicant (Core Container)

* Expand statuses per `applicant.md`
* Enforce editability by status
* Enforce server-side lifecycle rules

---

### 3. Promotion Stub

* Applicant → Student (minimal fields)
* Idempotent
* Auditable
* Irreversible

---

### ✅ Phase 1 Exit Condition

At the end of Phase 1:

> A Student can exist **only** via promotion from a Student Applicant.

---

## Phase 1.5 — Multi-School Admissions Governance (Design Lock)

> **This phase introduces no code.**
> It exists to close the multi-school / multi-org blind spot **before** Phase 2.

This phase is **authoritative and prerequisite** for all later phases.

---

### Purpose

Ensure that the admissions pipeline is:

* explicitly school-aware
* role-scoped
* analytically partitionable

No feature delivery is expected.

---

### Governance Reference

All rules in this phase are defined in the standalone:

> **Phase 1.5 — Multi-School Admissions Governance Contract**

This plan **does not redefine those rules**.
It relies on them.

---

### Design Outcomes (Assumed by Phase 2+)

After Phase 1.5:

* Every Applicant has an unambiguous institutional home
* Admissions authority is explicitly scoped
* Director oversight is guaranteed
* Analytics assumptions are safe
* No inference chains are required

---

### ✅ Phase 1.5 Exit Criteria

* Applicant scope is unambiguous
* Officer specialization is enforceable
* Director oversight is guaranteed
* Phase-2 features can assume correct governance

---

## Phase 2 — Admissions Intelligence (Decision Quality)

**Goal:** Enable *real* admissions decisions, not checkbox approvals.

This phase adds **meaning**, not mechanics.

---

### Deliverables

#### 1. Applicant Interview (Staff-Only)

* Multiple interviews per Applicant
* Informational, non-binding
* Never copied to Student by default

---

#### 2. Applicant Health Profile (Pre-Student)

* Family-entered, staff-reviewed
* No Student Patient yet
* Designed for selective promotion later

---

#### 3. Applicant Policy Acknowledgements

* Versioned acknowledgements
* Explicit consent tracking
* Promotion precondition

---

#### 4. Applicant Documents

* Upload + review flags
* Explicit inclusion / exclusion rules
* Rejection without data pollution

---

### Phase 2 Exit Criteria

* “Approved” has concrete meaning
* Review is auditable
* Decisions are defensible

---

## Phase 3 — Promotion Contract Completion (Legal Closure)

**Goal:** Make promotion **safe, complete, and irreversible**.

---

### Deliverables

#### 1. Full Promotion Mapping

* Applicant → Student
* Applicant Health → Student Patient
* Guardians → Student Guardians
* Files copied or moved deterministically

---

#### 2. Account Holder Resolution

* Explicit rule for account holder
* Promotion fails loudly if unresolved

---

#### 3. Student Patient Guarantee

* Created deterministically at promotion
* No orphan medical records
* Unique per Student

---

### Phase 3 Exit Criteria

* Promotion produces a fully valid Student
* No manual cleanup required
* All post-promotion records are consistent

---

## Phase 4 — Communication System (Admissions Reality)

**Goal:** Treat communication as **first-class data**.

---

### Deliverables

* Admissions Communication doctype (or equivalent)
* Linked to Inquiry / Applicant
* Directional (staff ↔ family)
* Channel-aware (email, portal, call)

Used for:

* Missing info requests
* Interview scheduling
* Decisions

---

### Phase 4 Exit Criteria

* No decision exists without a communication artifact
* Timeline tells the full admissions story

---

## Phase 5 — Portal & UX (Intentionally Last)

**Goal:** Improve experience **without weakening invariants**.

---

### Deliverables

* Applicant portal
* Progressive disclosure
* Notifications
* UX polish

---

### Rule

> UX may change.
> Contracts may not.

---

## Why This Order Matters

If you reverse this order:

* Portal first → data drift
* Automation first → silent errors
* Satellites first → unclear promotion rules

This plan enforces:

* Correctness before comfort
* Law before UX
* Structure before scale

---

## Canonical Summary

> Inquiry filters
> Applicant accumulates
> Interviews inform
> Promotion converts
> Student operates

Everything else is implementation detail.

---

### Status

* Phase 1: **In progress / partially implemented**
* Phase 1.5: **Design-locked (authoritative)**
* Phase 2+: **Blocked by design (correctly)**

---

### Final Check (Consistency)

* No governance duplicated
* No schema implied
* No execution assumptions leak upward
* Phase 2+ safely relies on Phase 1.5

---
