Ifitwala_Ed Concurrency & Scalability Proposal (Revised)

This strategy prepares Ifitwala_Ed for 1000+ simultaneous users across students, staff, and guardians.

Guiding principles

Requests are for reads + small writes. Anything heavy must leave the request.

Only compute once. Cache + reuse; invalidate deliberately.

Fail safe, recover fast. Idempotent jobs, durable events, clear monitoring.

Keep the DB breathing. Prefer fewer queries, fewer rows locked, fewer commits.

0) Capacity plan first (cross-cutting)

What’s missing: how many web workers, background workers, Redis capacity, and DB connections you can actually sustain.

Action items

Set (and document) a baseline deployment target:

web: gunicorn workers = CPU cores × 2 (or similar), request timeout, keep-alive.

RQ: separate queues (short, default, long) with explicit worker counts.

Establish guardrails: per-queue max concurrent jobs, global max enqueued jobs per job-type.

Put rate limiting on high-risk endpoints (e.g., analytics dashboards + mutations).

Add a “capacity risk” section for: Redis memory limits, DB max connections, queue backlog thresholds.

1) Move heavy computations to background jobs (RQ) — with idempotency

You got right: don’t compute term reports synchronously.
Risks you should address: repeated clicks, race conditions, and job duplication under load.

Improvements

Return 202 Accepted with a job id + a minimal state record (ReportCycleJob or similar) so the UI can show progress safely.

Enforce idempotency:

A “job key” per reporting cycle; reject if already running unless explicit override.

Consider an outbox-like pattern (log event → enqueue) to avoid lost jobs.

Ensure jobs run with correct context:

explicit site name

explicit user (if required) via frappe.set_user inside job

no reliance on frappe.local.request

2) Asynchronous email & notification pipelines — plus retries and DLQ

You got right: don’t block on SMTP.

Improvements

Use explicit retry policy (exponential backoff) on transient errors.

Create a dead-letter queue for failures that exceed retries (notification + dashboard).

Make email jobs safe to re-run:

store a unique “send id” and de-duplicate

log send status in a table and surface to admins

3) Decouple “next steps” in record submissions — split correctness vs enrichment

You got right: keep minimal sync work.

Improvements

Define clearly: what is required for correctness vs what is enrichment (SLA calc, follow-up assignment, analytics counters).

Keep synchronous state transitions monotonic:

Store logs as “Submitted” immediately.

Later job calculates SLA and updates fields; if it fails, the log stays usable.

Track job failure for follow-up tasks (prevent silent data drift).

4) Implement a Domain Event Bus — make events durable and idempotent

You got right: stop chaining logic directly.

Critical gaps

In-memory “fire-and-forget” events lose data under crashes.

Handlers must be idempotent or you’ll duplicate child records.

Improvements

Use a durable event mechanism:

simplest in Frappe: a table Domain Event (status: pending/processing/done) + dispatcher job

or a queue message with a transactional outbox (preferred if you’re already restructuring).

Enforce handler idempotency by event id and handler name.

Define event versioning (event schema in code with explicit fields).

5) Eliminate N+1 API design via aggregated payloads — but don’t create mega-endpoints

You got right: fewer HTTP requests; aggregated context endpoints.

Critical tradeoff: aggregation can become mega-endpoints that pull far too much and reload too often.

Improvements

Do “Context endpoints” but keep them bounded:

page context ≤ 250 ms target, ≤ 1MB JSON payload

Optimize server queries:

use frappe.get_all(..., pluck=...) for lists

limit columns

add and audit indexes on foreign keys used in filters

Encourage “query batching” where possible:

e.g., one call returns the necessary IDs and counts; avoid full object hydration unless needed.

Concrete “rules” (keep them explicit)

Rule A: ≤ 5 API calls to render a view.

**Rule B: Context endpoints must document their dependency invalidation triggers.

Rule C: Don’t aggregate unrelated domains just to reduce call count.

6) Realtime event broadcasting (Socket.IO) — plus fallback + auth

You got right: publish_realtime is the right mechanism for post-job signals.

Improvements

Define a fallback strategy (polling) for environments where websockets are blocked (common in schools/enterprise).

Avoid too many channels; use hierarchical channel naming and one “job-status” stream per user.

Ensure the worker knows which user to broadcast to (no accidental leaks to session user in jobs not tied to the right user context).

7) Aggressive cache utilization for reads — only with invalidation rules

You got right: cache hot config lookups.

Critical gap: cache without invalidation is a correctness risk and a debugging nightmare at scale.

Improvements

Document caching policy per key:

TTL OR explicit invalidation hook

Prefer safe cached entry points:

frappe.get_cached_value

frappe.get_cached_doc

Invalidate on DocType updates that matter (e.g., Program Enrollment changes should invalidate scope caches).

Instrument cache hit rate so you can prove value.

8) Batch database mutations — but watch locking and foreign keys

You got right: batched inserts/mutations reduce overhead.

Critical gap: bulk operations can still lock too much at once.

Improvements

Chunk writes with measurable batch size (50/100/500 depending on row size + lock behavior).

Avoid inside-loop commits; one commit per batch unless you must keep latency ultra-low.

For heavy table updates, consider:

selective updates

reorder: update minimal columns first if contention on large rows

Add explicit transaction boundaries and lock-minimizing query patterns (where possible).

9) Task queuing for complex DocType lifecycles — ensure UX + consistency

You got right: asynchronous “processing” for complex lifecycles.

Improvements

Provide end-user transparency:

job status, started/finished timestamps, error messages with a friendly code

Keep state transitions consistent:

if job fails, state is “Processing (Failed)” with retry option

Ensure atomic child-record creation per applicant (idempotent with applicant id).

10) Refactor SLA and cron scheduling — add “dispatcher” + backpressure

You got right: cron should enqueue batches, not process everything.

Status update (2026-03-12): the daily Student Log / HR leave scheduler hooks now dispatch chunk workers instead of processing the full sweep inline.

Critical gap: if cron enqueues too much too fast, you’ll backpressure Redis and workers and latency will spike anyway.

Improvements

Add a dispatcher job that:

chunks IDs

enforces max outstanding chunks

publishes progress metrics

Add worker-level constraints:

queue length alarm thresholds

slow job detection and alerting

Ensure chunk handlers tolerate partial failures and continue with retries.

11) Page payload versioning & cache stamps — align with HTTP semantics

You got right: ETag-like strategy cuts massive reads.

Improvements

Use standard semantics where possible:

ETag header + If-None-Match + 304 Not Modified

OR Last-Modified + If-Modified-Since

Define the hash properly:

stable version bytes; include relevant “last updated” timestamps and a “schema version”

Store payload in IndexedDB with eviction strategy.

12) Observability + governance (missing but essential)

What’s missing: a way to know if any of this works, and to stop regressions.

Minimum setup

Metrics: request latency by endpoint, queue depth, job duration, cache hit rate, DB query count.

Error budgets and SLOs for key flows (attendance ledger load, submit log, term report generation).

“Performance gate” in CI:

simple runtime checks for query count and cold-start payload size for top 10 pages.

Improved structure for the repo doc

In the ifitwala_ed repo, make this a living document:

Short summary (1 page)

Design decisions (ADR-style)

Rules checklist (API calls, caching, job idempotency)

Implementation plan with milestones and acceptance criteria

Runbook for failure scenarios (Redis down, worker overload, event queue growth)

If you want, tell me your current deployment shape (workers/queues/mariadb config) and the slowest endpoints, and I’ll tailor the capacity plan + batch sizes to your real constraints.




Below are 5 concrete “opportunity targets” per point (first 5 points in your proposal) that are consistent with what’s in the repo and the existing architectural docs you’ve already got.

Point 1 — Move heavy computations to background jobs (RQ)

Term reporting: ifitwala_ed.assessment.term_reporting.process_reports (already referenced in your docs) — enforce “submit request → enqueue job id → 202 response”.

Attendance ingestion: any endpoint that iterates student-by-student inserting/updating StudentAttendance/attendance logs in a loop should become “validate + enqueue chunk” (this is a common pattern in your attendance tool).

Meeting/booking rebuilds: student-group schedule rebuild + employee bookings (your schedule docs emphasize conflict checks and rebuilds). Rebuild operations should be enqueue-only with chunking.

Bulk “sync” buttons in Desk controllers (e.g., “regenerate focus items”, “recompute analytics”): stop doing in-request recomputations; enqueue with job-key so repeated clicks don’t double-load.

High-cardinality reports (long-running analytics SQL / number-card pipelines): convert to “start report” → background job writes report rows → UI polls via job id or realtime.

Point 2 — Asynchronous email & notification pipelines

Admissions portal invite / applicant identity upgrades: any action that sends “create account / confirm email” should enqueue sendmail + audit log; avoid SMTP in request lifecycle.

Recommendation intake emails: the intake flow should write to an email queue (frappe’s Email Queue) through short jobs, not direct send.

Inquiry follow-up and assignment notifications: when an inquiry is assigned/reassigned, split “DB mutation” vs “notify assignee” (enqueue the notification).

Student log follow-up notifications: “Follow-up person assigned” should enqueue email/bell notification with idempotent tracking to avoid duplicate sends.

SLA breach escalations: any SLA sweep (hourly/daily) must enqueue escalation notifications so one slow mail server doesn’t stall the scheduler.

Point 3 — Decouple “next steps” in record submissions

submit_student_log: do minimal validation + insert; move follow-up assignment/SLA calc/comment timelines/ToDo creation into a background “log_finalize” job.

Applicant submission: “submit application” should move heavy child creation (new records, ledger steps, re-routing) into a queued job; the submit request only marks it “Submitted/Processing”.

Attendance submission from portal: move “rebuild missing rows / enforce defaults / create analytics breadcrumbs” into queued jobs; keep synchronous path to “persist codes”.

Gradebook/task bulk updates: bulk update endpoints should accept a payload, validate quickly, queue the batch update, return job id.

Schedule edits (student group changes that cascade): execute the “validate + accept edit” fast, and queue downstream rebuilds (bookings, derived calendars, conflicts recalculation).

Point 4 — Implement a Domain Event Bus

Student log submitted event: create DomainEvent(StudentLogSubmitted, log_name) → handlers: follow-ups, dashboards, analytics counters, notifications.

Applicant lifecycle events: StudentApplicantSubmitted, StudentApplicantDecision, StudentApplicantWithdrawal—each fires events; handlers are decoupled (portal user handling, email, audit dashboards).

Inquiry lifecycle events: InquiryAssigned, InquiryContacted, InquiryClosed → handlers update metrics and notifications separately from the main mutation.

Attendance finalized event: AttendanceLedgerCommitted(group,date) → handlers are analytics refresh + risk model update (if you have those dashboards).

Policy sign-off / signature completed event: PolicySignatureCaptured(user,policy) → handlers update signature analytics + notification surfacing.

Point 5 — Eliminate N+1 API design via page payload aggregation

Use your own “aggregated context endpoint” rule for the worst offenders:

AttendanceLedger.vue: aggregate context into one get_attendance_ledger_context() endpoint (your report already calls this out).

Implemented read-model contract:

fetch_attendance_ledger_context(school, program, academic_year, term, student_group) → schools, programs, academic_years, terms, student_groups, resolved defaults.

AttendanceAnalytics.vue: aggregate into get_attendance_analytics_context() instead of scattered calls (context + groups + dashboard payload).

InquiryAnalytics.vue: aggregate get_inquiry_analytics_context() (types/users/years/orgs/schools in one).

RoomUtilization.vue: aggregate dashboard payload to avoid “freeRooms + timeUtil + capacity + analyticsAccess” as separate calls.

Admissions Cockpit / heavy SPA views: add a cockpit-context endpoint that returns all dependent dropdown lookups in one call, then reserve Promise.all for truly independent payloads (not tightly coupled primitives).

StudentAttendanceTool.vue should stay bounded, not monolithic:

fetch_attendance_tool_bootstrap(school, program, student_group) → schools, programs, codes, groups, resolved defaults

fetch_attendance_tool_group_context(student_group) → weekend_days, meeting_dates, recorded_dates, default_selected_date

fetch_attendance_tool_roster_context(student_group, attendance_date) → roster, previous_status, existing_attendance, blocks



Plan (short)

Standardize one contract for Job submission / status / realtime.

Apply that contract to the 25 targets (5 per proposal point).

Standardize one contract for Domain Event Bus and apply to the 5 event targets.

Standard job contract (use everywhere)

Submit endpoint response (whitelisted API)

returns HTTP 202

body: { job_id, queue, submitted_at }

optional status_url pointing to a dedicated status method

Status endpoint response

get_job_status(job_id) returns { job_id, status, progress, result }

status: queued/running/finished/failed

progress: 0-100 (optional)

result: minimal payload (or None)

Realtime channel naming

per-user: job:${user}:${job_id}

per-concern: term_reports_generated:${reporting_cycle}

message schema: { job_id, status, progress, result }

Worker side behavior

set user/site context explicitly inside jobs

publish realtime on progress milestones + on completion

idempotency: job key derived from critical inputs; reject duplicate enqueues unless explicitly allowed

Point 1 targets → contract application (5)

Term reporting (process_reports)

Submit: enqueue_term_reporting(reporting_cycle)

Queue: long

Realtime: term_reports_generated:${reporting_cycle}

Attendance ingestion

Submit: attendance_batch_submit(group, date, payload) → enqueue chunks

Queue: default or long depending on payload size

Realtime: attendance_submit:${group}:${date}

Meeting/booking rebuilds (schedule rebuild)

Submit: enqueue_schedule_rebuild(group_or_school, scope)

Queue: long

Realtime: schedule_rebuild:${scope}

Bulk sync buttons (focus items / analytics recompute)

Submit: enqueue_focus_regeneration(scope)

Queue: default

Realtime: focus_regeneration:${scope}

Heavy report generation

Submit: enqueue_dashboard_materialization(dashboard_name, filters)

Queue: default

Realtime: dashboard_materialized:${dashboard_name}

Point 2 targets → contract application (5)

Admissions portal invite

Submit: enqueue_admissions_invite(applicant)

Queue: short

Realtime: mail:${applicant} (or just job:${user}:${job_id})

Recommendation intake email

Submit: enqueue_recommendation_email(recommendation_id)

Queue: short

Realtime: recommendation:${recommendation_id}

Inquiry follow-up notifications

Submit: enqueue_inquiry_notification(inquiry_id, action)

Queue: short

Realtime: inquiry_notification:${inquiry_id}

Student log follow-up notification

Submit: enqueue_student_log_notification(log_name)

Queue: short

Realtime: student_log_notify:${log_name}

SLA breach escalations

Submit: cron schedules dispatcher → enqueue send_sla_escalation_batch(chunk)

Queue: short

Realtime: optional progress on dispatcher job only

Point 3 targets → contract application (5)

submit_student_log

Sync path: validate + insert only

Enqueue: finalize_student_log(log_name)

Queue: default

Realtime: student_log_finalize:${log_name}

Applicant submission

Sync path: state→Processing

Enqueue: process_applicant_submission(applicant_name)

Queue: long

Realtime: applicant_submission:${applicant_name}

Attendance submission from portal

Sync path: persist codes quickly

Enqueue: finalize_attendance_postprocessing(group,date)

Queue: default

Realtime: attendance_finalize:${group}:${date}

Gradebook/task bulk updates

Sync path: accept payload + enqueue

Enqueue: process_task_bulk_update(task_id, payload)

Queue: long if large

Realtime: task_bulk_update:${task_id}

Schedule edits cascading rebuild

Sync path: accept edit + enqueue cascades

Enqueue: cascade_schedule_changes(scope)

Queue: long

Realtime: schedule_cascade:${scope}

Point 4 targets → domain events contract (5)
Standard domain event contract

Event shape

DomainEvent(event_name, key, payload, version)

stored durably (table/doc)

status transitions: pending → processing → done/failed

handler idempotency enforced via (event_id, handler_name)

Dispatcher

cron/worker picks pending events

for each handler: enqueue run_domain_event_handler(event_id, handler_name)

handlers publish realtime minimally (optional), log results

Realtime channels

domain_event:${event_name}:${key} (only if valuable)

Event targets

StudentLogSubmitted

payload: log_name

handlers: analytics counters, follow-ups, notifications, dashboards

StudentApplicantSubmitted

payload: applicant_name

StudentApplicantDecision

payload: applicant_name, decision

InquiryAssigned/Contacted/Closed

payload: inquiry_id, action

PolicySignatureCaptured

payload: policy_id, user

Point 5 targets → job + aggregated endpoint contract (5)

For each of these SPA views, create one context endpoint returning a single payload + cache_stamp, and allow “realtime or 304 cache” refresh semantics:

AttendanceLedger.vue

AttendanceAnalytics.vue

InquiryAnalytics.vue

RoomUtilization.vue

Admissions Cockpit

Context endpoint response

context object plus

cache_stamp (hash over relevant “last updated” markers + schema version)

Stamp validation

client sends cache_stamp

server returns 304 if stamp matches, else full payload + new stamp

Realtime refresh

completion of related jobs publishes:

publish_realtime("invalidate", {"view": "AttendanceLedger"})

client maps view to cached entry and reloads only that context
