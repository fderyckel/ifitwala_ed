# Policy System — Controller Guards (v1, LOCKED)

> Applies to:
>
> * `Institutional Policy`
> * `Policy Version`
> * `Policy Acknowledgement`

All enforcement happens in **Document controllers**
(`before_insert`, `before_save`, `before_delete`).

No client logic is trusted.

---

## 1️⃣ Institutional Policy — Controller Guards

### File

```
institutional_policy.py
```

---

### `before_insert`

**Rules**

1. `policy_key` must be unique within `organization`
2. `organization` must be set
3. `school`, if set, must belong to the Policy Organization scope:
   School.organization must be either the same Organization or a descendant
   Organization in the Organization NestedSet.

**Hard-fail** if violated.

---

### `before_save`

**Immutability enforcement**

If `not self.is_new()`:

* Block changes to:

  * `policy_key`
  * `organization`
  * `school`

**Allowed edits**

* `policy_title`
* `policy_category`
* `description`
* `is_active`

> PowerSchool pattern: **policy identity never mutates**

---

### `before_delete`

**Always hard-fail**

```text
Institutional Policies cannot be deleted.
Deactivate instead.
```

No override. Ever.

---

## 2️⃣ Policy Version — Controller Guards

### File

```
policy_version.py
```

---

### `before_insert`

**Rules**

1. `institutional_policy` must exist and be active
2. `(institutional_policy, version_label)` must be unique
3. `policy_text` must not be empty

---

### `before_save`

This is the **most important guard set**.

#### Step 1 — Detect existing acknowledgements

```python
has_ack = frappe.db.exists(
	"Policy Acknowledgement",
	{"policy_version": self.name}
)
```

---

#### Step 2 — Immutability once acknowledged

If `has_ack`:

* Block changes to:

  * `policy_text`
  * `version_label`
  * `institutional_policy`

Unless:

* User has role **System Manager**
* AND `override_reason` is provided (mandatory)

> PowerSchool equivalent: “legal text lock”

---

#### Step 3 — Activation discipline

If setting `is_active = 1`:

* Ensure parent `Institutional Policy.is_active = 1`
* Ensure no **other active version** exists **for same policy**

You may:

* auto-deactivate previous version
  OR
* hard-fail and require manual supersede

**Recommendation (PowerSchool-style):**
👉 hard-fail, require explicit supersede action later.

---

#### Step 4 — `approved_by` authority and scope

If `approved_by` is set:

* Must be an enabled **System User**
* Must have **write** access to `Policy Version`
* Scope enforcement:
  * If policy has `school`: user must belong to that school or an ancestor (parent) school
  * If policy is org-scoped only: user must belong to that organization or an ancestor organization

Desk link options for `approved_by` are server-filtered to this same rule.

---

### `before_delete`

**Always hard-fail**

Policy Versions are legal artifacts.

---

## 3️⃣ Policy Acknowledgement — Controller Guards

### File

```
policy_acknowledgement.py
```

---

### `before_insert`

This is **append-only legal evidence**.

#### Core validations

1. `policy_version` must exist
2. `Policy Version.is_active = 1`
3. `acknowledged_by` must be current user

   * (no staff signing for others)
4. `acknowledged_at` is system-set
5. `(policy_version, acknowledged_by, context_doctype, context_name)` must be unique

---

#### Context integrity check (critical)

Validate that:

* `context_doctype` exists
* `context_name` exists
* Context is compatible with `acknowledged_for`

Example rules:

| acknowledged_for | allowed context_doctype     |
| ---------------- | --------------------------- |
| Applicant        | Student Applicant           |
| Student          | Student                     |
| Guardian         | Guardian                    |
| Staff            | Employee                    |

Hard-fail on mismatch.

Role authority (server-enforced):

* Applicant → Admissions Applicant only (must match `Student Applicant.applicant_user`)
* Student → Student OR Guardian linked to that Student
* Guardian → Guardian acknowledging for themselves only
* Staff → Staff only

> PowerSchool does this implicitly; we make it explicit.

---

### `before_save`

**Always hard-fail**

Acknowledgements are **immutable**.

```text
Policy Acknowledgements are append-only and cannot be edited.
```

---

### `before_delete`

**Always hard-fail**

No deletion. No exceptions.

---

## 4️⃣ Cross-Cutting Enforcement Utilities

### 4.1 Role checks (centralized helper)

Create one helper:

```python
def is_system_manager(user=None) -> bool
```

Use **once**, not ad-hoc role checks everywhere.

---

### 4.2 Override discipline (System Manager only)

Overrides must:

* require explicit reason
* be logged (Comment or Audit Log)
* never be silent

Pattern:

```python
if has_ack and not is_system_manager():
	frappe.throw(...)
```

---

## 5️⃣ PowerSchool-Inspired Design Notes (Why this works)

PowerSchool, Infinite Campus, and Workday all share these traits:

* Policy text freezes once acknowledged
* Consent is append-only
* Context is explicit (student, staff, guardian)
* Deactivation ≠ deletion
* Overrides are rare and logged

You’ve now matched that bar.

---

## 6️⃣ What this deliberately does NOT do

* ❌ no workflow transitions
* ❌ no approval gating
* ❌ no promotion checks
* ❌ no portal assumptions
* ❌ no auto-acknowledgement

Those belong to **Phase 03+**.

---

## 7️⃣ Lock statement

> These controller guards are **authoritative for Phase 02**.
>
> Any future change requires:
>
> * legal reasoning
> * schema contract bump
> * migration note

---
