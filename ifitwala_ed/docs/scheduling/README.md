# Scheduling Architecture Notes

This folder contains the current architecture and design notes for scheduling-adjacent domains.

Read in this order:

1. `01_scheduling_architecture.md` — canonical scheduling system boundaries, abstract-vs-materialized time model, and enrollment bridge points
2. `02_student_group_generation_architecture.md` — authoritative sectioning note for how `Student Group` rows are created, populated, linked, and not yet orchestrated
3. `03_attendance_architecture.md` — authoritative attendance note for ledger truth, meeting-date derivation, scoped read models, and current whole-day vs block constraints
4. `employee_booking_notes.md` — staff availability fact-table contract
5. `room_booking_notes.md` — room occupancy fact-table contract

Related canonical notes live in:

- `docs/enrollment/03_enrollment_architecture.md`
- `docs/enrollment/08_enrollment_scheduling_contract.md`
- `docs/enrollment/02_school_calendar_architecture.md`
- `docs/student/student_attendance_analytics.md`
- `docs/spa/09_event_quick_create_contract.md`
- `docs/spa/15_room_utilization_contract.md`

Only the files above should be treated as current architecture notes for scheduling runtime behavior.
