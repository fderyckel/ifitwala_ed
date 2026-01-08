Ifitwala Ed is a **Unified Institutional Operating System for Education** that replaces fragmented tools with one coherent data model, one permission system, and one analytics surface — without forcing everyone into the same experience.

# 🌱 Ifitwala_Ed

**Ifitwala_Ed** is a **full-scale, modern Education ERP** built on the **Frappe Framework**, designed for **schools, colleges, universities, and post-secondary institutions** that want **clarity, insight, and long-term control** over their systems.

It is **not tied to a single educational model, curriculum, or age group**.
It is built as **foundational infrastructure for education**, adaptable from early years through higher education.

---

## 🏛️ The Core: Hierarchy & "One Truth"

The central promise of Ifitwala_Ed is that **system architecture mirrors institutional reality**. We do not sync data between modules; we reference single sources of truth that respect your organizational structure.

### 🌳 The Power of Hierarchy (NestedSet)
Institutions are deeply hierarchical: *Organizations → Schools → Programs → Courses → Groups*.
Ifitwala_Ed models this natively using **Nested Sets**.
*   **Inheritance**: A policy set at the "High School" level automatically applies to all programs within it.
*   **Scoped Permissions**: "Not two people see the same thing." A Head of Department sees analytics for their department; a Principal sees the school; a Group Tutor sees their cohort.
*   **Contextual Analytics**: All dashboards allow filtering by hierarchy, letting you drill down from "Whole System" to "Single Student" instantly.

### 📅 The Uncompromised Calendar
Most systems separate "Timetables" (Academic) from "Calendars" (Administrative). This leads to double-bookings and invisible conflicts.

**Ifitwala_Ed unifies them.**
*   **Teaching**: Generated from term schedules.
*   **Meetings**: Staff and departmental collaboration.
*   **School Events**: Whole-school or cohort-specific events.

All three exist on the **same time-surface**, respecting the same constraints.

### 📍 Resource Truth (Fact Tables)
We eliminate "Double Booking"—not just for rooms, but for **people**.
*   **Location Booking**: The single source of truth for spaces. If a room is seemingly free in the schedule but booked for a meeting, `Location Booking` knows.
*   **Employee Booking**: The single source of truth for staff availability. It tracks teaching, meetings, and leaves in one place.

> **Operational Guarantee**: Availability queries never *infer* state from schedule patterns; they check the fact table. If it's in the table, the resource (room or person) is busy.

---

## 🧩 Module Deep Dive

### 🎓 Assessment & Attendance
We treat **Assessment as a Mode**, not the identity of a task.
*   **3-Layer Architecture**: Task Outcome (Fact) / Task Submission (Evidence) / Task Contribution (Judgment).
*   **Flexible Grading**: Supports Points, Criteria (Rubrics), Binary, or Completion-only.
*   **Attendance**: Integrated fully with the schedule. Mark attendance for a "Class Event" and it flows into the student's log and report card automatically.

### 📢 Communication Platform
A powerful engine to reach exactly the right people, without spamming the rest.
*   **Flexible Audiences**: Target by *Team* (Staff), *Student Group* (Academic), *School* (Whole entity), or specific lists.
*   **Morning Brief**: A daily digest for staff and students, aggregating what *they* need to know based on their role and hierarchy.
*   **Communication Archive**: A searchable history of all institutional announcements, ensuring institutional memory.
*   **Reach Analytics**: Know who read what, and when.

### 🏥 Health & Wellbeing
A complete medical record system, fully integrated with the student profile.
*   **Patient Visits**: Track nurse visits with timestamps and outcomes.
*   **Notifications**: Automatically notify the relevant instructor when a student is at the nurse.
*   **Vaccinations & Medical History**: Secure, permission-gated records.

### 🧾 Admissions & Enrollment
An auditable, pipeline-driven process that ensures no lead is lost.
*   **The Pipeline**: `Registration of Interest` → `Inquiry` → `Student Applicant` → `Student`.
*   **Analytics**: Enrollment trend reporting and demographic analysis.
*   **Guardians**: Linked automatically to students, ensuring accurate communication lines from Day 1.

### 📚 Curriculum & Learning
*   **Structure**: `Program` → `Course` → `Learning Unit` → `Lesson`.
*   **Standards**: align learning content with institutional or external standards.
*   **Planning**: Curriculum mapping and unit planning tools built-in.

### 🗓️ Scheduling & Operations
*   **Conflict-Free by Design**: Powered by the `Location Booking` and `Employee Booking` engines.
*   **Utilization Analytics**: Built-in dashboards to track room usage efficiency across the entire campus.
*   **Staff Workload**: Integrated view of teaching hours, meetings, and duties.

---

## 🚀 The Experience

### For Staff: The "Staff SPA"
We have invested in a dedicated **Single Page Application (SPA)** for staff, built with **Vue 3 + Tailwind CSS**.
*   It is **not** just standard Frappe desk views.
*   It is a premium, app-like experience designed for speed and clarity.
*   Includes the **Staff Analytics** dashboard and the **Grading Drawer**.

### For Students & Guardians: Portals
Tailored portals provide:
*   **Live Schedules**: Always in sync with the master calendar.
*   **Task Lists**: To-do items, upcoming deadlines, and feedback.
*   **Report Cards**: Digital, accessible academic history.
*   **Permissions**: Parents see *their* children; students see *their* tasks.

---

## 🛠️ Technology Stack

Ifitwala_Ed uses open-source, industry-standard technologies to ensure long-term sustainability:

*   **Backend**: [Frappe Framework](https://frappe.io/framework) (Python, MariaDB, Redis, Node.js).
*   **Frontend**: Vue 3, Tailwind CSS, Frappe UI.
*   **API**: REST & RPC endpoints for seamless integration.

---

## 📊 Analytics Surface

Ifitwala_Ed is built **from day one for institutional analytics**.
Because data is unified and hierarchical assumptions are built-in:
*   **Student Demographics**: Gender, nationality, and residency profiles.
*   **Enrollment Trends**: Longitudinal tracking of student population.
*   **Assessment Analytics**: Breakdown of academic performance by cohort or criteria.

---

## 🎯 Who This Is For

Ifitwala_Ed is a strong fit for:
*   **International schools** replacing disconnected SIS + LMS + Scheduling tools.
*   **Colleges & Universities** wanting a unified academic backbone.
*   **Multi-campus groups** needing standardisation.

If your institution currently relies on **multiple disconnected platforms**,
👉 **Ifitwala_Ed is designed to replace them with one coherent system.**

---

## 📬 Get in Touch

If you are exploring **modern, open, analytics-driven infrastructure for education**:

📧 **Email:** [f.deryckel@gmail.com](mailto:f.deryckel@gmail.com)

Conversations are welcome — especially with educators, institutional leaders, and technical teams thinking long-term.

---

## 🧩 Why Replacing the Stack Matters

**Replacing tools is not the goal. Replacing fragmentation is.**

Most educational institutions operate on a fragile stack of 5–10 disconnected systems.
**Ifitwala_Ed eliminates fragmentation at its root** by providing:
*   ✅ **One data model**
*   ✅ **One source of truth**
*   ✅ **One permission system**
*   ✅ **One analytics surface**

This is what makes insight reliable — and action possible.
