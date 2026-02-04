## 1) Restating our Class Hub direction (what we already decided)

### Class Hub is the teacher’s “in-class cockpit”

Not a content editor, not a planner, not a gradebook. It’s the place a teacher lives **while teaching**, where the system reduces cognitive load and increases instructional agency:

* **One screen for “who’s here, what we’re doing, what I need to notice, what I should do next.”**
* Optimized for **fast moves**: quick checks for understanding, grouping, noting misconceptions, capturing evidence, nudging feedback loops.

### The SPA must stay “dumb” (server truth wins)

We locked this: the SPA triggers actions and renders state; it does not infer workflow, does not do business logic, does not close loops by itself.

### UI architecture rules that shape the Class Hub UX

These are non-negotiable and directly affect wireframes:

* **One overlay system** via `OverlayHost` + HeadlessUI Dialog.
* **Overlay owns closing; services own orchestration** (A+ contract).
* **createResource + submit(flat payload)** only; no fetch/frappe.call/query hacks.
* **Typography must be semantic** (`.type-h1`, `.type-body`, etc.), not ad-hoc Tailwind text sizing.

That means Class Hub must be designed with:

* **Few, stable API calls**
* **Deterministic UI states**
* **Overlays for actions** (not modal spaghetti)
* **No “infinite drill-down” patterns** that cause N+1 calls

---

## 2) The educational philosophy (why this design supports learning)

Class Hub should increase the probability of the practices that have strong evidence:

### A) Make learning visible (minute-by-minute)

In-class teaching quality improves when teachers can **surface misconceptions early** and adapt instruction. This is the heart of formative assessment (Black & Wiliam’s synthesis is the classic reference) ([ResearchGate][1]) and it aligns with OECD’s framing of formative feedback cycles. ([OECD][2])

**Class Hub supports this** by making “check for understanding” and “who needs what” frictionless.

### B) Feedback loops that are fast, specific, and actionable

Hattie’s Visible Learning work repeatedly highlights feedback as a high-impact influence when it’s usable and timely. ([VISIBLE LEARNING][3])
Rosenshine’s principles reinforce frequent checking for understanding + guided practice + immediate correction. ([American Federation of Teachers][4])

**Class Hub supports this** by turning feedback into a *classroom action*, not a later admin job:

* quick evidence capture
* quick feedback notes
* quick regrouping signals

### C) Cognitive load and teacher attention are the scarce resources

The design must protect teacher working memory:

* stable layout
* minimal navigation
* “next action” clarity
* batching and defaults

That’s why Class Hub is “cockpit + action overlays,” not a maze of pages.

---

## 3) What Class Hub *is* in your current doctypes (server truth)

### The core “Class Hub context” (what defines a class *right now*)

This already exists via your scheduling + grouping doctypes:

* **Student Group** = the rostered class identity (students + instructor(s)).
* **Student Group Schedule** = the timetable reality (rotation_day, block_number, times, etc.).
* **School Schedule / Blocks / Days** = the authoritative time model.

(You already standardized rotation_day and block_number as integers in project rules; Class Hub should lean on that.)

### The “what we’re doing today”

You already have the curriculum spine:

* **Course → Learning Unit → Lesson → Lesson Activity** (content structure).
* **Lesson Instance** exists (your delivery layer anchor; it’s the right place to bind “this lesson happened with this group at this time”).
* **Task Delivery** can optionally link to **Lesson Instance** already.

So Class Hub can always render one of these “modes” depending on what exists:

* **Scheduled teaching block with Lesson Instance** (ideal)
* **Scheduled block with no Lesson Instance yet** (Class Hub can create a lightweight Lesson Instance stub)
* **Ad-hoc session** (if teacher opens Class Hub outside schedule, create a Lesson Instance marked as ad-hoc)

### The “make learning visible” data structures you already have

This is the key insight: you **don’t need a new evidence system**. You already have one:

* **Task Submission** supports `submission_origin = Teacher Observation` (exactly what we need for in-class evidence capture).
* Submissions carry `evidence_note`, attachments, link_url, text content, and are linked to student/task_delivery/task_outcome context.
* **Task Contribution** supports teacher feedback + rubric scores (usable later; Class Hub can create lightweight feedback without forcing grading).

So the Class Hub can support:

* “I observed this”
* “Here’s a quick note / photo”
* “These 6 students need a reteach”
  without inventing a parallel system.

---

## 4) Minimal new schema proposals (only if needed)

You asked: “if new doctypes or new fields are needed, propose them.”

### Proposal A (recommended): Add a few fields to Lesson Instance (not a new doctype)

**Why:** Lesson Instance should be the *session container* for in-class teaching. It’s the perfect “Class Hub record.”

Add fields (minimal, teaching-oriented, not planning):

1. `session_mode` (Select: Scheduled, Ad-hoc)
2. `teaching_phase` (Select: Launch, Guided Practice, Independent, Plenary)
3. `live_success_criteria` (Small Text or Text Editor — what the teacher is emphasizing *today*, not long-term planning)
4. `class_notes` (Text Editor — running notes)
5. `pulse_snapshot` (JSON / Small Text) — optional: store quick counts (e.g., “Got it / Almost / Not yet”)

This keeps “Class Hub” anchored to one doc: Lesson Instance.

### Proposal B: Add a lightweight child table for “in-class signals”

If you want per-student quick signals without creating submissions every time:

Child table on Lesson Instance: `Lesson Instance Signal`

* student (Link)
* signal (Select: Not Yet / Almost / Got It / Exceeded)
* note (Small Text)
* tagged_misconception (Data or Link later)

This is *not grading*. It’s formative visibility.

### What I would **not** add

* A new “Class Hub Doctype” (unnecessary duplication)
* A new “Observation system” (Task Submission already does Teacher Observation)
* Anything that forces planning into the Hub (that belongs elsewhere)

---

## 5) The Class Hub wireframe (greyscale, deterministic layout)

This is the “single teacher screen” layout. Everything else opens as overlays.

### Page shell (top to bottom)

**Top bar (fixed)**

* Left: breadcrumb: Staff → Class Hub → `[Student Group Name]`
* Center: “Now” chip: Rotation Day + Block + time range (from schedule)
* Right: 3 buttons

  * **Start / Resume Session** (creates or opens Lesson Instance)
  * **Quick Evidence** (opens overlay)
  * **End Session** (marks Lesson Instance ended)

**Row 1: Session strip (high-signal, low text)**

* Left card: “Today’s focus” (from Lesson Instance: live_success_criteria)
* Middle card: “Lesson / Activity” (links to Lesson / Lesson Activity; view-only)
* Right card: “Fast groups”

  * button: “Group by needs (auto)” (server-side suggestion)
  * button: “Create group (manual)”

**Row 2: Student grid (the heart)**

* Grid of student cards (uniform size; you already care about strict uniformity)
  Each card shows only what matters in-class:
* student name
* attendance state (present/late/absent)
* last signal (Not Yet / Almost / Got It)
* evidence count today
* a tiny “note dot” if teacher has a note

Clicking a student opens **Student Panel Overlay** (not a route change).

**Row 3: “Make learning visible” panel**
3 columns:

* **Checks for Understanding**

  * buttons: “Quick Poll”, “Thumbs”, “Mini-whiteboard”, “Exit Ticket”
  * each opens an overlay that records a snapshot to Lesson Instance + optional per-student signals
* **Misconceptions**

  * list of 3–5 “hot misconceptions” (pulled from Learning Unit misconceptions for context + teacher-added tags)
* **Next moves**

  * “Reteach group” (opens grouping overlay)
  * “Assign micro-task” (creates Task Delivery linked to Lesson Instance)

### Overlays (A+ compliant)

All overlays:

* render context
* collect input
* call **one** workflow action
* close immediately on success, independent of toasts/services

**Overlay 1: Student Panel**

* tabs: Snapshot / Evidence / Notes
* Snapshot: signal selector + quick note
* Evidence: add Task Submission with `submission_origin = Teacher Observation`
* Notes: session notes for that student (either stored as signals or linked submissions)

**Overlay 2: Quick Evidence**

* pick student(s)
* choose: photo/upload/link/text
* writes Task Submission(s) with Teacher Observation origin

**Overlay 3: Quick Check (class-wide)**

* choose check type
* records a snapshot (Lesson Instance fields or child table)
* optionally bulk-assign signals to students (fast grid input)

---

## 6) Data contracts per section (server truth → UI)

This is the “map” that keeps your Class Hub real and non-magical.

### A) “Now” context (Schedule truth)

Server returns:

* student_group
* rotation_day
* block_number
* from_time/to_time
* location
* instructor-of-record

UI renders that; no inference, no extra calls.

### B) Session truth (Lesson Instance)

Server returns:

* lesson_instance id (or null)
* session_mode
* live_success_criteria
* class_notes
* started_at/ended_at (if you store them)

UI never guesses; it shows “Start Session” if null.

### C) Learning context (read-only curriculum spine)

Server returns:

* course
* lesson + activity (if linked)
* optional “misconceptions” text (from Learning Unit)

### D) Evidence truth (Task Submission / Task Delivery)

Server returns (batched):

* evidence counts per student for this lesson_instance/date
* recent submissions list (compact)

When teacher adds evidence:

* create Task Submission with `submission_origin = Teacher Observation`
  No grading required.

---

