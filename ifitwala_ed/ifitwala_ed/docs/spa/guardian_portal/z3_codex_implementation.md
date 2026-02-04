Below is the **Codex handoff pack** you need. It is written so agents can execute without inventing schemas, and it assumes **Phase-1 includes Org Communication** and that **Task Delivery is the per-student-group assignment unit** (with `available_from`, `due_date`, `lock_date`).

---

# docs/portal/guardian/codex_pr0_brief_phase1.md

## Title

Guardian Portal Phase-1 — Guardian Home “Snapshot” (single-call) + SPA wiring

## Goal

Ship a Guardian Home that answers in <30 seconds:

* What’s happening with my kids today and over the next **7 school days**?
* Is anything needing my attention?
* What should I prepare for (bags, assessments, deadlines)?

## Scope (Phase-1)

### Must ship

1. **One backend endpoint** returning a **single bundled payload**: `GuardianHomeSnapshot`
2. Guardian Home SPA page renders 4 zones:

   * Family Timeline (next 7 school days)
   * Attention Needed
   * Preparation & Support
   * Recent Activity
3. Include **Org Communication** (unread + recent)
4. Include **Student Logs** that are guardian-visible
5. Include **Task due/assessment indicators** using **Task Delivery** (due date, availability) and **published Task Outcomes** for results

### Nice-to-have (if already trivial)

* Mark “read” interactions (only if the current interaction model supports it cleanly)

## Non-goals (explicitly forbidden in Phase-1)

* Payments, uploads, messaging replies/threads
* Monitoring alerts (“performance drop alerts”, push thresholds). No alerting in Phase-1.
* Showing rotation day or block numbers anywhere in UI.
* Any sibling comparison.

## Architecture constraints (must obey)

* **Server-side permissions** only. No UI-only gating.
* **One-call Home load**: 1 request preferred, max 2.
* No N+1 queries. Batch with `IN`.
* Use **Redis** only for stable templates (schedule structure), not for mutable per-student events.
* SPA transport boundary remains **only** in `ui-spa/src/resources/frappe.ts`.
* Services return domain payload only (no toasts, no signals unless mutation; Phase-1 is read-mostly).

## Backend deliverable

### New whitelisted method

`ifitwala_ed.api.guardian_home.get_guardian_home_snapshot(anchor_date=None, school_days=7, debug=0)`

**Inputs**

* `anchor_date`: `YYYY-MM-DD` (optional, default today in site TZ)
* `school_days`: int (default 7)
* `debug`: int (default 0)

**Output**

* Must match `GuardianHomeSnapshot` TS contract exactly.

## Data sources (confirmed in repo uploads)

* Guardian ↔ students: `Guardian` child table (Guardian Student), plus Student links
* Student Log (guardian-visible only)
* Org Communication + Org Communication Audience
* Communication Interaction (read/unread/reaction state)
* Task Delivery (assignment unit), Task (metadata), Task Outcome (published results only)
* School Calendar + Holidays, School Event (audience-scoped if applicable), School Schedule templates

## Acceptance tests (“done means”)

1. Guardian with 2–4 kids sees a coherent family timeline for next 7 school days.
2. No “rotation day” or “block number” is visible in UI or API payload.
3. Unread communications count matches interactions.
4. Student logs shown only when guardian-visible.
5. Results shown only when `Task Outcome.is_published = 1` (and include published date).
6. Page loads with a single request, stable response shape, no console errors.

---

# docs/portal/guardian/codex_task_breakdown_phase1.md

## PR-G1 — Endpoint skeleton + strict guardian scope

**Backend**

* Create `ifitwala_ed/api/guardian_home.py`
* Implement `get_guardian_home_snapshot(...)` returning correct empty structure (meta + zones + counts)
* Implement guardian → linked student list resolution (server-side enforcement)

**Acceptance**

* Endpoint exists, returns stable JSON keys, empty arrays, counts = 0.

---

## PR-G2 — Schedule horizon + calendar-aware “next 7 school days”

**Backend**

* Compute next N school days using School Calendar + Holidays (no hardcoded weekends only).
* For each student: resolve school schedule blocks into plain-language blocks:

  * `start_time`, `end_time`, `title`/`subtitle`, `kind`
* Cache schedule templates per school in Redis (TTL 6–24h).

**Acceptance**

* Timeline returns exactly N school days (or less if end-of-year edge case).
* No rotation/block leakage.

---

## PR-G3 — Task Delivery due/assessment chips

**Backend**

* Pull Task Deliveries relevant to the guardian’s children via student group membership.
* Use `Task Delivery.available_from`, `due_date`, `lock_date`, `delivery_mode`, `student_group`, `task`.
* Return “due today” and “upcoming assessments” chips (signal-only).

**Acceptance**

* Due chips appear, ordered by due date.
* No task noise flood (cap per child/day, provide “View all” in UI later).

---

## PR-G4 — Published Task Outcomes in Recent Activity

**Backend**

* Pull Task Outcomes for guardian’s children (only those linked to deliveries/tasks) where:

  * `is_published = 1`
  * include `published_on`, `published_by`
* Return Recent Activity items.

**Acceptance**

* No unpublished outcomes appear, ever.

---

## PR-G5 — Org Communication + unread logic

**Backend**

* Pull `Org Communication` scoped to guardian using `Org Communication Audience`.
* Determine `is_unread` using `Communication Interaction` (e.g., read receipt / last interaction / explicit read flag depending on schema).
* Include:

  * `unread_communications` count
  * Recent Activity communication items
  * Attention Needed communication items if unread / requires_ack.

**Acceptance**

* Unread count matches interaction rows.
* Only audience-targeted comms are visible.

---

## PR-G6 — Student Logs + attendance exceptions

**Backend**

* Student Log: include only guardian-visible logs.
* Attendance: include only exceptions (avoid dumping all rows).

**Acceptance**

* Guardian sees only what is allowed for their child(ren).

---

## PR-G7 — SPA contracts + service + GuardianHome wiring

**Frontend**

* Add TS contracts file (below).
* Add service `ui-spa/src/lib/service/guardianHome/guardianHomeService.ts` following your existing pattern.
* Wire `GuardianHome.vue` to one-call snapshot load, render zones.

**Acceptance**

* One request loads Home.
* No toasts in service; page owns loading/error.

---

# ifitwala_ed/ui-spa/src/contracts/guardian/guardianHomeContracts.ts

```ts
export type GuardianHomeSnapshot = {
  meta: {
    generated_at: string
    anchor_date: string
    school_days: number
    guardian: { name: string }
  }
  family: {
    children: ChildRef[]
  }
  zones: {
    family_timeline: FamilyTimelineDay[]
    attention_needed: AttentionItem[]
    preparation_and_support: PrepItem[]
    recent_activity: RecentActivityItem[]
  }
  counts: {
    unread_communications: number
    unread_visible_student_logs: number
    upcoming_due_tasks: number
    upcoming_assessments: number
  }
  debug?: { warnings: string[] }
}

export type ChildRef = {
  student: string
  full_name: string
  school: string
  student_image_url?: string
}

export type FamilyTimelineDay = {
  date: string
  label: string
  is_school_day: boolean
  children: ChildTimeline[]
}

export type ChildTimeline = {
  student: string
  day_summary: { start_time: string; end_time: string; note?: string }
  blocks: TimelineBlock[]
  tasks_due: DueTaskChip[]
  assessments_upcoming: DueTaskChip[]
}

export type TimelineBlock = {
  start_time: string
  end_time: string
  title: string
  subtitle?: string
  kind: "course" | "activity" | "recess" | "assembly" | "other"
}

export type DueTaskChip = {
  task_delivery: string
  title: string
  due_date: string
  kind: "assessment" | "homework" | "classwork" | "other"
  status: "assigned" | "submitted" | "missing" | "completed"
}

export type AttentionItem = AttendanceAttention | StudentLogAttention | CommunicationAttention

export type AttendanceAttention = {
  type: "attendance"
  student: string
  date: string
  time?: string
  summary: string
}

export type StudentLogAttention = {
  type: "student_log"
  student: string
  student_log: string
  date: string
  time?: string
  summary: string
  follow_up_status?: "Open" | "In Progress" | "Completed" | "Closed"
}

export type CommunicationAttention = {
  type: "communication"
  communication: string
  date: string
  title: string
  requires_ack?: boolean
  is_unread: boolean
}

export type PrepItem = {
  student: string
  date: string
  label: string
  source: "schedule" | "task" | "communication"
  related?: {
    task_delivery?: string
    communication?: string
    schedule_hint?: { start_time: string; end_time: string }
  }
}

export type RecentActivityItem = PublishedResultItem | StudentLogItem | CommunicationItem

export type PublishedResultItem = {
  type: "task_result"
  student: string
  task_outcome: string
  title: string
  published_on: string
  published_by?: string
  score?: { value: number | string; max?: number; label?: string }
  narrative?: string
}

export type StudentLogItem = {
  type: "student_log"
  student: string
  student_log: string
  date: string
  summary: string
}

export type CommunicationItem = {
  type: "communication"
  communication: string
  date: string
  title: string
  is_unread: boolean
}
```

---

# ifitwala_ed/api/guardian_home.py (backend skeleton)

```python
import frappe
from frappe import _
from frappe.utils import now_datetime, getdate

@frappe.whitelist()
def get_guardian_home_snapshot(anchor_date=None, school_days=7, debug=0):
	"""
	Phase-1 Guardian Home snapshot.
	Returns a single bundled payload for Guardian Home.
	Server-side permissions enforced. No rotation_day or block_number may leak.
	"""
	anchor = getdate(anchor_date) if anchor_date else getdate()
	try:
		school_days = int(school_days or 7)
	except Exception:
		frappe.throw(_("Invalid school_days"))

	payload = {
		"meta": {
			"generated_at": now_datetime().isoformat(),
			"anchor_date": str(anchor),
			"school_days": school_days,
			"guardian": {"name": None},
		},
		"family": {"children": []},
		"zones": {
			"family_timeline": [],
			"attention_needed": [],
			"preparation_and_support": [],
			"recent_activity": [],
		},
		"counts": {
			"unread_communications": 0,
			"unread_visible_student_logs": 0,
			"upcoming_due_tasks": 0,
			"upcoming_assessments": 0,
		},
	}

	if int(debug or 0):
		payload["debug"] = {"warnings": []}

	# NOTE: Implementation added in PR-G1..G6 in small steps.
	return payload
```

---
