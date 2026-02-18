# Focus List (Staff SPA) — Intent + Implementation Plan (Authoritative v1)

## 0) What this is (and what it is not)

This is a **Focus List**, not a user-managed task manager.

* Staff do **not** create items manually.
* Items are created by workflows (Student Log, Inquiry, Referral, Meetings, etc.).
* Clicking an item opens the correct **action overlay**.
* Completing the action removes the item from the list (and triggers the workflow’s server logic).

The Focus List is the SPA’s “what needs my attention” surface.

---

## 1) Core UX intent (locked)

### A) Reduce friction

* No hunting for the right form
* No multi-tab Desk navigation
* Action is one click away in the SPA

### B) Preserve professional trust

* “Assignee completed their action” removes it from their list immediately
* Author ownership continues via “Review outcome” where needed

### C) Avoid anxiety

* Focus items should not feel like punitive “ToDos”
* Use calm phrasing:

  * “Follow up”
  * “Review outcome”
  * “Action needed”
  * Avoid “Overdue! Failure!” tone

---

## 2) Architecture counterproposal (recommended)

### Why NOT bind the SPA directly to native ToDo

Native `ToDo` is useful, but it is **too generic** and creates long-term friction:

* It does not model “handoff” states cleanly (assignee → author review)
* It encourages per-item reference fetching (classic N+1)
* It mixes human-created tasks with system workflow tasks (messy later)
* Permission expectations vary by org; ToDo visibility can become political

### Recommended approach: “Focus Item” as a thin abstraction layer

Keep ToDo as an optional backend implementation detail, but never make the SPA depend on ToDo shape.

**Rule**

> SPA consumes `FocusItem` objects only.

Implementation options:

1. **Phase 1 (fastest)**: Implement Focus Items as a server-generated view over workflow docs (and optionally ToDo as a backend detail).
2. **Phase 2 (clean)**: Introduce a dedicated `Focus Item` doctype (or table) if we need:

   * snooze
   * ordering overrides
   * read-state persistence
   * cross-module analytics
   * offline-ish behavior

Phase 1 can still *store* in ToDo, but the SPA never knows.

---

## 3) Data model: FocusItem (normalized contract)

A Focus item returned to the SPA must already include enough context to render without N+1.

### FocusItem fields (contract)

* `id` (string) — stable, deterministic identifier
* `title` (string)
* `subtitle` (string) — small context line (e.g., student name + next step)
* `badge` (optional) — e.g., “Today”, “Due soon”
* `priority` (optional)
* `due_date` (optional)
* `action_type` (string) — drives which overlay content to render
* `reference_doctype` (string)
* `reference_name` (string)
* `payload` (object) — small, safe preview fields (no heavy HTML)
* `permissions` (object) — allowed actions for current user

### FocusItem lifecycle (minimal, locked)

A Focus Item is **ephemeral** in v1: it exists only while a workflow state requires it.

* The SPA does **not** manage focus state.
* There is no “manual done / dismiss / snooze” in v1.
* When the underlying workflow state changes, the Focus Item **disappears** from the list.

To support consistent UX grouping without adding a task engine, Focus Items include one minimal classification:

* `kind`: `"action"` or `"review"`

  * `action` — the user must do something (submit follow-up, contact parent, triage referral)
  * `review` — the user must decide what happens next (review outcome)

Optional derived hints (display-only):

* `state`: always `"open"` in v1 (items disappear when done)
* `due_state`: derived for badges only (`"today" | "soon" | "overdue" | null`)

**Rule**

> `kind` is for rendering + grouping only. It never replaces workflow logic.

### Stable ID rule (locked)

IDs must be deterministic to avoid UI churn and to support future persistence.

Recommended format:

`<source>:<reference_doctype>:<reference_name>:<action_type>`

Example:

`SL:Student Log:SLOG-202601-0001:student_log.follow_up.act.submit`

---

## 4) Overlay routing (critical design)

### Single overlay system (locked)

All overlays render through **OverlayHost + HeadlessUI Dialog** using the `.if-overlay*` CSS system.

There is no second overlay system for Focus.

### Router overlay pattern (recommended, future-proof)

Use one generic overlay shell:

* `FocusRouterOverlay.vue`

It:

* renders a consistent header (title, due, who requested, reference link)
* resolves the correct body component from `action_type`
* mounts the workflow-specific component inside the same overlay

**Rule**

> No nested overlays. FocusRouterOverlay is the single entry point.

### Action content components (workflow-owned)

Each workflow provides a body component that decides completion by calling its own workflow endpoint.

Example action types:

* `student_log.follow_up.act.submit` → mounts `StudentLogFollowUpAction.vue` (assignee mode)
* `student_log.follow_up.review.decide` → mounts `StudentLogReviewOutcome.vue` (author mode)
* `inquiry.follow_up.act.first_contact` → mounts `InquiryFollowUpAction.vue` (assignee mode)

Later:

* `referral.triage.act.start`
* `meeting.minutes.act.submit`

**Rule**

> Each workflow owns its own “complete” method and server-side side effects.
> The Focus List never reimplements business logic client-side.

---

## 5) API design (no chatty calls)

### Endpoint A: list

* `focus.list(open_only=1, limit=20, offset=0)`

Returns: array of `FocusItem` (already enriched)

### Endpoint B: get one item (optional)

* `focus.get_item(id)`

Returns a single `FocusItem` if the list payload does not include enough header context.

### Important rule about completion (locked)

Completion is **not** performed by `focus.complete()` in v1.

* The SPA calls the workflow endpoint (Student Log Follow Up submit, Inquiry mark_contacted, etc.).
* The Focus list reflects the new state automatically.

This keeps “server is authoritative” intact and prevents Focus from becoming a workflow engine.

**Rule**

> Focus API is a router + aggregator. Workflows remain owned by their DocTypes/modules.

---

## 6) Performance rules (locked)

### No N+1

* `focus.list` must not do one query per row
* Use:

  * batched `IN (...)` lookups
  * joins where safe
  * precomputed `payload` previews

### Pagination

* Always implement `limit/offset`
* Default `limit=8` for StaffHome (fast)

### Caching (Redis)

* If Focus item previews are expensive, cache per-user:

  * key: `focus:list:<user>`
  * TTL: short (30–120s)

* Invalidate on workflow events (assignment, submission, completion)

---

## 7) Permissions & privacy (non-negotiable)

Focus items must enforce server-side permissions.

For Student Log:

* Assignee sees items assigned to them
* Author sees review items for logs they created
* Admin roles see only if explicitly allowed (future setting)

For Inquiry:

* Assignee sees only Inquiry items assigned to them with open Follow-up ToDo
* Focus action execution requires assignee match and Inquiry read permission
* Completion is workflow-owned (`Inquiry.mark_contacted`) and not done in client logic

Never leak sibling school data through focus items.

---

## 8) Student Log v1 semantics for Focus (locked)

Student Log produces exactly two Focus item types in v1:

### A) Assignee action item (`kind="action"`)

Appears when:

* `Student Log.requires_follow_up=1`, and
* a follow-up person is assigned (single assignee policy), and
* no submitted follow-up exists yet for the current “active cycle”.

Disappears when:

* the assignee submits a `Student Log Follow Up` (docstatus=1)

Handoff:

* when the assignee submits, the assignee item disappears and an author review item becomes eligible.

### B) Author review item (`kind="review"`)

Appears when:

* a follow-up is submitted for the log, and
* the log is not yet in terminal state.

Disappears when:

* the author marks the log Completed, OR
* the author reassigns / triggers another follow-up cycle (creating a new assignee item).

#### Auto-timeout rule (locked)

Author review items can auto-resolve after a timeout.

Source of truth:

* `Student Log Next Step.auto_close_after_days` (synced onto `Student Log.auto_close_after_days` on follow-up submit)

Behavior:

* If the log has been in review-needed state and no further activity occurs for `auto_close_after_days`, the system:

  1. sets `Student Log.follow_up_status = "Completed"`
  2. closes any open assignment ToDos (if any remain)
  3. writes one audit timeline comment: `"Auto-completed after N days with no further action."`

**Rule**

> Auto-timeout is workflow-owned (Student Log scheduler), not Focus-owned.

---

## 9) Phase plan (do one workflow at a time)

### Phase 1 — Student Log (delivered)

1. Build `FocusListCard.vue` for StaffHome “Your Focus”
2. Implement `focus.list` returning Student Log follow-up items only
3. Implement `FocusRouterOverlay.vue` (generic shell)
4. Implement Student Log focus body components (assignee + author modes)
5. Wire click → `overlay.open('focus-router', { focus_item_id })`
6. Ensure workflow endpoints drive completion; Focus list refreshes after workflow action

### Phase 2 — Inquiry (delivered)

* Added `action_type` `inquiry.follow_up.act.first_contact`
* Added `InquiryFollowUpAction.vue` routed by `FocusRouterOverlay.vue`
* Extended `focus.list` and `focus.get_context` with Inquiry while preserving contract shape
* Added named endpoint `focus.mark_inquiry_contacted` with assignee + permission + idempotency guards

### Phase 3 — Student Referral / Meetings

* Same pattern

**Rule**

> The SPA contract remains stable; only new action_types are added.

---

## 10) StaffHome integration (UI intent)

“Your Focus” section becomes:

* list of FocusItem (max 6–8)
* grouped lightly (optional): “Needs action” vs “Review” (driven by `kind`)
* clicking opens overlay
* marking done happens inside workflow action component; list refreshes

No raw ToDo exposure in UI.

---

## 11) UI style compliance (locked)

Focus List components must respect the Ifitwala UI Style Architecture:

* Use existing typography helpers (`.type-*`) — no ad-hoc Tailwind text utilities
* Use existing surface/card patterns from `components.css`
* Do not add Tailwind imports anywhere
* Focus overlays must use the canonical `.if-overlay*` class system
* No nested overlays; FocusRouterOverlay is the single entry point






Below are **two short, authoritative markdown sections** to append to your existing Focus List / Student Log notes, followed by a **clean handoff message** to open the next chat.

---

## 🔒 Addendum — Locked Architectural Clarifications

### A) Deterministic FocusItem ID (Locked)

Focus items **must have deterministic, reproducible IDs**.

**Why**

* Prevent UI flicker and list reordering
* Enable stable caching (Redis, per-user)
* Allow idempotent refresh without diffing by content
* Prepare for a future persistent FocusItem table (Phase 2)

**Rule**

> A FocusItem ID is derived from workflow truth, not generated randomly.

**Canonical format (v1)**

```text
<workflow>::<reference_doctype>::<reference_name>::<action_type>::<user>
```

**Example**

```text
student_log::Student Log::LOG-00042::follow_up_assignee::alice@example.com
```

**Implications**

* Same workflow condition → same FocusItem ID
* When the condition disappears (e.g. follow-up submitted), the FocusItem simply no longer exists
* No separate “mark done” state required at Focus layer

This ID is **not** a database primary key in v1 — it is a **stable contract** between server and SPA.

---

### B) Focus API Is *Not* a Workflow Engine (Locked)

The Focus system is **read-only orchestration**, not business logic.

**Hard rule**

> Focus APIs must never decide workflow outcomes.

**Responsibilities**

* Focus API:

  * Aggregate “what needs attention”
  * Enrich items with preview context
  * Route clicks to the correct overlay
* Workflow controllers (Student Log, Inquiry, Referral, etc.):

  * Decide when an item is created
  * Decide when an item disappears
  * Create / close native Frappe `ToDo`
  * Write timeline comments, notifications, SLA logic

**Client behavior**

* SPA **never**:

  * creates a ToDo
  * closes a ToDo
  * mutates workflow status directly
* SPA **only**:

  * opens the correct overlay
  * submits the workflow action (submit follow-up, mark contacted, complete, reopen)

**Result**

* Focus list remains thin, calm, future-proof
* All business invariants stay server-side
* Native Frappe `ToDo` remains an implementation detail, fully hidden from the SPA

---

### C) Native ToDo Status (Confirmed)

We **continue using native Frappe `ToDo`**, with strict encapsulation.

**Confirmed behavior**

* Student Log / Follow Up controllers:

  * create ToDo on assignment
  * close ToDo on completion / auto-close
* API endpoints:

  * call controller or service methods
  * never manipulate ToDo directly
* Focus list:

  * reflects workflow truth
  * never exposes ToDo fields or concepts to users

> ToDo exists **behind the scenes only**.
> Focus List is the educator-facing abstraction.

---


✅ ONLY FocusRouterOverlay emits global signals

Why:
Keeps leaf components pure
Prevents accidental double invalidation
Centralizes refresh semantics
Allows future batching (Focus + Morning Brief + Notifications)

So:
StudentLogFollowUpAction.vue:
emits done
closes immediately
FocusRouterOverlay.vue:
interprets done
