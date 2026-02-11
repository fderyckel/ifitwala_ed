# Activity Booking Architecture (v2)

Status: Active

This document defines the implemented architecture for after-school / extra-curricular activity booking.

## 1. Canonical Models

1. `Program Offering` remains the offering envelope.
2. `Program Offering Activity Section` (child table) links each offering to one or more `Student Group` rows (`group_based_on = Activity`).
3. `Activity Booking` is the booking lifecycle truth.
4. `Org Communication` is the communication truth, with explicit activity context fields:
   - `activity_program_offering`
   - `activity_booking`
   - `activity_student_group`
5. `Communication Interaction` remains the summary/reaction state per user per communication.
6. `Communication Interaction Entry` stores append-only interaction history.

## 2. Readiness Gate (Pre-Open)

Readiness checks are executed through `Program Offering.run_activity_preopen_readiness(...)` and API wrappers.

A booking window can open only when all linked sections are valid:

1. Section exists and is `Student Group` type `Activity`.
2. Schedule rows exist.
3. Schedule rows use bookable locations.
4. Materialization succeeds via `student_group_employee_booking.rebuild_employee_bookings_for_student_group(...)`.
5. Room conflicts are checked against `Location Booking` through `find_room_conflicts(...)`.
6. Instructor conflicts are checked against `Employee Booking` through `find_employee_conflicts(...)`.

## 3. Booking Lifecycle

Implemented states:

1. `Draft`
2. `Submitted`
3. `Waitlisted`
4. `Offered`
5. `Confirmed`
6. `Cancelled`
7. `Rejected`
8. `Expired`

Server-side invariants:

1. One active booking per `(student, program_offering)`.
2. Capacity checks are server-side and atomic (row-lock based).
3. Overlap checks are server-side before section assignment/final confirmation.
4. Idempotency key support (`Activity Booking.idempotency_key`).

## 4. Allocation Modes

Configured on `Program Offering.activity_allocation_mode`:

1. `First Come First Serve`: immediate confirm or waitlist.
2. `Lottery (Preference)`: batch allocation endpoint.
3. `Manual`: staff-driven assignment endpoints.

Waitlist controls:

1. `activity_waitlist_enabled`
2. `activity_auto_promote_waitlist`
3. `activity_waitlist_offer_hours`

## 5. Billing Integration

When `payment_required=1` and amount > 0:

1. Account holder is mandatory.
2. Billable offering is mandatory.
3. Draft invoice is created through `create_draft_tuition_invoice(...)`.

## 6. Communication Integration

Activity communications are created/fetched through internal Org Communication APIs only.

1. Audience scope still enforced by `check_audience_match(...)`.
2. Activity feeds can filter by explicit activity context fields.
3. Interaction history is append-only via `Communication Interaction Entry`.

## 7. Key API Endpoints

Implemented in `ifitwala_ed/api/activity_booking.py`:

1. `preview_activity_preopen_validation`
2. `open_activity_booking_window`
3. `close_activity_booking_window`
4. `submit_activity_booking`
5. `allocate_activity_bookings`
6. `confirm_activity_booking_offer`
7. `cancel_activity_booking`
8. `get_student_activity_bookings`
9. `get_activity_booking_logistics`
10. `get_activity_communications`
11. `post_activity_communication_entry`
