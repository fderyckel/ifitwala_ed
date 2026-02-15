# A️ Task Submission Flows (Students uploading work)

## 1. What a Task Submission *is* (re-anchoring)

A **Task Submission file** is:

* Evidence of work
* Time-bound
* Replaceable
* Disposable

It is **not**:

* The grade
* The assessment record
* The academic decision

This separation is the core reason your architecture is already superior.

---

## 2. Canonical ownership & subject model

### Primary subject

```
primary_subject_type = student
primary_subject_id   = <Student>
```

Always the student — even for group work.

### Secondary subjects (optional)

Used only for **impact analysis**, never ownership.

Examples:

* Group task → other students as `co-owner`
* Teacher feedback file → teacher as `contextual`

Deletion authority remains **student-only**.

This is **correct GDPR controller logic**.

---

## 3. Slot model for tasks (NON-NEGOTIABLE)

You need **explicit slots**. No generic “attachments”.

### Required slots

| Slot                  | Behavior       | Versioning |
| --------------------- | -------------- | ---------- |
| `submission`          | Student upload | Versioned  |
| `feedback`            | Teacher upload | Versioned  |
| `rubric_evidence`     | Optional       | Versioned  |
| `supporting_material` | Optional       | Versioned  |

**Why slots matter**

* Allows delete-only-submission
* Allows delete-student-files-keep-grades
* Allows retention expiry by slot

Most LMS systems **cannot do this cleanly**.

---

## 4. Dispatcher payload (Task submission)

A student uploading a task **must** go through:

```python
create_and_classify_file(
	file_kwargs={
		"attached_to_doctype": "Task Submission",
		"attached_to_name": submission.name,
		"is_private": 1,
	},
	classification={
		"primary_subject_type": "student",
		"primary_subject_id": student,
		"data_class": "assessment",
		"purpose": "assessment_submission",
		"retention_policy": "until_school_exit_plus_6m",
		"slot": "submission",
		"organization": org,
		"school": school,
	},
	secondary_subjects=[
		{"subject_type": "student", "subject_id": peer_id, "role": "co-owner"}
	]
)
```

**No slot → reject upload.**

---

## 5. Deletion scenarios (must all work)

### Scenario 1 — Student requests erasure

✅ Delete all task files
✅ Keep grades, analytics, teacher comments (text)
✅ Assessment records still computable

### Scenario 2 — Teacher replaces feedback

✅ Old feedback file hidden
✅ Version incremented
✅ Only latest shown

### Scenario 3 — School retention expiry

✅ Bulk delete task files
✅ Academic outcomes untouched

This is where Moodle / Google Classroom **fail badly**.

---

## 6. Common platform mistakes (what you avoid)

| Platform mistake              | Why it’s bad                     |
| ----------------------------- | -------------------------------- |
| Files tied directly to grades | Erasure breaks transcripts       |
| Shared Drive folders          | Impossible to delete per student |
| Filename-based semantics      | Not machine-governable           |
| One-off attachment logic      | Impossible audits                |

You are **already ahead**.

---

# B️⃣ Admissions: Families uploading documents

This is even more sensitive.

---

## 1. Admissions uploads are **Applicant-owned**

Key insight (many platforms get this wrong):

> **Admissions files belong to the Student Applicant, not Student or Guardian.**

Until enrollment:

* No Student exists
* No operational Guardian context exists
* Admissions files are **decision evidence**, not operational records

---

## 2. Semantic ownership (belongs_to)

Admissions documents still carry **semantic meaning**:

* Child‑focused documents
* Guardian‑focused documents

This meaning is stored on **Applicant Document Type**:

```
belongs_to = student | guardian | family
```

This is **never** used for file ownership.

---

## 3. Slot taxonomy for admissions (REQUIRED)

You must define **admissions slots** explicitly.

### Core slots

| Slot                  | Data class     | Retention                 |
| --------------------- | -------------- | ------------------------- |
| `identity_passport`   | legal          | until_school_exit_plus_6m |
| `identity_birth_cert` | legal          | until_school_exit_plus_6m |
| `health_record`       | safeguarding   | until_school_exit_plus_6m |
| `prior_transcript`    | academic       | until_program_end_plus_1y |
| `family_photo`        | administrative | immediate_on_request      |
| `application_form`    | administrative | until_program_end_plus_1y |

Slots allow:

* Partial deletion
* Regulatory separation
* Legal hold where needed

---

## 4. Dispatcher payload (Admissions upload)

Example: passport upload during admission.

```python
create_and_classify_file(
	file_kwargs={
		"attached_to_doctype": "Student Applicant",
		"attached_to_name": applicant.name,
		"is_private": 1,
	},
	classification={
		"primary_subject_type": "Student Applicant",
		"primary_subject_id": applicant.name,
		"data_class": "legal",
		"purpose": "identity_verification",
		"retention_policy": "until_school_exit_plus_6m",
		"slot": "identity_passport",
		"organization": org,
		"school": school,
	}
)
```

---

## 5. Admission rejection scenario (IMPORTANT)

If application is rejected:

### Must be possible

✅ Delete **all files**
✅ Keep only minimal audit (decision + date)
✅ No residual files in backups (future crypto-erase)

### Must NOT happen

❌ Files auto-migrated to Student
❌ Identity docs kept “just in case”
❌ Shared folder leftovers

Your architecture **supports clean rejection**, which most platforms cannot do.

---

## 6. Multi-child family edge cases (handled cleanly)

Example:

* One guardian uploads:

  * Passport for Child A
  * Transcript for Child B

With your model:

* Each file has **one primary subject**
* Guardian is secondary
* Erasure of Child A does not affect Child B

This is **exceptionally hard** to retrofit later — you’re doing it right now.

---

NEW

## Admissions Workflow — File Ownership Clarification

In all admissions workflows, the **primary subject of uploaded files is always the Student Applicant**, regardless of the document’s semantic target.

Examples:
- Student passport → owned by Student Applicant
- Parent ID document → owned by Student Applicant
- Family consent form → owned by Student Applicant

### Important Distinction

Semantic meaning (e.g. “belongs to guardian”) is expressed via:
- document_type
- classification metadata
- internal flags

**Not via file ownership.**

### Invariant

At no point during admissions is a file owned by:
- Student
- Guardian
- Any post-promotion entity

---

# C️⃣ Student Portfolio + Journal (Students Module)

## 1. Portfolio/journal upload governance

All portfolio and journal artefacts are governed files.

Required purposes:

- `portfolio_evidence`
- `journal_attachment`
- `portfolio_export`
- `journal_export`

Required slots:

- `portfolio_artefact`
- `journal_attachment`
- `portfolio_export_pdf`
- `journal_export_pdf`

## 2. Dispatcher payload (portfolio evidence upload)

```python
create_and_classify_file(
	file_kwargs={
		"attached_to_doctype": "Student Portfolio",
		"attached_to_name": portfolio.name,
		"is_private": 1,
	},
	classification={
		"primary_subject_type": "Student",
		"primary_subject_id": student,
		"data_class": "academic",
		"purpose": "portfolio_evidence",
		"retention_policy": "until_school_exit_plus_6m",
		"slot": "portfolio_artefact",
		"organization": org,
		"school": school,
	}
)
```

## 3. Dispatcher payload (portfolio export PDF)

```python
create_and_classify_file(
	file_kwargs={
		"attached_to_doctype": "Student",
		"attached_to_name": student,
		"is_private": 1,
	},
	classification={
		"primary_subject_type": "Student",
		"primary_subject_id": student,
		"data_class": "academic",
		"purpose": "portfolio_export",
		"retention_policy": "immediate_on_request",
		"slot": "portfolio_export_pdf",
		"organization": org,
		"school": school,
	}
)
```

## 4. Portfolio rule

Portfolio items reference evidence sources.

Do not duplicate evidence blobs from Task Submission into portfolio storage.


# 🔎 Final Assessment (blunt)

### Task submissions

✔ Correct ownership
✔ Disposable by design
✔ Analytics-safe
✔ Slot-governed

### Admissions uploads

✔ Correct subject modeling
✔ Guardian/student separation
✔ Rejection-safe
✔ GDPR-credible

### Compared to other SaaS

You are **one full generation ahead** of:

* Moodle
* Google Classroom
* ManageBac
* Toddle
* PowerSchool

They store files.
You govern data.

---
