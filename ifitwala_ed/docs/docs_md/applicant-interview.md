---
title: "Applicant Interview: Structured Interview Evidence"
slug: applicant-interview
category: Admission
doc_order: 8
summary: "Record interview evidence, participants, and outcomes with audit trail comments pushed to the Student Applicant timeline."
---

# Applicant Interview: Structured Interview Evidence

`Applicant Interview` captures interview evidence as part of admissions review. It formalizes interview context and leaves an audit trail on the applicant record.

## What It Captures

- Interview date and mode (`In Person`, `Online`, `Phone`)
- Interview type (`Family`, `Student`, `Joint`)
- Confidentiality level
- Outcome impression
- Notes

## Child Table (Included in Parent)

`interviewers` uses child table **Applicant Interviewer**:

- `interviewer` -> `User`

Controller logic remains on the parent doctype; child table controller is intentionally empty.

## Where It Is Used Across the ERP

- [**Student Applicant**](/docs/en/student-applicant/):
  - interview count contributes to readiness snapshot
  - create/update events add audit comments on applicant timeline
- Admission workspace: direct access card under Student Applicant operations.

## Technical Notes (IT)

- **DocType**: `Applicant Interview` (`ifitwala_ed/admission/doctype/applicant_interview/`)
- **Autoname**: `hash`
- **Desk surface**:
  - parent doctype form in `ifitwala_ed/admission/doctype/applicant_interview/`
  - child table `Applicant Interviewer` embedded in parent
- **Student Applicant integration**:
  - readiness snapshot uses `has_required_interviews()`
  - create/update posts audit comments onto applicant timeline
- **Key hooks**:
  - `validate`: permission + applicant-state guard
  - `after_insert`: audit comment "Interview recorded"
  - `on_update`: audit comment "Interview updated"
- **Readiness nuance**:
  - `StudentApplicant.has_required_interviews()` tracks count and snapshot section
  - current `ready` boolean blocks on policies/documents/health, not interview count

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Officer` | Yes | Yes | Yes | Yes | Full Desk access |

Runtime controller rule:
- Only staff roles can manage records (`Admission` roles + `Academic Admin` + `System Manager`).
- Records are blocked when linked applicant is in terminal states (`Rejected`, `Promoted`).

## Reporting

- No dedicated Script/Query Report currently declares this doctype as `ref_doctype`.

## Related Docs

- [**Student Applicant**](/docs/en/student-applicant/) - readiness and decision flow
- [**Applicant Health Profile**](/docs/en/applicant-health-profile/) - health review component
- [**Applicant Document**](/docs/en/applicant-document/) - file review component
