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




## Overlay Performance Checklist (Staff SPA)

This is the **non-negotiable performance checklist** for any drawer/overlay in the SPA — including StudentLogCreateOverlay.

---

# 1) Images (biggest silent killer)

### 1.1 Always use low-res variants in overlays

* Overlays must **never** load original/full-size images.
* Always request **thumbnail/small** variants for student avatars.
* If you use your own helper, the fallback order must be “small → original” (never medium/large in overlays).

Acceptance checks

* On a slow network, opening the overlay does **not** trigger multi-MB image downloads.
* Avatar loads are **< 30–80 KB** typical (depends on your pipeline, but it must be “small”).

### 1.2 Avoid layout shift

* Reserve avatar box size (fixed width/height) and use object-cover.
* Lazy-load images and fade-in (you already have this pattern).

### 1.3 Cache headers / URLs

* Use stable URLs for resized images so browser caching works.
* Do not append random cache-busting params.

---

# 2) API Calls (batching + dedup)

### 2.1 The overlay must open instantly (no blocking)

* Open overlay first.
* Show skeleton/loader for options while fetching.
* Never wait on server to render the overlay.

### 2.2 Minimize request count (target: 1–2 on open)

**Best target per open:**

* Attendance mode: **1 request** to fetch both:

  * log types
  * next steps
* Home mode before student chosen: **1 request** to fetch log types + next steps for the user default school.

Then only additional calls as needed:

* assignee search is triggered only when:

  * needs follow-up ON
  * next step selected
  * user types at least 2 chars (or you choose 1 char if your dataset is small)

### 2.3 Batch “variants” into a single endpoint (recommended)

Instead of two separate calls:

* `/api/student_log/types`
* `/api/student_log/next_steps`

Prefer:

* `/api/student_log/variants`
  returns:

```json
{
  "log_types": [...],
  "next_steps": [...]
}
```

This reduces latency and makes caching simpler.

### 2.4 Deduplicate in-flight requests

If overlay opens twice quickly (or school changes):

* do not fire duplicate calls
* keep an in-flight promise keyed by `(endpoint, school)`
* cancel/ignore stale responses using a request token

### 2.5 Debounce typeahead calls

For student search / user search:

* debounce 200–300ms
* only query when:

  * query length >= 2
* always keep last result visible while loading next page of results

---

# 3) Caching Rules (client + server)

### 3.1 Server-side caching for shared lists (Redis)

These lists are **shared truth** and change rarely:

* Student Log Types
* Student Log Next Steps

Server must cache them (per school) using Redis (your project rule):

* `frappe.cache()` or `@redis_cache(ttl=...)`

Suggested TTL:

* 1 hour to 24 hours depending on how often you expect changes
* 24h is fine if you invalidate on DocType update later (optional)

Keyed by:

* `school`
* plus any “include parent/descendants” logic if you aggregate

### 3.2 Client-side cache for variants (short TTL)

In SPA:

* cache variants response keyed by `school`
* TTL 10–30 minutes
* store in-memory (not localStorage) to avoid stale across sessions

### 3.3 Don’t cache search results aggressively

Typeahead results for:

* student search
* assignee search
  should be cached only in-memory per query string briefly, because permissions/scope can shift.

---

# 4) Payload & Response Weight

### 4.1 Return minimal fields only

For pickers:

* `id`
* `label`
* `image_small` (or a resolved small image url)
  Nothing else.

Avoid sending:

* full Student doc
* full User doc
* metadata not needed for display

### 4.2 Paginate large searches

Student search must be paginated server-side:

* `start`
* `page_length`
  Even if UI shows only top 10.

---

# 5) Rendering & Reactivity (Vue)

### 5.1 Avoid deep reactive churn

* Keep form state in a single `reactive({ ... })` object
* Keep options lists in `shallowRef([])` or `ref([])` and replace arrays wholesale
* Avoid computed that re-sorts large arrays every keystroke

### 5.2 Avoid watch TDZ bugs and overlay breakage

Project rule:

* declare refs/computed before watchers
* never use `console.log()` as watch argument
* prefer watching primitives and using `immediate` carefully

### 5.3 Don’t rerender heavy editors unnecessarily

* Mount the rich text editor once per overlay open
* Don’t remount it when toggling follow-up section
* Avoid v-if toggling on the editor subtree (use v-show if needed)

---

# 6) UX Loading States (perceived performance)

### 6.1 Skeletons, not spinners everywhere

* Use skeleton rows for:

  * log type options (first load)
  * next step options (first load)
* Use subtle inline spinner only for typeahead search

### 6.2 Keep controls usable

* Let teachers start typing the log while options load.
* Only block submit until required fields are ready.

---

# 7) Observability (how we prove it’s fast)

### 7.1 Add lightweight timing logs in dev mode

In dev only:

* measure time from `overlay.open()` to first paint
* measure variants fetch time
* measure submit latency

### 7.2 Network assertions

Open DevTools → Network:

* opening overlay triggers ≤ 1–2 requests (excluding typeahead)
* no image > 150KB in overlay view

---

# 8) Final Acceptance Targets (hard numbers)

* Overlay opens and is interactive within **< 150ms** on warm load (no network wait)
* Variants loaded within **< 400ms** typical LAN / **< 1s** moderate WAN
* No large images requested (no original-size student photos)

