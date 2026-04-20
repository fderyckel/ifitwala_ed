# Ifitwala_Drive Usage For Admissions Portal Uploads

## Purpose

This note defines how `ifitwala_ed` should use `ifitwala_drive` for admissions-portal uploads.

The core rule is simple:

* the SPA must call `ifitwala_ed` admissions endpoints
* `ifitwala_ed` must call workflow-aware `ifitwala_drive` endpoints
* no new governed admissions upload should create, route, or finalize files through Ed-local file helpers from portal-facing business logic

This keeps `ifitwala_ed` as workflow authority and `ifitwala_drive` as governed file authority.

---

## Layering Rule

Preferred stack for admissions uploads:

1. SPA calls `ifitwala_ed.api.admissions_portal.*`
2. `ifitwala_ed.api.admissions_portal` validates applicant access and workflow state
3. `ifitwala_ed.admission.admissions_portal` calls a workflow-aware `ifitwala_drive.api.admissions.*` or `ifitwala_drive.api.media.*` endpoint
4. `ifitwala_drive` creates a `Drive Upload Session`
5. `ifitwala_drive` finalizes natively and writes the authoritative governed-file metadata

Avoid:

* SPA calling `ifitwala_drive` directly
* admissions portal methods calling generic `ifitwala_drive.api.uploads.create_upload_session` directly
* admissions portal methods writing files through retired Ed-local file creation/routing helpers

The generic `ifitwala_drive.api.uploads.*` endpoints are infrastructure-level upload lifecycle endpoints. Admissions portal flows should normally use workflow-aware wrappers instead.

---

## Current Admissions Portal Upload Inventory

### 1. Applicant document upload

Status:

* Drive-backed

Current portal entrypoint:

* `ifitwala_ed.api.admissions_portal.upload_applicant_document`

Current workflow path:

* SPA -> `ifitwala_ed.api.admissions_portal.upload_applicant_document`
* Ed -> `ifitwala_ed.admission.admissions_portal.upload_applicant_document`
* Drive -> `ifitwala_drive.api.admissions.upload_applicant_document`
* Drive session + finalize -> authoritative governed file creation

Notes:

* this is the correct pattern
* scope, slot, purpose, retention, organization, and school are resolved server-side

### 2. Applicant health vaccination proof upload

Status:

* Drive-backed

Current portal entrypoint:

* `ifitwala_ed.api.admissions_portal.update_applicant_health`

Current workflow path:

* SPA sends vaccination proof payload inside `update_applicant_health`
* Ed helper -> `ifitwala_ed.admission.admissions_portal.upload_applicant_health_vaccination_proof`
* Drive -> `ifitwala_drive.api.admissions.upload_applicant_health_vaccination_proof`
* Drive session + finalize -> authoritative governed file creation

Notes:

* deterministic slot contract remains `health_vaccination_proof_<key>`
* this now follows the correct Drive boundary

### 3. Applicant profile image upload

Status:

* Drive-backed

Current portal entrypoint:

* `ifitwala_ed.api.admissions_portal.upload_applicant_profile_image`

Current workflow path:

* SPA -> `ifitwala_ed.api.admissions_portal.upload_applicant_profile_image`
* Ed -> `ifitwala_ed.admission.admissions_portal.upload_applicant_profile_image`
* Drive -> `ifitwala_drive.api.admissions.upload_applicant_profile_image`
* Drive session + finalize -> authoritative governed file creation

Notes:

* `Student Applicant.applicant_image` is updated during Drive post-finalize

### 4. Applicant guardian image upload

Status:

* Drive-backed

Current portal entrypoint:

* `ifitwala_ed.api.admissions_portal.upload_applicant_guardian_image`

Current workflow path:

* SPA -> `ifitwala_ed.api.admissions_portal.upload_applicant_guardian_image`
* Ed -> `ifitwala_ed.admission.admissions_portal.upload_applicant_guardian_image`
* Drive -> `ifitwala_drive.api.admissions.upload_applicant_guardian_image`
* Drive session + finalize -> authoritative governed file creation

Notes:

* guardian image slot is row-aware: `guardian_profile_image__<guardian-row-key>`
* the upload requires a saved guardian row identity
* the current SPA rule is: save a new guardian row first, then upload its image

---

## Relevant Drive Endpoints

Workflow-aware endpoints currently available:

* `ifitwala_drive.api.admissions.upload_applicant_document`
* `ifitwala_drive.api.admissions.upload_applicant_profile_image`
* `ifitwala_drive.api.admissions.upload_applicant_guardian_image`
* `ifitwala_drive.api.admissions.upload_applicant_health_vaccination_proof`
* `ifitwala_drive.api.media.upload_student_image`
* `ifitwala_drive.api.media.upload_guardian_image`
* `ifitwala_drive.api.media.upload_employee_image`
* `ifitwala_drive.api.media.upload_organization_logo`
* `ifitwala_drive.api.media.upload_school_logo`
* `ifitwala_drive.api.media.upload_school_gallery_image`
* `ifitwala_drive.api.media.upload_organization_media_asset`
* `ifitwala_drive.api.submissions.upload_task_submission_artifact`

Infrastructure-level lifecycle endpoints:

* `ifitwala_drive.api.uploads.create_upload_session`
* `ifitwala_drive.api.uploads.upload_session_blob`
* `ifitwala_drive.api.uploads.finalize_upload_session`
* `ifitwala_drive.api.uploads.abort_upload_session`

Rule:

* admissions portal code should prefer workflow-aware admissions/media endpoints
* generic upload lifecycle endpoints should remain internal building blocks unless a new wrapper does not yet exist

Operational deployment rule:

* adding a new `ifitwala_drive.api.*` wrapper is a cross-app deployment, not an Ed-only code change
* the exported API wrapper and the underlying Drive integration service must ship together
* `bench clear-cache` is not sufficient for new Python wrapper exports; restart app processes after deploy
* verify wrapper availability from `bench --site <site> console` before testing in the browser

Recommended console verification:

```python
import ifitwala_drive.api.media as m
hasattr(m, "upload_guardian_image")

import ifitwala_drive.services.integration.ifitwala_ed_media as i
hasattr(i, "upload_guardian_image_service")
```

---

## Current Guidance

### MIME contract for portal uploads

Status:

* Implemented

Code refs:

* `ifitwala_ed.admission.admissions_portal.upload_applicant_document`
* `ifitwala_ed.admission.admissions_portal.upload_applicant_profile_image`
* `ifitwala_ed.admission.admissions_portal.upload_applicant_guardian_image`
* `ifitwala_ed.admission.admissions_portal.upload_applicant_health_vaccination_proof`
* shared helper: `ifitwala_ed.utilities.governed_uploads._resolve_upload_mime_type_hint`

Test refs:

* `ifitwala_ed/admission/test_admissions_portal_uploads_unit.py`

Rule:

* `mime_type_hint` sent to Drive must describe the file bytes expected at finalize time
* when the request carries `request.files["file"]`, derive the hint from the uploaded file object, not from `frappe.request.mimetype`
* for helper calls that receive raw `content`, accept an explicit per-file MIME or fall back to `file_name`
* never forward `multipart/form-data` to Drive as `mime_type_hint`

Why this is explicit:

* browser uploads routed through Frappe endpoints often have `frappe.request.mimetype == "multipart/form-data"`
* that value describes the transport envelope only
* forwarding it is a cross-app contract bug and Drive finalize should reject it when the bytes are actually `image/png`, `image/jpeg`, `application/pdf`, and so on

### Applicant profile image contract

Authoritative contract:

* owner doctype/name: `Student Applicant`
* attached doctype/name: `Student Applicant`
* attached field: `applicant_image`
* primary subject: `Student Applicant`
* slot: `profile_image`
* data class: `identity_image`
* purpose: `applicant_profile_display`
* retention policy: `until_school_exit_plus_6m`
* organization/school: from `Student Applicant`

Post-finalize:

* update `Student Applicant.applicant_image`
* keep the compatibility `File.file_url` on `Student Applicant.applicant_image`
* return a server-owned admissions `image_url` plus `drive_file_id` and `canonical_ref` to the SPA

### Applicant guardian image contract

Required request shape:

* include `guardian_row_name`

Authoritative contract:

* owner doctype/name: `Student Applicant`
* attached doctype/name: `Student Applicant Guardian` / `guardian_row_name`
* attached field: `guardian_image`
* primary subject: `Student Applicant`
* slot: `guardian_profile_image__<guardian-row-key>`
* data class: `identity_image`
* purpose: `applicant_profile_display`
* retention policy: `until_school_exit_plus_6m`
* organization/school: from `Student Applicant`

Why row-aware slotting matters:

* slots are legal/governance truth
* one generic `guardian_profile_image` slot is not sufficient when an applicant can have multiple guardians
* each guardian image needs independent replacement/version lineage

### SPA usage

For the SPA:

* keep calling `ifitwala_ed.api.admissions_portal.*`
* do not move browser code to direct `ifitwala_drive` calls
* pass `guardian_row_name` for guardian image uploads
* if the guardian row has no saved `name`, save the profile first

### Regression coverage

For each Drive-backed admissions upload:

* test that the Ed portal endpoint calls the correct `ifitwala_drive.api.*` wrapper
* test that a `Drive Upload Session` path is used
* test that classification and attached field remain correct
* test guardian image slot derivation from guardian row identity
* test wrapper-export drift: if the thin `ifitwala_drive.api.*` export is missing but the integration service exists, Ed should fail with an actionable deploy message or use the approved fallback

---

## Current Conclusion

As of this note:

* applicant document uploads are correctly routed through `ifitwala_drive`
* applicant health vaccination proof uploads are correctly routed through `ifitwala_drive`
* applicant profile image uploads are correctly routed through `ifitwala_drive`
* applicant guardian image uploads are correctly routed through `ifitwala_drive`
* guardian image uploads now require a saved guardian row identity
* portal upload helpers now explicitly treat `mime_type_hint` as file-byte metadata, not multipart transport metadata
