# Recommendation Intake Architecture (Canonical)

**Ifitwala_Ed | Admissions**

> **Status:** Implemented (runtime)
> **Scope:** Confidential recommendation letters for `Student Applicant`
> **Purpose:** Collect multiple letters without creating recommender users while preserving admissions portal auth boundaries.

---

## 1. Contract Boundary (Locked)

Status: Implemented
Code refs: `ifitwala_ed/api/recommendation_intake.py`, `ifitwala_ed/admission/doctype/recommendation_request/recommendation_request.py`, `ifitwala_ed/admission/doctype/recommendation_submission/recommendation_submission.py`, `ifitwala_ed/api/admissions_portal.py`
Test refs: `ifitwala_ed/api/test_recommendation_intake.py`, `ifitwala_ed/admission/doctype/recommendation_request/test_recommendation_request.py`, `ifitwala_ed/admission/doctype/recommendation_submission/test_recommendation_submission.py`

1. Admissions portal authentication remains password login for `Admissions Applicant` users only.
2. Recommender intake is a separate guest surface (`/admissions/recommendation/<token>`), not admissions portal authentication.
3. Recommender links grant one narrow capability: submit exactly one recommendation request payload.
4. Recommendation submissions are referee-owned. When a school enables file upload on the template, the referee uploads that file within the secure recommendation intake flow; otherwise the recommendation is form-only.
5. Recommendation evidence follows the same requirement/submission contract as all admissions evidence: the parent `Applicant Document` is aggregate-only and review, when required, happens only on the linked `Applicant Document Item`.
6. Applicant portal visibility is status-only. Applicants never open the recommendation submission, its answers, or any attached file, and recommendation target document types are excluded from `/admissions/documents`.

---

## 2. Runtime Data Model

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/recommendation_template/recommendation_template.json`, `ifitwala_ed/admission/doctype/recommendation_request/recommendation_request.json`, `ifitwala_ed/admission/doctype/recommendation_submission/recommendation_submission.json`
Test refs: `ifitwala_ed/admission/doctype/recommendation_template/test_recommendation_template.py`, `ifitwala_ed/admission/doctype/recommendation_request/test_recommendation_request.py`, `ifitwala_ed/admission/doctype/recommendation_submission/test_recommendation_submission.py`

### 2.1 Recommendation Template

School-scoped template controlling recommendation policy and form fields.

Key fields:
- `organization`, `school`
- `target_document_type` (`Applicant Document Type`)
  - optional at authoring time; when omitted, runtime auto-links or auto-creates a managed school-scoped `Applicant Document Type` for recommendation evidence and notifies staff on save
- `minimum_required`, `maximum_allowed`
  - limits are strict-validated (`minimum_required >= 0`, `maximum_allowed >= 1`, `minimum_required <= maximum_allowed`); invalid values are rejected, not auto-normalized
- `allow_file_upload`, `file_upload_required`
- `otp_enforced`
- `applicant_can_view_status`
- `template_fields` child rows (`field_key`, `label`, `field_type`, `is_required`, `options_json`, `help_text`)
  - supported field types: `Data`, `Small Text`, `Long Text`, `Select`, `Check`, `Section Header`, `Likert Scale`
  - `Section Header` is display-only; it groups the recommender form and never creates an answer row
  - `Likert Scale` renders as a matrix/radio grid for recommender ease-of-clicking; staff configure it through the template form builder, while `options_json` stores normalized internal `columns` and `rows` with stable keys plus display labels
  - Likert submissions store stable option/row keys in `answers_json`; review payloads return labels and matrix metadata so staff see human-readable responses

### 2.2 Recommendation Request

One invitation for one recommender and one submission slot.

Key fields:
- `student_applicant`, `recommendation_template`
- `target_document_type`, `applicant_document`, `applicant_document_item`
- `item_key`, `item_label`
- recommender identity (`recommender_name`, `recommender_email`, `recommender_relationship`)
- lifecycle (`request_status`, `expires_on`, `sent_on`, `opened_on`, `consumed_on`, `resend_count`)
- token/otp security (`token_hash`, `otp_*`)
- immutable `template_snapshot_json`

### 2.3 Recommendation Submission

Immutable sealed submission linked 1:1 to request.

Key fields:
- `recommendation_request` (unique)
- `student_applicant`, `recommendation_template`
- `applicant_document`, `applicant_document_item`
- `answers_json`, `attestation_confirmed`, `has_file`
- forensic metadata (`submitted_on`, `source_ip`, `user_agent`, `idempotency_key`)

---

## 3. Multi-Letter Strategy (Implemented)

Status: Implemented
Code refs: `ifitwala_ed/api/recommendation_intake.py`, `ifitwala_ed/admission/doctype/recommendation_request/recommendation_request.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
Test refs: `ifitwala_ed/api/test_recommendation_intake.py`, `ifitwala_ed/admission/doctype/recommendation_request/test_recommendation_request.py`

Multiple letters are supported via repeatable `Applicant Document Item` slots:

- each request gets a unique `item_key`
- recommendation files attach to `Applicant Document Item`
- any evidence review assignment created for a recommendation letter targets that `Applicant Document Item`, never the parent requirement card
- uniqueness is preserved by applicant + document type + item key

This avoids fake `Recommendation 1/2/3` document types and keeps admissions files under Applicant Document ownership.

---

## 4. Security and Confidentiality Invariants

Status: Implemented
Code refs: `ifitwala_ed/api/recommendation_intake.py`, `ifitwala_ed/admission/doctype/recommendation_submission/recommendation_submission.py`, `ifitwala_ed/api/admissions_portal.py`
Test refs: `ifitwala_ed/api/test_recommendation_intake.py`, `ifitwala_ed/api/test_admissions_portal.py`

Implemented controls:
- link token stored as SHA-256 hash (`token_hash`), never plaintext
- request expiry enforced server-side
- single-use semantics via request status + submission linkage
- resend rotates token (hash replaced)
- idempotency guards and cache locks on create/submit actions
- optional OTP challenge by template (`otp_enforced`)
- applicant surfaces expose status only; recommender identity/content remains staff-only

---

## 5. Runtime Workflow

Status: Implemented
Code refs: `ifitwala_ed/api/recommendation_intake.py`, `ifitwala_ed/admission/doctype/recommendation_template/recommendation_template.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`
Test refs: `ifitwala_ed/api/test_recommendation_intake.py`, `ifitwala_ed/admission/doctype/recommendation_template/test_recommendation_template.py`

1. Staff creates request from applicant context using a school-scoped template.
   - when template author left `target_document_type` empty, save auto-resolves/creates the managed recommendation document type before requests can be created
2. System allocates/links `Applicant Document Item` slot and issues secure intake URL.
3. Recommender opens token link, completes template fields, optionally uploads file, confirms attestation, submits.
4. System seals `Recommendation Submission`, updates request to `Submitted`, and stores evidence in admissions document item slot.
   - if staff evidence review is configured, the resulting review task is materialized against that submission row only
5. Staff can re-send or revoke open requests.
6. Applicant portal sees recommendation progress status only and cannot access the submission itself.

---

## 6. API Surface

Status: Implemented
Code refs: `ifitwala_ed/api/recommendation_intake.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.py`
Test refs: `ifitwala_ed/api/test_recommendation_intake.py`, `ifitwala_ed/admission/doctype/applicant_interview/test_applicant_interview.py`

Staff actions:
- `list_recommendation_templates`
- `create_recommendation_request`
- `resend_recommendation_request`
- `revoke_recommendation_request`
- `list_recommendation_requests`
- `get_recommendation_review_payload`

Recommender guest actions:
- `get_recommendation_intake_payload`
- `send_recommendation_otp` (when enabled)
- `verify_recommendation_otp` (when enabled)
- `submit_recommendation`

Readiness/status:
- `get_recommendation_status_for_applicant`
- included in `Student Applicant.get_readiness_snapshot()`
- exposed to applicant portal as snapshot `completeness.recommendations` and `recommendations_summary`

---

## 7. Readiness Contract

Status: Implemented
Code refs: `ifitwala_ed/api/recommendation_intake.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/api/admission_cockpit.py`
Test refs: `ifitwala_ed/api/test_recommendation_intake.py`, `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

Recommendation readiness is evaluated per in-scope active template:

- required threshold = sum of `minimum_required`
- received threshold = submitted request count
- readiness states: `optional`, `pending`, `in_progress`, `complete`
- when required threshold is not met, applicant readiness issues include recommendation blockers

---

## 8. Known Constraints

Status: Implemented
Code refs: `ifitwala_ed/api/recommendation_intake.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`, `ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsWorkspaceOverlay.vue`
Test refs: `ifitwala_ed/api/test_recommendation_intake.py`, `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

1. Applicant visibility is status-only and controlled by template `applicant_can_view_status`.
2. Template max allowed requests is enforced against open/submitted requests.
3. Recommender link flow depends on email delivery when send-email is enabled.
4. If a school wants the applicant to upload a recommendation letter directly, that must use a normal `Applicant Document Type` in the applicant documents workflow, not `Recommendation Template`.

## 9. Staff Review Surface

Status: Implemented
Code refs: `ifitwala_ed/api/recommendation_intake.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`, `ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsWorkspaceOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`
Test refs: `ifitwala_ed/api/test_recommendation_intake.py`

Staff review surfacing is applicant-centered:

- Desk `Student Applicant.documents_summary` shows submitted recommendation rows with direct `Review Recommendation` actions
- Admissions Cockpit cards expose recommendation review counts and open the applicant workspace directly into recommendation review when only one pending letter exists
- Admissions workspace overlay renders a recommendation queue plus a full recommendation detail pane sourced from `get_recommendation_review_payload`
- review decisions still call the canonical `Applicant Document Item` review endpoint; `Recommendation Submission` never becomes a second approval truth

## 10. Contract Matrix

Status: Implemented
Code refs: `ifitwala_ed/api/recommendation_intake.py`, `ifitwala_ed/api/admission_cockpit.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`, `ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.py`, `ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsWorkspaceOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`
Test refs: `ifitwala_ed/api/test_recommendation_intake.py`, `ifitwala_ed/admission/doctype/applicant_interview/test_applicant_interview.py`

| Area | Contract | State |
| --- | --- | --- |
| Schema / DocType | Template governs intake, request owns slot, submission is immutable, review truth remains on `Applicant Document Item` | Implemented |
| Controller / workflow logic | One request = one slot = one submission; review uses canonical document review workflow | Implemented |
| API endpoints | staff request actions, guest intake actions, readiness summary, and staff recommendation review payload | Implemented |
| SPA / UI surfaces | cockpit CTA and applicant workspace overlay expose recommendation review in applicant context | Implemented |
| Desk surfaces | `Student Applicant` form renders direct recommendation review actions and detail dialog | Implemented |
| Reports / dashboards / briefings | admissions cockpit includes recommendation counts and first pending review metadata per applicant | Implemented |
| Scheduler / background jobs | None | Implemented |
| Tests | backend coverage for creation, confidentiality, review payload, and cockpit metadata | Implemented |
