# Org Communication Attachment Contract

This document defines the canonical governed-file contract for `Org Communication.attachments`.

It closes the previous gap where governed uploads were implemented only for class-event and student-group communications even though `Org Communication` is used across:

* school-to-guardian communication
* school-to-school communication
* admin-to-staff communication
* staff-to-staff communication
* class and student-group communication

## 1. Scope

**Status:** Implemented
**Code refs:** `ifitwala_ed/api/org_communication_attachments.py`, `ifitwala_ed/api/file_access.py`, `ifitwala_ed/setup/doctype/org_communication/attachments.py`, `ifitwala_ed/setup/doctype/org_communication/org_communication.py`, `ifitwala_ed/setup/doctype/org_communication/org_communication.js`, `ifitwala_ed/integrations/drive/org_communications.py`
**Test refs:** `ifitwala_ed/api/test_org_communication_attachments_unit.py`, `ifitwala_ed/setup/doctype/org_communication/test_org_communication.py`, `ifitwala_ed/api/test_file_access.py`

This contract governs:

* governed file uploads into `Org Communication.attachments`
* governed link rows appended into `Org Communication.attachments`
* attachment open/download routing for authorized viewers

This contract does **not** widen inline SPA composer exposure by itself. Surface-specific UI exposure remains owned by the relevant SPA or Desk contract.

## 2. Canonical Ownership

**Status:** Implemented
**Code refs:** `ifitwala_ed/setup/doctype/org_communication/attachments.py`, `ifitwala_ed/setup/doctype/org_communication/org_communication.py`
**Test refs:** `ifitwala_ed/api/test_org_communication_attachments_unit.py`

Rules:

1. The owning business document is always `Org Communication`.
2. Each governed file row uses one deterministic slot: `communication_attachment__<row_name>`.
3. The primary governed subject remains the communication organization:
   * `primary_subject_type = Organization`
   * `primary_subject_id = Org Communication.organization`
4. `school` classification is optional and is present only when the communication resolves to a school-scoped attachment context.
5. Files remain `administrative` data with `administrative` purpose and `fixed_7y` retention unless a future approved contract states otherwise.

## 3. Attachment Context Resolution

**Status:** Implemented
**Code refs:** `ifitwala_ed/setup/doctype/org_communication/attachments.py`
**Test refs:** `ifitwala_ed/api/test_org_communication_attachments_unit.py`, `ifitwala_ed/setup/doctype/org_communication/test_org_communication.py`

The server resolves one authoritative attachment context per communication using this precedence:

1. **Student-group context**
   * Use `activity_student_group` when present.
   * Otherwise use the first `Student Group` audience row with a populated `student_group`.
   * This context requires authoritative `Student Group.course` and `Student Group.school`.
2. **School context**
   * Use `Org Communication.school` when present.
   * Otherwise, if there is exactly one `School Scope` audience school, use that school.
   * Otherwise, if there is exactly one `Team` audience row and that team has a school, use the team school.
3. **Organization context**
   * If neither student-group nor school context resolves, governed attachments are still allowed as long as the communication organization is present.

Rules:

1. Attachments must no longer require a `Student Group` audience by default.
2. Multi-school fan-out communications without one authoritative school anchor remain organization-scoped for attachment governance.
3. Team communications may resolve to school scope when the authoritative `Team.school` exists; otherwise they remain organization-scoped.
4. Partial class context must fail closed. If a communication resolves `student_group` context without authoritative `course` and `school`, upload must be rejected with an explicit validation error instead of falling through to school or organization folder routing.
5. Missing `organization` is a blocker and must be explained as such in the UI.
6. After the first governed file exists, changing the authoritative attachment context is blocked until governed file rows are removed. This protects Drive governance from post-upload scope drift.

## 4. Storage Boundary

**Status:** Implemented
**Code refs:** `ifitwala_ed/setup/doctype/org_communication/attachments.py`, `ifitwala_ed/integrations/drive/org_communications.py`, `ifitwala_drive/services/folders/resolution.py`, `ifitwala_drive/services/integration/ifitwala_ed_org_communications.py`
**Test refs:** `ifitwala_ed/api/test_org_communication_attachments_unit.py`, `ifitwala_drive/tests/test_org_communication_attachment_upload_flow.py`

Governed folder placement is determined by the resolved attachment context:

1. **Student-group context**
   * `root_folder = Home/Courses`
   * `subfolder = <course>/Communications/<student_group>/<org_communication>/Attachments`
   * `file_category = Class Communication Attachment`
2. **School context**
   * `root_folder = Home/Organizations`
   * `subfolder = <organization>/Schools/<school>/Communications/<org_communication>/Attachments`
   * `file_category = School Communication Attachment`
3. **Organization context**
   * `root_folder = Home/Organizations`
   * `subfolder = <organization>/Communications/<org_communication>/Attachments`
   * `file_category = Organization Communication Attachment`

Rules:

1. The UI must not guess any attachment path.
2. The upload/finalize session must be revalidated against the authoritative communication context before file finalization.
3. Class-event communication keeps its existing course/student-group placement; the broader contract adds school and organization context rather than replacing governance with raw attachments.
4. Post-finalize preview/derivative scheduling remains Drive-owned deferred enrichment and must enqueue onto a runtime-valid worker queue. Drive may keep semantic queue classes internally, but org communication uploads must not fail because a semantic queue label was sent directly into Frappe without runtime validation or fallback.

## 5. UX and Mutation Rules

**Status:** Implemented
**Code refs:** `ifitwala_ed/api/org_communication_attachments.py`, `ifitwala_ed/setup/doctype/org_communication/org_communication.js`
**Test refs:** `ifitwala_ed/api/test_org_communication_attachments_unit.py`

Rules:

1. Governed file uploads use only `ifitwala_ed.api.org_communication_attachments.upload_org_communication_attachment`.
2. External links use only `ifitwala_ed.api.org_communication_attachments.add_org_communication_link`.
3. Removal uses only `ifitwala_ed.api.org_communication_attachments.remove_org_communication_attachment`.
4. Desk must save dirty communications before opening the governed uploader so the server resolves attachment context from persisted state.
5. Desk must not claim that student-group, school, or organization routing locally. The server is the only authority for attachment context resolution.
6. Raw Desk `Attach` remains non-canonical and is still rejected by controller validation for file rows.

## 6. Visibility and Attachment Action URL Contract

**Status:** Implemented
**Code refs:** `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/org_communication_archive.py`, `ifitwala_ed/api/org_comm_utils.py`
**Test refs:** `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/api/test_org_communication_archive.py`

Rules:

1. Attachment reads must continue to enforce the same communication visibility contract as archive/detail reads.
2. Authorized viewers receive server-owned action URLs only.
3. File rows expose stable Ed-owned `open_url` values, stable Ed-owned `preview_url` values for richer preview flows, optional stable Ed-owned `thumbnail_url` values for inline image cards only when a ready `thumb` derivative exists, a `preview_status` hint so SPA surfaces know when the preview route resolves a renderable preview asset instead of the original file, and an additive nested `attachment_preview` block carrying the shared cross-surface preview DTO.
4. Those stable routes are not durable storage URLs; Drive grants remain short-lived and are resolved at request time.
5. Private file URLs must never be constructed in the client.
6. Authored-history owner access remains aligned with the existing `allow_owner=True` attachment-open rule.
7. Archive/detail surfaces must prefer `thumbnail_url` for inline image cards. If the thumbnail is missing but `preview_status` is `ready`, the surface may use `preview_url` as an inline fallback because that route resolves a governed preview derivative rather than the original file. If neither is available, the surface must fall back to an action-led card.
8. Thumbnail routes may use short-lived Ed-side redirect caching plus private browser cache headers, but the SPA still receives only stable Ed-owned action URLs rather than provider grants.
9. External links and non-ready PDFs must still degrade to action-led metadata cards instead of blank embeds or raw-path guesses.
10. Open and preview routes must not require a secondary `File` row lookup when a safe Drive grant URL is already resolved; `File` fallback exists only for inline streaming when the resolved target is a raw private path or no safe redirect target exists. Thumbnail routes for Org Communication must fail closed when no safe `thumb` derivative grant exists and must never stream or redirect to the original file.
