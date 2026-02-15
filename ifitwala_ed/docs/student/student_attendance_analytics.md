## Bottom line (what this dashboard is)

A **single Attendance Analytics surface** with **role-gated sections**, optimized for:

* fast situational awareness,
* early intervention,
* zero cognitive noise,
* honest data (no client-side inference).

One page. Multiple lenses. No duplicated dashboards.

---

## Core design principles (non-negotiable)

1. **Attendance is signal, not bureaucracy**

   * We surface *patterns*, *risk*, and *exceptions*, not raw logs.

2. **Whole-day vs block attendance are separate analytical modes**

   * `whole_day = 1` → daily compliance & wellbeing.
   * `whole_day = 0` → instructional fidelity & schedule integrity.
   * Never mixed implicitly.

3. **Semantics are school-defined, interpretation is standardized**

   * School defines codes.
   * Platform enforces:

     * Present vs Absent (via `count_as_present`)
     * Late as *present with friction*
     * Excused ≠ ignored (still tracked).

4. **Role determines horizon, not truth**

   * Same data.
   * Different aggregation, visibility, and framing.

---

## Page structure (high-level)

**Route**

```
/staff/analytics/attendance
```

**Companion Ledger Route**

```
/staff/analytics/attendance-ledger
```

Use this page for desk-equivalent, row-level attendance auditing (filters, grouped rows, dynamic code columns, and pagination). Keep `/staff/analytics/attendance` as the pattern-first executive surface.

**Persistent layout**

* FiltersBar (date range, school, program, student_group)
* Mode switch:

  * ◉ Whole Day
  * ◉ By Block / Session

**Calendar inheritance rule (Academic Year / Term filters)**

* If the selected school has no Academic Year or Term rows, the backend resolves the first ancestor school in the school tree that has them.
* Resolution order is strict: self -> parent -> grandparent (first match wins).
* This preserves sibling isolation while supporting shared parent calendars across child schools.

---

## SECTION A — Universal KPIs (everyone sees)

Purpose: *“Are we okay today?”*

**KPI Row**

* Attendance rate (present / expected)
* Absence rate
* Late rate
* % unexplained absences
* Trend indicator vs previous comparable window

Rules:

* Driven purely by `count_as_present`
* No per-student detail here
* Calm color scale (no red unless truly critical)

---

## SECTION B — Teachers (Instructor-scoped)

Visible only to **Instructor**

Scope:

* Students they teach
* Student Groups they are assigned to
* Block-level if applicable

### What teachers actually need (from competitors + reality)

Not:

* Term-wide compliance charts
* Export buttons

They need:

* “Who should I worry about *this week*?”

### Components

1. **My Groups Attendance Snapshot**

   * One card per Student Group
   * 7–14 day rolling window
   * Heatmap: day × block (if block-based)

2. **Students with Emerging Patterns**

   * Criteria (server-side):

     * ≥2 absences in last N sessions
     * frequent late arrivals
     * pattern-based (e.g. always absent block 1)
   * Click → student attendance drill-down (read-only)

3. **Today / This Week Exceptions**

   * Students expected but missing
   * Clear labels: “Absent”, “Late”, “No record”

This mirrors what **PowerSchool + ManageBac** fail at: they show totals, not patterns.

---

## SECTION C — Counselors / Pastoral Leaders

Visible to:

* Counselor
* Pastoral Lead
* Program-level instructors

Scope:

* Their assigned cohorts / programs
* Longer horizon (4–8 weeks)

### Focus: wellbeing & disengagement

1. **Chronic Absence Radar**

   * Histogram: % attendance buckets
   * Threshold markers are resolved from **School settings** on the selected root school:

     * `attendance_warning_threshold`
     * `attendance_critical_threshold`
   * Bucket semantics:

     * Critical: rate `< critical`
     * Warning: rate `>= critical` and `< warning`
     * OK: rate `>= warning`
   * Only students with expected sessions in the selected window are bucketed.

### School settings governance

* Threshold source is **server-owned** and read from the selected root school.
* UI does not own threshold values.
* On child school creation, threshold fields are copied from the parent school by default.

2. **Risk Signals**

   * Students with:

     * declining attendance trend
     * frequent unexplained absences
     * mismatch between whole-day present but block absences

3. **Block vs Day Mismatch**

   * Students marked present whole-day
   * but missing key blocks
   * This is a *pastoral goldmine* competitors ignore.

No raw tables by default.
Everything is *action-oriented*.

---

## SECTION D — Academic Admin / Assistant (global view)

Visible to:

* Academic Admin
* Academic Assistant

Scope:

* Entire school / program
* Cross-grade comparison

### What admins actually need

Not:

* Student names by default

They need:

* System health
* Operational issues
* Policy alignment

### Components

1. **Attendance Compliance Overview**

   * By School → Program → Grade
   * Whole-day first, block second

2. **Block Integrity Analysis**

   * Heatmap: block × day
   * Identify:

     * systemic under-attendance
     * schedule or staffing issues

3. **Attendance Method Mix**

   * Manual vs RFID vs QR vs API
   * Flags reliability gaps

4. **Codes Usage Audit**

   * Which attendance codes are used
   * Which are never used
   * Which count as present but dominate absences
   * This is *configuration insight*, not pedagogy.

---

## Activities / Extra-Curricular Attendance

Handled as a **parallel lens**, not mixed.

* Filter: `program_type = Activity`
* Session-based, not day-based
* Metrics:

  * participation rate
  * dropout patterns
  * instructor coverage

Competitors almost universally botch this by forcing ECA into academic logic.

---

## Primary vs Secondary vs College (adaptive behavior)

No branching dashboards.
Behavior adapts based on data availability.

| Context    | Default Mode | Emphasis                   |
| ---------- | ------------ | -------------------------- |
| Primary    | Whole day    | wellbeing, consistency     |
| Secondary  | Block        | instructional engagement   |
| College    | Session      | participation & compliance |
| Activities | Session      | retention & interest       |

Derived server-side from schedule + data density.

---

## Drill-down philosophy

* Aggregates → lists → individual
* Always permission-checked server-side
* No client-side filtering of sensitive data
* Drill-down is optional, never forced

---

## Competitive differentiation (why this wins)

Compared to:

* **PowerSchool**: too administrative
* **ManageBac**: too IB-form-centric
* **Skyward**: data-dense, insight-poor

Ifitwala’s edge:

* pattern detection, not just totals
* role-aware without duplicating dashboards
* whole-day vs block treated honestly
* calm, educator-first UX

---

## Phased delivery (recommended)

**Phase 1**

* KPIs
* Teacher + Admin sections
* Whole-day + block switch

**Phase 2**

* Counselor risk analytics
* Pattern detection
* Method integrity views

**Phase 3**

* Alerts & signals (outside dashboard)
* Saved views / presets

---

## Final note (important)

This dashboard should **not** feel like “analytics”.

It should feel like:

> “I understand what’s happening, and I know where to look next.”



======================================================================











Below are **Codex-grade backend instructions** for the Attendance Dashboard aggregation layer.
This is **governance + performance first**. Treat this as *authoritative marching orders* for agents.

---

# Codex Instructions

## Attendance Analytics – Backend Aggregation (Ifitwala_Ed)

### Objective

Provide **fast, role-aware, hierarchy-safe attendance analytics** over **very large datasets**, without:

* row-by-row processing,
* per-student loops,
* chatty APIs,
* or client-side inference.

Everything must scale to **millions of attendance rows**.

---

## 0. Non-Negotiable Rules

1. **Never query raw Student Attendance rows unless absolutely necessary**
2. **Always aggregate in SQL**
3. **Always scope by School hierarchy (parent → children)**
4. **Always enforce role scope server-side**
5. **Prefer pre-aggregated tables when available**
6. **Cache aggressively, invalidate deterministically**

Violating any of these is a bug.

---

## 1. School Hierarchy Resolution (FIRST STEP)

### Input

* `school` (optional)
* If not provided → use **employee.default_school**

### Required behavior

* If `school` is a **parent**, include **all descendants**
* If `school` is a leaf, include only itself

### Canonical pattern

Use existing `school_tree.py`.

**Do not** recurse manually.
**Do not** fetch children one by one.

```python
school_scope = get_school_scope_for_school(school)
# returns list[str] of school names including descendants
```

This list is used in **every WHERE clause**.

---

## 2. Time Window Resolution

### Inputs

* `start_date`
* `end_date`
* `academic_year`
* `term` (optional)
* `whole_day` (0/1)

### Rules

* Default window = current term OR rolling N days (configurable)
* Exclude:

  * weekends
  * holidays
  * breaks
    using **School Calendar** tables

### Pattern

* Precompute **valid_instruction_days** once per request
* Pass dates into SQL using `BETWEEN`

Never compute day validity per row.

---

## 3. Attendance Semantics (Critical)

### Inputs

* Attendance Code table (`student_attendance_code.json`)
* Fields like:

  * `count_as_present`
  * `is_late`
  * `is_excused`

### Canonical mapping (server-side)

Resolve once per request:

```python
code_map = {
  "P": {"present": 1, "late": 0},
  "L": {"present": 1, "late": 1},
  "A": {"present": 0, "late": 0},
}
```

This map is injected into SQL via CASE statements.

**Never infer semantics client-side.**

---

## 4. Role-Based Scope Enforcement

### Role → Scope matrix

| Role                 | Scope                                                 |
| -------------------- | ----------------------------------------------------- |
| Instructor           | Students in Student Groups they teach                 |
| Counselor / Pastoral | Programs / Groups they are assigned to                |
| Academic Admin       | All schools in hierarchy                              |
| Academic Assistant   | Same as Admin (read-only semantics handled elsewhere) |

### Pattern

Resolve **student_ids** or **group_ids** first, then join.

Never filter attendance rows by role directly.

---

## 5. Aggregation Strategy (Core)

### Use TWO layers

#### A. Primary Source

`Student Attendance Summary` (when possible)

This table already provides:

* totals
* rates
* per-student aggregation

Use it for:

* KPI tiles
* histograms
* risk buckets
* counselor/admin views

#### B. Raw Attendance (ONLY when required)

Used for:

* heatmaps
* block integrity
* short rolling windows

---

## 6. Canonical Aggregation Queries

### A. Whole-Day KPIs (FAST PATH)

```sql
SELECT
  COUNT(*) AS total_students,
  SUM(present_count) AS present_sessions,
  SUM(absent_count) AS absent_sessions,
  SUM(late_count) AS late_sessions,
  AVG(attendance_rate) AS avg_rate
FROM `tabStudent Attendance Summary`
WHERE school IN %(school_scope)s
AND academic_year = %(academic_year)s
AND last_updated_on BETWEEN %(start)s AND %(end)s
```

One query. No joins.

---

### B. Block-Level Heatmap (RAW but bounded)

```sql
SELECT
  attendance_date,
  block_number,
  SUM(CASE WHEN code.count_as_present = 1 THEN 1 ELSE 0 END) AS present,
  COUNT(*) AS expected
FROM `tabStudent Attendance` a
JOIN `tabAttendance Code` code ON code.name = a.attendance_code
WHERE a.school IN %(school_scope)s
AND a.attendance_date BETWEEN %(start)s AND %(end)s
AND a.whole_day = 0
GROUP BY attendance_date, block_number
```

**Never join Student unless names are explicitly requested.**

---

### C. Risk Detection (Counselors)

```sql
SELECT
  student,
  attendance_rate,
  absent_count,
  late_count
FROM `tabStudent Attendance Summary`
WHERE school IN %(school_scope)s
AND attendance_rate < %(threshold)s
ORDER BY attendance_rate ASC
LIMIT 50
```

No loops. No Python filtering.

---

## 7. Caching Strategy (MANDATORY)

### Cache layers

| Layer                | TTL       |
| -------------------- | --------- |
| Admin global KPIs    | 30 min |
| Counselor aggregates | 30 min    |
| Teacher group views  | 15 min     |
| Heatmaps             | 15 min   |

### Pattern

```python
@redis_cache(ttl=600)
def get_attendance_kpis(...):
    ...
```

Cache key **must include**:

* school_scope hash
* role
* date window
* whole_day flag

---

## 8. Pagination & Payload Discipline

* Always return **already-aggregated data**
* Never return > 200 rows
* No student names unless drill-down
* Drill-down endpoints are separate

---

## 9. Forbidden Patterns (Auto-Reject PR)

* Python loops over attendance rows
* `frappe.get_all()` without aggregation
* Client-side counting
* Ignoring school hierarchy
* Role filtering in JS
* Per-student queries inside loops
* Multiple queries per chart

---

## 10. Validation Checklist (Codex must self-check)

Before marking “Done”, verify:

* [ ] One request → ≤ 3 SQL queries
* [ ] All queries use `IN %(school_scope)s`
* [ ] No raw attendance scan without date bounds
* [ ] Redis cache applied
* [ ] Role scope enforced before aggregation
* [ ] whole_day logic respected
* [ ] No silent fallback logic

---

## Final Guidance to Codex

> Treat attendance like **financial transactions**:
> aggregate early, cache aggressively, never scan blindly.

If performance feels “fine” without aggregation, it is already wrong.




=============================================================

Add this

1. The "Turnaround" Signal (The Happy Ending)
The Missing Story: Current dashboards are depressing. They only show who is failing, which causes "compassion fatigue" for teachers. A story needs a resolution. If a student had critical absence levels last month but attended 100% of this week, that is a massive win. Your current logic hides this student because they are no longer a "risk," but it fails to celebrate the improvement.

The Suggestion: Add a "Back on Track" or "Improving Trends" section in the Teacher and Counselor views.

Logic: Students who triggered a risk flag in the previous window but are clean in the current window.

Why it wins: It gives teachers/admin a reason to high-five a student. It validates that their interventions are working. It turns the dashboard into a tool for positive reinforcement, not just policing.

2. The "Context" Overlay (The Plot Twist)
The Missing Story: Attendance is rarely the root problem; it is a symptom. If a student is absent every Tuesday, your dashboard shows the pattern. But why? Is it because they have Math on Tuesdays and are failing it? Or because they have a medical appointment?

The Suggestion: Add a "Context Sparkline" toggle (Server-side optional join).

Visual: When viewing a "Risk Student," allow a toggle to overlay a simple sparkline of their Academic Standing or Behavioral Incidents over the same timeline.

Why it wins: It immediately differentiates Truancy (attendance down, behavior down) from Avoidance (attendance down, grades down) from Life Circumstances (attendance down, grades steady). This saves the counselor 20 minutes of digging through other tabs.



=========================================================================

# Single API File: `api/attendance.py`

## Design principle (locked)

* **One file**
* **One public method**
* **Multiple modes**
* **Strict aggregation only**
* **Zero duplication of queries**
* **Server decides scope, hierarchy, permissions**

Frontend never calls “heatmap”, “overview”, etc.
It calls **attendance.get(...) with a mode**.

---

## Public API (only entry point)

```python
@frappe.whitelist()
def get(
    mode: str,
    school: str | None = None,
    academic_year: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    whole_day: int | None = None,
    thresholds: dict | None = None,
):
    ...
```

### `mode` (required)

Allowed values (enum, validate strictly):

* `"overview"`
* `"heatmap"`
* `"risk"`
* `"code_usage"`
* `"my_groups"`

Anything else → `frappe.throw`.

---

## Shared Resolution Pipeline (MANDATORY)

Every call goes through **this exact pipeline**, in this order:

### 1. Resolve user + role

* Read `frappe.session.user`
* Resolve Employee
* Determine **role class**:

  * instructor
  * counselor / pastoral
  * academic_admin / assistant

No branching later without this.

---

### 2. Resolve school scope (parent → children)

Rules:

* If `school` provided → expand to descendants
* Else → use `employee.school`, expand to descendants
* Use **existing** `school_tree.py`
* Result: `school_scope: list[str]`

This list is injected into **every SQL query**.

---

### 3. Resolve time window

Inputs:

* `academic_year`
* `start_date`
* `end_date`

Rules:

* If dates not provided:

  * derive from active term / academic year
* Exclude:

  * holidays
  * weekends
  * breaks
    via **School Calendar**

Result:

* `date_from`
* `date_to`

---

### 4. Resolve attendance semantics (once)

Load `Student Attendance Code` once per request and build:

```python
attendance_semantics = {
  "present_codes": [...],
  "late_codes": [...],
  "absent_codes": [...]
}
```

Used only in SQL `CASE` statements.
Never loop in Python.

---

## Mode Implementations (inside same file)

### MODE: `"overview"`

**Purpose**
High-level KPIs.

**Data source**

* `tabStudent Attendance Summary` ONLY

**Query shape**

* 1 query
* Grouped implicitly via SUM / AVG
* Filtered by `school_scope`, `academic_year`, date window

**Returns**

```json
{
  "kpis": {
    "expected_sessions": 18240,
    "present_sessions": 16980,
    "absent_sessions": 960,
    "late_sessions": 300,
    "attendance_rate": 93.1
  },
  "trend": {
    "previous_rate": 94.0,
    "delta": -0.9
  }
}
```

**Cache**

* TTL: **900s**

---

### MODE: `"heatmap"`

**Purpose**
Block/day density & integrity.

**Data source**

* `tabStudent Attendance` (raw, but bounded)

**Rules**

* `whole_day = 0` enforced
* Always date-bounded
* Group by:

  * `(attendance_date, block_number)` OR `(attendance_date)`

**Returns**

```json
{
  "axis": { "x": [...], "y": [...] },
  "cells": [
    { "x": "2026-01-15", "y": 1, "present": 120, "expected": 128 }
  ]
}
```

**Cache**

* TTL: **900s**
* If role == instructor AND date == today → 600s allowed

---

### MODE: `"risk"`

**Purpose**
Counselor / pastoral detection.

**Data source**

* `tabStudent Attendance Summary`

**Rules**

* Uses `attendance_rate`
* Thresholds passed or defaults

**Returns**

```json
{
  "buckets": {
    "critical": 12,
    "warning": 28,
    "ok": 412
  },
  "top_critical": [
    {
      "student": "STU-00012",
      "attendance_rate": 72.5
    }
  ]
}
```

**Cache**

* TTL: **900s**

---

### MODE: `"code_usage"`

**Purpose**
Admin audit of attendance codes.

**Data source**

* Raw attendance
* Grouped by `attendance_code`

**Returns**

```json
{
  "codes": [
    { "attendance_code": "P", "count": 14200, "count_as_present": 1 }
  ]
}
```

**Cache**

* TTL: **1800s**

---

### MODE: `"my_groups"`

**Purpose**
Teacher snapshot.

**Scope**

* Student Groups the instructor teaches
* Today or small date window only

**Data source**

* Raw attendance
* Group → students resolved first

**Returns**

```json
{
  "groups": [
    {
      "student_group": "G5-A",
      "expected": 24,
      "present": 22,
      "absent": 2
    }
  ]
}
```

**Cache**

* TTL: **600s**

---

## SQL Indexes (still mandatory)

Same as previously specified.
Codex must **not** change or omit them.

(Indexes omitted here for brevity — they remain unchanged and required.)

---

## Hard Rejection Rules

Reject any PR where:

* More than **one attendance API file** is created
* Mode logic is split across files
* Python loops process attendance rows
* Client decides scope or hierarchy
* Multiple endpoints are added “for convenience”

---

## Mental Model to Enforce

> **attendance.get(mode=…) is a query engine, not a controller zoo**

Frontend switches modes.
Backend stays singular, strict, and fast.

===========================================================================



Correct. A+ means **backend contract + frontend TypeScript contracts are locked together**.
Below is the **complete TS side** for the **single API file** you approved:

```
api/attendance.py  ⇄  ui-spa/src/types/contracts/attendance.ts
```

No drift. No ad-hoc typing. No normalization.

---

# A. Canonical TS Contract

`ui-spa/src/types/contracts/attendance.ts`

This file is **authoritative** for the SPA.

```ts
// ui-spa/src/types/contracts/attendance.ts

/* -------------------------------------------
 * Shared enums & primitives
 * ----------------------------------------- */

export type AttendanceMode =
	| 'overview'
	| 'heatmap'
	| 'risk'
	| 'code_usage'
	| 'my_groups'

export type AttendanceHeatmapMode = 'block' | 'day'

export interface AttendanceBaseParams {
	mode: AttendanceMode
	school?: string
	academic_year?: string
	start_date?: string
	end_date?: string
	whole_day?: 0 | 1
}

/* -------------------------------------------
 * Request payloads (discriminated union)
 * ----------------------------------------- */

export interface AttendanceOverviewParams extends AttendanceBaseParams {
	mode: 'overview'
}

export interface AttendanceHeatmapParams extends AttendanceBaseParams {
	mode: 'heatmap'
	heatmap_mode: AttendanceHeatmapMode
}

export interface AttendanceRiskParams extends AttendanceBaseParams {
	mode: 'risk'
	thresholds?: {
		warning: number
		critical: number
	}
}

export interface AttendanceCodeUsageParams extends AttendanceBaseParams {
	mode: 'code_usage'
}

export interface AttendanceMyGroupsParams extends AttendanceBaseParams {
	mode: 'my_groups'
	date?: string
}

export type AttendanceRequest =
	| AttendanceOverviewParams
	| AttendanceHeatmapParams
	| AttendanceRiskParams
	| AttendanceCodeUsageParams
	| AttendanceMyGroupsParams

/* -------------------------------------------
 * Response payloads
 * ----------------------------------------- */

export interface AttendanceOverviewResponse {
	kpis: {
		expected_sessions: number
		present_sessions: number
		absent_sessions: number
		late_sessions: number
		attendance_rate: number
	}
	trend: {
		previous_rate: number
		delta: number
	}
}

export interface AttendanceHeatmapResponse {
	axis: {
		x: string[]
		y: number[]
	}
	cells: Array<{
		x: string
		y: number
		present: number
		expected: number
	}>
}

export interface AttendanceRiskResponse {
	buckets: {
		critical: number
		warning: number
		ok: number
	}
	top_critical: Array<{
		student: string
		attendance_rate: number
		absent_count?: number
		late_count?: number
	}>
}

export interface AttendanceCodeUsageResponse {
	codes: Array<{
		attendance_code: string
		count: number
		count_as_present: 0 | 1
	}>
}

export interface AttendanceMyGroupsResponse {
	groups: Array<{
		student_group: string
		expected: number
		present: number
		absent: number
	}>
}

/* -------------------------------------------
 * Discriminated response union
 * ----------------------------------------- */

export type AttendanceResponse =
	| AttendanceOverviewResponse
	| AttendanceHeatmapResponse
	| AttendanceRiskResponse
	| AttendanceCodeUsageResponse
	| AttendanceMyGroupsResponse
```

---

# B. Resource Wrapper (A+ transport rule compliant)

**Only** `frappe.ts` may touch transport.

```ts
// ui-spa/src/resources/attendance.ts

import { api } from '@/lib/frappe'
import type {
	AttendanceRequest,
	AttendanceResponse,
} from '@/types/contracts/attendance'

export function fetchAttendance(
	payload: AttendanceRequest,
): Promise<AttendanceResponse> {
	return api<AttendanceResponse>('ifitwala_ed.students.api.attendance.get', payload)
}
```

Notes:

* ✅ flat payload
* ✅ no `{ payload }` wrapper
* ✅ no normalization
* ✅ backend owns shape

---

# C. Component usage pattern (example)

```ts
import { fetchAttendance } from '@/resources/attendance'

const data = await fetchAttendance({
	mode: 'overview',
	academic_year: currentAY,
})
```

Vue components **never** branch on role for scope.
They only choose `mode`.

---

# D. A+ Invariants (locked)

These must be enforced in review:

* ❌ no additional attendance endpoints
* ❌ no partial TS interfaces per component
* ❌ no `any`, `unknown`, or optional guessing
* ❌ no client-side role or school expansion
* ✅ one backend file
* ✅ one TS contract file
* ✅ discriminated unions everywhere

---

## Final confirmation

You now have:

* **1 backend file** (`api/attendance.py`)
* **1 TS contract** (`attendance.ts`)
* **1 resource wrapper**
* Zero duplication
* A+ transport boundary respected
