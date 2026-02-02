# Gap Audit — Admissions Canonical Contract vs Current Doctypes

## A) Inquiry (triage object) — Status: **aligned on handoff + transitions**, comms anchoring missing

### ✅ What already matches the contract

* **Public intake** exists (Inquiry Web Form).
* **Org/school consistency guard** exists (nested-set bounds check).
* **SLA + deadlines** are computed on save.
* **Assignment + “mark contacted”** logic exists and closes the correct ToDo.
* **Contact linking** exists (`create_contact_from_inquiry`).
* **Canonical handoff** exists (`invite_to_apply`, Inquiry ↔ Applicant link, idempotent).
* **Canonical states + transitions** enforced (New/Assigned/Contacted/Qualified/Archived).

### ❌ Gaps (must fix)

1. **Communication is not first-class**

   * **Missing:** a persisted “Admissions Communication” record (or at minimum a structured log object) linked to Inquiry/Applicant.
   * **Current:** comments exist, but no structured type for “message to family”, “missing info request”, “decision email sent”, etc.

   **Acceptance criteria**

   * There is a doctype (or pattern) that stores: direction (staff→family / family→staff), channel (email/portal/phone), subject, body/summary, sent_by, sent_at.
   * Inquiry actions write to it (not only comments).

---

## B) Student Applicant (staging container) — Status: **not yet a staging container**

Right now it’s basically: name + (program/AY/term) + image + status. No logic.

### ❌ Gaps (must fix)

1. **Applicant is missing the “container” responsibilities**

   * **Missing:** progress tracking, locking, review workflow behavior (linkage is partial).

   **Acceptance criteria**

   * Student Applicant can link to:

     * Origin Inquiry (`inquiry`) — implemented (PR-01)
     * Resulting Student (`student`) after promotion — pending
   * Applicant has a “lock/editability” behavior based on status (Draft/In Progress/Submitted/Under Review/Missing Info/Approved/Rejected/Promoted).

2. **No Applicant sub-domains exist**

   * Contract requires Applicant-scoped satellites (health, documents, policies, academics, guardians, etc.).
   * Current system has **Student Patient** only, but it requires a Student (so it cannot serve intake).

   **Acceptance criteria**

   * At least these Applicant-scoped doctypes exist (even minimal v1 shells):

     * Applicant Health Profile
     * Applicant Documents
     * Applicant Policy Acknowledgements
     * Applicant Academic Background
     * Applicant Guardians (or equivalent structure)
   * Each is linked to Student Applicant and has permissions consistent with the pipeline.

3. **Applicant Interview is missing**

   * You asked for it explicitly; it doesn’t exist yet.

   **Acceptance criteria**

   * Doctype “Applicant Interview” exists:

     * Link to Student Applicant
     * Interview type (Family/Student/Joint)
     * Interviewers (multi)
     * Notes + outcome
     * Staff-only write permissions
   * Multiple interviews per Applicant allowed.

4. **Applicant “completeness” / checklist layer is missing**

   * Without it, you can’t enforce “Approved requires X forms done”.

   **Acceptance criteria**

   * Either:

     * A generic checklist child table on Student Applicant, **or**
     * A computed completion model that checks satellite records.
   * Promotion preconditions can be evaluated deterministically.

5. **Applicant status enforcement is missing**

   * Status options now match the contract.
   * Missing: controller-enforced transitions + edit-lock rules.

   **Acceptance criteria**

   * Status changes only via controller methods; invalid transitions throw errors.
   * Editability enforced by status server-side.

---

## C) Student (canonical record) — Status: **good foundation**, but promotion dependencies are undefined

### ✅ What already matches the contract

* Student has a link to Student Applicant (`student_applicant`) — excellent for promotion lineage.
* Student is clearly canonical (lots of operational fields + guardians table).
* Student has `account_holder` **required** (important constraint).

### ❌ Gaps (must fix)

1. **Promotion contract is not implemented**

   * Student exists, but no controlled “Promote Applicant → Student” action exists yet.

   **Acceptance criteria**

   * A promotion method exists (ideally on Student Applicant) that creates Student, sets `student_applicant`, and updates Applicant status.
   * It is idempotent and logs promotion metadata.

2. **Account Holder requirement impacts admissions**

   * Student requires `account_holder`. Applicant stage doesn’t model it yet.
   * Decision needed: who/what is Account Holder during promotion (guardian? billing contact?).

   **Acceptance criteria**

   * Promotion contract specifies how `account_holder` is determined/created.
   * Promotion fails with a clear error if account holder cannot be resolved.

3. **Guardian capture boundary is unclear**

   * Student has guardians child table; Applicant has no guardian model yet.
   * Need mapping: Applicant guardians → Student guardians on promotion.

   **Acceptance criteria**

   * Applicant guardian structure exists and maps 1:1 into Student guardians during promotion.

---

## D) Student Patient (post-student health) — Status: **correctly post-promotion**, missing promotion wiring + intake boundary

### ✅ What already matches the contract

* Student Patient is strictly tied to Student (`student` is required + unique). Good: it prevents orphan medical records.
* It syncs photo from Student, which is consistent with your staff visibility intent.
* It has `medical_info` and `completion_state`.

### ❌ Gaps (must fix)

1. **No Applicant-stage health staging**

   * Since Student Patient requires Student, you *must* introduce Applicant Health Profile (or decide to create Student earlier, but that breaks your stated process).

   **Acceptance criteria**

   * Applicant Health Profile exists.
   * Promotion copies relevant info into Student Patient.

2. **Promotion does not auto-create Student Patient**

   * There’s no code yet that ensures Student Patient exists on promotion.

   **Acceptance criteria**

   * Promotion creates Student Patient deterministically (or schedules/queues it, but result must be guaranteed).
   * Duplicate prevention enforced (unique on student).

---

# The single most logical implementation order (agent-ready)

## Phase 1 — Pipeline wiring (no satellites yet)

1. Add Inquiry → Applicant creation method + link + audit
2. Expand Applicant statuses to contract semantics + lock/edit rules
3. Add Applicant → Student promotion method (stub) that creates bare Student + links back

## Phase 2 — Minimum satellites to make approval meaningful

4. Add Applicant Interview doctype (staff-only)
5. Add Applicant Health Profile (family input + staff review)
6. Add Applicant Policies (versioned acknowledgements)
7. Add Applicant Documents (uploads + review status)

## Phase 3 — Promotion contract completion

8. Implement full mapping: Applicant → Student + Student Patient + guardians + files
9. Add communication doctype and enforce “Missing Info request” as a first-class artifact

---


# Refined Gap Audit (Sharper, Agent-Executable)

Your gap audit is **correct**; I’m tightening it into *actionable deltas*.

### Inquiry — gaps

* ❌ No **Invite to Apply** action (explicit handoff)
* ❌ No structured Admissions Communication record
* ❌ State transitions not centrally enforced

### Student Applicant — gaps

* ❌ Not yet a true staging container
* ❌ No Applicant sub-domains
* ❌ No Applicant Interview
* ❌ No completeness / readiness evaluation
* ❌ Status semantics too coarse

### Student — gaps

* ❌ Promotion method not implemented
* ❌ Account Holder resolution not specified
* ❌ Guardian mapping undefined

### Student Patient — gaps

* ❌ No Applicant-stage health staging
* ❌ Promotion does not guarantee creation

This audit is **final** unless you change the contract.

---
