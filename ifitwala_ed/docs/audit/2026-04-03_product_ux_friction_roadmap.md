# Product UI-UX Friction Roadmap Anchored To Shipped SPA Surfaces

**Date:** 2026-04-03
**Status:** Planned proposal, non-authoritative audit note
**Scope:** Staff, admin, and student SPA experience in `ifitwala_ed/ui-spa/`
**Primary objective:** Reduce routine workflow friction by improving continuity and context preservation inside the hubs, overlays, and workspaces that already exist.

## Rating Model

Each roadmap item is scored on a **1-5 UX Impact Score** using this weighted user-impact model:

- **Workflow Frequency (30%)**: How often educators, admins, or students touch this flow.
- **Context Switch Reduction (30%)**: How much tab hopping, re-navigation, or repeated selection the change removes.
- **Action Clarity (25%)**: How much easier it becomes to understand what to do next and why something is blocked.
- **Presentation Quality (15%)**: How much better the content is rendered, scanned, and used on real screens.

**Score interpretation**

- **5.0-4.5** = High-priority UX leverage; schedule first.
- **4.4-3.8** = Strong improvement; sequence in the next product cycle.
- **3.7-3.0** = Useful, but narrower.
- **Below 3.0** = Defer unless bundled.

## Bottom Line

The next product work should **not** rebuild Staff Home, Morning Briefing, Focus, Student Home, Course Detail, or Admissions Cockpit. Those hubs already exist and already carry a lot of the right workflow structure.

The highest-leverage work is to **tighten the handoffs between those existing surfaces**, preserve the user's current context when they jump from a calendar/event/card into a workspace, and render authored learning content with the same fidelity that educators create in Desk/SPA editors.

## Current Product Baseline Observed In Code

| Persona | What already exists | Code refs |
|---|---|---|
| Staff / Educators | Staff Home already has a schedule calendar with source chips and event overlays, a Focus card routed through a Focus overlay, quick actions, and a Morning Brief entry point. Class Hub already has session start/end, quick evidence, student picker, notes/tasks, pulse, follow-ups, and an entry into Class Planning. Morning Briefing already has announcements, critical incidents, clinic volume, admissions pulse, absent students, recent logs, and community cards. | `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/ui-spa/src/components/calendar/ScheduleCalendar.vue`, `ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue`, `ifitwala_ed/ui-spa/src/components/focus/FocusListCard.vue`, `ifitwala_ed/ui-spa/src/overlays/focus/FocusRouterOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`, `ifitwala_ed/ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue` |
| Students | Student Home already has current/next class cards, a four-lane Work Board, a Timeline, StudentCalendar, and Quick Links. Course Detail already has Learning Focus, Next Actions, a sticky section navigator, Unit Journey, Session Journey, Assigned Work, and Resources. StudentCalendar already opens event overlays and class events already expose an "Open Course" action. | `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/components/calendar/StudentCalendar.vue`, `ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue` |
| Admin / Ops | Admissions Cockpit already has org/school/my-assignment filters, KPIs, blocker chips, a kanban-style applicant board, workspace overlays, interview actions, and a message drawer. Student Attendance Tool already has school/program/group/default-code filters, a meeting-date calendar, roster editing, remark tips, autosave state, and a direct student-log overlay. | `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`, `ifitwala_ed/ui-spa/src/pages/staff/schedule/StudentAttendanceTool.vue` |

## Ranked Roadmap

| Rank | Persona | Existing baseline | Remaining friction | Proposed increment | Target code refs | Frequency | Context Switch Reduction | Action Clarity | Presentation Quality | UX Impact Score |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | Staff / Educators | Staff schedule events already open `ClassEventModal`, and that modal already has Take Attendance, Open Gradebook, Create Announcement, and Create Task. Class Hub and Class Planning already exist as separate destination pages. | A teacher clicking a class on Staff Home still cannot jump straight into **Class Hub** or **Class Planning** with the clicked event's `student_group`, `session_date`, and `block_number` context preserved. That breaks the handoff from schedule → live teaching workflow. | Add **Open Class Hub** and **Open Class Planning** CTAs to `ClassEventModal`, pass `student_group` plus date/block query context into the destination route, and make the staff class-event modal the main bridge from calendar to the live class workspace. | `ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue` | 5 | 5 | 5 | 4 | **4.85** |
| 2 | Staff / Educators | Morning Briefing already has rich operational cards and Staff Home already has a Morning Brief button, but it opens the full briefing in a new tab and Staff Home itself stays mostly calendar + Focus + quick actions. | Critical incidents, key announcements, absences, or log spikes discovered in Morning Brief are not summarized inline on Staff Home, so users still split attention across two pages at the exact start-of-day moment. | Add a **compact Morning Brief strip/card on Staff Home** with only high-signal counts and one spotlight item, plus a drill-in link to the full Morning Brief page. Do not duplicate the full Morning Brief layout; surface only the top daily exceptions. | `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue` | 5 | 4 | 5 | 4 | **4.55** |
| 3 | Students | StudentCalendar class events already open `ClassEventModal`, and Course Detail already supports query-driven context selection and in-page jump navigation. | The student "Open Course" action from a class event currently routes only by `course_id`, so the student may land in the course but lose the clicked class/group context instead of being taken to the relevant session/unit. | Preserve **clicked class context** in the student calendar → course handoff. At minimum pass `student_group` into `student-course-detail`; ideally enrich the class-event payload and route so Course Detail can land on the matching unit/session section immediately. | `ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/components/calendar/StudentCalendar.vue` | 5 | 5 | 4 | 4 | **4.55** |
| 4 | Staff / Educators | Focus items already show title, subtitle, badge, and assignee metadata, and `FocusItem` already carries `priority` and `due_date`. FocusRouterOverlay already handles several workflow types. | Due timing and urgency are not visible in `FocusListItem`, so all rows can look equally urgent. Unsupported focus action types still fall into a "Not supported yet" dead end inside the overlay. | Render **due-date and priority chips** in Focus rows, sort/visually weight urgency more explicitly, and close the unsupported-action gap by either routing those items to a valid workspace or suppressing them until they are truly actionable. | `ifitwala_ed/ui-spa/src/components/focus/FocusListCard.vue`, `ifitwala_ed/ui-spa/src/components/focus/FocusListItem.vue`, `ifitwala_ed/ui-spa/src/types/focusItem.ts`, `ifitwala_ed/ui-spa/src/overlays/focus/FocusRouterOverlay.vue` | 5 | 4 | 5 | 4 | **4.55** |
| 5 | Students | Course Detail already shows unit summaries, session activities, resource descriptions, and assigned work. Educators now author several of those fields with rich text editors in the planning workspace. | Course Detail still renders many unit/session fields as plain text interpolation, so lists, headings, links, and emphasis authored by educators do not survive into the student experience. | Introduce a **shared rich-text display component** for student-facing learning content and apply it to unit overview, essential understanding, content, skills, concepts, activity directions, resource descriptions, and similar authored fields. | `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/components/planning/PlanningRichTextField.vue` | 5 | 3 | 4 | 5 | **4.25** |
| 6 | Students | Student Home already has Current Class / Next Up / Continue Learning, a Work Board, a Timeline, a Calendar, and Quick Links. Course Detail already has Next Actions and section-level jump controls. | The student experience is strong but still split across multiple decision surfaces that can compete with each other: Current/Next class, Continue Learning, Work Board, Timeline, Calendar, and Course Detail Next Actions all present "what now" signals with slightly different semantics. | Define a **single student action hierarchy** across Student Home and Course Detail: one primary "Continue" action, one secondary "Due soon" queue, and one "Plan ahead" timeline. Keep the current surfaces, but align labels, badge semantics, and CTA precedence so students learn one mental model. | `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue` | 5 | 3 | 5 | 4 | **4.20** |
| 7 | Admin / Ops | Admissions Cockpit already filters by blocker and stage and exposes per-applicant actions. | High-volume review is still card-by-card. There is no bulk selection or batch transition/assignment/message handling for obvious queue work. | Add **bulk selection + batch actions** inside each cockpit column, starting with low-risk actions such as assign to me, mark reviewed, or send templated follow-up where server workflows support it. | `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue` | 4 | 5 | 4 | 3 | **4.15** |
| 8 | Staff / Admin | ClassEventModal can open the Attendance Tool with `student_group`; StudentAttendanceTool consumes that query and already picks a meeting date, loads roster, shows save status, and supports remarks/logs. | The date of the clicked class event is not carried into the Attendance Tool route, and the tool currently clears the `student_group` query after consumption. That makes browser-level recovery/shareability weaker and can force a second date selection. | Make attendance deep links **fully context-preserving** by passing the clicked class `session_date` from `ClassEventModal`, hydrating that date in `StudentAttendanceTool`, and retaining school/program/group/date in the route query rather than consuming only `student_group` once. | `ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue`, `ifitwala_ed/ui-spa/src/pages/staff/schedule/StudentAttendanceTool.vue` | 4 | 5 | 4 | 3 | **4.15** |
| 9 | Admin / Ops | Admissions Cockpit already has blocker chips, per-card actions, applicant workspace overlays, direct interview creation, and a right-side message drawer. | The action model is fragmented: some actions open overlays, some open Desk in a new tab, and communication opens a local drawer. That makes the applicant card feel powerful but not fully coherent. | Consolidate applicant-card actions around a **single right-side case workspace pattern** where possible, and reserve new-tab Desk escape hatches for explicit advanced actions only. Keep blocker deep-links, but make the landing state consistent. | `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue` | 4 | 4 | 4 | 4 | **4.00** |
| 10 | Staff / Educators | Class Hub already has the live workflow surface and Staff Home already has Quick Actions plus the schedule calendar. | Quick Actions are mostly global, not event-aware. When a teacher is looking at a specific class event, the fastest next action should often be class-scoped, not global. | Add **context-aware quick-action variants** that prefill the active student group/course/session when the action is launched from a class event, Class Hub, or a recent calendar click. | `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`, `ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue` | 4 | 4 | 4 | 4 | **4.00** |

## Persona-Specific Proposal Notes

## Staff / Educators

Status: Planned proposal
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/ui-spa/src/components/calendar/ScheduleCalendar.vue`, `ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue`, `ifitwala_ed/ui-spa/src/components/focus/FocusListCard.vue`, `ifitwala_ed/ui-spa/src/components/focus/FocusListItem.vue`, `ifitwala_ed/ui-spa/src/overlays/focus/FocusRouterOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`, `ifitwala_ed/ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`
Test refs: No direct tests found for `StaffHome.vue`, `ScheduleCalendar.vue`, or `FocusRouterOverlay.vue` in this audit pass; any implementation slice should add component/page-level tests for the affected handoff and blocked-state behavior.

**Proposal 1: Calendar → Class Hub / Class Planning bridge**
The class-event modal is already the right event hub. The missing piece is a direct handoff into the live teaching surface and class planning surface with class/date/block context intact.

**Proposal 2: Staff Home Morning Brief digest**
Do not move Morning Briefing into Staff Home wholesale. Add only a compact digest card that surfaces the highest-priority counts and one spotlight announcement, so users can stay in Staff Home unless they need the full briefing.

**Proposal 3: Stronger Focus row semantics**
Focus is already a router and should stay that way. The improvement is to expose urgency (`due_date`, `priority`) and remove unsupported-action dead ends so every row that appears in Focus is actually actionable.

## Students

Status: Planned proposal
Code refs: `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/components/calendar/StudentCalendar.vue`, `ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue`
Test refs: `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

**Proposal 1: Preserve clicked class context from calendar into Course Detail**
StudentCalendar already gets students to the right course, but not reliably to the right class context. The route handoff should preserve at least `student_group`, and ideally the selected session/unit anchor as well.

**Proposal 2: Render authored curriculum content as rich text**
Now that planning content is authored with text editors, the student-facing side should render the same content with headings, links, lists, and emphasis preserved, not flattened into plain text.

**Proposal 3: One student action hierarchy across Home and Course Detail**
Student Home and Course Detail are both task-oriented already. The remaining design work is not adding more surfaces, but making the labels, badges, and CTA priority consistent so "Continue", "Due soon", and "Plan ahead" mean the same thing everywhere.

## Admin / Ops

Status: Planned proposal
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`, `ifitwala_ed/ui-spa/src/pages/staff/schedule/StudentAttendanceTool.vue`, `ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue`
Test refs: No direct page-level tests found for `AdmissionsCockpit.vue` or `StudentAttendanceTool.vue` in this audit pass; queue/bulk-action and deep-link hydration work should include interaction tests.

**Proposal 1: Make Admissions Cockpit action patterns more coherent**
The cockpit already exposes most of the right case actions. The UX debt is that those actions fan out into overlays, Desk tabs, and a local drawer. Converging on one case-workspace interaction pattern would reduce cognitive switching.

**Proposal 2: Add bulk queue operations where workflow state is unambiguous**
Admissions Cockpit is already organized as a board. Bulk actions should be layered on that existing board rather than introducing a separate queue page.

**Proposal 3: Make Attendance Tool links fully recoverable**
Attendance Tool is already usable and save-aware. The next improvement is route-level context persistence so a class-event click, browser refresh, or copied URL retains the intended school/program/group/date.

## Open Questions

- For staff class events, should **Open Class Hub** be the primary CTA and **Take Attendance / Open Gradebook** become secondary, or should that vary by role/capability?
- For Student Course Detail deep-linking, do we want to extend the class-event payload with `class_session` / `unit_plan`, or should the backend resolve the matching learning context from `student_group` + `session_date` + `block_number`?
- For Admissions Cockpit, which Desk-tab actions are intentionally kept as escape hatches for power users, and which should be migrated into the SPA workspace to reduce context switching?
