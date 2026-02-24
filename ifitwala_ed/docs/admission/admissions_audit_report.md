# Admissions Module Audit

**Date**: 2026-02-17
**Scope**: Admissions Module (`ifitwala_ed/admission`)

## 1. Executive Summary

The **Admissions module** is structurally sound and well-anchored to the governance intent (Org/School scoping), but suffers from a **critical security vulnerability** and identifiable efficiency bottlenecks.
**Top Frictions**: Reviewing an Applicant requires high cognitive load to parse "Review Snapshot" text without direct actions. Officers lack a unified "Action Dashboard" and rely on raw List Views.
**Drift**: The implementation aligns well with Phase 1.5 intent. `Program Offering` is present but not yet authoritative, which is correct per the "locked" governance docs.
**Efficiency**: The hourly SLA check (`check_sla_breaches`) performs full table scans on `Inquiry`, posing a scalability risk. The Applicant form loads heavy readiness checks synchronously on render.
**Security**: The `upload_applicant_document` endpoint allows **unauthorized file uploads** via parameter injection, bypassing permission checks. This is a critical risk that must be patched immediately.
**Recommendation**: Prioritize the security fix and SLA indexing immediately. Then, focus on the "Action Dashboard" to give officers a "cockpit" for their daily work.

## 2. Findings Table

| ID | Category | Role | Severity | Evidence | Current Behavior | Intended Behavior | Suggested Fix |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | Security | Any User | **Critical** | `admissions_portal.py` L18, L134 | `ignore_permissions` argument is exposed in whitelisted API. | Users should never control permission bypass. | Remove arg from public API; check permissions internally. |
| **EFF-01** | Efficiency | System | **High** | `admission_utils.py` L124; `inquiry.json` | SLA job runs `UPDATE` query filtering by non-indexed `workflow_state`. | Scheduled jobs should use efficient, indexed queries. | Add DB index to `workflow_state` and due date fields. |
| **EFF-02** | Efficiency | Officer | Med | `student_applicant.js` L117 | Readiness snapshot triggers multiple DB queries on every form load. | Form load should be instant; expensive checks optional. | Cache readiness state or batch queries into one call. |
| **UX-01** | UX | Officer | Med | `student_applicant.js` L142 | "Review Snapshot" lists missing items as static text. | Missing items should be actionable links. | Convert text items to links that open relevant dialogs/scroll. |
| **UX-02** | UX | Officer | Low | Desk (General) | Visual cues for "Due Today" relies on List View columns. | Urgent items should be grouped and pushed to user. | Introduce "Admissions Workspace" with "Breach Risk" cards. |

## 3. Top 5 Proposals

### Proposal 1: Patch Critical Security Loophole in Document Upload
**Title**: Secure `upload_applicant_document` and Enforce Permissions
**Problem**: (SEC-01) The `upload_applicant_document` endpoint accepts an `ignore_permissions` parameter from the client, allowing any authenticated user to upload files to any Applicant record.
**Target Roles**: All (Security)
**Scope**: `ifitwala_ed/admission/admissions_portal.py`
**Technical Approach**:
1. Remove `ignore_permissions` from the function signature.
2. Inside the function, explicitly call `ensure_admissions_permission()` (or check `has_permission` on the target Applicant).
3. Hardcode `ignore_permissions=True` in the internal `_resolve_applicant_document` call *only after* verifying legitimate access.
**Security Implications**: Fixes an arbitrary file upload/attachment vulnerability.
**Acceptance Criteria**:
1. API call with `ignore_permissions=1` helps NO ONE if they lack role access.
2. Regular Staff/Portal flows still work.
**Rollout Plan**: Immediate hotfix.
**Risk**: Low (Security fix).

### Proposal 2: Optimize SLA & Deadline Queries
**Title**: Index SLA Fields for Scalable Hourly Jobs
**Problem**: (EFF-01) `check_sla_breaches` performs a full table scan on `Inquiry` every hour. As data grows, this will degrade DB performance.
**Target Roles**: System / DevOps
**Scope**: `Inquiry` DocType.
**Technical Approach**:
1. Add `search_index=1` (standard index) to:
    - `workflow_state`
    - `first_contact_due_on`
    - `followup_due_on`
2. This allows MySQL/MariaDB to verify `workflow_state != 'Archived'` and date ranges efficiently.
**Security Implications**: None.
**Acceptance Criteria**: `EXPLAIN` query shows index usage instead of `ALL`.
**Rollout Plan**: Standard deployment (patches DB).
**Risk**: Low.

### Proposal 3: "Admissions Cockpit" Workspace
**Title**: Create Role-Specific Admissions Workspace
**Problem**: (UX-02) Officers rely on generic List Views to find work. They have to filter for "Due Today" or "Assigned to Me".
**Target Roles**: Admission Officer
**Scope**: New `Workspace` or update existing `Admissions` Workspace.
**Technical Approach**:
1. Create a Workspace "Admissions Cockpit".
2. Add "Number Cards":
    - "Inquiries Due Today" (Red)
    - "My Active Applicants" (Blue)
    - "Pending Reviews" (Orange)
3. Add "Quick Lists" with preset filters (`assigned_to = me`, `sla_status = Due Today`).
**Security Implications**: Respects existing permission scopes.
**Acceptance Criteria**: Officer logs in and sees their daily todo count immediately.
**Rollout Plan**: Phase 1 (Staff).
**Risk**: Low.

### Proposal 4: Actionable Review Snapshot
**Title**: Deep-Link "Missing Info" in Applicant Review
**Problem**: (UX-01) The "Review Snapshot" tells an officer "Missing: Passport", but they have to manually find the document upload section or email the family.
**Target Roles**: Admission Officer / Manager
**Scope**: `student_applicant.js` and `student_applicant.py`.
**Technical Approach**:
1. Update `get_readiness_snapshot` to return metadata (DocType, Fieldname) for missing items.
2. Update `student_applicant.js` to render "Missing: Passport" as a link.
3. On click:
    - If it's a file: Open the `upload_applicant_document` dialog (or scroll to Documents section).
    - If it's a policy: Open the specific Policy Acknowledgement dialog.
**Security Implications**: None.
**Acceptance Criteria**: Clicking a missing item item initiates the resolution action.
**Rollout Plan**: Phase 2.
**Risk**: Medium (Frontend complexity).

### Proposal 5: Optimistic/Cached Readiness Checks
**Title**: Async/Cached Applicant Readiness Check
**Problem**: (EFF-02) `get_readiness_snapshot` runs complex queries (Policy x Org x School) on every form load, adding ~200-500ms latency (growing with policy count).
**Target Roles**: Admission Officer
**Scope**: `student_applicant.py`
**Technical Approach**:
1. Cache the `readiness_snapshot` result in `frappe.cache().hset` with a key based on `Applicant.modified`.
2. Omit the call on "List View" or non-form interactions (already done, but ensure it's tight).
3. OR: Convert to a computed JSON field stored on the DocType (`_readiness_cache`) updated `on_update` and `on_daily_schedule`.
**Security Implications**: None.
**Acceptance Criteria**: Form render time is decoupled from Policy/Document query complexity.
**Rollout Plan**: Phase 2.
**Risk**: Medium (Cache invalidation logic).

## 4. Questions to resolve

*None blocking. The security fix is the immediate priority.*
