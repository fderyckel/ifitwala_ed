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
  * later identity upgrade (Admissions Applicant → Student, with separate Guardian provisioning)

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

* After promotion + active enrollment, the first active `Program Enrollment` can trigger the server-owned identity upgrade that removes the applicant role from the student account
* That applicant account becomes the `Student` identity
* Guardian identities are provisioned separately from explicit guardian rows

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

> “A pre-student admissions identity allowed to complete and review admissions materials within the configured admissions access mode.”

It is **not** a student role
It is **not** a staff role

### 4.2.1 Additional role: `Admissions Family`

When `Admission Settings.admissions_access_mode = Family Workspace`, a second website role is active:

> “A pre-guardian admissions collaborator allowed to work on all explicitly linked applicants in one family workspace.”

This role:

* is distinct from `Admissions Applicant`
* is anchored through explicit `Student Applicant Guardian` rows where `is_primary_guardian = 1` and the derived signer flag `can_consent = 1`
* uses one real user per adult collaborator; shared logins are not allowed

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
* verify role = `Admissions Applicant` or `Admissions Family`
* verify applicant ownership via one of:
  * `Student Applicant.applicant_user` in single-applicant mode
  * explicit consenting applicant guardian linkage in family-workspace mode
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

* `/hub/student`
* `/hub/guardian`
* `/hub/staff`

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

### 9.1 Admissions access modes

Admissions access is site-configured in `Admission Settings.admissions_access_mode`.

`Single Applicant Workspace`

* `Admissions Applicant` user is linked to exactly one `Student Applicant`
* no applicant switching

`Family Workspace`

* `Admissions Family` user can access one-or-more explicitly linked applicants
* sibling switching is allowed inside `/admissions`
* access is resolved only from explicit guardian rows, never from guessed shared email matches

In both modes, access is enforced **server-side**, not via UI hiding.

---

### 9.2 GDPR alignment (baseline)

* All uploads are linked to Student Applicant
* File Classification primary subject is **Student Applicant**
* All files are deletable via Applicant purge
* No documents live directly on User
* Files are never moved or re-linked on promotion
* Approved applicant evidence submissions are copied as new Student File records with source linkage preserved unless the parent requirement routes promotion elsewhere
* Identity can be erased independently of application record

(Full GDPR policy handled elsewhere; this portal does not violate it.)

---

## 10. What This Portal Is *Not*

To avoid future drift:

This portal is **not**:

* a CMS
* a Guardian preview
* a general-purpose messaging platform
* a real-time chat system
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
    roles: ["Admissions Applicant" | "Admissions Family"]
  }
  access_mode: "Single Applicant Workspace" | "Family Workspace"
  family_workspace_enabled: boolean
  selected_applicant: string
  available_applicants: AdmissionsSessionApplicant[]
  applicant: {
    name: string
    display_name: string
    portal_status: PortalApplicantStatus
    school: string
    organization: string
    is_read_only: boolean
    read_only_reason: string | null
  }
}
```

### Invariants

* Single-applicant mode resolves exactly one applicant via `applicant_user`
* Family-workspace mode resolves one-or-more applicants via explicit consenting guardian linkage
* If no applicant access exists → **403**
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

## A.3.1 Applicant Profile DTO

### Endpoints

```
GET  /api/admissions/profile/:applicant
POST /api/admissions/profile/update
POST /api/admissions/profile/image/upload
POST /api/admissions/profile/guardian/image/upload
```

### Returns

```ts
ApplicantProfilePayload {
  profile: ApplicantProfile
  completeness: {
    ok: boolean
    missing: string[]
    required: string[]
  }
  application_context: ApplicantApplicationContext
  applicant_image: string
  options: {
    genders: string[]
    residency_statuses: string[]
    languages: Array<{ value: string; label: string }>
    countries: Array<{ value: string; label: string }>
  }
}
```

### Rules

* Profile update is applicant-scoped and server-validated.
* Guardian rows (when enabled) are applicant-scoped and server-validated:
  * required per row: first name, last name, personal email, mobile phone, photo
  * personal/work emails must pass email validation
  * mobile/work phones must pass phone validation
* Profile image upload is applicant-scoped and mutable-status only.
* Profile image upload must route through dispatcher classification:
  * `data_class = identity_image`
  * `purpose = applicant_profile_display`
  * `retention_policy = until_school_exit_plus_6m`
  * `slot = profile_image`
  * `upload_source = SPA`
* Applicant and guardian portal photo uploads accept only `JPG`, `JPEG`, or `PNG`.
* Upload validation is server-owned:
  * file extension allowlist is enforced
  * upload bytes must sniff as `JPEG` or `PNG`
  * image decode must succeed
  * original upload size is capped at `10 MB`
  * decoded image size is capped at `25 megapixels`
* Accepted uploads are normalized server-side to a canonical `JPEG`:
  * EXIF orientation is applied
  * EXIF/ancillary metadata is stripped
  * the stored filename is generated by the server, not copied from the user upload
* Uploaded profile image remains private and stored on `Student Applicant.applicant_image`.
* Guardian photo upload remains private, is normalized with the same rules, and returns a canonical file URL used by `Student Applicant Guardian.guardian_image`.
* Portal responses add `X-Content-Type-Options: nosniff` via app request hooks.

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

### A.5.2 Applicant Requirements and Submitted Files

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
  label: string
  description: string
  is_required: boolean
  is_repeatable: boolean
  required_count: number
  uploaded_count: number
  approved_count: number
  rejected_count: number
  pending_count: number
  requirement_state:
    | 'not_started'
    | 'waiting_review'
    | 'changes_requested'
    | 'complete'
    | 'waived'
    | 'exception_approved'
  requirement_state_label: string
  requirement_override: 'Waived' | 'Exception Approved' | null
  override_reason: string | null
  override_by: string | null
  override_on: datetime | null
  review_status: "Pending" | "Approved" | "Rejected"
  reviewed_by: string | null
  reviewed_on: datetime | null
  uploaded_at: datetime
  file_url: string | null
  items: ApplicantDocumentSubmission[]
}

ApplicantDocumentSubmission {
  name: string
  item_key: string
  item_label: string
  review_status: "Pending" | "Approved" | "Rejected" | "Superseded"
  reviewed_by: string | null
  reviewed_on: datetime | null
  uploaded_at: datetime
  file_url: string
  file_name: string | null
}
```

### Upload rules

* Portal is requirement-centric; applicants do not choose between parent requirement and submission rows
* Upload resolves/creates one `Applicant Document` requirement card and creates/reuses one `Applicant Document Item` submission row server-side
* File attaches **only** to `Applicant Document Item`
* `item_label` is optional and is used only to help distinguish multiple submitted files
* Non-repeatable requirements reuse the existing submission row on replacement
* Repeatable requirements may allocate additional submission rows
* No direct file uploads to `Student Applicant` or `Applicant Document`
* File Classification primary subject is always **Student Applicant**
* Recommendation-template target document types are excluded from applicant document reads and uploads; applicants track referee progress only via `/admissions/status`

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
  typed_signature_name: string
  attestation_confirmed: 1
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

## A.8 Admissions Communication Thread

### Endpoints

```
POST /api/method/ifitwala_ed.api.admissions_communication.get_admissions_case_thread
POST /api/method/ifitwala_ed.api.admissions_communication.send_admissions_case_message
POST /api/method/ifitwala_ed.api.admissions_communication.mark_admissions_case_thread_read
```

### Rules

* Context is `Student Applicant` only for applicant portal callers.
* Applicant portal sends applicant-visible messages only.
* Internal staff notes never render in applicant portal thread responses.
* Read state is tracked per user/thread through `Portal Read Receipt`.
* Storage contract:
  * `Org Communication` = case thread/container
  * `Communication Interaction Entry` = applicant/staff message ledger
  * `Portal Read Receipt` = per-user read state
* Canonical cross-surface messaging rules live in `docs/spa/07_org_communication_messaging_contract.md`.

---

## A.9 Explicitly Forbidden APIs

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

### `/admissions/profile`

**Page:** `ApplicantProfile.vue`

**Purpose**

* Maintain student profile fields required for promotion
* Upload/update applicant-owned student image
* Optionally maintain one-or-more guardian intake rows when enabled in `Admission Settings.show_guardians_in_admissions_profile`
* Show inline upload progress for applicant and guardian image uploads so families can see that large files are still moving

**Reads**

* `ApplicantProfilePayload`

**Writes**

* profile update
* guardian intake row update (when enabled)
* profile image upload (governed)

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

* Upload & view applicant-owned documents
* Excludes recommendation evidence collected from external referees
* Show inline upload progress inside the upload overlay rather than relying only on disabled buttons or generic busy text

**Reads**

* ApplicantDocuments list

**Writes**

* Upload via overlay

---

### `/admissions/policies`

**Page:** `ApplicantPolicies.vue`

**Purpose**

* Display required policies
* Capture explicit electronic signatures + acknowledgements

**Writes**

* PolicyAcknowledgement only

---

### `/admissions/messages`

**Page:** `ApplicantMessages.vue`

**Purpose**

* Applicant ↔ admissions case communication in-app
* Keep communication attached to `Student Applicant` context

**Reads**

* Admissions case thread summary + message timeline

**Writes**

* Applicant-visible messages only

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
* Recommendation progress status
* Enrollment offer review / accept / decline when an Applicant Enrollment Plan offer is open
* No access to referee submission content or files

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
* upload overlays must keep progress feedback visible while the browser prepares/sends the file and while the server finalizes the governed upload

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
* staff notes
* review UI
* approval UI
* promotion UI

Messaging is intentionally shared between applicant portal and staff cockpit as the single case communication surface.
Staff-only notes remain staff workspace concerns.

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
| Scope                        | Site-configured: one applicant or all explicitly linked family applicants |
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

* Created by **admissions staff**
* Assigned:
  * `Admissions Applicant` for single-applicant login invite
  * `Admissions Family` for family-workspace adult collaborator invite

### User Identity Rules

* User **must not** be linked to:

  * Guardian
  * Student
  * Employee
* Email may later match a Guardian, but **no implicit upgrade**

### External Recommendation Intake (Implemented Extension)

The admissions portal authentication contract above remains unchanged.

For confidential recommender submissions, the system may add a **separate external intake surface** that is not applicant portal authentication:

* No `Admissions Applicant` login/session is created for recommenders.
* No Desk, Student, Guardian, or applicant-browsing access is granted.
* A single-use, expiring link may authorize one recommendation submission only.
* Token values must be stored hashed, with server-side expiry, consumption, and rate-limit guards.

This extension is implemented with:

* route: `/admissions/recommendation/<token>` (guest recommender intake)
* API: `ifitwala_ed.api.recommendation_intake.*`
* DocTypes: `Recommendation Template`, `Recommendation Request`, `Recommendation Submission`
* applicant status-only surface: admissions snapshot `recommendations_summary` + `completeness.recommendations`
* applicant documents surface excludes recommendation evidence and recommendation target document types
* if a school wants the applicant to upload a recommendation letter directly, that must be configured as a normal `Applicant Document Type`, not a `Recommendation Template`
* architecture contract: `docs/admission/06_recommendation_intake_architecture.md`

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

  * view requirement cards and submitted files
  * upload or replace files through named admissions endpoints
* Portal cannot:

  * approve / reject
  * change document type
  * delete
  * manage submission rows directly outside the upload flow

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
User has role Admissions Applicant or Admissions Family
AND
Applicant access resolves from the configured admissions access mode
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
/hub/*
/student/*
/guardian/*
/desk/*
```

Any attempt → redirect to login.

---

## C.8 Lifecycle Management (LOCKED)

### User Creation

Triggered by:

* Invite to Apply
* Identity Upgrade (server-owned, after first active enrollment or manual rerun)

### User Deactivation (MANDATORY)

| Event               | Action                  |
| ------------------- | ----------------------- |
| Applicant Rejected  | Disable user            |
| Applicant Withdrawn | Disable user            |
| Applicant Promoted  | Keep applicant login until server-owned identity upgrade |
| GDPR Erasure        | Anonymize or purge user |

Role mutation happens only inside the server-owned identity-upgrade flow after active enrollment.
No credential reuse across unrelated identities.
No silent persistence.

---

## C.9 Explicitly Forbidden Patterns

Codex **must not**:

* Reuse the applicant login as a guardian login
* Share accounts across Applicants
* Reuse credentials
* Grant Website User role
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
* [x] Never mutate roles dynamically

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

* Portal status ∈ {In Review, Offer Sent, Offer Expired, Accepted, Declined, Rejected, Withdrawn, Completed}
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
