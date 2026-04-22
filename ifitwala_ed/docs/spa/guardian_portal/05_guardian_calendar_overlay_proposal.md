# Guardian Calendar Overlay Contract (v0.1)

Status: Active
Audience: Humans, coding agents
Scope: `School Calendar` quick link and large monthly overlay launched from `/hub/guardian`
Last updated: 2026-04-22

This document is the canonical contract for the implemented guardian school-calendar overlay.

## 1. Objective

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`
- `ifitwala_ed/api/guardian_calendar.py`
- `ifitwala_ed/api/guardian_communications.py`

Test refs:
- `ifitwala_ed/api/test_guardian_calendar.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`
- `ifitwala_ed/ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts`

Rules:

1. Guardian Home includes one `School Calendar` quick link.
2. The quick link opens a large overlay instead of navigating the guardian into a second route.
3. The overlay answers one family-planning question: what holidays and family-relevant school events matter this month.
4. The surface is family-first by default and does not require guardians to open one child at a time before seeing the month.

## 2. UX Shape

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/composables/useOverlayStack.ts`
- `ifitwala_ed/ui-spa/src/overlays/OverlayHost.vue`
- `ifitwala_ed/ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`
- `ifitwala_ed/ui-spa/src/styles/components.css`

Test refs:
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`
- `ifitwala_ed/ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts`

Rules:

1. The overlay uses the shared SPA overlay stack and the `if-overlay__panel--xl` panel size.
2. The header exposes month navigation, refresh, and close actions.
3. The main body uses one large month grid with direct item clicks and an optional inline day-detail sheet below the grid when the guardian opens one date.
4. The calendar grid remains the primary object on all screen sizes; filters stack on smaller screens, but the overlay does not keep a permanent secondary agenda rail.
5. School-event pills may open the existing school-event overlay when an item exposes `open_target`; holiday and mixed-day review stays inside the inline day-detail sheet.

## 3. Filter Model

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_calendar.py`
- `ifitwala_ed/ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_calendar_overlay.ts`

Test refs:
- `ifitwala_ed/api/test_guardian_calendar.py`
- `ifitwala_ed/ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts`

Rules:

1. The child filter defaults to `All linked children` and may narrow to one linked child only.
2. The school filter defaults to `All family schools` and may narrow to one school derived from the guardian's linked children only.
3. When a selected child resolves to one school option, the school filter may be visually locked to that school.
4. `Show holidays` and `Show school events` both default to on and narrow the returned item set without changing guardian scope.
5. The overlay also shows summary chips for `holiday_count`, `school_event_count`, and the active month window.

## 4. Data Sources And Visibility

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_calendar.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.json`
- `ifitwala_ed/school_settings/doctype/school_calendar_holidays/school_calendar_holidays.json`
- `ifitwala_ed/school_settings/doctype/school_event/school_event.json`
- `ifitwala_ed/school_settings/doctype/school_event_audience/school_event_audience.json`
- `ifitwala_ed/school_settings/doctype/school_event_participant/school_event_participant.json`

Test refs:
- `ifitwala_ed/api/test_guardian_calendar.py`
- `ifitwala_ed/api/test_guardian_phase2.py`

Rules:

1. Holiday rows are sourced from `School Calendar Holidays` for the selected month window and exclude weekly off rows.
2. Holiday calendars resolve through `resolve_school_calendars_for_window(...)`; nearest-ancestor school-calendar semantics remain intact.
3. School-event rows reuse the guardian visibility rules already enforced by the communication center.
4. Parent-school events may match linked children through ancestor-school lineage, so one family event anchored on the parent school can still appear for linked children anchored on descendant schools in that branch.
5. Both holiday and school-event rows carry matched child labels resolved on the server.
6. The overlay may merge multiple in-scope family schools into one month view, but item rows keep plain school labels when available.

## 5. API Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_calendar.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_calendar_overlay.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCalendar/guardianCalendarService.ts`

Test refs:
- `ifitwala_ed/api/test_guardian_calendar.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCalendar/__tests__/guardianCalendarService.test.ts`

Rules:

1. The canonical endpoint is `ifitwala_ed.api.guardian_calendar.get_guardian_calendar_overlay`.
2. The request contract is `month_start?`, `student?`, `school?`, `include_holidays?`, and `include_school_events?`.
3. The response contract is the `Response` type in `ui-spa/src/types/contracts/guardian/get_guardian_calendar_overlay.ts`.
4. The payload is bounded to one month window and includes `meta`, `family`, `filter_options`, `summary`, and merged `items`.
5. The SPA service posts a flat JSON payload and returns the domain payload directly.

## 6. Explicit Non-Goals

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_calendar.py`
- `ifitwala_ed/ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_calendar_overlay.ts`

Test refs:
- `ifitwala_ed/api/test_guardian_calendar.py`
- `ifitwala_ed/ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts`

Rules:

1. The overlay is read-only in v1.
2. The overlay does not include class timetables, meetings, attendance, assignment dates, or guardian unread/read-state.
3. The overlay does not promise family-facing subtype filters such as `presentation`, `conference`, or `parents evening`.
4. `event_category` may be shown as a label for school-event items, but it is not documented as a normalized family-event taxonomy.

## 7. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_calendar.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/school_settings/doctype/school_calendar/*`
- `ifitwala_ed/school_settings/doctype/school_calendar_holidays/*`
- `ifitwala_ed/school_settings/doctype/school_event/*`
- `ifitwala_ed/school_settings/doctype/school_event_audience/*`
- `ifitwala_ed/school_settings/doctype/school_event_participant/*`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_calendar_overlay.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCalendar/guardianCalendarService.ts`

Test refs:
- `ifitwala_ed/api/test_guardian_calendar.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCalendar/__tests__/guardianCalendarService.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`
- `ifitwala_ed/ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | School calendars, school-calendar holidays, guardian-linked children, and guardian-visible school events | `school_settings/doctype/school_calendar/*`, `school_settings/doctype/school_calendar_holidays/*`, `school_settings/doctype/school_event/*`, `school_settings/doctype/school_event_audience/*`, `school_settings/doctype/school_event_participant/*`, `students/doctype/guardian/*`, `students/doctype/student_guardian/*`, `students/doctype/guardian_student/*` | `api/test_guardian_calendar.py`, `api/test_guardian_phase2.py` |
| Controller / workflow logic | Guardian month bootstrap, holiday resolution, school-event reuse, and scope validation for child and school filters | `api/guardian_calendar.py`, `api/guardian_communications.py`, `school_settings/school_settings_utils.py` | `api/test_guardian_calendar.py`, `api/test_guardian_phase2.py` |
| API endpoints | `get_guardian_calendar_overlay` | `api/guardian_calendar.py` | `api/test_guardian_calendar.py` |
| SPA / UI surfaces | Guardian Home quick link, overlay registration, large month view, direct calendar-item actions, and inline day-detail sheet | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/composables/useOverlayStack.ts`, `ui-spa/src/overlays/OverlayHost.vue`, `ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`, `ui-spa/src/styles/components.css` | `ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts` |
| Service / transport | Typed calendar overlay request and response transport | `ui-spa/src/types/contracts/guardian/get_guardian_calendar_overlay.ts`, `ui-spa/src/lib/services/guardianCalendar/guardianCalendarService.ts` | `ui-spa/src/lib/services/guardianCalendar/__tests__/guardianCalendarService.test.ts` |
