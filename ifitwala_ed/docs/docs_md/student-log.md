---
title: "Student Log: Track Observations and Follow-Ups"
slug: student-log
category: Students
doc_order: 2
version: "1.0.5"
last_change_date: "2026-04-25"
summary: "Document student observations, incidents, and concerns with built-in follow-up workflows. Keep everyone informed while maintaining appropriate privacy controls."
seo_title: "Student Log: Track Observations and Follow-Ups"
seo_description: "Learn how to use Student Logs to document observations, track follow-ups, and maintain a complete record of student support interactions in Ifitwala Ed."
---

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

---

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

---

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

---

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

---

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

---

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

---

## Permissions: Who Can Do What

Student Logs contain sensitive information, so access is carefully controlled:

| Role | What They Can Do | Typical User |
|------|------------------|--------------|
| **Academic Admin** | Full access including all follow-up actions | Principal, Vice Principal |
| **Counselor** | Create, edit, submit logs; manage follow-ups | School Counselor |
| **Learning Support** | Create and manage logs for supported students | Learning Support Specialist |
| **Curriculum Coordinator** | View and create logs across programs | Academic Coordinator |
| **Instructor** | Create logs for their students | Teachers |
| **Accreditation Visitor** | Read-only access for reviews | External Auditors |
| **Student** | View logs marked visible to them | The student (via portal) |
| **Guardian** | View logs marked visible to guardians | Parents (via portal) |

### Visibility Rules

- **Default visibility is off** for both students and guardians until staff chooses otherwise
- **Authors** can always see logs they created
- **Assignees** can see logs assigned to them for follow-up
- **Staff** see logs for students in their school scope
- **Students/Guardians** only see logs explicitly marked visible to them

### Who Can Complete or Reopen?

- **Complete:** Author, Academic Admin, or current assignee
- **Reopen:** Author or Academic Admin only
- **Reassign:** Author, Academic Admin, current assignee, or someone with the required role

---

## Best Practices

### Writing Good Logs

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Be specific and factual—quote the student when relevant.</Do>
  <Do>Record observations promptly while memory is fresh.</Do>
  <Do>Separate observation from interpretation.</Do>
  <Do>Use follow-up workflow for anything requiring action.</Do>
  <Do>Set appropriate visibility—share praise, protect privacy.</Do>
  <Dont>Use judgmental language or labels.</Dont>
  <Dont>Include irrelevant personal family information.</Dont>
  <Dont>Create logs for minor, one-time incidents without context.</Dont>
  <Dont>Forget to update follow-up status when work is done.</Dont>
</DoDont>

### Using Follow-Up Effectively

- **Be specific** in next steps—"Schedule meeting" is better than "Follow up"
- **Assign promptly**—don't leave logs unassigned in the queue
- **Add follow-up notes** as work progresses—don't wait until completion
- **Keep follow-ups lightweight**—use Student Referral for deeper coordinated cases
- **Complete logs** when done—don't let resolved items linger
- **Reopen if needed**—new information can emerge after closure

### Managing Visibility

- **Visible to student:** Progress notes, positive recognition, goal tracking
- **Visible to guardians:** Academic updates, behavioral patterns, intervention plans
- **Internal only:** Sensitive incidents, confidential assessments, other students' information

### For Multi-Campus Schools

- Logs are scoped to the school where they were created
- Academic context (Program, Academic Year) helps with cross-campus tracking
- Assignees must be within the same school branch

---

## Common Questions

**Q: Can I edit a log after submitting it?**
A: Yes, you can cancel and amend if no submitted follow-up work has started yet. Once a submitted follow-up exists, core fields become locked to preserve the record. Add clarification notes instead.

**Q: Who gets notified when I create a log?**
A: The assigned follow-up person gets a ToDo notification. If visible to guardians, they may see it on their portal (depending on your school's notification settings).

**Q: Can I attach files to a log?**
A: Yes, use the Follow Up entries to attach documents, images, or other evidence relevant to the case.

**Q: What happens to old logs?**
A: They remain in the student's permanent record. Follow-up status may auto-complete after inactivity, but the log content is preserved forever for historical context.

**Q: Can students see logs about behavioral incidents?**
A: Only if you explicitly check "Visible to Student." Most schools keep behavioral logs internal while sharing academic progress notes.

**Q: How do I run reports or analytics on student logs?**
A: Use the **Student Log Report** for formatted documentation and export (Students > Reports > Student Logs). For visual analytics and charts, use the **Student Log Dashboard** in the staff SPA at `/staff/analytics/student-logs`. See the dedicated sections above for details on both tools.

**Q: Can I print or export logs for case files?**
A: Yes! The Student Log Report includes a professionally formatted print template with color-coded status badges, threaded follow-ups, and filter summaries—perfect for case files, meetings, or accreditation evidence. Export to Excel for data analysis or PDF for documentation.

**Q: Can I create logs in bulk?**
A: Yes, Student Log supports Data Import for bulk creation (e.g., importing historical records). Use with care—logs are part of the official student record.

---

## Student Log Report

The **Student Logs Report** is a comprehensive script report that gives you a consolidated view of all student logs and their follow-ups—perfect for generating documentation for meetings, accreditation reviews, or case file exports.

### Accessing the Report

Navigate to **Students > Reports > Student Logs**. The report loads with a default date range (last 30 days) but you can customize filters to see exactly what you need.

### Available Filters

| Filter | What It Does | Example Use |
|--------|--------------|-------------|
| **From / To Date** | Date range for log creation | Last semester, specific month |
| **Student** | Filter to one specific student | Case file for a single student |
| **Program** | Filter by academic program | Elementary vs. High School logs |
| **School** | Filter by school (includes descendants) | Campus-specific reports |
| **Academic Year** | Filter by school year | 2024-2025 academic year only |
| **Log Type** | Filter by category | Only behavioral observations |
| **Follow-up Status** | Open, In Progress, or Completed | See what's still pending |
| **Requires Follow-up** | Yes/No filter | Find all unresolved cases |
| **Author** | Who created the log | My own logs for review |
| **Follow-up Author** | Who added follow-up notes | Cases handled by a counselor |

### Report Output

The report displays logs in a hierarchical format:

- **Parent rows** show the main Student Log with:
  - Log ID and student name
  - Date, time, and log type
  - Program, school, and academic year
  - Follow-up status with color coding
  - Visibility indicators (👤 student, 👪 guardians)
  - Log content snippet

- **Child rows** (indented) show each Follow Up with:
  - Follow-up date and author
  - Response content
  - Response time metrics

<Callout type="tip" title="Grouped view">
Logs with multiple follow-ups are grouped together under a single parent row, making it easy to see the complete history of a case at a glance.
</Callout>

### Printing and Exporting

The report includes a professionally formatted print template with:
- **Color-coded status badges** — Red (Open), Orange (In Progress), Green (Completed)
- **Status-accented card borders** — Each log card shows its status with a colored left border
- **Student and context information** — Clear metadata about program, school, academic year
- **Follow-up threading** — Indented follow-ups show the conversation flow
- **Filter summary** — Print header shows which filters were applied

**Export options:**
- **Print** — Generate PDF for case files or meetings
- **Export to Excel** — Download for further analysis or data manipulation

<Callout type="info" title="Why Ifitwala Ed is different">
Unlike basic list reports, the Student Logs Report presents data in a narrative format that reads like a case file. The print template is designed for professional documentation—perfect for counselor case notes, admin reviews, or accreditation evidence.
</Callout>

---

## Student Log Dashboard (Analytics)

The **Student Log Dashboard** provides visual analytics and insights into student support activity across your school or organization. Access it through the staff SPA at `/staff/analytics/student-logs`.

### Who Can Access

Dashboard access is restricted to specific roles:
- Academic Admin
- Pastoral Lead
- Counselor
- Learning Support
- Curriculum Coordinator
- Accreditation Visitor
- System Manager

### Dashboard Widgets

The dashboard presents multiple visualizations:

| Widget | What It Shows | Why It Matters |
|--------|---------------|----------------|
| **Logs by Type** | Bar chart of log types | Identify patterns (e.g., many academic concerns in one grade) |
| **Logs by Cohort** | Distribution across graduating classes | Track which year groups need more support |
| **Logs by Program** | Breakdown by academic program | Compare support needs across divisions |
| **Logs by Author** | Who's creating logs | Ensure consistent documentation practices |
| **Next Step Types** | What actions are being planned | Identify common intervention paths |
| **Incidents Over Time** | Timeline of log creation | Spot trends and seasonal patterns |
| **Open Follow-ups** | Count of pending tasks | Monitor workload and response times |

### Interactive Features

**Filtering:**
- Filter by date range, academic year, school, program, or author
- Academic Year takes precedence—if you select an AY, date range adjusts automatically
- School filter includes descendant schools (parent campus shows all satellites)

**Student Search:**
- Search for specific students to see their complete log history
- Recent logs appear with follow-up summaries and response time metrics
- Click through to view the full log detail

**Real-time Updates:**
- Filter meta (schools, programs, authors) updates based on your permission scope
- You only see data for schools and students within your organizational scope

### Response Time Metrics

For logs with follow-ups, the dashboard calculates and displays:
- **Response time in minutes** — How long from log creation to first follow-up
- **Human-readable labels** — "2h 30m", "1d 4h", etc.
- **Follow-up counts** — How many actions each log generated

<Callout type="success" title="Use case: Pastoral care review">
A Pastoral Lead can filter to their school, select the current academic year, and see:
- Which cohorts have the most behavioral logs
- Whether follow-ups are happening promptly
- Which types of incidents are trending upward
- Who on their team is handling the most cases
</Callout>

### Dashboard vs. Report: When to Use Which

| Use Case | Dashboard | Report |
|----------|-----------|--------|
| **Quick overview** | ✅ Charts show patterns at a glance | ❌ Requires reading rows |
| **Trend analysis** | ✅ Time series and distributions | ⚠️ Can export to analyze |
| **Single student case** | ✅ Student search with timeline | ✅ Filter to one student |
| **Printed documentation** | ❌ Screen-only | ✅ Professional print template |
| **Accreditation evidence** | ⚠️ Screenshots possible | ✅ Formatted PDF export |
| **Bulk data export** | ❌ Limited export | ✅ Excel export with all fields |

---

## Evidence Attachments

Staff with the right Student Log permissions can attach governed evidence, such as a photo or document, from the Student Log form. Evidence is private by default.

To share evidence on portals, both the log and the evidence row must be marked visible for that audience:

- Student portal: `Visible to Student` on the log and on the evidence row
- Guardian portal: `Visible to Guardians` on the log and on the evidence row

Evidence appears in the Student portal log detail, Guardian Monitoring log cards, and the Focus follow-up overlay for staff. Private files open through governed preview/open links rather than raw storage paths.

---

<RelatedDocs
  slugs="student,student-log-next-step,student-log-type,student-log-follow-up"
  title="Continue With Student Support Docs"
/>

---

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

### Permission Matrix

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
