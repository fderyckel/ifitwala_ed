# Admission Visit Contract

Status: Active; backend workflow and staff SPA booking overlay implemented

Code refs:
- `ifitwala_ed/admission/doctype/admission_visit/*`
- `ifitwala_ed/admission/doctype/admission_visit_staff/*`
- `ifitwala_ed/admission/doctype/admission_visit_informed_user/*`
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/api/calendar_details.py`
- `ifitwala_ed/school_settings/doctype/school_event/school_event.py`
- `ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsVisitScheduleOverlay.vue`
- `ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsWorkspaceService.ts`
- `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsInbox.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`

Test refs:
- `ifitwala_ed/admission/doctype/admission_visit/test_admission_visit.py`

This contract defines admissions visits for private schools and colleges: campus tours, family visits, open-day follow-ups, student shadow-day visits, school visits, and college visits.

## 1. Product Model

`Admission Visit` is the first-class admissions record for a planned visit.

It is not a replacement for:

- `Inquiry`
- `Admission Conversation`
- `Student Applicant`
- `Applicant Interview`
- `Meeting`
- `School Event`

The admissions pipeline remains:

```text
Inquiry -> Student Applicant -> Promotion -> Student
```

Admission visits may happen before an applicant exists. A visit may be linked to:

- an `Admission Conversation`
- an `Inquiry`
- a `Student Applicant`
- direct organization/school context when a staff user is creating the CRM context at the same time

The record must remain organization-scoped. School is optional only when the CRM context is genuinely organization-level and no physical visit location is selected.

Admissions Inbox and Admissions Cockpit open the staff scheduling overlay from the selected row/card or contextual timeline action. The surface passes only context keys such as conversation, inquiry, student applicant, organization, school, and visitor label; the Admission Visit workflow endpoint resolves permissions, scope, conflicts, and CRM side effects.

## 2. Calendar Projection

`Admission Visit` owns the admissions workflow truth.

`School Event` is the calendar projection.

When an admission visit is scheduled, the backend creates or updates one linked `School Event` with:

- `reference_type = Admission Visit`
- `reference_name = <Admission Visit name>`
- `event_category = Admissions Event`
- `audience = Custom Users`
- participants equal to the visit lead and additional visit staff only

The linked `School Event` then uses existing scheduling projections:

- participants create `Employee Booking` rows
- meeting room creates a `Location Booking` row
- staff calendar feed reads the linked `School Event`

The staff calendar remains a read model. Free/busy checks must read `Employee Booking` and `Location Booking`, not merged calendar events.

## 3. Lead, Staff, Location, And Informing

`lead_user` is the person accountable for the visit and is always booked.

Rows in `Admission Visit Staff` are additional visit staff. They are also booked through the School Event participant table.

Rows in `Admission Visit Informed User` are informational only. They must not be projected as School Event participants, because informing a person should not block that person's calendar.

`building` is context for the visit area or campus zone. It does not create a room booking.

`location` is the meeting room or schedulable location. It creates a `Location Booking` through the linked `School Event`.

If a non-schedulable visible Location is submitted as the visit location, the workflow treats it as `building` / area context instead of a meeting room. The visit may still be scheduled, but no room free/busy check runs and no `Location Booking` is created for that non-bookable area.

## 4. CRM Integration

Scheduling from an Inquiry or Student Applicant finds or creates an `Admission Conversation` when one does not already exist.

On create, the visit records a CRM activity:

```text
Admission CRM Activity.activity_type = Booked Tour
```

When the visit status changes to `Completed`, the visit records:

```text
Admission CRM Activity.activity_type = Attended Tour
```

CRM activity is append-only and remains conversation-owned.

When the visit is marked `No Show`, the workflow records a conversation-owned `Admission CRM Activity` with `activity_type = Note` and `outcome = No Show`.

When the visit is cancelled, the workflow records a conversation-owned `Admission CRM Activity` with `activity_type = Note` and `outcome = Cancelled`.

## 5. Permissions And Visibility

Admissions CRM users manage visits only inside their organization/school scope.

Visit lead and additional visit staff may read a visit, but they do not gain write access unless they also have admissions CRM permission.

Informed users do not automatically gain full Admission Visit read access. They are recorded for notification/audit intent so future messaging can send a sanitized heads-up without exposing internal admissions notes.

The explicit inform action sends a sanitized realtime inbox notification to `Admission Visit Informed User` rows and appends a CRM note. It must not add those users to the School Event participant list and must not create staff or room bookings for them.

Admission-visit School Events are participant-only for staff calendar visibility. Broad school-event audience matching must not surface an admission visit to unrelated staff.

## 6. Endpoints

Current backend workflow endpoints:

```text
ifitwala_ed.admission.doctype.admission_visit.admission_visit.get_admission_visit_schedule_options
ifitwala_ed.admission.doctype.admission_visit.admission_visit.get_admission_visit_detail
ifitwala_ed.admission.doctype.admission_visit.admission_visit.suggest_admission_visit_slots
ifitwala_ed.admission.doctype.admission_visit.admission_visit.schedule_admission_visit
ifitwala_ed.admission.doctype.admission_visit.admission_visit.reschedule_admission_visit
ifitwala_ed.admission.doctype.admission_visit.admission_visit.cancel_admission_visit
ifitwala_ed.admission.doctype.admission_visit.admission_visit.mark_admission_visit_completed
ifitwala_ed.admission.doctype.admission_visit.admission_visit.mark_admission_visit_no_show
ifitwala_ed.admission.doctype.admission_visit.admission_visit.notify_admission_visit_informed_users
```

The SPA should use these workflow endpoints rather than assembling visits from generic DocType writes.

## 7. SPA Workflow

Admissions staff can open the visit scheduler from:

- Admissions Inbox rows when the row has conversation, inquiry, applicant, or organization context
- Admissions Cockpit applicant cards
- staff calendar clicks on a School Event whose `reference_type = Admission Visit`

The overlay must keep the staff user in context. It may schedule before an applicant exists, reschedule an existing visit, cancel the visit, mark completed/no-show, and send the explicit inform action.

## 8. Cancellation

Cancellation is a named workflow endpoint, not a free-form DocType write.

Cancelling an Admission Visit must:

- set `status = Cancelled`
- store `cancelled_at`, `cancelled_by`, and optional `cancellation_reason`
- remove the linked School Event projection
- delete Employee Booking and Location Booking rows derived from that School Event
- append the CRM cancellation note when a conversation exists
