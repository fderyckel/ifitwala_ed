# Ifitwala_Ed — Gradebook UX Flow Sketch (Thin Spec)

Status: **UX LOCK DRAFT (Thin)**
Audience: Product + Engineering + Codex agents
Goal: A teacher should grade and return work with **minimum clicks** and **zero doctype awareness**.
Last updated: 2026-04-11

---

## 0. Principle

Back-end complexity (Delivery / Outcome / Submission / Contribution) is allowed.
**Teacher UX must feel like one object:** “this task for this student”.

The teacher interacts with:

* **Gradebook grid** (overview)
* **Grading Drawer** (details + actions)

Teachers must never navigate to doctypes.

---

## 1. Surfaces

### 1.1 Gradebook Page (Primary)

**Default mental model:** *Delivery-centric gradebook*

* Teachers think: “I’m grading **this assignment** for my class.”
* Student-centric is a secondary tool (interventions), not the default grading surface.
* Staff surfaces that already own class context, especially `ClassPlanning.vue`, should deep-link into Gradebook with `student_group` + `task` (`Task Delivery`) query context so the teacher lands on the exact delivery without reselecting it.
* Runtime shape is now a **dual-mode gradebook**:
  * **Task View** stays the default and optimized grading path.
  * **Overview** is a bounded class matrix for scanning all students across recent deliveries in one group.
* Overview must remain a secondary mode and must not add latency or request fan-out to the default task-first grading loop.

#### A) Context & Filters (top bar)

Always visible:

* School (role-defaulted)
* Academic Year (role-defaulted)

Primary filters (in order):

1. Course (required)
2. Student Group (required)
3. Time scope (Date range pills + optional calendar picker)

Secondary filters (collapsed by default):

* Delivery Mode: Assess | Collect | Assign Only (multi-select)

  * Default selected: **Assess** only
* Status filters: Missing, Late, Needs Review, Needs Moderation, Released
* Teacher scope: My student groups / All permitted (role-gated)

UX rule:

* Prevent “filter spaghetti” by collapsing advanced filters and showing active filter chips.

#### B) Delivery List (left rail or top row selector)

Default: show Deliveries within the chosen time scope.

* Displays: task title, due date, mode badge, status counts (e.g., Missing 3)
* Select one Delivery → renders grid

Why:

* avoids a 30-column grid
* keeps focus and speed

#### C) Gradebook Grid (main)

Grid is always:

* Rows: Students
* Columns: **One selected Delivery** in **Task View** (default) OR recent deliveries in **Overview** mode

**Default column mode:** single-delivery

* Keeps the primary grading workflow fast.
* Overview mode must lazy-load only when selected and must use one bounded aggregated read for the chosen student group.

Cell content rules (one glance, no clutter):

* Assess:

  * primary: Official grade/score (or “—”)
  * secondary: status dot
  * badges: New Evidence, Needs Review, Needs Moderation
  * comment box: only when the delivery explicitly allows comments
* Collect Work:

  * primary: Submitted / Late / Missing
  * badges: New Evidence
  * comment box: only when the delivery explicitly allows comments
* Assign Only:

  * primary: Complete checkbox
  * comment box: only when the delivery explicitly allows comments

**Click target:** the whole cell.
Click opens drawer.

Gradebook grid reads:

* Task Outcome rows (one per student × delivery)
* per‑criterion official values from Task Outcome Criterion (flattened for UI)

Strategy behavior:

* Separate Criteria → show criterion values only (no total column).
* Sum Total → show criterion values and the computed total/grade.

**Warning:** Gradebook must never compute totals client‑side. It only renders derived fields from outcome services.

---

### 1.2 Grading Drawer (Secondary)

Drawer is the **only** place to grade, compare, review, moderate, and release.

Default tab: **My Marking** (editable)
Secondary tabs (order):

1. Evidence
2. Official Result
3. Compare
4. Review / Moderation (role-gated)

Hard UX rule:

* The grid never shows multiple teacher marks.
* Comparisons exist only inside Compare tab.

If there is no submission:

* Drawer shows “No digital submission”
* Teacher can still grade
* System auto‑creates an Evidence Stub submission behind the scenes when `requires_submission = 1`
* Optional note field (e.g., “Paper collected in class”)

---

### 1.3 Student-centric View (Secondary)

Purpose: interventions and student support.
Not used for bulk grading.

* Select a student → shows timeline of Deliveries and outcomes
* Useful for: missing patterns, support plans, parent meetings

---

## 2. Core Flows (Teacher)

### Flow A — Quick Grade (Assess)

**Goal:** grade in <10 seconds per student.

1. Teacher clicks a cell
2. Drawer opens → My Contribution (editable)
3. Teacher enters:

   * Points OR Criteria levels OR quick grade
   * Optional comment, only when the delivery allows comments
4. Teacher hits **Save** (creates/updates Contribution)
5. UI updates cell optimistically

**Auto-behavior**

* If moderation is OFF: outcome can auto-finalize
* If moderation is ON: outcome remains “In Progress / Needs Review” until teacher action

---

### Flow B — Collect Work (No grading)

1. Teacher clicks a cell
2. Drawer opens → Evidence panel
3. Teacher leaves a comment only if the delivery allows comments
4. Teacher hits Save

Outcome stays non-graded; no score required.

---

### Flow C — Assign Only (Completion)

1. Teacher clicks a cell
2. Drawer opens → Completion toggle
3. Teacher marks complete (or student self-marks in portal later)

No grade, no submission required.

---

## 3. Evidence & Resubmission (Staleness)

### Flow D — Student Resubmits

Trigger: Student submits or resubmits (new submission version created by student).

System sets on Outcome:

* `has_new_submission = 1`
* existing teacher Contributions flagged `is_stale = 1`

Teacher‑created evidence stubs do **not** create “new evidence” badges.

**Gradebook grid** must show a clear badge:

* “New evidence”

Teacher clicks cell → Drawer shows:

* Latest submission version (default)
* Previous versions accessible via History

Policy toggle:

* Either reset grading status to “Not Started”
* Or keep grading status but show warning

---

## 4. Multi-Teacher Collaboration

### Flow E — Informal Peer Review (Your definition of moderation)

**Intent:** ask another teacher “What would you give?”

1. Teacher grades (My Contribution)
2. Teacher clicks **Request Review**
3. Select reviewer(s) (teachers on the group)
4. Reviewer creates a **Peer Review** Contribution
5. Original teacher sees Compare view highlighting differences

**Important UX rule**

* The grid never shows multiple grades.
* Comparisons live only inside the drawer.

---

### Flow F — Formal Moderation (Policy-driven)

**Intent:** compliance moderation / release gate

1. Teacher clicks **Send for Moderation**
2. Outcome status becomes “Needs Moderation”
3. Moderator opens drawer and can:

   * Approve → status “Moderated”
   * Adjust (creates Moderation contribution and updates Official Outcome) → “Moderated”
   * Return to Grader (Kickback) with internal note → status back to “In Progress”

---

## 5. Finalization vs Release

### Flow G — Finalize

Finalization means: teacher commits an official outcome value.

* If allowed, teacher can set Official Outcome from their contribution.
* If moderation required, finalization may be blocked until moderation completed.

### Flow H — Release / Return to Students

Release means: students/guardians can see the official outcome + feedback.

1. Teacher clicks **Release**
2. Outcome grading_status becomes “Released”
3. Student portal shows the outcome

Release should support:

* Release per student
* Release per delivery (bulk)

---

## 6. Group Submission UX

When group_submission is enabled:

* Cell shows “Submitted (Group)”
* Drawer shows uploader + group members
* Teacher can still grade each student individually

If someone diverges:

* new submission breaks group link for that student

---

## 7. Minimum Clicks Targets (Non-negotiable)

* Open student grading: **1 click** (cell)
* Enter grade + save: **1 save action**
* Request peer review: **2 clicks + select**
* Compare grades: **1 click** (Compare tab)
* Release to students: **1 click** (Release)

---

## 8. What the UI must hide

Teachers must not see:

* Delivery IDs
* Outcome IDs
* Submission versions as database objects
* Contribution rows as separate documents

They see:

* “My marking”
* “Official result”
* “Evidence”
* “History / Compare”

---

## 9. Developer Notes (Implementation Contract)

* Gradebook grid queries **Task Outcome** + **Task Outcome Criterion** as the fact tables.
* Drawer fetches:

  * Outcome
  * latest submission(s)
  * teacher’s contribution
  * optional compare contributions
* Writes go through server APIs:

  * submit_contribution
  * set_official_outcome (policy-driven)
  * request_review / send_for_moderation
  * release_outcome

* Gradebook API (`api/gradebook.py`) orchestrates only; it does not compute grades.
* Writes go to services; services may create Evidence Stub submissions when missing and `requires_submission = 1`.
* Frontend can omit `task_submission` in grade actions; backend will attach to latest student submission if present, else create a stub when required.
* Instructor-scoped users only see deliveries for taught student groups; course filters narrow scope but never broaden it.

**Canonical statement:** A Task Outcome always stores official results per criterion. Task totals are optional and only computed when the delivery strategy allows it.




## MODAL FOR CREATING TASKS

UI + Architecture Note: Fast Task Creation (Teacher-Centric)
Goal

Teachers should feel like they are creating one thing: “a task for my class”.
Behind the scenes, the system creates/uses the right objects (Task + Delivery + Outcomes) without exposing them.

The one modal that does everything
Entry points

Primary: + New button on Gradebook / Class page

Secondary: Reuse from Library (templates)

Modal name

Assign Task (not “Create Task”, not “Delivery”)

Modal structure (progressive disclosure)

Step 1 — What

Title (required)

Instructions (optional)

Attachments / link (optional)

Shared reuse control:

- default for new work created from class or session context should be **This class only**
- promotion into shared reusable task or common-assessment space should be an explicit later action
- the current workspace does not yet expose a dedicated promotion workflow, so no flow should silently treat new class-authored work as shared baseline by default

Step 2 — Who

Course (pre-filled from current page, required)

Student Group (required)

Optional: group submission toggle (hidden unless Collect/Assess)

Step 3 — How
A single choice, large buttons (default highlighted):

Assign only (default)

Collect work

Assess

Step 4 — When

Available from (optional)

Due date (optional)

Lock date (optional)

Late submission policy (shown only when Collect/Assess)

Footer

Primary button: Assign

Secondary: Save Draft (optional)

What happens in the backend (invisible to teachers)
Common to all modes (always)

Ensure there is a Task definition:

If teacher intentionally selects from a shared library: reuse existing Task

If teacher typed/edited new class-specific content: create a new Task definition plus one class-scoped Task Delivery

Do not silently promote that new class-authored work into shared library or common-assessment space

Optional Task.course can be stamped for library filtering (tagging)

Create one Task Delivery (the authoritative context):

Always required: student_group

Stamps/denormalizes: course, academic_year, school, (program if you use it)

Stores: dates + delivery_mode + policy flags

On Task Delivery submit: create Task Outcome rows in bulk

One Outcome per student in the group

This is your fact table for the gradebook grid

Denormalize again on Outcome: school/AY/course/etc. so gradebook queries don’t do deep joins

Mode-specific behavior
A) Assign Only

Teacher intent: give work; track completion if needed; no submissions, no grading.

Modal defaults

Delivery mode: Assign only

Requires submission: OFF (hidden)

Grade options hidden

Backend behavior

Outcomes created with:

submission_status = Not Required

grading_status = Not Applicable

Optional: is_complete toggled later (teacher or student, future)

UI placement

Appears in class feed / student agenda

Not shown in gradebook by default

B) Collect Work

Teacher intent: students submit evidence; feedback optional; not necessarily graded.

Modal shows

Submission requirements (File/Text/Link toggles)

Late submissions toggle

Backend behavior

Outcomes created with:

submission_status = Not Submitted initially

grading_status = Not Applicable (unless teacher later switches to Assess)

Submissions are created only when students submit (versioned)

UI placement

Appears in “To collect” queue and optionally in gradebook when teacher toggles Collect mode

C) Assess

Teacher intent: this goes into the gradebook and analytics.

Modal shows

Grading mode selector:

Points

Criteria/Rubric

Only show rubric picker if “Criteria” chosen

If rubric is picked, allow a lightweight “adjust weights / select criteria” (optional now)

Backend behavior

Outcomes created with:

grading_status = Not Started (or In Progress depending on policy)

If Criteria: create a Task Rubric Version snapshot at delivery submit

Teacher grading creates Task Contributions, which roll up into the Official Outcome per policy

UI placement

Shown in gradebook by default

Group submission UX + architecture (teacher never manages this)

If group_submission enabled on Delivery:

UI shows “Submitted (Group)” for all members after one upload

Backend uses clone + group_submission_id so each student still has a 1:1 submission linked to their outcome

Teachers can grade each student individually without any weird joins

Teacher experience after assigning (what they see)

They go to Gradebook

Pick a delivery from the Delivery list

Click a student cell → Grading Drawer

Default tab: My Marking

They never open doctypes, never hunt records

Why this matters for performance and sanity

One modal minimizes clicks and reduces teacher error

Gradebook grid reads from Task Outcome + Task Outcome Criterion only (fast)

Everything else loads lazily in the drawer

If you want the next increment, I’ll write the exact modal copy (button labels, help text, microcopy) so it feels premium and unambiguous for busy teachers.

---

## Architecture lock notes

- Autosave uses Draft Contributions, not Submissions. Draft save must never create evidence stubs and must never flip has_new_submission.
- save_draft() is idempotent: it upserts the current user's draft for an outcome and returns the draft id.

---

Good — this is exactly the right moment to write it.
Below is a **clean, copy-paste-ready UX Contract** you can drop straight into your notes and treat as **authoritative**.

I’m deliberately writing this as something that can be enforced against code, not marketing fluff.

---

# 🎓 Ifitwala_Ed — Teacher UX Contract (Assessment & Gradebook)

**Status:** Authoritative
**Audience:** Teachers, UI developers, coding agents
**Scope:** Task creation, submission, grading, moderation, release
**Primary principle:** *Teacher clarity over system completeness*

---

## 1. Core Teacher Mental Model (Non-Negotiable)

Teachers experience the system as **four simple concepts**:

1. **Assignment** – “Something I ask students to do”
2. **Student Work** – “What students submitted (or what I observed)”
3. **Feedback & Grade** – “My professional judgement”
4. **Release** – “When students and families can see it”

The system **must never expose**:

* internal concepts like *Outcome*, *Contribution*, *Rubric Version*
* technical workflows (autosave, moderation precedence, staleness)

> The system adapts to complexity.
> The teacher never has to.

---

## 2. Vocabulary & Language Lock (i18n-Friendly)

All teacher-facing strings **must** come from translation keys.

### Canonical Teacher Vocabulary

| Internal Concept    | Teacher-Facing Term                 | Notes                                    |
| ------------------- | ----------------------------------- | ---------------------------------------- |
| Task                | **Assignment**                      | Always singular in UI                    |
| Task Delivery       | **Assignment**                      | Never surfaced separately                |
| Task Outcome        | *Never shown*                       | Backend only                             |
| Submission          | **Student Work**                    | Includes uploads or teacher observations |
| Contribution        | *Never shown*                       | Backend only                             |
| Draft Contribution  | **Saved draft**                     | Not “draft contribution”                 |
| Submit Contribution | **Mark as ready**                   | Avoid “submit” ambiguity                 |
| Official Grade      | **Teacher grade**                   | Not “official”                           |
| Moderation          | **Moderation**                      | Peer check, not peer grading             |
| Is Published        | **Released to students**            | Binary mental model                      |
| Published           | **Visible to students & guardians** | Explicit audience                        |

### Forbidden Language (Never in UI)

* “Official”
* “Contribution”
* “Outcome”
* “Rubric version”
* “Stale”
* “Override”
* “Finalize” (unless very carefully contextualised)

---

## 3. Teacher Actions Model (What Teachers Can Do)

Teachers have **only these actions**:

### Assignment Creation

* Create assignment from:

  * Student Group
  * Course
  * Calendar event
* Choose:

  * Due date (optional)
  * Grading type (Score / Grade / Criteria / Feedback only)
* Save immediately (no multi-step wizard)

### While Grading

* View student work
* Write feedback
* Select grade or criteria levels
* Autosave happens silently
* Explicit action: **Mark as ready**

### Moderation (Teacher-to-Teacher)

* Moderator can:

  * Approve
  * Return to teacher with note
* Teacher sees moderation feedback clearly
* Moderation is **never visible to students**

### Release

* Teacher explicitly clicks **Release**
* Release controls visibility to:

  * Students
  * Guardians
* No automatic release

---

## 4. Autosave & Safety Guarantees (Teacher Trust)

The system **must guarantee**:

* Typed feedback is never lost
* Grades are never lost
* Network interruption does not destroy work

### Autosave Rules (Teacher-Facing Behaviour)

* Autosave occurs automatically
* UI shows:

  * “Saving…”
  * “Saved”
  * “Offline – changes will sync”
* Teacher never needs to click “Save”
* “Mark as ready” is **not** a save action — it is a status change

> If a teacher walks away mid-grading, their work must still be there.

---

## 5. Visibility & Release Rules (Critical Separation)

**Teacher grading ≠ Student visibility**

### Internal Truth

* Teacher grade & feedback exist immediately
* Used for:

  * moderation
  * reports
  * teacher review

### External Visibility

* Nothing is visible until **Release**
* Release is:

  * explicit
  * reversible (until reporting locks)

UI must clearly distinguish:

> “This is saved”
> vs
> “This is visible to students”

---

## 6. Gradebook UX Principles

### Grid View

* Shows:

  * Students × Assignments
* Cell indicators:

  * No work
  * Student work received
  * Teacher feedback started
  * Ready
  * Released

No numbers unless teacher opens the cell.

### Drawer View (Single Student × Assignment)

* Focused
* Calm
* No distractions
* One mental task at a time

---

## 7. Role Boundaries (Teacher-Centric)

### Teachers See

* Only their:

  * Assignments
  * Courses
  * Student groups
* No cross-course visibility

### Academic Admin / Coordinators

* Can see broader scope
* UI language remains teacher-friendly
* Extra controls are additive, not invasive

---

## 8. Explicit Non-Goals (Guardrails)

The UI must **not**:

* Expose backend architecture
* Require teachers to understand states
* Auto-release grades
* Mix grading and publishing actions
* Use technical jargon
* Present warnings unless action is required

---

## 9. Enforcement Rule (For Code & Agents)

Any UI, API, or Vue component that:

* uses forbidden vocabulary
* exposes internal states
* bypasses autosave guarantees
* releases grades implicitly

👉 **is a regression and must be rejected**

---

## 10. One-Line Product Promise

> *“Teachers can focus on feedback and judgement.
> The system handles complexity, safety, and timing.”*

---
