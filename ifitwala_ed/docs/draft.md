You’re right to call this out — dashboards are where permission leaks usually happen, because people treat them as “analytics” and accidentally broaden access.

And **your current dashboard API does broaden access**: it gates by “analytics roles” and then scopes by **authorized school branch**, which means a Pastoral Lead (or Curriculum Coordinator) can currently see aggregates + student log details for *everyone in that school tree*, not just their group/program. That violates the policy you’re trying to lock. (This is exactly what `ALLOWED_ANALYTICS_ROLES` + `sl.school IN authorized_schools` does today in `student_log_dashboard.py`.)

Below are **additional sections** to paste into your note so dashboards can’t become a loophole.

---

## 18. Dashboards & analytics permissions (no leaks)

### 18.1 Dashboards are read-only consumers, not alternate permission systems

Dashboards (including Student Log Dashboard / Analytics pages) must **never** define their own visibility rules.

They are **read-only consumers** of the canonical Student Log visibility policy (§15).

Hard rule:

> Any dashboard query may return only Student Logs that the requesting user could view in a normal Student Log list view.

This applies equally to:

* charts (aggregates)
* KPI cards
* “recent logs” tables
* “student details” panels that show full log text

### 18.2 Analytics-role gating is insufficient (and can be dangerous)

Having a role that grants access to “analytics pages” is a **UI navigation gate**, not a data-visibility gate.

Locked rule:

* “Analytics access” may allow a user to open the page.
* It must not expand what records they can see.

Visibility must still be enforced by Student Log permission truth.

### 18.3 Canonical enforcement method for dashboards (implementation requirement)

All analytics endpoints must enforce visibility using one of:

1. **DocType permission enforcement**

   * Use `frappe.get_list` / `frappe.get_all` (preferred), with normal permissions.

2. **SQL with canonical visibility clause**

   * If raw SQL is needed for performance, the endpoint must apply the **same visibility WHERE clause** as Student Log list permissions.

Hard invariant:

> A raw SQL dashboard query is a defect unless it applies the canonical Student Log visibility predicate.

### 18.4 Detail cards with full log text (high-risk surface)

Any dashboard component that returns full log content (e.g., “Student Logs” panel showing `log` text) must follow these rules:

* It must return **only logs the user is allowed to read** under §15.
* If the user is **not allowed** to see that student’s logs:

  * return an empty list (do not reveal existence, counts, or “permission denied” hints)
* No endpoint may accept `student` and bypass visibility under the assumption that “analytics roles are trusted.”

This prevents “select a student and read everything” leakage.

### 18.5 Aggregates must not leak sensitive existence

Aggregations must be computed over the **visible set** only.

Implication:

* A Pastoral Lead’s charts show counts only for their pastoral groups.
* A Curriculum Coordinator’s charts show counts only for students in their programs.
* Academic Staff charts show only:

  * their authored/assigned logs
  * plus teaching-context logs (Option A) if enabled

No aggregate may be based on school-tree scope unless the user has the school-tree oversight role (Academic Admin/Counsellor).

### 18.6 Filter metadata must be visibility-aware

Dashboard “filter dropdown options” (schools, students, authors, programs) must not reveal out-of-scope entities.

Rules:

* Student dropdown returns only students where the user has visibility to at least one log (or where they teach / pastoral lead / program coordinate).
* Author dropdown returns only authors within the visible set.
* Program dropdown may be broader for admins, but for coordinators it must be restricted to their coordinated programs.

---

## 19. One shared visibility predicate (prevents drift)

### 19.1 Visibility predicate is a shared server utility

There must be exactly one server utility that returns the canonical Student Log visibility predicate for a user.

Dashboards, reports, list endpoints, and detail endpoints must use it.

This prevents “dashboard is correct but reports are wrong” divergence.

### 19.2 Student Log dashboard endpoints must be refactored to use it

Any endpoint in `api/student_log_dashboard.py` that currently scopes by “authorized schools” must instead scope by:

* the canonical visibility predicate (§15 / Option A)

School-tree scope is allowed only for:

* Academic Admin
* Counsellor

For all other roles, school-tree scope is **not** sufficient and must not be used.

---
