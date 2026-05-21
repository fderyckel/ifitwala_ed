# Admission Visit Contract

Status: Backend/domain workflow implemented; dedicated SPA booking overlay planned

Code refs:
- `ifitwala_ed/admission/doctype/admission_visit/*`
- `ifitwala_ed/admission/doctype/admission_visit_staff/*`
- `ifitwala_ed/admission/doctype/admission_visit_informed_user/*`
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/api/calendar_details.py`
- `ifitwala_ed/school_settings/doctype/school_event/school_event.py`

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

## 5. Permissions And Visibility

Admissions CRM users manage visits only inside their organization/school scope.

Visit lead and additional visit staff may read a visit, but they do not gain write access unless they also have admissions CRM permission.

Informed users do not automatically gain full Admission Visit read access. They are recorded for notification/audit intent so future messaging can send a sanitized heads-up without exposing internal admissions notes.

Admission-visit School Events are participant-only for staff calendar visibility. Broad school-event audience matching must not surface an admission visit to unrelated staff.

## 6. Endpoints

Current backend workflow endpoints:

```text
ifitwala_ed.admission.doctype.admission_visit.admission_visit.get_admission_visit_schedule_options
ifitwala_ed.admission.doctype.admission_visit.admission_visit.suggest_admission_visit_slots
ifitwala_ed.admission.doctype.admission_visit.admission_visit.schedule_admission_visit
```

The SPA should use these workflow endpoints rather than assembling visits from generic DocType writes.

## 7. Current Limits

Cancellation is not a free-form status in the first implementation because cancelling a projected School Event must also resolve staff and room booking behavior consistently. A future cancel action should be a named workflow endpoint that updates the visit, the calendar projection, bookings, and CRM activity together.

Dedicated Inbox and calendar overlays are planned. Until then, the backend contract is the source of truth and the linked School Event provides calendar presence.
