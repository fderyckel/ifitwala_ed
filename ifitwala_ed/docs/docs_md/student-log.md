---
title: "Student Log: Track Observations and Follow-Ups"
slug: student-log
category: Students
doc_order: 2
version: "1.0.7"
last_change_date: "2026-04-25"
summary: "Document student observations, incidents, and concerns with built-in follow-up workflows. Keep everyone informed while maintaining appropriate privacy controls."
seo_title: "Student Log: Track Observations and Follow-Ups"
seo_description: "Learn how to use Student Logs to document observations, track follow-ups, and maintain a complete record of student support interactions in Ifitwala Ed."

## What is a Student Log?

A **Student Log** is your digital record for anything worth noting about a student. Think of it as a structured journal entry that connects observations to action.

Use Student Logs to document:
- **Behavioral observations** — both positive moments and concerns
- **Academic progress notes** — interventions, accommodations, achievements
- **Incident reports** — what happened, when, and what was done
- **Support conversations** — check-ins with students or families
- **Referrals** — connecting students to counselors, learning support, or health services

<Callout type="info" title="Why Ifitwala Ed is different">
Unlike scattered sticky notes or disconnected spreadsheets, Ifitwala Ed's Student Logs create a complete, searchable history that follows the student. Logs can trigger follow-up tasks, notify the right people, and even be shared with families—if you choose. It's student support coordination that actually coordinates.
</Callout>

## Why Student Logs Matter

### 1. **Everything in One Place**
No more hunting through emails, notebooks, or different systems. Every observation, incident, and follow-up lives in the student's permanent record—organized, searchable, and accessible to authorized staff.

### 2. **Built-In Follow-Up Workflow**
When something needs action, Student Logs don't just sit there. They become tasks assigned to the right people with due dates. Track progress from first observation to final resolution.

### 3. **Appropriate Transparency**
Control who sees what. Some logs are internal-only (sensitive incidents). Others can be visible to students and guardians (progress updates, positive recognition). You decide per log.

### 4. **Context-Rich Documentation**
Logs automatically capture academic context—program, academic year, school—so you know exactly what was happening in the student's journey when the observation was made.

### 5. **Accountability Without Micromanagement**
Follow-up assignments create clear ownership. Status tracking shows what's open, in progress, or completed. Auto-close ensures stale items don't linger forever.

## Creating a Student Log

<Steps title="Documenting a Student Observation">
  <Step title="Navigate to Student Logs">
    Go to **Students > Student Log** and click **New**.
  </Step>
  <Step title="Select the Student">
    Choose the student from the dropdown. Their name and photo will appear automatically.
  </Step>
  <Step title="Set Date and Time">
    Defaults to today, but adjust if documenting a past event. Time is optional but helpful for precise incident documentation.
  </Step>
  <Step title="Choose Log Type">
    Select the category: Academic Concern, Behavioral Observation, Positive Recognition, Incident Report, etc. Your school configures these types.
  </Step>
  <Step title="Write Your Log">
    Use the text editor to document what happened. Be factual, specific, and objective. Include who was involved, what was observed, and any immediate actions taken.
  </Step>
  <Step title="Set Visibility">
    Decide if this log should be visible to the student and/or guardians. Academic progress notes might be shared; sensitive incidents usually are not.
  </Step>
  <Step title="Submit">
    Click **Save** and then **Submit** to create the record. Once submitted, it becomes part of the student's official record.
  </Step>
</Steps>

<Callout type="tip" title="Context auto-fills">
When creating a new log, if the student has an active program enrollment, the system automatically fills in their current Program, Academic Year, Program Offering, and School. You can override these if documenting something from a previous term.
</Callout>

## When Follow-Up is Needed

Not every observation needs follow-up. But when it does, Student Logs become action items.

### Marking a Log for Follow-Up

When creating or editing a log:

1. Check **"Requires Follow Up"**
2. Select a **Next Step** (configured by your school—e.g., "Schedule parent meeting", "Refer to counselor")
3. Choose the **Follow-up Role** (who should handle this)
4. Assign a specific **Follow-up Person** (required before submit)

<Callout type="success" title="What happens automatically">
When you submit a log requiring follow-up:
- A ToDo task is created for the assigned person
- Due date follows the selected **Next Step** policy when configured, otherwise your school's default
- Status becomes "Open"
- The assignee gets notified
</Callout>

### Follow-Up Status Lifecycle

| Status | What It Means | Who Can Change It |
|--------|---------------|-------------------|
| **Open** | Task created, waiting for action | System-managed |
| **In Progress** | Follow-up work has started | System-managed when the first submitted follow-up is added |
| **Completed** | Resolution achieved | Author, Academic Admin, or current assignee |

### Adding Follow-Up Notes

As work progresses, the current assignee can add quick **Student Log Follow Up** entries to record:
- Conversations with the student or family
- Interventions attempted
- Outcomes and immediate next steps

If another staff member needs to add context without taking over the assignment, use **Add Clarification** on the Student Log.

For deeper, multi-party support work, move the case into **Student Referral** rather than turning the log into a long-running case file.

Each follow-up is timestamped and attributed, creating a complete timeline.

### Reassigning Follow-Up

Life happens—people go on leave or need help. To reassign:
1. Open the Student Log
2. Use the **Reassign** action
3. Select the new person (must have the required role)

<Callout type="warning" title="Reassignment rules">
Only the author, Academic Admin, current assignee, or someone with the follow-up role can reassign a log. Completed logs cannot be reassigned—they must be reopened first.
</Callout>

Reassigning a log starts a new follow-up cycle for the new assignee. The previous follow-up history stays on the log for context.

### Completing a Log

When the follow-up work is done:
1. Open the Student Log
2. Use the **Complete** action
3. The status changes to "Completed"
4. Any open ToDos are closed

Need to reopen? Authors and Academic Admins can reopen completed logs if new information emerges.

### Auto-Close for Stale Items

Logs "In Progress" that haven't been updated in a while are automatically marked "Completed" by the system using the selected **Next Step** policy when available, otherwise the school's default follow-up window. This prevents abandoned tasks from lingering in queues forever.

## Student Log Fields Explained

| Field | What It's For | Tips |
|-------|---------------|------|
| **Student** | Who this log is about | Required; links to their full record |
| **Date / Time** | When the observation occurred | Defaults to now; adjust for past events |
| **Log Type** | Category of observation | Configured by your school (Academic, Behavioral, Incident, etc.) |
| **Log** | The actual content | Be specific and objective; include facts, quotes, actions taken |
| **Visible to Student** | Can the student see this? | Usually yes for positive notes, no for sensitive matters |
| **Visible to Guardians** | Can parents see this? | Consider family dynamics and student privacy |
| **Requires Follow Up** | Does this need action? | Check to enable follow-up workflow |
| **Next Step** | What should happen next | Pre-configured options from your school |
| **Follow-up Role** | Required role for assignee | Defaults to `Academic Staff` when the selected Next Step has no associated role |
| **Follow-up Person** | Who's responsible | Set before submit or through explicit reassign/reopen workflow; ordinary saves do not repair task drift |
| **Follow-up Status** | Current state | Read-only; system manages this |
| **Program / Academic Year** | Academic context | Auto-fills from enrollment; override if needed |
| **School** | Which school this relates to | Auto-fills; important for multi-campus reporting |

## Where You'll Use Student Logs

### For Teachers
- Document academic concerns before they become crises
- Record positive behaviors and achievements
- Track interventions and their effectiveness
- Communicate with support staff about at-risk students

### For Counselors
- Maintain case notes with professional confidentiality
- Track ongoing student support cases
- Coordinate with teachers and families
- Document mandated reporting situations

### For Learning Support
- Record IEP accommodations and their implementation
- Track progress on learning goals
- Document assessments and referrals
- Coordinate with classroom teachers

### For Administrators
- Monitor patterns across classrooms or grade levels
- Track response to intervention (RTI) effectiveness
- Ensure compliance with follow-up requirements
- Generate reports for accreditation or compliance

### For Families
When logs are marked visible, guardians can:
- See academic progress updates
- Read positive recognition notes
- Understand classroom observations
- Stay informed about support interventions

<Callout type="info" title="Student and guardian portal access">
Students and guardians only see logs explicitly marked visible to them. This creates transparency for progress and praise while maintaining privacy for sensitive matters.
</Callout>

## Permission Matrix

| Role | Read | Write | Create | Delete | Submit | Cancel | Amend | Notes |
|------|------|-------|--------|--------|--------|--------|-------|-------|
| `System Manager` | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Full access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Full academic access |
| `Counselor` | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Student support access |
| `Learning Support` | Yes | Yes | Yes | Yes | Yes | Yes | No | SpEd/Learning support |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes | Yes | Yes | No | Program-level access |
| `Instructor` | Yes | Yes | Yes | Yes | Yes | Yes | No | Own students |
| `Accreditation Visitor` | Yes | No | No | No | No | No | No | Read-only for audits |
| `Student` | Yes* | No | No | No | No | No | No | Visible logs only (portal) |
| `Guardian` | Yes* | No | No | No | No | No | No | Visible logs only (portal) |

*Read access is scoped to logs explicitly marked visible and within school scope.

## Related Docs

<RelatedDocs
  slugs="student,student-log-next-step,student-log-type,student-log-follow-up"
  title="Continue With Student Support Docs"
/>

## Technical Notes (IT)

- **DocType**: `Student Log` — Located in Students module
- **Autoname**: `SLOG-.YY.-.MM.-.####` format (auto-generated)
- **Submittable**: Yes (must be submitted to create follow-up tasks)
- **Amendable**: Yes (unless follow-ups exist)
- **Follow-up Status**: Computed field (Open → In Progress → Completed)
- **Visibility Defaults**: `Visible to Student` and `Visible to Guardians` default to off
- **Evidence Attachments**: governed by Ifitwala Drive workflow `student_log.evidence_attachment`; parent log visibility and row-level visibility must both allow portal display
- **Scheduler**: Daily job auto-completes stale "In Progress" logs using the selected next-step policy or the school default
- **Academic context**: new logs seed missing `program`, `academic_year`, `program_offering`, and `school` from the student's current active Program Enrollment; existing sites backfill historical missing context through the one-shot patch `ifitwala_ed.patches.backfill_student_log_delivery_context`
- **Assignment lifecycle**: follow-up `ToDo` ownership is created on submit and updated through explicit reassign/reopen workflow only; existing sites backfill unambiguous assignment drift through the one-shot patch `ifitwala_ed.patches.backfill_student_log_follow_up_assignments`
- **Legacy remediation**: existing sites backfill missing `follow_up_role` values on follow-up logs through the one-shot patch `ifitwala_ed.patches.backfill_student_log_follow_up_roles`
