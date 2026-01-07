Curriculum ↔ Tasks (for humans + coding agents)

This is the “truth document” of the system. Read this as doctrine.
Last updated: 2026-01-07

Curriculum in Ifitwala_ed: first principles

Curriculum is not one thing. It has three lenses:

Planned curriculum
What we intend students to experience.

Taught curriculum
What actually happened in real time.

Assessed curriculum
What we formally judged and recorded.

Most systems collapse these. Ifitwala_ed explicitly separates them.

Planned curriculum (Curriculum module)

Planned curriculum is roster-agnostic and time-agnostic.

It is modeled as:

Learning Unit

Lesson

Lesson Activity (pedagogical atom)

These objects:

define intent

define sequence

define alignment to standards

do not imply delivery or assessment

They answer:

“What should be taught, and why?”

Taught curriculum (Lesson Instance)

Teaching is contextual and temporal.

A Lesson Instance represents:

“This learning experience happened with this group, at this time (or asynchronously).”

Lesson Instance:

links planned curriculum to real teaching

may be scheduled or asynchronous

may or may not involve tasks

exists even if nothing is assessed

Key principle
The system observes teaching. It does not prescribe it.

Lesson Instance creation is:

automatic when possible

implicit when tasks are delivered

never required from teachers

Assessed curriculum (Tasks & Outcomes)

Assessment is a mode, not an identity.

Assessment can exist with or without a digital submission.
Offline evidence is captured as a **Submission stub** when `requires_submission = 1`, so Outcome and Contribution remain consistent and auditable.

Task (definition)

A Task is a learning artifact:

instructions

resources

potential to collect evidence

potential to assess

Task may be aligned to:

course

learning unit

lesson

lesson activity

But a Task is not tied to:

a class

a date

a year

This preserves reuse and pedagogical flexibility.

Task Delivery (teaching event)

Task Delivery represents:

“This task was used with this group, in this context.”

It defines:

who (student group)

when (dates)

how (Assign / Collect / Assess)

Task Delivery may soft-link to a Lesson Instance:

best-effort

optional

never blocking

This allows:

async learning

ad hoc teaching

teacher autonomy

Task Outcome / Submission / Contribution

These represent assessed evidence.

Task Outcome: the official student-level fact record

Task Submission: versioned evidence

Task Contribution: professional judgment (grading, feedback)

**Canonical statement:** A Task Outcome always stores official results per criterion. Task totals are optional and only computed when the delivery strategy allows it.

Assessment can exist:

with or without a lesson

with or without submission

with or without moderation

The system supports:

formative assessment

summative assessment

ungraded work

compliance-driven moderation

Why this architecture is superior

Teachers retain agency

Students’ learning journeys are coherent

Async and sync learning coexist

Gradebook is clean and performant

Analytics distinguish:

planned vs taught vs assessed

Curriculum teams gain insight without policing teachers

This is learning-centered, not assignment-centered.

Framework variability

MYP: criteria remain separate per task; no task total; term reporting computes criterion term grades.

DP / Traditional: criteria may sum to a task total; task total maps to grade.

Framework logic does not live in controllers. It lives in delivery-level scoring strategy + reporting cycle aggregation policy.

---

Architecture lock notes

- Publishing is per Outcome (student x delivery). Curriculum relationships remain unchanged; publication is a visibility gate layered on top of Outcome truth.
