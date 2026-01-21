# Admissions Canonical Contract (ACC)

**Ifitwala_Ed — v1 (Living Document)**

> Admissions is not a form.
> It is a staged data-promotion pipeline with legal boundaries.

This document defines the **authoritative admissions lifecycle**, invariants, and promotion rules.
All code, doctypes, UI, workflows, and automation **must conform**.

---

## 0. Scope & Authority

This contract governs:

* Inquiry
* Student Applicant
* Applicant sub-domains (health, interview, documents, policies, etc.)
* Promotion to Student
* Admissions communication and audit

This document supersedes:

* UI assumptions
* Form layouts
* Portal workflows

If code contradicts this contract, **the code is wrong**.

---

## 1. Canonical Objects & Boundaries

### 1.1 Inquiry (Intent & Triage Object)

**Purpose**

* Capture initial interest
* Support admissions triage, SLA, and assignment
* Filter before heavy data collection

**Characteristics**

* Lightweight
* Discardable
* Operational

**Invariants**

* Inquiry NEVER becomes a Student
* Inquiry data is NOT legally authoritative
* Inquiry may be archived without consequences

**Terminal outcomes**

* Qualified → create Student Applicant
* Archived → end of lifecycle

---

### 1.2 Student Applicant (Staging Container)

**Purpose**

* Sole container for **all pre-student data**
* Aggregate forms, interviews, documents, consents
* Enable review and decision-making

**Characteristics**

* Mutable (until locked)
* Reviewable
* Legally sensitive
* Non-canonical

**Invariants**

* All intake data lives here (directly or via sub-records)
* Families NEVER write to Student or Student Patient
* Applicant may be rejected and deleted without polluting student records

**Terminal outcomes**

* Approved → Promoted to Student
* Rejected → Archived (read-only)

---

### 1.3 Student (Canonical Institutional Record)

**Purpose**

* Represent an enrolled individual in the institution
* Anchor enrollment, attendance, LMS, health, compliance

**Characteristics**

* Canonical
* Auditable
* Permanent

**Invariants**

* Student is created ONLY via promotion
* Student data is never directly edited by families
* Admissions logic does not live here

---

## 2. Applicant Sub-Domains (Satellite Records)

Applicant sub-domains are **first-class**, Applicant-scoped records.

They:

* Mirror parts of student-level doctypes
* Exist only pre-promotion
* Are copy-/transform-able at promotion

### Mandatory sub-domains

* Applicant Identity
* Applicant Guardians
* Applicant Academic Background
* Applicant Health Profile
* Applicant Policy Acknowledgements
* Applicant Documents

### Optional / contextual

* Applicant Logistics
* Applicant Financial Responsibility
* Applicant Language Profile

---

## 3. Applicant Interview (NEW — Mandatory Architectural Element)

### 3.1 Purpose

Applicant Interview captures **qualitative human judgment** that cannot be reduced to forms.

It supports:

* Family interviews
* Student interviews
* Joint interviews
* Multiple interviewers
* Multiple interview rounds

### 3.2 Applicant Interview Object

**Ownership**

* Staff only (never editable by family)

**Key properties (conceptual, not fieldnames)**

* Applicant
* Interview type

  * Family
  * Student
  * Joint
* Interviewers (one or many staff)
* Date & duration
* Mode (in-person / online / phone)
* Notes (free text)
* Outcome / impression (non-binding)
* Confidentiality level (e.g. admissions only)

### 3.3 Invariants

* Interviews are **informational**, not decisions
* Interview outcomes do NOT auto-approve or reject
* Multiple interviews may exist per Applicant
* Interview data is NOT copied to Student by default

**Rationale**
OpenApply and Veracross treat interviews as advisory signals, not state transitions.

---

## 4. Admissions Workflow States

### 4.1 Inquiry States

* New
* Assigned
* Contacted
* Qualified
* Archived

### 4.2 Applicant States

| State        | Family Edit | Staff Edit | Promotion Allowed |
| ------------ | ----------- | ---------- | ----------------- |
| Draft        | ❌           | ✅          | ❌                 |
| Invited      | ✅           | ✅          | ❌                 |
| In Progress  | ✅           | ✅          | ❌                 |
| Submitted    | ❌           | ✅          | ❌                 |
| Under Review | ❌           | ✅          | ❌                 |
| Missing Info | ✅ (scoped)  | ✅          | ❌                 |
| Approved     | ❌           | ✅          | ✅                 |
| Rejected     | ❌           | ❌          | ❌                 |
| Promoted     | ❌           | ❌          | ❌                 |

**Rule**

> A state that does not change permissions or behavior must not exist.

---

## 5. Communication as a First-Class Concern

Admissions is primarily **communication**, not data entry.

### 5.1 Communication Principles

* Linked to Inquiry or Applicant
* Persisted (not email-only)
* Timestamped
* Role-aware (family vs staff)
* Auditable

### 5.2 Communication Types

* Requests for missing information
* Interview scheduling / follow-up
* Decisions (approval / rejection)
* Internal admissions notes

**Invariant**

> No admissions decision exists without a traceable communication artifact.

---

## 6. Promotion Contract (Applicant → Student)

### 6.1 Preconditions

* Applicant state = Approved
* Required sub-domains completed
* Required policies acknowledged
* Health minimums met (school-defined)

### 6.2 Promotion Actions

**Create**

* Student
* Student Patient
* Required Contacts / Users (if missing)

**Copy / Transform**

* Identity → Student (locked)
* Guardians → Student
* Health → Student Patient
* Policy acknowledgements (selective)

**Do NOT copy**

* Interviews
* Internal notes
* Rejected / withdrawn documents

### 6.3 Post-Promotion Effects

* Applicant becomes read-only
* Applicant links to Student
* Files moved or duplicated correctly
* Promotion metadata recorded (who / when)

### 6.4 Invariants

* Promotion is explicit
* Promotion is idempotent
* Promotion is irreversible

---

## 7. Design Prohibitions (Hard Rules)

The system must NEVER:

* Merge Applicant and Student
* Write Applicant data directly into Student Patient
* Auto-enroll programs from Applicant intent
* Treat interviews as decisions
* Allow family edits post-approval
* Create Students implicitly

---

## 8. Future Compatibility Guarantees

This contract supports:

* Sibling applications
* Re-applications
* Transfers
* Mid-year admissions
* External systems (visa, exam boards)
* Regulatory audits

Without schema rewrites.

---

## 9. Summary (Non-Negotiable Truth)

> Inquiry filters
> Applicant accumulates
> Interviews inform
> Promotion converts
> Student operates

Everything else is implementation detail.

---


Excellent material. What you’re asking for now is **editorial + architectural refinement**, not new ideas. # 1️⃣ Refined Admissions Canonical Contract (ACC)

Below is your document **polished**, not rewritten.
Think: *constitutional text*, not prose.

---

# Admissions Canonical Contract (ACC)

**Ifitwala_Ed — v1 (Living Document)**

> Admissions is not a form.
> It is a staged data-promotion pipeline with legal boundaries.

This document defines the **authoritative admissions lifecycle**, its **invariants**, and the **only allowed promotion path** from prospect to student.

All code, DocTypes, UI, workflows, background jobs, and automation **must conform**.

---

## 0. Scope & Authority

This contract governs **only** the admissions pipeline, specifically:

* Inquiry (public intake & triage)
* Student Applicant (pre-student staging)
* Applicant sub-domains (health, interview, documents, policies, etc.)
* Promotion to Student
* Admissions communication and audit

This contract **supersedes**:

* UI assumptions
* Web form design
* Portal UX
* Convenience shortcuts

If implementation contradicts this document, **the implementation is wrong**.

---

## 1. Canonical Objects & Legal Boundaries

### 1.1 Inquiry — *Intent & Triage Object*

**Purpose**

* Capture initial interest
* Support admissions triage, SLA tracking, and assignment
* Filter before collecting legally sensitive data

**Characteristics**

* Lightweight
* Operational
* Disposable

**Invariants**

* Inquiry **never** becomes a Student
* Inquiry data is **not legally authoritative**
* Inquiry may be archived without downstream consequences

**Terminal outcomes**

* **Qualified** → Applicant invitation permitted
* **Archived** → lifecycle ends

---

### 1.2 Student Applicant — *Staging Container (Admissions Core)*

**Purpose**

* Sole container for **all pre-student data**
* Aggregate forms, interviews, documents, consents
* Enable review, communication, and decision-making

**Characteristics**

* Mutable until locked
* Reviewable by staff
* Legally sensitive
* Explicitly **non-canonical**

**Invariants**

* All admissions data lives here (directly or via Applicant sub-records)
* Families **never** write to Student or Student Patient
* Applicant may be rejected or deleted without polluting student records

**Terminal outcomes**

* **Approved** → Eligible for promotion
* **Rejected** → Archived (read-only, non-promotable)
* **Promoted** → Locked forever

---

### 1.3 Student — *Canonical Institutional Record*

**Purpose**

* Represent an enrolled individual within the institution
* Anchor enrollment, attendance, LMS, health, compliance, and reporting

**Characteristics**

* Canonical
* Auditable
* Permanent

**Invariants**

* Student is created **only** via promotion
* Student data is never directly edited by families
* Admissions logic does not live here

---

## 2. Applicant Sub-Domains (Satellite Records)

Applicant sub-domains are **first-class**, Applicant-scoped records.

They:

* Mirror relevant parts of student-level data
* Exist **only** pre-promotion
* Are copied or transformed **only** during promotion

### Mandatory sub-domains

* Applicant Identity
* Applicant Guardians
* Applicant Academic Background
* Applicant Health Profile
* Applicant Policy Acknowledgements
* Applicant Documents

### Optional / contextual

* Applicant Logistics
* Applicant Financial Responsibility
* Applicant Language Profile

---

## 3. Applicant Interview — *Mandatory Architectural Element*

### 3.1 Purpose

Applicant Interview captures **qualitative human judgment** that cannot be reduced to structured forms.

It supports:

* Family interviews
* Student interviews
* Joint interviews
* Multiple interviewers
* Multiple interview rounds

### 3.2 Applicant Interview Record

**Ownership**

* Staff-only (never editable by family)

**Conceptual properties**

* Linked Applicant
* Interview type (Family / Student / Joint)
* Interviewers (one or more staff)
* Date & duration
* Mode (in-person / online / phone)
* Free-text notes
* Outcome / impression (non-binding)
* Confidentiality level

### 3.3 Invariants

* Interviews are **informational**, not decisions
* Interview outcomes never auto-approve or reject
* Multiple interviews per Applicant are allowed
* Interview data is **not copied** to Student by default

---

## 4. Admissions Workflow States

### 4.1 Inquiry States

* New
* Assigned
* Contacted
* Qualified
* Archived

### 4.2 Applicant States

| State        | Family Edit | Staff Edit | Promotion Allowed |
| ------------ | ----------- | ---------- | ----------------- |
| Draft        | ❌           | ✅          | ❌                 |
| Invited      | ✅           | ✅          | ❌                 |
| In Progress  | ✅           | ✅          | ❌                 |
| Submitted    | ❌           | ✅          | ❌                 |
| Under Review | ❌           | ✅          | ❌                 |
| Missing Info | ✅ (scoped)  | ✅          | ❌                 |
| Approved     | ❌           | ✅          | ✅                 |
| Rejected     | ❌           | ❌          | ❌                 |
| Promoted     | ❌           | ❌          | ❌                 |

**Rule**

> A state that does not change permissions, editability, or allowed actions must not exist.

---

## 5. Communication as a First-Class System

Admissions is primarily **communication**, not data entry.

### 5.1 Principles

* Linked to Inquiry or Applicant
* Persisted (not email-only)
* Timestamped
* Role-aware (family vs staff)
* Auditable

### 5.2 Communication Types

* Requests for missing information
* Interview scheduling and follow-ups
* Decisions (approval / rejection)
* Internal admissions notes

**Invariant**

> No admissions decision exists without a traceable communication artifact.

---

## 6. Promotion Contract — *Applicant → Student*

### 6.1 Preconditions

* Applicant state = Approved
* Mandatory sub-domains completed
* Required policies acknowledged
* Health minimums met (school-defined)

### 6.2 Promotion Actions

**Create**

* Student
* Student Patient
* Required Contacts / Users (if missing)

**Copy / Transform**

* Identity → Student (immutable)
* Guardians → Student
* Health → Student Patient
* Policy acknowledgements (selective)

**Explicitly excluded**

* Interviews
* Internal notes
* Rejected / withdrawn documents

### 6.3 Post-Promotion Effects

* Applicant becomes read-only
* Applicant links to Student
* Files moved or duplicated correctly
* Promotion metadata recorded (who / when)

### 6.4 Invariants

* Promotion is explicit
* Promotion is idempotent
* Promotion is irreversible

---

## 7. Design Prohibitions (Hard Rules)

The system must **never**:

* Merge Applicant and Student
* Write Applicant data directly into Student Patient
* Auto-enroll programs from Applicant intent
* Treat interviews as decisions
* Allow family edits post-approval
* Create Students implicitly

---

## 8. Future Compatibility Guarantees

This contract supports:

* Sibling applications
* Re-applications
* Transfers
* Mid-year admissions
* External systems (visa, exam boards)
* Regulatory audits

Without schema rewrites.

---

## 9. Canonical Truth

> Inquiry filters
> Applicant accumulates
> Interviews inform
> Promotion converts
> Student operates

Everything else is implementation detail.

---
