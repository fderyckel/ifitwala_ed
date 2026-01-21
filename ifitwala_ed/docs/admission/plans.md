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

Below is **Phase 2 restated in full**, cleanly, without reinterpretation, aligned with everything we locked so far.
This is **the authoritative Phase 2 block** you can drop into `plans.md`.

---

## Phase 2 — Admissions Intelligence (Decision Quality)

**Objective**
Enable **real, defensible admissions decisions** by introducing structured human judgment, legally meaningful intake data, and review artifacts — **without** touching UX, portals, or automation polish.

Phase 2 is about **meaning**, not mechanics.

> If Phase 1 makes admissions *possible*,
> Phase 2 makes admissions *credible*.

---

### Core Principles (Phase 2)

* Admissions decisions are **human-led**, not form-led
* Data collected here is **pre-canonical** and **review-scoped**
* Nothing in Phase 2 creates Students
* Nothing in Phase 2 auto-approves or auto-rejects
* Every approval must be explainable after the fact

---

### 2.1 Applicant Interview (Staff-Only, Informational)

### Purpose

Capture **qualitative human judgment** that cannot be reduced to fields or checklists.

Supports:

* family interviews
* student interviews
* joint interviews
* multiple interview rounds
* multiple interviewers

### Object: Applicant Interview

**Scope**

* Linked to **Student Applicant**
* Exists only pre-promotion

**Characteristics**

* Staff-only (never editable by family)
* Informational, non-binding
* Multiple allowed per Applicant

**Conceptual attributes (not fieldnames)**

* Applicant
* Interview type

  * Family
  * Student
  * Joint
* Interviewers (one or many staff)
* Date & duration
* Mode (in-person / online / phone)
* Notes (free text)
* Impression / outcome (non-decisive)
* Confidentiality level (e.g. admissions only)

### Invariants

* Interviews **inform** decisions; they never **trigger** them
* Interview data is **not copied** to Student by default
* Absence of an interview is not automatically disqualifying
* Multiple interviews may coexist without conflict

---

### 2.2 Applicant Health Profile (Pre-Student)

### Purpose

Collect **health-related intake data** required for admissions review
*without* creating medical records prematurely.

### Object: Applicant Health Profile

**Scope**

* Linked to **Student Applicant**
* Family-entered, staff-reviewed
* Exists only before promotion

### Characteristics

* Captures declared conditions, allergies, accommodations
* Allows staff notes and review flags
* Designed to later map selectively into Student Patient

### Invariants

* Applicant Health ≠ Student Patient
* No Student Patient is created in Phase 2
* Health data remains editable only while Applicant is mutable
* Health completeness may be a promotion precondition (school-defined)

---

### 2.3 Applicant Policy Acknowledgements (Legal Intake)

### Purpose

Record **explicit, versioned consent** for institutional policies.

Policies may include:

* safeguarding
* behavior
* technology use
* medical consent
* photography / media
* enrollment terms

### Characteristics

* Versioned acknowledgements
* Explicit acceptance (not implied)
* Timestamped
* Linked to Applicant

### Invariants

* Acknowledgements are **not retroactive**
* Policy versions matter
* Promotion may require specific acknowledgements
* Rejection does not pollute Student records

---

### 2.4 Applicant Documents (Evidence Layer)

### Purpose

Attach **supporting documents** required for admissions decisions.

Examples:

* transcripts
* recommendation letters
* passports / visas
* assessments
* reports

### Characteristics

* Linked to Student Applicant
* Each document has review status (pending / accepted / rejected)
* Staff review flags exist independently of upload

### Invariants

* Documents are not canonical until promotion
* Rejected documents are **not copied** to Student
* Absence of documents blocks promotion only if configured
* Documents remain auditable even if Applicant is rejected

---

### 2.5 Decision Readiness (Completeness, Not Automation)

Phase 2 introduces the concept of **decision readiness**, not auto-decisions.

### Characteristics

* Readiness is evaluated by:

  * Applicant data presence
  * Interviews completed (if required)
  * Policies acknowledged
  * Documents reviewed
* Requirements are **school-configurable** (Phase 1.5 alignment)

### Invariants

* “Approved” means **requirements satisfied + human judgment**
* No automatic transitions to Approved or Rejected
* Staff explicitly sets decision states

---

### Phase 2 Exit Criteria

Phase 2 is complete when:

* Applicant review is **substantive**, not procedural
* Approval and rejection decisions are **defensible**
* Health, documents, interviews, and policies exist as first-class data
* Promotion preconditions can be evaluated deterministically
* No data collected here leaks into Student prematurely

---

### Explicit Non-Goals (Phase 2)

Phase 2 must **not** introduce:

* Applicant portal UX
* Workflow automation
* Notifications
* Auto-enrollment
* Billing logic
* Student creation side-effects

Those belong to later phases.

---

### Phase 2 Summary

> Phase 1 creates structure
> Phase 2 creates meaning
> Phase 3 creates legal closure

If Phase 2 is skipped or rushed, admissions becomes a checkbox exercise
instead of an institutional decision process.

---

## Phase 3 — Promotion Contract Completion (Legal Closure)

**Objective**
Make the transition from **Applicant → Student** legally safe, operationally complete, and **irreversible**.

Phase 3 is where admissions **ends** and institutional operations **begin**.

> If Phase 2 makes decisions defensible,
> Phase 3 makes them **binding**.

---

### Core Principles (Phase 3)

* Promotion is a **legal boundary**
* Data crosses that boundary **once**
* After promotion, admissions has no authority over Student data
* No manual cleanup is required post-promotion
* Failures must be loud, explicit, and blocking

---

### 3.1 Full Promotion Mapping (Applicant → Student)

### Purpose

Define **exactly** what crosses the boundary into canonical records.

### Required Effects of Promotion

Promotion must deterministically create or populate:

1. **Student**

   * Canonical identity
   * Immutable admissions lineage (`student_applicant`)
2. **Student Guardians**

   * From Applicant Guardians
   * With role mapping preserved
3. **Student Patient**

   * Created exactly once
   * Populated selectively from Applicant Health
4. **Linked Users / Contacts**

   * Created or linked if missing
   * Never duplicated

### Invariants

* Promotion is atomic (all-or-nothing)
* Partial promotion is forbidden
* Duplicate prevention is mandatory
* Promotion logic lives **only** in the Applicant controller

---

### 3.2 Account Holder Resolution (Hard Requirement)

### Purpose

Resolve **financial and legal responsibility** before the Student enters operations.

### Requirements

* An **Account Holder** must be resolved at promotion time
* Source may be:

  * one of the guardians
  * an explicitly designated billing contact
* Resolution rules must be explicit and configurable

### Invariants

* Promotion **fails hard** if account holder cannot be resolved
* No implicit defaults
* No post-promotion patching

---

### 3.3 Student Patient Guarantee (Medical Integrity)

### Purpose

Ensure medical records are created **once**, correctly, and never orphaned.

### Requirements

* A `Student Patient` record must exist for every Student
* Created automatically during promotion
* Unique per Student

### Invariants

* No Student exists without a Student Patient
* No Student Patient exists without a Student
* Applicant Health data is copied selectively (school-configured)

---

### 3.4 File & Data Finalization

### Purpose

Ensure documents and files end up in their **final legal location**.

### Requirements

* Accepted Applicant Documents are:

  * copied or moved to Student context
  * re-linked correctly
* Rejected / withdrawn documents are excluded
* File ownership and paths are correct

### Invariants

* No dangling file references
* No duplicate files created unintentionally
* Applicant retains historical record, but Student owns canonical files

---

### 3.5 Promotion Audit & Immutability

### Purpose

Make promotion **provable and irreversible**.

### Required Audit Data

* promoted_by
* promoted_at
* source_applicant
* target_student

### Invariants

* Applicant becomes permanently read-only
* Promotion cannot be undone
* Any correction requires **new administrative actions**, not reversal

---

### 3.6 Failure Semantics (Safety Over Convenience)

Promotion must **fail loudly** if:

* required Applicant data is missing
* required policies are not acknowledged
* account holder is unresolved
* medical minimums are unmet
* duplicate Student would be created

**Rules**

* No partial side-effects
* No silent skips
* No background retries

---

### Phase 3 Exit Criteria

Phase 3 is complete when:

* Promotion produces a fully valid, operational Student
* No manual intervention is required post-promotion
* All downstream systems (attendance, health, billing, LMS) can assume correctness
* Admissions data is frozen and auditable
* Legal and operational teams can trust the result

---

### Explicit Non-Goals (Phase 3)

Phase 3 must **not** introduce:

* Portal UX
* Notifications
* Automation heuristics
* Enrollment logic
* Billing workflows
* Communication flows

Those belong to later phases.

---

### Phase 3 Summary

> Phase 1 makes promotion possible
> Phase 2 makes promotion justifiable
> Phase 3 makes promotion **final**

After Phase 3, the Applicant lifecycle is over —
the Student lifecycle begins.

---

## Phase 4 — Communication System (Admissions Reality)

**Objective**
Treat admissions communication as **first-class institutional data**, not an email side-effect or UI convenience.

Phase 4 acknowledges a hard truth:

> Admissions is not primarily data entry.
> It is **structured communication over time**.

If Phase 4 is skipped, the system will **function** but will not be **trusted**.

---

### Core Principles (Phase 4)

* Every admissions decision must be communicable and auditable
* Communication must be:

  * persistent
  * role-aware
  * time-ordered
* Email is a **channel**, not a record
* Portals are **interfaces**, not sources of truth

---

### 4.1 Admissions Communication as a First-Class Object

### Purpose

Create a canonical record of **what was communicated**, **to whom**, and **why**.

### Object: Admissions Communication

**Scope**

* Linked to either:

  * Inquiry **or**
  * Student Applicant
* Never directly to Student

**Characteristics**

* Directional:

  * staff → family
  * family → staff
* Channel-aware:

  * email
  * portal message
  * phone summary
  * in-person note
* Persisted independently of delivery success

### Conceptual attributes (not fieldnames)

* linked_record (Inquiry / Applicant)
* direction
* channel
* subject / purpose
* body or structured summary
* sent_by
* sent_at
* visibility scope (staff-only / shared)

---

### 4.2 Communication Types (Non-Exhaustive)

Admissions Communication must support at least:

* Invitation to apply
* Requests for missing information
* Interview scheduling and follow-ups
* Decision notifications (approval / rejection)
* Clarifications and family responses
* Internal admissions notes (non-shared)

**Invariant**

> No admissions decision exists without a corresponding communication artifact.

---

### 4.3 Timeline Integrity & Audit

### Purpose

Ensure the admissions story can be reconstructed **years later**.

### Requirements

* All communications appear in:

  * Inquiry timeline (early)
  * Applicant timeline (post-invitation)
* Timestamps are authoritative
* Actor identity is preserved
* Deletions are forbidden (only redaction / supersession)

### Invariants

* Timeline order is canonical
* Communications survive Applicant rejection
* Communications are never copied to Student

---

### 4.4 Role-Aware Visibility

### Purpose

Prevent information leakage while maintaining transparency.

### Rules

* Families see:

  * messages explicitly shared with them
* Admissions staff see:

  * all communications for Applicants in their scope
* Admission Directors see:

  * cross-school communications
* Internal notes are never visible to families

Visibility rules must align with **Phase 1.5 governance**.

---

### 4.5 Delivery Is a Side-Effect, Not the Record

### Principle

Sending an email or notification is **not** the same as recording communication.

### Rules

* The Communication record is created **first**
* Delivery (email, SMS, portal notification) is:

  * optional
  * asynchronous
  * retryable
* Delivery failure does not erase communication intent

---

### Phase 4 Exit Criteria

Phase 4 is complete when:

* Every admissions action has a traceable communication
* Families and staff see consistent histories
* Audits can reconstruct who said what and when
* Email inboxes are no longer the source of truth
* Admissions decisions are legally defensible via data

---

#### Explicit Non-Goals (Phase 4)

Phase 4 must **not** introduce:

* Applicant portal UX
* Workflow automation
* Decision heuristics
* Chat systems
* Real-time messaging

Those belong to later phases.

---

#### Phase 4 Summary

> Phase 1 creates structure
> Phase 2 creates meaning
> Phase 3 creates closure
> Phase 4 creates trust

Without Phase 4, admissions works.
With Phase 4, admissions **holds up under scrutiny**.

---

## Phase 5 — Portal & UX (Experience Without Compromise)

**Objective**
Deliver a family-facing and staff-assisting experience that improves clarity,
reduces friction, and scales — **without weakening any canonical admissions contracts**.

> Phase 5 changes *how* users interact.
> It must never change *what is true*.

---

### Core Principle

> **UX is an interface, not an authority.**
> All truth lives in server-side contracts and governance layers.

---

### 5.1 Applicant & Family Portal (Read/Write Interface)

### Purpose

Provide families with a **guided, progressive interface** to complete
admissions requirements **without exposing internal state or logic**.

### Characteristics

* Built entirely on top of:

  * Student Applicant
  * Applicant sub-domains
  * Admissions Communication
* No direct access to Student or Student Patient
* No direct status mutation

### Capabilities

Families may:

* View application progress
* Complete required Applicant sections
* Upload documents
* Acknowledge policies
* Respond to Missing Info requests
* Read shared communications
* Submit application (explicit action)

### Prohibitions

Families must **never**:

* Change `application_status` directly
* See internal notes or interviews
* Trigger promotion
* Edit after submission unless explicitly reopened

---

### 5.2 Progressive Disclosure & Section Gating

### Purpose

Prevent overwhelm and enforce correctness.

### Rules

* Sections unlock based on:

  * application_status
  * school configuration (Phase 1.5)
* Completion indicators are computed, not manual
* Submission is blocked unless minimum completeness is met

---

### 5.3 Staff Admissions Workspace (Assistive UX)

### Purpose

Support admissions staff **without duplicating logic**.

### Capabilities

Staff may:

* Review Applicant completeness
* View interviews, documents, health summaries
* Send structured communications
* Change Applicant status via server methods
* Promote Applicant (with confirmation)

### Prohibitions

Staff UI must **not**:

* Bypass permission checks
* Encode school-specific logic
* Contain hidden side effects

---

### 5.4 Notifications & Delivery (UX Layer Only)

### Principle

Notifications are **derivative**, not authoritative.

### Rules

* Triggered by:

  * Communication creation
  * Status transitions
* Channels:

  * email
  * portal notification
  * push (future)
* Failure to notify does not mutate state

---

### 5.5 UX Guardrails (Non-Negotiable)

All Phase 5 UX must obey:

1. **No schema mutation**
2. **No new business logic**
3. **No status changes without server calls**
4. **No cross-school leakage**
5. **No implicit promotion**

Any UX requiring contract changes must:

* stop
* return to Phase 1.5 or earlier

---

### Phase 5 Exit Criteria

Phase 5 is complete when:

* Families can complete applications end-to-end
* Staff can review and decide without workarounds
* All admissions actions remain auditable
* No UX-only state exists
* Removing the UI does not change system truth

---

### Explicit Non-Goals (Phase 5)

Phase 5 does **not** include:

* Automated decisions
* AI recommendations
* Real-time chat
* CRM-style pipelines
* Cross-year re-applications

Those belong to future phases.

---

### Phase 5 Summary

> Phase 1 enforces structure
> Phase 2 adds substance
> Phase 3 ensures legality
> Phase 4 records truth
> Phase 5 reveals it safely

When Phase 5 is complete,
**Ifitwala_Ed admissions becomes usable — without becoming fragile.**

---
