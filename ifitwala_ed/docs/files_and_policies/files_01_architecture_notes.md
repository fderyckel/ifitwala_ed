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
| `primary_subject_type` | Select (`student`, `guardian`, `staff`) |
| `primary_subject_id`   | Dynamic Link                            |

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
| `subject_type` | Select                                          |
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

Examples:

```
assessment_submission
feedback
identity_verification
contractual
safeguarding_review
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

