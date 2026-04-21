Good. This is the right moment to hard-lock it.
# Policy & Acknowledgement Authority Matrix — v1

**Ifitwala_Ed (Authoritative)**

> Applies to the organization-wide policy system:
>
> ```
> Institutional Policy
> → Policy Version
> → Policy Acknowledgement
> ```

This matrix governs **who may create, modify, acknowledge, override, or view** policy artifacts.

---

## 0. Role Vocabulary (Canonical)

These roles already exist conceptually in your system; this matrix assumes them.

| Role                   | Scope                               |
| ---------------------- | ----------------------------------- |
| **System Manager**     | Global, technical + legal superuser |
| **Organization Admin** | Organization-wide governance        |
| **Accounts Manager**   | Finance governance                  |
| **Admission Manager**  | Admissions governance               |
| **Academic Admin**     | Academics governance                |
| **HR Manager**         | HR governance                       |
| **School Admin**       | School-scoped governance            |
| **Admissions Officer** | Admissions-only scope               |
| **Academic Staff**     | Teachers, counselors                |
| **Guardian**           | Parent / legal guardian             |
| **Student**            | Enrolled student                    |
| **Admissions Applicant** | Pre-student (Applicant portal user) |

> Visibility **≠ authority**.
> This matrix only defines authority.

---

## 1. Institutional Policy (semantic owner)

> Represents the **existence and intent** of a policy.

### Allowed actions

| Action                                      | System Manager | Org Admin | Policy Admin Managers* | School Admin | Others |
| ------------------------------------------- | -------------- | --------- | ---------------------- | ------------ | ------ |
| Create policy                               | ✅              | ✅         | ✅                      | ❌            | ❌      |
| Edit metadata (title, category, applies_to) | ✅              | ✅         | ✅                      | ❌            | ❌      |
| Deactivate policy                           | ✅              | ✅         | ✅                      | ❌            | ❌      |
| Delete policy                               | ❌              | ❌         | ❌                      | ❌            | ❌      |

\* Policy Admin Managers: `Accounts Manager`, `Admission Manager`, `Academic Admin`, `HR Manager` (and only when DocType permissions also grant access).

### Hard rules

* Policies are **never deleted**
* Deactivation hides future versions but preserves history
* School-specific policies must declare `school`
* Org-wide policies have `school = NULL`
* Organization-scoped policies cascade to descendant Organizations
  (Organization NestedSet only; School tree is not used for policy ancestry)
* Applicability is nearest-only by `policy_key`:
  when parent and child define the same key, the nearest Organization wins

**Invariant**

> Institutional Policy is *semantic*, not legal.
> No acknowledgements attach here.

---

## 2. Policy Version (legal truth)

> Represents the **exact text that was agreed to**.

### Allowed actions

| Action                            | System Manager   | Org Admin | Policy Admin Managers* | School Admin | Others |
| --------------------------------- | ---------------- | --------- | ---------------------- | ------------ | ------ |
| Create new version                | ✅                | ✅         | ✅                      | ❌            | ❌      |
| Edit text (draft only)            | ✅                | ✅         | ✅                      | ❌            | ❌      |
| Activate version                  | ✅                | ✅         | ✅                      | ❌            | ❌      |
| Supersede version                 | ✅                | ✅         | ✅                      | ❌            | ❌      |
| Edit text after activation        | ❌                | ❌         | ❌                      | ❌            | ❌      |
| Edit after acknowledgement exists | ❌                | ❌         | ❌                      | ❌            | ❌      |
| Delete version                    | ❌                | ❌         | ❌                      | ❌            | ❌      |

### Immutability rule (LOCKED)

> `policy_text` is editable only while Draft (`is_active = 0`) and no acknowledgements exist.
>
> Once a version is activated, text becomes permanently lock-protected.
>
> Once **any** Policy Acknowledgement exists:
>
> * `policy_text` becomes **read-only**
> * `version_label` becomes **read-only**
> * Only System Manager may override (with reason)

Override requires:

* explicit confirmation
* mandatory reason
* audit trail

---

## 3. Policy Acknowledgement (evidence of consent)

> Represents **who agreed, to what, in which context**.

### Who may acknowledge

| Actor                                      | Allowed   |
| ------------------------------------------ | --------- |
| Admissions Applicant (for Applicant)       | ✅         |
| Guardian (for Student / Guardian)          | ✅         |
| Student (if policy applies_to = Student)   | ✅         |
| Staff (for themselves)                     | ✅         |
| Staff acknowledging *for someone else*     | ❌         |
| System Manager (impersonated testing only) | ⚠️ Logged |

**Invariant**

> No one acknowledges on behalf of another adult.

---

### Who may create acknowledgements (technical authority)

| Role                                           | Allowed          |
| ---------------------------------------------- | ---------------- |
| Admissions Applicant / Guardian / Student / Staff | ✅ (self only) |
| Admissions Officer         | ❌                |
| School Admin               | ❌                |
| Org Admin                  | ❌                |
| System Manager             | ⚠️ Override only |

---

### Viewing acknowledgements

| Role               | Scope                 |
| ------------------ | --------------------- |
| System Manager     | All                   |
| Org Admin          | Org-wide              |
| School Admin       | School-scoped         |
| Admissions Officer | Applicant-scoped only |
| Guardian           | Own + dependents      |
| Student            | Own                   |
| Academic Staff     | Own staff records only |

---

### Editing / revoking acknowledgements

| Action                 | Anyone |
| ---------------------- | ------ |
| Edit acknowledgement   | ❌      |
| Cancel acknowledgement | ❌      |
| Revoke acknowledgement | ❌      |
| Delete acknowledgement | ❌      |

**Invariant**

> Acknowledgements are **append-only evidence**.

If policy wording changes → new Policy Version → new acknowledgement.

---

## 4. Context Binding Rules (critical)

Every Policy Acknowledgement **must** declare:

| Field              | Required |
| ------------------ | -------- |
| `policy_version`   | ✅        |
| `acknowledged_by`  | ✅        |
| `acknowledged_for` | ✅        |
| `context_doctype`  | ✅        |
| `context_name`     | ✅        |
| `acknowledged_at`  | System   |

Examples:

* Applicant consent → `Student Applicant`
* Student handbook → `Student`
* Staff code → `Employee`

**Invariant**

> Same person + same policy version + different context
> = different legal act.

---

## 5. Admissions Policy Acknowledgements — Current Runtime

Admissions acknowledgements are governed by two explicit runtime controls:

* `Admission Settings.admissions_access_mode`
  * `Single Applicant Workspace`
  * `Family Workspace`
* `Institutional Policy.admissions_acknowledgement_mode`
  * `Child Acknowledgement` (default)
  * `Family Acknowledgement`
  * `Child Optional Consent`

### Actor and context rules

#### Child Acknowledgement

* The current admissions portal user acknowledges in applicant context
* `acknowledged_for = Applicant`
* `context_doctype = Student Applicant`
* Access is limited to the requested applicant through admissions access resolution
* In `Family Workspace`, an `Admissions Family` user may complete this step only for explicitly linked applicants

#### Family Acknowledgement

* Only an `Admissions Family` user linked through a primary `Student Applicant Guardian` row with `can_consent = 1` may sign
* Evidence is always stored on guardian self-context
* `acknowledged_for = Guardian`
* `context_doctype = Guardian`
* `context_name` must resolve to the current signer's `Guardian` record
* Non-primary or non-signer guardians are blocked server-side

#### Child Optional Consent

* Uses the same applicant-context evidence shape as `Child Acknowledgement`
* `acknowledged_for = Applicant`
* `context_doctype = Student Applicant`
* It remains optional for admissions readiness and must not be treated as a missing required acknowledgement

### Scope and invariants

* Every admissions acknowledgement remains an explicit `Policy Acknowledgement` insert
* Applicant access is server-owned and resolved from the configured admissions access mode
* Guardian authority is explicit via `Student Applicant Guardian`; it is never inferred from `applicant_user` or shared email
* Family-mode acknowledgements do not create Guardian Portal access and do not promote the applicant to Guardian or Student
* Enrolled-student durable acknowledgement remains governed separately by `policy_06_enrolled_student_policy_acknowledgement_contract.md`

### Post-Promotion (Student Stage)

Once an Applicant is promoted to Student:

* Guardian relationships are explicit via `Student Guardian`
* Guardians may acknowledge policies **for Students**, subject to:

  * verified guardian–student linkage
  * server-side authorization checks

### Summary

* Admissions acknowledgement now supports applicant-context and guardian-self-context evidence depending on `admissions_acknowledgement_mode`
* Student-stage durable acknowledgement remains `Student` or linked `Guardian`, depending on audience and signer authority
* No implicit authority
* No retroactive inference
* All acknowledgement rules are explicit, auditable, and enforced server-side

---

## 5.1 Media / Image Consent (policy_key = `media_consent`)

This policy is the **sole consent gate** for publishing student profile photos.

**Required configuration**

* `Institutional Policy.policy_key = media_consent`
* `policy_category = Privacy & Data Protection`
* `applies_to` includes **Applicant**
* `Policy Version.is_active = 1`

**Acknowledgement context**

* `Child Acknowledgement` / `Child Optional Consent`

  * `acknowledged_for = Applicant`
  * `context_doctype = Student Applicant`
* `Family Acknowledgement`

  * `acknowledged_for = Guardian`
  * `context_doctype = Guardian`
  * self-context only for an eligible primary family signer

**Behavior**

* If acknowledged → Student image may be made public at promotion
* If not acknowledged → Student image stays private

---

## 6. Explicit Prohibitions (non-negotiable)

The system must **never**:

* Auto-acknowledge policies
* Assume consent from form submission
* Reuse acknowledgements across contexts
* Allow silent overrides
* Backfill acknowledgements for legacy users

Violations are **legal defects**, not bugs.

---

## 7. Lock Statement

> This authority matrix is **locked for v1**.
>
> Any future change requires:
>
> * explicit migration reasoning
> * legal impact review
> * version bump of this matrix

---

# Policy System — Schema Lock (v1)

**Applies globally across Ifitwala_Ed**

```
Institutional Policy
→ Policy Version
→ Policy Acknowledgement
```

No additional policy doctypes are permitted in Phase 02.

---

## 1️⃣ Institutional Policy — Doctype Schema (LOCKED)

### Purpose

Defines **what policy exists institutionally**.
No legal meaning. No acknowledgements here.

### Doctype

```
Institutional Policy
```

### Fields (authoritative)

| Fieldname         | Type                | Required | Notes                                                          |
| ----------------- | ------------------- | -------- | -------------------------------------------------------------- |
| `policy_key`      | Data                | ✅        | Stable, machine identifier (immutable)                         |
| `policy_title`    | Data                | ✅        | Human-readable                                                 |
| `policy_category` | Select              | ✅        | Safeguarding / Privacy & Data Protection / Admissions / Academic / Conduct & Behaviour / Health & Safety / Operations / Handbooks / Employment |
| `applies_to`      | Table MultiSelect   | ✅        | Child rows linked to `Policy Audience`: Applicant, Student, Guardian, Staff |
| `organization`    | Link → Organization | ✅        | Immutable                                                      |
| `school`          | Link → School       | ❌        | NULL = org-wide                                                |
| `description`     | Small Text          | ❌        | Non-legal                                                      |
| `is_active`       | Check               | ✅        | Controls discoverability                                       |

### Immutability rules

* `policy_key` → immutable after insert
* `organization`, `school` → immutable
* Deletion **forbidden**

### Server invariants

```text
(policy_key, organization) must be unique
```

---

## 2️⃣ Policy Version — Doctype Schema (LOCKED)

### Purpose

Defines **the exact legal text that may be acknowledged**.

### Doctype

```
Policy Version
```

### Fields (authoritative)

| Fieldname              | Type                        | Required | Notes                                                     |
| ---------------------- | --------------------------- | -------- | --------------------------------------------------------- |
| `institutional_policy` | Link → Institutional Policy | ✅        | Immutable                                                 |
| `version_label`        | Data                        | ✅        | Human version identifier                                  |
| `based_on_version`         | Link → Policy Version       | ✅*       | Required after first version; must belong to same policy  |
| `change_summary`       | Small Text                  | ✅*       | Required before activation when `based_on_version` is set      |
| `policy_text`          | Text / HTML                 | ✅        | Editable only in Draft before lock                        |
| `diff_html`            | Text / HTML                 | Auto      | Server-generated paragraph diff for amended versions      |
| `change_stats`         | Small Text (JSON)           | Auto      | `{added,removed,modified}`                                |
| `text_locked`          | Check (hidden)              | Auto      | Set on first activation or acknowledgement                |
| `effective_from`       | Date                        | ❌        | Optional                                                  |
| `effective_to`         | Date                        | ❌        | Optional                                                  |
| `approved_by`          | Link → User                 | ❌        | Governance metadata                                       |
| `approved_on`          | Datetime                    | ❌        | Governance metadata                                       |
| `is_active`            | Check                       | ✅        | Can be acknowledged                                       |

`✅*` = amendment boundary requirement; for `change_summary`, drafts may save blank but activation requires value.

### Immutability rules

`policy_text` is editable only while Draft (`is_active = 0`) and no acknowledgements exist.

After first activation, `text_locked = 1` and text remains lock-protected.

Once **any** Policy Acknowledgement exists:

* `policy_text` → read-only
* `version_label` → read-only
* `based_on_version`, `change_summary`, `diff_html`, `change_stats` → lock-protected
* record cannot be deleted
* only System Manager override allowed (reason required)

### Server invariants

```text
(institutional_policy, version_label) must be unique
```

---

## 3️⃣ Policy Acknowledgement — Doctype Schema (LOCKED)

### Purpose

Represents **explicit, contextual consent**.

### Doctype

```
Policy Acknowledgement
```

### Fields (authoritative)

| Fieldname          | Type                  | Required | Notes                                  |
| ------------------ | --------------------- | -------- | -------------------------------------- |
| `policy_version`   | Link → Policy Version | ✅        | Immutable                              |
| `acknowledged_by`  | Link → User / Contact | ✅        | The person who consented               |
| `acknowledged_for` | Select                | ✅        | Applicant / Student / Guardian / Staff |
| `context_doctype`  | Data                  | ✅        | e.g. Student Applicant                 |
| `context_name`     | Data                  | ✅        | Applicant ID, Student ID               |
| `acknowledged_at`  | Datetime              | ✅        | System-set                             |
| `ip_address`       | Data                  | ❌        | Optional (future-proof)                |
| `user_agent`       | Small Text            | ❌        | Optional                               |

### Immutability rules

* Entire document is **append-only submitted evidence**
* Auto-submit on insert (`docstatus = 1`)
* No edits
* No cancel
* No deletion
* No revocation

### Server invariants

```text
(policy_version, acknowledged_by, context_doctype, context_name) must be unique
```

---

## 4️⃣ Cross-Doctype Enforcement Rules (SERVER-SIDE)

These are **schema-level truths**, not workflow rules.

### 4.1 Creation constraints

* A Policy Version **cannot exist** without Institutional Policy
* Acknowledgement **cannot exist** unless Policy Version is active
* Acknowledgement **cannot be created** by staff on behalf of others

### 4.2 Deletion constraints

| Doctype                | Deletion |
| ---------------------- | -------- |
| Institutional Policy   | ❌ Never  |
| Policy Version         | ❌ Never  |
| Policy Acknowledgement | ❌ Never  |

Soft archival is allowed via `is_active = 0`.

---

## 5️⃣ What is intentionally NOT in schema (discipline)

These are explicitly deferred:

* ❌ workflow states
* ❌ auto-blocking logic
* ❌ promotion checks
* ❌ UI fields (“I agree” checkboxes)
* ❌ portal assumptions
* ❌ school-specific enforcement

All of those belong to **later phases**.

---

## 6️⃣ Why this matches ERP & SaaS best practice

This mirrors how serious systems behave:

* **SAP / Workday** → Policy + Version + Attestation
* **Rippling / Deel** → Immutable acknowledgements
* **PowerSchool / Infinite Campus** → Context-bound consent
* **ISO / SOC2** → Append-only legal evidence

Key best-practice traits:

* Legal text is immutable once used
* Consent is contextual
* Policy identity is stable
* Versioning is explicit, not inferred
* No “latest policy” shortcuts

---

## 7️⃣ Lock statement (final)

> This schema is **locked for Phase 02**.
>
> Any later change requires:
>
> * schema migration
> * legal review
> * version bump of this contract

---
