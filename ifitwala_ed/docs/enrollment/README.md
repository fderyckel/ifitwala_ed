# Enrollment Architecture Notes

This folder contains the current architecture and design notes for enrollment-adjacent domains.

Read in this order:

1. `01_academic_year_architecture.md` — lifecycle, visibility, Desk visibility, and scoped year closure
2. `02_school_calendar_architecture.md` — school-calendar authoring, term resolution, and nearest-ancestor calendar resolution
3. `03_enrollment_architecture.md` — canonical enrollment object chain, workflow lanes, and Desk vs portal ownership
4. `08_enrollment_scheduling_contract.md` — authoritative bridge between committed enrollment truth and operational scheduling/grouping
5. `07_year_rollover_architecture.md` — current rollover lanes, closure inventory, and explicit non-orchestrated gaps
6. `04_enrollment_examples.md` — non-normative scenarios and stress tests
7. `05_course_choice_semantics.md` — implemented basket-group and choice-row semantics
8. `06_activity_booking_architecture.md` — sibling architecture for activity booking

Only the files above should be treated as current architecture notes.

Historical audit and implementation-plan notes that no longer described current runtime behavior were intentionally removed. Use git history if historical context is required.
