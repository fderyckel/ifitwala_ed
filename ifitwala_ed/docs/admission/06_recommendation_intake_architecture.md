# Recommendation Intake Architecture (Canonical)

**Ifitwala_Ed | Admissions**

> **Status:** Implemented (runtime)
> **Scope:** Confidential recommendation letters for `Student Applicant`
> **Purpose:** Collect multiple letters without creating recommender users while preserving admissions portal auth boundaries.

---

## 1. Contract Boundary (Locked)

1. Admissions portal authentication remains password login for `Admissions Applicant` users only.
2. Recommender intake is a separate guest surface (`/admissions/recommendation/<token>`), not admissions portal authentication.
3. Recommender links grant one narrow capability: submit exactly one recommendation request payload.
4. Recommendation files continue to be admissions evidence and are uploaded through governed admissions document upload flows.

---

## 2. Runtime Data Model

### 2.1 Recommendation Template

School-scoped template controlling recommendation policy and form fields.

Key fields:
- `organization`, `school`
- `target_document_type` (`Applicant Document Type`)
- `minimum_required`, `maximum_allowed`
- `allow_file_upload`, `file_upload_required`
- `otp_enforced`
- `applicant_can_view_status`
- `template_fields` child rows (`field_key`, `label`, `field_type`, `is_required`, `options_json`, `help_text`)

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

Multiple letters are supported via repeatable `Applicant Document Item` slots:

- each request gets a unique `item_key`
- recommendation files attach to `Applicant Document Item`
- uniqueness is preserved by applicant + document type + item key

This avoids fake `Recommendation 1/2/3` document types and keeps admissions files under Applicant Document ownership.

---

## 4. Security and Confidentiality Invariants

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

1. Staff creates request from applicant context using a school-scoped template.
2. System allocates/links `Applicant Document Item` slot and issues secure intake URL.
3. Recommender opens token link, completes template fields, optionally uploads file, confirms attestation, submits.
4. System seals `Recommendation Submission`, updates request to `Submitted`, and stores evidence in admissions document item slot.
5. Staff can re-send or revoke open requests.
6. Applicant portal sees recommendation progress status only.

---

## 6. API Surface

Staff actions:
- `list_recommendation_templates`
- `create_recommendation_request`
- `resend_recommendation_request`
- `revoke_recommendation_request`
- `list_recommendation_requests`

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

Recommendation readiness is evaluated per in-scope active template:

- required threshold = sum of `minimum_required`
- received threshold = submitted request count
- readiness states: `optional`, `pending`, `in_progress`, `complete`
- when required threshold is not met, applicant readiness issues include recommendation blockers

---

## 8. Known Constraints

1. Applicant visibility is status-only and controlled by template `applicant_can_view_status`.
2. Template max allowed requests is enforced against open/submitted requests.
3. Recommender link flow depends on email delivery when send-email is enabled.
