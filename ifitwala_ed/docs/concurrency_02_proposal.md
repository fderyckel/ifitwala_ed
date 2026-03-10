# High-Concurrency Optimization Proposal (2 Hotspots)

Audience: internal Codex agent implementing changes in `fderyckel/ifitwala_ed` (Frappe v16 + ui-spa)

---

## Shared goals (both features)

* **Reduce worker time per user request** (free WSGI workers faster).
* **Reduce DB connection churn / auth overhead** by lowering API call count.
* **Clarify endpoint “intent”** (payload vs domain reads vs mutations).
* Make read flows **idempotent and cache-friendly**, and write flows **signal-driven**.

### Success criteria (measurable)

* Page initialization API calls: **1 call for init** (2 acceptable only if ledger content not included in init payload).
* TTI for init reduced by **>= 30%** in staging under synthetic load.
* DB query count for init reduced by **>= 20%** (or at minimum, no increase) while maintaining same data correctness.
* No increase in retry loops / stale data bugs: “stale loadRunId” guard remains correct.

### Dangers / blind spots

* “One big payload” can become a **big file** and regress memory/network.
* Scope/default derivation is tricky: wrong defaults can cause silent filter mismatch (showing data user didn’t intend).
* Cache invalidation: cached context must be scoped by **user permissions** + relevant filters, otherwise users see other users’ data.

---

# Hotspot A: Attendance Ledger (`AttendanceLedger.vue`)

Location:

* `ifitwala_ed/ui-spa/src/pages/staff/analytics/AttendanceLedger.vue`
* `ifitwala_ed/ui-spa/src/lib/services/studentAttendance/studentAttendanceService.ts`
* Backend methods currently in `ifitwala_ed/api/student_attendance.py`
* Ledger analytics currently in `ifitwala_ed/api/attendance.py` via `ifitwala_ed.api.attendance.get`

## Aims

* Replace sequential init with a **single view payload endpoint** returning filters + defaults (+ optional first-page ledger).
* Remove unnecessary duplicated calls (e.g., “derive academic years from student groups” should be consolidated server-side).
* Enforce “init budget”: **<= 5 calls** (target 1).

## Implementation steps (clear and concrete)

### 1) Add a view payload endpoint (backend)

Create a new whitelisted method (example name; exact name must be consistent with your repo’s naming conventions):

**`ifitwala_ed.api.student_attendance.fetch_attendance_ledger_context`**

Expected input (JSON payload):

* `{ school?: string|null, program?: string|null, include_ledger?: 0|1 }`

Expected output shape (JSON):

* `schools`, `default_school`
* `programs`
* `academic_years`, `default_academic_year`
* `terms`, `default_term`
* `student_groups`, `default_student_group`
* OPTIONAL: `ledger` (same contract as `AttendanceLedgerResponse`)

**Backend requirements**

* Reuse existing helpers (permissions, allowed scope, caching) from `student_attendance.py` **without duplicating logic**.
* Cache context objects by key:

  * `user_id` (or session)
  * `school`
  * `program`
  * include queryable metadata (e.g., `last_updated_ts`) if available
* If `include_ledger=1`, still return only **first page** unless specified otherwise. Do not “bulk dump all pages”.

### 2) Extend the student attendance service (frontend)

In `createStudentAttendanceService()`:

* Add `fetchAttendanceLedgerContext(payload)` resource using `createResource({ url: 'ifitwala_ed.api.student_attendance.fetch_attendance_ledger_context', method: 'POST' })`

### 3) Update `initializeFilters()` in `AttendanceLedger.vue`

Replace:

```ts
const schoolContext = await attendanceService.fetchSchoolContext()
...
programs.value = await attendanceService.fetchPrograms()
await loadAcademicYears()
await loadTerms()
await loadStudentGroups()
```

with one call:

```ts
const ctx = await attendanceService.fetchAttendanceLedgerContext({
  school: filters.school,
  program: filters.program,
  include_ledger: 0,
})

schools.value = ctx.schools
programs.value = ctx.programs
academicYears.value = ctx.academic_years
terms.value = ctx.terms
studentGroups.value = ctx.student_groups

filters.school = ctx.default_school
filters.academic_year = ctx.default_academic_year
filters.term = ctx.default_term
filters.program = ctx.default_program
filters.student_group = ctx.default_student_group
```

### 4) Decide on ledger initialization

Two acceptable strategies:

* **Strategy A (preferred)**: `include_ledger=0`, then `await reloadLedger()`
* **Strategy B (init latency optimized)**: `include_ledger=1`, hydrate `ledger.value = ctx.ledger`, and still keep `reloadLedger()` logic unchanged.

### 5) Optimize watchers (reduce waterfall on filter change)

Goal: fewer sequential calls when filters change, without correctness regression.

Best option:

* Reuse `fetchAttendanceLedgerContext()` for school/program changes (returns derived defaults and scoped lists) so you don’t need to call 3 endpoints. Then reload ledger.

Fallback option:

* Parallelize independent reads with `Promise.all`:

  * school change: `[fetchAcademicYears, fetchStudentGroups]` parallel, then `fetchTerms` using chosen academic_year
  * program change: `fetchStudentGroups` only (already scoped)

### 6) Instrumentation & testing

Add metrics in dev/staging:

* log init call count and total init time per mount
* capture DB query count (backend log or APM)
* load test with 1000 simulated concurrent staff accesses; confirm worker utilization improves.

## Success criteria (Attendance)

* Init call count: 1 (without ledger init) or 1 (with ledger init)
* No sequential init chain in code (no `await` waterfall during onMounted init beyond the payload and the ledger call)
* Stale run guard remains intact (`loadRunId` behavior unchanged)

## Blind spots / dangers (Attendance)

* Cached context must respect permission scope: **different schools / scopes must not share cached results**.
* Adding ledger into context can inflate response size; use only first page and appropriate pagination.
* Derived defaults can vary per site; avoid “hard-coded fallback” behavior not validated across deployments.

---

# Hotspot B: Policy Signature Analytics (`PolicySignatureAnalytics.vue`)

Location:

* `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`
* Likely corresponding service modules in `ifitwala_ed/ui-spa/src/lib/services/...`
* Likely backend API under `ifitwala_ed/api/...` (policy signatures domain)

## Aims

* Remove sequential init: `refreshOptions()` then `loadDashboard()` must not be waterfall.
* Ensure options + dashboard are delivered via a consolidated context payload.
* Ensure any write (acknowledge policy, assign policy, create campaign) emits a signal invalidation.

## Implementation steps (clear and concrete)

### 1) Add view payload endpoint (backend)

Create:

**`ifitwala_ed.api.policy_signatures.fetch_policy_signature_context`**
(or consistent naming per your endpoint taxonomy)

Expected input:

* `{ school?: string|null, include_dashboard?: 0|1, filters?: {...} }`

Output:

* `options` (e.g., school list, policies, versions, programs…)
* `defaults` (explicit default selections)
* OPTIONAL: `dashboard` payload (same contract as existing dashboard response)

**Backend requirements**

* Return only the fields used by the dashboard (keep contract tight).
* Cache options by “user scope + school” (options are high-fan-out and should be cached).
* Avoid unbounded joins; paginate dashboard results.

### 2) Extend the policy signatures service (frontend)

Add `fetchPolicySignatureContext(payload)` and restructure existing `refreshOptions`/`loadDashboard` logic to hydrate:

* `options`
* default filters
* dashboard response (if included)

### 3) Update component initialization

Replace sequential:

```ts
await refreshOptions()
await loadDashboard()
```

with one payload call, then hydrate defaults, then dashboard:

* Either `include_dashboard=1` in init, or
* init context call + `Promise.all([refreshOptions, loadDashboard])` depending on current code structure.

### 4) Implement invalidation signals for mutations

For every mutation endpoint (acknowledgement, assignment, policy admin actions):

* Emit a `uiSignals` event (example name: `SIGNAL_POLICY_SIGNATURES_INVALIDATE`)
* Ensure dashboards subscribe/refresh on invalidation, not via polling.

### 5) Instrumentation & testing

* Confirm init is 1 call in staging.
* Load test concurrent staff accesses to this analytics page.
* Validate no “stale options/dashboards” state by adding unit tests around “defaults derived from options”.

## Success criteria (Policy)

* Init call count: 1 (or 2 if you keep dashboard separate but parallelized; target 1)
* Options and dashboard fetches are either in the same payload call, or parallelized without dependency deadlocks.
* Mutation invalidation is deterministic and documented.

## Blind spots / dangers (Policy)

* Options caching must not leak across schools/scopes.
* Dashboard payloads can get expensive; keep them paginated and minimal.
* If you parallelize without deduplication, you might double-load options on fast remounts; consider request deduplication in the service layer.

---

## Deliverables (what Codex agent must produce)

1. Backend endpoints:

   * `fetch_attendance_ledger_context`
   * `fetch_policy_signature_context`
2. Frontend service additions:

   * `fetchAttendanceLedgerContext(...)`
   * `fetchPolicySignatureContext(...)`
3. Component rewrites:

   * `AttendanceLedger.vue` init + watchers
   * `PolicySignatureAnalytics.vue` init (and optionally watchers)
4. Updated endpoint docs/README (short contract summary)
5. Instrumentation hooks (dev-only) for init call count & elapsed time

If you want, I can tighten this into a PR checklist format (branch name, file paths to edit, exact contract keys, and a short test plan) once you confirm the exact service/module names for policy signatures in your repo.
