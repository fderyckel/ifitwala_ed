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
| Academic Staff     | ❌                     |

---

### Editing / revoking acknowledgements

| Action                 | Anyone |
| ---------------------- | ------ |
| Edit acknowledgement   | ❌      |
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

## 5. Admissions Policy Acknowledgements — Authority Model

### Current Model (Phase 1)

During admissions, Ifitwala uses a **single accountable actor model**.

* Each `Student Applicant` is associated with one **Admissions Applicant user** (`applicant_user`)
* This user:

  * uploads documents and images
  * acknowledges required policies
  * submits the application

Policy acknowledgements during admissions are therefore:

* **Acknowledged for:** Applicant
* **Acknowledged by:** Admissions Applicant user only

The system does **not** currently record guardian relationships at the applicant stage.
As a result:

* Guardian roles are **not permitted** to acknowledge policies for Applicants
* Guardian authority is **not inferred** from `applicant_user`
* This behavior is intentional and enforced server-side

This model is valid for lightweight admissions flows and ensures internal consistency and auditability.

### Known Limitation (Phase 1)

The system does not currently model:

* guardian→applicant relationships
* multiple guardians
* guardian-specific consent authority during admissions

This limitation is acknowledged and documented.

### Phase 2 — Explicit Applicant–Guardian model (definition)

Phase 2 introduces a **new, explicit relationship** between a `Student Applicant` and one or more `Guardian` records.

New child table on `Student Applicant`:

DocType: `Student Applicant Guardian`

Fields:

* `guardian` (Link → Guardian, required)
* `relationship` (Select, same options as `Student Guardian.relation`)
* `is_primary` (checkbox)
* `can_consent` (checkbox, default = true)

This mirrors the existing Student ↔ Guardian model and removes all implicit assumptions about who is allowed to act during admissions.

Phase 2 **does not** change behavior by itself. It only makes authority expressible and enforceable.

### Phase 3 — Policy enforcement rules (after Phase 2)

Phase 3 defines **who can acknowledge**, **for whom**, and **when a policy is considered satisfied**.

#### Actor eligibility rules (summary)

* Applicant-stage (`context_doctype = Student Applicant`)

  * `acknowledged_for = Applicant` → Admissions Applicant user, or Guardian user linked via `Student Applicant Guardian` with `can_consent = 1`
  * `acknowledged_for = Guardian` → Guardian user acknowledging for self only, and linked to the applicant

* Student-stage (`context_doctype = Student`)

  * `acknowledged_for = Student` → Student user, or Guardian user linked via `Student Guardian` (and `can_consent = 1` if added later)
  * `acknowledged_for = Guardian` → Guardian user acknowledging for self only

#### Completion rules (summary)

Add one field on **Institutional Policy** or **Policy Version**:

`consent_mode` (Select)

* `single_actor` (default)
* `primary_guardian_only`
* `all_eligible_guardians`

### Post-Promotion (Student Stage)

Once an Applicant is promoted to Student:

* Guardian relationships are explicit via `Student Guardian`
* Guardians may acknowledge policies **for Students**, subject to:

  * verified guardian–student linkage
  * server-side authorization checks

### Summary

* Admissions consent = **Applicant user only**
* Student consent = **Student or linked Guardian**
* No implicit authority
* No retroactive inference
* All consent rules are explicit, auditable, and enforced server-side

---

## 5.1 Media / Image Consent (policy_key = `media_consent`)

This policy is the **sole consent gate** for publishing student profile photos.

**Required configuration**

* `Institutional Policy.policy_key = media_consent`
* `policy_category = Privacy & Data Protection`
* `applies_to` includes **Applicant**
* `Policy Version.is_active = 1`

**Acknowledgement context (locked)**

* `acknowledged_for = Applicant`
* `context_doctype = Student Applicant`

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
| `applies_to`      | MultiSelect         | ✅        | Applicant, Student, Guardian, Staff                            |
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
| `amended_from`         | Link → Policy Version       | ✅*       | Required after first version; must belong to same policy  |
| `change_summary`       | Small Text                  | ✅*       | Human summary required when `amended_from` is set         |
| `policy_text`          | Text / HTML                 | ✅        | Editable only in Draft before lock                        |
| `diff_html`            | Text / HTML                 | Auto      | Server-generated paragraph diff for amended versions      |
| `change_stats`         | Small Text (JSON)           | Auto      | `{added,removed,modified}`                                |
| `text_locked`          | Check (hidden)              | Auto      | Set on first activation or acknowledgement                |
| `effective_from`       | Date                        | ❌        | Optional                                                  |
| `effective_to`         | Date                        | ❌        | Optional                                                  |
| `approved_by`          | Link → User                 | ❌        | Governance metadata                                       |
| `approved_on`          | Datetime                    | ❌        | Governance metadata                                       |
| `is_active`            | Check                       | ✅        | Can be acknowledged                                       |

`✅*` = required for versions after the first amendment boundary (`amended_from` set / prior version exists).

### Immutability rules

`policy_text` is editable only while Draft (`is_active = 0`) and no acknowledgements exist.

After first activation, `text_locked = 1` and text remains lock-protected.

Once **any** Policy Acknowledgement exists:

* `policy_text` → read-only
* `version_label` → read-only
* `amended_from`, `change_summary`, `diff_html`, `change_stats` → lock-protected
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

* Entire document is **append-only**
* No edits
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
