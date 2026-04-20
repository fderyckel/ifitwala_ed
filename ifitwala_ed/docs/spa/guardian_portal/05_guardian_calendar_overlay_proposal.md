# Guardian Calendar Overlay Proposal

Status: Proposal
Audience: Humans, coding agents
Scope: `/hub/guardian` family-facing school-calendar quick link and overlay
Last updated: 2026-04-20

This note is exploratory and non-authoritative.

It does not change the canonical guardian-portal runtime contract until implementation is approved and the active guardian docs are updated in the same change.

## 1. Objective

Status: Proposed

Current code refs:
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCommunicationCenter.vue`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/calendar_details.py`
- `ifitwala_ed/ui-spa/src/components/calendar/SchoolEventModal.vue`
- `ifitwala_ed/ui-spa/src/components/calendar/StudentCalendar.vue`
- `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`
- `ifitwala_ed/docs/spa/guardian_portal/02_information_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
- `ifitwala_ed/docs/enrollment/02_school_calendar_architecture.md`
- `ifitwala_ed/docs/scheduling/04_calendar_aggregation_architecture.md`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/api/test_portal_calendar.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCommunicationCenter.test.ts`

Proposal:

1. Add one new Guardian Home quick link: `School Calendar`.
2. The quick link opens a large overlay with a month view focused on:
   - school holidays and breaks
   - family-relevant school events already visible to guardians
3. The overlay keeps guardians in context instead of forcing navigation to a separate page.
4. The monthly view is family-first by default, with filters that only narrow already-authorized family scope.

Product reason:

- Guardians already see school events in `/guardian/communications`, but that surface is chronological and message-oriented.
- Families need a larger month-shaped planning view for holidays, conferences, presentations, and similar calendar-bound items.
- The overlay should answer one question quickly: `What days should this family plan around this month?`

## 2. Recommended UX Shape

Status: Proposed

Current code refs:
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/composables/useOverlayStack.ts`
- `ifitwala_ed/ui-spa/src/overlays/OverlayHost.vue`
- `ifitwala_ed/ui-spa/src/styles/components.css`
- `ifitwala_ed/ui-spa/src/components/calendar/SchoolEventModal.vue`

Test refs:
- None yet

Proposal:

1. Entry point:
   - add a `School Calendar` quick-link tile on `GuardianHome.vue`
   - keep v1 to this one launcher instead of adding a new routed page and a new rail item at the same time
2. Overlay size:
   - use the shared overlay stack
   - add a new large panel variant instead of reusing the current compact event modal width
   - target a desktop width around `72rem` to `80rem`, with near-full-height body scrolling
3. Overlay layout:
   - top bar with month title, previous/next month controls, and refresh
   - filter row with child selector, school selector, and include/exclude toggles
   - primary body with one month grid
   - secondary day-agenda/legend panel for the selected date or hovered day
4. Mobile behavior:
   - same overlay entry point
   - filters stack vertically
   - month grid remains primary
   - selected-day agenda drops below the calendar instead of staying side-by-side
5. Item interaction:
   - clicking a school event opens the existing school-event detail modal or the same detail content inline
   - clicking a holiday opens only inline day details inside the overlay; do not chain guardians into modal-on-modal for holidays

Why this shape is recommended:

- a large overlay matches the user request and preserves guardian-home context
- a month grid is better than the communication feed for long-range planning
- a side agenda keeps day cells readable when a family has multiple children or schools

## 3. Filter Model

Status: Proposed

Current code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/docs/spa/guardian_portal/02_information_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`

Test refs:
- `ifitwala_ed/api/test_guardian_phase2.py`

Proposal:

1. Child filter:
   - default: `All linked children`
   - options: each linked child already returned by guardian scope resolution
   - rule: this filter narrows the authorized payload only; it never widens visibility
2. School filter:
   - default: `All family schools`
   - options: distinct schools from the guardian's linked children only
   - rule: when one child is selected and that child has one school, the school filter should default to that school and may be visually locked
3. Content toggles:
   - `Show holidays`
   - `Show school events`
   - both default to on
4. Optional v1 legend chips:
   - holiday count
   - school-event count
   - selected-school count when multiple family schools are in scope

Recommended explicit non-goal for v1:

- do not promise event-subtype filters like `conference`, `presentation`, or `parents evening` unless the backend has an explicit normalized family-facing taxonomy for them

Reason:

- the verified `School Event` schema includes `event_category`
- the verified schema does not include a real `event_type` field
- the current guardian feed already carries `event_category`, but that is not a reliable enough family-facing taxonomy for the richer filter set requested

## 4. Data Sources And Visibility Rules

Status: Proposed

Current code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/api/calendar_details.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.json`
- `ifitwala_ed/school_settings/doctype/school_calendar_holidays/school_calendar_holidays.json`
- `ifitwala_ed/school_settings/doctype/school_event/school_event.json`
- `ifitwala_ed/school_settings/doctype/school_event_audience/school_event_audience.json`
- `ifitwala_ed/school_settings/doctype/school_event_participant/school_event_participant.json`
- `ifitwala_ed/docs/enrollment/02_school_calendar_architecture.md`

Test refs:
- `ifitwala_ed/api/test_portal_calendar.py`
- `ifitwala_ed/api/test_guardian_phase2.py`

Proposal:

1. Holidays:
   - source of truth is `School Calendar Holidays`
   - calendars must resolve through `resolve_school_calendars_for_window(...)`
   - nearest-ancestor school-calendar resolution must remain intact
2. School events:
   - source of truth is `School Event`
   - guardian visibility should reuse the existing server-owned audience rules already used by `/guardian/communications`
   - only family-relevant events should appear, meaning events that already reach guardians through:
     - `All Guardians`
     - `All Students, Guardians, and Employees`
     - student audiences with `include_guardians = 1`
     - explicit participant rows
3. Child matching:
   - the server returns matched child labels for each visible event
   - the SPA must not infer child relevance client-side
4. School matching:
   - when multiple children are linked to different schools, the overlay may merge all in-scope family schools into one month view
   - each returned item must carry its school label so the UI can show it plainly

Recommended v1 boundary:

- only merge `holiday` and `school_event`
- do not extend v1 into student classes, meetings, attendance, or assignment dates

Reason:

- this keeps the surface aligned with the stated planning need
- it avoids turning the guardian overlay into a second student timetable

## 5. Proposed API Contract

Status: Proposed

Current code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCommunication/guardianCommunicationService.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_communication_center.ts`

Test refs:
- None yet

Recommended named endpoint:

- `ifitwala_ed.api.guardian_calendar.get_guardian_calendar_overlay`

Recommended request shape:

```python
month_start: str | None = None   # first day of visible month, YYYY-MM-DD
student: str | None = None
school: str | None = None
include_holidays: int = 1
include_school_events: int = 1
```

Recommended response shape:

```ts
type Response = {
  meta: {
    generated_at: string
    timezone: string
    month_start: string
    month_end: string
    filters: {
      student: string | null
      school: string | null
      include_holidays: boolean
      include_school_events: boolean
    }
  }
  family: {
    children: ChildRef[]
  }
  filter_options: {
    students: ChildRef[]
    schools: Array<{ school: string; label: string }>
  }
  summary: {
    holiday_count: number
    school_event_count: number
  }
  items: Array<{
    item_id: string
    kind: 'holiday' | 'school_event'
    title: string
    start: string
    end: string
    all_day: boolean
    color?: string | null
    school?: string | null
    matched_children: ChildRef[]
    description?: string | null
    event_category?: string | null
    open_target?: { type: 'school-event'; name: string } | null
  }>
}
```

Why one bootstrap endpoint is recommended:

- it matches the repository high-concurrency rule for bounded page/overlay initialization
- it keeps the overlay fast enough for month switches
- it avoids a waterfall of:
  - scope call
  - school list call
  - holiday call
  - event call
  - detail prefetch call

## 6. SPA Implementation Slice

Status: Proposed

Likely implementation touchpoints:
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/composables/useOverlayStack.ts`
- `ifitwala_ed/ui-spa/src/overlays/OverlayHost.vue`
- `ifitwala_ed/ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCalendar/guardianCalendarService.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_calendar_overlay.ts`
- `ifitwala_ed/ui-spa/src/styles/components.css`
- `ifitwala_ed/ui-spa/src/components/calendar/SchoolEventModal.vue`

Test refs:
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCalendarOverlay.test.ts`

Recommended implementation notes:

1. Add a dedicated overlay type such as `guardian-calendar`.
2. Keep the overlay read-only in v1.
3. Reuse the existing FullCalendar assets and month-grid styling direction where practical.
4. Reuse the existing school-event detail modal for event drill-down.
5. Add a new large overlay panel modifier instead of stretching the compact event modal globally.

Important contract rule:

- the overlay must not perform client-side audience or school-calendar resolution
- the overlay only renders server-shaped items and emits close events per the shared overlay contract

## 7. Backend Implementation Slice

Status: Proposed

Likely implementation touchpoints:
- `ifitwala_ed/api/guardian_calendar.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/api/calendar.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`

Test refs:
- `ifitwala_ed/api/test_guardian_calendar.py`

Recommended backend rules:

1. Resolve guardian scope once per request using the existing guardian-scope helper.
2. Validate `student` and `school` filters against that resolved scope before any aggregation.
3. Resolve holiday rows through the canonical school-calendar lineage resolver.
4. Reuse existing guardian school-event audience logic instead of duplicating a second ruleset.
5. Return one merged, already-sorted item list for the requested month window.

Recommended design choice:

- do not introduce Redis caching in v1 unless invalidation ownership is specified for:
  - `School Event` writes
  - `School Calendar` writes
  - `School Calendar Holidays` changes

Reason:

- the request is already bounded to one family and one month
- cache correctness matters more than speculative cache hits on this permission-sensitive surface

## 8. Risks And Boundaries

Status: Proposed

Current code refs:
- `ifitwala_ed/docs/high_concurrency_contract.md`
- `ifitwala_ed/docs/spa/03_overlay_and_workflow.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`

Test refs:
- None yet

Primary risks:

1. UX drift:
   - if the overlay becomes a second communication center or a second student timetable, it loses the planning focus
2. permission drift:
   - if child or school filters widen scope instead of narrowing it, sibling or cross-family leakage becomes possible
3. data-model drift:
   - if v1 promises subtype filters not backed by real schema, the UI will invent semantics
4. concurrency drift:
   - if the overlay needs multiple follow-up requests per month switch, it violates the bounded bootstrap rule

Recommended guardrails:

1. v1 is read-only
2. v1 is month-view only
3. v1 merges only holidays and guardian-visible school events
4. v1 does not add schema fields

## 9. Approval Gates

Status: Proposed

This proposal is implementation-ready only for the no-schema-change path below.

### 9.1 Recommended path

Implement:

1. Guardian Home quick link
2. Large monthly overlay
3. child filter
4. school filter
5. show/hide holidays
6. show/hide school events
7. event click-through to the existing school-event detail modal

This path stays within verified current schema and current guardian visibility rules.

### 9.2 Separate approval required

Do not implement these without explicit follow-up approval:

1. a new guardian calendar route instead of an overlay
2. new `School Event` schema fields for family-facing subtypes or tags
3. cross-surface rail navigation changes
4. shared Redis caching without documented invalidators
5. class schedules, meetings, or assignments inside the same overlay

## 10. Test Plan If Approved

Status: Proposed

Recommended backend coverage:

1. guardian school filter rejects out-of-scope schools
2. child filter rejects out-of-scope students
3. nearest-ancestor school calendars still resolve holiday rows
4. events visible in `/guardian/communications` remain the only event rows eligible for the overlay
5. mixed-school family payloads return correct matched children and school labels
6. toggles exclude `holiday` and `school_event` rows server-side, not by hiding rows after fetch

Recommended SPA coverage:

1. Guardian Home renders the new quick link
2. clicking the quick link opens the overlay through the overlay stack
3. month navigation re-fetches the single bootstrap payload
4. child and school filters preserve only in-scope options
5. event clicks open school-event detail
6. the large overlay uses the new panel size modifier without changing other compact event modals
