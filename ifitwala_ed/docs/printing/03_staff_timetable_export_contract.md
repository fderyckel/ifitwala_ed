# Staff Timetable Export Contract

Status: Active

Code refs:
- `ifitwala_ed/api/calendar.py`
- `ifitwala_ed/api/calendar_export.py`
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/templates/print/staff_timetable_export.html`
- `ifitwala_ed/templates/print/staff_timetable_export.css`
- `ifitwala_ed/ui-spa/src/components/calendar/ScheduleCalendar.vue`
- `ifitwala_ed/ui-spa/src/components/calendar/staffTimetableExport.ts`

Test refs:
- `ifitwala_ed/api/test_calendar_export.py`
- `ifitwala_ed/ui-spa/src/components/calendar/__tests__/ScheduleCalendar.test.ts`

This document is authoritative for the premium self-service timetable PDF export surfaced from the staff calendar card.

If code and this note disagree, stop and resolve the drift explicitly.

## 1. Bottom Line

The staff timetable export is a dedicated Ifitwala PDF for the logged-in staff user.

It is not a `window.print()` flow and it must not feel like a printed `FullCalendar` screen.

The export lives on the existing staff calendar surface and supports:

- `This week`
- `Next 2 weeks`
- `Next month`

All outputs render as weekly timetable spreads so timed classes, meetings, events, and holidays remain readable on paper.

## 2. Surface Contract

### 2.1 Entry point

The action surfaces in the existing `ScheduleCalendar.vue` header/control cluster next to `Refresh`.

Rules:

1. The action label is `Print timetable`.
2. The action must remain visible on the staff calendar card rather than being buried in chips or unrelated menus.
3. On narrow layouts, the control may collapse visually, but it remains part of the same top control cluster.

### 2.2 Interaction

Clicking `Print timetable` opens a lightweight export panel on the calendar card.

The panel offers the three supported presets and short helper copy for each range.

Choosing a preset opens the PDF in a new tab using the server-owned export endpoint.

If the browser blocks the new tab, the UI must show an actionable inline error and toast telling the user to allow pop-ups.

## 3. Scope And Permissions

Status: Active

Phase 1 is self-service only.

Rules:

1. The export is limited to the current logged-in staff user.
2. The export requires a signed-in non-Guest user and the same employee-linked scope resolution already used by the staff calendar feed.
3. Printing another employee's timetable is out of scope until a separate permission contract exists.

## 4. Source Authority

Status: Active

The PDF is a print view over the existing staff calendar read model.

It must reuse the same source rules already defined in `docs/scheduling/04_calendar_aggregation_architecture.md`.

Included sources:

- `student_group`
- `meeting`
- `school_event`
- `staff_holiday`

Operational source truth:

1. Class commitments come from `Employee Booking` rows linked to `Student Group`.
2. Meetings come from `Meeting`.
3. School events come from `School Event`.
4. Holidays come from the resolved `Staff Calendar` / `School Calendar` precedence used by the staff feed.

Clients must not invent a separate print-only event source model.

## 5. Range Contract

Status: Active

The export window is resolved server-side using the Frappe site timezone.

Rules:

1. `this_week` means the Monday to Sunday week containing the current local date.
2. `next_2_weeks` means the current Monday plus fourteen days, rendered as two weekly spreads.
3. `next_month` means the next calendar month only, from the first day of next month to the first day of the following month.
4. Every preset renders as weekly spreads, even when the selected window starts or ends mid-week.
5. Days outside the selected window may appear as muted cells so each page preserves a stable Monday to Sunday timetable structure.

## 6. Print Composition Contract

Status: Active

This export uses the report-print HTML lane from the print system contract.

Rules:

1. The output is generated from dedicated server-owned HTML and CSS.
2. The export must not print the interactive calendar DOM.
3. The page model is A4 landscape.
4. The document must present itself as an Ifitwala planning sheet, not a generic SaaS calendar export.

Required visual grammar:

- top ribbon
- warm paper-toned background
- school logo and school tagline when present
- serif-led title treatment
- muted metadata blocks
- weekly day columns with soft panel treatment
- all-day strip for holidays and all-day events
- source-specific event cards for timed commitments
- empty-day planning space when no timed commitments exist
- compact weekly priorities checklist area
- daily open planning space lines on in-window days where layout allows

The document may borrow brand context from the employee school or organization, but it must stay within the current employee/event scope and must not guess cross-tenant branding.

## 7. API Boundary

Status: Active

The public RPC method path is:

- `ifitwala_ed.api.calendar.export_staff_timetable_pdf`

Rules:

1. The public API path remains anchored in `api/calendar.py`.
2. Export implementation details live in `api/calendar_export.py`.
3. The response is an inline `application/pdf` download payload.
4. The filename pattern is `staff-timetable-<preset>-<start_date>.pdf`.
5. The PDF renderer must enforce A4 landscape at generation time rather than relying on CSS print hints alone.

## 8. Performance Contract

Status: Active

Rules:

1. The export uses one bounded server-side range read for the selected window.
2. The export reuses the existing staff calendar aggregation rules rather than issuing per-event detail calls from the client.
3. Any future cache behavior must stay aligned with staff-feed scope ownership and permission boundaries.
