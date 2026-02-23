# Admissions UX, Portal Surface, Files & GDPR — Canonical Contract (LOCKED)

## 1. UX invariants and portal surface map (source)


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

## 0. Problem Being Solved

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
* File Classification primary subject is **Student Applicant**
* All files are deletable via Applicant purge
* No documents live directly on User
* Files are never moved or re-linked on promotion
* Approved promotable Applicant Documents are copied as new Student File records with source linkage preserved
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
    portal_status: PortalApplicantStatus
    school: string
    organization: string
    is_read_only: boolean
    read_only_reason: string | null
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
    portal_status: PortalApplicantStatus
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
  // mirrors Applicant Health Profile fields aligned to Student Patient intake:
  blood_group: string
  allergies: boolean
  food_allergies: string
  insect_bites: string
  medication_allergies: string
  asthma: string
  bladder__bowel_problems: string
  diabetes: string
  headache_migraine: string
  high_blood_pressure: string
  seizures: string
  bone_joints_scoliosis: string
  blood_disorder_info: string
  fainting_spells: string
  hearing_problems: string
  recurrent_ear_infections: string
  speech_problem: string
  birth_defect: string
  dental_problems: string
  g6pd: string
  heart_problems: string
  recurrent_nose_bleeding: string
  vision_problem: string
  diet_requirements: string
  medical_surgeries__hospitalizations: string
  other_medical_information: string
  applicant_health_declared_complete: boolean
  applicant_health_declared_by: string
  applicant_health_declared_on: string
  applicant_display_name: string
  vaccinations: Array<{
    vaccine_name: string
    date: string
    vaccination_proof: string
    additional_notes: string
    vaccination_proof_content?: string // request-only (base64 image)
    vaccination_proof_file_name?: string // request-only
    clear_vaccination_proof?: boolean // request-only
  }>
}
```

### Rules

* POST allowed only if Applicant mutable
* Health section is considered complete for applicant flow only when `applicant_health_declared_complete = true`
* Review status **not writable** by portal
* Staff notes invisible

---

## A.5 Applicant Documents DTO

### A.5.1 Applicant Document Types (Portal)

### Endpoint

```
GET /api/admissions/documents/types
```

### DTO

```ts
ApplicantDocumentType {
  name: string
  code: string
  document_type_name: string
  belongs_to: 'student' | 'guardian' | 'family'
  is_required: boolean
  description: string
}
```

**Rules**

* Types are scoped to Applicant organization/school
* Only `is_active = 1` types are returned
* Portal may upload **only** against these types
* `belongs_to` is semantic only (does not affect file ownership)

### A.5.2 Applicant Documents (Uploads)

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
* File Classification primary subject is always **Student Applicant**

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

  * application_status ∈ {Invited, In Progress, Missing Info}
* Only specific fields writable (no status, no governance fields)
* `student_joining_date` (Admission Date) is admissions-office-owned and portal read-only

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

### Two Explicit Lifecycle Boundaries

1. Promotion (Data Boundary)

- Applicant -> Student
- Creates/links `Student`
- Creates/syncs `Student Patient`
- Copies approved/promotable admissions documents
- Does not create Guardian records
- Does not provision portal identities or mutate access roles

2. Identity Upgrade (Access Boundary)

- Runs only after enrollment confirmation (active `Program Enrollment` for the promoted student)
- Creates/reuses `Guardian` records as needed
- Creates/links `User` records for guardians and student portal access
- Removes `Admissions Applicant` and assigns long-term portal roles (`Guardian`, `Student`)
- Links Guardian <-> Student in SIS records

Promotion and Identity Upgrade are independent actions and may happen at different times.

### User Creation

Triggered by:

* Invite to Apply
* Identity Upgrade (Guardian/Student access provisioning)

### User Deactivation (MANDATORY)

| Event               | Action                  |
| ------------------- | ----------------------- |
| Applicant Rejected  | Disable user            |
| Applicant Withdrawn | Disable user            |
| Applicant Promoted  | Disable OR delete user  |
| GDPR Erasure        | Anonymize or purge user |

Role mutation is allowed only inside Identity Upgrade.
Role reuse outside Identity Upgrade is forbidden.
No silent persistence.

---

## C.9 Explicitly Forbidden Patterns

Codex **must not**:

* Share accounts across Applicants
* Reuse credentials
* Grant Guardian/Student access during Promotion
* Grant Desk access
* Infer permissions from email match
* Allow multiple Applicants per user

---

## C.10 Codex Implementation Checklist

Codex must:

* [x] Create `Admissions Applicant` role
* [x] Assign minimal DocType permissions
* [x] Enforce record scoping in admissions-portal endpoints
* [x] Block all non-admissions routes
* [x] Disable user at Phase 3 completion
* [x] Keep promotion and identity upgrade as separate server actions
* [x] Gate identity upgrade on active Program Enrollment
* [x] Make identity upgrade idempotent for Users/Guardians/links

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

### A.3 `PortalApplicantStatus` (LOCKED ENUM)

This enum defines **all possible Applicant lifecycle states visible to the portal**.

```ts
export type PortalApplicantStatus =
  | 'Draft'
  | 'In Progress'
  | 'Action Required'
  | 'In Review'
  | 'Accepted'
  | 'Rejected'
  | 'Withdrawn'
  | 'Completed'
```

**Rules**

* This enum is **derived server-side** (read-only projection)
* The portal **must never** expose raw `application_status`
* No frontend remapping
* Status transitions remain server-controlled

### A.3.1 Status Mapping (Server-Owned, LOCKED)

| application_status | PortalApplicantStatus |
| ------------------ | --------------------- |
| Draft              | Draft                 |
| Invited            | Draft                 |
| In Progress        | In Progress           |
| Missing Info       | Action Required       |
| Submitted          | In Review             |
| Under Review       | In Review             |
| Approved           | Accepted              |
| Rejected           | Rejected              |
| Promoted           | Completed             |

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
  user: {
    name: string
    full_name: string
    roles: ["Admissions Applicant"]
  }
  applicant: {
    name: string
    portal_status: PortalApplicantStatus
    is_read_only: boolean
    read_only_reason: string | null
  }
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

* Portal status ∈ {In Review, Accepted, Rejected, Withdrawn, Completed}
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


---

## 2. UX invariants (additional) (source)


Part A

# Phase 5 — UX Invariants (Non-Negotiable)

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
| Personal Details | Student Applicant | Write (until submission, except Admission Date) |
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


---

## 3. Files architecture (system-wide) — admissions alignment (source)


# Files & Documents Architecture — Ifitwala_Ed

> **Status:** LOCKED (v1)
>
> This document defines the **authoritative architecture** for file and document management in Ifitwala_Ed.
> All current and future implementations **must conform**.
>
> This note is written to be:
>
> * GDPR-compliant by design
> * Multi‑school & multi‑organization safe
> * Superior to typical EdTech SaaS platforms
> * Compatible with Frappe today, not trapped by it

---

## 0. Scope and intent

This architecture governs **all files uploaded anywhere** in Ifitwala_Ed:

* Student uploads (tasks, assignments, evidence)
* Staff uploads (contracts, reports, observations)
* Admissions documents
* Safeguarding materials
* Meeting attachments
* System‑generated files

It applies equally to:

* Desk
* SPA (students, guardians, staff)
* Web Forms
* Background jobs
* Imports

There are **no exceptions**.

---

## 1. Core principles (non‑negotiable)

### 1.1 File ≠ Business Document

* A **File** is storage + metadata
* A **Business Document** gives meaning (Student, Task, Inquiry, Employee, Referral…)

Files **never exist on their own**.
Every file is owned by **exactly one business document**.

---

### 1.2 No orphan files

A valid file **must always**:

* Be attached to a doctype + docname
* Live in a deterministic folder
* Be relocatable without duplication
* Be deletable without side effects

If a file cannot be deterministically resolved, it is considered a **bug**.

---

### 1.3 Deterministic over convenience

User experience must **never** override:

* Traceability
* Deletability
* Compliance

Files are stored where the **system decides**, not where the user chooses.

---

## 2. Canonical classification model

Every file **must be classifiable** by the following dimensions:

| Dimension           | Required | Purpose                 |
| ------------------- | -------- | ----------------------- |
| Organization        | Yes      | Multi‑org separation    |
| School (tree‑aware) | Yes      | Visibility & governance |
| Business domain     | Yes      | Functional grouping     |
| Owning document     | Yes      | Lifecycle control       |

If any of these is missing, the upload is invalid.

---

## 3. Canonical logical storage model

> This is a **logical model**. Physical storage may change later (FS → S3 → GCS).

```
Home/
  Organizations/
    {ORG_ID}/
      Schools/
        {SCHOOL_ID}/
          {DOMAIN}/
            {ENTITY_ID}/
              {SLOT}/
                file_v{n}.{ext}
```

### Examples

**Student task submission**

```
.../Students/STU-2025-00012/Tasks/TASK-00087/submission/
```

**Employee contract**

```
.../Employees/EMP-00045/contracts/
```

**Admissions documents**

```
.../Admissions/INQ-2026-00123/identity/
```

---

## 4. Slots (critical concept)

Files are not identified by filenames.
They are identified by **slots**.

### 4.1 What is a slot

A slot represents the **semantic purpose** of a file:

* `profile_photo`
* `passport`
* `contract`
* `submission`
* `feedback`
* `evidence`
* `attachment`

Slots are **defined by the owning domain**, not by users.

---

### 4.2 Slot behavior

Each slot:

* May allow 1 file (replace)
* May allow N versions
* Has a retention policy
* Has a data classification

Slots make deletion, versioning, and compliance **tractable**.

---

## 5. File metadata (GDPR‑critical)

Every File **must carry** the following metadata:

### 5.1 Data subject

```
data_subject_type: student | guardian | staff
data_subject_id: <ID>
```

This is mandatory for GDPR resolution.

---

### 5.2 Data classification

```
data_class:
  - academic
  - assessment
  - safeguarding
  - administrative
  - legal
  - operational
```

Classification is explicit. There is no inference.

---

### 5.3 Retention policy

```
retention_policy:
  - until_program_end + 1y
  - until_school_exit + 6m
  - fixed_7y
  - immediate_on_request
```

Retention is **machine‑readable**, not policy text.

---

## 6. Versioning model

* Versioning is **per slot**
* Old versions are soft‑hidden
* Version caps are enforced per slot
* No branching
* No diffs

If versioning is disabled, replacement is destructive.

---

## 7. Dispatcher rule (single gateway)

> **All file writes go through the dispatcher.**

There are no direct `File.insert()` calls in business logic.

### 7.1 Dispatcher responsibilities

* Resolve organization
* Resolve school + descendants
* Resolve domain root
* Enforce slot rules
* Apply versioning
* Attach to owning document
* Return canonical File record

The dispatcher is the **only authority** on storage decisions.

---

## 8. Permissions & visibility

| Layer              | Responsibility                    |
| ------------------ | --------------------------------- |
| Frappe permissions | Who can see the owning document   |
| File logic         | Who can upload / replace / delete |
| UI                 | What actions are shown            |

**Key rule**

> If you cannot see the owning document, you cannot see the file.

No parallel ACL system exists for files.

---

## 9. Tasks & student uploads

### 9.1 Separation of concerns

* **Grades / analytics** are permanent
* **File content** is disposable

Deleting a student’s files **must not** break:

* Assessment records
* Aggregated analytics
* Reports

---

### 9.2 Task submission storage

Each submission:

* Is stored under the student
* References Task + Student Group
* Uses a dedicated `submission` slot

This allows:

* Per‑task deletion
* Full student erasure
* Retention‑based cleanup

---

## 10. GDPR erasure model

Deletion is a **workflow**, not a function call.

### 10.1 Erasure workflow stages

1. Scope identification
2. File resolution
3. Legal hold check
4. Physical deletion
5. Version invalidation
6. Minimal audit trail

No content survives deletion.

---

### 10.2 Audit trail (minimal)

Allowed to keep:

* Subject ID
* Date
* Categories deleted
* Request origin

Forbidden to keep:

* File names
* Content
* Recoverable versions

---

## 11. Backups & crypto‑erasure (forward design)

### 11.1 Known limitation

Historical backups cannot be reliably purged.

### 11.2 Designed solution

* Encrypt files per school or data subject
* On erasure: destroy the key
* Backups become cryptographically useless

The architecture must **allow this later** even if not implemented now.

---

## 12. What is explicitly out of scope

* User‑managed folder browsing
* Drive‑like UX
* Cross‑school file sharing
* Shared files without ownership
* Client‑side storage decisions

---

## 13. Compliance stance

Ifitwala_Ed is designed so that it can truthfully state:

> *We know exactly what data we hold, why we hold it, how long we keep it, and we can erase it without breaking academic integrity.*

This is a **competitive advantage**, not just compliance.

---

## 14. Implementation guardrails

Any code that:

* Bypasses the dispatcher
* Stores files without metadata
* Creates orphan files
* Violates retention rules

Is considered **architecturally invalid** and must be refactored.

---

## 15. Next execution track (locked)

We proceed in this exact order:

1. Add `File Classification` Doctype (single, system-wide)
2. Enforce dispatcher-only uploads (all surfaces)
3. Separate grades / analytics from file content
4. Implement GDPR erasure workflow
5. Prepare crypto-erase capability (design-ready)

No feature work proceeds that violates this sequence.

---

## 16. Decision lock

**Architecture decision:**

* File governance uses **one system-wide `File Classification` Doctype**
* No domain-specific subclasses in v1
* Schema must remain extensible without breaking contracts

This decision is **locked for v1**.

---

**End of authoritative note.**













## Why this choice is correct (brief, practical)

This supports **real school reality** without breaking GDPR logic:

* Group assignments (3–5 students, one submission)
* Siblings (documents referencing more than one child)
* Safeguarding notes involving multiple students
* Parent–student joint documents

At the same time:

* **One primary subject** keeps erasure deterministic
* Secondary subjects are **referential**, not ownership chaos
* No ambiguity about *who “owns” deletion authority*

This aligns with how serious SaaS systems model *data controllers vs data subjects*.

---

# STEP 1 — `File Classification` Doctype (AUTHORITATIVE)

Below is the **locked v1 schema**.
This is the backbone. Everything else builds on this.

---

## 1. Doctype: `File Classification`

**Type:** Standard (not Single)
**Cardinality:** 1:1 with `File` (mandatory)

---

## 2. Core identity fields

### 🔑 File linkage (mandatory)

| Field              | Type        | Notes                |
| ------------------ | ----------- | -------------------- |
| `file`             | Link → File | **Required**, unique |
| `attached_doctype` | Data        | Cached from File     |
| `attached_name`    | Data        | Cached from File     |

> We denormalize `attached_*` for fast queries and GDPR sweeps.

### 🛡️ Integrity & Lineage (New)

| Field          | Type        | Notes                                |
| -------------- | ----------- | ------------------------------------ |
| `content_hash` | Data        | SHA-256 (tamper proofing)            |
| `source_file`  | Link → File | Parent file (for thumbnails/derivs)  |

> `content_hash` must be calculated by dispatcher on upload.

## 3. Data subject model (GDPR-critical)

### 3.1 Primary subject (mandatory)

| Field                  | Type                                    |
| ---------------------- | --------------------------------------- |
| `primary_subject_type` | Select (`Student`, `Guardian`, `Employee`, `Student Applicant`) |
| `primary_subject_id`   | Dynamic Link                                                     |

**Rules**

* Exactly **one** primary subject
* Primary subject determines:

  * Erasure authority
  * Retention countdown
  * Crypto-erase scope (future)

---

### 3.2 Secondary subjects (optional)

Child table: **`File Classification Subject`**

| Field          | Type                                            |
| -------------- | ----------------------------------------------- |
| `subject_type` | Select (Same as primary)                        |
| `subject_id`   | Dynamic Link                                    |
| `role`         | Select (`co-owner`, `referenced`, `contextual`) |

**Rules**

* Secondary subjects:

  * Do **not** control deletion
  * Are included in *impact analysis*
* Used for:

  * Group work
  * Multi-student references
  * Safeguarding context

---

## 4. Data classification & purpose

| Field        | Type   | Required |
| ------------ | ------ | -------- |
| `data_class` | Select | ✅        |
| `purpose`    | Select | ✅        |

### `data_class` (locked values)

```
academic
assessment
safeguarding
administrative
legal
operational
```

### `purpose` (machine-readable)

```
identification_document
contract
assessment_submission
assessment_feedback
safeguarding_evidence
medical_record
visa_document
policy_acknowledgement
background_check
academic_report
administrative
other
```

> **GDPR rule:**
> If `purpose` expires → deletion must be possible.

---

## 5. Retention & deletion control

| Field              | Type   | Required     |
| ------------------ | ------ | ------------ |
| `retention_policy` | Select | ✅            |
| `retention_until`  | Date   | ⛔ (computed) |
| `legal_hold`       | Check  | ⛔            |
| `erasure_state`    | Select | ⛔            |

### `retention_policy` (v1)

```
until_program_end_plus_1y
until_school_exit_plus_6m
fixed_7y
immediate_on_request
```

### `erasure_state`

```
active
pending
blocked_legal
erased
```

---

## 6. Slot & versioning awareness

| Field                | Type  | Required |
| -------------------- | ----- | -------- |
| `slot`               | Data  | ✅        |
| `version_number`     | Int   | ⛔        |
| `is_current_version` | Check | ⛔        |

> Versioning remains **slot-based**, enforced by dispatcher.

---

## 7. Organization & school anchoring

| Field          | Type                | Required |
| -------------- | ------------------- | -------- |
| `organization` | Link → Organization | ✅        |
| `school`       | Link → School       | ✅        |

**Rules**

* `school` must be in the allowed subtree
* Cached here for:

  * Fast GDPR queries
  * School-scoped erasure
  * Backup key scoping (future)

---

## 8. Origin Context (Security)

| Field           | Type   | Notes                            |
| --------------- | ------ | -------------------------------- |
| `upload_source` | Select | `Desk`, `SPA`, `API`, `Job`      |
| `ip_address`    | Data   | Captured at upload time          |

> Critical for forensics (who uploaded what from where).

---

## 9. Invariants (non-negotiable)

1. A `File` **cannot exist** without a `File Classification`
2. Dispatcher **must create both atomically**
3. Direct `File.insert()` without classification = **bug**
4. Deletion checks:

   * `legal_hold = 1` → hard block
   * `erasure_state != active` → no writes
5. Secondary subjects never override primary subject rights

---

## 10. Dispatcher enforcement (preview)

When a file is uploaded, dispatcher must receive:

```python
{
  file,
  slot,
  primary_subject_type,
  primary_subject_id,
  secondary_subjects=[],
  data_class,
  purpose,
  retention_policy,
  organization,
  retention_policy,
  organization,
  school,
  upload_source  // Inferred by dispatcher
}
```

Missing any **mandatory** field → reject upload.

---

## 11. Why this is superior (explicitly)

With this model, you can:

* Delete **all data for one student** deterministically
* Delete **only task files**, keep grades
* Answer regulators in minutes, not weeks
* Add crypto-erase later without refactor
* Handle edge cases without schema hacks

Most ed platforms **cannot** do this cleanly.

---



## Admissions File Ownership (Authoritative Rule)

All files uploaded during the admissions process are **owned by the Student Applicant**.

This includes:
- child-related documents (passport, transcripts, reports, health records)
- parent / guardian documents (IDs, consent forms, declarations)

### Canonical Rule

During admissions (all phases prior to promotion):

owner_doctype = "Student Applicant"
owner_name = <student_applicant.name>


There are **no exceptions**.

### Explicit Prohibitions

Admissions files MUST NOT:
- be owned by Student
- be owned by Guardian
- be re-linked or moved on promotion
- be duplicated implicitly; only approved promotable documents are copied as new Student-owned records

### Rationale

- Student and Guardian records do not exist during admissions
- The Student Applicant is the sole legal intake container
- Admissions files are decision evidence, not operational student records
- This guarantees clean GDPR erasure and auditability

### Promotion Boundary

Promotion from Applicant → Student:
- does **not** move or re-link Applicant files
- copies only approved promotable Applicant Documents into new Student File records
- freezes Applicant files as historical admissions artefacts
- operational records must never depend on admissions file ownership


---

## 4. GDPR erasure workflows — Applicant vs Student (source)


# GDPR Erasure Workflows — Applicant vs Student

**Ifitwala_Ed — Canonical Data Erasure Contract (v1)**

> GDPR erasure is **not deletion**.
> It is **lawful destruction + lawful retention**, explicitly separated.

This contract defines **what may be erased, when, by whom, and how** — without corrupting institutional records.

---

## 1. First Principle (Non-Negotiable)

> **Applicants and Students are legally different data subjects.**

They have:

* different legal bases
* different retention obligations
* different erasure rights

**Mix them = audit failure.**

---

## 2. Data Classification (Authoritative)

All personal data must fall into **one and only one** class.

### 2.1 Applicant-Scoped Personal Data

**Owned by admissions. Erasable by default.**

Includes:

* Student Applicant core fields
* Applicant Interviews
* Applicant Health Profile
* Applicant Documents (and files)
* Applicant Policy Acknowledgements
* Inquiry (if linked only to Applicant)

**Legal basis:**
Consent + pre-contractual measures

---

### 2.2 Student-Scoped Personal Data

**Owned by the institution. Erasable only with constraints.**

Includes:

* Student record
* Academic history
* Attendance
* Assessment results
* Disciplinary logs
* Financial/accounting links

**Legal basis:**
Legal obligation + public interest + contract

---

### 2.3 Institutional Records (Never erased)

Includes:

* Aggregated analytics
* Anonymized statistics
* Financial ledgers (with pseudonymization)
* Audit logs (who did what)

---

## 3. Two Separate Erasure Workflows (DO NOT MERGE)

---

# WORKFLOW A — Applicant GDPR Erasure

### Who can request

* Guardian
* Applicant (where applicable)

### Who can execute

* System Manager
* Data Protection Officer role (recommended)

---

## A1. Preconditions

Applicant must be in one of:

* Draft
* Invited
* In Progress
* Submitted
* Under Review
* Missing Info
* Rejected

❌ **Not allowed if:** `application_status = Promoted`

---

## A2. What gets erased (hard delete)

### Structured data

* Student Applicant row
* Applicant Interviews
* Applicant Health Profile
* Applicant Policy Acknowledgements
* Applicant Documents

### Files

```
Home/Admissions/Applicant/<APPLICANT_ID>/
```

→ **entire folder recursively deleted**

This is why your folder isolation matters.

---

## A3. What is retained (minimal, lawful)

* Erasure log:

  * applicant_id
  * timestamp
  * executor
  * legal_basis = "GDPR Art. 17"
* Optional:

  * hashed applicant identifier (for repeat detection)

No names. No files. No content.

---

## A4. Technical implementation (Frappe-idiomatic)

### Entry point (only)

```python
erase_applicant_data(applicant_name, reason)
```

### Guards

* Hard fail if promoted
* Hard fail if not System Manager / DPO
* Transactional execution
* File deletion **after** DB success

### No UI delete button. Ever.

---

## A5. Audit posture

✔ Fully compliant
✔ Zero leakage
✔ Zero institutional risk

---

# WORKFLOW B — Student GDPR Erasure (Restricted)

> This is **exceptional**, not routine.

---

## B1. Legal reality (don’t pretend otherwise)

Students **do not have full erasure rights** once:

* enrolled
* assessed
* certified

Most schools **must refuse full deletion**.

Your system must support **partial erasure + pseudonymization**, not fantasy deletion.

---

## B2. What can be erased (soft)

* Profile photo
* Health notes (after retention period)
* Optional biographical fields
* Linked user accounts (portal access)

---

## B3. What must be retained

* Student ID
* Academic records
* Grades
* Attendance
* Certificates
* Financial traces

But…

---

## B4. Required action: Pseudonymization

Instead of deleting Student:

| Field        | Action                            |
| ------------ | --------------------------------- |
| Name         | Replace with anonymous token      |
| DOB          | Null or generalized               |
| Contact info | Deleted                           |
| User account | Disabled                          |
| Images       | Deleted                           |
| Documents    | Retained only if legally required |

Student becomes:

```
STU-2024-00421 → "Erased Student #00421"
```

---

## B5. Technical implementation

### Entry point

```python
pseudonymize_student(student_name, reason)
```

### Guards

* Requires DPO + System Manager
* Requires legal basis selection
* Writes irreversible marker: `gdpr_erased = 1`

### Hard rule

❌ Student is **never deleted** if academic records exist

---

## 4. Promotion Boundary (Critical)

> **Applicant → Student promotion permanently changes GDPR rights.**

This must be stated clearly in policy and enforced in code.

### Consequence

* Applicant erasure is **easy**
* Student erasure is **constrained**

This protects the institution.

---

## 5. Files Architecture Compliance (Why your design was right)

Your current design enables GDPR **cleanly**:

| Design choice             | GDPR impact            |
| ------------------------- | ---------------------- |
| Applicant-scoped folders  | One-shot deletion      |
| No shared admission files | No collateral damage   |
| Versioned documents       | Legal traceability     |
| No early Student writes   | Clear erasure boundary |

This is **better than most commercial SIS**.

---

## 6. Controller Guard Summary (Must-Have)

### Applicant

* `before_delete`: always blocked
* Only erase via `erase_applicant_data()`

### Student

* `before_delete`: always blocked
* Only via `pseudonymize_student()`

### File

* Never auto-delete outside orchestrated erasure

---

## 7. UX Rules (Non-Negotiable)

* ❌ No “Delete” buttons
* ❌ No bulk delete
* ❌ No client-side erasure
* ✅ Dedicated DPO flow only

---

## 8. Common GDPR Failure Modes (Avoid These)

❌ Deleting Student rows
❌ Deleting files without audit
❌ Allowing erasure after promotion
❌ Mixing Applicant + Student data
❌ Relying on “we’ll do it manually”

You’re avoiding all of them.

---

## 9. Final Verdict

Your system can support **real GDPR compliance**, not checkbox compliance, **because**:

* Applicant is disposable
* Student is institutional
* Files are isolated
* Promotion is a hard boundary

This is **exactly** how it should be.

---












---

# 1️⃣ `gdpr_erase.md` — Canonical GDPR Erasure Contract (LOCKED)

> **Authority level:** Same as `applicant.md`, `phase015.md`, `phase020.md`
> If implementation contradicts this document, **implementation is wrong**.

---

## GDPR Erasure — Applicant vs Student

**Ifitwala_Ed — Canonical Data Erasure Contract (v1)**

### Purpose

Define **exact, enforceable rules** for GDPR erasure that:

* protect the institution legally
* respect data subject rights
* do not corrupt academic or financial records
* are technically safe to execute

---

## 1. Fundamental Separation (Non-Negotiable)

> **Applicants and Students are legally distinct data subjects.**

| Entity            | Legal nature         | Erasure posture            |
| ----------------- | -------------------- | -------------------------- |
| Student Applicant | Pre-contractual      | Fully erasable             |
| Student           | Institutional record | Restricted / pseudonymized |

This boundary is **created at promotion** and **cannot be crossed retroactively**.

---

## 2. Data Classification (Authoritative)

All personal data must belong to **exactly one class**.

### 2.1 Applicant-Scoped Data (Erasable)

Includes:

* Student Applicant
* Applicant Interview
* Applicant Health Profile
* Applicant Document (+ files)
* Applicant Policy Acknowledgement
* Inquiry (if not independently retained)

**Legal basis:** GDPR Art. 6(1)(a), 6(1)(b)

---

### 2.2 Student-Scoped Data (Restricted)

Includes:

* Student core record
* Academic history
* Attendance
* Assessments
* Financial traces
* Certificates

**Legal basis:** GDPR Art. 6(1)(c), 6(1)(e)

---

### 2.3 Institutional Records (Never erased)

* Audit logs
* Aggregated analytics
* Accounting ledgers (may be pseudonymized)

---

## 3. Workflow A — Applicant GDPR Erasure

### Eligibility

Applicant **must not** be promoted.

Allowed statuses:

```
Draft, Invited, In Progress, Submitted,
Under Review, Missing Info, Rejected
```

---

### What is erased (hard delete)

* Student Applicant row
* All Applicant sub-doctypes
* All files under:

```
Home/Admissions/Applicant/<APPLICANT_ID>/
```

---

### What is retained

* GDPR Erasure Log:

  * applicant_id (internal)
  * erased_at
  * executed_by
  * legal_basis = "GDPR Art. 17"

No names. No files. No recovery.

---

### Execution rule

❌ Direct delete forbidden
✅ Only via:

```python
erase_applicant_data(applicant_name, reason)
```

---

## 4. Workflow B — Student GDPR Erasure (Pseudonymization)

### Reality check (locked)

> Students with academic records **cannot be deleted**.

Deletion is **illegal** in most jurisdictions.

---

### What is erased

* Profile photo
* Health notes (after retention)
* Contact information
* Linked User account (disabled)

---

### What is retained (pseudonymized)

| Field            | Action                        |
| ---------------- | ----------------------------- |
| Name             | Replace with anonymized token |
| DOB              | Null / generalized            |
| Student Name     | “Erased Student #<id>”        |
| Identifiers      | Preserved                     |
| Academic records | Preserved                     |

---

### Execution rule

❌ Student delete forbidden
✅ Only via:

```python
pseudonymize_student(student_name, reason)
```

Sets:

```
gdpr_erased = 1
```

Irreversible.

---

## 5. Promotion Boundary (Critical)

> Promotion permanently changes GDPR rights.

This must be:

* stated in policy
* enforced in code
* visible to staff

---

## 6. Controller Guards (Summary)

| Doctype           | Action | Rule                          |
| ----------------- | ------ | ----------------------------- |
| Student Applicant | delete | Always blocked                |
| Student           | delete | Always blocked                |
| File              | delete | Only via orchestrated erasure |

---

## 7. UX Rules

* ❌ No delete buttons
* ❌ No bulk delete
* ❌ No client-side erase
* ✅ DPO-only flow

---

## 8. Status

**LOCKED.**

---

# 2️⃣ DPO Role & Permissions (IMPLEMENTATION-READY)

## New Role

### `Data Protection Officer`

**Purpose:** Execute GDPR actions safely.

---

## Permissions Matrix

| Capability              | Admissions Officer | Academic Admin | System Manager | DPO |
| ----------------------- | ------------------ | -------------- | -------------- | --- |
| Erase Applicant         | ❌                  | ❌              | ✅              | ✅   |
| Pseudonymize Student    | ❌                  | ❌              | ✅              | ✅   |
| View erasure logs       | ❌                  | ❌              | ✅              | ✅   |
| Delete records directly | ❌                  | ❌              | ❌              | ❌   |

---

## Enforcement (Server-Side)

All GDPR methods must enforce:

```python
frappe.has_role("Data Protection Officer")
```

OR System Manager.

Client checks are **irrelevant**.

---

## Audit Requirements

Every erasure action must:

* require a reason
* write to Erasure Log
* be irreversible
* be timestamped

No background jobs. No retries.

---

# 3️⃣ Retention Period Configuration (ORG / SCHOOL)

## New Single Doctype

### `Data Retention Policy` (Single)

**Scope:** Organization (with optional School override)

---

## Fields (LOCKED)

| Field                             | Type  | Notes                     |
| --------------------------------- | ----- | ------------------------- |
| applicant_retention_days          | Int   | Default: 365              |
| rejected_applicant_retention_days | Int   | Default: 730              |
| health_data_retention_days        | Int   | Default: 365              |
| student_health_retention_days     | Int   | Default: legally required |
| auto_erase_applicants             | Check | Default: ❌                |
| require_manual_approval           | Check | Default: ✅                |

---

## Behavior Rules

* No auto-erase by default
* Scheduler may **flag**, never erase
* DPO executes manually

---

## Scheduler (Allowed)

Daily job may:

* list expired applicants
* notify DPO
* do **nothing else**

This avoids catastrophic mistakes.

---

## Why this matches best practice

This is how **PowerSchool, Workday, and SAP Education** actually operate:

* Applicants = disposable
* Students = protected
* Erasure = manual + audited
* Files = isolated

---

## Final Status

| Item                   | Status       |
| ---------------------- | ------------ |
| `gdpr_erase.md`        | ✅ Done       |
| DPO role & permissions | ✅ Done       |
| Retention config       | ✅ Done       |
| Architecture alignment | ✅ Clean      |
| Phase 03 compatibility | ✅ Guaranteed |

---








# GDPR — NEXT STEPS (EXECUTION TRACK, NO DRIFT)

This is **purely operational follow-through** on what is already locked.

---

## ✅ STEP 4 — GDPR Erasure Log (MANDATORY)

You cannot execute GDPR erasure without a **first-class audit object**.

### New Doctype: `GDPR Erasure Log`

**Purpose**
Immutable legal evidence that erasure occurred.

### Fields (LOCKED)

| Field             | Type        | Notes                           |
| ----------------- | ----------- | ------------------------------- |
| `subject_type`    | Select      | `Applicant`, `Student`          |
| `subject_doctype` | Data        | `Student Applicant` / `Student` |
| `subject_name`    | Data        | Internal ID only                |
| `action`          | Select      | `Erase`, `Pseudonymize`         |
| `legal_basis`     | Data        | e.g. `GDPR Art. 17`             |
| `reason`          | Small Text  | Required                        |
| `executed_by`     | Link → User | DPO / System Manager            |
| `executed_on`     | Datetime    | System                          |
| `irreversible`    | Check       | Always true                     |

**Hard rules**

* ❌ No delete
* ❌ No edit
* ❌ No child tables
* ❌ No file attachments

This log is **never erased**.

---

## ✅ STEP 5 — Controller Guards (ENFORCEMENT)

Contracts are useless without hard guards.

### A. Student Applicant

**In `student_applicant.py`:**

* `before_delete` → always `frappe.throw`
* No direct deletes allowed
* Only erasure path:

  ```python
  erase_applicant_data(applicant_name, reason)
  ```

---

### B. Student

**In `student.py`:**

* `before_delete` → always `frappe.throw`
* No deletion ever
* Only erasure path:

  ```python
  pseudonymize_student(student_name, reason)
  ```

---

### C. File

**Global rule**

* Never cascade delete Files from ORM
* Files deleted **only** by:

  * Applicant erasure orchestration
  * Explicit Student photo erase

This preserves audit safety.

---

## ✅ STEP 6 — Erasure Orchestrators (CORE LOGIC)

These are **the only executable GDPR actions**.

### 1️⃣ `erase_applicant_data(applicant_name, reason)`

**Order matters** (transactional):

1. Validate:

   * not promoted
   * executor is DPO / System Manager
2. Create `GDPR Erasure Log`
3. Delete in strict order:

   * Applicant sub-doctypes
   * Applicant Documents
   * Files under Applicant folder
   * Student Applicant row
4. Commit
5. No background jobs

Failure at any point → rollback.

---

### 2️⃣ `pseudonymize_student(student_name, reason)`

1. Validate:

   * academic records exist
   * executor authority
2. Create `GDPR Erasure Log`
3. Replace personal fields
4. Remove photos
5. Disable linked User
6. Set `gdpr_erased = 1`
7. Commit

**Never deletes Student row.**

---

## ✅ STEP 7 — Retention Enforcement (PASSIVE ONLY)

Retention **never auto-erases**.

### Scheduler job (daily)

* Identify:

  * expired applicants
  * expired rejected applicants
* Notify DPO
* Show counts only

❌ No delete
❌ No auto-execute

This keeps you legally safe.

---

## 🚦 Where we are now

| GDPR Item                  | Status   |
| -------------------------- | -------- |
| Canonical erasure contract | ✅ Locked |
| DPO role & authority       | ✅ Locked |
| Retention policy schema    | ✅ Locked |
| Erasure Log design         | 🟡 Next  |
| Controller guards          | 🟡 Next  |
| Orchestrator methods       | 🟡 Next  |

---










# GDPR Erasure Log — Doctype (Authoritative)

## 1️⃣ Doctype JSON

**File:**
`ifitwala_ed/governance/doctype/gdpr_erasure_log/gdpr_erasure_log.json`

```json
{
 "doctype": "DocType",
 "name": "GDPR Erasure Log",
 "module": "Governance",
 "custom": 0,
 "is_submittable": 0,
 "allow_rename": 0,
 "allow_import": 0,
 "track_changes": 0,
 "read_only": 1,
 "engine": "InnoDB",
 "field_order": [
  "subject_section",
  "subject_type",
  "subject_doctype",
  "subject_name",
  "action_section",
  "action",
  "legal_basis",
  "reason",
  "execution_section",
  "executed_by",
  "executed_on",
  "irreversible"
 ],
 "fields": [
  {
   "fieldname": "subject_section",
   "fieldtype": "Section Break",
   "label": "Data Subject"
  },
  {
   "fieldname": "subject_type",
   "fieldtype": "Select",
   "label": "Subject Type",
   "options": "Applicant\nStudent",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "subject_doctype",
   "fieldtype": "Data",
   "label": "Subject Doctype",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "subject_name",
   "fieldtype": "Data",
   "label": "Subject Identifier",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "action_section",
   "fieldtype": "Section Break",
   "label": "Erasure Action"
  },
  {
   "fieldname": "action",
   "fieldtype": "Select",
   "label": "Action",
   "options": "Erase\nPseudonymize",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "legal_basis",
   "fieldtype": "Data",
   "label": "Legal Basis",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "reason",
   "fieldtype": "Small Text",
   "label": "Reason",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "execution_section",
   "fieldtype": "Section Break",
   "label": "Execution"
  },
  {
   "fieldname": "executed_by",
   "fieldtype": "Link",
   "label": "Executed By",
   "options": "User",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "executed_on",
   "fieldtype": "Datetime",
   "label": "Executed On",
   "reqd": 1,
   "read_only": 1
  },
  {
   "fieldname": "irreversible",
   "fieldtype": "Check",
   "label": "Irreversible Action",
   "default": "1",
   "read_only": 1
  }
 ],
 "permissions": [
  {
   "role": "System Manager",
   "read": 1,
   "create": 0,
   "write": 0,
   "delete": 0
  },
  {
   "role": "Data Protection Officer",
   "read": 1,
   "create": 0,
   "write": 0,
   "delete": 0
  }
 ],
 "indexes": [
  {
   "fields": ["subject_type", "subject_name"]
  }
 ]
}
```

---

## 2️⃣ Python Controller

**File:**
`ifitwala_ed/governance/doctype/gdpr_erasure_log/gdpr_erasure_log.py`

```python
# Copyright (c) 2026
# License: see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class GDPRErasureLog(Document):
	"""
	Immutable legal audit record for GDPR erasure and pseudonymization.

	This document must:
	- never be edited
	- never be deleted
	- only be created programmatically
	"""

	def before_insert(self):
		# Enforce server-only creation
		if not frappe.flags.in_gdpr_erasure:
			frappe.throw(
				_("GDPR Erasure Logs can only be created by the system."),
				title=_("Operation Not Permitted")
			)

		self.executed_by = frappe.session.user
		self.executed_on = frappe.utils.now_datetime()
		self.irreversible = 1

	def before_update(self):
		frappe.throw(
			_("GDPR Erasure Logs are immutable."),
			title=_("Operation Not Permitted")
		)

	def before_delete(self):
		frappe.throw(
			_("GDPR Erasure Logs cannot be deleted."),
			title=_("Operation Not Permitted")
		)
```

---

## 3️⃣ Mandatory Creation Pattern (LOCKED)

Every erasure orchestrator **must** create the log like this:

```python
frappe.flags.in_gdpr_erasure = True

frappe.get_doc({
	"doctype": "GDPR Erasure Log",
	"subject_type": "Applicant",
	"subject_doctype": "Student Applicant",
	"subject_name": applicant.name,
	"action": "Erase",
	"legal_basis": "GDPR Art. 17",
	"reason": reason
}).insert(ignore_permissions=True)

frappe.flags.in_gdpr_erasure = False
```

❌ No manual creation
❌ No UI creation
❌ No backfilling
❌ No edits

---

## 4️⃣ Why this is correct (short, blunt)

* Immutable → **audit-safe**
* Server-only → **abuse-proof**
* Separate from subject → **GDPR-compliant**
* No attachments → **no secondary leakage**
* Indexed → **fast audits**

This matches **EU DPA expectations**, not “checkbox GDPR”.

---

## 5️⃣ GDPR Task Status (Updated)

| Item                  | Status |
| --------------------- | ------ |
| GDPR erasure contract | ✅      |
| DPO role              | ✅      |
| Retention config      | ✅      |
| GDPR Erasure Log      | ✅      |
| Controller guards     | ⏭ next |
| Erasure orchestrators | ⏭ next |

---
