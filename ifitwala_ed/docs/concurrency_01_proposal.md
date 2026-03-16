# Ifitwala_Ed Concurrency & Scalability Proposal

This document outlines a 10-point strategic engineering proposal to prepare **Ifitwala_Ed** for super high concurrency (1000+ simultaneous users: students, staff, and guardians).

Given the realities of Frappe v16 + Python 3.14, native `asyncio/await` is not feasible for request lifecycles. Our primary strategy relies on **background workers (RQ)**, **caching**, **Socket.IO realtime events**, **SPA parallelization**, and **event-driven architecture (Domain Event Bus)**.

---

## 1. Move Heavy Computations to Background Jobs (RQ)
**The Problem:** Current processes like `generate_student_term_reports` iterate synchronously over students, fetching `Course Term Result`, `Program Enrollment`, and `Course` data, and repeatedly inserting documents in a single request.
**The Solution:** Controller methods should be lightweight. When a cycle is requested, `frappe.enqueue("ifitwala_ed.assessment.term_reporting.process_reports", reporting_cycle=X, queue="long")` should be used. The API endpoint immediately returns a `202 Accepted` status to the SPA, freeing the WSGI worker to serve the next user.

## 2. Asynchronous Email & Notification Pipelines
**The Problem:** During admission processing (`admissions_portal.py`) and recommendation intakes (`recommendation_intake.py`), we are making synchronous `frappe.sendmail()` calls. If the mail server is slow, the user request hangs.
**The Solution:** Enqueue all transactional emails. Replace inline mail configuration with automated job queuing. Let Frappe’s built-in email queue (`frappe.enqueue(queue="short")`) handle network boundaries safely out-of-band.

## 3. Decouple "Next Steps" in Record Submissions
**The Problem:** The `submit_student_log` function performs synchronous validation, checks follow-up logic, verifies school scopes, inserts the doc, and submits it—all in one request.
**The Solution:** Only execute the absolute minimum validation synchronously (e.g., student existence and log validation) to acknowledge the submission. Hand off the `requires_follow_up`, SLA tracking, and assignment of the `follow_up_person` to a background worker to unblock the client immediately.

## 4. Implement a Domain Event Bus
**The Problem:** When a significant event occurs (e.g., `submit_application` on `StudentApplicant`), multiple actions follow: notifying teachers, updating analytics, regenerating focus items, creating student records. Chaining these tightly causes bottlenecks.
**The Solution:** Introduce a **Domain Event Bus**. When a student log or application is submitted, simply fire `DomainEvent("StudentLogSubmitted", doc.name)`. Independent listeners (Analytics, Notifications, Dashboards) subscribe to this event and are automatically dispatched to RQ workers. This perfectly mirrors your SPA signal architecture on the backend.

## 5. Eliminate N+1 API Design via Page Payload Aggregation (Deep Dive)
**The Problem:** Real-world examples in `ifitwala_ed/ui-spa` show systemic sequential `await`s fetching tightly coupled domain data. For instance, in `AttendanceLedger.vue`, loading the page blocks on:
```javascript
programs.value = await attendanceService.fetchPrograms();
await loadAcademicYears();
await loadTerms();
await loadStudentGroups();
```
While switching to `Promise.all()` solves the client-side waterfall latency, making 4 simultaneous requests per user places immense N+1 load on the database. 4 endpoints × 5 queries each = 20 queries per user. For 1000 concurrent users, that is 20,000 DB queries. Additionally, each API call carries CPU overhead in Frappe for auth validation, site context loading, and request parsing.

**The Concrete Solution:** Adopt a **hybrid API Strategy** to minimize backend load:
1. **Aggregated Page Payloads:** For tightly coupled domain data (like setting up an attendance ledger context), use a single endpoint that returns the comprehensive payload.
```javascript
// SPA (AttendanceLedger.vue)
const context = await attendanceService.getLedgerContext();
// Backend
@frappe.whitelist()
def get_attendance_ledger_context():
    return {
        "programs": get_programs(),
        "academic_years": get_years(),
        "terms": get_terms(),
        "student_groups": get_groups()
    }
```
2. **Parallel Domain Fetching:** Reserve `Promise.all()` strictly for independent, modular data domains (e.g., fetching a student's `schedule` and their `notifications` concurrently).
3. **The 5-Call Rule:** Enforce a strict architectural rule that no SPA view requires more than 5 distinct API calls to initialize its foundational payload.

### Codebase Instances: Aggregated Page Payloads (Rule 1)
*These components currently fetch highly related structural/domain data across multiple requests and should be consolidated into a single Context Endpoint.*

| Component (`ui-spa/src/...`) | Current Fragmented API Calls | Proposed Aggregated Endpoint |
| :--- | :--- | :--- |
| `AttendanceLedger.vue` | `fetchSchoolContext()`, `fetchPrograms()`, `loadAcademicYears()`, `loadTerms()`, `loadStudentGroups()` | `get_attendance_ledger_context()` |
| `AttendanceAnalytics.vue` | `fetchSchoolContext()`, `fetchPrograms()`, `loadStudentGroups()` | `get_attendance_analytics_context()` |
| `PolicySignatureAnalytics.vue`| `loadCapabilities()`, `refreshOptions()`, `loadDashboard()` | `get_policy_dashboard_payload()` |
| `InquiryAnalytics.vue` | `getInquiryTypes`, `getUserList`, `getAcademicYears`, `getOrganizations`, `getSchools` | `get_inquiry_analytics_context()` |
| `StudentOverview.vue` | `studentSearchResource.fetch()`, `snapshotResource.submit()` | `get_student_overview_payload()` |
| `RoomUtilization.vue` | `freeRooms()`, `timeUtil()`, `capacity()`, `analyticsAccess()` | `get_room_utilization_dashboard()` |
| `EnrollmentAnalytics.vue` | `drilldownResource.submit()`, `dashboardResource.submit()` | `get_enrollment_dashboard_payload()` |

### Codebase Instances: Parallel Domain Fetching (Rule 2)
*These components currently `await` independent data domains sequentially causing waterfall latency, or group independent domains improperly. They should use `Promise.all()` for speed.*

| Component (`ui-spa/src/...`) | Current Sequential Blockers | Proposed `Promise.all` Grouping |
| :--- | :--- | :--- |
| `AdmissionsCockpit.vue` | Awaits `getAdmissionsCaseThread()` before other cockpit data. | `Promise.all([getCockpitData, getCaseThread])` |
| `StudentActivities.vue` | Awaits `getActivityPortalBoard()` then `loadBoard()`. | `Promise.all([getPortalIdentity, getBoardHistory])` |
| `ClassHub.vue` | Awaits `service.getBundle()` then processes sessions. | `Promise.all([getClassHubBundle, getRecentSessions])` |
| `StaffHome.vue` | Loads `StaffHomeHeader` on mount, then later `listFocusItems()`. | `Promise.all([getStaffHomeHeader, listFocusItems])` |
| `OrgCommunicationArchive` | Serially fetches active context then the archive list. | `Promise.all([fetchContext, fetchArchive])` |

### Codebase Instances: The 5-Call Rule Violations (Rule 3)
*These heavy pages currently exceed the 5-Call maximum limit for initialization and are at highest risk of triggering database connection exhaustion during concurrent spikes.*

| Component | Initial API Call Count | Primary Bottleneck |
| :--- | :--- | :--- |
| `AttendanceAnalytics.vue` | **7 calls** | Disparate fetches for context, groups, overview, heatmap, risk, code usage. |
| `AttendanceLedger.vue` | **6 calls** | Granular fetching of school, programs, years, terms, groups, and ledger. |
| `InquiryAnalytics.vue` | **6 calls** | Separate structural lookups for options before getting the dashboard data. |
| `StudentAttendanceTool.vue` | **8+ calls** | Fetches context, programs, codes, weekend flags, meetings, recordings separately. |
| `RoomUtilization.vue` | **5 to 7 calls** | Splits the dashboard across free rooms, time utilization, capacity metrics. |

## 6. Realtime Event Broadcasting (Socket.IO)
**The Problem:** Since we are moving heavy logic (like term report generation or bulk activity bookings) to background workers, the SPA needs to know when the job finishes without polling the server synchronously.
**The Solution:** The backend worker uses `frappe.publish_realtime("term_reports_generated", {"cycle": ctx["name"]}, user=frappe.session.user)`. The Vue SPA listens via `frappe.realtime.on(...)` and triggers an invalidation of `uiSignals` to beautifully refresh the page without expensive HTTP polling.

## 7. Aggressive Cache Utilization for Reads
**The Problem:** Methods like `_is_student_in_session_scope` or fetching `pe_meta` perform repetitive database queries on every log insertion.
**The Solution:** Wrap high-read, low-mutation config lookups in `frappe.cache().get_value()`. A cached dictionary check takes microseconds compared to a full database query, massively reducing DB connection pool exhaustion during concurrent spikes.

## 8. Batch Database Mutations
**The Problem:** The API exposes both `submit_activity_booking` and `submit_activity_booking_batch`. Concurrency spikes occur if the SPA or cron jobs issue hundreds of single mutations.
**The Solution:** Push the UI and background loops to exclusively use batch endpoints or `frappe.db.bulk_insert`. When dealing with things like `process_expired_allocation` in HR modules, gather all expired ledgers and mutate them outside of individual object lifecycles using chunked SQL updates.

## 9. Task Queuing for Complex DocType Lifecycles
**The Problem:** `StudentApplicant.submit_application()` involves complex state machines, creating multiple child records and billing ledgers.
**The Solution:** The `submit` action should transition the DocType state to `Processing`. An enqueued task performs the heavy transactional work and then transitions it to `Enrolled`. This ensures that parent sessions do not lock up the database connection.

## 10. Refactor SLA and Cron Scheduling (Deep Dive)
**Status update (2026-03-12):** The daily scheduler hooks named below now use dispatcher entrypoints that enqueue chunk workers. The remaining concurrency concern is keeping dispatcher fan-out bounded and applying the same pattern to other heavy scheduled workflows such as SLA recomputation.

**Historical problem:** The `ifitwala_ed/hooks.py` relied heavily on massive scheduler events:
```python
scheduler_events = {
    "hourly": ["run_hourly_sla_sweep", "prewarm_meeting_dates_hourly_guard"],
    "daily": ["auto_close_completed_logs", "process_expired_allocation", "allocate_earned_leaves"]
}
```
Previously, jobs like `auto_close_completed_logs` or `process_expired_allocation` iterated over potentially thousands of records inside one scheduled job body. Under concurrency, those long write-heavy runs increased contention on shared operational tables.

**The Concrete Solution:** Move from "Cron acts on data" to "Cron dispatches jobs".
The daily cron should fetch ONLY canonical IDs, then map them into chunked queue payloads.
```python
def process_expired_allocation():
    # 1. Fetch only names
    allocations = frappe.get_all("Leave Ledger Entry", filters={"has_expired": 1}, pluck="name")

    # 2. Chunk into batches of 500
    for chunk in frappe.utils.create_batch(allocations, 500):
        # 3. Dispatch to RQ standard/long queue
        frappe.enqueue(
            "ifitwala_ed.hr.doctype.leave_ledger_entry.leave_ledger_entry.process_chunk",
            allocation_chunk=chunk,
            queue="long"
        )
```
*Why this matters for Frappe v16:* Frappe’s worker system allows the scheduled hook to return quickly while `long` queue workers process smaller, safer transactions that reduce contention for active users.

### Codebase Instances: Cron & Scheduler Batching (Point 10)
*These periodic cron jobs should use "Dispatcher Cron Jobs" that enqueue chunks to the background Redis workers. The daily jobs below now follow that model; remaining scheduled hotspots should be aligned to the same contract.*

| Scheduled Job (`ifitwala_ed.hooks.scheduler_events`) | Scope of Synchronous Loop | Proposed Dispatcher Pattern |
| :--- | :--- | :--- |
| `dispatch_auto_close_completed_logs` (Daily) | Dispatcher only; fetches eligible `Student Log` names and enqueues chunk workers. | Implemented: chunk workers re-check current eligibility before mutating `Student Log`, `ToDo`, and `Comment`. |
| `dispatch_process_expired_allocation` (Daily) | Dispatcher only; fetches canonical `Leave Allocation` names and enqueues chunk workers. | Implemented: chunk workers re-query live `Leave Ledger Entry` rows before creating expiry entries. |
| `dispatch_allocate_earned_leaves` (Daily) | Dispatcher only; groups allocation names per earned `Leave Type` and enqueues chunks. | Implemented: chunk workers apply per-allocation locks and write summaries. |
| `dispatch_generate_leave_encashment` (Daily) | Dispatcher only; fetches eligible `Leave Allocation` names and enqueues chunks. | Implemented: chunk workers skip allocations that already have a `Leave Encashment`. |
| `run_hourly_sla_sweep` (Hourly) | Runs `check_sla_breaches()` which likely iterates over open admissions queues. | Fetches Open Admission IDs only, then enqueues the heavy SLA metric computations to the background in batches of 100. |

## 11. Page Payload Versioning & Cache Stamps
**The Problem:** High-traffic dashboards (like `StaffHome` or `StudentOverview`) are frequently polled or reloaded by SPA hooks, re-querying the exact same dashboard data that hasn't changed, consuming precious WSGI workers.
**The Solution:** Implement **E-Tag / Cache Stamp Versioning** for heavy payload endpoints.
1. When the server generates `get_staff_home_payload()`, it calculates a fast hash of the current dependencies (e.g., `hash(last_log_time, user_settings_modified)`).
2. The endpoint returns this hash as a Cache Stamp.
3. The SPA stores this payload and stamp in the browser's `IndexedDB` or `localStorage`.
4. On subsequent page loads, the SPA sends the cache stamp to the server in the request footprint.
5. The backend validates the stamp in a microsecond cache lookup. If the stamp matches, the backend returns `HTTP 304 Not Modified`.
*Why this matters for Frappe v16:* This technique dramatically circumvents Frappe's JSON serialization and database payload limits, easily cutting 80–90% of massive read requests down to microsecond cache validations, giving the illusion of zero-latency dashboard loading.

---
### Summary Architecture:
- **Backend Lifecycle**: Controller (Immediate Validate) -> Enqueue Job -> Return 202 -> RQ Worker processes DB operations.
- **Client Cache Strategy**: Hydrate via Aggregated Payload Endpoint -> Cache Stamp -> `HTTP 304` on revisit.
- **Client Sync Strategy**: RQ Worker finishes -> `publish_realtime` -> Vue Socket.IO listener -> `uiSignals` refresh.
