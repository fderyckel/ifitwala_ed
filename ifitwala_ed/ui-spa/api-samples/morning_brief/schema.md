# Morning Brief schemas (DocTypes + backend code only)

Sources: `ifitwala_ed/api/morning_brief.py`, `ifitwala_ed/setup/doctype/communication_interaction/communication_interaction.py`, and DocType JSON files listed below. No live JSON samples were available in this workspace; add real responses later to validate.

## DocTypes referenced
- Org Communication: `setup/doctype/org_communication/org_communication.json`
- Org Communication Audience: `setup/doctype/org_communication_audience/org_communication_audience.json`
- Communication Interaction: `setup/doctype/communication_interaction/communication_interaction.json`
- Student Log: `students/doctype/student_log/student_log.json`
- Student Patient Visit: `health/doctype/student_patient_visit/student_patient_visit.json`
- Student Patient: `health/doctype/student_patient/student_patient.json`
- Student Applicant: `admission/doctype/student_applicant/student_applicant.json`
- Student: `students/doctype/student/student.json`
- Employee: `hr/doctype/employee/employee.json`
- Student Group Student: `schedule/doctype/student_group_student/student_group_student.json`
- Student Attendance: `students/doctype/student_attendance/student_attendance.json`
- Student Attendance Code: `school_settings/doctype/student_attendance_code/student_attendance_code.json`

## Endpoint: `ifitwala_ed.api.morning_brief.get_briefing_widgets`
- HTTP style: GET (`createResource.fetch`, auto)
- Behavior: returns a `widgets` object tailored to the signed-in user. `announcements` is always present (may be `[]`). All other keys are omitted entirely when the role/context check fails. Included lists are actual query results; no fabricated defaults.

### Root keys and presence rules
- `announcements`: `Announcement[]` (always; may be empty)
- `today_label`: string (formatted date label, e.g. `Monday, 06 January 2025`, site timezone)
- `staff_birthdays`: `StaffBirthday[]` (roles: Academic Staff, Employee, System Manager, Instructor)
- `clinic_volume`: `ClinicVolumePoint[]` (roles: Academic Admin, System Manager)
- `admissions_pulse`: `AdmissionsPulse` (roles: Academic Admin, System Manager)
- `critical_incidents`: `number` (roles: Academic Admin, System Manager)
- `grading_velocity`: `number` (roles: Instructor with at least one student group)
- `my_student_birthdays`: `StudentBirthday[]` (roles: Instructor with at least one student group)
- `student_logs`: `StudentLogItem[]` (roles: Academic Admin, System Manager, Grade Level Lead)
- `attendance_trend`: `AttendanceTrendPoint[]` (roles: Academic Admin, System Manager, Academic Assistant)
- `my_absent_students`: `AbsentStudent[]` (roles: Instructor with at least one student group)

### Announcement (Org Communication)
- `name`: string (DocType id)
- `title`: string
- `content`: string (HTML stripped from `message`)
- `type`: string (`communication_type`; options: Logistics | Reminder | Information | Policy Procedure | Celebration | Call to Action | Event Announcement | Class Announcement | Urgent | Alert)
- `priority`: string \| null (DocType options: Low | Normal | High | Critical; default Normal)
- `interaction_mode`: string (None | Staff Comments | Structured Feedback | Student Q&A)
- `allow_public_thread`: 0 \| 1
- `allow_private_notes`: 0 \| 1

### StaffBirthday (Employee)
- `name`: string (`employee_full_name`)
- `image`: string \| null (`employee_image` URL)
- `date_of_birth`: string (ISO date from `employee_date_of_birth`)

### ClinicVolumePoint (Student Patient Visit, last 3 days)
- `date`: string (formatted `dd-MMM` in site timezone)
- `count`: number

### AdmissionsPulse (Student Applicant, last 7 days)
- `total_new_weekly`: number
- `breakdown`: array of
  - `application_status`: string (Applied | Approved | Rejected | Admitted)
  - `count`: number

### Critical incidents count
- `critical_incidents`: number (open `Student Log` with `requires_follow_up=1` and `follow_up_status='Open'`, filtered by user’s school when present)

### MedicalContext (Student Patient joined to instructor groups)
- `first_name`: string
- `last_name`: string
- `medical_info`: string
- `allergies`: string \| null (Check stored as “0”/“1”; surfaced as string)
- `food_allergies`: string \| null
- Other allergy fields from `Student Patient` are omitted (not selected in SQL).

### Grading velocity
- `grading_velocity`: number (count of graded tasks past due; `0` when no groups)

### StudentBirthday (Student in instructor groups)
- `first_name`: string
- `last_name`: string
- `image`: string \| null (`student_image`)
- `date_of_birth`: string (ISO date)

### StudentLogItem (Student Log feed, last 48h)
- `name`: string (log id)
- `student_name`: string
- `student_image`: string \| null
- `log_type`: string (Link to `Student Log Type`)
- `date_display`: string (formatted `dd-MMM`)
- `snippet`: string (first ~120 chars of stripped `log`)
- `full_content`: string (HTML from `log`)
- `status_color`: string (`red` when follow-up open, `green` when completed, else `gray`)

### AttendanceTrendPoint (Student Attendance, last 30 days)
- `date`: string (`yyyy-mm-dd`)
- `count`: number (absences where `Student Attendance Code.count_as_present = 0`)

### AbsentStudent (today, instructor groups)
- `student_name`: string
- `attendance_code`: string (Link to `Student Attendance Code`)
- `student_group`: string
- `remark`: string \| null
- `student_image`: string \| null
- `status_color`: string \| null (from `Student Attendance Code.color`)

## Endpoint: `ifitwala_ed.api.morning_brief.get_critical_incidents_details`
- HTTP style: GET (`createResource.fetch`)
- Response: `StudentLogDetail[]` (open follow-up logs; filtered by user’s school when set)
  - `name`: string
  - `student_name`: string
  - `student_image`: string \| null
  - `log_type`: string
  - `date`: string (ISO date)
  - `log`: string (HTML/Text Editor)
  - `date_display`: string (formatted `dd-MMM`)
  - `snippet`: string (first ~100 chars of stripped `log`)

## Endpoint: `ifitwala_ed.api.morning_brief.get_clinic_visits_trend`
- HTTP style: GET (`createResource.fetch` via `HistoryDialog`)
- Request params:
  - `time_range`: string (`1M` default; `3M` | `6M` | `YTD`)
- Response:
  - `data`: `ClinicTrendPoint[]`
    - `date`: string (`yyyy-mm-dd`)
    - `count`: number
  - `school`: string (employee.school if set, else “All Schools”)
  - `range`: string (echo of `time_range`)

## Endpoint: `ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.get_org_comm_interaction_summary`
- HTTP style: POST (`createResource.submit`)
- Request body: `{ comm_names: string[] }` (JSON array or JSON string)
- Response: map keyed by org_communication name → `InteractionSummary`
  - `counts`: record of `intent_type` → number (intent defaults to `Comment` when null)
  - `self`: `InteractionSelf` \| null (current user’s interaction)

### InteractionSelf fields (Communication Interaction)
- `name`: string
- `org_communication`: string
- `user`: string
- `audience_type`: string (Staff | Student | Guardian | Community)
- `surface`: string (Desk | Morning Brief | Portal Feed | Student Portal | Guardian Portal | Other)
- `school`: string \| null
- `program`: string \| null
- `student_group`: string \| null
- `reaction_code`: string \| null (like | thank | heart | smile | applause | question | other)
- `intent_type`: string \| null (Comment | Acknowledged | Appreciated | Support | Positive | Celebration | Question | Concern | Other)
- `note`: string \| null (<= 300 chars)
- `visibility`: string \| null (Public to audience | Private to school | Hidden)
- `is_teacher_reply`: 0 \| 1
- `is_pinned`: 0 \| 1
- `is_resolved`: 0 \| 1
- `creation`: string (timestamp)
- `modified`: string (timestamp)
- Other standard Frappe doc fields from `SELECT *` (e.g. `owner`, `modified_by`, `docstatus`, `idx`) may be present.

## Endpoint: `ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.get_communication_thread`
- HTTP style: GET (`createResource.fetch`)
- Request params:
  - `org_communication`: string (required)
  - `limit_start`: number (default 0)
  - `limit_page_length`: number (default 20)
- Response: `InteractionThreadRow[]` ordered by `is_pinned` desc, then `creation` asc; rows filtered by interaction_mode and visibility rules in Python.
  - `name`: string
  - `user`: string
  - `full_name`: string \| null (from `tabUser`)
  - `audience_type`: string \| null
  - `intent_type`: string \| null
  - `reaction_code`: string \| null
  - `note`: string \| null
  - `visibility`: string \| null
  - `is_teacher_reply`: 0 \| 1
  - `is_pinned`: 0 \| 1
  - `is_resolved`: 0 \| 1
  - `creation`: string (timestamp)
  - `modified`: string (timestamp)

## Endpoint: `ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.upsert_communication_interaction`
- HTTP style: POST (`call`)
- Request body:
  - `org_communication`: string (required)
  - `intent_type`: string \| null (Comment | Acknowledged | Appreciated | Support | Positive | Celebration | Question | Concern | Other)
  - `reaction_code`: string \| null (like | thank | heart | smile | applause | question | other)
  - `note`: string \| null (<= 300 chars; required when `intent_type` = Question)
  - `surface`: string \| null (Desk | Morning Brief | Portal Feed | Student Portal | Guardian Portal | Other)
  - `student_group`: string \| null
  - `program`: string \| null
  - `school`: string \| null
- Response: the saved `Communication Interaction` document (all DocType fields plus standard Frappe metadata such as `doctype`, `name`, `owner`, `creation`, `modified`, `docstatus`, `idx`).
