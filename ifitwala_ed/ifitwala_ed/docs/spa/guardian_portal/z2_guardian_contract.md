<!-- docs/portal/guardian/guardian_home_data_contract.md -->

# Guardian Home — Data Contract (v0.1)

This document defines the **single payload** returned to render Guardian Home (parent-centric) with **minimal clicking**, **plain language**, and strict **visibility rules**.

---

## 1) Endpoint shape

### Server method (proposed)

`ifitwala_ed.api.guardian_home.get_guardian_home_snapshot`

**Request**

* `anchor_date?: string` (YYYY-MM-DD, default: today in System Settings timezone)
* `school_days: number` (default 7; “next 7 school days” per product intent)
* `timezone?: never` (always use site timezone)

**Response**

* `GuardianHomeSnapshot`

---

## 2) Primary payload

### `GuardianHomeSnapshot`

```ts
export type GuardianHomeSnapshot = {
  meta: {
    generated_at: string;        // ISO datetime in site TZ
    anchor_date: string;         // YYYY-MM-DD
    school_days: number;         // e.g. 7
    guardian: {
      name: string;              // Guardian.name (docname)
    };
  };

  family: {
    children: ChildRef[];        // ordered for scanning (see sorting)
    selected_child?: string;     // optional; UI local state, not required server-side
  };

  zones: {
    family_timeline: FamilyTimelineDay[];     // next 7 school days
    attention_needed: AttentionItem[];        // exceptions / things to notice
    preparation_and_support: PrepItem[];      // “pack swim kit”, “bring instrument”, etc.
    recent_activity: RecentActivityItem[];    // latest published results, visible logs, comms, etc.
  };

  counts: {
    unread_communications: number;
    unread_visible_student_logs: number;
    upcoming_due_tasks: number;
    upcoming_assessments: number;
  };

  debug?: {
    warnings: string[];
  };
};
```

### Child identity + switching

Parents start **family-first**; child switching is **occasional**.

```ts
export type ChildRef = {
  student: string;          // Student.name
  full_name: string;        // Student student_full_name (or equivalent)
  school: string;           // Student.school (if present) else derived
  student_image_url?: string;
};
```

---

## 3) Zone contracts

### 3.1 Family Timeline (next 7 school days)

This is the **default** view. It must be calendar-aware (skip non-school days).

```ts
export type FamilyTimelineDay = {
  date: string;                 // YYYY-MM-DD
  label: string;                // “Mon 12 Feb”
  is_school_day: boolean;
  children: ChildTimeline[];
};

export type ChildTimeline = {
  student: string;              // Student.name
  day_summary: {
    start_time: string;         // hh:mm
    end_time: string;           // hh:mm
    note?: string;              // optional, calm tone
  };

  blocks: TimelineBlock[];      // plain language, no “Rotation Day / Block #”
  tasks_due: DueTaskChip[];     // due today chips
  assessments_upcoming: DueTaskChip[]; // within lookahead window
};

export type TimelineBlock = {
  start_time: string;           // hh:mm
  end_time: string;             // hh:mm
  title: string;                // e.g. “Morning”, “After lunch”, “Class”, “Activity”
  subtitle?: string;            // e.g. course name, location, teacher (only if available + allowed)
  kind: "course" | "activity" | "recess" | "assembly" | "other";
};

export type DueTaskChip = {
  task_delivery: string;        // Task Delivery docname (if exists) else Task
  title: string;                // Task title
  due_date: string;             // YYYY-MM-DD
  kind: "assessment" | "homework" | "classwork" | "other";
  status: "assigned" | "submitted" | "missing" | "completed"; // parent-facing state (derived)
};
```

#### Schedule data source + transformation rules

* **Raw schedule time bounds** come from **School Schedule Block** child rows:

  * `rotation_day` (Int), `block_number` (Int), `from_time` (Time), `to_time` (Time), `block_type` (Select), `description` (Data).
* Rotation labels exist in **School Schedule Day**: `rotation_day`, `rotation_label`, `number_of_blocks`.
* **School Schedule** defines rotation system and first-day alignment:

  * `first_day_rotation_day`, `rotation_days`, `include_holidays_in_rotation`, plus child tables.

**Parent UX rule (non-negotiable):**

* Parents must never see `rotation_day` or `block_number` directly.
* The server converts (date → actual rotation day → blocks) and returns **plain-language block labels**.

**Block labeling strategy (v0.1):**

* Use `School Schedule Block.block_type` for `kind`.
* Use time ranges to generate labels:

  * First block(s) before ~11:00 → “Morning”
  * Midday → “Midday”
  * After ~12:30 → “After lunch”
  * Late day → “End of day”
* If `description` is set, it can become `subtitle` (short) or override `title` when appropriate.

> Note: this avoids teaching the rotation model while still respecting it.

---

### 3.2 Attention Needed (exceptions)

This is the “Is everything OK?” zone. No severity scoring; parents decide.

```ts
export type AttentionItem =
  | AttendanceAttention
  | StudentLogAttention
  | CommunicationAttention;

export type AttendanceAttention = {
  type: "attendance";
  student: string;
  date: string;
  time?: string;                 // hh:mm
  summary: string;               // “Marked absent in the morning”
  detail_route: { name: "guardian-student-attendance"; params: { student: string } };
};

export type StudentLogAttention = {
  type: "student_log";
  student: string;
  student_log: string;           // Student Log.name
  date: string;
  time?: string;
  summary: string;               // short plain summary (no HTML)
  follow_up_status?: "Open" | "In Progress" | "Completed";  // from Student Log
  detail_route: { name: "guardian-student-log"; params: { student_log: string } };
};

export type CommunicationAttention = {
  type: "communication";
  communication: string;         // Communication.name
  date: string;
  title: string;
  requires_ack?: boolean;
  is_unread: boolean;
  detail_route: { name: "guardian-communication"; params: { communication: string } };
};
```

#### Visibility gates (hard requirements)

* Student Logs must be filtered by `Student Log.visible_to_guardians = 1`.
* Attendance is inherently sensitive; only include for **linked children** (guardian scope) and keep language neutral.

Attendance source:

* `Student Attendance` includes `attendance_date`, `attendance_time`, `rotation_day`, `block_number`, `attendance_code`, etc.

---

### 3.3 Preparation & Support (reduce “pack anxiety”)

```ts
export type PrepItem = {
  student: string;
  date: string;                  // YYYY-MM-DD
  label: string;                 // “Bring PE kit”, “Swim bag”
  source: "schedule" | "task" | "communication";
  related?: {
    task_delivery?: string;
    communication?: string;
    schedule_hint?: { start_time: string; end_time: string };
  };
};
```

Sources (v0.1):

* `School Schedule Block.block_type` + optional `description` (“PE”, “Swim”, “Activity kit”).
* Tasks that include required materials (if modeled in Task instructions; see Task has `instructions` Text Editor).
* Communications tagged to guardians (via audience list; mapping to be finalized once Communication doctype is attached).

---

### 3.4 Recent Activity (lightweight, calm feed)

```ts
export type RecentActivityItem =
  | PublishedResultItem
  | StudentLogItem
  | CommunicationItem;

export type PublishedResultItem = {
  type: "task_result";
  student: string;
  task_outcome: string;         // Task Outcome.name
  title: string;                // Task title
  published_on: string;         // YYYY-MM-DD (or ISO date)
  score?: {
    value: number | string;     // supports points/levels
    max?: number;
    label?: string;             // e.g. “4/7”, “Achieved”, “Developing”
  };
  narrative?: string;           // brief, sanitized
  detail_route: { name: "guardian-task-result"; params: { task_outcome: string } };
};

export type StudentLogItem = {
  type: "student_log";
  student: string;
  student_log: string;
  date: string;
  summary: string;
};

export type CommunicationItem = {
  type: "communication";
  communication: string;
  date: string;
  title: string;
  is_unread: boolean;
};
```

#### Results publication gate (must be explicit)

Task outcomes must only appear when **published**. Your product wording says “published to parents”; the concrete implementation uses an explicit publish flag on Task Outcome (field name to verify in `task_outcome.json` when you attach it), and the UI must treat *unpublished* as **non-existent** to guardians.

---

## 4) Mapping: Doctypes → Guardian Home

### Guardian scope (family)

* `Guardian` has a child table `students` of type **Guardian Student**.
* `Student Log` is linked to `student` and guarded by `visible_to_guardians`.
* `Student Attendance` is linked to `student` and includes day/time/block fields.

### Schedule

* `School Schedule` → `School Schedule Day` + `School Schedule Block`.

---

## 5) Sorting and time windows

### Default ordering (family-first scanning)

* Children order:

  1. Then-current school (if multiple), then alphabetical by `full_name`.
* Family Timeline day order: ascending date, next 7 **school days**.

### Lookahead windows

* Timeline: next 7 **school days**.
* Upcoming due tasks: next 7 calendar days (or match school days if you prefer consistency).
* Recent activity: last 7 calendar days (cap to 50 items total across family).

---

## 6) Caching guidance (Redis)

### Safe to cache (shared / stable)

* Schedule templates per school calendar:

  * `School Schedule` + `School Schedule Block` + `School Schedule Day` can be cached with TTL (e.g. 6–24h) because they change rarely.

### Not safe to cache as shared truth (user-specific)

* Anything derived from:

  * Attendance rows (`Student Attendance`)
  * Student Logs filtered by `visible_to_guardians`
  * Communications read/unread
  * Task results publish state

### Recommended approach

* Cache schedule template pieces in Redis.
* Build GuardianHomeSnapshot per request with **batched queries** and minimal joins.
* Optional short per-guardian cache (30–120s) if needed for bursty refresh, but invalidate via signals when:

  * New visible student log created/updated
  * New published task outcome
  * New communication for guardian
  * Attendance updated for linked student

---

## 7) Weekly summary (future hook)

Not part of v0.1 payload rendering, but reserve a slot:

```ts
weekly_summary?: {
  week_start: string;           // YYYY-MM-DD
  highlights: string[];         // calm bullet summaries
  items_to_watch: string[];     // “Assessment on Thu”, “Project due”
};
```

---

Below is the **updated, complete contract file** incorporating the Communication layer you just shared.
This **supersedes** the earlier draft and is ready for agents + humans.

---

# docs/portal/guardian/guardian_home_data_contract.md

**Guardian Home — Data Contract (v0.2)**
Status: **Green-lit**
Audience: Humans + Coding Agents
Authoritative scope: Guardian Home (Phase-1)

---

## 0. Purpose

Define the **single canonical payload** used to render **Guardian Home**, enforcing:

* Parent-centric, family-first view
* Calm, awareness-oriented UX (anti-surveillance by default)
* Strict server-side visibility and audience rules
* Plain-language translation of school internals

---

## 1. Endpoint

### Server method

`ifitwala_ed.api.guardian_home.get_guardian_home_snapshot`

### Request

```json
{
  "anchor_date": "YYYY-MM-DD (optional, default = today)",
  "school_days": 7
}
```

* Timezone: **always System Settings timezone**
* No client-supplied timezone accepted

---

## 2. Root Payload

```ts
export type GuardianHomeSnapshot = {
  meta: {
    generated_at: string;     // ISO datetime (site TZ)
    anchor_date: string;      // YYYY-MM-DD
    school_days: number;
    guardian: {
      name: string;           // Guardian.name
    };
  };

  family: {
    children: ChildRef[];
  };

  zones: {
    family_timeline: FamilyTimelineDay[];
    attention_needed: AttentionItem[];
    preparation_and_support: PrepItem[];
    recent_activity: RecentActivityItem[];
  };

  counts: {
    unread_communications: number;
    unread_visible_student_logs: number;
    upcoming_due_tasks: number;
    upcoming_assessments: number;
  };

  debug?: {
    warnings: string[];
  };
};
```

---

## 3. Family Identity

```ts
export type ChildRef = {
  student: string;        // Student.name
  full_name: string;
  school: string;
  student_image_url?: string;
};
```

Rules:

* Guardian Home defaults to **family view**
* Child-centric drill-down is optional UI state, not part of payload

---

## 4. Zone Contracts

---

### 4.1 Family Timeline (primary surface)

Next **N school days**, calendar-aware.

```ts
export type FamilyTimelineDay = {
  date: string;           // YYYY-MM-DD
  label: string;          // “Mon 12 Feb”
  is_school_day: boolean;
  children: ChildTimeline[];
};
```

```ts
export type ChildTimeline = {
  student: string;

  day_summary: {
    start_time: string;   // hh:mm
    end_time: string;     // hh:mm
  };

  blocks: TimelineBlock[];
  tasks_due: DueTaskChip[];
  assessments_upcoming: DueTaskChip[];
};
```

```ts
export type TimelineBlock = {
  start_time: string;
  end_time: string;
  title: string;         // “Morning”, “After lunch”, etc.
  subtitle?: string;
  kind: "course" | "activity" | "recess" | "assembly" | "other";
};
```

**Hard UX rule**

* `rotation_day`, `block_number` **never leave the server**

---

### 4.2 Attention Needed (exceptions only)

```ts
export type AttentionItem =
  | AttendanceAttention
  | StudentLogAttention
  | CommunicationAttention;
```

#### Attendance

```ts
export type AttendanceAttention = {
  type: "attendance";
  student: string;
  date: string;
  summary: string;
};
```

#### Student Log

```ts
export type StudentLogAttention = {
  type: "student_log";
  student: string;
  student_log: string;
  date: string;
  summary: string;
  follow_up_status?: "Open" | "In Progress" | "Completed";
};
```

Visibility rule:

* Only `Student Log.visible_to_guardians = 1`

---

### 4.3 Communication (Org Communication)

**Source**

* `Org Communication`
* `Org Communication Audience`
* `Communication Interaction`

```ts
export type CommunicationAttention = {
  type: "communication";
  communication: string;
  date: string;
  title: string;
  is_unread: boolean;
  requires_ack?: boolean;
};
```

Rules:

* Guardian sees communication **only if**:

  * They are explicitly included in `Org Communication Audience`
  * Or audience is “All Guardians” (if modeled)
* Read state derived from `Communication Interaction`

---

### 4.4 Preparation & Support

```ts
export type PrepItem = {
  student: string;
  date: string;
  label: string;          // “Bring PE kit”, “Swim bag”
  source: "schedule" | "task" | "communication";
};
```

Sources:

* Schedule block descriptions (PE, Swim, Activity)
* Task instructions (if relevant)
* Communication hints

---

### 4.5 Recent Activity

```ts
export type RecentActivityItem =
  | PublishedResultItem
  | StudentLogItem
  | CommunicationItem;
```

#### Published Result

```ts
export type PublishedResultItem = {
  type: "task_result";
  student: string;
  task_outcome: string;
  title: string;
  published_on: string;
  published_by?: string;

  score?: {
    value: number | string;
    max?: number;
    label?: string;
  };

  narrative?: string;
};
```

**Publication gate**

* `Task Outcome.is_published = 1`
* `published_on IS NOT NULL`

#### Student Log

```ts
export type StudentLogItem = {
  type: "student_log";
  student: string;
  student_log: string;
  date: string;
  summary: string;
};
```

#### Communication

```ts
export type CommunicationItem = {
  type: "communication";
  communication: string;
  date: string;
  title: string;
  is_unread: boolean;
};
```

---

## 5. Sorting & Windows

* Timeline: next **7 school days**
* Recent activity: last **7 calendar days**
* Attention Needed: **all unresolved / unread**

---

## 6. Monitoring vs Awareness (policy)

Default:

* No real-time grade streams
* No automated performance alerts

Optional (future setting):

* “Monitoring Mode” must be explicit, per-guardian, reversible
* Still respects `is_published` and visibility rules

---

## 7. Caching Rules

Allowed:

* Schedule templates (school-level) → Redis TTL (6–24h)

Not allowed:

* Guardian-specific snapshots as long-term cache
* Attendance, logs, communications as shared cache

Short TTL (30–120s) per guardian allowed **with invalidation**.

---

## 8. Weekly Summary (reserved)

Not rendered yet, but contract slot reserved:

```ts
weekly_summary?: {
  week_start: string;
  highlights: string[];
  items_to_watch: string[];
};
```

---

## 9. Completion Criteria (Phase-1)

Guardian Home is compliant when:

* One server call renders Home
* No internal school mechanics leak
* Communications, logs, outcomes respect visibility
* Multi-child families can scan in <30 seconds
* No sibling comparison possible

---
