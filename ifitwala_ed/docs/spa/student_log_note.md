# Student Log & Follow‑Up — Canonical System + Staff SPA UX (v1)

> **Status:** Locked for v1. Any implementation (Desk, SPA, API, Reports, Dashboards) must conform.
>
> **Authority:** This note is subordinate only to:
>
> 1. `spa_architecture_and_rules.md` (SPA governance, API rules, folder semantics, contracts/types, styling invariants)
> 2. `overlay_and_workflow.md` (Overlay & workflow lifecycle contract — A+ model)
>
> If anything here conflicts with those two files, those two files win.

---

## 0. Intent and boundary (no drift)

### 0.1 What this system is

The Student Log system is a **teacher-centered observational workflow**, not discipline tooling.

It exists to:

* Capture meaningful observations (positive / neutral / concern-based)
* Fit daily teaching workflows (especially Attendance)
* Route responsibility clearly when follow-up is required
* Preserve history once action has begun

**Core principle**

> Capture is easy. Follow‑up is structured. History becomes immutable once acted upon.

### 0.2 What the SPA is (and is not)

Per `spa_architecture_and_rules.md`:

* SPA renders state, triggers actions, and obeys server truth.
* SPA does **not** invent business rules, close ToDos, or infer workflow state.
* All API calls use `createResource` and POST via `resource.submit(payload)`.

### 0.3 Overlay lifecycle (A+)

Per `overlay_and_workflow.md`:

* **Overlay owns closing. UI Services own orchestration.**
* On successful workflow action: overlay **closes immediately**, never gated by toast/refresh/reload.

---

## 1. Core objects and responsibilities (authoritative)

### 1.1 Student Log — Observation (submittable)

Represents **what was observed**.

Characteristics:

* Submittable
* May or may not require follow-up
* Can be amended **only before follow-up exists**
* Visibility to students/guardians is explicit and opt‑in in SPA
* Desk/controller logic is authoritative for state changes

Common fields (non‑exhaustive):

* `student`
* `date`, `time`
* `log_type`
* `log`
* `requires_follow_up`
* `next_step`
* `follow_up_person`
* `follow_up_status`
* `school` (derived server-side; read‑only)
* `amended_from`

### 1.2 Student Log Type — Classification (school-scoped)

Defines **what kind of observation** this is.

Locked decisions:

* `school` exists and is required
* Log Types are **school-scoped**
* School hierarchy rules apply (see §4)

### 1.3 Student Log Next Step — Routing definition (school-scoped)

Defines **what follow-up is required** when `requires_follow_up = 1`.

Fields (typical):

* `next_step`
* `associated_role`
* `school`
* `auto_close_after_days`

Design intent:

* Next Steps are school-scoped
* Responsibility is defined by **role**, not person
* Assignee is chosen at log creation
* SPA must never hardcode Next Steps

### 1.4 Student Log Follow Up — Action record (submittable)

Represents **work done in response to one Student Log**.

Locked characteristics:

* Always linked to exactly one Student Log
* Submittable and auditable
* Once any Follow Up exists, the parent log is historically frozen

This is the action trail. Amendments must not rewrite history.

---

## 2. Follow‑up status semantics and transitions (authoritative)

This defines the meaning of `follow_up_status` and the only allowed transitions.
It applies to Desk and SPA. SPA follows DocType controllers and does not invent alternatives.

### 2.1 Status meanings

**Open**

* `requires_follow_up = 1`
* Student Log is submitted
* Exactly one assignee exists
* No Follow Up entries exist yet

**In Progress**

* `requires_follow_up = 1`
* Work has started / evidence exists
* At least one Follow Up exists (draft or submitted), **or** case was reopened and work continues

**Completed (terminal)**

* Case is closed
* No more follow-ups can be added/edited
* Assignment fields are locked

Critical rule:

* Submitting a follow-up does **not** automatically complete the log.
* Follow-up submission completes the assignee’s contribution and hands control back to the author for **Review outcome**.

### 2.2 Allowed transitions (case-state only)

* (unset / None) → Open (follow-up becomes required and assignment exists)
* Open → In Progress (any follow-up exists or is submitted)
* In Progress → Completed (explicit author/admin completion OR auto-close policy)
* Completed → In Progress (reopen by author/admin)

Completed is the only terminal state.

### 2.3 Ownership and handoff (Focus model alignment)

* Assignee submits follow-up → assignee action ends.
* Author receives: timeline + bell notification and a Focus **Review outcome** item.
* Author decisions (Focus layer, not `follow_up_status`):

  1. Review outcome (default)
  2. Further action required (reassign / additional follow-up / escalate)
  3. Close case (mark Completed)

**Professional trust principle**

> Assignee completion is accepted as “done” without author approval, but the author retains ownership of the case lifecycle.

### 2.4 Auto-close policy

`auto_close_after_days` is a **case-level** policy. It may close after inactivity.

Locked rule:

* It must never be treated as “follow-up submitted = auto-complete”.

---

## 3. Visibility defaults (teacher-safe)

SPA defaults:

* Visible to student: **OFF**
* Visible to parents: **OFF**

Visibility must always be a conscious teacher decision.

---

## 4. School hierarchy & scoping (non-negotiable)

### 4.1 School model

* `School` is NestedSet (`is_tree = 1`)
* Parent field: `parent_school`
* Hierarchy via `lft` / `rgt`

### 4.2 Allowed school set rule

Given reference school **S**, allowed set is:

* S
* all descendants of S
* parent of S (one level only)
* **never sibling schools**

Applies uniformly to:

* student search
* log type lists
* next step lists
* follow-up assignee lists

---

## 5. School context resolution (server truth)

Canonical truth:

* `Student.anchor_school` defines the student’s school context

Usage:

* Attendance entry → school known from context (must match student scope)
* Staff Home entry → school resolved from selected student

`Student Log.school` is derived server-side and read-only.

---

## 6. SPA entry points (locked)

### 6.1 Attendance (primary)

* Student known and locked
* No student picker
* Two-click capture flow

### 6.2 Staff Home (secondary)

* Student typeahead enabled
* Scope = user default school + descendants (+ parent +1 rule)
* Never sibling schools

---

## 7. Follow‑up lifecycle (locked)

### 7.1 No follow-up required

If `requires_follow_up = 0`:

* On submit, log is marked **Completed**
* No Follow Up records exist

### 7.2 Follow-up required

If `requires_follow_up = 1`:

* `next_step` mandatory
* `follow_up_person` mandatory
* Status transitions are server-owned
* ToDo + notifications created by server/controller logic

SPA responsibilities:

* Fetch Next Steps (school-scoped)
* Fetch assignees (role + allowed school set)
* Block submit until valid

---

## 8. Editing, amendments, clarifications (immutability rule)

Invariant:

> Once follow-up work begins, history must not be rewritten.

Teacher-facing actions:

* **Edit log**

  * Internally uses Frappe Amend
  * Allowed only if **no Follow Up exists**

* **Add clarification**

  * Allowed always
  * Append-only (Comment / timeline note)
  * Does not alter follow-up logic

---

## 9. Reports & dashboards (read-only consumers)

Reporting philosophy:

* Reports and dashboards never mutate or reinterpret business logic.
* Status is derived strictly from stored fields.

### 9.1 Script report

* Parent row: Student Log
* Child rows: Student Log Follow Ups

### 9.2 Print templates

* Formal audit record
* One card per Student Log
* Follow Ups listed chronologically

### 9.3 Dashboards

* Student Log Dashboard → operational oversight
* Student Overview Dashboard → analytics only (no capture)

---

## 10. Focus integration (locked)

Student Log generates Focus items automatically (users do not create tasks manually):

* On assignment: assignee Focus item → **Provide follow-up**
* On follow-up submission: close assignee item → create author item → **Review outcome**
* On author close: close remaining author item
* On further action: create new assignee item (handoff repeats)

Focus is a SPA surface reflecting server truth. SPA does not create Focus items.

---

## 11. Source of truth for staff scoping

* Employee is authoritative
* `Employee.user_id` → User
* `Employee.school` → school node

---

## 12. UX language rules (teacher-facing)

Allowed:

* Edit log
* Add clarification
* Needs follow-up?
* Who should follow up?

Forbidden in UI:

* workflow
* docstatus
* amend
* architecture terms

---

## 13. Morning briefing integration (read-only)

Purpose:

* Situational awareness surface
* Surfaces recent Student Logs and active Follow Ups to appropriate staff
* Reduces hunting through reports/dashboards

Rules:

* Read-only; never mutates data
* Consumes server-side queries only
* Respects school hierarchy scoping, role visibility, and visibility flags
* Excludes draft/unsubmitted records

Interactions allowed:

* Navigate to Student Log (read-only)
* Navigate to Follow Up if user is involved

Not allowed:

* Edit/amend
* Create follow-ups
* Change status

---

## 14. Invariants (must never drift)

1. Follow Ups always belong to exactly one Student Log
2. Logs with Follow Ups are immutable
3. Reports reflect stored state only
4. School scoping uses NestedSet everywhere
5. SPA never hardcodes variants
6. Desk/controller logic is authoritative
7. Morning Briefing is read-only and never mutates data

---

# Staff SPA UX Contract — Student Log Drawer Overlay (HeadlessUI) (v1)

> **Component:** `StudentLogCreateOverlay.vue`
>
> **Overlay model:** Must comply with `overlay_and_workflow.md` (A+). All overlays render via `OverlayHost`.
> **SPA rules:** Must comply with `spa_architecture_and_rules.md` (API, contracts/types, no fetch, no ToDo logic, typography/styling).

---

## A. Entry points and modes

### Mode A — Attendance entry (primary)

Trigger:

* “Add log” action from a student row in Attendance

Intent:

* Fast capture in the moment
* Zero risk of logging the wrong student

Overlay open payload:

```ts
{
  mode: 'attendance',
  student: { id: string, label: string, image?: string },
  student_group?: { id: string, label: string },
  context_school?: string,
  sourceLabel: 'Attendance'
}
```

UX rules:

* Student is locked
* No student search field
* Student appears as a mini-card in the header

### Mode B — Staff Home entry (secondary)

Trigger:

* “New student log” quick link on Staff Home

Intent:

* Capture observations outside class context

Overlay open payload:

```ts
{
  mode: 'home',
  context_school: string,
  sourceLabel: 'Staff Home'
}
```

UX rules:

* Student typeahead visible
* Other fields hidden/disabled until student selected
* Student search scoped server-side to allowed school set (no siblings)

---

## B. Drawer layout

Geometry:

* Right-side drawer
* Full height
* Desktop width ~480–560px
* Tablet ~90vw
* Mobile 100vw
* Sticky header + footer

Header (sticky):

* Title: “New student log” (or “Edit student log”)
* Source pill: Attendance / Staff Home
* Close button

Close behavior:

* ESC closes
* Backdrop closes only if form not dirty
* If dirty: confirm “Discard this log?”

---

## C. Student display and images (performance invariant)

Student mini-card:

* Header (attendance mode)
* After selection (home mode)

Image rules (critical):

* Always use low-resolution/thumbnail student images
* Never load original/large images in overlays
* Use existing image utilities (prefer resized variants, safe fallback)

---

## D. Form structure

### Section 1 — Student and log type

Student:

* Attendance mode: locked mini-card
* Home mode: typeahead until selected

Changing student:

* Allowed only if form is empty
* Otherwise requires confirmation

Log type (required):

* Typeahead dropdown
* Placeholder: “Choose log type…”
* Keyboard-first
* Options fetched by school; no hardcoded values

### Section 2 — Date and time

* Default: now
* Display: “Today · HH:mm”
* Editable, visually secondary

### Section 3 — Visibility (inline)

Defaults OFF:

* “Visible to student”
* “Visible to parents”

Helper:

* “Leave off for staff-only notes.”

### Section 4 — Log content

* Label: “Log”
* Large text editor
* Placeholder:

  “What did you notice? What did the student say or do? What did you do?”

Optional helper chips (insert text):

* Observed:
* Student said:
* Action taken:

### Section 5 — Follow-up (progressive)

Toggle:

* “Needs follow-up?” (default OFF)

If OFF:

* Show: “No follow-up will be created.”

If ON:

1. Next step (required)

* Placeholder: “Choose next step…”
* Options fetched by school (no hardcoding)

2. Who should follow up? (required)

* Staff typeahead
* Results filtered server-side by role from next step + allowed school set

3. Preview text:

* “This will notify the person you choose.”

Submit blocked until valid.

---

## E. Footer actions (sticky)

Buttons:

* Primary: “Submit log”
* Secondary: Cancel

Rules:

* No draft save
* Disable during submit
* “Saving…” while busy
* Prevent double submit

---

## F. Post-submit behavior (A+ compliant)

On success:

* Toast: “Log submitted” (best-effort)
* Show success state with:

  * “Add another”
  * “Close”

Add another:

* Attendance mode: same student, cleared form
* Home mode: cleared form + student picker

**A+ rule:** overlay close must never depend on toast or refresh.

---

## G. Errors and edge cases

Validation errors:

* Show server message in toast
* Inline error where possible

Loading failures:

* Inline: “Couldn’t load options. Retry.”

Dirty close:

* Confirmation required

---

## H. Edit and clarification flows

Edit log:

* Label: “Edit log”
* Internally uses Frappe Amend
* Allowed only if no follow-ups exist
* UI identical to create

Add clarification:

* Always allowed
* Append-only comment/timeline entry
* Does not change follow-up logic

---

## I. SPA API contract (shape only; server owns truth)

All SPA calls must comply with `spa_architecture_and_rules.md`:

* `createResource`
* POST via `resource.submit(payload)`
* No `fetch()`
* No `frappe.form_dict`

Request shapes (illustrative; server signature is authoritative):

Fetch log types:

```json
{ "school": "SCH-..." }
```

Fetch next steps:

```json
{ "school": "SCH-..." }
```

Search follow-up assignees:

```json
{ "school": "SCH-...", "role": "Counselor", "q": "ann" }
```

Submit student log:

```json
{
  "student": "STU-...",
  "date": "YYYY-MM-DD",
  "time": "HH:mm",
  "log_type": "...",
  "log": "...",
  "visible_to_student": 0,
  "visible_to_parents": 0,
  "requires_follow_up": 0,
  "next_step": null,
  "follow_up_person": null
}
```

Server resolves and enforces:

* school (via `anchor_school`)
* permissions
* status transitions
* ToDo/notifications

---

## J. Acceptance criteria (v1)

* Attendance capture is two-click and safe
* Staff Home capture is scoped and explicit
* No hardcoded variants
* Low-res student images only
* Follow-up logic not duplicated client-side
* No architecture terms visible to teachers
