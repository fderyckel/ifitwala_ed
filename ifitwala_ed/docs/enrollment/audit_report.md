# Enrollment Execution Workflow Audit

## Status

Retrospective note. Preserved for historical design context only.

Use `03_enrollment_notes.md` for the current canonical architecture contract.

Code refs:
- `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/course_enrollment_tool/course_enrollment_tool.py`
- `ifitwala_ed/api/self_enrollment.py`

Test refs:
- `ifitwala_ed/admission/doctype/applicant_enrollment_plan/test_applicant_enrollment_plan.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`
- `ifitwala_ed/api/test_self_enrollment.py`

This audit captured an earlier point in the architecture evolution.

It remains useful for understanding:
- which boundaries were already correct
- which gaps were later filled
- which UX hardening gaps may still deserve follow-up

It is not the source of truth for current runtime behavior.

---

## 1. What The Audit Got Right

### 1.1 Request staging was the right backbone

The core conclusion still stands:

- `Program Enrollment Request` is the correct staging object
- validation and override logic belong there
- `Program Enrollment` must remain committed truth, not a draft buffer

### 1.2 Admissions needed a pre-student bridge

The audit correctly identified the need for a pre-student handoff layer.

That boundary now exists as:

- `Student Applicant`
- `Applicant Enrollment Plan`
- hydration into `Program Enrollment Request` only after promotion to `Student`

### 1.3 Direct administrative lanes are legitimate

The audit was also correct that bulk and direct staff tools are not bugs by default.

`Program Enrollment Tool` and `Course Enrollment Tool` are valid governed lanes when they preserve provenance and do not masquerade as request approval.

---

## 2. What Changed After The Audit

### 2.1 The request window is now explicit

At audit time, the architecture still described the need for a formal portal envelope.

That envelope now exists as `Program Offering Selection Window`.

It governs:

- one `Program Offering`
- one `Academic Year`
- one audience (`Student` or `Guardian`)
- one prepared draft `Program Enrollment Request` per student row

### 2.2 Self-enrollment is now a real portal lane

The audit described student-facing self-enrollment as future work.

That is no longer current.

The runtime now includes:

- student routes for course selection
- guardian routes for course selection
- window-scoped APIs for board, detail, save, and submit

The portal lane still respects the original architectural boundary:

- portal actors edit only the linked draft request
- staff still own review, override, approval, and materialization

### 2.3 Surface ownership is now clearer

The older audit spoke about “Front Desk” and “request-side UI” in a loose way.

The current contract is sharper:

- staff use Desk and workspace doctype surfaces
- students use student portal routes only
- guardians use guardian portal routes only

That distinction should now be treated as locked architecture, not a UX implementation detail.

---

## 3. Remaining Follow-Up Value

This retrospective still points at some useful product-quality questions.

### 3.1 `Program Enrollment Request` Desk console quality

The audit’s call for a stronger staff review console is still directionally useful.

The Desk surface should continue to optimize for:

- visible validation snapshots
- visible override rationale
- obvious next-action ownership
- visible materialization provenance

### 3.2 Program Enrollment Tool preview quality

The earlier recommendation for a server-backed dry run remains high leverage if not already completed to the required standard.

The tool should make it obvious:

- what enrollments will be created
- what request rows will be prepared
- what is blocked or skipped
- why each issue exists

### 3.3 Course Enrollment Tool exception handling

The audit’s concern about serial exception UX is still valid as a design smell.

Bulk staff tools should summarize conflicts in one actionable surface, not interrupt staff with fragmented warnings.

---

## 4. Retrospective Conclusion

This note should now be read as a historical checkpoint:

- it correctly defended the request-first architecture
- it correctly separated admissions, request, and direct-admin lanes
- it predated the explicit `Program Offering Selection Window` and shipped student/guardian self-enrollment portal surfaces

For current implementation and future change decisions, `03_enrollment_notes.md` is the canonical source.
