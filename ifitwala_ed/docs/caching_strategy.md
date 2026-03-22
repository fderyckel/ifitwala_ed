Below is the note I would lock for Ifitwala_Ed.

# Ifitwala_Ed — Caching Strategy Note for Frappe Framework v16

## Purpose

This note defines the forward-looking caching posture for **Ifitwala_Ed on Frappe v16** in a **high-concurrency, multi-worker** environment.

It is not a generic “use Redis more” note.

The real goal is this:

* reduce repeated DB and Redis overhead on hot paths
* keep cache correctness under multi-worker concurrency
* preserve auditability and permission safety
* align with current Frappe v16 direction rather than older v13/v14 habits

This also aligns with the project’s own locked engineering rules: reduce DB round-trips, use Redis for shared or stable data, avoid ad-hoc in-process dict caching, and assume multi-worker Gunicorn plus scheduler workloads.

---

## 1. Strategic shift in Frappe v16+

The old lazy instinct in Frappe was:

> “If it is hot, put it in Redis.”

That is no longer enough, and in some cases it is now the wrong first move.

Frappe’s own current direction is clearer than before:

* use **request/transaction-local caching** for repeated small reads
* use **Redis** for shared cross-worker cache
* reduce unnecessary Redis round-trips for ultra-hot framework reads
* rely on **coordinated invalidation**, not blind permanence

Two concrete Frappe changes matter here:

1. In v16, `db.count(..., cache=True)` now behaves like `db.get_value(..., cache=True)` and is stored in `value_cache`, not Redis; that cache is evicted after the current transaction. ([GitHub][1])

2. Frappe engineering explicitly moved some core hot reads away from constant Redis lookups by introducing coordinated client-side caching, because Redis itself had become part of the bottleneck for frequently accessed framework data. ([Frappe][2])

That means the right question is no longer:

> “How much can we put in Redis?”

It is:

> “Which layer should cache this read, for how long, and who owns invalidation?”

---

## 2. The caching model Ifitwala_Ed should adopt

Use a **4-layer cache model**.

### Layer A — Request / transaction cache

Use this first.

This is for repeated reads inside one request, one save flow, one API call, or one job run.

Typical tools and behaviors:

* `frappe.db.get_value(..., cache=True)`
* `frappe.db.count(..., cache=True)` in v16
* framework-local `value_cache`

This is cheap and usually the safest win. It avoids repeated DB work without adding cross-worker coherence problems. Frappe v16 explicitly moved more of this behavior toward request-local caching. ([GitHub][1])

**Use for:**

* repeated flags during one validation flow
* repeated settings checks inside one request
* repeated lookups of the same row during one API call

**Do not use as your only strategy** for data reused across requests.

---

### Layer B — Cached documents / settings

Use `frappe.get_cached_doc` for slow-changing configuration and reference documents.

Frappe’s own docs explicitly recommend this for documents that do not change often, especially settings-like documents. Cached document invalidation is “best effort”: ORM saves and `frappe.db.set_value` clear related cache, but raw SQL does not. Manual invalidation uses `frappe.clear_document_cache`. ([Frappe Documentation][3])

**Use for:**

* `Org Setting`
* School-level configuration
* Admission Settings
* policy/config Singles
* stable schedule configuration
* stable portal/shell settings

**Not for:**

* high-churn transactional doctypes
* rows commonly changed by bulk SQL
* permission-sensitive read models that vary per user

---

### Layer C — Shared Redis cache

Use Redis for **shared, deterministic, cross-worker reuse**.

Tools:

* `frappe.cache()`
* `@redis_cache(ttl=...)`

Frappe’s docs support this for expensive deterministic computations. ([Frappe Documentation][3])

This is the right place for app-level derived views and reusable lookup maps that must survive across workers and requests.

**Use for:**

* school tree expansions
* “students taught by instructor X” sets
* schedule resolution maps by `(student_group, rotation_day, block_number)`
* stable dashboard aggregate snapshots
* reusable permission input maps
* per-school or per-organization policy resolution bundles

**Do not use Redis as a dumping ground** for every hot read. Frappe’s own engineering write-up is explicit: too many Redis trips on very hot paths become a bottleneck. ([Frappe][2])

---

### Layer D — Framework-managed hot local cache

This is the Frappe-core side of the story.

Frappe is already optimizing some extremely hot metadata/config reads with local process memory plus coordinated invalidation, rather than forcing a Redis hit every time. The point is not that you should scatter custom global dicts through your app. The point is that **process-local caching is only acceptable when invalidation is coordinated and correctness is preserved**. ([Frappe][2])

For Ifitwala_Ed, the rule should stay strict:

* **no ad-hoc global dict cache in app code**
* only use local in-memory caching when it is clearly bounded and correctness is owned centrally

That matches your AGENTS rules exactly.

---

## 3. What to cache in Ifitwala_Ed

Cache **derived stable views**, not raw mutable truth.

That is the core design decision.

### Best cache targets

#### 3.1 School / organization hierarchy maps

These are reused everywhere and relatively stable.

Examples:

* descendants of school X
* nearest ancestor with active academic year visibility
* effective school scope for a user

These are strong Redis-cache candidates because they are reused across requests and expensive to rebuild repeatedly.

#### 3.2 Schedule resolution maps

Your schedule/attendance side is one of the highest-value cache domains.

Examples:

* block lookup by `(school, academic_year, rotation_day, block_number)`
* student group schedule projections
* instructor occupied slots
* location occupied slots

These are classic deterministic derived views with clear invalidation triggers.

#### 3.3 Permission input maps

Not final permission results for every request, but stable inputs.

Examples:

* student IDs taught by instructor X
* school scope list for user X
* allowed student groups for instructor X

That reduces repeated join-heavy permission preparation.

#### 3.4 Dashboard aggregate snapshots

Use short-TTL or explicit invalidation caches for expensive cards, summaries, and overview pages.

Examples:

* follow-up counts
* attendance summary cards
* open inquiry counts
* activity booking availability snapshots

#### 3.5 Stable config bundles

Bundle stable settings once and cache them.

Examples:

* school feature toggles
* student log privacy settings
* portal availability rules
* admissions configuration

#### 3.6 Read-heavy website / portal structure data

For any public or semi-public portal surface with repeated reads and slow-changing data, cache the resolved read model, not the raw doc tree.

---

## 4. What not to cache aggressively

### 4.1 Raw mutable operational rows

Examples:

* live attendance rows
* active workflow statuses
* “current exact seat count” if it changes constantly under contention
* draft submissions / in-progress grading states

These are often safer to compute from truth at read/write time, or to cache only as very short-lived snapshots.

### 4.2 Permission-sensitive final responses

Do not cache broad final datasets that may leak across users.

Cache permission inputs or low-level reusable maps, not a giant “student dashboard payload” without a very strict scope strategy.

### 4.3 Anything frequently mutated by raw SQL

Frappe docs are explicit: raw DB queries do not participate in automatic cached-doc invalidation. If a domain depends on raw SQL writes, caching it without explicit invalidation is asking for stale reads. ([Frappe Documentation][3])

---

## 5. Invalidation is the real architecture

This is the part most teams get wrong.

A cache without explicit invalidation ownership is not an optimization. It is delayed corruption.

For each cache family in Ifitwala_Ed, define:

* key namespace
* payload shape
* owner of recomputation
* TTL
* invalidation triggers
* stale-tolerance policy

### Example cache families

#### School tree cache

**Key**
`ifed:school_tree:{school}`

**Invalidated by**

* School insert/update affecting tree
* reparenting
* archive/unarchive if scope logic depends on it

#### Student group membership cache

**Key**
`ifed:group_students:{student_group}`

**Invalidated by**

* Student Group Student row changes
* relevant enrollment changes
* group archival

#### Instructor teaching scope cache

**Key**
`ifed:instructor_scope:{user}`

**Invalidated by**

* Student Group Instructor changes
* schedule changes that alter teaching assignment
* school scope changes for the user

#### Schedule resolution cache

**Key**
`ifed:schedule:{student_group}:{rotation_day}`

**Invalidated by**

* Student Group Schedule changes
* School Schedule Block changes
* academic-year visibility/closure changes if resolution depends on them

#### Dashboard summary cache

**Key**
`ifed:dash:{domain}:{scope}:{user_or_school}`

**Invalidated by**

* event-driven invalidation where possible
* otherwise short TTL

---

## 6. Strong rules for Frappe-specific correctness

### Rule 1 — ORM writes and raw SQL are not equal

Frappe cached docs are auto-cleared on `doc.save` and `frappe.db.set_value`, but not on raw SQL. Any cache design that ignores this is fragile. ([Frappe Documentation][3])

**Project implication:**
If a domain is cached, raw SQL writes to that domain must be rare and must explicitly clear affected cache keys.

---

### Rule 2 — Prefer `get_value`, `get_values`, `get_list/get_all` appropriately

Your own architecture already locks this in: reduce DB round-trips and prefer the tight DB APIs before reaching for more complex paths.

Caching does not excuse sloppy query patterns. Bad query design plus cache is still bad design.

---

### Rule 3 — Short TTL is not a substitute for invalidation

TTL is a fallback, not the primary correctness model.

Use TTL for:

* dashboard summaries
* soft eventually-consistent read models
* low-risk derived views

Do not rely only on TTL for:

* permission-critical scope data
* schedule conflict data
* identity / relationship truth
* workflow state that drives write decisions

---

### Rule 4 — Cache compact payloads, not bloated objects

Avoid storing large pickled doc trees when a compact JSON-like map would do.

Frappe’s own performance work points to serialization/deserialization and IPC overhead as part of the Redis cost story. ([Frappe][2])

---

### Rule 5 — Site-level isolation is mandatory

Frappe sites are multi-tenant at the bench level, and Frappe’s cache design already uses site-aware namespacing. Keep your app keys similarly disciplined. ([Frappe Documentation][3])

In Ifitwala_Ed, every custom cache key should be app-namespaced and safe under multi-site execution.

---

## 7. Recommended cache categories for Ifitwala_Ed

Below is the practical split I would adopt.

### Category A — Safe and heavy reuse

Cache aggressively with explicit invalidation.

* school tree / effective school scope
* academic-year availability maps
* schedule block maps
* student group membership maps
* instructor teaching scope maps
* portal configuration bundles
* reporting-cycle config bundles

### Category B — Derived operational read models

Cache with shorter TTL and event invalidation where possible.

* dashboard cards
* list summary counts
* attendance summaries
* activity booking board projections
* inquiry SLA summary cards

### Category C — Per-request repeat reads

Use request-local caching only.

* repeated single-value checks in one request
* repeated existence checks in one validation flow
* repeated settings reads inside one method chain

### Category D — Do not cache broadly

Read from source of truth.

* live writes under contention
* final permission-filtered datasets
* mutable assessment/grading draft states
* raw child-table truth that changes every minute

---

## 8. Forward-looking moves beyond basic Frappe caching

If the goal is serious concurrency, the next gains are not only “more cache.”

### 8.1 Materialized read models for hot dashboards

For the hottest staff dashboards, consider dedicated read models or precomputed summary tables updated by controlled write paths or background jobs.

That is often better than recomputing joins and then hiding the cost behind Redis.

### 8.2 Event-driven invalidation discipline

Standardize invalidation functions per domain.

Examples:

* `invalidate_school_scope_cache(...)`
* `invalidate_schedule_cache(...)`
* `invalidate_permission_scope_cache(...)`

Do not scatter anonymous `frappe.cache().delete_value(...)` calls everywhere.

### 8.3 Bulk recompute after structural changes

When a major upstream structure changes, invalidate in coarse batches instead of letting every request rebuild separately.

Examples:

* reparented school tree
* schedule block redesign
* term or academic-year structural changes

### 8.4 Read replicas for heavy analytics

Frappe docs explicitly support routing heavy reads to database replicas when scaling beyond a single-machine comfort zone. That is not “cache,” but it absolutely belongs in the high-concurrency strategy once reporting and analytics become heavy enough. ([Frappe Documentation][4])

### 8.5 Profiling before and after every cache change

Frappe Recorder is built for this. Use it to confirm that a cache actually lowers query count and request duration instead of just moving the cost somewhere harder to see. ([Frappe Documentation][5])

---

## 9. Anti-patterns to ban

These should be treated as architectural defects.

### 9.1 Random in-process dict caches in app modules

Your project rules already reject this. Keep that line.

### 9.2 Caching permission-sensitive final payloads without strict scoping

Too easy to leak data.

### 9.3 Raw SQL writes on cached domains without explicit invalidation

This is a stale-data factory. ([Frappe Documentation][3])

### 9.4 “Just add TTL” thinking

TTL is not correctness.

### 9.5 Caching a bad query instead of fixing the query

Always fix query shape first, then cache the derived result if needed.

### 9.6 Huge blob caches

Compact, deterministic, scoped payloads win.

---

## 10. Operational guidance for v16-era Frappe

A few current platform-level notes matter.

* Frappe v16-era work includes major reductions in Redis overhead, faster metadata access, faster ORM/query paths, and stronger concurrency support through threaded workers and other runtime optimizations. This improves the baseline, but it does not rescue bad app-level caching design. ([Frappe Forum][6])
* Site and common site config are themselves cached for up to one minute in v16, so config changes are not always instantly visible to running workers. That matters when debugging “stale behavior.” ([GitHub][1])

---

## 11. Recommended implementation posture for Ifitwala_Ed

### Immediate rule set

1. **Cache contracts first, code second.**
2. **Use request-local caching first for repeated small reads.**
3. **Use `get_cached_doc` for settings/config Singles and slow-changing docs.**
4. **Use Redis only for shared deterministic derived views.**
5. **Every Redis cache family must have explicit invalidation ownership.**
6. **No raw SQL writes on cached domains unless invalidation is handled.**
7. **Profile before and after every cache addition.**

### First cache families to formalize

In this order:

1. school tree / effective school scope
2. academic-year visibility maps
3. instructor teaching scope
4. student-group membership maps
5. schedule/block resolution maps
6. dashboard summary snapshots
7. policy/config bundles

That order fits your own architecture well because it attacks repeated scope resolution, scheduling reads, and summary computation first.

---

## 12. Final position

For Ifitwala_Ed on Frappe v16, the best caching strategy is:

> **Layered, explicit, invalidation-driven caching of stable derived views, combined with tight DB query design and request-local reuse.**

Not:

> “Put more things in Redis.”

Frappe itself is moving away from indiscriminate Redis dependency for every hot read. Your app should do the same. Use Redis where cross-worker sharing matters. Use request-local cache where it does not. Use cached docs for settings. Treat invalidation as architecture, not cleanup. ([GitHub][1])

And for this project specifically, keep the hard guardrails already locked in your repo: reduce round-trips, use Redis for shared stable data, avoid ad-hoc in-process caches, and assume concurrency from multi-worker web plus scheduler execution.

[1]: https://github.com/frappe/frappe/wiki/Migrating-to-version-16?utm_source=chatgpt.com "Migrating to version 16 · frappe/frappe Wiki"
[2]: https://frappe.io/blog/engineering/beating-redis-with-a-dictionary-and-redis?utm_source=chatgpt.com "Beating Redis with a Dictionary and Redis"
[3]: https://docs.frappe.io/framework/user/en/guides/caching?utm_source=chatgpt.com "Caching - Documentation for Frappe Apps"
[4]: https://docs.frappe.io/framework/user/en/database-optimization-hardware-and-configuration?utm_source=chatgpt.com "Database Optimization - Hardware and Configuration"
[5]: https://docs.frappe.io/framework/user/en/profiling?utm_source=chatgpt.com "Profiling and Monitoring - Documentation for Frappe Apps"
[6]: https://discuss.frappe.io/t/erpnext-hrms-frappe-framework-v16-release-dates/156349?utm_source=chatgpt.com "ERPNext, HRMS & Frappe Framework v16 Release Dates"
