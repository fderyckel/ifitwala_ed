# Policy System Audit Report

**Date:** 2026-02-01
**Auditor:** Antigravity
**Status:** In Progress / Changes Required

## 1. Acknowledgement of Reading
I have read and understood the following policy definition files:
*   `policy_01_design_notes.md` (Authority Matrix & Schema Locks)
*   `policy_02_controllers.md` (Controller Guards)
*   `policy_03_taxinomy.md` (Taxonomy & Categories)

---

## 2. Executive Summary
The core architecture for **Institutional Policy**, **Policy Version**, and **Policy Acknowledgement** is effectively implemented with strong adherence to the **immutability** and **server-side enforcement** principles outlined in the policy notes. The "PowerSchool-style" locking of legal text and versions works as intended.

However, there are **critical discrepancies** in the **Taxonomy/Category** implementation and **Guardian acknowledgement workflows** that must be referenced before calling this "complete".

---

## 3. What Has Been Achieved (Compliance Verified)

### ✅ Core Schema & Authority
*   **Doctypes exist** matching the specifications: `Institutional Policy`, `Policy Version`, `Policy Acknowledgement`.
*   **Immutability** is correctly enforced in `before_save` and `before_delete` controllers.
*   **Deletion** is strictly forbidden across all three doctypes, matching `policy_02`.
*   **System Manager overrides** are implemented with mandatory reasoning and commenting.

### ✅ Institutional Policy
*   Organization scoping is correctly enforced.
*   `policy_key` immutability is active.

### ✅ Policy Version
*   **Legal Text Lock:** The system successfully prevents editing `policy_text` once an acknowledgement exists.
*   **Active State Logic:** Correctly validates that the parent policy must be active.
*   **Uniqueness:** Version labels are unique per policy.

### ✅ Policy Acknowledgement
*   **Append-only:** No edits allowed.
*   **Context Binding:** Enforces `context_doctype` and `context_name`.
*   **Applicant Scope:** Correctly validates that the applicant belongs to the same organization as the policy.

---

## 4. Gaps and Missing Implementation (Action/Fix Required)

### 🔴 Critical: Taxonomy Mismatch (`policy_03_taxinomy.md`)
The `Institutional Policy` doctype (`institutional_policy.json`) uses an outdated or incorrect list of options for `policy_category`.

*   **Current (JSON):** "Privacy", "Safeguarding", "Academic", "Conduct", "Handbook", "Other".
*   **Required (Policy):** "Safeguarding", "Privacy & Data Protection", "Admissions", "Academic", "Conduct & Behaviour", "Health & Safety", "Operations", "Handbooks", "Employment".
*   **Violation:** The option "Other" is explicitly **forbidden** by the spec but is present in the code.
*   **Violation:** "Admissions", "Health & Safety", "Operations", "Employment" are missing.

### 🔴 Critical: Guardian Acknowledgement Logic Failure
The current implementation of `policy_acknowledgement.py` prevents Guardians from acknowledging policies for Students, which is a key requirement of `policy_01`.

*   **Issue:** `_is_role_allowed_for_ack` checks `has_student_role()` when `acknowledged_for == "Student"`. A Guardian user does not have the Student role, so they are blocked.
*   **Missing Logic:** There is no logic handling `acknowledged_for="Guardian"` (for parent handbooks) or `acknowledged_for="Student"` *by* a Guardian.
*   **Missing Option:** The `acknowledged_for` field in JSON lacks the "Guardian" option.
*   **Missing Context:** `ACK_CONTEXT_MAP` lacks a mapping for "Guardian".

### 🟠 Optimization & Efficiency
*   **No immediate risks.** The current lookup methods (`frappe.db.get_value`, `exists`) are efficient for the expected write volume (low-frequency administrative writes, moderate-frequency acknowledgement writes).
*   **Index Recommendation:** Ensure composite indexes exist for the uniqueness constraints (e.g., `(policy_version, acknowledged_by, context_doctype, context_name)`) to avoid table scans as the acknowledgement table grows.

### 🟡 Minor Discrepancies
*   **Naming:** The JSON uses "Privacy" vs Policy "Privacy & Data Protection".
*   **Naming:** The JSON uses "Conduct" vs Policy "Conduct & Behaviour".

---

## 5. Next Steps (Remediation Plan)

1.  **Refactor Taxonomy:** Update `Institutional Policy` JSON options to strictly match `policy_03_taxinomy.md`. Remove "Other".
2.  **Fix Guardian Logic:**
    *   Update `acknowledged_for` options to include "Guardian".
    *   Update `ACK_CONTEXT_MAP` to handle Guardian context.
    *   Refactor `_is_role_allowed_for_ack` to allow a user with **Guardian Role** to acknowledge when `acknowledged_for` is "Student" (if they are linked to that student) OR "Applicant".
3.  **Verify Indexes:** Confirm database indexes for the uniqueness checks.

---

## 6. Strategic Recommendations (Competitor Analysis)

To position IFitwala_Ed as a top-tier Education ERP, the following architectural enhancements are recommended. These are rated by **Impact (0.0–1.0)** based on competitive differentiation and value to the institution.

### 1. Automated "Re-certification" Campaigns & Workflows
*   **Impact:** `0.95`
*   **Why:** Currently, policies are passive. Top-tier SaaS (Workday, Rippling) drives compliance actively.
*   **Recommendation:** Implement a "Campaign" engine that pushes notifications (Email, SMS) to targeted cohorts (e.g., "All Science Teachers") requiring acknowledgement by a deadline. If overdue, escalation logic triggers or portal access is paused. This solves the #1 "nagging" pain point for administrators.

### 2. Point-of-Context "Just-in-Time" Injection
*   **Impact:** `0.92`
*   **Why:** Static "Policy Tabs" are ignored. Contextual consent is legally superior.
*   **Recommendation:** Inject acknowledgement requests directly into workflows.
    *   *Trip Payment:* "Agree to Refund Policy" before payment.
    *   *Team Sign-up:* "Agree to Sports Code of Conduct" before roster addition.
    *   *Enrollment:* "Agree to Financial Terms" before acceptance.

### 3. Visual Redline/Diffing for Version Updates
*   **Impact:** `0.88`
*   **Why:** "What changed?" is the most common question from parents and staff, eroding trust if not answered transparently.
*   **Recommendation:** When pushing `v2`, the UI should automatically display a computed "redline" diff against `v1` (the version they previously signed). This builds immense trust and transparency, a clear differentiator from opaque legacy ERPs.

### 4. Comprehension Verification (Quiz-to-Sign)
*   **Impact:** `0.85`
*   **Why:** Clicking "I Agree" is often legally insufficient for critical Safeguarding policies.
*   **Recommendation:** Add an optional `requires_comprehension` flag. If set, the user must correctly answer 3 randomized simple questions about the policy content before the "Acknowledge" button becomes active. This is the "Gold Standard" for Child Protection compliance.

### 5. "Audit-Ready" Time-Machine Reporting
*   **Impact:** `0.80`
*   **Why:** Auditors (CIS, WASC) rarely ask "who signed today". They ask "Was this policy active and signed by Staff Member X on the date of the incident?".
*   **Recommendation:** Build a Compliance Snapshot tool that exports a zip file containing:
    *   The exact PDF of the policy version active on Date X.
    *   The timestamped acknowledgement log.
    *   A certified "proof of coverage" report.

### 6. Dependency & Co-Signature Logic
*   **Impact:** `0.75`
*   **Why:** Education compliance often requires multi-party consent (Student + Guardian).
*   **Recommendation:** Implement "Pending Counter-Signature" states. Use case: Student signs "Acceptable Use Policy" in class; Guardian receives a notification to "Counter-sign" the same document. The policy is only "Fully Acknowledged" when both links are complete.

### 7. Policy "Bundles" & Onboarding Experiences
*   **Impact:** `0.70`
*   **Why:** Signing 15 individual policies is a poor user experience.
*   **Recommendation:** Create "Policy Bundles" (e.g., "New Staff Onboarding Pack", "Year 7 Enrollment Pack"). Present these as a single localized workflow with a progress bar ("3 of 10 policies signed"), rather than a disjointed list of files.

---

**Sign-off:**
*   *Architecture Status:* **Verified**
*   *Implementation Status:* **Incomplete (Categories & Guardian Flow)**
