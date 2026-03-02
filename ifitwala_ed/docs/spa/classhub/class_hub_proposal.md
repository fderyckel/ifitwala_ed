# Class Hub V1 Scope (Ifitwala_Ed)

Teacher “in-class cockpit” — **supports live teaching & learning only** (not planning, not full assessment workflows)

This is a **build spec**, anchored to your existing DocTypes. Where something is missing, I propose **minimal additions**.

---

## 0) Definition: what Class Hub is in v1

**Class Hub v1** is a **single teacher screen** for a **Student Group** that supports:

* starting/resuming a “session”
* seeing the roster + quick student signals
* doing fast checks for understanding (CFU) without leaving the room
* capturing lightweight evidence as “Teacher Observation”
* creating quick notes / follow-ups (if Student Log is already your pastoral spine)

It must work even when **no Lesson Instance exists yet**, and it must not force grading, planning, or complex workflows.

---

## 1) The v1 wireframe (exact sections, greyscale)

This is the Figma structure you must follow strictly.

### Header (fixed)

* Breadcrumb: Staff → Class Hub → **Student Group**
* “Now chip”: **Rotation Day + Block + time range + location**
* Actions (right):

  1. **Start/Resume Session**
  2. **Quick Evidence**
  3. **End Session**

### Section A — TODAY (max 3 lines)

Plain text list; each line opens an overlay. No badges/counters.

### Section B — STUDENTS IN FOCUS (3–5 chips)

Names only; click opens Student Context overlay.

### Section C — MY TEACHING (2-column)

**Left: Notes & Observations**
**Right: Tasks & Evidence** *(actionable only, no grades/averages)*

### Section D — CLASS PULSE (2–3 sentences)

Text-only indicators; click navigates to analytics page (not overlay).

### Section E — MY FOLLOW-UPS (1–3 lines)

Text-only; click opens follow-up overlay; items disappear by server truth.

**Figma guardrails** (hard)

* Greyscale only
* No charts
* No urgency colors
* No full roster tables
* No sorting/filtering controls
* No content tree, no messaging, no settings

---

## 2) Doctype anchors (what powers each section)

### 2.1 Class identity & roster (already exists)

* **Student Group**

  * required for hub: `name`, `student_group_abbreviation`, `academic_year`, `course`, `school`, `program_offering`
* **Student Group Student** (child)

  * required: `student`, `student_name`, `active`
* **Student Group Instructor** (child)

  * required: `instructor`, `user_id`, `instructor_name`

**V1 rule:** Teacher can open Class Hub only if their user_id is present in Student Group Instructor OR they pass the server permission check.

---

### 2.2 “Now” context (schedule truth; already exists)

* **Student Group Schedule** (child table)

  * required: `rotation_day` (int), `block_number` (int), `from_time`, `to_time`, `location`, `instructor`

**V1 “Now” resolution**

* Input: `student_group`, `date` (today)
* Server resolves rotation day for date (from School Calendar; you uploaded but not yet cited here)
* Finds matching Student Group Schedule row for that rotation day (and optionally block if routed from timetable)

---

### 2.3 “What we’re doing” in session (delivery truth)

* **Lesson Instance**
  This is your best “session container” (and your doctype description explicitly says it is lightweight and not required for grading).

**But Lesson Instance currently lacks a few fields needed for Class Hub v1** (see Section 3).

---

### 2.4 Evidence capture (already exists and is perfect for Hub)

* **Task Submission** — must support “Teacher Observation” origin (this is exactly what you want for in-class evidence).
* **Task / Task Delivery / Task Outcome / Task Contribution** exist; Hub will only touch them when needed (mostly via Task Submission creation, and optionally minimal task review entry points).

---

### 2.5 Curriculum context (read-only)

* **Course** (exists)
* **Learning Unit / Lesson / Lesson Activity**
  Lesson is already structured and published flag exists.
  Lesson Activity table exists for activities.
* **Learning Unit Standard Alignment** exists (child table).

**V1 rule:** Class Hub shows only read-only lesson/activity label if linked; no planning UI.

---

## 3) Minimal schema additions for V1 (proposal)

### 3.1 Add fields to Lesson Instance (recommended)

Lesson Instance currently has: lesson, lesson_activity, student_group, course, academic_year, instance_type, from/to time/date, created_from, created_by.

**Add these v1 fields** to support the hub as a live teaching workspace:

1. `session_mode` (Select)

   * Options: `Scheduled` / `Ad-hoc`
   * Default: `Scheduled` when created from timetable

2. `live_success_criteria` (Small Text)

   * “What students must be able to do by end of this session” (1–2 lines)

3. `class_notes` (Text Editor)

   * Teacher scratchpad for the session

4. `started_at` (Datetime) and `ended_at` (Datetime)

   * Supports “Start/End Session” buttons (and later analytics)

> Keep it light. No planning fields. No unit plans. No resources library.

---

### 3.2 Add child table “Lesson Instance Signal” (optional but high value)

This avoids forcing a Task Submission for every micro-signal.

**New child table doctype**: `Lesson Instance Signal` (istable=1)
Fields:

* `student` (Link Student)
* `signal` (Select: `Not Yet` / `Almost` / `Got It` / `Exceeded`)
* `note` (Small Text)
* `updated_at` (Datetime, optional)
* `source` (Select: `CFU` / `Teacher`) optional

**Attach to Lesson Instance**: field `signals` (Table → Lesson Instance Signal)

**Why:** This enables “make learning visible” in-class without grading.

If you want to keep v1 even tighter: skip the child table and store a minimal JSON snapshot field on Lesson Instance. But the child table is more queryable and cleaner.

---

## 4) V1 features, explicitly scoped

### Feature 1 — Open Class Hub (route)

**Route input:** `student_group` (required)
**Optional:** `date`, `block_number`

**Hub loads:**

* header context (Student Group + “Now” schedule info)
* session state (Lesson Instance for today/block if exists)
* roster + focus students
* today items
* follow-ups items
* notes previews (teacher-authored)
* task action items (minimal)
* class pulse statements (2–3)

**Performance rule:** Prefer **one bundle endpoint** for this (see Section 6).

---

### Feature 2 — Start/Resume Session

**If no Lesson Instance exists** for (student_group, date, block):

* create Lesson Instance

  * `student_group`, `from_date`, `to_date` (today), `instance_type="Scheduled Session"`
  * copy `course`, `academic_year` from student_group (already fetch_from exists)
  * set `created_from="Timetable"`
  * set `created_by=frappe.session.user`
  * set `started_at=now`

**If exists:** open the session overlay / bring into state.

---

### Feature 3 — End Session

* sets `ended_at=now`
* does **not** force any submissions, tasks, or grades
* closes any “session state” UI locally after server confirms

---

### Feature 4 — Students Grid (uniform cards)

From Student Group Student (active=1).
Each card shows:

* student_name
* attendance state (if your attendance tool exists; if not, hide in v1)
* today evidence count (Task Submission counts with origin Teacher Observation)
* latest signal (from Lesson Instance Signal table if you implement it)
* tiny “note dot” if teacher wrote a note today

**Click = Student Context overlay** (Feature 7)

---

### Feature 5 — Quick CFU (check for understanding) overlay

From Class Hub, teacher selects a CFU type:

* Thumbs
* Mini-whiteboard
* Exit ticket (lightweight, not a full task)
* Quick poll

**V1 output:** stores per-student signals (Lesson Instance Signal) or stores a class snapshot in Lesson Instance.

No grading. No task creation required.

---

### Feature 6 — Quick Evidence overlay

**Purpose:** capture evidence with near-zero friction.

Teacher selects:

* student(s) (multi-select)
* evidence type: text note / upload / link / photo
* optional tags (v1: plain text)

**V1 storage:**

* creates Task Submission(s) with `submission_origin="Teacher Observation"`
* links to `lesson_instance` if possible (if Task Submission supports that field; if not, we propose adding a link field—see below)

**If Task Submission currently cannot link to Lesson Instance:**

* **Proposal:** add `lesson_instance` (Link Lesson Instance) to Task Submission.
  This is a small, high-value join for analytics and “today’s evidence” retrieval.

---

### Feature 7 — Student Context overlay

Shows three tabs (read-only + quick entry):

1. Snapshot

* current signal selector (writes Lesson Instance Signal)

2. Evidence

* list of today’s teacher-observation submissions
* button “Add evidence” (opens Quick Evidence overlay prefilled to that student)

3. Notes

* quick note (either creates Student Log OR writes to class_notes + signal note)

**Important choice for v1:**
If you want pastoral notes separate from evidence, keep Student Log.
If you want “classroom-only notes,” keep it in Lesson Instance.
We can support both, but you should pick one as the default to avoid duplicates.

---

### Feature 8 — Today list (max 3 lines)

Generated server-side based on:

* pending quick follow-ups (focus)
* actionable task review items
* session focus text (if any)

Each line opens an overlay.

---

### Feature 9 — Notes & Observations list (left column)

Displays teacher-authored notes/evidence (choose one source for v1):

* **Option A (recommended):** show recent Teacher Observation submissions (Task Submission origin)
* **Option B:** show Student Log notes if you want pastoral integration

Keep it 3–5 items max.

---

### Feature 10 — Tasks & Evidence list (right column)

Only show actionable items:

* submissions pending review
* tasks that need teacher action

No gradebook, no averages.

---

### Feature 11 — Class Pulse (2–3 statements)

Simple sentences derived server-side:

* “3 students marked Not Yet”
* “5 students missing evidence today”
* “Attendance irregular this week” (only if attendance exists)

Click navigates to analytics page (out of scope to build fully; ok to link to placeholder route in v1).

---

## 5) Explicit out-of-scope (hard guardrails)

Not in Class Hub v1:

* planning UI (unit plans, lesson plan editor, resources library)
* grading workflows / rubrics / moderation
* full roster management
* messaging / announcements
* filters/sorting/power user tables
* charts/dashboards inside Hub
* multi-class overview (that’s Staff Home / Morning Briefing)

---

## 6) Required server endpoints (bundle-first)

### V1 endpoint: `class_hub.get_bundle(student_group, date?, block_number?)`

Returns everything the hub needs in **one** call.

Payload (conceptual):

```json
{
  "header": { ... },
  "now": { ... },
  "session": { ... },
  "today_items": [ ... ],
  "focus_students": [ ... ],
  "students": [ ... ],
  "notes_preview": [ ... ],
  "task_items": [ ... ],
  "pulse_items": [ ... ],
  "follow_up_items": [ ... ]
}
```

### Workflow endpoints (each overlay does one thing)

* `class_hub.start_session(...)` → creates/returns Lesson Instance, sets started_at
* `class_hub.end_session(lesson_instance)` → sets ended_at
* `class_hub.save_signals(lesson_instance, signals[])` → upsert Lesson Instance Signal rows
* `class_hub.quick_evidence(...)` → creates Task Submission(s) origin Teacher Observation
* `class_hub.student_context_bundle(student, student_group, lesson_instance)` → tiny bundle for the student overlay

All must:

* enforce permissions server-side
* avoid N+1
* accept explicit keyword args (no form_dict usage)

---

## 7) What you must confirm / what I will verify from your uploaded JSON

I can’t responsibly assume these without checking the actual JSON you uploaded:

1. Does **Task Submission** already have a Link field to `Lesson Instance`?

   * If not: add it (recommended).

2. What is the exact **Task Submission** fieldname for origin?

   * You have `submission_origin` options including Teacher Observation.
   * We will use that exact field.

3. Whether **Student Log** is in Class Hub v1 or kept separate:

   * I recommend defaulting to classroom evidence in Task Submission and keeping Student Log for pastoral, but you decide.

---

## 8) Deliverable checklist (what “done” means for v1)

### Figma

* [ ] One greyscale frame matching the wireframe sections exactly
* [ ] Click annotations for every interaction (“opens overlay X”)

### Backend

* [ ] Bundle endpoint returns full hub payload in one call
* [ ] Start/End session endpoints update Lesson Instance
* [ ] Signals storage implemented (child table or JSON snapshot)
* [ ] Quick evidence creates Teacher Observation submissions

### Frontend (SPA)

* [ ] One ClassHub page renders bundle data (no inference)
* [ ] Student cards uniform size grid
* [ ] Overlays: Student Context, Quick Evidence, Quick CFU
* [ ] No internal links with `/hub/` prefix

---
