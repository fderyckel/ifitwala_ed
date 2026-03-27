# 📦 PR TITLE

**GDPR-Compliant File Governance & Dispatcher Enforcement (Phases 1–3)**

---

# 🎯 PR OBJECTIVE (NON-NEGOTIABLE)

Implement the locked **Files & Documents Architecture** by:

1. Introducing a **system-wide File Classification governance layer**
2. Enforcing **dispatcher-only file finalization**
3. Refactoring file routing to **require explicit governance**
4. Preparing task uploads for **file / grade separation**

Any code that bypasses these rules is a **bug**, not a feature.

---

# Organization Media Extension (Docs-First Guardrail)

Before implementing reusable website / branding / gallery media uploads for organizations or schools, follow:

* `ifitwala_ed/docs/files_and_policies/files_05_organization_media_governance.md`

Current implementation gap:

* the dispatcher exists
* governed uploads exist for person/applicant-centered flows
* organization-owned public media classification now exists for organization logo, school logo, school gallery, and generic organization media uploads
* reuse-first organization media pickers now exist for school-context website block props and `Program Website Profile.hero_image`
* a generic organization media management surface now exists from `Organization` and `School` Desk forms
* legacy URL-only school/organization public media is no longer accepted and must be relinked or re-uploaded through governed organization media

## Runtime boundary with Ifitwala Drive

The file-governance architecture is not fully local to `ifitwala_ed`.
Current runtime is split deliberately:

* `ifitwala_ed` owns workflow context, permission checks, tenant scope, subject resolution, and which business record a file belongs to.
* `ifitwala_drive` owns Drive upload sessions, temporary object handling, finalize flow, and the governed storage boundary for the Drive-backed upload paths.

Current Drive-backed paths in production code include:

* admissions document and portal image uploads via `ifitwala_ed/admission/admissions_portal.py` -> `ifitwala_drive.api.admissions.*`
* task submission attachments via `ifitwala_ed/utilities/governed_uploads.py::upload_task_submission_attachment` -> `ifitwala_drive.api.submissions.upload_task_submission_artifact`
* task resource uploads via `ifitwala_ed/utilities/governed_uploads.py::upload_task_resource` -> `ifitwala_drive.api.resources.upload_task_resource`
* employee/student/school/organization media flows via `ifitwala_ed/utilities/governed_uploads.py` -> `ifitwala_drive.api.media.*`

Current direct-dispatcher path still present in production code:

* Desk applicant profile image upload via `ifitwala_ed/utilities/governed_uploads.py::upload_applicant_image` -> `ifitwala_ed.utilities.file_dispatcher.create_and_classify_file(...)`

Implication:

* `ifitwala_drive` is now an application dependency of `ifitwala_ed`, not an optional companion app, because multiple live upload paths import Drive modules directly and fail closed when Drive is missing.
* Any new governed upload path that crosses from `ifitwala_ed` into `ifitwala_drive` is a cross-app change set, not a local feature edit.

Cross-app wrapper contract:

* if `ifitwala_ed` calls a new `ifitwala_drive.api.*` method, that Drive wrapper must be exported in the deployed Drive app at the same time
* the thin API wrapper and the underlying `ifitwala_drive.services.integration.ifitwala_ed_media.*` service must both exist
* browser refresh, browser cache clear, and `bench clear-cache` do **not** reload Python imports for this contract
* deployment is incomplete until app processes are restarted and the imported module surface matches the code on disk

Mandatory deployment verification for new Drive-backed upload wrappers:

* deploy both `ifitwala_ed` and `ifitwala_drive` together
* restart the web and worker processes after deploy
* verify from `bench --site <site> console`:
  * `import ifitwala_drive.api.media as m; hasattr(m, "<method_name>")`
  * `import ifitwala_drive.services.integration.ifitwala_ed_media as i; hasattr(i, "<method_name>_service")`
  * confirm `m.__file__` and `i.__file__` point to the intended checkout
* add a regression test on the Ed side that resolves the correct Drive callable
* add a regression test on the Drive side that the exported wrapper delegates to the intended service

Cross-app MIME handoff rule:

Status:

* Implemented

Code refs:

* `ifitwala_ed/utilities/governed_uploads.py::_resolve_upload_mime_type_hint`
* `ifitwala_ed/utilities/governed_uploads.py::upload_student_image`
* `ifitwala_ed/utilities/governed_uploads.py::upload_employee_image`
* `ifitwala_ed/utilities/governed_uploads.py::upload_guardian_image`
* `ifitwala_ed/utilities/governed_uploads.py::upload_task_resource`
* `ifitwala_ed/utilities/governed_uploads.py::upload_task_submission_attachment`
* `ifitwala_ed/admission/admissions_portal.py::upload_applicant_document`
* `ifitwala_ed/admission/admissions_portal.py::upload_applicant_profile_image`

Test refs:

* `ifitwala_ed/utilities/test_governed_uploads_task_flows.py`
* `ifitwala_ed/admission/test_admissions_portal_uploads_unit.py`

Rule:

* `ifitwala_ed` owns `mime_type_hint` derivation for Drive-backed wrappers
* derive the hint from the uploaded file object when available
* if no file-object MIME is available, fall back to the filename
* never forward `frappe.request.mimetype` or the outer request `Content-Type` from `/api/method/upload_file` as `mime_type_hint`
* `multipart/form-data` is a transport-envelope value, not a governed file MIME
* if Ed forwards the envelope MIME, Drive finalize is expected to fail closed on mismatch

This rule applies to both Desk and admissions flows.

Therefore:

* do **not** add new direct `Attach`-based media workflows for school/website imagery
* do **not** introduce school-local media governance as a parallel system
* do **not** hardcode filesystem assumptions into media pickers, renderers, or website blocks

---

# 🧭 EXECUTION PHASES (LOCKED ORDER)

Codex must implement **in this exact order**:

---

## 🔹 PHASE 1 — File Classification (NEW GOVERNANCE LAYER)

### 1.1 Create new Doctype: `File Classification`

**Type:** Standard
**Cardinality:** Exactly 1 per `File`
**Module:** Setup or Utilities (not domain-specific)

#### Required fields

```text
file (Link → File) [unique, required]

attached_doctype (Data)
attached_name (Data)

primary_subject_type (Select: Student | Guardian | Employee | Student Applicant) [required]
primary_subject_id (Dynamic Link) [required]

data_class (Select) [required]
purpose (Select: identification_document | contract | assessment_submission | ... ) [required]

retention_policy (Select) [required]
retention_until (Date) [computed later]

slot (Data) [required]

organization (Link → Organization) [required]
school (Link → School) [required unless org‑level Employee]

legal_hold (Check, default 0)
erasure_state (Select: active | pending | blocked_legal | erased, default active)

version_number (Int)
is_current_version (Check)

content_hash (Data) [SHA-256]
source_file (Link → File) [optional]
upload_source (Select: Desk | SPA | API | Job)
ip_address (Data)
```

#### Child table: `File Classification Subject`

```text
subject_type (Select)
subject_id (Dynamic Link)
role (Select: co-owner | referenced | contextual)
```

#### Hard invariants (must be enforced in Python)

* `file` must be unique
* A `File` **must not** be finalized without a classification
* Secondary subjects **never** override primary subject
* `erasure_state != active` blocks writes

---

### 1.2 Production-safe migration (MANDATORY)

Codex must add a **non-destructive migration**:

* Existing `File` rows remain untouched
* No retroactive classification required
* System must tolerate **legacy unclassified files** temporarily

⚠️ Do **NOT** auto-classify legacy files.
That is a later, manual governance operation.

---

## 🔹 PHASE 2 — Dispatcher-Only Upload Enforcement (CRITICAL)

### 2.1 Enforce HARD GATE in `route_uploaded_file`

Modify:

```
ifitwala_ed/utilities/file_management.py
```

#### At the very top of `route_uploaded_file(...)`, add:

```python
# ── HARD GDPR GATE ──────────────────────────────────────────────
if not frappe.db.exists(
	"File Classification",
	{"file": doc.name}
):
	# File exists but has no governance.
	# Do NOT route, version, rename, or finalize.
	return
```

This is **mandatory**.

➡️ Result:

* Ungoverned files stay inert
* No routing, no versioning, no final path
* Dispatcher becomes the single gateway

---

### 2.2 Make hooks explicitly “dumb”

Update docstrings in:

```
ifitwala_ed/utilities/file_dispatcher.py
```

Clarify:

```python
"""
Legacy safety-net hooks.

All governed uploads MUST go through the dispatcher API.
This hook only finalizes files that already have File Classification.
"""
```

🚫 **Do NOT** add governance logic to hooks
🚫 **Do NOT** infer data_class, subject, or retention here

---

### 2.3 Introduce dispatcher API (NEW)

Add in `file_dispatcher.py`:

```python
def create_and_classify_file(
	*,
	file_kwargs: dict,
	classification: dict,
	secondary_subjects: list | None = None,
	context_override: dict | None = None,
) -> frappe.model.document.Document:
	"""
	The ONLY supported entry point for governed file uploads.
	Creates File + File Classification atomically.
	"""
```

Responsibilities:

1. Validate **all mandatory classification fields**
2. Calculate `content_hash` (SHA-256) and capture `ip_address` / `upload_source`
3. Create `File`
4. Create `File Classification`
4. Commit both
5. Finalize routing/versioning after classification (dispatcher-owned)

Missing governance → hard error.

---

### 2.4 Explicitly forbid direct `File.insert()` in business logic

Add a comment + grep-guard in code review notes:

> Any new `File.insert()` outside dispatcher is an architectural violation.

---

## 🔹 PHASE 3 — Refactor for Task / Grade Separation (SAFE REFACTOR)

⚠️ **NO functional change yet**, only structural separation.

### 3.1 Audit Task / Submission flows

Codex must identify:

* Where files are uploaded for:

  * Task Submission
  * Student Portfolio
* Where grades / scores / analytics are stored

### 3.2 Enforce separation

Rules:

* Grades, scores, completion status → **permanent**
* Files → **disposable**

Codex must ensure:

* Deleting all files for a student:

  * Does NOT break grades
  * Does NOT break analytics
* Task Submission Doctype does **not** depend on file existence

No UI changes required in this PR.

---

## 🧪 ACCEPTANCE CRITERIA (ALL MUST PASS)

### Phase 1

✅ `File Classification` exists
✅ 1-to-1 enforced with `File`
✅ Supports primary + secondary subjects

### Phase 2

✅ Ungoverned files do not move
✅ No routing without classification
✅ Dispatcher is the only valid entry

### Phase 3

✅ Task grades survive file deletion
✅ File logic is fully disposable

---

## 🚫 EXPLICITLY FORBIDDEN IN THIS PR

* Auto-classifying legacy files
* Adding ACLs to File
* UI file browsers
* Folder pickers
* Background cleanup jobs
* Crypto-erase implementation
* Any change to retention semantics

---

## 🧠 CODING STYLE & SAFETY RULES

* No breaking migrations
* No data deletion
* No implicit inference of GDPR fields
* All failures must be **hard and explicit**
* Prefer refusal over guesswork

---

# 1️⃣ Dispatcher Function Code (AUTHORITATIVE)

This is the **only supported entry point** for governed file uploads.

👉 Place this in
`ifitwala_ed/utilities/file_dispatcher.py`

---

## Dispatcher API: `create_and_classify_file`

```python
# ifitwala_ed/utilities/file_dispatcher.py

from __future__ import annotations
from typing import Dict, Any, List, Optional

import frappe
from frappe import _
from frappe.model.document import Document
from ifitwala_ed.utilities import file_management


REQUIRED_CLASSIFICATION_FIELDS = {
	"primary_subject_type",
	"primary_subject_id",
	"data_class",
	"purpose",
	"retention_policy",
	"slot",
	"organization",
	"school",
}


@frappe.whitelist()
def create_and_classify_file(
	*,
	file_kwargs: Dict[str, Any],
	classification: Dict[str, Any],
	secondary_subjects: Optional[List[Dict[str, Any]]] = None,
	context_override: Optional[Dict[str, Any]] = None,
) -> Document:
	"""
	Authoritative dispatcher entry point for ALL governed file uploads.

	Creates:
	1) File
	2) File Classification (1:1)

	Then finalizes routing/versioning after classification.

	This function MUST be used by:
	- Desk
	- SPA
	- Web Forms
	- Background jobs
	- Imports
	"""

	# ─────────────────────────────────────────────────────────────
	# 1. Validate classification payload (FAIL CLOSED)
	# ─────────────────────────────────────────────────────────────

	missing = REQUIRED_CLASSIFICATION_FIELDS - set(classification.keys())
	if "school" in missing and classification.get("primary_subject_type") == "Employee":
		missing.remove("school")
	if missing:
		frappe.throw(
			_("Missing mandatory file classification fields: {0}")
			.format(", ".join(sorted(missing)))
		)

	# Validate subject type early
	if classification["primary_subject_type"] not in ("Student", "Guardian", "Employee", "Student Applicant"):
		frappe.throw(_("Invalid primary_subject_type"))

	# ─────────────────────────────────────────────────────────────
	# 2. Create File (UNFINALIZED)
	# ─────────────────────────────────────────────────────────────

	file_doc = frappe.get_doc({
		"doctype": "File",
		**file_kwargs,
	})

	file_doc.insert(ignore_permissions=True)

	# ─────────────────────────────────────────────────────────────
	# 3. Create File Classification (ATOMIC GOVERNANCE)
	# ─────────────────────────────────────────────────────────────

	fc = frappe.get_doc({
		"doctype": "File Classification",
		"file": file_doc.name,
		"attached_doctype": file_doc.attached_to_doctype,
		"attached_name": file_doc.attached_to_name,

		"primary_subject_type": classification["primary_subject_type"],
		"primary_subject_id": classification["primary_subject_id"],

		"data_class": classification["data_class"],
		"purpose": classification["purpose"],
		"retention_policy": classification["retention_policy"],

		"slot": classification["slot"],

		"organization": classification["organization"],
		"school": classification.get("school"),

		"legal_hold": 0,
		"erasure_state": "active",

		"content_hash": file_management.calculate_hash(file_doc),  # New helper
		"source_file": classification.get("source_file"),
		"upload_source": classification.get("upload_source", "API"),
		"ip_address": frappe.local.request_ip if frappe.request else None,
	})

	fc.insert(ignore_permissions=True)

	# ─────────────────────────────────────────────────────────────
	# 4. Secondary subjects (OPTIONAL)
	# ─────────────────────────────────────────────────────────────

	if secondary_subjects:
		for subj in secondary_subjects:
			if not subj.get("subject_type") or not subj.get("subject_id"):
				frappe.throw(_("Secondary subject entries must include subject_type and subject_id"))

			fc.append("secondary_subjects", {
				"subject_type": subj["subject_type"],
				"subject_id": subj["subject_id"],
				"role": subj.get("role", "referenced"),
			})

		fc.save(ignore_permissions=True)

	# ─────────────────────────────────────────────────────────────
	# 5. Finalize routing/versioning (classification already exists)
	# ─────────────────────────────────────────────────────────────

	file_management.route_uploaded_file(
		file_doc,
		method="dispatcher",
		context_override=context_override,
	)

	# ─────────────────────────────────────────────────────────────
	# 6. Return File
	# ─────────────────────────────────────────────────────────────

	return file_doc
```

---


---

## 🔒 GUARANTEES THIS FUNCTION PROVIDES

Once this is merged:

* ❌ No file can be routed without governance
* ❌ No file can exist “meaningfully” without classification
* ✅ Hooks only finalize governed files
* ✅ GDPR invariants are enforceable
* ✅ All future erasure logic has a clean anchor

This function becomes **institutional law**.

---

## Desk governed uploads (fresh install)

Desk forms MUST NOT use the generic Attach/Attach Image uploader for governed files.
Instead, each doctype exposes a **named, whitelisted upload method** that:

1) reads the uploaded file
2) derives the file MIME from the uploaded file object or filename, never from the multipart request envelope
3) calls the authoritative governed upload boundary (`create_and_classify_file(...)` directly or the Drive session/finalize wrapper)
4) updates the owning document field / attachment table

Current governed Desk endpoints:

* `upload_employee_image(employee)`
* `upload_guardian_image(guardian)`
* `upload_student_image(student)`
* `upload_applicant_image(student_applicant)`
* `upload_task_resource(task)`
* `upload_task_submission_attachment(task_submission)`

These are the only allowed upload entry points for:

* Guardian `guardian_image`
* Employee `employee_image`
* Student `student_image`
* Student Applicant `applicant_image`
* Task `attachments` file rows
* Task Submission attachments

Server-side enforcement:

* Any `File` attached to the doctypes above that was **not** created by the dispatcher
  is rejected during `File.validate`.
* Any new `Task.attachments.file` value without a matching governed `Drive Binding` is rejected during `Task.validate`.
* This blocks sidebar uploads and prevents silent unclassified files.

---

## Governed derivative images (Employee only)

Employee profile images must generate **governed derivatives** for UI use.

### Sizes (locked)

* `thumb` (160px) → avatar / profile pic
* `card` (400px) → staff listing / website card
* `medium` (960px) → internal display where more detail is needed

### Governance rules

Each derivative is a **real File + File Classification** with:

* `source_file` = original profile image File
* Same `primary_subject_*`, `data_class`, `purpose`, `retention_policy`, `organization`, `school`
* **Slot naming**: `profile_image_thumb`, `profile_image_card`, `profile_image_medium`
* `upload_source` inherited from the original upload

### Creation flow (authoritative)

1) Original profile image is created via dispatcher
2) Classification is created (slot = `profile_image`)
3) Derivatives are generated **after classification**
4) Each derivative is created via dispatcher and classified

### Invariants

* No derivative may exist without classification
* Derivative generation is **idempotent** per source file
* Employee derivatives are limited to the three sizes above (no hero)

---

## Student image privacy (consent-gated)

Student profile images are **private by default**.

Public exposure is allowed **only** when the applicant has acknowledged the media consent policy:

* `policy_key = media_consent`
* `acknowledged_for = Applicant`
* `context_doctype = Student Applicant`

Promotion may **copy** `Student Applicant.applicant_image` into `Student.student_image`
as a new File record. The public version (if consented) must use a randomized suffix.

When Student profile images are governed uploads, derivative generation follows the same
post-classification rule as Employee profile images:

* canonical derivative slots: `profile_image_thumb`, `profile_image_card`, `profile_image_medium`
* derivatives are generated from the current governed original after classification
* Student list/avatar consumers must resolve these governed variants canonically and must not guess legacy `gallery_resized/student` URLs

**Operational activation**

1) Create an **Institutional Policy** with `policy_key = media_consent`
2) Add an **active Policy Version** with the consent text
3) Ensure the Admissions Applicant acknowledges it via the admissions flow

# 2️⃣ SECOND PR BRIEF — Phase 4: GDPR Erasure Workflow

This is the **next PR**, not mixed with the above.

You can hand this directly to Codex.

---

## 📦 PR TITLE

**GDPR Data Erasure Workflow (File-Level, Deterministic)**

---

## 🎯 PR OBJECTIVE

Implement a **formal, auditable, deterministic GDPR erasure workflow** for file data in Ifitwala_Ed.

This PR must allow the system to:

* Identify all files belonging to a data subject
* Determine deletability
* Delete physical files safely
* Preserve minimal audit proof
* Never break academic integrity

---

## 🔒 SCOPE (STRICT)

This PR applies **ONLY** to files and file classifications.

It does **NOT**:

* Delete business documents (Student, Task, Grade)
* Touch analytics
* Implement crypto-erase
* Modify retention semantics

---

## 🧱 NEW DOCTYPE — `Data Erasure Request`

**Type:** Standard
**Module:** Setup / Compliance

### Core fields

| Field               | Type                                                              |
| ------------------- | ----------------------------------------------------------------- |
| `data_subject_type` | Select                                                            |
| `data_subject_id`   | Dynamic Link                                                      |
| `requested_by`      | Link → User                                                       |
| `request_reason`    | Select                                                            |
| `scope`             | Select (`all`, `files_only`)                                      |
| `status`            | Select (`draft`, `approved`, `executing`, `completed`, `blocked`) |
| `executed_on`       | Datetime                                                          |

---

## 🔁 ERASURE EXECUTION LOGIC

### Step 1 — Resolve candidate files

Query `File Classification` where:

* `primary_subject_type = X`
* `primary_subject_id = Y`
* `erasure_state = active`

---

### Step 2 — Check blockers

For each classification:

* If `legal_hold = 1` → BLOCK
* If `data_class = legal` → BLOCK (v1 rule)
* If retention not expired → ALLOW ONLY IF `immediate_on_request`

Blocked files must be reported, not deleted.

---

### Step 3 — Execute deletion

For each allowed file:

1. Delete physical file (`file_url`)
2. Delete `File` row
3. Update `File Classification`:

   * `erasure_state = erased`

⚠️ **Order matters**.
Classification is never deleted.

---

### Step 4 — Minimal audit trail

Store ONLY:

* Subject type
* Subject ID
* Timestamp
* Count of files deleted
* Count of files blocked

🚫 Do NOT store:

* File names
* Paths
* Content
* Versions

---

## 🧪 ACCEPTANCE CRITERIA

✅ Can erase **all student files** without touching grades
✅ Can erase **task submissions only**
✅ Legal hold blocks deletion
✅ System remains queryable post-erasure
✅ Audit contains no personal content

---

## 🚫 FORBIDDEN

* Soft deletes
* Archiving instead of deletion
* File name retention
* Reversible erasure
* Background auto-cleanup (future PR)

---

## 🧠 CODING RULE

> **If deletion cannot be proven, it must not occur.**

Fail closed. Log clearly.

---

# ✅ WHERE WE ARE NOW

With what you just asked for, you now have:

* ✔️ Locked architecture
* ✔️ Dispatcher enforcement
* ✔️ Authoritative upload API
* ✔️ Clean path to GDPR erasure
* ✔️ Zero architectural debt

This is **enterprise-grade**, not “edtech-grade”.

---


NEW

---

## 1️⃣ Admissions uploads

**Where are Applicant Document files uploaded today?**

### Short answer (truthful)

There is **no single authoritative upload API** today.
Admissions uploads are currently fragmented and **implicitly rely on `File.insert()` via UI or generic attachment behavior**.

That is **exactly the problem Phase 2 is meant to fix**.

### Decision (LOCKED)

👉 **Codex MUST introduce a new whitelisted dispatcher-backed upload method for admissions.**

There is no safe legacy endpoint to reuse.

### What Codex should do

Add a new whitelisted method, e.g.:

```
ifitwala_ed.api.admissions_portal.upload_applicant_document
```

This method must:

* Accept raw file content or multipart upload
* Call `create_and_classify_file(...)`
* Attach to **Student Applicant** (or Applicant Document if already created)
* Reject uploads that bypass classification

### Explicit instruction

❌ Do not try to “discover” an existing endpoint
❌ Do not rely on Desk attachment behavior
✅ Add a new governed API and migrate callers gradually

This is **intended**, not a regression.

---

## 2️⃣ Admissions slot mapping

**How to derive slot deterministically?**

You are right: today there is **no deterministic slot source**.
We must introduce one now.

### Decision (LOCKED)

👉 **Slot is derived from `Applicant Document Type.code`**

Not label. Not free text. **Code only.**

### Required mapping rule (v1)

| Applicant Document Type.code | Slot                  |
| ---------------------------- | --------------------- |
| `passport`                   | `identity_passport`   |
| `id_documents`               | `identity_passport`   |
| `birth_certificate`          | `identity_birth_cert` |
| `health_record`              | `health_record`       |
| `transcript`                 | `prior_transcript`    |
| `transcripts`                | `prior_transcript`    |
| `report_card`                | `prior_transcript`    |
| `photo`                      | `family_photo`        |
| `application_form`           | `application_form`    |

For `Applicant Health Profile` vaccination proof uploads (not `Applicant Document`), use deterministic slot prefix:

* `health_vaccination_proof_<vaccine-and-date-key>`

### Enforcement rule

* If `Applicant Document Type.code` is missing or unmapped → **reject upload**
* Codex must add a **hard mapping dict**, not inference

### Why this is correct

* Deterministic
* Versionable
* Auditable
* Future-proof (new types = explicit decision)

---

## 3️⃣ Task Submission attachments

**What is the payload shape today?**

### Current reality (important)

Task submissions today typically involve one of:

* A `File` created via Desk attachment
* A `file_url` reference stored on a child row
* Sometimes raw file upload via form POST

This is inconsistent.

### Decision (LOCKED)

👉 **Phase 3 refactor standardizes Task Submission uploads to raw file content → dispatcher only.**

### Canonical payload going forward

All task submission uploads must call:

```python
create_and_classify_file(
	file_kwargs={
		"attached_to_doctype": "Task Submission",
		"attached_to_name": submission.name,
		"is_private": 1,
		"content": <raw file bytes or uploaded file>,
		"file_name": <original filename>,
	},
	classification={...}
)
```

### Explicit rules for Codex

* ❌ Do not accept pre-created `File` names
* ❌ Do not accept bare `file_url`
* ✅ Always create File inside dispatcher

Legacy flows may temporarily break routing — that is acceptable (see Q5).

---

## 4️⃣ Employee documents

**Where are contracts / resumes stored today?**

### Current state (honest)

You are correct:

* Only `employee_image` exists on `Employee`
* There is **no canonical Employee Document Doctype** yet

### Decision (LOCKED)

👉 **Employee documents are OUT OF SCOPE for Phase 3 enforcement.**

But we still prepare the architecture.

### What Codex should do now

* Do **not** attempt to refactor Employee uploads
* Do **not** add guesses for contract/resume storage
* Leave Employee flows untouched for now

### What is planned (later phase)

A future `Employee Document` Doctype using:

* Same dispatcher
* Same classification
* Primary subject = staff

Codex should not invent this now.

---

## 5️⃣ Module placement

**Where should new DocTypes live?**

### Decision (LOCKED)

| Item                          | Module     |
| ----------------------------- | ---------- |
| `File Classification`         | **Setup**  |
| `File Classification Subject` | Setup      |
| `Data Erasure Request`        | Setup      |
| Dispatcher utilities          | Utilities  |
| Admissions upload API         | Admissions |

### Why

* Governance objects belong to Setup
* Utilities stay non-domain
* Admissions API stays close to business flow

No ambiguity here.

---

## 6️⃣ Enforcement risk confirmation

**Are we OK with uploads breaking once hard gate is enabled?**

### Clear answer

👉 **YES. Explicitly YES.**

This is **intentional and desired**.

### Rationale

* Ungoverned uploads are a **liability**
* Silent misclassification is worse than rejection
* We prefer:

  * Temporary friction
  * Explicit failures
  * Clear TODO list

### Codex instruction

* Add hard gate
* Document known broken flows
* Do NOT add fallbacks
* Do NOT weaken enforcement

---

# ✅ FINAL GO-AHEAD TO CODEX (YOU CAN COPY THIS)

> You are cleared to proceed.
>
> Decisions are locked as follows:
>
> * Admissions uploads: add a new dispatcher-backed whitelisted API
> * Slot derivation: `Applicant Document Type.code → slot` (hard mapping)
> * Task submissions: raw file → dispatcher only (no legacy File reuse)
> * Employee documents: explicitly out of scope for this PR
> * New DocTypes live under Setup
> * Hard gate enforcement is intentional even if some flows temporarily break
>
> Do not infer. Do not soften enforcement. Fail closed.

---
