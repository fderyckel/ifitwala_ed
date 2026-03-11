# Enrollment Execution Workflow Audit

## Executive Summary
The server-side enrollment architecture appears directionally sound: request-based staging, validation, override, and materialized enrollment are the right primitives. The current gaps are not conceptual but operational:
1. weak or missing request-side Desk workflow surfaces,
2. lack of preview/anxiety-reduction for direct administrative bulk enrollment,
3. no formal admissions-to-enrollment bridge yet,
4. no student-facing self-enrollment planner after those core boundaries are stabilized.

## 1. The Three Enrollment Lanes (Architecture Verification)
The audit confirms that the codebase correctly supports three distinct enrollment lanes, which must not be conflated into a single "enrollment workflow":

### Lane A — Admissions Bridge
* **Flow:** `Student Applicant` → `Applicant Enrollment Plan` (pre-student bridge) → committee approval → offer sent/accepted → promotion to `Student` → hydrate real `Program Enrollment Request`.
* **Verdict:** The `Applicant Enrollment Plan` doctype is present in the repository, representing a firm architectural boundary. This prevents polluting the core enrollment engine with pre-student applicant data.

### Lane B — Request-Based Enrollment
* **Flow:** Student already exists → create `Program Enrollment Request` → validate snapshot → request override (if needed) → approve → materialize to `Program Enrollment`.
* **Verdict:** The single-source validation engine (`enrollment_engine.py`) securely handles constraints. However, it is fundamentally **probable / to confirm** that `program_enrollment_request.js` is either missing or anemic, hiding these powerful primitives from the Front Desk.

### Lane C — Direct Staff Enrollment (With Provenance)
* **Flow:** Batch rollover / administrative shell creation → explicit source/provenance required → no pretending this is a request workflow.
* **Verdict:** Supported fully by the `Program Enrollment Tool` and `Course Enrollment Tool`. These are valid, policy-defined, direct-enrollment lanes. They are *not* broken substitutes for the PER request workflow; they are tools for large-scale administrative materialization.

## 2. Tooling and UX Gaps

### Direct Administrative Lane: Program Enrollment Tool
This tool is a bulk administrative materialization tool used for rollover and cohort progression. The actual product gap is safety, not workflow validation.
* **Missing:** A **server-backed Dry Run / Preview**.
* **Fix needed:** Before committing, the tool must explicitly summarize what enrollments will be created, exactly which required courses the offering spine will seed, where capacity or basket anomalies exist, and what will be skipped/blocked.
* **Missing:** Better provenance display.

### Direct Administrative Lane: Course Enrollment Tool
* **Friction:** Currently serializes exception handling using serial `frappe.msgprint` interruptions for elective group conflicts.
* **Fix needed:** Replace with a single structured summary table. Rows should be grouped by student / conflict / recommended action, allowing admins to bulk deselect or ignore where policy allows.

### Request-Based Lane: PER Desk UI
The Desk form for `Program Enrollment Request` must be treated as an **operational console**, not merely a view with action buttons.
* **Fix needed:** The console must provide four core functionalities:
  - Display the immutable latest validation snapshot.
  - Expose override state and rationale (forcing narrative accountability).
  - Clarify workflow state (who owns the next action).
  - Clarify materialization provenance.

*Note: Previous recommendations regarding a visual "Course Spine Builder" inside `Program Offering` have been downgraded. The canonical child table is authoritative, and custom visual builders invite schema drift without unblocking the core transactional execution lanes.*

## 3. Action Plan & Prioritization

### Priority 1 — Admissions Bridge (High Leverage)
Build and finalize the new pre-student handoff object before tackling student self-enrollment:
- `Applicant Enrollment Plan`.
- Execute offer/acceptance on that object.
- Hydrate into a real `Program Enrollment Request` **only** after promotion to `Student`.

### Priority 2 — PER Desk Request Console
Implement or harden the Desk client/controller surface for `Program Enrollment Request` as a true operational console:
- Validate, Request Override, Approve, Materialize actions.
- Show the immutable validation snapshot.
- Show provenance and ownership.

### Priority 3 — Program Enrollment Tool Preview
Add the server-backed dry run mechanism:
- Expose what enrollments will be created, which required courses will seed, where capacity or basket issues exist, and what will be skipped/warned/blocked.

### Priority 4 — Course Enrollment Tool Exception Table
Replace serial `msgprint`-style interruptions with one structured exception summary, allowing bulk ignore/deselect workflows where policies allow.

### Priority 5 — Self-Enrollment Portal (Later)
Only after the core boundaries above are stabilized:
- Build the planner board.
- Implement discovery/catalog APIs.
- Build debounced validation against the Hub UI.
- Introduce pending approval states.
