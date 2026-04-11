# Room Utilization and Location Calendar Contract

Status: Implemented

This document is the canonical contract for the staff-facing Room Utilization page, including free-room search, room utilization analytics, shared-location visibility, and the information-only Location Calendar.

Authority order:

1. `ifitwala_ed/docs/spa/01_spa_architecture_and_rules.md`
2. `ifitwala_ed/docs/spa/06_analytics_pages.md`
3. `ifitwala_ed/docs/nested_scope_contract.md`
4. `ifitwala_ed/docs/scheduling/room_booking_notes.md`
5. This document

If implementation changes this workflow, update this document in the same change.

## 1. Surface Contract

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/RoomUtilization.vue`
- `ifitwala_ed/api/room_utilization.py`

Test refs:
- `ifitwala_ed/api/test_room_utilization.py`

Rules:

1. The Room Utilization page remains the canonical SPA surface for free-room search plus room-level utilization analytics.
2. The page now also owns the information-only Location Calendar for a selected room or building.
3. The page must keep one selected school context and reuse it across free-room search, utilization analytics, and location-calendar scope.
4. Room-type filtering is a first-class workflow input, not a presentation-only label.
5. The SPA must not compute school hierarchy, shared-location inheritance, or location privacy rules client-side.
6. Page access is staff-wide, but the utilization analytics components on that page remain restricted to the analytics roles enforced by the server.
7. The Free Rooms Finder may open the canonical event quick-create overlay as a contextual next action and should prefill the current school when one is selected.

## 2. API and Read-Model Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/utilities/location_utils.py`

Test refs:
- `ifitwala_ed/api/test_room_utilization.py`

Rules:

1. `get_room_utilization_filter_meta()` is the canonical bootstrap for allowed schools, default school, and schedulable room-type options.
2. `get_free_rooms(...)`, `get_room_time_utilization(...)`, and `get_room_capacity_utilization(...)` must all resolve candidate rooms through `get_visible_location_rows_for_school(...)`.
3. `get_location_calendar(...)` is the only Room Utilization endpoint allowed to read Location Booking rows directly for timeline display.
4. Room availability and utilization remain authoritative from `Location Booking`; the page must not union Meeting, School Event, Employee Booking, or timetable rows client-side.
5. The SPA must use the named endpoints directly and must not introduce extra room-scope fetches to rebuild visibility rules locally.

## 3. Shared Location Visibility Contract

Status: Implemented

Code refs:
- `ifitwala_ed/stock/doctype/location/location.json`
- `ifitwala_ed/stock/doctype/location/location.py`
- `ifitwala_ed/utilities/location_utils.py`

Test refs:
- `ifitwala_ed/stock/doctype/location/test_location.py`
- `ifitwala_ed/api/test_room_utilization.py`

Rules:

1. The canonical shared-location switch is `Location.shared_with_descendant_schools`.
2. Shared visibility is location-instance-specific; it is not owned by `Location Type`.
3. When the shared flag is enabled on a group/container location, descendant spaces become visible to descendant schools through the same canonical resolver.
4. Shared visibility never widens sibling-school access by default.
5. The shared flag requires `Location.school`; a school-less shared location is invalid metadata.

## 4. Room-Type Filtering Contract

Status: Implemented

Code refs:
- `ifitwala_ed/utilities/location_utils.py`
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/stock/doctype/location_type/location_type.json`

Test refs:
- `ifitwala_ed/api/test_room_utilization.py`

Rules:

1. Schedulable-room filtering must be driven by `Location Type.is_schedulable` when a location type is present.
2. Capacity `0` is not the canonical way to hide non-bookable spaces from rooming workflows.
3. Untyped legacy locations remain visible only through the bounded fallback in `location_utils.py` until data is cleaned up.
4. The Room Utilization page must pass the selected room type back to the server for free-room search and utilization analytics.

## 5. Location Calendar Privacy Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/docs/scheduling/room_booking_notes.md`

Test refs:
- `ifitwala_ed/api/test_room_utilization.py`

Rules:

1. The Location Calendar is operational visibility only.
2. Event titles in the Location Calendar must be redacted to occupancy labels such as `Teaching`, `Meeting`, or `School Event`.
3. When a group/building is selected, the title may append the concrete room label for operational clarity.
4. The Location Calendar must not leak Meeting or School Event titles merely because a booking exists in the same location.
5. Group selections must expand through canonical location hierarchy helpers instead of duplicating descendant lookups in the page or endpoint.
6. Teaching rows may add operational context limited to `Student Group` plus `Course`; they must not expose instructor identity from the room calendar.

## 6. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/RoomUtilization.vue`
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/utilities/location_utils.py`
- `ifitwala_ed/stock/doctype/location/location.py`
- `ifitwala_ed/stock/doctype/location/location.json`
- `ifitwala_ed/stock/doctype/location_type/location_type.json`

Test refs:
- `ifitwala_ed/api/test_room_utilization.py`
- `ifitwala_ed/stock/doctype/location/test_location.py`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| SPA surface | Room Utilization page | `ui-spa/src/pages/staff/analytics/RoomUtilization.vue` | None |
| API endpoints | `room_utilization.py` | `api/room_utilization.py` | `api/test_room_utilization.py` |
| Shared-location visibility | `Location` metadata plus `location_utils.py` | `stock/doctype/location/location.json`, `stock/doctype/location/location.py`, `utilities/location_utils.py` | `stock/doctype/location/test_location.py` |
| Room truth | `Location Booking` read model | `api/room_utilization.py`, `docs/scheduling/room_booking_notes.md` | `api/test_room_utilization.py` |
| Room-type filtering | `Location Type.is_schedulable` plus canonical resolver | `stock/doctype/location_type/location_type.json`, `utilities/location_utils.py` | `api/test_room_utilization.py` |

## 7. Technical Notes (IT)

Status: Implemented

Code refs:
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/utilities/location_utils.py`

Test refs:
- `ifitwala_ed/api/test_room_utilization.py`

- The Room Utilization page still uses one filter-meta bootstrap and one endpoint per read model; the Location Calendar adds one bounded debounced read rather than client-side request waterfalls.
- Shared-location visibility is cache-backed through `get_visible_location_names_for_school(...)`; cache keys remain school-scoped.
- The Location Calendar intentionally reuses `Location Booking` directly instead of rehydrating Meeting or School Event detail payloads.
