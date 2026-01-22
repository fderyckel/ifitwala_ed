# Admissions Portal (SPA) — Canonical Architecture Note

**Ifitwala_Ed | v1 (Locked)**

> **Status:** Canonical, binding
> **Scope:** Admissions-facing portal only (pre-guardian, pre-student)
> **Authority order:**
>
> 1. `spa_architecture_and_rules.md`
> 2. `overlay_and_workflow.md`
> 3. This document
>
> If anything here conflicts with SPA rules, **SPA rules win**.

---

## 0. Problem Being Solved (No Hand-Waving)

Admissions needs a **secure, authenticated, limited-scope portal** for applicants/families **before** they become Guardians or Students.

Constraints:

* User **must be logged in**
* User **must not** access Guardian or Student portals
* User **must not** see Desk
* UX must follow **SPA + Tailwind + HeadlessUI** rules
* Permissions must be **explicit, revocable, auditable**
* Must scale to:

  * shared URLs
  * password resets
  * partial completion
  * future identity upgrade (Applicant → Guardian)

This **cannot** be a Frappe Web Form.
This **must** be a Vue SPA surface.

---

## 1. Portal Type Decision (Locked)

### ✅ Chosen approach

**Option 2 — Custom Vue + Tailwind SPA (Portal)**

### ❌ Explicitly rejected

| Option                | Why it fails                                           |
| --------------------- | ------------------------------------------------------ |
| Frappe Web Form       | Anonymous by default, weak auth, no workflow lifecycle |
| Desk Form             | Wrong UX, wrong audience, permission risk              |
| Guardian Portal reuse | Leaks assumptions + future coupling                    |
| Public Vue page       | No identity, no audit trail                            |

**Conclusion:**
Admissions Portal is a **standalone SPA surface**, authenticated, role-scoped, and lifecycle-aware.

---

## 2. Portal Position in the System

```
Inquiry
   ↓
Student Applicant  ←── Admissions Portal (THIS)
   ↓
Guardian + Student (identity upgrade)
```

The Admissions Portal **only** operates on **Student Applicant** (and child artifacts).

It has **zero knowledge** of:

* Guardian
* Student
* Academic workflows
* Finance
* Attendance
* LMS

---

## 3. Authentication Model (Locked)

### 3.1 Identity type

Admissions users are **real Frappe Users**, not guests.

* Created by **Admissions Staff**
* Login + password issued (or reset link)
* Can be disabled at any time

This gives:

* auditability
* revocation
* rate-limit protection
* password hygiene
* future upgrade path

---

### 3.2 User lifecycle

**Creation**

* Admissions staff creates a User
* Assigns **Admissions Applicant** role
* Links User → Student Applicant

**Active**

* User logs in
* Can access only Admissions Portal routes

**Upgrade**

* On acceptance → later promoted to Guardian
* Old role removed
* New permissions applied

**Revoke**

* Disable User
* All access gone instantly

---

## 4. Role Model (NEW — LOCKED)

### 4.1 New role: `Admissions Applicant`

This role **must exist**.

It is **not optional**.

---

### 4.2 Role intent

The role represents:

> “A pre-guardian identity allowed to complete and review admissions materials for a single applicant.”

It is **not** a family role
It is **not** a student role
It is **not** a staff role

---

### 4.3 Role capabilities (authoritative)

| Capability             | Allowed                                    |
| ---------------------- | ------------------------------------------ |
| Login                  | ✅                                          |
| Access Vue SPA         | ✅ (Admissions routes only)                 |
| Access Desk            | ❌                                          |
| Access Guardian Portal | ❌                                          |
| Access Student Portal  | ❌                                          |
| Access API             | ✅ (strictly whitelisted, applicant-scoped) |

---

## 5. Permission Matrix (Locked)

### 5.1 Doctype-level permissions

#### **Student Applicant**

| Action | Permission              |
| ------ | ----------------------- |
| Read   | ✅ (own only)            |
| Write  | ✅ (allowed fields only) |
| Create | ❌                       |
| Delete | ❌                       |
| Submit | ❌                       |

Ownership is enforced **server-side** via:

* linked User
* explicit permission checks
  Never inferred in the SPA.

---

#### **Applicant Documents / Interviews / Notes**

| Action           | Permission |
| ---------------- | ---------- |
| Upload           | ✅          |
| View             | ✅          |
| Delete           | ❌          |
| Edit staff notes | ❌          |

Applicants can **add**, not curate history.

---

### 5.2 API-level enforcement

All endpoints used by the Admissions Portal must:

* explicitly check `frappe.session.user`
* verify role = `Admissions Applicant`
* verify ownership via `student_applicant`
* fail fast with translated errors

No implicit trust.
No “if role then allow all”.

---

## 6. SPA Surface & Routing (Locked)

### 6.1 Route namespace

Admissions Portal lives under **its own SPA base**, e.g.:

```
/admissions/*
```

It must **not** live under:

* `/portal/student`
* `/portal/guardian`
* `/portal/staff`

This avoids:

* router contamination
* layout leakage
* permission confusion

---

### 6.2 Layout shell

Admissions Portal has its **own layout shell**, minimal and calm:

* No staff navigation
* No academic widgets
* No dashboards
* Focused task flow

It may share:

* tokens
* components
* overlay system

It must **not** share:

* staff shell
* guardian shell

---

## 7. SPA Architecture Rules (Inherited)

The Admissions Portal **inherits all SPA rules**, without exception:

* No API calls in pages
* Services own mutations
* Overlays close immediately on success
* UI signals used for invalidation
* Pages are refresh owners
* Transport unwrapping happens once

Nothing about admissions weakens A+ discipline.

---

## 8. Overlay & Workflow Rules (Applied)

Admissions actions that:

* upload documents
* submit information
* confirm declarations
* acknowledge steps

➡️ **must be workflow overlays**

Rules:

* Overlay performs mutation
* On success → closes immediately
* Service emits invalidation signal
* Page refreshes

No “wizard logic” in pages.
No implicit completion.

---

## 9. Data Ownership & Safety

### 9.1 Single-applicant scope

An Admissions Applicant user is linked to **exactly one** Student Applicant.

No:

* sibling browsing
* multiple applicants
* switching context

This is enforced **server-side**, not via UI hiding.

---

### 9.2 GDPR alignment (baseline)

* All uploads are linked to Student Applicant
* All files are deletable via Applicant purge
* No documents live directly on User
* Identity can be erased independently of application record

(Full GDPR policy handled elsewhere; this portal does not violate it.)

---

## 10. What This Portal Is *Not*

To avoid future drift:

This portal is **not**:

* a CMS
* a Guardian preview
* a messaging platform
* a chat system
* a workflow engine

It is a **controlled data-completion surface**.

---

## 11. Phase Boundary (Very Explicit)

This document covers **everything up to Phase 5**.

It **does not define**:

* Phase 5A (identity upgrade to Guardian)
* Phase 5B (multi-guardian linking)
* Phase 5C (handoff to Guardian Portal)

Those phases **must not leak backwards** into this design.

---

## 12. Final Invariant (Read Twice)

> The Admissions Portal is a **standalone, authenticated SPA surface**
> with its **own role**, **own permission envelope**,
> and **zero coupling** to Student or Guardian portals.

If you violate this:

* you break security
* you break upgrade paths
* you break auditability

---






Good. Here is **A and B**, clean, explicit, and **Codex-ready**, fully aligned with your SPA rules and with **zero Phase-5 leakage**.

Nothing below invents semantics. Everything is derived from what you already locked.

---

# Admissions Portal (SPA) — Phase-5 Pre-Spec

**Section A — DTOs & API Contracts**
**Section B — Route Map & Page Responsibilities**

> **Status:** Canonical for implementation
> **Scope:** Admissions Portal only
> **Authority:**
>
> 1. `spa_architecture_and_rules.md`
> 2. `overlay_and_workflow.md`
> 3. This document

---

## A. Admissions Portal DTOs & API Contracts (Locked)

### A.1 Guiding Rules (Non-Negotiable)

* Portal **never mutates truth directly**
* Portal **never infers permissions**
* Portal **never unwraps transport**
* All logic lives in **server + services**
* DTOs are **Applicant-scoped only**

If an endpoint touches `Student`, `Guardian`, or `Employee`, it does **not** belong here.

---

## A.2 Identity & Session Contract

### Endpoint

```
GET /api/admissions/session
```

### Purpose

Resolve **who is logged in** and **what applicant they are bound to**.

### Returns (Domain DTO)

```ts
AdmissionsSession {
  user: {
    name: string
    full_name: string
    roles: ["Admissions Applicant"]
  }
  applicant: {
    name: string
    application_status: ApplicantStatus
    school: string
    organization: string
    is_read_only: boolean
  }
}
```

### Invariants

* Exactly **one applicant**
* If no applicant → **403**
* If role mismatch → **403**

---

## A.3 Applicant Snapshot DTO (Read Model)

### Endpoint

```
GET /api/admissions/applicant/:name/snapshot
```

### Purpose

Single authoritative read for the **Applicant Overview page**.

### Returns

```ts
ApplicantSnapshot {
  applicant: {
    name: string
    application_status: string
    submitted_at?: datetime
    decision_at?: datetime
  }

  completeness: {
    health: CompletionState
    documents: CompletionState
    policies: CompletionState
    interviews: CompletionState
  }

  next_actions: NextAction[]
}
```

### Rules

* No mutation
* No derived UI logic
* Completeness is **computed server-side**

---

## A.4 Applicant Health DTO

### Endpoints

```
GET  /api/admissions/health/:applicant
POST /api/admissions/health/update
```

### DTO

```ts
ApplicantHealthPayload {
  declared_conditions: string
  allergies: string
  accommodations: string
}
```

### Rules

* POST allowed only if Applicant mutable
* Review status **not writable** by portal
* Staff notes invisible

---

## A.5 Applicant Documents DTO

### Endpoints

```
GET  /api/admissions/documents/:applicant
POST /api/admissions/documents/upload
```

### DTO

```ts
ApplicantDocument {
  name: string
  document_type: string
  review_status: "Pending" | "Approved" | "Rejected"
  uploaded_at: datetime
}
```

### Upload rules

* Upload creates `Applicant Document`
* File attached **only** to Applicant Document
* No direct file uploads anywhere else

---

## A.6 Policy Acknowledgement DTO

### Endpoints

```
GET  /api/admissions/policies/:applicant
POST /api/admissions/policies/acknowledge
```

### DTO

```ts
PolicyAcknowledgementPayload {
  policy_version: string
  accepted: true
}
```

### Rules

* Only latest version shown
* Cannot un-acknowledge
* Timestamp is server-owned

---

## A.7 Submission Intent (Not Promotion)

### Endpoint

```
POST /api/admissions/applicant/submit
```

### Purpose

Family declares **“ready for review”**.

### Rules

* Does **not** approve
* Does **not** promote
* Locks Applicant edits
* Emits communication event

---

## A.8 Explicitly Forbidden APIs

The portal must **never** call:

* `promote_applicant`
* any Student API
* any Guardian API
* any Desk endpoint
* any bulk list API

---

# B. Admissions Portal Route Map & Page Responsibilities

---

## B.1 Route Namespace (Locked)

```
/admissions/*
```

No reuse. No aliasing.

---

## B.2 Layout Shell

**AdmissionsLayout.vue**

Responsibilities:

* session bootstrap
* applicant guard
* route outlet
* logout

No business logic.

---

## B.3 Routes & Pages

### `/admissions/overview`

**Page:** `ApplicantOverview.vue`

**Purpose**

* Show progress
* Show next required actions
* Entry point after login

**Reads**

* `ApplicantSnapshot`

**Writes**

* ❌ none

---

### `/admissions/health`

**Page:** `ApplicantHealth.vue`

**Purpose**

* Collect declared health info

**Reads**

* ApplicantHealth

**Writes**

* ApplicantHealth (overlay submit)

---

### `/admissions/documents`

**Page:** `ApplicantDocuments.vue`

**Purpose**

* Upload & view documents

**Reads**

* ApplicantDocuments list

**Writes**

* Upload via overlay

---

### `/admissions/policies`

**Page:** `ApplicantPolicies.vue`

**Purpose**

* Display required policies
* Capture acknowledgements

**Writes**

* PolicyAcknowledgement only

---

### `/admissions/submit`

**Page:** `ApplicantSubmit.vue`

**Purpose**

* Final declaration
* Explain consequences

**Writes**

* submit intent only

---

### `/admissions/status`

**Page:** `ApplicantStatus.vue`

**Purpose**

* Read-only state
* Waiting / decision / outcome

No edits.

---

## B.4 Overlay Responsibilities (Strict)

Overlays used for:

* document upload
* health save
* policy accept
* submission confirm

Overlay rules:

* mutation only
* closes immediately
* emits invalidation
* no toasts inside overlay

---

## B.5 Guards (Hard)

Every route checks:

1. Logged in
2. Role == Admissions Applicant
3. Applicant bound
4. Applicant scope match

Failure → redirect to `/login`

---

## B.6 What Is Deliberately Missing

No:

* multi-applicant support
* sibling switch
* chat
* messaging
* staff notes
* review UI
* approval UI
* promotion UI

Those belong to **staff workspace**, not this portal.

---

## Final Lock Statement

> This portal is **not a shortcut** to Guardianship.
> It is a **contained pre-institution surface** with its own identity, rules, and lifecycle.

If Codex follows **A and B**, Phase-5 UX can be implemented **without touching contracts, schema, or governance**.




Perfect. Here is **C**, fully locked, **Codex-ready**, and aligned with your SPA + governance rules.

This is the **last missing foundation** before implementation.
Once this exists, **Codex must not invent anything**.

---

# Admissions Portal — Section C

## Role, Permission Matrix & Lifecycle (LOCKED)

> **Scope:** Admissions Portal only
> **Applies to:** Phase 5 UX, Phase 2–3 data
> **Authority:**
>
> 1. `spa_architecture_and_rules.md`
> 2. `admissions_governance_contract.md`
> 3. This section

---

## C.1 Canonical Role Definition

### Role Name (LOCKED)

```
Admissions Applicant
```

> This role represents a **temporary, pre-institution user**.
> It is **not** a Guardian, Student, or Staff proxy.

---

## C.2 Role Characteristics (Non-Negotiable)

| Attribute                    | Value                             |
| ---------------------------- | --------------------------------- |
| Desk access                  | ❌ No                              |
| Portal access                | ✅ Yes                             |
| Scope                        | Exactly **one Student Applicant** |
| Duration                     | Temporary                         |
| Can mutate canonical records | ❌ No                              |
| Can promote applicant        | ❌ No                              |
| Can see staff notes          | ❌ No                              |

---

## C.3 Authentication Model

### User Type

* Standard Frappe `User`
* Password-based login
* No token or magic-link authentication

### User Creation

* Created by **admissions staff** during “Invite to Apply”
* Assigned **only** one role: `Admissions Applicant`

### User Identity Rules

* User **must not** be linked to:

  * Guardian
  * Student
  * Employee
* Email may later match a Guardian, but **no implicit upgrade**

---

## C.4 Permission Model (DocType Matrix)

### Read / Write Permissions

| DocType                  | Read              | Write            | Create | Delete |
| ------------------------ | ----------------- | ---------------- | ------ | ------ |
| Student Applicant        | ✅ (scoped)        | ⚠️ (limited)     | ❌      | ❌      |
| Applicant Health Profile | ✅                 | ✅                | ❌      | ❌      |
| Applicant Document       | ✅                 | ⚠️ (upload only) | ✅      | ❌      |
| Applicant Interview      | ❌                 | ❌                | ❌      | ❌      |
| Institutional Policy     | ✅ (read-only)     | ❌                | ❌      | ❌      |
| Policy Acknowledgement   | ✅                 | ❌                | ✅      | ❌      |
| Admissions Communication | ✅ (shared only)   | ❌                | ❌      | ❌      |
| File                     | ❌ (indirect only) | ❌                | ❌      | ❌      |

⚠️ **Write limitations enforced server-side**, not via permissions alone.

---

## C.5 Server-Side Guards (MANDATORY)

Permissions alone are **insufficient**.

### Required Guards

#### Student Applicant

* Editable **only if**:

  * application_status ∈ {Draft, In Progress}
* Only specific fields writable (no status, no governance fields)

#### Applicant Document

* Portal can:

  * upload
  * view
* Portal cannot:

  * approve / reject
  * change document type
  * delete

#### Policy Acknowledgement

* Create-only
* One per policy version
* No revocation

#### Submission

* `submit_application()`:

  * locks Applicant
  * emits communication
  * never approves

---

## C.6 Record Scoping Rule (Critical)

Every API must enforce:

```
User → Admissions Applicant role
AND
User is linked to exactly one Student Applicant
AND
Requested record belongs to that Applicant
```

Failure → `403 Forbidden`

No list views.
No filters.
No overrides.

---

## C.7 Route Access Control

### Allowed Routes

```
/admissions/*
```

### Forbidden Routes

```
/portal/*
/student/*
/guardian/*
/app/*
```

Any attempt → redirect to login.

---

## C.8 Lifecycle Management (LOCKED)

### User Creation

Triggered by:

* Invite to Apply

### User Deactivation (MANDATORY)

| Event               | Action                  |
| ------------------- | ----------------------- |
| Applicant Rejected  | Disable user            |
| Applicant Withdrawn | Disable user            |
| Applicant Promoted  | Disable OR delete user  |
| GDPR Erasure        | Anonymize or purge user |

No role mutation.
No role reuse.
No silent persistence.

---

## C.9 Explicitly Forbidden Patterns

Codex **must not**:

* Convert Admissions Applicant → Guardian
* Share accounts across Applicants
* Reuse credentials
* Grant Website User role
* Grant Desk access
* Infer permissions from email match
* Allow multiple Applicants per user

---

## C.10 Codex Implementation Checklist

Codex must:

* [ ] Create `Admissions Applicant` role
* [ ] Assign minimal DocType permissions
* [ ] Enforce record scoping in every endpoint
* [ ] Block all non-admissions routes
* [ ] Disable user at Phase 3 completion
* [ ] Never mutate roles dynamically

---

## Final Lock Statement

> The Admissions Applicant role is a **temporary legal surface**,
> not an early Guardian, not a UX convenience, and not a shortcut.

If this role is weakened, **every later phase becomes unsafe**.



---

# Phase 5 — Admissions Portal

## Canonical DTO & Implementation Addendum (LOCKED)

> **Status:** Authoritative
> **Audience:** Coding agents (SPA + backend)
> **Precedence:**
>
> 1. `spa_architecture_and_rules.md`
> 2. `admissions_governance_contract.md`
> 3. This addendum
> 4. `phase050.md` and `phase050_admission_portal.md`

This addendum **fills all missing type and flow definitions** required to implement Phase 5 without inference.

---

## A. Canonical DTO Definitions (Frontend Contracts)

All DTOs below are **read-only representations** derived from server truth.
No frontend may infer or compute business logic.

---

### A.1 `NextAction` (LOCKED)

Used by the portal to guide families toward required steps.

```ts
export type NextAction = {
  label: string
  route_name: string      // Vue Router named route
  intent: 'primary' | 'secondary' | 'neutral'
  is_blocking: boolean    // If true, prevents submission
  icon?: string           // Optional UI icon identifier
}
```

**Rules**

* `route_name` must reference a valid admissions SPA route
* `is_blocking = true` means submission is disabled until resolved
* UI must not infer actions — only render what is provided

---

### A.2 `CompletionState` (LOCKED)

Used for high-level progress indicators only.

```ts
export type CompletionState =
  | 'pending'
  | 'in_progress'
  | 'complete'
  | 'optional'
```

**Rules**

* No counts or thresholds in this type
* Specific deficiencies are expressed via `NextAction[]`
* UI badges must map **directly** to these values

---

### A.3 `ApplicantStatus` (LOCKED ENUM)

This enum defines **all possible Applicant lifecycle states visible to the portal**.

```ts
export type ApplicantStatus =
  | 'Draft'
  | 'In Review'
  | 'Action Required'
  | 'Accepted'
  | 'Waitlisted'
  | 'Rejected'
  | 'Withdrawn'
```

**Rules**

* Strings must match backend values exactly
* No frontend remapping
* Status transitions remain server-controlled

---

### A.4 `ApplicantDocument` DTO (LOCKED)

```ts
export type ApplicantDocument = {
  name: string
  document_type: string
  review_status: 'Pending' | 'Approved' | 'Rejected'
  uploaded_at: string
  file_url: string        // Signed or private URL, server-generated
}
```

**Rules**

* `file_url` must be directly usable for preview/download
* Frontend never queries `File` directly
* All file access is mediated by this DTO

---

### A.5 `ApplicantPolicy` DTO (LOCKED)

Returned by `GET /api/admissions/policies/:applicant`

```ts
export type ApplicantPolicy = {
  name: string
  policy_version: string
  content_html: string
  is_acknowledged: boolean
  acknowledged_at?: string
}
```

**Rules**

* `content_html` is authoritative policy text
* UI must not fetch policy content elsewhere
* Acknowledgement is version-specific

---

## B. Session & Read-Only Semantics

### B.1 `AdmissionsSession` Addendum (LOCKED)

To explain **why** editing is disabled, the following field is mandatory:

```ts
export type AdmissionsSession = {
  applicant: string
  applicant_status: ApplicantStatus
  is_read_only: boolean
  read_only_reason: string | null
}
```

**Examples**

* `"Application submitted"`
* `"Application under review"`
* `"Admissions cycle closed"`
* `"Applicant rejected"`

**Rules**

* If `is_read_only = true`, `read_only_reason` must be non-null
* UI must display this explanation verbatim
* No inferred messaging

---

### B.2 Read-Only Enforcement Rules

Editing is blocked if **any** of the following is true:

* Applicant status ∈ {In Review, Accepted, Waitlisted, Rejected, Withdrawn}
* Submission timestamp exists
* Admissions staff explicitly locked the Applicant

Frontend must treat read-only as **absolute**.

---

## C. Backend Workflow Clarifications (Codex-Safe)

---

### C.1 Invite Applicant Workflow (MANDATORY)

User creation **must never be manual**.

A single server method is authoritative:

```python
invite_applicant(
  email: str,
  student_applicant: str
) -> None
```

**This method must atomically:**

1. Create a Frappe User
2. Assign role: `Admissions Applicant`
3. Link User ↔ Student Applicant
4. Send invite communication (Phase 4 dependency)
5. Enforce one-user-per-applicant invariant

**No Desk-based user creation is allowed.**

---

### C.2 File Access Model (Clarified)

* Applicant files are accessed **only** via:

  * `ApplicantDocument.file_url`
* No generic `/files` browsing
* No shared access across applicants
* File routing follows `files_01_architecture_notes.md`

---

### C.3 Transport Wrapper Compliance

All Phase 5 endpoints must comply with:

* `spa_architecture_and_rules.md` §2.5
* Standard Ifitwala transport envelope
* No raw Frappe responses in components

SPA must consume **domain DTOs only**.

---

## Final Lock Statement

> Phase 5 UX is now fully specified.
>
> * All DTOs are defined
> * All enums are fixed
> * All workflows are explicit
> * No frontend inference is permitted
>
> Any implementation deviation is a **contract violation**, not a creative choice.

