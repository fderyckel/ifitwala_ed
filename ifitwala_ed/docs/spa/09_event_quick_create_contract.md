# Event Quick Create Contract (v1)

Status: Active

This document is the canonical contract for the Staff Home quick-action overlay that creates Meetings and School Events.

Authority order:

1. `ifitwala_ed/docs/spa/01_spa_architecture_and_rules.md`
2. `ifitwala_ed/docs/spa/03_overlay_and_workflow.md`
3. `ifitwala_ed/docs/setup/team_contract.md`
4. This document

If implementation changes this workflow, update this document in the same change.

## 1. Surface and Entry-Point Modes

Status: Implemented core behavior, partial entry-point coverage

Code refs:
- `ifitwala_ed/ui-spa/src/overlays/calendar/EventQuickCreateOverlay.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/RoomUtilization.vue`
- `ifitwala_ed/ui-spa/src/overlays/OverlayHost.vue`
- `ifitwala_ed/ui-spa/src/composables/useOverlayStack.ts`

Test refs:
- `None`

Rules:

1. The canonical overlay type is `event-quick-create`.
2. The overlay supports `eventType='meeting' | 'school_event'` and `lockEventType` so entry points can preselect or lock the workflow.
3. The meeting workflow also supports explicit `meetingMode='ad_hoc' | 'team'`.
4. `meetingMode='ad_hoc'` is the attendee-first workflow used by Staff Home.
5. `meetingMode='team'` is the team-owned workflow contract where team attendees are hydrated from the server and locked by context inside the overlay.
6. Staff Home and Room Utilization both open the overlay in `meetingMode='ad_hoc'`; Room Utilization should prefill the currently selected school when one is in scope.
7. Entry-point copy remains permission-sensitive: use `Schedule meeting` when the user can create meetings but not school events; otherwise use `Create event`.
8. No SPA team-owned entry point is wired to open `meetingMode='team'` yet, so the entry-point matrix is still partial even though the mode contract is implemented.

## 2. API and Payload Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/calendar.py`
- `ifitwala_ed/api/calendar_quick_create.py`
- `ifitwala_ed/ui-spa/src/lib/services/calendar/eventQuickCreateService.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/get_event_quick_create_options.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/create_meeting_quick.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/create_school_event_quick.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/search_meeting_attendees.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/get_meeting_team_attendees.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/suggest_meeting_slots.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/suggest_meeting_rooms.ts`

Test refs:
- `ifitwala_ed/api/test_calendar.py`

Rules:

1. The SPA must use named POST endpoints only:
   - `ifitwala_ed.api.calendar.get_event_quick_create_options`
   - `ifitwala_ed.api.calendar.search_meeting_attendees`
   - `ifitwala_ed.api.calendar.get_meeting_team_attendees`
   - `ifitwala_ed.api.calendar.suggest_meeting_slots`
   - `ifitwala_ed.api.calendar.suggest_meeting_rooms`
   - `ifitwala_ed.api.calendar.create_meeting_quick`
   - `ifitwala_ed.api.calendar.create_school_event_quick`
2. SPA POST payloads are sent as the JSON body directly, not wrapped inside a nested `payload` object.
3. `get_event_quick_create_options()` is the canonical source for meeting categories, school-event categories, audience types, selectable schools, selectable teams, selectable student groups, school-keyed selectable locations, school-keyed selectable room types, attendee kinds, and default scheduling times.
4. `search_meeting_attendees(...)` returns a mixed attendee list with `kind`, `label`, `meta`, and `availability_mode`.
5. `suggest_meeting_slots(...)` returns ranked exact matches plus fallback slots, server-owned availability notes, and when room-aware ranking is requested, suggested-room metadata on each slot; the request may also constrain ranking by `location_type`.
6. `suggest_meeting_rooms(...)` returns ranked room suggestions plus room-scope notes and may constrain ranking by `location_type`.
7. `create_meeting_quick(...)` accepts explicit attendees, optional team context, optional host school, and an idempotency key via `client_request_id`.
8. `create_meeting_quick(...)` and `create_school_event_quick(...)` must validate manual location choices through the same shared-location resolver used by room suggestions and Room Utilization.
9. `create_school_event_quick(...)` remains the canonical quick-create path for school events and continues to use the same overlay shell.

## 3. Meeting Workflow Contract

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/overlays/calendar/EventQuickCreateOverlay.vue`
- `ifitwala_ed/api/calendar_quick_create.py`
- `ifitwala_ed/setup/doctype/meeting/meeting.json`
- `ifitwala_ed/setup/doctype/meeting/meeting.py`
- `ifitwala_ed/setup/doctype/meeting_participant/meeting_participant.json`

Test refs:
- `ifitwala_ed/api/test_calendar.py`

Rules:

1. Ad-hoc meetings are attendee-first: employees, students, and guardians can all be invited directly from the overlay.
2. The organizer is always added server-side, even if the attendee list does not include the organizer explicitly.
3. Ad-hoc meetings require a host school so the meeting remains anchored to school and academic-year metadata even when no team is present.
4. Team bulk-add in ad-hoc mode only affects the attendee list; the final create payload leaves `team` empty so the meeting stays `Participants Only`.
5. Team mode submits the `team` field and defaults the meeting visibility scope to `Team & Participants`.
6. Participant child rows are built server-side from `Meeting Participant` with canonical `participant`, `participant_name`, and optional `employee`.
7. The overlay must not claim guardian free/busy certainty beyond school-side records; guardian availability is advisory and explicitly labeled as such.

## 4. Availability, Rooming, and Concurrency Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/calendar_quick_create.py`
- `ifitwala_ed/api/calendar_core.py`
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/setup/doctype/meeting/meeting.py`
- `ifitwala_ed/api/student_calendar.py`
- `ifitwala_ed/ui-spa/src/components/calendar/StudentCalendar.vue`
- `ifitwala_ed/docs/scheduling/employee_booking_notes.md`
- `ifitwala_ed/docs/scheduling/room_booking_notes.md`
- `ifitwala_ed/docs/concurrency_01_proposal.md`
- `ifitwala_ed/docs/concurrency_02_proposal.md`
- `ifitwala_ed/docs/high_concurrency_03.md`

Test refs:
- `ifitwala_ed/api/test_calendar.py`

Rules:

1. Meeting-attendee search, slot suggestion, and room suggestion are all server-owned workflows; the SPA must not fan out per attendee or per room.
2. Quick-create scope is cached per user in Redis-backed cache so repeated attendee and scheduling requests do not rebuild visibility scope every time.
3. Slot and room suggestion payloads are short-lived cached responses keyed by user plus filter scope.
4. Slot suggestion requests are bounded to 20 attendees, 14 days, and 15-minute increments.
5. Employee availability is authoritative from `Employee Booking`.
6. Student availability is derived from school timetable room slots plus known meetings and school events.
7. `create_meeting_quick(...)` must reject a requested slot when any invited student is already busy under that same student-availability model, even if the user skips slot suggestions.
8. Guardian availability is limited to known school-side meetings and school events and must be surfaced with an explicit note.
9. When `create_meeting_quick(...)` rejects a slot because of student availability, the overlay must stay open, preserve the drafted meeting state, show the server-owned conflict reason inline, and offer `Find common times` as the immediate recovery action.
10. For in-person and hybrid meeting quick create, exact common-time matches are room-aware: a slot only remains in the exact-match list when the selected host-school scope has at least one free room for that time.
11. Room availability is authoritative from `Location Booking` via `find_room_conflicts(...)`.
12. Room ranking is filtered by host-school descendant scope, ancestor-shared locations, optional `location_type`, and attendee-capacity threshold, then sorted to prefer the smallest adequate room before larger rooms.
13. Manual location pickers in the overlay must switch with the selected host school and must not present sibling-school rooms outside the canonical shared-location scope.
14. When room-aware ranking is requested, each slot payload may include `suggested_room` and `available_room_count` so the overlay can prefill the best room without extra per-slot requests.
15. Successful meeting writes must invalidate affected student calendar views through mutation-owned cache invalidation plus the user-scoped realtime event, so an already-open student calendar does not wait for TTL expiry.
16. None of these quick-create workflows enqueue background jobs today because the request path is bounded and aggregated; if the search bounds expand materially, the concurrency docs above must be revisited before widening them.

## 5. School Event Workflow Contract

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/overlays/calendar/EventQuickCreateOverlay.vue`
- `ifitwala_ed/api/calendar_quick_create.py`
- `ifitwala_ed/setup/doctype/school_event/school_event.json`

Test refs:
- `ifitwala_ed/api/test_calendar.py`

Rules:

1. School Event quick create remains a first-class tab inside the same overlay when the user has permission to create school events.
2. When the user can create meetings but cannot create school events, the Staff Home quick action and overlay copy must stop promising generic event creation.
3. Audience selection for school events continues to use the named server workflow and the canonical audience DocType contract.
4. The shared overlay shell must still close immediately on semantic success and rely on the calendar invalidate signal for refresh.

## 6. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/api/calendar.py`
- `ifitwala_ed/api/calendar_quick_create.py`
- `ifitwala_ed/setup/doctype/meeting/meeting.json`
- `ifitwala_ed/setup/doctype/meeting/meeting.py`
- `ifitwala_ed/setup/doctype/meeting_participant/meeting_participant.json`
- `ifitwala_ed/setup/doctype/school_event/school_event.json`
- `ifitwala_ed/ui-spa/src/overlays/calendar/EventQuickCreateOverlay.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`
- `ifitwala_ed/ui-spa/src/lib/services/calendar/eventQuickCreateService.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/get_event_quick_create_options.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/create_meeting_quick.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/search_meeting_attendees.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/get_meeting_team_attendees.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/suggest_meeting_slots.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/calendar/suggest_meeting_rooms.ts`

Test refs:
- `ifitwala_ed/api/test_calendar.py`
- Frontend contract coverage: `None`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | `Meeting`, `Meeting Participant`, `School Event` | `setup/doctype/meeting/meeting.json`, `setup/doctype/meeting_participant/meeting_participant.json`, `setup/doctype/school_event/school_event.json` | `ifitwala_ed/api/test_calendar.py` |
| Controller / workflow logic | `calendar_quick_create.py` plus `Meeting` controller invariants | `ifitwala_ed/api/calendar_quick_create.py`, `setup/doctype/meeting/meeting.py` | `ifitwala_ed/api/test_calendar.py` |
| API endpoints | `calendar.py` facade over quick-create methods | `ifitwala_ed/api/calendar.py`, `ifitwala_ed/api/calendar_quick_create.py` | `ifitwala_ed/api/test_calendar.py` |
| SPA/UI surfaces | Staff Home quick action plus `EventQuickCreateOverlay` | `ui-spa/src/pages/staff/StaffHome.vue`, `ui-spa/src/overlays/calendar/EventQuickCreateOverlay.vue` | `None` |
| Reports / dashboards / briefings | Staff Home quick-action copy and overlay entry point | `ui-spa/src/pages/staff/StaffHome.vue` | `None` |
| Scheduler / background jobs | None | None | None |
| Tests | Calendar facade and quick-create regression coverage | `ifitwala_ed/api/test_calendar.py` | `ifitwala_ed/api/test_calendar.py` |

## 7. Technical Notes (IT)

Status: Implemented

Code refs:
- `ifitwala_ed/api/calendar_quick_create.py`
- `ifitwala_ed/ui-spa/src/overlays/calendar/EventQuickCreateOverlay.vue`
- `ifitwala_ed/ui-spa/src/lib/services/calendar/eventQuickCreateService.ts`

Test refs:
- `ifitwala_ed/api/test_calendar.py`

- Quick-create cache TTLs:
  - options: `300s`
  - scope: `300s`
  - attendee search: `60s`
  - slot suggestions: `60s`
  - room suggestions: `60s`
- Save-time student conflicts:
  - the overlay stays open
  - drafted attendee and timing state remains intact
  - the inline error can trigger `Find common times` immediately
- Room-aware slot ranking:
  - exact matches in in-person/hybrid mode require at least one free room in the selected host-school scope
  - slot payloads can carry `suggested_room` and `available_room_count`
- Idempotency:
  - `create_meeting_quick(...)` and `create_school_event_quick(...)` use Redis-backed idempotency keys with `QUICK_CREATE_IDEMPOTENCY_TTL_SECONDS = 900`.
- Overlay close contract:
  - the overlay closes immediately after semantic success and relies on `SIGNAL_CALENDAR_INVALIDATE` from the calendar UI service for same-session calendar refresh.
  - blocked saves keep the overlay open and surface inline recovery instead of closing or clearing the form.
- Student calendar refresh contract:
  - meeting writes invalidate student-feed cache in the mutation path
  - affected student users receive `student_calendar:invalidate` after commit so open student portals refresh without manual action
- Current entry-point reality:
  - Staff Home is wired.
  - explicit team-mode SPA entry points are not wired yet.
