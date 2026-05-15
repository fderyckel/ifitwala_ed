<!-- ifitwala_ed/docs/testing/06_eca_activity_manual_qa_checklist.md -->
# ECA Activity Workflow Manual QA Checklist (Non-Canonical)

Status: Active manual QA note
Scope: physical end-to-end verification of the implemented ECA activity workflow
Canonical impact: none; behavior authority remains `ifitwala_ed/docs/enrollment/06_activity_booking_architecture.md`
Code refs: `ifitwala_ed/eca/doctype/activity/activity.json`, `ifitwala_ed/eca/doctype/activity_booking/activity_booking.json`, `ifitwala_ed/eca/doctype/activity_booking/activity_booking.py`, `ifitwala_ed/eca/doctype/activity_booking_settings/activity_booking_settings.json`, `ifitwala_ed/eca/doctype/program_offering_activity_section/program_offering_activity_section.json`, `ifitwala_ed/schedule/doctype/program_offering/program_offering.json`, `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`, `ifitwala_ed/api/activity_booking.py`, `ifitwala_ed/ui-spa/src/pages/student/StudentActivities.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`, `ifitwala_ed/ui-spa/src/components/activity/ActivityOfferingCard.vue`, `ifitwala_ed/ui-spa/src/components/activity/ActivityCommunicationPanel.vue`
Test refs: `ifitwala_ed/api/test_activity_booking.py`, `ifitwala_ed/eca/doctype/activity_booking/test_activity_booking.py`

## 1. Purpose

Use this checklist to physically verify the current runtime workflow around activities in the ECA module.

This is a manual execution note, not a new product contract.

Important runtime note:
- Student and guardian booking flows are surfaced in the SPA routes `/student/activities` and `/guardian/activities`.
- Operator transitions such as readiness preview, opening/closing the booking window, and batch allocation are implemented server-side in `ifitwala_ed/api/activity_booking.py`.
- I did not find dedicated ECA Desk form buttons for those operator actions in the current repo, so this checklist treats that lane as Desk/API-assisted verification rather than a polished Desk UI workflow.

## 2. Test Preconditions

Before starting, prepare one deterministic test setup and confirm each item:

- [ ] One active `Activity` exists for the target `Program` and `School`, with `status = 1`.
- [ ] The `Activity` has enough visible context to verify portal rendering:
  - descriptions
  - logistics location label
  - pickup and drop-off instructions
  - optional map URL
  - optional gallery link
- [ ] One `Program Offering` exists with:
  - `activity_booking_enabled = 1`
  - at least one active `Program Offering Activity Section`
  - valid `start_date` and `end_date`
  - explicit booking-role settings for student, guardian, and staff
- [ ] Each linked activity section points to a real `Student Group` where `group_based_on = Activity`.
- [ ] Each activity section has schedule rows and bookable locations so readiness can pass.
- [ ] At least one student matches the offering age policy and can log in through the student portal.
- [ ] At least one guardian is linked to one or more eligible students and can log in through the guardian portal.
- [ ] If paid booking must be tested, the setup includes:
  - `activity_payment_required = 1`
  - `activity_fee_amount > 0`
  - a valid `activity_billable_offering`
  - an `Account Holder` on the student
- [ ] `Activity Booking Settings` are reviewed before testing so expected portal behavior is known:
  - max choices
  - waitlist position visibility
  - guardian/student cancellation mode
  - paid-booking label mode
  - offer banner threshold

## 3. Activity Setup And Readiness

- [ ] In Desk, confirm the `Activity` is linked to the intended `Program` through the `program_allowed` child table.
- [ ] Confirm the `Activity` school matches the `Program Offering` school expected in the portal board.
- [ ] Confirm each `Program Offering Activity Section` has the expected:
  - student group
  - optional capacity override
  - priority tier
  - waitlist allowance
- [ ] Run the pre-open readiness check through the server/API-assisted lane and verify it fails clearly when a section is broken.
- [ ] Fix the broken prerequisite and rerun readiness until the report is successful.
- [ ] Move the `Program Offering.activity_booking_status` through `Draft` to `Ready` only after readiness passes.
- [ ] Verify invalid configurations are blocked server-side:
  - no active section
  - duplicate student group row
  - negative age or waitlist values
  - close datetime earlier than open datetime

## 4. Booking Window Visibility

- [ ] Before the offering is `Ready` or `Open`, verify the student and guardian boards do not present it as currently bookable.
- [ ] Open the booking window through the operator lane and verify:
  - `activity_booking_status = Open`
  - the board shows the offering with the correct booking window text
  - section capacity and next slot information appear
- [ ] If `activity_booking_open_from` is in the future, verify the portal explains that booking is not open yet.
- [ ] If `activity_booking_open_to` is in the past, verify submission is blocked and the portal no longer treats the offering as open now.
- [ ] Close the booking window and verify new submissions are blocked without silently hiding existing bookings.

## 5. Student Self-Booking Flow

- [ ] Log in as an eligible student and open `/student/activities`.
- [ ] Confirm the page loads without error and shows:
  - open-now KPI
  - active booking KPI
  - available activities
  - communication center
- [ ] Verify the student sees only their own bookings and not another student context.
- [ ] If student self-booking is disabled on the offering, verify the page explains that booking is not currently open for student self-booking.
- [ ] If student self-booking is allowed, submit a ranked booking with one or more section choices.
- [ ] Verify submission creates exactly one `Activity Booking` for that student and offering.
- [ ] Verify duplicate active booking submission for the same student/offering is rejected with a clear duplicate-booking message.
- [ ] Verify age-ineligible students are blocked with a clear age rule message.
- [ ] Verify the resulting status and label are correct for the allocation mode:
  - `Submitted` with `Pending Review`
  - `Waitlisted` with `On Waitlist`
  - `Offered` with `Spot Available`
  - `Confirmed` with `Booked`

## 6. Guardian Family Booking Flow

- [ ] Log in as a guardian and open `/guardian/activities`.
- [ ] Verify the family board shows only linked students.
- [ ] Verify no unrelated student can be accessed through request parameters or UI state.
- [ ] Confirm the guardian sees:
  - family summary
  - per-student existing bookings
  - multi-child booking controls
- [ ] If guardian booking is disabled on the offering, verify the page explains that guardian booking is not currently open.
- [ ] If guardian booking is allowed, submit one batch for multiple selected children.
- [ ] Verify each child returns an individual success or failure result.
- [ ] Confirm one failing child does not silently hide successful rows for other children.
- [ ] Verify duplicate active booking protection also applies in the guardian batch flow.

## 7. Allocation Modes And Operator Lane

- [ ] `First Come First Serve`: verify an available seat can confirm immediately or place the student on the waitlist when capacity is full.
- [ ] `Lottery (Preference)`: verify submissions stay pending until the operator runs the allocation lane, then review allocated, waitlisted, and rejected outcomes.
- [ ] `Manual`: verify submissions remain review-driven until the operator performs assignment/offer actions.
- [ ] For operator-managed actions, verify the API-assisted lane works for:
  - readiness preview
  - open booking window
  - close booking window
  - allocate activity bookings
- [ ] Verify operator actions do not bypass server-side overlap, capacity, or payment requirements.

## 8. Waitlist, Offer, Expiry, And Cancellation

- [ ] Fill a section to capacity and verify the next eligible request becomes `Waitlisted` when waitlist is enabled.
- [ ] Verify waitlist position is shown or hidden according to `Activity Booking Settings`.
- [ ] Promote a waitlisted booking to an offer and verify:
  - status becomes `Offered`
  - `offer_expires_on` is set
  - the portal shows the offer state clearly
- [ ] Confirm an offered booking as the student or guardian and verify:
  - status becomes `Confirmed`
  - waitlist state is updated
  - section assignment remains present
- [ ] Let an offer expire and verify the user receives a clear expiry error and the booking moves to `Expired`.
- [ ] Cancel a `Confirmed` booking as student or guardian when self-cancellation is allowed and verify:
  - status becomes `Cancelled`
  - cancellation reason is stored when supplied
  - a promoted waitlist row appears when auto-promotion is enabled
- [ ] When self-cancellation is disabled or first session start has passed, verify the user gets a clear blocked-action message instead of silent failure.

## 9. Billing, Logistics, And Activity Context

- [ ] For a paid offering, confirm the booking creates a draft invoice on confirmation.
- [ ] Verify the portal shows the expected paid-booking label behavior:
  - `Confirmed + Draft Invoice`
  - or `Payment Pending`
- [ ] Verify the invoice link opens the expected Desk sales invoice route.
- [ ] Verify the offering card shows:
  - activity description
  - logistics location label
  - pickup instructions
  - drop-off instructions
  - age policy
  - role access summary
- [ ] Verify section cards show next-slot timing and remaining capacity where available.
- [ ] Verify logistics returned by `get_activity_booking_logistics` match the allocated section and upcoming slot.

## 10. Communication Flow

- [ ] From the student portal, open embedded activity updates for one offering.
- [ ] From the guardian portal, open embedded activity updates for one offering.
- [ ] Verify the communication center loads the same activity feed for the selected offering.
- [ ] Confirm a booking-linked communication is created for major workflow events that should emit updates:
  - submission
  - offer
  - confirmation
- [ ] Verify comments and reactions work when enabled for the audience.
- [ ] Verify the UI shows an explicit message when there are no updates yet.

## 11. Permission And Failure Checks

- [ ] Student users can read and act only on their own `Activity Booking` rows.
- [ ] Guardian users can read and act only on rows for linked students.
- [ ] Staff/admin users can manage the workflow without creating sibling-school leakage in the tested tenant setup.
- [ ] Booking attempts fail clearly for:
  - closed window
  - actor not allowed
  - age mismatch
  - duplicate active booking
  - missing account holder on paid confirmation
  - overlapping confirmed/offered activity slot
- [ ] Every blocked path shows an actionable message; no silent failure, empty response, or misleading success toast appears.

## 12. Exit Criteria

Do not mark the workflow physically validated until all of the following are true:

- [ ] Happy-path student booking is verified.
- [ ] Happy-path guardian multi-child booking is verified.
- [ ] At least one operator-managed allocation path is verified.
- [ ] Waitlist promotion or offer expiry is verified.
- [ ] Paid-booking behavior is verified when payment is enabled.
- [ ] Communications render correctly from at least one portal surface.
- [ ] Permission boundaries and blocked-action messages are verified.

If any item fails, log:
- exact role used
- exact record names used
- step where behavior diverged
- whether the failure is UI-only, API-only, or cross-layer
