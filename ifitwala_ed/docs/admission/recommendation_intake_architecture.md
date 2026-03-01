# Recommendation Intake Architecture (Proposed)

**Ifitwala_Ed | Proposal**

> **Status:** Proposed (not yet implemented in runtime)
> **Scope:** Admissions recommendation letters for `Student Applicant`
> **Purpose:** Enable confidential, multi-recommender submissions without creating user accounts.

---

## 1. Problem Statement

Admissions needs recommendation letters that are:

- configurable per school (template fields/checklists/questions)
- confidential to admissions staff
- collectible from external recommenders without creating `User` accounts
- scalable to multiple letters per applicant

Current admissions portal auth remains account-based and is intentionally unchanged.

---

## 2. Contract Alignment (Non-Negotiable)

This proposal is designed to preserve existing locked contracts:

1. **Admissions Portal auth model stays unchanged**
- `/admissions/*` remains password login for `Admissions Applicant`.
- "No token/magic-link authentication" remains true for portal user authentication.

2. **External intake is a separate surface**
- Recommender intake links are scoped to one request and one submission action.
- No desk access, no applicant browsing, no reusable session identity.

3. **Admissions file governance remains authoritative**
- Recommendation files are routed through dispatcher-backed classification.
- Legal data subject remains `Student Applicant`.
- Admissions evidence ownership remains in the admissions evidence boundary.

4. **Server-side invariants remain the source of truth**
- Client UX only assists; uniqueness, confidentiality, and one-time token enforcement are server-owned.

---

## 3. Proposed Domain Model (Conceptual)

Concrete schema field names are intentionally deferred to implementation review; this section defines required capabilities.

1. **Recommendation Template**
- scoped by organization/school
- active/inactive lifecycle
- configurable form definition (questions/checkboxes/required flags)
- minimum/maximum expected recommendation count
- confidentiality policy (applicant-visible status only vs stricter hiding)

2. **Recommendation Request**
- one request targets one applicant and one recommender email
- linked to selected school-scoped template
- stores secure token hash, expiry, consumption timestamp, and request status
- supports resend/rotate token behavior
- carries a stable per-request slot identity used to distinguish multiple letters

3. **Recommendation Submission**
- immutable sealed record linked to one request
- stores submitted structured answers snapshot
- optional governed file upload evidence
- stores submission metadata for forensics/audit (timestamp, source footprint)

---

## 4. Multi-Letter Invariant

To support multiple recommendation letters for one applicant, the evidence key must include a per-request slot identity.

Target invariant:

- recommendation evidence uniqueness is **applicant + recommendation type + slot identity**
- not just **applicant + recommendation type**

This avoids artificial "Recommendation 1 / Recommendation 2 / Recommendation 3" hard caps per school and keeps one canonical workflow path.

---

## 5. Confidentiality Invariant

Recommendation content must be treated as confidential admissions evidence.

Required behavior:

1. Admissions staff can review recommendation content and attachments.
2. Applicant-facing surfaces must not expose recommendation content by default.
3. Applicant-facing surfaces may show status-only signals (for example: requested, received, complete).
4. Recommendation submissions are append-only from the recommender surface after submission.

---

## 6. Security Model for Unique URL Intake

Minimum controls:

1. token generated with cryptographic randomness
2. token persisted as hash only (no plaintext storage)
3. strict expiry enforced server-side
4. single-use consumption enforced transactionally
5. resend rotates token and invalidates previous token
6. rate limits and attempt limits by token + source
7. structured audit trail on request create/send/open/submit/expire events

Optional hardened mode:

- step-up OTP check to recommender email before final submit

---

## 7. Workflow (Target)

1. Admissions staff selects applicant and template, then creates recommendation request(s).
2. System sends unique one-time intake links to recommender emails.
3. Recommender opens link, fills template, optionally uploads file, submits once.
4. System seals submission, invalidates token, classifies file(s), and records audit timeline.
5. Admissions review workflow processes recommendation evidence.
6. Applicant sees status only (if enabled), never confidential content.

---

## 8. API Shape (High-Level)

Recommended server-owned actions:

1. create recommendation request(s)
2. resend/rotate request link
3. fetch intake payload by token (minimal context only)
4. submit recommendation payload (single transaction, idempotent guard)
5. fetch admissions-side recommendation summary/status for applicant

No generic CRUD assembly from client for meaningful workflow transitions.

---

## 9. Readiness Integration (Target)

Recommendation readiness should be explicit and institution-configurable:

1. if template has `minimum_required = 0`, recommendation is optional
2. if `minimum_required > 0`, applicant readiness requires at least that many valid submissions
3. approvals/rejections of recommendation content remain reviewer workflow decisions, not applicant-editable state

Recommendation readiness should be represented separately from other document slots so schools can tune policy by template/scope.

---

## 10. Rationale

### Pros

- supports multiple letters cleanly for one applicant
- keeps admissions portal auth model intact
- enables confidential external submission without account provisioning
- preserves governed file classification and auditability

### Cons

- introduces new public intake endpoints and email delivery dependency
- increases workflow and monitoring surface area

### Blind Spots

- link forwarding behavior and institutional legal wording need product/legal alignment
- school-specific recommendation rubric variance may pressure template UX design

### Risks

- token handling bugs could cause confidentiality leaks
- partial implementation could cause docs/runtime drift if rolled out without full guards
- readiness coupling can create admissions bottlenecks if defaults are too strict

---

## 11. Phased Delivery Plan

1. **Phase 1: Data and security foundation**
- add recommendation template/request/submission models
- implement token lifecycle + secure intake submit pipeline
- classify files through dispatcher

2. **Phase 2: Admissions workflow integration**
- add staff actions to create/resend/revoke requests
- add admissions review surfaces and status telemetry

3. **Phase 3: Applicant-facing status integration**
- expose status-only recommendation progress to applicant portal (optional by policy)

4. **Phase 4: Optional security hardening**
- add OTP challenge mode for high-sensitivity deployments

---

## 12. Open Decisions Required Before Schema PR

1. Default recommendation minimum per school/template
2. Whether file upload is mandatory, optional, or forbidden per template
3. Applicant-facing status visibility policy defaults
4. Token lifetime default and resend limits
5. Whether OTP hardening is optional or mandatory by policy scope
