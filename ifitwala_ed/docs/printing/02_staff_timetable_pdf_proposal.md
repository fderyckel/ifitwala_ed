# Staff Timetable PDF Proposal

Status: Historical proposal, superseded by `03_staff_timetable_export_contract.md`

Code refs:
- `ifitwala_ed/docs/printing/03_staff_timetable_export_contract.md`
- `ifitwala_ed/docs/printing/01_print_system_contract.md`
- `ifitwala_ed/docs/scheduling/04_calendar_aggregation_architecture.md`
- `ifitwala_ed/api/calendar.py`
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/api/calendar_details.py`
- `ifitwala_ed/ui-spa/src/composables/useCalendarEvents.ts`
- `ifitwala_ed/ui-spa/src/components/calendar/ScheduleCalendar.vue`
- `ifitwala_ed/hr/print_format/staff_calendar_print/staff_calendar_print.html`
- `ifitwala_ed/hr/print_format/staff_calendar_print/staff_calendar_print.css`
- `ifitwala_ed/printing/letter_head/default_school_letter_head.html`
- `ifitwala_ed/printing/letter_head/default_school_letter_head.css`

Test refs:
- `ifitwala_ed/api/test_portal_calendar.py`
- `ifitwala_ed/hr/test_staff_calendar_print_format.py`
- `ifitwala_ed/ui-spa/src/composables/__tests__/useCalendarEvents.test.ts`
- `ifitwala_ed/ui-spa/src/components/calendar/__tests__/scheduleCalendarListMeta.test.ts`

## Bottom line

Ifitwala_Ed should add a premium PDF timetable export for the logged-in staff employee directly from the existing staff calendar surface.

This should use the report-print HTML lane from the print contract, not a larger `Print Format` on `Staff Calendar`, because the requested output is a merged operational view across class bookings, meetings, school events, and holidays.

Week, next 2 weeks, and next month should all render as weekly timetable spreads so the PDF stays readable and elegant.

## 1. Current reality

1. The app already ships a managed `Staff Calendar Print` format.
2. That print format is polished, but it is a monthly holiday calendar for the `Staff Calendar` DocType.
3. The current staff portal calendar is already the correct user-facing read model for day-to-day commitments:
   - classes from `Employee Booking`
   - meetings from `Meeting`
   - school events from `School Event`
   - holidays from `Staff Calendar Holidays` or `School Calendar Holidays`
4. The current SPA calendar surface already follows the calm, premium staff style direction through `ScheduleCalendar.vue`, `paper-card`, `schedule-card`, and the staff shell.

## 2. Recommendation

### 2.1 Product shape

- Add a `Print timetable` action to the existing staff calendar surface.
- Phase 1 is self-service for the current logged-in employee only.
- Offer three presets:
  - this week
  - next 2 weeks
  - next month
- Include these source types in the printed timetable:
  - class commitments
  - meetings
  - school events
  - staff holidays / weekly offs

### 2.2 Print lane

- Use Lane B: report-print HTML.
- Keep the existing `Staff Calendar Print` as the holiday-calendar print lane.

Reason:

- the requested PDF is operational, not a single-record profile
- it spans multiple source doctypes
- it depends on a dedicated server-owned visibility model
- it should reuse the merged staff calendar read model rather than a `Staff Calendar` document print

## 3. UX proposal

- Entry point: the existing `ScheduleCalendar.vue` card on staff home.
- Desktop placement: a visible `Print timetable` action in the header/control cluster, grouped with `Refresh`, not buried inside source chips.
- Mobile placement: the same action should stay in the top control row, but may collapse into a compact overflow/export trigger if horizontal space is tight.
- Interaction: a small export sheet with the three date presets and a short range preview.
- Result: browser-opened PDF ready for print or save.
- Failure states must stay actionable:
  - if the user has no linked `Employee`, show the same explicit message already used by the staff calendar feed
  - if the range has no commitments, generate a valid empty-state PDF instead of failing silently

To reduce friction, the first version should not ask users to build a complex filter set. The default export should include the same four staff sources already used by the calendar feed.

The print action should feel like a natural extension of the staff home planning surface, not like a secondary report hidden elsewhere in Desk navigation.

## 4. Visual direction

The PDF should feel institution-facing and premium, aligned with the existing print and SPA style language:

- calm, formal, low-noise presentation
- generous whitespace
- serif-led title treatment, sans-serif body copy
- quiet metadata blocks
- restrained accent color
- light rules and soft panel boundaries
- no dense ERP-style tables unless they materially improve readability

### 4.0 Non-negotiable anti-goal

This must not feel like a printed `FullCalendar` page.

Rules:

- do not print the browser calendar DOM
- do not rely on `window.print()` over the interactive calendar surface
- do not carry over FullCalendar grid chrome, toolbar language, or generic event pills
- generate a dedicated server-owned print composition from normalized calendar payloads

The print artifact should be a designed document, not a screenshot or CSS print mode of the existing widget.

### 4.1 Page model

- A4 landscape for timetable pages
- compact brand header that borrows the grammar of the managed letterhead:
  - ribbon
  - school / organization identity
  - elegant title
  - muted generation metadata
- weekly timetable grid as the primary page
- all-day strip above the time grid for holidays and all-day school events
- timed commitments in the main grid with clear source distinction

### 4.1.1 Ifitwala-specific print grammar

The PDF should borrow recognizable Ifitwala traits from the existing letterhead and calm-first SPA language:

- a refined top ribbon and school-owned brand block
- warm paper-like background tone rather than flat white dashboard chrome
- serif month/week titles with restrained sans metadata
- muted day columns with soft school-brand tinting, not software-blue calendar borders
- event blocks styled as timetable cards with quiet source markers:
  - class blocks feel academic and structured
  - meeting blocks feel formal and administrative
  - school events feel ceremonial or community-facing
  - holidays / weekly offs live in a calmer all-day strip, not the same visual weight as timed teaching
- a slim notes rail or annotation area so the output feels like a working school document rather than a software export

The document should read like an Ifitwala planning sheet prepared for a teacher, not like a generic SaaS calendar export.

### 4.2 Range behavior

- `This week`: one weekly spread
- `Next 2 weeks`: two weekly spreads
- `Next month`: four or five weekly spreads, one per week

The proposal explicitly avoids a single compressed month matrix for the month option. That layout works for holidays, but not for a timetable with timed classes, meetings, and events.

## 5. Data and architecture

### 5.1 Source authority

The export must keep the same source authority already documented for the staff feed:

- classes from `Employee Booking`, not raw `Student Group Schedule`
- meetings from `Meeting`
- school events from `School Event`
- holidays from the resolved staff-calendar / school-calendar precedence

This avoids print-only scope drift and preserves the existing operational truth model.

### 5.2 Read-model rule

- build the print payload server-side
- use one bounded range read
- do not assemble the PDF from client-side waterfalls or per-event detail calls
- reuse the same subject/window/source cache ownership logic as the staff calendar feed where safe

### 5.3 Likely implementation touchpoints

- `ifitwala_ed/api/calendar.py`
  public RPC boundary should continue to own the staff calendar print/export entrypoint
- `ifitwala_ed/api/calendar_staff_feed.py`
  current source merge logic should be reused or factored so screen and print do not diverge
- `ifitwala_ed/ui-spa/src/components/calendar/ScheduleCalendar.vue`
  add the user-facing export action in the header/control cluster
- app-owned print HTML/CSS artifact
  new report-print asset for the timetable layout

No DocType schema change is required for the proposal as written.

## 6. Permissions and scope

Phase 1 should be limited to a user printing their own timetable.

That matches the current product ask, keeps the permission model simple, and reuses the existing employee-linked scope resolution in the staff calendar feed.

Printing another employee's timetable should be treated as a separate contract because it needs explicit owner rules for:

- who may select another employee
- whether scope is school-limited, organization-limited, or role-limited
- whether managers can print direct reports only or broader staff scope

## 7. Concurrency and performance

- one bounded export read per request
- no client-side refetch cascade
- no background job dependency for correctness-critical range assembly
- no duplicated source recomputation across independent helpers if the same window is already being built

If the export becomes a hot path, caching should stay permission-safe and keyed by the same scope dimensions already used by the staff feed.

## 8. Delivery phases

1. Add self-service timetable PDF export for current staff user with week / 2-week / month presets.
2. Reuse current staff calendar aggregation rules so print and screen stay identical on inclusion and visibility.
3. Match the PDF chrome to the managed letterhead / premium print grammar and add print-specific tests.
4. Revisit delegated export of another employee only after the permission contract is documented.

## 9. Risks and open questions

- The month preset must stay readable; weekly spreads are the recommended answer.
- A small product decision is still needed on whether export should always include all four staff sources or mirror the currently toggled chips from the on-screen calendar.
- If a future school wants a portrait month-planner, that should be a separate output type, not a compromise that weakens the operational timetable PDF.
