Below is a **Codex instruction set** to build a **Class Hub v1 mockup page** in the SPA using **Vue 3 + Tailwind v4 + frappe-ui resources**, your **HeadlessUI OverlayHost**, and your **typography/style/service rules**.

This is a **visual mockup first** with **demo/fake data**, but it must be wired so that swapping to real endpoints later is trivial. Where APIs don’t exist, Codex must create **minimal endpoints** that return **stub/demo** data shaped like the final contract (server truth pattern).

---

# Codex Instructions: Build Class Hub v1 Mockup (Vue + Tailwind + HeadlessUI)

## 0) Hard constraints (do not violate)

* Use **OverlayHost** stack for overlays (no ad-hoc modal).
* Overlays must **close deterministically on success** (A+ overlay contract).
* Use **.type-*** typography helpers only (no Tailwind text sizing in templates).
* Use frappe-ui `createResource` and **POST via `resource.submit(flatPayload)`**.
* Do **not** hardcode `/portal/` in any SPA links or routes.
* Keep page layout calm: **greyscale mockup**, no charts, no badges, no “urgent red”.

---

## 1) Files to create / modify

### 1.1 Create new page

**File:** `ui-spa/src/pages/staff/ClassHub.vue`

### 1.2 Create a page-level service (optional but recommended)

**File:** `ui-spa/src/services/classHubService.ts`

* Exposes `getBundle(studentGroup, date?, blockNumber?)`
* Exposes `startSession(studentGroup, date?, blockNumber?)`
* Exposes `endSession(lessonInstance)`
* Exposes `saveSignals(lessonInstance, signals[])`
* Exposes `quickEvidence(payload)`

### 1.3 Create new overlays (mockup versions)

**Folder:** `ui-spa/src/components/overlays/class-hub/`

Create:

* `StudentContextOverlay.vue`
* `QuickEvidenceOverlay.vue`
* `QuickCFUOverlay.vue`

All must conform to your overlay conventions:

* Receive props (IDs + minimal display)
* Do one action
* Close immediately on success
* Emit `close` and `after-leave` properly

### 1.4 Create small UI components (optional)

**Folder:** `ui-spa/src/components/class-hub/`

* `ClassHubHeader.vue`
* `TodayList.vue`
* `FocusStudentsRow.vue`
* `MyTeachingPanel.vue`
* `StudentsGrid.vue`
* `ClassPulse.vue`
* `FollowUpsList.vue`

Keep components “dumb”: props in, events out.

---

## 2) Route wiring

Add a route to your Staff router:

* name: `ClassHub`
* path: `/staff/class/:studentGroup`
* component: `ClassHub.vue`

The route param `studentGroup` is required.
Optional query params: `date`, `block`.

**No `/portal/` prefix anywhere.**

---

## 3) Backend: create stub endpoints (server truth shape)

Create a new API module:

**File:** `ifitwala_ed/api/class_hub.py`

Expose these whitelisted methods (minimal implementation is fine; return demo data if needed):

1. `get_bundle(student_group: str, date: str | None = None, block_number: int | None = None)`
2. `start_session(student_group: str, date: str | None = None, block_number: int | None = None)`
3. `end_session(lesson_instance: str)`
4. `save_signals(lesson_instance: str, signals_json: str)`

   * signals_json is JSON string for now (Codex: parse it)
5. `quick_evidence(payload_json: str)`

   * payload_json includes students[], type, text/link, etc.

### 3.1 Demo data policy

For now, it’s acceptable that:

* `get_bundle()` returns **fake data** shaped like final contracts
* BUT the endpoint must verify basic permission:

  * user is logged in
  * user is an instructor on the Student Group (via Student Group Instructor.user_id)

### 3.2 Use real doctypes where easy (recommended)

Where it’s easy, populate data from doctypes:

* Student Group & students from:

  * Student Group
  * Student Group Student child

* Schedule context (optional for v1 mock):

  * Student Group Schedule rows
  * If rotation-day resolution is hard, return a demo “Now chip”.

* Lesson Instance (optional):

  * If you can create a real Lesson Instance do it; otherwise return a fake id like `"LI-DEMO-0001"`

* Evidence counts:

  * For mock, return random small integers per student.

Do NOT add new doctypes yet for mockup. Field additions come later after UX feedback.

---

## 4) Data contract: exact shapes to implement

Codex must implement these payload shapes consistently in both backend and frontend.

### 4.1 Bundle response

```ts
type ClassHubBundle = {
  header: {
    student_group: string
    title: string           // e.g., "G6 Sci - Block B"
    academic_year?: string
    course?: string
  }
  now: {
    date_label: string      // e.g., "Tue 16 Jan"
    rotation_day_label?: string  // "Rotation Day 3"
    block_label?: string    // "Block B"
    time_range?: string     // "08:45–09:30"
    location?: string
  }
  session: {
    lesson_instance?: string | null
    status: "none" | "active" | "ended"
    live_success_criteria?: string
  }
  today_items: Array<{
    id: string
    label: string
    overlay: "QuickCFU" | "QuickEvidence" | "StudentContext" | "TaskReview"
    payload: Record<string, any>
  }>
  focus_students: Array<{
    student: string
    student_name: string
  }>
  students: Array<{
    student: string
    student_name: string
    evidence_count_today: number
    signal?: "Not Yet" | "Almost" | "Got It" | "Exceeded" | null
    has_note_today?: boolean
  }>
  notes_preview: Array<{
    id: string
    student_name: string
    preview: string
    created_at_label: string
  }>
  task_items: Array<{
    id: string
    title: string
    status_label: string
    pending_count?: number
    overlay: "TaskReview"
    payload: Record<string, any>
  }>
  pulse_items: Array<{ id: string; label: string; route?: { name: string; params?: any } }>
  follow_up_items: Array<{
    id: string
    label: string
    overlay: "StudentContext"
    payload: Record<string, any>
  }>
}
```

---

## 5) Page UI: exact layout requirements

**ClassHub.vue** must render in this order:

### 5.1 Header row

* Breadcrumb + title
* “Now chip” (date + rotation day + block + time)
* Buttons:

  * Start/Resume Session
  * Quick Evidence
  * End Session

### 5.2 TODAY section (max 3 lines)

* Title: “TODAY”
* List items show `label`
* Clicking opens overlay specified by item.overlay

### 5.3 STUDENTS IN FOCUS (chips)

* Title
* 3–5 chips
* Each chip click opens StudentContextOverlay for that student

### 5.4 MY TEACHING (two columns)

Left:

* Notes & Observations list (3–5 items)
* CTA “Add note” opens StudentContextOverlay (or QuickEvidence) with a preselected student prompt

Right:

* Tasks & Evidence list (actionable only)
* CTA “Review” opens TaskReview (mock overlay or placeholder)

### 5.5 CLASS PULSE (2–3 lines)

* Title
* sentence items
* click navigates to route if provided (can be stub route)

### 5.6 MY FOLLOW-UPS (1–3 lines)

* Title
* click opens StudentContextOverlay

### 5.7 Students Grid (if you include it in v1 mock)

If included, it must appear between “Students in Focus” and “My Teaching”, OR below “My Teaching” — choose one and keep stable.

* uniform card size
* name, evidence_count_today, signal, note dot
* click opens StudentContextOverlay

**Typography rule:** Use `.type-*` classes only.
**No charts.** No badges. No colored urgency.

---

## 6) Overlays: required behaviors

All overlays are HeadlessUI Dialog panels rendered via OverlayHost.

### 6.1 StudentContextOverlay.vue

Props:

* `student`, `student_name`, `student_group`, `lesson_instance?`

Tabs (simple, no fancy):

* Snapshot: radio/select for signal + small note
* Evidence: CTA “Add evidence” opens QuickEvidenceOverlay prefilled to this student
* Notes: text area “teacher note” (mock: save to service)

Actions:

* Save snapshot → calls `save_signals()` or mock service
* Must close immediately on success.

### 6.2 QuickEvidenceOverlay.vue

Props:

* `student_group`, `lesson_instance?`, optional preselected students

Form:

* multi-select students (simple list for mock)
* evidence type: text / link (file upload optional)
* evidence text/link field

Submit:

* calls `quick_evidence()` endpoint (payload_json)
* close on success

### 6.3 QuickCFUOverlay.vue

Props:

* `student_group`, `lesson_instance?`

UI:

* choose CFU type (thumbs/whiteboard/exit)
* set a quick class note
* optional: apply same signal to selected students

Submit:

* calls `save_signals()` with generated signals list
* close on success

**Important:** Overlay closes even if toast is unavailable.

---

## 7) Services + resources (front-end wiring)

In `classHubService.ts`, use `createResource`:

* `bundleResource` → method: `ifitwala_ed.api.class_hub.get_bundle`
* `startResource` → `start_session`
* `endResource` → `end_session`
* `saveSignalsResource` → `save_signals`
* `quickEvidenceResource` → `quick_evidence`

All must use:

```js
resource.submit({ flat: "payload" })
```

No wrapper `{ payload: ... }`.

If endpoint expects JSON string, pass it as `signals_json: JSON.stringify(signals)`.

---

## 8) Demo/fake data strategy (visual-first)

Codex must implement a toggle in ClassHub.vue:

* If API errors or returns empty bundle, use **local demo bundle** with:

  * 18–24 students
  * 3 focus students
  * 3 today items
  * 3 notes
  * 2 tasks
  * 2 pulse items
  * 1 follow-up

This ensures page always renders during mockup.

---

## 9) Acceptance criteria (mockup is “done” when)

* Navigating to `/staff/class/<studentGroup>` renders the full layout.
* Page renders even without real schedule/lesson instance.
* Clicking any item opens the correct overlay via OverlayHost.
* Overlay submit closes immediately and updates UI locally (optimistic) AND/OR refetches bundle.
* No Tailwind text sizing in templates (typography helpers only).
* No `/portal/` hardcoded paths anywhere.
* Backend endpoints exist and return shaped data (even if demo).

---

## 10) Notes for Codex: use existing doctypes correctly

When retrieving real data:

* Roster comes from Student Group Student rows with `active = 1`
* Instructor permission check uses Student Group Instructor.user_id
* Schedule rows use Student Group Schedule with `rotation_day` and `block_number` ints
* Student Group is anchored to Program Offering, Academic Year, Course

For v1 mockup, it’s acceptable to skip deep schedule logic and return demo “Now” info.

---

## 11) Deliverables Codex must output

* Full `ClassHub.vue`
* All created overlay components (full files)
* Any created small components (full files)
* `classHubService.ts` (full file)
* `ifitwala_ed/api/class_hub.py` (full file)
* Router update diff (exact file changed)

No partial methods. If modifying a method, output the entire method.

---
