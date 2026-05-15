# Student Log: Integrated Observational Workflow

> **For:** Educators, IT System Specialists, Academic Administrators, and Decision Makers.
> **Purpose:** Introduction to the Student Log ecosystem — from rapid capture to structured follow-up.

---

## 1. The Core Problem: Why Student Log Exists

In many schools, observational data is fragmented:

- **Siloed Systems:** Discipline notes in one place, academic concerns in another, and attendance somewhere else.
- **Broken Feedback Loops:** A teacher notes a concern, but never knows if it was acted upon.
- **Invisible Context:** A pastoral lead misses a pattern of behavior because they can't see the small observations from five different teachers.

**Student Log** solves this by integrating **recording**, **showing**, and **follow-up** into a single, cohesive workflow embedded directly in the `ifitwala_ed` ecosystem.

It is not just a digital notebook; it is a **workflow engine** designed to close the loop on student observations.

---

## 2. Solution: The 3 Layers of Integration

We solve the fragmentation problem by architecting the system in three distinct layers:

### Layer 1: Recording (Frictionless Capture)

We know that if recording is hard, it won't happen. Student Log is integrated where teachers already work:

1.  **Attendance Context:**
    - Teachers can log a note _during_ attendance taking.
    - **Context Aware:** The student is already selected; one click to add a note.
    - **Use Case:** "Student arrived late and seemed distressed."

2.  **Staff Home (Quick Link):**
    - Accessible immediately from the dashboard.
    - **School-Scoped:** Smart search only shows students relevant to the teacher's valid school context (no infinite global lists).

**Structured Data:** Every log captures:

- **Type:** Categorized (e.g., Behavior, Academic, Wellbeing) — customizable per school.
- **Note:** The qualitative observation.
- **Visibility:** Explicit control (Visible to Student / Visible to Parents). _Default is always OFF for safety._

### Layer 2: Showing (Integrated Analytics)

Data that sits in a database is useless. We surface it immediately to the right people:

1.  **Morning Briefing Integration:**
    - **Situational Awareness:** The Morning Briefing page automatically surfaces "Recent Logs (48h)" and "Critical Incidents."
    - **No Searching:** Pastoral leads start their day knowing exactly who needs attention before school starts.

2.  **Student Log Analytics Dashboard:**
    - **Trends:** See incidents over time, logs by cohort, or breakdown by log type.
    - **Filtering:** Slice by program, academic year, or author.
    - **Follow-Up Context in Tables:** The two detail tables keep one row per Student Log and summarize submitted follow-ups inline with doctype, next step, response latency, and comment preview.
    - **Zero Drift:** The dashboard respects the exact same permission rules as the rest of the system. You only see what you are allowed to see.

3.  **Student / Guardian Portal Read State:**
    - Guardian-visible and student-visible log rows can show unread/read state per portal user.
    - **Server-Owned:** Read state is stored through `Portal Read Receipt`, not inferred from browser memory.
    - **Explicit Workflow:** Opening a visible log uses a named read action so the "New" badge does not reappear after refresh.

### Layer 3: Follow-Up (Closing the Loop)

The most critical failure point in schools is the "black hole" where notes disappear.

- **Explicit Routing:** If a note requires action, the author _must_ select a **Next Step** and an **Assignee**.
- **Immutable History:** Once follow-up work begins, the original note locks. Integrating follow-up preserves the integrity of the original observation.
- **Lightweight Follow-Up:** `Student Log Follow Up` is for quick operational updates by the current assignee, not for deep multi-party case management.
- **Referral Boundary:** If the situation becomes a deeper support case, staff should move it into `Student Referral` rather than stretching Student Log beyond its intended scope.
- **Focus Integration:**
  - The assignee receives a task in their **Focus** inbox.
  - When they complete the work, the task loops back to the author to **Review Intent**.
  - If the author reassigns, the log enters a new assignee cycle while keeping prior follow-up notes in timeline order.
  - **Result:** No loose ends. Every "Follow-up Required" note tracks through to completion.

---

## 3. Key Benefits by Role

### For Educators

- **Speed:** Log a note in seconds without leaving your attendance screen.
- **Clarity:** Know exactly who accounts for the follow-up.
- **Control:** You decide if a student or parent sees the note. It’s never automatic.

### For Academic Administrators & Decision Makers

- **Unified View:** See academic, pastoral, and behavioral data in one timeline.
- **Accountability:** Analytics show open follow-ups. Ensure no student slips through the cracks.
- **Premium Experience:** A modern, fast interface that respects your staff’s time.

### For IT System Specialists

- **Single Source of Truth:** No "shadow systems" or spreadsheets. All data resides in the Student Log doctype.
- **Canonical Permissions:** Security is enforced at the database level. Dashboards, reports, and UI all obey the same strict visibility rules (School Hierarchy + Role).
- **No Drift:** The UI (SPA) is strictly a client for server-side logic. Business rules are consistent via API.

---

## 4. Flexibility & Context Adaptation

No two schools are the same. Student Log is designed to adapt to your specific context without custom code:

- **School-Scoped Taxonomy:** Define **Log Types** (e.g., "Uniform Violation", "IB Learner Profile", "Merit") specific to _your_ school level. A High School can have different types than a Primary School.
- **Intelligent Routing:** **Next Steps** are linked to **Roles**, not specific people.
  - _Example:_ If you select "Refer to Counselor", the system dynamically routes the task to the counselor assigned to _that_ student's specific school context.
- **Policy Automation:** Each Next Step has its own **Auto-close** policy (e.g., "Minor incidents auto-close in 7 days involved"). This prevents backlog accumulation without administrative overhead.

---

## 5. Summary of Workflows

| Stage               | Action                                                         | System                       |
| :------------------ | :------------------------------------------------------------- | :--------------------------- |
| **1. Trigger**      | Teacher observes an issue during class.                        | **Attendance / Staff Home**  |
| **2. Capture**      | Teacher flags "Needs Follow-up", selects "Refer to Counselor". | **Student Log Overlay**      |
| **3. Notification** | Counselor sees item in **Morning Briefing** & **Focus** inbox. | **Dashboard / Notification** |
| **4. Action**       | Counselor meets student, adds **Follow-Up** note.              | **Student Log Follow-Up**    |
| **5. Closure**      | Teacher receives "Review Outcome" task. Closes case.           | **Focus**                    |

## 6. Student Log Evidence Attachment Contract

- Status: Implemented
- Purpose: Student Logs can carry governed evidence attachments such as photos, PDFs, or external evidence links without exposing raw private file paths to portals.
- Governance: File uploads use Ifitwala Drive workflow `student_log.evidence_attachment`; Drive owns file metadata, storage, derivative generation, and short-lived grants. Ifitwala Ed owns Student Log permissions, portal visibility, and surface DTO assembly.
- Upload permission: evidence upload is limited to the log author, the active follow-up assignee, scoped users with Student Log write access, and academic/system administrators. Students and guardians cannot upload Student Log evidence.
- Visibility: attachments are staff-only by default. Student portal access requires both parent `visible_to_student = 1` and row `visible_to_student = 1`; guardian portal access requires both parent `visible_to_guardians = 1` and row `visible_to_guardians = 1`.
- Surfaces: evidence is visible on the Student Log Desk form, Student Log Follow Up Desk form, Focus Student Log overlay, Student portal log detail, and Guardian Monitoring log cards.
- Preview/open: surfaces receive Ed-owned `open_url`, `preview_url`, `thumbnail_url`, and nested `attachment_preview` values. Clients must not guess `/private/...` paths or call Drive grants directly.
- Code refs: `ifitwala_ed/students/doctype/student_log/evidence.py`, `ifitwala_ed/api/student_log_attachments.py`, `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/student_log.py`, `ifitwala_ed/api/guardian_monitoring.py`, `ifitwala_ed/api/focus_context.py`, `ifitwala_ed/integrations/drive/workflow_specs.py`, `ifitwala_ed/integrations/drive/student_logs.py`
- Test refs: `ifitwala_ed/students/doctype/student_log/test_student_log_evidence_unit.py`

## 7. Student Logs Query Report Contract

- Status: Implemented
- Purpose: `Student Logs` is the canonical Desk query report for grouped Student Log review with inline follow-up history and a print-friendly record view.
- UX: The interactive report supports two reading modes. `Compact` shows truncated snippets in the grid, while `Full` renders the full Student Log body and full follow-up text on screen. The print template also renders the full Student Log body and full follow-up text.
- Permissions: Report access is server-owned. A user must satisfy both the report role list and the underlying `Student Log` DocType access checks. Being listed on the report does not bypass the `ref_doctype` gate.
- Visibility: Returned rows are filtered with the same `Student Log` visibility predicate used elsewhere in the feature. The report must not widen access beyond the canonical Student Log permission model.
- Scope: Filters support date range, student, program, school, academic year, log type, follow-up status, author, follow-up author, and whether follow-up is required. School filtering expands to descendants server-side.
- Concurrency: The report uses one bounded SQL path with a shared visibility predicate and grouped follow-up aggregation. It does not rely on client-side waterfalls or client-owned permission filtering.
- Code refs: `ifitwala_ed/students/report/student_logs/student_logs.py`, `ifitwala_ed/students/report/student_logs/student_logs.js`, `ifitwala_ed/students/report/student_logs/student_logs.html`, `ifitwala_ed/students/doctype/student_log/student_log.py`
- Test refs: No dedicated automated test file currently covers `Student Logs` query report behavior.

Student Log transforms observation from a passive record into an active tool for student success.
