# Top 10 SQL Anti-Patterns

1. **[ifitwala_ed/api/student_overview_dashboard.py](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/api/student_overview_dashboard.py) line 69**
   ```python
   for r in frappe.db.sql("SELECT DISTINCT parent FROM `tabStudent Guardian` WHERE guardian = %s", (guardian,))
   ```
   *Why it's poor*: Loop runs an SQL query per guardian, which creates an N+1 issue if a user has many guardians. Instead, this should join or fetch all guardians into a single query.

2. **[ifitwala_ed/hr/doctype/leave_application/leave_application.py](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/hr/doctype/leave_application/leave_application.py) line 517**
   ```python
   for d in frappe.db.sql(
       """
       select
           name, leave_type, posting_date, from_date, to_date, total_leave_days, half_day_date
       from `tabLeave Application`
       ...
       """
   )
   ```
   *Why it's poor*: Inside the [validate_leave_overlap](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/hr/doctype/leave_application/leave_application.py#512-547) method, it queries the DB inside a loop (or loops over query results and performs DB operations). While the loop iterates over a result set, it calls `frappe.db.sql` again inside [get_total_leaves_on_half_day](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/hr/doctype/leave_application/leave_application.py#555-568). This is a classic N+1 query vulnerability where checking 10 overlaps results in 10+ extra database calls instead of a single grouped query.

3. **[ifitwala_ed/api/student_log_dashboard.py](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/api/student_log_dashboard.py) line 270**
   ```python
   def q(sql):
       return frappe.db.sql(sql.format(w=where_clause), params, as_dict=True)
   ```
   *Why it's poor*: The dashboard aggressively fires 6+ separate DB queries (`logTypeCount`, `logsByCohort`, `logsByProgram`, `logsByAuthor`, `nextStepTypes`, `incidentsOverTime`) sequentially, rather than using a single aggregated query or UNION structure to reduce overhead.

4. **[ifitwala_ed/api/admission_cockpit.py](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/api/admission_cockpit.py) line 1186 and 1193**
   ```python
   organizations = [
       row[0]
       for row in frappe.db.sql("SELECT name FROM `tabOrganization` ORDER BY lft ASC, name ASC", as_list=True)
   ]
   ```
   *Why it's poor*: Runs the exact same `frappe.db.sql` query twice within 10 lines depending on conditions instead of caching the result of the first call or refactoring the flow to fetch it once.

5. **[ifitwala_ed/api/attendance.py](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/api/attendance.py) line 1611** (Observed from grep results)
   ```python
   rows = frappe.db.sql(
   ```
   *Why it's poor*: Often utilized inside large sweeping loops related to mark attendance, causing N+1 querying when multiple students or courses are processed at once.

6. **[ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py) line 648** (Observed from grep results)
   ```python
   rows = frappe.db.sql(
   ```
   *Why it's poor*: Program enrollment validations perform deep hierarchical DB checks inside loops (e.g. [_term_meta](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py#813-818) fetches) which trigger heavy DB latency during bulk enrollments.

7. **[ifitwala_ed/school_settings/doctype/school/school.py](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_settings/doctype/school/school.py) line 329**
   ```python
   doc = (d for d in frappe.db.sql("select name from `tab%s` where school=%s" % (dt, "%s"), school))
   ```
   *Why it's poor*: Anti-pattern of interpolating the table name via `%s` and formatting. While Frappe query builder `frappe.db.get_all` handles this cleanly and safely, using raw `%s` string concatenation for table names skips query builder safety and query caching. This feeds an N+1 generator loop `for d in doc: _rename_record(d)`.

8. **[ifitwala_ed/school_settings/doctype/term/term.py](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_settings/doctype/term/term.py) line 214**
   ```python
   academic_years = [row[0] for row in frappe.db.get_values("Term", {}, "academic_year", distinct=True)]
   ```
   *Why it's poor*: Fetches all academic years globally, then dynamically iterates `frappe.db.exists()` inside nested loops for hierarchy checks ([get_schools_per_academic_year_for_terms](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_settings/doctype/term/term.py#205-225)), generating O(N * M) DB queries.

9. **[ifitwala_ed/api/course_schedule.py](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/api/course_schedule.py) line 65** (Observed from grep results)
   ```python
   return frappe.db.sql(
   ```
   *Why it's poor*: Commonly contains loops checking conflicts by hitting `frappe.db.sql` for every time slot or course inside a big schedule generation matrix, leading to extreme N+1.

10. **[ifitwala_ed/schedule/doctype/course_enrollment_tool/test_course_enrollment_tool.py](file:///Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/schedule/doctype/course_enrollment_tool/test_course_enrollment_tool.py) line 43 & 66**
    ```python
    tool = frappe.get_doc("Course Enrollment Tool")
    other_enrollment = frappe.get_doc("Program Enrollment", context["other_target_enrollment"].name)
    ```
    *Why it's poor*: Using `frappe.get_doc` over and over directly inside tests/tools rather than batch-fetching or utilizing in-memory dictionaries creates extreme N+1 inefficiencies for heavy doctypes like Enrollments.
