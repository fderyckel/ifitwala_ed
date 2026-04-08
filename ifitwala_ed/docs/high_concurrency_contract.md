# Ifitwala_Ed — High Concurrency, Caching, Async, and Nested Scope Governance Note

**Status:** Active
**Audience:** Human engineers and coding agents
**Applies to:** Ifitwala_Ed on Frappe v16+ with MariaDB, Redis, RQ workers, Desk, SPA, scheduler workloads, and multi-school NestedSet scope logic

---

## 0. Purpose

This note defines the canonical engineering posture for **Ifitwala_Ed under high concurrency**.

It is not a generic scalability note and it is not a generic Frappe note.

It exists to prevent the usual failure modes:

* request paths doing too much work
* dashboards recomputing expensive joins on every load
* ad-hoc caching with no invalidation ownership
* raw SQL writes silently drifting caches
* queueing used as a bandage for bad domain boundaries
* school-scope and permission leaks under caching
* subtree expansion repeated everywhere in inconsistent ways
* coding agents introducing performance regressions because the repo lacks one hard contract

This note is meant to be used by both:

* **human developers**
* **coding agents** working against the repo constitution and project rules

It is aligned with existing project direction:

* Frappe stays the framework base
* MariaDB stays the transactional database
* DB adapters are **not** introduced now
* adapters are appropriate for cache, async, files, notifications, and external boundaries
* school-tree / org-tree / location-tree scope is a core architecture concern, not a utility detail

This also aligns with the current code and docs posture in the repo:

* rich DocType lifecycle logic in `Student` and `Student Log`
* performance-oriented SQL and scoped APIs in student log/report/dashboard surfaces
* strong governance around files, admissions, reporting, delivery, and scheduling contracts

---

## 1. Strategic Position

### 1.1 What we are doing

We are scaling **within Frappe**, not around it.

The winning strategy for Ifitwala_Ed is:

* keep MariaDB as transactional truth
* make request paths smaller
* move side-effects off the request path
* cache only where the scope and invalidation story are clear
* build read models for hot dashboards and summary-heavy surfaces
* centralize nested-scope resolution and reuse it everywhere
* keep query count, lock duration, and fan-out bounded

### 1.2 What we are not doing

We are **not** doing these things now:

* replacing MariaDB
* introducing generic DB repository adapters everywhere
* rewriting Frappe lifecycle into a different framework model
* turning the app into microservices
* hiding bad query design behind Redis
* hiding correctness-critical work behind background jobs

### 1.3 Core architectural sentence

> **Truth is written synchronously and minimally; projections, summaries, notifications, and heavy recomputations are handled asynchronously or via read models; scope and cache correctness are explicit contracts.**

---

## 2. Core Principles

### 2.1 Requests are for reads and small writes

A request should:

* validate
* enforce permissions
* enforce invariants
* write canonical truth
* return quickly

A request should not:

* rebuild large projections
* fan out many side-effects
* run long loops over many records
* send network-bound notifications inline
* compute large analytics payloads from scratch if a read model exists

### 2.2 Only compute once

If the same expensive derived structure is reused:

* cache it
* snapshot it
* materialize it
* or compute it asynchronously and reuse it

Do not recompute the same scope, schedule, or dashboard structure on every request.

### 2.3 Correctness beats cache hit rate

A missed cache is acceptable.
A stale permission-sensitive cache is a defect.

### 2.4 Queueing does not remove work

Async is not magic. It only moves work.
If you enqueue bad work, you get a different bottleneck.

### 2.5 Scope logic is architecture, not UI sugar

School-tree, org-tree, location-tree, and inherited nearest-ancestor resolution are first-class contracts in Ifitwala_Ed. They must be:

* centralized
* testable
* cacheable
* permission-safe
* applied before aggregation and before UI shaping

---

## 3. System Boundaries

### 3.1 Authoritative write truth

MariaDB + Frappe DocTypes remain the source of truth for:

* canonical workflow state
* legal/audit state
* core relationships
* identity and scope ownership
* authoritative educational records

### 3.2 Shared infrastructure

Redis is used for:

* shared cache
* RQ queueing
* coordination/locking where appropriate
* bounded cross-worker state

### 3.3 Async infrastructure

RQ workers handle:

* background jobs
* domain event handlers
* deferred fan-out
* projection refreshes
* scheduled chunk processing

### 3.4 UI surfaces

The SPA and Desk should read from:

* bounded context endpoints
* read-model endpoints
* cached summary endpoints
* job-status endpoints

not from chains of tiny uncoordinated calls.

---

## 4. Synchronous Truth vs Deferred Enrichment

This section is non-negotiable.

## 4.1 Synchronous truth

Must complete before returning success:

* permission checks
* scope checks
* required validation
* invariant enforcement
* canonical insert/update
* core workflow transition
* any state other code will immediately rely on

### Examples

For `Student Log`, this includes at least the truth needed for the row to exist validly and be interpreted safely by later logic. The current `Student Log` lifecycle already treats follow-up state, assignment semantics, and immutability rules as core lifecycle concerns, not decorative add-ons.

For `Student`, creation-source invariants are canonical and must remain synchronous.

## 4.2 Deferred enrichment

May happen after the request:

* notifications
* email
* dashboard refresh
* analytics counters
* read-model refresh
* non-critical comments/timeline fan-out
* heavy recomputation
* derivative file processing
* search indexing

## 4.3 Rule

> **No user-visible success response may depend on deferred work unless the document state explicitly communicates “Processing” and the workflow contract allows it.**

---

## 5. Endpoint Taxonomy

Every API endpoint should fit one of these categories.

## 5.1 Mutation endpoints

Purpose:

* validate
* write truth
* possibly enqueue

Rules:

* small response
* no large summary payloads
* no long loops
* return quickly
* may return `202 Accepted` if asynchronous completion is the contract

## 5.2 Context endpoints

Purpose:

* bootstrap a page with options/defaults/filter context
* keep API call count low

Rules:

* bounded payload
* bounded query count
* cache-friendly
* explicit dependency/invalidation documentation
* no unrelated domains bundled together just to reduce call count

## 5.3 Read-model endpoints

Purpose:

* dashboards
* summary boards
* analytics surfaces
* pre-shaped list payloads

Rules:

* prefer cached or materialized sources
* pagination by default where needed
* avoid live recomputation from transactional truth if the surface is hot and repeated

## 5.4 Job/status endpoints

Purpose:

* enqueue background work
* report job status/progress/result

Rules:

* stable job contract
* idempotent submit semantics
* explicit status model
* clear failure visibility

---

## 6. Job Contract and Async Rules

## 6.1 Standard job submission contract

For long or deferred work, the submit endpoint should return:

* `HTTP 202`
* `{ job_id, queue, submitted_at }`
* optional `status_url`
* optional domain object reference

## 6.2 Standard job status contract

`get_job_status(job_id)` returns:

* `job_id`
* `status` = queued | running | finished | failed
* `progress` = optional 0–100
* `result` = minimal payload only

## 6.3 Job context rules

Workers must not rely on request context.
Jobs must set explicitly:

* site context
* user context if needed
* deterministic payload inputs

## 6.4 Idempotency contract

Every queued job must define:

* dedup key
* duplicate enqueue behavior
* safe retry behavior
* replay safety

### Examples

* one term-report generation per reporting cycle
* one finalization job per Student Log lifecycle version
* one applicant-processing job per applicant + workflow state
* one projection-refresh job per view + scope + version

## 6.5 Rule

> **A background job must be safe to run twice, or it must be rejected from duplicate enqueue. There is no third acceptable state.**

---

## 7. Domain Event Bus Governance

## 7.1 Why it exists

We do not want one mutation endpoint to chain:

* notifications
* analytics
* dashboards
* read-model refresh
* assignment fan-out
* downstream materialization

That coupling kills concurrency and maintainability.

## 7.2 Event taxonomy

Use three distinct kinds of events:

### Domain events

Business truth changed.
Examples:

* `StudentLogSubmitted`
* `StudentApplicantSubmitted`
* `InquiryAssigned`
* `AttendanceLedgerCommitted`
* `PolicySignatureCaptured`

### Projection events

A read model or dashboard projection should refresh.
Examples:

* `StudentLogProjectionRefreshRequested`
* `AttendanceAnalyticsRefreshRequested`

### Notification events

A user-facing communication should happen.
Examples:

* `StudentLogNotificationRequested`
* `AdmissionsInviteNotificationRequested`

Do not overload one event to mean all three.

## 7.3 Durability

Domain events must be durable, not in-memory fire-and-forget.

Acceptable pattern:

* `Domain Event` table / DocType
* status: pending / processing / done / failed
* dispatcher enqueues handler jobs

## 7.4 Handler contract

Every handler must define:

* handler name
* idempotency rule
* whether it can write authoritative truth or only projections/notifications
* retry policy
* event schema version

## 7.5 Rule

> **If an event matters for correctness or auditability, it must be durably recorded before fan-out begins.**

---

## 8. Caching Strategy for Frappe v16

This section locks the caching posture for Ifitwala_Ed.

## 8.1 Strategic shift in v16+

The old instinct was:

> “If it is hot, put it in Redis.”

That is not enough anymore, and often wrong as the first move.

Frappe v16 direction is:

* request/transaction-local caching for repeated small reads
* Redis for shared cross-worker reuse
* reduced unnecessary Redis trips on ultra-hot framework reads
* coordinated invalidation, not blind permanence

So the correct question is:

> **Which layer should cache this read, for how long, and who owns invalidation?**

## 8.2 The 4-layer cache model

### Layer A — Request / transaction cache

Use first.

Typical tools/behaviors:

* repeated `get_value(..., cache=True)`
* repeated `count(..., cache=True)` in request scope
* framework-local value cache

Use for:

* repeated settings checks in one request
* repeated existence checks in one flow
* repeated row reads inside one API or job

Do not treat this as a shared cache.

### Layer B — Cached documents / settings

Use `frappe.get_cached_doc` for slow-changing settings/reference docs.

Use for:

* `Org Setting`
* School-level configuration
* Admission Settings
* stable policy/config Singles
* stable schedule configuration
* portal/shell settings

Not for:

* high-churn transactional rows
* domains often mutated by raw SQL
* user-varying permission-sensitive read models

### Layer C — Shared Redis cache

Use for deterministic, shared, cross-worker reuse.

Use for:

* school tree expansions
* instructor teaching-scope sets
* schedule resolution maps
* stable dashboard snapshots
* reusable permission-input maps
* policy/config bundles by scope

Do not use Redis as a dumping ground.

### Layer D — Framework-managed hot local cache

Frappe itself is optimizing some hot reads locally with coordinated invalidation.

Project rule remains:

* no random app-level global dict caches
* no uncontrolled in-process state
* only bounded, centrally-owned local caches if correctness is explicit

---

## 9. What to Cache in Ifitwala_Ed

Cache **derived stable views**, not mutable raw truth.

## 9.1 Best cache targets

### School / organization hierarchy maps

Examples:

* descendants of school X
* effective school scope
* nearest ancestor with configuration

### Schedule resolution maps

Examples:

* block lookup by `(school, academic_year, rotation_day, block_number)`
* student-group schedule projections
* instructor occupied slots
* location occupied slots

### Permission input maps

Examples:

* students taught by instructor X
* school scope list for user X
* allowed student groups for instructor X

### Dashboard aggregate snapshots

Examples:

* follow-up counts
* attendance summary cards
* open inquiry counts
* activity booking availability summaries

### Stable config bundles

Examples:

* school feature toggles
* student-log privacy settings
* admissions configuration
* portal availability rules

### Website / portal structure data

Resolved read structures, not raw content trees.

---

## 10. What Not to Cache Aggressively

Do not broadly cache:

* raw mutable operational rows
* live attendance truth under contention
* draft grading / mutable assessment states
* exact current workflow states that drive writes
* broad final permission-filtered payloads without strict scoping
* domains frequently mutated by raw SQL unless invalidation is explicit

---

## 11. Invalidation Is Architecture

For every cache family define:

* key namespace
* payload shape
* owner of recomputation
* TTL
* invalidation triggers
* stale tolerance

### Example families

#### School tree cache

Key:
`ifed:school_tree:{school}`

Invalidated by:

* reparenting
* archive/unarchive if relevant
* tree-shape mutation

#### Student-group membership cache

Key:
`ifed:group_students:{student_group}`

Invalidated by:

* child-table changes
* relevant enrollment changes
* archival/state changes affecting membership truth

#### Instructor scope cache

Key:
`ifed:instructor_scope:{user}`

Invalidated by:

* teaching assignment changes
* schedule changes altering instructional scope
* school-scope changes for the user

#### Schedule resolution cache

Key:
`ifed:schedule:{student_group}:{rotation_day}`

Invalidated by:

* Student Group Schedule changes
* School Schedule Block changes
* structural calendar/scope changes that affect resolution

#### Dashboard summary cache

Key:
`ifed:dash:{domain}:{scope}:{user_or_school}`

Invalidated by:

* event-driven invalidation where feasible
* otherwise short TTL with explicit stale tolerance

## 11.1 Hard rules

* ORM writes and raw SQL are not equal
* raw SQL writes on cached domains require explicit invalidation
* short TTL is not a substitute for invalidation
* cache compact payloads, not bloated blobs
* site-level namespacing is mandatory
* key scope must include user/school/filter/schema version when relevant

---

## 12. Read-Model Policy

A read model is mandatory when a surface is:

* read-heavy
* aggregation-heavy
* repeatedly visited
* permission-scoped
* stable enough for short stale windows
* expensive to compute from transactional truth each time

## 12.1 Candidate read-model surfaces

* Student Log Dashboard
* attendance analytics and ledger-context-heavy pages
* inquiry analytics
* room utilization
* policy signature analytics
* Staff Home summary areas
* portal boards
* summary-heavy gradebook and delivery surfaces when patterns stabilize

## 12.2 Rule

> **If the same dashboard or board keeps re-aggregating live operational tables under load, it is a read-model candidate by default.**

This is consistent with other repo patterns:

* frozen reporting-cycle truth for term reporting
* explicit delivery and grade surfaces in curriculum/task/gradebook notes
* activity booking distinction between lifecycle truth and communication views

---

## 13. Nested Scope Contract

NestedSet-backed scope resolution is a huge part of Ifitwala_Ed. It affects:

* permissions
* dashboards
* reports
* analytics
* location capacity
* inherited configuration
* defaults on new docs
* school/organization scoping across the whole product

This section is canonical.

## 13.1 Canonical scope rules

1. When a feature contract is school-tree-aware, selecting a parent school implies the selected school plus all descendants.
2. Tree-aware scope must be applied server-side in SQL `WHERE` clauses before aggregation, never after grouping and never client-side as the real guard.
3. Requested school scope must always be intersected with the caller’s visible school subtree.
4. Exact-match school filters are allowed only when the owning contract explicitly says descendant inheritance is not part of the workflow/report.
5. Shared visibility helpers must preserve the same descendant-aware behavior as the reports/APIs they support.
6. Location capacity enforcement is part of the same nested-scope contract: parent locations must account for descendant-room utilization when capacity is enforced at the parent node.
7. New school-scoped forms may prefill the current user’s default school when the doc is new and empty, but the prefill remains editable unless the workflow says the context is locked.
8. Program assessment categories may resolve dynamically from the nearest ancestor when the child program has no local rows; local rows remain the canonical override.

## 13.2 Concurrency implications of nested scope

Nested scope is also a concurrency concern.

### Required posture

* centralize scope resolution
* cache reusable subtree expansions
* avoid ad-hoc tree traversal in reports/APIs
* avoid repeated `get_doc()` traversal in hot paths
* use pre-aggregation `IN %(scope)s` SQL predicates
* never apply subtree semantics after fetching broad data
* keep location subtree capacity checks request-bounded and grouped, not loop-heavy

## 13.3 Contract matrix posture

Scope ownership should remain centralized across:

* tree utilities
* school tree helpers
* shared school settings helpers
* location utilities
* report helpers
* analytics APIs

The technical note is simple:

> **Scope caches must always be keyed by permission scope and selected filter context; stale shared scope caches are a data-leak risk.**

## 13.4 Rule

> **Tree-aware scope parity across reports, APIs, dashboards, and UI defaults is not optional. Divergent subtree semantics are architecture bugs.**

---

## 14. Query-Shape Discipline

Bad query shape multiplied by concurrency is one of the main bottlenecks in Frappe apps.

## 14.1 Rules

* every hot endpoint should have a query budget
* fetch only used columns
* prefer one bounded SQL/query-builder query over many small ORM reads
* no inside-loop `get_value` on hot surfaces
* align indexes with real filters
* no deep hydration unless the UI truly needs it
* context endpoints must declare their dependency sources
* fix query shape before adding cache

Your codebase already shows the right direction in some places:

* lean SQL for student log portal/report surfaces
* batched/locked scheduler processing for auto-close flows

---

## 15. Aggregated Context Endpoints and the 5-Call Rule

The SPA should not initialize heavy views through a waterfall of small calls.

## 15.1 Rule

No view should require more than **5 distinct API calls** to initialize foundational payload.
Target is **1** bounded context endpoint where the domain is tightly coupled.

## 15.2 Bounded aggregation rules

Context endpoints must:

* stay bounded in payload and query count
* document their invalidation triggers
* avoid bundling unrelated domains just to reduce call count
* remain permission-safe
* prefer defaults/options/context, not giant live result sets unless explicitly justified

## 15.3 Parallelization rule

Use `Promise.all()` only for truly independent domains, not tightly coupled initialization primitives that belong in one page-context endpoint.

---

## 16. Realtime Broadcasting Rules

Realtime is for:

* job completion
* progress milestones
* coarse invalidation
* selective user-facing updates

Not for:

* chatty per-row storms
* broadcasting every tiny internal state change

## 16.1 Channel naming

Use:

* per-user job streams
* per-concern invalidation channels
* stable message schemas

## 16.2 Fallback

A polling fallback must exist for environments where websockets are unreliable or blocked.

## 16.3 Rule

> **Realtime is an optimization for refresh and awareness, not the only correctness path.**

---

## 17. Scheduler and Cron Governance

Cron must dispatch, not do heavy domain work inline.

## 17.1 Dispatcher rule

Scheduled tasks should:

* fetch canonical IDs only
* chunk them
* enqueue bounded workers
* return quickly
* publish progress/summary metrics

Your student-log auto-close flow already points in the correct direction with dispatcher locking and chunk workers.

## 17.2 Backpressure rule

Dispatchers must enforce:

* max outstanding chunks
* queue depth awareness
* slow-job thresholds
* bounded fan-out

## 17.3 Rule

> **Cron acting directly on thousands of mutable rows is banned unless the workload is proven small and bounded.**

---

## 18. Batch Mutation Rules

Batching is encouraged, but it must be bounded.

## 18.1 Rules

* use chunk sizes appropriate to row size and lock behavior
* avoid inside-loop commits unless explicitly justified
* bulk writes on cached domains require invalidation
* batch endpoints are preferred over many single-row mutation loops
* chunk workers must tolerate partial failure

## 18.2 Locking principle

Keep lock windows small:

* update only needed columns
* minimize row touches
* avoid holding large transactions for UI convenience

---

## 19. Failure Modes and Degraded Operation

This is required, not optional.

## 19.1 If Redis is degraded

Define:

* what reads fall back to DB
* what jobs stop being accepted
* which caches bypass safely
* which endpoints rate-limit or degrade

## 19.2 If workers are backlogged

Define:

* what jobs are delayed
* what user actions still succeed
* how UI shows “processing delayed”
* when dispatcher fan-out is paused or reduced

## 19.3 If realtime fails

Define:

* polling fallback
* refresh intervals
* safe status reload path
* no permanent “stuck processing” states

## 19.4 If a dispatcher over-enqueues

Define:

* outstanding chunk limits
* alarm thresholds
* circuit-breaker behavior
* requeue policy

## 19.5 Rule

> **Every async-dependent feature must still have a safe degraded behavior when queueing or realtime are unhealthy.**

---

## 20. Observability and Performance Governance

Without measurement, none of this is real.

## 20.1 Minimum metrics

Track:

* request latency by endpoint
* p95 for key pages
* queue depth per queue
* job duration
* job failure rate
* cache hit rate
* DB query count on hot endpoints
* payload size for heavy context endpoints

## 20.2 SLO-style focus

At minimum define performance targets for:

* attendance ledger initialization
* student learning-space bootstrap at class-start bell time
* Student Log submit
* dashboard load for hottest staff pages
* major background jobs such as reporting generation

## 20.3 CI / review posture

Changes to hot endpoints should be reviewed for:

* query count
* payload size
* cache scope
* invalidation path
* async/idempotency impact

---

## 21. Anti-Patterns to Ban

Treat these as defects.

1. random in-process dict caches in app modules
2. caching broad permission-sensitive final payloads without strict scope keys
3. raw SQL writes on cached domains without explicit invalidation
4. “just add TTL” thinking
5. caching a bad query instead of fixing the query
6. giant blob caches without bounded shape
7. domain events with no durability or idempotency
8. cron jobs iterating huge record sets inline
9. request endpoints doing email/network work inline
10. mega-context endpoints that solve call count by becoming huge slow endpoints
11. divergent subtree semantics across reports/APIs/UI
12. moving correctness-critical state transitions into async just to make the request fast

---

## 22. Immediate Implementation Priorities

In order:

### Priority 1

Formalize cache contracts for:

1. school tree / effective school scope
2. academic-year visibility maps
3. instructor teaching scope
4. student-group membership maps
5. schedule/block resolution maps
6. dashboard summary snapshots
7. policy/config bundles

### Priority 2

Standardize:

* job submit/status contract
* event durability/idempotency contract
* dispatcher chunking/backpressure contract

### Priority 3

Refactor hottest SPA surfaces to bounded context endpoints:

* attendance ledger
* attendance analytics
* inquiry analytics
* policy signature analytics
* other staff dashboards violating the 5-call rule

### Priority 4

Move read-heavy dashboards to read models or stamped cached payloads.

### Priority 5

Audit raw SQL write domains for explicit invalidation and projection refresh behavior.

---

## 23. Coding Agent Rules Summary

Coding agents working in Ifitwala_Ed must obey these rules:

1. Do not move correctness-critical lifecycle truth into async unless the workflow contract explicitly supports `Processing`.
2. Do not introduce shared cache keys without explicit scope and invalidation ownership.
3. Do not add ad-hoc global dict caches.
4. Do not add raw SQL writes on cached domains without invalidation.
5. Do not create new analytics/dashboard endpoints that live-query large mutable datasets on every request when a read model is justified.
6. Do not add SPA waterfalls for tightly coupled initialization data.
7. Do not introduce subtree logic inline when shared helpers already exist.
8. Do not use queueing to hide bad endpoint or query design.
9. Do not emit domain events without durable recording or idempotent handlers.
10. Do not change descendant-aware semantics for school-scoped features unless the owning contract explicitly allows exact-match scope.

---

## 24. Final Position

For Ifitwala_Ed on Frappe v16, high concurrency is achieved by:

* keeping MariaDB as authoritative transactional truth
* shrinking request-path work
* separating synchronous truth from deferred enrichment
* using layered, invalidation-driven caching
* centralizing and caching nested-scope resolution safely
* introducing durable event fan-out and bounded async workers
* building read models for hot summary-heavy surfaces
* enforcing bounded payloads, bounded queues, and bounded fan-out
* measuring everything that matters

Not by:

* “using Redis more”
* “making everything async”
* “adding more endpoints”
* “adding more cache TTLs”
* “replacing Frappe before fixing app architecture”

This is the posture that fits Ifitwala_Ed, fits Frappe v16, and gives both humans and coding agents a clear contract to build against.
