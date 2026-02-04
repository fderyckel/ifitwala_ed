Below is the **authoritative, updated version** of **`guardian_actions_contract.md`**, written for **humans and coding agents**, and **incorporating Monitoring Mode** as an explicit, high-impact action with guardrails.

This **supersedes v0.1** and can be committed as-is.

---

# Guardian Actions — Contract (v0.2)

**Ifitwala_Ed — Authoritative**
Status: Draft (Phase-0, patched)
Audience: Humans, coding agents
Scope: Actions available to Guardians via the Guardian Portal
Last updated: 2026-02-02

---

## 1. Purpose

This document defines **what Guardians may do**, **what those actions affect**, and **what they can never change**.

It exists to:

* prevent authority creep
* protect legal, academic, and financial integrity
* separate *visibility* from *agency*
* ensure all Guardian actions are explicit, auditable, and policy-compliant

**An action is a legally and systemically meaningful event.**

---

## 2. Core Principles (Locked)

### 2.1 Action ≠ Edit

Guardians may **initiate actions**, but may not **edit institutional truth**.

Actions may:

* acknowledge
* request
* communicate
* submit supporting material
* initiate workflows
* enable optional modes for themselves

Actions must never:

* mutate academic records
* rewrite staff input
* alter reporting outcomes
* change legal relationships
* bypass publication or reporting states

---

### 2.2 Explicit Authority Only

A Guardian may perform an action **only if**:

* a valid Guardian ↔ Student relationship exists
* the action applies to the Guardian role
* the action context is valid (Student / Guardian / School)

No implicit authority.
No inferred permission.
No “helpful shortcuts”.

---

### 2.3 Auditability Is Mandatory

Every Guardian action must be:

* timestamped
* attributed to a specific user
* context-bound (Guardian, Student, School)
* immutable once committed

Actions are **events**, not preferences.

---

## 3. Action Categories (Authoritative)

Guardian actions are grouped by **intent**, not by UI placement.

---

## 4. Legal & Consent Actions

### 4.1 Acknowledge Policy / Form

**Intent**
Provide explicit legal or procedural consent.

**Who**

* Guardian (for self)
* Guardian acknowledging **for a linked Student**, if permitted by policy

**Affects**

* Creates a `Policy Acknowledgement` record
* Does not modify policy text or version

**Rules**

* No proxy consent for other adults
* No revocation
* No silent acknowledgement
* New policy versions always require new acknowledgement

**Risk level**

* **High (legal)**

**Required protections**

* Clear policy text
* Explicit confirmation
* Adult-only gating
* Full audit trail

---

## 5. Communication Actions

### 5.1 Read Communication

**Intent**
Stay informed.

**Rules**

* Read state may be tracked
* Communication content is immutable once sent

---

### 5.2 Respond / React (Phase-2)

**Intent**
Acknowledge receipt or continue a conversation.

**Rules**

* Responses are append-only
* No editing of original messages
* Availability may be school-scoped or phased

**Note**
Execution may be deferred; **intent is locked**.

---

## 6. Scheduling & Meeting Actions

### 6.1 Book a Meeting

**Intent**
Request or reserve structured interaction with staff.

**Affects**

* Creates a booking request or confirmed slot
* Does not modify staff schedules directly

**Rules**

* Availability is staff-controlled
* Guardian cannot override constraints
* Cancellations follow school policy

---

## 7. Document & File Actions

### 7.1 Upload Document

**Intent**
Provide supporting material (forms, evidence, records).

**Affects**

* Creates a `File` record
* Links file to an explicit context (Student / Application / Case)

**Rules**

* Purpose must be explicit
* File classification enforced
* No overwrite of existing records

**Compliance**

* GDPR-aligned
* Retention policies apply
* No implicit reuse across contexts

---

## 8. Financial Actions

### 8.1 View Fees / Invoices

**Intent**
Understand financial obligations.

**Rules**

* Read-only
* No modification

---

### 8.2 Pay Fees

**Intent**
Settle financial obligations.

**Affects**

* Creates a payment transaction
* Does not modify invoice truth

**Risk level**

* **Very high (financial)**

**Required protections**

* Adult-only gating
* Re-authentication or explicit confirmation
* Clear amount, currency, and context

---

## 9. Monitoring Mode Actions (Opt-In, High-Impact)

### 9.1 Enable Monitoring Mode

**Intent**
Allow the Guardian to receive **more immediate visibility and alerts** about published academic results.

**Default state**

* Monitoring Mode is **disabled**
* System operates in **Awareness Mode**

**Scope**

* Enabled **per Guardian**
* Configured **per Student**
* Never global
* Never staff-controlled

**Effects (bounded)**

* Near-real-time notification when **published** Task Outcomes appear
* Optional alerts when **published results** fall below Guardian-defined thresholds

**Hard limits**
Monitoring Mode must **never**:

* expose draft or unpublished data
* bypass `published_to_parents` gates
* expose live gradebook views
* compute rolling averages
* compare siblings
* apply default thresholds

**Risk level**

* **Medium–High (wellbeing & relational)**

**Required protections**

* Clear explanation of consequences
* Explicit confirmation (not a silent toggle)
* Easy opt-out
* Audit logging of enable / disable events

---

### 9.2 Disable Monitoring Mode

**Intent**
Return to Awareness Mode.

**Rules**

* Immediate effect
* No historical data deleted
* No penalty or restriction

---

## 10. Explicitly Forbidden Actions (Non-Negotiable)

Guardians must **never** be able to:

* change Guardian ↔ Student relationships
* change legal identity or contact records
* edit academic results or feedback
* modify behaviour or health logs
* approve or override staff actions
* compare siblings academically
* bypass reporting or publication states

Requests for such changes must:

* be routed through staff workflows
* be logged as **requests**, not actions

---

## 11. Phase Awareness

Not all actions may be available in Phase-1.

**Invariant**

> If an action exists conceptually, its **authority, scope, and limits** must already be defined here.

UI availability ≠ permission.

---

## 12. Enforcement Rules (Server-Side, Mandatory)

All Guardian actions must be enforced:

* server-side
* with role + relationship validation
* with explicit context checks
* with immutable event logging

Frontend gating is **never sufficient**.

---

## 13. Phase-0 Lock Statement

> This document defines the **complete action authority of Guardians**.
>
> Any feature enabling Guardian interaction must conform to this contract.
>
> Deviations require:
>
> * explicit contract revision
> * governance review
> * legal consideration

---

