# Student Log — Staff SPA UX Contract

## Drawer Overlay (HeadlessUI) — Authoritative v1

This document defines the **UX, interaction, and component contract** for Student Log creation and editing in the **Staff SPA**, using the existing right-side drawer / slide-over overlay system.

This is a **teacher-facing contract**. No architectural, workflow, or DocType terminology may appear in the UI.

---

## 0. Naming & Scope

### Primary component

* `StudentLogCreateOverlay.vue`

This component is **self-contained**:

* Visibility toggles are implemented inline
* Follow-up logic UI is implemented inline
* No micro-components unless they are reused elsewhere

Supporting components (only if already existing or clearly reusable):

* Student typeahead
* User (staff) typeahead

---

## 1. Entry Points & Modes

### Mode A — Attendance entry (PRIMARY)

**Trigger**

* “Add log” action from a student row in Attendance

**Intent**

* Fast capture in the moment
* Zero risk of logging the wrong student

**Overlay open payload**

```ts
{
  mode: 'attendance',
  student: { id: string, label: string, image?: string },
  student_group?: { id: string, label: string },
  context_school?: string,
  sourceLabel: 'Attendance'
}
```

**UX rules**

* Student is **locked**
* No student search field is shown
* Student appears as a mini-card in the header

---

### Mode B — Staff Home entry (SECONDARY)

**Trigger**

* “New student log” quick link on Staff Home

**Intent**

* Capture observations outside class context

**Overlay open payload**

```ts
{
  mode: 'home',
  context_school: string,   // user default school
  sourceLabel: 'Staff Home'
}
```

**UX rules**

* Student typeahead is visible
* All other fields are hidden/disabled until student is selected
* Student search is scoped server-side to:

  * user default school
  * its descendants
  * never sibling schools

---

## 2. Drawer Layout

### Geometry

* Right-side drawer
* Full height
* Desktop width: ~480–560px
* Tablet: ~90vw
* Mobile: 100vw
* Sticky header and footer

### Header (sticky)

Always shows:

* Title: **New student log** (or **Edit student log** in edit flow)
* Source pill: Attendance / Staff Home
* Close button

**Close behavior**

* ESC closes
* Backdrop closes only if form is not dirty
* If dirty → confirmation: “Discard this log?”

---

## 3. Student Display & Images

### Student mini-card

Used in:

* Header (attendance mode)
* After student selection (home mode)

**Image requirements (critical)**

* Always use **low-resolution / thumbnail student images**
* Never load original or large images in overlays
* Image selection must follow existing image utilities:

  * Prefer resized / thumbnail variants
  * Fall back safely if missing

**Rationale**

* Overlays are high-frequency UI
* Must remain fast on low bandwidth
* Avoid layout jank and memory overhead

---

## 4. Form Structure

### Section 1 — Student & Log Type

#### Student

* Attendance mode: locked mini-card
* Home mode: typeahead until selected

Changing student:

* Allowed only if form is empty
* Otherwise require confirmation

#### Log type (required)

* Typeahead dropdown
* Placeholder: “Choose log type…”
* Keyboard-first navigation

Options:

* Fetched dynamically by school
* No hardcoded values

---

### Section 2 — Date & Time

* Default: now
* Displayed as: “Today · HH:mm”
* Editable but visually secondary

---

### Section 3 — Visibility (inline)

Two toggles (default OFF):

* “Visible to student”
* “Visible to parents”

Helper text:

* “Leave off for staff-only notes.”

No permission or system language.

---

### Section 4 — Log Content

* Label: “Log”
* Large text editor
* Placeholder:

  > “What did you notice? What did the student say or do? What did you do?”

Optional helper chips (insert text):

* Observed:
* Student said:
* Action taken:

No forced structure.

---

### Section 5 — Follow-up (progressive)

Toggle:

* “Needs follow-up?” (default OFF)

If OFF:

* Show note: “No follow-up will be created.”

If ON:

1. **Next step** (required)

   * Placeholder: “Choose next step…”
   * Options fetched dynamically by school

2. **Who should follow up?** (required)

   * Staff typeahead
   * Results filtered server-side by:

     * role from next step
     * allowed school set

3. Preview text:

   * “This will notify the person you choose.”

Submit is blocked until valid.

---

## 5. Footer Actions (sticky)

Buttons:

* Primary: **Submit log**
* Secondary: Cancel

No draft save.

Submit behavior:

* Disable buttons
* Show “Saving…”
* Prevent double submit

---

## 6. Post-submit Behavior

On success:

* Toast: “Log submitted”
* Show success state with:

  * “Add another”
  * “Close”

Add another:

* Attendance mode → same student, cleared form
* Home mode → cleared form + student picker

---

## 7. Errors & Edge Cases

### Validation errors

* Display server message in toast
* Inline error where possible

### Loading failures

* Inline message: “Couldn’t load options. Retry.”

### Dirty close

* Confirmation required

---

## 8. Edit & Clarification Flows

### Edit log

* Label: **Edit log**
* Internally uses Frappe Amend
* Allowed only if **no follow-ups exist**
* UI is identical to create

### Add clarification

* Always allowed
* Append-only
* Implemented as comment / timeline entry
* Does not change meaning or follow-up logic

---

## 9. API Contract (SPA)

All APIs live under `api/`.

### Fetch log types

```json
{ "school": "SCH-..." }
```

### Fetch next steps

```json
{ "school": "SCH-..." }
```

### Search follow-up assignees

```json
{ "school": "SCH-...", "role": "Counselor", "q": "ann" }
```

### Submit student log

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

Server resolves:

* school (via `anchor_school`)
* permissions
* follow-up creation
* notifications

---

## 10. School Hierarchy

All school scoping uses **NestedSet utilities**.

Rules:

* Same school
* Descendants
* Parent (+1)
* Never siblings

These rules apply consistently across:

* student search
* log types
* next steps
* assignee search

---

## 11. Acceptance Criteria

* Attendance flow is two-click and safe
* Home flow is scoped and explicit
* No hardcoded variants
* Low-res student images only
* Follow-up logic never duplicated client-side
* No architecture terms visible to teachers

---

**End of UX Contract**
