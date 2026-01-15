# Focus List (Staff SPA) — Intent + Implementation Plan (Authoritative v1)

## 0) What this is (and what it is not)

This is a **Focus List**, not a user-managed task manager.

* Staff do **not** create items manually
* Items are created by workflows (Student Log, Inquiry, Referral, Meetings, etc.)
* Clicking an item opens the correct **action overlay**
* Completing the action removes the item from the list (and triggers the workflow’s server logic)

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

1. **Phase 1 (fastest)**: Implement Focus Items as a server-generated view over ToDo + workflow docs.
2. **Phase 2 (clean)**: Introduce a dedicated `Focus Item` doctype (or table) that references:

   * `reference_doctype`
   * `reference_name`
   * `action_type`
   * `assigned_to`
   * `status` (Open/Done)
   * `handoff_to` (optional)
   * `priority`, `due_date` (optional)
   * `context_json` (small cached preview payload)

Phase 1 can still *store* in ToDo, but the SPA never knows.

---

## 3) Data model: FocusItem (normalized contract)

A Focus item returned to the SPA must already include enough context to render without N+1.

### FocusItem fields (contract)

* `id` (string)
* `title` (string)
* `subtitle` (string) — small context line (e.g., student name + log type)
* `badge` (optional) — e.g., “Today”, “Due soon”
* `priority` (optional)
* `due_date` (optional)
* `action_type` (string) — drives which overlay to open
* `reference_doctype` (string)
* `reference_name` (string)
* `payload` (object) — small, safe preview fields (no heavy HTML)
* `permissions` (object) — allowed actions for current user

---

## 4) Overlay routing (critical design)

### Two-layer model (locked)

1. **Focus List Overlay**: generic list component (StaffHome “Your Focus”)
2. **Action Overlay**: depends on `action_type`

Examples:

* `student_log.follow_up_assignee` → `StudentLogFollowUpOverlay.vue` (assignee mode)
* `student_log.review_outcome_author` → `StudentLogFollowUpOverlay.vue` (author mode)
  Later:
* `inquiry_first_contact` → `InquiryActionOverlay.vue`
* `meeting_action_item` → `MeetingActionOverlay.vue`
* `student_referral_triage` → `ReferralTriageOverlay.vue`

**Rule**

> Each workflow owns its own “complete” method and server-side side effects.
> Focus List calls the workflow endpoint; it never reimplements business logic client-side.

---

## 5) API design (no chatty calls)

### Endpoint A: list

* `focus.list(open_only=1, limit=20, offset=0)`
  Returns: array of FocusItem (already enriched)

### Endpoint B: context (single fetch per click)

* `focus.get_context(focus_item_id)`
  Returns everything needed by the overlay in one payload:
* parent record summary
* related records summaries (follow-ups, participants, etc.)
* allowed actions

### Endpoint C: complete / transition

* `focus.complete(focus_item_id, action_payload={...})`
  This endpoint:
* validates permissions
* calls the workflow-specific method (based on action_type)
* marks focus item done
* creates any handoff focus item(s)

**Important**

* Use POST and direct payload shape (project rule)
* Never pass `cmd` in payload
* Never require the SPA to close ToDo directly

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

Never leak sibling school data through focus items.

---

## 8) Phase plan (do one workflow at a time)

### Phase 1 — Student Log only (deliverable)

1. Build `FocusListCard.vue` for StaffHome “Your Focus”
2. Implement `focus.list` returning Student Log follow-up items only
3. Implement `StudentLogFollowUpOverlay.vue` (assignee + author modes)
4. Implement `focus.get_context` + `focus.complete`
5. Wire Overlay routing from Focus item click → overlay.open(action_type, {focus_item_id})

### Phase 2 — Inquiry

* Add `action_type` for inquiry flow
* Add `InquiryActionOverlay.vue`
* Extend focus endpoints without changing SPA contract

### Phase 3 — Student Referral / Meetings

* Same pattern

**Rule**

> The SPA contract remains stable; only new action_types are added.

---

## 9) StaffHome integration (UI intent)

“Your Focus” section becomes:

* list of FocusItem (max 6–8)
* grouped lightly (optional): “Needs action” vs “Review”
* clicking opens overlay
* marking done happens inside overlay; list refreshes

No raw ToDo exposure in UI.
