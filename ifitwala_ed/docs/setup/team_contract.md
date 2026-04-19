# Team Contract (v1)

Status: Active

This document is the canonical contract for `Team` hierarchy, membership, and team-owned meeting entry points.

## 1. Canonical Model

Status: Implemented

Code refs:
- `ifitwala_ed/setup/doctype/team/team.json`
- `ifitwala_ed/setup/doctype/team/team.py`
- `ifitwala_ed/setup/doctype/team_member/team_member.json`
- `ifitwala_ed/setup/doctype/team_member/team_member.py`

Test refs:
- `ifitwala_ed/setup/doctype/team/test_team.py`

Rules:

1. `Team` is a tree DocType backed by `NestedSet` using `parent_team` as the canonical hierarchy field.
2. `Team Member` is the `members` child table, and business rules for team membership belong in the parent `Team` controller.
3. Parent teams must be group nodes (`is_group = 1`).
4. Non-group teams must have at least 2 member rows with a valid `employee` link before save.
5. Duplicate members are rejected in the parent controller using `employee` first and `member` as fallback identity.
6. Circular `parent_team` chains are rejected.
7. The Desk tree root label `All Teams` is a UI sentinel, not a persisted `Team` record.

## 2. Tree View and Entry-Point Contract

Status: Partial

Code refs:
- `ifitwala_ed/setup/doctype/team/team_tree.js`
- `ifitwala_ed/setup/doctype/team/team.py`
- `ifitwala_ed/setup/doctype/team/team.json`

Test refs:
- `ifitwala_ed/setup/doctype/team/test_team.py`

Rules:

1. The Desk tree uses named server endpoints only:
   - `ifitwala_ed.setup.doctype.team.team.get_children`
   - `ifitwala_ed.setup.doctype.team.team.add_node`
2. Tree filters are limited to `organization` and `school`; no other filter contract is defined for the tree surface.
3. Root loading must treat a visible team whose parent is outside the visible result set as a root row so scoped trees do not render empty.
4. `add_node` maps the `All Teams` UI sentinel to an empty `parent_team`.
5. The tree `Add Child` prompt is a complete flow for creating group teams.
6. The tree `Add Child` prompt is not a complete flow for creating non-group teams because non-group teams still require member rows at save time and the prompt does not collect members.
7. Until a dedicated guided leaf-team flow is implemented, the canonical leaf-team creation path is the `Team` form surface, not the tree quick-create prompt.

## 3. Membership and Meeting Workflows

Status: Implemented

Code refs:
- `ifitwala_ed/setup/doctype/team/team.js`
- `ifitwala_ed/setup/doctype/team/team.py`
- `ifitwala_ed/setup/doctype/meeting/meeting.py`
- `ifitwala_ed/setup/doctype/meeting_series/meeting_series.json`

Test refs:
- `None`

Rules:

1. The `Team` form provides the membership UI; the child table controller remains empty.
2. The `Add Members` action calls `get_eligible_users`, which returns enabled `User` records joined to active `Employee` records and can be narrowed by `school` and `organization`.
3. `schedule_recurring_meetings` is the named team scheduling workflow endpoint. It creates a `Meeting Series` and inserts one `Meeting` per generated occurrence.
4. Team meeting scheduling copies current `Team Member` rows with an `employee` value into each created meeting as participants.
5. `get_schedulable_academic_years` resolves academic years from the team school first, then school ancestors.
6. `get_team_meeting_book` is the printable team meeting-book endpoint and requires `Team` read permission before meeting-level visibility is applied.

## 4. SPA Quick-Create Integration

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/overlays/calendar/EventQuickCreateOverlay.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/RoomUtilization.vue`
- `ifitwala_ed/ui-spa/src/lib/services/calendar/eventQuickCreateService.ts`
- `ifitwala_ed/api/calendar.py`
- `ifitwala_ed/api/calendar_quick_create.py`

Test refs:
- `ifitwala_ed/api/test_calendar.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffHome.test.ts`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/RoomUtilization.test.ts`

Rules:

1. `EventQuickCreateOverlay` supports a team scheduling mode via `meetingMode='team'`.
2. In team mode, the selected team is part of the workflow contract and team attendees are hydrated from the named endpoint `get_meeting_team_attendees`.
3. Team attendees loaded from team mode are locked by context inside the overlay because the meeting submit path also persists the `team` field server-side.
4. Staff Home keeps its existing ad-hoc event launcher and also exposes an explicit `Schedule team meeting` quick action that opens quick create in `meetingMode='team'`.
5. Room Utilization keeps its existing ad-hoc launcher and also exposes a `Schedule team meeting` entry point that carries the selected school into the team scheduling flow.

## 5. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/setup/doctype/team/team.json`
- `ifitwala_ed/setup/doctype/team/team.py`
- `ifitwala_ed/setup/doctype/team/team.js`
- `ifitwala_ed/setup/doctype/team/team_tree.js`
- `ifitwala_ed/setup/doctype/team_member/team_member.json`
- `ifitwala_ed/setup/doctype/team_member/team_member.py`
- `ifitwala_ed/setup/doctype/meeting/meeting.py`
- `ifitwala_ed/setup/doctype/meeting_series/meeting_series.json`
- `ifitwala_ed/ui-spa/src/overlays/calendar/EventQuickCreateOverlay.vue`
- `ifitwala_ed/ui-spa/src/lib/services/calendar/eventQuickCreateService.ts`
- `ifitwala_ed/api/calendar.py`
- `ifitwala_ed/api/calendar_quick_create.py`

Test refs:
- `ifitwala_ed/setup/doctype/team/test_team.py`
- `ifitwala_ed/api/test_calendar.py`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | `Team`, `Team Member` | `setup/doctype/team/team.json`, `setup/doctype/team_member/team_member.json` | `setup/doctype/team/test_team.py` |
| Controller / workflow logic | `Team` parent controller | `setup/doctype/team/team.py` | `setup/doctype/team/test_team.py` |
| API endpoints | `get_children`, `add_node`, `get_eligible_users`, `get_schedulable_academic_years`, `schedule_recurring_meetings`, `get_team_meeting_book` | `setup/doctype/team/team.py`, `setup/doctype/meeting/meeting.py` | `setup/doctype/team/test_team.py` |
| Desk / UI surfaces | Team form, Team tree, and team-aware quick-create contract | `setup/doctype/team/team.js`, `setup/doctype/team/team_tree.js`, `ui-spa/src/overlays/calendar/EventQuickCreateOverlay.vue`, `ui-spa/src/pages/staff/StaffHome.vue`, `ui-spa/src/pages/staff/analytics/RoomUtilization.vue` | `ifitwala_ed/api/test_calendar.py`, `ui-spa/src/pages/staff/__tests__/StaffHome.test.ts`, `ui-spa/src/pages/staff/__tests__/RoomUtilization.test.ts` |
| Reports / dashboards / briefings | Team meeting book only | `setup/doctype/meeting/meeting.py` | `None` |
| Scheduler / background jobs | None | None | None |
| Tests | Team tree contract regression coverage plus calendar quick-create facade coverage | `setup/doctype/team/test_team.py`, `ifitwala_ed/api/test_calendar.py` | `setup/doctype/team/test_team.py`, `ifitwala_ed/api/test_calendar.py` |

## 6. Technical Notes (IT)

Status: Implemented

Code refs:
- `ifitwala_ed/setup/doctype/team/team.json`
- `ifitwala_ed/setup/doctype/team/team.py`
- `ifitwala_ed/setup/doctype/team/team_tree.js`
- `ifitwala_ed/setup/doctype/team/test_team.py`

Test refs:
- `ifitwala_ed/setup/doctype/team/test_team.py`

- **DocType**: `Team` (`ifitwala_ed/setup/doctype/team/`)
- **Autoname**: `field:team_name`
- **Tree config**:
  - `is_tree = 1`
  - `nsm_parent_field = parent_team`
  - class `Team(NestedSet)`
- **Key fields in this contract**:
  - `team_name`
  - `team_code`
  - `is_group`
  - `organization`
  - `school`
  - `parent_team`
  - `members`
- **Whitelisted methods**:
  - `get_children`
  - `add_node`
  - `get_eligible_users`
  - `get_schedulable_academic_years`
  - `schedule_recurring_meetings`
- **Related meeting endpoint**:
  - `ifitwala_ed.setup.doctype.meeting.meeting.get_team_meeting_book`
