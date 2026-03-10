# Enrollment Workflow Audit Report

## Executive Summary
A comprehensive audit of the ifitwala_ed enrollment workflow was conducted, focusing on the invariants mapped out in the documentation vs. the actual codebase implementation. The core architecture—separating intention (`Program Enrollment Request`) from committed truth (`Program Enrollment`) and utilizing a unified `Enrollment Engine` for validation—is solid and well-implemented on the server side. However, significant drifts were found in the client-side execution, and crucial student-facing modules for self-enrollment remain unbuilt.

## 1. Drifts and Regressions (Documentation vs. Code)

### CRITICAL: Missing `Program Enrollment Request` Client-Side Logic
- The documentation (`program-enrollment-request.md`) explicitly describes a UI flow where users click **Validate**, **Approve**, and **Materialize** buttons.
- **Drift:** The file `program_enrollment_request.js` does not exist in the codebase.
- **Impact:** While the backend functions (`validate_program_enrollment_request`, `materialize_program_enrollment_request`) are correctly implemented in `enrollment_request_utils.py` and whitelisted, they are entirely disconnected from the Desk UI. Admins currently have no native buttons to interact with requests, meaning manual validation and materialization via the UI is broken or requires manual API calls.

### Missing Student Self-Enrollment Portal
- **Intent:** The `student-enrollment-playbook.md` mentions capturing intent "via portal (student)".
- **Drift:** There are no Web Forms, Portal pages, or dedicated front-end views for students to construct an Enrollment Request basket.
- **Note:** The doctypes `Program Enrollment Tool Student` and `Course Enrollment Tool Student` exist but they are merely child tables for the Admin tools, not actual student-facing views.

## 2. End of Year Transition Process

### Admin-Driven Rollover (Functional)
The system currently relies entirely on Admin-driven batch processing for end-of-year transitions using the **Program Enrollment Tool**.
- **Process:** Admins select a Cohort or existing Program Enrollment filters, define the target `Academic Year` and `Program Offering`, and execute.
- **Mechanism:** The tool creates shell `Program Enrollment` records. The magic happens during the `before_insert` hook of `Program Enrollment`, which automatically calls `_apply_offering_spine(allow_seed_courses=True)`. This automatically seeds all *required* courses for the next year based on the Offering's configuration.
- **Scaling:** The tool intelligently chunks operations >100 students to background async queues.

### Self-Enrollment (Missing)
To support a purely self-enrollment option in the future:
1. A Portal equivalent of `Program Enrollment Request` must be built.
2. Students build their desired basket of courses (electives + core).
3. The Portal hits the `validate_program_enrollment_request` engine strictly in Phase 1 (checking capacity, basket rules, prerequisites).
4. Valid requests await Admin bulk-approval and materialization.

## 3. UI/UX Refactoring & Friction Points

### A. Fix the Request UI (Highest Priority)
Implement `program_enrollment_request.js` immediately to expose standard Frappe buttons:
- **Validate:** Calls `ifitwala_ed.schedule.enrollment_request_utils.validate_program_enrollment_request`. Should render the returned summary (Blocked vs Ok, Requisites met) in a user-friendly HTML block within the document.
- **Approve:** Only shows if `validation_status == 'Valid'`.
- **Materialize:** Only shows if `status == 'Approved'`. Exposes a one-click transition to `Program Enrollment`.

### B. Rollover Preview and Anxiety Reduction
The **Program Enrollment Tool** lacks a "Preview" state.
- **Friction:** Running a mass enrollment job is a high-stress action.
- **Refactor:** Before clicking "Enroll", add a "Dry Run / Preview" button that fetches exactly which required courses will be bound to the students and identifies if any target capacities will be violently ruptured, allowing admins to adjust Offering constraints *before* generating 300 database records.

### C. Course Enrollment Tool Soft-Warnings
- **Current State:** The `Course Enrollment Tool` uses a sequence of `frappe.msgprint` alerts if a student already has a conflicting elective group (soft-warning).
- **Refactor:** If processing 50 students, reading 15 sequential system alerts is terrible UX. Instead, the UI should render a dedicated "Exceptions / Conflicts" HTML data table summary before finalizing the save, allowing the admin to easily uncheck specific students whose schedules conflict.

### D. Offering Course Spine Builder
- **Current State:** `Program Offering.courses` is a standard child table grid.
- **Refactor:** Structuring an academic spine (Core vs. Electives vs. Semesters) is difficult in a linear grid. A custom HTML component or Kanban-style visualizer inside `Program Offering` that visually splits "Required" vs "Elective Pool" courses would vastly reduce data-entry mistakes.

## 4. Code Quality and Invariant Compliance
- The `Enrollment Engine` (`enrollment_engine.py`) strictly complies with the architectural invariants outlined in the docs. It correctly maintains isolated evaluations for prerequisites, repeats, capacity locks, and basket logic.
- The separation of intent layer (`Request`) vs state layer (`Enrollment`) operates safely on the server side via the `enrollment_source` and `frappe.flags.enrollment_from_request` locks.

## 5. Product Proposal: Program Enrollment Request UI/UX

To resolve the missing client-side logic and provide a best-in-class experience, `program_enrollment_request.js` should be implemented with the following product and design principles:

### A. The "Validation Console" (Custom HTML Dashboard)
Relying on hidden JSON payloads or standard data entry fields is insufficient for complex enrollment logic. We should inject a custom HTML block (Validation Console) that parses the `validation_payload` and renders a human-readable dashboard:
- **Basket Health:** Visual progress bars for basket rules (e.g., "Elective Group 'Humanities': 1/2 courses", "Total Courses: 4/5 minimum").
- **Course-Level Diagnostics:** A clean data table or card view detailing exactly *why* a course is blocked with actionable evidence.
  - *Example:* ❌ **Calculus II** - Blocked: Prerequisite *Calculus I* not met (Score: 65.0, Required: 70.0).
  - *Example:* ⚠️ **Intro to Art** - At Risk: Only 2 seats remaining.

### B. Dynamic Workflow Buttons
The form should guide the user (student or admin) seamlessly using conditional Frappe primary buttons:
1. **Validate Basket:** Calls the server-side engine. Instantly injects the results into the Validation Console and alerts the user of any blockers.
2. **Request Override:** If the basket is invalid but the user wants to push it forward, provide a clear friction point to explicitly request an override, highlighting which rules are being broken for the reviewer.
3. **Approve (Admins only):** Only appears when the basket is undeniably `Valid` or overrides are explicitly granted. Locks the request layout.
4. **Materialize Enrollment (Admins only):** Only appears on `Approved` requests. One-click transition into the actual `Program Enrollment` record, returning a success toast and cleanly hyperlinking to the new committed truth.

### C. Preventive Friction (Client-Side Guards)
We should intercept user errors *before* they even hit the server validation engine to reduce frustration:
- **Duplicate Prevention:** The course child table should strictly prevent adding the same course twice in real-time.
- **Smart Catalog Picker:** When adding a course, the `Link` field should be dynamically filtered to only show courses from the selected `Program Offering`, preventing users from selecting off-catalog items unless the offering explicitly permits exceptions.

## 6. Product Proposal: Student Self-Enrollment Portal (`/hub`)

Drawing inspiration from top-tier SIS platforms (like PowerSchool, Canvas, and Workday Student), the ultimate goal of the student self-enrollment experience is to reduce anxiety and prevent invalid course selection *at the source*.

The current ifitwala_ed architecture is highly decoupled: `Program Offering` (catalog definitions) → `Program Enrollment Request` (the intent/basket) → `Enrollment Engine` (the validator). The Portal UI needs to reflect this flow via a clean, guided wizard.

### A. The "Course Discovery & Planner" Board
Top-tier SIS platforms do not present students with a raw dropdown of 500 courses. They present an interactive planning board.

**UI Paradigm: Guided Curriculum Tracks**
- **The Core Spine:** The UI should automatically pre-load the student's `Basket` with the *Required* courses for their specific `Program Offering` and target `Academic Year`. Students should not have to manually search for "Algebra I" if it is a mandatory core requirement for their 9th-grade offering.
- **The Elective Marketplace:** For open slots, present a visual "Marketplace" separated by `Elective Groups` (e.g., a tab for "Arts Requirements", a tab for "Physical Education").
- **Frictionless Discovery:** Each course card in the marketplace should clearly display:
  - **Prerequisites:** A clear green ✔️ or red ❌ indicating if the student has met the prerequisites *before* they even click "Add to Basket". (This requires a lightweight pre-flight check using the student's historical data).
  - **Seat Availability:** A dynamic indicator (e.g., "🔥 Only 3 seats left" or "🟢 Open").
  - **Credits/Level:** Clear metadata indicating the course difficulty and credit weight.

### B. The "Smart Basket" (Live Validation)
The basket should act like an intelligent shopping cart that continuously interacts with the `validate_program_enrollment_request` backend engine.

**UX Flow:**
1. **Live Validation Console:** As students drag or click courses into their basket, the UI fires a background asynchronous request to the engine.
2. **Instant Feedback Loop:**
   - If a constraint is violated (e.g., "Basket requires 2 Humanities courses, you only have 1"), the basket displays a persistent, friendly warning banner.
   - If an added course violates a prerequisite (perhaps they clicked an elective they aren't eligible for), the course turns red in the basket with an explicit "Blocked: Prerequisite Not Met" message, and a primary action button to "Request Override" appears immediately inline.
3. **The Progress Ring:** A visual progress ring indicating "Schedule Complete: 80%" based on the `Program Offering Enrollment Rule` minimums.

### C. The Checkout Flow: "Submit for Review"
Once the basket achieves a `Valid` status (or overrides are explicitly requested and attached), the student initiates the "Checkout" phase.

**UX Flow:**
1. **The Review Screen:** A final clean summary of the selected schedule, highlighting any approved/pending overrides.
2. **The Intent Generation:** Clicking "Submit Schedule" securely generates the `Program Enrollment Request` on the backend, setting the status to `Submitted` or `Under Review`.
3. **The Waiting Room (Read-Only State):** The Portal transitions the planner into a read-only "Pending Approval" state. Students can view their submitted basket but can no longer mutate it, preventing race conditions while Admins approve and materialize the requests via the Desk UI.

### D. Technical Implementation Strategy (Vue.js / Web Components)
To achieve this within the Frappe ecosystem on the `/hub` portal:
- **Framework:** Utilize Vue.js (or Frappe UI components) embedded within a Portal Web Page (`/hub/enrollment`).
- **State Management:** The Vue app manages the local basket state, debouncing calls to the Python validation engine to ensure a snappy UI without overloading the server.
- **API Surface:** Create a dedicated set of read-only, non-mutating portal endpoints (`@frappe.whitelist(allow_guest=False)`) that aggregate offering data, student history, and capacity counts for the discovery board, keeping the heavy `evaluate_enrollment_request` purely for the basket validation phase.

## 7. Action Plan Recommendations
1. **Ship `program_enrollment_request.js`**: Implement the proposed Validation Console and workflow buttons to restore manual functionality and provide a premium desk UI for Admins.
2. **Build the `/hub` Enrollment Vue App**: Execute the "Smart Basket" and "Course Discovery" proposal above, utilizing the existing robust backend engine.
3. **Enhance Admin Tools UX**: Add the "Dry Run / Preview" functionality to the `Program Enrollment Tool` prior to bulk generation.
