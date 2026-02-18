# Portal Sufficiency Audit: Teacher Experience & StaffHome

**Date:** 2026-02-18
**Author:** Antigravity (Product Manager Agent)
**Scope:** Teacher Experience on Portal (StaffHome + Daily Loops)
**Thesis:** Portal is the primary application for teachers. StaffHome must be an operational cockpit, not a dashboard of links.

---

## 1. Executive Summary

The current `StaffHome` is a **navigation hub**, not an **operational cockpit**. While it successfully keeps teachers on the Portal (adhering to the "Portal First" intent), it fails to surface critical daily signals. A teacher must click away to check attendance, view announcements, or see class lists, resulting in high cognitive load and constant context switching. The "Focus" system is technically sound but underutilized, currently showing only Student Log follow-ups while ignoring attendance gaps and grading deadlines. The highest leverage move is to transform `StaffHome` from a list of links into a high-signal surface that answers "What do I need to do right now?" without a click.

---

## 2. Intent Map

*   **Portal vs Desk Intent:**
    *   **Portal:** Primary daily driver for teachers. All routine tasks (Attendance, Logs, Briefing, simple Tasks) must be doable here.
    *   **Desk:** Admin backend (structures, HR, finance, setups). Teachers should rarely, if ever, visit Desk.
    *   *Source:* `docs/spa/01_spa_architecture_and_rules.md`, `docs/spa/student_log_note.md`
*   **Teacher Workflows Intent:**
    *   **Attendance:** "Two-click capture flow" rooted in teaching context. Primary entry point.
    *   **Student Log:** "Teacher-centered observational workflow". Capture is easy; follow-up is structured.
    *   **Focus:** "Surfaces attention... refreshes after completion." Should drive the workflow.
*   **Navigation Intent:**
    *   Teachers redirect to `/staff` immediately.
    *   Navigation should be role-scoped and minimize "hunting".
*   **Privacy/Visibility Intent:**
    *   **Option A (Teaching Context):** Teachers see logs for students they *currently teach*.
    *   Visibility is "Opt-in" for parents/students.
    *   *Source:* `docs/spa/student_log_note.md` (§15)

---

## 3. Portal Teacher Surface Inventory

| Surface / Route | Component | Key Actions |
| :--- | :--- | :--- |
| **/staff** (Gateway) | `StaffHome.vue` | View Schedule, Focus Items, Quick Actions, Analytics Links. |
| **Schedule** (Embedded) | `ScheduleCalendar.vue` | View monthly/weekly calendar. Click event to see details interaction. |
| **Focus** (Embedded) | `FocusListCard.vue` | View/Open "Pending" Student Log follow-ups. |
| **/staff/morning-brief** | `MorningBriefing.vue` | **(New Tab)** Read daily bulletin/briefing. |
| **/staff/attendance** | `StudentAttendanceTool.vue` | Mark attendance. |
| **/staff/gradebook** | `Gradebook.vue` | Enter grades/evidence. |
| **/staff/student-groups** | `StudentGroups.vue` | View class lists/rosters. |
| **Overlay: Create Task** | `CreateTaskOverlay.vue` | Create a generic task (ToDo). |
| **Overlay: Student Log** | `StudentLogCreateOverlay.vue` | Create an observation/incident log. |
| **Analytics Hub** | `StaffHome.vue` (Section) | Links to 20+ specific analytics dashboards. |

---

## 4. StaffHome "5-Second Cockpit" Evaluation

*Can a tired teacher answer these in 5 seconds without clicking?*

1.  **What do I teach today?**
    *   **Partial.** `ScheduleCalendar` shows the calendar, but it may be in "Month" or "Week" view, requiring cognitive parsing to find "Today's next lesson". It lacks a simple "Up Next: Grade 9 Math (Room 302)" summary.
    *   *Evidence:* `StaffHome.vue:35` (`<ScheduleCalendar />`).
2.  **What needs my action today?**
    *   **Partial/No.** `FocusListCard` shows *Student Log follow-ups* only. It does **NOT** show:
        *   Personal Tasks (created via "Create task" - these effectively disappear into the void?).
        *   Grading deadlines.
        *   Slip/Form approvals.
    *   *Evidence:* `api/focus.py` (`list_focus_items` queries only `Student Log` and `ToDo` linked to logs).
3.  **Student issues I must follow up on?**
    *   **Yes (if assigned).** Shows in Focus if `requires_follow_up=1` and linked to user.
    *   **No (if observational).** If I wrote a log that is "Open" with another staff member, I have no visibility of it here.
    *   *Evidence:* `api/focus.py` (Include `assignee` and `author review` items).
4.  **Attendance gaps?**
    *   **No.** There is zero signal for "You missed attendance for Period 2". It requires clicking "Attendance Analytics" or "Attendance Ledger".
    *   *Evidence:* `StaffHome.vue` has no component for this. `api/attendance.py` has no "my missing attendance" endpoint.
5.  **Messages/alerts?**
    *   **No.** "Morning Brief" is a static button. "Announcements" is a link. No "3 Unread" badge or list of recent headlines.
    *   *Evidence:* `StaffHome.vue:18` (Button), `StaffHome.vue:542` (Link).

---

## 5. Context Switch Points

*   **Checking "Morning Brief":** Forces New Tab (`target="_blank"` in `StaffHome.vue:21`). Teacher leaves the cockpit immediately.
*   **Marking Attendance:** Must click "Attendance Analytics" -> Navigate or rely on Calendar click -> Overlay. No direct "Mark Now" for current class on Home.
*   **Checking Announcements:** Must click link -> `/staff/announcements`.
*   **Viewing Class List:** Must click "Student Groups" or finding group in Calendar.

---

## 6. Friction Scorecard

| Area | Score (1-5) | Justification |
| :--- | :---: | :--- |
| **StaffHome** | **3/5** | Visually clean ("Apple-like"), but low information density. It's a launcher, not a dashboard. "Focus" is too narrow. |
| **Attendance Flow** | **2/5** | High friction. No "Submit Attendance" alert for the active class. Requires hunting in Calendar or navigating to tools. |
| **Student Log Flow** | **4/5** | Good. "Add student log" is a primary action. Follow-ups appear in Focus. |
| **Calendar/Tasks** | **3/5** | Calendar is robust but dense. "Create Task" exists, but *viewing* personal tasks is impossible on StaffHome (Focus doesn't load them). |
| **Signals** | **1/5** | Critical failure. No unread messages, no attendance alerts, no missing grade alerts. |

---

## 7. Proposals (Ranked by Leverage)

### Proposal 1: "Up Next" Teaching Card (Cockpit Primary)
*   **Problem:** `ScheduleCalendar` is too dense for "right now". Teachers need to know: "Where do I go *now*?" and "Did I take attendance?".
*   **Target Workflow:** Daily class management & movement.
*   **Changes on StaffHome:**
    *   Insert a new component `TeachingAgendaCard.vue` above/next to Focus.
    *   Fetch today's sessions from `api/calendar`.
    *   Display: Current/Next Class, Room, Time.
    *   **Crucial Signal:** "Attendance Status" indicator (Green Check / Red Warning).
    *   **Action:** Click -> Open Attendance Overlay (Mode A).
*   **Scope:** Portal only. Reuses existing Calendar/Attendance APIs.
*   **Acceptance:** Visible "Next Class". Red badge if attendance missing for past/current class.

### Proposal 2: "Attendance Gaps" in Focus Stream
*   **Problem:** Missing attendance is the #1 operational failure. It is currently invisible on StaffHome.
*   **Target Workflow:** Compliance / Daily Close-out.
*   **Changes on StaffHome:**
    *   Update `api/focus.py` to query `Student Group Schedule` vs `Student Attendance`.
    *   Inject synthetic Focus Items: "Missing Attendance: Grade 9 Science (Period 2)".
    *   Action: Click -> Open Attendance Overlay.
*   **Scope:** Backend `list_focus_items` update + frontend rendering (handled by existing `FocusListCard`).
*   **Acceptance:** Missing a session appears in "Your Focus" list automatically.

### Proposal 3: "Latest Announcements" Widget
*   **Problem:** Announcements are buried in the "Analytics" link farm. Important ops info is missed.
*   **Target Workflow:** Situational awareness.
*   **Changes on StaffHome:**
    *   Add `AnnouncementWidget.vue` (taking 1/3 width or stack with Quick Actions).
    *   Fetch latest 3 `Published` records from `Org Communication` (server-scoped to user).
    *   Display: Title, Date, "New" badge (if < 24h).
    *   Action: Click -> Open details overlay or navigate to Archive.
*   **Scope:** Portal read-only.
*   **Acceptance:** Top 3 announcements visible without click.

### Proposal 4: Rationalize "Quick Actions" with "My Tasks"
*   **Problem:** "Create Task" creates a ToDo, but `list_focus_items` filters for `Student Log` references only. Personal tasks vanish.
*   **Target Workflow:** Personal productivity.
*   **Changes on StaffHome:**
    *   Update `api/focus.py` to allow `reference_type = NULL` or `reference_type = 'Task'` (or whatever Create Task uses).
    *   Rename "Quick Actions" column to "My Day" or similar if space allows, or simply ensure Focus handles generic ToDos.
*   **Scope:** Backend query adjustment.
*   **Acceptance:** Creating a task "Grade Papers" makes it appear in the "Your Focus" list.

### Proposal 5: "Morning Brief" Inline Summary
*   **Problem:** Opening a new tab for Morning Brief disconnects the flow. It's often closed and forgotten.
*   **Target Workflow:** Daily start.
*   **Changes on StaffHome:**
    *   Replace the "Morning Brief" button with an inline, collapsible summary or a "Briefing Card".
    *   Or, keep the button but add a "status" line: "Use of Force Policy updated", "3 Absences today".
*   **Scope:** Portal UI.
*   **Acceptance:** Key briefing headlines visible on StaffHome.

---

## 8. Open Questions

1.  **Focus Definition:** Does the product intent allow "Focus" to include mere "Alerts" (like missing attendance), or must strictly be "Workflows"? (Assumption: Alerts are acceptable/necessary).
2.  **Task Storage:** Where do "Create Task" items actually go? `TabToDo`? Why are they excluded from Focus?
3.  **Attendance Query:** Is there a performant way to query "Missing Attendance" without scanning the whole year? (Restriction: Check `today` and `yesterday` only to keep it fast).
