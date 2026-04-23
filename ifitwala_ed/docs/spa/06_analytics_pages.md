# Analytics Pages in Ifitwala_Ed — Canonical Rules & Lessons Learned

> **Status:** Canonical (derived from production bugs)
> **Audience:** Humans + AI agents
> **Scope:** Vue 3 SPA analytics pages (staff-facing)

This document consolidates **hard-earned lessons** from building analytics pages in the Ifitwala_Ed SPA.
These are **not preferences** — they are **paid-for invariants**.

If an analytics page violates these rules, it is considered **defective** even if it “appears to work”.

---

## 1. Scope & File Location (Non-Negotiable)

### 1.1 Page location (locked)

All **analytics pages** MUST live under:

```
ui-spa/src/pages/staff/analytics/
```

Examples:

* `AttendanceAnalytics.vue`
* `StudentLogAnalytics.vue`
* `EnrollmentTrends.vue`

Rules:

* Pages = orchestration only
* Pages own refresh logic
* Pages subscribe to `uiSignals` (if needed)

❌ Analytics pages must not live in:

* `components/`
* `overlays/`
* random feature folders

---

### 1.2 Reusable analytics components

Reusable UI pieces used across analytics pages MUST live under:

```
ui-spa/src/components/analytics/
```

Examples:

* `FiltersBar.vue` (shared filter layout, see §2.1)
* `MetricCard.vue`
* `AnalyticsTable.vue`
* `EmptyAnalyticsState.vue`

Rules:

* Components render only
* Components contain **no API calls**
* Components contain **no business logic**
* Components must be permission-agnostic

Note:

* `FiltersBar.vue` is a shared layout component that lives under `components/filters/`.

### 1.3 Expanded chart view is shared

When an analytics card supports a zoom/expanded view:

* it MUST reuse the shared analytics expand overlay via `OverlayHost`
* it MUST NOT introduce a page-specific modal/overlay implementation
* chart-card click may open the expanded view, but data-point click must preserve the primary drill-down action
* clicking the backdrop or any empty overlay space outside the expanded panel MUST close the expanded view

This avoids overlay drift and keeps analytics interactions consistent across pages.

---

## 2. Filter Architecture (Critical)

### 2.1 FiltersBar is mandatory

All staff analytics pages MUST use the shared:

```
components/filters/FiltersBar.vue
```

Why this is locked:

* consistent UX across analytics
* predictable filter semantics
* fewer edge cases
* easier future extension (saved views, presets, roles)

Ad-hoc filter UIs are forbidden.

---

### 2.2 Filters are computation inputs, not UI state

Filters are **inputs to server computation**.

If a filter changes:

* the server must receive it
* the server must recompute
* the page must refetch

Anything else is lying to the user.

---

### 2.3 Single source of truth for filters

Each analytics page MUST have exactly **one** filter object:

```ts
const filters = reactive({
  organization,
  school,
  academic_year,
  program,
})
```

Rules:

* no duplicated refs
* no shadow computed filters
* no derived “almost the same” objects

---

## 3. Transport & API Rules (Hard-Won)

### 3.1 Analytics endpoints are POST only

All analytics endpoints are **POST**.

Reasons:

* complex parameter sets
* pagination
* aggregation
* long-term evolution

GET-style analytics is forbidden.

---

### 3.2 POST + filters ⇒ `resource.submit(payload)` (critical invariant)

This was the **single most expensive bug class** we hit.

#### ❌ Forbidden (silent failure)

```ts
createListResource({
  method: 'POST',
  params: filters, // ❌ GET thinking
})
```

Symptoms:

* filters look reactive
* watchers fire
* page does not change
* server never sees new filters

---

#### ✅ Required pattern (locked)

```ts
const resource = createListResource({
  url,
  method: 'POST',
  auto: false,
})

resource.submit({
  ...filters,
  start,
  page_length,
})
```

### 3.3 SQL helper fragments in raw queries must be interpolated deliberately

If a backend analytics query embeds an SQL helper fragment such as:

```python
policy_applies_to_filter_sql(...)
```

the outer SQL string MUST interpolate that helper before execution.

Required patterns:

* `f""" ... {policy_applies_to_filter_sql(...)} ... """`
* one explicit pre-built fragment variable inserted into the final SQL string

Forbidden pattern:

```python
frappe.db.sql(
    """
    ...
    AND {policy_applies_to_filter_sql(policy_alias="ip", audience_placeholder="%(applies_to)s")}
    ...
    """,
    params,
)
```

Why this is locked:

* the helper call remains literal text instead of SQL
* MySQL then receives broken identifiers such as `policy_alias`
* permitted users see a server error on a valid page
* the bug often escapes review because the query looks visually correct

Required follow-up:

* add a regression test that executes the real endpoint path under an allowed role
* do not rely on import-only or helper-only tests for dynamic SQL assembly

**Invariant**

> If filters exist → POST + `submit(payload)`

This rule exists because we already paid the cost of violating it.

---

### 3.3 Pagination is part of filtering

Pagination is **not UI-only state**.

Rules:

* `start` and `page_length` are part of the POST payload
* changing filters resets pagination
* changing pagination triggers recompute

---

### 3.4 Backend must never read `frappe.form_dict`

Analytics endpoints MUST:

* declare explicit arguments
* never inspect `frappe.form_dict`
* never validate raw request keys

```py
@frappe.whitelist()
def get_analytics(
    organization,
    school,
    academic_year,
    start=0,
    page_length=20
):
    ...
```

Reading `form_dict` caused:

* polluted payloads
* false validation errors
* environment-dependent bugs

This is now banned.

---

## 4. Permissions & Hierarchy (Critical)

### 4.1 Permissions are enforced server-side

Analytics pages must assume:

* the client is untrusted
* visibility rules are enforced **before aggregation**

Never:

* “hide” rows client-side
* filter results after aggregation
* rely on UI role checks

---

### 4.2 Organization & School hierarchy (NestedSet)

Rules:

* Schools belong to Organizations (NestedSet)
* Selecting a parent school includes **all descendants**
* Sibling isolation is mandatory

Analytics queries MUST:

1. Resolve user’s base organization
2. Resolve allowed schools via NestedSet
3. Apply hierarchy constraints **in SQL WHERE**
4. Aggregate only permitted rows

Filtering after aggregation is a data leak.

---

### 4.3 Instructor-scoped analytics

For instructors:

* only students they teach
* only logs they are permitted to see
* only schedules they are assigned to

Aggregation MUST respect these constraints **before grouping**.

---

### 4.4 Capability split: Admissions vs Demographics

StaffHome capabilities MUST keep these concerns separate:

* `analytics_admissions` → Admissions Cockpit, Inquiry Analytics, admissions workflows.
* `analytics_demographics` → Student Demographic Analytics only.

Why this is locked:

* prevents unrelated link exposure
* avoids role-based UI dead-ends
* keeps route discoverability aligned with endpoint permissions

Do not reuse admissions capability as a proxy for demographics visibility.

---

## 5. Visual & UX Rules

### 5.1 No optimistic analytics

Analytics pages must never:

* optimistically update charts
* animate to imply recompute
* reuse stale data

If the server did not respond → nothing changed.

---

### 5.2 Loading states must reflect real recompute

* loading starts on `.submit(payload)`
* loading ends on response
* debounce filter typing if needed
* no fake spinners

Trust > cleverness.

---

### 5.3 Empty states must be honest

Empty analytics means one of:

* no data for filter combo
* no permission
* time window mismatch

Never:

* reuse previous chart
* show partial results
* silently fallback

---

### 5.4 Snapshot export status

Snapshot export is temporarily disabled across staff analytics dashboards as of 2026-03-09.

Rules:

* Do not render PNG or PDF export actions on analytics pages until a replacement workflow is approved.
* Do not keep orphaned export-specific client composables, shared buttons, or server endpoints when export is disabled.
* If export returns later, the behavior must be re-documented here before code ships.

---

### 5.5 Permission states must be evidence-based

Analytics pages must only show an access-restricted state when the failure is actually a permission failure.

Required behavior:

* permission-like server responses may render the restricted state
* generic 500s must stay generic errors
* transport failures must stay transport failures

Forbidden behavior:

* mapping every failed bootstrap request to "You do not have permission"

Why this is locked:

* it hides real backend defects behind a false permission story
* it sends authorized users to role debugging when the real issue is server-side
* it increases time-to-fix because logs and UI disagree

If the page cannot prove the failure is permission-related, it must show an honest error state instead.

---

### 5.6 Analytics page header contract

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/styles/components.css`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/AcademicLoad.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/AttendanceAnalytics.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/AttendanceLedger.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/EnrollmentAnalytics.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/InquiryAnalytics.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/RoomUtilization.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentDemographicAnalytics.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentLogAnalytics.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentOverview.vue`

Test refs:
- None

Rules:

1. The first content block inside `analytics-shell` is one route-level page header, before `FiltersBar`, KPI rows, or data cards.
2. The header intro block stays left-aligned on every breakpoint. Do not center or right-anchor the title to compensate for pills, buttons, or selector width.
3. The route title uses `<h1 class="type-h1 text-canopy">...</h1>`.
4. The optional subtitle / top explanation uses `<p class="type-meta text-slate-token/80">...</p>`.
5. `type-h2`, `type-caption`, and raw `text-*` sizing classes are not allowed for the route-level analytics page title or subtitle.
6. Date-range pills, refresh actions, export replacements, and other page-scoped controls belong in a trailing actions cluster only.
7. The presence or width of actions must never visually re-anchor the intro block away from the left edge of the shell rhythm.
8. If a page needs more than one short sentence of operational context, keep the subtitle concise and move secondary detail into badges, helper chips, or the first surface below the header.

## 6. Performance & Query Design

### 6.1 Prefer one indexed query

Analytics queries should:

* build WHERE clauses centrally
* filter first, aggregate second
* use indexed fields
* avoid N+1 loops

Client-side aggregation is forbidden beyond presentation.

---

## 7. Debugging Lessons (Scar Tissue)

### 7.1 “Filters don’t work” is almost always transport

Checklist:

1. POST vs GET mismatch
2. missing `.submit(payload)`
3. server args not declared
4. payload shape mismatch

Do **not**:

* tweak watchers first
* add computed hacks
* blame Vue reactivity

---

### 7.2 Network tab ≠ runtime truth

We learned:

* frappe-ui may unwrap responses
* network payloads can differ from JS runtime
* double-unwrapping causes silent failures

Transport normalization happens **once**, centrally.

---

### 7.3 Heatmap visibility is a correctness contract

If a heatmap carries real values but appears blank or “washed out”, that is a defect.

Rules:

* Always define an explicit `inRange.color` palette for heatmaps, even when `visualMap.show = false`.
* Always clamp a non-zero max bound (`max >= 1`) so sparse datasets do not collapse into near-invisible color output.
* Prefer showing non-zero cell labels for sparse cohort/category matrices so users can verify values at a glance.
* Keep click payloads (`sliceKey`) in the series data tuple when adding display labels.

---

### 7.4 Drill-down drawers must be actionable

A drawer that lists entities but offers no next action is a UX dead-end.

Rules:

* Student drill-down rows must link directly to canonical Desk forms (`/desk/student/<name>`).
* Links must open safely (`target="_blank"` + `rel="noopener noreferrer"`) for staff workflows.
* Apply route links only for supported entities; unsupported entities must remain readable text, not broken links.

---

### 7.5 Donut chart hover behavior must be stable

If donut charts flicker or jitter on hover, treat that as an interaction defect.

Rules:

* Disable pie hover expansion/scale and hover labels when they trigger repeated repaint jitter.
* Constrain tooltips to chart/container bounds (`confine`) to avoid hover thrash near edges.
* Keep drill-down click handling intact after hover stabilization changes.

---

## 8. Anti-Patterns (Treat as Defects)

❌ Analytics page outside `pages/staff/analytics/`
❌ Ad-hoc filter UI (no FiltersBar)
❌ GET-style filters on POST endpoints
❌ `auto: true` on POST analytics resources
❌ Reading `frappe.form_dict`
❌ Client-side permission filtering
❌ Aggregating before permission checks
❌ Optimistic analytics updates
❌ Pagination excluded from payload
❌ Centered or right-anchored route-level analytics title blocks
❌ `type-h2`, `type-caption`, or raw `text-*` utilities on route-level analytics titles/subtitles
❌ Hidden heatmap visualMap with no explicit `inRange` palette
❌ Drill-down drawer rows that provide names but no direct action link
❌ Donut hover emphasis that causes visual jitter/flicker

Each of these already caused real bugs.

---

## 9. Summary Invariant (Memorable Version)

> **Analytics pages are contracts, not widgets.**
> Filters are computation inputs.
> POST is mandatory.
> `submit(payload)` is the only truth.
> Permissions and hierarchy are enforced before aggregation.
> If the server didn’t receive it — it didn’t happen.

---

## 10. Relationship to A+ SPA Architecture (Explicit Authority)

Analytics pages in Ifitwala_Ed are **not a special case**.
They are a **direct application** of the A+ SPA architecture and must obey it fully.

This document is **subordinate** to the following canonical SPA notes:

### 🔒 Authoritative A+ SPA Documents

1. **`01_spa_architecture_and_rules.md`**
   *Highest authority for all Vue SPA code*
   Defines:

   * ownership model (pages / services / overlays)

   * transport rules

   * POST + `submit(payload)` invariants

   * signal discipline

   * folder semantics

   * contract governance

   > If any rule in this analytics note conflicts with `01_spa_architecture_and_rules.md`,
   > **the SPA rules win**.

2. **`03_overlay_and_workflow.md`**
   *Canonical A+ lifecycle for workflows and overlays*
   Defines:

   * “Overlay owns closing, services own orchestration”
   * signal emission rules
   * refresh ownership
   * UX side-effect boundaries

   Analytics pages often **react** to workflows (Student Logs, Tasks, Attendance, Focus),
   therefore they must align with this contract.

---

## 10.1 How Analytics Pages Fit the A+ Model

Under A+, analytics pages are:

| Concern             | A+ Owner                | Analytics implication                                |
| ------------------- | ----------------------- | ---------------------------------------------------- |
| Data truth          | **Server**              | Analytics never infer or compute meaning client-side |
| Transport           | **resources/frappe.ts** | No GET params, no envelope handling                  |
| Fetch orchestration | **Page**                | Analytics pages own when/how to refetch              |
| Filters             | **Page (input state)**  | Filters are computation inputs, not UI cosmetics     |
| Invalidation        | **UI Services**         | Analytics refresh only via signals or local triggers |
| Permissions         | **Server**              | Analytics never filter permission client-side        |
| UX feedback         | **Page / Shell**        | Charts update only after real recompute              |

Analytics pages are therefore **pure refresh owners**:

* they subscribe (optionally) to signals
* they refetch deterministically
* they never participate in workflows directly

---

## 10.2 Analytics-Specific Restatement of A+ Invariants

For avoidance of doubt, when working on analytics pages:

* **Pages own refresh**
  Analytics pages decide *when* to fetch or refetch data.

* **Services own orchestration**
  Analytics pages never call endpoints directly; they consume services or resources.

* **Overlays own workflows**
  Analytics pages do not submit, approve, or mutate state.

* **Signals are advisory**
  Analytics pages may listen to invalidation signals but must coalesce refreshes and protect the backend.

* **Transport is centralized**
  Analytics pages never unwrap `{ message }`, `{ data }`, or Axios envelopes.

If an analytics implementation violates any of the above, it is an **A+ violation**, not a stylistic issue.

---

## 10.3 Practical Rule for Agents

When an agent touches an analytics page under:

```
ui-spa/src/pages/staff/analytics/
```

It must **mentally load these documents first**, in this order:

1. `01_spa_architecture_and_rules.md` (parent authority)
2. `03_overlay_and_workflow.md` (workflow boundaries)
3. **this analytics note** (domain-specific constraints)

If something feels unclear:

* **stop**
* ask which document governs the behavior
* do not invent a hybrid rule

---

## 10.4 Why This Explicit Link Exists (Historical Context)

This explicit cross-reference exists because analytics bugs we encountered were **not analytics problems**:

* filters “not working” → transport contract violation
* stale charts → refresh ownership confusion
* missing data → permission filtering done too late
* frozen UI → misuse of POST resources

Each of those failures was already covered by A+ —
they just weren’t *named* in analytics language yet.

This section closes that gap.

---

## 10.5 Student Log Analytics Table Contract

`StudentLogAnalytics.vue` has two detail tables at the end of the page:

* `Recent Student Logs`
* `Selected Student Logs`

For these two tables, the contract is:

* one row per `Student Log`
* follow-up rows are **not** exploded into one-row-per-follow-up
* follow-up detail is rendered inside a dedicated `Follow-ups` cell as a compact stack/timeline
* the same row contract must be usable in the expanded analytics overlay

For each submitted `Student Log Follow Up` rendered inside that cell, the UI may show:

* doctype label (`Student Log Follow Up`)
* parent `Student Log.next_step`
* response-latency label derived from parent-log creation time to follow-up creation time
* responder name
* follow-up comment preview

Rules:

* only submitted follow-ups (`docstatus = 1`) count as analytics follow-up activity
* follow-up visibility must inherit from the visible parent `Student Log`; analytics must not create a separate child-level permission path
* multiple follow-ups must collapse gracefully inline and expand cleanly in the shared analytics overlay
* “no follow-up yet” states must be explicit; silent empty cells are a defect

---

## Final Anchor Statement (Keep This)

> **Analytics pages are first-class SPA citizens.**
> They obey A+.
> They do not invent rules.
> They do not relax invariants.
> They specialize them.

---
